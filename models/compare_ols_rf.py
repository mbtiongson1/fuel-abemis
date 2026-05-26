"""
Head-to-head OLS vs RF comparison on a *single* held-out test set.

The existing OLS pipeline (`models.ols_regression`) fits its hierarchy on the
full 378-record dataset, while RF reports metrics on a 76-row holdout. That is
not an apples-to-apples comparison. This module fixes that: same train/test
split (random_state=42, test_size=0.2) is used to fit both models, and both
predict the *same* 76 holdout rows.

Three contenders:
    - RF                — the full 8-feature random forest
    - OLS Global Linear — single intercept + slope on power_kw
    - OLS Hierarchical  — per-type linear if n_train ≥ 15, else per-family,
                          else global. Mirrors the fallback logic in
                          `models.ols_regression` but in a self-contained,
                          train/test-aware form.

Output: `OLS_vs_RF_Comparison.xlsx` in `AMTEC_REGRESSION_DIR`, with sheets
    - Comparison Metrics    (one row per model)
    - Per-Record Predictions (76 rows × {actual, rf_pred, ols_global_pred, ols_hier_pred})
    - OLS Hierarchy         (per-type level used + train n)

Run as:
    python -m models.compare_ols_rf
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

import config
from config import AMTEC_REGRESSION_DIR
from models.random_forest import (
    CATEGORICAL_FEATURES,
    FEATURE_COLS,
    NUMERIC_FEATURES,
    RANDOM_STATE,
    TARGET_COL,
    TEST_SIZE,
    load_data,
)

OUTPUT_EXCEL = AMTEC_REGRESSION_DIR / "OLS_vs_RF_Comparison.xlsx"

POWER_COL    = "power_kw"
MIN_GROUP_N  = 15  # min train rows to fit a per-type/family OLS before falling back


def _fit_ols(train: pd.DataFrame):
    """Fit OLS: y = b0 + b1·power_kw on train. Returns callable predict(power_kw)."""
    X = sm.add_constant(train[[POWER_COL]].astype(float), has_constant="add")
    y = train[TARGET_COL].astype(float)
    model = sm.OLS(y, X).fit()

    def predict(power_kw_array):
        x = pd.DataFrame({POWER_COL: np.asarray(power_kw_array, dtype=float)})
        x = sm.add_constant(x, has_constant="add")
        # statsmodels needs the column order matched
        x = x[["const", POWER_COL]]
        return model.predict(x).values

    return model, predict


def fit_hierarchical_ols(train: pd.DataFrame):
    """Fit per-type, per-family, and global OLS on train. Return predictors + level map."""
    _, global_pred = _fit_ols(train)

    family_predictors = {}
    for family, g in train.groupby("machinery_family"):
        if len(g) >= MIN_GROUP_N and g[POWER_COL].nunique() >= 2:
            _, family_predictors[family] = _fit_ols(g)

    type_predictors = {}
    for mtype, g in train.groupby("machinery_type"):
        if len(g) >= MIN_GROUP_N and g[POWER_COL].nunique() >= 2:
            _, type_predictors[mtype] = _fit_ols(g)

    def predict_row(row):
        if row["machinery_type"] in type_predictors:
            return type_predictors[row["machinery_type"]]([row[POWER_COL]])[0], "MACHINERY_TYPE"
        if row["machinery_family"] in family_predictors:
            return family_predictors[row["machinery_family"]]([row[POWER_COL]])[0], "MACHINERY_FAMILY"
        return global_pred([row[POWER_COL]])[0], "GLOBAL"

    # Level map (per machinery_type → which level was used + train n)
    level_rows = []
    for mtype in sorted(train["machinery_type"].dropna().unique()):
        family = train.loc[train["machinery_type"] == mtype, "machinery_family"].dropna().iloc[0]
        if mtype in type_predictors:
            level = "MACHINERY_TYPE"
        elif family in family_predictors:
            level = "MACHINERY_FAMILY"
        else:
            level = "GLOBAL"
        level_rows.append({
            "machinery_type": mtype,
            "machinery_family": family,
            "level_used": level,
            "n_train_type": int((train["machinery_type"] == mtype).sum()),
            "n_train_family": int((train["machinery_family"] == family).sum()),
        })

    return predict_row, pd.DataFrame(level_rows)


def _metrics(y_true, y_pred, label, n):
    return {
        "model": label,
        "n_test": int(n),
        "r2":   r2_score(y_true, y_pred),
        "mae":  mean_absolute_error(y_true, y_pred),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
    }


def run():
    df, _encoders = load_data()
    print(f"Records after preprocessing: {len(df)}")

    train_idx, test_idx = train_test_split(df.index, test_size=TEST_SIZE, random_state=RANDOM_STATE)
    train_df = df.loc[train_idx].copy()
    test_df  = df.loc[test_idx].copy()
    print(f"Train: {len(train_df)}    Test: {len(test_df)}")

    # --- RF ---
    rf = RandomForestRegressor(
        n_estimators=300, max_depth=None, min_samples_split=5,
        min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1,
    )
    rf.fit(train_df[FEATURE_COLS].values, train_df[TARGET_COL].values)
    rf_pred = rf.predict(test_df[FEATURE_COLS].values)
    if config.CLIP_NEGATIVE_PREDICTIONS:
        rf_pred = np.clip(rf_pred, 0, None)

    # --- OLS Global Linear ---
    _, ols_global_pred_fn = _fit_ols(train_df)
    ols_global_pred = ols_global_pred_fn(test_df[POWER_COL].values)
    if config.CLIP_NEGATIVE_PREDICTIONS:
        ols_global_pred = np.clip(ols_global_pred, 0, None)

    # --- OLS Hierarchical ---
    predict_row, level_df = fit_hierarchical_ols(train_df)
    hier_results = test_df.apply(predict_row, axis=1, result_type="expand")
    ols_hier_pred = hier_results[0].values.astype(float)
    ols_hier_level = hier_results[1].values
    if config.CLIP_NEGATIVE_PREDICTIONS:
        ols_hier_pred = np.clip(ols_hier_pred, 0, None)

    y_test = test_df[TARGET_COL].values

    metrics_df = pd.DataFrame([
        _metrics(y_test, rf_pred,         "RF (8 features)",      len(y_test)),
        _metrics(y_test, ols_global_pred, "OLS Global Linear",    len(y_test)),
        _metrics(y_test, ols_hier_pred,   "OLS Hierarchical",     len(y_test)),
    ])
    print("\nComparison on identical 76-row holdout:")
    print(metrics_df.to_string(index=False))

    per_record = pd.DataFrame({
        "machinery_type":   test_df["machinery_type"].values,
        "machinery_family": test_df["machinery_family"].values,
        "power_kw":         test_df["power_kw"].values,
        "actual":           y_test,
        "rf_pred":          rf_pred,
        "ols_global_pred":  ols_global_pred,
        "ols_hier_pred":    ols_hier_pred,
        "ols_hier_level":   ols_hier_level,
    })

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        metrics_df.to_excel(writer, sheet_name="Comparison Metrics", index=False)
        per_record.to_excel(writer, sheet_name="Per-Record Predictions", index=False)
        level_df.to_excel(writer, sheet_name="OLS Hierarchy", index=False)

    print("Saved:", OUTPUT_EXCEL)
    return metrics_df


if __name__ == "__main__":
    config.create_output_dirs()
    run()
