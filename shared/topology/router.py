from __future__ import annotations


class Router(object):
    INF = 10 ** 10

    def __init__(self, nodes: list[Node], links: list[Link], src: Node, dst: Node):
        self.nodes = nodes
        self.links = links
        self.src = src
        self.dst = dst

    # TODO: test this method
    # calculate the shortest path from src to dst by dijkstra
    def calc(self) -> Path:
        spt: list[Link] = []
        edges: dict[Node, Link] = {}
        fixed_nodes = [self.src]
        costs = {self.src: 0}
        for n in self.nodes:
            if n != self.src:
                costs[n] = self.INF

        # update neighbors of last fixed node
        while self.dst not in spt:
            last = fixed_nodes[-1]
            for neighbor in self.neighbors(last):
                if neighbor in fixed_nodes:
                    continue

                for l in self.links:
                    edge_names = [l.v1.name, l.v2.name]
                    if neighbor.name in edge_names and last.name in edge_names:
                        link = l
                        break

                if costs[last] + link.cost < costs[neighbor]:
                    costs[neighbor] = costs[last] + link.cost
                    edges[neighbor] = link

            not_fixed_edges = dict(filter(lambda x: x[0] not in fixed_nodes, edges.items()))
            next_fixed_edge = min(not_fixed_edges.items(), key=lambda x: x[1].cost)[0]
            fixed_nodes.append(next_fixed_edge[0])
            spt.append(next_fixed_edge)

    def neighbors(self, node: Node) -> list[Node]:
        links = filter(lambda x: node in [x.v1, x.v2], self.links)
        node_names = map(lambda x: x.name, links)
        return list(filter(lambda x: x.name in node_names, self.nodes))


class Node(object):
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other: Node):
        return self.name == other.name

    def __ne__(self, other: Node):
        return not self.__eq__(other)


class Link(object):
    def __init__(self, name: str, v1: Node, v2: Node, cost: int):
        self.name = name
        self.v1 = v1
        self.v2 = v2
        self.cost = cost


class Path(object):
    def __init__(self, nodes: list[Node]):
        self.nodes = nodes

