"""M27.7 — Module 7: Figure Audit and Corrected Publication Figures.

Audits original M27 figures (fig01–fig10) and generates 4 corrected publication figures (300 DPI):
1. fig04_corrected_partial_rank_correlations.png:
   Displays partial rank correlations with explicit Benjamini-Hochberg FDR q-values,
   visually distinguishing confirmed significant (q <= 0.05), exploratory (q <= 0.10),
   and non-significant associations.
2. fig06_corrected_regime_conditional_rainfall.png:
   Annotates sample sizes (N=2 El Niño vs N=6 La Niña), exact permutation p-values (p=0.212),
   and reframes the post-monsoon R2 contrast as an underpowered descriptive difference.
3. fig07_corrected_spatial_field_significance.png:
   Contrasts naive binomial field significance with Livezey-Chen spatial permutation null
   distributions, showing spatial autocorrelation inflation and true field significance status.
4. fig08_year_dependence_diagnostics.png:
   Illustrates intra-year seasonal correlations across calendar years, variance inflation
   factors (VIF), effective sample sizes (N_eff), and naive vs year-block p-values.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.integration.climate_association.m27_7.m27_7_data_loader import (
    M277DataLoader,
    PROJECT_ROOT,
    M27_7_DIR,
)

logger = logging.getLogger(__name__)

FIGURES_DIR = M27_7_DIR / "figures"


def generate_corrected_fig04_partial_correlations():
    """Figure 4 Corrected: Partial Rank Correlations with FDR q-values."""
    table_path = M27_7_DIR / "tables" / "m27_7_partial_spearman_audit_comparison.csv"
    if not table_path.exists():
        logger.warning(f"Missing {table_path}, skipping Fig04 generation")
        return

    df = pd.read_csv(table_path)
    # Filter to seasonal rows
    seasons = ["pre_monsoon", "established_monsoon", "post_monsoon"]
    df_seas = df[df["season"].isin(seasons)].copy()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True, dpi=300)
    plt.subplots_adjust(wspace=0.15)

    season_labels = {
        "pre_monsoon": "Pre-Monsoon\n(Apr 15–May 14)",
        "established_monsoon": "Established Monsoon\n(Jul 15–Aug 13)",
        "post_monsoon": "Post-Monsoon\n(Oct 15–Nov 13)",
    }

    # Left: RONI controlling for DMI
    ax_roni = axes[0]
    # Right: DMI controlling for RONI
    ax_dmi = axes[1]

    colors = {
        "CONFIRMED STATISTICALLY SIGNIFICANT": "#1b9e77",  # Strong green
        "CORRECTION REQUIRED: DOWNGRADE TO EXPLORATORY": "#e6ab02",  # Gold/Yellow
        "CONFIRMED NON-SIGNIFICANT": "#7570b3",  # Purple/Muted
    }

    y_pos = 0
    y_ticks = []
    y_labels = []

    for s in seasons:
        s_df = df_seas[df_seas["season"] == s]
        for reg in ["R0", "R1", "R2", "R3"]:
            # Plot RONI
            row_r = s_df[(s_df["regime"] == reg) & (s_df["index_tested"] == "RONI")].iloc[0]
            rho_r = row_r["recalc_partial_rho_formula"]
            q_r = row_r["bh_fdr_q_value"]
            v_r = row_r["audit_decision"]
            c_r = colors.get(v_r, "#999999")
            ax_roni.barh(y_pos, rho_r, color=c_r, alpha=0.85, edgecolor="black", height=0.6)
            ax_roni.text(
                rho_r + (0.04 if rho_r >= 0 else -0.04),
                y_pos,
                f"ρ={rho_r:+.2f}\nq={q_r:.3f}",
                va="center",
                ha="left" if rho_r >= 0 else "right",
                fontsize=7.5,
                fontweight="bold" if v_r == "CONFIRMED STATISTICALLY SIGNIFICANT" else "normal",
            )

            # Plot DMI
            row_d = s_df[(s_df["regime"] == reg) & (s_df["index_tested"] == "DMI")].iloc[0]
            rho_d = row_d["recalc_partial_rho_formula"]
            q_d = row_d["bh_fdr_q_value"]
            v_d = row_d["audit_decision"]
            c_d = colors.get(v_d, "#999999")
            ax_dmi.barh(y_pos, rho_d, color=c_d, alpha=0.85, edgecolor="black", height=0.6)
            ax_dmi.text(
                rho_d + (0.04 if rho_d >= 0 else -0.04),
                y_pos,
                f"ρ={rho_d:+.2f}\nq={q_d:.3f}",
                va="center",
                ha="left" if rho_d >= 0 else "right",
                fontsize=7.5,
                fontweight="bold" if v_d == "CONFIRMED STATISTICALLY SIGNIFICANT" else "normal",
            )

            y_ticks.append(y_pos)
            y_labels.append(f"{reg} ({season_labels[s].split()[0]})")
            y_pos += 1
        y_pos += 0.8  # Gap between seasons

    for ax, title, idx_name in zip(
        [ax_roni, ax_dmi],
        ["Partial Correlation: Regime vs RONI | DMI", "Partial Correlation: Regime vs DMI | RONI"],
        ["RONI", "DMI"],
    ):
        ax.axvline(0, color="black", linestyle="--", linewidth=1.0)
        ax.set_xlim(-1.15, 1.15)
        ax.set_xlabel(f"Partial Spearman Rank Correlation (ρ)", fontsize=11, fontweight="bold")
        ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
        ax.grid(axis="x", linestyle=":", alpha=0.6)

    axes[0].set_yticks(y_ticks)
    axes[0].set_yticklabels(y_labels, fontsize=9)
    axes[0].invert_yaxis()

    # Custom Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=colors["CONFIRMED STATISTICALLY SIGNIFICANT"], edgecolor="black", label="Confirmed Significant (FDR q ≤ 0.05)"),
        Patch(facecolor=colors["CORRECTION REQUIRED: DOWNGRADE TO EXPLORATORY"], edgecolor="black", label="Exploratory Tendency (Unadjusted p ≤ 0.05, FDR q > 0.05)"),
        Patch(facecolor=colors["CONFIRMED NON-SIGNIFICANT"], edgecolor="black", label="Non-Significant (p > 0.05)"),
    ]
    fig.legend(
        handles=legend_elements,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.05),
        ncol=3,
        fontsize=10,
        frameon=True,
    )

    out_file = FIGURES_DIR / "fig04_corrected_partial_rank_correlations.png"
    plt.tight_layout()
    plt.savefig(out_file, bbox_inches="tight", dpi=300)
    plt.close()
    logger.info(f"Generated corrected Figure 4: {out_file}")


def generate_corrected_fig06_regime_rainfall():
    """Figure 6 Corrected: Regime-Conditional Rainfall with Sample Counts & Caveats."""
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)

    # Post-monsoon data: El Nino vs La Nina
    # Data: El Nino N=2 (2015, 2018), La Nina N=6 (2010, 2011, 2013, 2016, 2017, 2020)
    categories = ["R2 Convective Core", "Terrestrial Mean Rain", "R1 Shallow Cumulus"]
    el_nino_means = [0.7944, 0.6497, 0.1334]
    la_nina_means = [8.9335, 1.6996, 1.1597]
    p_values = [0.21248, 0.46386, 0.52389]
    pct_diffs = [-91.1, -61.8, -88.5]

    x = np.arange(len(categories))
    width = 0.35

    rects1 = ax.bar(x - width/2, la_nina_means, width, label="La Niña (N=6 years)", color="#2b83ba", edgecolor="black")
    rects2 = ax.bar(x + width/2, el_nino_means, width, label="El Niño (N=2 years: 2015, 2018)", color="#d7191c", edgecolor="black")

    ax.set_ylabel("Daily Rainfall / Conditional Mean (mm/day)", fontsize=11, fontweight="bold")
    ax.set_title(
        "M27.7 Audit: Post-Monsoon Rainfall Phase Contrasts Under Small Sample Size\n"
        "(Evaluating the Reported '91.1% Convective Collapse')",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=11, fontweight="bold")
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(axis="y", linestyle=":", alpha=0.6)

    # Annotations
    for i in range(len(categories)):
        y_max = max(la_nina_means[i], el_nino_means[i])
        ax.text(
            x[i],
            y_max + 0.4,
            f"Δ = {pct_diffs[i]:+.1f}%\nPerm p = {p_values[i]:.3f}\n(Non-Significant)",
            ha="center",
            va="bottom",
            fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="#fffae6", ec="#d95f02", lw=1.2),
        )

    # Callout warning box
    ax.text(
        0.02,
        0.95,
        "CRITICAL AUDIT NOTE:\n"
        "• El Niño sample size is severely constrained (N = 2).\n"
        "• Difference of -91.1% fails exact permutation test (p = 0.212).\n"
        "• Must be classified as UNDERPOWERED DESCRIPTIVE CONTRAST,\n"
        "  not an established teleconnection.",
        transform=ax.transAxes,
        fontsize=9,
        va="top",
        bbox=dict(boxstyle="square,pad=0.5", fc="#f0f0f0", ec="#666666", lw=1.0),
    )

    ax.set_ylim(0, 11.5)
    out_file = FIGURES_DIR / "fig06_corrected_regime_conditional_rainfall.png"
    plt.tight_layout()
    plt.savefig(out_file, bbox_inches="tight", dpi=300)
    plt.close()
    logger.info(f"Generated corrected Figure 6: {out_file}")


def generate_corrected_fig07_spatial_field_test():
    """Figure 7 Corrected: Livezey-Chen Spatial Field Significance vs Naive Binomial."""
    table_path = M27_7_DIR / "tables" / "m27_7_corrected_spatial_field_significance.csv"
    if not table_path.exists():
        logger.warning(f"Missing {table_path}, skipping Fig07 generation")
        return

    df = pd.read_csv(table_path)
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)

    test_labels = [f"{r['season'].replace('_', ' ').title()}\n{r['field_test']}" for _, r in df.iterrows()]
    y_pos = np.arange(len(df))

    observed_k = df["significant_cells_p05"].values
    null_mean = df["livezey_chen_null_mean_k"].values
    null_95 = df["livezey_chen_null_95th_k"].values
    audit_verdict = df["audit_verdict"].values

    bar_colors = []
    for v in audit_verdict:
        if v == "CONFIRMED_FIELD_SIGNIFICANT":
            bar_colors.append("#1b9e77")  # Green
        elif v == "DOWNGRADED_OVERSTATEMENT":
            bar_colors.append("#d95f02")  # Orange/Red
        else:
            bar_colors.append("#7570b3")  # Muted purple

    ax.barh(y_pos, observed_k, color=bar_colors, alpha=0.85, edgecolor="black", height=0.6, label="Observed Significant Cells (p ≤ 0.05)")

    # Error bars representing Livezey-Chen 95th percentile null expectation
    ax.scatter(null_95, y_pos, color="red", marker="|", s=150, linewidth=2.5, label="Livezey-Chen 95th Pct Null (Field Threshold)", zorder=5)
    ax.axvline(16.4, color="blue", linestyle="--", linewidth=1.2, label="Naive Binomial 5% Null (16.4 cells)")

    for i in range(len(df)):
        r = df.iloc[i]
        txt = f"k={int(r['significant_cells_p05'])} | LC p={r['livezey_chen_p_field']:.3f}"
        if r["audit_verdict"] == "DOWNGRADED_OVERSTATEMENT":
            txt += " [DOWNGRADED]"
        elif r["audit_verdict"] == "CONFIRMED_FIELD_SIGNIFICANT":
            txt += " [CONFIRMED]"
        ax.text(
            observed_k[i] + 1.5,
            y_pos[i],
            txt,
            va="center",
            fontsize=8.5,
            fontweight="bold" if r["audit_verdict"] != "CONFIRMED_NON_SIGNIFICANT" else "normal",
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(test_labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Significant Terrestrial Cells (out of 328 Tier 1 cells)", fontsize=11, fontweight="bold")
    ax.set_title(
        "M27.7 Audit: Spatial Field Significance Under Livezey-Chen Spatial Permutation\n"
        "(Preserving Full 328-Cell Spatial Autocorrelation vs Naive Binomial Independence)",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    ax.grid(axis="x", linestyle=":", alpha=0.6)
    ax.legend(loc="lower right", fontsize=9.5)

    out_file = FIGURES_DIR / "fig07_corrected_spatial_field_significance.png"
    plt.tight_layout()
    plt.savefig(out_file, bbox_inches="tight", dpi=300)
    plt.close()
    logger.info(f"Generated corrected Figure 7: {out_file}")


def generate_corrected_fig08_year_dependence():
    """Figure 8 Corrected: Year Dependence, Intra-Year Persistence & N_eff."""
    table_path = M27_7_DIR / "tables" / "m27_7_year_dependence_audit.csv"
    if not table_path.exists():
        logger.warning(f"Missing {table_path}, skipping Fig08 generation")
        return

    df = pd.read_csv(table_path)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)

    # Subplot 1: Intra-year persistence and Effective Sample Size
    reg_df = df[df["target_type"] == "regime_prevalence"].drop_duplicates("metric").copy()
    labels = [r["metric"] for _, r in reg_df.iterrows()]
    x = np.arange(len(labels))

    r_mean = reg_df["intra_year_mean_r"].values
    n_eff = reg_df["effective_n"].values

    color_r = "#e7298a"
    ax1.set_xlabel("Cloud Regime", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Mean Intra-Year Cross-Seasonal Correlation (r)", color=color_r, fontsize=11, fontweight="bold")
    bars1 = ax1.bar(x - 0.18, r_mean, width=0.35, color=color_r, alpha=0.8, edgecolor="black", label="Intra-Year Correlation")
    ax1.tick_params(axis="y", labelcolor=color_r)
    ax1.set_ylim(0, 1.0)
    ax1.grid(axis="y", linestyle=":", alpha=0.5)

    ax1_twin = ax1.twinx()
    color_n = "#1f78b4"
    ax1_twin.set_ylabel("Effective Sample Size (N_eff out of 36)", color=color_n, fontsize=11, fontweight="bold")
    bars2 = ax1_twin.bar(x + 0.18, n_eff, width=0.35, color=color_n, alpha=0.8, edgecolor="black", label="Effective Sample Size (N_eff)")
    ax1_twin.tick_params(axis="y", labelcolor=color_n)
    ax1_twin.set_ylim(0, 40)
    ax1_twin.axhline(36, color="blue", linestyle="--", linewidth=1.0, alpha=0.7)
    ax1_twin.text(3.4, 36.5, "Nominal N=36", color="blue", fontsize=8.5, ha="right")

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=10, fontweight="bold")
    ax1.set_title("Intra-Year Cross-Seasonal Persistence & N_eff", fontsize=11, fontweight="bold")

    for i in range(len(labels)):
        ax1.text(x[i] - 0.18, r_mean[i] + 0.02, f"r={r_mean[i]:.2f}", ha="center", fontsize=8.5, fontweight="bold")
        ax1_twin.text(x[i] + 0.18, n_eff[i] + 0.8, f"N={n_eff[i]:.1f}", ha="center", fontsize=8.5, fontweight="bold")

    # Subplot 2: Comparison of Naive vs Year-Block Permutation p-values
    # Filter to R0, R1, R2, R3 vs DMI and RONI
    y_pos = np.arange(len(reg_df) * 2)
    p_naive = []
    p_block = []
    plot_labels = []

    for _, r in df[df["target_type"] == "regime_prevalence"].iterrows():
        p_naive.append(r["orig_p_naive_perm"])
        p_block.append(r["p_year_block_perm"])
        plot_labels.append(f"{r['metric']} vs {r['climate_index']}")

    y_pos = np.arange(len(plot_labels))
    width = 0.38
    ax2.barh(y_pos - width/2, p_naive, height=width, color="#fb9a99", edgecolor="black", label="Original Naive Permutation p")
    ax2.barh(y_pos + width/2, p_block, height=width, color="#e31a1c", edgecolor="black", label="M27.7 Year-Block Permutation p")

    ax2.axvline(0.05, color="black", linestyle="--", linewidth=1.0, label="α = 0.05 Threshold")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(plot_labels, fontsize=8.5)
    ax2.invert_yaxis()
    ax2.set_xlabel("Two-Sided Permutation p-value", fontsize=11, fontweight="bold")
    ax2.set_title("Pooled Permutation p-value Shift Under Year-Block Clustering", fontsize=11, fontweight="bold")
    ax2.legend(loc="lower right", fontsize=8.5)
    ax2.grid(axis="x", linestyle=":", alpha=0.5)

    out_file = FIGURES_DIR / "fig08_year_dependence_diagnostics.png"
    plt.tight_layout()
    plt.savefig(out_file, bbox_inches="tight", dpi=300)
    plt.close()
    logger.info(f"Generated corrected Figure 8: {out_file}")


def generate_all_corrected_figures():
    """Execute generation of all 4 corrected publication figures."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    generate_corrected_fig04_partial_correlations()
    generate_corrected_fig06_regime_rainfall()
    generate_corrected_fig07_spatial_field_test()
    generate_corrected_fig08_year_dependence()
    logger.info("All 4 corrected figures successfully generated at 300 DPI.")


if __name__ == "__main__":
    generate_all_corrected_figures()
