from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]

ASSIGNMENT_FILE = (
    ROOT / "results/tables/07_clustering/assignments/"
    "established_monsoon_fixed_cluster_assignments.csv"
)
RAINFALL_DIR = ROOT / "data/processed/rainfall_daily/established_monsoon"
OUTPUT_DIR = ROOT / "results/tables/07_clustering/assignments"
OUTPUT_FILE = OUTPUT_DIR / "established_monsoon_rainfall_alignment_audit.csv"

def find_coord(ds, candidates):
    lookup = {name.lower(): name for name in ds.coords}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    raise ValueError(f"Coordinate not found: {candidates}")

def main():
    if OUTPUT_FILE.exists():
        raise FileExistsError(f"Refusing to overwrite: {OUTPUT_FILE}")

    assignments = pd.read_csv(ASSIGNMENT_FILE)
    assignments["date"] = pd.to_datetime(assignments["date"])
    assignments["year"] = assignments["year"].astype(int)

    keys = ["year", "date", "latitude", "longitude"]

    if assignments.duplicated(keys).any():
        raise ValueError("Duplicate cloud assignment keys detected.")

    rows = []

    for year in range(2010, 2022):
        print(f"\nAuditing {year}")

        path = RAINFALL_DIR / f"IMD_{year}_established_monsoon_daily.nc"

        if not path.exists():
            raise FileNotFoundError(path)

        year_assignments = assignments[
            assignments["year"] == year
        ].copy()

        with xr.open_dataset(path) as ds:
            print("Data variables:", list(ds.data_vars))
            print("Dimensions:", dict(ds.sizes))

            time_name = find_coord(ds, ["TIME", "time"])
            lat_name = find_coord(ds, ["LATITUDE", "latitude", "lat"])
            lon_name = find_coord(ds, ["LONGITUDE", "longitude", "lon"])

            rainfall_candidates = [
                name for name in ds.data_vars
                if name.lower() == "rainfall"
            ]

            if len(rainfall_candidates) != 1:
                raise ValueError(
                    f"{year}: expected one RAINFALL variable, "
                    f"found {rainfall_candidates}"
                )

            rainfall_name = rainfall_candidates[0]
            rainfall = ds[rainfall_name]

            expected_dims = {time_name, lat_name, lon_name}

            if set(rainfall.dims) != expected_dims:
                raise ValueError(
                    f"{year}: unexpected rainfall dimensions "
                    f"{rainfall.dims}"
                )

            rain_dates = pd.DatetimeIndex(
                pd.to_datetime(ds[time_name].values)
            ).normalize()

            assignment_dates = pd.DatetimeIndex(
                year_assignments["date"].unique()
            ).normalize()

            if len(rain_dates) != 30 or len(assignment_dates) != 30:
                raise ValueError(f"{year}: expected 30 daily dates.")

            if not rain_dates.equals(assignment_dates.sort_values()):
                raise ValueError(f"{year}: rainfall dates do not match.")

            rain_lat = np.asarray(ds[lat_name].values, dtype=float)
            rain_lon = np.asarray(ds[lon_name].values, dtype=float)

            assignment_lat = np.sort(
                year_assignments["latitude"].unique()
            )
            assignment_lon = np.sort(
                year_assignments["longitude"].unique()
            )

            if not np.array_equal(rain_lat, assignment_lat):
                raise ValueError(f"{year}: latitude coordinates differ.")

            if not np.array_equal(rain_lon, assignment_lon):
                raise ValueError(f"{year}: longitude coordinates differ.")

            values = rainfall.transpose(
                time_name, lat_name, lon_name
            ).values

            if values.shape != (30, 32, 30):
                raise ValueError(
                    f"{year}: unexpected rainfall array shape {values.shape}"
                )

            valid_mask = np.isfinite(values)

            valid_cells_per_day = valid_mask.sum(axis=(1, 2))

            lat_grid, lon_grid = np.meshgrid(
                rain_lat, rain_lon, indexing="ij"
            )

            valid_keys = []

            for day_index, date in enumerate(rain_dates):
                valid_lat, valid_lon = np.where(valid_mask[day_index])

                for lat_index, lon_index in zip(valid_lat, valid_lon):
                    valid_keys.append((
                        year,
                        date,
                        float(lat_grid[lat_index, lon_index]),
                        float(lon_grid[lat_index, lon_index])
                    ))

            valid_frame = pd.DataFrame(valid_keys, columns=keys)

            matched = year_assignments.merge(
                valid_frame,
                on=keys,
                how="inner",
                validate="one_to_one"
            )

            valid_observations = int(valid_mask.sum())
            matched_observations = len(matched)

            rows.append({
                "year": year,
                "rainfall_days": len(rain_dates),
                "grid_cells": len(rain_lat) * len(rain_lon),
                "valid_rainfall_observations": valid_observations,
                "missing_rainfall_observations": int(valid_mask.size - valid_observations),
                "minimum_valid_cells_per_day": int(valid_cells_per_day.min()),
                "maximum_valid_cells_per_day": int(valid_cells_per_day.max()),
                "cloud_assignment_observations": len(year_assignments),
                "cloud_rainfall_matched_observations": matched_observations,
                "cloud_observations_without_valid_rainfall": (
                    len(year_assignments) - matched_observations
                )
            })

            print("Rainfall variable:", rainfall_name)
            print("Rainfall dimensions:", rainfall.dims)
            print("Valid rainfall observations:", valid_observations)
            print("Valid cells/day: min =", valid_cells_per_day.min(),
                  "max =", valid_cells_per_day.max())
            print("Cloud assignment rows:", len(year_assignments))
            print("Valid cloud-rainfall matches:", matched_observations)

    summary = pd.DataFrame(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUTPUT_FILE, index=False)

    print("\n===== ALIGNMENT AUDIT COMPLETED =====")
    print(summary.to_string(index=False))
    print("\nTotal cloud assignments:", summary["cloud_assignment_observations"].sum())
    print("Total valid rainfall observations:",
          summary["valid_rainfall_observations"].sum())
    print("Total matched cloud-rainfall observations:",
          summary["cloud_rainfall_matched_observations"].sum())
    print("Audit output:", OUTPUT_FILE)

if __name__ == "__main__":
    main()
