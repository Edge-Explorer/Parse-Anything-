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
from universal_parser.extractors.tables.opencv_ensemble import OpenCVTableEnsemble


@register
class ImageScanExtractor(BaseExtractor):
    """
    Extractor for image and scanned files (.png, .jpg, .tiff, .bmp, .webp).
    Handles:
        - Image preprocessing (deskewing via Hough transform and line suppression)
        - CPU-based text and bounding box detection via RapidOCR (ONNX)
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

        # Step 2: Preprocess / deskew
        preprocessing_img = self._preprocess_image(img)

        # Step 3: Run RapidOCR
        ocr_results, _ = self._ocr(preprocessing_img)
        if not ocr_results:
            return

        # Collect parsed OCR tokens
        ocr_tokens: list[tuple[tuple[float, float, float, float], str, float]] = []
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
            ocr_tokens.append(((x0, y0, x1, y1), clean_text, float(score)))

        # Step 4: Extract visual tables from image gridlines
        visual_tables = self._table_ensemble.extract_tables_from_image(
            preprocessing_img, ocr_tokens
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

        # Step 6: Filter out OCR tokens that belong inside extracted tables
        for (x0, y0, x1, y1), clean_text, score in ocr_tokens:
            center_x = (x0 + x1) / 2.0
            center_y = (y0 + y1) / 2.0

            inside_table = False
            for tbl in visual_tables:
                if (
                    tbl.bbox.x0 - 5 <= center_x <= tbl.bbox.x1 + 5
                    and tbl.bbox.y0 - 5 <= center_y <= tbl.bbox.y1 + 5
                ):
                    inside_table = True
                    break

            if not inside_table:
                yield Element(
                    type="paragraph",
                    text=clean_text,
                    page=1,
                    bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
                    markdown_repr=clean_text,
                    confidence=round(score, 3),
                )

    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """Correct angular skew using Hough line estimation while ignoring table ruling lines."""
        deskewed_img, _ = estimate_and_deskew(img)
        return deskewed_img
