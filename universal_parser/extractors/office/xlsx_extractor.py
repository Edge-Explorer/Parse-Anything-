from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

from openpyxl import load_workbook

from universal_parser.core.router import register
from universal_parser.core.schema import Element, TableData
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor


@register
class XlsxExtractor(BaseExtractor):
    """
    Extractor for .xlsx files using openpyxl.
    Handles:
        - Memory-safe streaming using read_only=True
        - Multiple sheets (each sheet is extracted as a Table element)
        - Converts formula cells to values automatically using data_only=True
    """

    supported_types: ClassVar[list[FileType]] = [FileType.XLSX]

    def stream(self, path: str | Path) -> Iterator[Element]:
        """Stream sheets from an Excel workbook as Table elements."""
        path_str = str(path)

        try:
            # read_only=True streams cells instead of loading the whole document.
            # data_only=True evaluates Excel formulas and returns values.
            wb = load_workbook(path_str, read_only=True, data_only=True)

        except Exception:  # noqa: BLE001
            # Corrupted or password-protected file
            return

        try:
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]

                # Extract rows from sheet
                rows = []
                for row in sheet.iter_rows(values_only=True):
                    # Clean the row data (convert None values to empty strings)
                    clean_row = [
                        str(cell).strip() if cell is not None else "" for cell in row
                    ]

                    # Skip completely empty rows
                    if any(clean_row):
                        rows.append(clean_row)

                if not rows:
                    continue

                # The first row will act as the column headers
                headers = rows[0]
                data_rows = rows[1:]

                # Build a markdown representation of the spreadsheet
                md_header = "| " + " | ".join(headers) + " |"
                md_separator = "| " + " | ".join(["---"] * len(headers)) + " |"
                md_rows = ["| " + " | ".join(r) + " |" for r in data_rows]
                markdown_repr = f"### Sheet: {sheet_name}\n\n" + "\n".join(
                    [md_header, md_separator] + md_rows
                )

                yield Element(
                    type="table",
                    text=f"Sheet: {sheet_name}",
                    data=TableData(headers=headers, rows=data_rows),
                    markdown_repr=markdown_repr,
                )

        except Exception:  # noqa: BLE001
            return
        finally:
            wb.close()
