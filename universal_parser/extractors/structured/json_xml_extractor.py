from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

from universal_parser.core.router import register
from universal_parser.core.schema import Element, TableData
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor


@register
class JSONXMLExtractor(BaseExtractor):
    """
    Extractor for JSON (.json) and XML (.xml) files.

    Handles:
        - List of objects in JSON -> Table element (if tabular schema)
        - Nested JSON objects -> formatted code block element
        - XML -> element nodes parsed into headings, paragraphs, and code blocks
    """

    supported_types: ClassVar[list[FileType]] = [FileType.JSON, FileType.XML]

    def stream(self, path: str | Path) -> Iterator[Element]:
        path_obj = Path(path)
        ext = path_obj.suffix.lower()

        if ext == ".json":
            yield from self._stream_json(path_obj)
        elif ext == ".xml":
            yield from self._stream_xml(path_obj)

    def _stream_json(self, path: Path) -> Iterator[Element]:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                data = json.load(f)

            # Check if it's a list of uniform dictionaries (tabular JSON)
            if isinstance(data, list) and data and all(isinstance(row, dict) for row in data):
                headers = list(data[0].keys())
                rows = [
                    [str(row.get(h, "")).strip() for h in headers]
                    for row in data
                ]

                md_header = "| " + " | ".join(headers) + " |"
                md_separator = "| " + " | ".join(["---"] * len(headers)) + " |"
                md_rows = ["| " + " | ".join(r) + " |" for r in rows]
                markdown_repr = "\n".join([md_header, md_separator] + md_rows)

                yield Element(
                    type="table",
                    text=path.name,
                    data=TableData(headers=headers, rows=rows),
                    markdown_repr=markdown_repr,
                    confidence=1.0,
                )
            else:
                # General JSON: render formatted code block
                formatted_json = json.dumps(data, indent=2)
                yield Element(
                    type="code_block",
                    text=formatted_json,
                    markdown_repr=f"```json\n{formatted_json}\n```",
                    confidence=1.0,
                )
        except Exception:  # noqa: BLE001
            return

    def _stream_xml(self, path: Path) -> Iterator[Element]:
        try:
            tree = ET.parse(path)
            root = tree.getroot()

            # Yield root tag as level 1 heading
            yield Element(
                type="heading",
                level=1,
                text=root.tag,
                markdown_repr=f"# {root.tag}",
                confidence=1.0,
            )

            for child in root:
                text_val = (child.text or "").strip()
                if text_val:
                    yield Element(
                        type="paragraph",
                        text=f"{child.tag}: {text_val}",
                        markdown_repr=f"**{child.tag}**: {text_val}",
                        confidence=1.0,
                    )
                else:
                    child_str = ET.tostring(child, encoding="unicode").strip()
                    if child_str:
                        yield Element(
                            type="code_block",
                            text=child_str,
                            markdown_repr=f"```xml\n{child_str}\n```",
                            confidence=1.0,
                        )
        except Exception:  # noqa: BLE001
            return
