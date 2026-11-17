"""
M26 — Spatial and Temporal Dynamics Analysis Module

Executes:
1. Spatial Analysis: Evaluates geographic variations in regime prevalence, rainfall depth,
   and wet-day probability across the 328 Tier 1 grid cells (and 29 Tier 2 coastal cells).
2. Temporal Analysis: Evaluates daily regime persistence, day-to-day transition probabilities
   (d -> d+1) within each 29-day seasonal window, and rainfall differences associated with transitions.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data/processed/rainfall_validation"
TABLES_DIR = ROOT / "reports/integration/m26/tables"


def compute_spatial_cell_summaries(df_all_land: pd.DataFrame) -> pd.DataFrame:
    """Compute per-grid-cell regime prevalence and conditional rainfall metrics."""
    print("--- Computing Cell-Wise Spatial Rainfall and Prevalence Summaries ---")
    rows = []
    
    # Group by cell_index, latitude, longitude, quality_tier, season_name
    for (c_idx, lat, lon, tier, s_name), group in df_all_land.groupby(
        ["cell_index", "latitude", "longitude", "quality_tier", "season_name"], observed=True
    ):
        n_days = len(group)
        rain = group["rainfall_mm"].to_numpy(dtype=float)
        rain_valid = rain[np.isfinite(rain)]
        
        row = {
            "cell_index": c_idx,
            "latitude": lat,
            "longitude": lon,
            "quality_tier": tier,
            "season_name": s_name,
            "total_days": n_days,
            "overall_mean_rainfall_mm": round(float(np.mean(rain_valid)), 2),
            "overall_wet_day_25_pct": round(float(np.mean(rain_valid >= 2.5) * 100.0), 2),
        }
        
        for k in range(4):
            k_mask = (group["dominant_regime"] == k)
            k_count = k_mask.sum()
            k_prev = (k_count / n_days * 100.0) if n_days > 0 else 0.0
            
            k_rain = rain[k_mask]
            k_mean = float(np.mean(k_rain)) if len(k_rain) > 0 else np.nan
            k_wet = float(np.mean(k_rain >= 2.5) * 100.0) if len(k_rain) > 0 else np.nan
            
            row[f"r{k}_prevalence_pct"] = round(k_prev, 2)
            row[f"r{k}_mean_rainfall_mm"] = round(k_mean, 2) if np.isfinite(k_mean) else np.nan
            row[f"r{k}_wet_day_25_pct"] = round(k_wet, 2) if np.isfinite(k_wet) else np.nan
            
        rows.append(row)
        
    df_spatial = pd.DataFrame(rows)
    out_file = TABLES_DIR / "m26_spatial_regime_rainfall_by_cell.csv"
    df_spatial.to_csv(out_file, index=False)
    print(f"Saved cell-wise spatial summary to: {out_file}")
    return df_spatial


def compute_daily_regime_transitions(df_primary: pd.DataFrame) -> pd.DataFrame:
    """
    Compute daily regime transition matrix (d -> d+1) and associated rainfall differences
    within the 29-day seasonal windows.
    """
    print("--- Computing Daily Regime Persistence and Transition Dynamics ---")
    
    # Sort strictly by year, season_id, cell_index, day_index
    df_sorted = df_primary.sort_values(["year", "season_id", "cell_index", "day_index"]).copy()
    
    # Shift within same year, season, and cell
    df_sorted["next_dominant_regime"] = df_sorted.groupby(["year", "season_id", "cell_index"])["dominant_regime"].shift(-1)
    df_sorted["next_rainfall_mm"] = df_sorted.groupby(["year", "season_id", "cell_index"])["rainfall_mm"].shift(-1)
    df_sorted["next_day_index"] = df_sorted.groupby(["year", "season_id", "cell_index"])["day_index"].shift(-1)
    
    # Keep valid consecutive pairs (day d and day d+1)
    valid_pairs = df_sorted[df_sorted["next_dominant_regime"].notna() & (df_sorted["next_day_index"] == df_sorted["day_index"] + 1)].copy()
    valid_pairs["next_dominant_regime"] = valid_pairs["next_dominant_regime"].astype(int)
    
    rows = []
    
    for s_name in ["all_seasons", "pre_monsoon", "established_monsoon", "post_monsoon"]:
        sub = valid_pairs if s_name == "all_seasons" else valid_pairs[valid_pairs["season_name"] == s_name]
        
        # 4x4 Transition Matrix
        for from_k in range(4):
            from_sub = sub[sub["dominant_regime"] == from_k]
            n_from = len(from_sub)
            
            for to_k in range(4):
                to_sub = from_sub[from_sub["next_dominant_regime"] == to_k]
                n_trans = len(to_sub)
                trans_prob = (n_trans / n_from * 100.0) if n_from > 0 else 0.0
                
                # Rainfall characteristics during transition
                rain_from = from_sub["rainfall_mm"].to_numpy(dtype=float)
                rain_to = to_sub["next_rainfall_mm"].to_numpy(dtype=float)
                
                mean_rain_from = float(np.mean(rain_from)) if len(rain_from) > 0 else np.nan
                mean_rain_to = float(np.mean(rain_to)) if len(rain_to) > 0 else np.nan
                rain_delta = mean_rain_to - mean_rain_from if (np.isfinite(mean_rain_to) and np.isfinite(mean_rain_from)) else np.nan
                
                wet_pct_to = float(np.mean(rain_to >= 2.5) * 100.0) if len(rain_to) > 0 else np.nan
                
                rows.append({
                    "season": s_name,
                    "from_regime": f"R{from_k}",
                    "to_regime": f"R{to_k}",
                    "transition_type": "PERSISTENCE" if from_k == to_k else "TRANSITION",
                    "transition_count": n_trans,
                    "total_from_count": n_from,
                    "transition_probability_pct": round(trans_prob, 2),
                    "mean_rainfall_day_d_mm": round(mean_rain_from, 2),
                    "mean_rainfall_day_d1_mm": round(mean_rain_to, 2),
                    "rainfall_change_delta_mm": round(rain_delta, 2),
                    "wet_day_pct_day_d1": round(wet_pct_to, 2),
                })
                
    df_trans = pd.DataFrame(rows)
    out_file = TABLES_DIR / "m26_temporal_regime_transitions.csv"
    df_trans.to_csv(out_file, index=False)
    print(f"Saved temporal transition summary to: {out_file}")
    return df_trans


def run_spatial_temporal_analysis() -> None:
    """Execute spatial and temporal dynamics pipeline."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    
    p_path = DATA_DIR / "m26_cloud_rainfall_matched_primary.parquet"
    s1_path = DATA_DIR / "m26_cloud_rainfall_matched_s1_all_land.parquet"
    
    if not (p_path.exists() and s1_path.exists()):
        raise FileNotFoundError("Matched analysis datasets missing in data/processed/rainfall_validation")
        
    df_primary = pd.read_parquet(p_path)
    df_all_land = pd.read_parquet(s1_path)
    
    compute_spatial_cell_summaries(df_all_land)
    compute_daily_regime_transitions(df_primary)


if __name__ == "__main__":
    run_spatial_temporal_analysis()
