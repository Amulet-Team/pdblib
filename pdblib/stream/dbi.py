from io import BytesIO
from math import ceil
from typing import Optional, List, Tuple
from dataclasses import dataclass, field

from ..struct import Struct, read_str
from .base import BaseStream


DBIHeaderStruct = Struct("<iIIHHHHHHiiiiiIiiHHI")
DBIModuleInfoStruct = Struct("<Ih2xiiIh2xIIHhIIIH2xIII")
SectionContribEntryStruct = Struct("<H2xiiIH2xII")
SectionMapHeaderStruct = Struct("<HH")
SectionMapEntryStruct = Struct("<HHHHHHII")
FileInfoHeaderStruct = Struct("<HH")


@dataclass
class DBIHeader:
    VersionSignature: int
    VersionHeader: int
    Age: int
    GlobalStreamIndex: int
    BuildNumber: int
    PublicStreamIndex: int
    PdbDllVersion: int
    SymRecordStream: int
    PdbDllRbld: int
    ModInfoSize: int
    SectionContributionSize: int
    SectionMapSize: int
    SourceInfoSize: int
    TypeServerMapSize: int
    MFCTypeServerIndex: int
    OptionalDbgHeaderSize: int
    ECSubstreamSize: int
    Flags: int
    Machine: int
    Padding: int


@dataclass
class DBIModuleInfo:
    Unused1: int
    Section: int
    Offset: int
    Size: int
    Characteristics: int
    ModuleIndex: int
    DataCrc: int
    RelocCrc: int
    Flags: int
    ModuleSymStream: int
    SymByteSize: int
    C11ByteSize: int
    C13ByteSize: int
    SourceFileCount: int
    Unused2: int
    SourceFileNameIndex: int
    PdbFilePathNameIndex: int
    ModuleName: bytes
    ObjFileName: bytes


@dataclass
class SectionContribEntry:
    Section: int
    Offset: int
    Size: int
    Characteristics: int
    ModuleIndex: int
    DataCrc: int
    RelocCrc: int


@dataclass
class SectionMapHeader:
    Count: int
    LogCount: int


@dataclass
class SectionMapEntry:
    Flags: int
    Ovl: int
    Group: int
    Frame: int
    SectionName: int
    ClassName: int
    Offset: int
    SectionLength: int


@dataclass
class FileInfo:
    NumModules: int
    NumSourceFiles: int
    ModIndices: Tuple[int]
    ModFileCounts: Tuple[int]
    FileNameOffsets: Tuple[int]
    NamesBuffer: Tuple[bytes]


@dataclass
class DBIStream(BaseStream):
    header: Optional[DBIHeader] = None
    modules: List[DBIModuleInfo] = field(default_factory=list)
    section_contributions: List[SectionContribEntry] = field(default_factory=list)
    section_map_header: Optional[SectionMapHeader] = None
    section_maps: List[SectionMapEntry] = field(default_factory=list)
    file_info: Optional[FileInfo] = None

    @classmethod
    def from_bytes(cls, buffer: bytes):
        self = cls(buffer)
        dbi = BytesIO(buffer)
        self.header = DBIHeader(*DBIHeaderStruct.read(dbi))
        if self.header.VersionSignature != -1:
            raise NotImplementedError
        if self.header.VersionHeader != 19990903:
            raise NotImplementedError

        # https://llvm.org/docs/PDB/DbiStream.html#module-info-substream
        dbi_section = BytesIO(dbi.read(self.header.ModInfoSize))
        while dbi_section.tell() < self.header.ModInfoSize:
            self.modules.append(
                DBIModuleInfo(
                    *DBIModuleInfoStruct.read(dbi_section),
                    read_str(dbi_section),
                    read_str(dbi_section),
                )
            )
            dbi_section.seek(ceil(dbi_section.tell() / 4) * 4)  # Not sure if this should be before or after

        # https://llvm.org/docs/PDB/DbiStream.html#section-contribution-substream
        dbi_section = BytesIO(dbi.read(self.header.SectionContributionSize))
        if Struct("<I").read(dbi_section)[0] != 4046371373:
            raise NotImplementedError
        while dbi_section.tell() < self.header.SectionContributionSize:
            self.section_contributions.append(
                SectionContribEntry(
                    *SectionContribEntryStruct.read(dbi_section)
                )
            )

        # https://llvm.org/docs/PDB/DbiStream.html#section-map-substream
        dbi_section = BytesIO(dbi.read(self.header.SectionMapSize))
        self.section_map_header = SectionMapHeader(*SectionMapHeaderStruct.read(dbi_section))
        while dbi_section.tell() < self.header.SectionMapSize:
            self.section_maps.append(
                SectionMapEntry(
                    *SectionMapEntryStruct.read(dbi_section)
                )
            )

        # https://llvm.org/docs/PDB/DbiStream.html#file-info-substream
        dbi_section = BytesIO(dbi.read(self.header.SourceInfoSize))
        NumModules, NumSourceFiles = FileInfoHeaderStruct.read(dbi_section)
        self.file_info = FileInfo(
            NumModules,
            NumSourceFiles,
            Struct(f"<{NumModules}H").read(dbi_section),
            Struct(f"<{NumModules}H").read(dbi_section),
            Struct(f"<{NumSourceFiles}I").read(dbi_section),
            tuple(read_str(dbi_section) for _ in range(NumSourceFiles))
        )
        if dbi_section.read():
            raise RuntimeError

        # https://llvm.org/docs/PDB/DbiStream.html#dbi-type-server-map-substream
        # https://llvm.org/docs/PDB/DbiStream.html#dbi-optional-dbg-stream
        # https://llvm.org/docs/PDB/DbiStream.html#dbi-ec-substream

        return self
