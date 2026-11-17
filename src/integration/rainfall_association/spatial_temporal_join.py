"""
M26 — Spatial-Temporal Join and Integration Verification Module

Executes the formal space-time join between M25 daily cloud summaries and IMD daily rainfall
on the exact 4-tuple key: `(year, date, latitude, longitude)`.

Verifies:
1. Coordinate equality (Delta = 0.000 deg).
2. Zero duplicate keys.
3. Exact row counts:
   - Primary Analysis (Tier 1 Full Land, 29 Complete Days): Exactly 342,432 observations.
   - Sensitivity S1 (Tier 1 + Tier 2 Coastal, 29 Complete Days): Exactly 372,708 observations.
   - Sensitivity S2/S3 (UTC Calendar Day, 30 Days): Exactly 354,240 Tier 1; 385,560 all-land observations.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data/processed/rainfall_validation"

KEYS = ["year", "date", "latitude", "longitude"]


def execute_primary_join(df_cloud_primary: pd.DataFrame, df_rainfall: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Join Primary Shifted 29-day cloud summaries with IMD rainfall.
    Outputs:
    1. df_primary: Tier 1 Full Land (342,432 rows)
    2. df_all_land: Tier 1 + Tier 2 (372,708 rows)
    """
    print("--- Executing Primary Space-Time Join (Exact Shifted Window, Days 1–29) ---")
    
    # Filter rainfall to Days 1–29
    df_rf_29d = df_rainfall[df_rainfall["day_index"] <= 29].copy()
    
    assert len(df_cloud_primary) == 1002240, f"Expected 1,002,240 primary cloud rows, got {len(df_cloud_primary)}"
    assert len(df_rf_29d) == 1002240, f"Expected 1,002,240 rainfall rows, got {len(df_rf_29d)}"
    
    # Assert zero duplicates on keys
    assert not df_cloud_primary.duplicated(KEYS).any(), "Duplicate keys in primary cloud summaries!"
    assert not df_rf_29d.duplicated(KEYS).any(), "Duplicate keys in IMD rainfall dataset!"
    
    # Select columns to merge
    rf_cols_to_merge = KEYS + [
        "quality_tier", "is_valid_land", "rainfall_mm", "is_dry_day", "is_wet_day_25"
    ]
    
    matched = df_cloud_primary.merge(
        df_rf_29d[rf_cols_to_merge],
        on=KEYS,
        how="inner",
        validate="one_to_one"
    )
    
    assert len(matched) == 1002240, f"Expected 1,002,240 matched rows, got {len(matched)}"
    
    # Extract subsets
    df_primary_tier1 = matched[matched["quality_tier"] == "TIER_1_FULL_LAND"].copy().reset_index(drop=True)
    df_all_land = matched[matched["is_valid_land"]].copy().reset_index(drop=True)
    
    # Verify exact counts
    expected_primary = 342432  # 12 * 3 * 29 * 328
    expected_all_land = 372708 # 12 * 3 * 29 * 357
    expected_tier2 = 30276     # 12 * 3 * 29 * 29
    
    assert len(df_primary_tier1) == expected_primary, f"Expected {expected_primary} Tier 1 rows, got {len(df_primary_tier1)}"
    assert len(df_all_land) == expected_all_land, f"Expected {expected_all_land} all-land rows, got {len(df_all_land)}"
    tier2_count = (df_all_land["quality_tier"] == "TIER_2_COASTAL").sum()
    assert tier2_count == expected_tier2, f"Expected {expected_tier2} Tier 2 rows, got {tier2_count}"
    
    print(f"Primary Join Verified: {len(df_primary_tier1):,} Tier 1 observations.")
    print(f"Sensitivity S1 Join Verified: {len(df_all_land):,} Total Terrestrial observations (Tier 1 + Tier 2).")
    
    return df_primary_tier1, df_all_land


def execute_calendar_join(df_cloud_cal: pd.DataFrame, df_rainfall: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Join Sensitivity Calendar Day 30-day cloud summaries with IMD rainfall.
    Outputs:
    1. df_cal_tier1: Tier 1 Full Land (354,240 rows)
    2. df_cal_all_land: Tier 1 + Tier 2 (385,560 rows)
    """
    print("--- Executing Sensitivity Space-Time Join (UTC Calendar Day, Days 1–30) ---")
    
    rf_cols_to_merge = KEYS + [
        "quality_tier", "is_valid_land", "rainfall_mm", "is_dry_day", "is_wet_day_25"
    ]
    
    matched = df_cloud_cal.merge(
        df_rainfall[rf_cols_to_merge],
        on=KEYS,
        how="inner",
        validate="one_to_one"
    )
    
    assert len(matched) == 1036800, f"Expected 1,036,800 matched rows, got {len(matched)}"
    
    df_cal_tier1 = matched[matched["quality_tier"] == "TIER_1_FULL_LAND"].copy().reset_index(drop=True)
    df_cal_all_land = matched[matched["is_valid_land"]].copy().reset_index(drop=True)
    
    expected_cal_tier1 = 354240  # 12 * 3 * 30 * 328
    expected_cal_all = 385560    # 12 * 3 * 30 * 357
    
    assert len(df_cal_tier1) == expected_cal_tier1, f"Expected {expected_cal_tier1} rows, got {len(df_cal_tier1)}"
    assert len(df_cal_all_land) == expected_cal_all, f"Expected {expected_cal_all} rows, got {len(df_cal_all_land)}"
    
    print(f"Calendar Day Join Verified: {len(df_cal_tier1):,} Tier 1 observations; {len(df_cal_all_land):,} Total Land observations.")
    return df_cal_tier1, df_cal_all_land


def run_spatial_temporal_join() -> None:
    """Execute complete join pipeline and persist datasets."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    primary_cloud_path = DATA_DIR / "m26_daily_regime_aggregation_primary.parquet"
    cal_cloud_path = DATA_DIR / "m26_daily_regime_aggregation_calendar.parquet"
    rf_path = DATA_DIR / "m26_imd_rainfall_daily.parquet"
    
    if not (primary_cloud_path.exists() and cal_cloud_path.exists() and rf_path.exists()):
        raise FileNotFoundError("Prerequisite aggregated files missing in data/processed/rainfall_validation")
        
    df_cloud_primary = pd.read_parquet(primary_cloud_path)
    df_cloud_cal = pd.read_parquet(cal_cloud_path)
    df_rainfall = pd.read_parquet(rf_path)
    
    df_primary_tier1, df_all_land_29d = execute_primary_join(df_cloud_primary, df_rainfall)
    df_cal_tier1, df_cal_all_land = execute_calendar_join(df_cloud_cal, df_rainfall)
    
    # Save datasets
    p_out = DATA_DIR / "m26_cloud_rainfall_matched_primary.parquet"
    df_primary_tier1.to_parquet(p_out, index=False)
    print(f"Saved primary matched dataset (Tier 1, 342,432 obs) to: {p_out}")
    
    s1_out = DATA_DIR / "m26_cloud_rainfall_matched_s1_all_land.parquet"
    df_all_land_29d.to_parquet(s1_out, index=False)
    print(f"Saved Sensitivity S1 dataset (All Land, 372,708 obs) to: {s1_out}")
    
    cal_out = DATA_DIR / "m26_cloud_rainfall_matched_calendar.parquet"
    df_cal_all_land.to_parquet(cal_out, index=False)
    print(f"Saved Calendar Day dataset (385,560 obs) to: {cal_out}")


if __name__ == "__main__":
    run_spatial_temporal_join()
