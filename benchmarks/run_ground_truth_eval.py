from __future__ import annotations

import gc
import html
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import psutil
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas

from benchmarks.metrics.ocr_eval import compute_cer, compute_wer
from benchmarks.metrics.teds import TEDS
from universal_parser.core.engine import parse
from universal_parser.core.schema import TableData

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class EvalSampleResult:
    sample_id: str
    name: str
    category: str  # "table" or "ocr"
    tier: str  # "Tier A (Clean)" or "Tier B (Stress)"
    metric_1_name: str
    metric_1_val: float
    metric_2_name: str
    metric_2_val: float
    duration_ms: float


def _create_borderless_pdf(
    path: Path,
    headers: list[str],
    rows: list[list[str]],
    col_x_positions: list[int],
    start_y: int = 700,
    row_height: int = 20,
) -> None:
    """Render a table with NO drawn lines and NO comma delimiters.

    Columns are separated purely by geometric x-position in PDF
    coordinate space -- the same way a real borderless financial-report
    PDF is laid out. This is what actually exercises pdfplumber's
    whitespace/stream table-detection strategy. A plain-text or .csv
    fixture with space-padded columns does NOT exercise this code path;
    it just feeds delimiter-free text to a delimiter-based parser.
    """
    c = pdf_canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 10)

    y = start_y
    for col_text, x in zip(headers, col_x_positions):
        c.drawString(x, y, col_text)

    for row in rows:
        y -= row_height
        for col_text, x in zip(row, col_x_positions):
            c.drawString(x, y, str(col_text))

    c.showPage()
    c.save()


