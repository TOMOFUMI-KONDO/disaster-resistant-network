from __future__ import annotations

from typing import Optional

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.controller import Datapath
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib.packet.ether_types import ETH_TYPE_IPV6
from ryu.lib.packet.ethernet import ethernet
from ryu.lib.packet.packet import Packet
from ryu.ofproto.ofproto_v1_3 import OFPP_CONTROLLER, OFPCML_NO_BUFFER, OFP_VERSION, OFP_NO_BUFFER, \
    OFPP_FLOOD, OFPPR_DELETE
from ryu.ofproto.ofproto_v1_3_parser import OFPMatch, OFPActionOutput, OFPPacketOut, \
    OFPPacketIn, OFPAction, OFPPortStatus, OFPPort

from flow_addable import FlowAddable
from router import Router, Node, Link


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
        self.datapaths: dict[int, Datapath] = {}  # dict[dpid, Datapath]
        self.mac_to_port: dict[int, dict[str, int]] = {}  # dict[dpid, dict[MAC, port]]

        # TODO: Make router dynamically, not statically.
        """
        Topology is like below. (size = 2)

        h1 --- s1 --(1G)-- s2
               |           |
             (100M)      (10M)
               |           |
               s3 --(1G)-- s4 --- h2
        """
        # dict[dpid, dict[port, Node]]
        self.port_to_node: dict[int, dict[int, Node]] = {
            1: {1: Node("s2"), 2: Node("s3")},
            2: {1: Node("s1"), 2: Node("s4")},
            3: {1: Node("s1"), 2: Node("s4")},
            4: {1: Node("s2"), 2: Node("s3")},
        }
        self.router = Router(
            [Node("s1"), Node("s2"), Node("s3"), Node("s4")],
            [
                Link("s1", "s2", self.COST_OF_MBPS[1000]),
                Link("s1", "s3", self.COST_OF_MBPS[100]),
                Link("s2", "s4", self.COST_OF_MBPS[10]),
                Link("s3", "s4", self.COST_OF_MBPS[1000]),
            ],
            Node("s1"),
            Node("S4"),
        )

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp: Datapath = ev.msg.datapath
        self.datapaths[dp.id] = dp

        self.logger.info("[INFO]OFPSwitchFeature: datapath %d", dp.id)

        # send PacketIn to controller when receive unknown packet
        self._add_flow(dp, 0, OFPMatch(), [OFPActionOutput(OFPP_CONTROLLER, OFPCML_NO_BUFFER)])

        # set drop action to prevent flood loop
        if dp.id == 3:
            self._add_flow(dp, 1, OFPMatch(in_port=2), [])
        if dp.id == 4:
            self._add_flow(dp, 1, OFPMatch(in_port=2), [])

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

        self.logger.info("[INFO]PortStatus reason:%d datapath:%s port:%d", msg.reason, dpid, desc.port_no)

        if msg.reason == OFPPR_DELETE:
            print(self.router.get_links())
            opposite = self.port_to_node[dpid].pop(desc.port_no)
            self.router.rm_link_by_nodes(f"s{dpid}", opposite.name)
            print(self.router.get_links())

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
        self.mac_to_port.setdefault(dp.id, {})
        self.logger.info("[INFO]PacketIn ether_type:%s datapath:%s mac_src:%s mac_dst:%s in_port:%d",
                         hex(eth.ethertype), dp.id, eth.src, eth.dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dp.id][eth.src] = in_port

        if eth.dst in self.mac_to_port[dp.id]:
            out_port = self.mac_to_port[dp.id][eth.dst]
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
