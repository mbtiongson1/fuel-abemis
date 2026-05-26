# Architecture

## Overview

This project predicts fuel consumption for agricultural machinery in the Philippines using data from two official sources: ABEMIS (inventory) and AMTEC (test reports). The pipeline covers data ingestion, quality checking, analytics, OLS regression modeling, Random Forest, and model explainability (SHAP + LIME).

> **Note:** `FuelRequirement.ipynb` is the canonical reference for this codebase. It documents the original research and cell-by-cell implementation. **Do not delete it.**

---

## File Structure

```
fuel-abemis/
├── FuelRequirement.ipynb           # Original monolith — canonical reference, DO NOT DELETE
├── ARCHITECTURE.md                 # This file
├── CLAUDE.md                       # Project context for Claude Code
├── config.py                       # All shared paths, flags, and thresholds
├── main.py                         # Pipeline orchestration (--skip-ingestion etc.)
│
├── data/                           # All data pre-processing
│   ├── ingestion/                  # Done — raw data extraction
│   │   ├── abemis_extractor.py     # Regional ZIP → Excel (Cell 16)
│   │   └── amtec_pdf_extractor.py  # AMTEC PDFs → AMTEC_full_extracted_dataset.xlsx (Cell 18)
│   ├── abemis_usability.py         # Column availability check by region (Cell 21)
│   ├── abemis_classifier.py        # Fuel vs. non-fuel keyword classifier (Cell 23)
│   └── amtec_analytics.py          # Cleaning, derived metrics, outlier detection (Cell 25)
│
├── models/                         # ML models
│   ├── ols_regression.py           # Hierarchical OLS with ANOVA + diagnostics (Cell 27)
│   └── random_forest.py            # Random Forest regressor
│
├── analysis/                       # Explainability
│   ├── shap_analysis.py            # SHAP feature importance (TreeExplainer)
│   └── lime_explanations.py        # LIME local explanations (LimeTabularExplainer)
│
└── utils/
    └── io_helpers.py               # Shared Excel I/O, read_file_safely(), ensure_dirs()
```

---

## Data Sources

| Source | Format | Content |
|--------|--------|---------|
| ABEMIS | Region-labeled ZIP files | Machinery inventory (type, power, brand, model, location) |
| AMTEC  | PDF test reports | Performance data — power ratings + fuel consumption |

---

## Data Flow

```
config.py  (BASE path, 8 output dirs, flags)
    │
    ├─► data/ingestion/abemis_extractor.py
    │         ZIP → Regional Excel files in ABEMIS_EXTRACTED_DIR   [DONE]
    │         └─► data/abemis_usability.py
    │                   → ABEMIS_Inventory_Usability_Check.xlsx
    │                   └─► data/abemis_classifier.py
    │                             → ABEMIS_Fuel_vs_NoFuel_Machinery_V2.xlsx
    │
    └─► data/ingestion/amtec_pdf_extractor.py
              PDF → AMTEC_full_extracted_dataset.xlsx              [DONE]
              └─► data/amtec_analytics.py
                        → AMTEC_Test_Report_Fuel_Power_Analytics_V2.xlsx
                          (Clean Record Level sheet is the key input for all models)
                        │
                        ├─► models/ols_regression.py
                        │         → AMTEC_Regression_All_Parameters_V3_Filtered_R2.xlsx
                        │
                        └─► models/random_forest.py
                                  → rf_model.pkl
                                  → RF_Predictions.xlsx
                                  │
                                  ├─► analysis/shap_analysis.py
                                  │         → SHAP_Analysis.xlsx
                                  │         → shap_summary_bar.png
                                  │         → shap_summary_beeswarm.png
                                  │
                                  └─► analysis/lime_explanations.py
                                            → LIME_Explanations.xlsx
                                            → lime_example_<n>.png
```

---

## Module Details

### `config.py`
Single source of truth for all directory paths and modeling parameters.

