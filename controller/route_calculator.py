from __future__ import annotations

from typing import Optional

from components import Switch, Link, Path, HostServer, HostClient, DirectedLink
from enums import RoutingAlgorithm


class RouteCalculator(object):
    # approximate infinite cost and bandwidth
    COST_INF = 10 ** 10
    BANDWIDTH_INF = 10 ** 10

    def __init__(self, routing_algorithm: RoutingAlgorithm = RoutingAlgorithm.DIJKSTRA,
                 host_pairs: list[list[HostClient, HostServer]] = None,
                 switches: list[Switch] = None,
                 links: list[Link] = None):
        self.__routing_algorithm = routing_algorithm

        if host_pairs is None:
            self.__host_pairs = []
        else:
            self.__host_pairs = host_pairs

        if switches is None:
            self.__switches = []
        else:
            self.__switches = switches

        if links is None:
            self.__links = []
        else:
            self.__links = links

    @property
    def host_pairs(self) -> list[list[HostClient, HostServer]]:
        return self.__host_pairs

    def add_host_pairs(self, client: HostClient, server: HostServer):
        self.__host_pairs.append([client, server])

    def update_host_client(self, client: str, fail_at_sec: int, datasize_gb: int):
        index = self.__find_host_pair_by_client(client)
        if index is None:
            return

        host_pair = self.host_pairs[index]
        client = host_pair[0]
        client.fail_at_sec = fail_at_sec
        client.datasize_gb = datasize_gb
        server = host_pair[1]

        self.__host_pairs.pop(index)
        self.add_host_pairs(client, server)

    def __find_host_pair_by_client(self, client: str) -> Optional[int]:
        for i in range(len(self.host_pairs)):
            host_pair = self.host_pairs[i]
            if host_pair[0].name == client:
                return i

    @property
    def switches(self) -> list[Switch]:
        return self.__switches

    def add_switch(self, switch: Switch):
        self.__switches.append(switch)

    def rm_switch(self, switch: str):
        switch = self.__find_switch(switch)
        if switch is None:
            return

        self.__switches.remove(switch)
        links = self.__find_links_by_switch(switch)
        for l in links:
            self.rm_link(l.switch1, l.switch2)

    @property
    def links(self) -> list[Link]:
        return self.__links

    def add_link(self, link: Link):
        found = self.__find_link_by_switches(link.switch1, link.switch2)
        if found is None:
            self.__links.append(link)

    def register_link_fail_time(self, switch1: str, switch2: str, fail_at_sec: int):
        link = self.__find_link_by_switches(switch1, switch2)
        link.fail_at_sec = fail_at_sec

        # replace link with one with fail_at_sec
        self.rm_link(switch1, switch2)
        self.add_link(link)

    def rm_link(self, switch1: str, switch2: str):
        link = self.__find_link_by_switches(switch1, switch2)
        if link is None:
            return
        self.__links.remove(link)

    def calc_shortest_path(self, nth_update: int = 0, update_interval_sec: int = 0) \
            -> list[list[HostClient, HostServer, Path]]:
        if self.__routing_algorithm == RoutingAlgorithm.DIJKSTRA:
            return self.__calc_dijkstra()

        if self.__routing_algorithm == RoutingAlgorithm.TAKAHIRA:
            return self.__calc_takahira(nth_update, update_interval_sec)

        raise ValueError(f"Routing algorithm is invalid: {self.__routing_algorithm}")

    # TODO: fix to use host_pair instead of src and dst
    def __calc_dijkstra(self) -> list[list[HostClient, HostServer, Path]]:
        """
        Calculate the shortest path from src to dst by dijkstra.

        :return:
        Path:shortest path from src to dst
        """
        link_to_switch: dict[Switch, Link] = {}
        fixed_switches = [self.__src]
        costs = {self.__src: 0}
        for s in self.__switches:
            if s != self.__src:
                costs[s] = self.COST_INF

        # update neighbors of last fixed switch
        while self.__dst not in fixed_switches:
            last_fixed_switch = fixed_switches[-1]
            for neighbor in self.__neighbors(last_fixed_switch):
                # don't update fixed_neighbor
                if neighbor in fixed_switches:
                    continue

                # update cost if it's less than current
                link_to_neighbor = self.__find_link_by_switches(last_fixed_switch.name, neighbor.name)
                if costs[last_fixed_switch] + link_to_neighbor.cost() < costs[neighbor]:
                    costs[neighbor] = costs[last_fixed_switch] + link_to_neighbor.cost()
                    link_to_switch[neighbor] = link_to_neighbor

            cost_of_not_fixed_switches = dict(filter(lambda x: x[0] not in fixed_switches, costs.items()))
            next_fixed_switch = min(cost_of_not_fixed_switches.items(), key=lambda x: x[1])[0]
            fixed_switches.append(next_fixed_switch)

        path = Path()
        switch = self.__dst
        while switch != self.__src:
            if link_to_switch.get(switch) is None:
                return

            path.push(link_to_switch[switch])
            switch = self.__find_opposite_switch(link_to_switch[switch], switch)

        return path

    # TODO: implement
    def __calc_takahira(self, nth_update: int, update_interval_sec: int) \
            -> list[list[HostClient, HostServer, Path]]:
        """
        Calculate the path from src to dst by takahira method taking into account effect by disaster and amount of
        backup data.

        :return:
        Path:efficient path from src to dst with consideration for disaster and data size
        """
        if nth_update < 0:
            raise ValueError(f"nth_update must be greater than 0, got {nth_update}")
        if update_interval_sec < 1:
            raise ValueError(f"update_interval_sec must be greater than 0, got {update_interval_sec}")

        elapsed_sec = nth_update * update_interval_sec
        next_elapsed_sec = elapsed_sec + update_interval_sec

        # dict[switch1_name, dict[switch2_name, bw]]
        expected_bw_gbps: dict[str, dict[str, float]] = {s.name: {} for s in self.__switches}
        # dict[switch1_name, dict[switch2_name, Link]]
        switch_to_link: dict[str, dict[str, Link]] = {s.name: {} for s in self.__switches}
        # calculate expected bandwidths between each connected switches.
        for l in self.__links:
            if l.fail_at_sec == -1 or next_elapsed_sec <= l.fail_at_sec:
                ope_ratio = 1
            elif elapsed_sec <= l.fail_at_sec < next_elapsed_sec:
                ope_ratio = (l.fail_at_sec - elapsed_sec) / update_interval_sec
            else:
                ope_ratio = 0

            expected_bw = ope_ratio * l.bandwidth_mbps
            expected_bw_gbps[l.switch1][l.switch2] = expected_bw
            expected_bw_gbps[l.switch2][l.switch1] = expected_bw
            switch_to_link[l.switch1][l.switch2] = l
            switch_to_link[l.switch2][l.switch1] = l

        # calculate requested bw of each host pair
        requested_bandwidths: list[list[HostClient, HostServer, float]] = []
        for [client, server] in self.__host_pairs:
            # TODO: consider whether client and server have already failed
            requested_bandwidths.append([client, server, client.datasize_gb / client.fail_at_sec])

        # sort order by bw desc
        requested_bandwidths.sort(key=lambda x: x[2], reverse=True)

        # assign path to each host pair greedily
        result: list[list[HostClient, HostServer, Path]] = []
        for [client, server, req_bw] in requested_bandwidths:
            # bandwidths all between each two switches. dict[switch1_name, dict[switch2_name, bw]]
            bandwidths: dict[str, dict[str, float]] = {s.name: {} for s in self.__switches}

            # path between each switch pair that has maximum bottleneck bw
            paths: dict[str, dict[str, Path]] = {s.name: {} for s in self.__switches}

            for s1 in self.__switches:
                for s2 in self.__switches:
                    bw = self.BANDWIDTH_INF if s1 == s2 else -self.BANDWIDTH_INF
                    bandwidths[s1.name][s2.name] = bw
                    bandwidths[s2.name][s1.name] = bw
                    paths[s1.name][s2.name] = Path()

            for s1, v in expected_bw_gbps.items():
                for s2, exp_bw in v.items():
                    bandwidths[s1][s2] = exp_bw
                    bandwidths[s2][s1] = exp_bw

            for s1, v in switch_to_link.items():
                for s2, link in v.items():
                    paths[s1][s2] = Path([DirectedLink.from_link(link, s1, s2)])
                    paths[s2][s1] = Path([DirectedLink.from_link(link, s2, s1)])

            # calc maximum bottleneck bw and its path of each switch pair by Algorithm like Floyd-Warshall
            for s1 in self.__switches:
                for s2 in self.__switches:
                    for s3 in self.__switches:
                        bw_direct = bandwidths[s1.name][s3.name]
                        bw_via_s2 = min(bandwidths[s1.name][s2.name], bandwidths[s2.name][s3.name])
                        if bw_direct < bw_via_s2:
                            bandwidths[s1.name][s3.name] = bw_via_s2
                            bandwidths[s3.name][s1.name] = bw_via_s2
                            paths[s1.name][s3.name] = Path.merge(paths[s1.name][s2.name], paths[s2.name][s3.name])
                            paths[s3.name][s1.name] = Path.merge(paths[s3.name][s2.name], paths[s2.name][s1.name])

            path = paths[client.neighbor_switch][server.neighbor_switch]
            result.append([client, server, path])

            # subtract assigned bw from each link on path
            bottleneck = path.bottleneck_bw_gbps()
            for l in path.links:
                expected_bw_gbps[l.switch1][l.switch2] = expected_bw_gbps[l.switch1][l.switch2] - bottleneck
                expected_bw_gbps[l.switch2][l.switch1] = expected_bw_gbps[l.switch2][l.switch1] - bottleneck

        return result

    def __neighbors(self, switch: Switch) -> list[Switch]:
        links = filter(lambda x: switch.name in [x.switch1, x.switch2], self.__links)
        neighbors = map(lambda x: self.__find_opposite_switch(x, switch), links)
        return list(filter(lambda x: x is not None, neighbors))

    def __find_switch(self, name: str) -> Optional[Switch]:
        result = list(filter(lambda x: x.name == name, self.__switches))
        if len(result) == 0:
            return

        return result[0]

    # return link between the two switches
    def __find_link_by_switches(self, switch1: str, switch2: str) -> Optional[Link]:
        switches = [switch1, switch2]
        result = list(filter(lambda x: x.switch1 in switches and x.switch2 in switches, self.__links))
        if len(result) == 0:
            return

        return result[0]

    # return links connected to the switch
    def __find_links_by_switch(self, switch: Switch) -> list[Link]:
        return list(filter(lambda x: x.switch1 == switch.name or x.switch2 == switch.name, self.__links))

    def __find_opposite_switch(self, link: Link, switch: Switch) -> Optional[Switch]:
        if switch.name != link.switch1:
            return self.__find_switch(link.switch1)
        else:
            return self.__find_switch(link.switch2)

    def reset(self):
        self.__host_pairs = []
        self.__switches = []
        self.__links = []
