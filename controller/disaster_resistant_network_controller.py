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

from components import Node, Path, Link
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

        kwargs['wsgi'].register(DisasterResistantNetworkWsgiController, {self.APP_INSTANCE_NAME: self})

        self.__h1 = "10.0.0.1"
        self.__h2 = "10.0.0.2"
        self.__update_times = 0

        self.__init()

    def __init(self):
        self.__route_priority = 100  # this will be incremented on each routing
        self.__datapaths: dict[int, controller.Datapath] = {}  # dict[dpid, Datapath]
        self.__mac_to_port: dict[int, dict[str, int]] = {}  # dict[dpid, dict[MAC, port]]

        # TODO: Make router dynamically, not statically.
        """
        Topology is like below. (size = 2)

        h1 --- s1 --(1G)-- s2
               |           |
             (10M)       (100M)
               |           |
               s3 --(1G)-- s4 --- h2
        """
        # dict[dpid, dict[port, Node]]
        self.__port_to_node: dict[int, dict[int, Node]] = {
            1: {1: Node("s2"), 2: Node("s3")},
            2: {1: Node("s1"), 2: Node("s4")},
            3: {1: Node("s1"), 2: Node("s4")},
            4: {1: Node("s2"), 2: Node("s3")},
        }
        links = [
            Link("s1", "s2", 1000, 100),
            Link("s1", "s3", 10, -1),
            Link("s2", "s4", 100, -1),
            Link("s3", "s4", 1000, 220),
        ]

        self.__router = RouteCalculator(
            routing_algorithm=self.__ROUTING_ALGORITHM,
            nodes=[Node("s1"), Node("s2"), Node("s3"), Node("s4")],
            links=links,
            src=Node("s1"),
            dst=Node("s4"),
            datasize_gb=20
        )

    def start_update_path(self):
        self.logger.info('[INFO]started path update')
        self.__update_path()

    def __update_path(self):
        path = self.__router.calc_shortest_path(self.__update_times, self.__UPDATE_INTERVAL_SEC)
        if path is None:
            self.logger.info("[INFO]no path available")
            return

        self.logger.info("[INFO]updated path")
        self.__set_route_by_path(path)

        self.__update_times += 1

        # update path every self.__update_interval_sec
        t = threading.Timer(self.__UPDATE_INTERVAL_SEC, self.__update_path)
        t.start()

    @handler.set_ev_cls(ofp_event.EventOFPSwitchFeatures, handler.CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp: controller.Datapath = ev.msg.datapath
        self.__datapaths[dp.id] = dp

        self.logger.info("[INFO]OFPSwitchFeature: datapath %d", dp.id)

        # send PacketIn to controller when receive unknown packet
        actions = [ofparser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(dp, 0, ofparser.OFPMatch(), actions)

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

        if msg.reason == ofproto.OFPPR_DELETE and self.__port_to_node[dpid].get(port_no) is not None:
            opposite = self.__port_to_node[dpid].pop(port_no)
            self.__router.rm_link(f"s{dpid}", opposite.name)

            # NOTE: This is temporary impl that initializes when all link is removed to run experiment in succession.
            num_link = [len(x.keys()) for x in self.__port_to_node.values()]
            if num_link == 0:
                self.logger.info('[INFO]initialize controller')
                self.__init()
                return

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

        if eth.dst in self.__mac_to_port[dp.id]:
            out_port = self.__mac_to_port[dp.id][eth.dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [ofparser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = ofparser.OFPMatch(eth_dst=eth.dst)
            if buffer_id != ofproto.OFP_NO_BUFFER:
                self._add_flow(dp, 10, match, actions, buffer_id)
                return None
            else:
                self._add_flow(dp, 10, match, actions)

        return actions

    def __set_route_by_path(self, path: Path):
        for l in path.links:
            node1_dpid = self.__to_dpid(l.node1)
            port_node1_to_node2 = self.__find_port(node1_dpid, Node(l.node2))
            match = ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=self.__h2)
            actions = [ofparser.OFPActionOutput(port_node1_to_node2)]
            self._add_flow(self.__datapaths[node1_dpid], self.__route_priority, match, actions)

            node2_dpid = self.__to_dpid(l.node2)
            port_node2_to_node1 = self.__find_port(node2_dpid, Node(l.node1))
            match = ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=self.__h1)
            actions = [ofparser.OFPActionOutput(port_node2_to_node1)]
            self._add_flow(self.__datapaths[node2_dpid], self.__route_priority, match, actions)

        self.__route_priority += 1

    def __find_port(self, dpid: int, node: Node) -> Optional[int]:
        for k, v in self.__port_to_node[dpid].items():
            if v == node:
                return k

    def __to_dpid(self, switch_name: str) -> int:
        # assume switch name is like "s[0-9]+"
        return int(switch_name[1:])


class DisasterResistantNetworkWsgiController(wsgi.ControllerBase):
    def __init__(self, req, link, data, **config):
        super(DisasterResistantNetworkWsgiController, self).__init__(req, link, data, **config)
        self.disaster_resistant_network_app: DisasterResistantNetworkController = \
            data[DisasterResistantNetworkController.APP_INSTANCE_NAME]

    @wsgi.route('disaster_notification', '/disaster/notify', methods=['POST'])
    def handle_disaster_notification(self, req, **kwargs):
        self.disaster_resistant_network_app.start_update_path()
        return webob.Response(content_type='text/plain', body='success')
