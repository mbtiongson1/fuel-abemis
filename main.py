"""
Pipeline orchestration — runs all stages in order.

Usage:
  python main.py                    # full pipeline
  python main.py --skip-ingestion   # skip data ingestion (assumes xlsx already extracted)
"""

import argparse
import sys

import config


def main():
    parser = argparse.ArgumentParser(description="Fuel Requirement ML Pipeline")
    parser.add_argument("--skip-ingestion", action="store_true",
                        help="Skip data ingestion (use when ABEMIS/AMTEC data already extracted)")
    parser.add_argument("--skip-processing", action="store_true",
                        help="Skip data processing (use when analytics xlsx already generated)")
    parser.add_argument("--skip-ols", action="store_true",
                        help="Skip OLS regression modeling")
    parser.add_argument("--skip-rf", action="store_true",
                        help="Skip Random Forest training")
    parser.add_argument("--skip-analysis", action="store_true",
                        help="Skip SHAP/LIME explainability analysis")
    args = parser.parse_args()

    config.create_output_dirs()

    # ── Stage 1: Data Ingestion ────────────────────────────────────────────────
    if not args.skip_ingestion:
        print("\n[Stage 1] ABEMIS ZIP extraction ...")
        from data.ingestion import abemis_extractor
        abemis_extractor.run()

        print("\n[Stage 1] AMTEC PDF extraction ...")
        from data.ingestion import amtec_pdf_extractor
        amtec_pdf_extractor.run()
    else:
        print("[Stage 1] Skipped ingestion.")

    # ── Stage 2: Data Processing ───────────────────────────────────────────────
    if not args.skip_processing:
        print("\n[Stage 2a] ABEMIS usability check ...")
        from data import abemis_usability
        abemis_usability.run()

        print("\n[Stage 2b] ABEMIS fuel-relevance classification ...")
        from data import abemis_classifier
        abemis_classifier.run()

        print("\n[Stage 2c] AMTEC analytics & cleaning ...")
        from data import amtec_analytics
        amtec_analytics.run()
    else:
        print("[Stage 2] Skipped processing.")

    # ── Stage 3: OLS Regression ────────────────────────────────────────────────
    if not args.skip_ols:
        print("\n[Stage 3] OLS regression modeling ...")
        from models import ols_regression
        ols_regression.run()
    else:
        print("[Stage 3] Skipped OLS regression.")

    # ── Stage 4: Random Forest ─────────────────────────────────────────────────
    if not args.skip_rf:
        print("\n[Stage 4] Random Forest training ...")
        from models import random_forest
        random_forest.run()
    else:
        print("[Stage 4] Skipped Random Forest.")

    # ── Stage 5: Explainability ────────────────────────────────────────────────
    if not args.skip_analysis:
        print("\n[Stage 5a] SHAP feature importance ...")
        from analysis import shap_analysis
        shap_analysis.run()

        print("\n[Stage 5b] LIME local explanations ...")
        from analysis import lime_explanations
        lime_explanations.run()
    else:
        print("[Stage 5] Skipped explainability analysis.")

    print("\nPipeline complete.")
    print("=" * 60)
    print("Output locations:")
    print("  ABEMIS diagnostics  :", config.ABEMIS_DIAG_DIR)
    print("  ABEMIS fuel classes :", config.ABEMIS_FUEL_DIR)
    print("  AMTEC extraction    :", config.AMTEC_EXTRACTION_DIR)
    print("  AMTEC analytics     :", config.AMTEC_ANALYTICS_DIR)
    print("  Regression output   :", config.AMTEC_REGRESSION_DIR)


if __name__ == "__main__":
    main()
