import re

import pandas as pd

import config
from config import ABEMIS_EXTRACTED_DIR, ABEMIS_DIAG_DIR
from utils.io_helpers import read_file_safely

OUTPUT_FILE = ABEMIS_DIAG_DIR / "ABEMIS_Inventory_Usability_Check.xlsx"

MACHINERY_KEYWORDS = ["machine", "machinery", "equipment", "implement", "commodity", "type", "classification", "category"]
LOCATION_KEYWORDS  = ["region", "province", "municipality", "city", "barangay", "location", "psgc"]
BRAND_KEYWORDS     = ["brand", "make", "manufacturer"]
MODEL_KEYWORDS     = ["model", "model no", "model number"]
POWER_KEYWORDS     = ["hp", "horsepower", "kw", "power", "rated"]
QUANTITY_KEYWORDS  = ["quantity", "qty", "count", "number", "units", "no.", "total"]
OWNER_KEYWORDS     = ["owner", "beneficiary", "farmer", "fca", "association", "cooperative"]
DATE_KEYWORDS      = ["date", "year", "acquired", "encoded", "created", "updated"]


def normalize_colname(col):
    col = str(col).strip().lower()
    col = re.sub(r"[^a-z0-9]+", "_", col)
    col = re.sub(r"_+", "_", col)
    return col.strip("_")


def find_matching_columns(columns, keywords):
    matches = []
    for col in columns:
        col_norm = normalize_colname(col)
        for key in keywords:
            if normalize_colname(key) in col_norm:
                matches.append(col)
                break
    return matches


def infer_region_from_filename(file_path):
    match = re.search(r"(NCR|CAR|BARMM|NIRR|R\d+[A-Z]?)", file_path.stem, re.IGNORECASE)
    return match.group(1).upper() if match else None


def classify_usability(row_count, col_count, machinery_cols, location_cols):
    if row_count == 0:
        return "UNUSABLE - No rows"
    if col_count == 0:
        return "UNUSABLE - No columns"
    if not machinery_cols and not location_cols:
        return "LOW - Cannot detect machinery or location columns"
    if not machinery_cols:
        return "PARTIAL - Location only, machinery column missing"
    if not location_cols:
        return "PARTIAL - Machinery only, location columns missing"
    return "GOOD - Has machinery and location indicators"


def run():
    all_files = []
    for ext in ("*.xlsx", "*.xls", "*.csv", "*.json"):
        all_files.extend(ABEMIS_EXTRACTED_DIR.rglob(ext))
    all_files = sorted(all_files)
    print("Files found:", len(all_files))

    file_summaries = []
    column_summaries = []
    sample_rows = []

    for i, file_path in enumerate(all_files, start=1):
        print(f"[{i}/{len(all_files)}] Checking: {file_path.name}")
        df, status = read_file_safely(file_path)
        inferred_region = infer_region_from_filename(file_path)

        if df is None:
            file_summaries.append({
                "file_name": file_path.name,
                "file_path": str(file_path),
                "inferred_region": inferred_region,
                "read_status": status,
                "row_count": 0,
                "column_count": 0,
                "duplicate_rows": None,
                "machinery_columns": None,
                "location_columns": None,
                "brand_columns": None,
                "model_columns": None,
                "power_columns": None,
                "quantity_columns": None,
                "owner_columns": None,
                "date_columns": None,
                "usability_rating": "UNUSABLE - Read error",
            })
            continue

        df = df.dropna(how="all").dropna(axis=1, how="all")
        columns = list(df.columns)

        machinery_cols = find_matching_columns(columns, MACHINERY_KEYWORDS)
        location_cols  = find_matching_columns(columns, LOCATION_KEYWORDS)
        brand_cols     = find_matching_columns(columns, BRAND_KEYWORDS)
        model_cols     = find_matching_columns(columns, MODEL_KEYWORDS)
        power_cols     = find_matching_columns(columns, POWER_KEYWORDS)
        quantity_cols  = find_matching_columns(columns, QUANTITY_KEYWORDS)
        owner_cols     = find_matching_columns(columns, OWNER_KEYWORDS)
        date_cols      = find_matching_columns(columns, DATE_KEYWORDS)

        file_summaries.append({
            "file_name": file_path.name,
            "file_path": str(file_path),
            "inferred_region": inferred_region,
            "read_status": status,
            "row_count": len(df),
            "column_count": len(df.columns),
            "duplicate_rows": df.duplicated().sum(),
            "machinery_columns": ", ".join(map(str, machinery_cols)),
            "location_columns": ", ".join(map(str, location_cols)),
            "brand_columns": ", ".join(map(str, brand_cols)),
            "model_columns": ", ".join(map(str, model_cols)),
            "power_columns": ", ".join(map(str, power_cols)),
            "quantity_columns": ", ".join(map(str, quantity_cols)),
            "owner_columns": ", ".join(map(str, owner_cols)),
            "date_columns": ", ".join(map(str, date_cols)),
            "usability_rating": classify_usability(len(df), len(df.columns), machinery_cols, location_cols),
        })

        for col in df.columns:
            column_summaries.append({
                "file_name": file_path.name,
                "inferred_region": inferred_region,
                "column_name": col,
                "normalized_column_name": normalize_colname(col),
                "non_missing_count": df[col].notna().sum(),
                "missing_count": df[col].isna().sum(),
                "missing_rate": round(df[col].isna().mean(), 4),
                "unique_count": df[col].nunique(dropna=True),
                "example_values": " | ".join(df[col].dropna().astype(str).head(5).tolist()),
            })

        sample = df.head(5).copy()
        sample.insert(0, "source_file", file_path.name)
        sample.insert(1, "inferred_region", inferred_region)
        sample_rows.append(sample)

    file_summary_df   = pd.DataFrame(file_summaries)
    column_summary_df = pd.DataFrame(column_summaries)
    sample_rows_df    = pd.concat(sample_rows, ignore_index=True, sort=False) if sample_rows else pd.DataFrame()

    overall_summary = pd.DataFrame([{
        "total_files_found":      len(all_files),
        "readable_files":         (file_summary_df["read_status"] == "OK").sum() if not file_summary_df.empty else 0,
        "total_rows":             file_summary_df["row_count"].sum() if not file_summary_df.empty else 0,
        "total_columns_scanned":  file_summary_df["column_count"].sum() if not file_summary_df.empty else 0,
        "good_files":             file_summary_df["usability_rating"].astype(str).str.contains("GOOD", na=False).sum() if not file_summary_df.empty else 0,
        "partial_files":          file_summary_df["usability_rating"].astype(str).str.contains("PARTIAL", na=False).sum() if not file_summary_df.empty else 0,
        "low_or_unusable_files":  file_summary_df["usability_rating"].astype(str).str.contains("LOW|UNUSABLE", na=False).sum() if not file_summary_df.empty else 0,
    }])

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        overall_summary.to_excel(writer, sheet_name="Overall Summary", index=False)
        file_summary_df.to_excel(writer, sheet_name="File Summary", index=False)
        column_summary_df.to_excel(writer, sheet_name="Column Summary", index=False)
        sample_rows_df.to_excel(writer, sheet_name="Sample Rows", index=False)

    print("\nDONE. Diagnostic file saved to:")
    print(OUTPUT_FILE)
    print("\nOverall Summary:")
    print(overall_summary)


if __name__ == "__main__":
    config.create_output_dirs()
    run()
