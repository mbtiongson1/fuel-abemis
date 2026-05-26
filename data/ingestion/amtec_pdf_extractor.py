import re
import warnings
from datetime import datetime

import fitz  # PyMuPDF
import pandas as pd

import config
from config import (
    AMTEC_PDF_DIR,
    AMTEC_EXTRACTION_DIR,
    USE_OCR,
    OCR_MAX_PAGES,
)

warnings.filterwarnings("ignore")

MIN_TEXT_LENGTH = 300
CHECKPOINT_EVERY = 100

MACHINE_PATTERNS = {
    "Solar-Powered Irrigation System": [
        r"\bSPIS\b",
        r"solar[-\s]?powered irrigation system",
    ],
    "Walking-Type Agricultural Tractor": [
        r"walking[-\s]?type agricultural tractor",
        r"walk[-\s]?behind agricultural tractor",
    ],
    "Four-Wheel Tractor": [
        r"four[-\s]?wheel tractor",
        r"4[-\s]?wheel tractor",
        r"\b4wt\b",
    ],
    "Hand Tractor": [
        r"hand tractor",
        r"walking[-\s]?type tractor",
        r"two[-\s]?wheel tractor",
        r"2[-\s]?wheel tractor",
        r"\bpower tiller\b",
    ],
    "Small Engine": [
        r"small engine",
        r"gasoline engine",
        r"diesel engine",
    ],
    "Rotary Tiller": [
        r"rotary tiller",
        r"rotavator",
        r"rotary cultivator",
    ],
    "Combine Harvester": [
        r"combine harvester",
        r"rice combine",
        r"corn combine",
    ],
    "Rice Transplanter": [
        r"rice transplanter",
        r"mechanical rice transplanter",
        r"walk[-\s]?behind transplanter",
        r"riding[-\s]?type transplanter",
    ],
    "Reaper": [
        r"\breaper\b",
        r"rice reaper",
    ],
    "Water Pump": [
        r"water pump",
        r"irrigation pump",
        r"\bpump\b",
    ],
    "Mechanical Dryer": [
        r"mechanical dryer",
        r"flatbed dryer",
        r"recirculating dryer",
        r"grain dryer",
        r"batch dryer",
    ],
    "Thresher": [
        r"\bthresher\b",
        r"rice thresher",
    ],
    "Sheller": [
        r"\bsheller\b",
        r"corn sheller",
    ],
    "Rice Mill": [
        r"rice mill",
        r"milling machine",
        r"rice milling",
    ],
    "Seeder": [
        r"\bseeder\b",
        r"seed drill",
    ],
    "Sprayer": [
        r"\bsprayer\b",
        r"power sprayer",
    ],
}

LOW_PRIORITY_PATTERNS = [
    r"moisture meter",
    r"tester",
    r"analyzer",
    r"weighing scale",
    r"laboratory",
    r"meter",
    r"sensor",
]


# ── Text extraction ──────────────────────────────────────────────────────────

def clean_text(text):
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\xa0", " ")
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def extract_text_pymupdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        text = clean_text(text)
        if len(text) < MIN_TEXT_LENGTH:
            return text, "LOW_TEXT_POSSIBLE_SCANNED"
        return text, "TEXT_EXTRACTED"
    except Exception as e:
        return "", f"PDF_READ_ERROR: {e}"


def extract_text_ocr(pdf_path, max_pages=3):
    try:
        import pytesseract
        from pdf2image import convert_from_path

        pages = convert_from_path(str(pdf_path), first_page=1, last_page=max_pages, dpi=200)
        text = ""
        for img in pages:
            text += pytesseract.image_to_string(img, lang="eng") + "\n"
        text = clean_text(text)
        if len(text) < MIN_TEXT_LENGTH:
            return text, "OCR_LOW_TEXT"
        return text, "OCR_EXTRACTED"
    except Exception as e:
        return "", f"OCR_ERROR: {e}"


def extract_text(pdf_path):
    text, status = extract_text_pymupdf(pdf_path)
    if USE_OCR and len(text) < MIN_TEXT_LENGTH:
        ocr_text, ocr_status = extract_text_ocr(pdf_path, OCR_MAX_PAGES)
        if len(ocr_text) > len(text):
            return ocr_text, ocr_status
    return text, status


# ── Field helpers ────────────────────────────────────────────────────────────

def clean_field_value(value):
    if value is None:
        return None
    value = str(value)
    value = value.replace("\n", " ")
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" :;,.|-–")
    return value.strip()


def is_valid_field_value(value):
    if value is None:
        return False
    value = str(value).strip()
    if not value:
        return False
    if re.fullmatch(r"[,.\s/-]+", value):
        return False
    return True


