from __future__ import annotations


def levenshtein_distance(seq1: str | list[str], seq2: str | list[str]) -> int:
    """Calculate minimum edit distance with O(min(m, n)) space complexity using two rolling rows."""
    if not seq1:
        return len(seq2)
    if not seq2:
        return len(seq1)

    if len(seq1) < len(seq2):
        seq1, seq2 = seq2, seq1

    m, n = len(seq1), len(seq2)
    prev_row = list(range(n + 1))
    curr_row = [0] * (n + 1)

    for i in range(1, m + 1):
        curr_row[0] = i
        elem1 = seq1[i - 1]
        for j in range(1, n + 1):
            cost = 0 if elem1 == seq2[j - 1] else 1
            curr_row[j] = min(
                prev_row[j] + 1,  # deletion
                curr_row[j - 1] + 1,  # insertion
                prev_row[j - 1] + cost,  # substitution
            )

        prev_row, curr_row = curr_row, prev_row
    return prev_row[n]


def compute_cer(reference_text: str, predicted_text: str, ignore_case: bool = False) -> float:
    """Calculate Character Error Rate (CER).
    Formula:
        CER = LevenshteinDistance(reference, predicted) / len(reference)
    """
    if ignore_case:
        reference_text = reference_text.lower()
        predicted_text = predicted_text.lower()

    if not reference_text and not predicted_text:
        return 0.0

    if not reference_text:
        return 1.0

    distance = levenshtein_distance(reference_text, predicted_text)
    return float(distance / len(reference_text))


def compute_wer(reference_text: str, predicted_text: str, ignore_case: bool = False) -> float:
    """Calculate Word Error Rate (WER).
    Formula:
        WER = LevenshteinDistance(reference_words, predicted_words) / len(reference_words)
    """
    if ignore_case:
        reference_text = reference_text.lower()
        predicted_text = predicted_text.lower()

    ref_words = reference_text.strip().split()
    pred_words = predicted_text.strip().split()

    if not ref_words and not pred_words:
        return 0.0

    if not ref_words:
        return 1.0

    distance = levenshtein_distance(ref_words, pred_words)
    return float(distance / len(ref_words))
