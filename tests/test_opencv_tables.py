from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from universal_parser.core.engine import parse
from universal_parser.core.schema import TableData
from universal_parser.extractors.images.deskew import estimate_and_deskew
from universal_parser.extractors.images.scan_extractor import ImageScanExtractor
from universal_parser.extractors.tables.opencv_ensemble import OpenCVTableEnsemble


def _get_test_font(size: int = 18) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def test_visual_table_detection_clean_grid() -> None:
    img = Image.new("RGB", (600, 200), color="white")
    d = ImageDraw.Draw(img)

    # Draw 3x3 table grid
    d.rectangle([(20, 20), (580, 180)], outline="black", width=2)
    d.line([(20, 70), (580, 70)], fill="black", width=2)
    d.line([(20, 125), (580, 125)], fill="black", width=2)
    d.line([(200, 20), (200, 180)], fill="black", width=2)
    d.line([(390, 20), (390, 180)], fill="black", width=2)

    tokens = [
        ((30.0, 30.0, 100.0, 60.0), "Item", 0.99),
        ((210.0, 30.0, 280.0, 60.0), "Category", 0.99),
        ((400.0, 30.0, 470.0, 60.0), "Price", 0.99),
        ((30.0, 80.0, 100.0, 115.0), "Alpha", 0.99),
        ((210.0, 80.0, 280.0, 115.0), "Hardware", 0.99),
        ((400.0, 80.0, 470.0, 115.0), "$100", 0.99),
        ((30.0, 135.0, 100.0, 170.0), "Beta", 0.99),
        ((210.0, 135.0, 280.0, 170.0), "Software", 0.99),
        ((400.0, 135.0, 470.0, 170.0), "$200", 0.99),
    ]

    ensemble = OpenCVTableEnsemble()
    results = ensemble.extract_tables_from_image(np.array(img), tokens)

    assert len(results) == 1
    table = results[0]
    assert isinstance(table.data, TableData)
    assert table.data.headers == ["Item", "Category", "Price"]
    assert len(table.data.rows) == 2
    assert table.data.rows[0] == ["Alpha", "Hardware", "$100"]
    assert table.data.rows[1] == ["Beta", "Software", "$200"]
    assert table.confidence >= 0.80


def test_visual_table_detection_thin_lines() -> None:
    img = Image.new("RGB", (600, 200), color="white")
    d = ImageDraw.Draw(img)

    # Draw 3x3 table with 1px thin lines
    d.rectangle([(20, 20), (580, 180)], outline="black", width=1)
    d.line([(20, 70), (580, 70)], fill="black", width=1)
    d.line([(20, 125), (580, 125)], fill="black", width=1)
    d.line([(200, 20), (200, 180)], fill="black", width=1)
    d.line([(390, 20), (390, 180)], fill="black", width=1)

    tokens = [
        ((30.0, 30.0, 100.0, 60.0), "Col1", 0.99),
        ((210.0, 30.0, 280.0, 60.0), "Col2", 0.99),
        ((400.0, 30.0, 470.0, 60.0), "Col3", 0.99),
        ((30.0, 80.0, 100.0, 115.0), "A", 0.99),
        ((210.0, 80.0, 280.0, 115.0), "B", 0.99),
        ((400.0, 80.0, 470.0, 115.0), "C", 0.99),
        ((30.0, 135.0, 100.0, 170.0), "D", 0.99),
        ((210.0, 135.0, 280.0, 170.0), "E", 0.99),
        ((400.0, 135.0, 470.0, 170.0), "F", 0.99),
    ]

    ensemble = OpenCVTableEnsemble()
    results = ensemble.extract_tables_from_image(np.array(img), tokens)

    assert len(results) == 1
    assert results[0].data.headers == ["Col1", "Col2", "Col3"]
    assert results[0].data.rows[0] == ["A", "B", "C"]


