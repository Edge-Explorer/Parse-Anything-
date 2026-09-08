from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import numpy as np
import pdfplumber
import pypdfium2 as pdfium
from rapidocr_onnxruntime import RapidOCR

from universal_parser.core.router import register
from universal_parser.core.schema import BBox, Element
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor
from universal_parser.extractors.pdf.tables import PDFTableExtractor


@register
class NativePDFExtractor(BaseExtractor):
    """Extractor for PDF files (both native text and scanned pages).

    Handles:
        - Multi-column reading order via column-band clustering
        - Dynamic header hierarchy using font-size percentiles
        - Bordered & borderless table extraction integrated into the reading flow
        - Automatic OCR fallback (via RapidOCR ONNX) for scanned pages with no text
    """

    supported_types: ClassVar[list[FileType]] = [FileType.PDF]

    def __init__(self) -> None:
        super().__init__()
        self._ocr = RapidOCR()

    def stream(self, path: str | Path) -> Iterator[Element]:
        """Stream elements from a PDF page by page."""
        path_str = str(path)

        try:
            plumber_doc = pdfplumber.open(path_str)
            pdfium_doc = pdfium.PdfDocument(path_str)
        except Exception:  # noqa: BLE001
            return

        try:
            # Collect font sizes for header hierarchy
            font_sizes = self._collect_font_sizes(plumber_doc, max_pages=10)
            thresholds = self._compute_header_thresholds(font_sizes)

            for page_num in range(len(plumber_doc.pages)):
                plumber_page = plumber_doc.pages[page_num]
                page_width = float(plumber_page.width)

                # A. Extract tables and their bounding boxes using pdfplumber
                try:
                    table_extractor = PDFTableExtractor(plumber_page)
                    page_tables = table_extractor.extract_tables()
                except Exception:  # noqa: BLE001
                    page_tables = []

                table_bboxes = [table["bbox"] for table in page_tables]

                # B. Extract native text words/spans
                words = plumber_page.extract_words(extra_attrs=["size"], keep_blank_chars=False)
                spans = []

                # Group adjacent words on same line into phrase spans
                current_line: list[dict] = []
                for word in words:
                    bbox = (
                        float(word["x0"]),
                        float(word["top"]),
                        float(word["x1"]),
                        float(word["bottom"]),
                    )
                    if self._is_inside_any_bbox(bbox, table_bboxes):
                        continue

                    if not current_line:
                        current_line.append(word)
                    else:
                        prev = current_line[-1]
                        # Check if on same line (vertical overlap) and close horizontal gap
                        same_line = abs(float(word["top"]) - float(prev["top"])) < 4.0
                        gap = float(word["x0"]) - float(prev["x1"])
                        if same_line and gap < 12.0:
                            current_line.append(word)
                        else:
                            span_text = " ".join(w["text"] for w in current_line).strip()
                            if span_text:
                                spans.append(
                                    {
                                        "is_table": False,
                                        "text": span_text,
                                        "size": round(float(current_line[0].get("size", 10.0)), 1),
                                        "bbox": (
                                            float(current_line[0]["x0"]),
                                            float(min(w["top"] for w in current_line)),
                                            float(current_line[-1]["x1"]),
                                            float(max(w["bottom"] for w in current_line)),
                                        ),
                                    }
                                )
                            current_line = [word]

                if current_line:
                    span_text = " ".join(w["text"] for w in current_line).strip()
                    if span_text:
                        spans.append(
                            {
                                "is_table": False,
                                "text": span_text,
                                "size": round(float(current_line[0].get("size", 10.0)), 1),
                                "bbox": (
                                    float(current_line[0]["x0"]),
                                    float(min(w["top"] for w in current_line)),
                                    float(current_line[-1]["x1"]),
                                    float(max(w["bottom"] for w in current_line)),
                                ),
                            }
                        )

                # C. Wrap extracted tables
                for table in page_tables:
                    spans.append(
                        {
                            "is_table": True,
                            "table_data": table["data"],
                            "confidence": table["confidence"],
                            "bbox": table["bbox"],
                        }
                    )

                # D. SCANNED PAGE FALLBACK: If page has NO native text or tables, run OCR
                if not spans:
                    if page_num < len(pdfium_doc):
                        yield from self._ocr_scanned_page(
                            pdfium_doc[page_num],
                            page_num + 1,
                            page_width,
                            float(plumber_page.height),
                        )
                    continue

                # Step 3: Sort in natural reading order
                ordered_elements = self._sort_reading_order(spans, page_width)

                # Step 4: Yield sorted elements
                for el in ordered_elements:
                    bbox_coords = el["bbox"]

                    if el["is_table"]:
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
                                y1=bbox_coords[3],
                            ),
                            data=el["table_data"],
                            markdown_repr=markdown_repr,
                            confidence=el["confidence"],
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
                                y1=bbox_coords[3],
                            ),
                        )
        finally:
            pdfium_doc.close()
            plumber_doc.close()

    def _ocr_scanned_page(
        self, page: pdfium.PdfPage, page_num: int, page_w: float, page_h: float
    ) -> Iterator[Element]:
        """Render a scanned PDF page to an image and run RapidOCR."""
        try:
            scale = 200.0 / 72.0
            bitmap = page.render(scale=scale)
            pil_img = bitmap.to_pil().convert("RGB")
            img_np = np.array(pil_img)
            bitmap.close()

            ocr_results, _ = self._ocr(img_np)
            if not ocr_results:
                return

            scale_x = page_w / pil_img.width
            scale_y = page_h / pil_img.height

            for item in ocr_results:
                dt_boxes, text, score = item
                clean_text = text.strip()
                if not clean_text:
                    continue

                pts = np.array(dt_boxes, dtype=np.float32)
                x0 = float(np.min(pts[:, 0])) * scale_x
                y0 = float(np.min(pts[:, 1])) * scale_y
                x1 = float(np.max(pts[:, 0])) * scale_x
                y1 = float(np.max(pts[:, 1])) * scale_y

                yield Element(
                    type="paragraph",
                    text=clean_text,
                    page=page_num,
                    bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
                    markdown_repr=clean_text,
                    confidence=round(float(score), 3),
                )
        except Exception:  # noqa: BLE001
            return

    def _is_inside_any_bbox(
        self,
        span_bbox: tuple[float, float, float, float],
        table_bboxes: list[tuple[float, float, float, float]],
    ) -> bool:
        """Check if a text span falls inside any table bounding box."""
        sx0, sy0, sx1, sy1 = span_bbox
        for tx0, ty0, tx1, ty1 in table_bboxes:
            if sx0 >= (tx0 - 2) and sy0 >= (ty0 - 2) and sx1 <= (tx1 + 2) and sy1 <= (ty1 + 2):
                return True
        return False

    def _collect_font_sizes(self, doc: pdfplumber.PDF, max_pages: int) -> list[float]:
        """Collect all font sizes from the start of the document."""
        sizes = []
        pages_to_scan = min(len(doc.pages), max_pages)
        for i in range(pages_to_scan):
            page = doc.pages[i]
            words = page.extract_words(extra_attrs=["size"])
            for w in words:
                sizes.append(float(w.get("size", 10.0)))
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
        """Sort elements to preserve natural multi-column reading order."""
        if len(elements) < 5:
            return sorted(elements, key=lambda e: (e["bbox"][1], e["bbox"][0]))

        midpoint = page_width / 2.0

        left_col = []
        right_col = []
        full_width = []

        for el in elements:
            x0, _, x1, _ = el["bbox"]
            if x1 <= (midpoint + 15):
                left_col.append(el)
            elif x0 >= (midpoint - 15):
                right_col.append(el)
            else:
                full_width.append(el)

        def key_y(e):
            return (e["bbox"][1], e["bbox"][0])

        left_sorted = sorted(left_col, key=key_y)
        right_sorted = sorted(right_col, key=key_y)

        if len(left_sorted) >= 2 and len(right_sorted) >= 2:
            col_top = min(left_sorted[0]["bbox"][1], right_sorted[0]["bbox"][1])
            col_bottom = max(left_sorted[-1]["bbox"][3], right_sorted[-1]["bbox"][3])

            top_full = [e for e in full_width if e["bbox"][3] <= col_top + 10]
            bottom_full = [e for e in full_width if e["bbox"][1] >= col_bottom - 10]
            mid_full = [e for e in full_width if e not in top_full and e not in bottom_full]

            return (
                sorted(top_full, key=key_y)
                + sorted(mid_full, key=key_y)
                + left_sorted
                + right_sorted
                + sorted(bottom_full, key=key_y)
            )

        return sorted(elements, key=key_y)
