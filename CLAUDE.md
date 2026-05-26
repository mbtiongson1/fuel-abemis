# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

This project predicts fuel consumption for Philippine agricultural machinery by combining two official datasets:
- **ABEMIS** — inventory of machinery distributed across all regions (ZIP → Excel)
- **AMTEC** — performance test reports (PDF → structured data)

The original implementation lives in `FuelRequirement.ipynb` (43 cells, ~3 000 lines). **Do not delete or modify it** — it is the canonical research reference. The Python module tree is a refactor of that notebook into importable, runnable scripts. The notebook will be rebuilt from scratch once the module split is validated.

**Current state:** Data ingestion (ABEMIS extraction + AMTEC PDF parsing) and analytics are done. The full modeling pipeline (OLS, Random Forest, SHAP, LIME) has now been run end-to-end against the 371-record "Clean Record Level" sheet; outputs live in `Mini-Project/Agricultural Machinery Inventory from ABEMIS/Regression Parameters Output V3/`. Latest RF holdout metrics: R² 0.92, MAE 0.89 L/h, RMSE 1.56 L/h.

The previous `Mini-Project/Test Report/` directory was removed during cleanup; AMTEC outputs now live in the ABEMIS folder. `config.py` paths reflect this (see Architecture below).

---

## First-time Setup

`config.py` is already set to a repo-relative `BASE = Path("Mini-Project/")`. AMTEC paths point at the post-cleanup layout (outputs live inside `Agricultural Machinery Inventory from ABEMIS/`).

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
python -m data.amtec_analytics
python -m models.ols_regression
python -m models.random_forest
python -m analysis.shap_analysis
python -m analysis.lime_explanations
```

Syntax-check all modules without executing them:

```bash
python -m py_compile config.py main.py data/abemis_usability.py data/abemis_classifier.py data/amtec_analytics.py models/ols_regression.py models/random_forest.py analysis/shap_analysis.py analysis/lime_explanations.py
```

---

## Architecture

### Config-driven design

`config.py` is the single source of truth. Every module imports its paths and modeling flags from there — nothing is hardcoded inside a module. After the post-handover cleanup, all processed outputs (ABEMIS + AMTEC) live under `Mini-Project/Agricultural Machinery Inventory from ABEMIS/`. The relevant constants:

- `AMTEC_PDF_DIR = BASE / "Test Reports from BAFE-AMTEC"`
- `AMTEC_EXTRACTION_DIR = BASE / "Agricultural Machinery Inventory from ABEMIS/Extracted Batches Improved V3"`
- `AMTEC_ANALYTICS_DIR = BASE / "Agricultural Machinery Inventory from ABEMIS/Analytics Output V2"`
- `AMTEC_REGRESSION_DIR = BASE / "Agricultural Machinery Inventory from ABEMIS/Regression Parameters Output V3"` (also receives RF/SHAP/LIME outputs)

### Module responsibilities and data flow

```
data/ingestion/abemis_extractor.py    ZIP  → Regional Excel files        [DONE]
data/ingestion/amtec_pdf_extractor.py PDF  → V3 batch xlsx files         [DONE — full xlsx deleted, V3 batches survive]
                                             (PyMuPDF + optional OCR, checkpoints every 100 PDFs)

data/abemis_usability.py              Regional Excel → usability report
data/abemis_classifier.py             Keyword-rule classification → Fuel / No-Fuel / Uncertain
data/amtec_analytics.py               extracted dataset → Analytics V2 xlsx
                                             (derived: fuel_l_per_hr, fuel_l_per_kw_hr,
                                              power_class_fixed, fuel_intensity_class,
                                              fuel_outlier_severity)

models/ols_regression.py              Analytics V2 "Clean Record Level" → Regression V3 xlsx       [DONE]
                                             (hierarchical OLS: GLOBAL > FAMILY > TYPE,
                                              3 forms each: linear/quadratic/log_response,
                                              R² filter, fallback hierarchy, diagnostic plots)
