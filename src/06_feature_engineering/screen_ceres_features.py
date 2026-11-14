
from pathlib import Path
import json
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "interim" / "ceres_seasonal" / "post_monsoon"
OUT_DIR = ROOT / "reports" / "data_quality"

OUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = range(2010, 2022)

# Screening thresholds, not final scientific acceptance criteria.
MAX_MISSING_PCT = 50.0
MAX_OUT_OF_RANGE_PCT = 1.0
MIN_STD = 1e-8
CORRELATION_THRESHOLD = 0.90
SAMPLES_PER_YEAR = 10000
RANDOM_SEED = 42

# Categorical variables are retained for separate analysis,
# not treated as continuous clustering features.
CATEGORICAL_PREFIXES = ("cldphase_",)


def get_numeric_attribute(da, name):
    value = da.attrs.get(name)

    if value is None:
        return None

    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def classify_variable(name, units):
    if name.startswith("cldarea_"):
        return "cloud_area_fraction"
    if name.startswith("cldhght_"):
        return "cloud_height"
    if name.startswith("cldphase_"):
        return "cloud_phase"
    if name.startswith("cldpress_"):
        return "cloud_pressure"
    if name.startswith("cldtau_"):
        return "optical_depth"
    if name.startswith("cldtemp_"):
        return "cloud_temperature"
    if name.startswith("lwp_"):
        return "liquid_water_path"
    if name.startswith("iwp_"):
        return "ice_water_path"
    return "other"


def classify_layer(name):
    for layer in (
        "mid_high", "mid_low", "high", "low", "total"
    ):
        if f"_{layer}_" in name:
            return layer
    return "unknown"


def inspect_variable(da, year):
    values = np.asarray(da.values, dtype=np.float64)
    finite = np.isfinite(values)

    total = values.size
    valid_count = int(finite.sum())
    missing_count = total - valid_count

    valid_min = get_numeric_attribute(da, "valid_min")
    valid_max = get_numeric_attribute(da, "valid_max")

    physical_valid = finite.copy()

    if valid_min is not None:
        physical_valid &= values >= valid_min

    if valid_max is not None:
        physical_valid &= values <= valid_max

    out_of_range = finite & (~physical_valid)

    usable = values[physical_valid]

    if usable.size:
        minimum = float(np.min(usable))
        maximum = float(np.max(usable))
        mean = float(np.mean(usable))
        median = float(np.median(usable))
        std = float(np.std(usable))
        p01 = float(np.percentile(usable, 1))
        p99 = float(np.percentile(usable, 99))
        unique_count = int(np.unique(usable).size) if usable.size < 500000 else None
    else:
        minimum = maximum = mean = median = std = p01 = p99 = np.nan
        unique_count = 0

    missing_pct = 100 * missing_count / total if total else np.nan
    out_of_range_pct = (
        100 * int(out_of_range.sum()) / valid_count
        if valid_count else np.nan
    )

    return {
        "year": year,
        "variable": da.name,
        "feature_family": classify_variable(da.name, da.attrs.get("units")),
        "vertical_layer": classify_layer(da.name),
        "dimensions": str(da.dims),
        "units": da.attrs.get("units"),
        "long_name": da.attrs.get("long_name"),
        "valid_min_attribute": valid_min,
        "valid_max_attribute": valid_max,
        "total_values": total,
        "valid_values": valid_count,
        "missing_values": missing_count,
        "missing_pct": missing_pct,
        "out_of_range_values": int(out_of_range.sum()),
        "out_of_range_pct_of_finite": out_of_range_pct,
        "observed_min": minimum,
        "observed_max": maximum,
        "mean": mean,
        "median": median,
        "std": std,
        "p01": p01,
        "p99": p99,
        "unique_count": unique_count,
    }, values, physical_valid


