
from pathlib import Path
import gzip
import shutil
import tempfile

import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[3]

SOURCE_DIR = ROOT / "raw_data" / "CERES"
OUTPUT_DIR = ROOT / "data" / "interim" / "ceres_extracted"
TEMP_DIR = ROOT / "data" / "interim"

LAT_MIN, LAT_MAX = 6.0, 38.0
LON_MIN, LON_MAX = 68.0, 98.0

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = range(2010, 2022)

WINDOWS = [
    ("pre_monsoon", "04-15", "05-14"),
    ("established_monsoon", "07-15", "08-13"),
    ("withdrawal", "09-15", "10-14"),
]


def build_time_mask(time_values):
    mask = np.zeros(len(time_values), dtype=bool)

    for year in YEARS:
        for _, start_md, end_md in WINDOWS:
            start = np.datetime64(f"{year}-{start_md}")
            end = np.datetime64(
                f"{year}-{end_md}"
            ) + np.timedelta64(1, "D")

            mask |= (time_values >= start) & (time_values < end)

    return mask


def extract_file(source_file):
    print("\n" + "=" * 75)
    print("PROCESSING:", source_file.name)

    with tempfile.TemporaryDirectory(dir=TEMP_DIR) as temp_folder:
        temp_nc = Path(temp_folder) / source_file.name[:-3]

        print("Temporarily decompressing...")

        with gzip.open(source_file, "rb") as compressed:
            with open(temp_nc, "wb") as decompressed:
                shutil.copyfileobj(compressed, decompressed)

        print("Opening NetCDF...")

        with xr.open_dataset(temp_nc, engine="netcdf4") as ds:

            required = ["time", "lat", "lon"]
            missing = [name for name in required if name not in ds.coords]

            if missing:
                raise ValueError(
                    f"Missing required coordinates: {missing}"
                )

            time_values = ds["time"].values.astype("datetime64[ns]")

            time_mask = build_time_mask(time_values)

            lat_values = ds["lat"].values
            lon_values = ds["lon"].values

            lat_mask = (
                (lat_values >= LAT_MIN) &
                (lat_values <= LAT_MAX)
            )

            lon_mask = (
                (lon_values >= LON_MIN) &
                (lon_values <= LON_MAX)
            )

            time_indices = np.flatnonzero(time_mask)
            lat_indices = np.flatnonzero(lat_mask)
            lon_indices = np.flatnonzero(lon_mask)

            if (
                len(time_indices) == 0
                or len(lat_indices) == 0
                or len(lon_indices) == 0
            ):
                print("No matching observations. Skipping.")
                return

            cropped = ds.isel(
                time=time_indices,
                lat=lat_indices,
                lon=lon_indices
            )

            output_name = (
                source_file.name
                .replace(".nc.gz", "_cropped.nc")
            )

            output_file = OUTPUT_DIR / output_name
            partial_file = OUTPUT_DIR / (output_name + ".partial")

            encoding = {
                name: {
                    "zlib": True,
                    "complevel": 4
                }
                for name in cropped.data_vars
            }

            print("Original dimensions:", dict(ds.sizes))
            print("Cropped dimensions:", dict(cropped.sizes))
            print("Selected observations:", len(time_indices))
            print("Saving cropped dataset...")

            try:
                cropped.to_netcdf(
                    partial_file,
                    engine="netcdf4",
                    encoding=encoding
                )
                partial_file.replace(output_file)
            except Exception:
                if partial_file.exists():
                    partial_file.unlink()
                raise

            print("Saved:", output_file)
            print(
                "Output size:",
                f"{output_file.stat().st_size / (1024 ** 2):.2f} MB"
            )


def main():
    source_files = sorted(SOURCE_DIR.glob("*.nc.gz"))

    if not source_files:
        raise FileNotFoundError(
            f"No compressed CERES files found in {SOURCE_DIR}"
        )

    print("CERES TEMPORAL AND SPATIAL EXTRACTION")
    print("Study period: 2010–2021")
    print("Latitude:", LAT_MIN, "to", LAT_MAX)
    print("Longitude:", LON_MIN, "to", LON_MAX)
    print("Source files:", len(source_files))

    for source_file in source_files:
        extract_file(source_file)

    print("\nEXTRACTION PROCESS FINISHED")
    print("Output directory:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
