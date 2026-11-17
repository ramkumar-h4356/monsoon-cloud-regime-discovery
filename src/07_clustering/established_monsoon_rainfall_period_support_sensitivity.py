from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "results/tables/07_clustering/rainfall_association/"
    "within_cell_analysis/within_cell_year_pairwise_differences.csv"
)

OUTPUT_DIR = (
    ROOT / "results/tables/07_clustering/rainfall_association/"
    "within_cell_analysis/period_comparison"
)

OUTPUT = OUTPUT_DIR / "period_support_sensitivity.csv"

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

df = pd.read_csv(INPUT)

df = df[
    (df["observations_a"] >= 5) &
    (df["observations_b"] >= 5)
].copy()

df["period"] = np.where(
    df["year"] <= 2016, "2010_2016", "2017_2021"
)

keys = [
    "variant", "k", "cluster_a", "cluster_b",
    "latitude", "longitude", "period"
]

cell_period = (
    df.groupby(keys)
    .agg(
        mean_difference_mm=(
            "mean_difference_a_minus_b_mm", "mean"
        ),
        qualifying_years=("year", "nunique")
    )
    .reset_index()
)

index_keys = [
    "variant", "k", "cluster_a", "cluster_b",
    "latitude", "longitude"
]

wide_difference = cell_period.pivot(
    index=index_keys,
    columns="period",
    values="mean_difference_mm"
)

wide_years = cell_period.pivot(
    index=index_keys,
    columns="period",
    values="qualifying_years"
)

records = []

for threshold in [1, 2, 3, 4]:
    valid = (
        wide_difference[["2010_2016", "2017_2021"]].notna().all(axis=1)
        & (wide_years["2010_2016"] >= threshold)
        & (wide_years["2017_2021"] >= threshold)
    )

    selected = wide_difference.loc[valid]

    for (variant, k, a, b), group in selected.groupby(
        level=["variant", "k", "cluster_a", "cluster_b"]
    ):
        pre = group["2010_2016"]
        post = group["2017_2021"]
        change = post - pre

        records.append({
            "minimum_qualifying_years_per_period": threshold,
            "variant": variant,
            "k": k,
            "cluster_a": a,
            "cluster_b": b,
            "paired_cells": len(group),
            "pre_mean_difference_mm": pre.mean(),
            "post_mean_difference_mm": post.mean(),
            "mean_change_mm": change.mean(),
            "median_change_mm": change.median(),
            "cells_with_positive_change_pct": (change > 0).mean() * 100,
            "cells_with_negative_change_pct": (change < 0).mean() * 100
        })

result = pd.DataFrame(records)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT, index=False)

print("===== PERIOD SUPPORT SENSITIVITY =====")
print(result.round(3).to_string(index=False))
print("\nOutput:", OUTPUT)
