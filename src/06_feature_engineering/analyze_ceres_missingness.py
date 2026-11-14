
from pathlib import Path
import json

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]

SEASON_DIRS = {
    "pre_monsoon": ROOT / "data/interim/ceres_seasonal/pre_monsoon",
    "established_monsoon": ROOT / "data/interim/ceres_seasonal/established_monsoon",
    "post_monsoon": ROOT / "data/interim/ceres_seasonal/post_monsoon",
}

SCREENING_FILE = (
    ROOT / "reports/data_quality/ceres_feature_screening_summary.csv"
)

OUTPUT_DIR = ROOT / "reports/data_quality"

YEARS = range(2010, 2022)
EXPECTED_DIMS = ("time", "lat", "lon")
EXPECTED_SHAPE = (720, 32, 30)

# A cloud-area variable is used only as a diagnostic comparator.
# This does not treat cloud area as a definitive retrieval-quality flag.
AREA_PREFIX = "cldarea_"
VARIABLE_SUFFIX = "_1h"


def find_column(dataframe, candidates):
    lookup = {column.lower(): column for column in dataframe.columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    raise ValueError(
        f"Could not find any of {candidates}. "
        f"Available columns: {list(dataframe.columns)}"
    )


def load_eligible_variables():
    screening = pd.read_csv(SCREENING_FILE)

    variable_column = find_column(
        screening,
        ["variable", "variable_name", "short_name"],
    )

    status_column = find_column(
        screening,
        ["status", "screening_status"],
    )

    variables = screening.loc[
        screening[status_column].astype(str).str.upper()
        == "ELIGIBLE_CANDIDATE",
        variable_column,
    ].dropna().astype(str).unique().tolist()

    if len(variables) != 36:
        raise ValueError(
            f"Expected 36 eligible candidates, found {len(variables)}. "
            "Review the screening report before continuing."
        )

    return sorted(variables)


def matching_area_variable(variable, available_variables):
    if variable.startswith(AREA_PREFIX):
        return None

    if not variable.endswith(VARIABLE_SUFFIX):
        return None

    stem = variable[:-len(VARIABLE_SUFFIX)]

    if "_" not in stem:
        return None

    layer = stem.split("_", 1)[1]
    candidate = f"cldarea_{layer}_1h"

    return candidate if candidate in available_variables else None


def safe_correlation(x, y):
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return None

    value = np.corrcoef(x, y)[0, 1]

    return float(value) if np.isfinite(value) else None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    variables = load_eligible_variables()
    variable_set = set(variables)

    print("=" * 70)
    print("CERES MISSINGNESS AND RETRIEVAL-PATTERN INVESTIGATION")
    print("=" * 70)
    print(f"Variables: {len(variables)}")
    print(f"Years: {len(YEARS)}")
    print(f"Seasons: {len(SEASON_DIRS)}")
    print(f"Expected seasonal datasets: {len(YEARS) * len(SEASON_DIRS)}")

    dataset_records = []
    area_association_records = []

    spatial_counts = {}
    hourly_counts = {}
    variable_metadata = {}

    latitude = None
    longitude = None

    for season, directory in SEASON_DIRS.items():
        print(f"\nProcessing {season}")

        for year in YEARS:
            filename = f"CERES_{year}_{season}.nc"
            path = directory / filename

            if not path.exists():
                raise FileNotFoundError(f"Missing dataset: {path}")

            print(f"  {filename}")

            with xr.open_dataset(
                path,
                decode_cf=True,
                mask_and_scale=True,
            ) as dataset:

                if tuple(dataset.sizes[d] for d in EXPECTED_DIMS) != EXPECTED_SHAPE:
                    raise ValueError(
                        f"Unexpected dimensions in {path}: "
                        f"{dict(dataset.sizes)}"
                    )

                if latitude is None:
                    latitude = np.asarray(
                        dataset["lat"].values,
                        dtype=float,
                    )
                    longitude = np.asarray(
                        dataset["lon"].values,
                        dtype=float,
                    )
                else:
                    if not np.array_equal(
                        latitude,
                        np.asarray(dataset["lat"].values, dtype=float),
                    ):
                        raise ValueError(
                            f"Latitude coordinates differ in {path}"
                        )

                    if not np.array_equal(
                        longitude,
                        np.asarray(dataset["lon"].values, dtype=float),
                    ):
                        raise ValueError(
                            f"Longitude coordinates differ in {path}"
                        )

                for variable in variables:
                    if variable not in dataset.variables:
                        raise ValueError(
                            f"{variable} missing from {path}"
                        )

                for variable in variables:
                    data_array = dataset[variable]

                    if tuple(data_array.dims) != EXPECTED_DIMS:
                        raise ValueError(
                            f"Unexpected dimensions for {variable} "
                            f"in {path}: {data_array.dims}"
                        )

                    values = np.asarray(
                        data_array.values,
                        dtype=np.float64,
                    )

                    finite = np.isfinite(values)
                    missing = ~finite

                    total_count = int(values.size)
                    missing_count = int(missing.sum())
                    finite_count = int(finite.sum())
                    zero_count = int(
                        np.count_nonzero(finite & (values == 0))
                    )

                    finite_values = values[finite]

                    if finite_count:
                        minimum = float(finite_values.min())
                        maximum = float(finite_values.max())
                        mean = float(finite_values.mean())
                        std = float(finite_values.std())
                    else:
                        minimum = maximum = mean = std = None

                    attrs = data_array.attrs

                    metadata_key = variable

                    if metadata_key not in variable_metadata:
                        variable_metadata[metadata_key] = {
                            "variable": variable,
                            "long_name": attrs.get("long_name"),
                            "units": attrs.get("units"),
                            "valid_min": attrs.get("valid_min"),
                            "valid_max": attrs.get("valid_max"),
                        }

                    dataset_records.append({
                        "season": season,
                        "year": year,
                        "variable": variable,
                        "total_observations": total_count,
                        "finite_observations": finite_count,
                        "missing_observations": missing_count,
                        "missing_fraction": (
                            missing_count / total_count
                        ),
                        "zero_observations": zero_count,
                        "zero_fraction_of_finite": (
                            zero_count / finite_count
                            if finite_count else None
                        ),
                        "minimum_finite_value": minimum,
                        "maximum_finite_value": maximum,
                        "mean_finite_value": mean,
                        "std_finite_value": std,
                    })

                    key = (season, variable)

                    if key not in spatial_counts:
                        spatial_counts[key] = {
                            "missing": np.zeros(
                                EXPECTED_SHAPE[1:],
                                dtype=np.int64,
                            ),
                            "total": np.zeros(
                                EXPECTED_SHAPE[1:],
                                dtype=np.int64,
                            ),
                        }

                    spatial_counts[key]["missing"] += missing.sum(axis=0)
                    spatial_counts[key]["total"] += missing.shape[0]

                    if key not in hourly_counts:
                        hourly_counts[key] = {
                            "missing": np.zeros(24, dtype=np.int64),
                            "total": np.zeros(24, dtype=np.int64),
                        }

                    for hour_slot in range(24):
                        hour_missing = missing[hour_slot::24]

                        hourly_counts[key]["missing"][hour_slot] += (
                            hour_missing.sum()
                        )
                        hourly_counts[key]["total"][hour_slot] += (
                            hour_missing.size
                        )

                    area_variable = matching_area_variable(
                        variable,
                        variable_set,
                    )

                    if area_variable is not None:
                        area_values = np.asarray(
                            dataset[area_variable].values,
                            dtype=np.float64,
                        )

                        area_finite = np.isfinite(area_values)
                        paired = area_finite

                        paired_area = area_values[paired]
                        paired_missing = missing[paired].astype(np.float64)

                        area_zero = paired_area == 0
                        area_positive = paired_area > 0

                        missing_rate_zero = (
                            float(paired_missing[area_zero].mean())
                            if area_zero.any() else None
                        )

                        missing_rate_positive = (
                            float(paired_missing[area_positive].mean())
                            if area_positive.any() else None
                        )

                        missing_area_mean = (
                            float(paired_area[paired_missing == 1].mean())
                            if np.any(paired_missing == 1) else None
                        )

                        observed_area_mean = (
                            float(paired_area[paired_missing == 0].mean())
                            if np.any(paired_missing == 0) else None
                        )

                        association = safe_correlation(
                            paired_missing,
                            paired_area,
                        )

                        area_association_records.append({
                            "season": season,
                            "year": year,
                            "variable": variable,
                            "comparison_area_variable": area_variable,
                            "paired_observations": int(paired.sum()),
                            "missing_rate_when_area_zero": missing_rate_zero,
                            "missing_rate_when_area_positive": missing_rate_positive,
                            "mean_area_when_target_missing": missing_area_mean,
                            "mean_area_when_target_observed": observed_area_mean,
                            "pearson_correlation_missing_indicator_vs_area": (
                                association
                            ),
                        })

            print(f"    Completed {len(variables)} variables")

    dataset_df = pd.DataFrame(dataset_records)
    area_df = pd.DataFrame(area_association_records)

    dataset_path = (
        OUTPUT_DIR / "ceres_missingness_by_dataset.csv"
    )
    dataset_df.to_csv(dataset_path, index=False)

    # Variable summaries are weighted by the number of observations,
    # rather than taking an unweighted mean of file-level percentages.
    grouped = (
        dataset_df.groupby(["season", "variable"], as_index=False)
        .agg(
            total_observations=("total_observations", "sum"),
            finite_observations=("finite_observations", "sum"),
            missing_observations=("missing_observations", "sum"),
            zero_observations=("zero_observations", "sum"),
        )
    )

    grouped["missing_fraction"] = (
        grouped["missing_observations"]
        / grouped["total_observations"]
    )

    grouped["zero_fraction_of_finite"] = (
        grouped["zero_observations"]
        / grouped["finite_observations"].replace(0, np.nan)
    )

    overall = (
        dataset_df.groupby("variable", as_index=False)
        .agg(
            total_observations=("total_observations", "sum"),
            finite_observations=("finite_observations", "sum"),
            missing_observations=("missing_observations", "sum"),
            zero_observations=("zero_observations", "sum"),
        )
    )

    overall["season"] = "all_seasons"
    overall["missing_fraction"] = (
        overall["missing_observations"]
        / overall["total_observations"]
    )
    overall["zero_fraction_of_finite"] = (
        overall["zero_observations"]
        / overall["finite_observations"].replace(0, np.nan)
    )

    variable_summary = pd.concat(
        [grouped, overall],
        ignore_index=True,
    )

    variable_summary = variable_summary.merge(
        pd.DataFrame(variable_metadata.values()),
        on="variable",
        how="left",
    )

    variable_summary_path = (
        OUTPUT_DIR / "ceres_missingness_variable_summary.csv"
    )
    variable_summary.to_csv(variable_summary_path, index=False)

    # Spatial missingness: each cell's rate pooled across all 12 years
    # within each season.
    spatial_records = []

    for (season, variable), counts in spatial_counts.items():
        rates = (
            counts["missing"] / counts["total"]
        )

        for lat_index, lat in enumerate(latitude):
            for lon_index, lon in enumerate(longitude):
                spatial_records.append({
                    "season": season,
                    "variable": variable,
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "missing_observations": int(
                        counts["missing"][lat_index, lon_index]
                    ),
                    "total_observations": int(
                        counts["total"][lat_index, lon_index]
                    ),
                    "missing_fraction": float(
                        rates[lat_index, lon_index]
                    ),
                })

    spatial_df = pd.DataFrame(spatial_records)
    spatial_path = (
        OUTPUT_DIR / "ceres_missingness_spatial_by_season.csv"
    )
    spatial_df.to_csv(spatial_path, index=False)

    # Hour-of-day missingness, based on the 24 hourly positions
    # in each 720-observation seasonal file.
    hourly_records = []

    for (season, variable), counts in hourly_counts.items():
        for hour_slot in range(24):
            total = int(counts["total"][hour_slot])
            missing = int(counts["missing"][hour_slot])

            hourly_records.append({
                "season": season,
                "variable": variable,
                "hour_slot_from_file_start": hour_slot,
                "missing_observations": missing,
                "total_observations": total,
                "missing_fraction": (
                    missing / total if total else None
                ),
            })

    hourly_df = pd.DataFrame(hourly_records)
    hourly_path = (
        OUTPUT_DIR / "ceres_missingness_hourly_by_season.csv"
    )
    hourly_df.to_csv(hourly_path, index=False)

    area_path = (
        OUTPUT_DIR / "ceres_missingness_area_association.csv"
    )
    area_df.to_csv(area_path, index=False)

    # Summary statistics
    overall_summary = variable_summary[
        variable_summary["season"] == "all_seasons"
    ]

    summary = {
        "analysis": "CERES missingness and retrieval-pattern investigation",
        "years": list(YEARS),
        "seasons": list(SEASON_DIRS.keys()),
        "eligible_variable_count": len(variables),
        "dataset_count": len(SEASON_DIRS) * len(YEARS),
        "expected_dimensions": list(EXPECTED_DIMS),
        "expected_shape": list(EXPECTED_SHAPE),
        "missing_definition": "Non-finite values after xarray CF decoding and mask/scale handling",
        "zero_definition": "Exact numerical zero among finite observations",
        "spatial_analysis": "Per-grid-cell missing fraction pooled across years within each season",
        "hourly_analysis": "24 within-file time-index slots, pooled across days and years within each season",
        "area_association": (
            "Compares target-variable missingness with matching-layer "
            "cloud-area fraction. This is a diagnostic association, "
            "not a retrieval-quality test or causal conclusion."
        ),
        "overall_missingness": {
            "minimum_variable_missing_fraction": float(
                overall_summary["missing_fraction"].min()
            ),
            "maximum_variable_missing_fraction": float(
                overall_summary["missing_fraction"].max()
            ),
            "variables_over_50_percent_missing": (
                overall_summary.loc[
                    overall_summary["missing_fraction"] > 0.50,
                    "variable",
                ].tolist()
            ),
            "variables_over_75_percent_missing": (
                overall_summary.loc[
                    overall_summary["missing_fraction"] > 0.75,
                    "variable",
                ].tolist()
            ),
        },
        "interpretation_limitations": [
            "Missingness patterns do not by themselves identify the reason for a missing retrieval.",
            "Cloud-area fraction is a diagnostic comparator, not a substitute for CERES quality flags.",
            "An exact zero is counted separately from missingness and is not automatically assumed to mean clear sky.",
            "The 24 time slots are indexed from the start of each seasonal file; they are not converted to local solar time.",
            "No imputation, interpolation, filtering, or modification of source data was performed.",
            "Missingness associations do not establish causal relationships."
        ],
        "output_files": [
            dataset_path.name,
            variable_summary_path.name,
            spatial_path.name,
            hourly_path.name,
            area_path.name,
        ],
    }

    summary_path = (
        OUTPUT_DIR / "ceres_missingness_summary.json"
    )

    with open(summary_path, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print("\n" + "=" * 70)
    print("MISSINGNESS INVESTIGATION COMPLETED")
    print("=" * 70)
    print(f"Dataset-variable records: {len(dataset_df):,}")
    print(f"Variable summary records: {len(variable_summary):,}")
    print(f"Spatial records: {len(spatial_df):,}")
    print(f"Hourly records: {len(hourly_df):,}")
    print(f"Area-association records: {len(area_df):,}")
    print(f"Reports saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
