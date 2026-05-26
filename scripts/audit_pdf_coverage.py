"""
audit_pdf_coverage.py
---------------------
Audits which AMTEC PDFs have NOT yet been extracted into V3 batch xlsx files.

Safe to re-run (idempotent). Does NOT trigger extraction.
"""

import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Resolve repo root and import config
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import config  # noqa: E402  (imported after sys.path update)

AMTEC_PDF_DIR    = REPO_ROOT / config.AMTEC_PDF_DIR
AMTEC_EXTRACTION_DIR = REPO_ROOT / config.AMTEC_EXTRACTION_DIR
OUTPUT_FILE      = REPO_ROOT / "Mini-Project/Agricultural Machinery Inventory from ABEMIS/missing_pdfs.txt"

SOURCE_COL       = "source_file"   # column name used by amtec_pdf_extractor.py
STATUS_COL       = "extraction_status"


# ---------------------------------------------------------------------------
# 1. Glob all source PDFs
# ---------------------------------------------------------------------------
all_pdf_paths = sorted(AMTEC_PDF_DIR.rglob("*.pdf"))
print(f"[1] Source PDF directory : {AMTEC_PDF_DIR}")
print(f"    PDFs found (recursive): {len(all_pdf_paths)}")

# Build a mapping: filename -> list of full paths  (detect collisions)
filename_to_paths: dict[str, list[Path]] = {}
for p in all_pdf_paths:
    filename_to_paths.setdefault(p.name, []).append(p)

collisions = {fn: paths for fn, paths in filename_to_paths.items() if len(paths) > 1}
if collisions:
    print(f"\n  WARNING: {len(collisions)} duplicate filename(s) across subfolders:")
    for fn, paths in list(collisions.items())[:10]:
        for pp in paths:
            print(f"    {pp.relative_to(AMTEC_PDF_DIR)}")
    if len(collisions) > 10:
        print(f"    ... and {len(collisions) - 10} more")
else:
    print("    No duplicate filenames detected across subfolders.")


# ---------------------------------------------------------------------------
# 2. Read all batch xlsx files and collect extracted source identifiers
# ---------------------------------------------------------------------------
batch_files = sorted(AMTEC_EXTRACTION_DIR.glob("AMTEC_extracted_improved_v3_batch_*.xlsx"))
print(f"\n[2] Extraction batch directory: {AMTEC_EXTRACTION_DIR}")
print(f"    Batch xlsx files found: {len(batch_files)}")

extracted_filenames: set[str] = set()
status_counts: dict[str, int] = {}
empty_batches: list[str] = []

for bf in batch_files:
    try:
        df = pd.read_excel(bf)
        if df.empty:
            empty_batches.append(bf.name)
            continue
        if SOURCE_COL not in df.columns:
            print(f"  WARNING: {bf.name} missing '{SOURCE_COL}' column — skipped.")
            continue
        extracted_filenames.update(df[SOURCE_COL].dropna().astype(str).str.strip().tolist())
        if STATUS_COL in df.columns:
            for status, cnt in df[STATUS_COL].value_counts().items():
                status_counts[status] = status_counts.get(status, 0) + int(cnt)
    except Exception as exc:
        print(f"  ERROR reading {bf.name}: {exc}")

if empty_batches:
    print(f"  WARNING: {len(empty_batches)} empty batch file(s): {empty_batches}")


# ---------------------------------------------------------------------------
# 3. Identify unextracted PDFs
# ---------------------------------------------------------------------------
all_filenames    = {p.name for p in all_pdf_paths}
missing_filenames = all_filenames - extracted_filenames

# Map missing filenames back to full paths
missing_paths = []
for fn in sorted(missing_filenames):
    paths = filename_to_paths.get(fn, [])
    missing_paths.extend(paths)
missing_paths.sort()

total         = len(all_pdf_paths)
n_extracted   = len(all_filenames & extracted_filenames)
n_missing     = len(missing_paths)

print(f"\n[3] Coverage report")
print(f"    Total source PDFs          : {total}")
print(f"    Already extracted          : {n_extracted}")
print(f"    Remaining (not extracted)  : {n_missing}")
print()
print("    Extraction status breakdown (across all batches):")
for status, cnt in sorted(status_counts.items(), key=lambda x: -x[1]):
    label = ""
    if "OCR" in status.upper():
        label = "  <-- OCR"
    elif "TEXT" in status.upper():
        label = "  <-- text"
    print(f"      {status:<45} {cnt:>6}{label}")

# Compute OCR vs TEXT counts from status_counts
ocr_count  = sum(v for k, v in status_counts.items() if "OCR"  in k.upper())
text_count = sum(v for k, v in status_counts.items() if "TEXT" in k.upper() and "OCR" not in k.upper())
print()
print(f"    OCR_EXTRACTED   (approx): {ocr_count}")
print(f"    TEXT_EXTRACTED  (approx): {text_count}")


# ---------------------------------------------------------------------------
# 4. Write missing_pdfs.txt
# ---------------------------------------------------------------------------
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
    for p in missing_paths:
        fh.write(str(p.resolve()) + "\n")

print(f"\n[4] Missing PDF list written to:")
print(f"    {OUTPUT_FILE}")
print(f"    Lines written: {len(missing_paths)}")


# ---------------------------------------------------------------------------
# 5. File-size heuristics for missing PDFs
# ---------------------------------------------------------------------------
print(f"\n[5] File-size heuristics for {n_missing} unextracted PDFs")
if missing_paths:
    sizes_mb = []
    for p in missing_paths:
        try:
            sizes_mb.append(p.stat().st_size / (1024 * 1024))
        except OSError:
            pass

    if sizes_mb:
        import statistics
        mean_mb   = statistics.mean(sizes_mb)
        median_mb = statistics.median(sizes_mb)
        over_5mb  = sum(1 for s in sizes_mb if s > 5)
        over_1mb  = sum(1 for s in sizes_mb if s > 1)
        print(f"    Mean size   : {mean_mb:.2f} MB")
        print(f"    Median size : {median_mb:.2f} MB")
        print(f"    > 1 MB      : {over_1mb} files")
        print(f"    > 5 MB      : {over_5mb} files  (likely image-heavy scans)")
    else:
        print("    Could not stat any missing PDF files.")
else:
    print("    All PDFs already extracted — nothing to size-check.")

print("\nDone.")
