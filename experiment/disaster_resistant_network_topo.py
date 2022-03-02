import random

from mininet.link import TCLink
from mininet.topo import Topo


class DisasterResistantNetworkTopo(Topo):
    BW_MIN_MBPS = 500
    BW_MAX_MBPS = 1000

    def build(self, *args, **params):
        """
        Topology is like below. (size = 3)

        h3s --- s1 --- s2 --- s3 --- h1c
                 |     |      |
        h1s --- s4 --- s5 --- s6 --- h2c
                 |     |      |
        h2s --- s7 --- s8 --- s9 --- h3c
        """
        # add switches
        size = params["size"]
        switches = []
        for i in range(size):
            for j in range(size):
                dpid = size * i + j + 1
                switches.append(self.addSwitch(f"s{dpid}", dpid=str(dpid)))

        # add links between switches
        # for i in range(size):
        #     for j in range(size):
        #         switch = switches[size * i + j]
        #         if j != size - 1:
        #             right = switches[size * i + j + 1]
        #             self.addLink(switch, right, cls=TCLink, bw=self.__bandwidth())
        #         if i != size - 1:
        #             bottom = switches[size * (i + 1) + j]
        #             self.addLink(switch, bottom, cls=TCLink, bw=self.__bandwidth())
        # TODO: create links dynamically according to size
        self.addLink(switches[0], switches[1], cls=TCLink, bw=779)
        self.addLink(switches[0], switches[3], cls=TCLink, bw=605)
        self.addLink(switches[1], switches[2], cls=TCLink, bw=861)
        self.addLink(switches[1], switches[4], cls=TCLink, bw=748)
        self.addLink(switches[2], switches[5], cls=TCLink, bw=813)
        self.addLink(switches[3], switches[4], cls=TCLink, bw=550)
        self.addLink(switches[3], switches[6], cls=TCLink, bw=662)
        self.addLink(switches[4], switches[5], cls=TCLink, bw=610)
        self.addLink(switches[4], switches[7], cls=TCLink, bw=681)
        self.addLink(switches[5], switches[8], cls=TCLink, bw=524)
        self.addLink(switches[6], switches[7], cls=TCLink, bw=786)
        self.addLink(switches[7], switches[8], cls=TCLink, bw=753)

        # NOTE: self.hosts() return hosts that are automatically ordered in alphabetically order
        # add hosts
        hosts = [
            self.addHost(f"h1c", ip=f"10.0.0.1", mac=f"00:00:00:00:00:01"),
            self.addHost(f"h1s", ip=f"10.0.0.2", mac=f"00:00:00:00:00:02"),
            self.addHost(f"h2c", ip=f"10.0.0.3", mac=f"00:00:00:00:00:03"),
            self.addHost(f"h2s", ip=f"10.0.0.4", mac=f"00:00:00:00:00:04"),
            self.addHost(f"h3c", ip=f"10.0.0.5", mac=f"00:00:00:00:00:05"),
            self.addHost(f"h3s", ip=f"10.0.0.6", mac=f"00:00:00:00:00:06"),
        ]

        # NOTE: assume size is 3
        # add links between host and switch
        self.addLink(hosts[0], switches[2])
        self.addLink(hosts[1], switches[3])
        self.addLink(hosts[2], switches[5])
        self.addLink(hosts[3], switches[6])
        self.addLink(hosts[4], switches[8])
        self.addLink(hosts[5], switches[0])

    def __bandwidth(self):
        return random.randint(self.BW_MIN_MBPS, self.BW_MAX_MBPS)


topos = {"disaster_resistant_network__topo": lambda: DisasterResistantNetworkTopo()}
