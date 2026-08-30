from __future__ import annotations

from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor

# Central registry: FileType -> Extractor class
# Extractors are added here as they are built, phase by phase.
# engine.py reads this — it never imports an extractor directly.

FORMAT_REGISTRY: dict[FileType, type[BaseExtractor]] = {}


def register(extractor_cls: type[BaseExtractor]) -> type[BaseExtractor]:
    """
    Decorator to register an extractor class into FORMAT_REGISTRY.
    Usage — put this on any extractor class:
        @register
        class PDFExtractor(BaseExtractor):
            supported_types = [FileType.PDF]
            ...
    This automatically maps FileType.PDF -> PDFExtractor in the registry.
    No manual entry needed in this file when adding a new format.
    """
    for file_type in extractor_cls.supported_types:
        FORMAT_REGISTRY[file_type] = extractor_cls
    return extractor_cls


def get_extractor(file_type: FileType) -> BaseExtractor | None:
    """
    Look up and return an instantiated extractor for the given FileType.
    Returns None if no extractor is registered for this type.
    engine.py handles the None case — it never crashes here.
    """
    extractor_cls = FORMAT_REGISTRY.get(file_type)
    if extractor_cls is None:
        return None
    return extractor_cls()
