from __future__ import annotations

from typing import List, Union


def levenshtein_distance(seq1: Union[str, List[str]], seq2: Union[str, List[str]]) -> int:
    """Calculate minimum edit distance (Levenshtein) between two strings or token sequences.
    
    Supports both character strings (for CER) and word lists (for WER).
    """
    if not seq1:
        return len(seq2)
    if not seq2:
        return len(seq1)
    
    m, n = len(seq1), len(seq2)
    dp= [[0] * (n+1) for _ in range(m+1)]
    
    for i in range(m+1):
        dp[i][0]= i
    for j in range(n+1):
        dp[0][j]= j
        
    for i in range(1, m+1):
        for j in range(1, n+1):
            cost= 0 if seq1[i-1]== seq2[j-1] else 1
            dp[i][j]= min(
                dp[i-1][j] + 1,         # deletion
                dp[i][j-1] + 1,         # insertion
                dp[i-1][j-1] + cost     # substitution
            )
    return dp[m][n]

def compute_cer(reference_text: str, predicted_text: str, ignore_case: bool = False) -> float:
    """Calculate Character Error Rate (CER).
    Formula:
        CER = LevenshteinDistance(reference, predicted) / len(reference)
    """
    if ignore_case:
        reference_text= reference_text.lower()
        predicted_text= predicted_text.lower()
        
    if not reference_text and not predicted_text:
        return 0.0
    
    if not reference_text:
        return 1.0
    
    distance= levenshtein_distance(reference_text, predicted_text)
    return float(distance / len(reference_text))


def compute_wer(reference_text: str, predicted_text: str, ignore_case: bool = False) -> float:
    """Calculate Word Error Rate (WER).
    Formula:
        WER = LevenshteinDistance(reference_words, predicted_words) / len(reference_words)
    """
    if ignore_case:
        reference_text= reference_text.lower()
        predicted_text= predicted_text.lower()
        
    ref_words= reference_text.strip().split()
    pred_words= predicted_text.strip().split()
    
    if not ref_words and not pred_words:
        return 0.0
    
    if not ref_words:
        return 1.0
    
    distance= levenshtein_distance(ref_words, pred_words)
    return float(distance / len(ref_words))
