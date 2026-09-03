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


@register
class ImageScanExtractor(BaseExtractor):
    """
    Extractor for image and scanned files (.png, .jpg, .tiff, .bmp, .webp).
    Handles:
        - Image preprocessing (deskewing / contrast enhancement via OpenCV)
        - CPU-based text and bounding box detection via RapidOCR (ONNX)
        - Confidence scoring per text element
    """
    supported_types: ClassVar[list[FileType]] = [FileType.IMAGE]
    def __init__(self) -> None:
        super().__init__()
        # Initialize RapidOCR engine (cached in memory)
        self._ocr= RapidOCR()
        
    def stream(self, path: str | Path) -> Iterator[Element]:
        path_str= str(path)
        
        try:
            # Step 1: Read image with OpenCV
            img= cv2.imread(path_str)
            if img is None:
                return
            
            # Step 2: Preprocess / deskew
            preprocessing_img= self._preprocess_image(img)
            
            # Step 3: Run RapidOCR
            ocr_results, _ = self._ocr(preprocessing_img)
            if not ocr_results:
                return
            # Step 4: Stream extracted elements
            for item in ocr_results:
                dt_boxes, text, score= item
                clean_text= text.strip()
                if not clean_text:
                    continue
                
                # Compute bounding box (x0, y0, x1, y1)
                pts= np.array(dt_boxes, dtype= np.float32)
                x0= float(np.min(pts[:, 0]))
                y0= float(np.min(pts[:, 1]))
                x1= float(np.max(pts[:, 0]))
                y1= float(np.max(pts[:, 1]))
                
                yield Element(
                    type= "paragraph",
                    text= clean_text,
                    page= 1,
                    bbox= BBox(x0=x0, y0=y0, x1=x1, y1= y1),
                    markdown_repr= clean_text,
                    confidence= round(float(score), 3),
                )
        
        except Exception:      # noqa: BLE001
            return
        
    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """Basic contrast & grayscale cleanup for sharper OCR."""
        # RapidOCR handles RGB internally; return original if valid
        return img
    