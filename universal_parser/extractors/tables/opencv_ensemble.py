from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import numpy as np

from universal_parser.core.schema import BBox, TableData

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class VisualTableResult:
    """Represents a detected visual table with structured data and spatial boundaries."""

    data: TableData
    bbox: BBox
    confidence: float
    cell_bboxes: list[tuple[float, float, float, float]]


class OpenCVTableEnsemble:
    """
    Extracts tabular data from raster images and scanned documents using OpenCV morphological
    line detection, projection profiling, and spatial OCR token clustering.

    Pipeline:
        1. Preprocessing: Median filtering and adaptive/Otsu binarization.
        2. Morphological Kernel Filtering: Isolation of horizontal and vertical ruling lines.
        3. Line Continuity Dilation: Bridging broken line segments caused by noise or scan artifacts.
        4. Projection Profiling & Grid Reconstruction: Extracting table row/column coordinates.
        5. Spatial OCR Assignment: Associating text tokens with their corresponding grid cells.
    """

    def __init__(
        self,
        min_table_width: int = 80,
        min_table_height: int = 40,
        min_rows: int = 2,
        min_cols: int = 2,
    ) -> None:
        self.min_table_width = min_table_width
        self.min_table_height = min_table_height
        self.min_rows = min_rows
        self.min_cols = min_cols

    def extract_tables_from_image(
        self,
        image: np.ndarray,
        ocr_tokens: Sequence[tuple[tuple[float, float, float, float], str, float]] | None = None,
    ) -> list[VisualTableResult]:
        """
        Detect and extract structured tables from an image array.

        Args:
            image: Input image as BGR, RGB, or Grayscale numpy array.
            ocr_tokens: Optional list of tuples ((x0, y0, x1, y1), text, confidence).

        Returns:
            list[VisualTableResult]: Detected tables with headers, rows, and spatial bounding boxes.
        """
        if image is None or image.size == 0:
            return []

        # Step 1: Normalize color space to Grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h_img, w_img = gray.shape[:2]
        if h_img < self.min_table_height or w_img < self.min_table_width:
            return []

        # Step 2: Inverted Binarization (preserve 1px thin lines without destructive median filter)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        # Dynamic scale factors based on image dimensions
        h_scale = max(18, w_img // 28)
        v_scale = max(18, h_img // 18)

        # Pre-closing to bridge 1px thin or broken lines
        closed_thresh = cv2.morphologyEx(
            thresh,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
            iterations=1,
        )

        # Step 3: Morphological Line Extraction
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_scale, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_scale))

        h_lines = cv2.morphologyEx(closed_thresh, cv2.MORPH_OPEN, h_kernel)
        h_lines = cv2.dilate(
            h_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1)), iterations=2
        )

        v_lines = cv2.morphologyEx(closed_thresh, cv2.MORPH_OPEN, v_kernel)
        v_lines = cv2.dilate(
            v_lines, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15)), iterations=2
        )

        # Combine lines and dilate to ensure intersection connectivity
        table_grid = cv2.bitwise_or(h_lines, v_lines)
        table_grid_connected = cv2.dilate(
            table_grid, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1
        )

        # Step 4: Outer Table Region Detection
        contours, _ = cv2.findContours(
            table_grid_connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return []

        results: list[VisualTableResult] = []
        tokens = ocr_tokens or []

        for contour in contours:
            tx, ty, tw, th = cv2.boundingRect(contour)
            if tw < self.min_table_width or th < self.min_table_height:
                continue

            # Sub-masks for this table region
            sub_h = h_lines[ty : ty + th, tx : tx + tw]
            sub_v = v_lines[ty : ty + th, tx : tx + tw]

            # Horizontal Line Y-Coordinates via Projection Profile
            h_proj = np.sum(sub_h > 0, axis=1)
            h_line_ys = self._detect_line_positions(
                h_proj, expected_line_length=tw, threshold_ratio=0.30, offset=ty
            )

            # Vertical Line X-Coordinates via Projection Profile
            v_proj = np.sum(sub_v > 0, axis=0)
            v_line_xs = self._detect_line_positions(
                v_proj, expected_line_length=th, threshold_ratio=0.30, offset=tx
            )

            if len(h_line_ys) < 2 or len(v_line_xs) < 2:
                continue

            num_rows = len(h_line_ys) - 1
            num_cols = len(v_line_xs) - 1

            if num_rows < self.min_rows or num_cols < self.min_cols:
                continue

            # Reconstruct 2D cell grid and assign OCR tokens
            grid_data: list[list[str]] = []
            all_cell_bboxes: list[tuple[float, float, float, float]] = []
            non_empty_cells = 0

            for r in range(num_rows):
                row_data: list[str] = []
                cy0, cy1 = float(h_line_ys[r]), float(h_line_ys[r + 1])

                for c in range(num_cols):
                    cx0, cx1 = float(v_line_xs[c]), float(v_line_xs[c + 1])
                    all_cell_bboxes.append((cx0, cy0, cx1, cy1))

                    # Find all OCR tokens whose center falls inside this cell
                    cell_tokens: list[tuple[float, float, str]] = []
                    for (bx0, by0, bx1, by1), text, _ in tokens:
                        center_x = (bx0 + bx1) / 2.0
                        center_y = (by0 + by1) / 2.0
                        if cx0 <= center_x <= cx1 and cy0 <= center_y <= cy1:
                            cell_tokens.append((by0, bx0, text))

                    # Sort tokens in cell by reading order (top-to-bottom, left-to-right)
                    cell_tokens.sort(key=lambda t: (t[0], t[1]))
                    cell_text = " ".join(t[2] for t in cell_tokens).strip()
                    if cell_text:
                        non_empty_cells += 1
                    row_data.append(cell_text)

                grid_data.append(row_data)

            if len(grid_data) < self.min_rows:
                continue

            headers = grid_data[0]
            data_rows = grid_data[1:]

            # Geometric uniformity score: measures height and width regularity across cells
            row_heights = [h_line_ys[i + 1] - h_line_ys[i] for i in range(num_rows)]
            col_widths = [v_line_xs[i + 1] - v_line_xs[i] for i in range(num_cols)]
            h_var = float(np.std(row_heights) / max(1.0, np.mean(row_heights)))
            w_var = float(np.std(col_widths) / max(1.0, np.mean(col_widths)))
            uniformity = max(0.0, 1.0 - 0.5 * (h_var + w_var))
            fill_ratio = non_empty_cells / max(1, num_rows * num_cols)

            confidence = round(
                min(0.98, max(0.65, 0.70 + 0.15 * uniformity + 0.13 * fill_ratio)), 3
            )

            table_bbox = BBox(
                x0=float(v_line_xs[0]),
                y0=float(h_line_ys[0]),
                x1=float(v_line_xs[-1]),
                y1=float(h_line_ys[-1]),
            )

            results.append(
                VisualTableResult(
                    data=TableData(headers=headers, rows=data_rows),
                    bbox=table_bbox,
                    confidence=confidence,
                    cell_bboxes=all_cell_bboxes,
                )
            )

        return results

    @staticmethod
    def _detect_line_positions(
        projection: np.ndarray,
        expected_line_length: int,
        threshold_ratio: float,
        offset: int,
    ) -> list[int]:
        """Detect central coordinates of continuous line segments in a projection profile."""
        threshold = threshold_ratio * expected_line_length
        positions: list[int] = []
        in_line = False
        start_idx = 0

        for idx, count in enumerate(projection):
            if count > threshold:
                if not in_line:
                    in_line = True
                    start_idx = idx
            else:
                if in_line:
                    in_line = False
                    mid_idx = (start_idx + idx) // 2
                    positions.append(offset + mid_idx)

        if in_line:
            mid_idx = (start_idx + len(projection) - 1) // 2
            positions.append(offset + mid_idx)

        return positions
