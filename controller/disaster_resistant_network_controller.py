from __future__ import annotations

import json
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
    __INITIAL_ROUTE_PRIORITY = 100

    def __init__(self, *args, **kwargs):
        super(DisasterResistantNetworkController, self).__init__(*args, **kwargs)

        self.__is_updating = False
        self.__update_times = 0
        self.__route_priority = self.__INITIAL_ROUTE_PRIORITY  # this will be incremented on each routing
        self.__datapaths: list[controller.Datapath] = []
        self.__dpid_to_mac_to_port: dict[int, dict[str, int]] = {}
        self.__host_to_ip: dict[str, str] = {}
        self.__port_to_switch: dict[int, dict[int, Switch]] = {}
        self.__route_calculator = RouteCalculator(self.__ROUTING_ALGORITHM)

        kwargs['wsgi'].register(DisasterResistantNetworkWsgiController, {self.APP_INSTANCE_NAME: self})

    @property
    def host_pairs(self) -> list[list[HostClient, str, HostServer, str]]:
        return list(map(lambda x: [x[0], self.__host_to_ip[x[0].name], x[1], self.__host_to_ip[x[1].name]],
                        self.__route_calculator.host_pairs))

    @property
    def port_to_switch(self):
        return self.__port_to_switch

    @property
    def switches(self):
        return self.__route_calculator.switches

    @property
    def links(self):
        return self.__route_calculator.links

    def init(self):
        self.logger.info('[INFO]initializing controller...')

        self.__is_updating = False
        self.__update_times = 0
        self.__route_priority = self.__INITIAL_ROUTE_PRIORITY
        self.__datapaths = []
        self.__dpid_to_mac_to_port = {}
        self.__host_to_ip = {}
        self.__port_to_switch = {}
        self.__route_calculator.reset()

    def add_link(self, link: Link, s1_port: int, s2_port: int):
        self.__route_calculator.add_link(link)

        s1_dpid = self.__to_dpid(link.switch1)
        self.__port_to_switch.setdefault(s1_dpid, {})
        self.__port_to_switch[s1_dpid][s1_port] = Switch(link.switch2)

        s2_dpid = self.__to_dpid(link.switch2)
        self.__port_to_switch.setdefault(s2_dpid, {})
        self.__port_to_switch[s2_dpid][s2_port] = Switch(link.switch1)

    def register_link_fail_time(self, switch1: str, switch2: str, fail_at_sec: int):
        self.__route_calculator.register_link_fail_time(switch1, switch2, fail_at_sec)

    def add_host_pair(self, client: HostClient, client_ip: str, client_port: int,
                      server: HostServer, server_ip: str, server_port: int):
        self.__host_to_ip[client.name] = client_ip
        self.__host_to_ip[server.name] = server_ip

        self.__route_calculator.add_host_pairs(client, server)

        self.__add_flow_for_host(self.__find_dp(self.__to_dpid(client.neighbor_switch)), client_ip, client_port)
        self.__add_flow_for_host(self.__find_dp(self.__to_dpid(server.neighbor_switch)), server_ip, server_port)

    def update_host_client(self, client: str, fail_at_sec: int, datasize_gb: int):
        self.__route_calculator.update_host_client(client, fail_at_sec, datasize_gb)

    def __add_flow_for_host(self, dp: controller.Datapath, ip: str, port: int, priority=50):
        self._add_flow(dp, priority, ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=ip),
                       [ofparser.OFPActionOutput(port)])
        self._add_flow(dp, priority, ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=ip),
                       [ofparser.OFPActionOutput(port)])

    def start_update_path(self):
        self.logger.info('[INFO]started path update')
        self.__is_updating = True
        self.__update_path()

    def __update_path(self):
        if not self.__is_updating:
            return

        path = self.__route_calculator.calc_shortest_path(self.__update_times, self.__UPDATE_INTERVAL_SEC)
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
                self._add_flow(self.__find_dp(switch1_dpid), self.__route_priority,
                               ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=server_ip), actions)
                self._add_flow(self.__find_dp(switch1_dpid), self.__route_priority,
                               ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=server_ip), actions)

                # control packet from server to client
                switch2_dpid = self.__to_dpid(l.switch2)
                port_switch2_to_switch1 = self.__find_port(switch2_dpid, Switch(l.switch1))

                actions = [ofparser.OFPActionOutput(port_switch2_to_switch1)]
                self._add_flow(self.__find_dp(switch2_dpid), self.__route_priority,
                               ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=client_ip), actions)
                self._add_flow(self.__find_dp(switch2_dpid), self.__route_priority,
                               ofparser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_tpa=client_ip), actions)

        self.__route_priority += 1

    def __find_port(self, dpid: int, switch: Switch) -> Optional[int]:
        for k, v in self.__port_to_switch[dpid].items():
            if v == switch:
                return k

    def __find_dp(self, dpid: int) -> Optional[controller.Datapath]:
        for dp in self.__datapaths:
            if dp.id == dpid:
                return dp

    def __to_dpid(self, switch_name: str) -> int:
        # assume switch name is like "s[0-9]+"
        return int(switch_name[1:])

    @handler.set_ev_cls(ofp_event.EventOFPSwitchFeatures, handler.CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp: controller.Datapath = ev.msg.datapath
        self.logger.info("[INFO]OFPSwitchFeature: datapath %d", dp.id)

        self.__datapaths.append(dp)
        self.__route_calculator.add_switch(Switch(f"s{dp.id}"))

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

        if msg.reason == ofproto.OFPPR_DELETE and self.__port_to_switch[dpid].get(port_no) is not None:
            opposite = self.__port_to_switch[dpid].pop(port_no)
            self.__route_calculator.rm_link(f"s{dpid}", opposite.name)

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
        self.__dpid_to_mac_to_port.setdefault(dp.id, {})
        self.logger.info("[INFO]PacketIn ether_type:%s datapath:%s mac_src:%s mac_dst:%s in_port:%d",
                         hex(eth.ethertype), dp.id, eth.src, eth.dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.__dpid_to_mac_to_port[dp.id][eth.src] = in_port

        out_port = self.__dpid_to_mac_to_port[dp.id][eth.dst] \
            if eth.dst in self.__dpid_to_mac_to_port[dp.id] \
            else ofproto.OFPP_FLOOD
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

    @wsgi.route("disaster", "/disaster", methods=["POST"])
    def handle_disaster(self, req, **kwargs):
        self.disaster_resistant_network_app.start_update_path()
        return webob.Response(content_type="text/plain", body="success")

    @wsgi.route("init", "/init", methods=["PUT"])
    def handle_init(self, req, **kwargs):
        self.disaster_resistant_network_app.init()
        return webob.Response(content_type="text/plain", body="success")

    @wsgi.route("get port_to_switch", "/port-to-switch", methods=["GET"])
    def handle_get_port_to_swtich(self, req, **kwargs):
        port_to_switch = {dpid: {
            port: switch.name for port, switch in v.items()
        } for dpid, v in self.disaster_resistant_network_app.port_to_switch.items()}
        body = json.dumps({"result": "success", "data": {"port_to_switch": port_to_switch}})
        return webob.Response(content_type="application/json", json_body=body)

    @wsgi.route("list switches", "/switch", methods=["GET"])
    def handle_list_switches(self, req, **kwargs):
        switches = list(map(lambda x: x.name, self.disaster_resistant_network_app.switches))
        body = json.dumps({"result": "success", "data": {"switches": switches}})
        return webob.Response(content_type="application/json", json_body=body)

    @wsgi.route("list links", "/link", methods=["GET"])
    def handle_list_links(self, req, **kwargs):
        links = list(map(lambda x: {
            "switch1": x.switch1,
            "switch2": x.switch2,
            "bandwidth_mbps": x.bandwidth_mbps,
            "fail_at_sec": x.fail_at_sec
        }, self.disaster_resistant_network_app.links))
        body = json.dumps({"result": "success", "data": {"links": links}})
        return webob.Response(content_type="application/json", json_body=body)

    @wsgi.route("add link", "/link", methods=["POST"])
    def handle_add_link(self, req, **kwargs):
        s1 = req.json["switch1"]
        s2 = req.json["switch2"]
        link = Link(s1["name"], s2["name"], req.json["bandwidth_mbps"])

        self.disaster_resistant_network_app.add_link(link, s1["port"], s2["port"])
        return webob.Response(content_type="text/plain", body="success")

    @wsgi.route("register link fail time", "/link", methods=["PUT"])
    def handle_register_link_fail_time(self, req, **kwargs):
        self.disaster_resistant_network_app.register_link_fail_time(req.json["switch1"], req.json["switch2"],
                                                                    req.json["fail_at_sec"])
        return webob.Response(content_type="text/plain", body="success")

    @wsgi.route("list host pairs", "/host-pair", methods=["GET"])
    def handle_list_host_pairs(self, req, **kwargs):
        host_pairs = list(map(lambda x: {
            "client": {
                "name": x[0].name,
                "neighbor": x[0].neighbor_switch,
                "fail_at_sec": x[0].fail_at_sec,
                "datasize_gb": x[0].datasize_gb,
                "ip_address": x[1]
            },
            "server": {
                "name": x[2].name,
                "neighbor": x[2].neighbor_switch,
                "ip_address": x[3]
            }
        }, self.disaster_resistant_network_app.host_pairs))
        body = json.dumps({"result": "success", "data": {"host_pairs": host_pairs}})
        return webob.Response(content_type="application/json", json_body=body)

    @wsgi.route("add host pair", "/host-pair", methods=["POST"])
    def handle_add_host_pair(self, req, **kwargs):
        req_client = req.json["client"]
        req_server = req.json["server"]
        client = HostClient(req_client["name"], req_client["neighbor"])
        server = HostServer(req_server["name"], req_server["neighbor"])

        self.disaster_resistant_network_app.add_host_pair(client, req_client["ip_address"], req_client["port"],
                                                          server, req_server["ip_address"], req_server["port"])
        return webob.Response(content_type="text/plain", body="success")

    @wsgi.route("update host client", "/host-client", methods=["PUT"])
    def handle_update_host_pair(self, req, **kwargs):
        self.disaster_resistant_network_app.update_host_client(req.json["client"], req.json["fail_at_sec"],
                                                               req.json["datasize_gb"])
        return webob.Response(content_type="text/plain", body="success")
