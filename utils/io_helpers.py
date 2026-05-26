import pandas as pd
from pathlib import Path


def read_excel(path, **kwargs):
    return pd.read_excel(path, **kwargs)


def write_excel_multi_sheet(path: Path, sheets: dict):
    """Write multiple DataFrames to named sheets in one xlsx file."""
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def read_file_safely(file_path: Path):
    """Read xlsx/xls/csv/json; return (DataFrame, status_str)."""
    suffix = file_path.suffix.lower()
    try:
        if suffix in (".xlsx", ".xls"):
            return pd.read_excel(file_path), "OK"
        if suffix == ".csv":
            try:
                return pd.read_csv(file_path, encoding="utf-8"), "OK"
            except UnicodeDecodeError:
                return pd.read_csv(file_path, encoding="latin1"), "OK"
        if suffix == ".json":
            return pd.read_json(file_path), "OK"
        return None, f"Unsupported file type: {suffix}"
    except Exception as e:
        return None, f"Read error: {e}"


def ensure_dirs(*dirs):
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
