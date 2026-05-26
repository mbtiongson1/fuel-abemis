import re

import pandas as pd

import config
from config import ABEMIS_EXTRACTED_DIR, ABEMIS_FUEL_DIR
from utils.io_helpers import read_file_safely

OUTPUT_FILE = ABEMIS_FUEL_DIR / "ABEMIS_Fuel_vs_NoFuel_Machinery_V2.xlsx"

POSSIBLE_MACHINE_COLUMNS = [
    "Machine Name", "Machinery Name", "Machine", "Machinery",
    "Equipment", "Equipment Name", "Name of Machine",
]

POSSIBLE_POWER_COLUMNS = [
    "Rated Power", "Power", "Horsepower", "HP", "kW",
]

FUEL_KEYWORDS = [
    "tractor", "four wheel tractor", "four-wheel tractor", "4wt", "hand tractor",
    "walking type", "walking-type", "power tiller", "rotary tiller", "rotavator",
    "combine harvester", "harvester", "reaper", "transplanter", "water pump",
    "irrigation pump", "pump", "engine", "diesel", "gasoline", "petrol", "kerosene",
    "dryer", "mechanical dryer", "flatbed dryer", "recirculating dryer", "thresher",
    "sheller", "rice mill", "milling machine", "corn mill", "sprayer", "shredder",
    "chipper", "grass cutter", "brush cutter", "lawn mower", "hauling truck", "truck",
    "cargo motorcycle", "three wheel cargo motorcycle", "motorcycle", "multi cultivator",
    "cultivator", "disc cultivator", "inter row tine cultivator", "chainsaw",
    "mist blower", "pole pruner", "backhoe loader", "front loader", "loader",
    "forklift", "heavy duty forklift", "rough terrain crane", "telehandler",
    "drilling rig", "soil auger", "trailer", "hauler", "paddy hauler",
    "granule applicator", "fertilizer applicator", "broadcast spreader", "seed spreader",
    "corn seeder", "mechanical corn seeder", "precision seeder", "precision planter",
    "riding type palay seeder", "pneumatic corn seeder", "drum seeder", "sugarcane planter",
    "rotary ditcher", "mouldboard plow", "cane gruber", "cassava rootcrop digger",
    "power duster", "fogging machine", "refrigerated van", "mobile veterinary clinic",
    "agriculture promotion vehicle", "chipping machine", "weeder", "generator", "seeder",
    "corn picker", "baler", "manure rotary spreader", "compost windrow turner",
]

NO_FUEL_KEYWORDS = [
    "electric", "electrical", "electric motor", "motor driven", "motor-driven",
    "single phase", "three phase", "1 phase", "3 phase",
    "220v", "230v", "240v", "380v", "440v",
    "gmp", "good manufacturing practices", "food grade", "food-grade",
    "food processing", "processing facility", "processing center", "processing plant",
    "postharvest facility", "stainless", "stainless steel",
    "ss table", "working table", "preparation table", "washing table",
    "packaging", "packing", "vacuum sealer", "sealer", "impulse sealer",
    "continuous band sealer", "bottling", "bottle", "capping", "capper",
    "labeling", "labeler", "filling machine", "filler", "strapping", "strapping machine",
    "mixing machine", "mixer", "pulverizer", "grinder", "slicer", "chopper",
    "washer", "blancher", "dehydrator", "freezer", "chiller", "cold storage",
    "cabinet dryer", "dryer cabinet", "oven", "roaster", "steamer", "pasteurizer",
    "kettle", "juicer", "extractor", "separator", "peeler", "crusher",
    "hydroponics", "greenhouse", "nursery", "building", "warehouse", "storage",
    "solar", "solar-powered", "sensor", "moisture meter", "weighing scale", "scale",
    "tester", "analyzer", "laboratory", "meter", "drone", "uav", "software",
    "computer", "printer", "tablet", "gps", "office", "facility", "structure",
    "shed", "trays", "net", "plastic", "irrigation system", "drip irrigation",
    "sprinkler system", "photovoltaic system", "egg incubator", "rotary composter",
    "rotary sifter", "vermicast sifter", "vermi tea brewer", "misting system",
    "automated disinfection system", "ln2 tank", "hermetic bag", "ice making machine",
    "pressure cooker", "abaca stripper", "fiber decorticator", "coconut coir decorticator",
    "hammer mill", "micro mill", "feed mill", "flour mill", "adlay mill",
    "coffee pulper", "coffee huller", "cacao huller", "paddy huller", "brown rice huller",
    "impeller type huller", "rubber roll type huller", "huller", "mist polisher",
    "rice polisher", "polisher", "rice whitener", "whitener", "destoner",
    "color sorter", "soybean sorter", "seed sorter", "length grader",
    "paddy seed cleaner", "pre cleaner", "vibrating cleaner", "corn grain cleaner",
    "grain collector", "cacao cracker and winnower", "cassava granulator",
    "soybean granulator", "cassava grater", "multi commodity grater",
    "multi commodity grinding machine", "poultry defeathering machine",
    "milking machine", "milk homogenizer", "sack sewing machine",
    "cotton ginning machine", "roasting machine", "melanger",
    "chocolate tempering machine", "mushroom bagger", "feed pelletizer",
    "fertilizer pelletizer", "feed pellet cooler", "briquetting machine",
    "tramline system", "vari trac wheels", "vari-trac wheels",
    "paddy vari trac wheels", "aerator",
]

