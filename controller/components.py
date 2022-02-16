from __future__ import annotations


class Switch(object):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        cls = type(self)
        return f"{self.name} <{cls.__module__}.{cls.__name__} object at {hex(id(self))}>"

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other: Switch):
        return self.name == other.name

    def __ne__(self, other: Switch):
        return not self == other


class Link(object):
    def __init__(self, switch1: str, switch2: str, bandwidth: int = -1, fail_at_sec: int = -1):
        """
        :param switch1: name of switch on one side
        :param switch2: name of switch on the other side
        :param bandwidth: must be greater than 0.
        :param fail_at_sec: must be greater or equal to 0. -1 means that fail_at_sec has not been determined yet.
        """
        self.switch1 = switch1
        self.switch2 = switch2
        self.bandwidth = bandwidth
        self.fail_at_sec = fail_at_sec

    # faster bps, lower cost
    def cost(self):
        return 10000 // self.bandwidth

    def __repr__(self):
        cls = type(self)
        return f"{self.switch1}---{self.switch2} <{cls.__module__}.{cls.__name__} object at {hex(id(self))}>"

    def __hash__(self):
        return hash(f"{self.switch1}-{self.switch2}")

    def __eq__(self, other: Link):
        return (self.switch1 == other.switch1 and self.switch2 == other.switch2) or \
               (self.switch1 == other.switch2 and self.switch2 == other.switch1)

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
