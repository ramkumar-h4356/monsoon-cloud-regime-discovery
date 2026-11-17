"""
M26 — IMD Daily Gridded Rainfall Loader and QC Masking Module

Ingests the 12 annual IMD 1.0° NetCDF files (2010–2021) from `raw_data/IMD_Rainfall/`,
slices the exact approved seasonal windows (Pre-Monsoon, Established Monsoon, Post-Monsoon),
extracts the canonical 32x30 M25 analysis grid via native coordinate sub-indexing,
and applies the audited M25.4 Data Quality Policy:
- Preserves genuine zero rainfall (0.0 mm).
- Masks missing sentinels (-999.0 -> NaN).
- Categorizes each cell into Quality Tiers:
  - Tier 1: Full Land (328 cells, primary analysis)
  - Tier 2: Partial Coastal (29 cells, sensitivity analysis)
  - Tier 4: Ocean structural absence (603 cells, preserved as NaN; never zero-filled).
"""

from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[3]
IMD_DIR = ROOT / "raw_data/IMD_Rainfall"
OUTPUT_DIR = ROOT / "data/processed/rainfall_validation"

YEARS = list(range(2010, 2022))

SEASON_DEFINITIONS = [
    (0, "pre_monsoon", "04-15", "05-14", 30),
    (1, "established_monsoon", "07-15", "08-13", 30),
    (2, "post_monsoon", "10-15", "11-13", 30),
]


def build_quality_tier_mask(land_mask_2d: np.ndarray) -> np.ndarray:
    """
    Construct the M25.4 quality tier grid (shape: 32, 30) for the 960 canonical cells:
    - Tier 1: 328 full land cells (interior)
    - Tier 2: 29 coastal boundary cells (peninsular marine border south of 22N)
    - Tier 4: 603 ocean / foreign absence cells
    """
    tier_grid = np.full(land_mask_2d.shape, "TIER_4_OCEAN", dtype=object)
    
    # Identify coastal perimeter cells:
    # Lats 8.5N to 21.5N (indices 2 to 15 in the 32-point grid: lats 6.5, 7.5, 8.5 ... 21.5)
    coastal_mask = np.zeros_like(land_mask_2d, dtype=bool)
    for i in range(2, 16):
        row = np.where(land_mask_2d[i])[0]
        if len(row) > 0:
            coastal_mask[i, row[0]] = True   # West coastal edge
            coastal_mask[i, row[-1]] = True  # East coastal edge
            
    # Southernmost cape cell at 8.5N, 77.5E (middle of the 3 southern cells: 76.5, 77.5, 78.5)
    row_8_5 = np.where(land_mask_2d[2])[0]
    if len(row_8_5) >= 2:
        coastal_mask[2, row_8_5[1]] = True  # Kanyakumari apex
        
    for i in range(32):
        for j in range(30):
            if land_mask_2d[i, j]:
                if coastal_mask[i, j]:
                    tier_grid[i, j] = "TIER_2_COASTAL"
                else:
                    tier_grid[i, j] = "TIER_1_FULL_LAND"
                    
    assert (tier_grid == "TIER_1_FULL_LAND").sum() == 328, f"Expected 328 Tier 1 cells, got {(tier_grid == 'TIER_1_FULL_LAND').sum()}"
    assert (tier_grid == "TIER_2_COASTAL").sum() == 29, f"Expected 29 Tier 2 cells, got {(tier_grid == 'TIER_2_COASTAL').sum()}"
    assert (tier_grid == "TIER_4_OCEAN").sum() == 603, f"Expected 603 Tier 4 cells, got {(tier_grid == 'TIER_4_OCEAN').sum()}"
    return tier_grid


