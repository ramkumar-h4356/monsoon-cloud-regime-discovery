"""Prepare validated Established Monsoon Group B matrices and M3 manifest.

Outputs are written to a new M3-specific directory. Existing clustering inputs
and results are not overwritten.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import xarray as xr
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "06_feature_engineering"))

from established_monsoon_feature_validation import (  # noqa: E402
    FEATURES, LOG1P_FEATURES, YEARS, EXPECTED_ROWS_PER_YEAR,
    validate_annual_dataset, validate_feature_frame, build_feature_registry,
    validate_registry,
)

DATA_DIR = ROOT / "data" / "processed" / "ceres_daily" / "established_monsoon"
TABLE_DIR = ROOT / "results" / "tables" / "06_feature_engineering"
OUTPUT_DIR = ROOT / "data" / "processed" / "clustering" / "established_monsoon" / "m3_feature_preparation"


def load_evidence():
    screening = pd.read_csv(TABLE_DIR / "established_monsoon_variable_screening.csv")
    yearly = pd.read_csv(TABLE_DIR / "established_monsoon_yearly_screening.csv")
    integrated = pd.read_csv(TABLE_DIR / "established_monsoon_integrated_feature_evidence.csv")
    return screening, yearly, integrated


def main():
    annual_frames = []
    reference_lat = reference_lon = None
    print("========== M3 GROUP B FEATURE PREPARATION ==========")
    for year in YEARS:
        path = DATA_DIR / f"CERES_{year}_established_monsoon_daily.nc"
        if not path.is_file():
            raise FileNotFoundError(f"Required annual CERES file missing: {path}")
        with xr.open_dataset(path) as ds:
            validate_annual_dataset(ds, year)
            lat = np.asarray(ds["lat"].values, dtype=float)
            lon = np.asarray(ds["lon"].values, dtype=float)
            if reference_lat is None:
                reference_lat, reference_lon = lat.copy(), lon.copy()
            elif not np.array_equal(lat, reference_lat) or not np.array_equal(lon, reference_lon):
                raise ValueError(f"{year}: spatial grid differs from reference year.")
            ncell = ds.sizes["lat"] * ds.sizes["lon"]
            frame = pd.DataFrame({
                feature: np.asarray(ds[feature].values, dtype=np.float64).reshape(-1)
                for feature in FEATURES
            })
            frame.insert(0, "longitude", np.tile(lon, ds.sizes["time"] * ds.sizes["lat"]))
            frame.insert(0, "latitude", np.tile(np.repeat(lat, ds.sizes["lon"]), ds.sizes["time"]))
            frame.insert(0, "date", np.repeat(pd.to_datetime(ds["time"].values), ncell))
            frame.insert(0, "year", year)
            annual_frames.append(frame)
        print(f"Validated {year}")

    data = pd.concat(annual_frames, ignore_index=True)
    validate_feature_frame(data)
    complete_mask = np.isfinite(data.loc[:, FEATURES].to_numpy(dtype=np.float64)).all(axis=1)
    complete = data.loc[complete_mask].copy().reset_index(drop=True)
    if complete.empty:
        raise ValueError("No complete-case observations remain.")
    X_original = complete.loc[:, FEATURES].to_numpy(dtype=np.float64)
    X_log_frame = complete.loc[:, FEATURES].copy()
    for feature in LOG1P_FEATURES:
        X_log_frame.loc[:, feature] = np.log1p(X_log_frame[feature].to_numpy(dtype=float))
    X_log = X_log_frame.to_numpy(dtype=np.float64)

    # Preserve the existing descriptive full-period StandardScaler baseline.
    baseline_scaler = StandardScaler()
    baseline = baseline_scaler.fit_transform(X_original)
    log_scaler = StandardScaler()
    log_matrix = log_scaler.fit_transform(X_log)

    if not np.isfinite(baseline).all() or not np.isfinite(log_matrix).all():
        raise ValueError("Non-finite values detected after scaling.")
    if baseline.shape != (len(complete), len(FEATURES)) or log_matrix.shape != baseline.shape:
        raise ValueError("Unexpected model matrix shape.")

    screening, yearly, integrated = load_evidence()
    registry = build_feature_registry(screening, yearly, integrated)
    validate_registry(registry)

    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = complete[["year", "date", "latitude", "longitude"]].copy()
    registry.to_csv(output_dir / "established_monsoon_group_B_feature_registry.csv", index=False)
    metadata.to_csv(output_dir / "established_monsoon_group_B_metadata.csv", index=False)
    np.savez_compressed(
        output_dir / "established_monsoon_group_B_baseline.npz",
        X=baseline, features=np.array(FEATURES),
        scaler_mean=baseline_scaler.mean_, scaler_scale=baseline_scaler.scale_,
    )
    np.savez_compressed(
        output_dir / "established_monsoon_group_B_log_sensitivity.npz",
        X=log_matrix, features=np.array(FEATURES),
        scaler_mean=log_scaler.mean_, scaler_scale=log_scaler.scale_,
        log1p_features=np.array(LOG1P_FEATURES),
    )
    manifest = {
        "project_component": "Established Monsoon",
        "years": list(YEARS),
        "seasonal_window": ["07-15", "08-13"],
        "expected_rows_per_year": EXPECTED_ROWS_PER_YEAR,
        "expected_raw_rows": EXPECTED_ROWS_PER_YEAR * len(YEARS),
        "observed_raw_rows": int(len(data)),
        "complete_case_rows": int(len(complete)),
        "excluded_incomplete_rows": int(len(data) - len(complete)),
        "feature_count": len(FEATURES),
        "features_in_order": list(FEATURES),
        "log1p_features": list(LOG1P_FEATURES),
        "imputation": "None; incomplete rows excluded for complete-case matrices",
        "scaling_fit_scope": "Full 2010-2021 complete-case period for descriptive unsupervised baseline; not a held-out predictive evaluation",
        "leakage_note": "For any future train/test or predictive evaluation, fit transformations and scalers on training/reference data only, then transform held-out data.",
        "baseline_matrix": "established_monsoon_group_B_baseline.npz",
        "log_sensitivity_matrix": "established_monsoon_group_B_log_sensitivity.npz",
        "metadata": "established_monsoon_group_B_metadata.csv",
        "feature_registry": "established_monsoon_group_B_feature_registry.csv",
    }
    (output_dir / "established_monsoon_group_B_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print("\n========== M3 PREPARATION SUMMARY ==========")
    print(f"Raw observations: {len(data):,}")
    print(f"Complete cases: {len(complete):,}")
    print(f"Excluded incomplete: {len(data) - len(complete):,}")
    print(f"Features: {len(FEATURES)}")
    print(f"Baseline matrix: {baseline.shape}")
    print(f"Log sensitivity matrix: {log_matrix.shape}")
    print(f"Output: {output_dir}")
    print("PASS: feature matrix, registry and manifest validated.")


if __name__ == "__main__":
    main()
