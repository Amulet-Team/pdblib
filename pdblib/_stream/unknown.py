from dataclasses import dataclass

from .base import BaseStream


@dataclass
class UnknownStream(BaseStream):
    @classmethod
    def from_bytes(cls, buffer: bytes):
        self = cls(buffer)
        return self
