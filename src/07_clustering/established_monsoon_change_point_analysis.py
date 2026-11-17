from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "results/tables/07_clustering/annual_coverage_matched/annual_coverage_matched_cluster_prevalence_corrected.csv"
OUT = ROOT / "results/tables/07_clustering/change_point_analysis"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT)
df.columns = [c.strip() for c in df.columns]

def find_col(candidates, required=True):
    lower = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    if required:
        raise ValueError(
            f"Could not identify column from {candidates}. "
            f"Available columns: {list(df.columns)}"
        )
    return None

year_col = find_col(["year"])
threshold_col = find_col(["threshold_pct"])
variant_col = find_col(["variant"])
k_col = find_col(["k"])
cluster_col = find_col(["cluster"])

value_col = find_col([
    "equal_cell_mean_prevalence_pct",
    "equal_cell_mean_pct",
    "equal_cell_prevalence_pct",
    "mean_equal_cell_prevalence_pct"
], required=False)

if value_col is None:
    possible = [
        c for c in df.columns
        if "equal" in c.lower() and "mean" in c.lower()
    ]
    if len(possible) == 1:
        value_col = possible[0]
    else:
        raise ValueError(
            "Could not identify the equal-cell prevalence column. "
            f"Available columns: {list(df.columns)}"
        )

df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
df = df.dropna(subset=[year_col, value_col]).copy()
df[year_col] = df[year_col].astype(int)

def fit_model(y, X, extra_parameters=0):
    n = len(y)
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    residuals = y - X @ beta
    sse = max(float(np.sum(residuals ** 2)), 1e-12)

    # Regression coefficients + residual variance + breakpoint search parameter.
    p = X.shape[1]
    parameter_count = p + 1 + extra_parameters

    aic = n * np.log(sse / n) + 2 * parameter_count
    bic = n * np.log(sse / n) + parameter_count * np.log(n)

    if n - parameter_count - 1 <= 0:
        aicc = np.inf
    else:
        aicc = aic + (
            2 * parameter_count * (parameter_count + 1)
            / (n - parameter_count - 1)
        )

    return {
        "sse": sse,
        "aicc": aicc,
        "bic": bic,
        "parameter_count": parameter_count
    }

all_results = []

group_cols = [threshold_col, variant_col, k_col, cluster_col]

for keys, group in df.groupby(group_cols):
    group = group.groupby(year_col, as_index=False)[value_col].mean()
    group = group.sort_values(year_col)

    years = group[year_col].to_numpy(dtype=float)
    y = group[value_col].to_numpy(dtype=float)

    if len(y) != 12 or not np.array_equal(years, np.arange(2010, 2022)):
        print(f"WARNING: unexpected annual series for {keys}: {years.tolist()}")

    if len(y) < 7:
        continue

    t = years - years.mean()

    # No-break models
    models = []

    constant = fit_model(y, np.ones((len(y), 1)))
    models.append({
        "model": "constant",
        "break_boundary": None,
        **constant
    })

    linear = fit_model(y, np.column_stack([np.ones(len(y)), t]))
    models.append({
        "model": "linear",
        "break_boundary": None,
        **linear
    })

    # Candidate breakpoints: at least 3 annual observations on either side.
    for split in range(3, len(y) - 2):
        boundary = f"{int(years[split - 1])}-{int(years[split])}"
        post = (np.arange(len(y)) >= split).astype(float)

        # Step model: separate means before and after the boundary.
        X_step = np.column_stack([np.ones(len(y)), post])
        step = fit_model(y, X_step, extra_parameters=1)
        models.append({
            "model": "step",
            "break_boundary": boundary,
            **step
        })

        # Segmented trend: separate intercept and slope after the boundary.
        t_after = np.where(post == 1, t - t[split], 0.0)
        X_segmented = np.column_stack([
            np.ones(len(y)),
            t,
            post,
            t_after
        ])
        segmented = fit_model(y, X_segmented, extra_parameters=1)
        models.append({
            "model": "segmented_trend",
            "break_boundary": boundary,
            **segmented
        })

    result = pd.DataFrame(models)
    result["delta_aicc"] = result["aicc"] - result["aicc"].min()
    result["delta_bic"] = result["bic"] - result["bic"].min()

    for col, value in zip(group_cols, keys):
        result[col] = value

    all_results.append(result)

if not all_results:
    raise RuntimeError("No valid annual series were analysed.")

results = pd.concat(all_results, ignore_index=True)

results = results[
    group_cols + [
        "model", "break_boundary", "sse",
        "parameter_count", "aicc", "delta_aicc",
        "bic", "delta_bic"
    ]
]

results.to_csv(OUT / "all_candidate_model_scores.csv", index=False)

best_aicc = (
    results.sort_values("aicc")
    .groupby(group_cols, as_index=False)
    .first()
)
best_bic = (
    results.sort_values("bic")
    .groupby(group_cols, as_index=False)
    .first()
)

best_aicc["selection_criterion"] = "AICc"
best_bic["selection_criterion"] = "BIC"

best = pd.concat([best_aicc, best_bic], ignore_index=True)
best.to_csv(OUT / "best_model_by_series.csv", index=False)

print("\n===== BEST MODEL BY AICc AND BIC =====")
print(best.to_string(index=False))

print("\n===== 2016-2017 BREAKPOINT COMPARISON =====")
target = results[results["break_boundary"] == "2016-2017"]
print(
    target.sort_values(group_cols + ["aicc"])
    .to_string(index=False)
)

print("\n===== VALIDATION =====")
print("Annual input rows:", len(df))
print("Series analysed:", len(all_results))
print("Candidate model records:", len(results))
print("Value column:", value_col)
print("Outputs:", OUT)