def test_visual_table_detection_noisy_grid() -> None:
    img = Image.new("RGB", (620, 200), color="white")
    d = ImageDraw.Draw(img)

    d.rectangle([(20, 20), (600, 180)], outline="black", width=2)
    d.line([(20, 70), (600, 70)], fill="black", width=2)
    d.line([(20, 125), (600, 125)], fill="black", width=2)
    d.line([(210, 20), (210, 180)], fill="black", width=2)
    d.line([(410, 20), (410, 180)], fill="black", width=2)

    # Salt-and-pepper noise
    arr = np.array(img.convert("L"))
    rng = np.random.default_rng(seed=42)
    noise_mask = rng.random(arr.shape)
    arr[noise_mask < 0.02] = 0
    arr[noise_mask > 0.98] = 255
    noisy_img = Image.fromarray(arr).convert("RGB")

    tokens = [
        ((35.0, 35.0, 95.0, 60.0), "Asset", 0.95),
        ((225.0, 35.0, 285.0, 60.0), "Class", 0.95),
        ((425.0, 35.0, 505.0, 60.0), "Allocation", 0.95),
        ((35.0, 85.0, 95.0, 115.0), "Equity", 0.95),
        ((225.0, 85.0, 285.0, 115.0), "Public", 0.95),
        ((425.0, 85.0, 485.0, 115.0), "60%", 0.95),
        ((35.0, 140.0, 145.0, 170.0), "FixedIncome", 0.95),
        ((225.0, 140.0, 285.0, 170.0), "Bonds", 0.95),
        ((425.0, 140.0, 485.0, 170.0), "40%", 0.95),
    ]

    ensemble = OpenCVTableEnsemble()
    results = ensemble.extract_tables_from_image(np.array(noisy_img), tokens)

    assert len(results) == 1
    table = results[0]
    assert table.data.headers == ["Asset", "Class", "Allocation"]
    assert table.data.rows[0] == ["Equity", "Public", "60%"]
    assert table.data.rows[1] == ["FixedIncome", "Bonds", "40%"]


def test_visual_table_detection_non_table_image() -> None:
    img = Image.new("RGB", (500, 200), color="white")
    d = ImageDraw.Draw(img)
    font = _get_test_font(18)
    d.text(
        (50, 50), "This is a plain paragraph without any table borders.", fill="black", font=font
    )

    tokens = [
        ((50.0, 50.0, 400.0, 80.0), "This is a plain paragraph without any table borders.", 0.98)
    ]
    ensemble = OpenCVTableEnsemble()
    results = ensemble.extract_tables_from_image(np.array(img), tokens)

    assert results == []


def test_deskew_deadband_on_straight_image() -> None:
    img = Image.new("RGB", (600, 150), color="white")
    d = ImageDraw.Draw(img)
    font = _get_test_font(24)
    d.text((40, 40), "Standard Clean Text Line", fill="black", font=font)

    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    deskewed, angle = estimate_and_deskew(cv_img, deadband_deg=0.75)

    assert angle == 0.0
    assert deskewed.shape == cv_img.shape


def test_deskew_deadband_on_noisy_straight_image() -> None:
    img = Image.new("RGB", (600, 150), color="white")
    d = ImageDraw.Draw(img)
    font = _get_test_font(24)
    d.text((40, 40), "Noisy Straight Text Line", fill="black", font=font)

    arr = np.array(img.convert("L"))
    rng = np.random.default_rng(seed=42)
    noise_mask = rng.random(arr.shape)
    arr[noise_mask < 0.03] = 0
    arr[noise_mask > 0.97] = 255
    noisy_img = Image.fromarray(arr).convert("RGB")

    cv_img = cv2.cvtColor(np.array(noisy_img), cv2.COLOR_RGB2BGR)
    deskewed, angle = estimate_and_deskew(cv_img, deadband_deg=0.75)

    assert angle == 0.0
    assert deskewed.shape == cv_img.shape


def test_deskew_deadband_on_blurred_straight_image() -> None:
    from PIL import ImageFilter

    img = Image.new("RGB", (600, 150), color="white")
    d = ImageDraw.Draw(img)
    font = _get_test_font(24)
    d.text((40, 40), "Blurred Straight Text Line", fill="black", font=font)

    blurred_img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
    cv_img = cv2.cvtColor(np.array(blurred_img), cv2.COLOR_RGB2BGR)
    deskewed, angle = estimate_and_deskew(cv_img, deadband_deg=0.75)

    assert angle == 0.0
    assert deskewed.shape == cv_img.shape


def test_corrupt_image_raises_value_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        corrupt_file = Path(tmpdir) / "corrupt.png"
        corrupt_file.write_bytes(b"\x89PNG\r\n\x1a\nCorruptPayloadDataHereThatCannotBeDecoded")

        extractor = ImageScanExtractor()
        with pytest.raises(ValueError, match="Unreadable or corrupt image file"):
            list(extractor.stream(corrupt_file))


