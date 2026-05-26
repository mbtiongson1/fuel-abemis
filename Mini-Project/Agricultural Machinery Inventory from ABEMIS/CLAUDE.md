# Agricultural Machinery Inventory from ABEMIS

This folder is dual-purpose: it holds the ABEMIS machinery inventory data **and** all processed AMTEC outputs (extraction, analytics, modeling). The naming is historical — outputs landed here during the project handover and have not been split.

## Subdirectories — current best version

| Folder | What it contains | Best/current version |
|---|---|---|
| `Raw/` | ABEMIS source files (zip output batches, ~36 xlsx across nested dirs) | input |
| `Extracted/` | 36 regional ABEMIS xlsx files (~40 MB total) | current |
| `Diagnostics/` | `ABEMIS_Inventory_Usability_Check.xlsx` | current |
| `Fuel Classification/` | V1 fuel classification (91 MB) | superseded |
| `Fuel Classification V2/` | `ABEMIS_Fuel_vs_NoFuel_Machinery_V2.xlsx` (95 MB) | **★ current** |
| `Extracted Batches/` | AMTEC extraction V1 (4 batches) | superseded |
| `Extracted Batches Improved/` | AMTEC extraction V2 (6 batches) | superseded |
| `Extracted Batches Improved V3/` | AMTEC extraction V3 (6 batches) | **★ current** |
| `Analytics Output/` | V1 analytics | superseded |
| `Analytics Output V2/` | `AMTEC_Test_Report_Fuel_Power_Analytics_V2.xlsx` + 5 PNGs | **★ current** — input to all ML |
| `Regression Parameters Output V3/` | OLS, RF, SHAP, LIME outputs | **★ current** |

## What was deleted

The previous `Mini-Project/Test Report/Full Extraction Output/` directory (with `AMTEC_full_extracted_dataset.xlsx`, 1,691 records) was removed. The V3 batches in `Extracted Batches Improved V3/` are the surviving extraction artifacts. If a full re-extraction is needed, run `data/ingestion/amtec_pdf_extractor.py` against `../Test Reports from BAFE-AMTEC/` (~30 min + OCR time).

## File-size warning

`Fuel Classification V2/ABEMIS_Fuel_vs_NoFuel_Machinery_V2.xlsx` is 95 MB. Avoid opening it casually with pandas in tight loops; the 8-sheet structure is documented in `data/abemis_classifier.py`.