def find_first(patterns, text, flags=re.IGNORECASE):
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            value = clean_field_value(match.group(1))
            if is_valid_field_value(value):
                return value
    return None


def extract_number_and_unit(value):
    if value is None:
        return None, None
    value = str(value).replace(",", "")
    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z/%\-\^0-9]+(?:/[A-Za-z0-9]+)?)?",
        value,
    )
    if not match:
        return None, None
    return float(match.group(1)), match.group(2)


def kw_to_hp(kw):
    return kw * 1.34102209 if kw is not None else None


def hp_to_kw(hp):
    return hp * 0.745699872 if hp is not None else None


# ── Field extractors ─────────────────────────────────────────────────────────

def extract_report_no(text, filename):
    combined = f"{filename}\n{text}"
    value = find_first([
        r"Test\s*Report\s*No\.?\s*[:\-]?\s*((?:19|20)\d{2}[-–]\d{3,5})",
        r"Report\s*No\.?\s*[:\-]?\s*((?:19|20)\d{2}[-–]\d{3,5})",
        r"\b((?:19|20)\d{2}[-–]\d{3,5})\b",
    ], combined)
    return value.replace("–", "-") if value else None


def extract_machinery_type(text, filename):
    combined = f"{filename}\n{text}".lower()
    scores = {}
    for machine_type, patterns in MACHINE_PATTERNS.items():
        score = 0
        for pattern in patterns:
            hits = re.findall(pattern, combined, flags=re.IGNORECASE)
            score += len(hits)
            if re.search(pattern, filename.lower(), flags=re.IGNORECASE):
                score += 5
        if score > 0:
            scores[machine_type] = score
    if not scores:
        return None
    return max(scores, key=scores.get)


def extract_from_filename(pdf_path):
    stem = pdf_path.stem
    report_no = None
    m = re.search(r"\b((?:19|20)\d{2}[-–]\d{3,5})\b", stem)
    if m:
        report_no = m.group(1).replace("–", "-")
    cleaned = re.sub(r"\b(?:19|20)\d{2}[-–]\d{3,5}\b", "", stem)
    cleaned = cleaned.replace("_", " ").replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    machinery_type = extract_machinery_type("", cleaned)
    brand = None
    model = None
    temp = cleaned
    if machinery_type:
        for pattern in MACHINE_PATTERNS.get(machinery_type, []):
            temp = re.sub(pattern, "", temp, flags=re.IGNORECASE).strip()
    temp = re.sub(r"\s+", " ", temp).strip(" -_")
    parts = temp.split()
    if len(parts) >= 1:
        brand = parts[0]
    if len(parts) >= 2:
        model = " ".join(parts[1:])
    return report_no, machinery_type, brand, model


def classify_project_relevance(text, filename, machinery_type):
    combined = f"{filename}\n{text}".lower()
    if machinery_type in MACHINE_PATTERNS:
        return "HIGH_RELEVANCE"
    for pattern in LOW_PRIORITY_PATTERNS:
        if re.search(pattern, combined):
            return "LOW_RELEVANCE"
    return "UNKNOWN_RELEVANCE"


def extract_matched_keywords(text, filename):
    combined = f"{filename}\n{text}".lower()
    matched = []
    for machine_type, patterns in MACHINE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined):
                matched.append(machine_type)
                break
    return ", ".join(sorted(set(matched)))


def extract_brand(text):
    return find_first([
        r"\bBrand\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9 \-/().,&]{1,60})",
        r"\bTrade\s*Name\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9 \-/().,&]{1,60})",
        r"\bMake\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9 \-/().,&]{1,60})",
    ], text)


def extract_model(text):
    return find_first([
        r"\bModel\s*No\.?\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9 \-/().,&]{1,60})",
        r"\bModel\s*[:\-]\s*([A-Za-z0-9][A-Za-z0-9 \-/().,&]{1,60})",
    ], text)


def extract_power_raw(text):
    return find_first([
        r"Rated\s*Power\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:kW|KW|kw|hp|HP|Hp))",
        r"Engine\s*Power\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:kW|KW|kw|hp|HP|Hp))",
        r"Power\s*Rating\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:kW|KW|kw|hp|HP|Hp))",
        r"Maximum\s*Power\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:kW|KW|kw|hp|HP|Hp))",
        r"\b([0-9]+(?:\.[0-9]+)?\s*kW)\b",
        r"\b([0-9]+(?:\.[0-9]+)?\s*hp)\b",
    ], text)


def normalize_power(power_raw):
    value, unit = extract_number_and_unit(power_raw)
    if value is None or unit is None:
        return None, None
    unit_l = unit.lower()
    if "kw" in unit_l:
        power_kw = value
        power_hp = kw_to_hp(value)
    elif "hp" in unit_l:
        power_hp = value
        power_kw = hp_to_kw(value)
    else:
        return None, None
    if power_kw <= 0 or power_kw > 500:
        return None, None
    return round(power_kw, 3), round(power_hp, 3)


