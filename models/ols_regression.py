import re
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.outliers_influence import OLSInfluence

import config
from config import (
    AMTEC_ANALYTICS_DIR,
    AMTEC_REGRESSION_DIR,
    ALPHA,
    MIN_RECORDS,
    MIN_UNIQUE_POWER,
    MIN_ACCEPTABLE_R2,
    R2_FILTER_TYPE,
    EXCLUDE_EXTREME_OUTLIERS_FOR_FINAL,
    CLIP_NEGATIVE_PREDICTIONS,
)

warnings.filterwarnings("ignore")

INPUT_FILE   = AMTEC_ANALYTICS_DIR  / "AMTEC_Test_Report_Fuel_Power_Analytics_V2.xlsx"
OUTPUT_EXCEL = AMTEC_REGRESSION_DIR / "AMTEC_Regression_All_Parameters_V3_Filtered_R2.xlsx"
SHEET_NAME   = "Clean Record Level"
TARGET_COL   = "fuel_l_per_hr"
POWER_COL    = "power_kw"


# ── Helpers ──────────────────────────────────────────────────────────────────

def safe_name(text):
    text = re.sub(r"[^A-Za-z0-9]+", "_", str(text))
    return re.sub(r"_+", "_", text).strip("_")


def build_design_matrix(data, model_form):
    x = data[POWER_COL].astype(float)
    if model_form == "linear":
        X = pd.DataFrame({POWER_COL: x})
    elif model_form == "quadratic":
        X = pd.DataFrame({POWER_COL: x, "power_kw_squared": x ** 2})
    elif model_form == "log_response":
        X = pd.DataFrame({POWER_COL: x})
    else:
        raise ValueError(f"Invalid model_form: {model_form}")
    return sm.add_constant(X, has_constant="add")


def get_response(data, model_form):
    y = data[TARGET_COL].astype(float)
    return np.log(y) if model_form == "log_response" else y


def inverse_transform(pred, model_form):
    if model_form == "log_response":
        pred = np.exp(pred)
    return np.maximum(pred, 0) if CLIP_NEGATIVE_PREDICTIONS else pred


def equation_from_model(model, model_form):
    p = model.params.to_dict()
    b0, b1, b2 = p.get("const", 0), p.get(POWER_COL, 0), p.get("power_kw_squared", 0)
    if model_form == "linear":
        return f"Fuel_L_h = {b0:.6f} + {b1:.6f}(Power_kW)"
    if model_form == "quadratic":
        return f"Fuel_L_h = {b0:.6f} + {b1:.6f}(Power_kW) + {b2:.6f}(Power_kW^2)"
    if model_form == "log_response":
        return f"ln(Fuel_L_h) = {b0:.6f} + {b1:.6f}(Power_kW); Fuel_L_h = exp({b0:.6f} + {b1:.6f}(Power_kW))"
    return None


