# CLAUDE.md

Project context for fine-tuning a ByT5 model to correct OCR errors in ancient Akkadian transliterations. This file gives Claude Code the full background needed to help build the training pipeline.

## Project goal

Fine-tune a ByT5 model that takes garbled OCR text of Akkadian cuneiform transliterations as input and outputs the corrected, scholar-verified transliteration.

End user: FactGrid's linked cuneiform language database. Once trained, the model cleans up OCR'd transliterations from old academic publications so they can be ingested into the database with fewer human corrections.

## Domain background (one-paragraph version)

Ancient Mesopotamian scribes wrote on clay tablets in cuneiform script. Modern Assyriologists "transliterate" cuneiform into Latin characters with diacritics (e.g. `a-na I-na-a`, `Aššur-nādā`). Many transliterations exist only in printed academic books, and when those books are scanned and OCR'd, the special characters (`ā`, `š`, `ṣ`, `ḫ`, `ú`, etc.) get butchered. The job is to train a model to undo that butchering.

## Why ByT5 specifically

ByT5 reads input byte-by-byte instead of word-by-word. This matters because Akkadian transliterations contain unusual Unicode characters that standard tokenizers fragment poorly. Byte-level reading sidesteps the tokenizer-vocabulary problem entirely. We use `google/byt5-small` as the base; `byt5-base` is an upgrade if compute allows.

## The core data problem

To fine-tune we need **paired data**: noisy OCR text on one side, correct gold text on the other. The model learns the mapping.

- Gold text: PLENTIFUL. We have it.
- Noisy OCR text: MISSING. Has to be generated.

This is the central blocker the pipeline must solve.

## What's actually in the data folder

### Gold data (clean, human-verified Akkadian transliterations)

| File | Source | Tablets | Notes |
|---|---|---|---|
| `Innaya_with_translations_2_2026.csv` | Innaya archive | ~250 | Already structured: `No., label_line, akkadian_line, french_line, english_line`. ~5,920 non-empty Akkadian lines. The cleanest source. |
| `4__I__Six_Basic_Documents__1-6__1_.txt` through `17__XIV__S_u-Is_tar__235-245.txt` | Veenhof 2014, *Kültepe Tabletleri VIII* (Elamma archive) | ~240 across 14 chapter files | Two-column format: Akkadian text on left, English translation on right, separated by tabs/spaces, mixed with footnotes and commentary. **Requires custom parser.** |
| `OARE_no-gaps_3-9-26.csv` | OARE corpus | ~1,500 lines | "no-gaps" means bracket reconstructions filled in. Slightly different formatting convention from Innaya. |

Combined potential: ~490 tablets / 7,000+ Akkadian lines after deduplication and parsing.

### Reference / metadata only — DO NOT train on

| File | Why skip |
|---|---|
| `1___Preliminary_pages.txt` | Title page only |
| `2___Preface__contents__bibliogr__concord_docx.txt` | TOC and bibliography |
| `3__Introduction.txt` | English prose commentary |
| `Innaya_Vol_2_Translations.txt` | Duplicates Innaya's translation columns |
| `RlA_Bibliograph_2026.csv` | German bibliography reference |

### Tooling notebooks (reference, not data)

| File | Purpose |
|---|---|
| `Copy_of_Boxes.ipynb` | Tesseract OCR pipeline. Takes PDF input, returns predicted text + bounding boxes. Useful for generating noisy text from PDFs of the source publications. |
| `Copy_of_BLEU_CHRF_result.ipynb` | Reference code for BLEU and chrF++ metric calculation. The original notebook compares English translations; we'll reuse the metric calls but compare predicted vs gold Akkadian instead. |

### PDFs of the chapter files

Same content as the .txt files, in PDF form. **All confirmed text PDFs (digital exports), not scanned images.** Running them through Tesseract produces real OCR-style noise (diacritic loss, merged tokens) even though the source is clean. This is documented behavior, not a bug.

## Strategy for generating noisy data

Three viable paths, listed in order of recommended priority:

### Option 1: Tesseract on the text PDFs (PRIMARY)

Run `Boxes.ipynb` on the chapter PDFs. Even on clean text PDFs, Tesseract produces realistic OCR-style errors:
- Loses diacritics: `ā→a`, `š→s`, `ṣ→s`, `ḫ→h`, `ú→u`
- Merges/splits tokens around special characters
- Drops or substitutes scholarly markers (`°`, `¿`, `*`)

Pros: real OCR errors, including structural ones synthetic noise can't easily replicate.
Cons: requires alignment between OCR boxes and gold lines.

### Option 2: Synthetic noise (FAST FALLBACK)

Programmatically corrupt gold text using known error patterns from the project's cleaning doc:
- `ū → ü`, `ā → ä`, `ī → ï`, `ē → ë`
- `ṣ → s`, `š → s`, `ḫ → h`, `ṭ → t`
- Random character drops, swaps, OCR-confusable substitutions (`l↔1`, `0↔o`)

Pros: instant, fully controllable, no alignment needed.
Cons: lacks structural errors (merges, line splits) that real OCR produces.

### Option 3: Combine 1 + 2 (RECOMMENDED FOR FINAL MODEL)

Use Tesseract output where alignment succeeds. Apply additional synthetic noise on top to expand training set and cover patterns Tesseract didn't produce.

### What we don't have

Real scanned images of older printed cuneiform publications. If those surface from the team, treat as a future upgrade; don't block on them.

## The full pipeline (what needs to be built)

### Stage 1: Data ingestion and parsing

