from __future__ import annotations

import difflib
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from rapidocr_onnxruntime import RapidOCR

from benchmarks.metrics.ocr_eval import compute_cer
from benchmarks.run_ground_truth_eval import _create_base_ocr_image
from universal_parser.extractors.images.deskew import estimate_and_deskew


@dataclass
class TokenMatch:
    fixture_id: str
    token_text: str
    gt_matched_text: str
    confidence: float
    token_cer: float
    is_correct: bool
    bbox: tuple[float, float, float, float]


def find_best_gt_match(detected_token: str, gt_full_text: str) -> tuple[str, float]:
    """Find the best matching ground truth word or subphrase for a detected token."""
    gt_words = gt_full_text.split()
    best_match = ""
    lowest_cer = 1.0

    # Test single words and multi-word phrases up to length 3
    candidates: list[str] = []
    for i in range(len(gt_words)):
        for length in (1, 2, 3):
            if i + length <= len(gt_words):
                candidates.append(" ".join(gt_words[i : i + length]))

    det_lower = detected_token.lower().strip()
    for cand in candidates:
        cand_lower = cand.lower().strip()
        cer = compute_cer(cand_lower, det_lower, ignore_case=True)
        if cer < lowest_cer:
            lowest_cer = cer
            best_match = cand
        if lowest_cer == 0.0:
            break

    # If no close candidate found, compare against whole lines
    if lowest_cer > 0.6:
        for line in gt_full_text.splitlines():
            line_cand = line.strip()
            if not line_cand:
                continue
            matcher = difflib.SequenceMatcher(None, det_lower, line_cand.lower())
            match = matcher.find_longest_match(0, len(det_lower), 0, len(line_cand))
            if match.size > 0:
                sub = line_cand[match.b : match.b + max(match.size, len(det_lower))]
                cer = compute_cer(sub, det_lower, ignore_case=True)
                if cer < lowest_cer:
                    lowest_cer = cer
                    best_match = sub

    return best_match, lowest_cer


