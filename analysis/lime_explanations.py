"""
LIME local explanations for individual fuel consumption predictions.

Inputs  : trained RF model (rf_model.pkl)  +  Clean Record Level xlsx
Outputs : LIME_Explanations.xlsx, lime_example_<n>.png (one per sampled instance)
"""

import numpy as np
import pandas as pd

import config
from config import AMTEC_ANALYTICS_DIR, AMTEC_REGRESSION_DIR
from models.random_forest import FEATURE_COLS, TARGET_COL, INPUT_FILE, load_model

OUTPUT_DIR   = AMTEC_REGRESSION_DIR
OUTPUT_EXCEL = OUTPUT_DIR / "LIME_Explanations.xlsx"

# Number of instances to explain (sample from the dataset)
N_SAMPLES = 10


def load_data() -> pd.DataFrame:
    df = pd.read_excel(INPUT_FILE, sheet_name="Clean Record Level")
    required = [TARGET_COL] + FEATURE_COLS
    df = df.dropna(subset=required).copy()
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=required)


def run(n_samples: int = N_SAMPLES):
    import matplotlib.pyplot as plt
    from lime import lime_tabular

    model   = load_model()
    df      = load_data()
    X_train = df[FEATURE_COLS].values

    explainer = lime_tabular.LimeTabularExplainer(
        training_data=X_train,
        feature_names=FEATURE_COLS,
        mode="regression",
        random_state=42,
    )

    sample_idx = np.random.choice(len(df), size=min(n_samples, len(df)), replace=False)
    all_explanations = []

    for i, idx in enumerate(sample_idx):
        instance = X_train[idx]
        exp      = explainer.explain_instance(instance, model.predict, num_features=len(FEATURE_COLS))

        actual    = df.iloc[idx][TARGET_COL]
        predicted = model.predict([instance])[0]

        row = {"sample_index": idx, "actual_fuel_l_hr": actual, "predicted_fuel_l_hr": predicted}
        for feat, weight in exp.as_list():
            row[f"lime_{feat}"] = weight
        all_explanations.append(row)

        fig = exp.as_pyplot_figure()
        fig.suptitle(f"LIME - Sample {idx}  |  Actual={actual:.3f}  Pred={predicted:.3f}", fontsize=9)
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
