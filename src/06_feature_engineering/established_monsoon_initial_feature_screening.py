from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(".")
DATA_DIR = ROOT / "data/processed/ceres_daily/established_monsoon"

SCRIPT_OUTPUT = ROOT / "src/06_feature_engineering"
TABLE_OUTPUT = ROOT / "results/tables/06_feature_engineering"
REPORT_OUTPUT = ROOT / "reports/06_feature_engineering"
METHOD_OUTPUT = ROOT / "docs/methodology"

SUMMARY_FILE = TABLE_OUTPUT / "established_monsoon_variable_screening.csv"
YEARLY_FILE = TABLE_OUTPUT / "established_monsoon_yearly_screening.csv"
REPORT_FILE = REPORT_OUTPUT / "established_monsoon_initial_feature_screening.md"
METHOD_FILE = METHOD_OUTPUT / "established_monsoon_initial_feature_screening.md"

YEARS = list(range(2010, 2022))
EXPECTED_VARIABLES = 45
EXPECTED_DAYS = 30
EXPECTED_LAT = 32
EXPECTED_LON = 30

def get_statistics(values):
    values = np.asarray(values, dtype=np.float64)
    finite = values[np.isfinite(values)]

    base = {
        "total_observations": int(values.size),
        "valid_observations": int(finite.size),
        "missing_observations": int(values.size - finite.size),
        "missing_percentage": float(
            100 * (values.size - finite.size) / values.size
        )
    }

    if finite.size == 0:
        return {
            **base,
            "minimum": np.nan,
            "maximum": np.nan,
            "mean": np.nan,
            "median": np.nan,
            "standard_deviation": np.nan,
            "percentile_01": np.nan,
            "percentile_05": np.nan,
            "percentile_25": np.nan,
            "percentile_75": np.nan,
            "percentile_95": np.nan,
            "percentile_99": np.nan,
            "interquartile_range": np.nan,
            "zero_count": 0,
            "zero_percentage": np.nan,
            "constant": False
        }

    q = np.percentile(finite, [1, 5, 25, 50, 75, 95, 99])

    return {
        **base,
        "total_observations": int(values.size),
        "valid_observations": int(finite.size),
        "missing_observations": int(values.size - finite.size),
        "missing_percentage": float(
            100 * (values.size - finite.size) / values.size
        ),
        "minimum": float(np.min(finite)),
        "maximum": float(np.max(finite)),
        "mean": float(np.mean(finite)),
        "median": float(q[3]),
        "standard_deviation": float(np.std(finite)),
        "percentile_01": float(q[0]),
        "percentile_05": float(q[1]),
        "percentile_25": float(q[2]),
        "percentile_75": float(q[4]),
        "percentile_95": float(q[5]),
        "percentile_99": float(q[6]),
        "interquartile_range": float(q[4] - q[2]),
        "zero_count": int(np.count_nonzero(finite == 0)),
        "zero_percentage": float(100 * np.mean(finite == 0)),
        "constant": bool(np.min(finite) == np.max(finite))
    }


