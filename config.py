from pathlib import Path

# Repo-relative path to data directory.
BASE = Path("Mini-Project/")

# ABEMIS directories
ABEMIS_RAW_DIR       = BASE / "Agricultural Machinery Inventory from ABEMIS/Raw"
ABEMIS_EXTRACTED_DIR = BASE / "Agricultural Machinery Inventory from ABEMIS/Extracted"
ABEMIS_DIAG_DIR      = BASE / "Agricultural Machinery Inventory from ABEMIS/Diagnostics"
ABEMIS_FUEL_DIR      = BASE / "Agricultural Machinery Inventory from ABEMIS/Fuel Classification V2"

# AMTEC directories — outputs co-located in the ABEMIS folder after cleanup.
AMTEC_PDF_DIR        = BASE / "Test Reports from BAFE-AMTEC"
AMTEC_EXTRACTION_DIR = BASE / "Agricultural Machinery Inventory from ABEMIS/Extracted Batches Improved V3"
AMTEC_ANALYTICS_DIR  = BASE / "Agricultural Machinery Inventory from ABEMIS/Analytics Output V2"
AMTEC_REGRESSION_DIR = BASE / "Agricultural Machinery Inventory from ABEMIS/Regression Parameters Output V3"

# OCR settings — only used if pytesseract + pdf2image are installed
USE_OCR       = True
OCR_MAX_PAGES = 3

# Regression settings
ALPHA                              = 0.05
MIN_RECORDS                        = 5
MIN_UNIQUE_POWER                   = 3
MIN_ACCEPTABLE_R2                  = 0.50
R2_FILTER_TYPE                     = "adjusted"   # "adjusted" or "raw"
EXCLUDE_EXTREME_OUTLIERS_FOR_FINAL = True
CLIP_NEGATIVE_PREDICTIONS          = True


def create_output_dirs():
    for _d in [
        ABEMIS_EXTRACTED_DIR, ABEMIS_DIAG_DIR, ABEMIS_FUEL_DIR,
        AMTEC_EXTRACTION_DIR, AMTEC_ANALYTICS_DIR, AMTEC_REGRESSION_DIR,
    ]:
        _d.mkdir(parents=True, exist_ok=True)
