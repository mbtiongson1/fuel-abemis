"""
Apply the trained Random Forest model to ABEMIS fuel-relevant deployment records
and aggregate predicted fuel rates by region.

Inputs  : ABEMIS_Fuel_vs_NoFuel_Machinery_V2.xlsx  (Fuel Relevant sheet)
          rf_model.pkl, rf_encoders.pkl             (from models.random_forest)
          abemis_machinery_context.xlsx             (from data.abemis_context_features)
Outputs : ABEMIS_Regional_Fuel_Estimates.xlsx
            - Per Record         : full per-deployment predictions
            - Per Region         : region-level aggregates
            - Per Region x Type  : region × machinery_type breakdown
            - Status Summary     : counts by prediction_status

DO NOT run this module until the RF model has been retrained with the
abemis context features (abemis_total_count, abemis_region_breadth,
abemis_dominant_region_share) included in NUMERIC_FEATURES.
"""

import logging
import pickle
import re
from pathlib import Path

import numpy as np
import pandas as pd

import config
from config import ABEMIS_FUEL_DIR, AMTEC_ANALYTICS_DIR, AMTEC_REGRESSION_DIR
from data.abemis_context_features import map_abemis_to_amtec_type
from data.amtec_analytics import classify_machinery_family, classify_analysis_subset

logger = logging.getLogger(__name__)

CLASSIFIER_XLSX  = ABEMIS_FUEL_DIR   / "ABEMIS_Fuel_vs_NoFuel_Machinery_V2.xlsx"
CONTEXT_XLSX     = AMTEC_ANALYTICS_DIR / "abemis_machinery_context.xlsx"
MODEL_FILE       = AMTEC_REGRESSION_DIR / "rf_model.pkl"
ENCODER_FILE     = AMTEC_REGRESSION_DIR / "rf_encoders.pkl"
OUTPUT_EXCEL     = AMTEC_REGRESSION_DIR / "ABEMIS_Regional_Fuel_Estimates.xlsx"

HP_TO_KW = 0.7457


# ── Rated Power parsing ───────────────────────────────────────────────────────

# Matches patterns such as:
#   "75"          → 75 (unit unknown, assumed kW based on context)
#   "75 hp"       → 75 hp → 55.93 kW
#   "5.5 HP"      → 5.5 hp
#   "10kW"        → 10 kW
#   "55 kW"       → 55 kW
#   "75 hp/55 kW" → prefers explicit kW if present, else converts hp
#   "37.3kw"      → 37.3 kW
_POWER_RE = re.compile(
    r"(?P<kw_val>\d+(?:\.\d+)?)\s*kw"        # explicit kW value
    r"|(?P<hp_val>\d+(?:\.\d+)?)\s*hp"        # explicit hp value
    r"|^(?P<bare>\d+(?:\.\d+)?)$",            # bare numeric (treated as kW)
    re.IGNORECASE,
)


def parse_rated_power_kw(raw) -> float | None:
    """
    Parse a Rated Power value to kW.

    Handles:
        float/int → returned as-is (assumed kW, consistent with ABEMIS column semantics)
        "75 hp"   → 55.93 kW
        "10kW"    → 10.0 kW
        "75 hp/55 kW" → 55.0 kW  (explicit kW wins)
        "75"      → 75.0 kW      (bare number, treated as kW)

    Returns None if the value is missing, zero, or unparseable.
    """
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return None

    # Numeric types: ABEMIS Rated Power column is typically float64 already
    if isinstance(raw, (int, float, np.floating, np.integer)):
        val = float(raw)
        return val if val > 0 else None

    text = str(raw).strip()
    if not text:
        return None

    # Search for all kW and hp mentions in the string; kW takes precedence
    kw_matches  = re.findall(r"(\d+(?:\.\d+)?)\s*kw", text, re.IGNORECASE)
    hp_matches  = re.findall(r"(\d+(?:\.\d+)?)\s*hp", text, re.IGNORECASE)
    bare_matches = re.findall(r"^\s*(\d+(?:\.\d+)?)\s*$", text)

    if kw_matches:
        val = float(kw_matches[0])
        return val if val > 0 else None
    if hp_matches:
        val = float(hp_matches[0]) * HP_TO_KW
        return val if val > 0 else None
    if bare_matches:
        val = float(bare_matches[0])
        return val if val > 0 else None

    return None


# ── Data loading ──────────────────────────────────────────────────────────────

