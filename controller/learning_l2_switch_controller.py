from __future__ import annotations

from typing import Optional

import webob
from ryu.app import wsgi
from ryu.base import app_manager
from ryu.controller import ofp_event, handler, controller
from ryu.lib.packet import ether_types, ethernet, packet
from ryu.ofproto import ofproto_v1_3
from ryu.ofproto import ofproto_v1_3 as ofproto
from ryu.ofproto import ofproto_v1_3_parser as ofparser

from flow_addable import FlowAddable


class LearningL2SwitchController(app_manager.RyuApp, FlowAddable):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {'wsgi': wsgi.WSGIApplication}
    APP_INSTANCE_NAME = 'learning_l2_switch_app'

    def __init__(self, *args, **kwargs):
        super(LearningL2SwitchController, self).__init__(*args, **kwargs)
        self.__dpid_to_mac_to_port: dict[int, dict[str, int]] = {}
        kwargs['wsgi'].register(LearningL2SwitchWsgiController, {self.APP_INSTANCE_NAME: self})

    def init(self):
        self.logger.info('[INFO]initializing controller...')

        self.__dpid_to_mac_to_port = {}

    @handler.set_ev_cls(ofp_event.EventOFPSwitchFeatures, handler.CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp: controller.Datapath = ev.msg.datapath
        self.logger.info("[INFO]OFPSwitchFeature: datapath %d", dp.id)

        # send PacketIn to controller when receive unknown packet
        actions = [ofparser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self._add_flow(dp, 0, ofparser.OFPMatch(), actions)

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


class LearningL2SwitchWsgiController(wsgi.ControllerBase):
    def __init__(self, req, link, data, **config):
        super(LearningL2SwitchWsgiController, self).__init__(req, link, data, **config)
        self.learning_l2_switch_app: LearningL2SwitchController = data[LearningL2SwitchController.APP_INSTANCE_NAME]

    @wsgi.route("init", "/init", methods=["PUT"])
    def handle_init(self, req, **kwargs):
        self.learning_l2_switch_app.init()
        return webob.Response(content_type="text/plain", body="success")
