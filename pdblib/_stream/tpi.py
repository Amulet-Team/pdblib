from dataclasses import dataclass
import logging

from pdblib._struct import Struct
from .base import BaseStream

log = logging.getLogger(__name__)

TpiStreamHeader = Struct("<IIIIHHIIiIiIiI")


@dataclass
class TPIIPIStream(BaseStream):
    @classmethod
    def from_bytes(cls, buffer: bytes):
        self = cls(buffer)
        Version = Struct("<I").unpack_from(buffer)[0]
        if Version != 20040203:  # V80
            raise NotImplementedError("Only V80 is supported.")
        (
            HeaderSize,
            TypeIndexBegin,
            TypeIndexEnd,
            TypeRecordBytes,
            HashStreamIndex,
            HashAuxStreamIndex,
            HashKeySize,
            NumHashBuckets,
            HashValueBufferOffset,
            HashValueBufferLength,
            IndexOffsetBufferOffset,
            IndexOffsetBufferLength,
            HashAdjBufferOffset,
            HashAdjBufferLength,
        ) = TpiStreamHeader.unpack_from(buffer, 4)
        if TypeRecordBytes:
            log.info("TPI/IPI only support header. No extra data found in test examples")

        return self
