"""
Load and clean the OARE no-gaps CSV gold data.

The OARE_no-gaps CSV has these columns:
  'Transliteration' — the Akkadian cuneiform transliteration (what we want)
  'Translation'     — English (skip)
  'Unnamed: 0'      — row index (use as tablet_id)

Each row is a WHOLE TABLET's transliteration as one long string (~500-600 chars).
We chunk these into line-sized segments (~70 chars) to match Innaya/Veenhof granularity.
"""

import re
import pandas as pd
from pathlib import Path

AKKADIAN_COL = "Transliteration"
CHUNK_TARGET = 70  # target chars per chunk; splits on word boundaries


def _chunk_tablet(text: str, target: int = CHUNK_TARGET) -> list[str]:
    """
    Split a long tablet transliteration into line-sized chunks.
    Splits on word boundaries, keeping chunks close to `target` chars.
    """
    words = text.split()
    chunks = []
    current: list[str] = []
    length = 0
    for word in words:
        if length + len(word) + 1 > target and current:
            chunks.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def load_oare(
    csv_path: str | Path,
    akkadian_col: str = AKKADIAN_COL,
) -> pd.DataFrame:
    """
    Returns a DataFrame with columns: source, tablet_id, line_id, akkadian_gold.
    Each row is a chunk of one tablet (~70 chars).
    Prints the actual columns found so you can catch header mismatches early.
    """
    df = pd.read_csv(csv_path, dtype=str)
    print(f"OARE columns found: {list(df.columns)}")

    if akkadian_col not in df.columns:
        raise ValueError(
            f"Column '{akkadian_col}' not found. "
            f"Available: {list(df.columns)}. "
            f"Pass akkadian_col='<correct name>' to fix."
        )

    df = df.dropna(subset=[akkadian_col])
    df = df[df[akkadian_col].str.strip() != ""]

    records = []
    for tablet_idx, row in df.iterrows():
        text = row[akkadian_col].strip()
        chunks = _chunk_tablet(text)
        for chunk_idx, chunk in enumerate(chunks):
            records.append({
                "source": "oare",
                "tablet_id": f"oare_{tablet_idx:04d}",
                "line_id": f"oare_{tablet_idx:04d}_{chunk_idx:03d}",
                "akkadian_gold": chunk,
            })

    return pd.DataFrame(records).reset_index(drop=True)
