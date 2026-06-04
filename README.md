# ByT5 Akkadian OCR Correction

Fine-tuning `google/byt5-small` to fix OCR errors in ancient Akkadian cuneiform transliterations, so digitized academic texts can be ingested into [FactGrid's cuneiform database](https://database.factgrid.de) with fewer manual corrections.

**[Full Project Report and Findings →](https://app.notion.com/p/Byt5-Akkadian-OCR-Correction-Report-375a5f597a88806a8084cda056e7f6a4?source=copy_link)**

---

## Results

| Metric | Baseline (no model) | ByT5-small fine-tuned |
|---|---|---|
| Exact match | 0.366 | **0.724** |
| CER (lower = better) | 0.066 | **0.017** |
| chrF++ | 76.94 | **95.40** |
| BLEU | 62.17 | **90.32** |

---

## Running the Pipeline

The full pipeline takes **2-3 hours** end to end. Steps 1-5 run locally (no GPU needed). Step 6 requires a GPU.

```bash
# 1. Clone the repo
git clone <this-repo-url> && cd Byt5-Akkadian-OCR-Correction

# 2. Install dependencies
pip install -r requirements.txt
brew install tesseract        # macOS
# apt-get install tesseract-ocr  # Linux

# 3. Gold data is already in the repo
#    data/innaya/   ← Innaya_with_translations_2_2026.csv
#    data/veenhof/  ← chapter .txt files + PDFs
#    data/oare/     ← OARE_no-gaps_3-9-26.csv

# 4. Generate synthetic noisy-gold pairs  (~2 min)
python notebooks/generate_synthetic_pairs.py
# → writes results/synthetic_pairs.jsonl  (~74k pairs)

# 5. Run Tesseract OCR on Veenhof PDFs  (~20 min)
jupyter notebook notebooks/boxes_ocr.ipynb
# → writes results/ocr_pairs.jsonl
```

### Option A — Google Colab (recommended)

**Use an A100 GPU with High RAM runtime** — training takes ~1.5 hours. T4 works but takes ~3 hours.

> **Important:** After connecting the runtime, verify the GPU is live before running anything:
> ```python
> import torch
> print(torch.cuda.is_available())       # must be True
> print(torch.cuda.get_device_name(0))   # should say A100
> ```
> If `False`, disconnect the runtime and reconnect — Colab sometimes attaches a session without initializing the GPU.

```
1. Open notebooks/finetune_byt5.ipynb in Colab
2. Select Runtime → Change runtime type → A100 GPU, High RAM
3. Paste your GitHub repo URL into GITHUB_REPO_URL in the Setup cell
4. Run the Setup cell — the repo clones automatically
5. Run the Upload cell — click "Choose Files" and select both:
     results/synthetic_pairs.jsonl
     results/ocr_pairs.jsonl
6. Run all remaining cells
   → trains model, prints metrics inline (~1.5 hrs on A100)
   → writes results/byt5-akkadian/ checkpoint to the Colab session
```

> **Save your checkpoint** before the session ends — Colab sessions are temporary. Download `results/byt5-akkadian/` from the file sidebar.

### Option B — Local GPU

Requires an NVIDIA GPU with CUDA. Results write directly to `results/` — no upload needed.

```bash
# From the repo root:
jupyter notebook notebooks/finetune_byt5.ipynb
# Run all cells — the notebook detects it is not on Colab and skips file upload.
# → trains model, prints metrics inline
# → writes results/byt5-akkadian/ and results/model_predictions.txt
```

---

## Dataset Overview

- **18,579** unique gold Akkadian lines across **2,005** tablets
- **74,316** synthetic training pairs at 4 noise levels (passthrough / light / medium / heavy)
- **2,671** real OCR pairs from Tesseract on Veenhof PDFs
- Split **by tablet** (80/10/10 train/val/test) to prevent data leakage

| Source | Lines | Tablets |
|---|---|---|
| Innaya archive | 5,920 | 187 |
| OARE corpus | 10,536 | 1,562 |
| Veenhof 2014 | 3,803 | 256 |

---

## What's Included

| File | Runs on | What it does |
|---|---|---|
| `notebooks/generate_synthetic_pairs.py` | Local | Corrupts gold lines at 4 noise levels to produce training pairs |
| `notebooks/boxes_ocr.ipynb` | Local (no GPU) | Tesseract OCR on Veenhof PDFs, aligns to gold lines |
| `notebooks/finetune_byt5.ipynb` | Colab A100 or local GPU | Tokenizes, trains, evaluates, saves checkpoint |

### Source Modules (`src/`)

- `parsing/` — loaders for Innaya CSV, OARE CSV, and Veenhof two-column .txt files
- `noise/` — synthetic OCR noise generator (diacritic stripping, confusables, drops, swaps)
- `alignment/` — fuzzy-matches Tesseract output lines to gold lines using rapidfuzz
- `metrics/` — CER, exact match, chrF++, BLEU

---

## Project Structure

```
Byt5-Akkadian-OCR-Correction/
├── data/
│   ├── innaya/        ← Innaya CSV
│   ├── veenhof/       ← chapter .txt files + PDFs
│   └── oare/          ← OARE CSV
├── notebooks/
│   ├── boxes_ocr.ipynb
│   ├── finetune_byt5.ipynb
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

---

## Requirements

- Python 3.10+
- Tesseract binary (`brew install tesseract` on macOS, `apt-get install tesseract-ocr` on Linux)
- See `requirements.txt` for Python packages
- GPU for fine-tuning: A100 recommended (80GB VRAM), T4 minimum (15GB)

---

## Acknowledgements

Gold data is drawn from three scholarly sources:

**Innaya archive** — Old Assyrian merchant correspondence from the Innaya archive, Kültepe (ancient Kanesh). Approximately 250 tablets, ~5,920 transliteration lines.

**OARE corpus** — Open Access Research on the Euphrates. A curated no-gaps corpus of Old Assyrian tablet transliterations. Approximately 1,560 tablets across multiple collections.

**Veenhof 2014** — Veenhof, K.R. *Kültepe Tabletleri VIII: The Archive of Elamma son of Iddin-Suen and his Family.* Türk Tarih Kurumu, Ankara, 2014. The Elamma family archive, ~240 tablets, used here with the permission embedded in its academic publication context.

All transliterations are the work of the original scholars. This project applies machine learning to assist in digitization; it does not claim authorship of the underlying philological work.
