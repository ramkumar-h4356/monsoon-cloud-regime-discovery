
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import xarray as xr


# ============================================================
# 1. PROJECT PATHS AND CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data" / "interim" / "ceres_seasonal" / "pre_monsoon"
OUTPUT_DIR = ROOT / "reports" / "data_quality"

EXPECTED_YEARS = set(range(2010, 2022))
EXPECTED_DAYS = 30
EXPECTED_HOURS = 720
EXPECTED_LAT = 32
EXPECTED_LON = 30

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. VALIDATION FUNCTION
# ============================================================

def validate_file(file, reference_lat=None, reference_lon=None):

    with xr.open_dataset(file) as ds:

        # Check required coordinates
        required = {"time", "lat", "lon"}

        if not required.issubset(ds.variables):
            raise ValueError(
                f"{file.name}: missing required coordinates"
            )

        times = pd.DatetimeIndex(ds["time"].values)
        lat = np.asarray(ds["lat"].values)
        lon = np.asarray(ds["lon"].values)

        if len(times) == 0 or len(lat) == 0 or len(lon) == 0:
            raise ValueError(
                f"{file.name}: empty time or spatial coordinates"
            )

        # Determine year from filename
        import re

        match = re.fullmatch(
            r"CERES_(\d{4})_pre_monsoon\.nc",
            file.name
        )

        if match is None:
            raise ValueError(
                f"Unexpected filename: {file.name}"
            )

        year = int(match.group(1))

        # Expected seasonal boundaries
        expected_start = pd.Timestamp(year, 4, 15)
        expected_end = pd.Timestamp(year, 5, 15)

        expected_slots = pd.date_range(
            expected_start,
            periods=EXPECTED_HOURS,
            freq="h"
        )

        # ====================================================
        # 3. TEMPORAL VALIDATION
        # ====================================================

        hourly_slots = times.floor("h")

        duplicate_timestamps = int(
            times.duplicated().sum()
        )

        duplicate_hourly_slots = int(
            hourly_slots.duplicated().sum()
        )

        missing_hourly_slots = int(
            len(expected_slots.difference(hourly_slots))
        )

        unexpected_hourly_slots = int(
            len(hourly_slots.difference(expected_slots))
        )

        unique_dates = int(
            times.normalize().nunique()
        )

        chronologically_ordered = bool(
            times.is_monotonic_increasing
            and not times.hasnans
        )

        within_season = bool(
            not times.hasnans
            and (times >= expected_start).all()
            and (times < expected_end).all()
        )

        expected_dates = pd.date_range(
            expected_start,
            periods=EXPECTED_DAYS,
            freq="D"
        )

        actual_dates = times.normalize()

        missing_dates = int(
            len(expected_dates.difference(actual_dates))
        )

        unexpected_dates = int(
            len(actual_dates.difference(expected_dates))
        )

        # Calculate timestamp interval differences
        if len(times) > 1 and not times.hasnans:
            differences = np.diff(times.asi8) / 3.6e12

            min_interval = float(differences.min())
            max_interval = float(differences.max())
        else:
            min_interval = np.nan
            max_interval = np.nan

        # ====================================================
        # 4. SPATIAL COORDINATE VALIDATION
        # ====================================================

        lat_finite = bool(np.isfinite(lat).all())
        lon_finite = bool(np.isfinite(lon).all())

        lat_unique = bool(
            len(np.unique(lat)) == len(lat)
        )

        lon_unique = bool(
            len(np.unique(lon)) == len(lon)
        )

        lat_ordered = bool(
            np.all(np.diff(lat) > 0)
            or np.all(np.diff(lat) < 0)
        )

        lon_ordered = bool(
            np.all(np.diff(lon) > 0)
            or np.all(np.diff(lon) < 0)
        )

        lat_range_correct = bool(
            lat_finite
            and np.isclose(lat.min(), 6.5)
            and np.isclose(lat.max(), 37.5)
        )

        lon_range_correct = bool(
            lon_finite
            and np.isclose(lon.min(), 68.5)
            and np.isclose(lon.max(), 97.5)
        )

        # Compare spatial coordinates across years
        if reference_lat is None:
            reference_lat = lat.copy()
            reference_lon = lon.copy()

        grid_consistent = bool(
            np.array_equal(lat, reference_lat)
            and np.array_equal(lon, reference_lon)
        )

        # ====================================================
        # 5. DATASET DIMENSIONS
        # ====================================================

        time_count = len(times)
        latitude_count = len(lat)
        longitude_count = len(lon)

        dimensions_correct = bool(
            time_count == EXPECTED_HOURS
            and latitude_count == EXPECTED_LAT
            and longitude_count == EXPECTED_LON
        )

        # ====================================================
        # 6. COLLECT VALIDATION RESULTS
        # ====================================================

        result = {
            "year": year,
            "filename": file.name,

            "time_count": time_count,
            "latitude_count": latitude_count,
            "longitude_count": longitude_count,

            "first_timestamp": str(times[0]),
            "last_timestamp": str(times[-1]),

            "duplicate_timestamps": duplicate_timestamps,
            "duplicate_hourly_slots": duplicate_hourly_slots,

            "missing_hourly_slots": missing_hourly_slots,
            "unexpected_hourly_slots": unexpected_hourly_slots,

            "unique_dates": unique_dates,
            "missing_dates": missing_dates,
            "unexpected_dates": unexpected_dates,

            "chronologically_ordered": chronologically_ordered,
            "within_season": within_season,

            "min_time_interval_hours": min_interval,
            "max_time_interval_hours": max_interval,

            "lat_finite": lat_finite,
            "lon_finite": lon_finite,

            "lat_unique": lat_unique,
            "lon_unique": lon_unique,

            "lat_ordered": lat_ordered,
            "lon_ordered": lon_ordered,

            "lat_range_correct": lat_range_correct,
            "lon_range_correct": lon_range_correct,

            "grid_consistent": grid_consistent,
            "dimensions_correct": dimensions_correct,
        }

        # ====================================================
        # 7. INDIVIDUAL FILE PASS/FAIL
        # ====================================================

        result["validation_passed"] = bool(
            year in EXPECTED_YEARS
            and dimensions_correct
            and duplicate_timestamps == 0
            and duplicate_hourly_slots == 0
            and missing_hourly_slots == 0
            and unexpected_hourly_slots == 0
            and unique_dates == EXPECTED_DAYS
            and missing_dates == 0
            and unexpected_dates == 0
            and chronologically_ordered
            and within_season
            and lat_finite
            and lon_finite
            and lat_unique
            and lon_unique
            and lat_ordered
            and lon_ordered
            and lat_range_correct
            and lon_range_correct
            and grid_consistent
        )

        return result, reference_lat, reference_lon


