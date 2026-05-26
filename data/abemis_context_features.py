"""
Build ABEMIS-derived context features keyed by AMTEC machinery_type.

Three features per type:
  abemis_total_count           — nationwide deployments in ABEMIS Fuel Relevant records
  abemis_region_breadth        — number of distinct regions with ≥1 deployment
  abemis_dominant_region_share — share of total from the most-represented region (0–1)

Output: Analytics Output V2/abemis_machinery_context.xlsx
"""

import logging

import pandas as pd

import config
from config import ABEMIS_FUEL_DIR, AMTEC_ANALYTICS_DIR

logger = logging.getLogger(__name__)

CLASSIFIER_XLSX = ABEMIS_FUEL_DIR / "ABEMIS_Fuel_vs_NoFuel_Machinery_V2.xlsx"
OUTPUT_FILE     = AMTEC_ANALYTICS_DIR / "abemis_machinery_context.xlsx"

# Maps normalised ABEMIS machine name substrings → AMTEC machinery_type.
# Keys are matched in order; first hit wins. Lowercase, stripped.
_AMTEC_TYPE_KEYWORDS: dict[str, str] = {
    # Four-Wheel Tractor — must come before "tractor" to avoid false matches
    "four-wheel tractor":                  "Four-Wheel Tractor",
    "four wheel tractor":                  "Four-Wheel Tractor",
    "mini four wheel":                     "Four-Wheel Tractor",
    "crawler-wheel tractor":               "Four-Wheel Tractor",
    "4wt":                                 "Four-Wheel Tractor",

    # Hand Tractor / Walking-Type Agricultural Tractor
    # The AMTEC split: "Hand Tractor" vs "Walking-Type Agricultural Tractor"
    # ABEMIS uses "HANDTRACTOR" and "Walking-type Agricultural Tractor: ..."
    "walking-type agricultural tractor":   "Walking-Type Agricultural Tractor",
    "walking type agricultural tractor":   "Walking-Type Agricultural Tractor",
    "handtractor":                         "Hand Tractor",
    "hand tractor":                        "Hand Tractor",
    "hand tractor/cultivator":             "Hand Tractor",

    # Rotary Tiller
    "rotary tiller":                       "Rotary Tiller",
    "rotavator":                           "Rotary Tiller",

    # Combine Harvester (rice, corn, multi-crop all → same AMTEC type)
    "combine harvester":                   "Combine Harvester",

    # Rice Transplanter
    "transplanter":                        "Rice Transplanter",

    # Reaper
    "reaper":                              "Reaper",

    # Seeder
    "corn seeder":                         "Seeder",
    "precision seeder":                    "Seeder",
    "mechanical corn seeder":              "Seeder",
    "pneumatic corn seeder":               "Seeder",
    "drum seeder":                         "Seeder",
    "rice drum seeder":                    "Seeder",
    "onion seeder":                        "Seeder",
    "tractor-drawn seeder":                "Seeder",
    "riding-type palay seeder":            "Seeder",
    "seeder":                              "Seeder",

    # Sprayer
    "knapsack sprayer":                    "Sprayer",
    "power sprayer":                       "Sprayer",
    "boom sprayer":                        "Sprayer",
    "mist blower":                         "Sprayer",
    "disinfectant sprayer":                "Sprayer",
    "stationary power sprayer":            "Sprayer",

    # Water Pump / Irrigation Pump
    "irrigation pump":                     "Water Pump",
    "pump and engine":                     "Water Pump",   # "Pump and Engine Set" variants
    "open source pump":                    "Water Pump",
    "hydraulic ram pump":                  "Water Pump",
    "jet pump":                            "Water Pump",

    # Small Engine (diesel/gasoline engines, marine engines not pump-specific)
    "marine engine":                       "Small Engine",
    "diesel engine":                       "Small Engine",
    "gasoline engine":                     "Small Engine",
    "generator":                           "Small Engine",

    # Thresher
    "thresher":                            "Thresher",

    # Sheller
    "sheller":                             "Sheller",
    "husker-sheller":                      "Sheller",
    "husker/sheller":                      "Sheller",

    # Rice Mill
    "rice mill":                           "Rice Mill",
    "brown rice mill":                     "Rice Mill",
    "single pass rice mill":               "Rice Mill",
    "corn mill":                           "Rice Mill",   # nearest AMTEC category
    "mini corn mill":                      "Rice Mill",

    # Mechanical Dryer
    "dryer":                               "Mechanical Dryer",
}


def map_abemis_to_amtec_type(machine_name: str) -> str | None:
    """Return the AMTEC machinery_type for an ABEMIS machine name, or None if no match."""
    if not isinstance(machine_name, str):
        return None
    norm = machine_name.lower().strip()
    for keyword, amtec_type in _AMTEC_TYPE_KEYWORDS.items():
        if keyword in norm:
            return amtec_type
    return None


def build_context_table(classifier_xlsx_path) -> pd.DataFrame:
    """
    Read the Fuel Relevant sheet, map each row to an AMTEC machinery_type, then
    aggregate the three context features.  Returns a DataFrame indexed by
    machinery_type with columns:
        abemis_total_count, abemis_region_breadth, abemis_dominant_region_share
    """
    df = pd.read_excel(classifier_xlsx_path, sheet_name="Fuel Relevant")

    # Map ABEMIS names to AMTEC types; drop rows with no match
    df["machinery_type"] = df["machine_name_for_classification"].apply(map_abemis_to_amtec_type)
    matched   = df[df["machinery_type"].notna()].copy()
    unmatched = df[df["machinery_type"].isna()]
    if len(unmatched) > 0:
        logger.debug("ABEMIS rows with no AMTEC type mapping: %d", len(unmatched))

    region_col = "inferred_region"

    total_count = (
        matched
        .groupby("machinery_type")
        .size()
        .rename("abemis_total_count")
    )

    region_breadth = (
        matched
        .dropna(subset=[region_col])
        .groupby("machinery_type")[region_col]
        .nunique()
        .rename("abemis_region_breadth")
    )

    # Dominant region: for each type, find region with max count, then divide by total
    region_counts = (
        matched
        .dropna(subset=[region_col])
        .groupby(["machinery_type", region_col])
        .size()
        .reset_index(name="cnt")
    )
    dominant = (
        region_counts
        .loc[region_counts.groupby("machinery_type")["cnt"].idxmax()]
        .set_index("machinery_type")["cnt"]
    )
    dominant_share = (dominant / total_count).rename("abemis_dominant_region_share")

    context = (
        pd.concat([total_count, region_breadth, dominant_share], axis=1)
        .reset_index()
    )
    context["abemis_region_breadth"]        = context["abemis_region_breadth"].fillna(0).astype(int)
    context["abemis_dominant_region_share"] = context["abemis_dominant_region_share"].round(4)

    return context


def run():
    config.create_output_dirs()
    context = build_context_table(CLASSIFIER_XLSX)
    context.to_excel(OUTPUT_FILE, index=False)
    print("Context table saved to:", OUTPUT_FILE)
    print()
    print(context.to_string(index=False))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    run()
