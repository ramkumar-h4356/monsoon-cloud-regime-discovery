
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

# ==========================================
# 1. PATH CONFIGURATION
# ==========================================

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data/interim/ceres_seasonal/pre_monsoon"
OUT = ROOT / "reports/iwp_investigation"
OUT.mkdir(parents=True, exist_ok=True)

files = sorted(DATA_DIR.glob("*.nc"))
assert len(files) == 12, f"Expected 12 files, found {len(files)}"

# ==========================================
# 2. HELPERS
# ==========================================

def percentage(numerator, denominator):
    return 100 * numerator / denominator if denominator else np.nan

def metadata_value(value):
    if value is None:
        return ""
    return str(value)

def numeric_array(da):
    return np.asarray(da.values, dtype=np.float64)

def mask_for(da):
    return np.isfinite(numeric_array(da))

def variable_metadata(da):
    attrs = da.attrs
    encoding = da.encoding
    return {
        "units": metadata_value(attrs.get("units")),
        "long_name": metadata_value(attrs.get("long_name")),
        "standard_name": metadata_value(attrs.get("standard_name")),
        "valid_min": metadata_value(attrs.get("valid_min")),
        "valid_max": metadata_value(attrs.get("valid_max")),
        "fill_value": metadata_value(
            encoding.get("_FillValue", attrs.get("_FillValue"))
        ),
        "missing_value": metadata_value(
            encoding.get("missing_value", attrs.get("missing_value"))
        ),
        "dtype": str(da.dtype)
    }

def save_report(records, filename, columns):
    df = pd.DataFrame(records, columns=columns)
    path = OUT / filename
    df.to_csv(path, index=False)
    print("Saved:", path.name)
    return df

# ==========================================
# 3. REPORT STORAGE
# ==========================================

metadata_rows = []
availability_rows = []
condition_rows = []
hour_rows = []
spatial_rows = []
raw_rows = []
phase_rows = []

# ==========================================
# 4. PROCESS EACH YEAR
# ==========================================

for file in files:
    year = int(file.stem.split("_")[1])
    print(f"\nProcessing {year}: {file.name}")

    with xr.open_dataset(file, mask_and_scale=True) as ds:

        iwp_names = sorted(
            name for name in ds.data_vars
            if name.lower().startswith("iwp_")
        )

        lwp_names = sorted(
            name for name in ds.data_vars
            if name.lower().startswith("lwp_")
        )

        cloud_names = sorted(
            name for name in ds.data_vars
            if name.lower().startswith("cldarea_")
        )

        phase_names = sorted(
            name for name in ds.data_vars
            if "phase" in name.lower()
        )

        relevant = (
            iwp_names + lwp_names
            + cloud_names + phase_names
        )

        # ----------------------------------
        # CHECK A: METADATA
        # ----------------------------------

        for name in relevant:
            da = ds[name]
            metadata_rows.append({
                "year": year,
                "variable": name,
                **variable_metadata(da)
            })

        # ----------------------------------
        # CHECK B: VARIABLE AVAILABILITY
        # ----------------------------------

        for name in iwp_names + lwp_names:
            da = ds[name]
            values = numeric_array(da)
            valid = np.isfinite(values)
            count = values.size
            nvalid = int(valid.sum())
            nzero = int(np.count_nonzero(valid & (values == 0)))

            availability_rows.append({
                "year": year,
                "variable": name,
                "total_count": count,
                "valid_count": nvalid,
                "missing_count": count - nvalid,
                "missing_percent": percentage(count - nvalid, count),
                "zero_count": nzero,
                "zero_percent_among_valid": percentage(nzero, nvalid),
                "negative_count": int(
                    np.count_nonzero(valid & (values < 0))
                ),
                "mean_valid": float(np.mean(values[valid]))
                    if nvalid else np.nan,
                "median_valid": float(np.median(values[valid]))
                    if nvalid else np.nan
            })

        # ----------------------------------
        # CHECK C: CLOUD CONDITIONS
        # ----------------------------------

        if "cldarea_total_1h" in ds:
            cloud = ds["cldarea_total_1h"]

            for name in iwp_names:
                iwp = ds[name]
                if iwp.dims != cloud.dims:
                    continue

                cv = numeric_array(cloud)
                iv = numeric_array(iwp)
                missing = ~np.isfinite(iv)

                conditions = {
                    "clear_0_to_1": np.isfinite(cv) & (cv <= 1),
                    "partial_1_to_50": np.isfinite(cv) & (cv > 1) & (cv <= 50),
                    "cloudy_50_to_99": np.isfinite(cv) & (cv > 50) & (cv < 99),
                    "overcast_99_to_100": np.isfinite(cv) & (cv >= 99)
                }

                for label, mask in conditions.items():
                    total = int(mask.sum())
                    absent = int(np.count_nonzero(mask & missing))

                    condition_rows.append({
                        "year": year,
                        "variable": name,
                        "condition": label,
                        "sample_count": total,
                        "missing_count": absent,
                        "missing_percent": percentage(absent, total),
                        "valid_count": total - absent
                    })

        # ----------------------------------
        # CHECK D: HOURLY MISSINGNESS
        # ----------------------------------

        if "iwp_low_1h" in ds:
            da = ds["iwp_low_1h"]

            if "time" in da.dims:
                for hour in range(24):
                    subset = da.where(
                        da.time.dt.hour == hour,
                        drop=True
                    )
                    values = numeric_array(subset)
                    total = values.size
                    missing = int((~np.isfinite(values)).sum())

                    hour_rows.append({
                        "year": year,
                        "hour_utc": hour,
                        "total_count": total,
                        "missing_percent": percentage(missing, total),
                        "valid_count": total - missing
                    })

        # ----------------------------------
        # CHECK E: SPATIAL MISSINGNESS
        # ----------------------------------

        if "iwp_low_1h" in ds:
            da = ds["iwp_low_1h"]

            if all(d in da.dims for d in ("time", "lat", "lon")):
                missing_grid = da.isnull().mean(dim="time") * 100

                for lat in missing_grid.lat.values:
                    for lon in missing_grid.lon.values:
                        value = missing_grid.sel(lat=lat, lon=lon)
                        spatial_rows.append({
                            "year": year,
                            "lat": float(lat),
                            "lon": float(lon),
                            "missing_percent": float(value.values)
                        })

        # ----------------------------------
        # CHECK F: PHASE INDICATORS
        # ----------------------------------

        for name in phase_names:
            da = ds[name]
            vals = numeric_array(da)
            valid = np.isfinite(vals)

            phase_rows.append({
                "year": year,
                "phase_variable": name,
                "units": metadata_value(da.attrs.get("units")),
                "long_name": metadata_value(da.attrs.get("long_name")),
                "valid_count": int(valid.sum()),
                "missing_percent": percentage(
                    int((~valid).sum()), vals.size
                ),
                "min_valid": float(vals[valid].min())
                    if valid.any() else np.nan,
                "max_valid": float(vals[valid].max())
                    if valid.any() else np.nan
            })

    # --------------------------------------
    # CHECK G: RAW FILL VALUES
    # --------------------------------------

    with xr.open_dataset(
        file, decode_cf=False, mask_and_scale=False
    ) as raw_ds:

        for name in iwp_names:
            raw_da = raw_ds[name]
            raw_values = np.asarray(raw_da.values)
            raw_attrs = raw_da.attrs

            fill = raw_attrs.get("_FillValue")
            missing_attr = raw_attrs.get("missing_value")

            fill_count = 0
            missing_attr_count = 0

            if fill is not None:
                for marker in np.atleast_1d(fill):
                    fill_count += int(
                        np.count_nonzero(raw_values == marker)
                    )

            if missing_attr is not None:
                for marker in np.atleast_1d(missing_attr):
                    missing_attr_count += int(
                        np.count_nonzero(raw_values == marker)
                    )

            raw_rows.append({
                "year": year,
                "variable": name,
                "raw_dtype": str(raw_da.dtype),
                "fill_value": metadata_value(fill),
                "fill_count": fill_count,
                "missing_value_attribute": metadata_value(missing_attr),
                "missing_attribute_count": missing_attr_count,
                "raw_nan_count": int(
                    np.count_nonzero(
                        ~np.isfinite(raw_values.astype(float))
                    )
                )
            })

    print(f"Completed {year}")

