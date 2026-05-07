"""
Synthetic OCR noise generator for Akkadian transliterations.

Applies character-level corruption that mirrors real Tesseract errors:
diacritic stripping, OCR confusables, random drops and swaps.

Noise levels:
  light     -- 20% diacritic strip, mimics a good scan
  medium    -- 60% diacritic strip, mimics typical Tesseract on text PDF
  heavy     -- 90% diacritic strip, mimics a bad scan
  passthrough -- 0% corruption, teaches the model not to over-correct clean input
"""

import random
from typing import Optional

# Diacritic substitutions: gold character -> what OCR typically outputs
_DIACRITIC_MAP = {
    "ā": "a", "Ā": "A",
    "ī": "i", "Ī": "I",
    "ū": "u", "Ū": "U",
    "ē": "e", "Ē": "E",
    "š": "s", "Š": "S",
    "ṣ": "s", "Ṣ": "S",
    "ḫ": "h", "Ḫ": "H",
    "ṭ": "t", "Ṭ": "T",
    # Acute/grave accent variants seen in real scans
    "ú": "u", "Ú": "U",
    "á": "a", "Á": "A",
    "é": "e", "É": "E",
    "ì": "i", "Ì": "I",
}

# Visual OCR confusables -- pairs that look alike on a printed page
# Each tuple is (char_a, char_b); substitution goes in a random direction
_VISUAL_CONFUSABLES = [
    ("l", "1"), ("o", "0"), ("I", "l"),
    ("rn", "m"), ("ii", "n"),
    ("c", "e"), ("s", "5"), ("Z", "2"), ("S", "5"),
]

# Named presets: (diacritic_rate, confusable_rate, drop_rate, swap_rate)
NOISE_LEVELS = {
    "passthrough": (0.00, 0.00, 0.000, 0.000),
    "light":       (0.20, 0.03, 0.005, 0.005),
    "medium":      (0.60, 0.05, 0.020, 0.010),
    "heavy":       (0.90, 0.08, 0.040, 0.020),
}


def _apply_diacritics(text: str, rate: float, rng: random.Random) -> str:
    """Strip each diacriticized character with probability `rate`."""
    return "".join(
        _DIACRITIC_MAP[ch] if ch in _DIACRITIC_MAP and rng.random() < rate else ch
        for ch in text
    )


def _apply_confusables(text: str, rate: float, rng: random.Random) -> str:
    """Substitute visually similar character pairs at probability `rate`."""
    for a, b in _VISUAL_CONFUSABLES:
        if rng.random() < rate:
            src, dst = (a, b) if rng.random() < 0.5 else (b, a)
            text = text.replace(src, dst, 1)
    return text


def _apply_drops(text: str, rate: float, rng: random.Random) -> str:
    """Randomly drop individual characters."""
    return "".join(ch for ch in text if rng.random() > rate)


def _apply_swaps(text: str, rate: float, rng: random.Random) -> str:
    """Randomly transpose adjacent characters."""
    chars = list(text)
    for i in range(len(chars) - 1):
        if rng.random() < rate:
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
    return "".join(chars)


def corrupt(
    text: str,
    diacritic_rate: float = 0.6,
    confusable_rate: float = 0.05,
    drop_rate: float = 0.02,
    swap_rate: float = 0.01,
    seed: Optional[int] = None,
) -> str:
    """
    Apply synthetic OCR noise to a single clean Akkadian line.

    Parameters match NOISE_LEVELS presets -- prefer using corrupt_at_level()
    unless you need fine-grained control.
    """
    rng = random.Random(seed)
    text = _apply_diacritics(text, diacritic_rate, rng)
    text = _apply_confusables(text, confusable_rate, rng)
    text = _apply_drops(text, drop_rate, rng)
    text = _apply_swaps(text, swap_rate, rng)
    return text


def corrupt_at_level(text: str, level: str, seed: Optional[int] = None) -> str:
    """Corrupt `text` using a named noise preset. Level must be in NOISE_LEVELS."""
    d, c, dr, sw = NOISE_LEVELS[level]
    return corrupt(text, diacritic_rate=d, confusable_rate=c, drop_rate=dr, swap_rate=sw, seed=seed)


def generate_pairs(
    gold_lines: list[str],
    levels: tuple[str, ...] = ("light", "medium", "heavy", "passthrough"),
    seed_offset: int = 0,
) -> list[tuple[str, str, str]]:
    """
    Generate (noisy, gold, level) triples from a list of clean gold lines.

    For each gold line, one noisy version is produced per level in `levels`.
    Passthrough pairs have noisy == gold and teach the model not to over-correct.

    Returns a flat list of (noisy, gold, level) triples.
    """
    pairs = []
    for i, line in enumerate(gold_lines):
        for level in levels:
            noisy = corrupt_at_level(line, level, seed=seed_offset + i)
            pairs.append((noisy, line, level))
    return pairs
