"""Load and clean the Innaya CSV gold data."""

import pandas as pd
from pathlib import Path


def load_innaya(csv_path: str | Path) -> pd.DataFrame:
    """
    Returns a DataFrame with columns: source, tablet_id, line_id, akkadian_gold.
    Drops rows where akkadian_line is null or empty.
    """
    df = pd.read_csv(csv_path, dtype=str)
    df = df.dropna(subset=["akkadian_line"])
    df = df[df["akkadian_line"].str.strip() != ""]

    out = pd.DataFrame({
        "source": "innaya",
        "tablet_id": "innaya_" + df["No."].str.strip(),  # No. = tablet number (251 unique tablets)
        "line_id": df["label_line"].str.strip(),          # label_line = "BIN 6 90  3" (unique per line)
        "akkadian_gold": df["akkadian_line"].str.strip(),
    })
    return out.reset_index(drop=True)
