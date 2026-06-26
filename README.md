# fuel-abemis

[![Powered by Gaia](https://gaia.tiongson.co/badges/powered-by-gaia.svg)](https://gaia.tiongson.co/)
[![Slides](https://img.shields.io/badge/slides-GitHub%20Pages-blue?logo=github)](https://mbtiongson1.github.io/fuel-abemis/)
[![Paper](https://img.shields.io/badge/paper-IEEE%20format-green?logo=overleaf)](Mini-Project/Project%20Documents/Rosas%2C%20Tiongson%20-%20Pilot%20ML%20Fuel%20Agriculture%20%5BIEEE%5D.pdf)

<p align="center">
  <img src="Mini-Project/Project%20Documents/images/tractor_ph_rice_field.jpg" width="700" alt="Philippine rice field tractor"/>
</p>

> Pilot study predicting fuel consumption for Philippine agricultural machinery by combining two official datasets: ABEMIS (national inventory) and AMTEC (laboratory performance tests).

**Best RF holdout metrics: R² 0.91 · MAE 1.09 L/h · RMSE 1.61 L/h**

---

## Datasets

| Source | Description | Records |
|--------|-------------|---------|
| **ABEMIS** | DA-BAFE national inventory of distributed machinery across all regions | ~246,000 |
| **AMTEC** | Performance test reports — lab-condition fuel consumption and rated power data | 371 (clean) |

---

## Results

### Exploratory Data Analysis

<p align="center">
  <img src="Mini-Project/Project%20Documents/average_fuel_by_machinery_family.png" width="48%" alt="Average fuel by machinery family"/>
  <img src="Mini-Project/Project%20Documents/average_fuel_by_machinery_type.png" width="48%" alt="Average fuel by machinery type"/>
</p>

<p align="center">
  <img src="Mini-Project/Project%20Documents/fuel_intensity_by_machinery_type.png" width="48%" alt="Fuel intensity by machinery type"/>
  <img src="Mini-Project/Project%20Documents/power_vs_fuel_all.png" width="48%" alt="Power vs fuel — all machinery"/>
</p>

<p align="center">
  <img src="Mini-Project/Project%20Documents/power_vs_fuel_field_machinery.png" width="60%" alt="Power vs fuel — field machinery"/>
</p>

---

### OLS Regression Diagnostics

Each hierarchical scope was modeled using linear, quadratic, and cubic OLS forms. Final model selected per scope based on adjusted R² and residual diagnostics.

#### Global — All Machinery

| Residuals vs Fitted | Q-Q Plot | Studentized Residuals | Leverage |
|:---:|:---:|:---:|:---:|
| ![](Mini-Project/Project%20Documents/GLOBAL_ALL_MACHINERY_FINAL_quadratic_residuals_vs_fitted.png) | ![](Mini-Project/Project%20Documents/GLOBAL_ALL_MACHINERY_FINAL_quadratic_qqplot.png) | ![](Mini-Project/Project%20Documents/GLOBAL_ALL_MACHINERY_FINAL_quadratic_studentized_residuals.png) | ![](Mini-Project/Project%20Documents/GLOBAL_ALL_MACHINERY_FINAL_quadratic_leverage.png) |

#### Family — Harvest Machinery

| Residuals vs Fitted | Q-Q Plot | Studentized Residuals | Leverage |
|:---:|:---:|:---:|:---:|
| ![](Mini-Project/Project%20Documents/MACHINERY_FAMILY_Harvest_Machinery_FINAL_quadratic_residuals_vs_fitted.png) | ![](Mini-Project/Project%20Documents/MACHINERY_FAMILY_Harvest_Machinery_FINAL_quadratic_qqplot.png) | ![](Mini-Project/Project%20Documents/MACHINERY_FAMILY_Harvest_Machinery_FINAL_quadratic_studentized_residuals.png) | ![](Mini-Project/Project%20Documents/MACHINERY_FAMILY_Harvest_Machinery_FINAL_quadratic_leverage.png) |

#### Family — Mobile Field Machinery

| Residuals vs Fitted | Q-Q Plot | Studentized Residuals | Leverage |
|:---:|:---:|:---:|:---:|
| ![](Mini-Project/Project%20Documents/MACHINERY_FAMILY_Mobile_Field_Machinery_FINAL_quadratic_residuals_vs_fitted.png) | ![](Mini-Project/Project%20Documents/MACHINERY_FAMILY_Mobile_Field_Machinery_FINAL_quadratic_qqplot.png) | ![](Mini-Project/Project%20Documents/MACHINERY_FAMILY_Mobile_Field_Machinery_FINAL_quadratic_studentized_residuals.png) | ![](Mini-Project/Project%20Documents/MACHINERY_FAMILY_Mobile_Field_Machinery_FINAL_quadratic_leverage.png) |

#### Type — Combine Harvester

| Residuals vs Fitted | Q-Q Plot | Studentized Residuals | Leverage |
|:---:|:---:|:---:|:---:|
| ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Combine_Harvester_FINAL_quadratic_residuals_vs_fitted.png) | ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Combine_Harvester_FINAL_quadratic_qqplot.png) | ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Combine_Harvester_FINAL_quadratic_studentized_residuals.png) | ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Combine_Harvester_FINAL_quadratic_leverage.png) |

#### Type — Four Wheel Tractor

| Residuals vs Fitted | Q-Q Plot | Studentized Residuals | Leverage |
|:---:|:---:|:---:|:---:|
| ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Four_Wheel_Tractor_FINAL_quadratic_residuals_vs_fitted.png) | ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Four_Wheel_Tractor_FINAL_quadratic_qqplot.png) | ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Four_Wheel_Tractor_FINAL_quadratic_studentized_residuals.png) | ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Four_Wheel_Tractor_FINAL_quadratic_leverage.png) |

