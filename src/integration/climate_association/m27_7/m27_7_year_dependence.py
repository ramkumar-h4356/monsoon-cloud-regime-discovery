"""M27.7 — Module 4: Year Dependence and Cross-Seasonal Pooling Audit.

Audits cross-seasonal pooling in original M27:
- Evaluates repeated-year dependence across 12 calendar years (pre-monsoon, established monsoon, post-monsoon).
- Computes intra-year cross-season correlations (pre-est, est-post, pre-post).
- Calculates effective degrees of freedom (N_eff) accounting for intra-year persistence.
- Implements year-block permutation testing (permuting 12 calendar year blocks intact, B=100,000).
- Compares original naive p-values vs block-permuted and N_eff-adjusted p-values.
- Applies Benjamini-Hochberg FDR adjustment across pooled tests.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from src.integration.climate_association.m27_7.m27_7_data_loader import (
    M277DataLoader,
    PROJECT_ROOT,
    M27_7_DIR,
)

logger = logging.getLogger(__name__)


def compute_intra_year_correlations(
    df: pd.DataFrame, metric_col: str
) -> Tuple[float, float, float, float]:
    """Compute pairwise seasonal Pearson correlations across years and their mean."""
    piv = df.pivot(index="year", columns="season", values=metric_col)
    # Ensure all 3 seasons exist
    seasons = ["pre_monsoon", "established_monsoon", "post_monsoon"]
    for s in seasons:
        if s not in piv.columns:
            return 0.0, 0.0, 0.0, 0.0

    r_pre_est, _ = stats.pearsonr(piv["pre_monsoon"], piv["established_monsoon"])
    r_est_post, _ = stats.pearsonr(piv["established_monsoon"], piv["post_monsoon"])
    r_pre_post, _ = stats.pearsonr(piv["pre_monsoon"], piv["post_monsoon"])

    mean_r = float(np.mean([r_pre_est, r_est_post, r_pre_post]))
    return float(r_pre_est), float(r_est_post), float(r_pre_post), mean_r


def compute_effective_n(n_total: int, k_seasons: int, mean_r: float) -> Tuple[float, float]:
    """Compute effective sample size N_eff and effective degrees of freedom df_eff."""
    # VIF = 1 + (k - 1) * max(0, mean_r)
    # If correlation is negative, conservative approach sets VIF = 1
    vif = 1.0 + (k_seasons - 1) * max(0.0, mean_r)
    n_eff = float(n_total / vif)
    df_eff = max(1.0, n_eff - 2.0)
    return n_eff, df_eff


def compute_t_pvalue(rho: float, df: float) -> float:
    """Compute two-sided p-value from Spearman rho and degrees of freedom."""
    if abs(rho) >= 1.0:
        return 0.0
    t_stat = rho * np.sqrt(df / (1.0 - rho**2))
    p_val = float(2.0 * (1.0 - stats.t.cdf(np.abs(t_stat), df=df)))
    return p_val


def run_year_block_permutation(
    y_vals: np.ndarray,
    x_vals: np.ndarray,
    b_permutations: int = 100_000,
    random_seed: int = 42,
) -> Tuple[float, float]:
    """Run fast vectorized year-block permutation test permuting 12 year-triplets intact."""
    assert len(y_vals) == 36 and len(x_vals) == 36
    # Reshape into (12 years, 3 seasons)
    y_mat = y_vals.reshape(12, 3)
    x_mat = x_vals.reshape(12, 3)

    y_ranks = stats.rankdata(y_vals)
    x_ranks_mat = stats.rankdata(x_vals).reshape(12, 3)

    y_dev = y_ranks - np.mean(y_ranks)
    y_var = np.sum(y_dev**2)

    np.random.seed(random_seed)
    perm_indices = np.array([np.random.permutation(12) for _ in range(b_permutations)])

    x_perm_ranks = x_ranks_mat[perm_indices, :]  # (B, 12, 3)
    x_perm_flat = x_perm_ranks.reshape(b_permutations, 36)

    x_dev = x_perm_flat - np.mean(x_ranks_mat)
    num = np.dot(x_dev, y_dev)
    x_var = np.sum(x_dev**2, axis=1)
    sim_rhos = num / np.sqrt(y_var * x_var)

    obs_rho, _ = stats.spearmanr(y_vals, x_vals)
    p_block = float((np.sum(np.abs(sim_rhos) >= np.abs(obs_rho)) + 1) / (b_permutations + 1))
    return float(obs_rho), p_block


def benjamini_hochberg(p_values: List[float]) -> List[float]:
    """Compute BH FDR adjusted q-values."""
    p_arr = np.asarray(p_values, dtype=float)
    n = len(p_arr)
    if n == 0:
        return []
    sorted_indices = np.argsort(p_arr)
    sorted_p = p_arr[sorted_indices]
    q_vals = np.zeros(n, dtype=float)
    min_q = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        q = sorted_p[i] * n / rank
        if q < min_q:
            min_q = q
        q_vals[i] = min_q
    orig_q = np.zeros(n, dtype=float)
    orig_q[sorted_indices] = q_vals
    return [float(x) for x in np.clip(orig_q, 0.0, 1.0)]


def audit_year_dependence() -> pd.DataFrame:
    """Execute complete year dependence audit across pooled regime and rainfall tests."""
    loader = M277DataLoader()
    prev = loader.load_regime_prevalence()
    rain = loader.load_rainfall_metrics()
    clim = loader.load_aligned_climate_data()
    orig_regime, orig_rain, _ = loader.load_original_correlation_tables()

    # Merge into a single pooled dataset
    df_reg = pd.merge(prev, clim, on=["year", "season", "season_id"]).sort_values(
        ["year", "season_id"]
    ).reset_index(drop=True)
    df_rain = pd.merge(rain, clim, on=["year", "season", "season_id"]).sort_values(
        ["year", "season_id"]
    ).reset_index(drop=True)

    results = []

    # 1. Regime Prevalence Audits (Domain level)
    regimes = [
        ("R0", "p_R0_domain", "R0: Mixed Convective & Congestus"),
        ("R1", "p_R1_domain", "R1: Boundary-Layer Shallow Cumulus"),
        ("R2", "p_R2_domain", "R2: Deep Convective Storm Cores"),
        ("R3", "p_R3_domain", "R3: Thin Cirrus & Anvil Outflow"),
    ]

    for reg_id, col, name in regimes:
        r_pre_est, r_est_post, r_pre_post, mean_r = compute_intra_year_correlations(df_reg, col)
        n_eff, df_eff = compute_effective_n(36, 3, mean_r)

        # RONI
        y_vals = df_reg[col].values
        x_roni = df_reg["roni_anomaly"].values
        rho_roni, p_block_roni = run_year_block_permutation(y_vals, x_roni, b_permutations=100_000)
        p_neff_roni = compute_t_pvalue(rho_roni, df_eff)

        # Original M27 pooled row
        orig_row = orig_regime[
            (orig_regime["season"] == "pooled_three_seasons") & (orig_regime["regime"] == reg_id)
        ]
        orig_p_roni = orig_row["p_roni_perm"].values[0] if len(orig_row) > 0 else np.nan

        results.append({
            "target_type": "regime_prevalence",
            "metric": reg_id,
            "metric_description": name,
            "climate_index": "RONI",
            "pooled_n": 36,
            "rho_spearman": rho_roni,
            "orig_p_naive_perm": orig_p_roni,
            "r_pre_est": r_pre_est,
            "r_est_post": r_est_post,
            "r_pre_post": r_pre_post,
            "intra_year_mean_r": mean_r,
            "effective_n": n_eff,
            "effective_df": df_eff,
            "p_neff_adjusted": p_neff_roni,
            "p_year_block_perm": p_block_roni,
        })

        # DMI
        x_dmi = df_reg["dmi_anomaly"].values
        rho_dmi, p_block_dmi = run_year_block_permutation(y_vals, x_dmi, b_permutations=100_000)
        p_neff_dmi = compute_t_pvalue(rho_dmi, df_eff)
        orig_p_dmi = orig_row["p_dmi_perm"].values[0] if len(orig_row) > 0 else np.nan

        results.append({
            "target_type": "regime_prevalence",
            "metric": reg_id,
            "metric_description": name,
            "climate_index": "DMI",
            "pooled_n": 36,
            "rho_spearman": rho_dmi,
            "orig_p_naive_perm": orig_p_dmi,
            "r_pre_est": r_pre_est,
            "r_est_post": r_est_post,
            "r_pre_post": r_pre_post,
            "intra_year_mean_r": mean_r,
            "effective_n": n_eff,
            "effective_df": df_eff,
            "p_neff_adjusted": p_neff_dmi,
            "p_year_block_perm": p_block_dmi,
        })

    # 2. Key Rainfall Metrics
    rain_metrics = [
        ("mean_rainfall_mm", "mean_rainfall_mm", "Terrestrial Mean Rainfall (mm/day)"),
        ("rainfall_anomaly_mm", "rainfall_anomaly_mm", "Rainfall Anomaly (mm/day)"),
        ("wet_day_freq_25mm", "wet_day_freq_25mm", "Wet-Day Frequency >= 25mm (fraction)"),
        ("cond_mean_R2", "cond_mean_R2", "R2 Regime Conditional Mean (mm/day)"),
        ("vol_contrib_R2", "vol_contrib_R2", "R2 Volume Contribution (%)"),
        ("cond_mean_R1", "cond_mean_R1", "R1 Regime Conditional Mean (mm/day)"),
    ]

    for m_id, col, desc in rain_metrics:
        r_pre_est, r_est_post, r_pre_post, mean_r = compute_intra_year_correlations(df_rain, col)
        n_eff, df_eff = compute_effective_n(36, 3, mean_r)

        # RONI
        y_vals = df_rain[col].values
        x_roni = df_rain["roni_anomaly"].values
        rho_roni, p_block_roni = run_year_block_permutation(y_vals, x_roni, b_permutations=100_000)
        p_neff_roni = compute_t_pvalue(rho_roni, df_eff)

        # Find original pooled row if exists
        orig_row = orig_rain[
            (orig_rain["season"] == "pooled_three_seasons") & (orig_rain["metric"] == col)
        ]
        orig_p_roni = orig_row["p_roni_perm"].values[0] if len(orig_row) > 0 else np.nan

        results.append({
            "target_type": "rainfall_metric",
            "metric": m_id,
            "metric_description": desc,
            "climate_index": "RONI",
            "pooled_n": 36,
            "rho_spearman": rho_roni,
            "orig_p_naive_perm": orig_p_roni,
            "r_pre_est": r_pre_est,
            "r_est_post": r_est_post,
            "r_pre_post": r_pre_post,
            "intra_year_mean_r": mean_r,
            "effective_n": n_eff,
            "effective_df": df_eff,
            "p_neff_adjusted": p_neff_roni,
            "p_year_block_perm": p_block_roni,
        })

        # DMI
        x_dmi = df_rain["dmi_anomaly"].values
        rho_dmi, p_block_dmi = run_year_block_permutation(y_vals, x_dmi, b_permutations=100_000)
        p_neff_dmi = compute_t_pvalue(rho_dmi, df_eff)
        orig_p_dmi = orig_row["p_dmi_perm"].values[0] if len(orig_row) > 0 else np.nan

        results.append({
            "target_type": "rainfall_metric",
            "metric": m_id,
            "metric_description": desc,
            "climate_index": "DMI",
            "pooled_n": 36,
            "rho_spearman": rho_dmi,
            "orig_p_naive_perm": orig_p_dmi,
            "r_pre_est": r_pre_est,
            "r_est_post": r_est_post,
            "r_pre_post": r_pre_post,
            "intra_year_mean_r": mean_r,
            "effective_n": n_eff,
            "effective_df": df_eff,
            "p_neff_adjusted": p_neff_dmi,
            "p_year_block_perm": p_block_dmi,
        })

    out_df = pd.DataFrame(results)

    # Compute BH FDR across year-block p-values
    out_df["q_year_block_fdr"] = benjamini_hochberg(out_df["p_year_block_perm"].tolist())

    # Add definitive scientific status
    conclusions = []
    for _, row in out_df.iterrows():
        p_b = row["p_year_block_perm"]
        q_b = row["q_year_block_fdr"]
        p_neff = row["p_neff_adjusted"]

        if q_b <= 0.05 and p_neff <= 0.05:
            conclusions.append("CONFIRMED_SIGNIFICANT")
        elif q_b <= 0.10 or p_b <= 0.05:
            conclusions.append("EXPLORATORY_TENDENCY")
        else:
            conclusions.append("NON_SIGNIFICANT")

    out_df["audit_verdict"] = conclusions

    # Format numbers for clean presentation
    numeric_cols = [
        "rho_spearman", "orig_p_naive_perm", "r_pre_est", "r_est_post", "r_pre_post",
        "intra_year_mean_r", "effective_n", "effective_df", "p_neff_adjusted",
        "p_year_block_perm", "q_year_block_fdr"
    ]
    for c in numeric_cols:
        out_df[c] = out_df[c].round(5)

    out_path = M27_7_DIR / "tables" / "m27_7_year_dependence_audit.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    logger.info(f"Generated Year Dependence Audit table: {out_path} ({len(out_df)} rows)")
    return out_df


if __name__ == "__main__":
    df = audit_year_dependence()
    print("M27.7 Year Dependence Audit Summary:")
    print(df[["metric", "climate_index", "intra_year_mean_r", "effective_n", "orig_p_naive_perm", "p_year_block_perm", "q_year_block_fdr", "audit_verdict"]].to_string())
