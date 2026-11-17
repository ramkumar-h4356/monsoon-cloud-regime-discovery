from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "results/tables/07_clustering/rainfall_association/"
    "within_cell_analysis/within_cell_year_pairwise_differences.csv"
)

OUTPUT_DIR = (
    ROOT / "results/tables/07_clustering/rainfall_association/"
    "within_cell_analysis"
)

OUTPUT_FILE = OUTPUT_DIR / "within_cell_minimum_support_sensitivity.csv"

if OUTPUT_FILE.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT_FILE}")

df = pd.read_csv(INPUT)

results = []

for threshold in [1, 5, 10]:
    selected = df[
        (df["observations_a"] >= threshold) &
        (df["observations_b"] >= threshold)
    ]

    for (variant, k, a, b), group in selected.groupby(
        ["variant", "k", "cluster_a", "cluster_b"]
    ):
        differences = group["mean_difference_a_minus_b_mm"]

        results.append({
            "minimum_observations_per_cluster": threshold,
            "variant": variant,
            "k": k,
            "cluster_a": a,
            "cluster_b": b,
            "matched_cell_years": len(group),
            "unique_cells": group[
                ["latitude", "longitude"]
            ].drop_duplicates().shape[0],
            "mean_paired_difference_mm": differences.mean(),
            "median_paired_difference_mm": differences.median(),
            "q25_difference_mm": differences.quantile(0.25),
            "q75_difference_mm": differences.quantile(0.75),
            "positive_difference_pct": (differences > 0).mean() * 100,
            "negative_difference_pct": (differences < 0).mean() * 100,
            "mean_observations_a": group["observations_a"].mean(),
            "mean_observations_b": group["observations_b"].mean(),
        })

result = pd.DataFrame(results)
result.to_csv(OUTPUT_FILE, index=False)

print("===== MINIMUM SUPPORT SENSITIVITY =====")
print(result.round(3).to_string(index=False))

print("\nOutput:", OUTPUT_FILE)
