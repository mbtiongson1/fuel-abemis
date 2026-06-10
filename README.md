# fuel-abemis

[![Powered by Gaia](https://gaia.tiongson.co/badges/powered-by-gaia.svg)](https://gaia.tiongson.co/)

Predicts fuel consumption for Philippine agricultural machinery by combining two official datasets:

- **ABEMIS** — inventory of machinery distributed across all regions (~246K records)
- **AMTEC** — performance test reports (371 clean records, lab-condition fuel + power data)

**Latest RF holdout metrics:** R² 0.91 · MAE 1.09 L/h · RMSE 1.61 L/h

---

## Setup

```bash
pip install pymupdf pandas openpyxl numpy matplotlib scipy statsmodels scikit-learn shap lime pytesseract pdf2image pillow
```

---

## Running the pipeline

> Data ingestion is already done. Always use `--skip-ingestion` to avoid re-extracting ~1,600 PDFs.

```bash
# Most common — data already extracted
python main.py --skip-ingestion

# Skip ingestion + processing (analytics xlsx already exists)
python main.py --skip-ingestion --skip-processing

# OLS only
python main.py --skip-ingestion --skip-processing --skip-rf --skip-analysis

# RF + SHAP + LIME only
python main.py --skip-ingestion --skip-processing --skip-ols
```

---

## Architecture

```
config.py          # single source of truth for all paths and flags
main.py            # pipeline orchestration

data/
  ingestion/       # ZIP → Excel (ABEMIS), PDF → xlsx (AMTEC)   [done]
  abemis_usability.py
  abemis_classifier.py
  amtec_analytics.py

models/
  ols_regression.py   # hierarchical OLS (GLOBAL > FAMILY > TYPE, 3 forms each)
  random_forest.py    # RF regressor + 5-fold CV

analysis/
  shap_analysis.py    # global SHAP (TreeExplainer)
  lime_explanations.py
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full data-flow diagram and module details.

---

## Key outputs

All outputs live under `Mini-Project/Agricultural Machinery Inventory from ABEMIS/Regression Parameters Output V3/`:

| File | Description |
|------|-------------|
| `AMTEC_Regression_All_Parameters_V3_Filtered_R2.xlsx` | OLS model parameters |
| `RF_Predictions.xlsx` | RF predictions, CV metrics, feature importance |
| `SHAP_Analysis.xlsx` + `shap_summary_*.png` | Global SHAP feature importance |
| `LIME_Explanations.xlsx` + `lime_example_*.png` | Local LIME explanations |

---

## Reference notebook

`FuelRequirement.ipynb` is the canonical research reference (original monolith, 43 cells). Do not delete it. The Python module tree is a validated refactor of that notebook.