def load_abemis_records(classifier_xlsx_path) -> pd.DataFrame:
    """
    Load Fuel Relevant ABEMIS rows.

    Keeps: Region, Year Funded, Rated Power, Machine Name, inferred_region,
           machine_name_for_classification, source_file.

    Uses the 'Region' column from the original ABEMIS data as the primary region
    identifier; falls back to 'inferred_region' (filename-parsed) where Region is
    missing.
    """
    df = pd.read_excel(classifier_xlsx_path, sheet_name="Fuel Relevant")

    # Normalise region: prefer the full Region column, fall back to inferred
    if "Region" in df.columns:
        df["region"] = df["Region"].where(df["Region"].notna(), df.get("inferred_region"))
    else:
        df["region"] = df.get("inferred_region")

    keep_cols = [
        "machine_name_for_classification",
        "Region", "region", "inferred_region",
        "Rated Power", "Year Funded",
        "source_file",
        "Province", "Municipality",
    ]
    available = [c for c in keep_cols if c in df.columns]
    return df[available].copy()


# ── Feature matrix construction ───────────────────────────────────────────────

def build_feature_matrix(
    df_abemis: pd.DataFrame,
    encoders: dict,
    feature_cols: list[str],
) -> tuple[np.ndarray, pd.DataFrame]:
    """
    Map ABEMIS records to the RF feature space.

    Adds a 'prediction_status' column:
        'ok'             — all features resolved, ready for prediction
        'missing_power'  — Rated Power absent or zero; excluded from aggregates
        'missing_year'   — Year Funded invalid; year imputed with training median
        'unmappable_type'— machine name did not match any AMTEC type; excluded

    Also adds resolved columns: power_kw, year, machinery_type,
    machinery_family, analysis_subset, abemis context features.

    Returns (X, df_out) where X is only the rows with status in
    ('ok', 'missing_year') and df_out is the full annotated frame.
    """
    df = df_abemis.copy()

    # ── power_kw ─────────────────────────────────────────────────────────────
    df["power_kw"] = df["Rated Power"].apply(parse_rated_power_kw)

    # ── year ─────────────────────────────────────────────────────────────────
    df["year"] = pd.to_numeric(df["Year Funded"], errors="coerce")

    # ── machinery_type via keyword mapping ───────────────────────────────────
    df["machinery_type"] = df["machine_name_for_classification"].apply(
        map_abemis_to_amtec_type
    )

    # ── machinery_family and analysis_subset ─────────────────────────────────
    # Reuse the same classification functions used in amtec_analytics.py
    # to guarantee identical family/subset labels between training and inference.
    df["machinery_family"] = df["machinery_type"].apply(classify_machinery_family)
    df["analysis_subset"]  = df["machinery_type"].apply(classify_analysis_subset)

    # ── ABEMIS context features (per-machinery-type lookup) ──────────────────
    if CONTEXT_XLSX.exists():
        context = pd.read_excel(CONTEXT_XLSX)
        df = df.merge(context, on="machinery_type", how="left")
    else:
        # Provide NaN columns so downstream code doesn't break;
        # scoring will still fail for these rows via missing numeric check.
        logger.warning(
            "abemis_machinery_context.xlsx not found — context features will be NaN. "
            "Run: python -m data.abemis_context_features"
        )
        for col in ("abemis_total_count", "abemis_region_breadth", "abemis_dominant_region_share"):
            df[col] = np.nan

    # ── Assign prediction_status ─────────────────────────────────────────────
    # Order matters: most-severe exclusion wins.
    df["prediction_status"] = "ok"
    df.loc[df["machinery_type"].isna(),    "prediction_status"] = "unmappable_type"
    df.loc[df["power_kw"].isna(),          "prediction_status"] = "missing_power"
    # missing_year is non-excluding: impute and flag rather than drop
    year_missing = df["year"].isna()
    if year_missing.any():
        median_year = df["year"].median()
        if pd.isna(median_year):
            median_year = 2018.0  # hard fallback if all years are missing
        df.loc[year_missing, "year"]               = median_year
        # Only override status if it is currently 'ok'
        df.loc[year_missing & (df["prediction_status"] == "ok"), "prediction_status"] = "missing_year"

    # ── Build X for predictable rows ─────────────────────────────────────────
    predictable_mask = df["prediction_status"].isin(["ok", "missing_year"])
    df_pred = df[predictable_mask].copy()

    # Encode categoricals using saved encoder mappings.
    # Unknown categories get code 0 (the most common sentinel) because the RF
    # was trained with integer codes and silently handles unseen values this way;
    # forcing NaN would cause silent row drops instead of explicit flagging.
    for col in ("machinery_type", "machinery_family", "analysis_subset"):
        mapping = encoders.get(col, {})
        code_col = f"{col}_code"
        df_pred[code_col] = df_pred[col].astype(str).map(mapping).fillna(0).astype(int)
        df[code_col] = np.nan  # placeholder so df_out has the column

    # Write codes back to the full df for reference
    for col in ("machinery_type", "machinery_family", "analysis_subset"):
        code_col = f"{col}_code"
        df.loc[predictable_mask, code_col] = df_pred[code_col].values

    # Build the numeric feature matrix respecting feature_cols order
    # Coerce all feature columns to numeric to catch any stray strings
    for fc in feature_cols:
        if fc in df_pred.columns:
            df_pred[fc] = pd.to_numeric(df_pred[fc], errors="coerce")

    X = df_pred[feature_cols].values.astype(float)

    return X, df