UNCERTAIN_KEYWORDS = ["equipment", "system", "set", "package", "accessories", "machinery"]


def normalize_text(x):
    if pd.isna(x):
        return ""
    x = str(x).lower().strip()
    x = re.sub(r"[^a-z0-9]+", " ", x)
    x = re.sub(r"\s+", " ", x)
    return x.strip()


def keyword_in_text(keyword, text):
    return normalize_text(keyword) in text


def find_column(df, possible_names):
    normalized_columns = {normalize_text(col): col for col in df.columns}
    for name in possible_names:
        name_norm = normalize_text(name)
        if name_norm in normalized_columns:
            return normalized_columns[name_norm]
    for col in df.columns:
        col_norm = normalize_text(col)
        for name in possible_names:
            if normalize_text(name) in col_norm:
                return col
    return None


def infer_region_from_filename(file_path):
    match = re.search(r"(NCR|CAR|BARMM|NIRR|R\d+[A-Z]?)", file_path.stem.upper())
    return match.group(1) if match else None


def has_valid_power(power_value):
    if power_value is None or pd.isna(power_value):
        return False
    try:
        return float(str(power_value).replace(",", "").strip()) > 0
    except Exception:
        return False


def classify_fuel_relevance(machine_name, power_value=None):
    text = normalize_text(machine_name)
    matched_fuel      = [kw for kw in FUEL_KEYWORDS     if keyword_in_text(kw, text)]
    matched_no_fuel   = [kw for kw in NO_FUEL_KEYWORDS   if keyword_in_text(kw, text)]
    matched_uncertain = [kw for kw in UNCERTAIN_KEYWORDS if keyword_in_text(kw, text)]
    has_power = has_valid_power(power_value)

    if matched_no_fuel:
        return ("NO_FUEL_OR_NON_RELEVANT", ", ".join(matched_fuel), ", ".join(matched_no_fuel), "NO_FUEL_OVERRIDE")
    if matched_fuel:
        return ("FUEL_RELEVANT", ", ".join(matched_fuel), "", "FUEL_KEYWORD_MATCH")
    if has_power:
        return ("UNCERTAIN_REVIEW", "has rated power but unknown machinery", "", "HAS_POWER_BUT_UNKNOWN")
    if matched_uncertain:
        return ("UNCERTAIN_REVIEW", "", ", ".join(matched_uncertain), "AMBIGUOUS_KEYWORD")
    return ("NO_FUEL_OR_NON_RELEVANT", "", "", "NO_MATCH_DEFAULT_NO_FUEL")