# ==========================================
# 5. SAVE CSV REPORTS
# ==========================================

metadata_df = save_report(
    metadata_rows,
    "01_iwp_metadata.csv",
    ["year", "variable", "units", "long_name",
     "standard_name", "valid_min", "valid_max",
     "fill_value", "missing_value", "dtype"]
)

availability_df = save_report(
    availability_rows,
    "02_iwp_lwp_availability.csv",
    ["year", "variable", "total_count", "valid_count",
     "missing_count", "missing_percent", "zero_count",
     "zero_percent_among_valid", "negative_count",
     "mean_valid", "median_valid"]
)

conditions_df = save_report(
    condition_rows,
    "03_iwp_by_cloud_condition.csv",
    ["year", "variable", "condition", "sample_count",
     "missing_count", "missing_percent", "valid_count"]
)

hourly_df = save_report(
    hour_rows,
    "04_iwp_hourly_missingness.csv",
    ["year", "hour_utc", "total_count",
     "missing_percent", "valid_count"]
)

spatial_df = save_report(
    spatial_rows,
    "05_iwp_spatial_missingness.csv",
    ["year", "lat", "lon", "missing_percent"]
)

raw_df = save_report(
    raw_rows,
    "06_iwp_raw_fill_values.csv",
    ["year", "variable", "raw_dtype", "fill_value",
     "fill_count", "missing_value_attribute",
     "missing_attribute_count", "raw_nan_count"]
)

phase_df = save_report(
    phase_rows,
    "07_cloud_phase_inventory.csv",
    ["year", "phase_variable", "units", "long_name",
     "valid_count", "missing_percent",
     "min_valid", "max_valid"]
)

# ==========================================
# 6. SUMMARY REPORT
# ==========================================

summary = (
    availability_df.groupby("variable", as_index=False)
    .agg(
        total_count=("total_count", "sum"),
        valid_count=("valid_count", "sum"),
        missing_count=("missing_count", "sum"),
        zero_count=("zero_count", "sum")
    )
)

summary["missing_percent"] = (
    100 * summary["missing_count"] / summary["total_count"]
)

summary["zero_percent_among_valid"] = (
    100 * summary["zero_count"]
    / summary["valid_count"].replace(0, np.nan)
)

summary.to_csv(
    OUT / "08_overall_iwp_summary.csv",
    index=False
)

print("\n=== OVERALL IWP/LWP SUMMARY ===")
print(summary.to_string(index=False))

print("\n=== IWP LOW: CLOUD CONDITIONS ===")
print(
    conditions_df[
        conditions_df["variable"] == "iwp_low_1h"
    ].groupby("condition")[["sample_count", "missing_count"]]
     .sum()
     .assign(
         missing_percent=lambda x:
         100 * x["missing_count"] / x["sample_count"]
     ).to_string()
)

print("\nPhase variables discovered:",
      sorted(phase_df["phase_variable"].unique())
      if not phase_df.empty else "None")

print("\nSUCCESS: IWP INVESTIGATION COMPLETED")
print("Reports saved to:", OUT)