| Symbol | Description |
|--------|-------------|
| `BASE` | Root directory of the project data |
| `ABEMIS_RAW_DIR` | Raw ZIP files from ABEMIS |
| `ABEMIS_EXTRACTED_DIR` | Extracted regional Excel files |
| `ABEMIS_DIAG_DIR` | Usability check outputs |
| `ABEMIS_FUEL_DIR` | Fuel vs. non-fuel classification outputs |
| `AMTEC_PDF_DIR` | Raw AMTEC PDF test reports |
| `AMTEC_EXTRACTION_DIR` | Extracted AMTEC dataset xlsx |
| `AMTEC_ANALYTICS_DIR` | Analytics and cleaning outputs |
| `AMTEC_REGRESSION_DIR` | Regression model outputs + plots |
| `MIN_ACCEPTABLE_R2` | Minimum adjusted/raw R² to keep a model (default 0.50) |
| `R2_FILTER_TYPE` | `"adjusted"` or `"raw"` |

---

### `data/abemis_usability.py`
Scans all regional Excel files in `ABEMIS_EXTRACTED_DIR` and reports column availability.

- **Output:** `ABEMIS_Inventory_Usability_Check.xlsx` (sheets: Overall Summary, File Summary, Column Summary, Sample Rows)

### `data/abemis_classifier.py`
Keyword-rule classifier: labels each inventory row as `FUEL_RELEVANT`, `NO_FUEL_OR_NON_RELEVANT`, or `UNCERTAIN_REVIEW`.

- **Key function:** `classify_fuel_relevance(machine_name, power_value)`
- **Output:** `ABEMIS_Fuel_vs_NoFuel_Machinery_V2.xlsx` (8 sheets including master, fuel list, no-fuel list)

### `data/amtec_analytics.py`
Cleans the extracted AMTEC dataset and computes derived metrics.

- **Derived columns:** `fuel_l_per_hr`, `fuel_l_per_kw_hr`, `fuel_l_per_hp_hr`, `power_class_fixed`, `fuel_intensity_class`, `fuel_outlier_severity`
- **Output:** `AMTEC_Test_Report_Fuel_Power_Analytics_V2.xlsx` (20 sheets)

---

### `models/ols_regression.py`
Hierarchical OLS regression (3 scopes × 3 forms = up to 9 models per machinery type).

- **Scopes:** `GLOBAL` → `MACHINERY_FAMILY` → `MACHINERY_TYPE`
- **Forms:** `linear`, `quadratic`, `log_response`
- **Filtering:** Models with R² < `MIN_ACCEPTABLE_R2` are removed
- **Fallback hierarchy:** For each machinery type, picks the most specific passing model
- **Output:** `AMTEC_Regression_All_Parameters_V3_Filtered_R2.xlsx` (16 sheets + diagnostic PNG plots)

### `models/random_forest.py`
Random Forest regressor; user-extensible via `FEATURE_COLS`.

- **Output:** `rf_model.pkl`, `RF_Predictions.xlsx`

---

### `analysis/shap_analysis.py`
Global SHAP feature importance using `shap.TreeExplainer`.

- **Output:** `SHAP_Analysis.xlsx`, `shap_summary_bar.png`, `shap_summary_beeswarm.png`

### `analysis/lime_explanations.py`
LIME local explanations for `N_SAMPLES` individual predictions.

- **Output:** `LIME_Explanations.xlsx`, `lime_example_<n>.png`

---

## Running the Pipeline

```bash
# Full pipeline (includes ingestion)
python main.py

# Skip ingestion (data already extracted) — most common after first run
python main.py --skip-ingestion

# Skip ingestion + processing (analytics xlsx already exists)
python main.py --skip-ingestion --skip-processing

# Only OLS regression
python main.py --skip-ingestion --skip-processing --skip-rf --skip-analysis

# Only RF + analysis
python main.py --skip-ingestion --skip-processing --skip-ols
```

---

## Dependencies

```
pymupdf      # PDF extraction
pandas
openpyxl
numpy
matplotlib
scipy
statsmodels  # OLS regression, ANOVA, diagnostics
scikit-learn # Random Forest, metrics
shap         # SHAP explainability
lime         # LIME explainability
pytesseract  # OCR (optional, for scanned PDFs)
pdf2image    # OCR support (optional)
```
