"""
LIME local explanations for individual fuel consumption predictions.

Inputs  : trained RF model (rf_model.pkl)  +  Clean Record Level xlsx
Outputs : LIME_Explanations.xlsx, lime_example_<n>.png (one per sampled instance)
"""

import numpy as np
import pandas as pd

import config
from config import AMTEC_REGRESSION_DIR
from models.random_forest import (
    FEATURE_COLS,
    CATEGORICAL_FEATURES,
    TARGET_COL,
    load_data,
    load_model,
)

OUTPUT_DIR   = AMTEC_REGRESSION_DIR
OUTPUT_EXCEL = OUTPUT_DIR / "LIME_Explanations.xlsx"

N_SAMPLES = 10


def run(n_samples: int = N_SAMPLES):
    import matplotlib.pyplot as plt
    from lime import lime_tabular

    model = load_model()
    df, encoders = load_data()
    X_train = df[FEATURE_COLS].values

    cat_indices = [FEATURE_COLS.index(f"{c}_code") for c in CATEGORICAL_FEATURES]
    cat_names = {
        FEATURE_COLS.index(f"{c}_code"): list(encoders[c].keys())
        for c in CATEGORICAL_FEATURES
    }

    explainer = lime_tabular.LimeTabularExplainer(
        training_data=X_train,
        feature_names=FEATURE_COLS,
        mode="regression",
        categorical_features=cat_indices,
        categorical_names=cat_names,
        random_state=42,
    )

    rng = np.random.default_rng(42)
    sample_idx = rng.choice(len(df), size=min(n_samples, len(df)), replace=False)
    all_explanations = []

    for i, idx in enumerate(sample_idx):
        instance = X_train[idx]
        exp = explainer.explain_instance(
            instance, model.predict, num_features=len(FEATURE_COLS)
        )

        actual    = float(df.iloc[idx][TARGET_COL])
        predicted = float(model.predict([instance])[0])

        row = {
            "sample_index": int(idx),
            "machinery_type": df.iloc[idx]["machinery_type"],
            "power_kw": float(df.iloc[idx]["power_kw"]),
            "actual_fuel_l_hr": actual,
            "predicted_fuel_l_hr": predicted,
        }
        for feat, weight in exp.as_list():
            row[f"lime_{feat}"] = weight
        all_explanations.append(row)

        fig = exp.as_pyplot_figure()
        fig.suptitle(
            f"LIME - Sample {idx}  |  {df.iloc[idx]['machinery_type']}  |  "
            f"Actual={actual:.3f}  Pred={predicted:.3f}",
            fontsize=9,
        )
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / f"lime_example_{i}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

    explanations_df = pd.DataFrame(all_explanations)

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        explanations_df.to_excel(writer, sheet_name="LIME Explanations", index=False)

    print("LIME explanations saved to:", OUTPUT_EXCEL)
    return explanations_df


if __name__ == "__main__":
    config.create_output_dirs()
    run()
