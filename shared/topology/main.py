from __future__ import annotations

import argparse

from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.topo import Topo

"""
Topology is like below.

h1 --- s1 --- s2 --- s3
       |      |      |
       s4 --- s5 --- s6
       |      |      |
       s7 --- s8 --- s9 --- h2
"""


class PathSwitchTopo(Topo):
    def build(self, *args, **params):
        # add switches and links between switches
        size: int = params["size"]
        for i in range(size):
            for j in range(size):
                dpid = size * i + j + 1
                self.addSwitch(f"s{dpid}", dpid=str(dpid))

        switches: list[str] = self.switches()
        for i in range(size):
            for j in range(size):
                current = switches[size * i + j]
                if j != size - 1:
                    right = switches[size * i + j + 1]
                    self.addLink(current, right)
                if i != size - 1:
                    bottom = switches[size * (i + 1) + j]
                    self.addLink(current, bottom)

        # add hosts and links between host and switch
        host_pair: int = params["host_pair"]
        for i in range(host_pair * 2):
            self.addHost(f"h{i + 1}", ip=f"10.0.0.{i + 1}", mac=f"00:00:00:00:00:0{i + 1}")

        hosts = self.hosts()
        for i in range(host_pair):
            self.addLink(hosts[i * 2], switches[0])
            self.addLink(hosts[i * 2 + 1], switches[-1])


topos = {"path_switch_topo": lambda: PathSwitchTopo()}


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", dest="size", type=int, default=2,
                        help="size of mesh topology, size*size switches will be created.")
    parser.add_argument("--pair", dest="host_pair", type=int, default=1, help="number of host pairs")
    parser.add_argument("--log", dest="log", type=str, default="info", help="log level")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse()

    setLogLevel(args.log)

    net = Mininet(
        topo=PathSwitchTopo(size=args.size, host_pair=args.host_pair),
        controller=RemoteController("c1", ip="127.0.0.1")
    )
    net.start()
    CLI(net)
    net.stop()