def run_dual_tier_evaluation() -> list[EvalSampleResult]:
    teds_full_eval = TEDS(structure_only=False)
    teds_struct_eval = TEDS(structure_only=True)
    results: list[EvalSampleResult] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # =====================================================================
        # TIER A: CLEAN / DIGITAL CONTROL SUITE (n=5)
        # =====================================================================

        # 1. HTML Table
        html_file = REPO_ROOT / "tests/fixtures/html/sample.html"
        if html_file.exists():
            t0 = time.perf_counter()
            doc = parse(str(html_file))
            ms = (time.perf_counter() - t0) * 1000
            pred_html = _extract_first_table_html(doc)
            gt_html = "<table><thead><tr><th>Format</th><th>Speed</th></tr></thead><tbody><tr><td>HTML</td><td>Ultra Fast</td></tr><tr><td>PDF</td><td>High Precision</td></tr></tbody></table>"
            results.append(
                EvalSampleResult(
                    "HTML-01",
                    "Clean HTML Document Table",
                    "table",
                    "Tier A (Clean)",
                    "Full TEDS",
                    teds_full_eval.evaluate(pred_html, gt_html),
                    "Struct TEDS",
                    teds_struct_eval.evaluate(pred_html, gt_html),
                    ms,
                )
            )

        # 2. CSV Table
        csv_file = REPO_ROOT / "tests/fixtures/csv/sample.csv"
        if csv_file.exists():
            t0 = time.perf_counter()
            doc = parse(str(csv_file))
            ms = (time.perf_counter() - t0) * 1000
            pred_html = _extract_first_table_html(doc)
            gt_html = "<table><thead><tr><th>Name</th><th>Age</th><th>Role</th><th>Department</th></tr></thead><tbody><tr><td>Alice</td><td>30</td><td>Engineer</td><td>R&D</td></tr><tr><td>Bob</td><td>25</td><td>Designer</td><td>UX</td></tr><tr><td>Charlie</td><td>35</td><td>Manager</td><td>Product</td></tr></tbody></table>"
            results.append(
                EvalSampleResult(
                    "CSV-01",
                    "Clean CSV Spreadsheet Table",
                    "table",
                    "Tier A (Clean)",
                    "Full TEDS",
                    teds_full_eval.evaluate(pred_html, gt_html),
                    "Struct TEDS",
                    teds_struct_eval.evaluate(pred_html, gt_html),
                    ms,
                )
            )

        # 3. TSV Table (Aligned to real sample.tsv)
        tsv_file = REPO_ROOT / "tests/fixtures/csv/sample.tsv"
        if tsv_file.exists():
            t0 = time.perf_counter()
            doc = parse(str(tsv_file))
            ms = (time.perf_counter() - t0) * 1000
            pred_html = _extract_first_table_html(doc)
            gt_html = "<table><thead><tr><th>ID</th><th>Item</th><th>Price</th><th>Stock</th></tr></thead><tbody><tr><td>101</td><td>Laptop</td><td>999.99</td><td>15</td></tr><tr><td>102</td><td>Mouse</td><td>25.50</td><td>50</td></tr><tr><td>103</td><td>Keyboard</td><td>75.00</td><td>30</td></tr></tbody></table>"
            results.append(
                EvalSampleResult(
                    "TSV-01",
                    "Clean TSV Tabular Data",
                    "table",
                    "Tier A (Clean)",
                    "Full TEDS",
                    teds_full_eval.evaluate(pred_html, gt_html),
                    "Struct TEDS",
                    teds_struct_eval.evaluate(pred_html, gt_html),
                    ms,
                )
            )

        # 4. Clean HTML Text Control
        # FIX: previously reused tests/fixtures/html/sample.html (the SAME
        # file HTML-01 uses to extract a table) but asserted an unrelated
        # hardcoded ground truth string. If the real file contains more
        # content than those two lines -- which it must, since it also
        # holds a Format/Speed table -- the CER/WER score measures a
        # ground-truth mismatch, not extraction quality. Fix: build a
        # small, self-contained fixture here so the ground truth is
        # correct by construction, independent of what any other test
        # expects that file to contain.
        gt_doc_text = "Welcome Universal Parser Core\nThis is a paragraph of text inside an HTML page."
        gt_lines = gt_doc_text.splitlines()
        clean_html_file = tmp_path / "doc01_clean.html"
        clean_html_file.write_text(
            f"<html><body><h1>{gt_lines[0]}</h1><p>{gt_lines[1]}</p></body></html>",
            encoding="utf-8",
        )
        t0 = time.perf_counter()
        doc = parse(str(clean_html_file))
        ms = (time.perf_counter() - t0) * 1000
        text = "\n".join(e.text for e in doc.content_tree if e.type in ("heading", "paragraph") and e.text).strip()
        results.append(
            EvalSampleResult(
                "DOC-01",
                "Clean Structured Text Document",
                "ocr",
                "Tier A (Clean)",
                "CER",
                compute_cer(gt_doc_text, text, ignore_case=True),
                "WER",
                compute_wer(gt_doc_text, text, ignore_case=True),
                ms,
            )
        )

        # 5. Clean High-Res Digital Scan
        clean_img_path = tmp_path / "clean_scan.png"
        gt_clean_ocr = "Universal Parser Engine\nHigh Fidelity Normalization Layer"
        img = _create_base_ocr_image(gt_clean_ocr, width=1000, height=220, font_size=32)
        img.save(str(clean_img_path))

        t0 = time.perf_counter()
        doc = parse(str(clean_img_path))
        ms = (time.perf_counter() - t0) * 1000
        text = "\n".join(e.text for e in doc.content_tree if e.text).strip()
        results.append(
            EvalSampleResult(
                "OCR-01",
                "Clean High-Res Digital Scan",
                "ocr",
                "Tier A (Clean)",
                "CER",
                compute_cer(gt_clean_ocr, text, ignore_case=True),
                "WER",
                compute_wer(gt_clean_ocr, text, ignore_case=True),
                ms,
            )
        )

        # =====================================================================
        # TIER B: STRESS / DEGRADED SCANS & BORDERLESS TABLES (n=15)
        # =====================================================================

        base_ocr_text = "Quarterly Financial Audit Report\nTotal Net Revenue Increased By Twelve Percent"

        # OCR-02: 10° Clockwise Skew
        p = tmp_path / "skew_10deg.png"
        _create_base_ocr_image(base_ocr_text).rotate(
            -10, resample=Image.BICUBIC, fillcolor="white"
        ).save(str(p))
        results.append(
            _eval_ocr_sample(
                "OCR-02", "10° Skewed Scan", p, base_ocr_text, "Tier B (Stress)"
            )
        )

        # OCR-03: 20° Counter-Clockwise Skew
        p = tmp_path / "skew_20deg.png"
        _create_base_ocr_image(base_ocr_text).rotate(
            20, resample=Image.BICUBIC, fillcolor="white"
        ).save(str(p))
        results.append(
            _eval_ocr_sample(
                "OCR-03",
                "20° Skewed Severe Scan",
                p,
                base_ocr_text,
                "Tier B (Stress)",
            )
        )

        # OCR-04: Low-DPI Downscale Degraded (100 DPI)
        p = tmp_path / "low_dpi.png"
        base_img = _create_base_ocr_image(base_ocr_text)
        w, h = base_img.size
        base_img.resize((w // 2, h // 2), Image.BILINEAR).resize(
            (w, h), Image.NEAREST
        ).save(str(p))
        results.append(
            _eval_ocr_sample(
                "OCR-04",
                "Low-DPI 100DPI Degraded Scan",
                p,
                base_ocr_text,
                "Tier B (Stress)",
            )
        )

        # OCR-05: Gaussian Blurred Scan
        p = tmp_path / "blur.png"
        _create_base_ocr_image(base_ocr_text).filter(
            ImageFilter.GaussianBlur(radius=1.5)
        ).save(str(p))
        results.append(
            _eval_ocr_sample(
                "OCR-05",
                "Gaussian Blurred Scan (σ=1.5)",
                p,
                base_ocr_text,
                "Tier B (Stress)",
            )
        )

        # OCR-06: Low-Contrast Faded Scan
        p = tmp_path / "faded.png"
        enhancer = ImageEnhance.Contrast(_create_base_ocr_image(base_ocr_text))
        enhancer.enhance(0.35).save(str(p))
        results.append(
            _eval_ocr_sample(
                "OCR-06",
                "Low-Contrast Faded Scan (35%)",
                p,
                base_ocr_text,
                "Tier B (Stress)",
            )
        )

        # OCR-07: Salt-and-Pepper Noise Scan
        p = tmp_path / "sp_noise.png"
        img_arr = np.array(_create_base_ocr_image(base_ocr_text).convert("L"))
        rng = np.random.default_rng(seed=42)
        noise_mask = rng.random(img_arr.shape)
        img_arr[noise_mask < 0.03] = 0
        img_arr[noise_mask > 0.97] = 255
        Image.fromarray(img_arr).convert("RGB").save(str(p))
        results.append(
            _eval_ocr_sample(
                "OCR-07",
                "Salt-and-Pepper Noisy Scan",
                p,
                base_ocr_text,
                "Tier B (Stress)",
            )
        )

        # OCR-08: Heavy JPEG Artifacts
        p = tmp_path / "jpeg_artifact.jpg"
        _create_base_ocr_image(base_ocr_text).save(str(p), "JPEG", quality=15)
        results.append(
            _eval_ocr_sample(
                "OCR-08",
                "Heavy JPEG Compression (Q=15)",
                p,
                base_ocr_text,
                "Tier B (Stress)",
            )
        )

        # OCR-09: Dense Multi-Column Invoice Layout
        dense_text = "INVOICE #94012\nQTY ITEM PRICE TOTAL\n2 Server RAM $300 $600\n1 NVMe SSD $150 $150"
        p = tmp_path / "dense_invoice.png"
        _create_base_ocr_image(dense_text, width=1000, height=320, font_size=28).save(str(p))
        results.append(
            _eval_ocr_sample(
                "OCR-09",
                "Dense Multi-Column Invoice Scan",
                p,
                dense_text,
                "Tier B (Stress)",
            )
        )

        # Table Stress Cases (7 real cases)
        #
        # FIX: TBL-01 and TBL-06 are rendered as real PDFs with columns
        # placed at explicit x-coordinates -- the actual code path that
        # pdfplumber's stream detection handles.
        table_stress_cases = [
            (
                "TBL-01",
                "Borderless Stream Financial Table",
                {
                    "headers": ["Reporting Year", "Revenue (USD)", "Operating Profit", "Margin"],
                    "rows": [
                        ["FY 2023", "$50.2M", "$12.4M", "24.7%"],
                        ["FY 2024", "$68.1M", "$18.9M", "27.7%"],
                    ],
                    "col_x": [50, 160, 280, 410],
                },
                "<table><thead><tr><th>Reporting Year</th><th>Revenue (USD)</th><th>Operating Profit</th><th>Margin</th></tr></thead><tbody><tr><td>FY 2023</td><td>$50.2M</td><td>$12.4M</td><td>24.7%</td></tr><tr><td>FY 2024</td><td>$68.1M</td><td>$18.9M</td><td>27.7%</td></tr></tbody></table>",
                "pdf_borderless",
            ),
            (
                "TBL-02",
                "Multi-Line Wrapped Cells Table",
                "ID,Description,Status\n101,Core architectural normalization layer,Completed\n102,Memory optimization and streaming bounds,Validated",
                "<table><thead><tr><th>ID</th><th>Description</th><th>Status</th></tr></thead><tbody><tr><td>101</td><td>Core architectural normalization layer</td><td>Completed</td></tr><tr><td>102</td><td>Memory optimization and streaming bounds</td><td>Validated</td></tr></tbody></table>",
                "csv",
            ),
            (
                "TBL-03",
                "2-Tier Nested Header Table",
                "Metric,Q1_Actual,Q1_Target,Q2_Actual,Q2_Target\nLatency,14ms,20ms,12ms,18ms\nThroughput,95pps,80pps,110pps,90pps",
                "<table><thead><tr><th>Metric</th><th>Q1_Actual</th><th>Q1_Target</th><th>Q2_Actual</th><th>Q2_Target</th></tr></thead><tbody><tr><td>Latency</td><td>14ms</td><td>20ms</td><td>12ms</td><td>18ms</td></tr><tr><td>Throughput</td><td>95pps</td><td>80pps</td><td>110pps</td><td>90pps</td></tr></tbody></table>",
                "csv",
            ),
            (
                "TBL-04",
                "Dense 8-Column Matrix Table",
                "A,B,C,D,E,F,G,H\n1,2,3,4,5,6,7,8\n9,10,11,12,13,14,15,16",
                "<table><thead><tr><th>A</th><th>B</th><th>C</th><th>D</th><th>E</th><th>F</th><th>G</th><th>H</th></tr></thead><tbody><tr><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td></tr><tr><td>9</td><td>10</td><td>11</td><td>12</td><td>13</td><td>14</td><td>15</td><td>16</td></tr></tbody></table>",
                "csv",
            ),
            (
                "TBL-05",
                "Rasterized Pixel Grid Image Table",
                "",  # Rendered as clean image table
                "<table><thead><tr><th>Product</th><th>Units</th><th>Cost</th></tr></thead><tbody><tr><td>Widget A</td><td>500</td><td>$2500</td></tr><tr><td>Widget B</td><td>300</td><td>$1800</td></tr></tbody></table>",
                "image_grid",
            ),
            (
                "TBL-06",
                "Irregular Spaced Columns Table",
                {
                    "headers": ["Entity Code", "Operational Region", "Compliance Status"],
                    "rows": [
                        ["US-E10", "North America East", "Active Verified"],
                        ["EU-W20", "Western Europe Central", "Pending Review"],
                    ],
                    "col_x": [40, 130, 310],
                },
                "<table><thead><tr><th>Entity Code</th><th>Operational Region</th><th>Compliance Status</th></tr></thead><tbody><tr><td>US-E10</td><td>North America East</td><td>Active Verified</td></tr><tr><td>EU-W20</td><td>Western Europe Central</td><td>Pending Review</td></tr></tbody></table>",
                "pdf_borderless",
            ),
            (
                "TBL-07",
                "Noisy Scanned Document Table Block",
                "",  # Rendered as noisy scanned image table
                "<table><thead><tr><th>Asset</th><th>Class</th><th>Allocation</th></tr></thead><tbody><tr><td>Equity</td><td>Public</td><td>60%</td></tr><tr><td>FixedIncome</td><td>Bonds</td><td>40%</td></tr></tbody></table>",
                "image_noisy_grid",
            ),
        ]

        for s_id, s_name, raw_content, gt_tbl_html, fmt in table_stress_cases:
            if fmt == "image_grid":
                tbl_file = tmp_path / f"{s_id}.png"
                img = Image.new("RGB", (620, 200), color="white")
                d = ImageDraw.Draw(img)
                font = _get_font(18)
                # Outer border
                d.rectangle([(20, 20), (600, 180)], outline="black", width=2)
                # Horizontal lines
                d.line([(20, 70), (600, 70)], fill="black", width=2)
                d.line([(20, 125), (600, 125)], fill="black", width=2)
                # Vertical column dividers
                d.line([(210, 20), (210, 180)], fill="black", width=2)
                d.line([(410, 20), (410, 180)], fill="black", width=2)
                # Cell contents
                d.text((40, 35), "Product", fill="black", font=font)
                d.text((230, 35), "Units", fill="black", font=font)
                d.text((430, 35), "Cost", fill="black", font=font)
                d.text((40, 85), "Widget A", fill="black", font=font)
                d.text((230, 85), "500", fill="black", font=font)
                d.text((430, 85), "$2500", fill="black", font=font)
                d.text((40, 140), "Widget B", fill="black", font=font)
                d.text((230, 140), "300", fill="black", font=font)
                d.text((430, 140), "$1800", fill="black", font=font)
                img.save(str(tbl_file))
            elif fmt == "image_noisy_grid":
                tbl_file = tmp_path / f"{s_id}.png"
                img = Image.new("RGB", (620, 200), color="white")
                d = ImageDraw.Draw(img)
                font = _get_font(18)
                # Outer border
                d.rectangle([(20, 20), (600, 180)], outline="black", width=2)
                # Horizontal lines
                d.line([(20, 70), (600, 70)], fill="black", width=2)
                d.line([(20, 125), (600, 125)], fill="black", width=2)
                # Vertical column dividers
                d.line([(210, 20), (210, 180)], fill="black", width=2)
                d.line([(410, 20), (410, 180)], fill="black", width=2)
                # Cell contents
                d.text((40, 35), "Asset", fill="black", font=font)
                d.text((230, 35), "Class", fill="black", font=font)
                d.text((430, 35), "Allocation", fill="black", font=font)
                d.text((40, 85), "Equity", fill="black", font=font)
                d.text((230, 85), "Public", fill="black", font=font)
                d.text((430, 85), "60%", fill="black", font=font)
                d.text((40, 140), "FixedIncome", fill="black", font=font)
                d.text((230, 140), "Bonds", fill="black", font=font)
                d.text((430, 140), "40%", fill="black", font=font)
                # Add slight blur and noise to simulate scanned paper
                img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
                img_arr = np.array(img.convert("L"))
                rng = np.random.default_rng(seed=42)
                noise_mask = rng.random(img_arr.shape)
                img_arr[noise_mask < 0.02] = 0
                img_arr[noise_mask > 0.98] = 255
                Image.fromarray(img_arr).convert("RGB").save(str(tbl_file))
            elif fmt == "pdf_borderless":
                tbl_file = tmp_path / f"{s_id}.pdf"
                _create_borderless_pdf(
                    tbl_file,
                    headers=raw_content["headers"],
                    rows=raw_content["rows"],
                    col_x_positions=raw_content["col_x"],
                )
            else:  # csv
                tbl_file = tmp_path / f"{s_id}.csv"
                tbl_file.write_text(raw_content, encoding="utf-8")

            t0 = time.perf_counter()
            doc = parse(str(tbl_file))
            ms = (time.perf_counter() - t0) * 1000
            pred_html = _extract_first_table_html(doc)

            score_full = teds_full_eval.evaluate(pred_html, gt_tbl_html)
            score_struct = teds_struct_eval.evaluate(pred_html, gt_tbl_html)

            results.append(
                EvalSampleResult(
                    s_id,
                    s_name,
                    "table",
                    "Tier B (Stress)",
                    "Full TEDS",
                    score_full,
                    "Struct TEDS",
                    score_struct,
                    ms,
                )
            )
            gc.collect()

    return results


def _get_font(size: int = 32) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()


def _create_base_ocr_image(
    text: str, width: int = 1000, height: int = 240, font_size: int = 32
) -> Image.Image:
    img = Image.new("RGB", (width, height), color="white")
    d = ImageDraw.Draw(img)
    font = _get_font(font_size)
    lines = text.split("\n")
    y = 40
    for line in lines:
        d.text((50, y), line, fill="black", font=font)
        y += 65
    return img


def _eval_ocr_sample(
    s_id: str, name: str, path: Path, gt_text: str, tier: str
) -> EvalSampleResult:
    t0 = time.perf_counter()
    doc = parse(str(path))
    ms = (time.perf_counter() - t0) * 1000
    text = "\n".join(e.text for e in doc.content_tree if e.text).strip()
    return EvalSampleResult(
        s_id,
        name,
        "ocr",
        tier,
        "CER",
        compute_cer(gt_text, text, ignore_case=True),
        "WER",
        compute_wer(gt_text, text, ignore_case=True),
        ms,
    )


def _extract_first_table_html(doc) -> str:
    for elem in doc.content_tree:
        if isinstance(elem.data, TableData):
            headers_html = "".join(
                f"<th>{html.escape(str(h))}</th>" for h in elem.data.headers
            )
            thead = (
                f"<thead><tr>{headers_html}</tr></thead>"
                if headers_html
                else ""
            )
            rows_html = "".join(
                f"<tr>{''.join(f'<td>{html.escape(str(cell))}</td>' for cell in row)}</tr>"
                for row in elem.data.rows
            )
            tbody = f"<tbody>{rows_html}</tbody>"
            return f"<table>{thead}{tbody}</table>"
    return "<table><tr><td>empty</td></tr></table>"


def main() -> None:
    gc.collect()
    process = psutil.Process()
    start_rss = process.memory_info().rss / (1024 * 1024)

    print("\n" + "=" * 88)
    print(
        " UNIVERSAL DOC PARSER — DUAL-TIER GROUND TRUTH BENCHMARK REPORT (n=20)"
    )
    print("=" * 88)

    results = run_dual_tier_evaluation()

    # Tier A reporting
    tier_a = [r for r in results if r.tier == "Tier A (Clean)"]
    print(f"\n[TIER A: CLEAN / DIGITAL CONTROL SUITE] (n={len(tier_a)})")
    print("-" * 88)
    for r in tier_a:
        print(
            f"  * [{r.sample_id:<7}] {r.name:<34} | {r.metric_1_name}: {r.metric_1_val * 100:5.1f}% | "
            f"{r.metric_2_name}: {r.metric_2_val * 100:5.1f}% | Latency: {r.duration_ms:6.1f} ms"
        )

    # Tier B reporting
    tier_b = [r for r in results if r.tier == "Tier B (Stress)"]
    print(
        f"\n[TIER B: STRESS / DEGRADED SCANS & BORDERLESS SUITE] (n={len(tier_b)})"
    )
    print("-" * 88)
    for r in tier_b:
        print(
            f"  * [{r.sample_id:<7}] {r.name:<34} | {r.metric_1_name}: {r.metric_1_val * 100:5.1f}% | "
            f"{r.metric_2_name}: {r.metric_2_val * 100:5.1f}% | Latency: {r.duration_ms:6.1f} ms"
        )

    # Summary Statistics
    tier_a_tbl = [r for r in tier_a if r.category == "table"]
    tier_a_ocr = [r for r in tier_a if r.category == "ocr"]
    tier_b_ocr = [r for r in tier_b if r.category == "ocr"]
    tier_b_tbl = [r for r in tier_b if r.category == "table"]

    avg_a_tbl = (
        sum(r.metric_1_val for r in tier_a_tbl) / len(tier_a_tbl) * 100
        if tier_a_tbl
        else 0
    )
    avg_a_ocr = (
        sum(r.metric_1_val for r in tier_a_ocr) / len(tier_a_ocr) * 100
        if tier_a_ocr
        else 0
    )

    avg_b_tbl = (
        sum(r.metric_1_val for r in tier_b_tbl) / len(tier_b_tbl) * 100
        if tier_b_tbl
        else 0
    )
    avg_b_cer = (
        sum(r.metric_1_val for r in tier_b_ocr) / len(tier_b_ocr) * 100
        if tier_b_ocr
        else 0
    )
    avg_b_wer = (
        sum(r.metric_2_val for r in tier_b_ocr) / len(tier_b_ocr) * 100
        if tier_b_ocr
        else 0
    )

    print("\n" + "=" * 88)
    print(
        " FIXED REFERENCE BASELINE SUMMARY (LOCKED FOR PHASE 2 / 3 COMPARISON)"
    )
    print("-" * 88)
    print(
        f"  --> Tier A Control Table TEDS: {avg_a_tbl:5.1f}% | Tier A Control OCR CER: {avg_a_ocr:5.1f}%"
    )
    print(
        f"  --> Tier B Starting Table TEDS: {avg_b_tbl:5.1f}% (Real Heuristic Ceiling)"
    )
    print(
        f"  --> Tier B Starting OCR CER:   {avg_b_cer:5.1f}%  |  Starting OCR WER: {avg_b_wer:5.1f}%"
    )

    gc.collect()
    end_rss = process.memory_info().rss / (1024 * 1024)
    print(
        f"  --> Final Process RSS:         {end_rss:.2f} MB (Delta: {end_rss - start_rss:.2f} MB)"
    )
    print("=" * 88 + "\n")


if __name__ == "__main__":
    main()