"""M27.4 — Rainfall Modulation Engine.

Quantifies how large-scale climate modes (NOAA RONI and DMI) modulate
terrestrial rainfall over India during 2010–2021 across the 328 Tier 1 grid cells,
using validated M26 rainfall-cloud regime matched records (342,432 observations).

Evaluates:
1. Terrestrial seasonal mean rainfall and wet-day frequencies (>=1.0mm, >=2.5mm).
2. Seasonal rainfall anomalies relative to the 12-year climatology.
3. Regime-conditional rainfall intensity (mean mm/day on days dominated by R_k).
4. Regime rainfall volume contributions (fraction of total rain attributed to R_k).
5. Continuous-fraction weighted rainfall intensity and volume fractions.
6. Non-parametric Spearman and partial rank correlations with exact B=100,000 permutations.
7. Targeted R2 (deep convection) and R1 (shallow cumulus) phase contrasts.
8. Jackknife Leave-One-Out (LOOCV) sensitivity analysis specifically evaluating 2015 and 2019.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.integration.climate_association.m27_climate_index_loader import (
    get_aligned_climate_indices,
)
from src.integration.climate_association.m27_statistical_validation import (
    compute_spearman_correlation,
    permutation_test_spearman,
    permutation_test_partial_spearman,
    fdr_correction_bh,
    leave_one_out_sensitivity,
    exact_two_group_permutation_test,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FROZEN_M26_DIR = PROJECT_ROOT / "data" / "processed" / "rainfall_validation"
PROCESSED_CLIMATE_DIR = PROJECT_ROOT / "data" / "processed" / "climate_indices"
TABLES_DIR = PROJECT_ROOT / "reports" / "integration" / "m27" / "tables"


class RainfallClimateModulationEngine:
    """Engine for analyzing rainfall modulation by ENSO and IOD."""

    def __init__(
        self,
        m26_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        tables_dir: Optional[Path] = None,
    ):
        self.m26_dir = m26_dir or FROZEN_M26_DIR
        self.output_dir = output_dir or PROCESSED_CLIMATE_DIR
        self.tables_dir = tables_dir or TABLES_DIR

    def compute_annual_seasonal_rainfall_metrics(self) -> pd.DataFrame:
        """Aggregate 342,432 matched records into 36 annual-seasonal rainfall summaries."""
        matched_file = self.m26_dir / "m26_cloud_rainfall_matched_primary.parquet"
        if not matched_file.exists():
            raise FileNotFoundError(f"Primary matched rainfall parquet missing: {matched_file}")

        df = pd.read_parquet(matched_file)

        records: List[Dict[str, Any]] = []
        for (yr, sid), grp in df.groupby(["year", "season_id"]):
            sname = str(grp["season_name"].iloc[0])
            n_obs = len(grp)
            tot_rain = float(grp["rainfall_mm"].sum())
            mean_rain = float(grp["rainfall_mm"].mean())
            wet_10 = float((grp["rainfall_mm"] >= 1.0).mean())
            wet_25 = float(grp["is_wet_day_25"].mean())

            rec: Dict[str, Any] = {
                "year": int(yr),
                "season_id": int(sid),
                "season": sname,
                "n_cell_days": n_obs,
                "total_rainfall_volume_mm": round(tot_rain, 2),
                "mean_rainfall_mm": round(mean_rain, 4),
                "wet_day_freq_1mm": round(wet_10, 4),
                "wet_day_freq_25mm": round(wet_25, 4),
            }

            for k in range(4):
                sub_k = grp[grp["dominant_regime"] == k]
                count_k = len(sub_k)
                sum_rain_k = float(sub_k["rainfall_mm"].sum()) if count_k > 0 else 0.0
                cond_mean = float(sub_k["rainfall_mm"].mean()) if count_k > 0 else 0.0
                vol_contrib = (sum_rain_k / tot_rain) if tot_rain > 0 else 0.0

                rec[f"dominant_days_R{k}"] = count_k
                rec[f"cond_mean_R{k}"] = round(cond_mean, 4)
                rec[f"vol_contrib_R{k}"] = round(vol_contrib, 5)

                # Continuous fraction weighted metrics
                frac_w = grp[f"frac_r{k}"]
                sum_w = float(frac_w.sum())
                w_rain = float((frac_w * grp["rainfall_mm"]).sum())
                cf_mean = (w_rain / sum_w) if sum_w > 0 else 0.0
                cf_vol = (w_rain / tot_rain) if tot_rain > 0 else 0.0

                rec[f"cf_mean_R{k}"] = round(cf_mean, 4)
                rec[f"cf_vol_contrib_R{k}"] = round(cf_vol, 5)

            records.append(rec)

        df_metrics = pd.DataFrame(records)

        # Compute seasonal rainfall anomalies relative to the 12-year seasonal mean
        df_metrics["rainfall_anomaly_mm"] = 0.0
        for sid in [0, 1, 2]:
            mask = df_metrics["season_id"] == sid
            s_mean = df_metrics.loc[mask, "mean_rainfall_mm"].mean()
            df_metrics.loc[mask, "rainfall_anomaly_mm"] = round(
                df_metrics.loc[mask, "mean_rainfall_mm"] - s_mean, 4
            )

        return df_metrics

    def run_rainfall_climate_analysis(
        self, B_perm: int = 100_000, seed: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Compute rainfall modulation correlations, LOOCV, and R2/R1 phase contrasts."""
        df_metrics = self.compute_annual_seasonal_rainfall_metrics()
        df_climate = get_aligned_climate_indices()

        df_merged = pd.merge(df_climate, df_metrics, on=["year", "season_id", "season"])

        corr_records: List[Dict[str, Any]] = []
        loocv_records: List[Dict[str, Any]] = []
        contrast_records: List[Dict[str, Any]] = []

        seasons = [
            (0, "pre_monsoon"),
            (1, "established_monsoon"),
            (2, "post_monsoon"),
            (-1, "pooled_three_seasons"),
        ]

        target_metrics = [
            ("mean_rainfall_mm", "Terrestrial Mean Rainfall (mm/day)"),
            ("rainfall_anomaly_mm", "Seasonal Rainfall Anomaly (mm/day)"),
            ("wet_day_freq_25mm", "Wet-Day Frequency (>=2.5 mm/day)"),
            ("cond_mean_R2", "R2 Deep Convective Conditional Mean (mm/day)"),
            ("vol_contrib_R2", "R2 Rainfall Volume Contribution Fraction"),
            ("cond_mean_R1", "R1 Shallow Cumulus Conditional Mean (mm/day)"),
            ("vol_contrib_R1", "R1 Rainfall Volume Contribution Fraction"),
            ("cond_mean_R0", "R0 Mixed Convective Conditional Mean (mm/day)"),
            ("cond_mean_R3", "R3 Thin Cirrus/Anvil Conditional Mean (mm/day)"),
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

            for m_tag, m_desc in target_metrics:
                m_vals = sub[m_tag].values

                # 1. Spearman with RONI
                rho_roni, p_roni_perm, roni_ci_l, roni_ci_u = permutation_test_spearman(
                    m_vals, roni, B=B_perm, seed=seed + (sid + 2) * 20
                )
                _, p_roni_asympt = compute_spearman_correlation(m_vals, roni)

                # 2. Spearman with DMI
                rho_dmi, p_dmi_perm, dmi_ci_l, dmi_ci_u = permutation_test_spearman(
                    m_vals, dmi, B=B_perm, seed=seed + 100 + (sid + 2) * 20
                )
                _, p_dmi_asympt = compute_spearman_correlation(m_vals, dmi)

                # 3. Partial Spearman
                rho_part_roni, p_part_roni_perm = permutation_test_partial_spearman(
                    m_vals, roni, dmi, B=B_perm, seed=seed + 200 + (sid + 2) * 20
                )
                rho_part_dmi, p_part_dmi_perm = permutation_test_partial_spearman(
                    m_vals, dmi, roni, B=B_perm, seed=seed + 300 + (sid + 2) * 20
                )

                corr_records.append({
                    "season": sname,
                    "season_id": sid,
                    "n_years": n_samples,
                    "metric": m_tag,
                    "metric_description": m_desc,
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

                # LOOCV for seasonal records (N=12)
                if sid >= 0:
                    df_loo_r = leave_one_out_sensitivity(m_vals, roni, years)
                    df_loo_d = leave_one_out_sensitivity(m_vals, dmi, years)
                    for row_i in range(len(df_loo_r)):
                        loocv_records.append({
                            "season": sname,
                            "metric": m_tag,
                            "dropped_year": int(df_loo_r.iloc[row_i]["dropped_year"]),
                            "rho_roni_full": float(df_loo_r.iloc[row_i]["rho_full"]),
                            "rho_roni_loo": float(df_loo_r.iloc[row_i]["rho_loo"]),
                            "delta_rho_roni": float(df_loo_r.iloc[row_i]["delta_rho"]),
                            "rho_dmi_full": float(df_loo_d.iloc[row_i]["rho_full"]),
                            "rho_dmi_loo": float(df_loo_d.iloc[row_i]["rho_loo"]),
                            "delta_rho_dmi": float(df_loo_d.iloc[row_i]["delta_rho"]),
                        })

            # Discrete phase contrasts for R2 and R1 (El Niño vs La Niña; Pos IOD vs Neg IOD)
            if sid >= 0:
                for target_m in ["mean_rainfall_mm", "cond_mean_R2", "cond_mean_R1", "vol_contrib_R2"]:
                    # ENSO contrast
                    el_nino_vals = sub[sub["enso_phase"] == "El Niño"][target_m].values
                    la_nina_vals = sub[sub["enso_phase"] == "La Niña"][target_m].values
                    n_en, n_ln = len(el_nino_vals), len(la_nina_vals)
                    diff_enso, p_enso, _ = exact_two_group_permutation_test(
                        el_nino_vals, la_nina_vals, B=B_perm, seed=seed + 500 + sid
                    )

                    # IOD contrast
                    pos_iod_vals = sub[sub["iod_phase"] == "Positive IOD"][target_m].values
                    neg_iod_vals = sub[sub["iod_phase"] == "Negative IOD"][target_m].values
                    n_pos, n_neg = len(pos_iod_vals), len(neg_iod_vals)
                    diff_iod, p_iod, _ = exact_two_group_permutation_test(
                        pos_iod_vals, neg_iod_vals, B=B_perm, seed=seed + 600 + sid
                    )

                    contrast_records.append({
                        "season": sname,
                        "metric": target_m,
                        # ENSO Comparison
                        "n_el_nino": n_en,
                        "mean_el_nino": float(round(np.mean(el_nino_vals), 4)) if n_en > 0 else np.nan,
                        "n_la_nina": n_ln,
                        "mean_la_nina": float(round(np.mean(la_nina_vals), 4)) if n_ln > 0 else np.nan,
                        "diff_el_nino_minus_la_nina": float(round(diff_enso, 4)) if np.isfinite(diff_enso) else np.nan,
                        "p_perm_enso_contrast": float(round(p_enso, 5)) if np.isfinite(p_enso) else np.nan,
                        # IOD Comparison
                        "n_pos_iod": n_pos,
                        "mean_pos_iod": float(round(np.mean(pos_iod_vals), 4)) if n_pos > 0 else np.nan,
                        "n_neg_iod": n_neg,
                        "mean_neg_iod": float(round(np.mean(neg_iod_vals), 4)) if n_neg > 0 else np.nan,
                        "diff_pos_minus_neg_iod": float(round(diff_iod, 4)) if np.isfinite(diff_iod) else np.nan,
                        "p_perm_iod_contrast": float(round(p_iod, 5)) if np.isfinite(p_iod) else np.nan,
                    })

        df_corr = pd.DataFrame(corr_records)
        df_loocv = pd.DataFrame(loocv_records)
        df_contrasts = pd.DataFrame(contrast_records)

        # FDR correction (q=0.10) per seasonal family
        df_corr["q_roni_fdr"] = np.nan
        df_corr["sig_roni_fdr"] = False
        df_corr["q_dmi_fdr"] = np.nan
        df_corr["sig_dmi_fdr"] = False

        for sid in [0, 1, 2, -1]:
            mask = df_corr["season_id"] == sid
            p_r_sub = df_corr.loc[mask, "p_roni_perm"].values
            p_d_sub = df_corr.loc[mask, "p_dmi_perm"].values
            sig_r, q_r = fdr_correction_bh(p_r_sub, q=0.10)
            sig_d, q_d = fdr_correction_bh(p_d_sub, q=0.10)
            df_corr.loc[mask, "q_roni_fdr"] = np.round(q_r, 5)
            df_corr.loc[mask, "sig_roni_fdr"] = sig_r
            df_corr.loc[mask, "q_dmi_fdr"] = np.round(q_d, 5)
            df_corr.loc[mask, "sig_dmi_fdr"] = sig_d

        return df_metrics, df_corr, df_loocv, df_contrasts

    def export_all(
        self, B_perm: int = 100_000, seed: int = 42
    ) -> Dict[str, Path]:
        """Execute and export all rainfall modulation deliverables."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tables_dir.mkdir(parents=True, exist_ok=True)

        df_metrics, df_corr, df_loocv, df_contrasts = self.run_rainfall_climate_analysis(
            B_perm=B_perm, seed=seed
        )

        paths = {
            "metrics_parquet": self.output_dir / "m27_rainfall_annual_seasonal_modulation.parquet",
            "metrics_csv": self.tables_dir / "m27_rainfall_annual_seasonal_metrics.csv",
            "correlations_csv": self.tables_dir / "m27_rainfall_climate_modulation.csv",
            "loocv_csv": self.tables_dir / "m27_rainfall_loocv_sensitivity.csv",
            "contrasts_csv": self.tables_dir / "m27_r2_r1_phase_contrasts.csv",
        }

        df_metrics.to_parquet(paths["metrics_parquet"], index=False)
        df_metrics.to_csv(paths["metrics_csv"], index=False)
        df_corr.to_csv(paths["correlations_csv"], index=False)
        df_loocv.to_csv(paths["loocv_csv"], index=False)
        df_contrasts.to_csv(paths["contrasts_csv"], index=False)

        for name, p in paths.items():
            logger.info(f"Exported {name} -> {p} ({p.stat().st_size} bytes)")

        return paths


if __name__ == "__main__":
    engine = RainfallClimateModulationEngine()
    exported = engine.export_all(B_perm=100_000)
    print("M27.4 Rainfall Climate Modulation Engine completed successfully!")
    for k, v in exported.items():
        print(f"  {k}: {v.name} ({v.stat().st_size} bytes)")
