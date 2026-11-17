"""
M26 — Regime-Conditioned Rainfall Statistics Engine

Computes comprehensive parametric and non-parametric rainfall statistics conditioned
on M25 cloud regimes (R0, R1, R2, R3) across:
1. Pooled 3-season record (Primary Tier 1, 342,432 observations).
2. Season-stratified records (Pre-Monsoon, Established Monsoon, Post-Monsoon).
3. Annual stability records (2010–2021).
4. Multi-threshold occurrence sensitivity.
5. Volumetric contribution and extreme event attribution.
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

THRESHOLDS = [0.1, 1.0, 2.5, 5.0, 10.0, 15.6, 35.5, 64.5]


def compute_distribution_metrics(sub_df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Compute distribution and occurrence statistics for grouped subsets."""
    rows = []
    
    for keys, group in sub_df.groupby(group_cols, sort=True, observed=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
            
        rain = group["rainfall_mm"].to_numpy(dtype=float)
        # Filter valid finite
        valid_mask = np.isfinite(rain)
        rain_valid = rain[valid_mask]
        
        n_total = len(rain_valid)
        if n_total == 0:
            continue
            
        wet_mask = (rain_valid >= 2.5)
        pos_mask = (rain_valid > 0.0)
        
        mean_all = float(np.mean(rain_valid))
        std_all = float(np.std(rain_valid, ddof=1)) if n_total > 1 else 0.0
        median_all = float(np.median(rain_valid))
        iqr_all = float(np.quantile(rain_valid, 0.75) - np.quantile(rain_valid, 0.25))
        
        q25 = float(np.quantile(rain_valid, 0.25))
        q75 = float(np.quantile(rain_valid, 0.75))
        q90 = float(np.quantile(rain_valid, 0.90))
        q95 = float(np.quantile(rain_valid, 0.95))
        q99 = float(np.quantile(rain_valid, 0.99))
        max_val = float(np.max(rain_valid))
        
        p_dry = float(np.mean(rain_valid == 0.0) * 100.0)
        p_pos = float(np.mean(pos_mask) * 100.0)
        p_wet_25 = float(np.mean(wet_mask) * 100.0)
        
        # Wet-day conditional mean
        mean_wet = float(np.mean(rain_valid[pos_mask])) if pos_mask.sum() > 0 else 0.0
        
        row = dict(zip(group_cols, keys))
        row.update({
            "observations": n_total,
            "mean_rainfall_mm": round(mean_all, 3),
            "std_rainfall_mm": round(std_all, 3),
            "median_rainfall_mm": round(median_all, 3),
            "iqr_rainfall_mm": round(iqr_all, 3),
            "q25_rainfall_mm": round(q25, 3),
            "q75_rainfall_mm": round(q75, 3),
            "q90_rainfall_mm": round(q90, 3),
            "q95_rainfall_mm": round(q95, 3),
            "q99_rainfall_mm": round(q99, 3),
            "max_rainfall_mm": round(max_val, 3),
            "dry_day_pct": round(p_dry, 2),
            "positive_rain_pct": round(p_pos, 2),
            "wet_day_25_pct": round(p_wet_25, 2),
            "wet_day_conditional_mean_mm": round(mean_wet, 3),
            "total_rainfall_volume_mm": round(float(np.sum(rain_valid)), 1),
        })
        rows.append(row)
        
    df_res = pd.DataFrame(rows)
    return df_res


def generate_pooled_summary(df_primary: pd.DataFrame) -> pd.DataFrame:
    """Generate overall pooled regime summary across all seasons."""
    print("--- Generating Pooled Regime Rainfall Summary ---")
    df_dist = compute_distribution_metrics(df_primary, ["dominant_regime"])
    
    total_obs = df_dist["observations"].sum()
    total_vol = df_dist["total_rainfall_volume_mm"].sum()
    
    df_dist["prevalence_pct"] = round(df_dist["observations"] / total_obs * 100.0, 2)
    df_dist["volume_contribution_pct"] = round(df_dist["total_rainfall_volume_mm"] / total_vol * 100.0, 2)
    df_dist["regime_name"] = df_dist["dominant_regime"].map(REGIME_NAMES)
    
    # Reorder columns
    cols = [
        "dominant_regime", "regime_name", "observations", "prevalence_pct",
        "mean_rainfall_mm", "std_rainfall_mm", "median_rainfall_mm", "iqr_rainfall_mm",
        "q25_rainfall_mm", "q75_rainfall_mm", "q90_rainfall_mm", "q95_rainfall_mm", "q99_rainfall_mm",
        "max_rainfall_mm", "dry_day_pct", "positive_rain_pct", "wet_day_25_pct",
        "wet_day_conditional_mean_mm", "volume_contribution_pct"
    ]
    df_out = df_dist[cols].sort_values("dominant_regime").reset_index(drop=True)
    out_file = TABLES_DIR / "m26_regime_rainfall_pooled_summary.csv"
    df_out.to_csv(out_file, index=False)
    print(f"Saved pooled summary to: {out_file}")
    return df_out


def generate_season_summary(df_primary: pd.DataFrame) -> pd.DataFrame:
    """Generate season-stratified regime statistics."""
    print("--- Generating Season-Stratified Regime Rainfall Summary ---")
    df_dist = compute_distribution_metrics(df_primary, ["season_name", "dominant_regime"])
    
    # Compute season-specific prevalence and volume share
    season_totals = df_dist.groupby("season_name")[["observations", "total_rainfall_volume_mm"]].transform("sum")
    df_dist["prevalence_pct"] = round(df_dist["observations"] / season_totals["observations"] * 100.0, 2)
    df_dist["volume_contribution_pct"] = round(df_dist["total_rainfall_volume_mm"] / season_totals["total_rainfall_volume_mm"] * 100.0, 2)
    df_dist["regime_name"] = df_dist["dominant_regime"].map(REGIME_NAMES)
    
    cols = [
        "season_name", "dominant_regime", "regime_name", "observations", "prevalence_pct",
        "mean_rainfall_mm", "std_rainfall_mm", "median_rainfall_mm", "iqr_rainfall_mm",
        "q25_rainfall_mm", "q75_rainfall_mm", "q90_rainfall_mm", "q95_rainfall_mm", "q99_rainfall_mm",
        "max_rainfall_mm", "dry_day_pct", "positive_rain_pct", "wet_day_25_pct",
        "wet_day_conditional_mean_mm", "volume_contribution_pct"
    ]
    df_out = df_dist[cols].sort_values(["season_name", "dominant_regime"]).reset_index(drop=True)
    out_file = TABLES_DIR / "m26_regime_rainfall_by_season.csv"
    df_out.to_csv(out_file, index=False)
    print(f"Saved season summary to: {out_file}")
    return df_out


def generate_annual_summary(df_primary: pd.DataFrame) -> pd.DataFrame:
    """Generate annual stability summary (2010–2021)."""
    print("--- Generating Annual Stability Regime Rainfall Summary ---")
    df_dist = compute_distribution_metrics(df_primary, ["year", "season_name", "dominant_regime"])
    df_dist["regime_name"] = df_dist["dominant_regime"].map(REGIME_NAMES)
    out_file = TABLES_DIR / "m26_regime_rainfall_by_year.csv"
    df_dist.to_csv(out_file, index=False)
    print(f"Saved annual summary to: {out_file}")
    return df_dist


def generate_threshold_sensitivity(df_primary: pd.DataFrame) -> pd.DataFrame:
    """Evaluate occurrence probabilities across multiple rainfall depth thresholds."""
    print("--- Evaluating Multi-Threshold Exceedance Probabilities ---")
    rows = []
    
    for s_name in ["all_seasons", "pre_monsoon", "established_monsoon", "post_monsoon"]:
        sub = df_primary if s_name == "all_seasons" else df_primary[df_primary["season_name"] == s_name]
        
        for k in range(4):
            regime_sub = sub[sub["dominant_regime"] == k]
            rain = regime_sub["rainfall_mm"].to_numpy(dtype=float)
            rain_valid = rain[np.isfinite(rain)]
            n_obs = len(rain_valid)
            
            row = {
                "season": s_name,
                "regime_id": k,
                "regime_name": REGIME_NAMES[k],
                "observations": n_obs,
                "p_rain_gt_0": round(float(np.mean(rain_valid > 0.0) * 100.0), 2),
            }
            for th in THRESHOLDS:
                col_name = f"p_exceed_{str(th).replace('.', '_')}_mm"
                row[col_name] = round(float(np.mean(rain_valid >= th) * 100.0), 2)
                
            rows.append(row)
            
    df_th = pd.DataFrame(rows)
    out_file = TABLES_DIR / "m26_rainfall_threshold_sensitivity.csv"
    df_th.to_csv(out_file, index=False)
    print(f"Saved threshold sensitivity to: {out_file}")
    return df_th


def generate_extreme_attribution(df_primary: pd.DataFrame) -> pd.DataFrame:
    """Evaluate attribution of upper-tail extreme rainfall events (Q90, Q95, Q99)."""
    print("--- Evaluating Extreme Rainfall Event Attribution ---")
    rows = []
    
    for s_name in ["all_seasons", "pre_monsoon", "established_monsoon", "post_monsoon"]:
        sub = df_primary if s_name == "all_seasons" else df_primary[df_primary["season_name"] == s_name]
        rain = sub["rainfall_mm"].to_numpy(dtype=float)
        valid_rain = rain[np.isfinite(rain)]
        
        # Domain quantiles
        q90_th = float(np.quantile(valid_rain, 0.90))
        q95_th = float(np.quantile(valid_rain, 0.95))
        q99_th = float(np.quantile(valid_rain, 0.99))
        
        # Subsets of extreme events
        ext90 = sub[sub["rainfall_mm"] >= q90_th]
        ext95 = sub[sub["rainfall_mm"] >= q95_th]
        ext99 = sub[sub["rainfall_mm"] >= q99_th]
        
        total_ext90 = len(ext90)
        total_ext95 = len(ext95)
        total_ext99 = len(ext99)
        
        for k in range(4):
            reg_n = len(sub[sub["dominant_regime"] == k])
            reg_prev = reg_n / len(sub) * 100.0
            
            c90 = len(ext90[ext90["dominant_regime"] == k])
            c95 = len(ext95[ext95["dominant_regime"] == k])
            c99 = len(ext99[ext99["dominant_regime"] == k])
            
            share90 = (c90 / total_ext90 * 100.0) if total_ext90 > 0 else 0.0
            share95 = (c95 / total_ext95 * 100.0) if total_ext95 > 0 else 0.0
            share99 = (c99 / total_ext99 * 100.0) if total_ext99 > 0 else 0.0
            
            # Relative Risk of extreme event: (share / prevalence)
            rr95 = (share95 / reg_prev) if reg_prev > 0 else 0.0
            
            rows.append({
                "season": s_name,
                "regime_id": k,
                "regime_name": REGIME_NAMES[k],
                "regime_prevalence_pct": round(reg_prev, 2),
                "threshold_q90_mm": round(q90_th, 2),
                "threshold_q95_mm": round(q95_th, 2),
                "threshold_q99_mm": round(q99_th, 2),
                "q90_event_share_pct": round(share90, 2),
                "q95_event_share_pct": round(share95, 2),
                "q99_event_share_pct": round(share99, 2),
                "q95_relative_risk": round(rr95, 2),
            })
            
    df_ext = pd.DataFrame(rows)
    out_file = TABLES_DIR / "m26_extreme_event_attribution.csv"
    df_ext.to_csv(out_file, index=False)
    print(f"Saved extreme attribution to: {out_file}")
    return df_ext


def run_regime_statistics() -> None:
    """Execute all statistical routines on primary matched dataset."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    p_path = DATA_DIR / "m26_cloud_rainfall_matched_primary.parquet"
    if not p_path.exists():
        raise FileNotFoundError(f"Primary matched dataset not found: {p_path}")
        
    df_primary = pd.read_parquet(p_path)
    generate_pooled_summary(df_primary)
    generate_season_summary(df_primary)
    generate_annual_summary(df_primary)
    generate_threshold_sensitivity(df_primary)
    generate_extreme_attribution(df_primary)


if __name__ == "__main__":
    run_regime_statistics()
