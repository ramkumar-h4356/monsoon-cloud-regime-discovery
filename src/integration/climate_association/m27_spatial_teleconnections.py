"""M27.5 — Spatial Teleconnections and Field Significance Engine.

Quantifies the geographic patterns of ENSO and IOD teleconnections across
the 328 Tier 1 terrestrial grid cells of India during 2010–2021.

Analyzes:
1. Cell-wise anomaly composites:
   - Delta R_j(ENSO) = Mean Rain(El Niño) - Mean Rain(La Niña)
   - Delta P_j(R_k | ENSO) = Fraction(R_k | El Niño) - Fraction(R_k | La Niña)
   - Delta R_j(IOD) = Mean Rain(Positive IOD) - Mean Rain(Negative IOD)
   - Delta P_j(R_k | IOD) = Fraction(R_k | Positive IOD) - Fraction(R_k | Negative IOD)
2. Continuous cell-wise rank correlations:
   - rho_j(Rain, RONI) and rho_j(Rain, DMI)
   - rho_j(P(R_2), RONI) and rho_j(P(R_2), DMI)
3. Spatial Field Significance:
   - Livezey-Chen / Walker field significance test: compares the percentage of locally
     significant cells (p <= 0.05) against the binomial null expectation (5%),
     ensuring isolated grid-point noise is not misinterpreted as discovery.
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
FROZEN_M26_DIR = PROJECT_ROOT / "data" / "processed" / "rainfall_validation"
PROCESSED_CLIMATE_DIR = PROJECT_ROOT / "data" / "processed" / "climate_indices"
TABLES_DIR = PROJECT_ROOT / "reports" / "integration" / "m27" / "tables"


class SpatialTeleconnectionEngine:
    """Engine for cell-wise composite anomalies and spatial field significance."""

    def __init__(
        self,
        m26_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        tables_dir: Optional[Path] = None,
    ):
        self.m26_dir = m26_dir or FROZEN_M26_DIR
        self.output_dir = output_dir or PROCESSED_CLIMATE_DIR
        self.tables_dir = tables_dir or TABLES_DIR

    def compute_cell_teleconnections(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Compute cell-wise anomaly composites and evaluate field significance."""
        matched_file = self.m26_dir / "m26_cloud_rainfall_matched_primary.parquet"
        if not matched_file.exists():
            raise FileNotFoundError(f"Primary matched rainfall parquet missing: {matched_file}")

        df_matched = pd.read_parquet(matched_file)
        df_clim = get_aligned_climate_indices()

        # Merge climate phase indicators with daily matched records
        df_merged = pd.merge(
            df_matched,
            df_clim[["year", "season_id", "season", "roni_anomaly", "dmi_anomaly", "enso_phase", "iod_phase"]],
            on=["year", "season_id"],
        )

        cell_records: List[Dict[str, Any]] = []
        field_records: List[Dict[str, Any]] = []

        # Annual aggregation per cell-season (12 years x 328 cells x 3 seasons)
        cell_annual = df_merged.groupby(["season_id", "cell_index", "year", "latitude", "longitude"]).agg({
            "rainfall_mm": "mean",
            "frac_r0": "mean",
            "frac_r1": "mean",
            "frac_r2": "mean",
            "frac_r3": "mean",
            "roni_anomaly": "first",
            "dmi_anomaly": "first",
            "enso_phase": "first",
            "iod_phase": "first",
        }).reset_index()

        season_names = {0: "pre_monsoon", 1: "established_monsoon", 2: "post_monsoon"}

        for sid in [0, 1, 2]:
            sname = season_names[sid]
            sub_s = cell_annual[cell_annual["season_id"] == sid]

            p_vals_rain_roni: List[float] = []
            p_vals_rain_dmi: List[float] = []
            p_vals_r2_roni: List[float] = []
            p_vals_r2_dmi: List[float] = []

            for c_idx, grp in sub_s.groupby("cell_index"):
                lat = float(grp["latitude"].iloc[0])
                lon = float(grp["longitude"].iloc[0])

                # ENSO composite difference (El Niño vs La Niña)
                en_sub = grp[grp["enso_phase"] == "El Niño"]
                ln_sub = grp[grp["enso_phase"] == "La Niña"]

                r_en = float(en_sub["rainfall_mm"].mean()) if len(en_sub) > 0 else np.nan
                r_ln = float(ln_sub["rainfall_mm"].mean()) if len(ln_sub) > 0 else np.nan
                delta_r_enso = r_en - r_ln if (np.isfinite(r_en) and np.isfinite(r_ln)) else np.nan

                # Regime fraction differences (El Niño vs La Niña)
                delta_p_r0_enso = float(en_sub["frac_r0"].mean() - ln_sub["frac_r0"].mean()) if (len(en_sub) > 0 and len(ln_sub) > 0) else np.nan
                delta_p_r1_enso = float(en_sub["frac_r1"].mean() - ln_sub["frac_r1"].mean()) if (len(en_sub) > 0 and len(ln_sub) > 0) else np.nan
                delta_p_r2_enso = float(en_sub["frac_r2"].mean() - ln_sub["frac_r2"].mean()) if (len(en_sub) > 0 and len(ln_sub) > 0) else np.nan
                delta_p_r3_enso = float(en_sub["frac_r3"].mean() - ln_sub["frac_r3"].mean()) if (len(en_sub) > 0 and len(ln_sub) > 0) else np.nan

                # IOD composite difference (Positive IOD vs Negative IOD)
                pos_sub = grp[grp["iod_phase"] == "Positive IOD"]
                neg_sub = grp[grp["iod_phase"] == "Negative IOD"]

                r_pos = float(pos_sub["rainfall_mm"].mean()) if len(pos_sub) > 0 else np.nan
                r_neg = float(neg_sub["rainfall_mm"].mean()) if len(neg_sub) > 0 else np.nan
                delta_r_iod = r_pos - r_neg if (np.isfinite(r_pos) and np.isfinite(r_neg)) else np.nan

                delta_p_r0_iod = float(pos_sub["frac_r0"].mean() - neg_sub["frac_r0"].mean()) if (len(pos_sub) > 0 and len(neg_sub) > 0) else np.nan
                delta_p_r1_iod = float(pos_sub["frac_r1"].mean() - neg_sub["frac_r1"].mean()) if (len(pos_sub) > 0 and len(neg_sub) > 0) else np.nan
                delta_p_r2_iod = float(pos_sub["frac_r2"].mean() - neg_sub["frac_r2"].mean()) if (len(pos_sub) > 0 and len(neg_sub) > 0) else np.nan
                delta_p_r3_iod = float(pos_sub["frac_r3"].mean() - neg_sub["frac_r3"].mean()) if (len(pos_sub) > 0 and len(neg_sub) > 0) else np.nan

                # Continuous cell rank correlation with RONI and DMI
                res_rain_roni = stats.spearmanr(grp["rainfall_mm"], grp["roni_anomaly"])
                res_rain_dmi = stats.spearmanr(grp["rainfall_mm"], grp["dmi_anomaly"])
                res_r2_roni = stats.spearmanr(grp["frac_r2"], grp["roni_anomaly"])
                res_r2_dmi = stats.spearmanr(grp["frac_r2"], grp["dmi_anomaly"])

                p_rain_roni = float(res_rain_roni.pvalue) if np.isfinite(res_rain_roni.pvalue) else 1.0
                p_rain_dmi = float(res_rain_dmi.pvalue) if np.isfinite(res_rain_dmi.pvalue) else 1.0
                p_r2_roni = float(res_r2_roni.pvalue) if np.isfinite(res_r2_roni.pvalue) else 1.0
                p_r2_dmi = float(res_r2_dmi.pvalue) if np.isfinite(res_r2_dmi.pvalue) else 1.0

                p_vals_rain_roni.append(p_rain_roni)
                p_vals_rain_dmi.append(p_rain_dmi)
                p_vals_r2_roni.append(p_r2_roni)
                p_vals_r2_dmi.append(p_r2_dmi)

                cell_records.append({
                    "season": sname,
                    "season_id": sid,
                    "cell_index": int(c_idx),
                    "latitude": round(lat, 2),
                    "longitude": round(lon, 2),
                    "mean_rainfall_climatology_mm": round(float(grp["rainfall_mm"].mean()), 3),
                    # ENSO Teleconnection
                    "delta_rainfall_enso_mm": round(delta_r_enso, 3) if np.isfinite(delta_r_enso) else np.nan,
                    "delta_p_r0_enso": round(delta_p_r0_enso, 4) if np.isfinite(delta_p_r0_enso) else np.nan,
                    "delta_p_r1_enso": round(delta_p_r1_enso, 4) if np.isfinite(delta_p_r1_enso) else np.nan,
                    "delta_p_r2_enso": round(delta_p_r2_enso, 4) if np.isfinite(delta_p_r2_enso) else np.nan,
                    "delta_p_r3_enso": round(delta_p_r3_enso, 4) if np.isfinite(delta_p_r3_enso) else np.nan,
                    "rho_rain_roni": round(float(res_rain_roni.statistic), 4) if np.isfinite(res_rain_roni.statistic) else 0.0,
                    "p_rain_roni": round(p_rain_roni, 4),
                    "rho_r2_roni": round(float(res_r2_roni.statistic), 4) if np.isfinite(res_r2_roni.statistic) else 0.0,
                    "p_r2_roni": round(p_r2_roni, 4),
                    # IOD Teleconnection
                    "delta_rainfall_iod_mm": round(delta_r_iod, 3) if np.isfinite(delta_r_iod) else np.nan,
                    "delta_p_r0_iod": round(delta_p_r0_iod, 4) if np.isfinite(delta_p_r0_iod) else np.nan,
                    "delta_p_r1_iod": round(delta_p_r1_iod, 4) if np.isfinite(delta_p_r1_iod) else np.nan,
                    "delta_p_r2_iod": round(delta_p_r2_iod, 4) if np.isfinite(delta_p_r2_iod) else np.nan,
                    "delta_p_r3_iod": round(delta_p_r3_iod, 4) if np.isfinite(delta_p_r3_iod) else np.nan,
                    "rho_rain_dmi": round(float(res_rain_dmi.statistic), 4) if np.isfinite(res_rain_dmi.statistic) else 0.0,
                    "p_rain_dmi": round(p_rain_dmi, 4),
                    "rho_r2_dmi": round(float(res_r2_dmi.statistic), 4) if np.isfinite(res_r2_dmi.statistic) else 0.0,
                    "p_r2_dmi": round(p_r2_dmi, 4),
                })

            # Evaluate Field Significance across the 328 cells
            n_cells = len(sub_s["cell_index"].unique())
            for field_name, p_list in [
                ("Rainfall vs RONI", p_vals_rain_roni),
                ("Rainfall vs DMI", p_vals_rain_dmi),
                ("R2 Convection vs RONI", p_vals_r2_roni),
                ("R2 Convection vs DMI", p_vals_r2_dmi),
            ]:
                k_sig = int(np.sum(np.array(p_list) <= 0.05))
                pct_sig = (k_sig / n_cells) * 100.0
                # Binomial test against 5% false-positive expectation
                p_field = float(stats.binomtest(k_sig, n_cells, 0.05, alternative="greater").pvalue)
                is_field_sig = p_field < 0.05

                field_records.append({
                    "season": sname,
                    "season_id": sid,
                    "field_test": field_name,
                    "total_tier1_cells": n_cells,
                    "significant_cells_p05": k_sig,
                    "significant_percentage": round(pct_sig, 2),
                    "null_expectation_pct": 5.0,
                    "p_field_significance": round(p_field, 5),
                    "achieves_field_significance": is_field_sig,
                })

        df_cells = pd.DataFrame(cell_records)
        df_field = pd.DataFrame(field_records)
        return df_cells, df_field

    def export_all(self) -> Dict[str, Path]:
        """Execute and export all spatial teleconnection deliverables."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tables_dir.mkdir(parents=True, exist_ok=True)

        df_cells, df_field = self.compute_cell_teleconnections()

        paths = {
            "spatial_parquet": self.output_dir / "m27_spatial_teleconnections.parquet",
            "spatial_csv": self.tables_dir / "m27_spatial_teleconnection_anomalies.csv",
            "field_sig_csv": self.tables_dir / "m27_spatial_field_significance.csv",
        }

        df_cells.to_parquet(paths["spatial_parquet"], index=False)
        df_cells.to_csv(paths["spatial_csv"], index=False)
        df_field.to_csv(paths["field_sig_csv"], index=False)

        for name, p in paths.items():
            logger.info(f"Exported {name} -> {p} ({p.stat().st_size} bytes)")

        return paths


if __name__ == "__main__":
    engine = SpatialTeleconnectionEngine()
    exported = engine.export_all()
    print("M27.5 Spatial Teleconnections Engine completed successfully!")
    for k, v in exported.items():
        print(f"  {k}: {v.name} ({v.stat().st_size} bytes)")
