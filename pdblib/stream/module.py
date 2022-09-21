from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Tuple, Optional, List
from io import BytesIO
import logging

from ..struct import Struct, read_str
from .base import BaseStream

if TYPE_CHECKING:
    from .dbi import DBIModuleInfo

log = logging.getLogger(__name__)
Lazy = True


# https://github.com/microsoft/microsoft-pdb/blob/master/include/cvinfo.h


@dataclass
class ModiStream:
    Signature: int
    Symbols: bytes
    C11LineInfo: bytes
    C13LineInfo: bytes
    GlobalRefsSize: int
    GlobalRefs: Tuple[int]


@dataclass
class CodeViewData:
    pass


@dataclass
class FarBASICString(CodeViewData):  # 0x0006
    pass


class UnknownRecord(CodeViewData):
    pass


PUBSYM32Struct = Struct("<IIH")  # + Name


@dataclass
class PUBSYM32(CodeViewData):
    pubsymflags: int
    off: int
    seg: int
    name: bytes       # Length-prefixed name


class PublicSymbol(PUBSYM32):  # 0x110E
    pass


PROCSYM32Struct = Struct("<IIIIIIIIHB")  # + Name


@dataclass
class PROCSYM32(CodeViewData):
    pParent: int    # pointer to the parent
    pEnd: int       # pointer to this blocks end
    pNext: int      # pointer to next symbol
    len: int        # Proc length
    DbgStart: int   # Debug start offset
    DbgEnd: int     # Debug end offset
    typind: int     # Type index or ID
    off: int
    seg: int
    flags: int      # Proc flags
    name: bytes    # Length-prefixed name


class LocalProcedure(PROCSYM32):  # 0x110F
    pass


REFSYM2Struct = Struct("<IIH")  # + Name

@dataclass
class REFSYM2(CodeViewData):
    sumName: int    # SUC of the name
    ibSym: int      # Offset of actual symbol in $$Symbols
    imod: int       # Module containing the actual symbol
    name: bytes     # hidden name made a first class member


class LocalProcedureReference(REFSYM2):  # 0x1127
    pass


def parse_record(record_kind: int, record: bytes) -> CodeViewData:
    record_stream = BytesIO(record)
    if record_kind == 0x0006:
        record_data = FarBASICString()
    elif record_kind == 0x110E:
        record_data = PublicSymbol(
            *PUBSYM32Struct.read(record_stream),
            read_str(record_stream),
        )
    elif record_kind == 0x110F:
        record_data = LocalProcedure(
            *PROCSYM32Struct.read(record_stream),
            read_str(record_stream)
        )
    elif record_kind == 0x1127:
        record_data = LocalProcedureReference(
            *REFSYM2Struct.read(record_stream),
            read_str(record_stream),
        )
    else:
        log.info(f"Unknown record type {record_kind:04X}")
        record_data = UnknownRecord()

    if not isinstance(record_data, UnknownRecord) and any(record_stream.read()):
        log.info("More data in record")
    return record_data


@dataclass
class CodeView:
    RecordKind: int = 0
    Record: bytes = b""
    _record_data: Optional[CodeViewData] = None

    @property
    def RecordData(self) -> CodeViewData:
        if self._record_data is None:
            self._record_data = parse_record(self.RecordKind, self.Record)
        return self._record_data

    @classmethod
    def from_file(cls, stream: BytesIO):
        self = cls()
        RecordLen, self.RecordKind = Struct("<HH").read(stream)
        self.Record = stream.read(RecordLen-2)
        if not Lazy:
            self.RecordData
        return self

    @classmethod
    def from_file_all(cls, stream: BytesIO):
        stream_len = len(stream.getvalue())
        items = []
        while stream.tell() < stream_len:
            items.append(cls.from_file(stream))
        return items


@dataclass
class ModuleStream(BaseStream):
    module_info: Optional[DBIModuleInfo] = None
    modi_stream: Optional[ModiStream] = None
    symbols: List[CodeView] = field(default_factory=list)

    @classmethod
    def from_bytes(cls, buffer: bytes, module_info: DBIModuleInfo):
        self = cls(buffer, module_info)
        stream = BytesIO(buffer)

        Signature = Struct("<I").read(stream)[0]
        if Signature != 4:
            raise NotImplementedError
        Symbols = stream.read(module_info.SymByteSize-4)
        C11LineInfo = stream.read(module_info.C11ByteSize)
        C13LineInfo = stream.read(module_info.C13ByteSize)
        GlobalRefsSize = Struct("<I").read(stream)[0]
        GlobalRefsCount = GlobalRefsSize // 4
        GlobalRefs = Struct(f"<{GlobalRefsCount}I").read(stream)

        self.modi_stream = ModiStream(
            Signature,
            Symbols,
            C11LineInfo,
            C13LineInfo,
            GlobalRefsSize,
            GlobalRefs,
        )

        if stream.read():
            log.info("more data in stream")

        self.symbols = CodeView.from_file_all(BytesIO(Symbols))

        return self