def extract_fuel_raw(text):
    return find_first([
        r"Fuel\s*Consumption\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:L/hr|L/h|l/hr|l/h|li/hr|L/ha|l/ha|kg/hr|kg/h))",
        r"Specific\s*Fuel\s*Consumption\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:L/hr|L/h|l/hr|l/h|g/kWh|g/hp-hr))",
        r"Fuel\s*Rate\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:L/hr|L/h|l/hr|l/h))",
        r"Diesel\s*Consumption\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:L/hr|L/h|l/hr|l/h|L/ha|l/ha))",
        r"Gasoline\s*Consumption\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:L/hr|L/h|l/hr|l/h|L/ha|l/ha))",
        r"\b([0-9]+(?:\.[0-9]+)?\s*(?:L/hr|L/h|l/hr|l/h|li/hr|L/ha|l/ha))\b",
    ], text)


def normalize_fuel(fuel_raw):
    value, unit = extract_number_and_unit(fuel_raw)
    if value is None:
        return None, None
    if value <= 0 or value > 300:
        return None, None
    if unit:
        unit = unit.replace("l", "L")
        unit = unit.replace("L/hr", "L/h")
        unit = unit.replace("L/H", "L/h")
    return value, unit


def extract_field_capacity_raw(text):
    return find_first([
        r"Effective\s*Field\s*Capacity\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:ha/hr|ha/h|hectare/hr|hectares/hr))",
        r"Theoretical\s*Field\s*Capacity\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:ha/hr|ha/h|hectare/hr|hectares/hr))",
        r"Field\s*Capacity\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:ha/hr|ha/h|hectare/hr|hectares/hr))",
        r"\b([0-9]+(?:\.[0-9]+)?\s*(?:ha/hr|ha/h))\b",
    ], text)


def extract_operating_speed_raw(text):
    return find_first([
        r"Operating\s*Speed\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:km/hr|km/h|kph))",
        r"Forward\s*Speed\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:km/hr|km/h|kph))",
        r"Travel\s*Speed\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:km/hr|km/h|kph))",
        r"\b([0-9]+(?:\.[0-9]+)?\s*(?:km/hr|km/h|kph))\b",
    ], text)


def validate_speed(speed_raw):
    value, unit = extract_number_and_unit(speed_raw)
    if value is None:
        return None, None
    if value <= 0 or value > 40:
        return None, None
    return value, unit


def extract_general_capacity_raw(text):
    return find_first([
        r"Output\s*Capacity\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:kg/hr|kg/h|tons/hr|ton/hr|t/hr|cavans/hr|bags/hr))",
        r"Throughput\s*Capacity\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:kg/hr|kg/h|tons/hr|ton/hr|t/hr))",
        r"Capacity\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?\s*(?:kg/hr|kg/h|tons/hr|ton/hr|t/hr|cavans/hr|bags/hr))",
    ], text)


def extract_fuel_type(text):
    value = find_first([
        r"Fuel\s*Type\s*[:\-]?\s*(Diesel|Gasoline|Petrol|Kerosene)",
        r"\b(Diesel|Gasoline|Petrol|Kerosene)\b",
    ], text)
    return value.title() if value else None


# ── Record builder ────────────────────────────────────────────────────────────

