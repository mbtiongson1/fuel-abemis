"""
SHAP feature importance analysis for the Random Forest fuel model.

Inputs  : trained RF model (rf_model.pkl)  +  Clean Record Level xlsx
Outputs : SHAP_Analysis.xlsx, shap_summary_bar.png, shap_summary_beeswarm.png
"""

import numpy as np
import pandas as pd

import config
from config import AMTEC_REGRESSION_DIR
from models.random_forest import FEATURE_COLS, TARGET_COL, load_data, load_model

OUTPUT_DIR   = AMTEC_REGRESSION_DIR
OUTPUT_EXCEL = OUTPUT_DIR / "SHAP_Analysis.xlsx"


def run():
    import shap
    import matplotlib.pyplot as plt

    model = load_model()
    df, _encoders = load_data()
    X_df = df[FEATURE_COLS]

    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_df)

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance_df = pd.DataFrame({
        "feature": FEATURE_COLS,
        "mean_abs_shap": mean_abs_shap,
    }).sort_values("mean_abs_shap", ascending=False)

    plt.figure()
    shap.summary_plot(shap_values, X_df, plot_type="bar", show=False)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "shap_summary_bar.png", dpi=300, bbox_inches="tight")
    plt.close()

    plt.figure()
    shap.summary_plot(shap_values, X_df, show=False)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "shap_summary_beeswarm.png", dpi=300, bbox_inches="tight")
    plt.close()

    shap_df = pd.DataFrame(shap_values, columns=[f"shap_{c}" for c in FEATURE_COLS])
    output_df = pd.concat([df.reset_index(drop=True), shap_df], axis=1)

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        importance_df.to_excel(writer, sheet_name="Feature Importance", index=False)
        output_df.to_excel(writer, sheet_name="SHAP Values Per Record", index=False)

    print("SHAP analysis saved to:", OUTPUT_EXCEL)
    return importance_df, shap_values


if __name__ == "__main__":
    config.create_output_dirs()
    run()
