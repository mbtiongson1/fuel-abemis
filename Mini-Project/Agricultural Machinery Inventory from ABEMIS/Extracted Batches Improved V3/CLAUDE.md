# Extracted Batches Improved V3

The current best AMTEC PDF extraction — V3 of the improved batch extractor. Six representative batches:

- `AMTEC_extracted_improved_v3_batch_001.xlsx`
- `AMTEC_extracted_improved_v3_batch_002.xlsx`
- `AMTEC_extracted_improved_v3_batch_003.xlsx`
- `AMTEC_extracted_improved_v3_batch_008.xlsx`
- `AMTEC_extracted_improved_v3_batch_015.xlsx`
- `AMTEC_extracted_improved_v3_batch_030.xlsx`

Each batch has a matching `*_summary.txt` with extraction stats.

## Why this is the canonical extraction

The previous `Mini-Project/Test Report/Full Extraction Output/AMTEC_full_extracted_dataset.xlsx` (1,691 rows, all PDFs) was **deleted**. These six V3 batches are the surviving structured extraction. The downstream Analytics V2 file in `../Analytics Output V2/` was generated from the full extraction before deletion (3,065 raw → 371 clean records), so the modeling pipeline still has its training input — but the bulk extraction artifact is no longer on disk.

## How to regenerate

If a full extraction is needed:
```bash
python -m data.ingestion.amtec_pdf_extractor
```
Reads PDFs from `../../Test Reports from BAFE-AMTEC/`, writes here. Expect ~30 minutes + OCR time for ~1,690 PDFs.

## Schema

22 columns per batch (subset of the full 34-column schema): `test_report_no`, `year`, `machinery_type`, `brand`, `model`, `rated_power`, `fuel_type`, `fuel_consumption`, `field_capacity`, `operating_speed`, `general_capacity`, `project_relevance`, `matched_keywords`, `source_file`, `source_path`, `extraction_status`, `text_length`, `needs_ocr`, `missing_machinery_type`, `missing_fuel_consumption`, `missing_rated_power`, `high_priority_for_review`.
