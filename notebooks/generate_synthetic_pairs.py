"""
Generate synthetic noisy-gold training pairs from all gold data sources.

Produces results/synthetic_pairs.jsonl — one JSON object per line:
  {"noisy": "...", "gold": "...", "level": "medium", "source": "innaya", "tablet_id": "..."}

Run from the repo root:
  python notebooks/generate_synthetic_pairs.py
"""

import json
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from src.parsing.innaya_loader import load_innaya
from src.parsing.oare_loader import load_oare
from src.parsing.veenhof_parser import parse_all_chapters
from src.noise.synthetic import generate_pairs, NOISE_LEVELS

DATA_DIR    = Path("data")
OUTPUT_PATH = Path("results/synthetic_pairs.jsonl")
OUTPUT_PATH.parent.mkdir(exist_ok=True)

SPLIT_SEED  = 42
NOISE_SEED  = 0
# Noise levels to generate per gold line
LEVELS = ("passthrough", "light", "medium", "heavy")


def main():
    # ── 1. Load and pool gold data ────────────────────────────────────────────
    print("Loading gold data...")
    innaya  = load_innaya(DATA_DIR / "innaya" / "Innaya_with_translations_2_2026.csv")
    oare    = load_oare(DATA_DIR / "oare" / "OARE_no-gaps_3-9-26.csv")
    veenhof = parse_all_chapters(DATA_DIR / "veenhof")

    gold_df = pd.concat([innaya, oare, veenhof], ignore_index=True)
    gold_df = gold_df.drop_duplicates(subset="akkadian_gold").reset_index(drop=True)
    print(f"Total unique gold lines: {len(gold_df)}")
    for src, grp in gold_df.groupby("source"):
        print(f"  {src}: {len(grp)} lines, {grp.tablet_id.nunique()} tablets")

    # ── 2. Train / val / test split BY TABLET ────────────────────────────────
    print("\nSplitting by tablet (80/10/10)...")
    tablets = gold_df["tablet_id"].unique().tolist()
    rng = random.Random(SPLIT_SEED)
    rng.shuffle(tablets)

    n = len(tablets)
    train_t = set(tablets[:int(0.8 * n)])
    val_t   = set(tablets[int(0.8 * n):int(0.9 * n)])
    test_t  = set(tablets[int(0.9 * n):])

    splits = {
        "train": gold_df[gold_df.tablet_id.isin(train_t)],
        "val":   gold_df[gold_df.tablet_id.isin(val_t)],
        "test":  gold_df[gold_df.tablet_id.isin(test_t)],
    }
    for split, df in splits.items():
        print(f"  {split}: {len(df)} lines, {df.tablet_id.nunique()} tablets")

    # ── 3. Generate noisy pairs ───────────────────────────────────────────────
    print(f"\nGenerating noisy pairs at levels: {LEVELS}")
    all_records = []

    for split_name, split_df in splits.items():
        gold_lines = split_df["akkadian_gold"].tolist()
        sources    = split_df["source"].tolist()
        tablet_ids = split_df["tablet_id"].tolist()

        pairs = generate_pairs(gold_lines, levels=LEVELS, seed_offset=NOISE_SEED)

        # generate_pairs returns: for each line, all levels in order.
        # So interleave sources/tablet_ids to match: [s0,s0,...,s1,s1,...].
        sources_exp    = [s for s in sources    for _ in LEVELS]
        tablet_ids_exp = [t for t in tablet_ids for _ in LEVELS]

        for (noisy, gold, level), source, tablet_id in zip(pairs, sources_exp, tablet_ids_exp):
            all_records.append({
                "noisy":     noisy,
                "gold":      gold,
                "level":     level,
                "split":     split_name,
                "source":    source,
                "tablet_id": tablet_id,
            })

    # ── 4. Save ───────────────────────────────────────────────────────────────
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nSaved {len(all_records)} pairs to {OUTPUT_PATH}")
    by_split  = {s: sum(1 for r in all_records if r["split"] == s) for s in ("train", "val", "test")}
    by_level  = {l: sum(1 for r in all_records if r["level"] == l) for l in LEVELS}
    print(f"  By split: {by_split}")
    print(f"  By level: {by_level}")

    # ── 5. Print sample pairs for manual inspection ───────────────────────────
    print("\n── SAMPLE PAIRS (medium noise, 10 random) ──")
    medium_pairs = [r for r in all_records if r["level"] == "medium" and r["split"] == "train"]
    sample = rng.sample(medium_pairs, min(10, len(medium_pairs)))
    for rec in sample:
        print(f"  source : {rec['source']}")
        print(f"  gold   : {rec['gold']}")
        print(f"  noisy  : {rec['noisy']}")
        print()


if __name__ == "__main__":
    main()