def run_confidence_diagnostics() -> list[TokenMatch]:
    ocr = RapidOCR()
    matches: list[TokenMatch] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        base_ocr_text = (
            "Quarterly Financial Audit Report\nTotal Net Revenue Increased By Twelve Percent"
        )
        gt_clean_ocr = "Universal Parser Engine\nHigh Fidelity Normalization Layer"
        dense_text = (
            "INVOICE #94012\nQTY ITEM PRICE TOTAL\n2 Server RAM $300 $600\n1 NVMe SSD $150 $150"
        )

        fixtures: list[tuple[str, str, Path, str]] = []

        # OCR-01: Clean Scan
        p1 = tmp_path / "clean_scan.png"
        _create_base_ocr_image(gt_clean_ocr, width=1000, height=220, font_size=32).save(str(p1))
        fixtures.append(("OCR-01", "Clean High-Res Digital Scan", p1, gt_clean_ocr))

        # OCR-02: 10 deg Skew
        p2 = tmp_path / "skew_10deg.png"
        _create_base_ocr_image(base_ocr_text).rotate(
            -10, resample=Image.BICUBIC, fillcolor="white"
        ).save(str(p2))
        fixtures.append(("OCR-02", "10 deg Skewed Scan", p2, base_ocr_text))

        # OCR-03: 20 deg Skew
        p3 = tmp_path / "skew_20deg.png"
        _create_base_ocr_image(base_ocr_text).rotate(
            20, resample=Image.BICUBIC, fillcolor="white"
        ).save(str(p3))
        fixtures.append(("OCR-03", "20 deg Skewed Severe Scan", p3, base_ocr_text))

        # OCR-04: Low-DPI 100DPI
        p4 = tmp_path / "low_dpi.png"
        base_img = _create_base_ocr_image(base_ocr_text)
        w, h = base_img.size
        base_img.resize((w // 2, h // 2), Image.BILINEAR).resize((w, h), Image.NEAREST).save(
            str(p4)
        )
        fixtures.append(("OCR-04", "Low-DPI 100DPI Degraded Scan", p4, base_ocr_text))

        # OCR-05: Gaussian Blur
        p5 = tmp_path / "blur.png"
        _create_base_ocr_image(base_ocr_text).filter(ImageFilter.GaussianBlur(radius=1.5)).save(
            str(p5)
        )
        fixtures.append(("OCR-05", "Gaussian Blurred Scan (sigma=1.5)", p5, base_ocr_text))

        # OCR-06: Low-Contrast Faded (35%)
        p6 = tmp_path / "faded.png"
        ImageEnhance.Contrast(_create_base_ocr_image(base_ocr_text)).enhance(0.35).save(str(p6))
        fixtures.append(("OCR-06", "Low-Contrast Faded Scan (35%)", p6, base_ocr_text))

        # OCR-07: Salt-and-Pepper Noise
        p7 = tmp_path / "sp_noise.png"
        img_arr = np.array(_create_base_ocr_image(base_ocr_text).convert("L"))
        rng = np.random.default_rng(seed=42)
        noise_mask = rng.random(img_arr.shape)
        img_arr[noise_mask < 0.03] = 0
        img_arr[noise_mask > 0.97] = 255
        Image.fromarray(img_arr).convert("RGB").save(str(p7))
        fixtures.append(("OCR-07", "Salt-and-Pepper Noisy Scan", p7, base_ocr_text))

        # OCR-08: Heavy JPEG Compression (Q=15)
        p8 = tmp_path / "jpeg_artifact.jpg"
        _create_base_ocr_image(base_ocr_text).save(str(p8), "JPEG", quality=15)
        fixtures.append(("OCR-08", "Heavy JPEG Compression (Q=15)", p8, base_ocr_text))

        # OCR-09: Dense Multi-Column Invoice
        p9 = tmp_path / "dense_invoice.png"
        _create_base_ocr_image(dense_text, width=1000, height=320, font_size=28).save(str(p9))
        fixtures.append(("OCR-09", "Dense Multi-Column Invoice Scan", p9, dense_text))

        for f_id, f_name, f_path, gt_text in fixtures:
            img = cv2.imread(str(f_path))
            if img is None:
                continue

            prep_img, _ = estimate_and_deskew(img)
            ocr_results, _ = ocr(prep_img)
            if not ocr_results:
                continue

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

                best_match, cer = find_best_gt_match(clean_text, gt_text)
                is_correct = cer == 0.0

                matches.append(
                    TokenMatch(
                        fixture_id=f_id,
                        token_text=clean_text,
                        gt_matched_text=best_match,
                        confidence=float(score),
                        token_cer=cer,
                        is_correct=is_correct,
                        bbox=(x0, y0, x1, y1),
                    )
                )

    return matches


def print_diagnostic_report(matches: list[TokenMatch]) -> None:
    print("\n" + "=" * 92)
    print(" TOKEN CONFIDENCE & ERROR ALIGNMENT DIAGNOSTIC REPORT")
    print("=" * 92)

    print(f"\nTotal Extracted Tokens Analyzed: {len(matches)}")
    correct_tokens = [m for m in matches if m.is_correct]
    corrupted_tokens = [m for m in matches if not m.is_correct]

    print(
        f"  * Perfect Matches (CER == 0.0): {len(correct_tokens)} ({len(correct_tokens) / len(matches) * 100:.1f}%)"
    )
    print(
        f"  * Corrupted Tokens (CER > 0.0):  {len(corrupted_tokens)} ({len(corrupted_tokens) / len(matches) * 100:.1f}%)"
    )

    # Statistical distribution of confidence scores
    if correct_tokens:
        corr_scores = [m.confidence for m in correct_tokens]
        print("\n[Accurate Tokens Confidence Distribution]")
        print(
            f"  Mean: {np.mean(corr_scores):.4f} | Median: {np.median(corr_scores):.4f} | Min: {np.min(corr_scores):.4f} | Max: {np.max(corr_scores):.4f} | Std: {np.std(corr_scores):.4f}"
        )

    if corrupted_tokens:
        corrupt_scores = [m.confidence for m in corrupted_tokens]
        print("\n[Corrupted Tokens Confidence Distribution]")
        print(
            f"  Mean: {np.mean(corrupt_scores):.4f} | Median: {np.median(corrupt_scores):.4f} | Min: {np.min(corrupt_scores):.4f} | Max: {np.max(corrupt_scores):.4f} | Std: {np.std(corrupt_scores):.4f}"
        )

    # Inspect corrupted tokens in detail
    print("\n" + "-" * 92)
    print(" DETAILED CORRUPTED TOKENS INSPECTION (WHERE OCR MAKES MISTAKES)")
    print("-" * 92)
    print(
        f" {'Fixture':<8} | {'Confidence':<10} | {'Token CER':<10} | {'Detected Text':<28} | {'Matched GT Substring':<24}"
    )
    print("-" * 92)
    for m in sorted(corrupted_tokens, key=lambda x: x.confidence):
        print(
            f" {m.fixture_id:<8} | {m.confidence:<10.4f} | {m.token_cer * 100:<9.1f}% | {m.token_text:<28} | {m.gt_matched_text:<24}"
        )

    # Threshold Sweep Table
    print("\n" + "=" * 92)
    print(" EMPIRICAL THRESHOLD SWEEP TABLE (PRECISION / RECALL OF ERROR DETECTION)")
    print("=" * 92)
    print(" Condition: Flag token for Tier 2 Retry if Confidence < Threshold (tau)")
    print("-" * 92)
    print(
        f" {'Threshold (tau)':<16} | {'Flagged Tokens':<15} | {'Precision':<11} | {'Recall':<11} | {'F1-Score':<11} | {'False Alarm Rate':<16}"
    )
    print("-" * 92)

    total = len(matches)
    n_corrupt = len(corrupted_tokens)
    n_correct = len(correct_tokens)

    thresholds = [0.40, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.82, 0.85, 0.88, 0.90, 0.92, 0.95]
    for tau in thresholds:
        flagged = [m for m in matches if m.confidence < tau]
        tp = sum(1 for m in flagged if not m.is_correct)
        fp = sum(1 for m in flagged if m.is_correct)
        fn = n_corrupt - tp

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        false_alarm = (fp / n_correct) if n_correct > 0 else 0.0

        print(
            f"  tau < {tau:<10.2f} | {len(flagged):>4} / {total:<8} | {precision * 100:8.1f}% | {recall * 100:8.1f}% | {f1:8.3f}   | {false_alarm * 100:13.1f}%"
        )
    print("=" * 92 + "\n")


def main() -> None:
    matches = run_confidence_diagnostics()
    print_diagnostic_report(matches)


if __name__ == "__main__":
    main()
