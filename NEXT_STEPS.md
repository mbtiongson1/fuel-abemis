# NEXT STEPS — Paper + Slide Deck (LaTeX)

Plan-of-record for converting the run artifacts into the final LaTeX deliverables. This complements `HANDOVER.md`; that doc covers code state, this one covers writing.

The proposal `Mini-Project/Project Documents/Project Proposal Long Format 1st Revision.tex` already has Sections I–X (Introduction → Software & Hardware). The paper extends that file; the slide deck is a separate Beamer document.

---

## 1. Paper — sections to add

Append to the existing `.tex`. Use `\section*{}` for consistency with the rest of the document. No bibliography pass yet — that follows once content is locked.

### XI. Results

Three subsections, each tied to specific artifacts under `Mini-Project/Agricultural Machinery Inventory from ABEMIS/Regression Parameters Output V3/`.

**XI.A — Dataset and feature set.** State the final 378-record count, the 8-feature vector (5 numeric + 3 categorical-encoded), and the train/test split (302 / 76, `random_state=42`). Mention the OCR blocker (247 scanned PDFs unrecovered) and the 7 newly-extracted local records as a footnote, not in the headline.

**XI.B — Model performance.** Report RF holdout metrics (R² 0.911, MAE 1.09 L/h, RMSE 1.61 L/h) **and** 5-fold CV mean ± std (R² 0.895 ± std, MAE 1.08 ± std, RMSE 1.77 ± std — pull exact std values from `RF_Predictions.xlsx → CV Metrics`). Side-by-side comparison table from `OLS_vs_RF_Comparison.xlsx → Comparison Metrics`:

| Model | R² | MAE (L/h) | RMSE (L/h) |
|---|---|---|---|
| RF (8 features) | 0.911 | 1.09 | 1.61 |
| OLS Global Linear | 0.761 | 1.68 | 2.64 |
| OLS Hierarchical | 0.722 | 1.87 | 2.85 |

Worth a sentence: hierarchical OLS *under*performs global linear on this holdout because per-type fits over-fit to small sub-samples. RF's gain is from non-linearity + feature interaction, not just having more features.

**XI.C — Feature importance and interpretability.** Importance bar from `RF_Predictions.xlsx → Feature Importance`. SHAP global ordering from `SHAP_Analysis.xlsx → Feature Importance` (embed `shap_summary_bar.png` and `shap_summary_beeswarm.png`). One LIME instance from `lime_example_0.png` to show local explanation reads cleanly. Discuss `power_kw` 76% dominance, `year` ~12% as a proxy for engine-efficiency drift, ABEMIS context features ~3.5% combined (small-but-consistent — keep them, they cost nothing).

### XII. Discussion

**XII.A — Per-machinery-type residuals.** Pull `RF_Predictions.xlsx → Per-Type Residuals`. Highlight which types the RF predicts well (low MAE, low |mean residual|) vs poorly (large MAE or systematic bias). Tie poor performers to small training counts.

**XII.B — Regional fuel demand.** From `ABEMIS_Regional_Fuel_Estimates.xlsx → Per Region` and `Per Region × Type`. Caveat: 70% coverage (172,265 of 246,741 fuel-relevant ABEMIS records) — 25% missing power, ~5% unmappable type. Show a regional bar chart; rank regions by predicted L/h aggregate. Acknowledge the corn-mill→Rice-Mill mapping fudge (~2,934 rows, see `HANDOVER.md` Blocker §4).

**XII.C — Limitations.** Three honest items: (1) AMTEC test reports are lab-condition, not field-condition — expect real fuel consumption to be higher under load; (2) no temporal feature yet (RAED cropping calendar still pending); (3) the legacy 371 records cannot be re-extracted from current source PDFs.

### XIII. Conclusion

One paragraph. RF beats OLS by a material margin on the same holdout (R² 0.91 vs 0.76 vs 0.72). The 8-feature model with ABEMIS context is the recommended deliverable. Regional fuel demand estimates are usable for BAFE planning subject to the 70%-coverage caveat.

### XIV. Recommendations / Future Work

Bullet list:
- OCR retraining once Tesseract/Poppler binaries are installed → expected 500–550 records, R² likely 0.93–0.95.
- RAED cropping calendar integration adds the temporal axis (`is_in_season`, `crop_stage_intensity`).
- Recover the original 3,065-PDF set from collaborator's machine for a much larger training base.
- Field-validation campaign to bridge lab-vs-field gap.

