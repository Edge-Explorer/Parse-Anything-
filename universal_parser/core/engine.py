from __future__ import annotations

from pathlib import Path

from universal_parser.core.router import get_extractor
from universal_parser.core.schema import Document, DocumentMetadata
from universal_parser.core.sniffer import sniff


def parse(path: str | Path) -> Document:
    """
    Parse any supported document into a Document object.
    This is the only function external code needs to call.
    Internally it:
        1. Sniffs the file type via magic bytes
        2. Looks up the registered extractor for that type
        3. Streams Elements from the extractor into content_tree
        4. Returns a validated Document
    Args:
        path: path to the document to parse
    Returns:
        Document — fully validated Pydantic model
    Raises:
        FileNotFoundError: if the file does not exist
        ValueError: if the file type is unsupported (no extractor registered)
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Step 1 — What is this file?
    file_type = sniff(path)

    # Step 2 — Do we have an extractor for it?
    extractor = get_extractor(file_type)
    if extractor is None:
        raise ValueError(
            f"Unsupported file type: {file_type.name} ({path.suffix}). "
            f"No extractor registered for this format yet."
        )

    # Step 3 — Build the document shell
    doc = Document(
        metadata=DocumentMetadata(
            file_name=path.name,
            file_type=file_type.name.lower(),
        )
    )

    # Step 4 — Stream elements from the extractor into content_tree
    for element in extractor.stream(path):
        doc.content_tree.append(element)

    return doc
