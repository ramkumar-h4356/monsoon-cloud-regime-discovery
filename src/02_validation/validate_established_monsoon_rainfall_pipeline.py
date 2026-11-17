"""Run the established-monsoon rainfall and cloud-assignment preflight audit.

Run from any working directory:
    python src/02_validation/validate_established_monsoon_rainfall_pipeline.py

The script reads existing files only. It does not modify NetCDF inputs or
existing research outputs. New audit CSVs are written only if their paths do
not already exist.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(VALIDATION_DIR))

from established_monsoon_rainfall_validation import (  # noqa: E402
    CLUSTER_COLUMNS,
    EXPECTED_YEARS,
    KEYS,
    RainfallValidationError,
    build_rainfall_key_frame,
    validate_assignment_frame,
    validate_coordinate,
    validate_rainfall_units,
    validate_rainfall_values,
    validate_dates,
    validate_matched_frame,
    validate_summary_frame,
)

ASSIGNMENT_FILE = ROOT / "results/tables/07_clustering/assignments/established_monsoon_fixed_cluster_assignments.csv"
RAINFALL_DIR = ROOT / "data/processed/rainfall_daily/established_monsoon"
REPORT_DIR = ROOT / "reports/data_quality"
ANNUAL_AUDIT = REPORT_DIR / "established_monsoon_rainfall_pipeline_validation.csv"
CLUSTER_YEAR_AUDIT = REPORT_DIR / "established_monsoon_rainfall_cluster_year_coverage.csv"
MATCHED_FILE = ROOT / "results/tables/07_clustering/rainfall_association/established_monsoon_cloud_rainfall_matched.csv"

SUMMARY_TABLE_SPECS = [
    ("established_monsoon_rainfall_pooled.csv", ["variant", "k", "cluster"], ["observations", "mean_mm", "median_mm", "q25_mm", "q75_mm", "q90_mm", "q95_mm", "positive_rainfall_pct", "wet_day_pct"], ["observations"]),
    ("established_monsoon_rainfall_by_year.csv", ["variant", "k", "year", "cluster"], ["observations", "mean_mm", "median_mm", "q25_mm", "q75_mm", "q90_mm", "q95_mm", "positive_rainfall_pct", "wet_day_pct"], ["observations", "year"]),
    ("established_monsoon_rainfall_by_period.csv", ["variant", "k", "period", "cluster"], ["observations", "mean_mm", "median_mm", "q25_mm", "q75_mm", "q90_mm", "q95_mm", "positive_rainfall_pct", "wet_day_pct"], ["observations"]),
    ("established_monsoon_annual_pairwise_contrasts.csv", ["variant", "k", "year", "cluster_a", "cluster_b"], ["observations_a", "observations_b", "mean_difference_a_minus_b_mm", "median_difference_a_minus_b_mm", "wet_day_difference_a_minus_b_pp", "positive_rainfall_difference_a_minus_b_pp"], ["observations_a", "observations_b", "year"]),
    ("within_cell_analysis/within_cell_year_pairwise_differences.csv", ["year", "latitude", "longitude", "variant", "k", "cluster_a", "cluster_b"], ["mean_rainfall_a_mm", "mean_rainfall_b_mm", "observations_a", "observations_b", "mean_difference_a_minus_b_mm"], ["observations_a", "observations_b", "year"]),
    ("within_cell_analysis/within_cell_minimum_support_sensitivity.csv", ["minimum_observations_per_cluster", "variant", "k", "cluster_a", "cluster_b"], ["matched_cell_years", "unique_cells", "mean_paired_difference_mm", "median_paired_difference_mm", "q25_difference_mm", "q75_difference_mm", "positive_difference_pct", "negative_difference_pct", "mean_observations_a", "mean_observations_b"], ["minimum_observations_per_cluster", "matched_cell_years", "unique_cells"]),
    ("within_cell_analysis/period_comparison/paired_spatial_period_rainfall_contrasts_by_cell.csv", ["variant", "k", "cluster_a", "cluster_b", "latitude", "longitude"], ["2010_2016", "2017_2021", "change_in_difference_mm"], []),
    ("within_cell_analysis/annual_within_cell_pairwise_summary.csv", ["variant", "k", "year", "cluster_a", "cluster_b"], ["matched_cell_years", "mean_paired_difference_mm", "median_paired_difference_mm", "q25_paired_difference_mm", "q75_paired_difference_mm", "positive_difference_pct", "negative_difference_pct", "zero_difference_pct", "mean_observations_a", "mean_observations_b", "minimum_observations_a", "minimum_observations_b"], ["matched_cell_years", "year", "minimum_observations_a", "minimum_observations_b"]),
    ("within_cell_analysis/overall_within_cell_pairwise_summary.csv", ["variant", "k", "cluster_a", "cluster_b"], ["matched_cell_years", "mean_paired_difference_mm", "median_paired_difference_mm", "q25_paired_difference_mm", "q75_paired_difference_mm", "positive_difference_pct", "negative_difference_pct", "zero_difference_pct", "mean_observations_a", "mean_observations_b", "minimum_observations_a", "minimum_observations_b"], ["matched_cell_years", "minimum_observations_a", "minimum_observations_b"]),
    ("within_cell_analysis/period_comparison/paired_spatial_period_rainfall_contrasts.csv", ["variant", "k", "cluster_a", "cluster_b"], ["paired_cells", "pre_period_mean_difference_mm", "post_period_mean_difference_mm", "mean_change_mm", "median_change_mm", "q25_change_mm", "q75_change_mm", "cells_with_direction_change", "positive_change_pct", "negative_change_pct"], ["paired_cells", "cells_with_direction_change"]),
    ("within_cell_analysis/period_comparison/period_support_sensitivity.csv", ["minimum_qualifying_years_per_period", "variant", "k", "cluster_a", "cluster_b"], ["paired_cells", "pre_mean_difference_mm", "post_mean_difference_mm", "mean_change_mm", "median_change_mm", "cells_with_positive_change_pct", "cells_with_negative_change_pct"], ["minimum_qualifying_years_per_period", "paired_cells"]),
]


def find_coord(ds: xr.Dataset, candidates: tuple[str, ...]) -> str:
    lookup = {name.lower(): name for name in ds.coords}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    raise RainfallValidationError(f"Required coordinate not found; candidates={candidates}")


def inspect_year(year: int, assignments: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    path = RAINFALL_DIR / f"IMD_{year}_established_monsoon_daily.nc"
    if not path.is_file():
        raise FileNotFoundError(path)

    with xr.open_dataset(path) as ds:
        time_name = find_coord(ds, ("time", "TIME"))
        lat_name = find_coord(ds, ("latitude", "LATITUDE", "lat"))
        lon_name = find_coord(ds, ("longitude", "LONGITUDE", "lon"))
        rainfall_names = [name for name in ds.data_vars if name.lower() == "rainfall"]
        if len(rainfall_names) != 1:
            raise RainfallValidationError(f"{year}: expected exactly one RAINFALL variable; found {rainfall_names}")
        rainfall = ds[rainfall_names[0]]
        expected_dims = {time_name, lat_name, lon_name}
        if set(rainfall.dims) != expected_dims or len(rainfall.dims) != 3:
            raise RainfallValidationError(f"{year}: unexpected RAINFALL dimensions {rainfall.dims}")

        dates = validate_dates(ds[time_name].values, year)
        lat = validate_coordinate(ds[lat_name].values, "latitude", 32)
        lon = validate_coordinate(ds[lon_name].values, "longitude", 30)
        validate_rainfall_units(rainfall.attrs.get("units"), year)
        values = np.asarray(rainfall.transpose(time_name, lat_name, lon_name).values)
        valid_count, missing_count = validate_rainfall_values(values, year)
        if values.shape != (30, 32, 30):
            raise RainfallValidationError(f"{year}: unexpected rainfall array shape {values.shape}")

        year_assignments = assignments.loc[assignments["year"] == year].copy()
        if year_assignments.empty:
            raise RainfallValidationError(f"{year}: no cloud assignments found")
        if not year_assignments["date"].isin(dates).all():
            raise RainfallValidationError(f"{year}: assignment dates do not belong to rainfall date coordinate")
        if not year_assignments["latitude"].isin(lat).all():
            raise RainfallValidationError(f"{year}: assignment latitude outside rainfall grid")
        if not year_assignments["longitude"].isin(lon).all():
            raise RainfallValidationError(f"{year}: assignment longitude outside rainfall grid")

        valid_keys = build_rainfall_key_frame(year, dates, lat, lon, values)
        matched = year_assignments.merge(valid_keys, on=KEYS, how="inner", validate="one_to_one")
        assignment_without_valid_rain = len(year_assignments) - len(matched)
        valid_rain_without_assignment = len(valid_keys) - len(matched)

        row = {
            "year": year,
            "rainfall_days": len(dates),
            "latitude_count": len(lat),
            "longitude_count": len(lon),
            "valid_rainfall_observations": valid_count,
            "missing_rainfall_observations": missing_count,
            "negative_rainfall_observations": 0,
            "infinite_rainfall_observations": 0,
            "cloud_assignment_observations": len(year_assignments),
            "matched_cloud_rainfall_observations": len(matched),
            "assignments_without_valid_rainfall": assignment_without_valid_rain,
            "valid_rainfall_without_cloud_assignment": valid_rain_without_assignment,
            "status": "PASS",
        }
        return row, valid_keys


def main() -> None:
    if not ASSIGNMENT_FILE.is_file():
        raise FileNotFoundError(ASSIGNMENT_FILE)
    if ANNUAL_AUDIT.exists() or CLUSTER_YEAR_AUDIT.exists():
        raise FileExistsError(
            "Refusing to overwrite existing M2 audit output(s): "
            f"{ANNUAL_AUDIT if ANNUAL_AUDIT.exists() else ''} "
            f"{CLUSTER_YEAR_AUDIT if CLUSTER_YEAR_AUDIT.exists() else ''}"
        )

    raw_assignments = pd.read_csv(ASSIGNMENT_FILE)
    assignments, issues = validate_assignment_frame(raw_assignments)
    annual_rows = []
    all_valid_keys = []

    for year in EXPECTED_YEARS:
        print(f"Validating rainfall and assignment alignment: {year}")
        row, valid_keys = inspect_year(year, assignments)
        annual_rows.append(row)
        all_valid_keys.append(valid_keys)

    valid_rainfall_keys = pd.concat(all_valid_keys, ignore_index=True)
    if valid_rainfall_keys.duplicated(KEYS).any():
        raise RainfallValidationError("Duplicate valid rainfall keys across annual files")

    matched_all = assignments.merge(
        valid_rainfall_keys, on=KEYS, how="inner", validate="one_to_one"
    )

    # Validate the existing matched table against a fresh exact-key join.
    if not MATCHED_FILE.is_file():
        raise FileNotFoundError(MATCHED_FILE)
    stored_matched = validate_matched_frame(pd.read_csv(MATCHED_FILE))
    recomputed_keys = matched_all[KEYS].copy()
    stored_keys = stored_matched[KEYS].copy()
    for key_frame in (recomputed_keys, stored_keys):
        key_frame["year"] = key_frame["year"].astype(int)
        key_frame["date"] = pd.to_datetime(key_frame["date"]).dt.normalize()
        key_frame["latitude"] = key_frame["latitude"].astype(float)
        key_frame["longitude"] = key_frame["longitude"].astype(float)
    recomputed_keys = recomputed_keys.sort_values(KEYS).reset_index(drop=True)
    stored_keys = stored_keys.sort_values(KEYS).reset_index(drop=True)
    if not recomputed_keys.equals(stored_keys):
        raise RainfallValidationError(
            "Stored cloud-rainfall matched table does not contain exactly the "
            "same year/date/latitude/longitude keys as the recomputed exact join"
        )

    # Validate existing pooled, annual, within-cell and period summaries.
    association_dir = MATCHED_FILE.parent
    validated_summary_tables = 0
    for relative_path, key_columns, numeric_columns, nonnegative_columns in SUMMARY_TABLE_SPECS:
        summary_path = association_dir / relative_path
        if not summary_path.is_file():
            raise FileNotFoundError(summary_path)
        summary_frame = pd.read_csv(summary_path)
        validate_summary_frame(
            summary_frame,
            name=relative_path,
            key_columns=key_columns,
            numeric_columns=numeric_columns,
            allow_empty=False,
            nonnegative_columns=nonnegative_columns,
        )
        validated_summary_tables += 1

    annual = pd.DataFrame(annual_rows)

    coverage_rows = []
    for column, k in CLUSTER_COLUMNS.items():
        for year in EXPECTED_YEARS:
            year_frame = assignments.loc[assignments["year"] == year, column]
            for label in range(k):
                count = int((year_frame == label).sum())
                coverage_rows.append({
                    "model": column,
                    "year": year,
                    "cluster": label,
                    "assignment_observations": count,
                    "status": "PRESENT" if count else "MISSING_CLUSTER_YEAR",
                })

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    annual.to_csv(ANNUAL_AUDIT, index=False)
    pd.DataFrame(coverage_rows).to_csv(CLUSTER_YEAR_AUDIT, index=False)

    print("\n========== M2 RAINFALL PREFLIGHT ==========")
    print(annual.to_string(index=False))
    print(f"\nAssignment observations: {len(assignments):,}")
    print(f"Valid rainfall observations: {len(valid_rainfall_keys):,}")
    print(f"Matched cloud-rainfall observations: {len(matched_all):,}")
    print(f"Assignments without valid rainfall: {len(assignments) - len(matched_all):,}")
    print(f"Missing cluster-year combinations flagged: {sum(i.code == 'MISSING_CLUSTER_YEAR' for i in issues)}")
    print(f"Existing rainfall summary tables validated: {validated_summary_tables}")
    print(f"Annual audit: {ANNUAL_AUDIT}")
    print(f"Cluster-year audit: {CLUSTER_YEAR_AUDIT}")
    print("\nPASS: rainfall inputs and exact-key alignment passed required validation.")
    print("Review MISSING_CLUSTER_YEAR rows as support warnings, not automatic failures.")


if __name__ == "__main__":
    main()
