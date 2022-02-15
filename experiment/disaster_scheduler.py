from __future__ import annotations

import threading

from mininet.log import info


class DisasterScheduler(object):
    def __init__(self, switches):
        self.__switches = switches

    def run(self, failures: list[Failure]):
        for f in failures:
            t = threading.Timer(f.fail_at_sec, lambda: self.__fail(f))
            t.start()

    def __fail(self, failure: Failure):
        s = self.__switches[0]
        info(f"*** Link between {failure.node1} and {failure.node2} failed")
        s.cmd(f"ovs-vsctl del-port {failure.node1}-eth{failure.port_node1}")
        s.cmd(f"ovs-vsctl del-port {failure.node2}-eth{failure.port_node2}")


class Failure(object):
    def __init__(self, node1: str, port_node1: int, node2: str, port_node2: int, fail_at_sec: int):
        self.node1 = node1
        self.node2 = node2
        self.port_node1 = port_node1
        self.port_node2 = port_node2
        self.fail_at_sec = fail_at_sec
