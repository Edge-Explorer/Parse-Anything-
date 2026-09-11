from __future__ import annotations

from benchmarks.metrics.ocr_eval import compute_cer, compute_wer, levenshtein_distance
from benchmarks.metrics.teds import TEDS, TableTree

__all__ = [
    "TEDS",
    "TableTree",
    "compute_cer",
    "compute_wer",
    "levenshtein_distance",
]
