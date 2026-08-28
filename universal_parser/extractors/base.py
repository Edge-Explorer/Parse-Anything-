from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

from universal_parser.core.schema import Element
from universal_parser.core.sniffer import FileType

class BaseExtractor(ABC):
    """
    Abstract base class for all format extractors.
    Every extractor in universal_parser.extractors must:
        1. Inherit from BaseExtractor
        2. Declare which FileTypes it handles via supported_types
        3. Implement stream() — yield Elements one at a time, never return a list
    Adding a new format = one new file inheriting this + one entry in router.py.
    Nothing else in core/ needs to change.
    """
    supported_types: list[FileType]= []
    
    @abstractmethod
    def stream(self, path: str | Path) -> Iterator[Element]:
        """
        Parse the document at the given path and yield Element objects.
        Rules:
            - Must yield, never return a full list (streaming = memory safe)
            - Must never raise on a recoverable error — yield a low-confidence
              element or skip, log the issue, keep going
            - One Element at a time, in reading order
        Args:
            path: absolute or relative path to the source file
        Yields:
            Element objects in document reading order
        """
        ...