def main():
    rng = np.random.default_rng(RANDOM_SEED)

    yearly_rows = []
    sample_data = {}
    variable_metadata = {}

    print("\n========== CERES FEATURE SCREENING ==========")

    for year in YEARS:
        path = DATA_DIR / f"CERES_{year}_post_monsoon.nc"

        if not path.exists():
            raise FileNotFoundError(path)

        print(f"Inspecting {year}: {path.name}")

        with xr.open_dataset(
            path,
            decode_cf=True,
            mask_and_scale=True
        ) as ds:

            if "time" not in ds.coords:
                raise ValueError(f"No time coordinate in {path.name}")

            if len(ds["time"]) != 720:
                raise ValueError(
                    f"Expected 720 observations in {path.name}, "
                    f"found {len(ds['time'])}"
                )

            if year == 2010:
                variable_names = list(ds.data_vars)
                print(f"Variables found: {len(variable_names)}")

            for name in ds.data_vars:
                da = ds[name]

                if not np.issubdtype(da.dtype, np.number):
                    continue

                row, values, physical_valid = inspect_variable(da, year)
                yearly_rows.append(row)

                variable_metadata[name] = {
                    "family": row["feature_family"],
                    "layer": row["vertical_layer"],
                    "units": row["units"],
                    "long_name": row["long_name"],
                    "valid_min": row["valid_min_attribute"],
                    "valid_max": row["valid_max_attribute"],
                }

                # Deterministic sampling for correlation analysis.
                flat_values = values.reshape(-1)
                flat_valid = physical_valid.reshape(-1)

                sample_size = min(SAMPLES_PER_YEAR, flat_values.size)
                indices = rng.choice(
                    flat_values.size,
                    size=sample_size,
                    replace=False
                )

                sampled = flat_values[indices].astype(np.float32)
                sampled[~flat_valid[indices]] = np.nan

                sample_data.setdefault(name, []).append(sampled)

    yearly_df = pd.DataFrame(yearly_rows)

    # Aggregate metrics across all 12 years.
    summary_rows = []

    for name, group in yearly_df.groupby("variable"):
        meta = variable_metadata[name]

        total = int(group["total_values"].sum())
        missing = int(group["missing_values"].sum())
        valid = int(group["valid_values"].sum())
        out_of_range = int(group["out_of_range_values"].sum())

        missing_pct = 100 * missing / total if total else np.nan
        out_of_range_pct = (
            100 * out_of_range / valid if valid else np.nan
        )

        annual_missing_max = float(group["missing_pct"].max())
        annual_missing_min = float(group["missing_pct"].min())

        std_values = group["std"].dropna()
        std_mean = float(std_values.mean()) if len(std_values) else np.nan
        std_min = float(std_values.min()) if len(std_values) else np.nan

        year_count = int(group["year"].nunique())

        is_categorical = name.startswith(CATEGORICAL_PREFIXES)

        reasons = []

        if is_categorical:
            reasons.append("Categorical variable; do not use as continuous input")

        if missing_pct > MAX_MISSING_PCT:
            reasons.append(
                f"Overall missingness exceeds {MAX_MISSING_PCT}%"
            )

        if annual_missing_max > MAX_MISSING_PCT:
            reasons.append(
                f"At least one year exceeds {MAX_MISSING_PCT}% missingness"
            )

        if out_of_range_pct > MAX_OUT_OF_RANGE_PCT:
            reasons.append(
                f"Out-of-range values exceed {MAX_OUT_OF_RANGE_PCT}%"
            )

        if not np.isfinite(std_mean) or std_mean <= MIN_STD:
            reasons.append("No meaningful numerical variation")

        if year_count != len(list(YEARS)):
            reasons.append("Not present in every study year")

        if is_categorical:
            status = "SEPARATE_CATEGORICAL_ANALYSIS"
        elif (
            missing_pct <= MAX_MISSING_PCT
            and annual_missing_max <= MAX_MISSING_PCT
            and out_of_range_pct <= MAX_OUT_OF_RANGE_PCT
            and np.isfinite(std_mean)
            and std_mean > MIN_STD
            and year_count == len(list(YEARS))
        ):
            status = "ELIGIBLE_CANDIDATE"
        else:
            status = "REVIEW_OR_EXCLUDE"

        summary_rows.append({
            "variable": name,
            "feature_family": meta["family"],
            "vertical_layer": meta["layer"],
            "units": meta["units"],
            "long_name": meta["long_name"],
            "years_present": year_count,
            "overall_missing_pct": missing_pct,
            "minimum_annual_missing_pct": annual_missing_min,
            "maximum_annual_missing_pct": annual_missing_max,
            "out_of_range_pct_of_finite": out_of_range_pct,
            "mean_annual_std": std_mean,
            "minimum_annual_std": std_min,
            "status": status,
            "screening_reasons": "; ".join(reasons) if reasons else "Passed initial screening",
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_df = summary_df.sort_values(
        ["status", "overall_missing_pct", "feature_family"]
    )

    # Correlations using a deterministic sample from every year.
    correlation_df = pd.DataFrame({
        name: np.concatenate(samples)
        for name, samples in sample_data.items()
    })

    correlations = correlation_df.corr(
        method="spearman",
        min_periods=1000
    )

    correlation_pairs = []

    columns = correlations.columns.tolist()

    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            value = correlations.iloc[i, j]

            if pd.notna(value) and abs(value) >= CORRELATION_THRESHOLD:
                a = columns[i]
                b = columns[j]

                correlation_pairs.append({
                    "variable_1": a,
                    "variable_2": b,
                    "spearman_correlation": float(value),
                    "absolute_correlation": float(abs(value)),
                    "family_1": variable_metadata[a]["family"],
                    "family_2": variable_metadata[b]["family"],
                    "same_family": (
                        variable_metadata[a]["family"]
                        == variable_metadata[b]["family"]
                    ),
                })

    correlation_pairs_df = pd.DataFrame(correlation_pairs)

    if not correlation_pairs_df.empty:
        correlation_pairs_df = correlation_pairs_df.sort_values(
            "absolute_correlation",
            ascending=False
        )

    # Save reports.
    yearly_df.to_csv(
        OUT_DIR / "ceres_feature_screening_yearly.csv",
        index=False
    )

    summary_df.to_csv(
        OUT_DIR / "ceres_feature_screening_summary.csv",
        index=False
    )

    correlations.to_csv(
        OUT_DIR / "ceres_feature_spearman_correlation_matrix.csv"
    )

    correlation_pairs_df.to_csv(
        OUT_DIR / "ceres_feature_high_correlations.csv",
        index=False
    )

    result = {
        "years_inspected": len(list(YEARS)),
        "variables_screened": int(summary_df.shape[0]),
        "eligible_candidates": int(
            (summary_df["status"] == "ELIGIBLE_CANDIDATE").sum()
        ),
        "review_or_exclude": int(
            (summary_df["status"] == "REVIEW_OR_EXCLUDE").sum()
        ),
        "categorical_variables": int(
            (summary_df["status"] == "SEPARATE_CATEGORICAL_ANALYSIS").sum()
        ),
        "high_correlation_pairs": int(len(correlation_pairs_df)),
        "thresholds": {
            "maximum_overall_missing_pct": MAX_MISSING_PCT,
            "maximum_annual_missing_pct": MAX_MISSING_PCT,
            "maximum_out_of_range_pct": MAX_OUT_OF_RANGE_PCT,
            "minimum_std": MIN_STD,
            "high_correlation_threshold": CORRELATION_THRESHOLD,
            "correlation_method": "Spearman",
            "samples_per_year_per_variable": SAMPLES_PER_YEAR,
        },
        "important_note": (
            "This is an initial screening, not final scientific feature "
            "selection. Metadata valid_min/valid_max are screening bounds, "
            "not independent physical validation. Correlations are estimated "
            "from deterministic samples."
        ),
    }

    with open(
        OUT_DIR / "ceres_feature_screening_summary.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(result, f, indent=4)

    print("\n========== SCREENING RESULTS ==========")
    print(json.dumps(result, indent=4))

    print("\n========== ELIGIBLE CANDIDATES ==========")
    print(
        summary_df[
            summary_df["status"] == "ELIGIBLE_CANDIDATE"
        ][
            [
                "variable",
                "feature_family",
                "overall_missing_pct",
                "mean_annual_std",
            ]
        ].to_string(index=False)
    )

    print("\n========== HIGH CORRELATIONS ==========")
    if correlation_pairs_df.empty:
        print("No pairs exceeded the correlation threshold.")
    else:
        print(correlation_pairs_df.head(30).to_string(index=False))

    print("\nReports saved in:", OUT_DIR)


if __name__ == "__main__":
    main()
