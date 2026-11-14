
from pathlib import Path
import re
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data/interim/ceres_extracted/established_monsoon"
TABLE_DIR = ROOT / "results/tables/established_monsoon_v3"
LOG_DIR = ROOT / "reports/data_quality"

EXPECTED_YEARS = list(range(2010, 2022))
EXPECTED_FILES = {
    f"CERES_{year}_established_monsoon.nc"
    for year in EXPECTED_YEARS
}

OUTPUTS = [
    TABLE_DIR / "variable_quality_by_year_v3.csv",
    TABLE_DIR / "variable_quality_summary_v3.csv",
    TABLE_DIR / "time_coordinate_quality_v3.csv",
    LOG_DIR / "established_monsoon_scientific_qc_log_v3.txt",
]


def get_fill_information(raw_variable, raw_values):
    attributes = raw_variable.attrs
    candidates = []

    for key in ("_FillValue", "missing_value"):
        if key in attributes:
            values = np.asarray(attributes[key]).ravel()
            for value in values:
                try:
                    candidates.append((key, float(value)))
                except (TypeError, ValueError):
                    pass

    fill_nan_declared = any(
        np.isnan(value) for _, value in candidates
    )

    numeric_sentinels = {
        value
        for _, value in candidates
        if np.isfinite(value)
    }

    raw_nan_count = int(np.isnan(raw_values).sum())

    raw_fill_nan_count = (
        raw_nan_count if fill_nan_declared else 0
    )

    raw_numeric_fill_count = sum(
        int(np.count_nonzero(raw_values == value))
        for value in numeric_sentinels
    )

    description = "; ".join(
        f"{key}={value}" for key, value in candidates
    )

    return (
        description,
        raw_nan_count,
        raw_fill_nan_count,
        raw_numeric_fill_count,
    )


def calculate_statistics(values):
    finite = values[np.isfinite(values)]

    if not finite.size:
        return {
            key: np.nan
            for key in [
                "minimum", "maximum", "mean", "median",
                "std_dev", "p05", "p25", "p75", "p95"
            ]
        }

    return {
        "minimum": float(np.min(finite)),
        "maximum": float(np.max(finite)),
        "mean": float(np.mean(finite)),
        "median": float(np.median(finite)),
        "std_dev": float(np.std(finite)),
        "p05": float(np.percentile(finite, 5)),
        "p25": float(np.percentile(finite, 25)),
        "p75": float(np.percentile(finite, 75)),
        "p95": float(np.percentile(finite, 95)),
    }


