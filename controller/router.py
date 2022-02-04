from __future__ import annotations


class Router(object):
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

    def add_node(self, node: Node):
        self.__nodes.append(node)

    def rm_node(self, node: Node):
        self.__nodes.remove(node)
        links = self.__find_links_by_node(node)
        for l in links:
            self.rm_link(l)

    def add_link(self, link: Link):
        self.__links.append(link)

    def rm_link(self, link: Link):
        self.__links.remove(link)

    def set_src(self, node: Node):
        self.__src = node

    def set_dst(self, node: Node):
        self.__dst = node

    # calculate the shortest path from src to dst by dijkstra
    def calc_shortest_path(self) -> Path:
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
                link_to_neighbor = self.__find_link_by_nodes(last_fixed_node, neighbor)
                if costs[last_fixed_node] + link_to_neighbor.cost < costs[neighbor]:
                    costs[neighbor] = costs[last_fixed_node] + link_to_neighbor.cost
                    link_to_node[neighbor] = link_to_neighbor

            cost_of_not_fixed_nodes = dict(filter(lambda x: x[0] not in fixed_nodes, costs.items()))
            next_fixed_node = min(cost_of_not_fixed_nodes.items(), key=lambda x: x[1])[0]
            fixed_nodes.append(next_fixed_node)

        path = Path()
        node = self.__dst
        while node != self.__src:
            path.push(link_to_node[node])
            node = self.__find_opposite_node(link_to_node[node], node)

        return path

    def __neighbors(self, node: Node) -> list[Node]:
        links = filter(lambda x: node.name in [x.node1, x.node2], self.__links)
        return list(map(lambda x: self.__find_opposite_node(x, node), links))

    def __find_node(self, name: int) -> Node:
        return list(filter(lambda x: x.name == name, self.__nodes))[0]

    # return link between the two nodes
    def __find_link_by_nodes(self, node1: Node, node2: Node) -> Link:
        node_names = [node1.name, node2.name]
        return list(filter(lambda x: x.node1 in node_names and x.node2 in node_names, self.__links))[0]

    # return links connected to the node
    def __find_links_by_node(self, node: Node) -> list[Link]:
        return list(filter(lambda x: x.node1 == node.name or x.node2 == node.name, self.__links))

    def __find_opposite_node(self, link: Link, node: Node) -> Node:
        if node.name != link.node1:
            return self.__find_node(link.node1)
        else:
            return self.__find_node(link.node2)


class Node(object):
    def __init__(self, name: int):
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
    def __init__(self, node1: int, node2: int, cost: int):
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

    def append(self, link: Link):
        self.links.append(link)

    def push(self, link: Link):
        self.links.insert(0, link)
