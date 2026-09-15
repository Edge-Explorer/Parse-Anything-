from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

from universal_parser.core.router import register
from universal_parser.core.schema import BBox, Element
from universal_parser.core.sniffer import FileType
from universal_parser.extractors.base import BaseExtractor
from universal_parser.extractors.images.deskew import estimate_and_deskew
from universal_parser.extractors.images.enhancement import (
    enhance_contrast_adaptive,
    is_low_contrast,
    merge_overlapping_line_tokens,
    normalize_ocr_token_text,
)
from universal_parser.extractors.tables.opencv_ensemble import OpenCVTableEnsemble


@register
class ImageScanExtractor(BaseExtractor):
    """
    Extractor for image and scanned files (.png, .jpg, .tiff, .bmp, .webp).
    Handles:
        - Image preprocessing (deskewing via Hough transform, contrast-gated CLAHE enhancement)
        - CPU-based text and bounding box detection via RapidOCR (ONNX)
        - Horizontal token overlap merging and intelligent word boundary normalization
        - Visual table line and lattice detection via OpenCVTableEnsemble
        - Confidence scoring per text and table element
    """

    supported_types: ClassVar[list[FileType]] = [FileType.IMAGE]

    def __init__(self) -> None:
        super().__init__()
        # Initialize RapidOCR engine (cached in memory)
        self._ocr = RapidOCR()
        self._table_ensemble = OpenCVTableEnsemble()

    def stream(self, path: str | Path) -> Iterator[Element]:
        path_str = str(path)

        # Step 1: Read image with OpenCV
        img = cv2.imread(path_str)
        if img is None:
            raise ValueError(f"Unreadable or corrupt image file: {path}")

        # Step 2: Preprocess / deskew / contrast gate
        preprocessing_img = self._preprocess_image(img)

        # Step 3: Run RapidOCR
        ocr_results, _ = self._ocr(preprocessing_img)
        if not ocr_results:
            return

        # Collect raw OCR tokens with single-token normalization for table cell extraction
        raw_tokens: list[tuple[tuple[float, float, float, float], str, float]] = []
        for item in ocr_results:
            dt_boxes, text, score = item
            clean_text = text.strip()
            if not clean_text:
                continue

            pts = np.array(dt_boxes, dtype=np.float32)
            x0 = float(np.min(pts[:, 0]))
            y0 = float(np.min(pts[:, 1]))
            x1 = float(np.max(pts[:, 0]))
            y1 = float(np.max(pts[:, 1]))
            norm_text = normalize_ocr_token_text(clean_text)
            raw_tokens.append(((x0, y0, x1, y1), norm_text, float(score)))

        # Step 4: Extract visual tables from image gridlines using cell-isolated tokens
        visual_tables = self._table_ensemble.extract_tables_from_image(
            preprocessing_img, raw_tokens
        )

        # Step 5: Stream detected tables
        for tbl in visual_tables:
            headers = tbl.data.headers
            data_rows = tbl.data.rows
            md_header = "| " + " | ".join(headers) + " |"
            md_separator = "| " + " | ".join(["---"] * len(headers)) + " |"
            if data_rows:
                md_rows = "\n".join("| " + " | ".join(row) + " |" for row in data_rows)
                table_md = f"{md_header}\n{md_separator}\n{md_rows}"
            else:
                table_md = f"{md_header}\n{md_separator}"

            yield Element(
                type="table",
                data=tbl.data,
                page=1,
                bbox=tbl.bbox,
                markdown_repr=table_md,
                confidence=tbl.confidence,
            )

        # Step 6: Separate OCR tokens that belong outside extracted tables
        outside_ocr_results: list[Any] = []
        for item in ocr_results:
            dt_boxes, text, score = item
            pts = np.array(dt_boxes, dtype=np.float32)
            center_x = float(np.mean(pts[:, 0]))
            center_y = float(np.mean(pts[:, 1]))

            inside_table = False
            for tbl in visual_tables:
                if (
                    tbl.bbox.x0 - 5 <= center_x <= tbl.bbox.x1 + 5
                    and tbl.bbox.y0 - 5 <= center_y <= tbl.bbox.y1 + 5
                ):
                    inside_table = True
                    break

            if not inside_table:
                outside_ocr_results.append(item)

        # Step 7: Merge overlapping horizontal line tokens for paragraphs outside tables
        paragraph_tokens = merge_overlapping_line_tokens(outside_ocr_results)
        for (x0, y0, x1, y1), clean_text, score in paragraph_tokens:
            yield Element(
                type="paragraph",
                text=clean_text,
                page=1,
                bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
                markdown_repr=clean_text,
                confidence=round(score, 3),
            )

    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """
        Preprocess image with deskewing and contrast-gated adaptive enhancement.
        Clean images bypass enhancement filters to guarantee 0ms latency penalty and no artifacts.
        """
        deskewed_img, _ = estimate_and_deskew(img)

        # Contrast-gated bypass: only enhance low-contrast / faded documents
        if is_low_contrast(deskewed_img):
            return enhance_contrast_adaptive(deskewed_img)
        return deskewed_img
