"""
Align Tesseract OCR output lines to gold transliteration lines.

Uses rapidfuzz token_set_ratio for robustness against word-order drift
and merged/split tokens. Pairs below `min_score` are discarded.
"""

from __future__ import annotations

from rapidfuzz import fuzz, process

DEFAULT_MIN_SCORE = 60  # below this, the OCR line is too garbled to trust


def align_ocr_to_gold(
    ocr_lines: list[str],
    gold_lines: list[str],
    min_score: float = DEFAULT_MIN_SCORE,
) -> list[tuple[str, str, float]]:
    """
    For each gold line, find the best-matching OCR line.

    Returns a list of (ocr_line, gold_line, score) tuples for pairs that
    meet `min_score`. Each OCR line is consumed at most once.
    """
    remaining = list(enumerate(ocr_lines))  # (original_idx, text)
    pairs: list[tuple[str, str, float]] = []

    for gold in gold_lines:
        if not remaining:
            break

        texts = [t for _, t in remaining]
        result = process.extractOne(
            gold,
            texts,
            scorer=fuzz.token_set_ratio,
        )
        if result is None:
            continue

        best_text, score, best_pos = result
        if score < min_score:
            continue

        original_idx = remaining[best_pos][0]
        pairs.append((best_text, gold, score))
        remaining.pop(best_pos)

    return pairs


def pairs_to_lists(
    aligned: list[tuple[str, str, float]],
) -> tuple[list[str], list[str]]:
    """Unzip aligned pairs into (noisy_list, gold_list)."""
    noisy = [a[0] for a in aligned]
    gold = [a[1] for a in aligned]
    return noisy, gold
