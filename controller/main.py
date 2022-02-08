from __future__ import annotations

from typing import Optional

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.controller import Datapath
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib.packet.ether_types import ETH_TYPE_IPV6, ETH_TYPE_IP
from ryu.lib.packet.ethernet import ethernet
from ryu.lib.packet.packet import Packet
from ryu.ofproto.ofproto_v1_3 import OFPP_CONTROLLER, OFPCML_NO_BUFFER, OFP_VERSION, OFP_NO_BUFFER, \
    OFPP_FLOOD, OFPPR_DELETE
from ryu.ofproto.ofproto_v1_3_parser import OFPMatch, OFPActionOutput, OFPPacketOut, \
    OFPPacketIn, OFPAction, OFPPortStatus, OFPPort

from flow_addable import FlowAddable
from router import Router, Node, Link, Path


class DisasterResistantNetwork(app_manager.RyuApp, FlowAddable):
    OFP_VERSIONS = [OFP_VERSION]

    # faster bps, lower cost
    COST_OF_MBPS = {
        10000: 1,
        1000: 10,
        100: 100,
        10: 1000,
    }

    def __init__(self, *args, **kwargs):
        super(DisasterResistantNetwork, self).__init__(*args, **kwargs)
        self.__route_priority = 100  # this will be incremented on each routing
        self.__datapaths: dict[int, Datapath] = {}  # dict[dpid, Datapath]
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
        self.__router = Router(
            [Node("s1"), Node("s2"), Node("s3"), Node("s4")],
            [
                Link("s1", "s2", self.COST_OF_MBPS[1000]),
                Link("s1", "s3", self.COST_OF_MBPS[10]),
                Link("s2", "s4", self.COST_OF_MBPS[100]),
                Link("s3", "s4", self.COST_OF_MBPS[1000]),
            ],
            Node("s1"),
            Node("s4"),
        )
        self.h1 = "10.0.0.1"
        self.h2 = "10.0.0.2"

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp: Datapath = ev.msg.datapath
        self.__datapaths[dp.id] = dp

        self.logger.info("[INFO]OFPSwitchFeature: datapath %d", dp.id)

        # send PacketIn to controller when receive unknown packet
        self._add_flow(dp, 0, OFPMatch(), [OFPActionOutput(OFPP_CONTROLLER, OFPCML_NO_BUFFER)])

        # set drop action to prevent flood loop
        # if dp.id == 3:
        #     self._add_flow(dp, 1, OFPMatch(in_port=2), [])
        # if dp.id == 4:
        #     self._add_flow(dp, 1, OFPMatch(in_port=2), [])

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

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        msg: OFPPortStatus = ev.msg
        dpid = msg.datapath.id
        desc: OFPPort = msg.desc
        port_no = desc.port_no

        self.logger.info("[INFO]PortStatus reason:%d datapath:%s port:%d", msg.reason, dpid, port_no)

        if msg.reason == OFPPR_DELETE and self.__port_to_node[dpid].get(port_no) is not None:
            opposite = self.__port_to_node[dpid].pop(port_no)
            self.__router.rm_link(f"s{dpid}", opposite.name)

            path = self.__router.calc_shortest_path()
            if path is None:
                return

            self.__set_route_by_path(path)

    @set_ev_cls(ofp_event.EventOFPPacketIn)
    def packet_in_handler(self, ev):
        msg: OFPPacketIn = ev.msg
        buffer_id = msg.buffer_id

        data = msg.data
        pkt = Packet(data)
        eth: ethernet = pkt.get_protocol(ethernet)

        # ignore IPv6 ICMP
        if eth.ethertype == ETH_TYPE_IPV6:
            return

        dp: Datapath = msg.datapath
        in_port = msg.match["in_port"]
        actions = self.__handle_eth(eth, dp, in_port, buffer_id)
        if actions is None:
            return

        out = OFPPacketOut(
            datapath=dp,
            buffer_id=buffer_id,
            in_port=in_port,
            actions=actions,
            data=data
        )
        dp.send_msg(out)

    def __handle_eth(self, eth: ethernet, dp: Datapath, in_port: int, buffer_id) -> Optional[list[OFPAction]]:
        self.__mac_to_port.setdefault(dp.id, {})
        self.logger.info("[INFO]PacketIn ether_type:%s datapath:%s mac_src:%s mac_dst:%s in_port:%d",
                         hex(eth.ethertype), dp.id, eth.src, eth.dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.__mac_to_port[dp.id][eth.src] = in_port

        if eth.dst in self.__mac_to_port[dp.id]:
            out_port = self.__mac_to_port[dp.id][eth.dst]
        else:
            out_port = OFPP_FLOOD

        actions = [OFPActionOutput(out_port)]

        if out_port != OFPP_FLOOD:
            match = OFPMatch(eth_dst=eth.dst)
            if buffer_id != OFP_NO_BUFFER:
                self._add_flow(dp, 10, match, actions, buffer_id)
                return None
            else:
                self._add_flow(dp, 10, match, actions)

        return actions

    def __set_route_by_path(self, path: Path):
        for l in path.links:
            node1_dpid = self.__to_dpid(l.node1)
            port_node1_to_node2 = self.__find_port(node1_dpid, Node(l.node2))
            self._add_flow(self.__datapaths[node1_dpid], self.__route_priority,
                           OFPMatch(eth_type=ETH_TYPE_IP, ipv4_dst=self.h2), [OFPActionOutput(port_node1_to_node2)])

            node2_dpid = self.__to_dpid(l.node2)
            port_node2_to_node1 = self.__find_port(node2_dpid, Node(l.node1))
            self._add_flow(self.__datapaths[node2_dpid], self.__route_priority,
                           OFPMatch(eth_type=ETH_TYPE_IP, ipv4_dst=self.h1), [OFPActionOutput(port_node2_to_node1)])

        self.__route_priority += 1

    def __find_port(self, dpid: int, node: Node) -> Optional[int]:
        for k, v in self.__port_to_node[dpid].items():
            if v == node:
                return k

    def __to_dpid(self, switch_name: str) -> int:
        # assume switch name is like "s[0-9]+"
        return int(switch_name[1:])
