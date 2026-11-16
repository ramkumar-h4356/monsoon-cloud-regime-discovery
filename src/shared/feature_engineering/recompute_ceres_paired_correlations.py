
from pathlib import Path
import json
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = ROOT / "data" / "interim" / "ceres_seasonal" / "post_monsoon"
REPORT_DIR = ROOT / "reports" / "data_quality"

SUMMARY_FILE = REPORT_DIR / "ceres_feature_screening_summary.csv"

YEARS = range(2010, 2022)
SAMPLES_PER_YEAR = 30000
RANDOM_SEED = 42
CORRELATION_THRESHOLD = 0.90
MINIMUM_PAIRED_OBSERVATIONS = 1000


def main():
    if not SUMMARY_FILE.exists():
        raise FileNotFoundError(SUMMARY_FILE)

    screening = pd.read_csv(SUMMARY_FILE)

    candidates = screening.loc[
        screening["status"] == "ELIGIBLE_CANDIDATE",
        "variable"
    ].tolist()

    if not candidates:
        raise ValueError("No eligible continuous candidates found.")

    rng = np.random.default_rng(RANDOM_SEED)
    sampled_years = []

    print(f"Eligible continuous candidates: {len(candidates)}")

    for year in YEARS:
        path = DATA_DIR / f"CERES_{year}_post_monsoon.nc"

        if not path.exists():
            raise FileNotFoundError(path)

        print(f"Sampling {year}: {path.name}")

        with xr.open_dataset(
            path,
            decode_cf=True,
            mask_and_scale=True
        ) as ds:

            missing_variables = [
                name for name in candidates if name not in ds.data_vars
            ]

            if missing_variables:
                raise ValueError(
                    f"Missing variables in {year}: {missing_variables}"
                )

            reference = ds[candidates[0]]

            if reference.ndim != 3:
                raise ValueError(
                    f"Expected 3D variables; got {reference.dims}"
                )

            reference_dims = reference.dims
            reference_shape = reference.shape

            for name in candidates:
                if (
                    ds[name].dims != reference_dims
                    or ds[name].shape != reference_shape
                ):
                    raise ValueError(
                        f"Dimension mismatch for {name} in {year}"
                    )

            total_positions = int(np.prod(reference_shape))
            sample_count = min(SAMPLES_PER_YEAR, total_positions)

            # One shared set of indices for every variable in this year.
            indices = rng.choice(
                total_positions,
                size=sample_count,
                replace=False
            )

            sampled = {}

            for name in candidates:
                values = np.asarray(
                    ds[name].values,
                    dtype=np.float64
                ).reshape(-1)

                sampled[name] = values[indices]

            sampled_df = pd.DataFrame(sampled)
            sampled_df["year"] = year
            sampled_years.append(sampled_df)

    combined = pd.concat(sampled_years, ignore_index=True)

    feature_data = combined[candidates]

    correlations = feature_data.corr(
        method="spearman",
        min_periods=MINIMUM_PAIRED_OBSERVATIONS
    )

    pairs = []

    for i, variable_1 in enumerate(candidates):
        for variable_2 in candidates[i + 1:]:
            value = correlations.loc[variable_1, variable_2]

            if pd.notna(value):
                pairs.append({
                    "variable_1": variable_1,
                    "variable_2": variable_2,
                    "spearman_correlation": float(value),
                    "absolute_correlation": float(abs(value)),
                    "high_correlation": (
                        abs(value) >= CORRELATION_THRESHOLD
                    ),
                })

    pairs_df = pd.DataFrame(pairs)

    if not pairs_df.empty:
        pairs_df = pairs_df.sort_values(
            "absolute_correlation",
            ascending=False
        )

    high_pairs = (
        pairs_df[pairs_df["high_correlation"]]
        if not pairs_df.empty
        else pd.DataFrame()
    )

    correlations.to_csv(
        REPORT_DIR / "ceres_paired_spearman_correlation_matrix.csv"
    )

    pairs_df.to_csv(
        REPORT_DIR / "ceres_paired_correlation_pairs.csv",
        index=False
    )

    high_pairs.to_csv(
        REPORT_DIR / "ceres_paired_high_correlations.csv",
        index=False
    )

    summary = {
        "years": len(list(YEARS)),
        "eligible_continuous_variables": len(candidates),
        "sampled_positions_per_year": SAMPLES_PER_YEAR,
        "total_sampled_positions": int(len(combined)),
        "correlation_method": "Spearman",
        "shared_time_and_location_indices": True,
        "pairwise_missing_value_handling": True,
        "minimum_paired_observations": MINIMUM_PAIRED_OBSERVATIONS,
        "correlation_threshold": CORRELATION_THRESHOLD,
        "valid_correlation_pairs": int(len(pairs_df)),
        "high_correlation_pairs": int(len(high_pairs)),
        "note": (
            "Correlations use paired observations from identical "
            "sampled time and location positions. They are exploratory "
            "and descriptive; spatial and temporal autocorrelation "
            "means they should not be interpreted as independent "
            "statistical evidence."
        ),
    }

    with open(
        REPORT_DIR / "ceres_paired_correlation_summary.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(summary, file, indent=4)

    print("\n========== PAIRED CORRELATION RESULTS ==========")
    print(json.dumps(summary, indent=4))

    print("\n========== STRONGEST CORRELATIONS ==========")

    if pairs_df.empty:
        print("No valid correlation pairs were calculated.")
    else:
        print(
            pairs_df.head(25).to_string(index=False)
        )

    print("\n========== HIGH CORRELATION PAIRS ==========")

    if high_pairs.empty:
        print("No pairs exceeded the threshold.")
    else:
        print(high_pairs.to_string(index=False))

    print("\nReports saved in:", REPORT_DIR)


if __name__ == "__main__":
    main()
