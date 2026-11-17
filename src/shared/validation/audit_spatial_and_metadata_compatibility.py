
from pathlib import Path
import json
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[3]

IMD_DIR = ROOT / "raw_data" / "IMD_Rainfall"
CERES_DIR = ROOT / "data" / "interim" / "ceres_seasonal" / "post_monsoon"
OUT = ROOT / "reports" / "data_quality"

OUT.mkdir(parents=True, exist_ok=True)

YEARS = range(2010, 2022)

def find_coord(ds, candidates):
    lookup = {name.lower(): name for name in ds.coords}
    lookup.update({name.lower(): name for name in ds.dims})

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    raise KeyError(
        f"Could not find coordinate among {candidates}. "
        f"Available coordinates: {list(ds.coords)}"
    )

def coordinate_values(ds, candidates):
    name = find_coord(ds, candidates)
    return name, np.asarray(ds[name].values)

def compare_arrays(a, b):
    return (
        a.shape == b.shape
        and np.array_equal(a, b)
    )

def nearest_coordinate_difference(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)

    if len(a) == 0 or len(b) == 0:
        return None

    return float(np.max(np.min(np.abs(a[:, None] - b[None, :]), axis=1)))

def inspect_dataset(path, dataset_type, year):
    with xr.open_dataset(path, decode_cf=True, mask_and_scale=True) as ds:
        lat_name, lat = coordinate_values(
            ds, ["lat", "latitude"]
        )
        lon_name, lon = coordinate_values(
            ds, ["lon", "longitude"]
        )
        time_name, time = coordinate_values(
            ds, ["time"]
        )

        result = {
            "dataset": dataset_type,
            "year": year,
            "file": str(path.relative_to(ROOT)),
            "dimensions": dict(ds.sizes),
            "latitude_name": lat_name,
            "longitude_name": lon_name,
            "time_name": time_name,
            "latitude_count": int(len(lat)),
            "longitude_count": int(len(lon)),
            "latitude_min": float(np.nanmin(lat)),
            "latitude_max": float(np.nanmax(lat)),
            "longitude_min": float(np.nanmin(lon)),
            "longitude_max": float(np.nanmax(lon)),
            "time_count": int(len(time)),
            "time_start": str(time[0]),
            "time_end": str(time[-1]),
            "variables": list(ds.data_vars),
        }

        if len(time) > 1:
            time_values = pd.to_datetime(time)
            differences = np.diff(time_values.values)
            result["median_time_step_hours"] = float(
                np.median(differences) / np.timedelta64(1, "h")
            )
        else:
            result["median_time_step_hours"] = None

        variable_rows = []

        for name, da in ds.data_vars.items():
            attrs = dict(da.attrs)
            encoding = dict(da.encoding)

            variable_rows.append({
                "dataset": dataset_type,
                "year": year,
                "variable": name,
                "dimensions": str(da.dims),
                "dtype": str(da.dtype),
                "units": attrs.get("units"),
                "long_name": attrs.get("long_name"),
                "standard_name": attrs.get("standard_name"),
                "valid_min": attrs.get("valid_min"),
                "valid_max": attrs.get("valid_max"),
                "valid_range": str(attrs.get("valid_range")),
                "fill_value_attribute": attrs.get("_FillValue"),
                "fill_value_encoding": encoding.get("_FillValue"),
                "scale_factor": encoding.get("scale_factor"),
                "add_offset": encoding.get("add_offset"),
            })

        mask_info = None

        if dataset_type == "IMD":
            rainfall_name = next(
                (name for name in ds.data_vars
                 if name.lower() == "rainfall"),
                None
            )

            if rainfall_name is None:
                raise KeyError(
                    f"RAINFALL variable not found in {path.name}"
                )

            da = ds[rainfall_name]

            if time_name not in da.dims:
                raise ValueError(
                    f"RAINFALL has no {time_name} dimension in {path.name}"
                )

            values = np.asarray(da.values)
            valid = np.isfinite(values)

            if values.ndim != 3:
                raise ValueError(
                    f"Expected 3D rainfall array, got {values.shape}"
                )

            daily_counts = valid.reshape(valid.shape[0], -1).sum(axis=1)

            always_valid = valid.all(axis=0)
            always_missing = (~valid).all(axis=0)
            sometimes_valid = valid.any(axis=0) & (~valid).all(axis=0)

            mask_info = {
                "valid_cells_every_day": int(always_valid.sum()),
                "missing_cells_every_day": int(always_missing.sum()),
                "cells_with_temporal_variation": int(
                    sometimes_valid.sum()
                ),
                "minimum_valid_cells_per_day": int(daily_counts.min()),
                "maximum_valid_cells_per_day": int(daily_counts.max()),
                "daily_valid_counts_constant": bool(
                    daily_counts.min() == daily_counts.max()
                ),
                "valid_mask": always_valid,
            }

        result["mask_info"] = mask_info

        return result, variable_rows, lat, lon

