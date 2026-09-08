from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

from universal_parser.core.router import register
from universal_parser.core.schema import Element, TableData
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor


@register
class CSVExtractor(BaseExtractor):
    """
    Extractor for delimited text files (.csv, .tsv).
    Handles:
        - Auto-dialect detection (delimiter, quotechar) via csv.Sniffer
        - UTF-8, Latin-1, and Windows-1252 encodings
        - Streams rows into structured TableData
    """

    supported_types: ClassVar[list[FileType]] = [FileType.CSV, FileType.TSV]

    def stream(self, path: str | Path) -> Iterator[Element]:
        """Stream table element from a CSV/TSV file."""
        path_obj = Path(path)
        path_str = str(path)

        # Step 1: Detect encoding safely
        encoding = self._detect_encoding(path_str)

        try:
            with open(path_str, encoding=encoding, errors="replace") as f:
                sample = f.read(4096)
                f.seek(0)

                if not sample.strip():
                    return

                # Step 2: Auto-detect delimiter using Sniffer, fallback to extension
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                    delimiter = dialect.delimiter
                except Exception:  # noqa: BLE001
                    delimiter = "\t" if path_obj.suffix.lower() == ".tsv" else ","

                reader = csv.reader(f, delimiter=delimiter)
                rows = []
                for row in reader:
                    clean_row = [cell.strip() for cell in row]
                    if any(clean_row):
                        rows.append(clean_row)

                if not rows:
                    return

                headers = rows[0]
                data_rows = rows[1:]

                # Generate markdown representation
                md_header = "| " + " | ".join(headers) + " |"
                md_separator = "| " + " | ".join(["---"] * len(headers)) + " |"
                md_rows = ["| " + " | ".join(r) + " |" for r in data_rows]
                markdown_repr = "\n".join([md_header, md_separator] + md_rows)

                yield Element(
                    type="table",
                    text=path_obj.name,
                    data=TableData(headers=headers, rows=data_rows),
                    markdown_repr=markdown_repr,
                    confidence=1.0,
                )

        except Exception:  # noqa: BLE001
            return

    def _detect_encoding(self, path: str) -> str:
        """Try decoding a small chunk with UTF-8, fallback to latin-1."""
        try:
            with open(path, "rb") as f:
                f.read(2048).decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            return "latin-1"
