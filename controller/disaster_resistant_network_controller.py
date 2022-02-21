from __future__ import annotations

import threading
from typing import Optional

import webob
from ryu.app import wsgi
from ryu.base import app_manager
from ryu.controller import ofp_event, controller, handler
from ryu.lib.packet import ether_types, ethernet, packet
from ryu.ofproto import ofproto_v1_3 as ofproto
from ryu.ofproto import ofproto_v1_3_parser as ofparser

from components import Switch, Path, Link, HostClient, HostServer
from enums import RoutingAlgorithm
from flow_addable import FlowAddable
from route_calculator import RouteCalculator


class DisasterResistantNetworkController(app_manager.RyuApp, FlowAddable):
    OFP_VERSIONS = [ofproto.OFP_VERSION]

    _CONTEXTS = {'wsgi': wsgi.WSGIApplication}
    APP_INSTANCE_NAME = 'disaster_resistant_network_app'

    __ROUTING_ALGORITHM = RoutingAlgorithm.TAKAHIRA
    __UPDATE_INTERVAL_SEC = 30

    def __init__(self, *args, **kwargs):
        super(DisasterResistantNetworkController, self).__init__(*args, **kwargs)
        self.__is_updating = None
        self.__update_times = None
        self.__route_priority = None
        self.__datapaths = None
        self.__mac_to_port = None
        self.__host_to_ip = None
        self.__port_to_switch = None
        self.__router = None

        kwargs['wsgi'].register(DisasterResistantNetworkWsgiController, {self.APP_INSTANCE_NAME: self})
        self.init()

    def init(self):
        self.logger.info('[INFO]initializing controller...')
        self.__is_updating = False
        self.__update_times = 0
        self.__route_priority = 100  # this will be incremented on each routing
        self.__datapaths: dict[int, controller.Datapath] = {}  # dict[dpid, Datapath]
        self.__mac_to_port: dict[int, dict[str, int]] = {}  # dict[dpid, dict[MAC, port]]

        # TODO: Make router dynamically, not statically.
        """
        Topology is like below. (size = 2)

        h1-s --- s1 --(1G)-- s2 --- h2-c
                  |           |
                (10M)       (100M)
                  |           |
        h2-s --- s3 --(1G)-- s4 --- h1-c
        """
        self.__host_to_ip = {
            'h1-c': '10.0.0.1',
            'h1-s': '10.0.0.2',
            'h2-c': '10.0.0.3',
            'h2-s': '10.0.0.4',
        }

        # dict[dpid, dict[port, Switch]]
        self.__port_to_switch: dict[int, dict[int, Switch]] = {
            1: {1: Switch("s2"), 2: Switch("s3")},
            2: {1: Switch("s1"), 2: Switch("s4")},
            3: {1: Switch("s1"), 2: Switch("s4")},
            4: {1: Switch("s2"), 2: Switch("s3")},
        }
        self.__router = RouteCalculator(
            routing_algorithm=self.__ROUTING_ALGORITHM,
            host_pairs=[[HostClient('h1-c', 's4', 220, 20), HostServer('h1-s', 's1')],
                        [HostClient('h2-c', 's2', 400, 100), HostServer('h2-s', 's3')]],
            switches=[Switch("s1"), Switch("s2"), Switch("s3"), Switch("s4")],
            links=[
                Link("s1", "s2", 1, 100),
                Link("s1", "s3", 0.01, -1),
                Link("s2", "s4", 0.1, -1),
                Link("s3", "s4", 1, 220),
            ],
        )

    def start_update_path(self):
        self.logger.info('[INFO]started path update')
        self.__is_updating = True
        self.__update_path()

    def __update_path(self):
        if not self.__is_updating:
            return

        path = self.__router.calc_shortest_path(self.__update_times, self.__UPDATE_INTERVAL_SEC)
        if len(path) == 0:
            self.logger.info("[INFO]no path available")
            return

        self.logger.info(f"[INFO]updated path {self.__update_times}th")
        self.__set_route_by_path(path)

        self.__update_times += 1

        # update path every self.__update_interval_sec
        t = threading.Timer(self.__UPDATE_INTERVAL_SEC, self.__update_path)
        t.start()

    def __set_route_by_path(self, paths: list[list[HostClient, HostServer, Path]]):
        for [client, server, path] in paths:
            client_ip = self.__host_to_ip[client.name]
            server_ip = self.__host_to_ip[server.name]

            for l in path.links:
                # control packet from client to server
                switch1_dpid = self.__to_dpid(l.switch1)
                port_switch1_to_switch2 = self.__find_port(switch1_dpid, Switch(l.switch2))

                actions = [ofparser.OFPActionOutput(port_switch1_to_switch2)]
                self._add_flow(self.__datapaths[switch1_dpid], self.__route_priority,
                               ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=server_ip), actions)
                self._add_flow(self.__datapaths[switch1_dpid], self.__route_priority,
                               ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=server_ip), actions)

                # control packet from server to client
                switch2_dpid = self.__to_dpid(l.switch2)
                port_switch2_to_switch1 = self.__find_port(switch2_dpid, Switch(l.switch1))

                actions = [ofparser.OFPActionOutput(port_switch2_to_switch1)]
                self._add_flow(self.__datapaths[switch2_dpid], self.__route_priority,
                               ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=client_ip), actions)
                self._add_flow(self.__datapaths[switch2_dpid], self.__route_priority,
                               ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=client_ip), actions)

        self.__route_priority += 1

    def __find_port(self, dpid: int, switch: Switch) -> Optional[int]:
        for k, v in self.__port_to_switch[dpid].items():
            if v == switch:
                return k

    def __to_dpid(self, switch_name: str) -> int:
        # assume switch name is like "s[0-9]+"
        return int(switch_name[1:])

    @handler.set_ev_cls(ofp_event.EventOFPSwitchFeatures, handler.CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp: controller.Datapath = ev.msg.datapath
        self.__datapaths[dp.id] = dp

        self.logger.info("[INFO]OFPSwitchFeature: datapath %d", dp.id)

        # send PacketIn to controller when receive unknown packet
        actions = [ofparser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(dp, 0, ofparser.OFPMatch(), actions)

        if dp.id == 1:
            match = ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=self.__host_to_ip['h1-s'])
            self._add_flow(dp, 50, match, [ofparser.OFPActionOutput(3)])
            match = ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=self.__host_to_ip['h1-s'])
            self._add_flow(dp, 50, match, [ofparser.OFPActionOutput(3)])
        if dp.id == 2:
            match = ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=self.__host_to_ip['h2-c'])
            self._add_flow(dp, 50, match, [ofparser.OFPActionOutput(3)])
            match = ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=self.__host_to_ip['h2-c'])
            self._add_flow(dp, 50, match, [ofparser.OFPActionOutput(3)])
        if dp.id == 3:
            match = ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=self.__host_to_ip['h2-s'])
            self._add_flow(dp, 50, match, [ofparser.OFPActionOutput(3)])
            match = ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=self.__host_to_ip['h2-s'])
            self._add_flow(dp, 50, match, [ofparser.OFPActionOutput(3)])
        if dp.id == 4:
            match = ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=self.__host_to_ip['h1-c'])
            self._add_flow(dp, 50, match, [ofparser.OFPActionOutput(3)])
            match = ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=self.__host_to_ip['h1-c'])
            self._add_flow(dp, 50, match, [ofparser.OFPActionOutput(3)])

    # TODO: use to create topology dynamically
    # @set_ev_cls(ofp_event.EventOFPPortDescStatsReply)
    # def desc_stats_reply_handler(self, ev):
    #     msg: OFPPortDescStatsReply = ev.msg
    #     for port in msg.body:
    #         if port.state != OFPPS_LIVE:
    #             continue
    #
    #         mbps = int(port.curr_speed) // 10 ** 3
    #         cost = self.COST_OF_MBPS[mbps]

    @handler.set_ev_cls(ofp_event.EventOFPPortStatus, handler.MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        msg: ofparser.OFPPortStatus = ev.msg
        dpid = msg.datapath.id
        desc: ofparser.OFPPort = msg.desc
        port_no = desc.port_no

        self.logger.info("[INFO]PortStatus reason:%d datapath:%s port:%d", msg.reason, dpid, port_no)

        if msg.reason == ofproto.OFPPR_DELETE and self.__port_to_switch[dpid].get(port_no) is not None:
            opposite = self.__port_to_switch[dpid].pop(port_no)
            self.__router.rm_link(f"s{dpid}", opposite.name)

    @handler.set_ev_cls(ofp_event.EventOFPPacketIn, handler.MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg: ofparser.OFPPacketIn = ev.msg
        buffer_id = msg.buffer_id

        data = msg.data
        pkt = packet.Packet(data)
        eth: ethernet.ether = pkt.get_protocol(ethernet.ethernet)

        # ignore IPv6 ICMP
        if eth.ethertype == ether_types.ETH_TYPE_IPV6:
            return

        dp = msg.datapath
        in_port = msg.match["in_port"]
        actions = self.__handle_eth(eth, dp, in_port, buffer_id)
        if actions is None:
            return

        out = ofparser.OFPPacketOut(
            datapath=dp,
            buffer_id=buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )
        dp.send_msg(out)

    def __handle_eth(self, eth: ethernet.ethernet, dp: controller.Datapath, in_port: int, buffer_id) \
            -> Optional[list[ofparser.OFPAction]]:
        self.__mac_to_port.setdefault(dp.id, {})
        self.logger.info("[INFO]PacketIn ether_type:%s datapath:%s mac_src:%s mac_dst:%s in_port:%d",
                         hex(eth.ethertype), dp.id, eth.src, eth.dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.__mac_to_port[dp.id][eth.src] = in_port

        out_port = self.__mac_to_port[dp.id][eth.dst] if eth.dst in self.__mac_to_port[dp.id] else ofproto.OFPP_FLOOD
        actions = [ofparser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = ofparser.OFPMatch(eth_dst=eth.dst)
            if buffer_id != ofproto.OFP_NO_BUFFER:
                self._add_flow(dp, 10, match, actions, buffer_id)
                return None
            else:
                self._add_flow(dp, 10, match, actions)

        return actions


class DisasterResistantNetworkWsgiController(wsgi.ControllerBase):
    def __init__(self, req, link, data, **config):
        super(DisasterResistantNetworkWsgiController, self).__init__(req, link, data, **config)
        self.disaster_resistant_network_app: DisasterResistantNetworkController = \
            data[DisasterResistantNetworkController.APP_INSTANCE_NAME]

    @wsgi.route('disaster', '/disaster', methods=['POST'])
    def handle_disaster(self, req, **kwargs):
        self.disaster_resistant_network_app.start_update_path()
        return webob.Response(content_type='text/plain', body='success')

    @wsgi.route('init', '/init', methods=['PUT'])
    def handle_init(self, req, **kwargs):
        self.disaster_resistant_network_app.init()
        return webob.Response(content_type='text/plain', body='success')
