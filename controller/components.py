from __future__ import annotations


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
    def __init__(self, node1: str, node2: str, cost: int = -1, fail_at_sec: int = -1):
        """
        :param node1: name of first node
        :param node2: name of second node
        :param cost: must be greater or equal to 0.  -1 means that cost has not been determined yet.
        :param fail_at_sec: must be greater or equal to 0. -1 means that fail_at_sec has not been determined yet.
        """
        self.node1 = node1
        self.node2 = node2
        self.cost = cost
        self.fail_at_sec = fail_at_sec

    def __repr__(self):
        cls = type(self)
        return f"{self.node1}---{self.node2} <{cls.__module__}.{cls.__name__} object at {hex(id(self))}>"

    def __hash__(self):
        return hash(f"{self.node1}-{self.node2}")

    def __eq__(self, other: Link):
        return (self.node1 == other.node1 and self.node2 == other.node2) or \
               (self.node1 == other.node2 and self.node2 == other.node1)

    def __ne__(self, other: Link):
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
