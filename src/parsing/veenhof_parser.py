"""
Parser for Veenhof 2014 Kültepe Tabletleri VIII chapter .txt files.

Each file has a two-column layout: Akkadian text (left) and English translation
(right), separated by two or more spaces or a tab. Lines that are commentary,
section headers, footnotes, or purely English prose are skipped.
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd

# Matches tablet headers like "1. Kt 91/k 347 (1-204-91)" or "145. Kt 91/k 424 (1-277-91)"
_TABLET_HEADER = re.compile(
    r"^\d{1,3}\.\s+Kt\s+\S+", re.IGNORECASE
)

# Standalone face markers and section labels -- skip when they appear alone on a line.
_SKIP_EXACT = {
    "obv.", "rev.", "l.e.", "u.e.", "r.e.", "le.", "lo.e.", "le.e.", "ri.e.",
    "notes", "note", "comment", "seals", "seal a", "seal b", "seal c", "seal d",
    "text", "s",
}

# Sections that begin commentary -- skip everything until the next tablet header.
_NOTES_SECTION_TRIGGERS = {"notes", "comment", "note"}

# Minimum character length for a line to be accepted as Akkadian.
_MIN_LINE_LEN = 8

# Known Akkadian diacritics -- presence is a positive signal for Akkadian lines.
_AKKADIAN_CHARS = set("āīūēṣšḫṭḷÀàÁáÂâÃãĀāĒēĪīŌōŪūŠšṢṣḪḫṬṭ")

# Column separator: Akkadian tokens are separated by 2 spaces; the gap between
# the Akkadian column and the English column is 6+ spaces. Split there only.
_COL_SPLIT = re.compile(r"\t| {6,}")

# Smart quotes and other Word artifacts.
_WORD_JUNK = str.maketrans({
    "‘": "'", "’": "'",
    "“": '"', "”": '"',
    "­": "",   # soft hyphen
    " ": " ",  # non-breaking space
})


def _normalize(text: str) -> str:
    text = text.translate(_WORD_JUNK)
    text = unicodedata.normalize("NFC", text)
    return text.strip()


_ENGLISH_SIGNALS = frozenset({
    "the", "of", "and", "to", "a", "in", "is", "that", "this", "with", "for",
    "was", "were", "are", "be", "have", "had", "been", "which", "from", "it",
    "an", "as", "at", "by", "on", "or", "he", "she", "we", "they",
})


def _is_akkadian_line(text: str) -> bool:
    """Heuristic: line looks like an Akkadian transliteration."""
    if len(text) < _MIN_LINE_LEN:
        return False
    # Reject pure numerals / punctuation.
    if re.fullmatch(r"[\d\s\.\-:]+", text):
        return False
    # Long lines with 3+ English function words are prose, even if they mention
    # Akkadian place names (e.g. "Wahšušana") which contain diacritics.
    words = text.split()
    if len(words) > 10:
        word_set = {w.lower().rstrip(",.;:()") for w in words}
        if len(word_set & _ENGLISH_SIGNALS) >= 3:
            return False
    return True


def _extract_tablet_id(filename: str) -> str:
    """Pull a short chapter ID from the filename, e.g. '4. I. Six Basic Documents, 1-6.txt' -> 'veenhof_ch04'."""
    stem = Path(filename).stem
    match = re.match(r"(\d+)", stem)
    chapter = match.group(1) if match else stem
    return f"veenhof_ch{int(chapter):02d}"


def parse_chapter_file(filepath: str | Path) -> pd.DataFrame:
    """
    Parse a single Veenhof chapter .txt file.

    Returns DataFrame with columns: source, tablet_id, line_id, akkadian_gold.
    """
    filepath = Path(filepath)
    chapter_id = _extract_tablet_id(filepath.name)
    records = []
    current_tablet = chapter_id
    line_counter = 0
    in_notes_section = False  # True after "Notes" header; reset on next tablet header

    with open(filepath, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = _normalize(raw)

            if not line:
                continue

            lower = line.lower().rstrip(".")

            # A new tablet header resets the notes-section flag.
            if _TABLET_HEADER.match(line):
                current_tablet = f"{chapter_id}_{line}"
                in_notes_section = False
                continue

            # Entering the Notes / Comment section for the current tablet -- skip until next tablet.
            if lower in _NOTES_SECTION_TRIGGERS or lower.startswith("notes") or lower.startswith("comment"):
                in_notes_section = True
                continue

            if in_notes_section:
                continue

            # Skip standalone face markers, seal labels, and other known junk.
            if lower in _SKIP_EXACT:
                continue

            # Split at the column boundary (6+ spaces or tab).
            parts = _COL_SPLIT.split(line, maxsplit=1)
            candidate = parts[0].strip()

            # Strip leading face markers and line numbers from the Akkadian candidate.
            candidate = re.sub(r"^(?:obv\.|rev\.|l\.e\.|u\.e\.|r\.e\.|le\.e\.|ri\.e\.)\s*", "", candidate, flags=re.IGNORECASE)
            candidate = re.sub(r"^\d{1,3}['.\s]+", "", candidate).strip()

            if _is_akkadian_line(candidate):
                records.append({
                    "source": "veenhof",
                    "tablet_id": current_tablet,
                    "line_id": f"{chapter_id}_{line_counter:05d}",
                    "akkadian_gold": candidate,
                })
                line_counter += 1

    return pd.DataFrame(records)


def parse_all_chapters(veenhof_dir: str | Path) -> pd.DataFrame:
    """
    Parse all chapter .txt files in veenhof_dir and return a single pooled DataFrame.
    Skips files whose names match known non-chapter metadata files.
    """
    veenhof_dir = Path(veenhof_dir)
    # Files 1, 2, 3 are metadata -- skip them. All others are chapter data.
    skip_patterns = {
        "preliminary", "preface", "introduction", "translation", "bibliograph"
    }
    frames = []
    # Covers both .txt and .docx.txt (chapters 10 and 16 were exported as .docx)
    txt_files = list(veenhof_dir.glob("*.txt"))
    for txt in sorted(txt_files):
        if any(p in txt.name.lower() for p in skip_patterns):
            continue
        df = parse_chapter_file(txt)
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame(columns=["source", "tablet_id", "line_id", "akkadian_gold"])
    return pd.concat(frames, ignore_index=True)
