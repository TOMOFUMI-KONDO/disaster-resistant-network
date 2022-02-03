from __future__ import annotations

from typing import Optional

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.controller import Datapath
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.lib.packet.ether_types import ETH_TYPE_IP, ETH_TYPE_IPV6
from ryu.lib.packet.ethernet import ethernet
from ryu.lib.packet.ipv4 import ipv4
from ryu.lib.packet.packet import Packet
from ryu.ofproto.ofproto_v1_3 import OFPP_CONTROLLER, OFPCML_NO_BUFFER, OFP_VERSION, OFP_NO_BUFFER, \
    OFPP_FLOOD
from ryu.ofproto.ofproto_v1_3_parser import OFPMatch, OFPActionOutput, OFPPacketOut, \
    OFPPacketIn, OFPAction, OFPPortStatus

from flow_addable import FlowAddable
from router import Router, Node, Link


class DisasterResistantNetwork(app_manager.RyuApp, FlowAddable):
    OFP_VERSIONS = [OFP_VERSION]

    # Faster bps, lower cost
    COST_OF_MBPS = {
        10000: 1,
        1000: 10,
        100: 100,
        10: 1000,
    }

    def __init__(self, *args, **kwargs):
        super(DisasterResistantNetwork, self).__init__(*args, **kwargs)
        self.datapaths: dict[int, Datapath] = {}
        self.mac_to_port: dict[int, dict[str, int]] = {}
        self.ip_to_port: dict[int, dict[str, int]] = {}

        """
        Topology is like below. (size = 2)

        h1 --- s1 -1G- s2
               |        |
              100M     10M 
               |        |
               s3 -1G- s4 --- h2
        """
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
        self.logger.info("[INFO]OFPSwitchFeature: Datapath %d", dp.id)

        self.datapaths[dp.id] = dp

        # send PacketIn to controller when receive unknown packet
        self._add_flow(dp, 0, OFPMatch(), [OFPActionOutput(OFPP_CONTROLLER, OFPCML_NO_BUFFER)])

        # set static route to prevent flood loop
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

        # if msg.reason == OFPPR_DELETE:
        #     self.logger.info(msg)

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
        if eth.ethertype == ETH_TYPE_IP:
            actions = self.__handle_ip(pkt.get_protocol(ipv4), dp, in_port, buffer_id)
        else:
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

        self.logger.info("[INFO]PacketIn ether_type: %s datapath:%s mac_src:%s mac_dst:%s in_port:%d",
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

    def __handle_ip(self, ip: ipv4, dp: Datapath, in_port: int, buffer_id) -> Optional[list[OFPAction]]:
        self.ip_to_port.setdefault(dp.id, {})

        self.logger.info("[INFO]PacketIn datapath:%s ip_src:%s ip_dst:%s in_port:%d", dp.id, ip.src, ip.dst, in_port)

        # learn a ipv4 address to avoid FLOOD next time.
        self.ip_to_port[dp.id][ip.src] = in_port

        if ip.dst in self.ip_to_port[dp.id]:
            out_port = self.ip_to_port[dp.id][ip.dst]
        else:
            out_port = OFPP_FLOOD

        actions = [OFPActionOutput(out_port)]

        # install a flow to avoid packet_in next time
        if out_port != OFPP_FLOOD:
            match = OFPMatch(eth_type=ETH_TYPE_IP, ipv4_dst=ip.dst)
            if buffer_id != OFP_NO_BUFFER:
                self._add_flow(dp, 20, match, actions, buffer_id)
                return None
            else:
                self._add_flow(dp, 20, match, actions)

        return actions
