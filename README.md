# ByT5 Akkadian OCR Correction

Fine-tuning `google/byt5-small` to correct OCR errors in ancient Akkadian cuneiform transliterations. Target use case: cleaning OCR'd output from old academic publications before ingestion into [FactGrid's cuneiform database](https://database.factgrid.de).

## Repo layout

```
byt5-akkadian-ocr/
├── data/
│   ├── gold/
│   │   ├── innaya/       ← Innaya_with_translations_2_2026.csv
│   │   ├── veenhof/      ← 14 chapter .txt files + PDFs
│   │   └── oare/         ← OARE_no-gaps_3-9-26.csv
│   └── README.md
├── notebooks/
│   ├── 01_boxes_ocr.ipynb     ← Tesseract pipeline
│   ├── 02_evaluation.ipynb    ← BLEU / chrF++ / CER
│   └── 03_finetune_byt5.ipynb ← end-to-end training
├── src/
│   ├── parsing/         ← loaders for Innaya, OARE, Veenhof
│   ├── noise/           ← synthetic OCR noise generator
│   ├── alignment/       ← Tesseract output → gold line matching
│   └── metrics/         ← CER, exact match, chrF++, BLEU
└── results/             ← checkpoints, eval logs (gitignored)
```

## Roadmap

### Stage 1 — Data ingestion (unblocker)
- [ ] Drop gold files into `data/gold/{innaya,veenhof,oare}/`
- [ ] Verify `src/parsing/innaya_loader.py` on the Innaya CSV
- [ ] Run `src/parsing/veenhof_parser.py` on the 14 chapter .txt files; audit output for false positives (English prose leaking in) and missed Akkadian lines
- [ ] Verify `src/parsing/oare_loader.py` -- check actual column names in OARE CSV and adjust `AKKADIAN_COL` constant if needed
- [ ] Pool all three sources into one DataFrame; deduplicate on `akkadian_gold`

### Stage 2 — Noise generation
- [ ] **Synthetic (fast, do this first):** `src/noise/synthetic.py` is ready. Run `generate_pairs()` on all gold lines; inspect ~50 pairs to confirm the noise looks realistic
- [ ] Tune `diacritic_rate` (currently 0.6) if the synthetic noise is too aggressive or too mild compared to real Tesseract output
- [ ] **Tesseract (optional, adds structural errors):** run `notebooks/01_boxes_ocr.ipynb` on the Veenhof PDFs; check alignment yield -- if below ~50%, the PDF layout may need tuning

### Stage 3 — Train/val/test split
- [ ] Split **by tablet ID**, not by line (already wired in `03_finetune_byt5.ipynb`)
- [ ] Confirm no tablet leaks across splits

### Stage 4 — Fine-tuning
- [ ] Upload repo (or just `src/` + `notebooks/03_finetune_byt5.ipynb`) to Colab
- [ ] Mount Drive or upload gold CSVs/txts directly
- [ ] Run the training cell; ~5 epochs on T4 should take 1-3 hours depending on dataset size
- [ ] Save best checkpoint to Drive

### Stage 5 — Evaluation
- [ ] Run `notebooks/02_evaluation.ipynb` on the held-out test set
- [ ] **Compute baseline first** (noisy input vs gold, no model). Model must beat this to be useful.
- [ ] Report CER, exact match, chrF++, BLEU

## Install (local dev / testing)

```bash
pip install -r requirements.txt
```

Tesseract binary also needed for OCR notebook:
```bash
# macOS
brew install tesseract
# Ubuntu / Colab
apt-get install tesseract-ocr
```

## Key design decisions

- **Byte-level model (ByT5):** sidesteps tokenizer-vocabulary problems with Akkadian diacritics (`ā`, `š`, `ṣ`, `ḫ`, etc.)
- **Split by tablet, not line:** lines from the same tablet share vocabulary; line-level split leaks data
- **Synthetic noise as primary path:** Tesseract alignment is supplemental -- synthetic pairs are faster to generate and fully controllable
- **CER is the primary metric:** it's the most informative for character-level OCR correction tasks
