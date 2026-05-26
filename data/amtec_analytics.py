import logging
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import config
from config import AMTEC_EXTRACTION_DIR, AMTEC_ANALYTICS_DIR

logger = logging.getLogger(__name__)

CONTEXT_FILE = AMTEC_ANALYTICS_DIR / "abemis_machinery_context.xlsx"

warnings.filterwarnings("ignore")

INPUT_FILE   = AMTEC_EXTRACTION_DIR / "AMTEC_full_extracted_dataset.xlsx"
OUTPUT_EXCEL = AMTEC_ANALYTICS_DIR  / "AMTEC_Test_Report_Fuel_Power_Analytics_V2.xlsx"


# ── Machinery classification ─────────────────────────────────────────────────

def classify_machinery_family(machine):
    if pd.isna(machine):
        return "Unknown"
    machine = str(machine).strip()
    mobile_field = ["Four-Wheel Tractor", "Hand Tractor", "Walking-Type Agricultural Tractor", "Rotary Tiller", "Rice Transplanter", "Reaper", "Seeder", "Sprayer"]
    harvest = ["Combine Harvester"]
    stationary_engine = ["Small Engine", "Water Pump", "Solar-Powered Irrigation System"]
    postharvest_processing = ["Thresher", "Sheller", "Rice Mill", "Mechanical Dryer"]
    if machine in mobile_field:
        return "Mobile Field Machinery"
    if machine in harvest:
        return "Harvest Machinery"
    if machine in stationary_engine:
        return "Stationary Engine / Irrigation"
    if machine in postharvest_processing:
        return "Postharvest / Processing"
    return "Other / Unclassified"


def classify_analysis_subset(machine):
    family = classify_machinery_family(machine)
    if family in ("Mobile Field Machinery", "Harvest Machinery"):
        return "Dataset A - Field Machinery"
    if family in ("Stationary Engine / Irrigation", "Postharvest / Processing"):
        return "Dataset B - Stationary and Processing"
    return "Dataset C - Other"


# ── Power classification ─────────────────────────────────────────────────────

def fixed_power_class_kw(power_kw):
    if pd.isna(power_kw):
        return np.nan
    if power_kw < 5:
        return "Very Low Power (<5 kW)"
    if power_kw < 10:
        return "Low Power (5–<10 kW)"
    if power_kw < 20:
        return "Medium Power (10–<20 kW)"
    if power_kw < 40:
        return "High Power (20–<40 kW)"
    if power_kw < 75:
        return "Very High Power (40–<75 kW)"
    return "Extra High Power (≥75 kW)"


def add_within_machine_power_class(group):
    group = group.copy()
    # pandas 2.2+ groupby/apply drops the group key column; restore it from group.name
    if "machinery_type" not in group.columns and getattr(group, "name", None) is not None:
        group["machinery_type"] = group.name
    if group["power_kw"].nunique() < 3 or len(group) < 6:
        group["power_class_within_machine"] = "Single/Narrow Power Range"
        return group
    try:
        group["power_class_within_machine"] = pd.qcut(
            group["power_kw"], q=3,
            labels=["Low Power Within Type", "Medium Power Within Type", "High Power Within Type"],
            duplicates="drop",
        ).astype(str)
    except Exception:
        group["power_class_within_machine"] = "Single/Narrow Power Range"
    return group


# ── Fuel intensity & outliers ─────────────────────────────────────────────────

def fuel_intensity_class(value):
    if pd.isna(value):
        return np.nan
    if value < 0.10:
        return "Very Low Fuel Intensity (<0.10 L/kW-h)"
    if value < 0.20:
        return "Low Fuel Intensity (0.10–<0.20 L/kW-h)"
    if value < 0.35:
        return "Moderate Fuel Intensity (0.20–<0.35 L/kW-h)"
    if value < 0.60:
        return "High Fuel Intensity (0.35–<0.60 L/kW-h)"
    return "Very High Fuel Intensity (>=0.60 L/kW-h)"