def run():
    all_files = []
    for ext in ("*.xlsx", "*.xls", "*.csv"):
        all_files.extend(ABEMIS_EXTRACTED_DIR.rglob(ext))
    all_files = sorted(all_files)
    print("Files found:", len(all_files))

    records = []
    file_logs = []

    for i, file_path in enumerate(all_files, start=1):
        print(f"[{i}/{len(all_files)}] Processing {file_path.name}")
        df, status = read_file_safely(file_path)

        if df is None:
            file_logs.append({"file_name": file_path.name, "status": status, "rows": 0, "machine_column": None, "power_column": None})
            continue

        df = df.dropna(how="all").dropna(axis=1, how="all")
        machine_col = find_column(df, POSSIBLE_MACHINE_COLUMNS)
        power_col   = find_column(df, POSSIBLE_POWER_COLUMNS)
        region      = infer_region_from_filename(file_path)

        if machine_col is None:
            file_logs.append({"file_name": file_path.name, "status": "NO_MACHINE_COLUMN_FOUND", "rows": len(df), "machine_column": None, "power_column": power_col})
            continue

        for _, row in df.iterrows():
            machine_name = row.get(machine_col)
            power_value  = row.get(power_col) if power_col else None
            classification, matched_fuel, matched_no_fuel, rule_applied = classify_fuel_relevance(machine_name, power_value)
            record = row.to_dict()
            record.update({
                "source_file": file_path.name,
                "inferred_region": region,
                "detected_machine_column": machine_col,
                "detected_power_column": power_col,
                "machine_name_for_classification": machine_name,
                "fuel_relevance_class": classification,
                "matched_fuel_keywords": matched_fuel,
                "matched_no_fuel_keywords": matched_no_fuel,
                "classification_rule_applied": rule_applied,
            })
            records.append(record)

        file_logs.append({"file_name": file_path.name, "status": "OK", "rows": len(df), "machine_column": machine_col, "power_column": power_col})

    master   = pd.DataFrame(records)
    file_log = pd.DataFrame(file_logs)

    fuel_relevant = master[master["fuel_relevance_class"] == "FUEL_RELEVANT"].copy()
    no_fuel       = master[master["fuel_relevance_class"] == "NO_FUEL_OR_NON_RELEVANT"].copy()
    uncertain     = master[master["fuel_relevance_class"] == "UNCERTAIN_REVIEW"].copy()

    summary = pd.DataFrame([{
        "total_files_processed":         len(all_files),
        "total_records":                  len(master),
        "fuel_relevant_records":          len(fuel_relevant),
        "no_fuel_or_non_relevant_records": len(no_fuel),
        "uncertain_review_records":        len(uncertain),
    }])

    machinery_summary = (
        master
        .groupby(["machine_name_for_classification", "fuel_relevance_class", "classification_rule_applied"], dropna=False)
        .size()
        .reset_index(name="records")
        .sort_values("records", ascending=False)
    )

    rule_summary = (
        master
        .groupby(["fuel_relevance_class", "classification_rule_applied"], dropna=False)
        .size()
        .reset_index(name="records")
        .sort_values("records", ascending=False)
    )

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        rule_summary.to_excel(writer, sheet_name="Rule Summary", index=False)
        file_log.to_excel(writer, sheet_name="File Log", index=False)
        machinery_summary.to_excel(writer, sheet_name="Machinery Summary", index=False)
        fuel_relevant.to_excel(writer, sheet_name="Fuel Relevant", index=False)
        no_fuel.to_excel(writer, sheet_name="No Fuel", index=False)
        uncertain.to_excel(writer, sheet_name="Uncertain Review", index=False)
        master.to_excel(writer, sheet_name="Master Classified", index=False)

    print("\nDONE. Output saved to:")
    print(OUTPUT_FILE)
    print("\nSummary:")
    print(summary)


if __name__ == "__main__":
    config.create_output_dirs()
    run()
