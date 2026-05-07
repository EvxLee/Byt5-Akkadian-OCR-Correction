# Data Sources

Gold data lives in `gold/` and is **not committed to git** (added manually).

## gold/innaya/
**File:** `Innaya_with_translations_2_2026.csv`
**Source:** Innaya archive, ~250 tablets, ~5,920 Akkadian lines.
**Columns used:** `akkadian_line` (primary), `label_line` (tablet ID).
**Citation:** [add when confirmed]

## gold/veenhof/
**Files:** `4__I__Six_Basic_Documents__1-6__1_.txt` through `17__XIV__S_u-Is_tar__235-245.txt` (14 chapter files)
**Source:** Veenhof 2014, *Kültepe Tabletleri VIII* (Elamma archive), ~240 tablets.
**Format:** Two-column, Akkadian | English translation, tab/space separated. Mixed with footnotes and commentary. Requires `src/parsing/veenhof_parser.py`.
**Citation:** Veenhof, K.R. 2014. *Kültepe Tabletleri VIII.* Türk Tarih Kurumu.

Corresponding PDFs live alongside the .txt files and are used as Tesseract input for noisy pair generation.

## gold/oare/
**File:** `OARE_no-gaps_3-9-26.csv`
**Source:** OARE corpus, ~1,500 lines. "No-gaps" means bracket reconstructions are filled in.
**Citation:** [add when confirmed]

## Do NOT use for training
- `1___Preliminary_pages.txt`
- `2___Preface__contents__bibliogr__concord_docx.txt`
- `3__Introduction.txt`
- `Innaya_Vol_2_Translations.txt`
- `RlA_Bibliograph_2026.csv`