# ============================================================
# 8. MAIN PROGRAM
# ============================================================

def main():

    if not DATA_DIR.exists():
        print("ERROR: Dataset directory does not exist.")
        print(DATA_DIR)
        return 1

    files = sorted(DATA_DIR.glob("*.nc"))

    print("\n" + "=" * 65)
    print("PRE-MONSOON FINAL INTEGRITY AUDIT")
    print("=" * 65)

    print("Dataset directory:", DATA_DIR)
    print("Files found:", len(files))

    if not files:
        print("ERROR: No NetCDF files found.")
        return 1

    results = []
    reference_lat = None
    reference_lon = None

    for file in files:

        print(f"\nChecking: {file.name}")

        try:
            result, reference_lat, reference_lon = validate_file(
                file,
                reference_lat,
                reference_lon
            )

            results.append(result)

            if result["validation_passed"]:
                print("Status: PASS")
            else:
                print("Status: REVIEW REQUIRED")

        except Exception as error:
            print(f"Status: FAILED - {error}")

            results.append({
                "filename": file.name,
                "validation_passed": False,
                "error": str(error)
            })

    # ========================================================
    # 9. SAVE CSV REPORT
    # ========================================================

    df = pd.DataFrame(results)

    output_file = (
        OUTPUT_DIR / "pre_monsoon_final_integrity.csv"
    )

    df.to_csv(output_file, index=False)

    # ========================================================
    # 10. FINAL VALIDATION
    # ========================================================

    valid_years = set(
        pd.to_numeric(
            df.get("year", pd.Series(dtype=float)),
            errors="coerce"
        ).dropna().astype(int)
    )

    all_passed = bool(
        len(files) == 12
        and len(df) == 12
        and valid_years == EXPECTED_YEARS
        and df["validation_passed"].fillna(False).eq(True).all()
    )

    print("\n" + "=" * 65)
    print("FINAL VALIDATION SUMMARY")
    print("=" * 65)

    print("Files checked:", len(files))
    print(
        "Files passed:",
        int(df["validation_passed"].fillna(False).eq(True).sum())
    )
    print(
        "Files requiring review:",
        int(df["validation_passed"].fillna(False).eq(False).sum())
    )

    print(
        "\nFINAL STATUS:",
        "PASS" if all_passed else "REVIEW REQUIRED"
    )

    print("Report saved to:", output_file)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
