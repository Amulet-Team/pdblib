from io import BytesIO
from dataclasses import dataclass

from ..struct import Struct
from .base import BaseStream


@dataclass
class PDBInfoStream(BaseStream):
    @classmethod
    def from_bytes(cls, buffer: bytes):
        self = cls(buffer)
        # https://llvm.org/docs/PDB/PdbStream.html
        f = BytesIO(buffer)
        version, timestamp, age, guid_lower, guid_upper, str_size = Struct("<IIIQQI").read(f)
        guid = guid_lower + (guid_upper << 64)
        if version != 20000404:
            raise NotImplementedError("Only VC70 is supported.")
        str_data = f.read(str_size)
        str_count = Struct("<I").read(f)
        # TODO: hash table
        # TODO: more here

        return self