def safe_mape(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    mask = y_true != 0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.sum() > 0 else np.nan


# ── Regression fitter ─────────────────────────────────────────────────────────

def fit_regression(data, model_scope, group_name, model_form):
    data = data.dropna(subset=[TARGET_COL, POWER_COL]).copy()
    n, unique_power = len(data), data[POWER_COL].nunique()

    _insufficient = pd.DataFrame([{"model_scope": model_scope, "group_name": group_name, "model_form": model_form,
                                    "model_status": "INSUFFICIENT_DATA", "n_observations": n, "unique_power_values": unique_power}])
    if n < MIN_RECORDS or unique_power < MIN_UNIQUE_POWER:
        return _insufficient, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    X = build_design_matrix(data, model_form)
    y_model = get_response(data, model_form)
    y_actual = data[TARGET_COL].astype(float)

    try:
        model = sm.OLS(y_model, X).fit()
    except Exception as e:
        return pd.DataFrame([{"model_scope": model_scope, "group_name": group_name, "model_form": model_form,
                               "model_status": f"MODEL_ERROR: {e}", "n_observations": n, "unique_power_values": unique_power}]), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    influence   = OLSInfluence(model)
    pred_model  = model.fittedvalues
    pred_actual = inverse_transform(pred_model, model_form)
    resid       = y_actual - pred_actual

    k = int(model.df_model)
    p = int(model.df_model + 1)
    sst   = np.sum((y_actual - y_actual.mean()) ** 2)
    ssres = np.sum(resid ** 2)
    ssr   = sst - ssres
    msr   = ssr / k if k > 0 else np.nan
    msres = ssres / (n - p) if (n - p) > 0 else np.nan
    f0    = msr / msres if msres and msres != 0 else np.nan
    f_crit = stats.f.ppf(1 - ALPHA, k, n - p) if k > 0 and (n - p) > 0 else np.nan

    r2_actual  = 1 - (ssres / sst) if sst != 0 else np.nan
    adj_r2     = 1 - ((n - 1) / (n - p)) * (1 - r2_actual) if (n - p) > 0 else np.nan
    filter_r2  = adj_r2 if R2_FILTER_TYPE == "adjusted" else r2_actual
    passes_r2  = pd.notna(filter_r2) and filter_r2 >= MIN_ACCEPTABLE_R2

    lev_lecture = (p + 1) / n
    lev_2p = (2 * p) / n
    lev_3p = (3 * p) / n

    model_summary = pd.DataFrame([{
        "model_scope": model_scope, "group_name": group_name, "model_form": model_form,
        "model_status": "OK", "n_observations": n, "unique_power_values": unique_power,
        "k_regressors": k, "p_parameters_including_intercept": p,
        "df_model": model.df_model, "df_residual": model.df_resid, "alpha": ALPHA,
        "sst_total_sum_squares": sst, "ssr_regression_sum_squares": ssr, "ssres_residual_sum_squares": ssres,
        "msr_regression_mean_square": msr, "msres_residual_mean_square": msres,
        "f_statistic_actual_scale": f0, "f_critical": f_crit,
        "f_p_value_model_scale": model.f_pvalue,
        "f_test_decision": "Reject H0" if pd.notna(f0) and pd.notna(f_crit) and f0 > f_crit else "Fail to reject H0",
        "r_squared_model_scale": model.rsquared, "adjusted_r_squared_model_scale": model.rsquared_adj,
        "r_squared_actual_scale": r2_actual, "adjusted_r_squared_actual_scale": adj_r2,
        "r2_filter_type": R2_FILTER_TYPE, "r2_filter_value": filter_r2,
        "min_acceptable_r2": MIN_ACCEPTABLE_R2, "passes_r2_filter": passes_r2,
        "r2_filter_decision": "KEEP" if passes_r2 else "REMOVE_WEAK_R2",
        "aic": model.aic, "bic": model.bic,
        "residual_standard_error_actual_scale": np.sqrt(msres) if pd.notna(msres) else np.nan,
        "mse_actual_scale": np.mean(resid ** 2),
        "rmse_actual_scale": np.sqrt(np.mean(resid ** 2)),
        "mae_actual_scale": np.mean(np.abs(resid)),
        "mape_percent_actual_scale": safe_mape(y_actual, pred_actual),
        "min_power_kw": data[POWER_COL].min(), "max_power_kw": data[POWER_COL].max(),
        "avg_power_kw": data[POWER_COL].mean(), "min_fuel_l_hr": y_actual.min(),
        "max_fuel_l_hr": y_actual.max(), "avg_fuel_l_hr": y_actual.mean(),
        "leverage_cutoff_lecture_p_plus_1_over_n": lev_lecture,
        "leverage_cutoff_common_2p_over_n": lev_2p,
        "leverage_cutoff_common_3p_over_n": lev_3p,
        "studentized_residual_cutoff": 3,
        "cooks_distance_cutoff_4_over_n": 4 / n,
        "equation": equation_from_model(model, model_form),
    }])

    coef_df = pd.DataFrame({
        "model_scope": model_scope, "group_name": group_name, "model_form": model_form,
        "parameter": model.params.index,
        "estimate": model.params.values, "standard_error": model.bse.values,
        "t_value": model.tvalues.values, "p_value": model.pvalues.values,
        "ci_lower_95": model.conf_int(alpha=ALPHA)[0].values,
        "ci_upper_95": model.conf_int(alpha=ALPHA)[1].values,
    })
    coef_df["significant_at_0_05"] = coef_df["p_value"] < ALPHA

    anova_df = pd.DataFrame([
        {"model_scope": model_scope, "group_name": group_name, "model_form": model_form, "source": "Regression",
         "df": k, "sum_sq": ssr, "mean_sq": msr, "f_value": f0, "p_value_model_scale": model.f_pvalue},
        {"model_scope": model_scope, "group_name": group_name, "model_form": model_form, "source": "Residual",
         "df": n - p, "sum_sq": ssres, "mean_sq": msres, "f_value": np.nan, "p_value_model_scale": np.nan},
        {"model_scope": model_scope, "group_name": group_name, "model_form": model_form, "source": "Total",
         "df": n - 1, "sum_sq": sst, "mean_sq": np.nan, "f_value": np.nan, "p_value_model_scale": np.nan},
    ])

    diag = data.copy()
    diag.update({col: val for col, val in [
        ("model_scope", model_scope), ("group_name", group_name), ("model_form", model_form),
        ("passes_r2_filter", passes_r2), ("r2_filter_decision", "KEEP" if passes_r2 else "REMOVE_WEAK_R2"),
    ]})
    diag["model_scope"]        = model_scope
    diag["group_name"]         = group_name
    diag["model_form"]         = model_form
    diag["passes_r2_filter"]   = passes_r2
    diag["r2_filter_decision"] = "KEEP" if passes_r2 else "REMOVE_WEAK_R2"
    diag["actual_fuel_l_hr"]   = y_actual
    diag["predicted_fuel_l_hr"] = pred_actual
    diag["residual_actual_scale"] = resid
    diag["absolute_residual"] = np.abs(resid)
    diag["percent_error"] = np.where(y_actual != 0, diag["absolute_residual"] / y_actual * 100, np.nan)
    diag["fitted_model_scale"]   = pred_model
    diag["residual_model_scale"] = model.resid
    diag["standardized_residual"] = influence.resid_studentized_internal
    diag["studentized_residual"]  = influence.resid_studentized_external
    diag["leverage_hi"]          = influence.hat_matrix_diag
    diag["cooks_distance"]       = influence.cooks_distance[0]
    diag["dffits"]               = influence.dffits[0]
    diag["leverage_cutoff_lecture"] = lev_lecture
    diag["leverage_cutoff_2p"]   = lev_2p
    diag["leverage_cutoff_3p"]   = lev_3p
    diag["is_leverage_point_lecture"] = diag["leverage_hi"] > lev_lecture
    diag["is_leverage_point_2p"]      = diag["leverage_hi"] > lev_2p
    diag["is_leverage_point_3p"]      = diag["leverage_hi"] > lev_3p
    diag["is_possible_outlier_studentized"] = diag["studentized_residual"].abs() > 3
    diag["is_influential_cooks"]            = diag["cooks_distance"] > 4 / n
    diag["diagnostic_priority"] = np.select(
        [diag["is_possible_outlier_studentized"] & diag["is_influential_cooks"],
         diag["is_possible_outlier_studentized"], diag["is_influential_cooks"],
         diag["is_leverage_point_lecture"]],
        ["HIGH - outlier and influential", "MEDIUM - studentized outlier",
         "MEDIUM - influential Cook's distance", "LOW - high leverage"],
        default="NORMAL",
    )
    return model_summary, coef_df, anova_df, diag


def run_all_models(data, label_suffix="FULL"):
    summaries, coefs, anovas, diags = [], [], [], []
    for model_form in ("linear", "quadratic", "log_response"):
        s, c, a, d = fit_regression(data, "GLOBAL", f"ALL_MACHINERY_{label_suffix}", model_form)
        summaries.append(s)
        for lst, df in [(coefs, c), (anovas, a), (diags, d)]:
            if not df.empty:
                lst.append(df)
        for family, group in data.groupby("machinery_family"):
            s, c, a, d = fit_regression(group, "MACHINERY_FAMILY", f"{family}_{label_suffix}", model_form)
            summaries.append(s)
            for lst, df in [(coefs, c), (anovas, a), (diags, d)]:
                if not df.empty:
                    lst.append(df)
        for machine, group in data.groupby("machinery_type"):
            s, c, a, d = fit_regression(group, "MACHINERY_TYPE", f"{machine}_{label_suffix}", model_form)
            summaries.append(s)
            for lst, df in [(coefs, c), (anovas, a), (diags, d)]:
                if not df.empty:
                    lst.append(df)
    return (
        pd.concat(summaries, ignore_index=True, sort=False),
        pd.concat(coefs, ignore_index=True, sort=False) if coefs else pd.DataFrame(),
        pd.concat(anovas, ignore_index=True, sort=False) if anovas else pd.DataFrame(),
        pd.concat(diags, ignore_index=True, sort=False) if diags else pd.DataFrame(),
    )


def _plot_diagnostics(diag, title_prefix, output_prefix):
    if len(diag) < 5:
        return
    for ydata, ylabel, title_suffix, fname_suffix in [
        (diag["residual_actual_scale"], "Residuals", "Residuals vs Fitted", "residuals_vs_fitted"),
        (diag["studentized_residual"], "Studentized Residual", "Studentized Residuals", "studentized_residuals"),
        (diag["leverage_hi"], "Leverage hᵢ", "Leverage Values", "leverage"),
    ]:
        plt.figure(figsize=(8, 6))
        if fname_suffix == "residuals_vs_fitted":
            plt.scatter(diag["predicted_fuel_l_hr"], ydata, alpha=0.7)
            plt.axhline(0, linestyle="--")
            plt.xlabel("Fitted Values")
        else:
            plt.scatter(range(len(diag)), ydata, alpha=0.7)
            plt.xlabel("Observation Index")
            if fname_suffix == "studentized_residuals":
                plt.axhline(3, linestyle="--")
                plt.axhline(-3, linestyle="--")
            elif fname_suffix == "leverage" and "leverage_cutoff_lecture" in diag.columns:
                plt.axhline(diag["leverage_cutoff_lecture"].iloc[0], linestyle="--")
        plt.ylabel(ylabel)
        plt.title(f"{title_suffix} - {title_prefix}")
        plt.tight_layout()
        plt.savefig(AMTEC_REGRESSION_DIR / f"{output_prefix}_{fname_suffix}.png", dpi=300)
        plt.close()

    plt.figure(figsize=(8, 6))
    sm.qqplot(diag["residual_actual_scale"], line="45", fit=True)
    plt.title(f"Normal Q-Q Plot - {title_prefix}")
    plt.tight_layout()
    plt.savefig(AMTEC_REGRESSION_DIR / f"{output_prefix}_qqplot.png", dpi=300)
    plt.close()


def run():
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
    required = [TARGET_COL, POWER_COL, "machinery_family", "machinery_type"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for col in (TARGET_COL, POWER_COL):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ("machinery_family", "machinery_type"):
        df[col] = df[col].astype("string").str.strip()

    usable = df.dropna(subset=required).copy()
    usable = usable[(usable[TARGET_COL] > 0) & (usable[TARGET_COL] <= 300) & (usable[POWER_COL] > 0) & (usable[POWER_COL] <= 500)].copy()
    usable["row_id"] = np.arange(1, len(usable) + 1)
    print("Usable records before diagnostics:", len(usable))

    # First pass (full data) to identify global outliers
    model_summary_full, coef_full, anova_full, diagnostics_full = run_all_models(usable, "FULL")

    global_linear = diagnostics_full[
        (diagnostics_full["model_scope"] == "GLOBAL") &
        (diagnostics_full["group_name"] == "ALL_MACHINERY_FULL") &
        (diagnostics_full["model_form"] == "linear")
    ].copy()
    extreme_ids = set(global_linear[global_linear["is_possible_outlier_studentized"]]["row_id"].tolist())

    final_data = usable[~usable["row_id"].isin(extreme_ids)].copy() if EXCLUDE_EXTREME_OUTLIERS_FOR_FINAL else usable.copy()
    print("Extreme global outliers identified:", len(extreme_ids))
    print("Records for final models:", len(final_data))

    # Second pass (final data)
    model_summary_final, coef_final, anova_final, diagnostics_final = run_all_models(final_data, "FINAL")

    # Filter weak-R² models
    ok_models     = model_summary_final[model_summary_final["model_status"] == "OK"].copy()
    strong_models = ok_models[ok_models["passes_r2_filter"]].copy()
    weak_models   = ok_models[~ok_models["passes_r2_filter"]].copy()
    best_strong   = (
        strong_models
        .sort_values(["model_scope", "group_name", "rmse_actual_scale", "aic", "adjusted_r_squared_actual_scale"],
                     ascending=[True, True, True, True, False])
        .groupby(["model_scope", "group_name"], as_index=False)
        .first()
    )
    pred_hierarchy = best_strong[[
        "model_scope", "group_name", "model_form", "model_status", "n_observations",
        "unique_power_values", "equation", "min_power_kw", "max_power_kw", "avg_power_kw",
        "avg_fuel_l_hr", "r_squared_actual_scale", "adjusted_r_squared_actual_scale",
        "rmse_actual_scale", "mae_actual_scale", "mape_percent_actual_scale",
        "aic", "bic", "r2_filter_type", "r2_filter_value", "min_acceptable_r2", "r2_filter_decision",
    ]].copy()

    # Fallback hierarchy
    fallback_notes = []
    for machine in sorted(final_data["machinery_type"].dropna().unique()):
        family = final_data.loc[final_data["machinery_type"] == machine, "machinery_family"].dropna().iloc[0]
        level, group = "NO_ACCEPTABLE_MODEL", None
        for scope, grp in [("MACHINERY_TYPE", f"{machine}_FINAL"), ("MACHINERY_FAMILY", f"{family}_FINAL"), ("GLOBAL", "ALL_MACHINERY_FINAL")]:
            if len(pred_hierarchy[(pred_hierarchy["model_scope"] == scope) & (pred_hierarchy["group_name"] == grp)]) > 0:
                level, group = scope, grp
                break
        fallback_notes.append({"machinery_type": machine, "machinery_family": family,
                                "recommended_prediction_level": level, "recommended_prediction_group": group,
                                "min_acceptable_r2": MIN_ACCEPTABLE_R2, "r2_filter_type": R2_FILTER_TYPE})
    fallback_hierarchy = pd.DataFrame(fallback_notes)

    diag_filtered   = diagnostics_final[diagnostics_final["passes_r2_filter"]].copy()
    high_leverage   = diagnostics_final[diagnostics_final["is_leverage_point_lecture"]].copy()
    stud_outliers   = diagnostics_final[diagnostics_final["is_possible_outlier_studentized"]].copy()
    influential     = diagnostics_final[diagnostics_final["is_influential_cooks"]].copy()
    priority_review = diagnostics_final[diagnostics_final["diagnostic_priority"] != "NORMAL"].copy()

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        usable.to_excel(writer, sheet_name="Original Regression Dataset", index=False)
        final_data.to_excel(writer, sheet_name="Final Regression Dataset", index=False)
        model_summary_full.to_excel(writer, sheet_name="Model Parameters FULL", index=False)
        model_summary_final.to_excel(writer, sheet_name="Model Parameters FINAL", index=False)
        coef_final.to_excel(writer, sheet_name="Coefficient Parameters FINAL", index=False)
        anova_final.to_excel(writer, sheet_name="ANOVA FINAL", index=False)
        pred_hierarchy.to_excel(writer, sheet_name="Prediction Hierarchy FILTERED", index=False)
        fallback_hierarchy.to_excel(writer, sheet_name="Fallback Hierarchy", index=False)
        strong_models.to_excel(writer, sheet_name="Strong Models Kept", index=False)
        weak_models.to_excel(writer, sheet_name="Weak Models Removed", index=False)
        diagnostics_final.to_excel(writer, sheet_name="Residual Diagnostics FINAL", index=False)
        diag_filtered.to_excel(writer, sheet_name="Diagnostics Strong Models", index=False)
        priority_review.to_excel(writer, sheet_name="Priority Review Points", index=False)
        high_leverage.to_excel(writer, sheet_name="High Leverage Points", index=False)
        stud_outliers.to_excel(writer, sheet_name="Studentized Outliers", index=False)
        influential.to_excel(writer, sheet_name="Influential Points", index=False)

    print("Saved:", OUTPUT_EXCEL)

    for _, row in pred_hierarchy.iterrows():
        diag = diagnostics_final[
            (diagnostics_final["model_scope"] == row["model_scope"]) &
            (diagnostics_final["group_name"] == row["group_name"]) &
            (diagnostics_final["model_form"] == row["model_form"])
        ]
        _plot_diagnostics(diag, f"{row['model_scope']} - {row['group_name']} - {row['model_form']}",
                          f"{safe_name(row['model_scope'])}_{safe_name(row['group_name'])}_{safe_name(row['model_form'])}")

    print("DONE.")
    return pred_hierarchy, fallback_hierarchy


if __name__ == "__main__":
    config.create_output_dirs()
    run()
