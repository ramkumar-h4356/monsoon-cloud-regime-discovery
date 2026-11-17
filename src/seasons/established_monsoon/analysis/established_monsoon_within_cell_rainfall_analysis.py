from pathlib import Path
import itertools
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "results/tables/07_clustering/rainfall_association/"
    "established_monsoon_cloud_rainfall_matched.csv"
)

OUTPUT_DIR = (
    ROOT / "results/tables/07_clustering/rainfall_association/"
    "within_cell_analysis"
)

PAIRED_FILE = OUTPUT_DIR / "within_cell_year_pairwise_differences.csv"
ANNUAL_FILE = OUTPUT_DIR / "annual_within_cell_pairwise_summary.csv"
OVERALL_FILE = OUTPUT_DIR / "overall_within_cell_pairwise_summary.csv"

MODELS = [
    ("baseline", 2, "baseline_k2"),
    ("log_sensitivity", 2, "log_k2"),
    ("log_sensitivity", 3, "log_k3"),
]

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def summarize(group, keys):
    records = []

    for group_key, part in group.groupby(keys, sort=True):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)

        differences = part["mean_difference_a_minus_b_mm"].to_numpy()

        record = dict(zip(keys, group_key))
        record.update({
            "matched_cell_years": len(part),
            "mean_paired_difference_mm": float(np.mean(differences)),
            "median_paired_difference_mm": float(np.median(differences)),
            "q25_paired_difference_mm": float(np.quantile(differences, 0.25)),
            "q75_paired_difference_mm": float(np.quantile(differences, 0.75)),
            "positive_difference_pct": float(np.mean(differences > 0) * 100),
            "negative_difference_pct": float(np.mean(differences < 0) * 100),
            "zero_difference_pct": float(np.mean(differences == 0) * 100),
            "mean_observations_a": float(part["observations_a"].mean()),
            "mean_observations_b": float(part["observations_b"].mean()),
            "minimum_observations_a": int(part["observations_a"].min()),
            "minimum_observations_b": int(part["observations_b"].min()),
        })
        records.append(record)

    return pd.DataFrame(records)

def main():
    for path in [PAIRED_FILE, ANNUAL_FILE, OVERALL_FILE]:
        require(not path.exists(), f"Refusing to overwrite: {path}")

    frame = pd.read_csv(INPUT)
    frame["date"] = pd.to_datetime(frame["date"])
    frame["year"] = frame["year"].astype(int)

    cell_keys = ["year", "latitude", "longitude"]

    all_pairs = []

    for variant, k, label_column in MODELS:
        print(f"Analyzing {variant}, K={k}")

        grouped = (
            frame.groupby(cell_keys + [label_column], observed=True)
            .agg(
                mean_rainfall_mm=("rainfall_mm", "mean"),
                observations=("rainfall_mm", "size")
            )
            .reset_index()
        )

        means = grouped.pivot(
            index=cell_keys,
            columns=label_column,
            values="mean_rainfall_mm"
        )

        counts = grouped.pivot(
            index=cell_keys,
            columns=label_column,
            values="observations"
        )

        for a, b in itertools.combinations(range(k), 2):
            if a not in means.columns or b not in means.columns:
                continue

            valid = means[[a, b]].notna().all(axis=1)

            paired = pd.DataFrame({
                "year": means.index.get_level_values("year")[valid],
                "latitude": means.index.get_level_values("latitude")[valid],
                "longitude": means.index.get_level_values("longitude")[valid],
                "mean_rainfall_a_mm": means.loc[valid, a].to_numpy(),
                "mean_rainfall_b_mm": means.loc[valid, b].to_numpy(),
                "observations_a": counts.loc[valid, a].to_numpy(),
                "observations_b": counts.loc[valid, b].to_numpy(),
            })

            paired["mean_difference_a_minus_b_mm"] = (
                paired["mean_rainfall_a_mm"] -
                paired["mean_rainfall_b_mm"]
            )
            paired["variant"] = variant
            paired["k"] = k
            paired["cluster_a"] = a
            paired["cluster_b"] = b

            all_pairs.append(paired)

    require(len(all_pairs) > 0, "No paired cell-year comparisons found.")

    paired_all = pd.concat(all_pairs, ignore_index=True)

    annual = summarize(
        paired_all,
        ["variant", "k", "year", "cluster_a", "cluster_b"]
    )

    overall = summarize(
        paired_all,
        ["variant", "k", "cluster_a", "cluster_b"]
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    paired_all.to_csv(PAIRED_FILE, index=False)
    annual.to_csv(ANNUAL_FILE, index=False)
    overall.to_csv(OVERALL_FILE, index=False)

    print("\n===== OVERALL WITHIN-CELL COMPARISON =====")
    print(overall.round(3).to_string(index=False))

    print("\n===== ANNUAL WITHIN-CELL COMPARISON =====")
    print(annual.round(3).to_string(index=False))

    print("\n===== SUPPORT =====")
    print(
        paired_all.groupby(
            ["variant", "k", "cluster_a", "cluster_b"]
        ).agg(
            paired_cell_years=("year", "size"),
            unique_cells=("latitude", lambda x: len(set(
                zip(x, paired_all.loc[x.index, "longitude"])
            ))),
            mean_observations_per_cluster_a=("observations_a", "mean"),
            mean_observations_per_cluster_b=("observations_b", "mean")
        ).round(2).to_string()
    )

    print("\nOutputs:")
    print(PAIRED_FILE)
    print(ANNUAL_FILE)
    print(OVERALL_FILE)

if __name__ == "__main__":
    main()
