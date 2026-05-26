"""
Random Forest regressor for fuel consumption prediction.

Inputs  : AMTEC_Test_Report_Fuel_Power_Analytics_V2.xlsx  (Clean Record Level sheet)
Outputs : rf_model.pkl, RF_Predictions.xlsx
"""

from pathlib import Path

import numpy as np
import pandas as pd

import config
from config import AMTEC_ANALYTICS_DIR, AMTEC_REGRESSION_DIR

INPUT_FILE   = AMTEC_ANALYTICS_DIR  / "AMTEC_Test_Report_Fuel_Power_Analytics_V2.xlsx"
OUTPUT_DIR   = AMTEC_REGRESSION_DIR
MODEL_FILE   = OUTPUT_DIR / "rf_model.pkl"
ENCODER_FILE = OUTPUT_DIR / "rf_encoders.pkl"
OUTPUT_EXCEL = OUTPUT_DIR / "RF_Predictions.xlsx"

TARGET_COL = "fuel_l_per_hr"

# Numeric features kept as-is.
NUMERIC_FEATURES: list[str] = [
    "power_kw",
    "year",
    "abemis_total_count",
    "abemis_region_breadth",
    "abemis_dominant_region_share",
]

# Categorical features encoded as integer labels (RF handles label-encoded categoricals).
CATEGORICAL_FEATURES: list[str] = [
    "machinery_type",
    "machinery_family",
    "analysis_subset",
]

FEATURE_COLS: list[str] = NUMERIC_FEATURES + [f"{c}_code" for c in CATEGORICAL_FEATURES]

TEST_SIZE     = 0.2
RANDOM_STATE  = 42


def load_data() -> tuple[pd.DataFrame, dict]:
    """Load Clean Record Level, encode categoricals, return (df, encoders)."""
    df = pd.read_excel(INPUT_FILE, sheet_name="Clean Record Level")

    required_raw = [TARGET_COL] + NUMERIC_FEATURES + CATEGORICAL_FEATURES
    df = df.dropna(subset=required_raw).copy()

    for col in [TARGET_COL] + NUMERIC_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[TARGET_COL] + NUMERIC_FEATURES)

    encoders: dict[str, dict] = {}
    for col in CATEGORICAL_FEATURES:
        cats = sorted(df[col].astype(str).unique())
        mapping = {v: i for i, v in enumerate(cats)}
        df[f"{col}_code"] = df[col].astype(str).map(mapping).astype(int)
        encoders[col] = mapping

    return df, encoders


def train(df: pd.DataFrame):
    """Fit and return a trained RandomForestRegressor on a train split."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split

    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model, (X_train, X_test, y_train, y_test)


def evaluate(model, X, y) -> dict:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    pred = model.predict(X)
    return {
        "r2":   r2_score(y, pred),
        "mae":  mean_absolute_error(y, pred),
        "rmse": np.sqrt(mean_squared_error(y, pred)),
    }


def cross_validate_rf(df: pd.DataFrame, n_splits: int = 5) -> pd.DataFrame:
    """k-fold CV on the full preprocessed dataset; returns per-fold + aggregate metrics."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.model_selection import KFold

    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    rows = []
    for fold_idx, (train_idx, test_idx) in enumerate(kf.split(X), start=1):
        m = RandomForestRegressor(
            n_estimators=300, max_depth=None, min_samples_split=5,
            min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1,
        )
        m.fit(X[train_idx], y[train_idx])
        pred = m.predict(X[test_idx])
        rows.append({
            "fold": fold_idx,
            "n_train": len(train_idx),
            "n_test":  len(test_idx),
            "r2":      r2_score(y[test_idx], pred),
            "mae":     mean_absolute_error(y[test_idx], pred),
            "rmse":    np.sqrt(mean_squared_error(y[test_idx], pred)),
        })

    folds = pd.DataFrame(rows)
    summary = pd.DataFrame([
        {"fold": "mean", "n_train": folds["n_train"].mean(), "n_test": folds["n_test"].mean(),
         "r2": folds["r2"].mean(),  "mae": folds["mae"].mean(),  "rmse": folds["rmse"].mean()},
        {"fold": "std",  "n_train": folds["n_train"].std(),  "n_test": folds["n_test"].std(),
         "r2": folds["r2"].std(),   "mae": folds["mae"].std(),   "rmse": folds["rmse"].std()},
    ])
    return pd.concat([folds, summary], ignore_index=True)


