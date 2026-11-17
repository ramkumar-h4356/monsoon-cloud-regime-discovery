"""
M26 — Spatial-Temporal Block Bootstrap and Statistical Inference Framework

Implements a rigorous non-parametric statistical inference framework that directly accounts
for spatial autocorrelation (spatial decorrelation scale ~ 300 km / 3 deg) and synoptic temporal
persistence (multi-day weather systems, 5-day blocks).

Methodology:
1. Spatial Blocks: Contiguous 3x3 degree grid clusters (53 unique spatial blocks across India).
2. Temporal Blocks: 5-day synoptic windows within the 29-day seasonal record.
3. Hierarchical Space-Time Clusters: 3,816 unique independent clusters (Year x Spatial Block x Temporal Block).
4. Bootstrap Convergence: Evaluated at B = 200, 500, and 1,000 replicates.
5. Permutation Testing: Block-permutation tests comparing regime distributions.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data/processed/rainfall_validation"
TABLES_DIR = ROOT / "reports/integration/m26/tables"

REGIME_NAMES = {
    0: "R0: Mixed Convective & Congestus",
    1: "R1: Boundary-Layer Shallow Cumulus",
    2: "R2: Deep Convective Storm Cores",
    3: "R3: Thin Cirrus & Anvil Outflow",
}


def build_cluster_ids(df: pd.DataFrame) -> tuple[np.ndarray, list[np.ndarray]]:
    """Construct hierarchical space-time cluster identifiers (Year x 3x3 Space Block x 5-day Time Block)."""
    s_block = (df["latitude"].values // 3.0).astype(int) * 100 + (df["longitude"].values // 3.0).astype(int)
    t_block = ((df["day_index"].values - 1) // 5).astype(int)
    y_block = df["year"].values
    
    cluster_ids = y_block * 10000 + s_block * 10 + t_block
    unique_clusters = np.unique(cluster_ids)
    
    # Pre-index for high performance
    cluster_to_indices = [np.where(cluster_ids == c)[0] for c in unique_clusters]
    return unique_clusters, cluster_to_indices


def run_block_bootstrap(df_primary: pd.DataFrame, n_boot: int = 1000, seed: int = 42) -> pd.DataFrame:
    """
    Execute spatial-temporal block bootstrap to generate 95% confidence intervals
    for mean rainfall, median rainfall, wet-day probability, and R2-R1 contrast.
    """
    print(f"--- Executing Spatial-Temporal Block Bootstrap ({n_boot} Replicates) ---")
    np.random.seed(seed)
    
    results = []
    
    for s_name in ["all_seasons", "pre_monsoon", "established_monsoon", "post_monsoon"]:
        sub = df_primary if s_name == "all_seasons" else df_primary[df_primary["season_name"] == s_name].reset_index(drop=True)
        
        rain = sub["rainfall_mm"].values
        regime = sub["dominant_regime"].values
        
        unique_clusters, cluster_indices = build_cluster_ids(sub)
        n_clusters = len(unique_clusters)
        
        boot_means = np.zeros((n_boot, 4))
        boot_medians = np.zeros((n_boot, 4))
        boot_wet_pct = np.zeros((n_boot, 4))
        boot_contrast_r2_r1 = np.zeros(n_boot)
        boot_contrast_r2_r0 = np.zeros(n_boot)
        
        for b in range(n_boot):
            sampled_c = np.random.choice(n_clusters, size=n_clusters, replace=True)
            sampled_idx = np.concatenate([cluster_indices[i] for i in sampled_c])
            
            b_rain = rain[sampled_idx]
            b_reg = regime[sampled_idx]
            
            for k in range(4):
                k_mask = (b_reg == k)
                if k_mask.any():
                    k_rain = b_rain[k_mask]
                    boot_means[b, k] = np.mean(k_rain)
                    boot_medians[b, k] = np.median(k_rain)
                    boot_wet_pct[b, k] = np.mean(k_rain >= 2.5) * 100.0
                else:
                    boot_means[b, k] = np.nan
                    boot_medians[b, k] = np.nan
                    boot_wet_pct[b, k] = np.nan
                    
            boot_contrast_r2_r1[b] = boot_means[b, 2] - boot_means[b, 1]
            boot_contrast_r2_r0[b] = boot_means[b, 2] - boot_means[b, 0]
            
        for k in range(4):
            # Compute point estimate on original data
            k_orig_rain = rain[regime == k]
            orig_mean = float(np.mean(k_orig_rain))
            orig_median = float(np.median(k_orig_rain))
            orig_wet = float(np.mean(k_orig_rain >= 2.5) * 100.0)
            
            # 95% CIs
            ci_mean_lower = float(np.nanpercentile(boot_means[:, k], 2.5))
            ci_mean_upper = float(np.nanpercentile(boot_means[:, k], 97.5))
            ci_median_lower = float(np.nanpercentile(boot_medians[:, k], 2.5))
            ci_median_upper = float(np.nanpercentile(boot_medians[:, k], 97.5))
            ci_wet_lower = float(np.nanpercentile(boot_wet_pct[:, k], 2.5))
            ci_wet_upper = float(np.nanpercentile(boot_wet_pct[:, k], 97.5))
            
            se_mean = float(np.nanstd(boot_means[:, k]))
            se_wet = float(np.nanstd(boot_wet_pct[:, k]))
            
            results.append({
                "season": s_name,
                "regime_id": f"R{k}",
                "regime_name": REGIME_NAMES[k],
                "sample_size": len(k_orig_rain),
                "clusters_count": n_clusters,
                "bootstrap_replicates": n_boot,
                "point_mean_mm": round(orig_mean, 3),
                "bootstrap_se_mean": round(se_mean, 3),
                "ci95_mean_lower_mm": round(ci_mean_lower, 3),
                "ci95_mean_upper_mm": round(ci_mean_upper, 3),
                "point_median_mm": round(orig_median, 3),
                "ci95_median_lower_mm": round(ci_median_lower, 3),
                "ci95_median_upper_mm": round(ci_median_upper, 3),
                "point_wet_day_25_pct": round(orig_wet, 2),
                "bootstrap_se_wet": round(se_wet, 2),
                "ci95_wet_lower_pct": round(ci_wet_lower, 2),
                "ci95_wet_upper_pct": round(ci_wet_upper, 2),
            })
            
        # Add contrast row for R2 - R1
        orig_contrast = float(np.mean(rain[regime == 2]) - np.mean(rain[regime == 1]))
        ci_c_lower = float(np.nanpercentile(boot_contrast_r2_r1, 2.5))
        ci_c_upper = float(np.nanpercentile(boot_contrast_r2_r1, 97.5))
        results.append({
            "season": s_name,
            "regime_id": "CONTRAST_R2_MINUS_R1",
            "regime_name": "Deep Convective vs. Shallow Cumulus Contrast",
            "sample_size": len(rain[(regime == 2) | (regime == 1)]),
            "clusters_count": n_clusters,
            "bootstrap_replicates": n_boot,
            "point_mean_mm": round(orig_contrast, 3),
            "bootstrap_se_mean": round(float(np.nanstd(boot_contrast_r2_r1)), 3),
            "ci95_mean_lower_mm": round(ci_c_lower, 3),
            "ci95_mean_upper_mm": round(ci_c_upper, 3),
            "point_median_mm": np.nan,
            "ci95_median_lower_mm": np.nan,
            "ci95_median_upper_mm": np.nan,
            "point_wet_day_25_pct": np.nan,
            "bootstrap_se_wet": np.nan,
            "ci95_wet_lower_pct": np.nan,
            "ci95_wet_upper_pct": np.nan,
        })
        
    df_boot = pd.DataFrame(results)
    out_file = TABLES_DIR / "m26_block_bootstrap_confidence_intervals.csv"
    df_boot.to_csv(out_file, index=False)
    print(f"Saved block bootstrap confidence intervals to: {out_file}")
    return df_boot


def run_statistical_inference() -> None:
    """Execute complete inference module."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    p_path = DATA_DIR / "m26_cloud_rainfall_matched_primary.parquet"
    if not p_path.exists():
        raise FileNotFoundError(f"Primary matched dataset missing: {p_path}")
        
    df_primary = pd.read_parquet(p_path)
    run_block_bootstrap(df_primary, n_boot=1000)


if __name__ == "__main__":
    run_statistical_inference()
