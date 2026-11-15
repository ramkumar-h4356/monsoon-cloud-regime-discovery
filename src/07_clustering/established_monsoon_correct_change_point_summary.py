from pathlib import Path
import pandas as pd

root = Path.cwd()
folder = root / "results/tables/07_clustering/change_point_analysis"

scores = pd.read_csv(folder / "all_candidate_model_scores.csv")

groups = ["threshold_pct", "variant", "k", "cluster"]

# Select complete rows rather than using groupby().first(),
# which can incorrectly fill missing breakpoint values.
best_aicc = (
    scores.sort_values("aicc")
    .groupby(groups, sort=False)
    .head(1)
    .copy()
)
best_aicc["selection_criterion"] = "AICc"

best_bic = (
    scores.sort_values("bic")
    .groupby(groups, sort=False)
    .head(1)
    .copy()
)
best_bic["selection_criterion"] = "BIC"

best = pd.concat([best_aicc, best_bic], ignore_index=True)
best.to_csv(folder / "best_model_by_series_corrected.csv", index=False)

# Show all candidate models for the three-cluster log-sensitivity analysis.
focus = scores[
    (scores["variant"] == "log_sensitivity") &
    (scores["k"] == 3)
].sort_values(groups + ["aicc"])

focus.to_csv(folder / "log_k3_candidate_ranking.csv", index=False)

print("\n===== CORRECTED WINNING MODELS =====")
print(best[groups + [
    "model", "break_boundary", "aicc", "bic",
    "selection_criterion"
]].to_string(index=False))

print("\n===== LOG K3 CANDIDATE RANKING =====")
for keys, group in focus.groupby(
    ["threshold_pct", "cluster"], sort=True
):
    print(f"\nCoverage={keys[0]}%, Cluster={keys[1]}")
    print(group[[
        "model", "break_boundary", "aicc", "delta_aicc",
        "bic", "delta_bic"
    ]].sort_values("aicc").to_string(index=False))

print("\nCorrected reports saved:", folder)