def per_type_residuals(df_test: pd.DataFrame, y_true, y_pred) -> pd.DataFrame:
    """Group holdout residuals by machinery_type → count, mean residual, MAE, RMSE."""
    out = df_test[["machinery_type"]].copy()
    out["actual"]   = y_true
    out["pred"]     = y_pred
    out["residual"] = out["actual"] - out["pred"]
    grouped = out.groupby("machinery_type").agg(
        n=("residual", "size"),
        mean_actual=("actual", "mean"),
        mean_pred=("pred", "mean"),
        mean_residual=("residual", "mean"),
        mae=("residual", lambda r: r.abs().mean()),
        rmse=("residual", lambda r: float(np.sqrt((r ** 2).mean()))),
    ).reset_index().sort_values("n", ascending=False)
    return grouped


def save_model(model, encoders, model_path: Path = MODEL_FILE, enc_path: Path = ENCODER_FILE):
    import pickle
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    with open(enc_path, "wb") as f:
        pickle.dump({"encoders": encoders, "feature_cols": FEATURE_COLS}, f)
    print("Model saved:", model_path)
    print("Encoders saved:", enc_path)


def load_model(path: Path = MODEL_FILE):
    import pickle
    with open(path, "rb") as f:
        return pickle.load(f)


def run():
    df, encoders = load_data()
    print(f"Records after preprocessing: {len(df)}")
    print(f"Features ({len(FEATURE_COLS)}):", FEATURE_COLS)

    model, (X_train, X_test, y_train, y_test) = train(df)

    train_metrics = evaluate(model, X_train, y_train)
    test_metrics  = evaluate(model, X_test, y_test)
    print("Train metrics:", train_metrics)
    print("Test metrics: ", test_metrics)

    cv_df = cross_validate_rf(df, n_splits=5)
    print("CV (5-fold) mean R²/MAE/RMSE:",
          float(cv_df.loc[cv_df["fold"] == "mean", "r2"].iloc[0]),
          float(cv_df.loc[cv_df["fold"] == "mean", "mae"].iloc[0]),
          float(cv_df.loc[cv_df["fold"] == "mean", "rmse"].iloc[0]))

    save_model(model, encoders)

    df["rf_predicted_fuel_l_hr"] = model.predict(df[FEATURE_COLS].values)
    if config.CLIP_NEGATIVE_PREDICTIONS:
        df["rf_predicted_fuel_l_hr"] = df["rf_predicted_fuel_l_hr"].clip(lower=0)
    df["rf_residual"] = df[TARGET_COL] - df["rf_predicted_fuel_l_hr"]
    df["rf_abs_residual"] = df["rf_residual"].abs()
    df["rf_pct_error"] = np.where(
        df[TARGET_COL] != 0,
        df["rf_abs_residual"] / df[TARGET_COL] * 100,
        np.nan,
    )

    # Recover the holdout rows so we can break residuals down by machinery_type.
    from sklearn.model_selection import train_test_split
    df_train_idx, df_test_idx = train_test_split(
        df.index, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    df_test = df.loc[df_test_idx]
    test_pred = model.predict(df_test[FEATURE_COLS].values)
    if config.CLIP_NEGATIVE_PREDICTIONS:
        test_pred = np.clip(test_pred, 0, None)
    per_type_df = per_type_residuals(df_test, df_test[TARGET_COL].values, test_pred)

    importances = pd.DataFrame({
        "feature": FEATURE_COLS,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)

    metrics_df = pd.DataFrame([
        {"split": "train", **train_metrics, "n": len(y_train)},
        {"split": "test",  **test_metrics,  "n": len(y_test)},
        {"split": "all",   **evaluate(model, df[FEATURE_COLS].values, df[TARGET_COL].values), "n": len(df)},
    ])

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="RF Predictions", index=False)
        metrics_df.to_excel(writer, sheet_name="Metrics", index=False)
        cv_df.to_excel(writer, sheet_name="CV Metrics", index=False)
        per_type_df.to_excel(writer, sheet_name="Per-Type Residuals", index=False)
        importances.to_excel(writer, sheet_name="Feature Importance", index=False)
        for col, mapping in encoders.items():
            pd.DataFrame(
                [{"category": k, "code": v} for k, v in mapping.items()]
            ).to_excel(writer, sheet_name=f"Encoder {col}"[:31], index=False)

    print("Predictions saved:", OUTPUT_EXCEL)
    return model, {"train": train_metrics, "test": test_metrics,
                   "cv_mean_r2":  float(cv_df.loc[cv_df["fold"] == "mean", "r2"].iloc[0]),
                   "cv_std_r2":   float(cv_df.loc[cv_df["fold"] == "std",  "r2"].iloc[0])}


if __name__ == "__main__":
    config.create_output_dirs()
    run()