def main():
    files = sorted(DATA_DIR.glob(
        "CERES_*_established_monsoon_daily.nc"
    ))

    if len(files) != len(YEARS):
        raise RuntimeError(
            f"Expected {len(YEARS)} annual files, found {len(files)}"
        )

    variable_values = {}
    yearly_records = []
    reference_variables = None
    reference_lat = None
    reference_lon = None
    reference_metadata = {}

    print("========== INITIAL FEATURE SCREENING ==========")

    for path in files:
        year = int(path.name.split("_")[1])

        if year not in YEARS:
            raise RuntimeError(f"Unexpected year: {year}")

        print(f"Processing {year}...")

        with xr.open_dataset(path) as ds:
            if dict(ds.sizes) != {
                "time": EXPECTED_DAYS,
                "lat": EXPECTED_LAT,
                "lon": EXPECTED_LON
            }:
                raise RuntimeError(
                    f"Unexpected dimensions in {path.name}: {dict(ds.sizes)}"
                )

            dates = ds["time"].values.astype("datetime64[D]")
            expected_dates = pd.date_range(
                f"{year}-07-15", periods=EXPECTED_DAYS
            ).values.astype("datetime64[D]")

            if not np.array_equal(dates, expected_dates):
                raise RuntimeError(f"Unexpected dates in {year}")

            physical = sorted(
                name for name in ds.data_vars
                if not name.endswith("_valid_hour_count")
            )

            diagnostics = [
                name for name in ds.data_vars
                if name.endswith("_valid_hour_count")
            ]

            if len(physical) != EXPECTED_VARIABLES:
                raise RuntimeError(
                    f"Expected 45 physical variables in {year}, "
                    f"found {len(physical)}"
                )

            if len(diagnostics) != EXPECTED_VARIABLES:
                raise RuntimeError(
                    f"Expected 45 diagnostic variables in {year}, "
                    f"found {len(diagnostics)}"
                )

            if reference_variables is None:
                reference_variables = physical
                reference_lat = ds["lat"].values.copy()
                reference_lon = ds["lon"].values.copy()

                for name in physical:
                    reference_metadata[name] = {
                        "units": ds[name].attrs.get("units"),
                        "valid_min": ds[name].attrs.get("valid_min"),
                        "valid_max": ds[name].attrs.get("valid_max")
                    }

                    variable_values[name] = []
            elif physical != reference_variables:
                raise RuntimeError(
                    f"Physical variable schema mismatch in {year}"
                )

            if not np.array_equal(ds["lat"].values, reference_lat):
                raise RuntimeError(f"Latitude grid mismatch in {year}")

            if not np.array_equal(ds["lon"].values, reference_lon):
                raise RuntimeError(f"Longitude grid mismatch in {year}")

            for name in reference_variables:
                variable = ds[name]

                if variable.dims != ("time", "lat", "lon"):
                    raise RuntimeError(
                        f"Unexpected dimensions for {name} in {year}"
                    )

                metadata = {
                    "units": variable.attrs.get("units"),
                    "valid_min": variable.attrs.get("valid_min"),
                    "valid_max": variable.attrs.get("valid_max")
                }

                if metadata != reference_metadata[name]:
                    raise RuntimeError(
                        f"Metadata mismatch for {name} in {year}"
                    )

                values = np.asarray(variable.values, dtype=np.float64)

                if np.isinf(values).any():
                    raise RuntimeError(
                        f"Infinite values found in {name}, {year}"
                    )

                finite = values[np.isfinite(values)]

                valid_min = float(metadata["valid_min"])
                valid_max = float(metadata["valid_max"])

                below = int(np.count_nonzero(finite < valid_min - 1e-6))
                above = int(np.count_nonzero(finite > valid_max + 1e-6))

                stats = get_statistics(values)

                yearly_records.append({
                    "year": year,
                    "variable": name,
                    **stats,
                    "below_declared_valid_min": below,
                    "above_declared_valid_max": above
                })

                variable_values[name].append(values.reshape(-1))

    if len(reference_variables) != EXPECTED_VARIABLES:
        raise RuntimeError("Final variable count validation failed")

    yearly = pd.DataFrame(yearly_records)

    if len(yearly) != EXPECTED_VARIABLES * len(YEARS):
        raise RuntimeError("Unexpected number of yearly records")

    summary_records = []

    for name in reference_variables:
        combined = np.concatenate(variable_values[name])
        stats = get_statistics(combined)

        yearly_subset = yearly[yearly["variable"] == name]

        metadata = reference_metadata[name]

        summary_records.append({
            "variable": name,
            "units": metadata["units"],
            "declared_valid_min": float(metadata["valid_min"]),
            "declared_valid_max": float(metadata["valid_max"]),
            **stats,
            "below_declared_valid_min": int(
                yearly_subset["below_declared_valid_min"].sum()
            ),
            "above_declared_valid_max": int(
                yearly_subset["above_declared_valid_max"].sum()
            ),
            "years_with_data": int(
                (yearly_subset["valid_observations"] > 0).sum()
            )
        })

    summary = pd.DataFrame(summary_records)

    if summary["variable"].nunique() != EXPECTED_VARIABLES:
        raise RuntimeError("Duplicate or missing physical variables")

    if summary["valid_observations"].sum() + \
       summary["missing_observations"].sum() != \
       EXPECTED_VARIABLES * len(YEARS) * EXPECTED_DAYS * \
       EXPECTED_LAT * EXPECTED_LON:
        raise RuntimeError("Observation accounting validation failed")

    if summary[
        ["below_declared_valid_min", "above_declared_valid_max"]
    ].to_numpy().sum() != 0:
        print("WARNING: Declared valid-range violations detected")

    if not np.isfinite(
        summary.select_dtypes(include="number").values
    ).all():
        raise RuntimeError("Non-finite values in summary")

    yearly_with_data = yearly[yearly["valid_observations"] > 0]

    distribution_columns = [
        "minimum", "maximum", "mean", "median",
        "standard_deviation", "percentile_01", "percentile_05",
        "percentile_25", "percentile_75", "percentile_95",
        "percentile_99", "interquartile_range"
    ]

    if not np.isfinite(
        yearly_with_data[distribution_columns].to_numpy(dtype=float)
    ).all():
        raise RuntimeError(
            "Non-finite distribution statistics in rows with valid data"
        )

    if (yearly["valid_observations"] == 0).any():
        empty_rows = yearly[yearly["valid_observations"] == 0]
        print(
            "\\nNOTE: Entirely missing variable-year combinations:",
            len(empty_rows)
        )
        print(
            empty_rows[["year", "variable", "missing_percentage"]]
            .to_string(index=False)
        )

    # Output files are written only after validation succeeds.
    for directory in [TABLE_OUTPUT, REPORT_OUTPUT, METHOD_OUTPUT]:
        directory.mkdir(parents=True, exist_ok=True)

    summary.to_csv(SUMMARY_FILE, index=False)
    yearly.to_csv(YEARLY_FILE, index=False)

    summary_sorted = summary.sort_values(
        "missing_percentage", ascending=False
    )

    high_missing = summary_sorted.head(10)

    constant_count = int(summary["constant"].sum())
    range_violations = int(
        summary[
            ["below_declared_valid_min", "above_declared_valid_max"]
        ].to_numpy().sum()
    )

    report = [
        "# Established Monsoon: Initial Feature Screening",
        "",
        "## Scope",
        "",
        "- Period: 2010–2021",
        "- Seasonal window: July 15–August 13",
        "- Years: 12",
        "- Physical CERES variables: 45",
        "- Spatial grid: 32 × 30",
        "- Daily observations per year: 30",
        "- Diagnostic valid-hour count variables excluded.",
        "- IMD rainfall excluded from clustering features.",
        "- Climate indices excluded from clustering features.",
        "",
        "## Method",
        "",
        "Statistics were calculated from all finite daily grid-cell observations",
        "for each physical CERES variable. Missing values were excluded from",
        "distribution statistics and retained in missingness counts.",
        "No imputation or zero replacement was performed.",
        "",
        "The daily variables are the existing arithmetic daily aggregates.",
        "Area-weighted phase alternatives were not substituted.",
        "",
        "## Overall validation",
        "",
        f"- Variable count: {len(summary)}",
        f"- Year-variable records: {len(yearly)}",
        f"- Total variable-day-grid observations: "
        f"{int(summary['total_observations'].sum()):,}",
        f"- Exact constant variables: {constant_count}",
        f"- Declared valid-range violations: {range_violations}",
        "",
        "## Ten variables with highest missingness",
        "",
        "| Variable | Missing (%) | Valid observations | Units |",
        "|---|---:|---:|---|"
    ]

    for _, row in high_missing.iterrows():
        report.append(
            f"| {row['variable']} | {row['missing_percentage']:.4f} "
            f"| {int(row['valid_observations']):,} | {row['units']} |"
        )

    report.extend([
        "",
        "## Interpretation cautions",
        "",
        "- Missingness alone does not establish scientific irrelevance.",
        "- A zero value is not automatically invalid.",
        "- Declared valid ranges are metadata checks, not proof of",
        "  scientific suitability.",
        "- Low variability must be evaluated in the context of each",
        "  variable's physical meaning and measurement scale.",
        "- Correlation and redundancy analysis will be conducted separately.",
        "- This is one season's screening evidence; final feature selection",
        "  must use a common feature set across all seasons.",
        "",
        "## Output files",
        "",
        f"- `{SUMMARY_FILE.as_posix()}`",
        f"- `{YEARLY_FILE.as_posix()}`",
        f"- `{REPORT_FILE.as_posix()}`",
        ""
    ])

    REPORT_FILE.write_text("\n".join(report), encoding="utf-8")

    methodology = [
        "# Methodology: Initial CERES Feature Screening",
        "",
        "## Objective",
        "",
        "Describe the statistical distributions and data completeness of",
        "the 45 physical CERES cloud variables before feature selection.",
        "",
        "## Data",
        "",
        "- CERES daily aggregates for 2010–2021.",
        "- July 15 through August 13 for each year.",
        "- 30 days × 32 latitude cells × 30 longitude cells per year.",
        "- 12 years and 45 physical variables.",
        "",
        "## Exclusions",
        "",
        "The `_valid_hour_count` variables are diagnostics and are not",
        "physical cloud features. Rainfall and climate indices are not",
        "included as clustering inputs.",
        "",
        "## Statistics",
        "",
        "For each variable, calculate valid and missing observation counts,",
        "missing percentage, minimum, maximum, mean, median, standard",
        "deviation, percentiles (1, 5, 25, 75, 95, 99), interquartile range,",
        "zero count, zero percentage and exact-constant status.",
        "",
        "The same statistics are calculated separately for each year.",
        "",
        "## Missing data and ranges",
        "",
        "Non-finite missing values are excluded from distribution statistics",
        "but included in missingness counts. No imputation or zero filling",
        "is performed. Observations are checked against the declared",
        "valid_min and valid_max metadata.",
        "",
        "## Interpretation",
        "",
        "This is descriptive screening, not final feature selection.",
        "No variable is automatically removed based on missingness,",
        "zero frequency, range, or variability. Correlation, redundancy,",
        "physical interpretation, and cross-season consistency are",
        "separate decision stages.",
        "",
        "## Aggregation",
        "",
        "The existing arithmetic daily aggregates are analysed. The",
        "area-weighted phase alternative remains a separate sensitivity",
        "question and is not substituted in this screening."
    ]

    METHOD_FILE.write_text(
        "\n".join(methodology) + "\n",
        encoding="utf-8"
    )

    print("\n========== SCREENING SUMMARY ==========")
    print("Physical variables:", len(summary))
    print("Year-variable records:", len(yearly))
    print("Total observations:", f"{int(summary['total_observations'].sum()):,}")
    print("Exact constant variables:", constant_count)
    print("Range violations:", range_violations)

    print("\n========== HIGHEST MISSINGNESS ==========")
    print(
        summary_sorted[
            ["variable", "missing_percentage", "valid_observations"]
        ].head(15).round(4).to_string(index=False)
    )

    print("\n========== OUTPUTS ==========")
    print(SUMMARY_FILE)
    print(YEARLY_FILE)
    print(REPORT_FILE)
    print(METHOD_FILE)

    print("\nInitial feature screening completed successfully.")


if __name__ == "__main__":
    main()
