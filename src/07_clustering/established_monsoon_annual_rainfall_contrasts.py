from pathlib import Path
import itertools
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

INPUT = (
    ROOT / "results/tables/07_clustering/rainfall_association/"
    "established_monsoon_rainfall_by_year.csv"
)

OUTPUT = (
    ROOT / "results/tables/07_clustering/rainfall_association/"
    "established_monsoon_annual_pairwise_contrasts.csv"
)

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite: {OUTPUT}")

df = pd.read_csv(INPUT)
rows = []

for (variant, k), group in df.groupby(["variant", "k"]):
    for year, yearly in group.groupby("year"):
        yearly = yearly.set_index("cluster")

        clusters = sorted(yearly.index)

        for a, b in itertools.combinations(clusters, 2):
            x = yearly.loc[a]
            y = yearly.loc[b]

            rows.append({
                "variant": variant,
                "k": k,
                "year": year,
                "cluster_a": a,
                "cluster_b": b,
                "observations_a": int(x["observations"]),
                "observations_b": int(y["observations"]),
                "mean_difference_a_minus_b_mm":
                    x["mean_mm"] - y["mean_mm"],
                "median_difference_a_minus_b_mm":
                    x["median_mm"] - y["median_mm"],
                "wet_day_difference_a_minus_b_pp":
                    x["wet_day_pct"] - y["wet_day_pct"],
                "positive_rainfall_difference_a_minus_b_pp":
                    x["positive_rainfall_pct"] -
                    y["positive_rainfall_pct"]
            })

result = pd.DataFrame(rows)
result.to_csv(OUTPUT, index=False)

print("Annual pairwise comparisons:", len(result))
print("\n===== DIRECTION CONSISTENCY =====")

for (variant, k, a, b), group in result.groupby(
    ["variant", "k", "cluster_a", "cluster_b"]
):
    print(
        f"{variant}, K={k}, C{a}-C{b}: "
        f"mean difference positive in "
        f"{(group['mean_difference_a_minus_b_mm'] > 0).sum()}/"
        f"{len(group)} years; "
        f"wet-day difference positive in "
        f"{(group['wet_day_difference_a_minus_b_pp'] > 0).sum()}/"
        f"{len(group)} years"
    )

print("\n===== ANNUAL CONTRAST TABLE =====")
print(result.round(3).to_string(index=False))

print("\nOutput:", OUTPUT)
