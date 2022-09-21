from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, List, Dict
from math import ceil
from dataclasses import dataclass, field
from io import BytesIO
import logging

from .struct import Struct
from .stream import BaseStream, DBIStream, PDBInfoStream, ModuleStream, TPIIPIStream, UnknownStream
from .stream.module import CodeView

log = logging.getLogger(__name__)


@dataclass
class SuperBlock:
    BlockSize: int
    FreeBlockMapBlock: int
    NumBlocks: int
    NumDirectoryBytes: int
    Unknown: int
    BlockMapAddr: int


@dataclass
class AbstractBasePDB(ABC):
    @classmethod
    def from_path(cls, path: str):
        with open(path, "rb") as pdb:
            return cls.from_file(pdb)

    @classmethod
    @abstractmethod
    def from_file(cls, pdb: BinaryIO):
        raise NotImplementedError


PDB7Header = b"Microsoft C/C++ MSF 7.00\r\n\x1ADS\0\0\0"


@dataclass
class PDB7(AbstractBasePDB):
    header: Optional[SuperBlock] = None
    unused_blocks: Dict[int, bytes] = field(default_factory=list)
    unused_streams: Dict[int, BaseStream] = field(default_factory=list)
    zero_stream: Optional[UnknownStream] = None
    info_stream: Optional[PDBInfoStream] = None
    tpi_stream: Optional[TPIIPIStream] = None
    dbi_steam: Optional[DBIStream] = None
    ipi_stream: Optional[TPIIPIStream] = None
    modules: List[ModuleStream] = field(default_factory=list)
    SymRecordStream: List[CodeView] = field(default_factory=list)

    @classmethod
    def from_path(cls, path: str):
        with open(path, "rb") as pdb:
            return cls.from_file(pdb)

    @classmethod
    def from_file(cls, pdb: BinaryIO):
        self = cls()

        # https://llvm.org/docs/PDB/MsfFile.html#the-superblock
        if pdb.read(32) != PDB7Header:
            raise ValueError("Header is incorrect")
        self.header = SuperBlock(*Struct("<IIIIII").read(pdb))

        self.unused_blocks = unused_blocks = {}
        block_index = 0
        pdb.seek(0)
        while block := pdb.read(self.header.BlockSize):
            unused_blocks[block_index] = block
            block_index += 1

        if any(unused_blocks.pop(0)[32 + 6 * 4:]):
            log.info("Extra data in the superblock")

        # https://llvm.org/docs/PDB/MsfFile.html#the-free-block-map  # TODO

        # https://llvm.org/docs/PDB/MsfFile.html#the-stream-directory
        root_stream_table = BytesIO(unused_blocks.pop(self.header.BlockMapAddr))
        block_index_count = ceil(self.header.NumDirectoryBytes / self.header.BlockSize)
        if block_index_count > self.header.BlockSize / 4:
            raise NotImplementedError
        block_indexes = Struct(f"<{block_index_count}I").read(root_stream_table)

        root_stream_bytes = b"".join(map(unused_blocks.pop, block_indexes))
        if any(root_stream_bytes[self.header.NumDirectoryBytes:]):
            log.info("Extra data after root stream")
        root_stream = BytesIO(root_stream_bytes[:self.header.NumDirectoryBytes])
        stream_count = Struct("<I").read(root_stream)[0]
        stream_sizes = Struct(f"<{stream_count}I").read(root_stream)
        stream_block_indexes = []

        for stream_size in stream_sizes:
            stream_index_count = ceil(stream_size / self.header.BlockSize)
            stream_block_indexes.append(
                Struct(f"<{stream_index_count}I").read(root_stream)
            )

        if root_stream.read():
            raise ValueError("root stream has incorrect size")

        self.unused_streams = streams = {}
        for stream_index, (stream_size, stream_blocks) in enumerate(zip(stream_sizes, stream_block_indexes)):
            stream = b"".join(map(unused_blocks.pop, stream_blocks))
            if any(stream[stream_size:]):
                log.info(f"Extra data after stream {stream_index}")
            streams[stream_index] = stream[:stream_size]

        self.zero_stream = UnknownStream.from_bytes(streams.pop(0))  # TODO
        self.info_stream = PDBInfoStream.from_bytes(streams.pop(1))
        self.tpi_stream = TPIIPIStream.from_bytes(streams.pop(2))
        self.dbi_steam = DBIStream.from_bytes(streams.pop(3))
        self.ipi_stream = TPIIPIStream.from_bytes(streams.pop(4))

        for module_info in self.dbi_steam.modules:
            if module_info.ModuleSymStream == -1:
                continue
            stream = streams.pop(module_info.ModuleSymStream)
            self.modules.append(ModuleStream.from_bytes(stream, module_info))

        self.SymRecordStream = CodeView.from_file_all(BytesIO(self.unused_streams.pop(self.dbi_steam.header.SymRecordStream)))

        return self


def parse(path: str) -> PDB7:
    return PDB7.from_path(path)
