# analysis/

Explainability for the trained Random Forest. Both modules require `rf_model.pkl` and `rf_encoders.pkl` (produced by `models.random_forest`) to exist before they can run.

## Files

| File | Status | Notes |
|---|---|---|
| `shap_analysis.py` | done, run | TreeExplainer on RF; produces global feature importance + summary plots |
| `lime_explanations.py` | done, run | Per-instance local explanations on 10 sampled records |
| `__init__.py` | empty | package marker |

## How to run

```bash
python -m analysis.shap_analysis
python -m analysis.lime_explanations
```

Both reuse `models.random_forest.load_data()` so the same categorical encoding is applied to the explanation set.

## Outputs (in `AMTEC_REGRESSION_DIR`)

- `SHAP_Analysis.xlsx` — 2 sheets: `Feature Importance` (mean |SHAP| per feature) and `SHAP Values Per Record` (one column per feature)
- `shap_summary_bar.png`, `shap_summary_beeswarm.png`
- `LIME_Explanations.xlsx` — one row per sampled instance with feature contributions
- `lime_example_0.png` ... `lime_example_9.png` — per-instance plots

## LIME categorical handling

`LimeTabularExplainer` is initialized with `categorical_features` (positional indices) and `categorical_names` (the original string categories from the encoders). This makes the explanation plots show readable labels like `machinery_type=Thresher` instead of raw integer codes.

To change the number of explained instances: pass `n_samples=N` to `run()` or change the module-level `N_SAMPLES = 10`.

## Latest results

SHAP global importance (mean |SHAP|): `power_kw` 3.63 → `year` 0.65 → `machinery_type_code` 0.27 → `machinery_family_code` 0.21 → `analysis_subset_code` 0.07. Same ordering as RF feature importance, which is reassuring.
