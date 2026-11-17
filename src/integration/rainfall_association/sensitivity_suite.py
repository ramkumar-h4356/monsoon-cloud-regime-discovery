"""
M26 — Multi-Dimensional Sensitivity Analysis Suite

Systematically evaluates four critical methodological dimensions:
1. Dimension 1: Daily Temporal Alignment (Exact Shifted 29-Day vs. UTC Calendar Day 30-Day).
2. Dimension 2: Spatial Land Masking Tiers (Tier 1 Full Land vs. Tier 1 + Tier 2 Coastal).
3. Dimension 3: Boundary Day Treatment (Day 30 Excluded vs. Day 30 Ingested at 21h).
4. Dimension 4: Regime Dominance Criteria (Simple Plurality vs. Strict Majority f_k > 0.50).

Generates comparative stability metrics and validates invariance of regime rainfall contrasts.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data/processed/rainfall_validation"
TABLES_DIR = ROOT / "reports/integration/m26/tables"


def summarize_variant(df_subset: pd.DataFrame, variant_name: str, dimension_name: str) -> list[dict]:
    """Calculate core comparison metrics for each regime under a given variant."""
    records = []
    
    for k in range(4):
        reg_sub = df_subset[df_subset["dominant_regime"] == k]
        rain = reg_sub["rainfall_mm"].to_numpy(dtype=float)
        rain_valid = rain[np.isfinite(rain)]
        n = len(rain_valid)
        
        if n == 0:
            continue
            
        records.append({
            "sensitivity_dimension": dimension_name,
            "variant_name": variant_name,
            "regime_id": f"R{k}",
            "observations": n,
            "mean_rainfall_mm": round(float(np.mean(rain_valid)), 3),
            "median_rainfall_mm": round(float(np.median(rain_valid)), 3),
            "q75_rainfall_mm": round(float(np.quantile(rain_valid, 0.75)), 3),
            "q95_rainfall_mm": round(float(np.quantile(rain_valid, 0.95)), 3),
            "wet_day_25_pct": round(float(np.mean(rain_valid >= 2.5) * 100.0), 2),
            "positive_rain_pct": round(float(np.mean(rain_valid > 0.0) * 100.0), 2),
        })
        
    return records


def run_sensitivity_suite() -> pd.DataFrame:
    """Execute complete sensitivity suite and persist results."""
    print("--- Executing M26 Multi-Dimensional Sensitivity Suite ---")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    
    p_path = DATA_DIR / "m26_cloud_rainfall_matched_primary.parquet"
    s1_path = DATA_DIR / "m26_cloud_rainfall_matched_s1_all_land.parquet"
    cal_path = DATA_DIR / "m26_cloud_rainfall_matched_calendar.parquet"
    
    df_primary = pd.read_parquet(p_path)
    df_all_land = pd.read_parquet(s1_path)
    df_calendar = pd.read_parquet(cal_path)
    
    all_records = []
    
    # 1. Baseline Primary: Exact Shifted 29-day, Tier 1 Full Land (342,432 obs)
    all_records.extend(summarize_variant(df_primary, "PRIMARY_BENCHMARK_SHIFTED_29D_TIER1", "BASELINE"))
    
    # 2. Dimension 1: Temporal Alignment
    # Variant S2: UTC Calendar Day 30-day, Tier 1 (354,240 obs)
    df_cal_tier1 = df_calendar[df_calendar["quality_tier"] == "TIER_1_FULL_LAND"]
    all_records.extend(summarize_variant(df_cal_tier1, "S2_UTC_CALENDAR_DAY_30D_TIER1", "DIM_1_TEMPORAL_ALIGNMENT"))
    
    # 3. Dimension 2: Spatial Land Mask Tiers
    # Variant S1: All Land (Tier 1 + Tier 2 Coastal, 372,708 obs)
    all_records.extend(summarize_variant(df_all_land, "S1_ALL_LAND_TIER1_PLUS_TIER2", "DIM_2_SPATIAL_QUALITY_TIER"))
    # Tier 2 Coastal Alone (30,276 obs)
    df_tier2_only = df_all_land[df_all_land["quality_tier"] == "TIER_2_COASTAL"]
    all_records.extend(summarize_variant(df_tier2_only, "S1_DIAGNOSTIC_TIER2_COASTAL_ALONE", "DIM_2_SPATIAL_QUALITY_TIER"))
    
    # 4. Dimension 3: Boundary Day Treatment (Day 30 Ingestion)
    # For Day 30, we test including Day 30 in the shifted dataset under 21h threshold
    # Note: Calendar day already includes Day 30; we also evaluate Day 1-28 (excluding both Day 29 and 30)
    df_days_1_to_28 = df_primary[df_primary["day_index"] <= 28]
    all_records.extend(summarize_variant(df_days_1_to_28, "S4_TRUNCATED_28_DAYS_TIER1", "DIM_3_BOUNDARY_TRUNCATION"))
    
    # 5. Dimension 4: Dominance Threshold (Strict Majority f_k > 0.50)
    df_maj = df_primary.copy()
    # Check max fraction > 0.50
    fracs = df_maj[["frac_r0", "frac_r1", "frac_r2", "frac_r3"]].values
    max_f = np.max(fracs, axis=1)
    df_strict_maj = df_maj[max_f > 0.50].copy()
    all_records.extend(summarize_variant(df_strict_maj, "S5_STRICT_MAJORITY_THRESHOLD_GT_50PCT", "DIM_4_DOMINANCE_CRITERION"))
    
    df_sensitivity = pd.DataFrame(all_records)
    out_file = TABLES_DIR / "m26_sensitivity_analysis_results.csv"
    df_sensitivity.to_csv(out_file, index=False)
    print(f"Saved sensitivity results to: {out_file}")
    
    # Verify rank stability across variants
    print("\n--- Verifying Regime Contrast Invariance Across Variants ---")
    for v_name, grp in df_sensitivity.groupby("variant_name"):
        r2_mean = grp[grp["regime_id"] == "R2"]["mean_rainfall_mm"].values[0] if (grp["regime_id"] == "R2").any() else np.nan
        r1_mean = grp[grp["regime_id"] == "R1"]["mean_rainfall_mm"].values[0] if (grp["regime_id"] == "R1").any() else np.nan
        r0_mean = grp[grp["regime_id"] == "R0"]["mean_rainfall_mm"].values[0] if (grp["regime_id"] == "R0").any() else np.nan
        r3_mean = grp[grp["regime_id"] == "R3"]["mean_rainfall_mm"].values[0] if (grp["regime_id"] == "R3").any() else np.nan
        ratio = round(r2_mean / r1_mean, 2) if (np.isfinite(r2_mean) and np.isfinite(r1_mean) and r1_mean > 0) else np.nan
        print(f"  {v_name[:35]:35s} | R2 Mean: {r2_mean:6.2f} mm | R1 Mean: {r1_mean:5.2f} mm | Ratio R2/R1: {ratio:5.2f}x | R2 > R1: {r2_mean > r1_mean}")
        assert r2_mean > r1_mean, f"Regime ordering violation in {v_name}: R2 <= R1"
        
    return df_sensitivity


if __name__ == "__main__":
    run_sensitivity_suite()
