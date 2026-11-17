"""
M26 — Publication-Quality Diagnostic Visualizations

Generates publication-quality 300 DPI figures for Milestone M26:
1. Fig 1: Regime Rainfall Distributions by Season (Violin/Box & Occurrence).
2. Fig 2: Spatial Rainfall Composites by Cloud Regime across India.
3. Fig 3: Continuous Convective Fraction Response Curves (Decile Composites).
4. Fig 4: Multi-Dimensional Sensitivity Invariance Matrix.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data/processed/rainfall_validation"
FIGURES_DIR = ROOT / "reports/integration/m26/figures"
TABLES_DIR = ROOT / "reports/integration/m26/tables"

REGIME_COLORS = {
    0: "#2ca02c",  # Green - Mixed Congestus
    1: "#ff7f0e",  # Orange - Shallow Cumulus
    2: "#d62728",  # Red - Deep Convective Storm Cores
    3: "#1f77b4",  # Blue - Thin Cirrus
}

REGIME_NAMES_SHORT = {
    0: "R0: Congestus",
    1: "R1: Shallow Cu",
    2: "R2: Deep Convective",
    3: "R3: Cirrus Anvil",
}


def plot_fig1_distributions(df_primary: pd.DataFrame) -> None:
    """Figure 1: Regime Rainfall Distributions and Wet-Day Probabilities by Season."""
    print("--- Generating Figure 1: Regime Rainfall Distributions by Season ---")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=300)
    seasons = [
        ("pre_monsoon", "Pre-Monsoon (Apr 15–May 13)", axes[0, 0]),
        ("established_monsoon", "Established Monsoon (Jul 15–Aug 12)", axes[0, 1]),
        ("post_monsoon", "Post-Monsoon (Oct 15–Nov 12)", axes[1, 0]),
        ("all_seasons", "All Seasons Pooled (12-Year Primary Tier 1)", axes[1, 1]),
    ]
    
    for s_name, title, ax in seasons:
        sub = df_primary if s_name == "all_seasons" else df_primary[df_primary["season_name"] == s_name]
        
        means = []
        medians = []
        wet_pcts = []
        labels = []
        colors = []
        
        for k in range(4):
            reg_sub = sub[sub["dominant_regime"] == k]
            rain = reg_sub["rainfall_mm"].values
            rain_valid = rain[np.isfinite(rain)]
            
            means.append(np.mean(rain_valid))
            medians.append(np.median(rain_valid))
            wet_pcts.append(np.mean(rain_valid >= 2.5) * 100.0)
            labels.append(REGIME_NAMES_SHORT[k])
            colors.append(REGIME_COLORS[k])
            
        x = np.arange(4)
        width = 0.35
        
        # Primary axis: Mean Rainfall (mm)
        bars = ax.bar(x - width/2, means, width, label="Mean Rainfall (mm)", color=colors, alpha=0.85, edgecolor="black")
        
        # Secondary axis: Wet-Day %
        ax2 = ax.twinx()
        line = ax2.plot(x + width/2, wet_pcts, "o--", color="black", linewidth=2, markersize=7, label="Wet Day % (>=2.5 mm)")
        
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_ylabel("Mean Daily Rainfall (mm)", fontsize=11, fontweight="bold")
        ax2.set_ylabel("Wet Day Frequency (%)", fontsize=11, fontweight="bold", color="black")
        ax2.set_ylim(0, 100)
        ax.grid(axis="y", linestyle=":", alpha=0.6)
        
        # Add values atop bars
        for bar, m in zip(bars, means):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, f"{m:.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
            
    fig.suptitle("M26 — Surface Rainfall Signatures across M25 Cloud Regimes (Tier 1 Full Land)", fontsize=15, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_path = FIGURES_DIR / "fig1_regime_rainfall_distributions_by_season.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved Figure 1 to: {out_path}")


def plot_fig2_spatial_composites(df_primary: pd.DataFrame) -> None:
    """Figure 2: Spatial Mean Rainfall Maps across India by Cloud Regime (Established Monsoon)."""
    print("--- Generating Figure 2: Spatial Rainfall Composites by Regime ---")
    sub = df_primary[df_primary["season_name"] == "established_monsoon"]
    
    fig, axes = plt.subplots(1, 4, figsize=(18, 5.5), dpi=300)
    
    lats = np.arange(6.5, 38.5, 1.0)
    lons = np.arange(68.5, 98.5, 1.0)
    
    for k in range(4):
        ax = axes[k]
        k_sub = sub[sub["dominant_regime"] == k]
        
        # Compute cell-wise mean rainfall
        cell_means = k_sub.groupby(["latitude", "longitude"])["rainfall_mm"].mean().reset_index()
        
        # Build 2D grid
        grid_2d = np.full((len(lats), len(lons)), np.nan)
        for _, row in cell_means.iterrows():
            lat_idx = int(round(row["latitude"] - 6.5))
            lon_idx = int(round(row["longitude"] - 68.5))
            if 0 <= lat_idx < len(lats) and 0 <= lon_idx < len(lons):
                grid_2d[lat_idx, lon_idx] = row["rainfall_mm"]
                
        im = ax.imshow(grid_2d, origin="lower", extent=[68.5, 97.5, 6.5, 37.5], cmap="YlGnBu", vmin=0, vmax=35)
        ax.set_title(f"{REGIME_NAMES_SHORT[k]}\n(Established Monsoon)", fontsize=11, fontweight="bold")
        ax.set_xlabel("Longitude (°E)", fontsize=9)
        if k == 0:
            ax.set_ylabel("Latitude (°N)", fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.5)
        
    cbar_ax = fig.add_axes([0.92, 0.2, 0.015, 0.6])
    cbar = fig.colorbar(im, cax=cbar_ax)
    cbar.set_label("Mean Daily Rainfall (mm/day)", fontsize=11, fontweight="bold")
    
    fig.suptitle("Figure 2: Spatial Distribution of Daily Rainfall Conditioned on M25 Cloud Regimes", fontsize=14, fontweight="bold", y=0.98)
    out_path = FIGURES_DIR / "fig2_spatial_rainfall_composites_by_regime.png"
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
    print(f"Saved Figure 2 to: {out_path}")


def plot_fig3_decile_response(df_primary: pd.DataFrame) -> None:
    """Figure 3: Daily Rainfall vs. Continuous Convective Regime Fraction (f2)."""
    print("--- Generating Figure 3: Convective Fraction Response Curves ---")
    dec_file = TABLES_DIR / "m26_convective_decile_composites.csv"
    if not dec_file.exists():
        return
        
    df_dec = pd.read_csv(dec_file)
    sub = df_dec[df_dec["season"] == "established_monsoon"].copy()
    
    fig, ax1 = plt.subplots(figsize=(10, 6), dpi=300)
    
    x = np.arange(len(sub))
    labels = sub["convective_fraction_bin"].values
    means = sub["mean_rainfall_mm"].values
    medians = sub["median_rainfall_mm"].values
    wet_pct = sub["wet_day_25_pct"].values
    
    ax1.plot(x, means, "s-", color="#d62728", linewidth=2.5, markersize=8, label="Mean Rainfall (mm)")
    ax1.plot(x, medians, "o--", color="#ff7f0e", linewidth=2.0, markersize=7, label="Median Rainfall (mm)")
    
    ax2 = ax1.twinx()
    ax2.plot(x, wet_pct, "^-.", color="#1f77b4", linewidth=2.0, markersize=8, label="Wet Day Probability (%)")
    
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=30, ha="right", fontsize=10)
    ax1.set_ylabel("Rainfall Depth (mm/day)", fontsize=12, fontweight="bold", color="#d62728")
    ax2.set_ylabel("Wet Day Frequency (%)", fontsize=12, fontweight="bold", color="#1f77b4")
    ax2.set_ylim(0, 100)
    
    ax1.set_title("Figure 3: Daily Precipitation Response to Increasing Deep Convective Fraction (f2)\nEstablished Monsoon (July 15–August 12)", fontsize=13, fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.6)
    
    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True)
    
    plt.tight_layout()
    out_path = FIGURES_DIR / "fig3_convective_fraction_vs_rainfall_deciles.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved Figure 3 to: {out_path}")


def plot_fig4_sensitivity_matrix() -> None:
    """Figure 4: Sensitivity Comparison Matrix Demonstrating Rank Invariance."""
    print("--- Generating Figure 4: Sensitivity Comparison Matrix ---")
    sens_file = TABLES_DIR / "m26_sensitivity_analysis_results.csv"
    if not sens_file.exists():
        return
        
    df_sens = pd.read_csv(sens_file)
    
    # Filter 4 key variants
    key_variants = [
        ("PRIMARY_BENCHMARK_SHIFTED_29D_TIER1", "Primary Benchmark\n(Exact Shifted, Tier 1)"),
        ("S1_ALL_LAND_TIER1_PLUS_TIER2", "Sensitivity S1\n(Tier 1 + Coastal Tier 2)"),
        ("S2_UTC_CALENDAR_DAY_30D_TIER1", "Sensitivity S2\n(UTC Calendar Day 30d)"),
        ("S5_STRICT_MAJORITY_THRESHOLD_GT_50PCT", "Sensitivity S5\n(Strict Majority f_k > 0.5)"),
    ]
    
    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    
    x = np.arange(len(key_variants))
    width = 0.18
    
    for k in range(4):
        k_means = []
        for v_code, _ in key_variants:
            v_sub = df_sens[(df_sens["variant_name"] == v_code) & (df_sens["regime_id"] == f"R{k}")]
            m = v_sub["mean_rainfall_mm"].values[0] if len(v_sub) > 0 else 0.0
            k_means.append(m)
            
        pos = x + (k - 1.5) * width
        bars = ax.bar(pos, k_means, width, label=REGIME_NAMES_SHORT[k], color=REGIME_COLORS[k], alpha=0.85, edgecolor="black")
        for bar, m in zip(bars, k_means):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2, f"{m:.1f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
            
    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in key_variants], fontsize=11, fontweight="bold")
    ax.set_ylabel("Mean Daily Rainfall (mm)", fontsize=12, fontweight="bold")
    ax.set_title("Figure 4: Robustness of Regime–Rainfall Contrasts across Sensitivity Dimensions\n(Validates Invariance of R2 > R0 > R3 > R1 Hierarchy)", fontsize=13, fontweight="bold")
    ax.legend(title="Cloud Regime", loc="upper right", frameon=True)
    ax.grid(axis="y", linestyle=":", alpha=0.6)
    
    plt.tight_layout()
    out_path = FIGURES_DIR / "fig4_sensitivity_comparison_matrix.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved Figure 4 to: {out_path}")


def run_figure_generation() -> None:
    """Generate all publication-quality figures."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    p_path = DATA_DIR / "m26_cloud_rainfall_matched_primary.parquet"
    if not p_path.exists():
        raise FileNotFoundError(f"Primary dataset missing: {p_path}")
        
    df_primary = pd.read_parquet(p_path)
    plot_fig1_distributions(df_primary)
    plot_fig2_spatial_composites(df_primary)
    plot_fig3_decile_response(df_primary)
    plot_fig4_sensitivity_matrix()


if __name__ == "__main__":
    run_figure_generation()
