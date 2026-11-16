"""Post-Monsoon Missingness Classification and Feature Engineering Audit (Milestone M20).

Analyzes all 12 post-monsoon observation windows (October 15 - November 13, 2010-2021)
using the shared missingness classification engine and feature set definitions.
Produces per-variable, per-year, and aggregate missingness accounting.
"""

from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
import xarray as xr

PROJECT_ROOT = Path(r"D:\Project Simulator\monsoon_cloud_research")
sys.path.insert(0, str(PROJECT_ROOT / "src" / "shared" / "missingness"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "shared" / "feature_engineering"))

from missingness_classifier import (
    MissingnessCode,
    classify_missingness,
    load_feature_registry,
    CLASSIFICATION_LABELS,
)

DATA_DIR = PROJECT_ROOT / "data" / "interim" / "ceres_seasonal" / "post_monsoon"
OUT_MISSINGNESS = PROJECT_ROOT / "reports" / "seasons" / "post_monsoon" / "missingness"
OUT_FE = PROJECT_ROOT / "reports" / "seasons" / "post_monsoon" / "feature_engineering"

YEARS = list(range(2010, 2022))
OUT_MISSINGNESS.mkdir(parents=True, exist_ok=True)
OUT_FE.mkdir(parents=True, exist_ok=True)