def load_all_seasonal_rainfall() -> pd.DataFrame:
    """
    Extract and process IMD rainfall across all 12 years and 3 seasons.
    Returns DataFrame containing all 30 seasonal days (1,036,800 rows).
    """
    print("--- Ingesting IMD 1.0° Gridded Rainfall Archives (2010–2021) ---")
    
    # Establish canonical grid
    sample_file = IMD_DIR / "RFone_imd_rf_1x1_2010.nc"
    with xr.open_dataset(sample_file) as ds:
        lats_raw = ds["LATITUDE"].values[0:32].astype(np.float64)
        lons_raw = ds["LONGITUDE"].values[2:32].astype(np.float64)
        sample_rain = ds["RAINFALL"].values[0, 0:32, 2:32]
        land_mask_2d = (sample_rain != -999.0) & np.isfinite(sample_rain)
        
    tier_grid_2d = build_quality_tier_mask(land_mask_2d)
    
    # Pre-flatten coordinate and tier arrays
    lat_grid, lon_grid = np.meshgrid(lats_raw, lons_raw, indexing="ij")
    flat_lats = lat_grid.ravel()
    flat_lons = lon_grid.ravel()
    flat_tiers = tier_grid_2d.ravel()
    flat_cell_indices = np.arange(960, dtype=np.int16)
    
    all_records = []
    
    for year in YEARS:
        file_path = IMD_DIR / f"RFone_imd_rf_1x1_{year}.nc"
        if not file_path.exists():
            raise FileNotFoundError(f"Missing IMD rainfall file: {file_path}")
            
        with xr.open_dataset(file_path) as ds:
            times = ds["TIME"].values
            dates_year = pd.to_datetime([
                t.isoformat() if hasattr(t, "isoformat") else str(t) for t in times
            ]).strftime("%Y-%m-%d").values
            
            date_to_idx = {d: i for i, d in enumerate(dates_year)}
            
            # Sub-index M25 domain: lat 0..31, lon 2..31
            rf_cube = ds["RAINFALL"].values[:, 0:32, 2:32]  # shape: (days_in_year, 32, 30)
            
            for s_idx, s_name, start_md, end_md, num_days in SEASON_DEFINITIONS:
                # 30 calendar days
                seasonal_dates = pd.date_range(f"{year}-{start_md}", f"{year}-{end_md}", freq="D").strftime("%Y-%m-%d")
                assert len(seasonal_dates) == num_days, f"Expected {num_days} days, got {len(seasonal_dates)}"
                
                for d_idx, date_str in enumerate(seasonal_dates):
                    day_file_idx = date_to_idx[date_str]
                    day_rain = rf_cube[day_file_idx]  # shape: (32, 30)
                    
                    # Flatten
                    rain_flat = day_rain.ravel().copy()
                    
                    # Quality filtering:
                    # Missing sentinel -999.0 -> NaN
                    is_sentinel = (rain_flat == -999.0) | (~np.isfinite(rain_flat))
                    rain_flat[is_sentinel] = np.nan
                    
                    # Sanity check: valid land values must be >= 0.0
                    valid_vals = rain_flat[~is_sentinel]
                    if (valid_vals < 0.0).any():
                        raise ValueError(f"Unphysical negative rainfall in {year} on {date_str}")
                    if (valid_vals > 1500.0).any():
                        raise ValueError(f"Catastrophic rainfall > 1500 mm in {year} on {date_str}")
                        
                    is_dry_day = np.zeros(960, dtype=bool)
                    is_dry_day[~is_sentinel] = (valid_vals == 0.0)
                    
                    is_wet_day_25 = np.zeros(960, dtype=bool)
                    is_wet_day_25[~is_sentinel] = (valid_vals >= 2.5)
                    
                    df_day = pd.DataFrame({
                        "year": np.full(960, year, dtype=np.int16),
                        "season_id": np.full(960, s_idx, dtype=np.int8),
                        "season_name": np.full(960, s_name, dtype=object),
                        "day_index": np.full(960, d_idx + 1, dtype=np.int8),
                        "date": np.full(960, date_str, dtype=object),
                        "cell_index": flat_cell_indices,
                        "latitude": flat_lats,
                        "longitude": flat_lons,
                        "quality_tier": flat_tiers,
                        "is_valid_land": (flat_tiers != "TIER_4_OCEAN"),
                        "rainfall_mm": rain_flat,
                        "is_dry_day": is_dry_day,
                        "is_wet_day_25": is_wet_day_25,
                    })
                    all_records.append(df_day)
                    
    df_all = pd.concat(all_records, ignore_index=True)
    print(f"IMD rainfall extraction complete: {len(df_all):,} total grid-day observations.")
    return df_all


def run_rainfall_loader() -> pd.DataFrame:
    """Execute IMD rainfall loader and save processed dataset."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df_rainfall = load_all_seasonal_rainfall()
    out_path = OUTPUT_DIR / "m26_imd_rainfall_daily.parquet"
    df_rainfall.to_parquet(out_path, index=False)
    print(f"Saved IMD seasonal rainfall dataset to: {out_path}")
    return df_rainfall


if __name__ == "__main__":
    run_rainfall_loader()