def main():
    imd_results = []
    ceres_results = []
    variable_rows = []
    coordinate_rows = []

    imd_masks = []
    imd_lats = []
    imd_lons = []
    ceres_lats = []
    ceres_lons = []

    print("\n========== IMD METADATA AND MASK AUDIT ==========")

    for year in YEARS:
        path = IMD_DIR / f"RFone_imd_rf_1x1_{year}.nc"

        if not path.exists():
            raise FileNotFoundError(path)

        result, variables, lat, lon = inspect_dataset(
            path, "IMD", year
        )

        imd_results.append(result)
        variable_rows.extend(variables)
        imd_masks.append(result["mask_info"]["valid_mask"])
        imd_lats.append(lat)
        imd_lons.append(lon)

        print(
            f"IMD {year}: {result['time_count']} days, "
            f"{result['latitude_count']} x {result['longitude_count']} grid, "
            f"{result['mask_info']['valid_cells_every_day']} "
            "always-valid cells, "
            f"{result['mask_info']['cells_with_temporal_variation']} "
            "temporally varying cells"
        )

    print("\n========== CERES METADATA AUDIT ==========")

    for year in YEARS:
        path = CERES_DIR / f"CERES_{year}_post_monsoon.nc"

        if not path.exists():
            raise FileNotFoundError(path)

        result, variables, lat, lon = inspect_dataset(
            path, "CERES", year
        )

        ceres_results.append(result)
        variable_rows.extend(variables)
        ceres_lats.append(lat)
        ceres_lons.append(lon)

        print(
            f"CERES {year}: {result['time_count']} observations, "
            f"{result['latitude_count']} x {result['longitude_count']} grid, "
            f"time step={result['median_time_step_hours']} hours"
        )

    # Check coordinate consistency across years.
    imd_lat_consistent = all(
        compare_arrays(imd_lats[0], x) for x in imd_lats[1:]
    )
    imd_lon_consistent = all(
        compare_arrays(imd_lons[0], x) for x in imd_lons[1:]
    )
    ceres_lat_consistent = all(
        compare_arrays(ceres_lats[0], x) for x in ceres_lats[1:]
    )
    ceres_lon_consistent = all(
        compare_arrays(ceres_lons[0], x) for x in ceres_lons[1:]
    )

    imd_mask_consistent = all(
        compare_arrays(imd_masks[0], x) for x in imd_masks[1:]
    )

    # Compare grids using coordinate values.
    imd_lat = imd_lats[0]
    imd_lon = imd_lons[0]
    ceres_lat = ceres_lats[0]
    ceres_lon = ceres_lons[0]

    common_lat = np.intersect1d(imd_lat, ceres_lat)
    common_lon = np.intersect1d(imd_lon, ceres_lon)

    overlap = {
        "common_latitude_count_exact": int(len(common_lat)),
        "common_longitude_count_exact": int(len(common_lon)),
        "exact_common_grid_cells": int(
            len(common_lat) * len(common_lon)
        ),
        "imd_latitude_nearest_difference_degrees": (
            nearest_coordinate_difference(imd_lat, ceres_lat)
        ),
        "imd_longitude_nearest_difference_degrees": (
            nearest_coordinate_difference(imd_lon, ceres_lon)
        ),
        "imd_bounds": {
            "south": float(np.min(imd_lat)),
            "north": float(np.max(imd_lat)),
            "west": float(np.min(imd_lon)),
            "east": float(np.max(imd_lon)),
        },
        "ceres_bounds": {
            "south": float(np.min(ceres_lat)),
            "north": float(np.max(ceres_lat)),
            "west": float(np.min(ceres_lon)),
            "east": float(np.max(ceres_lon)),
        },
        "common_bounds": {
            "south": float(max(np.min(imd_lat), np.min(ceres_lat))),
            "north": float(min(np.max(imd_lat), np.max(ceres_lat))),
            "west": float(max(np.min(imd_lon), np.min(ceres_lon))),
            "east": float(min(np.max(imd_lon), np.max(ceres_lon))),
        },
    }

    summary = {
        "imd": {
            "files_inspected": len(imd_results),
            "latitude_consistent_across_years": imd_lat_consistent,
            "longitude_consistent_across_years": imd_lon_consistent,
            "valid_mask_identical_across_years": imd_mask_consistent,
            "first_year_mask": imd_results[0]["mask_info"],
            "annual_time_counts": {
                str(x["year"]): x["time_count"]
                for x in imd_results
            },
        },
        "ceres": {
            "files_inspected": len(ceres_results),
            "latitude_consistent_across_years": ceres_lat_consistent,
            "longitude_consistent_across_years": ceres_lon_consistent,
            "annual_time_counts": {
                str(x["year"]): x["time_count"]
                for x in ceres_results
            },
        },
        "spatial_comparison": overlap,
    }

    # Remove NumPy arrays from JSON structure.
    summary["imd"]["first_year_mask"].pop("valid_mask", None)

    pd.DataFrame([
        {k: v for k, v in x.items() if k != "mask_info"}
        for x in imd_results + ceres_results
    ]).to_csv(
        OUT / "spatial_metadata_file_summary.csv", index=False
    )

    pd.DataFrame(variable_rows).to_csv(
        OUT / "spatial_metadata_variable_attributes.csv",
        index=False
    )

    pd.DataFrame({
        "imd_valid_mask_latitude": np.repeat(imd_lat, len(imd_lon)),
        "imd_valid_mask_longitude": np.tile(imd_lon, len(imd_lat)),
        "always_valid": imd_masks[0].reshape(-1),
    }).to_csv(
        OUT / "imd_spatial_validity_mask.csv", index=False
    )

    pd.DataFrame({
        "ceres_latitude": ceres_lat
    }).to_csv(
        OUT / "ceres_latitude_coordinates.csv", index=False
    )

    pd.DataFrame({
        "ceres_longitude": ceres_lon
    }).to_csv(
        OUT / "ceres_longitude_coordinates.csv", index=False
    )

    with open(
        OUT / "spatial_metadata_compatibility_summary.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(summary, f, indent=4, default=str)

    print("\n========== CONSISTENCY RESULTS ==========")
    print(f"IMD latitude consistent: {imd_lat_consistent}")
    print(f"IMD longitude consistent: {imd_lon_consistent}")
    print(f"IMD valid mask identical across years: {imd_mask_consistent}")
    print(f"CERES latitude consistent: {ceres_lat_consistent}")
    print(f"CERES longitude consistent: {ceres_lon_consistent}")

    print("\n========== SPATIAL GRID COMPARISON ==========")
    print(json.dumps(overlap, indent=4))

    print("\n========== AUDIT COMPLETE ==========")
    print(f"Reports saved in: {OUT}")

if __name__ == "__main__":
    main()
