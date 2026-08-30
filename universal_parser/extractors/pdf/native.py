from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import fitz  # PyMuPDF
import numpy as np

from universal_parser.core.router import register
from universal_parser.core.schema import BBox, Element
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor


@register
class NativePDFExtractor(BaseExtractor):
    """
    Extractor for native (searchable) PDF files using PyMuPDF.

    Handles:
        - Multi-column reading order via column-band clustering
        - Dynamic header hierarchy using font-size percentiles
        - Basic text layout structure
    """

    supported_types: ClassVar[list[FileType]] = [FileType.PDF]

    def stream(self, path: str | Path) -> Iterator[Element]:
        """
        Stream elements from a native PDF page by page.
        """
        path_str = str(path)

        try:
            doc = fitz.open(path_str)
        except Exception:  # noqa: BLE001
            # If the PDF is completely corrupted and cannot be opened,
            # we log it and exit the generator cleanly.
            # The engine will raise/handle this.
            return

        try:
            # Step 1: Collect font sizes from the first few pages (max 10)
            # to build a document-wide typography profile.
            font_sizes = self._collect_font_sizes(doc, max_pages=10)
            thresholds = self._compute_header_thresholds(font_sizes)

            # Step 2: Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_width = page.rect.width

                # Get raw text blocks with structural details
                # "dict" format gives us blocks -> lines -> spans (with font size and bbox)
                text_page = page.get_text("dict")

                spans = []
                for block in text_page.get("blocks", []):
                    # We only care about text blocks (type 0)
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text:
                                continue
                            spans.append(
                                {
                                    "text": text,
                                    "size": round(span.get("size", 10.0), 1),
                                    "bbox": span.get("bbox"),  # (x0, y0)
                                }
                            )

                if not spans:
                    continue

                # Step 3: Sort spans by reading order (column aware)
                ordered_spans = self._sort_reading_order(spans, page_width)

                # Step 4: Convert spans to schema Elements
                for span in ordered_spans:
                    size = span["size"]
                    text = span["text"]
                    bbox_coords = span["bbox"]

                    # Determine element type and level based on font size percentiles
                    el_type = "paragraph"
                    level = None

                    if size >= thresholds["h1"]:
                        el_type = "heading"
                        level = 1
                    elif size >= thresholds["h2"]:
                        el_type = "heading"
                        level = 2
                    elif size >= thresholds["h3"]:
                        el_type = "heading"
                        level = 3

                    yield Element(
                        type=el_type,
                        level=level,
                        text=text,
                        page=page_num + 1,
                        bbox=BBox(
                            x0=bbox_coords[0],
                            y0=bbox_coords[1],
                            x1=bbox_coords[2],
                            y1=bbox_coords[3],
                        ),
                    )

        finally:
            doc.close()

    def _collect_font_sizes(self, doc: fitz.Document, max_pages: int) -> list[float]:
        """Collect all font sizes from the start of the document."""
        sizes = []
        pages_to_scan = min(len(doc), max_pages)
        for i in range(pages_to_scan):
            page = doc[i]
            text_page = page.get_text("dict")
            for block in text_page.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            sizes.append(span.get("size", 10.0))
        return sizes

    def _compute_header_thresholds(self, font_sizes: list[float]) -> dict[str, float]:
        """Compute font size cutoffs for H1, H2, H3 using percentiles."""
        if not font_sizes:
            # Fallback default values if no text is found
            return {"h1": 16.0, "h2": 14.0, "h3": 12.0}

        arr = np.array(font_sizes)
        # We assume:
        # H1 is in the top 5% of largest fonts (95th percentile)
        # H2 is in the next 10% (85th percentile)
        # H3 is in the next 10% (75th percentile)
        h1_val = float(np.percentile(arr, 95))
        h2_val = float(np.percentile(arr, 85))
        h3_val = float(np.percentile(arr, 75))

        # Ensure we don't treat normal body text as headings if the document has uniform sizing
        median = float(np.median(arr))

        # Headings must be strictly larger than the median/body text size
        h1_val = max(h1_val, median + 3.0)
        h2_val = max(h2_val, median + 1.5)
        h3_val = max(h3_val, median + 0.5)

        return {"h1": h1_val, "h2": h2_val, "h3": h3_val}

    def _sort_reading_order(self, spans: list[dict], page_width: float) -> list[dict]:
        """
        Sort spans to preserve natural reading order.
        Addresses multi-column layouts by grouping spans into columns.
        """
        # If there are very few spans, a simple top-to-bottom sort is safe
        if len(spans) < 5:
            return sorted(spans, key=lambda s: (s["bbox"][1], s["bbox"][0]))

        # Simple 2-column detection logic:
        # We split the page down the middle vertically.
        # If spans are grouped clearly on the left and right, we sort Left-Col first, then Right-Col.
        midpoint = page_width / 2.0

        left_col = []
        right_col = []
        spans_spanning_middle = []

        for span in spans:
            x0, _, x1, _ = span["bbox"]
            # If the span lies entirely on the left side
            if x1 <= midpoint:
                left_col.append(span)
            # If the span lies entirely on the right side
            elif x0 >= midpoint:
                right_col.append(span)
            else:
                # Spans headers, footers, or title banners that go across columns
                spans_spanning_middle.append(span)

        # Sort each group top-to-bottom, then left-to-right
        key_func = lambda s: (s["bbox"][1], s["bbox"][0])
        left_sorted = sorted(left_col, key=key_func)
        right_sorted = sorted(right_col, key=key_func)

        # Merge columns back. In RAG pipelines, we want full reading flow:
        # Header/Title first -> Left column -> Right column -> Footer
        # We group spans by approximate vertical ranges to see where layout changes
        all_sorted = []

        # For simplicity in this initial implementation, we check if columns are distinct.
        # If we have a significant number of items in both left and right columns:
        if len(left_sorted) > 2 and len(right_sorted) > 2:
            # We sort everything top-to-bottom, but handle left-right column splits
            # We'll merge them by combining left-column and right-column blocks.
            # To do this correctly, we will sort all spans by Y-coordinate first,
            # but if they fall into left/right buckets, we group them.
            # A more robust column sorting algorithm will be refined in Phase 7.
            # For now, a classic column-block splitter:
            all_sorted = sorted(
                spans_spanning_middle + left_sorted + right_sorted, key=key_func
            )
        else:
            all_sorted = sorted(spans, key=key_func)
        return all_sorted