1. Load Innaya CSV directly. Extract `akkadian_line` column. Drop nulls (~2,046 rows).
2. Write a **chapter file parser** for the 14 Veenhof .txt files. Must:
   - Identify two-column format (Akkadian | English)
   - Skip section headers, footnotes, commentary paragraphs
   - Handle line markers (`l.e.`, `rev.`, `u.e.`)
   - Strip Word artifacts (smart quotes, weird whitespace)
   - Output one clean Akkadian line per row, tagged with source tablet ID
3. Load OARE CSV, extract Akkadian column. Note the "no-gaps" formatting difference.
4. Pool everything into one dataframe: `[source, tablet_id, line_id, akkadian_gold]`.
5. Deduplicate (Innaya may overlap with other sources for some tablets).

### Stage 2: Generate noisy pairs

**Path A (Tesseract):**
1. Run `Boxes.ipynb` logic on each chapter PDF.
2. Get OCR output as line-of-text with bounding boxes.
3. Filter out non-tablet content (titles, footnotes, English columns).
4. **Align OCR lines to gold lines** using fuzzy string matching (`rapidfuzz`). For each gold line, find the OCR line with highest similarity score above a threshold.
5. Discard pairs where alignment confidence is too low.
6. Output pairs: `[akkadian_noisy, akkadian_gold]`.

**Path B (synthetic):**
1. Define error pattern dictionary (diacritic substitutions, char drops, swaps).
2. Apply patterns probabilistically to each gold line. Each character has some chance of being corrupted.
3. Tunable noise level — start around 10-15% character corruption rate.
4. Output pairs: `[akkadian_noisy, akkadian_gold]`.

### Stage 3: Dataset preparation

1. Train/val/test split **by tablet, not by line** (lines from same tablet share vocabulary; splitting by line leaks data).
2. Suggested split: 80/10/10.
3. Save as HuggingFace `datasets.Dataset` for easy loading.

### Stage 4: Tokenization

1. Load `AutoTokenizer.from_pretrained("google/byt5-small")`.
2. Tokenize input (noisy) and target (gold) separately.
3. Max length: 128 bytes is enough (gold lines max out at 83 chars; allow headroom).
4. Pad and truncate as needed.

### Stage 5: Fine-tuning

1. Load `AutoModelForSeq2SeqLM.from_pretrained("google/byt5-small")`.
2. Use `Seq2SeqTrainer` with `Seq2SeqTrainingArguments`.
3. Suggested hyperparameters (starting point):
   - learning rate: `3e-4`
   - batch size: 8 with gradient accumulation if needed (Colab T4 memory)
   - epochs: 3-5
   - fp16: True
   - eval/save strategy: every epoch
4. Use a `DataCollatorForSeq2Seq` to handle padding.

### Stage 6: Evaluation

Compute three metrics on the held-out test set:

1. **Exact match**: percentage of predictions identical to gold.
2. **Character Error Rate (CER) / Levenshtein distance**: most informative metric for OCR correction. Use `python-Levenshtein` or `jiwer`.
3. **chrF++ and BLEU**: borrowed from the reference notebook. Use `sacrebleu`. These are translation metrics, less ideal for spellcheck-style tasks but expected by the project framing.

**Critical baseline: compute the same metrics on the noisy input itself** (no model). If the fine-tuned model doesn't beat raw noisy input, something is broken in the pipeline.

## Environment

- Target platform: Google Colab (likely free tier, T4 GPU ~15GB VRAM)
- Frameworks: `transformers`, `datasets`, `torch`, `sacrebleu`, `rapidfuzz`, `python-Levenshtein`, `pymupdf`, `pytesseract`
- All work in a single Colab notebook for now; refactor into modules later if it grows

## User preferences (style)

- Layman-friendly explanations, never over-explain
- Brutal honesty over reassurance
- No em-dashes in writing
- Concise responses, no padding
- Test understanding when teaching new concepts

## Known terminology / vocabulary

- **Gold / ground truth**: human-verified correct data. Our Akkadian transliterations.
- **Transliteration**: the romanized Latin-character version of cuneiform symbols.
- **Diacritics**: marks above/below letters (`ā` macron, `š` háček, `ṣ` cedilla/dot, etc.).
- **Tablet**: one ancient clay document, broken into multiple lines.
- **OCR**: software that reads text from images.
- **ByT5** (not "Byte-T5"): byte-level T5 model from Google.
- **CER**: Character Error Rate. Levenshtein distance normalized by length.
- **Alignment**: matching OCR output lines to corresponding gold lines.

## Current status (as of project start)

- ✅ Gold data identified across multiple sources
- ✅ Tesseract pipeline (`Boxes.ipynb`) confirmed functional
- ✅ Verified that text PDFs still produce useful OCR noise via Tesseract
- ⏳ Chapter file parser: not yet written
- ⏳ Noise generation (either path): not yet started
- ⏳ Fine-tuning loop: not yet started
- ⏳ Evaluation: not yet started

## Immediate next step

Write the chapter file parser. It's the unblocker for pooling the Veenhof data with Innaya. Once that's done, we can move on to noise generation (start with synthetic to keep momentum, layer in Tesseract output if time allows).

## Common pitfalls to avoid

1. **Don't split train/val/test by line.** Split by tablet.
2. **Don't trust the previous run's outputs in `Boxes.ipynb`.** They're stale; the source PDF is gone. Re-run from scratch on a known-good PDF.
3. **Don't pool sources without checking formatting consistency.** Innaya, Veenhof, and OARE may use slightly different bracket conventions, character choices, or markers. Normalize first.
4. **Don't use the `Innaya_Vol_2_Translations.txt` file as additional gold.** It duplicates the Innaya CSV.
5. **Don't skip the noisy-input baseline during evaluation.** Without it, you can't tell if the model learned anything.
6. **Don't forget tablet IDs.** Track which tablet each line came from for the split, deduplication, and error analysis.
