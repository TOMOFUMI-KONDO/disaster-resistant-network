from enum import Enum


class Network(Enum):
    TCP = 1
    QUIC = 2

    @property
    def name_lower(self) -> str:
        return self.name.lower()