def add_outlier_severity(group):
    group = group.copy()
    if "machinery_type" not in group.columns and getattr(group, "name", None) is not None:
        group["machinery_type"] = group.name
    if len(group) < 5:
        group["fuel_z_score_within_machine"] = np.nan
        group["fuel_outlier_severity"] = "Insufficient Records"
        return group
    mean_val = group["fuel_l_per_hr"].mean()
    std_val  = group["fuel_l_per_hr"].std()
    if std_val == 0 or pd.isna(std_val):
        group["fuel_z_score_within_machine"] = 0
        group["fuel_outlier_severity"] = "No Variation"
        return group
    group["fuel_z_score_within_machine"] = (group["fuel_l_per_hr"] - mean_val) / std_val
    abs_z = group["fuel_z_score_within_machine"].abs()
    group["fuel_outlier_severity"] = np.select(
        [abs_z >= 3, abs_z >= 2, abs_z >= 1.5],
        ["Extreme", "Moderate", "Mild"],
        default="Normal",
    )
    return group


# ── Quick regression summary (analytics-level, not the formal OLS in models/) ─

def regression_summary(group, group_name_col):
    results = []
    for name, g in group:
        g = g.dropna(subset=["power_kw", "fuel_l_per_hr"]).copy()
        if len(g) < 5 or g["power_kw"].nunique() < 2:
            results.append({group_name_col: name, "records": len(g), "regression_status": "Insufficient data",
                            "intercept": np.nan, "slope_fuel_per_kw": np.nan, "equation": None,
                            "r2": np.nan, "mae": np.nan, "rmse": np.nan})
            continue
        X = g[["power_kw"]].values
        y = g["fuel_l_per_hr"].values
        model = LinearRegression()
        model.fit(X, y)
        pred = model.predict(X)
        intercept = float(model.intercept_)
        slope     = float(model.coef_[0])
        results.append({
            group_name_col: name,
            "records": len(g),
            "regression_status": "OK",
            "intercept": intercept,
            "slope_fuel_per_kw": slope,
            "equation": f"Fuel_L_h = {intercept:.4f} + {slope:.4f}(Power_kW)",
            "r2": r2_score(y, pred),
            "mae": mean_absolute_error(y, pred),
            "rmse": np.sqrt(mean_squared_error(y, pred)),
        })
    return pd.DataFrame(results)


def correlation_by_group(data, group_col, corr_cols):
    rows = []
    for name, g in data.groupby(group_col):
        g = g[corr_cols].dropna(how="all")
        if len(g) < 5:
            rows.append({group_col: name, "records": len(g),
                         "corr_power_kw_fuel": np.nan, "corr_field_capacity_fuel": np.nan, "corr_speed_fuel": np.nan})
            continue
        corr = g.corr(numeric_only=True)
        rows.append({
            group_col: name,
            "records": len(g),
            "corr_power_kw_fuel":        corr.loc["power_kw", "fuel_l_per_hr"] if "power_kw" in corr.index and "fuel_l_per_hr" in corr.columns else np.nan,
            "corr_field_capacity_fuel":  corr.loc["field_capacity_value", "fuel_l_per_hr"] if "field_capacity_value" in corr.index and "fuel_l_per_hr" in corr.columns else np.nan,
            "corr_speed_fuel":           corr.loc["operating_speed_value", "fuel_l_per_hr"] if "operating_speed_value" in corr.index and "fuel_l_per_hr" in corr.columns else np.nan,
        })
    return pd.DataFrame(rows)


# ── Main runner ───────────────────────────────────────────────────────────────

