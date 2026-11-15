
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

DATA_DIR = Path("data/interim/ceres_seasonal/pre_monsoon")
OUTPUT_DIR = Path("reports/data_quality")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(DATA_DIR.glob("*.nc"))
results = []
reference_lat = None
reference_lon = None

for file in files:
    with xr.open_dataset(file) as ds:
        year = int(pd.Timestamp(ds.time.values[0]).year)
        times = pd.DatetimeIndex(ds.time.values)

        lat = ds.lat.values
        lon = ds.lon.values

        expected_start = pd.Timestamp(year, 4, 15)
        expected_end = pd.Timestamp(year, 5, 15)

        hourly_slots = times.floor("h")
        expected_slots = pd.date_range(
            expected_start,
            periods=720,
            freq="h"
        )

        differences = np.diff(times.asi8) / 3.6e12

        if reference_lat is None:
            reference_lat = lat.copy()
            reference_lon = lon.copy()

        grid_consistent = (
            np.array_equal(lat, reference_lat)
            and np.array_equal(lon, reference_lon)
        )

        result = {
            "year": year,
            "filename": file.name,
            "time_count": len(times),
            "latitude_count": len(lat),
            "longitude_count": len(lon),
            "first_timestamp": str(times[0]),
            "last_timestamp": str(times[-1]),
            "duplicate_timestamps": int(times.duplicated().sum()),
            "missing_hourly_slots": len(
                expected_slots.difference(hourly_slots)
            ),
            "unexpected_hourly_slots": len(
                hourly_slots.difference(expected_slots)
            ),
            "min_time_interval_hours": (
                float(differences.min()) if len(differences) else np.nan
            ),
            "max_time_interval_hours": (
                float(differences.max()) if len(differences) else np.nan
            ),
            "within_season": bool(
                (times >= expected_start).all()
                and (times < expected_end).all()
            ),
            "grid_consistent": bool(grid_consistent),
            "lat_range_correct": bool(
                np.isclose(lat.min(), 6.5)
                and np.isclose(lat.max(), 37.5)
            ),
            "lon_range_correct": bool(
                np.isclose(lon.min(), 68.5)
                and np.isclose(lon.max(), 97.5)
            ),
        }

        results.append(result)

df = pd.DataFrame(results)

output = OUTPUT_DIR / "pre_monsoon_final_integrity.csv"
df.to_csv(output, index=False)

print("\n=== PRE-MONSOON FINAL INTEGRITY AUDIT ===")
print(df.to_string(index=False))

print("\nFiles found:", len(files))

checks_passed = (
    len(files) == 12
    and set(df["year"]) == set(range(2010, 2022))
    and (df["time_count"] == 720).all()
    and (df["latitude_count"] == 32).all()
    and (df["longitude_count"] == 30).all()
    and (df["duplicate_timestamps"] == 0).all()
    and (df["missing_hourly_slots"] == 0).all()
    and (df["unexpected_hourly_slots"] == 0).all()
    and df["within_season"].all()
    and df["grid_consistent"].all()
    and df["lat_range_correct"].all()
    and df["lon_range_correct"].all()
)

print("\nFINAL STATUS:", "PASS" if checks_passed else "REVIEW REQUIRED")
print("Report saved to:", output)
