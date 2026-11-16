
from pathlib import Path
import xarray as xr

ROOT = Path(__file__).resolve().parents[3] / "raw_data"

FOLDERS = [
    "CERES",
    "IMD_Rainfall",
    "NOAA_RONI",
    "NOAA_DMI"
]

print("=" * 65)
print("MONSOON RESEARCH DATASET VERIFICATION")
print("=" * 65)

for folder_name in FOLDERS:
    folder = ROOT / folder_name

    print(f"\n\n{'=' * 55}")
    print(f"FOLDER: {folder_name}")
    print("=" * 55)

    if not folder.exists():
        print("STATUS: FOLDER NOT FOUND")
        continue

    files = [f for f in folder.rglob("*") if f.is_file()]

    if not files:
        print("STATUS: NO FILES FOUND")
        continue

    total_size = 0

    for file in files:
        size_mb = file.stat().st_size / (1024 ** 2)
        total_size += file.stat().st_size

        print(f"\nFile: {file.name}")
        print(f"Size: {size_mb:.2f} MB")
        print(f"Extension: {''.join(file.suffixes)}")

        if file.name.endswith(".nc"):
            try:
                with xr.open_dataset(file) as ds:
                    print("NetCDF: READABLE")
                    print("Dimensions:", dict(ds.sizes))
                    print("Variables:", list(ds.data_vars))
                    print("Coordinates:", list(ds.coords))
            except Exception as e:
                print("NetCDF: ERROR")
                print("Reason:", str(e)[:300])

        elif file.name.endswith(".nc.gz"):
            print("NetCDF: COMPRESSED - NOT OPENED")

        elif file.suffix.lower() in [".csv", ".txt"]:
            print("Text file: PRESENT")

    print(f"\nFolder total: {total_size / (1024 ** 3):.2f} GB")

print("\n\nVERIFICATION REPORT COMPLETE")
