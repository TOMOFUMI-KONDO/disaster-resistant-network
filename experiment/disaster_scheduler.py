from __future__ import annotations

import threading

from mininet.log import info


class DisasterScheduler(object):
    def __init__(self, switches):
        self.__switches = switches

    def run(self, failures: list[Failure]):
        for f in failures:
            t = threading.Timer(f.fail_at_sec, lambda x: self.__fail(x), [f])
            t.start()

    def __fail(self, failure: Failure):
        s = self.__switches[0]
        info(f"*** Link between {failure.switch1} and {failure.switch2} failed")
        s.cmd(f"ovs-vsctl del-port {failure.switch1}-eth{failure.port_switch1}")
        s.cmd(f"ovs-vsctl del-port {failure.switch2}-eth{failure.port_switch2}")


class Failure(object):
    def __init__(self, switch1: str, port_switch1: int, switch2: str, port_switch2: int, fail_at_sec: int):
        self.switch1 = switch1
        self.switch2 = switch2
        self.port_switch1 = port_switch1
        self.port_switch2 = port_switch2
        self.fail_at_sec = fail_at_sec