def run():
    df = pd.read_excel(INPUT_FILE)
    print("Original records:", len(df))

    # Basic cleaning
    for col in ["machinery_type", "fuel_unit", "brand", "model", "fuel_type", "project_relevance", "extraction_status"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
    for col in ["power_kw", "power_hp", "fuel_value", "field_capacity_value", "operating_speed_value", "general_capacity_value"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Filter to L/h records only
    usable = df[df["machinery_type"].notna() & df["power_kw"].notna() & df["fuel_value"].notna()].copy()
    usable["fuel_unit_clean"] = (
        usable["fuel_unit"].astype("string").str.lower()
        .str.replace("l/hr", "l/h", regex=False)
        .str.replace("li/hr", "l/h", regex=False)
        .str.replace("liter/hr", "l/h", regex=False)
        .str.strip()
    )
    usable = usable[usable["fuel_unit_clean"].isin(["l/h"])].copy()
    usable["fuel_l_per_hr"] = usable["fuel_value"]
    usable = usable[(usable["power_kw"] > 0) & (usable["power_kw"] <= 500) & (usable["fuel_l_per_hr"] > 0) & (usable["fuel_l_per_hr"] <= 300)].copy()
    print("Usable L/h records:", len(usable))

    # Classification
    usable["machinery_family"] = usable["machinery_type"].apply(classify_machinery_family)
    usable["analysis_subset"]  = usable["machinery_type"].apply(classify_analysis_subset)

    # Derived metrics
    usable["fuel_l_per_kw_hr"] = usable["fuel_l_per_hr"] / usable["power_kw"]
    usable["kw_per_l_per_hr"]  = usable["power_kw"] / usable["fuel_l_per_hr"]
    usable["fuel_l_per_hp_hr"] = usable["fuel_l_per_hr"] / usable["power_hp"]
    usable["hp_per_l_per_hr"]  = usable["power_hp"] / usable["fuel_l_per_hr"]
    usable["power_class_fixed"] = usable["power_kw"].apply(fixed_power_class_kw)
    usable = pd.concat(
        [add_within_machine_power_class(g.assign(machinery_type=k)) for k, g in usable.groupby("machinery_type", group_keys=False)],
        ignore_index=True,
    )
    usable["fuel_intensity_class"] = usable["fuel_l_per_kw_hr"].apply(fuel_intensity_class)
    usable = pd.concat(
        [add_outlier_severity(g.assign(machinery_type=k)) for k, g in usable.groupby("machinery_type", group_keys=False)],
        ignore_index=True,
    )

    possible_outliers = usable[usable["fuel_outlier_severity"].isin(["Mild", "Moderate", "Extreme"])].copy()

    # Regression summaries
    regression_by_machine = regression_summary(usable.groupby("machinery_type"), "machinery_type").sort_values(["regression_status", "records"], ascending=[True, False])
    regression_by_family  = regression_summary(usable.groupby("machinery_family"), "machinery_family").sort_values(["regression_status", "records"], ascending=[True, False])
    regression_by_subset  = regression_summary(usable.groupby("analysis_subset"), "analysis_subset").sort_values(["regression_status", "records"], ascending=[True, False])

    # Correlation
    corr_cols = [c for c in ["power_kw", "power_hp", "fuel_l_per_hr", "fuel_l_per_kw_hr", "field_capacity_value", "operating_speed_value", "general_capacity_value"] if c in usable.columns]
    overall_correlation = usable[corr_cols].corr(numeric_only=True).reset_index().rename(columns={"index": "variable"})
    fuel_correlation = usable[corr_cols].corr(numeric_only=True)[["fuel_l_per_hr"]].reset_index().rename(columns={"index": "variable", "fuel_l_per_hr": "correlation_with_fuel_l_hr"}).sort_values("correlation_with_fuel_l_hr", ascending=False)
    correlation_by_machine = correlation_by_group(usable, "machinery_type", corr_cols)
    correlation_by_family  = correlation_by_group(usable, "machinery_family", corr_cols)

    # Join ABEMIS context features (built by data/abemis_context_features.py)
    if CONTEXT_FILE.exists():
        context = pd.read_excel(CONTEXT_FILE)
        usable = usable.merge(context, on="machinery_type", how="left")
        print("ABEMIS context features joined:", context.shape[0], "type(s) matched")
    else:
        logger.warning("abemis_machinery_context.xlsx not found — skipping context join. Run: python -m data.abemis_context_features")

    # Summary tables
    record_cols = [c for c in [
        "test_report_no", "year", "machinery_family", "analysis_subset", "machinery_type",
        "brand", "model", "rated_power_raw", "power_kw", "power_hp", "power_class_fixed",
        "power_class_within_machine", "fuel_type", "fuel_consumption_raw", "fuel_l_per_hr",
        "fuel_l_per_kw_hr", "fuel_l_per_hp_hr", "kw_per_l_per_hr", "fuel_intensity_class",
        "field_capacity_value", "field_capacity_unit", "operating_speed_value", "operating_speed_unit",
        "general_capacity_value", "general_capacity_unit", "fuel_z_score_within_machine",
        "fuel_outlier_severity",
        "abemis_total_count", "abemis_region_breadth", "abemis_dominant_region_share",
        "source_file", "source_path",
    ] if c in usable.columns]
    clean_record_level = usable[record_cols].copy()

    agg_spec = dict(records=("fuel_l_per_hr", "count"), avg_power_kw=("power_kw", "mean"),
                    min_power_kw=("power_kw", "min"), max_power_kw=("power_kw", "max"),
                    avg_power_hp=("power_hp", "mean"), avg_fuel_l_hr=("fuel_l_per_hr", "mean"),
                    min_fuel_l_hr=("fuel_l_per_hr", "min"), max_fuel_l_hr=("fuel_l_per_hr", "max"),
                    median_fuel_l_hr=("fuel_l_per_hr", "median"), avg_fuel_l_per_kw_hr=("fuel_l_per_kw_hr", "mean"),
                    median_fuel_l_per_kw_hr=("fuel_l_per_kw_hr", "median"), avg_kw_per_l_per_hr=("kw_per_l_per_hr", "mean"))

    summary_by_machine = usable.groupby(["machinery_family", "machinery_type"]).agg(**agg_spec).reset_index().sort_values(["machinery_family", "records"], ascending=[True, False])
    summary_by_family  = usable.groupby("machinery_family").agg(records=("fuel_l_per_hr", "count"), machinery_types=("machinery_type", "nunique"), avg_power_kw=("power_kw", "mean"), min_power_kw=("power_kw", "min"), max_power_kw=("power_kw", "max"), avg_fuel_l_hr=("fuel_l_per_hr", "mean"), min_fuel_l_hr=("fuel_l_per_hr", "min"), max_fuel_l_hr=("fuel_l_per_hr", "max"), median_fuel_l_hr=("fuel_l_per_hr", "median"), avg_fuel_l_per_kw_hr=("fuel_l_per_kw_hr", "mean")).reset_index().sort_values("records", ascending=False)
    summary_by_subset  = usable.groupby("analysis_subset").agg(records=("fuel_l_per_hr", "count"), machinery_types=("machinery_type", "nunique"), avg_power_kw=("power_kw", "mean"), avg_fuel_l_hr=("fuel_l_per_hr", "mean"), avg_fuel_l_per_kw_hr=("fuel_l_per_kw_hr", "mean")).reset_index().sort_values("records", ascending=False)
    summary_by_fixed_power_class = usable.groupby(["machinery_family", "machinery_type", "power_class_fixed"]).agg(**{k: v for k, v in agg_spec.items() if k not in ("avg_power_hp",)}).reset_index().sort_values(["machinery_family", "machinery_type", "avg_power_kw"])
    summary_by_within_power_class = usable.groupby(["machinery_family", "machinery_type", "power_class_within_machine"]).agg(**{k: v for k, v in agg_spec.items() if k not in ("avg_power_hp",)}).reset_index().sort_values(["machinery_family", "machinery_type", "avg_power_kw"])
    fuel_intensity_summary = usable.groupby(["machinery_family", "machinery_type", "fuel_intensity_class"]).agg(records=("fuel_l_per_hr", "count"), avg_power_kw=("power_kw", "mean"), avg_fuel_l_hr=("fuel_l_per_hr", "mean"), avg_fuel_l_per_kw_hr=("fuel_l_per_kw_hr", "mean")).reset_index().sort_values(["machinery_family", "machinery_type", "avg_fuel_l_per_kw_hr"])
    pivot_avg_fuel_fixed_power = pd.pivot_table(usable, values="fuel_l_per_hr", index=["machinery_family", "machinery_type"], columns="power_class_fixed", aggfunc="mean").reset_index()
    pivot_count_fixed_power    = pd.pivot_table(usable, values="fuel_l_per_hr", index=["machinery_family", "machinery_type"], columns="power_class_fixed", aggfunc="count").reset_index()
    dataset_a_field      = usable[usable["analysis_subset"] == "Dataset A - Field Machinery"].copy()
    dataset_b_stationary = usable[usable["analysis_subset"] == "Dataset B - Stationary and Processing"].copy()
    weak_categories = usable.groupby("machinery_type").size().reset_index(name="records")
    weak_categories = weak_categories[weak_categories["records"] < 5]

    # Save Excel
    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        clean_record_level.to_excel(writer, sheet_name="Clean Record Level", index=False)
        summary_by_family.to_excel(writer, sheet_name="Summary by Family", index=False)
        summary_by_subset.to_excel(writer, sheet_name="Summary by Dataset", index=False)
        summary_by_machine.to_excel(writer, sheet_name="Summary by Machine", index=False)
        summary_by_fixed_power_class.to_excel(writer, sheet_name="By Fixed Power Class", index=False)
        summary_by_within_power_class.to_excel(writer, sheet_name="By Within-Type Power", index=False)
        fuel_intensity_summary.to_excel(writer, sheet_name="Fuel Intensity Summary", index=False)
        regression_by_machine.to_excel(writer, sheet_name="Regression by Machine", index=False)
        regression_by_family.to_excel(writer, sheet_name="Regression by Family", index=False)
        regression_by_subset.to_excel(writer, sheet_name="Regression by Dataset", index=False)
        fuel_correlation.to_excel(writer, sheet_name="Fuel Correlation", index=False)
        overall_correlation.to_excel(writer, sheet_name="Overall Correlation", index=False)
        correlation_by_machine.to_excel(writer, sheet_name="Correlation by Machine", index=False)
        correlation_by_family.to_excel(writer, sheet_name="Correlation by Family", index=False)
        possible_outliers.to_excel(writer, sheet_name="Outlier Severity", index=False)
        pivot_avg_fuel_fixed_power.to_excel(writer, sheet_name="Pivot Avg Fuel", index=False)
        pivot_count_fixed_power.to_excel(writer, sheet_name="Pivot Count", index=False)
        dataset_a_field.to_excel(writer, sheet_name="Dataset A Field Machinery", index=False)
        dataset_b_stationary.to_excel(writer, sheet_name="Dataset B Stationary", index=False)
        weak_categories.to_excel(writer, sheet_name="Weak Categories", index=False)

    print("Excel analytics saved to:", OUTPUT_EXCEL)

    # Charts
    for title, xlabel, ydata, fname in [
        ("Average Fuel Consumption by Machinery Type", "Machinery Type", summary_by_machine.sort_values("avg_fuel_l_hr", ascending=False), "average_fuel_by_machinery_type.png"),
        ("Average Fuel Consumption by Machinery Family", "Machinery Family", summary_by_family.sort_values("avg_fuel_l_hr", ascending=False), "average_fuel_by_machinery_family.png"),
    ]:
        plt.figure(figsize=(12, 6))
        plt.bar(ydata[xlabel.lower().replace(" ", "_") if "Type" not in xlabel else "machinery_type" if "Type" in xlabel else "machinery_family"], ydata["avg_fuel_l_hr"])
        plt.xticks(rotation=75, ha="right")
        plt.ylabel("Average Fuel Consumption (L/h)")
        plt.xlabel(xlabel)
        plt.title(title)
        plt.tight_layout()
        plt.savefig(AMTEC_ANALYTICS_DIR / fname, dpi=300)
        plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(usable["power_kw"], usable["fuel_l_per_hr"], alpha=0.7)
    plt.xlabel("Rated Power (kW)")
    plt.ylabel("Fuel Consumption (L/h)")
    plt.title("Rated Power vs Fuel Consumption - All Machinery")
    plt.tight_layout()
    plt.savefig(AMTEC_ANALYTICS_DIR / "power_vs_fuel_all.png", dpi=300)
    plt.close()

    print("DONE.")
    return usable


if __name__ == "__main__":
    config.create_output_dirs()
    run()
