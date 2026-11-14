
from pathlib import Path
import re
import json
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]

CERES_DIR = ROOT / "data/interim/ceres_seasonal/post_monsoon"
IMD_DIR = ROOT / "raw_data/IMD_Rainfall"
RONI_FILE = ROOT / "raw_data/NOAA_RONI/RONI.ascii.txt"
DMI_FILE = ROOT / "raw_data/NOAA_DMI/dmi.had.long.csv"

QUALITY_DIR = ROOT / "reports/data_quality"
CLIMATE_DIR = ROOT / "data/interim/climate_indices"

for folder in [QUALITY_DIR, CLIMATE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

YEARS = range(2010, 2022)


def numeric_stats(data):
    values = np.asarray(data).ravel()
    finite = np.isfinite(values)

    valid = values[finite]
    missing = len(values) - len(valid)

    if len(valid) == 0:
        return {
            "total": len(values),
            "valid": 0,
            "missing": missing,
            "missing_pct": 100.0 if len(values) else np.nan,
            "min": np.nan,
            "max": np.nan,
            "mean": np.nan,
            "median": np.nan,
            "std": np.nan,
            "p01": np.nan,
            "p99": np.nan
        }

    return {
        "total": len(values),
        "valid": len(valid),
        "missing": missing,
        "missing_pct": missing / len(values) * 100,
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "mean": float(np.mean(valid)),
        "median": float(np.median(valid)),
        "std": float(np.std(valid)),
        "p01": float(np.percentile(valid, 1)),
        "p99": float(np.percentile(valid, 99))
    }


def inspect_netcdf(directory, dataset_name, expected_files):
    file_rows = []
    variable_rows = []

    for year in YEARS:
        matches = list(directory.glob(f"*{year}*.nc"))

        if len(matches) != 1:
            file_rows.append({
                "dataset": dataset_name,
                "year": year,
                "file": "",
                "status": "MISSING_OR_AMBIGUOUS",
                "details": f"Found {len(matches)} matching files"
            })
            continue

        path = matches[0]

        try:
            with xr.open_dataset(path) as ds:
                time_name = next(
                    (name for name in ds.coords if name.lower() == "time"),
                    None
                )

                time_count = (
                    ds.sizes.get(time_name, 0)
                    if time_name else np.nan
                )

                time_start = ""
                time_end = ""

                if time_name and time_count:
                    times = pd.to_datetime(ds[time_name].values)
                    time_start = str(times.min())
                    time_end = str(times.max())

                file_rows.append({
                    "dataset": dataset_name,
                    "year": year,
                    "file": str(path.relative_to(ROOT)),
                    "status": "OPENED",
                    "file_size_mb": round(path.stat().st_size / 1024**2, 3),
                    "dimensions": json.dumps(dict(ds.sizes)),
                    "time_count": time_count,
                    "time_start": time_start,
                    "time_end": time_end,
                    "variable_count": len(ds.data_vars)
                })

                for name, da in ds.data_vars.items():
                    if not np.issubdtype(da.dtype, np.number):
                        continue

                    stats = numeric_stats(da.values)

                    attrs = da.attrs
                    variable_rows.append({
                        "dataset": dataset_name,
                        "year": year,
                        "variable": name,
                        "dimensions": str(da.dims),
                        "dtype": str(da.dtype),
                        "units": attrs.get("units", ""),
                        "long_name": attrs.get("long_name", ""),
                        "valid_min_attribute": attrs.get("valid_min", ""),
                        "valid_max_attribute": attrs.get("valid_max", ""),
                        "fill_value_attribute": attrs.get("_FillValue", ""),
                        **stats
                    })

        except Exception as exc:
            file_rows.append({
                "dataset": dataset_name,
                "year": year,
                "file": str(path),
                "status": "ERROR",
                "details": str(exc)
            })

    file_df = pd.DataFrame(file_rows)
    variable_df = pd.DataFrame(variable_rows)

    file_df.to_csv(
        QUALITY_DIR / f"{dataset_name}_file_quality.csv",
        index=False
    )

    variable_df.to_csv(
        QUALITY_DIR / f"{dataset_name}_variable_quality.csv",
        index=False
    )

    return file_df, variable_df


def process_roni():
    rows = []

    with open(RONI_FILE, "r", encoding="utf-8") as file:
        for line in file:
            match = re.match(
                r"^\s*([A-Z]{3})\s+(\d{4})\s+([-+]?\d*\.?\d+)\s*$",
                line
            )

            if match:
                season, year, value = match.groups()
                year = int(year)

                if year in YEARS:
                    rows.append({
                        "season": season,
                        "year": year,
                        "roni_anomaly": float(value)
                    })

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("No RONI records found for 2010–2021.")

    df["duplicate"] = df.duplicated(
        subset=["year", "season"], keep=False
    )

    counts = df.groupby("year").size()

    summary = {
        "records": len(df),
        "years": df["year"].nunique(),
        "duplicate_records": int(df["duplicate"].sum()),
        "years_with_12_records": int((counts == 12).sum()),
        "missing_values": int(df["roni_anomaly"].isna().sum())
    }

    df.to_csv(CLIMATE_DIR / "roni_2010_2021.csv", index=False)

    return summary


def process_dmi():
    df = pd.read_csv(
        DMI_FILE,
        skiprows=1,
        header=None,
        names=["date", "dmi_anomaly"],
        skipinitialspace=True
    )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["dmi_anomaly"] = pd.to_numeric(
        df["dmi_anomaly"], errors="coerce"
    )

    df = df[df["date"].dt.year.between(2010, 2021)].copy()

    df.loc[df["dmi_anomaly"] == -9999, "dmi_anomaly"] = np.nan

    df["duplicate"] = df.duplicated(subset=["date"], keep=False)

    counts = df.groupby(df["date"].dt.year).size()

    summary = {
        "records": len(df),
        "years": df["date"].dt.year.nunique(),
        "duplicate_records": int(df["duplicate"].sum()),
        "years_with_12_records": int((counts == 12).sum()),
        "missing_values": int(df["dmi_anomaly"].isna().sum())
    }

    df.to_csv(CLIMATE_DIR / "dmi_2010_2021.csv", index=False)

    return summary


def main():
    print("\n========== CLIMATE INDEX AUDIT ==========")

    roni_summary = process_roni()
    dmi_summary = process_dmi()

    print("RONI:", roni_summary)
    print("DMI:", dmi_summary)

    print("\n========== POST-MONSOON CERES AUDIT ==========")

    ceres_files, ceres_variables = inspect_netcdf(
        CERES_DIR,
        "post_monsoon_ceres",
        12
    )

    print("CERES files:")
    print(ceres_files["status"].value_counts().to_dict())
    print("CERES variable entries:", len(ceres_variables))

    print("\n========== IMD RAINFALL AUDIT ==========")

    imd_files, imd_variables = inspect_netcdf(
        IMD_DIR,
        "imd_rainfall",
        12
    )

    print("IMD files:")
    print(imd_files["status"].value_counts().to_dict())
    print("IMD variable entries:", len(imd_variables))

    summary = {
        "roni": roni_summary,
        "dmi": dmi_summary,
        "ceres_files": len(ceres_files),
        "ceres_opened": int((ceres_files["status"] == "OPENED").sum()),
        "imd_files": len(imd_files),
        "imd_opened": int((imd_files["status"] == "OPENED").sum())
    }

    with open(QUALITY_DIR / "combined_audit_summary.json", "w") as f:
        json.dump(summary, f, indent=4)

    print("\n========== AUDIT COMPLETE ==========")
    print(json.dumps(summary, indent=4))
    print("\nReports saved in:", QUALITY_DIR)
    print("Climate CSV files saved in:", CLIMATE_DIR)


if __name__ == "__main__":
    main()
