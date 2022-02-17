from __future__ import annotations

from copy import deepcopy


class Host(object):
    def __init__(self, name: str, neighbor_switch: str):
        """
        :param name: name of host
        :param neighbor_switch: name of switch that is connected to this host
        """
        self.name = name
        self.neighbor_switch = neighbor_switch


class HostClient(Host):
    def __init__(self, name: str, neighbor_switch: str, fail_at_sec: int, datasize_gb: int):
        """
        :param fail_at_sec: this host will fail after this time has elapsed. must be greater than or equal to 0.
            -1 means that fail_at_sec is unknown
        :param datasize_gb: size(GB) of data that is backed up.
        """
        super(HostClient, self).__init__(name, neighbor_switch)
        self.fail_at_sec = fail_at_sec
        self.datasize_gb = datasize_gb

    def __repr__(self):
        cls = type(self)
        return f"{self.name} <{cls.__module__}.{cls.__name__} object at {hex(id(self))}>"

    def __hash__(self):
        return hash(self.name)


class HostServer(Host):
    def __init__(self, name: str, neighbor_switch: str):
        super(HostServer, self).__init__(name, neighbor_switch)


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
    def __init__(self, switch1: str, switch2: str, bandwidth_gbps: float = -1, fail_at_sec: int = -1):
        """
        :param switch1: name of switch on one side
        :param switch2: name of switch on the other side
        :param bandwidth_gbps: bandwidth(Gbps). this must be greater than 0.
        :param fail_at_sec: this link will fail after fail_at_sec elapsed. fail_at_sec must be greater or equal to 0.
            -1 means that fail_at_sec has not been determined yet.
        """
        self.switch1 = switch1
        self.switch2 = switch2
        self.bandwidth_gbps = bandwidth_gbps
        self.fail_at_sec = fail_at_sec

    # faster bps, lower cost
    def cost(self):
        return 10 // self.bandwidth_gbps

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


class DirectedLink(Link):
    @staticmethod
    def from_link(link: Link, from_: str, to: str):
        if link.switch1 == from_:
            assert link.switch2 == to
            return DirectedLink(False, link.switch1, link.switch2, link.bandwidth_gbps, link.fail_at_sec)
        else:
            assert link.switch1 == to and link.switch2 == from_
            return DirectedLink(False, link.switch2, link.switch1, link.bandwidth_gbps, link.fail_at_sec)

    def __init__(self, direction: bool, switch1: str, switch2: str, bandwidth_gbps: float = -1, fail_at_sec: int = -1):
        """
        :param direction: if False, direction is switch1 to switch2. otherwise, it is reverse.
        """
        super(DirectedLink, self).__init__(switch1, switch2, bandwidth_gbps, fail_at_sec)
        self.direction = direction

    def __repr__(self):
        cls = type(self)
        return f"{self.__link_repr} <{cls.__module__}.{cls.__name__} object at {hex(id(self))}>"

    def __hash__(self):
        return hash(self.__link_repr)

    def __eq__(self, other: DirectedLink):
        if self.direction == other.direction:
            return self.switch1 == other.switch1 and self.switch2 == other.switch2
        else:
            return self.switch1 == other.switch2 and self.switch2 == other.switch1

    def __ne__(self, other: DirectedLink):
        return not self == other

    @property
    def __link_repr(self) -> str:
        return f"{self.switch1}<--{self.switch2}" if self.direction else f"{self.switch1}-->{self.switch2}"


# TODO: make links private
class Path(object):
    @staticmethod
    def merge(path1: Path, path2: Path) -> Path:
        merged = deepcopy(path1)
        merged.extend(path2)
        return merged

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

    def rm(self, link: Link):
        self.links.remove(link)

    def extend(self, path: Path):
        self.links.extend(path.links)
