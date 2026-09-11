from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import psutil

from benchmarks.metrics.ocr_eval import compute_cer, compute_wer
from benchmarks.metrics.teds import TEDS
from universal_parser.core.engine import parse
from universal_parser.core.schema import TableData


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
            "name": "Standard Bordered Financial Table",
            "file": "tests/fixtures/pdf/sample.pdf",
            "ground_truth_html": """
            <table>
                <thead>
                    <tr><th>Item</th><th>Description</th><th>Amount</th></tr>
                </thead>
                <tbody>
                    <tr><td>01</td><td>Consulting Services</td><td>$5,000.00</td></tr>
                    <tr><td>02</td><td>Software License</td><td>$1,200.00</td></tr>
                </tbody>
            </table>
            """,
        },
        {
            "name": "Multi-Column Spreadsheet Layout",
            "file": "tests/fixtures/csv/sample.csv",
            "ground_truth_html": """
            <table>
                <thead>
                    <tr><th>Name</th><th>Role</th><th>Department</th></tr>
                </thead>
                <tbody>
                    <tr><td>Alice</td><td>Engineer</td><td>Core</td></tr>
                    <tr><td>Bob</td><td>Manager</td><td>Product</td></tr>
                </tbody>
            </table>
            """,
        },
    ]

    for item in table_fixtures:
        path = Path(item["file"])
        if not path.exists():
            continue

        start_time = time.perf_counter()
        doc = parse(str(path))
        duration_ms = (time.perf_counter() - start_time) * 1000

        pred_html = ""
        for elem in doc.content_tree:
            if isinstance(elem.data, TableData):
                rows_html = []
                for row in elem.data.rows:
                    cells = "".join(f"<td>{cell}</td>" for cell in row)
                    rows_html.append(f"<tr>{cells}</tr>")
                pred_html = f"<table>{''.join(rows_html)}</table>"
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

    ocr_fixtures = [
        {
            "name": "Standard Clean Scanned Invoice",
            "file": "tests/fixtures/pdf/sample.pdf",
            "ground_truth_text": "Sample Document\nThis is a sample document for testing the universal parser.",
        }
    ]

    for item in ocr_fixtures:
        path = Path(item["file"])
        if not path.exists():
            continue

        start_time = time.perf_counter()
        doc = parse(str(path))
        duration_ms = (time.perf_counter() - start_time) * 1000

        extracted_text = "\n".join(elem.text for elem in doc.content_tree if elem.text).strip()
        gt_text = item["ground_truth_text"].strip()

        cer = compute_cer(gt_text, extracted_text, ignore_case=True)
        wer = compute_wer(gt_text, extracted_text, ignore_case=True)

        results.append(
            OCREvalResult(
                name=item["name"],
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
            f"  * {res.name:<38} | Full TEDS: {res.teds_full * 100:5.1f}% | Struct TEDS: {res.teds_structure * 100:5.1f}% | Latency: {res.duration_ms:6.1f} ms"
        )

    if table_results:
        avg_full = sum(r.teds_full for r in table_results) / len(table_results) * 100
        avg_struct = sum(r.teds_structure for r in table_results) / len(table_results) * 100
        print(
            f"  --> Average Table Accuracy: Full TEDS = {avg_full:.1f}% | Structure TEDS = {avg_struct:.1f}%"
        )

    # 2. Run OCR Evaluations
    print("\n[2/2] Evaluating OCR Extraction Accuracy (CER / WER)...")
    ocr_results = evaluate_ocr_baseline()
    for res in ocr_results:
        print(
            f"  * {res.name:<38} | CER: {res.cer * 100:5.1f}% | WER: {res.wer * 100:5.1f}% | Latency: {res.duration_ms:6.1f} ms"
        )

    if ocr_results:
        avg_cer = sum(r.cer for r in ocr_results) / len(ocr_results) * 100
        avg_wer = sum(r.wer for r in ocr_results) / len(ocr_results) * 100
        print(f"  --> Average OCR Error Rates: CER = {avg_cer:.1f}% | WER = {avg_wer:.1f}%")

    # Memory summary
    end_rss = process.memory_info().rss / (1024 * 1024)
    print("\n" + "-" * 70)
    print(f" Peak Process RSS: {end_rss:.2f} MB (Delta: {end_rss - start_rss:.2f} MB)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
