
from pathlib import Path
from itertools import combinations
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
SAMPLES_PER_DATASET = 30000
RANDOM_SEED = 42
CORRELATION_THRESHOLD = 0.90
MINIMUM_PAIRED_OBSERVATIONS = 1000

SEASON_LABELS = {
    "pre_monsoon": "Pre-monsoon",
    "established_monsoon": "Established monsoon",
    "post_monsoon": "Post-monsoon",
}


def find_column(dataframe, candidates):
    lookup = {column.lower(): column for column in dataframe.columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    raise ValueError(
        f"Could not find any of these columns: {candidates}. "
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

    eligible = screening.loc[
        screening[status_column].astype(str).str.upper()
        == "ELIGIBLE_CANDIDATE",
        variable_column,
    ].dropna().astype(str).unique().tolist()

    if len(eligible) < 2:
        raise ValueError(
            f"Expected at least two eligible variables; found {len(eligible)}."
        )

    return sorted(eligible)


def load_sampled_dataset(path, variables, sample_indices, expected_shape,
                         expected_dims):
    if not path.exists():
        raise FileNotFoundError(f"Missing seasonal dataset: {path}")

    sampled = {}

    with xr.open_dataset(
        path,
        decode_cf=True,
        mask_and_scale=True,
    ) as dataset:

        if "time" not in dataset.dims:
            raise ValueError(f"'time' dimension missing in {path}")

        if tuple(dataset.sizes[d] for d in dataset.dims) != expected_shape:
            raise ValueError(
                f"Dataset shape mismatch in {path}: "
                f"{tuple(dataset.sizes[d] for d in dataset.dims)}"
            )

        for variable in variables:
            if variable not in dataset.variables:
                raise ValueError(
                    f"Variable '{variable}' missing in {path}"
                )

            data_array = dataset[variable]

            if tuple(data_array.dims) != expected_dims[variable]:
                raise ValueError(
                    f"Dimension mismatch for {variable} in {path}: "
                    f"{data_array.dims}"
                )

            values = np.asarray(data_array.values, dtype=np.float64)

            if values.shape != expected_shape:
                raise ValueError(
                    f"Shape mismatch for {variable} in {path}: "
                    f"{values.shape}"
                )

            sampled[variable] = values.reshape(-1)[sample_indices]

    return pd.DataFrame(sampled)


def calculate_correlations(dataframe, variables, season, year=None):
    correlations = dataframe.corr(
        method="spearman",
        min_periods=MINIMUM_PAIRED_OBSERVATIONS,
    )

    valid = dataframe.notna().astype(np.int32)
    paired_counts = valid.T.dot(valid)

    records = []

    for variable_a, variable_b in combinations(variables, 2):
        rho = correlations.loc[variable_a, variable_b]
        paired_n = int(paired_counts.loc[variable_a, variable_b])

        valid_correlation = (
            pd.notna(rho)
            and paired_n >= MINIMUM_PAIRED_OBSERVATIONS
        )

        records.append({
            "season": season,
            "year": year,
            "variable_a": variable_a,
            "variable_b": variable_b,
            "spearman_rho": float(rho) if pd.notna(rho) else None,
            "paired_observations": paired_n,
            "valid_correlation": bool(valid_correlation),
            "high_correlation": bool(
                valid_correlation
                and abs(rho) >= CORRELATION_THRESHOLD
            ),
        })

    return records, correlations


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    variables = load_eligible_variables()
    pairs = list(combinations(variables, 2))

    print("=" * 65)
    print("CERES CROSS-SEASON CORRELATION ANALYSIS")
    print("=" * 65)
    print(f"Eligible variables: {len(variables)}")
    print(f"Variable pairs: {len(pairs)}")
    print(f"Years: {len(YEARS)}")
    print(f"Samples per seasonal dataset: {SAMPLES_PER_DATASET:,}")

    rng = np.random.default_rng(RANDOM_SEED)

    reference_path = (
        SEASON_DIRS["pre_monsoon"]
        / "CERES_2010_pre_monsoon.nc"
    )

    with xr.open_dataset(
        reference_path,
        decode_cf=True,
        mask_and_scale=True,
    ) as reference:

        expected_dims = {}
        for variable in variables:
            if variable not in reference.variables:
                raise ValueError(
                    f"Reference file lacks eligible variable: {variable}"
                )
            expected_dims[variable] = tuple(
                reference[variable].dims
            )

        expected_shape = tuple(
            reference.sizes[dimension]
            for dimension in reference.dims
        )

    total_positions = int(np.prod(expected_shape))

    if SAMPLES_PER_DATASET > total_positions:
        raise ValueError("Requested sample exceeds available positions.")

    sample_indices = np.sort(
        rng.choice(
            total_positions,
            size=SAMPLES_PER_DATASET,
            replace=False,
        )
    )

    print(f"Reference dimensions: {expected_shape}")
    print(f"Total grid-time positions: {total_positions:,}")
    print("One common set of sampled positions will be used")
    print("for every year and season.")

    annual_records = []
    pooled_records = []
    season_summaries = {}

    for season, directory in SEASON_DIRS.items():
        print(f"\nProcessing: {SEASON_LABELS[season]}")

        seasonal_frames = []

        for year in YEARS:
            filename = f"CERES_{year}_{season}.nc"
            path = directory / filename

            print(f"  Loading {filename}")

            dataframe = load_sampled_dataset(
                path,
                variables,
                sample_indices,
                expected_shape,
                expected_dims,
            )

            year_records, _ = calculate_correlations(
                dataframe,
                variables,
                season,
                year,
            )

            annual_records.extend(year_records)
            seasonal_frames.append(dataframe)

            print(
                f"    Sampled rows: {len(dataframe):,}; "
                f"valid annual pairs: "
                f"{sum(r['valid_correlation'] for r in year_records)}"
            )

        pooled_data = pd.concat(
            seasonal_frames,
            ignore_index=True,
        )

        print(
            f"  Pooled observations: {len(pooled_data):,}"
        )

        season_pooled_records, pooled_matrix = calculate_correlations(
            pooled_data,
            variables,
            season,
        )

        pooled_records.extend(season_pooled_records)

        matrix_path = (
            OUTPUT_DIR
            / f"ceres_{season}_pooled_spearman_matrix.csv"
        )
        pooled_matrix.to_csv(matrix_path, index=True)

        season_annual = pd.DataFrame([
            record
            for record in annual_records
            if record["season"] == season
        ])

        valid_annual = season_annual[
            season_annual["valid_correlation"]
        ]

        high_by_pair = (
            valid_annual.groupby(
                ["variable_a", "variable_b"]
            )["high_correlation"]
            .sum()
        )

        season_pooled = pd.DataFrame(season_pooled_records)
        pooled_valid = season_pooled[
            season_pooled["valid_correlation"]
        ]

        season_summaries[season] = {
            "season_label": SEASON_LABELS[season],
            "years_processed": len(YEARS),
            "sampled_observations_per_year": SAMPLES_PER_DATASET,
            "pooled_sampled_observations": len(pooled_data),
            "annual_pair_records": len(season_annual),
            "valid_annual_correlations": int(
                season_annual["valid_correlation"].sum()
            ),
            "pooled_pair_records": len(season_pooled),
            "valid_pooled_correlations": int(
                season_pooled["valid_correlation"].sum()
            ),
            "pooled_high_correlation_pairs": int(
                pooled_valid["high_correlation"].sum()
            ),
            "pairs_high_in_all_valid_years": int(
                (
                    high_by_pair.reindex(
                        pd.MultiIndex.from_tuples(
                            pairs,
                            names=["variable_a", "variable_b"],
                        ),
                        fill_value=0,
                    )
                    == len(YEARS)
                ).sum()
            ),
        }

        print(
            "  Pooled high-correlation pairs: "
            f"{season_summaries[season]['pooled_high_correlation_pairs']}"
        )

        del seasonal_frames, pooled_data

    annual_df = pd.DataFrame(annual_records)
    pooled_df = pd.DataFrame(pooled_records)

    annual_path = (
        OUTPUT_DIR / "ceres_cross_season_annual_correlations.csv"
    )
    pooled_path = (
        OUTPUT_DIR / "ceres_cross_season_pooled_correlations.csv"
    )

    annual_df.to_csv(annual_path, index=False)
    pooled_df.to_csv(pooled_path, index=False)

    comparison = pd.DataFrame({
        "variable_a": [a for a, _ in pairs],
        "variable_b": [b for _, b in pairs],
    })

    for season in SEASON_DIRS:
        pooled_season = pooled_df[
            pooled_df["season"] == season
        ][[
            "variable_a",
            "variable_b",
            "spearman_rho",
            "paired_observations",
            "valid_correlation",
            "high_correlation",
        ]].rename(columns={
            "spearman_rho": f"{season}_pooled_rho",
            "paired_observations": f"{season}_pooled_n",
            "valid_correlation": f"{season}_pooled_valid",
            "high_correlation": f"{season}_pooled_high",
        })

        annual_season = annual_df[
            annual_df["season"] == season
        ]

        annual_summary = (
            annual_season.groupby(
                ["variable_a", "variable_b"]
            )
            .agg(
                annual_valid_years=("valid_correlation", "sum"),
                annual_high_years=("high_correlation", "sum"),
                annual_mean_rho=("spearman_rho", "mean"),
                annual_median_rho=("spearman_rho", "median"),
            )
            .reset_index()
            .rename(columns={
                "annual_valid_years": f"{season}_valid_years",
                "annual_high_years": f"{season}_high_years",
                "annual_mean_rho": f"{season}_annual_mean_rho",
                "annual_median_rho": f"{season}_annual_median_rho",
            })
        )

        comparison = comparison.merge(
            pooled_season,
            on=["variable_a", "variable_b"],
            how="left",
        )

        comparison = comparison.merge(
            annual_summary,
            on=["variable_a", "variable_b"],
            how="left",
        )

    pooled_high_columns = [
        f"{season}_pooled_high"
        for season in SEASON_DIRS
    ]

    comparison["pooled_high_in_all_three_seasons"] = (
        comparison[pooled_high_columns]
        .fillna(False)
        .all(axis=1)
    )

    comparison["pooled_sign_consistent"] = comparison.apply(
        lambda row: (
            all(
                pd.notna(row[f"{season}_pooled_rho"])
                for season in SEASON_DIRS
            )
            and (
                all(
                    row[f"{season}_pooled_rho"] > 0
                    for season in SEASON_DIRS
                )
                or all(
                    row[f"{season}_pooled_rho"] < 0
                    for season in SEASON_DIRS
                )
            )
        ),
        axis=1,
    )

    comparison_path = (
        OUTPUT_DIR / "ceres_cross_season_correlation_comparison.csv"
    )
    comparison.to_csv(comparison_path, index=False)

    summary = {
        "analysis": "CERES cross-season Spearman correlation comparison",
        "years": list(YEARS),
        "seasons": list(SEASON_DIRS.keys()),
        "eligible_variable_count": len(variables),
        "eligible_variables": variables,
        "variable_pair_count": len(pairs),
        "samples_per_dataset": SAMPLES_PER_DATASET,
        "total_sampled_positions_per_season": (
            SAMPLES_PER_DATASET * len(YEARS)
        ),
        "common_sample_indices_across_all_datasets": True,
        "random_seed": RANDOM_SEED,
        "correlation_method": "Spearman",
        "correlation_threshold_absolute": CORRELATION_THRESHOLD,
        "minimum_paired_observations": MINIMUM_PAIRED_OBSERVATIONS,
        "reference_dataset_shape": expected_shape,
        "annual_correlation_records": len(annual_df),
        "annual_valid_correlations": int(
            annual_df["valid_correlation"].sum()
        ),
        "pooled_correlation_records": len(pooled_df),
        "pooled_valid_correlations": int(
            pooled_df["valid_correlation"].sum()
        ),
        "pairs_high_in_all_three_pooled_seasons": int(
            comparison["pooled_high_in_all_three_seasons"].sum()
        ),
        "pairs_with_consistent_pooled_sign_across_seasons": int(
            comparison["pooled_sign_consistent"].sum()
        ),
        "season_summaries": season_summaries,
        "interpretation_limitations": [
            "Correlations describe associations, not causal relationships.",
            "Spatial and temporal autocorrelation reduce the independence "
            "of sampled observations.",
            "Pooled correlations may reflect spatial and temporal gradients.",
            "A high correlation does not automatically justify removing "
            "a physically distinct variable.",
            "Spearman correlations are calculated using pairwise "
            "available observations after ranking non-missing values "
            "within each variable.",
            "The common sampled indices improve positional comparability "
            "but do not remove missing-data or retrieval-quality effects.",
            "Results are exploratory and should inform, not replace, "
            "scientific feature selection."
        ],
    }

    summary_path = (
        OUTPUT_DIR / "ceres_cross_season_summary.json"
    )

    with open(summary_path, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print("\n" + "=" * 65)
    print("CROSS-SEASON ANALYSIS COMPLETED")
    print("=" * 65)
    print(f"Annual records: {len(annual_df):,}")
    print(f"Pooled records: {len(pooled_df):,}")
    print(
        "Pairs highly correlated in all three pooled seasons: "
        f"{summary['pairs_high_in_all_three_pooled_seasons']}"
    )
    print(f"\nReports saved in: {OUTPUT_DIR}")
    print(f"- {annual_path.name}")
    print(f"- {pooled_path.name}")
    print(f"- {comparison_path.name}")
    print(f"- {summary_path.name}")


if __name__ == "__main__":
    main()
