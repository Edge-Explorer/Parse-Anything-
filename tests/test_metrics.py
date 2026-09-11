from __future__ import annotations

import pytest

from benchmarks.metrics.ocr_eval import compute_cer, compute_wer, levenshtein_distance
from benchmarks.metrics.teds import TEDS


def test_levenshtein_distance_strings():
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("flaw", "lawn") == 2
    assert levenshtein_distance("", "abc") == 3
    assert levenshtein_distance("abc", "") == 3
    assert levenshtein_distance("same", "same") == 0


def test_levenshtein_distance_words():
    ref = ["the", "quick", "brown", "fox"]
    pred = ["the", "fast", "brown", "fox"]
    assert levenshtein_distance(ref, pred) == 1


def test_compute_cer():
    ref = "Invoice Number: 10428"
    pred = "Invoice Number: 10428"
    assert compute_cer(ref, pred) == 0.0

    # 1 substitution in 10 chars
    assert compute_cer("abcdefghij", "abcxefghij") == pytest.approx(0.1, abs=1e-4)

    # Empty cases
    assert compute_cer("", "") == 0.0
    assert compute_cer("hello", "") == 1.0


def test_compute_wer():
    ref = "Quarterly Revenue was 5 million dollars"
    pred = "Quarterly Revenue was 4 million dollars"
    assert compute_wer(ref, pred) == pytest.approx(1 / 6, abs=1e-4)

    assert compute_wer("single", "single") == 0.0
    assert compute_wer("", "") == 0.0


def test_teds_identical_table():
    html = """
    <table>
        <thead>
            <tr><th>Item</th><th>Price</th></tr>
        </thead>
        <tbody>
            <tr><td>Apple</td><td>$1.00</td></tr>
            <tr><td>Banana</td><td>$0.50</td></tr>
        </tbody>
    </table>
    """
    teds = TEDS()
    score = teds.evaluate(html, html)
    assert score == pytest.approx(1.0, abs=1e-4)


def test_teds_structural_difference():
    # Table with 2 columns vs 3 columns
    table_a = "<table><tr><td>A</td><td>B</td></tr></table>"
    table_b = "<table><tr><td>A</td><td>B</td><td>C</td></tr></table>"

    teds = TEDS(structure_only=True)
    score = teds.evaluate(table_a, table_b)
    assert 0.0 < score < 1.0
