from __future__ import annotations

from typing import Optional

from components import Switch, Link, Path
from enums import RoutingAlgorithm


class RouteCalculator(object):
    # approximate infinite cost
    COST_INF = 10 ** 10

    def __init__(self, routing_algorithm: RoutingAlgorithm = RoutingAlgorithm.DIJKSTRA,
                 switches: list[Switch] = None, links: list[Link] = None, src: Switch = None, dst: Switch = None,
                 datasize_gb: int = None):
        self.__routing_algorithm = routing_algorithm

        if switches is None:
            self.__switches = []
        else:
            self.__switches = switches

        if links is None:
            self.__links = []
        else:
            self.__links = links

        self.__src = src
        self.__dst = dst
        self.__datasize_gb = datasize_gb

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

    @property
    def src(self) -> Switch:
        return self.__src

    @property
    def dst(self) -> Switch:
        return self.__dst

    def set_src(self, switch: Switch):
        self.__src = switch

    def set_dst(self, switch: Switch):
        self.__dst = switch

    def calc_shortest_path(self, nth_update: int = 0, update_interval_sec: int = 0) -> Optional[Path]:
        if self.__routing_algorithm == RoutingAlgorithm.DIJKSTRA:
            return self.__calc_dijkstra()

        if self.__routing_algorithm == RoutingAlgorithm.TAKAHIRA:
            return self.__calc_takahira(nth_update, update_interval_sec)

        raise ValueError(f"Routing algorithm is invalid: {self.__routing_algorithm}")

    def __calc_dijkstra(self) -> Optional[Path]:
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
    def __calc_takahira(self, nth_update: int, update_interval_sec: int) -> Optional[Path]:
        """
        Calculate the path from src to dst by takahira method taking into account effect by disaster and amount of
        backup data.

        :return:
        Path:shortest path from src to dst
        """
        if nth_update < 1:
            raise ValueError(f"nth_update must be greater than 0, got {nth_update}")
        if update_interval_sec < 1:
            raise ValueError(f"update_interval_sec must be greater than 0, got {update_interval_sec}")

        elapsed_sec = nth_update * update_interval_sec
        next_elapsed_sec = elapsed_sec + update_interval_sec

        # calculate disaster effect
        expected_bandwidth: dict[Link, float] = {}
        for l in self.__links:
            if l.fail_at_sec == -1 or next_elapsed_sec <= l.fail_at_sec:
                ope_ratio = 1
            elif elapsed_sec <= l.fail_at_sec < next_elapsed_sec:
                ope_ratio = (l.fail_at_sec - elapsed_sec) / update_interval_sec
            else:
                ope_ratio = 0

            expected_bandwidth[l] = ope_ratio * l.bandwidth

        #  calculate data size of each host

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