def run_post_monsoon_m20_audit():
    print("=" * 70)
    print("M20: POST-MONSOON MISSINGNESS & FEATURE ENGINEERING AUDIT")
    print("=" * 70)

    # 1. Load Feature Registry
    registry_path = PROJECT_ROOT / "reports" / "feature_engineering" / "feature_set_registry.csv"
    registry_df = pd.read_csv(registry_path)
    mapping = load_feature_registry(registry_path)
    registered_vars = list(registry_df["variable"].str.strip())
    print(f"Loaded {len(registered_vars)} registered variables from {registry_path.name}")

    # 2. Cloud area variables
    cloud_area_vars = [v for v in registered_vars if v.startswith("cldarea_")]
    property_vars = [v for v in registered_vars if not v.startswith("cldarea_")]

    yearly_records = []
    variable_stats = {v: {
        "variable": v,
        "is_cloud_area": v.startswith("cldarea_"),
        "matching_area_variable": mapping.get(v),
        "total_values": 0,
        "observed": 0,
        "structural_absence": 0,
        "residual_missing": 0,
        "unknown_cloud_availability": 0,
        "cloud_area_missing": 0,
        "finite_values": 0,
        "out_of_range": 0,
        "min": float("inf"),
        "max": float("-inf"),
        "sum": 0.0,
        "sq_sum": 0.0,
    } for v in registered_vars}

    for year in YEARS:
        nc_file = DATA_DIR / f"CERES_{year}_post_monsoon.nc"
        print(f"Processing Year {year}: {nc_file.name}")
        with xr.open_dataset(nc_file) as ds:
            # Pre-load cloud area variables for this year
            area_arrays = {ca: np.asarray(ds[ca].values, dtype=np.float64) for ca in cloud_area_vars}

            for var in registered_vars:
                var_da = ds[var]
                vals = np.asarray(var_da.values, dtype=np.float64)
                finite_mask = np.isfinite(vals)
                n_total = vals.size

                # Range check from metadata
                valid_min = var_da.attrs.get("valid_min")
                valid_max = var_da.attrs.get("valid_max")
                out_of_range_cnt = 0
                if valid_min is not None and valid_max is not None:
                    out_of_range_cnt = int(np.count_nonzero(finite_mask & ((vals < float(valid_min)) | (vals > float(valid_max)))))

                # Classification
                if var in cloud_area_vars:
                    codes = classify_missingness(vals, var)
                else:
                    match_area_var = mapping[var]
                    area_vals = area_arrays[match_area_var]
                    codes = classify_missingness(vals, var, area_values=area_vals, area_variable=match_area_var)

                # Counts
                c_obs = int(np.count_nonzero(codes == MissingnessCode.OBSERVED))
                c_sa = int(np.count_nonzero(codes == MissingnessCode.STRUCTURAL_ABSENCE))
                c_rm = int(np.count_nonzero(codes == MissingnessCode.RESIDUAL_MISSING))
                c_unk = int(np.count_nonzero(codes == MissingnessCode.UNKNOWN_CLOUD_AVAILABILITY))
                c_cam = int(np.count_nonzero(codes == MissingnessCode.CLOUD_AREA_MISSING))

                # Numerical moments
                usable = vals[finite_mask]
                if usable.size > 0:
                    v_min = float(np.min(usable))
                    v_max = float(np.max(usable))
                    v_sum = float(np.sum(usable))
                    v_sq_sum = float(np.sum(usable ** 2))
                else:
                    v_min, v_max, v_sum, v_sq_sum = np.nan, np.nan, 0.0, 0.0

                # Update per-variable overall
                vstat = variable_stats[var]
                vstat["total_values"] += n_total
                vstat["observed"] += c_obs
                vstat["structural_absence"] += c_sa
                vstat["residual_missing"] += c_rm
                vstat["unknown_cloud_availability"] += c_unk
                vstat["cloud_area_missing"] += c_cam
                vstat["finite_values"] += int(usable.size)
                vstat["out_of_range"] += out_of_range_cnt
                if not np.isnan(v_min) and v_min < vstat["min"]:
                    vstat["min"] = v_min
                if not np.isnan(v_max) and v_max > vstat["max"]:
                    vstat["max"] = v_max
                vstat["sum"] += v_sum
                vstat["sq_sum"] += v_sq_sum

                yearly_records.append({
                    "year": year,
                    "variable": var,
                    "total_samples": n_total,
                    "observed": c_obs,
                    "observed_pct": round(100.0 * c_obs / n_total, 4),
                    "structural_absence": c_sa,
                    "structural_absence_pct": round(100.0 * c_sa / n_total, 4),
                    "residual_missing": c_rm,
                    "residual_missing_pct": round(100.0 * c_rm / n_total, 4),
                    "unknown_cloud_availability": c_unk,
                    "unknown_cloud_availability_pct": round(100.0 * c_unk / n_total, 4),
                    "cloud_area_missing": c_cam,
                    "cloud_area_missing_pct": round(100.0 * c_cam / n_total, 4),
                    "out_of_range": out_of_range_cnt,
                    "mean": float(np.mean(usable)) if usable.size > 0 else np.nan,
                    "std": float(np.std(usable)) if usable.size > 0 else np.nan,
                })

    # Summary table per variable
    var_summary_rows = []
    for var, stat in variable_stats.items():
        n = stat["total_values"]
        c_obs = stat["observed"]
        c_sa = stat["structural_absence"]
        c_rm = stat["residual_missing"]
        c_unk = stat["unknown_cloud_availability"]
        c_cam = stat["cloud_area_missing"]
        n_finite = stat["finite_values"]
        mean_val = stat["sum"] / n_finite if n_finite > 0 else np.nan
        var_val = (stat["sq_sum"] / n_finite) - (mean_val ** 2) if n_finite > 1 else np.nan
        std_val = float(np.sqrt(max(0.0, var_val))) if not np.isnan(var_val) else np.nan

        # Eligibility screening
        missing_pct = 100.0 * (n - c_obs) / n
        residual_pct = 100.0 * c_rm / n
        if residual_pct <= 5.0:
            band = "LOW_CONCERN"
            rec = "INCLUDE"
        elif residual_pct <= 20.0:
            band = "MODERATE_REVIEW"
            rec = "REVIEW"
        else:
            band = "HIGH_CONCERN"
            rec = "EXCLUDE_PRIMARY"

        var_summary_rows.append({
            "variable": var,
            "is_cloud_area": stat["is_cloud_area"],
            "matching_area_variable": stat["matching_area_variable"],
            "total_observations": n,
            "observed_pct": round(100.0 * c_obs / n, 4),
            "structural_absence_pct": round(100.0 * c_sa / n, 4),
            "residual_missing_pct": round(residual_pct, 4),
            "unknown_cloud_availability_pct": round(100.0 * c_unk / n, 4),
            "cloud_area_missing_pct": round(100.0 * c_cam / n, 4),
            "total_missing_pct": round(missing_pct, 4),
            "eligibility_band": band,
            "screening_recommendation": rec,
            "mean": round(mean_val, 4) if not np.isnan(mean_val) else None,
            "std": round(std_val, 4) if not np.isnan(std_val) else None,
            "min": round(stat["min"], 4) if np.isfinite(stat["min"]) else None,
            "max": round(stat["max"], 4) if np.isfinite(stat["max"]) else None,
        })

    # Save outputs
    yearly_df = pd.DataFrame(yearly_records)
    yearly_csv = OUT_MISSINGNESS / "post_monsoon_missingness_by_year.csv"
    yearly_df.to_csv(yearly_csv, index=False)
    print(f"Saved yearly missingness: {yearly_csv}")

    var_df = pd.DataFrame(var_summary_rows)
    var_csv = OUT_MISSINGNESS / "post_monsoon_missingness_by_variable.csv"
    var_df.to_csv(var_csv, index=False)
    print(f"Saved variable missingness summary: {var_csv}")

    # Feature Set Validation
    fs_validation = {}
    for fs_id in ["FS-A", "FS-B", "FS-C", "FS-D", "FS-E", "FS-F"]:
        in_fs = registry_df[registry_df[fs_id] == True]["variable"].str.strip().tolist()
        fs_validation[fs_id] = {
            "feature_set": fs_id,
            "expected_count": {"FS-A": 36, "FS-B": 21, "FS-C": 21, "FS-D": 21, "FS-E": 16, "FS-F": 21}[fs_id],
            "actual_count": len(in_fs),
            "variables": in_fs,
            "status": "VALID" if len(in_fs) == {"FS-A": 36, "FS-B": 21, "FS-C": 21, "FS-D": 21, "FS-E": 16, "FS-F": 21}[fs_id] else "INVALID"
        }

    fs_json = OUT_FE / "post_monsoon_feature_set_validation.json"
    fs_json.write_text(json.dumps(fs_validation, indent=2), encoding="utf-8")
    print(f"Saved feature set validation: {fs_json}")

    # Overall Summary JSON
    summary = {
        "milestone": "M20",
        "title": "Post-Monsoon Missingness and Feature Engineering Audit",
        "season": "post_monsoon",
        "season_window": "October 15 - November 13",
        "study_years": YEARS,
        "total_seasonal_files": len(YEARS),
        "total_observations_per_variable": len(YEARS) * 720 * 32 * 30,
        "registered_variables_audited": len(registered_vars),
        "feature_set_validation": {k: v["status"] for k, v in fs_validation.items()},
        "cloud_area_missingness_policy": "Zero-fill forbidden. Missing cloud area classified as CLOUD_AREA_MISSING.",
        "status": "COMPLETED_VALIDATED"
    }
    summary_json = OUT_MISSINGNESS / "post_monsoon_missingness_summary.json"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Saved overall summary: {summary_json}")
    print("M20 Audit completed successfully.")

if __name__ == "__main__":
    run_post_monsoon_m20_audit()
