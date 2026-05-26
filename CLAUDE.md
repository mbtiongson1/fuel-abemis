# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This project predicts fuel consumption for Philippine agricultural machinery by combining two official datasets:
- **ABEMIS** — inventory of machinery distributed across all regions (ZIP → Excel)
- **AMTEC** — performance test reports (PDF → structured data)

The original implementation lives in `FuelRequirement.ipynb` (43 cells, ~3 000 lines). **Do not delete or modify it** — it is the canonical research reference. The Python module tree is a refactor of that notebook into importable, runnable scripts. The notebook will be rebuilt from scratch once the module split is validated.

**Current state:** Data ingestion (ABEMIS extraction + AMTEC PDF parsing) is done and outputs exist under `Mini-Project/`. Active work is on the modeling side: OLS regression is extracted; Random Forest, SHAP, and LIME are stubs awaiting implementation.

---

## First-time Setup

**Update `BASE` in `config.py` before running anything.** The original notebook used a Google Colab mount path. For local use set it to the repo-relative data directory:

```python
# config.py
BASE = Path("Mini-Project/")   # relative to repo root
```

Install dependencies (no lock file exists yet):

```bash
pip install pymupdf pandas openpyxl numpy matplotlib scipy statsmodels scikit-learn shap lime pytesseract pdf2image pillow
```

---

## Running the Pipeline

> **Default:** always run with `--skip-ingestion`. Data ingestion is done; re-running it would re-extract ~1 600 PDFs unnecessarily.

All stages are orchestrated through `main.py` from the repo root:

```bash
# DEFAULT — data already extracted
python main.py --skip-ingestion

# Skip ingestion + processing (analytics xlsx already exists)
python main.py --skip-ingestion --skip-processing

# Run only OLS regression
python main.py --skip-ingestion --skip-processing --skip-rf --skip-analysis

# Run only RF + explainability (after OLS is done)
python main.py --skip-ingestion --skip-processing --skip-ols

# Full pipeline (re-extracts everything)
python main.py
```

Run a single module directly (all modules have `if __name__ == "__main__"` guards):

```bash
python -c "import config; config.create_output_dirs()"   # create output dirs
python data/amtec_analytics.py
python models/ols_regression.py
python models/random_forest.py
python analysis/shap_analysis.py
python analysis/lime_explanations.py
```

Syntax-check all modules without executing them:

```bash
python -m py_compile config.py main.py data/abemis_usability.py data/abemis_classifier.py data/amtec_analytics.py models/ols_regression.py models/random_forest.py analysis/shap_analysis.py analysis/lime_explanations.py
```

---

## Architecture

### Config-driven design

`config.py` is the single source of truth. Every module imports its paths and modeling flags from there — nothing is hardcoded inside a module. The key thing to understand is the 8-directory layout (4 ABEMIS + 4 AMTEC), all rooted at `BASE`.

### Module responsibilities and data flow

```
data/ingestion/abemis_extractor.py    ZIP  → Regional Excel files        [DONE]
data/ingestion/amtec_pdf_extractor.py PDF  → AMTEC_full_extracted_dataset.xlsx  [DONE]
                                             (PyMuPDF + optional OCR, checkpoints every 100 PDFs)

data/abemis_usability.py              Regional Excel → usability report
data/abemis_classifier.py             Keyword-rule classification → Fuel / No-Fuel / Uncertain
data/amtec_analytics.py               full_extracted_dataset → Analytics V2 xlsx
                                             (derived: fuel_l_per_hr, fuel_l_per_kw_hr,
                                              power_class_fixed, fuel_intensity_class,
                                              fuel_outlier_severity)

models/ols_regression.py              Analytics V2 "Clean Record Level" → Regression V3 xlsx
                                             (hierarchical OLS: GLOBAL > FAMILY > TYPE,
                                              3 forms each: linear/quadratic/log_response,
                                              R² filter, fallback hierarchy, diagnostic plots)
models/random_forest.py               Analytics V2 → rf_model.pkl + RF_Predictions.xlsx

analysis/shap_analysis.py             rf_model.pkl → SHAP_Analysis.xlsx + plots
analysis/lime_explanations.py         rf_model.pkl → LIME_Explanations.xlsx + per-instance plots
```

### Key intermediate files (under `Mini-Project/`)

| File | Produced by | Consumed by |
|------|-------------|-------------|
| `AMTEC_full_extracted_dataset.xlsx` | `amtec_pdf_extractor` | `amtec_analytics` |
| `AMTEC_Test_Report_Fuel_Power_Analytics_V2.xlsx` | `amtec_analytics` | `ols_regression`, `random_forest` |
| `AMTEC_Regression_All_Parameters_V3_Filtered_R2.xlsx` | `ols_regression` | — |
| `rf_model.pkl` | `random_forest` | `shap_analysis`, `lime_explanations` |

The `"Clean Record Level"` sheet of the Analytics V2 xlsx is the standard input for all model modules.

### OLS regression model structure

`models/ols_regression.py` runs **two passes**:
1. FULL pass → identifies global studentized outliers
2. FINAL pass (outliers excluded) → builds the actual hierarchy

For each scope × form combination, `fit_regression()` returns four DataFrames: model summary, coefficients, ANOVA table, and per-observation diagnostics (leverage, Cook's D, studentized residuals). Only models passing `MIN_ACCEPTABLE_R2` (default 0.50, `R2_FILTER_TYPE = "adjusted"`) survive into the prediction hierarchy.

### ABEMIS classification logic

`data/abemis_classifier.py::classify_fuel_relevance()` applies a priority-ordered rule chain:
1. Any `NO_FUEL_KEYWORDS` match → `NO_FUEL_OR_NON_RELEVANT` (electric/GMP/food-processing terms override fuel terms)
2. Any `FUEL_KEYWORDS` match → `FUEL_RELEVANT`
3. Has valid rated power but no keyword match → `UNCERTAIN_REVIEW`
4. Only ambiguous terms → `UNCERTAIN_REVIEW`
5. No match → `NO_FUEL_OR_NON_RELEVANT`

### Extending the RF model

`models/random_forest.py` exposes `FEATURE_COLS` at module level. Add feature names there (they must exist as columns in the "Clean Record Level" sheet) to extend the model without touching any other file.

---

## Notebook reference

`FuelRequirement.ipynb` cell index for quick lookup:

| Cell | Content |
|------|---------|
| 9 | Imports |
| 13 | Configuration (mirrors `config.py`) |
| 16 | ABEMIS ZIP extractor → `data/ingestion/abemis_extractor.py` |
| 18 | AMTEC PDF extractor V4 → `data/ingestion/amtec_pdf_extractor.py` |
| 21 | ABEMIS usability check → `data/abemis_usability.py` |
| 23 | ABEMIS fuel-relevance separator → `data/abemis_classifier.py` |
| 25 | AMTEC analytics & cleaning → `data/amtec_analytics.py` |
| 27 | OLS regression V3 → `models/ols_regression.py` |
| 30–37 | RF scaffolding (headers only) → `models/random_forest.py` |