# ── Full scoring pipeline ─────────────────────────────────────────────────────

def score(
    model_path=MODEL_FILE,
    encoder_path=ENCODER_FILE,
    classifier_xlsx_path=CLASSIFIER_XLSX,
    output_xlsx_path=OUTPUT_EXCEL,
):
    """
    Full pipeline: load records → build features → predict → aggregate → save xlsx.

    Only rows with prediction_status in ('ok', 'missing_year') receive predictions.
    Rows with 'missing_power' or 'unmappable_type' are retained in Per Record with
    NaN predicted_fuel_l_hr and excluded from all aggregates.
    """
    # Load model and encoders
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(encoder_path, "rb") as f:
        enc_payload = pickle.load(f)
    encoders     = enc_payload["encoders"]
    feature_cols = enc_payload["feature_cols"]

    # Load ABEMIS records
    df_abemis = load_abemis_records(classifier_xlsx_path)
    logger.info("Loaded %d fuel-relevant ABEMIS records", len(df_abemis))

    # Build feature matrix
    X, df_out = build_feature_matrix(df_abemis, encoders, feature_cols)

    # Predict only on rows that have a feature matrix entry
    predictable_mask = df_out["prediction_status"].isin(["ok", "missing_year"])
    predicted = model.predict(X)
    if config.CLIP_NEGATIVE_PREDICTIONS:
        predicted = predicted.clip(min=0)

    df_out["predicted_fuel_l_hr"] = np.nan
    df_out.loc[predictable_mask, "predicted_fuel_l_hr"] = predicted

    # ── Per Record sheet ─────────────────────────────────────────────────────
    per_record_cols = [
        "region", "Province", "Municipality",
        "machine_name_for_classification",
        "Year Funded", "year", "Rated Power", "power_kw",
        "machinery_type", "machinery_family", "analysis_subset",
        "abemis_total_count", "abemis_region_breadth", "abemis_dominant_region_share",
        "predicted_fuel_l_hr", "prediction_status",
        "source_file",
    ]
    per_record = df_out[[c for c in per_record_cols if c in df_out.columns]].copy()

    # ── Per Region sheet ─────────────────────────────────────────────────────
    df_agg = df_out[predictable_mask & df_out["predicted_fuel_l_hr"].notna()].copy()

    per_region = (
        df_agg
        .groupby("region", dropna=False)
        .agg(
            record_count         =("predicted_fuel_l_hr", "count"),
            mean_predicted_l_hr  =("predicted_fuel_l_hr", "mean"),
            median_predicted_l_hr=("predicted_fuel_l_hr", "median"),
            # Sum treats all machines as running simultaneously — an upper bound.
            sum_predicted_l_hr   =("predicted_fuel_l_hr", "sum"),
        )
        .reset_index()
        .sort_values("sum_predicted_l_hr", ascending=False)
    )

    # ── Per Region x Type sheet ───────────────────────────────────────────────
    per_region_type = (
        df_agg
        .groupby(["region", "machinery_type"], dropna=False)
        .agg(
            record_count         =("predicted_fuel_l_hr", "count"),
            mean_predicted_l_hr  =("predicted_fuel_l_hr", "mean"),
            sum_predicted_l_hr   =("predicted_fuel_l_hr", "sum"),
        )
        .reset_index()
        .sort_values(["region", "sum_predicted_l_hr"], ascending=[True, False])
    )

    # ── Status Summary sheet ──────────────────────────────────────────────────
    status_summary = (
        df_out["prediction_status"]
        .value_counts()
        .rename_axis("prediction_status")
        .reset_index(name="count")
    )

    # ── Save ─────────────────────────────────────────────────────────────────
    with pd.ExcelWriter(output_xlsx_path, engine="openpyxl") as writer:
        per_record.to_excel(writer,       sheet_name="Per Record",        index=False)
        per_region.to_excel(writer,       sheet_name="Per Region",        index=False)
        per_region_type.to_excel(writer,  sheet_name="Per Region x Type", index=False)
        status_summary.to_excel(writer,   sheet_name="Status Summary",    index=False)

    print("ABEMIS fuel estimates saved to:", output_xlsx_path)
    print()
    print("Status summary:")
    print(status_summary.to_string(index=False))
    print()
    print(f"Predictable records : {predictable_mask.sum()}")
    print(f"Total input records : {len(df_out)}")

    return df_out, per_region


# ── Entry point ───────────────────────────────────────────────────────────────

def run():
    config.create_output_dirs()
    score()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