def main():
    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Dataset directory not found: {DATA_DIR}"
        )

    files = sorted(DATA_DIR.glob("*.nc"))

    actual_names = {path.name for path in files}
    missing_files = sorted(EXPECTED_FILES - actual_names)
    unexpected_files = sorted(actual_names - EXPECTED_FILES)

    if missing_files or unexpected_files:
        raise ValueError(
            f"Dataset inventory mismatch.\n"
            f"Missing: {missing_files}\n"
            f"Unexpected: {unexpected_files}"
        )

    existing = [str(path) for path in OUTPUTS if path.exists()]

    if existing:
        raise FileExistsError(
            "Refusing to overwrite existing outputs:\n"
            + "\n".join(existing)
        )

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    quality_rows = []
    time_rows = []
    reference_variables = None
    structural_issues = []

    for file_path in files:
        match = re.fullmatch(
            r"CERES_(20\d{2})_established_monsoon\.nc",
            file_path.name
        )

        if not match:
            raise ValueError(f"Unexpected filename: {file_path.name}")

        year = int(match.group(1))

        print(f"Processing {year}...", flush=True)

        with xr.open_dataset(
            file_path, engine="netcdf4"
        ) as decoded, xr.open_dataset(
            file_path,
            engine="netcdf4",
            decode_cf=False,
            mask_and_scale=False
        ) as raw:

            expected_dimensions = {
                "time": 720,
                "lat": 32,
                "lon": 30
            }

            actual_dimensions = dict(decoded.sizes)

            if actual_dimensions != expected_dimensions:
                structural_issues.append(
                    f"{file_path.name}: dimensions "
                    f"{actual_dimensions}"
                )

            variables = set(decoded.data_vars)

            if len(variables) != 45:
                structural_issues.append(
                    f"{file_path.name}: expected 45 variables, "
                    f"found {len(variables)}"
                )

            if reference_variables is None:
                reference_variables = variables
            elif variables != reference_variables:
                structural_issues.append(
                    f"{file_path.name}: variable schema differs "
                    "from the first yearly file"
                )

            if "time" not in decoded or "time" not in raw:
                raise ValueError(
                    f"Missing time coordinate in {file_path.name}"
                )

            times = decoded["time"].values
            raw_time = np.asarray(raw["time"].values)

            deltas = (
                np.diff(times)
                .astype("timedelta64[ns]")
                .astype(np.float64) / 1e9
            )

            if raw_time.size and np.issubdtype(
                raw_time.dtype, np.floating
            ):
                coordinate_spacing_seconds = (
                    float(
                        np.spacing(
                            np.max(np.abs(raw_time))
                        )
                    ) * 86400
                )
            else:
                coordinate_spacing_seconds = np.nan

            if np.isfinite(coordinate_spacing_seconds):
                exceeds_precision = int(
                    np.sum(
                        np.abs(deltas - 3600)
                        > coordinate_spacing_seconds
                    )
                )
            else:
                exceeds_precision = np.nan

            time_rows.append({
                "year": year,
                "file": file_path.name,
                "time_count": len(times),
                "unique_timestamps": len(np.unique(times)),
                "strictly_increasing": bool(
                    len(times) > 1 and np.all(
                        np.diff(times) > np.timedelta64(0, "ns")
                    )
                ),
                "raw_time_dtype": str(raw_time.dtype),
                "raw_time_units": raw["time"].attrs.get(
                    "units", ""
                ),
                "float32_spacing_seconds": (
                    coordinate_spacing_seconds
                ),
                "first_timestamp": str(times[0]),
                "last_timestamp": str(times[-1]),
                "mean_step_seconds": (
                    float(np.mean(deltas)) if len(deltas) else np.nan
                ),
                "median_step_seconds": (
                    float(np.median(deltas)) if len(deltas) else np.nan
                ),
                "minimum_step_seconds": (
                    float(np.min(deltas)) if len(deltas) else np.nan
                ),
                "maximum_step_seconds": (
                    float(np.max(deltas)) if len(deltas) else np.nan
                ),
                "max_abs_deviation_from_3600_seconds": (
                    float(np.max(np.abs(deltas - 3600)))
                    if len(deltas) else np.nan
                ),
            })

            for name, variable in decoded.data_vars.items():
                values = np.asarray(
                    variable.values, dtype=np.float64
                )

                raw_values = np.asarray(raw[name].values)

                (
                    fill_description,
                    raw_nan_count,
                    raw_fill_nan_count,
                    raw_numeric_fill_count,
                ) = get_fill_information(
                    raw[name], raw_values
                )

                decoded_nan_count = int(np.isnan(values).sum())
                infinite_count = int(np.isinf(values).sum())

                row = {
                    "year": year,
                    "file": file_path.name,
                    "variable": name,
                    "units": variable.attrs.get("units", ""),
                    "long_name": variable.attrs.get("long_name", ""),
                    "total_values": int(values.size),
                    "valid_finite_values": int(
                        np.isfinite(values).sum()
                    ),
                    "raw_nan_count": raw_nan_count,
                    "raw_fill_nan_count": raw_fill_nan_count,
                    "raw_numeric_fill_count": raw_numeric_fill_count,
                    "decoded_nan_count": decoded_nan_count,
                    "raw_decoded_nan_mismatch": (
                        raw_nan_count != decoded_nan_count
                    ),
                    "infinite_count": infinite_count,
                    "raw_fill_attributes": fill_description,
                    "missing_pct": (
                        100 * decoded_nan_count / values.size
                        if values.size else np.nan
                    ),
                    **calculate_statistics(values),
                }

                finite = values[np.isfinite(values)]

                if name.lower().startswith("cldarea"):
                    row["outside_0_100_count"] = int(
                        np.sum((finite < 0) | (finite > 100))
                    )
                else:
                    row["outside_0_100_count"] = ""

                quality_rows.append(row)

    if structural_issues:
        raise ValueError(
            "Structural validation failed:\n"
            + "\n".join(structural_issues)
            + "\nNo QC reports were written."
        )

    quality = pd.DataFrame(quality_rows)
    time_quality = pd.DataFrame(time_rows)

    if len(quality) != 540:
        raise ValueError(
            f"Expected 540 variable-year records, "
            f"found {len(quality)}"
        )

    quality.to_csv(OUTPUTS[0], index=False)
    time_quality.to_csv(OUTPUTS[2], index=False)

    summary = quality.groupby(
        ["variable", "units", "long_name"],
        dropna=False
    ).agg(
        years_present=("year", "nunique"),
        total_values=("total_values", "sum"),
        total_valid_values=("valid_finite_values", "sum"),
        total_raw_nan_values=("raw_nan_count", "sum"),
        total_raw_fill_nan_values=("raw_fill_nan_count", "sum"),
        total_raw_numeric_fill_values=(
            "raw_numeric_fill_count", "sum"
        ),
        total_decoded_nan_values=("decoded_nan_count", "sum"),
        total_infinite_values=("infinite_count", "sum"),
        average_yearly_missing_pct=("missing_pct", "mean"),
        lowest_observed_value=("minimum", "min"),
        highest_observed_value=("maximum", "max"),
        years_with_missing=(
            "decoded_nan_count",
            lambda x: int((x > 0).sum())
        ),
    ).reset_index()

    summary.to_csv(OUTPUTS[1], index=False)

    log = [
        "ESTABLISHED MONSOON SCIENTIFIC QUALITY CONTROL V3",
        f"Files processed: {len(files)}",
        f"Variable-year records: {len(quality)}",
        f"Unique variables: {quality['variable'].nunique()}",
        f"Raw NaN values: {int(quality['raw_nan_count'].sum())}",
        f"NaNs associated with declared NaN fill attributes: {int(quality['raw_fill_nan_count'].sum())}",
        f"Raw numeric fill matches: {int(quality['raw_numeric_fill_count'].sum())}",
        f"Decoded NaN values: {int(quality['decoded_nan_count'].sum())}",
        f"Raw/decoded NaN mismatches: {int(quality['raw_decoded_nan_mismatch'].sum())}",
        f"Infinite values: {int(quality['infinite_count'].sum())}",
        f"Time records not equal to 720: {int((time_quality['time_count'] != 720).sum())}",
        f"Years not strictly increasing: {int((~time_quality['strictly_increasing']).sum())}",
        "",
        "INTERPRETATION",
        "- Missing values and unusual ranges are reported, not corrected.",
        "- Raw NaNs, NaN fill attributes, and numeric fill sentinels are distinguished.",
        "- Raw and decoded NaN counts are compared.",
        "- Time intervals and stored coordinate precision are reported descriptively.",
        "- Apparent interval variation is consistent with float32 coordinate quantization; product sampling accuracy has not been independently established.",
        "- Cloud-area values outside 0-100 are flagged for investigation.",
        "- Statistical extremes are descriptive, not proof of invalid data.",
        "- No clustering features are selected in this stage.",
        "- Original NetCDF datasets are never modified.",
    ]

    OUTPUTS[3].write_text(
        "\n".join(log), encoding="utf-8"
    )

    print("\nQC V3 completed successfully.")
    print(f"Files processed: {len(files)}")
    print(f"Variables: {quality['variable'].nunique()}")
    print(f"Variable-year records: {len(quality)}")
    print("\nReports saved:")

    for path in OUTPUTS:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()

