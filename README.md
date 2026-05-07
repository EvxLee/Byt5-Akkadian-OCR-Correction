# ByT5 Akkadian OCR Correction

Fine-tuning `google/byt5-small` to fix OCR errors in ancient Akkadian cuneiform transliterations, so digitized academic texts can be ingested into [FactGrid's cuneiform database](https://database.factgrid.de) with fewer manual corrections.

## Running the Pipeline

Steps 1-5 are the same regardless of where you run training.

```bash
# 1. Clone the repo
git clone <this-repo-url> && cd byt5-akkadian-ocr

# 2. Install dependencies
pip install -r requirements.txt
brew install tesseract        # macOS
# apt-get install tesseract-ocr  # Linux

# 3. Gold data is already in the repo
#    data/innaya/   ← Innaya_with_translations_2_2026.csv
#    data/veenhof/  ← chapter .txt files + PDFs
#    data/oare/     ← OARE_no-gaps_3-9-26.csv

# 4. Generate synthetic noisy-gold pairs
python scripts/generate_synthetic_pairs.py
# → writes results/synthetic_pairs.jsonl  (~74k pairs)

# 5. Run Tesseract OCR on Veenhof PDFs
jupyter notebook notebooks/01_boxes_ocr.ipynb
# → writes results/ocr_pairs.jsonl
```

### Option A — Local GPU (cleaner, no upload/download)

Requires an NVIDIA GPU with CUDA. Results write directly to `results/` — no Drive sync needed.

```bash
# 6. Open the training notebook from the repo root
jupyter notebook notebooks/02_finetune_byt5.ipynb
# Run all cells. The notebook detects it is not on Colab and skips Drive mounting.
# → trains model, prints metrics inline
# → writes results/byt5-akkadian/ and results/model_predictions.txt
```

> **Apple Silicon (MPS):** Open `02_finetune_byt5.ipynb` and change `fp16=True` to `fp16=False` in the training args before running — fp16 is not supported on MPS.

### Option B — Google Colab (free T4 GPU)

```bash
# 6. Upload the whole repo folder to Google Drive
#    Also copy results/synthetic_pairs.jsonl and results/ocr_pairs.jsonl into it
#    (they are gitignored and won't be there from git clone)

# 7. Open notebooks/02_finetune_byt5.ipynb in Colab
#    Connect to a T4 GPU runtime
#    Set DRIVE_REPO_PATH in the first cell to match your Drive path
#    Run all cells (~2-4 hours)
# → trains model, prints metrics inline
# → saves results/byt5-akkadian/ and results/model_predictions.txt back to Drive
```

## Dataset Overview

- **18,579** unique gold Akkadian lines across **2,007** tablets
- **74,316** synthetic training pairs generated at 4 noise levels (passthrough / light / medium / heavy)
- Split **by tablet** (80/10/10 train/val/test) to prevent data leakage
- Gold data is human-verified transliteration; noisy data is programmatically corrupted to mimic real OCR errors

| Source | Lines | Tablets |
|---|---|---|
| Innaya archive | 5,920 | 187 |
| OARE corpus | 10,536 | 1,562 |
| Veenhof 2014 | 3,803 | 256 |

## What's Included

### Notebooks

| Notebook | Runs on | What it does |
|---|---|---|
| `01_boxes_ocr.ipynb` | Local (no GPU) | Tesseract OCR on Veenhof PDFs, aligns output to gold lines |
| `02_finetune_byt5.ipynb` | Local GPU or Colab | Loads pairs, tokenizes, fine-tunes ByT5-small, evaluates vs. baseline, saves checkpoint |

### Scripts

- `scripts/generate_synthetic_pairs.py` — corrupts gold lines at multiple noise levels to produce training pairs

### Source Modules (`src/`)

- `parsing/` — loaders for Innaya CSV, OARE CSV, and Veenhof two-column .txt files
- `noise/` — synthetic OCR noise generator (diacritic stripping, character confusables, drops, swaps)
- `alignment/` — fuzzy-matches Tesseract output lines to gold lines using rapidfuzz
- `metrics/` — CER, exact match, chrF++, BLEU

## Project Structure

```
byt5-akkadian-ocr/
├── data/
│   ├── innaya/        ← Innaya CSV
│   ├── veenhof/       ← chapter .txt files + PDFs
│   └── oare/          ← OARE CSV
├── notebooks/
│   ├── 01_boxes_ocr.ipynb
│   └── 02_finetune_byt5.ipynb
├── scripts/
│   └── generate_synthetic_pairs.py
├── src/
│   ├── parsing/
│   ├── noise/
│   ├── alignment/
│   └── metrics/
└── results/               ← generated files, gitignored
    ├── synthetic_pairs.jsonl
    ├── ocr_pairs.jsonl
    ├── test_pairs.jsonl
    ├── model_predictions.txt
    └── byt5-akkadian/     ← model checkpoint
```

## Requirements

- Python 3.10+
- Tesseract binary (`brew install tesseract` on macOS, `apt-get install tesseract-ocr` on Linux/Colab)
- See `requirements.txt` for Python packages

Fine-tuning requires a GPU. `byt5-small` fits in ~6GB VRAM; `byt5-base` is a viable upgrade if compute allows. The training notebook auto-detects whether it is running on Colab or locally and skips Drive mounting accordingly. Apple Silicon users should set `fp16=False` in the training args.

## Acknowledgements

Gold data is drawn from three scholarly sources:

**Innaya archive** — Old Assyrian merchant correspondence from the Innaya archive, Kültepe (ancient Kanesh). Approximately 250 tablets, ~5,920 transliteration lines.

**OARE corpus** — Open Access Research on the Euphrates. A curated no-gaps corpus of Old Assyrian tablet transliterations. Approximately 1,560 tablets across multiple collections.

**Veenhof 2014** — Veenhof, K.R. *Kültepe Tabletleri VIII: The Archive of Elamma son of Iddin-Suen and his Family.* Türk Tarih Kurumu, Ankara, 2014. The Elamma family archive, ~240 tablets, used here with the permission embedded in its academic publication context.

All transliterations are the work of the original scholars. This project applies machine learning to assist in digitization; it does not claim authorship of the underlying philological work.
