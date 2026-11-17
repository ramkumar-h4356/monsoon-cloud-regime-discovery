"""M18.7 preflight: validate the 36 CERES inputs and estimate output storage.

This script does not impute, scale, write model-ready matrices, or modify source
NetCDF files. It creates a validated processing plan for the subsequent M18.7
processor.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAN = PROJECT_ROOT / "config" / "m18_7_processing_plan.json"
DEFAULT_FEATURE_REGISTRY = (
    PROJECT_ROOT / "reports" / "feature_engineering" / "feature_set_registry.csv"
)
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "interim" / "ceres_seasonal"
DEFAULT_AUDIT = PROJECT_ROOT / "reports" / "feature_engineering" / "m18_7_processing_preflight.json"
FEATURE_SET_IDS = ("FS-A", "FS-B", "FS-C", "FS-D", "FS-E", "FS-F")
CLOUD_AREA_VARIABLES = {
    "cldarea_high_1h",
    "cldarea_mid_high_1h",
    "cldarea_mid_low_1h",
    "cldarea_low_1h",
    "cldarea_total_1h",
}


def _read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _membership(value, variable: str, feature_set: str) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if pd.isna(value):
        raise ValueError(f"Null membership for {variable} in {feature_set}")
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Invalid membership {value!r} for {variable}/{feature_set}")


def load_registry(path: Path, expected_counts: dict) -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(path)
    required = {"variable", "family", "matching_cloud_area_variable", *FEATURE_SET_IDS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Feature registry missing columns: {sorted(missing)}")
    if frame.empty or frame["variable"].isna().any():
        raise ValueError("Feature registry is empty or contains null variable names")
    frame["variable"] = frame["variable"].astype(str).str.strip()
    if frame["variable"].eq("").any() or frame["variable"].duplicated().any():
        raise ValueError("Feature registry has blank or duplicate variable names")

    selected = {}
    for feature_set in FEATURE_SET_IDS:
        mask = [
            _membership(v, variable, feature_set)
            for v, variable in zip(frame[feature_set], frame["variable"])
        ]
        chosen = frame.loc[mask].copy()
        expected = int(expected_counts[feature_set])
        if len(chosen) != expected:
            raise ValueError(
                f"{feature_set} expected {expected} features, found {len(chosen)}"
            )
        selected[feature_set] = chosen

    known_areas = CLOUD_AREA_VARIABLES
    for row in frame.itertuples(index=False):
        area = getattr(row, "matching_cloud_area_variable")
        if pd.notna(area) and str(area).strip() and str(area).strip() not in known_areas:
            raise ValueError(f"Invalid area mapping for {row.variable}: {area}")
    return frame, selected


def _parse_file(path: Path) -> tuple[int, str]:
    match = re.fullmatch(r"CERES_(\d{4})_([a-z_]+)", path.stem)
    if not match:
        raise ValueError(f"Unexpected CERES filename: {path.name}")
    return int(match.group(1)), match.group(2)


def inspect_inputs(data_dir: Path, required_variables: set[str], plan: dict) -> dict:
    expected = plan["expected_data"]
    expected_seasons = set(expected["seasons"])
    files = sorted(Path(data_dir).glob("*/*.nc"))
    if not files:
        raise FileNotFoundError(f"No NetCDF files found under {data_dir}")

    seen = set()
    file_records = []
    reference_lat = None
    reference_lon = None
    all_times = []
    variable_presence = {name: 0 for name in required_variables}
    total_time = 0

    for path in files:
        year, season = _parse_file(path)
        key = (year, season)
        if key in seen:
            raise ValueError(f"Duplicate dataset: {key}")
        seen.add(key)
        if season not in expected_seasons:
            raise ValueError(f"Unexpected season {season} in {path.name}")
        if not 2010 <= year <= 2021:
            raise ValueError(f"Unexpected year {year} in {path.name}")

        with xr.open_dataset(path, decode_times=True) as ds:
            for dimension in ("time", "lat", "lon"):
                if dimension not in ds.sizes:
                    raise ValueError(f"{path.name} lacks required dimension {dimension}")
            time_count = int(ds.sizes["time"])
            lat = np.asarray(ds["lat"].values)
            lon = np.asarray(ds["lon"].values)
            times = pd.to_datetime(ds["time"].values)
            if time_count != int(expected["timestamps_per_dataset"]):
                raise ValueError(
                    f"{path.name}: expected {expected['timestamps_per_dataset']} times, got {time_count}"
                )
            if len(lat) != int(expected["latitude_count"]) or len(lon) != int(expected["longitude_count"]):
                raise ValueError(f"{path.name}: unexpected spatial grid {len(lat)}x{len(lon)}")
            if reference_lat is None:
                reference_lat, reference_lon = lat.copy(), lon.copy()
            elif not np.array_equal(reference_lat, lat) or not np.array_equal(reference_lon, lon):
                raise ValueError(f"Spatial coordinates differ in {path.name}")
            if len(times) and (not times.is_monotonic_increasing or times.has_duplicates):
                raise ValueError(f"Time coordinate is not strictly increasing in {path.name}")

            missing_vars = sorted(required_variables - set(ds.variables))
            if missing_vars:
                raise ValueError(
                    f"{path.name} is missing required variables: {missing_vars}"
                )
            for name in required_variables:
                variable_presence[name] += 1
            total_time += time_count
            all_times.extend(times.to_numpy())
            file_records.append({
                "year": year,
                "season": season,
                "file": path.name,
                "path": path.relative_to(PROJECT_ROOT).as_posix()
                    if path.is_relative_to(PROJECT_ROOT) else str(path),
                "time_count": time_count,
                "latitude_count": len(lat),
                "longitude_count": len(lon),
                "size_bytes": path.stat().st_size,
                "missing_required_variables": missing_vars,
            })

    expected_keys = {
        (year, season)
        for year in range(2010, 2022)
        for season in expected_seasons
    }
    missing_keys = sorted(expected_keys - seen)
    unexpected_keys = sorted(seen - expected_keys)
    if len(files) != int(expected["datasets"]) or missing_keys or unexpected_keys:
        raise ValueError(
            f"Dataset inventory mismatch: files={len(files)}, missing={missing_keys}, unexpected={unexpected_keys}"
        )

    all_times = pd.DatetimeIndex(all_times)
    duplicate_timestamps = int(all_times.duplicated().sum())
    if duplicate_timestamps:
        raise ValueError(f"Found {duplicate_timestamps} duplicate timestamps across seasonal files")

    samples = total_time * int(expected["latitude_count"]) * int(expected["longitude_count"])
    return {
        "file_count": len(files),
        "dataset_combinations": len(seen),
        "total_timestamps": total_time,
        "grid_cells": int(expected["latitude_count"]) * int(expected["longitude_count"]),
        "grid_shape": [int(expected["latitude_count"]), int(expected["longitude_count"])],
        "grid_cell_hour_observations": samples,
        "duplicate_timestamps_across_files": duplicate_timestamps,
        "variable_presence_file_counts": variable_presence,
        "files": file_records,
    }


def estimate_storage(samples: int, selected: dict, experiment_count: int) -> dict:
    estimates = {}
    total = 0
    for feature_set, frame in selected.items():
        feature_count = len(frame)
        # Feature tensor plus one uint8 missingness-code tensor.
        bytes_per_run = samples * feature_count * (4 + 1)
        estimates[feature_set] = {
            "feature_count": feature_count,
            "estimated_bytes_per_experiment": bytes_per_run,
            "estimated_gib_per_experiment": round(bytes_per_run / (1024 ** 3), 3),
        }
    # Stage A and B each contain 4 runs per feature set (one baseline + three variants).
    for feature_set, values in estimates.items():
        runs = 4
        total += values["estimated_bytes_per_experiment"] * runs
        values["stage_a_b_run_count"] = runs
    estimates["stage_a_b_total"] = {
        "experiment_count": int(experiment_count),
        "estimated_uncompressed_bytes": int(total),
        "estimated_uncompressed_gib": round(total / (1024 ** 3), 2),
        "note": "Conservative tensor-size estimate before NetCDF compression; indicator features and metadata may increase output size."
    }
    return estimates


def build_preflight(plan_path: Path, registry_path: Path, data_dir: Path) -> dict:
    plan = _read_json(plan_path)
    frame, selected = load_registry(registry_path, plan["expected_data"]["feature_sets"])
    required_variables = set().union(*(set(x["variable"]) for x in selected.values()))
    inputs = inspect_inputs(data_dir, required_variables, plan)
    experiment_count = 24
    storage = estimate_storage(
        inputs["grid_cell_hour_observations"], selected, experiment_count
    )
    disk = shutil.disk_usage(PROJECT_ROOT)
    return {
        "milestone": "M18.7",
        "status": "PASS",
        "partition_policy": plan["processing_partitions"],
        "input_validation": inputs,
        "feature_sets": {
            key: frame["variable"].astype(str).tolist()
            for key, frame in selected.items()
        },
        "storage_estimate": storage,
        "disk_space": {
            "free_bytes": disk.free,
            "free_gib": round(disk.free / (1024 ** 3), 2),
            "estimated_uncompressed_gib": storage["stage_a_b_total"]["estimated_uncompressed_gib"],
            "sufficient_for_uncompressed_estimate": disk.free >= storage["stage_a_b_total"]["estimated_uncompressed_bytes"] * 1.1,
        },
        "raw_data_modified": False,
        "processing_executed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--registry", type=Path, default=DEFAULT_FEATURE_REGISTRY)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()

    report = build_preflight(args.plan, args.registry, args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(args.output)

    print("\n========== M18.7 PROCESSING PREFLIGHT ==========")
    print(f"Input files: {report['input_validation']['file_count']}")
    print(f"Grid-cell-hour observations: {report['input_validation']['grid_cell_hour_observations']:,}")
    print(f"Feature sets: {len(report['feature_sets'])}")
    print(f"Experiments planned: 24")
    print(f"Estimated uncompressed output: {report['storage_estimate']['stage_a_b_total']['estimated_uncompressed_gib']} GiB")
    print(f"Available disk: {report['disk_space']['free_gib']} GiB")
    print(f"Disk sufficient for conservative estimate: {report['disk_space']['sufficient_for_uncompressed_estimate']}")
    print("Processing executed: False")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
