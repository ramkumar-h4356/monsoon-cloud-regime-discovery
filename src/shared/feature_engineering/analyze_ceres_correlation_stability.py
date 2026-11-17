
from pathlib import Path
import json

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = (
    ROOT / "data" / "interim" / "ceres_seasonal" / "post_monsoon"
)
REPORT_DIR = ROOT / "reports" / "data_quality"

SCREENING_FILE = REPORT_DIR / "ceres_feature_screening_summary.csv"
POOLED_PAIRS_FILE = REPORT_DIR / "ceres_paired_correlation_pairs.csv"

ANNUAL_OUTPUT = REPORT_DIR / "ceres_annual_correlation_pairs.csv"
STABILITY_OUTPUT = REPORT_DIR / "ceres_correlation_stability_summary.csv"
SUMMARY_OUTPUT = REPORT_DIR / "ceres_correlation_stability_summary.json"

YEARS = range(2010, 2022)

SAMPLES_PER_YEAR = 30000
RANDOM_SEED = 42
CORRELATION_THRESHOLD = 0.90
MINIMUM_PAIRED_OBSERVATIONS = 1000


def load_candidates():
    if not SCREENING_FILE.exists():
        raise FileNotFoundError(SCREENING_FILE)

    screening = pd.read_csv(SCREENING_FILE)

    candidates = screening.loc[
        screening["status"] == "ELIGIBLE_CANDIDATE",
        "variable"
    ].tolist()

    if len(candidates) < 2:
        raise ValueError("At least two eligible variables are required.")

    return candidates


def sample_year(year, candidates, rng):
    path = DATA_DIR / f"CERES_{year}_post_monsoon.nc"

    if not path.exists():
        raise FileNotFoundError(path)

    print(f"Processing year {year}: {path.name}")

    with xr.open_dataset(
        path,
        decode_cf=True,
        mask_and_scale=True
    ) as ds:

        missing = [
            name for name in candidates
            if name not in ds.data_vars
        ]

        if missing:
            raise ValueError(
                f"Variables missing in {year}: {missing}"
            )

        reference = ds[candidates[0]]

        if reference.ndim != 3:
            raise ValueError(
                f"Expected 3D variables, got {reference.dims}"
            )

        reference_dims = reference.dims
        reference_shape = reference.shape

        for name in candidates:
            variable = ds[name]

            if (
                variable.dims != reference_dims
                or variable.shape != reference_shape
            ):
                raise ValueError(
                    f"Dimension mismatch for {name} in {year}"
                )

        total_positions = int(np.prod(reference_shape))
        sample_count = min(SAMPLES_PER_YEAR, total_positions)

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

    return pd.DataFrame(sampled)


def calculate_annual_correlations(year, sampled, candidates):
    records = []

    for i, variable_1 in enumerate(candidates):
        x = sampled[variable_1].to_numpy()

        for variable_2 in candidates[i + 1:]:
            y = sampled[variable_2].to_numpy()

            valid = np.isfinite(x) & np.isfinite(y)

            paired_count = int(valid.sum())
            correlation = np.nan

            if paired_count >= MINIMUM_PAIRED_OBSERVATIONS:
                x_valid = x[valid]
                y_valid = y[valid]

                if (
                    np.unique(x_valid).size > 1
                    and np.unique(y_valid).size > 1
                ):
                    correlation = float(
                        pd.Series(x_valid).corr(
                            pd.Series(y_valid),
                            method="spearman"
                        )
                    )

            records.append({
                "year": year,
                "variable_1": variable_1,
                "variable_2": variable_2,
                "spearman_correlation": correlation,
                "absolute_correlation": (
                    abs(correlation)
                    if pd.notna(correlation)
                    else np.nan
                ),
                "paired_observations": paired_count,
                "valid_correlation": pd.notna(correlation),
                "high_correlation": (
                    abs(correlation) >= CORRELATION_THRESHOLD
                    if pd.notna(correlation)
                    else False
                )
            })

    return records


