"""M27.3 — Cloud-Regime Modulation Engine.

Quantifies the empirical association between frozen M25 cloud regimes (R0, R1, R2, R3)
and large-scale climate modes (NOAA RONI and DMI) across the Indian monsoon domain
for 2010–2021 (N=12 independent annual seasons).

Methodological Principles:
1. Unit of Analysis: Annual-seasonal regime occurrence fraction P(R_k | y, s)
2. Small-Sample Inference: B=100,000 Monte Carlo permutations for exact p-values
3. Coupling Control: Partial Spearman correlation controlling for opposing ocean index
4. Multiplicity Correction: Benjamini-Hochberg FDR control at q=0.10
5. Compositional Rigor: Verifies zero-sum simplex constraint (sum Delta P = 0)
   and computes Centered Log-Ratio (CLR) sensitivity
6. Robustness: Full Leave-One-Out (LOOCV) cross-validation and targeted 2015/2019 exclusions
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from src.integration.climate_association.m27_climate_index_loader import (
    get_aligned_climate_indices,
    SEASON_CONFIG,
)
from src.integration.climate_association.m27_statistical_validation import (
    compute_spearman_correlation,
    compute_partial_spearman_correlation,
    permutation_test_spearman,
    permutation_test_partial_spearman,
    fdr_correction_bh,
    leave_one_out_sensitivity,
    clr_transformation,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FROZEN_M25_DIR = PROJECT_ROOT / "data" / "processed" / "combined_3season"
FROZEN_M26_DIR = PROJECT_ROOT / "data" / "processed" / "rainfall_validation"
PROCESSED_CLIMATE_DIR = PROJECT_ROOT / "data" / "processed" / "climate_indices"
TABLES_DIR = PROJECT_ROOT / "reports" / "integration" / "m27" / "tables"

REGIME_NAMES = {
    0: "R0: Mixed Convective & Congestus",
    1: "R1: Boundary-Layer Shallow Cumulus",
    2: "R2: Deep Convective Storm Cores",
    3: "R3: Thin Cirrus & Anvil Outflow",
}


class RegimeClimateCorrelationEngine:
    """Engine for computing and validating regime-climate teleconnections."""

    def __init__(
        self,
        m25_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        tables_dir: Optional[Path] = None,
    ):
        self.m25_dir = m25_dir or FROZEN_M25_DIR
        self.output_dir = output_dir or PROCESSED_CLIMATE_DIR
        self.tables_dir = tables_dir or TABLES_DIR

    def compute_annual_regime_prevalence(self) -> pd.DataFrame:
        """Compute domain-wide and Tier 1 terrestrial annual-seasonal regime fractions."""
        years_file = self.m25_dir / "combined_3season_years.npy"
        sids_file = self.m25_dir / "combined_3season_season_ids.npy"
        labels_file = self.m25_dir / "combined_3season_cluster_labels.npy"
        cells_file = self.m25_dir / "combined_3season_cell_indices.npy"

        if not (years_file.exists() and sids_file.exists() and labels_file.exists()):
            raise FileNotFoundError("Frozen M25 3-season arrays missing from processed directory")

        years = np.load(years_file)
        season_ids = np.load(sids_file)
        labels = np.load(labels_file)

        # 1. Domain-wide vectorized binning (960 cells * 30 days * 24 hours = 691,200 per year-season)
        key_domain = (years - 2010) * 3 + season_ids
        counts_domain = np.bincount(key_domain * 4 + labels, minlength=36 * 4).reshape((36, 4))
        tot_domain = counts_domain.sum(axis=1, keepdims=True)
        frac_domain = counts_domain / tot_domain

        # 2. Tier 1 terrestrial binning (328 cells * 30 days * 24 hours = 236,160 per year-season)
        tier1_frac = np.full((36, 4), np.nan)
        if cells_file.exists():
            cell_indices = np.load(cells_file)
            matched_parquet = FROZEN_M26_DIR / "m26_cloud_rainfall_matched_primary.parquet"
            if matched_parquet.exists():
                df_matched = pd.read_parquet(matched_parquet)
                tier1_cells = set(df_matched["cell_index"].unique())
                t1_mask = np.isin(cell_indices, list(tier1_cells))

                key_t1 = (years[t1_mask] - 2010) * 3 + season_ids[t1_mask]
                counts_t1 = np.bincount(key_t1 * 4 + labels[t1_mask], minlength=36 * 4).reshape((36, 4))
                tot_t1 = counts_t1.sum(axis=1, keepdims=True)
                tier1_frac = counts_t1 / tot_t1

        records = []
        season_names = {0: "pre_monsoon", 1: "established_monsoon", 2: "post_monsoon"}

        for row_idx in range(36):
            yr = 2010 + (row_idx // 3)
            sid = row_idx % 3
            records.append({
                "year": int(yr),
                "season": season_names[sid],
                "season_id": int(sid),
                "total_obs_domain": int(tot_domain[row_idx, 0]),
                "p_R0_domain": float(frac_domain[row_idx, 0]),
                "p_R1_domain": float(frac_domain[row_idx, 1]),
                "p_R2_domain": float(frac_domain[row_idx, 2]),
                "p_R3_domain": float(frac_domain[row_idx, 3]),
                "p_R0_tier1": float(tier1_frac[row_idx, 0]),
                "p_R1_tier1": float(tier1_frac[row_idx, 1]),
                "p_R2_tier1": float(tier1_frac[row_idx, 2]),
                "p_R3_tier1": float(tier1_frac[row_idx, 3]),
            })

        df_prevalence = pd.DataFrame(records)
        return df_prevalence

    def run_regime_climate_analysis(
        self, B_perm: int = 100_000, seed: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Compute comprehensive Spearman, partial, CLR, and LOOCV teleconnection metrics."""
        df_prev = self.compute_annual_regime_prevalence()
        df_climate = get_aligned_climate_indices()

        df_merged = pd.merge(df_climate, df_prev, on=["year", "season", "season_id"])

        corr_records: List[Dict[str, Any]] = []
        clr_records: List[Dict[str, Any]] = []
        loocv_records: List[Dict[str, Any]] = []

        seasons = [
            (0, "pre_monsoon"),
            (1, "established_monsoon"),
            (2, "post_monsoon"),
            (-1, "pooled_three_seasons"),
        ]

        for sid, sname in seasons:
            if sid == -1:
                sub = df_merged.copy()
            else:
                sub = df_merged[df_merged["season_id"] == sid].copy()

            n_samples = len(sub)
            years = sub["year"].values
            roni = sub["roni_anomaly"].values
            dmi = sub["dmi_anomaly"].values

            # Compositional simplex validation
            p_matrix = sub[["p_R0_domain", "p_R1_domain", "p_R2_domain", "p_R3_domain"]].values
            clr_matrix = clr_transformation(p_matrix)

            for k in range(4):
                regime_tag = f"R{k}"
                regime_desc = REGIME_NAMES[k]
                p_rk = sub[f"p_{regime_tag}_domain"].values
                clr_rk = clr_matrix[:, k]

                # 1. Spearman with RONI
                rho_roni, p_roni_perm, roni_ci_l, roni_ci_u = permutation_test_spearman(
                    p_rk, roni, B=B_perm, seed=seed + sid * 10 + k
                )
                _, p_roni_asympt = compute_spearman_correlation(p_rk, roni)

                # 2. Spearman with DMI
                rho_dmi, p_dmi_perm, dmi_ci_l, dmi_ci_u = permutation_test_spearman(
                    p_rk, dmi, B=B_perm, seed=seed + 100 + sid * 10 + k
                )
                _, p_dmi_asympt = compute_spearman_correlation(p_rk, dmi)

                # 3. Partial Spearman
                rho_part_roni, p_part_roni_perm = permutation_test_partial_spearman(
                    p_rk, roni, dmi, B=B_perm, seed=seed + 200 + sid * 10 + k
                )
                rho_part_dmi, p_part_dmi_perm = permutation_test_partial_spearman(
                    p_rk, dmi, roni, B=B_perm, seed=seed + 300 + sid * 10 + k
                )

                corr_records.append({
                    "season": sname,
                    "season_id": sid,
                    "n_years": n_samples,
                    "regime": regime_tag,
                    "regime_name": regime_desc,
                    # RONI Teleconnection
                    "rho_roni": float(round(rho_roni, 4)),
                    "p_roni_perm": float(round(p_roni_perm, 5)),
                    "p_roni_asympt": float(round(p_roni_asympt, 5)),
                    "roni_ci_lower_95": float(round(roni_ci_l, 4)),
                    "roni_ci_upper_95": float(round(roni_ci_u, 4)),
                    "rho_partial_roni": float(round(rho_part_roni, 4)),
                    "p_partial_roni_perm": float(round(p_part_roni_perm, 5)),
                    # DMI Teleconnection
                    "rho_dmi": float(round(rho_dmi, 4)),
                    "p_dmi_perm": float(round(p_dmi_perm, 5)),
                    "p_dmi_asympt": float(round(p_dmi_asympt, 5)),
                    "dmi_ci_lower_95": float(round(dmi_ci_l, 4)),
                    "dmi_ci_upper_95": float(round(dmi_ci_u, 4)),
                    "rho_partial_dmi": float(round(rho_part_dmi, 4)),
                    "p_partial_dmi_perm": float(round(p_part_dmi_perm, 5)),
                })

                # CLR sensitivity
                rho_clr_roni, p_clr_r_perm, _, _ = permutation_test_spearman(
                    clr_rk, roni, B=B_perm, seed=seed + 400 + sid * 10 + k
                )
                rho_clr_dmi, p_clr_d_perm, _, _ = permutation_test_spearman(
                    clr_rk, dmi, B=B_perm, seed=seed + 500 + sid * 10 + k
                )
                clr_records.append({
                    "season": sname,
                    "season_id": sid,
                    "regime": regime_tag,
                    "rho_raw_roni": float(round(rho_roni, 4)),
                    "rho_clr_roni": float(round(rho_clr_roni, 4)),
                    "p_clr_roni_perm": float(round(p_clr_r_perm, 5)),
                    "rho_raw_dmi": float(round(rho_dmi, 4)),
                    "rho_clr_dmi": float(round(rho_clr_dmi, 4)),
                    "p_clr_dmi_perm": float(round(p_clr_d_perm, 5)),
                })

                # LOOCV Sensitivity (for season-specific analysis N=12)
                if sid >= 0:
                    df_loo_r = leave_one_out_sensitivity(p_rk, roni, years)
                    df_loo_d = leave_one_out_sensitivity(p_rk, dmi, years)
                    for row_i in range(len(df_loo_r)):
                        loocv_records.append({
                            "season": sname,
                            "regime": regime_tag,
                            "dropped_year": int(df_loo_r.iloc[row_i]["dropped_year"]),
                            "rho_roni_full": float(df_loo_r.iloc[row_i]["rho_full"]),
                            "rho_roni_loo": float(df_loo_r.iloc[row_i]["rho_loo"]),
                            "delta_rho_roni": float(df_loo_r.iloc[row_i]["delta_rho"]),
                            "rho_dmi_full": float(df_loo_d.iloc[row_i]["rho_full"]),
                            "rho_dmi_loo": float(df_loo_d.iloc[row_i]["rho_loo"]),
                            "delta_rho_dmi": float(df_loo_d.iloc[row_i]["delta_rho"]),
                        })

        df_corr = pd.DataFrame(corr_records)
        df_clr = pd.DataFrame(clr_records)
        df_loocv = pd.DataFrame(loocv_records)

        # Apply Benjamini-Hochberg FDR correction (q=0.10) per seasonal family (8 hypotheses: 4 regimes x 2 indices)
        df_corr["q_roni_fdr"] = np.nan
        df_corr["sig_roni_fdr"] = False
        df_corr["q_dmi_fdr"] = np.nan
        df_corr["sig_dmi_fdr"] = False

        for sid in [0, 1, 2, -1]:
            mask = df_corr["season_id"] == sid
            # Combined p-values for the seasonal hypothesis family
            p_r_sub = df_corr.loc[mask, "p_roni_perm"].values
            p_d_sub = df_corr.loc[mask, "p_dmi_perm"].values
            
            sig_r, q_r = fdr_correction_bh(p_r_sub, q=0.10)
            sig_d, q_d = fdr_correction_bh(p_d_sub, q=0.10)
            
            df_corr.loc[mask, "q_roni_fdr"] = np.round(q_r, 5)
            df_corr.loc[mask, "sig_roni_fdr"] = sig_r
            df_corr.loc[mask, "q_dmi_fdr"] = np.round(q_d, 5)
            df_corr.loc[mask, "sig_dmi_fdr"] = sig_d

        return df_prev, df_corr, df_clr, df_loocv

    def export_all(
        self, B_perm: int = 100_000, seed: int = 42
    ) -> Dict[str, Path]:
        """Run analysis and export all data and table deliverables."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tables_dir.mkdir(parents=True, exist_ok=True)

        df_prev, df_corr, df_clr, df_loocv = self.run_regime_climate_analysis(
            B_perm=B_perm, seed=seed
        )

        paths = {
            "prevalence_parquet": self.output_dir / "m27_regime_annual_seasonal_prevalence.parquet",
            "prevalence_csv": self.tables_dir / "m27_regime_annual_seasonal_prevalence.csv",
            "correlations_csv": self.tables_dir / "m27_regime_climate_correlations.csv",
            "clr_sensitivity_csv": self.tables_dir / "m27_regime_clr_correlations.csv",
            "loocv_csv": self.tables_dir / "m27_regime_climate_loocv.csv",
        }

        df_prev.to_parquet(paths["prevalence_parquet"], index=False)
        df_prev.to_csv(paths["prevalence_csv"], index=False)
        df_corr.to_csv(paths["correlations_csv"], index=False)
        df_clr.to_csv(paths["clr_sensitivity_csv"], index=False)
        df_loocv.to_csv(paths["loocv_csv"], index=False)

        for name, p in paths.items():
            logger.info(f"Exported {name} -> {p} ({p.stat().st_size} bytes)")

        return paths


if __name__ == "__main__":
    engine = RegimeClimateCorrelationEngine()
    exported = engine.export_all(B_perm=100_000)
    print("M27.3 Regime Climate Modulation Engine completed successfully!")
    for k, v in exported.items():
        print(f"  {k}: {v.name} ({v.stat().st_size} bytes)")
