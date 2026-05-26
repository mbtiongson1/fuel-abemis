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
OUTPUT_EXCEL = OUTPUT_DIR / "RF_Predictions.xlsx"

TARGET_COL   = "fuel_l_per_hr"
FEATURE_COLS: list[str] = [
    "power_kw",
    # Add additional features here as needed, e.g.:
    # "field_capacity_value",
    # "operating_speed_value",
]


def load_data() -> pd.DataFrame:
    df = pd.read_excel(INPUT_FILE, sheet_name="Clean Record Level")
    required = [TARGET_COL] + FEATURE_COLS
    df = df.dropna(subset=required).copy()
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)
    return df


def train(df: pd.DataFrame):
    """Fit and return a trained RandomForestRegressor."""
    from sklearn.ensemble import RandomForestRegressor

    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=None,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)
    return model


def evaluate(model, df: pd.DataFrame) -> dict:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    X = df[FEATURE_COLS].values
    y = df[TARGET_COL].values
    pred = model.predict(X)
    return {
        "r2": r2_score(y, pred),
        "mae": mean_absolute_error(y, pred),
        "rmse": np.sqrt(mean_squared_error(y, pred)),
    }


def save_model(model, path: Path = MODEL_FILE):
    import pickle
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print("Model saved:", path)


def load_model(path: Path = MODEL_FILE):
    import pickle
    with open(path, "rb") as f:
        return pickle.load(f)


def run():
    df = load_data()
    print("Training records:", len(df))

    model = train(df)
    metrics = evaluate(model, df)
    print("Train metrics:", metrics)

    save_model(model)

    df["rf_predicted_fuel_l_hr"] = model.predict(df[FEATURE_COLS].values)
    df["rf_residual"] = df[TARGET_COL] - df["rf_predicted_fuel_l_hr"]

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="RF Predictions", index=False)
        pd.DataFrame([metrics]).to_excel(writer, sheet_name="Metrics", index=False)

    print("Predictions saved:", OUTPUT_EXCEL)
    return model, metrics


if __name__ == "__main__":
    config.create_output_dirs()
    run()
