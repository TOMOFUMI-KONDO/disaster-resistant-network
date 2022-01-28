from __future__ import annotations

from typing import Optional

from ryu.controller.controller import Datapath
from ryu.ofproto.ofproto_v1_3_parser import OFPMatch, OFPAction


class FlowAddable:
    def _add_flow(
            self,
            datapath: Datapath,
            priority: int,
            match: OFPMatch,
            actions: list[OFPAction],
            buffer_id: Optional[int] = None
    ):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        if buffer_id:
            mod = parser.OFPFlowMod(
                datapath=datapath,
                buffer_id=buffer_id,
                priority=priority,
                match=match,
                instructions=inst,
            )
        else:
            mod = parser.OFPFlowMod(
                datapath=datapath,
                priority=priority,
                match=match,
                instructions=inst,
            )

        datapath.send_msg(mod)
