from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from universal_parser.extractors.images.enhancement import (
    enhance_contrast_adaptive,
    is_low_contrast,
    merge_overlapping_line_tokens,
    normalize_ocr_token_text,
)
from universal_parser.extractors.images.scan_extractor import ImageScanExtractor


def test_is_low_contrast_clean_vs_faded():
    # Clean high contrast image (black text on white background)
    clean_img = np.full((100, 400, 3), 255, dtype=np.uint8)
    clean_img[20:80, 50:150] = 0  # Black box
    assert not is_low_contrast(clean_img)

    # Low contrast faded image (light gray on white)
    faded_img = np.full((100, 400, 3), 240, dtype=np.uint8)
    faded_img[20:80, 50:150] = 200  # Faded text
    assert is_low_contrast(faded_img)

    # Edge cases
    assert not is_low_contrast(None)
    assert not is_low_contrast(np.array([]))


def test_enhance_contrast_adaptive_runs():
    img = np.full((120, 300, 3), 220, dtype=np.uint8)
    img[30:90, 50:150] = 180
    enhanced = enhance_contrast_adaptive(img)
    assert enhanced.shape == img.shape
    assert enhanced.dtype == np.uint8

    # Grayscale image
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    enhanced_gray = enhance_contrast_adaptive(gray)
    assert enhanced_gray.shape == gray.shape


def test_normalize_ocr_token_text():
    # 1. CamelCase splitting
    assert normalize_ocr_token_text("FinancialAuditReport") == "Financial Audit Report"
    assert normalize_ocr_token_text("TotalNetRevenue") == "Total Net Revenue"

    # 2. Punctuation & Separators
    assert normalize_ocr_token_text("RAM$300$600") == "RAM $300 $600"
    assert normalize_ocr_token_text("INVOICE#94012") == "INVOICE #94012"

    # 3. Digits and text boundaries
    assert normalize_ocr_token_text("2ServerRAM") == "2 Server RAM"
    assert normalize_ocr_token_text("SSD150") == "SSD 150"
    assert normalize_ocr_token_text("Q1 Revenue") == "Q1 Revenue"
    assert normalize_ocr_token_text("FY2024 Report") == "FY 2024 Report"

    # 4. Currency / numbers cleanup
    assert normalize_ocr_token_text("$ 300") == "$300"
    assert normalize_ocr_token_text("# 94012") == "#94012"

    # 5. ALL-CAPS keyword segmentation
    assert normalize_ocr_token_text("QTYITEMPRICETOTAL") == "QTY ITEM PRICE TOTAL"
    assert normalize_ocr_token_text("INVOICESUMMARY") == "INVOICE SUMMARY"

    # 6. Empty string
    assert normalize_ocr_token_text("") == ""


def test_merge_overlapping_line_tokens():
    # Two overlapping boxes on the same line (UniversalParserE + Engine)
    box1 = [[50.0, 50.0], [290.0, 50.0], [290.0, 75.0], [50.0, 75.0]]
    box2 = [[280.0, 50.0], [380.0, 50.0], [380.0, 75.0], [280.0, 75.0]]
    box3 = [[50.0, 110.0], [500.0, 110.0], [500.0, 135.0], [50.0, 135.0]]

    raw_results = [
        (box1, "UniversalParserE", 0.98),
        (box2, "Engine", 0.99),
        (box3, "High Fidelity Normalization Layer", 0.99),
    ]

    merged = merge_overlapping_line_tokens(raw_results)
    assert len(merged) == 2  # box1 and box2 merged into one line

    # Line 1: 'Universal Parser Engine'
    assert merged[0][1] == "Universal Parser Engine"
    assert merged[0][0][0] == 50.0
    assert merged[0][0][2] == 380.0

    # Line 2: 'High Fidelity Normalization Layer'
    assert merged[1][1] == "High Fidelity Normalization Layer"


def test_image_scan_extractor_end_to_end():
    extractor = ImageScanExtractor()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        img_path = tmp_path / "test_scan.png"

        # Create simple image with text
        img = Image.new("RGB", (600, 150), color="white")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default(size=24)
        draw.text((30, 30), "Invoice #1042", fill="black", font=font)
        draw.text((30, 80), "Total Amount $500", fill="black", font=font)
        img.save(str(img_path))

        elements = list(extractor.stream(img_path))
        assert len(elements) >= 2
        texts = [e.text for e in elements if e.text]
        full_text = " ".join(texts)
        assert "Invoice" in full_text
        assert "Total" in full_text
