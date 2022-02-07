from __future__ import annotations

from time import sleep

import argparse
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.topo import Topo


def main():
    args = parse()

    setLogLevel(args.log)

    net = Mininet(
        topo=DisasterResistantNetworkTopo(),
        controller=RemoteController("c0", port=6633),
    )
    net.start()

    if args.cli:
        CLI(net)
    run(net)
    if args.cli:
        CLI(net)

    net.stop()


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    # parser.add_argument("--size", dest="size", type=int, default=2,
    #                     help="size of mesh topology, size*size switches will be created.")
    parser.add_argument("--cli", dest="cli", type=bool, default=0, help="enable cli")
    parser.add_argument("--log", dest="log", type=str, default="info", help="log level")
    return parser.parse_args()


def run(net: Mininet):
    h0, h1 = net.hosts[0], net.hosts[1]
    setup(h0)
    start_backup(h1, f"{h0.IP()}:44300")

    sleep(10)  # wait to start disaster
    start_disaster(net)


# prepare for back up data
def setup(receiver):
    # suffix = datetime.now().strftime('%Y%m%d_%H%M%S')
    suffix = ""
    receiver.cmd(f"./bin/server -v > log/server_{suffix}.log &")
    sleep(5)  # wait to boot server


def start_backup(sender, dst):
    sender.cmd(f"./bin/client -addr {dst} -file 1G.txt &")


def start_disaster(net: Mininet):
    info("*** Link between s1 and s2 is being swept by tsunami...\n")
    net.switches[0].cmd("ovs-vsctl del-port s1-eth1")
    net.switches[0].cmd("ovs-vsctl del-port s2-eth1")


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

        # TODO: create any given size topology
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

if __name__ == "__main__":
    main()
