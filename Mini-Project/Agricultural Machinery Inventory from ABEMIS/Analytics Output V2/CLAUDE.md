# Analytics Output V2

This is the **ML training input**. The analytics step in `data/amtec_analytics.py` reads the V3 batch extractions, derives fuel/power metrics, classifies outliers, and writes everything here.

## Files

- `AMTEC_Test_Report_Fuel_Power_Analytics_V2.xlsx` — main file, **20 sheets**
- `AMTEC_Analytics_V2_Summary.txt` — quick stats (3,065 raw → 371 usable L/h records)
- 5 PNG charts: `average_fuel_by_machinery_type.png`, `average_fuel_by_machinery_family.png`, `fuel_intensity_by_machinery_type.png`, `power_vs_fuel_all.png`, `power_vs_fuel_field_machinery.png`

The `AMTEC_Analytics_V2_Summary.txt` was generated on the original developer's machine and references `C:\Users\romer\OneDrive\...` paths — those paths no longer apply; the file has been copied here.

## Sheet map

| Sheet | Rows | Purpose |
|---|---|---|
| **Clean Record Level** | **371** | **★ ML input**: one row per usable test report |
| Summary by Family | 4 | aggregates by machinery family |
| Summary by Dataset | 2 | Field Machinery (104) vs. Stationary/Processing (267) |
| Summary by Machine | 14 | by machinery type |
| By Fixed Power Class | 28 | grouped by fixed kW bins |
| By Within-Type Power | 29 | within-type power tertiles |
| Fuel Intensity Summary | 41 | fuel intensity classes |
| Regression by Machine / Family / Dataset | 14 / 4 / 2 | quick linear regressions |
| Fuel Correlation, Overall Correlation, Correlation by Machine / Family | — | Pearson correlations |
| Outlier Severity | 32 | flagged outliers |
| Pivot Avg Fuel, Pivot Count | — | pivot tables |
| Dataset A Field Machinery, Dataset B Stationary | 104, 267 | filtered subsets |
| Weak Categories | 4 | machinery types with <5 records |

## Clean Record Level — usable columns

29 columns total. Key columns for ML:

**Target:** `fuel_l_per_hr` (371/371 non-null)

**Numeric features (100% complete):**
- `power_kw`, `power_hp`, `year`

**Categorical features:**
- `machinery_family` (4 unique)
- `machinery_type` (14 unique)
- `analysis_subset` (Dataset A / B)
- `fuel_type`, `power_class_fixed`, `power_class_within_machine`, `fuel_intensity_class`

**Sparse features (avoid as required inputs — would drop 78–79% of rows):**
- `field_capacity_value` (80/371 non-null)
- `operating_speed_value` (77/371 non-null)
- `general_capacity_value` (0/371)

**Derived from target — DO NOT use as features (data leakage):**
- `fuel_l_per_kw_hr`, `fuel_l_per_hp_hr`, `kw_per_l_per_hr`
- `fuel_z_score_within_machine`, `fuel_outlier_severity`, `fuel_intensity_class`

**Diagnostic / metadata:**
- `test_report_no`, `brand`, `model`, `source_file`, `source_path`, `rated_power_raw`, `fuel_consumption_raw`
