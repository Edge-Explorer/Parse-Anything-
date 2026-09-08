from __future__ import annotations

import pdfplumber

from universal_parser.core.schema import TableData


class PDFTableExtractor:
    """
    Handles bordered (Lattice) and borderless (Stream) table extraction from PDF pages.

    Provides:
        - Bordered table extraction via coordinate grid mapping
        - Borderless table extraction via whitespace column clustering
        - Confidence scoring based on layout density and cell consistency
    """

    def __init__(self, page: pdfplumber.page.Page):
        self.page = page

    def extract_tables(self) -> list[dict]:
        """
        Extract all tables from the page.

        Returns:
            list[dict]: A list of tables found, each formatted as:
                {
                    "data": TableData,
                    "bbox": tuple(x0, y0, x1, y1),
                    "confidence": float (0.0 to 1.0)
                }
        """

        tables = []

        # 1. Try Lattice extraction first (bordered tables)
        lattice_tables = self._extract_lattice()
        if lattice_tables:
            tables.extend(lattice_tables)

        # 2. Try Stream extraction (borderless tables)
        # We only run stream extraction if we don't find lattice tables
        # to prevent duplicate extractions on the same area.
        if not lattice_tables:
            stream_tables = self._extract_stream()
            if stream_tables:
                tables.extend(stream_tables)

        return tables

    def _extract_lattice(self) -> list[dict]:
        """Extract tables using vertical and horizontal vector lines."""
        extracted = []
        # pdfplumber vertical and horizontal line settings
        table_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3,
        }

        plumber_tables = self.page.find_tables(table_settings=table_settings)
        for table in plumber_tables:
            raw_data = table.extract()
            if not raw_data or len(raw_data) < 2:
                continue

            clean_rows = []
            for row in raw_data:
                # Convert None to empty string
                clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                clean_rows.append(clean_row)

            headers = clean_rows[0]
            data_rows = clean_rows[1:]

            # Lattice table confidence is high (0.95+) since lines physically define cells
            confidence = 0.98 if all(len(row) == len(headers) for row in data_rows) else 0.90

            extracted.append(
                {
                    "data": TableData(headers=headers, rows=data_rows),
                    "bbox": table.bbox,  # (x0, y0, x1, y1)
                    "confidence": confidence,
                }
            )

        return extracted

    def _extract_stream(self) -> list[dict]:
        """Extract borderless tables using whitespace distance clustering and text alignment."""
        extracted = []
        table_settings = {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "snap_tolerance": 4,
            "join_tolerance": 4,
            "min_words_vertical": 3,
            "min_words_horizontal": 2,
        }

        try:
            plumber_tables = self.page.find_tables(table_settings=table_settings)
            for table in plumber_tables:
                raw_data = table.extract()
                if not raw_data or len(raw_data) < 2:
                    continue

                clean_rows = []
                total_words = 0
                non_empty_cells = 0

                for row in raw_data:
                    clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                    if any(clean_row):
                        clean_rows.append(clean_row)
                        for cell in clean_row:
                            if cell:
                                word_count = len(cell.split())
                                total_words += word_count
                                non_empty_cells += 1

                if len(clean_rows) < 2 or non_empty_cells < 4:
                    continue

                # Heuristic: Genuine tables contain concise cell values (labels, numbers, codes <= 2.5 words/cell).
                # If cells contain full paragraph sentences, it is multi-column text, not a table.
                avg_words_per_cell = total_words / max(1, non_empty_cells)
                if avg_words_per_cell > 2.5:
                    continue

                # Filter out tables that swallow more than 40% of page height (multi-column text pages)
                page_h = float(self.page.height)
                table_h = float(table.bbox[3] - table.bbox[1])
                if table_h > (0.40 * page_h):
                    continue

                max_cols = max(len(r) for r in clean_rows)
                if max_cols < 2:
                    continue

                headers = clean_rows[0]
                data_rows = clean_rows[1:]

                extracted.append(
                    {
                        "data": TableData(headers=headers, rows=data_rows),
                        "bbox": table.bbox,  # (x0, y0, x1, y1)
                        "confidence": 0.85,
                    }
                )
        except Exception:  # noqa: BLE001
            return []

        return extracted