def create_stability_summary(annual_df):
    pooled = pd.read_csv(POOLED_PAIRS_FILE)

    required_columns = {
        "variable_1",
        "variable_2",
        "spearman_correlation"
    }

    if not required_columns.issubset(pooled.columns):
        raise ValueError(
            "The pooled correlation report has unexpected columns."
        )

    pooled = pooled[
        [
            "variable_1",
            "variable_2",
            "spearman_correlation"
        ]
    ].rename(
        columns={
            "spearman_correlation": "pooled_spearman_correlation"
        }
    )

    summary_records = []

    for (variable_1, variable_2), group in annual_df.groupby(
        ["variable_1", "variable_2"],
        sort=False
    ):
        valid = group.loc[group["valid_correlation"]]

        correlations = valid["spearman_correlation"]
        positive = int((correlations > 0).sum())
        negative = int((correlations < 0).sum())
        zero = int((correlations == 0).sum())

        valid_years = len(valid)
        dominant_sign_years = max(positive, negative, zero)

        summary_records.append({
            "variable_1": variable_1,
            "variable_2": variable_2,
            "valid_years": valid_years,
            "years_above_threshold": int(
                valid["high_correlation"].sum()
            ),
            "positive_years": positive,
            "negative_years": negative,
            "zero_correlation_years": zero,
            "sign_consistency_years": dominant_sign_years,
            "sign_consistency_fraction": (
                dominant_sign_years / valid_years
                if valid_years else np.nan
            ),
            "mean_annual_correlation": (
                correlations.mean() if valid_years else np.nan
            ),
            "median_annual_correlation": (
                correlations.median() if valid_years else np.nan
            ),
            "median_absolute_annual_correlation": (
                correlations.abs().median()
                if valid_years else np.nan
            ),
            "minimum_paired_observations": (
                int(valid["paired_observations"].min())
                if valid_years else 0
            ),
            "median_paired_observations": (
                float(valid["paired_observations"].median())
                if valid_years else np.nan
            )
        })

    stability = pd.DataFrame(summary_records)

    stability = stability.merge(
        pooled,
        on=["variable_1", "variable_2"],
        how="left",
        validate="one_to_one"
    )

    stability["pooled_absolute_correlation"] = (
        stability["pooled_spearman_correlation"].abs()
    )

    stability["pooled_high_correlation"] = (
        stability["pooled_absolute_correlation"]
        >= CORRELATION_THRESHOLD
    )

    stability["annual_high_correlation_fraction"] = (
        stability["years_above_threshold"]
        / stability["valid_years"].replace(0, np.nan)
    )

    stability = stability.sort_values(
        "pooled_absolute_correlation",
        ascending=False
    )

    return stability


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not POOLED_PAIRS_FILE.exists():
        raise FileNotFoundError(POOLED_PAIRS_FILE)

    candidates = load_candidates()

    rng = np.random.default_rng(RANDOM_SEED)

    print("========== CORRELATION STABILITY ANALYSIS ==========")
    print(f"Years: {len(list(YEARS))}")
    print(f"Variables: {len(candidates)}")
    print(f"Expected pairs: {len(candidates) * (len(candidates) - 1) // 2}")
    print(f"Samples per year: {SAMPLES_PER_YEAR}")

    all_records = []
    total_sampled_positions = 0

    for year in YEARS:
        sampled = sample_year(year, candidates, rng)

        total_sampled_positions += len(sampled)

        annual_records = calculate_annual_correlations(
            year,
            sampled,
            candidates
        )

        all_records.extend(annual_records)

    annual_df = pd.DataFrame(all_records)

    annual_df = annual_df.sort_values(
        ["variable_1", "variable_2", "year"]
    )

    stability = create_stability_summary(annual_df)

    annual_df.to_csv(ANNUAL_OUTPUT, index=False)
    stability.to_csv(STABILITY_OUTPUT, index=False)

    valid_correlations = annual_df[
        annual_df["valid_correlation"]
    ]

    summary = {
        "analysis": "Year-wise CERES Spearman correlation stability",
        "years": list(YEARS),
        "number_of_years": len(list(YEARS)),
        "eligible_continuous_variables": len(candidates),
        "expected_variable_pairs": (
            len(candidates) * (len(candidates) - 1) // 2
        ),
        "sampled_positions_per_year": SAMPLES_PER_YEAR,
        "total_sampled_positions": total_sampled_positions,
        "random_seed": RANDOM_SEED,
        "correlation_method": "Spearman",
        "sampling_method": (
            "One shared random sample of time-location positions "
            "per year, shared across all candidate variables."
        ),
        "pairwise_missing_value_handling": True,
        "minimum_paired_observations": MINIMUM_PAIRED_OBSERVATIONS,
        "correlation_threshold": CORRELATION_THRESHOLD,
        "annual_pair_records": len(annual_df),
        "valid_annual_correlations": len(valid_correlations),
        "invalid_annual_correlations": int(
            (~annual_df["valid_correlation"]).sum()
        ),
        "pooled_high_correlation_pairs": int(
            stability["pooled_high_correlation"].sum()
        ),
        "pairs_highly_correlated_in_at_least_one_year": int(
            (stability["years_above_threshold"] > 0).sum()
        ),
        "pairs_highly_correlated_in_every_valid_year": int(
            (
                (stability["valid_years"] > 0)
                & (
                    stability["years_above_threshold"]
                    == stability["valid_years"]
                )
            ).sum()
        ),
        "interpretation_note": (
            "Annual correlations are descriptive measures of "
            "within-year association. They are not independent "
            "statistical evidence because satellite observations "
            "may have spatial and temporal autocorrelation. "
            "Pooled correlations and annual correlations answer "
            "different questions and should not be treated as "
            "directly interchangeable. No feature is automatically "
            "removed based on these results."
        ),
        "outputs": [
            str(ANNUAL_OUTPUT.relative_to(ROOT)),
            str(STABILITY_OUTPUT.relative_to(ROOT)),
            str(SUMMARY_OUTPUT.relative_to(ROOT))
        ]
    }

    with open(SUMMARY_OUTPUT, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    print("\n========== ANALYSIS SUMMARY ==========")
    print(json.dumps(summary, indent=4))

    print("\n========== MOST POOLED-CORRELATED PAIRS ==========")
    print(
        stability.head(20).to_string(index=False)
    )

    print("\n========== OUTPUT FILES ==========")
    print(ANNUAL_OUTPUT)
    print(STABILITY_OUTPUT)
    print(SUMMARY_OUTPUT)


if __name__ == "__main__":
    main()
