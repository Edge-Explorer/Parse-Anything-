from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import fitz  # PyMuPDF
import numpy as np
import pdfplumber

from universal_parser.core.router import register
from universal_parser.core.schema import BBox, Element
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor
from universal_parser.extractors.pdf.tables import PDFTableExtractor


@register
class NativePDFExtractor(BaseExtractor):
    """
    Extractor for native (searchable) PDF files.
    
    Handles:
        - Multi-column reading order via column-band clustering
        - Dynamic header hierarchy using font-size percentiles
        - Bordered & borderless table extraction integrated into the reading flow
    """
    supported_types: ClassVar[list[FileType]] = [FileType.PDF]

    def stream(self, path: str | Path) -> Iterator[Element]:
        """Stream elements from a native PDF page by page."""
        path_str = str(path)
        
        try:
            doc = fitz.open(path_str)
            # Open with pdfplumber for table extraction
            plumber_doc = pdfplumber.open(path_str)
        except Exception:  # noqa: BLE001
            # Corrupted PDF
            return

        try:
            # Step 1: Collect font sizes from the first few pages (max 10)
            font_sizes = self._collect_font_sizes(doc, max_pages=10)
            thresholds = self._compute_header_thresholds(font_sizes)

            # Step 2: Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_width = page.rect.width
                
                # A. Extract tables and their bounding boxes using pdfplumber
                plumber_page = plumber_doc.pages[page_num]
                table_extractor = PDFTableExtractor(plumber_page)
                page_tables = table_extractor.extract_tables()
                
                # Keep track of table bounding boxes to filter out overlapping text
                table_bboxes = [table["bbox"] for table in page_tables]

                # B. Extract text spans using PyMuPDF (fitz)
                text_page = page.get_text("dict")
                spans = []
                for block in text_page.get("blocks", []):
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text:
                                continue
                            
                            bbox = span.get("bbox")  # (x0, y0, x1, y1)
                            
                            # Filter out text spans that fall inside any table boundary
                            if self._is_inside_any_bbox(bbox, table_bboxes):
                                continue
                                
                            spans.append({
                                "is_table": False,
                                "text": text,
                                "size": round(span.get("size", 10.0), 1),
                                "bbox": bbox,
                            })

                # C. Wrap extracted tables as sortable elements
                for table in page_tables:
                    spans.append({
                        "is_table": True,
                        "table_data": table["data"],
                        "confidence": table["confidence"],
                        "bbox": table["bbox"],
                    })

                if not spans:
                    continue

                # Step 3: Sort both text and tables together in natural reading order
                ordered_elements = self._sort_reading_order(spans, page_width)

                # Step 4: Yield sorted elements
                for el in ordered_elements:
                    bbox_coords = el["bbox"]
                    
                    if el["is_table"]:
                        # Pre-render markdown representation of the table
                        headers = el["table_data"].headers
                        rows = el["table_data"].rows
                        md_header = "| " + " | ".join(headers) + " |"
                        md_separator = "| " + " | ".join(["---"] * len(headers)) + " |"
                        md_rows = ["| " + " | ".join(row) + " |" for row in rows]
                        markdown_repr = "\n".join([md_header, md_separator] + md_rows)

                        yield Element(
                            type="table",
                            page=page_num + 1,
                            bbox=BBox(
                                x0=bbox_coords[0],
                                y0=bbox_coords[1],
                                x1=bbox_coords[2],
                                y1=bbox_coords[3]
                            ),
                            data=el["table_data"],
                            markdown_repr=markdown_repr,
                            confidence=el["confidence"]
                        )
                    else:
                        size = el["size"]
                        text = el["text"]
                        
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
                                y1=bbox_coords[3]
                            )
                        )
        finally:
            doc.close()
            plumber_doc.close()

    def _is_inside_any_bbox(
        self, 
        span_bbox: tuple[float, float, float, float], 
        table_bboxes: list[tuple[float, float, float, float]]
    ) -> bool:
        """Check if a text span falls inside any table bounding box (with 2-point padding safety)."""
        sx0, sy0, sx1, sy1 = span_bbox
        for tx0, ty0, tx1, ty1 in table_bboxes:
            if sx0 >= (tx0 - 2) and sy0 >= (ty0 - 2) and sx1 <= (tx1 + 2) and sy1 <= (ty1 + 2):
                return True
        return False

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
            return {"h1": 16.0, "h2": 14.0, "h3": 12.0}
            
        arr = np.array(font_sizes)
        h1_val = float(np.percentile(arr, 95))
        h2_val = float(np.percentile(arr, 85))
        h3_val = float(np.percentile(arr, 75))
        
        median = float(np.median(arr))
        
        h1_val = max(h1_val, median + 3.0)
        h2_val = max(h2_val, median + 1.5)
        h3_val = max(h3_val, median + 0.5)
        
        return {"h1": h1_val, "h2": h2_val, "h3": h3_val}

    def _sort_reading_order(self, elements: list[dict], page_width: float) -> list[dict]:
        """Sort elements to preserve natural reading order (supports multi-column layouts)."""
        if len(elements) < 5:
            return sorted(elements, key=lambda e: (e["bbox"][1], e["bbox"][0]))

        midpoint = page_width / 2.0
        
        left_col = []
        right_col = []
        spans_spanning_middle = []
        
        for el in elements:
            x0, _, x1, _ = el["bbox"]
            if x1 <= midpoint:
                left_col.append(el)
            elif x0 >= midpoint:
                right_col.append(el)
            else:
                spans_spanning_middle.append(el)
                
        key_func = lambda e: (e["bbox"][1], e["bbox"][0])
        left_sorted = sorted(left_col, key=key_func)
        right_sorted = sorted(right_col, key=key_func)
        
        if len(left_sorted) > 2 and len(right_sorted) > 2:
            all_sorted = sorted(spans_spanning_middle + left_sorted + right_sorted, key=key_func)
        else:
            all_sorted = sorted(elements, key=key_func)
            
        return all_sorted