models/random_forest.py               Analytics V2 → rf_model.pkl + RF_Predictions.xlsx            [DONE]

analysis/shap_analysis.py             rf_model.pkl → SHAP_Analysis.xlsx + plots                   [DONE]
analysis/lime_explanations.py         rf_model.pkl → LIME_Explanations.xlsx + per-instance plots  [DONE]
```

### Key intermediate files (under `Mini-Project/Agricultural Machinery Inventory from ABEMIS/`)

| File | Produced by | Consumed by |
|------|-------------|-------------|
| `Extracted Batches Improved V3/AMTEC_extracted_improved_v3_batch_*.xlsx` | `amtec_pdf_extractor` | `amtec_analytics` |
| `Analytics Output V2/AMTEC_Test_Report_Fuel_Power_Analytics_V2.xlsx` | `amtec_analytics` | `ols_regression`, `random_forest` |
| `Regression Parameters Output V3/AMTEC_Regression_All_Parameters_V3_Filtered_R2.xlsx` | `ols_regression` | — (final OLS output) |
| `Regression Parameters Output V3/rf_model.pkl` + `rf_encoders.pkl` | `random_forest` | `shap_analysis`, `lime_explanations` |
| `Regression Parameters Output V3/RF_Predictions.xlsx` | `random_forest` | — (final RF output) |
| `Regression Parameters Output V3/SHAP_Analysis.xlsx`, `LIME_Explanations.xlsx` | `analysis/*` | — (paper artifacts) |

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

`models/random_forest.py` exposes two lists at module level:

```python
NUMERIC_FEATURES     = ["power_kw", "year"]
CATEGORICAL_FEATURES = ["machinery_type", "machinery_family", "analysis_subset"]
```

Add columns to either list — `load_data()` handles label-encoding for categoricals automatically and saves the encoder dict to `rf_encoders.pkl`. Sparse columns like `field_capacity_value` (80/371) and `operating_speed_value` (77/371) will collapse the training set to ~80 rows; if you add them, expect a much smaller model. The SHAP and LIME modules pick up the new features automatically since they reuse `models.random_forest.load_data()`.

---

## RAED Cropping Calendar (planned)

**Status:** Data not yet acquired. Only blank data-gathering form exists.

**Form location:** `Mini-Project/Data Gathering form for Cropping Calendar (ao07222022).xlsx`

**Sheets (4 total):**
- `Legend` — operation codes (LP/I/P/CC/H/PP/SR/TP/T) mapped to operations (e.g., LP→Land Preparation) and machinery groups (e.g., Tractors, Hand Tractor).
- `Rice Cropping Calendar`, `Corn`, `HVC` — to be filled with region × month × operation intensity once data is provided.

**Join chain:** RAED operation code → `Legend` sheet → machinery_type string → (existing AMTEC + ABEMIS) → fuel model.

**Outputs (when data arrives):** `data/raed_cropping_calendar.py` will load the three crop sheets, normalize operation codes via `Legend`, and emit `Analytics Output V2/raed_seasonal_demand.xlsx` keyed by (machinery_type, region, month).

**Time predictors produced:**
- `is_in_season` (binary) — machinery_type × region × month active flag.
- `crop_stage_intensity` (0–1 scalar) — normalized machinery utilization per stage.

**Integration point:** Phase B2 regional scoring (`analysis/abemis_fuel_scoring.py`, planned) gains temporal axis: base B2 score × is_in_season × crop_stage_intensity. Training phase (B1, OLS + RF) is **unchanged** because AMTEC test reports lack region/month context.

---

## Notebook reference

`FuelRequirement.ipynb` cell index for quick lookup. Cells 30–42 in the notebook are still markdown stubs — the working ML code lives in `models/random_forest.py` and `analysis/*` only.

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
| 30–42 | RF / SHAP / LIME — markdown stubs only; not yet backfilled from modules |
