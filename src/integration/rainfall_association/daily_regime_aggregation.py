"""
M26 — Daily Cloud Regime Aggregation Module

Aggregates frozen hourly M25 cloud regime labels (24,883,200 hourly observations)
into daily grid-cell summaries across all three seasons (Pre-Monsoon, Established Monsoon,
Post-Monsoon) and 12 study years (2010–2021).

Supports:
1. Primary Convention: Exact IMD Shifted 24-Hour Window (03:00 UTC D to 03:00 UTC D+1)
   for Complete Days 1–29 (24/24 valid hours, 100% temporal overlap).
2. Secondary Convention: UTC Calendar Day (00:00 to 24:00 UTC) for Days 1–30 (Sensitivity S2).
3. Incomplete Day 30 Shifted Window (21 valid hours) for Sensitivity S4.
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
M25_DATA_DIR = ROOT / "data/processed/combined_3season"
OUTPUT_DIR = ROOT / "data/processed/rainfall_validation"

YEARS = list(range(2010, 2022))  # 12 years: 2010..2021
SEASON_IDS = [0, 1, 2]  # 0: Pre, 1: Established, 2: Post
SEASON_NAMES = {0: "pre_monsoon", 1: "established_monsoon", 2: "post_monsoon"}

# Exact 30 calendar dates per season
SEASONAL_DATE_OFFSETS = {
    0: pd.date_range("2010-04-15", "2010-05-14", freq="D").strftime("%m-%d").tolist(),
    1: pd.date_range("2010-07-15", "2010-08-13", freq="D").strftime("%m-%d").tolist(),
    2: pd.date_range("2010-10-15", "2010-11-13", freq="D").strftime("%m-%d").tolist(),
}


def load_m25_labels() -> np.ndarray:
    """Load and reshape frozen M25 hourly cluster labels into (12, 3, 720, 960)."""
    label_path = M25_DATA_DIR / "combined_3season_cluster_labels.npy"
    if not label_path.exists():
        raise FileNotFoundError(f"Missing M25 cluster labels: {label_path}")
    
    labels = np.load(label_path, mmap_mode="r")
    if labels.shape != (24883200,):
        raise ValueError(f"Unexpected M25 label shape: {labels.shape}")
    
    # Reshape to (12 years, 3 seasons, 720 hours, 960 grid cells)
    labels_4d = labels.reshape(12, 3, 720, 960)
    return labels_4d


def get_grid_coordinates() -> tuple[np.ndarray, np.ndarray]:
    """Return regular 1.0 degree lat and lon arrays for 960 canonical M25 grid cells."""
    cell_indices = np.arange(960)
    lats = 6.5 + (cell_indices // 30).astype(np.float64)
    lons = 68.5 + (cell_indices % 30).astype(np.float64)
    return lats, lons


def build_primary_shifted_aggregation(labels_4d: np.ndarray) -> pd.DataFrame:
    """
    Aggregate hourly labels into the Primary Exact Shifted 24-hour Window (03:00 to 03:00 UTC).
    Extracts 29 complete days (Days 1–29) per season. Each day has exactly 24 valid hours.
    Total records: 12 years x 3 seasons x 29 days x 960 cells = 1,002,240 rows.
    """
    print("--- Aggregating Primary Exact Shifted Window (Days 1–29, 24 h/day) ---")
    lats_960, lons_960 = get_grid_coordinates()
    
    records = []
    
    for y_idx, year in enumerate(YEARS):
        for s_idx in SEASON_IDS:
            season_name = SEASON_NAMES[s_idx]
            date_strings = [f"{year}-{md}" for md in SEASONAL_DATE_OFFSETS[s_idx]]
            
            # Days 0..28 (29 complete days)
            for d in range(29):
                date_str = date_strings[d]
                h_start = d * 24 + 3
                h_end = (d + 1) * 24 + 3
                
                # Sliced window of shape (24 hours, 960 cells)
                day_slice = labels_4d[y_idx, s_idx, h_start:h_end, :]  # shape: (24, 960)
                
                # Counts per regime k in 0..3: shape (960, 4)
                counts = np.zeros((960, 4), dtype=np.int16)
                for k in range(4):
                    counts[:, k] = np.sum(day_slice == k, axis=0)
                
                fractions = counts / 24.0
                dominant = np.argmax(counts, axis=1)
                
                # Check ties
                sorted_c = np.partition(counts, -2, axis=1)
                ties = (sorted_c[:, -1] == sorted_c[:, -2])
                
                df_day = pd.DataFrame({
                    "year": np.full(960, year, dtype=np.int16),
                    "season_id": np.full(960, s_idx, dtype=np.int8),
                    "season_name": np.full(960, season_name, dtype=object),
                    "day_index": np.full(960, d + 1, dtype=np.int8),
                    "date": np.full(960, date_str, dtype=object),
                    "cell_index": np.arange(960, dtype=np.int16),
                    "latitude": lats_960,
                    "longitude": lons_960,
                    "valid_cloud_hours": np.full(960, 24, dtype=np.int8),
                    "is_complete_24h": np.full(960, True, dtype=bool),
                    "count_r0": counts[:, 0],
                    "count_r1": counts[:, 1],
                    "count_r2": counts[:, 2],
                    "count_r3": counts[:, 3],
                    "frac_r0": fractions[:, 0],
                    "frac_r1": fractions[:, 1],
                    "frac_r2": fractions[:, 2],
                    "frac_r3": fractions[:, 3],
                    "dominant_regime": dominant,
                    "tie_occurred": ties,
                    "alignment_convention": np.full(960, "EXACT_SHIFTED_03TO03_UTC", dtype=object),
                })
                records.append(df_day)
                
    df_primary = pd.concat(records, ignore_index=True)
    print(f"Primary shifted aggregation complete: {len(df_primary):,} daily records.")
    return df_primary


def build_calendar_day_aggregation(labels_4d: np.ndarray) -> pd.DataFrame:
    """
    Aggregate hourly labels into the UTC Calendar Day Window (00:00 to 24:00 UTC) for Sensitivity S2.
    Extracts all 30 days per season. Each day has exactly 24 valid hours.
    Total records: 12 years x 3 seasons x 30 days x 960 cells = 1,036,800 rows.
    """
    print("--- Aggregating Sensitivity UTC Calendar Day Window (Days 1–30, 24 h/day) ---")
    lats_960, lons_960 = get_grid_coordinates()
    
    records = []
    
    for y_idx, year in enumerate(YEARS):
        for s_idx in SEASON_IDS:
            season_name = SEASON_NAMES[s_idx]
            date_strings = [f"{year}-{md}" for md in SEASONAL_DATE_OFFSETS[s_idx]]
            
            # Days 0..29 (30 days)
            for d in range(30):
                date_str = date_strings[d]
                h_start = d * 24
                h_end = (d + 1) * 24
                
                day_slice = labels_4d[y_idx, s_idx, h_start:h_end, :]  # shape: (24, 960)
                
                counts = np.zeros((960, 4), dtype=np.int16)
                for k in range(4):
                    counts[:, k] = np.sum(day_slice == k, axis=0)
                
                fractions = counts / 24.0
                dominant = np.argmax(counts, axis=1)
                sorted_c = np.partition(counts, -2, axis=1)
                ties = (sorted_c[:, -1] == sorted_c[:, -2])
                
                df_day = pd.DataFrame({
                    "year": np.full(960, year, dtype=np.int16),
                    "season_id": np.full(960, s_idx, dtype=np.int8),
                    "season_name": np.full(960, season_name, dtype=object),
                    "day_index": np.full(960, d + 1, dtype=np.int8),
                    "date": np.full(960, date_str, dtype=object),
                    "cell_index": np.arange(960, dtype=np.int16),
                    "latitude": lats_960,
                    "longitude": lons_960,
                    "valid_cloud_hours": np.full(960, 24, dtype=np.int8),
                    "is_complete_24h": np.full(960, True, dtype=bool),
                    "count_r0": counts[:, 0],
                    "count_r1": counts[:, 1],
                    "count_r2": counts[:, 2],
                    "count_r3": counts[:, 3],
                    "frac_r0": fractions[:, 0],
                    "frac_r1": fractions[:, 1],
                    "frac_r2": fractions[:, 2],
                    "frac_r3": fractions[:, 3],
                    "dominant_regime": dominant,
                    "tie_occurred": ties,
                    "alignment_convention": np.full(960, "UTC_CALENDAR_DAY_00TO24", dtype=object),
                })
                records.append(df_day)
                
    df_cal = pd.concat(records, ignore_index=True)
    print(f"Calendar day aggregation complete: {len(df_cal):,} daily records.")
    return df_cal


def run_daily_aggregation() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Execute both primary shifted and secondary calendar day aggregations and save to disk."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    labels_4d = load_m25_labels()
    
    df_primary = build_primary_shifted_aggregation(labels_4d)
    primary_out = OUTPUT_DIR / "m26_daily_regime_aggregation_primary.parquet"
    df_primary.to_parquet(primary_out, index=False)
    print(f"Saved primary daily aggregation to: {primary_out}")
    
    df_calendar = build_calendar_day_aggregation(labels_4d)
    calendar_out = OUTPUT_DIR / "m26_daily_regime_aggregation_calendar.parquet"
    df_calendar.to_parquet(calendar_out, index=False)
    print(f"Saved calendar daily aggregation to: {calendar_out}")
    
    return df_primary, df_calendar


if __name__ == "__main__":
    run_daily_aggregation()
