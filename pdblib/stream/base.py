from typing import Optional
from dataclasses import dataclass


@dataclass
class BaseStream:
    stream: Optional[bytes] = None
