from __future__ import annotations

import html
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import psutil
from PIL import Image, ImageDraw

from benchmarks.metrics.ocr_eval import compute_cer, compute_wer
from benchmarks.metrics.teds import TEDS
from universal_parser.core.engine import parse
from universal_parser.core.schema import TableData

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class TableEvalResult:
    name: str
    teds_full: float
    teds_structure: float
    duration_ms: float


@dataclass
class OCREvalResult:
    name: str
    cer: float
    wer: float
    duration_ms: float


def evaluate_table_baseline() -> list[TableEvalResult]:
    """Evaluates the parser's table extraction against ground truth table structures."""
    teds_full_evaluator = TEDS(structure_only=False)
    teds_struct_evaluator = TEDS(structure_only=True)
    results: list[TableEvalResult] = []

    table_fixtures = [
        {
            "name": "HTML Document Table",
            "file": "tests/fixtures/html/sample.html",
            "ground_truth_html": """
            <table>
                <thead>
                    <tr><th>Format</th><th>Speed</th></tr>
                </thead>
                <tbody>
                    <tr><td>HTML</td><td>Ultra Fast</td></tr>
                    <tr><td>PDF</td><td>High Precision</td></tr>
                </tbody>
            </table>
            """,
        },
        {
            "name": "CSV Spreadsheet Table",
            "file": "tests/fixtures/csv/sample.csv",
            "ground_truth_html": """
            <table>
                <thead>
                    <tr><th>Name</th><th>Age</th><th>Role</th><th>Department</th></tr>
                </thead>
                <tbody>
                    <tr><td>Alice</td><td>30</td><td>Engineer</td><td>R&D</td></tr>
                    <tr><td>Bob</td><td>25</td><td>Designer</td><td>UX</td></tr>
                    <tr><td>Charlie</td><td>35</td><td>Manager</td><td>Product</td></tr>
                </tbody>
            </table>
            """,
        },
    ]

    for item in table_fixtures:
        path = REPO_ROOT / item["file"]
        if not path.exists():
            raise FileNotFoundError(f"Evaluation fixture not found: {path}")

        start_time = time.perf_counter()
        doc = parse(str(path))
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Build predicted HTML with both <thead> and <tbody> and html.escape
        pred_html = ""
        for elem in doc.content_tree:
            if isinstance(elem.data, TableData):
                headers_html = "".join(f"<th>{html.escape(str(h))}</th>" for h in elem.data.headers)
                thead = f"<thead><tr>{headers_html}</tr></thead>" if headers_html else ""

                rows_html = "".join(
                    f"<tr>{''.join(f'<td>{html.escape(str(cell))}</td>' for cell in row)}</tr>"
                    for row in elem.data.rows
                )
                tbody = f"<tbody>{rows_html}</tbody>"
                pred_html = f"<table>{thead}{tbody}</table>"
                break

        if not pred_html:
            pred_html = "<table><tr><td>empty</td></tr></table>"

        gt_html = item["ground_truth_html"]
        score_full = teds_full_evaluator.evaluate(pred_html, gt_html)
        score_struct = teds_struct_evaluator.evaluate(pred_html, gt_html)

        results.append(
            TableEvalResult(
                name=item["name"],
                teds_full=score_full,
                teds_structure=score_struct,
                duration_ms=duration_ms,
            )
        )

    return results


def evaluate_ocr_baseline() -> list[OCREvalResult]:
    """Evaluates the parser's OCR pipeline against labeled ground truth scanned documents."""
    results: list[OCREvalResult] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        scan_path = Path(tmpdir) / "sample_scan.png"

        # Generate a clean synthetic scan
        img = Image.new("RGB", (500, 180), color="white")
        draw = ImageDraw.Draw(img)
        draw.text((25, 35), "Universal Parser OCR Engine", fill="black")
        draw.text((25, 95), "High Throughput Local CPU Extraction", fill="black")
        img.save(str(scan_path))

        gt_text = "Universal Parser OCR Engine\nHigh Throughput Local CPU Extraction"

        start_time = time.perf_counter()
        doc = parse(str(scan_path))
        duration_ms = (time.perf_counter() - start_time) * 1000

        extracted_text = "\n".join(elem.text for elem in doc.content_tree if elem.text).strip()

        cer = compute_cer(gt_text, extracted_text, ignore_case=True)
        wer = compute_wer(gt_text, extracted_text, ignore_case=True)

        results.append(
            OCREvalResult(
                name="Synthetic Scanned Document (CPU OCR)",
                cer=cer,
                wer=wer,
                duration_ms=duration_ms,
            )
        )

    return results


def main() -> None:
    process = psutil.Process()
    start_rss = process.memory_info().rss / (1024 * 1024)

    print("\n" + "=" * 70)
    print(" UNIVERSAL DOC PARSER — GROUND TRUTH BASELINE EVALUATION")
    print("=" * 70)

    # 1. Run Table Evaluations
    print("\n[1/2] Evaluating Table Structure Recognition (TEDS)...")
    table_results = evaluate_table_baseline()
    for res in table_results:
        print(
            f"  * {res.name:<38} | Full TEDS: {res.teds_full * 100:5.1f}% | "
            f"Struct TEDS: {res.teds_structure * 100:5.1f}% | Latency: {res.duration_ms:6.1f} ms"
        )

    if table_results:
        avg_full = sum(r.teds_full for r in table_results) / len(table_results) * 100
        avg_struct = sum(r.teds_structure for r in table_results) / len(table_results) * 100
        print(
            f"  --> Average Table Accuracy: Full TEDS = {avg_full:.1f}% | "
            f"Structure TEDS = {avg_struct:.1f}%"
        )

    # 2. Run OCR Evaluations
    print("\n[2/2] Evaluating OCR Extraction Accuracy (CER / WER)...")
    ocr_results = evaluate_ocr_baseline()
    for res in ocr_results:
        print(
            f"  * {res.name:<38} | CER: {res.cer * 100:5.1f}% | "
            f"WER: {res.wer * 100:5.1f}% | Latency: {res.duration_ms:6.1f} ms"
        )

    if ocr_results:
        avg_cer = sum(r.cer for r in ocr_results) / len(ocr_results) * 100
        avg_wer = sum(r.wer for r in ocr_results) / len(ocr_results) * 100
        print(f"  --> Average OCR Error Rates: CER = {avg_cer:.1f}% | WER = {avg_wer:.1f}%")

    # Process RSS
    end_rss = process.memory_info().rss / (1024 * 1024)
    print("\n" + "-" * 70)
    print(f" Final Process RSS: {end_rss:.2f} MB (Delta: {end_rss - start_rss:.2f} MB)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
