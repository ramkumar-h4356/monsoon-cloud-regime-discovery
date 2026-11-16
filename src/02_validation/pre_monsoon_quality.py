
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

# ============================================================
# 1. PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    ROOT / "data" / "interim"
    / "ceres_seasonal" / "pre_monsoon"
)

REPORT_DIR = ROOT / "reports" / "data_quality"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(DATA_DIR.glob("*.nc"))

print("=== PRE-MONSOON DATA QUALITY ANALYSIS ===")
print("Project root:", ROOT)
print("Dataset directory:", DATA_DIR)
print("Number of files:", len(files))

if len(files) != 12:
    raise ValueError(
        f"Expected 12 NetCDF files, found {len(files)}"
    )

# ============================================================
# 2. STORAGE FOR RESULTS
# ============================================================

quality_rows = []
yearly_rows = []

# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================

def metadata_number(value):
    """Convert scalar numeric metadata safely."""
    if value is None:
        return np.nan

    try:
        arr = np.asarray(value)

        if arr.size != 1:
            return np.nan

        return float(arr.item())

    except (TypeError, ValueError, OverflowError):
        return np.nan


def calculate_statistics(values):
    """Calculate descriptive statistics on finite values."""

    if values.size == 0:
        return {
            "minimum": np.nan,
            "maximum": np.nan,
            "mean": np.nan,
            "median": np.nan,
            "std": np.nan,
            "p01": np.nan,
            "p05": np.nan,
            "p25": np.nan,
            "p75": np.nan,
            "p95": np.nan,
            "p99": np.nan,
        }

    return {
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values)),
        "p01": float(np.percentile(values, 1)),
        "p05": float(np.percentile(values, 5)),
        "p25": float(np.percentile(values, 25)),
        "p75": float(np.percentile(values, 75)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
    }


# ============================================================
# 4. PROCESS EACH YEAR
# ============================================================

for file in files:

    year = int(file.stem.split("_")[1])

    print(f"\nProcessing year: {year}")

    with xr.open_dataset(file, mask_and_scale=True) as ds:

        print("Dimensions:", dict(ds.sizes))
        print("Variables:", len(ds.data_vars))

        for name, variable in ds.data_vars.items():

            # Load one variable at a time
            values = np.asarray(variable.values).ravel()

            total_count = values.size

            # CERES variables are expected to be numeric
            if not np.issubdtype(values.dtype, np.number):
                print("Skipping non-numeric variable:", name)
                continue

            # Missing values are decoded to NaN by xarray
            missing_mask = pd.isna(values)

            # Distinguish NaN/missing from infinity
            finite_mask = np.isfinite(values)
            infinite_mask = np.isinf(values)

            clean = values[finite_mask]

            missing_count = int(np.sum(missing_mask))
            infinite_count = int(np.sum(infinite_mask))
            valid_count = int(clean.size)

            missing_percent = (
                100 * missing_count / total_count
                if total_count else np.nan
            )

            finite_percent = (
                100 * valid_count / total_count
                if total_count else np.nan
            )

            # Metadata validity limits
            valid_min = metadata_number(
                variable.attrs.get("valid_min")
            )

            valid_max = metadata_number(
                variable.attrs.get("valid_max")
            )

            below_min = 0
            above_max = 0

            if np.isfinite(valid_min):
                below_min = int(np.sum(clean < valid_min))

            if np.isfinite(valid_max):
                above_max = int(np.sum(clean > valid_max))

            outside_count = below_min + above_max

            outside_percent = (
                100 * outside_count / valid_count
                if valid_count else np.nan
            )

            stats = calculate_statistics(clean)

            row = {
                "year": year,
                "variable": name,
                "units": variable.attrs.get("units", ""),
                "long_name": variable.attrs.get(
                    "long_name", ""
                ),
                "dtype": str(variable.dtype),
                "total_count": total_count,
                "valid_count": valid_count,
                "missing_count": missing_count,
                "missing_percent": missing_percent,
                "infinite_count": infinite_count,
                "finite_percent": finite_percent,
                "valid_min_metadata": valid_min,
                "valid_max_metadata": valid_max,
                "below_valid_min": below_min,
                "above_valid_max": above_max,
                "outside_metadata_range": outside_count,
                "outside_percent": outside_percent,
            }

            row.update(stats)

            quality_rows.append(row)

        yearly_rows.append({
            "year": year,
            "time_records": ds.sizes.get("time", 0),
            "latitude_points": ds.sizes.get("lat", 0),
            "longitude_points": ds.sizes.get("lon", 0),
            "variable_count": len(ds.data_vars),
            "first_timestamp": str(
                ds.time.values[0]
            ) if "time" in ds.coords else "",
            "last_timestamp": str(
                ds.time.values[-1]
            ) if "time" in ds.coords else "",
        })

    print(f"Completed year {year}")

# ============================================================
# 5. CREATE DATAFRAMES
# ============================================================

quality_df = pd.DataFrame(quality_rows)
yearly_df = pd.DataFrame(yearly_rows)

# ============================================================
# 6. SAVE COMPLETE QUALITY REPORT
# ============================================================

quality_path = (
    REPORT_DIR / "pre_monsoon_quality.csv"
)

quality_df.to_csv(quality_path, index=False)

print("\nSaved:", quality_path)

# ============================================================
# 7. SAVE YEARLY DATASET SUMMARY
# ============================================================

yearly_path = (
    REPORT_DIR / "pre_monsoon_yearly_summary.csv"
)

yearly_df.to_csv(yearly_path, index=False)

print("Saved:", yearly_path)

# ============================================================
# 8. SAVE MISSING-VALUE SUMMARY
# ============================================================

missing_df = quality_df[
    [
        "year",
        "variable",
        "total_count",
        "missing_count",
        "missing_percent",
        "infinite_count",
    ]
].copy()

missing_path = (
    REPORT_DIR / "pre_monsoon_missing_values.csv"
)

missing_df.to_csv(missing_path, index=False)

print("Saved:", missing_path)

# ============================================================
# 9. SAVE METADATA RANGE VIOLATIONS
# ============================================================

range_df = quality_df[
    [
        "year",
        "variable",
        "valid_min_metadata",
        "valid_max_metadata",
        "below_valid_min",
        "above_valid_max",
        "outside_metadata_range",
        "outside_percent",
    ]
].copy()

range_path = (
    REPORT_DIR / "pre_monsoon_range_checks.csv"
)

range_df.to_csv(range_path, index=False)

print("Saved:", range_path)

# ============================================================
# 10. PRINT SUMMARY
# ============================================================

print("\n=== ANALYSIS SUMMARY ===")

print("Years processed:", len(yearly_df))
print("Variable-year records:", len(quality_df))

print("\nTop 10 variable-year combinations by missing %:")

print(
    quality_df[
        ["year", "variable", "missing_percent"]
    ]
    .sort_values("missing_percent", ascending=False)
    .head(10)
    .to_string(index=False)
)

print("\nTotal values outside metadata ranges:")
print(int(quality_df["outside_metadata_range"].sum()))

print("\nSUCCESS: PRE-MONSOON QUALITY ANALYSIS COMPLETED!")
