# analysis/

Explainability for the trained Random Forest. Both modules require `rf_model.pkl` and `rf_encoders.pkl` (produced by `models.random_forest`) to exist before they can run.

## Files

| File | Status | Notes |
|---|---|---|
| `shap_analysis.py` | done, run | TreeExplainer on RF; produces global feature importance + summary plots |
| `lime_explanations.py` | done, run | Per-instance local explanations on 10 sampled records |
| `abemis_fuel_scoring.py` | done, run | Applies trained RF to all 246,741 fuel-relevant ABEMIS deployments → regional fuel estimates |
| `__init__.py` | empty | package marker |

## How to run

```bash
python -m analysis.shap_analysis
python -m analysis.lime_explanations
python -m analysis.abemis_fuel_scoring
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

SHAP global importance now reflects the 8-feature model (5 numeric + 3 categorical-encoded). Top driver remains `power_kw` (76.2% RF importance). The three ABEMIS context features (`abemis_total_count`, `abemis_region_breadth`, `abemis_dominant_region_share`) contribute ~3.5% combined — small but consistent.

## ABEMIS regional scoring

`abemis_fuel_scoring.py` loads `rf_model.pkl` + `rf_encoders.pkl` and predicts `fuel_l_per_hr` for every fuel-relevant ABEMIS deployment. Output: `Regression Parameters Output V3/ABEMIS_Regional_Fuel_Estimates.xlsx` with 4 sheets — Per Record, Per Region, Per Region × Type, Status Summary. Of 246,741 fuel-relevant ABEMIS records, 172,265 (70%) are predictable; the rest are excluded due to missing power (62,808) or unmappable type (11,668). Power parsing handles the free-text `Rated Power` column ("75 hp", "10kW", "75 hp/55 kW", etc.).

## RAED dependency (planned)

B2 regional scoring module (not yet written) will combine B1 model outputs with RAED seasonal demand: `is_in_season` (binary) and `crop_stage_intensity` (0–1). The RAED data pipeline (`data/raed_cropping_calendar.py`) will produce `raed_seasonal_demand.xlsx` keyed by (machinery_type, region, month). B2 reuses the same RF encoder pickles (`rf_encoders.pkl`) to ensure consistent machinery_type mapping.