---

## 2. Figures and tables — concrete checklist

Save copies (not symlinks) into a new `Mini-Project/Project Documents/figures/` directory so the `.tex` references are stable:

| LaTeX label | Source file | Section |
|---|---|---|
| `fig:rf-importance` | `Regression Parameters Output V3/SHAP_Analysis.xlsx` (Feature Importance sheet → bar chart) or `shap_summary_bar.png` | XI.C |
| `fig:shap-beeswarm` | `Regression Parameters Output V3/shap_summary_beeswarm.png` | XI.C |
| `fig:lime-example` | `Regression Parameters Output V3/lime_example_0.png` | XI.C |
| `fig:regional-fuel` | new bar chart from `ABEMIS_Regional_Fuel_Estimates.xlsx → Per Region` (script: `analysis/abemis_fuel_scoring.py` can be extended to emit a PNG, or do it in a one-off cell) | XII.B |
| `fig:residuals-by-type` | new horizontal bar from `RF_Predictions.xlsx → Per-Type Residuals` (MAE per type) | XII.A |
| `tab:model-comparison` | `OLS_vs_RF_Comparison.xlsx → Comparison Metrics` | XI.B |
| `tab:cv-metrics` | `RF_Predictions.xlsx → CV Metrics` (drop per-fold rows; keep mean/std) | XI.B |
| `tab:feature-importance` | `RF_Predictions.xlsx → Feature Importance` | XI.C |

Use `\input{tables/<name>.tex}` for tables; generate them with `pandas.DataFrame.to_latex()` in a 3-line script so they regenerate from the xlsx without manual transcription.

---

## 3. Slide deck — Beamer outline (~10 slides, 12 min talk)

New file: `Mini-Project/Project Documents/Slide Deck.tex` using `\documentclass{beamer}` with the `metropolis` theme (clean, two-author friendly).

| # | Title | Content | Source |
|---|---|---|---|
| 1 | Title | Project title + authors + course | — |
| 2 | Motivation | Static-coefficient gap; ML opportunity | Proposal §I |
| 3 | Data | AMTEC (378 records, lab tests) + ABEMIS (246K deployments). Two flow diagram. | Proposal §VII |
| 4 | Method | Pipeline diagram: Ingest → Analytics → OLS/RF → SHAP/LIME → Regional Scoring | `CLAUDE.md` architecture diagram |
| 5 | Features | 8-feature vector visual; highlight 3 ABEMIS context features as the "novelty" | `random_forest.py` |
| 6 | Results — RF | Headline metrics card: R² 0.91, MAE 1.09, RMSE 1.61. CV mean R² 0.90. | `RF_Predictions.xlsx` |
| 7 | Results — OLS vs RF | Comparison table (3 rows). One-line takeaway: RF wins by 0.15 R². | `OLS_vs_RF_Comparison.xlsx` |
| 8 | Interpretability | SHAP bar (global) + 1 LIME plot (local). 30 sec each. | SHAP/LIME plots |
| 9 | Regional fuel demand | Bar chart, 17 regions. Caveat one-liner about 70% coverage. | `ABEMIS_Regional_Fuel_Estimates.xlsx` |
| 10 | Conclusion + Future Work | Three bullets each. | This doc §1 XIII–XIV |

Backup slides (3): per-type residual table, RAED design preview, OCR blocker.

---

## 4. Suggested writing order

1. Generate the regional + per-type residual PNGs (small script — ~30 lines).
2. Export `to_latex` for the three tables → `figures/tables/`.
3. Write XI.A (dataset) + XI.B (metrics) — the easiest wins, locks the headline numbers.
4. Write XI.C (interpretability) — leans on SHAP/LIME plots that already exist.
5. Write XII (Discussion) — needs the per-type residual figure.
6. Write XIII + XIV — short, mostly structural.
7. Build the Beamer deck after the paper headline is locked. Slides 6/7/9 share figures with the paper, so generate-once-use-twice.

Estimated time on a focused day: paper draft ~4 h, deck ~2 h, figures + tables ~1 h.

---

## 5. Things that should NOT block writing

- OCR retraining (need binaries) — write the paper with 378 records; if OCR yields more later, re-run and update the metrics table only.
- RAED data acquisition — already framed as future work in §XIV; no rewrite needed when it lands.
- Recovering collaborator's 3,065 PDFs — same; framed as future work.

These are upgrades, not prerequisites.
