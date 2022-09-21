from struct import Struct as Struct_
from typing import BinaryIO
from io import BytesIO


class Struct(Struct_):
    def read(self, f: BinaryIO):
        return self.unpack(f.read(self.size))


def read_str(f: BytesIO):
    """Read a null terminated string."""
    s = f.getvalue()[f.tell():].split(b"\x00", 1)[0]
    f.seek(len(s)+1, 1)
    return s
