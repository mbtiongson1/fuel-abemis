# Mini-Project Data Directory

Two source datasets feed this project:

- **AMTEC** — Agricultural Machinery Testing and Evaluation Center test reports (PDFs, 1990s–2024)
- **ABEMIS** — Agricultural and Biosystems Engineering Management Information System inventory (regional Excel exports)

After cleanup, the folder layout is simplified:

```
Mini-Project/
├── Agricultural Machinery Inventory from ABEMIS/   ← all processed outputs (ABEMIS + AMTEC)
├── Test Reports from BAFE-AMTEC/                   ← source PDFs (read-only, do not modify)
├── Project Documents/                              ← LaTeX + PDFs of the proposal
├── References/                                     ← 10 cited papers
├── Assumptions.xlsx
├── Data Gathering form for Cropping Calendar (ao07222022).xlsx
└── Fuel Requirement Calculation (ao 09082025).xlsx
```

The original `Test Report/` directory was removed (it held a regenerated extraction; the surviving versions in the ABEMIS folder are newer).

## Directory map

| Subdirectory | Stage | Producer | Status |
|---|---|---|---|
| `Test Reports from BAFE-AMTEC/` | Source PDFs | manual collection | done |
| `Agricultural Machinery Inventory from ABEMIS/Raw/` | Source ABEMIS ZIP outputs | manual extraction | done |
| `Agricultural Machinery Inventory from ABEMIS/Extracted/` | Regional ABEMIS xlsx (36 files) | `data/ingestion/abemis_extractor.py` | done |
| `Agricultural Machinery Inventory from ABEMIS/Diagnostics/` | ABEMIS column usability | `data/abemis_usability.py` | done |
| `Agricultural Machinery Inventory from ABEMIS/Fuel Classification V2/` | Fuel-relevance per machine | `data/abemis_classifier.py` | done |
| `Agricultural Machinery Inventory from ABEMIS/Extracted Batches Improved V3/` | AMTEC extraction (V3 batches, 6 files) | `data/ingestion/amtec_pdf_extractor.py` | done |
| `Agricultural Machinery Inventory from ABEMIS/Analytics Output V2/` | AMTEC analytics + cleaned record table | `data/amtec_analytics.py` | done |
| `Agricultural Machinery Inventory from ABEMIS/Regression Parameters Output V3/` | OLS + RF + SHAP + LIME outputs | `models/`, `analysis/` | done |

## Files in repo root

- `Assumptions.xlsx` — modeling assumptions (manual, reference)
- `Data Gathering form for Cropping Calendar (ao07222022).xlsx` — RAED cropping-calendar data-gathering instrument; cropping calendar integration is **not yet done**
- `Fuel Requirement Calculation (ao 09082025).xlsx` — manual reference computation
