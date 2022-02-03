from __future__ import annotations

import argparse

from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.topo import Topo


class DisasterResistantNetworkTopo(Topo):
    def build(self, *args, **params):
        """
        Topology is like below.

        h1 --- s1 --- s2 --- s3
               |      |      |
               s4 --- s5 --- s6
               |      |      |
               s7 --- s8 --- s9 --- h2
        """

        # add switches
        size = params["size"]
        for i in range(size):
            for j in range(size):
                dpid = size * i + j + 1
                self.addSwitch(f"s{dpid}", dpid=str(dpid))

        # add links between switches
        switches = self.switches()
        for i in range(size):
            for j in range(size):
                current = switches[size * i + j]
                if j != size - 1:
                    right = switches[size * i + j + 1]
                    self.addLink(current, right)
                if i != size - 1:
                    bottom = switches[size * (i + 1) + j]
                    self.addLink(current, bottom)

        # add hosts
        self.addHost(f"h1", ip=f"10.0.0.1", mac=f"00:00:00:00:00:01")
        self.addHost(f"h2", ip=f"10.0.0.2", mac=f"00:00:00:00:00:02")

        # add links between host and switch
        hosts = self.hosts()
        self.addLink(hosts[0], switches[0])
        self.addLink(hosts[1], switches[-1])


topos = {"disaster_resistant_network__topo": lambda: DisasterResistantNetworkTopo()}


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", dest="size", type=int, default=2,
                        help="size of mesh topology, size*size switches will be created.")
    parser.add_argument("--log", dest="log", type=str, default="info", help="log level")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse()

    setLogLevel(args.log)

    net = Mininet(
        topo=DisasterResistantNetworkTopo(size=args.size),
        controller=RemoteController("c1", ip="127.0.0.1")
    )
    net.start()
    CLI(net)
    net.stop()
