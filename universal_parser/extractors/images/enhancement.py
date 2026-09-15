from __future__ import annotations

import re
from typing import Any

import cv2
import numpy as np

# Common tabular and invoice header keywords for all-caps token segmentation
COMMON_HEADER_KEYWORDS: list[str] = [
    "INVOICE",
    "REPORT",
    "STATEMENT",
    "SUMMARY",
    "QTY",
    "QUANTITY",
    "ITEM",
    "PRICE",
    "TOTAL",
    "SUBTOTAL",
    "DESCRIPTION",
    "AMOUNT",
    "TAX",
    "DISCOUNT",
    "UNIT",
    "RATE",
    "DATE",
    "NAME",
    "ID",
    "CODE",
    "TYPE",
    "STATUS",
    "ACCOUNT",
    "REVENUE",
    "PROFIT",
    "MARGIN",
    "COST",
    "SALES",
    "YEAR",
    "MONTH",
]


def is_low_contrast(img: np.ndarray, min_std_dev: float = 35.0) -> bool:
    """
    Check whether an image exhibits low global contrast or faded text.

    Args:
        img: Input image as BGR or grayscale numpy array.
        min_std_dev: Minimum standard deviation of luminance. If std dev is below
                     this threshold, the image has low dynamic range and requires enhancement.

    Returns:
        bool: True if image is low-contrast and should undergo adaptive enhancement.
    """
    if img is None or img.size == 0:
        return False

    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    std_dev = float(np.std(gray))
    return std_dev < min_std_dev


def enhance_contrast_adaptive(
    img: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """
    Apply Contrast Limited Adaptive Histogram Equalization (CLAHE)
    and mild unsharp masking to enhance faded text while avoiding noise amplification.

    Args:
        img: Input image as BGR or grayscale numpy array.
        clip_limit: Threshold for contrast limiting in CLAHE.
        tile_grid_size: Grid size for histogram equalization tiles.

    Returns:
        np.ndarray: Enhanced image in the original color channel format.
    """
    if img is None or img.size == 0:
        return img

    is_bgr = len(img.shape) == 3
    if is_bgr:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img.copy()

    # Mild unsharp mask to restore soft character edge transitions
    gaussian = cv2.GaussianBlur(gray, (0, 0), 1.5)
    unsharp = cv2.addWeighted(gray, 1.4, gaussian, -0.4, 0)

    # Adaptive histogram equalization
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    enhanced = clahe.apply(unsharp)

    if is_bgr:
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    return enhanced


def normalize_ocr_token_text(text: str) -> str:
    """
    Recover missing whitespace and separators in OCR outputs.
    Handles:
        - CamelCase concatenation: 'FinancialAudit' -> 'Financial Audit'
        - Punctuation/separators: 'RAM$300' -> 'RAM $300', 'INVOICE#94012' -> 'INVOICE #94012'
        - Digits vs alphabet boundary: '2Server' -> '2 Server', 'SSD150' -> 'SSD 150'
        - Financial syntax preservation: '$ 300' -> '$300', '# 94012' -> '#94012'
        - ALL-CAPS keyword segmentation: 'QTYITEMPRICETOTAL' -> 'QTY ITEM PRICE TOTAL'
    """
    if not text:
        return ""

    s = text

    # 1. CamelCase splitting: lowercase followed directly by uppercase
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)

    # 2. Separators: #, $
    s = re.sub(r"([A-Za-z0-9])(\$|\#)", r"\1 \2", s)
    s = re.sub(r"(\$|\#)([A-Za-z0-9])", r"\1\2", s)

    # 3. Digits vs Multi-letter Words: '2Server' -> '2 Server', 'RAM300' -> 'RAM 300'
    # Preserves single-letter codes and quarters like 'Q1', 'H2', 'v2', 'A1'
    s = re.sub(r"([A-Za-z]{2,})(\d+)", r"\1 \2", s)
    s = re.sub(r"(\d+)([A-Za-z]{2,})", r"\1 \2", s)

    # 4. Currency and identifier spacing cleanup: '$ 300' -> '$300'
    s = re.sub(r"(\$|\#)\s+(\d)", r"\1\2", s)

    # 5. ALL-CAPS keyword segmentation for concatenated table headers
    words = s.split()
    processed_words: list[str] = []
    for w in words:
        if len(w) > 4 and w.isupper() and w.isalpha():
            curr = w
            segments: list[str] = []
            while curr:
                matched = False
                for kw in sorted(COMMON_HEADER_KEYWORDS, key=len, reverse=True):
                    if curr.startswith(kw):
                        segments.append(kw)
                        curr = curr[len(kw) :]
                        matched = True
                        break
                if not matched:
                    segments.append(curr[0])
                    curr = curr[1:]
            if len(segments) > 1 and all(seg in COMMON_HEADER_KEYWORDS for seg in segments):
                processed_words.append(" ".join(segments))
            else:
                processed_words.append(w)
        else:
            processed_words.append(w)

    s = " ".join(processed_words)
    return re.sub(r"[ \t]+", " ", s).strip()


def merge_overlapping_line_tokens(
    ocr_results: list[Any],
) -> list[tuple[tuple[float, float, float, float], str, float]]:
    """
    Merge adjacent or horizontally overlapping bounding boxes on the same text line
    to eliminate duplicate character tokens and fragmented words.

    Args:
        ocr_results: Raw list of (dt_boxes, text, score) from RapidOCR.

    Returns:
        list of ((x0, y0, x1, y1), normalized_text, score)
    """
    if not ocr_results:
        return []

    boxes: list[dict[str, Any]] = []
    for item in ocr_results:
        dt_boxes, text, score = item
        clean_text = str(text).strip()
        if not clean_text:
            continue

        pts = np.array(dt_boxes, dtype=np.float32)
        x0 = float(np.min(pts[:, 0]))
        y0 = float(np.min(pts[:, 1]))
        x1 = float(np.max(pts[:, 0]))
        y1 = float(np.max(pts[:, 1]))
        boxes.append(
            {
                "bbox": (x0, y0, x1, y1),
                "text": clean_text,
                "score": float(score),
            }
        )

    # Sort boxes top to bottom by y0, then left to right by x0
    boxes.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))

    merged: list[dict[str, Any]] = []
    for b in boxes:
        if not merged:
            merged.append(b)
            continue

        prev = merged[-1]
        px0, py0, px1, py1 = prev["bbox"]
        cx0, cy0, cx1, cy1 = b["bbox"]

        prev_cy = (py0 + py1) / 2.0
        curr_cy = (cy0 + cy1) / 2.0
        same_line = abs(prev_cy - curr_cy) < 12.0 and abs((py1 - py0) - (cy1 - cy0)) < 15.0

        # Check if boxes overlap horizontally or are adjacent
        if same_line and cx0 <= px1 + 5.0:
            prev_t = prev["text"]
            curr_t = b["text"]
            # Deduplicate character overlap if last character matches first character
            if prev_t and curr_t and prev_t[-1].lower() == curr_t[0].lower():
                merged_text = prev_t[:-1] + " " + curr_t
            else:
                merged_text = prev_t + " " + curr_t

            prev["bbox"] = (min(px0, cx0), min(py0, cy0), max(px1, cx1), max(py1, cy1))
            prev["text"] = merged_text
            prev["score"] = (prev["score"] + b["score"]) / 2.0
        else:
            merged.append(b)

    # Normalize whitespace and character boundaries
    results: list[tuple[tuple[float, float, float, float], str, float]] = []
    for b in merged:
        norm_text = normalize_ocr_token_text(b["text"])
        if norm_text:
            results.append((b["bbox"], norm_text, b["score"]))

    return results
