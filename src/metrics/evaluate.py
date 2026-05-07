"""
Evaluation metrics for the OCR correction task.

All functions accept lists of strings (predictions and references).
"""

from __future__ import annotations

import Levenshtein
import sacrebleu


def exact_match(predictions: list[str], references: list[str]) -> float:
    """Fraction of predictions that exactly match their reference."""
    assert len(predictions) == len(references)
    correct = sum(p == r for p, r in zip(predictions, references))
    return correct / len(predictions)


def character_error_rate(predictions: list[str], references: list[str]) -> float:
    """
    Mean CER = mean(Levenshtein distance / len(reference)) across all pairs.
    A CER of 0.0 is perfect; higher is worse.
    """
    assert len(predictions) == len(references)
    scores = []
    for p, r in zip(predictions, references):
        if len(r) == 0:
            continue
        scores.append(Levenshtein.distance(p, r) / len(r))
    return sum(scores) / len(scores) if scores else 0.0


def chrf_score(predictions: list[str], references: list[str]) -> float:
    """chrF++ score (sacrebleu). Higher is better, max 100."""
    result = sacrebleu.corpus_chrf(predictions, [references], word_order=2)
    return result.score


def bleu_score(predictions: list[str], references: list[str]) -> float:
    """Corpus BLEU (sacrebleu). Higher is better."""
    result = sacrebleu.corpus_bleu(predictions, [references])
    return result.score


def full_report(
    predictions: list[str],
    references: list[str],
    label: str = "model",
) -> dict[str, float]:
    """
    Compute all metrics and return a dict. Pass noisy input as `predictions`
    with the same `references` to get the baseline score.
    """
    return {
        "label": label,
        "exact_match": exact_match(predictions, references),
        "cer": character_error_rate(predictions, references),
        "chrf": chrf_score(predictions, references),
        "bleu": bleu_score(predictions, references),
    }
