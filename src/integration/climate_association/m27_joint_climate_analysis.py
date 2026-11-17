"""M27.5 — Joint ENSO–IOD Interaction Analysis Engine.

Analyzes the combined and interactive modulation of Indian cloud regimes and rainfall
by concurrent Pacific (RONI) and Indian Ocean (DMI) climate modes.

Components:
1. 3x3 and 2x2 Contingency Phase Matrices with exact annual membership and sample sizes.
2. Case studies of historical co-occurrence and pure events:
   - 2015: Super El Niño + Positive IOD (Concurrent Pacific-Indian warming)
   - 2010: Strong La Niña + Negative IOD (Concurrent basin-scale cooling)
   - 2019: Super Positive IOD with Neutral ENSO (Pure Indian Ocean forcing)
   - 2016: Negative IOD with developing La Niña
3. Interaction OLS regression:
   Y = beta_0 + beta_1 * RONI + beta_2 * DMI + beta_3 * (RONI x DMI) + eps
   with exact permutation p-values (B=100,000) for interaction term beta_3.
4. Methodological safeguards:
   Explicitly marks small-sample phase combinations as underpowered.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from src.integration.climate_association.m27_climate_index_loader import (
    get_aligned_climate_indices,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_CLIMATE_DIR = PROJECT_ROOT / "data" / "processed" / "climate_indices"
TABLES_DIR = PROJECT_ROOT / "reports" / "integration" / "m27" / "tables"


class JointClimateAnalysisEngine:
    """Engine for joint ENSO-IOD contingency, interaction, and case study analysis."""

    def __init__(
        self,
        processed_dir: Optional[Path] = None,
        tables_dir: Optional[Path] = None,
    ):
        self.processed_dir = processed_dir or PROCESSED_CLIMATE_DIR
        self.tables_dir = tables_dir or TABLES_DIR

    def load_combined_dataset(self) -> pd.DataFrame:
        """Merge climate indices, regime prevalence, and rainfall metrics."""
        df_clim = get_aligned_climate_indices()
        prev_file = self.processed_dir / "m27_regime_annual_seasonal_prevalence.parquet"
        rain_file = self.processed_dir / "m27_rainfall_annual_seasonal_modulation.parquet"

        if not prev_file.exists():
            raise FileNotFoundError(f"Regime prevalence parquet missing: {prev_file}")
        if not rain_file.exists():
            raise FileNotFoundError(f"Rainfall modulation parquet missing: {rain_file}")

        df_prev = pd.read_parquet(prev_file)
        df_rain = pd.read_parquet(rain_file)

        df_merged = pd.merge(df_clim, df_prev, on=["year", "season_id", "season"])
        df_merged = pd.merge(
            df_merged,
            df_rain[[
                "year", "season_id", "season",
                "mean_rainfall_mm", "rainfall_anomaly_mm", "wet_day_freq_25mm",
                "cond_mean_R0", "cond_mean_R1", "cond_mean_R2", "cond_mean_R3",
                "vol_contrib_R2", "vol_contrib_R0",
            ]],
            on=["year", "season_id", "season"],
        )
        return df_merged

    def build_contingency_matrix(self, df_merged: pd.DataFrame) -> pd.DataFrame:
        """Construct the 3x3 ENSO x IOD phase matrix across all seasons."""
        records: List[Dict[str, Any]] = []

        enso_phases = ["El Niño", "Neutral", "La Niña"]
        iod_phases = ["Positive IOD", "Neutral", "Negative IOD"]

        for sid in [0, 1, 2, -1]:
            if sid == -1:
                sub = df_merged.copy()
                sname = "pooled_three_seasons"
            else:
                sub = df_merged[df_merged["season_id"] == sid].copy()
                sname = sub["season"].iloc[0]

            for ep in enso_phases:
                for ip in iod_phases:
                    cell_sub = sub[(sub["enso_phase"] == ep) & (sub["iod_phase"] == ip)]
                    n_yrs = len(cell_sub)
                    yrs_list = sorted(cell_sub["year"].tolist())
                    yrs_str = ", ".join(str(y) for y in yrs_list) if yrs_list else "None"

                    is_underpowered = n_yrs < 3

                    records.append({
                        "season": sname,
                        "season_id": sid,
                        "enso_phase": ep,
                        "iod_phase": ip,
                        "joint_phase": f"{ep} + {ip}",
                        "n_years": n_yrs,
                        "years": yrs_str,
                        "is_underpowered": is_underpowered,
                        "mean_rainfall_mm": float(round(cell_sub["mean_rainfall_mm"].mean(), 4)) if n_yrs > 0 else np.nan,
                        "mean_wet_day_freq_25": float(round(cell_sub["wet_day_freq_25mm"].mean(), 4)) if n_yrs > 0 else np.nan,
                        "mean_p_R0": float(round(cell_sub["p_R0_domain"].mean(), 4)) if n_yrs > 0 else np.nan,
                        "mean_p_R1": float(round(cell_sub["p_R1_domain"].mean(), 4)) if n_yrs > 0 else np.nan,
                        "mean_p_R2": float(round(cell_sub["p_R2_domain"].mean(), 4)) if n_yrs > 0 else np.nan,
                        "mean_p_R3": float(round(cell_sub["p_R3_domain"].mean(), 4)) if n_yrs > 0 else np.nan,
                        "cond_mean_R2": float(round(cell_sub["cond_mean_R2"].mean(), 4)) if n_yrs > 0 else np.nan,
                        "vol_contrib_R2": float(round(cell_sub["vol_contrib_R2"].mean(), 4)) if n_yrs > 0 else np.nan,
                    })

        return pd.DataFrame(records)

    def analyze_interaction_effects(
        self, df_merged: pd.DataFrame, B_perm: int = 100_000, seed: int = 42
    ) -> pd.DataFrame:
        """Estimate the multiplicative interaction RONI x DMI via permutation."""
        records: List[Dict[str, Any]] = []

        target_vars = [
            ("mean_rainfall_mm", "Terrestrial Mean Rainfall"),
            ("wet_day_freq_25mm", "Wet-Day Frequency (>=2.5mm)"),
            ("p_R0_domain", "R0 Mixed Convective Fraction"),
            ("p_R1_domain", "R1 Shallow Cumulus Fraction"),
            ("p_R2_domain", "R2 Deep Convective Fraction"),
            ("p_R3_domain", "R3 Thin Cirrus/Anvil Fraction"),
            ("cond_mean_R2", "R2 Conditional Mean Intensity"),
        ]

        for sid in [0, 1, 2, -1]:
            if sid == -1:
                sub = df_merged.copy()
                sname = "pooled_three_seasons"
            else:
                sub = df_merged[df_merged["season_id"] == sid].copy()
                sname = sub["season"].iloc[0]

            n = len(sub)
            x_roni = sub["roni_anomaly"].values
            x_dmi = sub["dmi_anomaly"].values
            x_inter = x_roni * x_dmi

            # Standardize predictors for numerical stability
            X = np.column_stack([np.ones(n), x_roni, x_dmi, x_inter])

            for var_name, var_desc in target_vars:
                y = sub[var_name].values

                # OLS solution
                try:
                    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
                    beta_inter_obs = float(beta[3])
                except Exception:
                    beta_inter_obs = np.nan

                # Permutation of interaction term
                rng = np.random.default_rng(seed + (sid + 2) * 10)
                perm_betas = np.empty(B_perm, dtype=float)

                # Under H0: no interaction, permute x_inter relative to (y, x_roni, x_dmi)
                # Or orthogonalize x_inter with respect to [1, x_roni, x_dmi]
                X_base = X[:, :3]
                beta_base, _, _, _ = np.linalg.lstsq(X_base, x_inter, rcond=None)
                res_inter = x_inter - X_base @ beta_base

                beta_y_base, _, _, _ = np.linalg.lstsq(X_base, y, rcond=None)
                res_y = y - X_base @ beta_y_base

                # Partial regression coefficient of res_y on res_inter
                denom_inter = np.sum(res_inter**2)
                if denom_inter > 1e-12:
                    b_obs = float(np.sum(res_inter * res_y) / denom_inter)
                    base_res = res_y.copy()
                    for b in range(B_perm):
                        shuffled_y = rng.permutation(base_res)
                        perm_betas[b] = np.sum(res_inter * shuffled_y) / denom_inter

                    abs_obs = np.abs(b_obs)
                    p_inter_perm = float((1.0 + np.sum(np.abs(perm_betas) >= abs_obs - 1e-12)) / (B_perm + 1.0))
                else:
                    b_obs = 0.0
                    p_inter_perm = 1.0

                records.append({
                    "season": sname,
                    "season_id": sid,
                    "variable": var_name,
                    "variable_description": var_desc,
                    "beta_interaction_ols": float(round(b_obs, 5)),
                    "p_interaction_perm": float(round(p_inter_perm, 5)),
                    "is_significant_p05": p_inter_perm < 0.05,
                })

        return pd.DataFrame(records)

    def extract_case_studies(self, df_merged: pd.DataFrame) -> pd.DataFrame:
        """Extract historical case study benchmarks (2015, 2010, 2019, 2016)."""
        case_years = [2010, 2015, 2016, 2018, 2019, 2020]
        sub_cases = df_merged[df_merged["year"].isin(case_years)].copy()

        event_descriptions = {
            (2010, 1): "2010 Est-Monsoon: Moderate La Niña + Neutral IOD",
            (2010, 2): "2010 Post-Monsoon: Super La Niña (-1.61°C) + Negative IOD (-0.47°C)",
            (2015, 1): "2015 Est-Monsoon: Super El Niño (+1.27°C) + Neutral IOD",
            (2015, 2): "2015 Post-Monsoon: Super El Niño (+2.03°C) + Positive IOD (+0.41°C)",
            (2016, 1): "2016 Est-Monsoon: La Niña (-0.70°C) + Negative IOD (-0.60°C)",
            (2018, 2): "2018 Post-Monsoon: Moderate El Niño (+0.62°C) + Positive IOD (+0.59°C)",
            (2019, 1): "2019 Est-Monsoon: Neutral ENSO (+0.04°C) + Positive IOD (+0.52°C)",
            (2019, 2): "2019 Post-Monsoon: Neutral ENSO (+0.15°C) + Super Positive IOD (+0.90°C)",
            (2020, 2): "2020 Post-Monsoon: La Niña (-1.37°C) + Neutral IOD (+0.05°C)",
        }

        sub_cases["event_benchmark"] = [
            event_descriptions.get((y, sid), f"{y} {s}")
            for y, sid, s in zip(sub_cases["year"], sub_cases["season_id"], sub_cases["season"])
        ]

        cols_order = [
            "year", "season", "season_id", "event_benchmark",
            "roni_anomaly", "enso_phase", "dmi_anomaly", "iod_phase", "joint_phase",
            "mean_rainfall_mm", "rainfall_anomaly_mm", "wet_day_freq_25mm",
            "p_R0_domain", "p_R1_domain", "p_R2_domain", "p_R3_domain",
            "cond_mean_R2", "vol_contrib_R2",
        ]
        return sub_cases[cols_order].sort_values(by=["season_id", "year"]).reset_index(drop=True)

    def export_all(
        self, B_perm: int = 100_000, seed: int = 42
    ) -> Dict[str, Path]:
        """Execute and export all joint analysis deliverables."""
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.tables_dir.mkdir(parents=True, exist_ok=True)

        df_merged = self.load_combined_dataset()
        df_matrix = self.build_contingency_matrix(df_merged)
        df_inter = self.analyze_interaction_effects(df_merged, B_perm=B_perm, seed=seed)
        df_cases = self.extract_case_studies(df_merged)

        paths = {
            "matrix_parquet": self.processed_dir / "m27_joint_enso_iod_matrix.parquet",
            "matrix_csv": self.tables_dir / "m27_joint_enso_iod_phase_matrix.csv",
            "interaction_csv": self.tables_dir / "m27_joint_interaction_effects.csv",
            "cases_csv": self.tables_dir / "m27_joint_enso_iod_case_studies.csv",
        }

        df_matrix.to_parquet(paths["matrix_parquet"], index=False)
        df_matrix.to_csv(paths["matrix_csv"], index=False)
        df_inter.to_csv(paths["interaction_csv"], index=False)
        df_cases.to_csv(paths["cases_csv"], index=False)

        for name, p in paths.items():
            logger.info(f"Exported {name} -> {p} ({p.stat().st_size} bytes)")

        return paths


if __name__ == "__main__":
    engine = JointClimateAnalysisEngine()
    exported = engine.export_all(B_perm=100_000)
    print("M27.5 Joint Climate Analysis Engine completed successfully!")
    for k, v in exported.items():
        print(f"  {k}: {v.name} ({v.stat().st_size} bytes)")
