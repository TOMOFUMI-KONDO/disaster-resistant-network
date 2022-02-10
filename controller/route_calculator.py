from __future__ import annotations

from typing import Optional


class RouteCalculator(object):
    INF = 10 ** 10

    def __init__(self, nodes: list[Node] = None, links: list[Link] = None, src: Node = None, dst: Node = None):
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

    def get_nodes(self) -> list[Node]:
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

    def get_links(self) -> list[Link]:
        return self.__links

    def add_link(self, link: Link):
        self.__links.append(link)

    def rm_link(self, node1: str, node2: str):
        link = self.__find_link_by_nodes(node1, node2)
        if link is None:
            return

        self.__links.remove(link)

    def get_src(self) -> Node:
        return self.__src

    def get_dst(self) -> Node:
        return self.__dst

    def set_src(self, node: Node):
        self.__src = node

    def set_dst(self, node: Node):
        self.__dst = node

    def calc_shortest_path(self) -> Optional[Path]:
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
                costs[n] = self.INF

        # update neighbors of last fixed node
        while self.__dst not in fixed_nodes:
            last_fixed_node = fixed_nodes[-1]
            for neighbor in self.__neighbors(last_fixed_node):
                # don't update fixed_neighbor
                if neighbor in fixed_nodes:
                    continue

                # update cost if it's less than current
                link_to_neighbor = self.__find_link_by_nodes(last_fixed_node.name, neighbor.name)
                if costs[last_fixed_node] + link_to_neighbor.cost < costs[neighbor]:
                    costs[neighbor] = costs[last_fixed_node] + link_to_neighbor.cost
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


class Node(object):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        cls = type(self)
        return f"{self.name} <{cls.__module__}.{cls.__name__} object at {hex(id(self))}>"

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other: Node):
        return self.name == other.name

    def __ne__(self, other: Node):
        return not self == other


class Link(object):
    def __init__(self, node1: str, node2: str, cost: int):
        self.node1 = node1
        self.node2 = node2
        self.cost = cost

    def __repr__(self):
        cls = type(self)
        return f"{self.node1}---{self.node2} <{cls.__module__}.{cls.__name__} object at {hex(id(self))}>"

    def __eq__(self, other):
        return (self.node1 == other.node1 and self.node2 == other.node2) or \
               (self.node1 == other.node2 and self.node2 == other.node1)

    def __ne__(self, other):
        return not self == other


class Path(object):
    def __init__(self, links: list[Link] = None):
        if links is None:
            self.links = []
        else:
            self.links = links

    def __repr__(self):
        cls = type(self)
        return " ".join([l.__repr__() for l in self.links]) + \
               f"<{cls.__module__}.{cls.__name__} object at {hex(id(self))}>"

    def append(self, link: Link):
        self.links.append(link)

    def push(self, link: Link):
        self.links.insert(0, link)
