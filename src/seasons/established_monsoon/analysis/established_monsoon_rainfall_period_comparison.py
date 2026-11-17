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

OUTPUT_FILE = OUTPUT_DIR / "paired_spatial_period_rainfall_contrasts.csv"

if OUTPUT_FILE.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT_FILE}")

df = pd.read_csv(INPUT)

df = df[
    (df["observations_a"] >= 5) &
    (df["observations_b"] >= 5)
].copy()

df["period"] = np.where(
    df["year"] <= 2016,
    "2010_2016",
    "2017_2021"
)

cell_keys = [
    "variant", "k", "cluster_a", "cluster_b",
    "latitude", "longitude", "period"
]

cell_period = (
    df.groupby(cell_keys)
    .agg(
        mean_difference_mm=("mean_difference_a_minus_b_mm", "mean"),
        matched_years=("year", "nunique"),
        total_observations_a=("observations_a", "sum"),
        total_observations_b=("observations_b", "sum")
    )
    .reset_index()
)

index_keys = [
    "variant", "k", "cluster_a", "cluster_b",
    "latitude", "longitude"
]

wide = cell_period.pivot(
    index=index_keys,
    columns="period",
    values="mean_difference_mm"
).dropna(
    subset=["2010_2016", "2017_2021"]
).reset_index()

wide["change_in_difference_mm"] = (
    wide["2017_2021"] - wide["2010_2016"]
)

wide["direction_changed"] = (
    np.sign(wide["2010_2016"]) !=
    np.sign(wide["2017_2021"])
)

summary = (
    wide.groupby(
        ["variant", "k", "cluster_a", "cluster_b"]
    )
    .agg(
        paired_cells=("latitude", "size"),
        pre_period_mean_difference_mm=("2010_2016", "mean"),
        post_period_mean_difference_mm=("2017_2021", "mean"),
        mean_change_mm=("change_in_difference_mm", "mean"),
        median_change_mm=("change_in_difference_mm", "median"),
        q25_change_mm=("change_in_difference_mm",
                       lambda x: x.quantile(0.25)),
        q75_change_mm=("change_in_difference_mm",
                       lambda x: x.quantile(0.75)),
        cells_with_direction_change=("direction_changed", "sum"),
        positive_change_pct=("change_in_difference_mm",
                             lambda x: (x > 0).mean() * 100),
        negative_change_pct=("change_in_difference_mm",
                             lambda x: (x < 0).mean() * 100)
    )
    .reset_index()
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

wide.to_csv(
    OUTPUT_DIR / "paired_spatial_period_rainfall_contrasts_by_cell.csv",
    index=False
)
summary.to_csv(OUTPUT_FILE, index=False)

print("===== PAIRED SPATIAL PERIOD COMPARISON =====")
print(summary.round(3).to_string(index=False))

print("\n===== MATCHED CELL DETAILS =====")
print("Total paired cell comparisons:", len(wide))
print("\nOutput:", OUTPUT_FILE)
