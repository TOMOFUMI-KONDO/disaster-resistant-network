from mininet.link import TCLink
from mininet.topo import Topo


class DisasterResistantNetworkTopo(Topo):
    def build(self, *args, **params):
        """
        Topology is like below. (size = 2)

        h1s --- s1 --(1G)-- s2 --- h2c
                 |           |
               (10M)       (100M)
                 |           |
        h2s --- s3 --(1G)-- s4 --- h1c
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
        self.addLink(switches[0], switches[1], cls=TCLink, bw=1000)  # bandwidth is specified with Mbps
        self.addLink(switches[0], switches[2], cls=TCLink, bw=10)
        self.addLink(switches[1], switches[3], cls=TCLink, bw=100)
        self.addLink(switches[2], switches[3], cls=TCLink, bw=1000)

        # NOTE: self.hosts() return hosts that are automatically ordered in alphabetically order
        # add hosts
        hosts = [
            self.addHost(f"h1c", ip=f"10.0.0.1", mac=f"00:00:00:00:00:01"),
            self.addHost(f"h1s", ip=f"10.0.0.2", mac=f"00:00:00:00:00:02"),
            self.addHost(f"h2c", ip=f"10.0.0.3", mac=f"00:00:00:00:00:03"),
            self.addHost(f"h2s", ip=f"10.0.0.4", mac=f"00:00:00:00:00:04"),
        ]

        # add links between host and switch
        self.addLink(hosts[0], switches[3])
        self.addLink(hosts[1], switches[0])
        self.addLink(hosts[2], switches[1])
        self.addLink(hosts[3], switches[2])


topos = {"disaster_resistant_network__topo": lambda: DisasterResistantNetworkTopo()}
