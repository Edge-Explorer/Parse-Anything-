from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import olefile
import xlrd

from universal_parser.core.router import register
from universal_parser.core.schema import Element, TableData
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor


@register
class LegacyOfficeExtractor(BaseExtractor):
    """
    Extractor for legacy Microsoft Office binary formats (.doc, .xls, .ppt).
    Handles:
        - .xls: Streams sheets into structured TableData & Markdown using xlrd
        - .doc / .ppt: Decodes text streams from OLE2 binary containers via olefile
    """

    supported_types: ClassVar[list[FileType]] = [
        FileType.DOC,
        FileType.XLS,
        FileType.PPT,
    ]

    def stream(self, path: str | Path) -> Iterator[Element]:
        path_obj = Path(path)
        ext = path_obj.suffix.lower()

        if ext == ".xls":
            yield from self._stream_xls(path_obj)
        elif ext in (".doc", ".ppt"):
            yield from self._stream_ole_text(path_obj)

    def _stream_xls(self, path: Path) -> Iterator[Element]:
        """Stream sheets from legacy .xls files using xlrd."""
        try:
            wb = xlrd.open_workbook(str(path))
            for sheet in wb.sheets():
                rows = []
                for row_idx in range(sheet.nrows):
                    rows_vals = [
                        str(sheet.cell_value(row_idx, col_idx)).strip()
                        for col_idx in range(sheet.ncols)
                    ]
                    if any(rows_vals):
                        rows.append(rows_vals)

                if not rows:
                    continue

                headers = rows[0]
                data_rows = rows[1:]

                md_header = "| " + " | ".join(headers) + " |"
                md_separator = "| " + " | ".join(["---"] * len(headers)) + " |"
                md_rows = ["| " + " | ".join(r) + " |" for r in data_rows]
                markdown_repr = f"### Sheet: {sheet.name}\n\n" + "\n".join(
                    [md_header, md_separator] + md_rows
                )

                yield Element(
                    type="table",
                    text=f"Sheet: {sheet.name}",
                    data=TableData(headers=headers, rows=data_rows),
                    markdown_repr=markdown_repr,
                    confidence=1.0,
                )

        except Exception:  # noqa: BLE001
            return

    def _stream_ole_text(self, path: Path) -> Iterator[Element]:
        """Extract readable text streams from OLE2 compound files (.doc / .ppt)."""
        try:
            if not olefile.isOleFile(str(path)):
                return

            ole = olefile.OleFileIO(str(path))
            extracted_text = []

            for stream_name in ole.listdir():
                try:
                    stream_data = ole.openstream(stream_name).read()
                    # Filter ASCII string sequences from binary stream
                    raw_strings = re.findall(rb"[\x20-\x7E]{4,}", stream_data)
                    for s in raw_strings:
                        decoded = s.decode("ascii", errors="ignore").strip()
                        if len(decoded) > 3 and not decoded.startswith("Microsoft"):
                            extracted_text.append(decoded)

                except Exception:  # noqa: BLE001, S112
                    continue

            ole.close()

            for text_chunk in extracted_text:
                yield Element(
                    type="Paragraph",
                    text=text_chunk,
                    markdown_repr=text_chunk,
                    confidence=0.8,
                )

        except Exception:  # noqa: BLE001
            return
