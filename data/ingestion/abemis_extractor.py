import re
import shutil
import zipfile

import config
from config import ABEMIS_RAW_DIR, ABEMIS_EXTRACTED_DIR


def get_batch_no(name):
    match = re.search(r"output_batch[_\s-]*(\d+)", name, re.IGNORECASE)
    return int(match.group(1)) + 1 if match else None


def normalize_stem(path):
    return path.stem.strip()


REGION_MAP = {
    "machineries_inv": "NCR",
    "machineries_inv (1)": "CAR",
    "machineries_inv (2)": "R1",
    "machineries_inv (3)": "R2",
    "machineries_inv (4)": "R3",
    "machineries_inv (5)": "R4A",
    "machineries_inv (6)": "R4B",
    "machineries_inv (7)": "R5",
    "machineries_inv (8)": "R6",
    "machineries_inv (9)": "R7",
    "machineries_inv (10)": "R8",
    "machineries_inv (11)": "R9",
    "machineries_inv (12)": "R10",
    "machineries_inv (13)": "R11",
    "machineries_inv (14)": "R12",
    "machineries_inv (15)": "R13",
    "machineries_inv (16)": "BARMM",
    "machineries_inv (17)": "NIRR",
}


def run():
    TEMP_DIR = ABEMIS_EXTRACTED_DIR / "_temp_extracted"
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    total_copied = 0
    zip_files = list(ABEMIS_RAW_DIR.rglob("*.zip"))

    print("ZIP files found:", len(zip_files))

    for zip_path in zip_files:
        zip_stem = normalize_stem(zip_path)

        if zip_stem not in REGION_MAP:
            print("Skipped unmapped ZIP:", zip_path.name)
            continue

        region = REGION_MAP[zip_stem]
        extract_to = TEMP_DIR / zip_stem
        extract_to.mkdir(parents=True, exist_ok=True)

        print(f"\nExtracting {zip_path.name} -> {region}")

        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_to)

        batch_files = [
            p for p in extract_to.rglob("*")
            if p.is_file() and "output_batch" in p.name.lower()
        ]

        print("Batch files found:", len(batch_files))

        for file in batch_files:
            batch_no = get_batch_no(file.name)

            if batch_no is None:
                print("Skipped, no batch number:", file.name)
                continue

            ext = file.suffix if file.suffix else ".csv"
            destination = ABEMIS_EXTRACTED_DIR / f"{region} batch {batch_no}{ext}"

            counter = 2
            while destination.exists():
                destination = ABEMIS_EXTRACTED_DIR / f"{region} batch {batch_no} copy {counter}{ext}"
                counter += 1

            shutil.copy2(file, destination)
            total_copied += 1
            print("Copied:", file.name, "->", destination.name)

    print("\nDONE")
    print("Total copied:", total_copied)
    print("Output folder:", ABEMIS_EXTRACTED_DIR)


if __name__ == "__main__":
    config.create_output_dirs()
    run()
