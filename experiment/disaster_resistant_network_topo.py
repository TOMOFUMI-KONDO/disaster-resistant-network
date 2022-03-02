import random

from mininet.link import TCLink
from mininet.topo import Topo


class DisasterResistantNetworkTopo(Topo):
    BW_MIN_MBPS = 500
    BW_MAX_MBPS = 1000

    def build(self, *args, **params):
        """
        Topology is like below. (size = 3)

        h1s --- s1 --- s2 --- s3 --- h2c
                 |     |      |
                s4 --- s5 --- s6
                 |     |      |
        h2s --- s7 --- s8 --- s9 --- h1c
        """
        # add switches
        size = params["size"]
        switches = []
        for i in range(size):
            for j in range(size):
                dpid = size * i + j + 1
                switches.append(self.addSwitch(f"s{dpid}", dpid=str(dpid)))

        # # add links between switches
        for i in range(size):
            for j in range(size):
                switch = switches[size * i + j]
                if j != size - 1:
                    right = switches[size * i + j + 1]
                    self.addLink(switch, right, cls=TCLink, bw=self.__bandwidth())
                if i != size - 1:
                    bottom = switches[size * (i + 1) + j]
                    self.addLink(switch, bottom, cls=TCLink, bw=self.__bandwidth())

        # NOTE: self.hosts() return hosts that are automatically ordered in alphabetically order
        # add hosts
        hosts = [
            self.addHost(f"h1c", ip=f"10.0.0.1", mac=f"00:00:00:00:00:01"),
            self.addHost(f"h1s", ip=f"10.0.0.2", mac=f"00:00:00:00:00:02"),
            self.addHost(f"h2c", ip=f"10.0.0.3", mac=f"00:00:00:00:00:03"),
            self.addHost(f"h2s", ip=f"10.0.0.4", mac=f"00:00:00:00:00:04"),
        ]

        # add links between host and switch
        self.addLink(hosts[0], switches[size * size - 1])  # h1c
        self.addLink(hosts[1], switches[0])  # h1s
        self.addLink(hosts[2], switches[size - 1])  # h2c
        self.addLink(hosts[3], switches[size * (size - 1)])  # h2s

    def __bandwidth(self):
        return random.randint(self.BW_MIN_MBPS, self.BW_MAX_MBPS)


topos = {"disaster_resistant_network__topo": lambda: DisasterResistantNetworkTopo()}
