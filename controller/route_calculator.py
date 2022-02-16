from __future__ import annotations

from typing import Optional

from components import Node, Link, Path
from enums import RoutingAlgorithm


class RouteCalculator(object):
    # approximate infinite cost
    COST_INF = 10 ** 10

    def __init__(self, routing_algorithm: RoutingAlgorithm = RoutingAlgorithm.DIJKSTRA,
                 nodes: list[Node] = None, links: list[Link] = None, src: Node = None, dst: Node = None,
                 datasize_gb: int = None):
        self.__routing_algorithm = routing_algorithm

        if nodes is None:
            self.__nodes = []
        else:
            self.__nodes = nodes

        if links is None:
            self.__links = []
        else:
            self.__links = links

        self.__src = src
        self.__dst = dst
        self.__datasize_gb = datasize_gb

    @property
    def nodes(self) -> list[Node]:
        return self.__nodes

    def add_node(self, node: Node):
        self.__nodes.append(node)

    def rm_node(self, node: str):
        node = self.__find_node(node)
        if node is None:
            return

        self.__nodes.remove(node)
        links = self.__find_links_by_node(node)
        for l in links:
            self.rm_link(l.node1, l.node2)

    @property
    def links(self) -> list[Link]:
        return self.__links

    def add_link(self, link: Link):
        self.__links.append(link)

    def rm_link(self, node1: str, node2: str):
        link = self.__find_link_by_nodes(node1, node2)
        if link is None:
            return
        self.__links.remove(link)

    @property
    def src(self) -> Node:
        return self.__src

    @property
    def dst(self) -> Node:
        return self.__dst

    def set_src(self, node: Node):
        self.__src = node

    def set_dst(self, node: Node):
        self.__dst = node

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
        link_to_node: dict[Node, Link] = {}
        fixed_nodes = [self.__src]
        costs = {self.__src: 0}
        for n in self.__nodes:
            if n != self.__src:
                costs[n] = self.COST_INF

        # update neighbors of last fixed node
        while self.__dst not in fixed_nodes:
            last_fixed_node = fixed_nodes[-1]
            for neighbor in self.__neighbors(last_fixed_node):
                # don't update fixed_neighbor
                if neighbor in fixed_nodes:
                    continue

                # update cost if it's less than current
                link_to_neighbor = self.__find_link_by_nodes(last_fixed_node.name, neighbor.name)
                if costs[last_fixed_node] + link_to_neighbor.cost() < costs[neighbor]:
                    costs[neighbor] = costs[last_fixed_node] + link_to_neighbor.cost()
                    link_to_node[neighbor] = link_to_neighbor

            cost_of_not_fixed_nodes = dict(filter(lambda x: x[0] not in fixed_nodes, costs.items()))
            next_fixed_node = min(cost_of_not_fixed_nodes.items(), key=lambda x: x[1])[0]
            fixed_nodes.append(next_fixed_node)

        path = Path()
        node = self.__dst
        while node != self.__src:
            if link_to_node.get(node) is None:
                return

            path.push(link_to_node[node])
            node = self.__find_opposite_node(link_to_node[node], node)

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

    def __neighbors(self, node: Node) -> list[Node]:
        links = filter(lambda x: node.name in [x.node1, x.node2], self.__links)
        neighbors = map(lambda x: self.__find_opposite_node(x, node), links)
        return list(filter(lambda x: x is not None, neighbors))

    def __find_node(self, name: str) -> Optional[Node]:
        result = list(filter(lambda x: x.name == name, self.__nodes))
        if len(result) == 0:
            return

        return result[0]

    # return link between the two nodes
    def __find_link_by_nodes(self, node1: str, node2: str) -> Optional[Link]:
        node_names = [node1, node2]
        result = list(filter(lambda x: x.node1 in node_names and x.node2 in node_names, self.__links))
        if len(result) == 0:
            return

        return result[0]

    # return links connected to the node
    def __find_links_by_node(self, node: Node) -> list[Link]:
        return list(filter(lambda x: x.node1 == node.name or x.node2 == node.name, self.__links))

    def __find_opposite_node(self, link: Link, node: Node) -> Optional[Node]:
        if node.name != link.node1:
            return self.__find_node(link.node1)
        else:
            return self.__find_node(link.node2)