#### Type — Mechanical Dryer

| Residuals vs Fitted | Q-Q Plot | Studentized Residuals | Leverage |
|:---:|:---:|:---:|:---:|
| ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Mechanical_Dryer_FINAL_quadratic_residuals_vs_fitted.png) | ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Mechanical_Dryer_FINAL_quadratic_qqplot.png) | ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Mechanical_Dryer_FINAL_quadratic_studentized_residuals.png) | ![](Mini-Project/Project%20Documents/MACHINERY_TYPE_Mechanical_Dryer_FINAL_quadratic_leverage.png) |

---

### Interpretability

#### SHAP — Global Feature Importance

<p align="center">
  <img src="Mini-Project/Project%20Documents/shap_summary_bar.png" width="48%" alt="SHAP bar summary"/>
  <img src="Mini-Project/Project%20Documents/shap_summary_beeswarm.png" width="48%" alt="SHAP beeswarm summary"/>
</p>

#### LIME — Local Explanations (sample)

<p align="center">
  <img src="Mini-Project/Project%20Documents/lime_example_0.png" width="32%"/>
  <img src="Mini-Project/Project%20Documents/lime_example_1.png" width="32%"/>
  <img src="Mini-Project/Project%20Documents/lime_example_2.png" width="32%"/>
</p>
<p align="center">
  <img src="Mini-Project/Project%20Documents/lime_example_3.png" width="32%"/>
  <img src="Mini-Project/Project%20Documents/lime_example_4.png" width="32%"/>
  <img src="Mini-Project/Project%20Documents/lime_example_5.png" width="32%"/>
</p>
<p align="center">
  <img src="Mini-Project/Project%20Documents/lime_example_6.png" width="32%"/>
  <img src="Mini-Project/Project%20Documents/lime_example_7.png" width="32%"/>
  <img src="Mini-Project/Project%20Documents/lime_example_8.png" width="32%"/>
</p>

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
