from __future__ import annotations

from typing import Optional

from components import Switch, Link, Path, HostServer, HostClient
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
        self.__links.append(link)

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
        Path:shortest path from src to dst
        """
        if nth_update < 0:
            raise ValueError(f"nth_update must be greater than 0, got {nth_update}")
        if update_interval_sec < 1:
            raise ValueError(f"update_interval_sec must be greater than 0, got {update_interval_sec}")

        elapsed_sec = nth_update * update_interval_sec
        next_elapsed_sec = elapsed_sec + update_interval_sec

        # expected bandwidths between each two switches. dict[switch1_name, dict[switch2_name, bw]]
        expected_bw_gbps: dict[str, dict[str, float]] = {}
        # path of each switch pair that has maximum bottleneck bw
        paths: dict[str, dict[str, Path]] = {}
        for s1 in self.__switches:
            for s2 in self.__switches:
                expected_bw_gbps[s1.name][s2.name] = self.BANDWIDTH_INF if s1 == s2 else 0
                paths[s1.name][s2.name] = Path()

        # calculate disaster effect
        for l in self.__links:
            if l.fail_at_sec == -1 or next_elapsed_sec <= l.fail_at_sec:
                ope_ratio = 1
            elif elapsed_sec <= l.fail_at_sec < next_elapsed_sec:
                ope_ratio = (l.fail_at_sec - elapsed_sec) / update_interval_sec
            else:
                ope_ratio = 0

            expected_bw = ope_ratio * l.bandwidth_gbps
            expected_bw_gbps[l.switch1][l.switch2] = expected_bw
            expected_bw_gbps[l.switch2][l.switch1] = expected_bw
            paths[l.switch1][l.switch2] = Path([l])
            paths[l.switch2][l.switch1] = Path([l])

        #  calculate requested bw of each host pair
        requested_bandwidth_gbps: list[list[HostClient, HostServer, float]] = []
        for [client, server] in self.__host_pairs:
            # TODO: consider whether client and server have already failed
            requested_bandwidth_gbps.append([client, server, client.datasize_gb / client.fail_at_sec])

        # sort order by bw desc
        requested_bandwidth_gbps.sort(key=lambda x: x[2], reverse=True)

        result: list[list[HostClient, HostServer, Path]] = []
        # assign path to each host pair greedily
        for [client, server, bw] in requested_bandwidth_gbps:
            # calc maximum bottleneck bw and its path of each switch pair by Algorithm like Floyd-Warshall
            for s1 in self.__switches:
                for s2 in self.__switches:
                    for s3 in self.__switches:
                        bw_direct = expected_bw_gbps[s1.name][s2.name]
                        bw_via_s2 = min(expected_bw_gbps[s1.name][s2.name], expected_bw_gbps[s2.name][s3.name])
                        if bw_direct < bw_via_s2:
                            expected_bw_gbps[s1.name][s3.name] = bw_via_s2
                            expected_bw_gbps[s3.name][s1.name] = bw_via_s2
                            paths[s1.name][s3.name] = Path.merge(paths[s1.name][s2.name], paths[s2.name][s3.name])

            path = paths[client.neighbor_switch][server.neighbor_switch]
            result.append([client, server, path])

            # subtract assigned bw from each link on path
            for l in path.links:
                expected_bw_gbps[l.switch1][l.switch2] = max(expected_bw_gbps[l.switch1][l.switch2] - bw, 0)
                expected_bw_gbps[l.switch2][l.switch1] = max(expected_bw_gbps[l.switch2][l.switch1] - bw, 0)

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
