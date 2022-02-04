from __future__ import annotations

import argparse
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.topo import Topo


class DisasterResistantNetworkTopo(Topo):
    def build(self, *args, **params):
        """
        Topology is like below. (size = 3)

        h1 --- s1 --- s2 --- s3
               |      |      |
               s4 --- s5 --- s6
               |      |      |
               s7 --- s8 --- s9 --- h2
        """

        # add switches
        # size = params["size"]
        # switches = []
        # for i in range(size):
        #     for j in range(size):
        #         dpid = size * i + j + 1
        #         switches.append(self.addSwitch(f"s{dpid}", dpid=str(dpid)))
        #
        # # add links between switches
        # for i in range(size):
        #     for j in range(size):
        #         current = switches[size * i + j]
        #         if j != size - 1:
        #             right = switches[size * i + j + 1]
        #             self.addLink(current, right)
        #         if i != size - 1:
        #             bottom = switches[size * (i + 1) + j]
        #             self.addLink(current, bottom)
        switches = [self.addSwitch(f"s{i}", dpid=str(i)) for i in range(1, 5)]
        self.addLink(switches[0], switches[1], cls=TCLink, bw=1000)
        self.addLink(switches[0], switches[2], cls=TCLink, bw=10)
        self.addLink(switches[1], switches[3], cls=TCLink, bw=100)
        self.addLink(switches[2], switches[3], cls=TCLink, bw=1000)

        # add hosts
        hosts = [
            self.addHost(f"h1", ip=f"10.0.0.1", mac=f"00:00:00:00:00:01"),
            self.addHost(f"h2", ip=f"10.0.0.2", mac=f"00:00:00:00:00:02"),
        ]

        # add links between host and switch
        self.addLink(hosts[0], switches[0])
        self.addLink(hosts[1], switches[-1])


topos = {"disaster_resistant_network__topo": lambda: DisasterResistantNetworkTopo()}


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    # parser.add_argument("--size", dest="size", type=int, default=2,
    #                     help="size of mesh topology, size*size switches will be created.")
    parser.add_argument("--log", dest="log", type=str, default="info", help="log level")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse()

    setLogLevel(args.log)

    net = Mininet(
        topo=DisasterResistantNetworkTopo(),
        controller=RemoteController("c0", port=6633),
    )
    net.start()
    CLI(net)
    net.stop()