def test_mixed_text_and_table_image() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "mixed_doc.png"
        img = Image.new("RGB", (650, 400), color="white")
        d = ImageDraw.Draw(img)
        font = _get_test_font(20)

        # Header paragraph
        d.text((30, 20), "Monthly Executive Operations Report", fill="black", font=font)

        # Table in the middle
        d.rectangle([(30, 70), (620, 280)], outline="black", width=2)
        d.line([(30, 140), (620, 140)], fill="black", width=2)
        d.line([(30, 210), (620, 210)], fill="black", width=2)
        d.line([(220, 70), (220, 280)], fill="black", width=2)
        d.line([(420, 70), (420, 280)], fill="black", width=2)

        d.text((50, 95), "Region", fill="black", font=font)
        d.text((240, 95), "Q1 Revenue", fill="black", font=font)
        d.text((440, 95), "Growth", fill="black", font=font)

        d.text((50, 165), "North", fill="black", font=font)
        d.text((240, 165), "$1.2M", fill="black", font=font)
        d.text((440, 165), "+15%", fill="black", font=font)

        d.text((50, 235), "South", fill="black", font=font)
        d.text((240, 235), "$0.8M", fill="black", font=font)
        d.text((440, 235), "+8%", fill="black", font=font)

        # Footer paragraph
        d.text(
            (30, 320), "Report signed and verified by internal audit team.", fill="black", font=font
        )
        img.save(str(img_path))

        doc = parse(str(img_path))

        tables = [e for e in doc.content_tree if e.type == "table"]
        paragraphs = [e for e in doc.content_tree if e.type == "paragraph"]

        assert len(tables) == 1
        assert tables[0].data.headers[0] == "Region"
        assert "Q1" in tables[0].data.headers[1]
        assert "Growth" in tables[0].data.headers[2]
        assert len(tables[0].data.rows) == 2
        assert len(paragraphs) >= 2


def test_deskew_exact_ocr05_financial_fixture_remains_straight() -> None:
    """Exact regression test: OCR-05 2-line financial report with Gaussian blur (sigma=1.5)."""
    from PIL import ImageFilter

    base_ocr_text = (
        "Quarterly Financial Audit Report\nTotal Net Revenue Increased By Twelve Percent"
    )
    img = Image.new("RGB", (1000, 240), color="white")
    d = ImageDraw.Draw(img)
    font = _get_test_font(32)
    lines = base_ocr_text.split("\n")
    y = 40
    for line in lines:
        d.text((50, y), line, fill="black", font=font)
        y += 65

    blurred_img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
    cv_img = cv2.cvtColor(np.array(blurred_img), cv2.COLOR_RGB2BGR)

    deskewed, angle = estimate_and_deskew(cv_img, deadband_deg=0.75)
    assert angle == 0.0
    assert deskewed.shape == cv_img.shape

    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "ocr05_test.png"
        blurred_img.save(str(p))
        doc = parse(str(p))
        # Ensure it does NOT detect a fake 49-column table
        tables = [e for e in doc.content_tree if e.type == "table"]
        paragraphs = [e for e in doc.content_tree if e.type == "paragraph"]
        assert len(tables) == 0
        assert len(paragraphs) >= 1


def test_deskew_true_skewed_document_corrected() -> None:
    """A truly tilted clean document (e.g. 15 degrees) must be detected and corrected."""
    base_text = "Quarterly Financial Audit Report\nTotal Net Revenue Increased By Twelve Percent"
    img = Image.new("RGB", (1000, 240), color="white")
    d = ImageDraw.Draw(img)
    font = _get_test_font(32)
    lines = base_text.split("\n")
    y = 40
    for line in lines:
        d.text((50, y), line, fill="black", font=font)
        y += 65

    rotated_img = img.rotate(-15, resample=Image.BICUBIC, fillcolor="white")
    cv_img = cv2.cvtColor(np.array(rotated_img), cv2.COLOR_RGB2BGR)

    _, angle = estimate_and_deskew(cv_img, deadband_deg=0.75)
    assert abs(angle - 15.0) < 2.5


def test_visual_table_detection_geometry_only_without_ocr_tokens() -> None:
    """Geometry-only table extraction must detect grid cells even when ocr_tokens is None."""
    img = Image.new("RGB", (620, 200), color="white")
    d = ImageDraw.Draw(img)
    d.rectangle([(20, 20), (600, 180)], outline="black", width=2)
    d.line([(20, 70), (600, 70)], fill="black", width=2)
    d.line([(20, 125), (600, 125)], fill="black", width=2)
    d.line([(210, 20), (210, 180)], fill="black", width=2)
    d.line([(410, 20), (410, 180)], fill="black", width=2)

    ensemble = OpenCVTableEnsemble()
    results = ensemble.extract_tables_from_image(np.array(img), ocr_tokens=None)

    assert len(results) == 1
    assert len(results[0].data.headers) == 3
    assert len(results[0].data.rows) == 2


def test_visual_table_detection_on_high_res_image() -> None:
    """A small table on a high-res (2000x2000) canvas must not have its ruling lines eroded."""
    img = Image.new("RGB", (2000, 2000), color="white")
    d = ImageDraw.Draw(img)
    d.rectangle([(500, 500), (700, 650)], outline="black", width=2)
    d.line([(500, 575), (700, 575)], fill="black", width=2)
    d.line([(600, 500), (600, 650)], fill="black", width=2)

    ensemble = OpenCVTableEnsemble()
    results = ensemble.extract_tables_from_image(np.array(img), ocr_tokens=None)

    assert len(results) == 1
    assert len(results[0].data.headers) == 2
    assert len(results[0].data.rows) == 1
