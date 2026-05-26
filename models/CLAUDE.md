# models/

Modeling code: OLS baseline + Random Forest. Both have been run end-to-end on the 378-record "Clean Record Level" sheet.

## Files

| File | Status | Notes |
|---|---|---|
| `ols_regression.py` | done, run | Hierarchical OLS (GLOBAL → FAMILY → TYPE × linear/quadratic/log_response). Two-pass: identifies extreme outliers in pass 1, refits in pass 2. |
| `random_forest.py` | done, run | RandomForestRegressor; 80/20 train-test split; saves `rf_model.pkl` + `rf_encoders.pkl`. |
| `__init__.py` | empty | package marker |

Both write outputs to `AMTEC_REGRESSION_DIR` (`Mini-Project/Agricultural Machinery Inventory from ABEMIS/Regression Parameters Output V3/`).

## How to run

Run as **modules** from the repo root (so `import config` resolves):

```bash
python -m models.ols_regression
python -m models.random_forest
```

`python models/ols_regression.py` will fail with `ModuleNotFoundError: config` because Python adds the script directory (`models/`) to `sys.path`, not the cwd.

## Random Forest features

```python
NUMERIC_FEATURES     = ["power_kw", "year", "abemis_total_count", "abemis_region_breadth", "abemis_dominant_region_share"]
CATEGORICAL_FEATURES = ["machinery_type", "machinery_family", "analysis_subset"]
FEATURE_COLS         = NUMERIC_FEATURES + [f"{c}_code" for c in CATEGORICAL_FEATURES]
```

Categoricals are integer-label encoded inside `load_data()`. The encoder dict is saved to `rf_encoders.pkl` and exported to per-encoder sheets in `RF_Predictions.xlsx`. The three `abemis_*` numeric features come from the join performed in `data/amtec_analytics.py` against `Analytics Output V2/abemis_machinery_context.xlsx` (built by `data/abemis_context_features.py`).

To extend: add to `NUMERIC_FEATURES` or `CATEGORICAL_FEATURES` only. The pipeline picks the rest up automatically. Sparse columns like `field_capacity_value` (80/378) and `operating_speed_value` (77/378) will collapse the dataset; if you add them, expect ~80 records to survive.

## Latest test metrics (76 holdout records)

R² = 0.91, MAE = 1.09 L/h, RMSE = 1.61 L/h. Feature importance: `power_kw` 76.2%, `year` ~12%, ABEMIS context features ~3.5% combined; remaining ~8% split across the three categorical-coded features.

## OLS structure

For each (scope, form) combination, `fit_regression()` returns: model_summary, coefficients, ANOVA, per-observation diagnostics. `MIN_ACCEPTABLE_R2 = 0.50` (adjusted) filters weak models. The `Fallback Hierarchy` sheet lists the recommended scope per machinery type:

- 4 types model at MACHINERY_TYPE level (Combine Harvester, Four-Wheel Tractor, Mechanical Dryer, plus the Mobile Field umbrella)
- 6 types fall back to MACHINERY_FAMILY (Mobile Field Machinery)
- 4 types fall back to GLOBAL (Rice Mill, Sheller, Small Engine, Thresher, Water Pump)
