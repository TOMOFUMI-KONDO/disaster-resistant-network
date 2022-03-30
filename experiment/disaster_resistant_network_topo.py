from __future__ import annotations

import json
import random

import requests
from mininet.link import TCLink
from mininet.topo import Topo


class DisasterResistantNetworkTopo(Topo):
    __BW_MIN_MBPS = 500
    __BW_MAX_MBPS = 1000

    __URL = "http://localhost:8080"

    def __init__(self, *args, **params):
        self.__switch_port_counts = {}
        self.__links = []
        self.__host_pairs = []
        super(DisasterResistantNetworkTopo, self).__init__(*args, **params)

    # return n links selected randomly
    def rand_links(self, n: int) -> list[dict]:
        return random.choices(self.__links, k=n)

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
                name = f"s{dpid}"
                switches.append(self.addSwitch(name, dpid=hex(dpid)[2:]))
                self.__switch_port_counts[name] = 0

        # add links between switches
        for i in range(size):
            for j in range(size):
                switch = switches[size * i + j]
                if j != size - 1:
                    right = switches[size * i + j + 1]
                    self.__switch_port_counts[switch] += 1
                    self.__switch_port_counts[right] += 1
                    self.__add_link(switch, self.__switch_port_counts[switch], right, self.__switch_port_counts[right])

                if i != size - 1:
                    bottom = switches[size * (i + 1) + j]
                    self.__switch_port_counts[switch] += 1
                    self.__switch_port_counts[bottom] += 1
                    self.__add_link(switch, self.__switch_port_counts[switch],
                                    bottom, self.__switch_port_counts[bottom])

        # NOTE: assume size >= 3
        # NOTE: self.hosts() return hosts that are automatically ordered in alphabetically order
        # add 3 host pairs
        switch_for_h1c = switches[size - 1]
        self.__switch_port_counts[switch_for_h1c] += 1
        switch_for_h1s = switches[size]
        self.__switch_port_counts[switch_for_h1s] += 1
        self.__add_host_pair("h1c", self.__switch_port_counts[switch_for_h1c],
                             "10.0.0.1", "00:00:00:00:00:01", switch_for_h1c,
                             "h1s", self.__switch_port_counts[switch_for_h1s],
                             "10.0.0.2", "00:00:00:00:00:02", switch_for_h1s)

        switch_for_h2c = switches[size * (size // 2 + 1) - 1]
        self.__switch_port_counts[switch_for_h2c] += 1
        switch_for_h2s = switches[size * (size - 1)]
        self.__switch_port_counts[switch_for_h2s] += 1
        self.__add_host_pair("h2c", self.__switch_port_counts[switch_for_h2c],
                             "10.0.0.3", "00:00:00:00:00:03", switch_for_h2c,
                             "h2s", self.__switch_port_counts[switch_for_h2s],
                             "10.0.0.4", "00:00:00:00:00:04", switch_for_h2s)

        switch_for_h3c = switches[size * size - 1]
        self.__switch_port_counts[switch_for_h3c] += 1
        switch_for_h3s = switches[0]
        self.__switch_port_counts[switch_for_h3s] += 1
        self.__add_host_pair("h3c", self.__switch_port_counts[switch_for_h3c],
                             "10.0.0.5", "00:00:00:00:00:05", switch_for_h3c,
                             "h3s", self.__switch_port_counts[switch_for_h3s],
                             "10.0.0.6", "00:00:00:00:00:06", switch_for_h3s)

    def __add_link(self, switch1: str, switch1_port: int, switch2: str, switch2_port: int, bw: int = None, cls=TCLink):
        if bw is None:
            bw = self.__rand_bandwidth()

        # add link to mininet
        self.addLink(switch1, switch2, cls=cls, bw=bw)

        # register link to controller
        self.__links.append({
            "switch1": {"name": switch1, "port": switch1_port},
            "switch2": {"name": switch2, "port": switch2_port},
            "bandwidth_mbps": bw,
        })

    def __add_host_pair(self, client_name: str, client_port: int, client_ip: str, client_mac: str, client_neighbor: str,
                        server_name: str, server_port: int, server_ip: str, server_mac: str, server_neighbor: str):
        # add host to mininet
        self.addHost(client_name, ip=client_ip, mac=client_mac)
        self.addHost(server_name, ip=server_ip, mac=server_mac)
        self.addLink(client_name, client_neighbor)
        self.addLink(server_name, server_neighbor)

        # register host-pair to controller
        self.__host_pairs.append({
            "client": {
                "name": client_name,
                "port": client_port,
                "ip_address": client_ip,
                "neighbor": client_neighbor
            },
            "server": {
                "name": server_name,
                "port": server_port,
                "ip_address": server_ip,
                "neighbor": server_neighbor
            }
        })

    def __rand_bandwidth(self):
        return random.randint(self.__BW_MIN_MBPS, self.__BW_MAX_MBPS)

    def register_links(self):
        for l in self.__links:
            requests.post(self.__URL + "/link", data=json.dumps(l))

    def register_host_pairs(self):
        for h in self.__host_pairs:
            requests.post(self.__URL + "/host-pair", data=json.dumps(h))


topos = {"disaster_resistant_network__topo": lambda: DisasterResistantNetworkTopo()}
