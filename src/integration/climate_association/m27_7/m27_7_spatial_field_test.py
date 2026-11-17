"""M27.7 — Module 5: Spatial Field Significance Audit (Livezey-Chen Permutation).

Audits spatial teleconnections and field significance across India's 328 Tier 1 cells:
- Replaces naive binomial independence assumption with Livezey-Chen / Walker
  year-level spatial permutation testing (B=5,000 permutations).
- Preserves full 328-cell spatial covariance and spatial autocorrelation by permuting
  annual climate index values uniformly across all grid cells intact.
- Calculates empirical field significance p-values and 95th percentile null expectation
  for all 12 tests (4 tests x 3 seasons).
- Identifies and corrects false positives from the naive binomial test.
- Outputs corrected spatial field significance table.
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


def compute_livezey_chen_field_significance(
    b_permutations: int = 5_000,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Execute Livezey-Chen year-level spatial permutation test across all 12 tests."""
    loader = M277DataLoader()
    
    # 1. Load cell-level annual data
    m26_path = loader.m26_dir / "m26_cloud_rainfall_matched_primary.parquet"
    if not m26_path.exists():
        raise FileNotFoundError(f"Missing matched rainfall dataset: {m26_path}")

    logger.info("Loading daily matched primary dataset for spatial aggregation...")
    df_matched = pd.read_parquet(
        m26_path, columns=["season_id", "cell_index", "year", "rainfall_mm", "frac_r2"]
    )
    # Aggregate to cell-season-year means (12 years x 328 cells x 3 seasons = 11,808 rows)
    cell_annual = (
        df_matched.groupby(["season_id", "cell_index", "year"])[["rainfall_mm", "frac_r2"]]
        .mean()
        .reset_index()
    )

    # 2. Load aligned climate indices
    df_clim = loader.load_aligned_climate_data()

    # Pre-generate permutation indices (B, 12)
    np.random.seed(random_seed)
    perm_indices = np.array([np.random.permutation(12) for _ in range(b_permutations)])

    # Critical rho for n=12, df=10, alpha=0.05 two-tailed
    t_crit = float(stats.t.ppf(0.975, df=10))
    rho_crit = float(t_crit / np.sqrt(10.0 + t_crit**2))

    season_names = {0: "pre_monsoon", 1: "established_monsoon", 2: "post_monsoon"}
    tests = [
        ("Rainfall vs RONI", "rainfall_mm", "roni_anomaly"),
        ("Rainfall vs DMI", "rainfall_mm", "dmi_anomaly"),
        ("R2 Convection vs RONI", "frac_r2", "roni_anomaly"),
        ("R2 Convection vs DMI", "frac_r2", "dmi_anomaly"),
    ]

    # Load original M27 spatial field table for direct comparison
    orig_field_path = loader.project_root / "reports" / "integration" / "m27" / "tables" / "m27_spatial_field_significance.csv"
    orig_field_df = pd.read_csv(orig_field_path) if orig_field_path.exists() else None

    records: List[Dict[str, object]] = []

    for sid in [0, 1, 2]:
        sname = season_names[sid]
        sub_cell = cell_annual[cell_annual["season_id"] == sid]
        sub_clim = df_clim[df_clim["season_id"] == sid].set_index("year")

        for field_name, y_col, x_col in tests:
            # Pivot into (12 years, 328 cells)
            piv_y = sub_cell.pivot(index="year", columns="cell_index", values=y_col)
            years = piv_y.index.tolist()
            x_vec = sub_clim.loc[years, x_col].values

            # Rank data
            y_ranks = stats.rankdata(piv_y.values, axis=0)  # (12, 328)
            x_ranks = stats.rankdata(x_vec)  # (12,)

            # Centered deviations
            y_dev = y_ranks - np.mean(y_ranks, axis=0, keepdims=True)
            y_var = np.sum(y_dev**2, axis=0)
            x_dev = x_ranks - np.mean(x_ranks)
            x_var = np.sum(x_dev**2)

            # Observed rank correlations across 328 cells
            with np.errstate(divide="ignore", invalid="ignore"):
                denom = np.sqrt(x_var * y_var)
                obs_rhos = np.where(denom > 0, np.dot(x_dev, y_dev) / denom, 0.0)
            k_obs = int(np.sum(np.abs(obs_rhos) >= rho_crit))
            pct_obs = float((k_obs / len(piv_y.columns)) * 100.0)

            # Naive Binomial test (M27 method)
            binom_p = float(
                stats.binomtest(k_obs, len(piv_y.columns), 0.05, alternative="greater").pvalue
            )
            binom_verdict = binom_p <= 0.05

            # Livezey-Chen Spatial Permutations (preserving 328-cell spatial covariance)
            P_x_dev = x_dev[perm_indices]  # (B, 12)
            with np.errstate(divide="ignore", invalid="ignore"):
                perm_rhos = np.where(denom > 0, np.dot(P_x_dev, y_dev) / denom, 0.0)  # (B, 328)
            perm_k = np.sum(np.abs(perm_rhos) >= rho_crit, axis=1)  # (B,)

            p_lc = float((np.sum(perm_k >= k_obs) + 1) / (b_permutations + 1))
            lc_verdict = p_lc <= 0.05
            null_mean_k = float(np.mean(perm_k))
            null_mean_pct = float((null_mean_k / 328.0) * 100.0)
            null_95_k = float(np.percentile(perm_k, 95.0))
            null_95_pct = float((null_95_k / 328.0) * 100.0)

            # Determine audit classification
            if binom_verdict and not lc_verdict:
                audit_verdict = "DOWNGRADED_OVERSTATEMENT"
                justification = (
                    "Naive binomial test assumed spatial independence across 328 cells. "
                    "Livezey-Chen spatial permutation accounts for true spatial autocorrelation, "
                    f"raising p_field from {binom_p:.5f} to {p_lc:.5f} (non-significant)."
                )
            elif binom_verdict and lc_verdict:
                audit_verdict = "CONFIRMED_FIELD_SIGNIFICANT"
                justification = (
                    "Field significance confirmed under full spatial autocorrelation. "
                    f"Observed {k_obs} significant cells exceeds 95th percentile null expectation ({null_95_k:.1f})."
                )
            else:
                audit_verdict = "CONFIRMED_NON_SIGNIFICANT"
                justification = (
                    "Locally significant cell count is consistent with null spatial noise."
                )

            records.append({
                "season": sname,
                "season_id": sid,
                "field_test": field_name,
                "total_tier1_cells": len(piv_y.columns),
                "significant_cells_p05": k_obs,
                "significant_percentage": round(pct_obs, 2),
                "null_expectation_pct": 5.0,
                "naive_binomial_p": round(binom_p, 5),
                "naive_binomial_verdict": binom_verdict,
                "livezey_chen_null_mean_k": round(null_mean_k, 2),
                "livezey_chen_null_95th_k": round(null_95_k, 2),
                "livezey_chen_null_95th_pct": round(null_95_pct, 2),
                "livezey_chen_p_field": round(p_lc, 5),
                "livezey_chen_verdict": lc_verdict,
                "audit_verdict": audit_verdict,
                "scientific_justification": justification,
            })

    out_df = pd.DataFrame(records)
    out_path = M27_7_DIR / "tables" / "m27_7_corrected_spatial_field_significance.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    logger.info(f"Generated Corrected Spatial Field Significance table: {out_path} ({len(out_df)} rows)")
    return out_df


if __name__ == "__main__":
    df = compute_livezey_chen_field_significance(b_permutations=5_000)
    print("M27.7 Corrected Spatial Field Significance Summary:")
    print(
        df[
            [
                "season",
                "field_test",
                "significant_cells_p05",
                "significant_percentage",
                "naive_binomial_p",
                "livezey_chen_p_field",
                "livezey_chen_verdict",
                "audit_verdict",
            ]
        ].to_string()
    )
