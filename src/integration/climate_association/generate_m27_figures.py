"""M27.6 — Publication-Quality Figure Generation Suite.

Generates the 10 required high-resolution (300 DPI) publication figures for M27:
1. fig01_annual_roni_dmi_timeseries.png
2. fig02_annual_seasonal_alignment_matrix.png
3. fig03_regime_prevalence_vs_climate_indices.png
4. fig04_partial_rank_correlations.png
5. fig05_seasonal_rainfall_vs_climate_indices.png
6. fig06_regime_conditional_rainfall_response.png
7. fig07_enso_phase_composite_maps.png
8. fig08_iod_phase_composite_maps.png
9. fig09_joint_enso_iod_phase_matrix.png
10. fig10_sensitivity_loocv_diagnostics.png
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIGURES_DIR = PROJECT_ROOT / "reports" / "integration" / "m27" / "figures"
TABLES_DIR = PROJECT_ROOT / "reports" / "integration" / "m27" / "tables"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "climate_indices"

# Style configuration
plt.rcParams["font.sans-serif"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#333333"
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["grid.color"] = "#E0E0E0"
plt.rcParams["grid.linestyle"] = "--"
plt.rcParams["grid.alpha"] = 0.7


class M27FigureGenerator:
    """Figure generation orchestrator for Milestone M27."""

    def __init__(self, figures_dir: Optional[Path] = None):
        self.figures_dir = figures_dir or FIGURES_DIR
        self.figures_dir.mkdir(parents=True, exist_ok=True)

        self.df_clim = pd.read_parquet(PROCESSED_DIR / "m27_climate_indices_aligned.parquet")
        self.df_prev = pd.read_parquet(PROCESSED_DIR / "m27_regime_annual_seasonal_prevalence.parquet")
        self.df_rain = pd.read_parquet(PROCESSED_DIR / "m27_rainfall_annual_seasonal_modulation.parquet")
        self.df_corr = pd.read_csv(TABLES_DIR / "m27_regime_climate_correlations.csv")
        self.df_rain_corr = pd.read_csv(TABLES_DIR / "m27_rainfall_climate_modulation.csv")
        self.df_matrix = pd.read_parquet(PROCESSED_DIR / "m27_joint_enso_iod_matrix.parquet")
        self.df_spatial = pd.read_parquet(PROCESSED_DIR / "m27_spatial_teleconnections.parquet")
        self.df_loocv_regime = pd.read_csv(TABLES_DIR / "m27_regime_climate_loocv.csv")
        self.df_loocv_rain = pd.read_csv(TABLES_DIR / "m27_rainfall_loocv_sensitivity.csv")

    def generate_fig01_annual_timeseries(self) -> Path:
        """Fig 1: Annual RONI and DMI time series (2010-2021)."""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, dpi=300)

        # Plot Post-Monsoon (peak teleconnection season) series
        post_sub = self.df_clim[self.df_clim["season_id"] == 2].sort_values("year")
        years = post_sub["year"].values
        roni = post_sub["roni_anomaly"].values
        dmi = post_sub["dmi_anomaly"].values

        # RONI Panel
        ax1.plot(years, roni, color="#D95F02", marker="o", linewidth=2.2, label="RONI (SON)")
        ax1.axhline(0.50, color="#D95F02", linestyle="--", alpha=0.7, label="El Niño Threshold (+0.50°C)")
        ax1.axhline(-0.50, color="#1B9E77", linestyle="--", alpha=0.7, label="La Niña Threshold (-0.50°C)")
        ax1.axhline(0.0, color="#777777", linestyle="-", linewidth=0.8)
        ax1.fill_between(years, roni, 0.50, where=(roni >= 0.50), color="#D95F02", alpha=0.25)
        ax1.fill_between(years, roni, -0.50, where=(roni <= -0.50), color="#1B9E77", alpha=0.25)
        ax1.set_ylabel("RONI Anomaly (°C)", fontsize=11, fontweight="bold")
        ax1.set_title("Annual Climate Indices over the Indian Monsoon Study Period (2010–2021)", fontsize=13, fontweight="bold")
        ax1.grid(True)
        ax1.legend(loc="upper left", framealpha=0.9, fontsize=9)
        ax1.set_ylim(-2.0, 2.5)

        # Annotate 2015 Super El Niño
        ax1.annotate("2015 Super El Niño\n(+2.03°C)", xy=(2015, 2.03), xytext=(2013.2, 1.8),
                     arrowprops=dict(facecolor="#D95F02", shrink=0.08, width=1, headwidth=6),
                     fontsize=9, fontweight="bold", color="#D95F02")

        # DMI Panel
        ax2.plot(years, dmi, color="#7570B3", marker="s", linewidth=2.2, label="DMI (Oct-Nov Mean)")
        ax2.axhline(0.40, color="#7570B3", linestyle="--", alpha=0.7, label="Positive IOD (+0.40°C)")
        ax2.axhline(-0.40, color="#E7298A", linestyle="--", alpha=0.7, label="Negative IOD (-0.40°C)")
        ax2.axhline(0.0, color="#777777", linestyle="-", linewidth=0.8)
        ax2.fill_between(years, dmi, 0.40, where=(dmi >= 0.40), color="#7570B3", alpha=0.25)
        ax2.fill_between(years, dmi, -0.40, where=(dmi <= -0.40), color="#E7298A", alpha=0.25)
        ax2.set_ylabel("DMI Anomaly (°C)", fontsize=11, fontweight="bold")
        ax2.set_xlabel("Study Year (2010–2021)", fontsize=11, fontweight="bold")
        ax2.set_xticks(years)
        ax2.grid(True)
        ax2.legend(loc="upper left", framealpha=0.9, fontsize=9)
        ax2.set_ylim(-0.8, 1.2)

        # Annotate 2019 Super Positive IOD
        ax2.annotate("2019 Super Positive IOD\n(+0.90°C)", xy=(2019, 0.90), xytext=(2017.0, 0.95),
                     arrowprops=dict(facecolor="#7570B3", shrink=0.08, width=1, headwidth=6),
                     fontsize=9, fontweight="bold", color="#7570B3")

        plt.tight_layout()
        out_path = self.figures_dir / "fig01_annual_roni_dmi_timeseries.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated {out_path.name}")
        return out_path

    def generate_fig02_alignment_matrix(self) -> Path:
        """Fig 2: Annual-seasonal climate index alignment matrix."""
        fig, ax = plt.subplots(figsize=(10, 8), dpi=300)

        pivot_data = self.df_clim.pivot(index="year", columns="season", values="roni_anomaly")
        season_order = ["pre_monsoon", "established_monsoon", "post_monsoon"]
        pivot_data = pivot_data[season_order]

        sns.heatmap(
            pivot_data, annot=True, fmt=".2f", cmap="coolwarm", center=0.0,
            cbar_kws={"label": "RONI Anomaly (°C)"}, ax=ax, linewidths=1.0, linecolor="white"
        )
        ax.set_title("Annual-Seasonal RONI Matrix Across Three 30-Day Observation Windows", fontsize=12, fontweight="bold")
        ax.set_xlabel("Monsoon Season", fontsize=11, fontweight="bold")
        ax.set_ylabel("Year", fontsize=11, fontweight="bold")
        ax.set_xticklabels(["Pre-Monsoon\n(MAM)", "Established Monsoon\n(JJA)", "Post-Monsoon\n(SON)"], rotation=0)

        plt.tight_layout()
        out_path = self.figures_dir / "fig02_annual_seasonal_alignment_matrix.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated {out_path.name}")
        return out_path

    def generate_fig03_regime_prevalence_vs_climate(self) -> Path:
        """Fig 3: R0-R3 prevalence versus RONI and DMI."""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10), dpi=300)
        df_m = pd.merge(self.df_clim, self.df_prev, on=["year", "season_id", "season"])

        colors = ["#1F78B4", "#33A02C", "#E31A1C", "#FF7F00"]
        regime_labels = ["R0: Mixed Convective", "R1: Shallow Cumulus", "R2: Deep Storm Cores", "R3: Cirrus/Anvil"]

        for k in range(4):
            ax = axes[k // 2, k % 2]
            for sid, sname, mkr in [(0, "Pre-Monsoon", "o"), (1, "Established Monsoon", "s"), (2, "Post-Monsoon", "^")]:
                sub = df_m[df_m["season_id"] == sid]
                ax.scatter(sub["roni_anomaly"], sub[f"p_R{k}_domain"], label=sname, marker=mkr, s=60, alpha=0.85)
            ax.set_title(regime_labels[k], fontsize=11, fontweight="bold")
            ax.set_xlabel("RONI Anomaly (°C)", fontsize=10)
            ax.set_ylabel(f"P(R{k}) Occurrence Fraction", fontsize=10)
            ax.grid(True)
            if k == 0:
                ax.legend(loc="upper left", fontsize=8)

        fig.suptitle("Frozen M25 Cloud Regime Prevalence vs. NOAA RONI (2010–2021)", fontsize=13, fontweight="bold")
        plt.tight_layout()
        out_path = self.figures_dir / "fig03_regime_prevalence_vs_climate_indices.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated {out_path.name}")
        return out_path

    def generate_fig04_partial_correlations(self) -> Path:
        """Fig 4: Partial rank correlations comparing simple vs partial."""
        fig, ax = plt.subplots(figsize=(11, 7), dpi=300)

        sub_corr = self.df_corr[self.df_corr["season_id"] >= 0].copy()
        y_labels = [f"{r['season'][:4].upper()}-{r['regime']}" for _, r in sub_corr.iterrows()]
        y_pos = np.arange(len(y_labels))

        bar_width = 0.38
        ax.barh(y_pos - bar_width / 2, sub_corr["rho_roni"], height=bar_width, color="#D95F02", alpha=0.6, label="Spearman rho(RONI)")
        ax.barh(y_pos - bar_width / 2, sub_corr["rho_partial_roni"], height=bar_width, color="#D95F02", edgecolor="black", fill=False, linewidth=1.8, label="Partial rho(RONI | DMI)")

        ax.barh(y_pos + bar_width / 2, sub_corr["rho_dmi"], height=bar_width, color="#7570B3", alpha=0.6, label="Spearman rho(DMI)")
        ax.barh(y_pos + bar_width / 2, sub_corr["rho_partial_dmi"], height=bar_width, color="#7570B3", edgecolor="black", fill=False, linewidth=1.8, label="Partial rho(DMI | RONI)")

        ax.axvline(0.0, color="#333333", linestyle="-", linewidth=0.8)
        ax.axvline(0.497, color="gray", linestyle=":", alpha=0.7, label="Critical Threshold alpha=0.10 (|rho|=0.497)")
        ax.axvline(-0.497, color="gray", linestyle=":", alpha=0.7)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(y_labels, fontsize=9)
        ax.set_xlabel("Rank Correlation Coefficient", fontsize=11, fontweight="bold")
        ax.set_title("Simple vs. Partial Spearman Rank Correlations by Season and Regime", fontsize=12, fontweight="bold")
        ax.grid(True, axis="x")
        ax.legend(loc="lower right", framealpha=0.9, fontsize=8)
        ax.set_xlim(-1.0, 1.0)

        plt.tight_layout()
        out_path = self.figures_dir / "fig04_partial_rank_correlations.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated {out_path.name}")
        return out_path

    def generate_fig05_seasonal_rainfall_vs_climate(self) -> Path:
        """Fig 5: Seasonal rainfall versus climate indices."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
        df_m = pd.merge(self.df_clim, self.df_rain, on=["year", "season_id", "season"])

        markers = ["o", "s", "^"]
        season_names = ["Pre-Monsoon", "Established Monsoon", "Post-Monsoon"]

        for sid in [0, 1, 2]:
            sub = df_m[df_m["season_id"] == sid]
            ax1.scatter(sub["roni_anomaly"], sub["mean_rainfall_mm"], label=season_names[sid], marker=markers[sid], s=70)
            ax2.scatter(sub["dmi_anomaly"], sub["mean_rainfall_mm"], label=season_names[sid], marker=markers[sid], s=70)

        ax1.set_xlabel("RONI Anomaly (°C)", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Terrestrial Mean Rainfall (mm/day)", fontsize=11, fontweight="bold")
        ax1.set_title("Rainfall vs. NOAA RONI", fontsize=12, fontweight="bold")
        ax1.grid(True)
        ax1.legend(loc="upper right")

        ax2.set_xlabel("DMI Anomaly (°C)", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Terrestrial Mean Rainfall (mm/day)", fontsize=11, fontweight="bold")
        ax2.set_title("Rainfall vs. NOAA DMI", fontsize=12, fontweight="bold")
        ax2.grid(True)
        ax2.legend(loc="upper right")

        fig.suptitle("Terrestrial Mean Daily Rainfall Response to Climate Forcing (2010–2021)", fontsize=13, fontweight="bold")
        plt.tight_layout()
        out_path = self.figures_dir / "fig05_seasonal_rainfall_vs_climate_indices.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated {out_path.name}")
        return out_path

    def generate_fig06_regime_conditional_rainfall(self) -> Path:
        """Fig 6: Regime-specific rainfall response."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
        df_m = pd.merge(self.df_clim, self.df_rain, on=["year", "season_id", "season"])
        post_sub = df_m[df_m["season_id"] == 2]

        # R2 conditional intensity in post-monsoon
        sns.barplot(data=post_sub, x="enso_phase", y="cond_mean_R2", hue="enso_phase", palette="Set2", ax=ax1, ci=None)
        ax1.set_title("Post-Monsoon: R2 Convective Intensity by ENSO Phase", fontsize=11, fontweight="bold")
        ax1.set_ylabel("R2 Conditional Mean Rainfall (mm/day)", fontsize=10, fontweight="bold")
        ax1.set_xlabel("ENSO Phase", fontsize=10, fontweight="bold")
        ax1.grid(True, axis="y")

        # R2 volume contribution in post-monsoon
        sns.barplot(data=post_sub, x="enso_phase", y="vol_contrib_R2", hue="enso_phase", palette="Pastel2", ax=ax2, ci=None)
        ax2.set_title("Post-Monsoon: R2 Volume Contribution Fraction", fontsize=11, fontweight="bold")
        ax2.set_ylabel("R2 Volume Contribution Fraction", fontsize=10, fontweight="bold")
        ax2.set_xlabel("ENSO Phase", fontsize=10, fontweight="bold")
        ax2.grid(True, axis="y")

        plt.tight_layout()
        out_path = self.figures_dir / "fig06_regime_conditional_rainfall_response.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated {out_path.name}")
        return out_path

    def generate_fig07_enso_phase_maps(self) -> Path:
        """Fig 7: ENSO phase composite maps over 328 Tier 1 cells."""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=300)

        for sid, sname in [(0, "Pre-Monsoon"), (1, "Established Monsoon"), (2, "Post-Monsoon")]:
            ax = axes[sid]
            sub = self.df_spatial[self.df_spatial["season_id"] == sid]
            sc = ax.scatter(
                sub["longitude"], sub["latitude"], c=sub["delta_rainfall_enso_mm"],
                cmap="BrBG", s=25, vmin=-3.0, vmax=3.0, edgecolors="none"
            )
            ax.set_title(f"{sname}\nDelta Rain: El Niño - La Niña", fontsize=10, fontweight="bold")
            ax.set_xlabel("Longitude (°E)", fontsize=9)
            ax.set_ylabel("Latitude (°N)", fontsize=9)
            ax.grid(True, linestyle=":", alpha=0.6)
            ax.set_xlim(68, 98)
            ax.set_ylim(6, 38)
            plt.colorbar(sc, ax=ax, orientation="horizontal", pad=0.15, label="Delta Rainfall (mm/day)")

        fig.suptitle("Spatial Rainfall Anomaly Composites: El Niño vs. La Niña (328 Tier 1 Cells)", fontsize=13, fontweight="bold")
        plt.tight_layout()
        out_path = self.figures_dir / "fig07_enso_phase_composite_maps.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated {out_path.name}")
        return out_path

    def generate_fig08_iod_phase_maps(self) -> Path:
        """Fig 8: IOD phase composite maps over 328 Tier 1 cells."""
        fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=300)

        for sid, sname in [(0, "Pre-Monsoon"), (1, "Established Monsoon"), (2, "Post-Monsoon")]:
            ax = axes[sid]
            sub = self.df_spatial[self.df_spatial["season_id"] == sid]
            sc = ax.scatter(
                sub["longitude"], sub["latitude"], c=sub["delta_rainfall_iod_mm"],
                cmap="PuOr", s=25, vmin=-3.0, vmax=3.0, edgecolors="none"
            )
            ax.set_title(f"{sname}\nDelta Rain: Pos IOD - Neg IOD", fontsize=10, fontweight="bold")
            ax.set_xlabel("Longitude (°E)", fontsize=9)
            ax.set_ylabel("Latitude (°N)", fontsize=9)
            ax.grid(True, linestyle=":", alpha=0.6)
            ax.set_xlim(68, 98)
            ax.set_ylim(6, 38)
            plt.colorbar(sc, ax=ax, orientation="horizontal", pad=0.15, label="Delta Rainfall (mm/day)")

        fig.suptitle("Spatial Rainfall Anomaly Composites: Positive IOD vs. Negative IOD (328 Tier 1 Cells)", fontsize=13, fontweight="bold")
        plt.tight_layout()
        out_path = self.figures_dir / "fig08_iod_phase_composite_maps.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated {out_path.name}")
        return out_path

    def generate_fig09_joint_phase_matrix(self) -> Path:
        """Fig 9: Joint ENSO-IOD 3x3 phase contingency heatmap."""
        fig, ax = plt.subplots(figsize=(8, 6), dpi=300)
        post_matrix = self.df_matrix[self.df_matrix["season_id"] == 2]

        pivot_n = post_matrix.pivot(index="enso_phase", columns="iod_phase", values="n_years").reindex(
            index=["El Niño", "Neutral", "La Niña"], columns=["Positive IOD", "Neutral", "Negative IOD"]
        )

        sns.heatmap(pivot_n, annot=True, fmt="d", cmap="Blues", cbar_kws={"label": "Sample Size (Years)"}, ax=ax)
        ax.set_title("Post-Monsoon Joint ENSO–IOD Contingency Matrix (N=12 Years)", fontsize=12, fontweight="bold")
        ax.set_xlabel("Indian Ocean Dipole Phase", fontsize=11, fontweight="bold")
        ax.set_ylabel("ENSO Phase (RONI)", fontsize=11, fontweight="bold")

        plt.tight_layout()
        out_path = self.figures_dir / "fig09_joint_enso_iod_phase_matrix.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated {out_path.name}")
        return out_path

    def generate_fig10_loocv_diagnostics(self) -> Path:
        """Fig 10: Sensitivity and leave-one-year-out diagnostics."""
        fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
        est_r3 = self.df_loocv_regime[(self.df_loocv_regime["season"] == "established_monsoon") & (self.df_loocv_regime["regime"] == "R3")]

        years = est_r3["dropped_year"].values
        delta_roni = est_r3["delta_rho_roni"].values
        delta_dmi = est_r3["delta_rho_dmi"].values

        x = np.arange(len(years))
        width = 0.35

        ax.bar(x - width / 2, delta_roni, width, color="#D95F02", alpha=0.8, label="Influence on rho(R3, RONI)")
        ax.bar(x + width / 2, delta_dmi, width, color="#7570B3", alpha=0.8, label="Influence on rho(R3, DMI)")

        ax.axhline(0.0, color="#333333", linestyle="-", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(years, fontsize=9)
        ax.set_xlabel("Dropped Year in Jackknife LOOCV", fontsize=11, fontweight="bold")
        ax.set_ylabel("Delta rho (Full - LOO)", fontsize=11, fontweight="bold")
        ax.set_title("Established Monsoon R3: Leave-One-Year-Out Influence Diagnostics", fontsize=12, fontweight="bold")
        ax.grid(True, axis="y")
        ax.legend(loc="upper right", framealpha=0.9)

        # Annotate 2015 leverage
        idx_2015 = list(years).index(2015)
        ax.annotate("2015 Leverage", xy=(idx_2015 - width / 2, delta_roni[idx_2015]),
                    xytext=(idx_2015 - 1.5, delta_roni[idx_2015] + 0.05),
                    arrowprops=dict(facecolor="#D95F02", shrink=0.08, width=1, headwidth=5),
                    fontsize=9, fontweight="bold", color="#D95F02")

        plt.tight_layout()
        out_path = self.figures_dir / "fig10_sensitivity_loocv_diagnostics.png"
        fig.savefig(out_path, dpi=300)
        plt.close(fig)
        logger.info(f"Generated {out_path.name}")
        return out_path

    def generate_all_figures(self) -> Dict[str, Path]:
        """Generate all 10 publication figures."""
        logger.info("Generating all 10 M27 publication figures at 300 DPI...")
        paths = {
            "fig01": self.generate_fig01_annual_timeseries(),
            "fig02": self.generate_fig02_alignment_matrix(),
            "fig03": self.generate_fig03_regime_prevalence_vs_climate(),
            "fig04": self.generate_fig04_partial_correlations(),
            "fig05": self.generate_fig05_seasonal_rainfall_vs_climate(),
            "fig06": self.generate_fig06_regime_conditional_rainfall(),
            "fig07": self.generate_fig07_enso_phase_maps(),
            "fig08": self.generate_fig08_iod_phase_maps(),
            "fig09": self.generate_fig09_joint_phase_matrix(),
            "fig10": self.generate_fig10_loocv_diagnostics(),
        }
        return paths


if __name__ == "__main__":
    generator = M27FigureGenerator()
    generated = generator.generate_all_figures()
    print("M27 Figure Generation Completed Successfully (10 figures generated at 300 DPI):")
    for name, p in generated.items():
        print(f"  {name}: {p.name} ({p.stat().st_size} bytes)")