def extract_record(pdf_path):
    text, status = extract_text(pdf_path)
    filename_report_no, filename_machine, filename_brand, filename_model = extract_from_filename(pdf_path)
    report_no = extract_report_no(text, pdf_path.name) or filename_report_no
    year = report_no[:4] if report_no else None
    machinery_type = extract_machinery_type(text, pdf_path.name) or filename_machine
    brand = extract_brand(text) or filename_brand
    model = extract_model(text) or filename_model
    if machinery_type == "Solar-Powered Irrigation System":
        brand = None
        model = None
    relevance = classify_project_relevance(text, pdf_path.name, machinery_type)
    matched_keywords = extract_matched_keywords(text, pdf_path.name)
    power_raw = extract_power_raw(text)
    power_kw, power_hp = normalize_power(power_raw)
    fuel_raw = extract_fuel_raw(text)
    fuel_value, fuel_unit = normalize_fuel(fuel_raw)
    field_capacity_raw = extract_field_capacity_raw(text)
    field_capacity_value, field_capacity_unit = extract_number_and_unit(field_capacity_raw)
    speed_raw = extract_operating_speed_raw(text)
    speed_value, speed_unit = validate_speed(speed_raw)
    general_capacity_raw = extract_general_capacity_raw(text)
    general_capacity_value, general_capacity_unit = extract_number_and_unit(general_capacity_raw)
    return {
        "test_report_no": report_no,
        "year": year,
        "machinery_type": machinery_type,
        "brand": brand,
        "model": model,
        "rated_power_raw": power_raw,
        "power_kw": power_kw,
        "power_hp": power_hp,
        "fuel_type": extract_fuel_type(text),
        "fuel_consumption_raw": fuel_raw,
        "fuel_value": fuel_value,
        "fuel_unit": fuel_unit,
        "field_capacity_raw": field_capacity_raw,
        "field_capacity_value": field_capacity_value,
        "field_capacity_unit": field_capacity_unit,
        "operating_speed_raw": speed_raw,
        "operating_speed_value": speed_value,
        "operating_speed_unit": speed_unit,
        "general_capacity_raw": general_capacity_raw,
        "general_capacity_value": general_capacity_value,
        "general_capacity_unit": general_capacity_unit,
        "project_relevance": relevance,
        "matched_keywords": matched_keywords,
        "source_file": pdf_path.name,
        "source_path": str(pdf_path),
        "extraction_status": status,
        "text_length": len(text),
        "needs_ocr": len(text) < MIN_TEXT_LENGTH,
    }


_BLANK_RECORD = {k: None for k in [
    "test_report_no", "year", "machinery_type", "brand", "model",
    "rated_power_raw", "power_kw", "power_hp", "fuel_type",
    "fuel_consumption_raw", "fuel_value", "fuel_unit",
    "field_capacity_raw", "field_capacity_value", "field_capacity_unit",
    "operating_speed_raw", "operating_speed_value", "operating_speed_unit",
    "general_capacity_raw", "general_capacity_value", "general_capacity_unit",
    "matched_keywords",
]}
_BLANK_RECORD.update({"project_relevance": "ERROR", "needs_ocr": True, "text_length": 0})


# ── Main runner ───────────────────────────────────────────────────────────────

def run():
    all_pdfs = sorted(AMTEC_PDF_DIR.rglob("*.pdf"))
    total_files = len(all_pdfs)
    print("Total PDFs found:", total_files)
    print("OCR enabled:", USE_OCR)
    print("Output folder:", AMTEC_EXTRACTION_DIR)

    records = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for i, pdf_path in enumerate(all_pdfs, start=1):
        print(f"[{i}/{total_files}] {pdf_path.name}")
        try:
            records.append(extract_record(pdf_path))
        except Exception as e:
            rec = dict(_BLANK_RECORD)
            rec.update({
                "source_file": pdf_path.name,
                "source_path": str(pdf_path),
                "extraction_status": f"ERROR: {e}",
            })
            records.append(rec)

        if i % CHECKPOINT_EVERY == 0:
            checkpoint_df = pd.DataFrame(records)
            checkpoint_file = AMTEC_EXTRACTION_DIR / f"AMTEC_full_extraction_checkpoint_{i}_{timestamp}.xlsx"
            checkpoint_df.to_excel(checkpoint_file, index=False)
            print("Checkpoint saved:", checkpoint_file)

    df = pd.DataFrame(records)
    df["missing_machinery_type"] = df["machinery_type"].isna()
    df["missing_fuel_consumption"] = df["fuel_value"].isna()
    df["missing_rated_power"] = df["power_kw"].isna()
    df["missing_field_capacity"] = df["field_capacity_value"].isna()
    df["usable_for_core_dataset"] = (
        (df["project_relevance"] == "HIGH_RELEVANCE")
        & df["machinery_type"].notna()
        & df["fuel_value"].notna()
        & df["power_kw"].notna()
    )
    df["high_priority_for_review"] = (
        (df["project_relevance"] == "HIGH_RELEVANCE") & ~df["usable_for_core_dataset"]
    )

    full_file   = AMTEC_EXTRACTION_DIR / "AMTEC_full_extracted_dataset.xlsx"
    core_file   = AMTEC_EXTRACTION_DIR / "AMTEC_core_usable_dataset.xlsx"
    review_file = AMTEC_EXTRACTION_DIR / "AMTEC_high_priority_for_review.xlsx"
    ocr_file    = AMTEC_EXTRACTION_DIR / "AMTEC_needs_ocr.xlsx"

    df.to_excel(full_file, index=False)
    df[df["usable_for_core_dataset"]].to_excel(core_file, index=False)
    df[df["high_priority_for_review"]].to_excel(review_file, index=False)
    df[df["needs_ocr"]].to_excel(ocr_file, index=False)

    print("DONE.")
    print("Output folder:", AMTEC_EXTRACTION_DIR)


if __name__ == "__main__":
    config.create_output_dirs()
    run()
