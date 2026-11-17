"""M18.7 out-of-core CERES feature processing.

The processor executes one registered M18.6 experiment at a time. It creates
one compressed NetCDF4 model-ready file per experiment, with scaled continuous
features, unscaled binary indicators, and a separate uint8 missingness-code
array for each retained source feature.

The initial M18.7 release processes the primary descriptive partition only:
2010-2021 inclusive. Temporal-transfer and exclude-2017 sensitivities are
reserved for M18.8 so that the 24-run storage estimate is not multiplied by
additional partition copies.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FEATURE_MODULE_DIR = PROJECT_ROOT / "src" / "06_feature_engineering"
if str(FEATURE_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(FEATURE_MODULE_DIR))

from missingness_classifier import (  # noqa: E402
    MissingnessCode,
    classify_missingness,
)
from missingness_treatments import (  # noqa: E402
    assess_ca_b_feature,
    fit_cloud_area_treatment,
    fit_property_treatment,
    transform_cloud_area_treatment,
    transform_property_treatment,
)
from feature_scaling import (  # noqa: E402
    FeatureScalingModel,
    transform_feature_scaler,
)
from experiment_orchestrator import update_run_status  # noqa: E402

DEFAULT_PLAN = PROJECT_ROOT / "config" / "m18_7_processing_plan.json"
DEFAULT_EXPERIMENT_CONFIG = (
    PROJECT_ROOT / "config" / "m18_experiment_orchestration.json"
)
DEFAULT_FEATURE_REGISTRY = (
    PROJECT_ROOT / "reports" / "feature_engineering" / "feature_set_registry.csv"
)
DEFAULT_RUN_REGISTRY = (
    PROJECT_ROOT / "reports" / "feature_engineering" / "m18_experiment_registry.csv"
)
DEFAULT_PREFLIGHT_REPORT = (
    PROJECT_ROOT / "reports" / "feature_engineering" / "m18_7_processing_preflight.json"
)
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "interim" / "ceres_seasonal"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "m18_model_ready"
DEFAULT_WORK_DIR = PROJECT_ROOT / "data" / "processed" / "m18_work"
DEFAULT_PROCESSING_MANIFEST_DIR = (
    PROJECT_ROOT / "reports" / "feature_engineering" / "m18_7_processing_manifests"
)

FEATURE_SET_IDS = ("FS-A", "FS-B", "FS-C", "FS-D", "FS-E", "FS-F")
CLOUD_AREA_VARIABLES = {
    "cldarea_high_1h",
    "cldarea_mid_high_1h",
    "cldarea_mid_low_1h",
    "cldarea_low_1h",
    "cldarea_total_1h",
}
SEASON_CODES = {
    "pre_monsoon": 1,
    "established_monsoon": 2,
    "post_monsoon": 3,
}
CLASSIFICATION_LABELS = {
    int(MissingnessCode.OBSERVED): "observed",
    int(MissingnessCode.STRUCTURAL_ABSENCE): "structural_absence",
    int(MissingnessCode.RESIDUAL_MISSING): "residual_missing",
    int(MissingnessCode.UNKNOWN_CLOUD_AVAILABILITY): "unknown_cloud_availability",
    int(MissingnessCode.CLOUD_AREA_MISSING): "cloud_area_missing",
}
VALID_RUN_STATUSES = {"PENDING", "RUNNING", "FAILED", "COMPLETED", "SKIPPED"}
DEFAULT_TIME_CHUNK = 24
FIT_CHUNK_SAMPLES = 250_000
GIB = 1024 ** 3


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_json(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, allow_nan=False, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_dataset_name(path: Path) -> tuple[int, str]:
    match = re.fullmatch(r"CERES_(\d{4})_([a-z_]+)", path.stem)
    if not match:
        raise ValueError(f"Unexpected CERES filename: {path.name}")
    year, season = int(match.group(1)), match.group(2)
    if season not in SEASON_CODES:
        raise ValueError(f"Unexpected season in filename: {path.name}")
    return year, season


def _membership(value: Any, variable: str, feature_set: str) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if pd.isna(value):
        raise ValueError(f"Null feature membership for {variable}/{feature_set}")
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Invalid feature membership {value!r} for {variable}/{feature_set}")


def load_feature_registry(path: Path, expected_counts: dict) -> tuple[pd.DataFrame, dict]:
    frame = pd.read_csv(path)
    required = {
        "variable", "family", "matching_cloud_area_variable",
        *FEATURE_SET_IDS,
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Feature registry missing columns: {sorted(missing)}")
    if frame.empty or frame["variable"].isna().any():
        raise ValueError("Feature registry is empty or has null variable names")
    frame["variable"] = frame["variable"].astype(str).str.strip()
    if frame["variable"].eq("").any() or frame["variable"].duplicated().any():
        raise ValueError("Feature registry has blank or duplicate variable names")

    selected = {}
    for feature_set in FEATURE_SET_IDS:
        mask = [
            _membership(value, variable, feature_set)
            for value, variable in zip(frame[feature_set], frame["variable"])
        ]
        chosen = frame.loc[mask].copy().reset_index(drop=True)
        expected = int(expected_counts[feature_set])
        if len(chosen) != expected:
            raise ValueError(
                f"{feature_set}: expected {expected} features, found {len(chosen)}"
            )
        selected[feature_set] = chosen

    for row in frame.itertuples(index=False):
        area = row.matching_cloud_area_variable
        if pd.notna(area) and str(area).strip() and str(area).strip() not in CLOUD_AREA_VARIABLES:
            raise ValueError(f"Invalid cloud-area mapping for {row.variable}: {area}")
        if row.variable in CLOUD_AREA_VARIABLES and pd.notna(area) and str(area).strip():
            raise ValueError(f"Cloud-area variable must not map to itself: {row.variable}")
    return frame, selected


def load_run_table(path: Path) -> pd.DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(
            f"M18.6 experiment registry not found: {path}. Run the M18.6 orchestrator first."
        )
    frame = pd.read_csv(path, dtype=str).fillna("")
    required = {
        "run_id", "stage", "feature_set", "property_treatment",
        "cloud_area_treatment", "scaler", "weighting", "status",
        "feature_registry_sha256", "config_sha256",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"M18.6 run registry missing columns: {sorted(missing)}")
    if frame["run_id"].duplicated().any():
        raise ValueError("M18.6 run registry contains duplicate run IDs")
    bad = sorted(set(frame["status"]) - VALID_RUN_STATUSES)
    if bad:
        raise ValueError(f"M18.6 run registry contains invalid statuses: {bad}")
    return frame


def _timestamp_interval_diagnostics(times: pd.DatetimeIndex) -> dict:
    """Describe observed timestamp spacing without assuming complete hourly coverage."""
    if len(times) < 2:
        return {
            "interval_count": 0,
            "min_interval_seconds": None,
            "median_interval_seconds": None,
            "max_interval_seconds": None,
            "non_hourly_interval_count": 0,
        }

    intervals_ns = np.diff(times.asi8)
    if np.any(intervals_ns <= 0):
        raise ValueError("Timestamps must be strictly increasing and unique")

    intervals_seconds = intervals_ns.astype(np.float64) / 1_000_000_000.0
    return {
        "interval_count": int(intervals_seconds.size),
        "min_interval_seconds": float(intervals_seconds.min()),
        "median_interval_seconds": float(np.median(intervals_seconds)),
        "max_interval_seconds": float(intervals_seconds.max()),
        "non_hourly_interval_count": int(
            np.count_nonzero(intervals_ns != 3_600_000_000_000)
        ),
    }


def discover_input_files(data_dir: Path, expected: dict) -> tuple[list[dict], np.ndarray, np.ndarray]:
    files = sorted(Path(data_dir).glob("*/*.nc"))
    if len(files) != int(expected["datasets"]):
        raise ValueError(
            f"Expected {expected['datasets']} CERES files, found {len(files)}"
        )

    records = []
    reference_lat = None
    reference_lon = None
    all_times = []
    seen = set()

    for path in files:
        year, season = _parse_dataset_name(path)
        if not int(expected["start_year"]) <= year <= int(expected["end_year"]):
            raise ValueError(f"Unexpected year in {path.name}")
        key = (year, season)
        if key in seen:
            raise ValueError(f"Duplicate year/season dataset: {key}")
        seen.add(key)

        with xr.open_dataset(path, decode_times=True) as ds:
            if not {"time", "lat", "lon"}.issubset(ds.sizes):
                raise ValueError(f"{path.name} must have time/lat/lon dimensions")
            times = pd.DatetimeIndex(pd.to_datetime(ds["time"].values))
            lat = np.asarray(ds["lat"].values, dtype=np.float32)
            lon = np.asarray(ds["lon"].values, dtype=np.float32)
            if len(times) != int(expected["timestamps_per_dataset"]):
                raise ValueError(
                    f"{path.name}: expected {expected['timestamps_per_dataset']} times, got {len(times)}"
                )
            if not times.is_monotonic_increasing or times.has_duplicates:
                raise ValueError(f"Invalid time ordering in {path.name}")
            # Preserve source timestamps. Missing hourly slots are not
            # synthesized; irregular intervals are recorded as diagnostics.
            timestamp_diagnostics = _timestamp_interval_diagnostics(times)
            if len(lat) != int(expected["latitude_count"]) or len(lon) != int(expected["longitude_count"]):
                raise ValueError(f"Unexpected grid in {path.name}: {len(lat)}x{len(lon)}")
            if reference_lat is None:
                reference_lat, reference_lon = lat.copy(), lon.copy()
            elif not np.array_equal(reference_lat, lat) or not np.array_equal(reference_lon, lon):
                raise ValueError(f"Spatial grid mismatch in {path.name}")
            records.append({
                "path": path,
                "year": year,
                "season": season,
                "time_count": len(times),
                "first_time": times[0],
                "times": times,
                "timestamp_diagnostics": timestamp_diagnostics,
                "size_bytes": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
            })
            all_times.extend(times.to_numpy())

    expected_seasons = set(expected["seasons"])
    expected_keys = {
        (year, season)
        for year in range(int(expected["start_year"]), int(expected["end_year"]) + 1)
        for season in expected_seasons
    }
    missing = sorted(expected_keys - seen)
    unexpected = sorted(seen - expected_keys)
    if missing or unexpected:
        raise ValueError(f"Dataset combination mismatch; missing={missing}, unexpected={unexpected}")

    all_time_index = pd.DatetimeIndex(all_times)
    if all_time_index.has_duplicates:
        raise ValueError("Duplicate timestamps found across CERES seasonal files")

    records.sort(key=lambda item: item["first_time"])
    return records, reference_lat, reference_lon


def calculate_storage_estimate(
    samples: int,
    selected_features: dict,
    registry_frame: pd.DataFrame,
) -> dict:
    """Estimate uncompressed feature, code, indicator, and peak work storage."""
    total_feature_code_bytes = 0
    total_indicator_bytes = 0
    per_run = []
    max_raw_work_bytes = 0

    for feature_set, frame in selected_features.items():
        feature_count = len(frame)
        property_count = int((frame["family"].astype(str) != "cloud_area").sum())
        raw_work = samples * feature_count * np.dtype("float32").itemsize
        max_raw_work_bytes = max(max_raw_work_bytes, raw_work)
        specs = [
            ("A", "SA-A", "CA-A", feature_count, property_count + 5),
            ("B-MD-B", "MD-B", "CA-A", feature_count, 2 * property_count + 5),
            ("B-SA-B", "SA-B", "CA-A", feature_count, 2 * property_count + 5),
            ("B-CA-B", "SA-A", "CA-B", feature_count - 1, property_count),
        ]
        for label, prop_treatment, area_treatment, output_features, indicator_count in specs:
            feature_bytes = samples * output_features * 4
            code_bytes = samples * feature_count
            base = feature_bytes + code_bytes
            indicators = samples * indicator_count
            total_feature_code_bytes += base
            total_indicator_bytes += indicators
            per_run.append({
                "feature_set": feature_set,
                "variant": label,
                "output_feature_count": output_features,
                "indicator_count": indicator_count,
                "estimated_uncompressed_bytes": base + indicators,
            })

    output_bytes = total_feature_code_bytes + total_indicator_bytes
    return {
        "experiment_count": len(per_run),
        "feature_and_code_bytes": int(total_feature_code_bytes),
        "indicator_bytes": int(total_indicator_bytes),
        "total_uncompressed_output_bytes": int(output_bytes),
        "total_uncompressed_output_gib": round(output_bytes / GIB, 2),
        "peak_raw_work_bytes": int(max_raw_work_bytes),
        "peak_raw_work_gib": round(max_raw_work_bytes / GIB, 2),
        "recommended_free_space_bytes": int(output_bytes * 1.10 + max_raw_work_bytes + 5 * GIB),
        "recommended_free_space_gib": round(
            (output_bytes * 1.10 + max_raw_work_bytes + 5 * GIB) / GIB, 2
        ),
        "per_run": per_run,
        "note": (
            "Uncompressed estimate includes scaled features, uint8 missingness codes, "
            "and treatment indicators. NetCDF compression may reduce actual output size. "
            "Temporal-transfer and exclude-2017 sensitivity partitions are not included in M18.7."
        ),
    }


def _model_columns(feature_rows: pd.DataFrame, experiment: dict) -> list[dict]:
    columns = []
    prop_strategy = experiment["property_treatment"]
    area_strategy = experiment["cloud_area_treatment"]

    for row in feature_rows.itertuples(index=False):
        variable = str(row.variable)
        family = str(row.family)
        if family == "cloud_area":
            columns.append({
                "name": f"feature__{variable}",
                "kind": "feature",
                "source_variable": variable,
                "indicator_type": None,
                "family": family,
                "scale": True,
            })
            if area_strategy == "CA-A":
                columns.append({
                    "name": f"indicator__{variable}__availability_missing",
                    "kind": "indicator",
                    "source_variable": variable,
                    "indicator_type": "availability_missing",
                    "family": None,
                    "scale": False,
                })
        else:
            columns.append({
                "name": f"feature__{variable}",
                "kind": "feature",
                "source_variable": variable,
                "indicator_type": None,
                "family": family,
                "scale": True,
            })
            columns.append({
                "name": f"indicator__{variable}__unknown_cloud_availability",
                "kind": "indicator",
                "source_variable": variable,
                "indicator_type": "unknown_cloud_availability",
                "family": None,
                "scale": False,
            })
            if prop_strategy == "MD-B":
                indicator_type = "residual_missingness"
            elif prop_strategy == "SA-B":
                indicator_type = "structural_absence"
            else:
                indicator_type = None
            if indicator_type:
                columns.append({
                    "name": f"indicator__{variable}__{indicator_type}",
                    "kind": "indicator",
                    "source_variable": variable,
                    "indicator_type": indicator_type,
                    "family": None,
                    "scale": False,
                })
    names = [column["name"] for column in columns]
    if len(names) != len(set(names)):
        raise ValueError("Generated duplicate model matrix column names")
    return columns


def _fit_out_of_core_scaler(
    feature_rows: pd.DataFrame,
    experiment: dict,
    treatment_models: dict,
    raw_maps: dict,
    area_map_by_feature: dict,
    n_samples: int,
    model_columns: list[dict],
) -> FeatureScalingModel:
    scaler_type = str(experiment["scaler"]).lower()
    weighting = str(experiment["weighting"]).lower()
    if scaler_type not in {"robust", "standard"}:
        raise ValueError(f"Unsupported scaler: {scaler_type}")
    if weighting not in {"equal", "family_balanced"}:
        raise ValueError(f"Unsupported weighting: {weighting}")

    names = tuple(column["name"] for column in model_columns)
    families = tuple(column["family"] for column in model_columns)
    scale_mask = np.asarray([column["scale"] for column in model_columns], dtype=bool)
    center = np.zeros(len(model_columns), dtype=np.float64)
    scale = np.ones(len(model_columns), dtype=np.float64)

    model_column_index = {
        (column["source_variable"], column["indicator_type"]): index
        for index, column in enumerate(model_columns)
    }

    for row in feature_rows.itertuples(index=False):
        variable = str(row.variable)
        family = str(row.family)
        column_index = model_column_index[(variable, None)]
        raw = raw_maps[variable]
        imputed = np.empty(n_samples, dtype=np.float32)

        if family == "cloud_area":
            if experiment["cloud_area_treatment"] == "CA-A":
                model = treatment_models[variable]
                for start in range(0, n_samples, FIT_CHUNK_SAMPLES):
                    end = min(start + FIT_CHUNK_SAMPLES, n_samples)
                    result = transform_cloud_area_treatment(raw[start:end], model)
                    imputed[start:end] = result["feature"]
            else:
                imputed[:] = raw[:]
                if not np.isfinite(imputed).all():
                    raise ValueError(
                        f"CA-B retained {variable} with missing values. "
                        "CA-B is screening-only and will not silently impute it."
                    )
        else:
            area_variable = area_map_by_feature[variable]
            area_raw = raw_maps[area_variable]
            model = treatment_models[variable]
            for start in range(0, n_samples, FIT_CHUNK_SAMPLES):
                end = min(start + FIT_CHUNK_SAMPLES, n_samples)
                values_chunk = raw[start:end]
                area_chunk = area_raw[start:end]
                codes = classify_missingness(
                    values_chunk,
                    variable,
                    area_values=area_chunk,
                    area_variable=area_variable,
                )
                result = transform_property_treatment(
                    values_chunk,
                    area_chunk,
                    codes,
                    model,
                )
                imputed[start:end] = result["feature"]

        if not np.isfinite(imputed).all():
            raise ValueError(f"Imputation left non-finite values in {variable}")

        if scaler_type == "robust":
            q25, median, q75 = np.percentile(imputed, [25.0, 50.0, 75.0])
            center[column_index] = float(median)
            fitted_scale = float(q75 - q25)
        else:
            center[column_index] = float(np.mean(imputed, dtype=np.float64))
            fitted_scale = float(np.std(imputed, dtype=np.float64, ddof=0))
        scale[column_index] = fitted_scale if fitted_scale > 1e-12 else 1.0
        del imputed

    weights = np.ones(len(model_columns), dtype=np.float64)
    if weighting == "family_balanced":
        family_counts: dict[str, int] = {}
        for index, is_scaled in enumerate(scale_mask):
            if is_scaled:
                family = families[index]
                if family is None:
                    raise ValueError(
                        f"Family-balanced scaling needs a family for {names[index]}"
                    )
                family_counts[str(family)] = family_counts.get(str(family), 0) + 1
        for index, is_scaled in enumerate(scale_mask):
            if is_scaled:
                weights[index] = 1.0 / math.sqrt(family_counts[str(families[index])])

    return FeatureScalingModel(
        scaler_type=scaler_type,
        weighting=weighting,
        feature_names=names,
        feature_families=families,
        scale_mask=tuple(bool(value) for value in scale_mask),
        center=center,
        scale=scale,
        feature_weights=weights,
        n_training_samples=int(n_samples),
        quantile_range=(25.0, 75.0),
    )


def _fit_treatment_models(
    feature_rows: pd.DataFrame,
    experiment: dict,
    raw_maps: dict,
    area_map_by_feature: dict,
) -> tuple[dict, dict, dict]:
    models = {}
    missingness_counts = {}
    screening = {}
    prop_strategy = experiment["property_treatment"]
    area_strategy = experiment["cloud_area_treatment"]

    for row in feature_rows.itertuples(index=False):
        variable = str(row.variable)
        family = str(row.family)
        values = raw_maps[variable]

        if family == "cloud_area":
            finite = np.isfinite(values)
            missing_pct = 100.0 * float((~finite).sum()) / values.size
            negative_count = int(np.count_nonzero(finite & (values < 0)))
            if negative_count:
                raise ValueError(f"Negative cloud-area values in {variable}")
            if area_strategy == "CA-A":
                model = fit_cloud_area_treatment(values, strategy="CA-A")
                models[variable] = model
                codes = np.where(
                    finite,
                    int(MissingnessCode.OBSERVED),
                    int(MissingnessCode.CLOUD_AREA_MISSING),
                ).astype(np.uint8)
                missingness_counts[variable] = _count_codes(codes)
                screening[variable] = {
                    "missing_pct": missing_pct,
                    "decision": "IMPUTE_CA_A",
                    "training_median": model.median,
                }
            elif area_strategy == "CA-B":
                decision = assess_ca_b_feature(missing_pct)
                exclude = decision["decision"] == "EXCLUDE_PRIMARY"
                if not exclude and not finite.all():
                    raise ValueError(
                        f"CA-B retained {variable} ({decision['band']}) but it has "
                        "missing values. CA-B is screening-only; no silent imputation."
                    )
                screening[variable] = {
                    "missing_pct": missing_pct,
                    **decision,
                    "excluded_from_model_matrix": bool(exclude),
                }
                codes = np.where(
                    finite,
                    int(MissingnessCode.OBSERVED),
                    int(MissingnessCode.CLOUD_AREA_MISSING),
                ).astype(np.uint8)
                missingness_counts[variable] = _count_codes(codes)
            else:
                raise ValueError(f"Unsupported cloud-area treatment: {area_strategy}")
        else:
            area_variable = area_map_by_feature.get(variable)
            if not area_variable or area_variable not in raw_maps:
                raise ValueError(
                    f"Missing matching cloud-area data for property {variable}: {area_variable}"
                )
            area_values = raw_maps[area_variable]
            codes = classify_missingness(
                values,
                variable,
                area_values=area_values,
                area_variable=area_variable,
            )
            model = fit_property_treatment(
                values,
                area_values,
                codes,
                strategy=prop_strategy,
            )
            models[variable] = model
            missingness_counts[variable] = _count_codes(codes)
            screening[variable] = {
                "residual_missing_pct": (
                    100.0 * missingness_counts[variable]["residual_missing"] / values.size
                ),
                "treatment": prop_strategy,
                "conditional_training_median": model.conditional_median,
                "overall_training_median": model.overall_median,
            }
            del codes

    return models, missingness_counts, screening


def _count_codes(codes: np.ndarray) -> dict:
    counts = np.bincount(np.asarray(codes, dtype=np.uint8), minlength=5)
    return {
        CLASSIFICATION_LABELS[index]: int(counts[index])
        for index in range(5)
    }


def _create_raw_memmaps(
    records: list[dict],
    feature_rows: pd.DataFrame,
    work_dir: Path,
    lat_count: int,
    lon_count: int,
    time_chunk: int,
) -> tuple[dict, int, list[np.ndarray], list[int], list[int]]:
    variables = feature_rows["variable"].astype(str).tolist()
    unique_variables = list(dict.fromkeys(variables))
    total_time = sum(record["time_count"] for record in records)
    total_samples = total_time * lat_count * lon_count
    work_dir.mkdir(parents=True, exist_ok=True)

    raw_maps = {}
    for variable in unique_variables:
        raw_maps[variable] = np.memmap(
            work_dir / f"{variable}.f32",
            mode="w+",
            dtype=np.float32,
            shape=(total_samples,),
        )

    all_times = []
    years = []
    seasons = []
    time_offset = 0
    sample_offset = 0

    for record in records:
        path = record["path"]
        with xr.open_dataset(path, decode_times=True) as ds:
            for variable in unique_variables:
                if variable not in ds.variables:
                    raise ValueError(f"{path.name} is missing required variable {variable}")
                if tuple(ds[variable].dims) != ("time", "lat", "lon"):
                    raise ValueError(
                        f"{path.name}:{variable} has dimensions {ds[variable].dims}; "
                        "expected ('time', 'lat', 'lon')"
                    )
            times = pd.DatetimeIndex(pd.to_datetime(ds["time"].values))
            all_times.extend(times.to_numpy())
            years.extend([record["year"]] * len(times))
            seasons.extend([SEASON_CODES[record["season"]]] * len(times))

            for t_start in range(0, len(times), time_chunk):
                t_end = min(t_start + time_chunk, len(times))
                chunk_times = t_end - t_start
                sample_count = chunk_times * lat_count * lon_count
                target = slice(sample_offset, sample_offset + sample_count)
                for variable in unique_variables:
                    values = np.asarray(
                        ds[variable].isel(time=slice(t_start, t_end)).values,
                        dtype=np.float32,
                    )
                    if values.shape != (chunk_times, lat_count, lon_count):
                        raise ValueError(
                            f"Unexpected chunk shape for {path.name}:{variable}: {values.shape}"
                        )
                    raw_maps[variable][target] = values.reshape(-1)
                sample_offset += sample_count
                time_offset += chunk_times

    for mapped in raw_maps.values():
        mapped.flush()

    time_index = pd.DatetimeIndex(all_times)
    if time_index.has_duplicates:
        raise ValueError("Duplicate timestamps detected while building raw feature maps")
    if not time_index.is_monotonic_increasing:
        raise ValueError("Input files are not in chronological order")
    return (
        raw_maps,
        total_samples,
        [time_index.to_numpy()],
        years,
        seasons,
    )


def _transform_feature_chunk(
    feature_rows: pd.DataFrame,
    experiment: dict,
    raw_maps: dict,
    treatment_models: dict,
    area_map_by_feature: dict,
    start: int,
    end: int,
    excluded_features: set[str] | None = None,
) -> tuple[dict, dict]:
    columns = {}
    codes_by_feature = {}
    excluded_features = excluded_features or set()
    prop_strategy = experiment["property_treatment"]
    area_strategy = experiment["cloud_area_treatment"]

    for row in feature_rows.itertuples(index=False):
        variable = str(row.variable)
        family = str(row.family)
        values = np.asarray(raw_maps[variable][start:end], dtype=np.float32)

        if family == "cloud_area":
            if area_strategy == "CA-A":
                result = transform_cloud_area_treatment(
                    values,
                    treatment_models[variable],
                )
                columns[f"feature__{variable}"] = result["feature"]
                columns[f"indicator__{variable}__availability_missing"] = result[
                    "availability_missing"
                ]
                codes = np.where(
                    np.isfinite(values),
                    int(MissingnessCode.OBSERVED),
                    int(MissingnessCode.CLOUD_AREA_MISSING),
                ).astype(np.uint8)
            else:
                finite = np.isfinite(values)
                codes = np.where(
                    finite,
                    int(MissingnessCode.OBSERVED),
                    int(MissingnessCode.CLOUD_AREA_MISSING),
                ).astype(np.uint8)
                if variable in excluded_features:
                    codes_by_feature[variable] = codes
                    continue
                if not finite.all():
                    raise ValueError(f"CA-B retained cloud-area feature {variable} with missing values")
                columns[f"feature__{variable}"] = values.astype(np.float32, copy=False)
        else:
            area_variable = area_map_by_feature[variable]
            area_values = np.asarray(raw_maps[area_variable][start:end], dtype=np.float32)
            codes = classify_missingness(
                values,
                variable,
                area_values=area_values,
                area_variable=area_variable,
            )
            result = transform_property_treatment(
                values,
                area_values,
                codes,
                treatment_models[variable],
            )
            columns[f"feature__{variable}"] = result["feature"]
            columns[f"indicator__{variable}__unknown_cloud_availability"] = result[
                "unknown_cloud_availability"
            ]
            if "residual_missingness" in result:
                columns[f"indicator__{variable}__residual_missingness"] = result[
                    "residual_missingness"
                ]
            if "structural_absence" in result:
                columns[f"indicator__{variable}__structural_absence"] = result[
                    "structural_absence"
                ]
        codes_by_feature[variable] = codes

    return columns, codes_by_feature


def _create_netcdf_output(
    output_tmp: Path,
    output_features: list[str],
    model_columns: list[dict],
    missingness_variables: list[str],
    lat: np.ndarray,
    lon: np.ndarray,
    times: np.ndarray,
    years: list[int],
    seasons: list[int],
    experiment: dict,
    run_id: str,
    input_inventory: list[dict],
    scaling_model: FeatureScalingModel,
    time_chunk: int,
):
    try:
        from netCDF4 import Dataset
    except ImportError as exc:
        raise RuntimeError(
            "netCDF4 is required to write compressed NetCDF4 outputs. "
            "Install it with: python -m pip install netCDF4"
        ) from exc

    output_tmp.parent.mkdir(parents=True, exist_ok=True)
    if output_tmp.exists():
        output_tmp.unlink()

    with Dataset(str(output_tmp), "w", format="NETCDF4") as nc:
        nc.createDimension("time", len(times))
        nc.createDimension("lat", len(lat))
        nc.createDimension("lon", len(lon))

        lat_var = nc.createVariable("lat", "f4", ("lat",))
        lon_var = nc.createVariable("lon", "f4", ("lon",))
        lat_var[:] = lat
        lon_var[:] = lon
        lat_var.units = "degrees_north"
        lon_var.units = "degrees_east"

        time_var = nc.createVariable("time", "i8", ("time",))
        epoch_seconds = np.asarray(times).astype("datetime64[s]").astype(np.int64)
        time_var[:] = epoch_seconds
        time_var.units = "seconds since 1970-01-01 00:00:00"
        time_var.calendar = "proleptic_gregorian"
        time_var.standard_name = "time"

        year_var = nc.createVariable("year", "i2", ("time",))
        season_var = nc.createVariable("season_code", "i1", ("time",))
        year_var[:] = np.asarray(years, dtype=np.int16)
        season_var[:] = np.asarray(seasons, dtype=np.int8)
        season_var.flag_values = np.asarray([1, 2, 3], dtype=np.int8)
        season_var.flag_meanings = "pre_monsoon established_monsoon post_monsoon"

        chunks = (min(time_chunk, len(times)), len(lat), len(lon))
        feature_vars = {}
        indicator_vars = {}
        code_vars = {}

        for column in model_columns:
            name = column["name"]
            if column["kind"] == "feature":
                var = nc.createVariable(
                    name, "f4", ("time", "lat", "lon"),
                    zlib=True, complevel=4, shuffle=True, chunksizes=chunks,
                )
                var.long_name = f"Scaled cloud feature: {column['source_variable']}"
                var.source_variable = column["source_variable"]
                var.feature_family = str(column["family"])
                var.units = "scaled_dimensionless"
                feature_vars[name] = var
            else:
                var = nc.createVariable(
                    name, "u1", ("time", "lat", "lon"),
                    zlib=True, complevel=4, shuffle=True, chunksizes=chunks,
                )
                var.long_name = f"Binary indicator: {column['indicator_type']} for {column['source_variable']}"
                var.source_variable = column["source_variable"]
                var.flag_values = np.asarray([0, 1], dtype=np.uint8)
                var.flag_meanings = "false true"
                indicator_vars[name] = var

        for variable in missingness_variables:
            name = f"missingness_code__{variable}"
            var = nc.createVariable(
                name, "u1", ("time", "lat", "lon"),
                zlib=True, complevel=4, shuffle=True, chunksizes=chunks,
            )
            var.long_name = f"Missingness classification for {variable}"
            var.flag_values = np.asarray([0, 1, 2, 3, 4], dtype=np.uint8)
            var.flag_meanings = (
                "observed structural_absence residual_missing "
                "unknown_cloud_availability cloud_area_missing"
            )
            code_vars[variable] = var

        nc.title = "CERES M18.7 model-ready cloud feature dataset"
        nc.milestone = "M18.7"
        nc.run_id = run_id
        nc.feature_set = experiment["feature_set"]
        nc.stage = experiment["stage"]
        nc.property_treatment = experiment["property_treatment"]
        nc.cloud_area_treatment = experiment["cloud_area_treatment"]
        nc.scaler = experiment["scaler"]
        nc.weighting = experiment["weighting"]
        nc.processing_partition = "primary_descriptive_fit"
        nc.fit_years = "2010-2021"
        nc.includes_2017 = "true"
        nc.fit_scope_note = (
            "Full 2010-2021 descriptive fit; not a held-out temporal validation result."
        )
        nc.raw_source_modified = "false"
        nc.source_files = json.dumps([
            {
                "file": item["path"].name,
                "size_bytes": item["size_bytes"],
                "mtime_ns": item["mtime_ns"],
                "timestamp_diagnostics": item.get("timestamp_diagnostics", {}),
            }
            for item in input_inventory
        ])
        nc.feature_order = json.dumps(output_features)
        nc.model_matrix_order = json.dumps([column["name"] for column in model_columns])
        nc.missingness_code_labels = json.dumps(CLASSIFICATION_LABELS)
        nc.scaler_center = json.dumps(scaling_model.center.tolist())
        nc.scaler_scale = json.dumps(scaling_model.scale.tolist())
        nc.feature_weights = json.dumps(scaling_model.feature_weights.tolist())
        nc.history = f"Created { _utc_now() } by process_m18_7_datasets.py"

        return feature_vars, indicator_vars, code_vars


def _validate_written_output(
    output_path: Path,
    total_time: int,
    lat_count: int,
    lon_count: int,
    model_columns: list[dict],
    output_feature_names: list[str],
    run_id: str,
    time_chunk: int,
) -> dict:
    """Validate NetCDF structure and sample boundary chunks after writing.

    Every chunk is also validated in-memory during the write pass. This second
    check verifies the published file structure and catches truncated or
    malformed output without rereading the complete multi-gigabyte file.
    """
    try:
        from netCDF4 import Dataset
    except ImportError as exc:
        raise RuntimeError("netCDF4 is required for output validation") from exc

    expected_feature_vars = {
        column["name"] for column in model_columns if column["kind"] == "feature"
    }
    expected_indicator_vars = {
        column["name"] for column in model_columns if column["kind"] == "indicator"
    }
    expected_code_vars = {f"missingness_code__{name}" for name in output_feature_names}

    with Dataset(str(output_path), "r") as nc:
        if nc.dimensions["time"].size != total_time:
            raise ValueError("Output time dimension has an unexpected length")
        if nc.dimensions["lat"].size != lat_count or nc.dimensions["lon"].size != lon_count:
            raise ValueError("Output spatial dimensions have unexpected lengths")
        expected_names = expected_feature_vars | expected_indicator_vars | expected_code_vars
        missing = expected_names - set(nc.variables)
        if missing:
            raise ValueError(f"Output is missing variables: {sorted(missing)}")
        if nc.getncattr("run_id") != run_id:
            raise ValueError("Output run_id metadata does not match requested experiment")
        time_values = np.asarray(nc.variables["time"][:], dtype=np.int64)
        if time_values.size != total_time or (time_values.size > 1 and np.any(np.diff(time_values) <= 0)):
            raise ValueError("Output time coordinate is not strictly increasing")

        sample_slices = [slice(0, min(time_chunk, total_time))]
        if total_time > time_chunk:
            sample_slices.append(slice(max(0, total_time - time_chunk), total_time))

        for variable_name in expected_feature_vars:
            variable = nc.variables[variable_name]
            for time_slice in sample_slices:
                values = np.asarray(variable[time_slice, :, :])
                if not np.isfinite(values).all():
                    raise ValueError(f"Non-finite values found in output feature {variable_name}")
        for variable_name in expected_indicator_vars:
            variable = nc.variables[variable_name]
            for time_slice in sample_slices:
                values = np.asarray(variable[time_slice, :, :])
                if not np.isin(values, [0, 1]).all():
                    raise ValueError(f"Non-binary values found in indicator {variable_name}")
        for variable_name in expected_code_vars:
            variable = nc.variables[variable_name]
            for time_slice in sample_slices:
                values = np.asarray(variable[time_slice, :, :])
                if not np.isin(values, [0, 1, 2, 3, 4]).all():
                    raise ValueError(f"Invalid missingness codes found in {variable_name}")

    return {
        "status": "PASS",
        "time_count": total_time,
        "grid_shape": [lat_count, lon_count],
        "feature_variable_count": len(expected_feature_vars),
        "indicator_variable_count": len(expected_indicator_vars),
        "missingness_code_variable_count": len(expected_code_vars),
        "all_written_chunks_checked_in_memory": True,
        "file_structure_and_boundary_chunks_reopened": True,
    }


def _write_netcdf_chunks(
    output_tmp: Path,
    records: list[dict],
    raw_maps: dict,
    feature_rows: pd.DataFrame,
    experiment: dict,
    treatment_models: dict,
    area_map_by_feature: dict,
    model_columns: list[dict],
    scaling_model: FeatureScalingModel,
    time_chunk: int,
    lat_count: int,
    lon_count: int,
    output_feature_names: list[str],
    excluded_features: set[str],
):
    from netCDF4 import Dataset

    model_column_names = [column["name"] for column in model_columns]
    feature_names = [
        column["name"] for column in model_columns if column["kind"] == "feature"
    ]
    indicator_names = [
        column["name"] for column in model_columns if column["kind"] == "indicator"
    ]
    offset_samples = 0
    offset_time = 0

    with Dataset(str(output_tmp), "a") as nc:
        for record in records:
            with xr.open_dataset(record["path"], decode_times=True) as ds:
                count = int(ds.sizes["time"])
                for t_start in range(0, count, time_chunk):
                    t_end = min(t_start + time_chunk, count)
                    chunk_times = t_end - t_start
                    n_chunk = chunk_times * lat_count * lon_count
                    start = offset_samples
                    end = start + n_chunk

                    transformed_columns, codes = _transform_feature_chunk(
                        feature_rows,
                        experiment,
                        raw_maps,
                        treatment_models,
                        area_map_by_feature,
                        start,
                        end,
                        excluded_features=excluded_features,
                    )
                    matrix = np.column_stack([
                        transformed_columns[name] for name in model_column_names
                    ])
                    scaled = transform_feature_scaler(
                        matrix,
                        scaling_model,
                        model_column_names,
                    )
                    if not np.isfinite(scaled).all():
                        raise ValueError("Non-finite scaled values produced during output write")
                    for indicator_name in indicator_names:
                        indicator_values = transformed_columns[indicator_name]
                        if not np.isin(indicator_values, [0, 1]).all():
                            raise ValueError(f"Non-binary indicator generated: {indicator_name}")
                    for source_name, code_values in codes.items():
                        if not np.isin(code_values, [0, 1, 2, 3, 4]).all():
                            raise ValueError(f"Invalid missingness code generated for {source_name}")

                    for index, name in enumerate(model_column_names):
                        shaped = scaled[:, index].reshape(chunk_times, lat_count, lon_count)
                        if name in indicator_names:
                            nc.variables[name][offset_time:offset_time + chunk_times, :, :] = (
                                np.rint(shaped).astype(np.uint8)
                            )
                        else:
                            nc.variables[name][offset_time:offset_time + chunk_times, :, :] = shaped

                    for variable, code_values in codes.items():
                        nc.variables[f"missingness_code__{variable}"][
                            offset_time:offset_time + chunk_times, :, :
                        ] = code_values.reshape(chunk_times, lat_count, lon_count)

                    offset_samples = end
                    offset_time += chunk_times

    return offset_time, offset_samples


def _build_scaling_manifest(model: FeatureScalingModel) -> dict:
    return {
        "scaler_type": model.scaler_type,
        "weighting": model.weighting,
        "fit_scope": "full_2010_2021_primary_descriptive_partition",
        "n_training_samples": model.n_training_samples,
        "feature_order": list(model.feature_names),
        "feature_families": list(model.feature_families),
        "scale_mask": list(model.scale_mask),
        "center": model.center.tolist(),
        "scale": model.scale.tolist(),
        "feature_weights": model.feature_weights.tolist(),
        "quantile_range": list(model.quantile_range),
        "output_dtype": "float32",
    }


def process_experiment(
    run_row: dict,
    registry_frame: pd.DataFrame,
    selected_features: dict,
    records: list[dict],
    lat: np.ndarray,
    lon: np.ndarray,
    plan: dict,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    work_root: Path = DEFAULT_WORK_DIR,
    processing_manifest_dir: Path = DEFAULT_PROCESSING_MANIFEST_DIR,
    time_chunk: int = DEFAULT_TIME_CHUNK,
) -> dict:
    run_id = run_row["run_id"]
    feature_set = run_row["feature_set"]
    experiment = {
        "stage": run_row["stage"],
        "feature_set": feature_set,
        "property_treatment": run_row["property_treatment"],
        "cloud_area_treatment": run_row["cloud_area_treatment"],
        "scaler": run_row["scaler"],
        "weighting": run_row["weighting"],
        "purpose": run_row.get("purpose", ""),
    }
    feature_rows = selected_features[feature_set].copy().reset_index(drop=True)
    feature_names = feature_rows["variable"].astype(str).tolist()
    area_map_by_feature = {}
    for row in feature_rows.itertuples(index=False):
        if str(row.family) != "cloud_area":
            area_value = row.matching_cloud_area_variable
            if pd.isna(area_value) or not str(area_value).strip():
                raise ValueError(f"Missing cloud-area mapping for {row.variable}")
            area_map_by_feature[str(row.variable)] = str(area_value).strip()

    all_area_names = set(area_map_by_feature.values())
    selected_area_names = set(
        feature_rows.loc[feature_rows["family"].astype(str) == "cloud_area", "variable"].astype(str)
    )
    if not all_area_names.issubset(selected_area_names):
        raise ValueError(
            f"Feature set {feature_set} does not contain all required matching area variables: "
            f"{sorted(all_area_names - selected_area_names)}"
        )

    total_time = sum(record["time_count"] for record in records)
    lat_count, lon_count = len(lat), len(lon)
    n_samples = total_time * lat_count * lon_count
    work_dir = Path(work_root) / run_id
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    processing_manifest_dir = Path(processing_manifest_dir)
    output_path = output_dir / f"{run_id}.nc"
    output_tmp = output_path.with_suffix(".nc.tmp")
    processing_manifest_path = processing_manifest_dir / f"{run_id}.json"

    if output_path.exists():
        raise FileExistsError(
            f"Output already exists without a verified completed status: {output_path}. "
            "Move it aside or inspect the processing manifest before rerunning."
        )

    work_dir.mkdir(parents=True, exist_ok=True)
    raw_maps = {}
    try:
        raw_maps, total_samples, time_holder, years, seasons = _create_raw_memmaps(
            records,
            feature_rows,
            work_dir,
            lat_count,
            lon_count,
            time_chunk,
        )
        if total_samples != n_samples:
            raise RuntimeError("Raw memmap sample count does not match input inventory")
        times = time_holder[0]

        treatment_models, missingness_counts, screening = _fit_treatment_models(
            feature_rows,
            experiment,
            raw_maps,
            area_map_by_feature,
        )

        excluded_features = sorted([
            variable
            for variable, decision in screening.items()
            if decision.get("excluded_from_model_matrix", False)
        ])
        output_feature_rows = feature_rows.loc[
            ~feature_rows["variable"].astype(str).isin(excluded_features)
        ].copy().reset_index(drop=True)
        output_feature_names = output_feature_rows["variable"].astype(str).tolist()
        if not output_feature_names:
            raise ValueError("No model features remain after CA-B screening")

        model_columns = _model_columns(output_feature_rows, experiment)
        scaling_model = _fit_out_of_core_scaler(
            output_feature_rows,
            experiment,
            treatment_models,
            raw_maps,
            area_map_by_feature,
            n_samples,
            model_columns,
        )

        _create_netcdf_output(
            output_tmp,
            output_feature_names,
            model_columns,
            feature_names,
            lat,
            lon,
            times,
            years,
            seasons,
            experiment,
            run_id,
            records,
            scaling_model,
            time_chunk,
        )
        written_times, written_samples = _write_netcdf_chunks(
            output_tmp,
            records,
            raw_maps,
            feature_rows,
            experiment,
            treatment_models,
            area_map_by_feature,
            model_columns,
            scaling_model,
            time_chunk,
            lat_count,
            lon_count,
            output_feature_names,
            set(excluded_features),
        )
        if written_times != total_time or written_samples != n_samples:
            raise RuntimeError(
                f"Output count mismatch: times={written_times}/{total_time}, "
                f"samples={written_samples}/{n_samples}"
            )
        output_validation = _validate_written_output(
            output_tmp,
            total_time,
            lat_count,
            lon_count,
            model_columns,
            feature_names,
            run_id,
            time_chunk,
        )

        output_size = output_tmp.stat().st_size
        output_sha256 = _sha256_file(output_tmp)
        os.replace(output_tmp, output_path)

        manifest = {
            "schema_version": "1.0",
            "milestone": "M18.7",
            "run_id": run_id,
            "status": "COMPLETED",
            "created_utc": _utc_now(),
            "processing_partition": "primary_descriptive_fit",
            "fit_years": [2010, 2021],
            "transform_years": [2010, 2021],
            "includes_2017": True,
            "interpretation": (
                "Full-period descriptive processing; not a held-out temporal validation result."
            ),
            "experiment": experiment,
            "input": {
                "dataset_count": len(records),
                "timestamp_count": total_time,
                "grid_shape": [lat_count, lon_count],
                "grid_cell_hour_observations": n_samples,
                "files": [
                    {
                        "path": str(item["path"].relative_to(PROJECT_ROOT))
                        if item["path"].is_relative_to(PROJECT_ROOT)
                        else str(item["path"]),
                        "size_bytes": item["size_bytes"],
                        "mtime_ns": item["mtime_ns"],
                        "timestamp_diagnostics": item.get("timestamp_diagnostics", {}),
                    }
                    for item in records
                ],
            },
            "feature_set_registry_order": feature_names,
            "output_feature_order": output_feature_names,
            "missingness_code_feature_order": feature_names,
            "excluded_features": excluded_features,
            "model_matrix_order": [column["name"] for column in model_columns],
            "model_matrix_columns": model_columns,
            "missingness_counts": missingness_counts,
            "treatment_and_screening": screening,
            "scaling": _build_scaling_manifest(scaling_model),
            "output_validation": output_validation,
            "output": {
                "path": str(output_path.relative_to(PROJECT_ROOT))
                if output_path.is_relative_to(PROJECT_ROOT)
                else str(output_path),
                "size_bytes": output_size,
                "sha256": output_sha256,
                "format": "NetCDF4",
                "compression": "zlib level 4",
                "feature_dtype": "float32",
                "indicator_dtype": "uint8",
                "missingness_code_dtype": "uint8",
            },
            "raw_netcdf_modified": False,
        }
        try:
            _atomic_json(processing_manifest_path, manifest)
        except Exception:
            if output_path.exists():
                output_path.unlink()
            raise
        return {
            "run_id": run_id,
            "status": "COMPLETED",
            "output_path": str(output_path),
            "output_size_gib": round(output_size / GIB, 3),
            "manifest_path": str(processing_manifest_path),
            "feature_count": len(output_feature_names),
            "model_column_count": len(model_columns),
        }
    finally:
        for mapped in raw_maps.values():
            try:
                mapped.flush()
                mapped._mmap.close()
            except Exception:
                pass
        raw_maps.clear()
        gc.collect()
        if output_tmp.exists():
            try:
                output_tmp.unlink()
            except OSError:
                pass
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


def validate_preflight_report(path: Path, expected_samples: int, expected_files: int) -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"M18.7 preflight report not found: {path}. Run prepare_m18_7_processing_preflight.py first."
        )
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS":
        raise ValueError("M18.7 preflight report does not have PASS status")
    inventory = report.get("input_validation", {})
    if int(inventory.get("file_count", -1)) != int(expected_files):
        raise ValueError("Preflight file count does not match current input inventory")
    if int(inventory.get("grid_cell_hour_observations", -1)) != int(expected_samples):
        raise ValueError("Preflight observation count does not match current input inventory")
    if report.get("processing_executed") is not False:
        raise ValueError("Preflight report must record processing_executed=false")
    return report


def _load_context(
    plan_path: Path,
    experiment_config_path: Path,
    feature_registry_path: Path,
    run_registry_path: Path,
    data_dir: Path,
    preflight_report_path: Path,
):
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    experiment_config = json.loads(
        Path(experiment_config_path).read_text(encoding="utf-8")
    )
    feature_registry, selected = load_feature_registry(
        feature_registry_path,
        experiment_config["expected_feature_counts"],
    )
    run_table = load_run_table(run_registry_path)

    expected_registry_hash = _sha256_file(feature_registry_path)
    expected_config_hash = hashlib.sha256(
        Path(experiment_config_path).read_bytes()
    ).hexdigest()
    for row in run_table.to_dict("records"):
        if row["feature_registry_sha256"] != expected_registry_hash:
            raise ValueError(
                "M18.6 experiment registry feature-registry hash is stale. "
                "Regenerate the M18.6 experiment registry before M18.7."
            )
        if row["config_sha256"] != expected_config_hash:
            raise ValueError(
                "M18.6 experiment registry config hash is stale. "
                "Regenerate the M18.6 experiment registry before M18.7."
            )

    expected = dict(plan["expected_data"])
    expected["start_year"] = int(plan["study_period"]["start_year"])
    expected["end_year"] = int(plan["study_period"]["end_year"])
    records, lat, lon = discover_input_files(data_dir, expected)
    n_time = sum(record["time_count"] for record in records)
    n_samples = n_time * len(lat) * len(lon)
    validate_preflight_report(preflight_report_path, n_samples, len(records))
    return plan, experiment_config, feature_registry, selected, run_table, records, lat, lon


def _select_pilot(run_table: pd.DataFrame) -> dict:
    matches = run_table[
        (run_table["stage"] == "A")
        & (run_table["feature_set"] == "FS-A")
        & (run_table["purpose"] == "baseline")
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one Stage A FS-A baseline run, found {len(matches)}")
    return matches.iloc[0].to_dict()


def _estimate_for_run(run_row: dict, selected_features: dict, n_samples: int) -> dict:
    frame = selected_features[run_row["feature_set"]]
    feature_count = len(frame)
    properties = int((frame["family"].astype(str) != "cloud_area").sum())
    areas = 5
    if run_row["cloud_area_treatment"] == "CA-B":
        # CA-B removes the low-layer area feature for the audited dataset.
        feature_count -= 1
        indicator_count = properties
    else:
        indicator_count = properties
        if run_row["property_treatment"] in {"MD-B", "SA-B"}:
            indicator_count += properties
        indicator_count += areas
    output = n_samples * (feature_count * 4 + len(frame) + indicator_count)
    raw_work = n_samples * len(frame) * 4
    return {
        "estimated_output_gib": round(output / GIB, 2),
        "estimated_work_gib": round(raw_work / GIB, 2),
        "recommended_free_gib": round((output * 1.10 + raw_work + 5 * GIB) / GIB, 2),
    }


def _run_one(
    row: dict,
    registry_frame: pd.DataFrame,
    selected_features: dict,
    records: list[dict],
    lat: np.ndarray,
    lon: np.ndarray,
    plan: dict,
    run_registry_path: Path,
    output_dir: Path,
    work_dir: Path,
    manifest_dir: Path,
    time_chunk: int,
) -> dict:
    run_id = row["run_id"]
    output_path = output_dir / f"{run_id}.nc"
    processing_manifest = manifest_dir / f"{run_id}.json"
    if row["status"] == "COMPLETED":
        if not output_path.exists() or not processing_manifest.exists():
            raise FileNotFoundError(
                f"Run {run_id} is marked COMPLETED but output or processing manifest is missing"
            )
        return {
            "run_id": run_id,
            "status": "SKIPPED_ALREADY_COMPLETED",
            "output_path": str(output_path),
        }

    if output_path.exists() and processing_manifest.exists():
        recovered = json.loads(processing_manifest.read_text(encoding="utf-8"))
        output_meta = recovered.get("output", {})
        if (
            recovered.get("status") == "COMPLETED"
            and int(output_meta.get("size_bytes", -1)) == output_path.stat().st_size
            and output_meta.get("sha256") == _sha256_file(output_path)
        ):
            update_run_status(
                run_registry_path,
                run_id,
                "COMPLETED",
                "Recovered completed output/manifest after interrupted registry update",
            )
            return {
                "run_id": run_id,
                "status": "RECOVERED_COMPLETED",
                "output_path": str(output_path),
            }
        raise FileExistsError(
            f"Existing output/manifest for {run_id} failed completion verification. "
            "Inspect the artifacts before rerunning."
        )

    if output_path.exists() or processing_manifest.exists():
        raise FileExistsError(
            f"Incomplete output/manifest found for non-completed run {run_id}. "
            "Inspect or move the stale artifact before rerunning."
        )

    update_run_status(run_registry_path, run_id, "RUNNING", "M18.7 processing started")
    try:
        result = process_experiment(
            row,
            registry_frame,
            selected_features,
            records,
            lat,
            lon,
            plan,
            output_dir,
            work_dir,
            manifest_dir,
            time_chunk,
        )
        update_run_status(run_registry_path, run_id, "COMPLETED", "M18.7 output and manifest validated")
        return result
    except Exception as exc:
        update_run_status(run_registry_path, run_id, "FAILED", f"{type(exc).__name__}: {exc}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--experiment-config", type=Path, default=DEFAULT_EXPERIMENT_CONFIG)
    parser.add_argument("--feature-registry", type=Path, default=DEFAULT_FEATURE_REGISTRY)
    parser.add_argument("--run-registry", type=Path, default=DEFAULT_RUN_REGISTRY)
    parser.add_argument("--preflight-report", type=Path, default=DEFAULT_PREFLIGHT_REPORT)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_PROCESSING_MANIFEST_DIR)
    parser.add_argument("--time-chunk", type=int, default=DEFAULT_TIME_CHUNK)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list-runs", action="store_true")
    group.add_argument("--estimate", action="store_true")
    group.add_argument("--pilot", action="store_true")
    group.add_argument("--run-id")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.time_chunk < 1:
        parser.error("--time-chunk must be positive")

    plan, exp_config, registry_frame, selected, run_table, records, lat, lon = _load_context(
        args.plan,
        args.experiment_config,
        args.feature_registry,
        args.run_registry,
        args.data_dir,
        args.preflight_report,
    )
    n_time = sum(record["time_count"] for record in records)
    n_samples = n_time * len(lat) * len(lon)

    if args.list_runs:
        print(run_table[["run_id", "stage", "feature_set", "property_treatment", "cloud_area_treatment", "status"]].to_string(index=False))
        return

    if args.estimate:
        estimate = calculate_storage_estimate(n_samples, selected, registry_frame)
        disk = shutil.disk_usage(PROJECT_ROOT)
        print("\n========== M18.7 STORAGE ESTIMATE ==========")
        print(f"Experiments: {estimate['experiment_count']}")
        print(f"Uncompressed output including indicators: {estimate['total_uncompressed_output_gib']} GiB")
        print(f"Peak raw work space: {estimate['peak_raw_work_gib']} GiB")
        print(f"Recommended free space including 10% headroom and 5 GiB reserve: {estimate['recommended_free_space_gib']} GiB")
        print(f"Currently available: {disk.free / GIB:.2f} GiB")
        print(f"Sufficient: {disk.free >= estimate['recommended_free_space_bytes']}")
        return

    if args.pilot:
        rows = [_select_pilot(run_table)]
    elif args.run_id:
        matches = run_table[run_table["run_id"] == args.run_id]
        if len(matches) != 1:
            raise KeyError(f"Run ID not found or not unique: {args.run_id}")
        rows = [matches.iloc[0].to_dict()]
    else:
        rows = [
            row for row in run_table.to_dict("records")
            if row["status"] in {"PENDING", "FAILED", "RUNNING"}
        ]

    if not rows:
        print("No pending experiments to process.")
        return

    disk = shutil.disk_usage(PROJECT_ROOT)
    if args.all:
        estimate = calculate_storage_estimate(n_samples, selected, registry_frame)
        required = estimate["recommended_free_space_bytes"]
        print(
            f"Full-batch uncompressed output estimate: "
            f"{estimate['total_uncompressed_output_gib']:.2f} GiB"
        )
        print(
            f"Recommended free space: {estimate['recommended_free_space_gib']:.2f} GiB; "
            f"currently available: {disk.free / GIB:.2f} GiB"
        )
        if disk.free < required:
            raise OSError(
                f"Insufficient disk space for full M18.7 run: available={disk.free / GIB:.2f} GiB, "
                f"recommended={required / GIB:.2f} GiB"
            )
    else:
        run_estimate = _estimate_for_run(rows[0], selected, n_samples)
        required = run_estimate["recommended_free_gib"] * GIB
        print(
            f"Selected-run uncompressed output estimate: {run_estimate['estimated_output_gib']:.2f} GiB; "
            f"peak work space: {run_estimate['estimated_work_gib']:.2f} GiB"
        )
        print(
            f"Recommended free space: {run_estimate['recommended_free_gib']:.2f} GiB; "
            f"currently available: {disk.free / GIB:.2f} GiB"
        )
        if disk.free < required:
            raise OSError(
                f"Insufficient disk space for selected run: available={disk.free / GIB:.2f} GiB, "
                f"recommended={required / GIB:.2f} GiB"
            )

    print("\n========== M18.7 PROCESSING ==========")
    print(f"Selected experiments: {len(rows)}")
    print(f"Input datasets: {len(records)}")
    print(f"Grid-cell-hour observations per experiment: {n_samples:,}")
    print("Partition: primary descriptive fit (2010-2021, including 2017)")
    results = []
    for index, row in enumerate(rows, start=1):
        print(f"\n[{index}/{len(rows)}] {row['run_id']} | {row['status']}")
        result = _run_one(
            row,
            registry_frame,
            selected,
            records,
            lat,
            lon,
            plan,
            args.run_registry,
            args.output_dir,
            args.work_dir,
            args.manifest_dir,
            args.time_chunk,
        )
        results.append(result)
        print(result)

    completed = sum(item["status"] == "COMPLETED" for item in results)
    skipped = sum(item["status"] == "SKIPPED_ALREADY_COMPLETED" for item in results)
    print("\n========== M18.7 RESULT ==========")
    print(f"Completed in this invocation: {completed}")
    print(f"Already completed and skipped: {skipped}")
    print(f"Output directory: {args.output_dir}")
    print(f"Processing manifests: {args.manifest_dir}")


if __name__ == "__main__":
    main()
