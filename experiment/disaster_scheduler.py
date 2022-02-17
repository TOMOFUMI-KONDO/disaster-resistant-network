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

        if isinstance(failure, LinkFailure):
            info(f"*** Link between {failure.switch1} and {failure.switch2} failed\n")
            s.vsctl(f"del-port {failure.switch1}-eth{failure.port_switch1}")
            s.vsctl(f"del-port {failure.switch2}-eth{failure.port_switch2}")
        elif isinstance(failure, HostFailure):
            info(f"*** Host {failure.host} failed\n")
            s.vsctl(f"del-port {failure.neighbor_switch}-eth{failure.port}")


class Failure(object):
    def __init__(self, fail_at_sec: int):
        self.fail_at_sec = fail_at_sec


class LinkFailure(Failure):
    def __init__(self, switch1: str, port_switch1: int, switch2: str, port_switch2: int, fail_at_sec: int):
        super(LinkFailure, self).__init__(fail_at_sec)
        self.switch1 = switch1
        self.switch2 = switch2
        self.port_switch1 = port_switch1
        self.port_switch2 = port_switch2


class HostFailure(Failure):
    def __init__(self, host: str, neighbor_switch: str, port: int, fail_at_sec: int):
        super(HostFailure, self).__init__(fail_at_sec)
        self.host = host
        self.neighbor_switch = neighbor_switch
        self.port = port
