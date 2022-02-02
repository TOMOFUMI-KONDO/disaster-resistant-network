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
        link_to_node: dict[Node, Link] = {}
        fixed_nodes = [self.src]
        costs = {self.src: 0}
        for n in self.nodes:
            if n != self.src:
                costs[n] = self.INF

        # update neighbors of last fixed node
        while self.dst not in fixed_nodes:
            last_fixed_node = fixed_nodes[-1]
            for neighbor in self.__neighbors(last_fixed_node):
                # don't update fixed_neighbor
                if neighbor in fixed_nodes:
                    continue

                # update cost if it's less than current
                link_to_neighbor = self.__find_link_by_nodes(last_fixed_node, neighbor)
                if costs[last_fixed_node] + link_to_neighbor.cost < costs[neighbor]:
                    costs[neighbor] = costs[last_fixed_node] + link_to_neighbor.cost
                    link_to_node[neighbor] = link_to_neighbor

            cost_of_not_fixed_nodes = dict(filter(lambda x: x[0] not in fixed_nodes, costs.items()))
            next_fixed_node = min(cost_of_not_fixed_nodes.items(), key=lambda x: x[1])
            fixed_nodes.append(next_fixed_node)

        path = Path()
        node = self.dst
        while node != self.src:
            path.append(link_to_node[node])

            # find opposite node
            if node != link_to_node[node].node1:
                node = self.__find_node(link_to_node[node].node1)
            else:
                node = self.__find_node(link_to_node[node].node2)

        return path

    def __neighbors(self, node: Node) -> list[Node]:
        links = filter(lambda x: node in [x.node1, x.node2], self.links)
        node_names = map(lambda x: x.name, links)
        return list(filter(lambda x: x.name in node_names, self.nodes))

    def __find_node(self, name: str) -> Node:
        return list(filter(lambda x: x.name == name, self.nodes))[0]

    def __find_link_by_nodes(self, node1: Node, node2: Node) -> Link:
        node_names = [node1.name, node2.name]
        return list(filter(lambda x: x.node1 in node_names and x.node2 in node_names, self.links))[0]


class Node(object):
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other: Node):
        return self.name == other.name

    def __ne__(self, other: Node):
        return not self.__eq__(other)


class Link(object):
    def __init__(self, name: str, node1: str, node2: str, cost: int):
        self.name = name
        self.node1 = node1
        self.node2 = node2
        self.cost = cost


class Path(object):
    def __init__(self, links: list[Link] = None):
        if links is None:
            self.links = []
        else:
            self.links = links

    def append(self, link: Link):
        self.links.append(link)
