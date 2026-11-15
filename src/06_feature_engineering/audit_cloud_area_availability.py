
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data" / "interim" / "ceres_seasonal"
OUTPUT_DIR = ROOT / "reports" / "data_quality"

EXPECTED_SEASONS = {
    "pre_monsoon",
    "established_monsoon",
    "post_monsoon",
}

CLOUD_AREA_VARIABLES = [
    "cldarea_high_1h",
    "cldarea_mid_high_1h",
    "cldarea_mid_low_1h",
    "cldarea_low_1h",
    "cldarea_total_1h",
]

EXPECTED_DATASETS = 36


def extract_year(filename):
    match = re.search(r"CERES_(\d{4})_", filename)
    return int(match.group(1)) if match else None


def audit_variable(data_array, variable, year, season, file_path):
    values = np.asarray(data_array.values, dtype=np.float64)

    total = int(values.size)
    finite_mask = np.isfinite(values)
    finite_values = values[finite_mask]

    finite_count = int(finite_mask.sum())
    missing_count = total - finite_count

    zero_count = int(np.count_nonzero(finite_values == 0))
    positive_count = int(np.count_nonzero(finite_values > 0))
    negative_count = int(np.count_nonzero(finite_values < 0))

    return {
        "year": year,
        "season": season,
        "variable": variable,
        "file": file_path.name,
        "status": "present",
        "dimensions": str(dict(data_array.sizes)),
        "total_values": total,
        "finite_values": finite_count,
        "missing_values": missing_count,
        "missing_pct": (
            100 * missing_count / total if total else None
        ),
        "zero_area_values": zero_count,
        "zero_pct_of_finite": (
            100 * zero_count / finite_count if finite_count else None
        ),
        "positive_area_values": positive_count,
        "positive_pct_of_finite": (
            100 * positive_count / finite_count
            if finite_count else None
        ),
        "negative_area_values": negative_count,
        "minimum": (
            float(finite_values.min()) if finite_count else None
        ),
        "maximum": (
            float(finite_values.max()) if finite_count else None
        ),
        "mean": (
            float(finite_values.mean()) if finite_count else None
        ),
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(DATA_DIR.glob("*/*.nc"))

    if not files:
        raise FileNotFoundError(
            f"No NetCDF files found under {DATA_DIR}"
        )

    records = []
    dataset_inventory = []
    errors = []

    seen_dataset_keys = set()

    for file_path in files:
        season = file_path.parent.name
        year = extract_year(file_path.name)

        if year is None:
            errors.append(f"Could not extract year: {file_path}")
            continue

        dataset_key = (year, season)

        if dataset_key in seen_dataset_keys:
            errors.append(
                f"Duplicate dataset for year={year}, season={season}"
            )
        seen_dataset_keys.add(dataset_key)

        inventory = {
            "year": year,
            "season": season,
            "file": file_path.name,
            "time_count": None,
            "variables_present": [],
            "variables_missing": [],
            "status": "review",
        }

        try:
            with xr.open_dataset(file_path) as ds:
                inventory["time_count"] = int(
                    ds.sizes.get("time", 0)
                )

                for variable in CLOUD_AREA_VARIABLES:
                    if variable not in ds.variables:
                        inventory["variables_missing"].append(variable)
                        records.append({
                            "year": year,
                            "season": season,
                            "variable": variable,
                            "file": file_path.name,
                            "status": "missing_variable",
                            "dimensions": None,
                            "total_values": 0,
                            "finite_values": 0,
                            "missing_values": None,
                            "missing_pct": None,
                            "zero_area_values": None,
                            "zero_pct_of_finite": None,
                            "positive_area_values": None,
                            "positive_pct_of_finite": None,
                            "negative_area_values": None,
                            "minimum": None,
                            "maximum": None,
                            "mean": None,
                        })
                        continue

                    inventory["variables_present"].append(variable)

                    records.append(
                        audit_variable(
                            ds[variable],
                            variable,
                            year,
                            season,
                            file_path,
                        )
                    )

                inventory["status"] = (
                    "pass"
                    if not inventory["variables_missing"]
                    else "review"
                )

        except Exception as exc:
            inventory["status"] = "error"
            errors.append(f"{file_path}: {exc}")

        dataset_inventory.append(inventory)

    detail = pd.DataFrame(records)
    inventory_df = pd.DataFrame(dataset_inventory)

    present = detail[detail["status"] == "present"].copy()

    summary = (
        present.groupby(["season", "variable"], as_index=False)
        .agg(
            datasets=("file", "nunique"),
            total_values=("total_values", "sum"),
            finite_values=("finite_values", "sum"),
            missing_values=("missing_values", "sum"),
            zero_area_values=("zero_area_values", "sum"),
            positive_area_values=("positive_area_values", "sum"),
            negative_area_values=("negative_area_values", "sum"),
        )
    )

    summary["missing_pct"] = (
        100 * summary["missing_values"] / summary["total_values"]
    )

    summary["zero_pct_of_finite"] = np.where(
        summary["finite_values"] > 0,
        100 * summary["zero_area_values"] / summary["finite_values"],
        np.nan,
    )

    summary["positive_pct_of_finite"] = np.where(
        summary["finite_values"] > 0,
        100 * summary["positive_area_values"] / summary["finite_values"],
        np.nan,
    )

    overall = (
        present.groupby("variable", as_index=False)
        .agg(
            datasets=("file", "nunique"),
            total_values=("total_values", "sum"),
            finite_values=("finite_values", "sum"),
            missing_values=("missing_values", "sum"),
            zero_area_values=("zero_area_values", "sum"),
            positive_area_values=("positive_area_values", "sum"),
            negative_area_values=("negative_area_values", "sum"),
        )
    )

    overall["missing_pct"] = (
        100 * overall["missing_values"] / overall["total_values"]
    )

    overall["zero_pct_of_finite"] = np.where(
        overall["finite_values"] > 0,
        100 * overall["zero_area_values"] / overall["finite_values"],
        np.nan,
    )

    overall["positive_pct_of_finite"] = np.where(
        overall["finite_values"] > 0,
        100 * overall["positive_area_values"] / overall["finite_values"],
        np.nan,
    )

    expected_combinations = {
        (year, season)
        for year in range(2010, 2022)
        for season in EXPECTED_SEASONS
    }

    observed_combinations = set(seen_dataset_keys)

    missing_combinations = sorted(
        expected_combinations - observed_combinations
    )
    unexpected_combinations = sorted(
        observed_combinations - expected_combinations
    )

    validation = {
        "expected_dataset_count": EXPECTED_DATASETS,
        "observed_dataset_count": len(files),
        "unique_dataset_count": len(seen_dataset_keys),
        "expected_years": list(range(2010, 2022)),
        "expected_seasons": sorted(EXPECTED_SEASONS),
        "missing_year_season_combinations": [
            {"year": year, "season": season}
            for year, season in missing_combinations
        ],
        "unexpected_year_season_combinations": [
            {"year": year, "season": season}
            for year, season in unexpected_combinations
        ],
        "datasets_with_review_status": int(
            (inventory_df["status"] == "review").sum()
        ) if not inventory_df.empty else 0,
        "datasets_with_error_status": int(
            (inventory_df["status"] == "error").sum()
        ) if not inventory_df.empty else 0,
        "missing_cloud_area_variables": int(
            (detail["status"] == "missing_variable").sum()
        ) if not detail.empty else 0,
        "errors": errors,
    }

    validation["overall_status"] = (
        "pass"
        if (
            len(files) == EXPECTED_DATASETS
            and len(seen_dataset_keys) == EXPECTED_DATASETS
            and not missing_combinations
            and not unexpected_combinations
            and validation["datasets_with_review_status"] == 0
            and validation["datasets_with_error_status"] == 0
            and validation["missing_cloud_area_variables"] == 0
            and not errors
        )
        else "review"
    )

    detail.to_csv(
        OUTPUT_DIR / "cloud_area_availability_by_dataset.csv",
        index=False,
    )

    summary.to_csv(
        OUTPUT_DIR / "cloud_area_availability_by_season.csv",
        index=False,
    )

    overall.to_csv(
        OUTPUT_DIR / "cloud_area_availability_overall.csv",
        index=False,
    )

    inventory_df.to_csv(
        OUTPUT_DIR / "cloud_area_dataset_inventory.csv",
        index=False,
    )

    with open(
        OUTPUT_DIR / "cloud_area_availability_audit.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {
                "validation": validation,
                "overall_summary": overall.to_dict(orient="records"),
                "season_summary": summary.to_dict(orient="records"),
            },
            file,
            indent=2,
            allow_nan=False,
            default=str,
        )

    print("\n========== M18.2 CLOUD-AREA AUDIT ==========")
    print(f"Files discovered: {len(files)}")
    print(f"Dataset combinations: {len(seen_dataset_keys)}")
    print(f"Audit records: {len(detail)}")
    print(f"Validation: {validation['overall_status']}")
    print("\nOverall cloud-area summary:")
    print(overall.to_string(index=False))
    print(f"\nReports saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
