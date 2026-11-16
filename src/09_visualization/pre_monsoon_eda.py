
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns

# ==================================================
# 1. PROJECT DIRECTORIES
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data" / "interim" / "ceres_seasonal" / "pre_monsoon"

QUALITY_CSV = (
    ROOT / "reports" / "data_quality"
    / "pre_monsoon_quality.csv"
)

FIGURE_DIR = ROOT / "results" / "figures" / "pre_monsoon"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

FILES = sorted(DATA_DIR.glob("*.nc"))

if len(FILES) != 12:
    raise ValueError(f"Expected 12 NetCDF files, found {len(FILES)}")

if not QUALITY_CSV.exists():
    raise FileNotFoundError(QUALITY_CSV)

sns.set_theme(style="whitegrid")

print("=== PRE-MONSOON EXPLORATORY DATA ANALYSIS ===")
print("NetCDF files:", len(FILES))

# ==================================================
# 2. MISSING-VALUE HEATMAP
# ==================================================

quality = pd.read_csv(QUALITY_CSV)

heatmap_data = quality.pivot(
    index="variable",
    columns="year",
    values="missing_percent"
)

plt.figure(figsize=(14, 15))

sns.heatmap(
    heatmap_data,
    cmap="YlOrRd",
    vmin=0,
    vmax=100,
    cbar_kws={"label": "Missing values (%)"}
)

plt.title("CERES Pre-Monsoon Missing Data (2010–2021)")
plt.xlabel("Year")
plt.ylabel("Cloud Variable")
plt.tight_layout()

plt.savefig(
    FIGURE_DIR / "01_missing_data_heatmap.png",
    dpi=300
)
plt.close()

print("Saved: Missing-data heatmap")

# ==================================================
# 3. SELECT CLOUD-COVER VARIABLE
# ==================================================

# Total cloud area fraction, hourly
VARIABLE = "cldarea_total_1h"

with xr.open_dataset(FILES[0]) as ds:
    if VARIABLE not in ds.data_vars:
        raise KeyError(
            f"{VARIABLE} not found in dataset"
        )

# ==================================================
# 4. CLOUD-COVER DISTRIBUTION
# ==================================================

samples = []

for file in FILES:
    with xr.open_dataset(file) as ds:
        values = ds[VARIABLE].values.ravel()
        valid = values[np.isfinite(values)]

        # Use deterministic subsampling for plotting
        if valid.size > 100000:
            indices = np.linspace(
                0, valid.size - 1, 100000,
                dtype=int
            )
            valid = valid[indices]

        samples.append(valid)

all_values = np.concatenate(samples)

plt.figure(figsize=(10, 6))
plt.hist(all_values, bins=50, edgecolor="black")

plt.title("Pre-Monsoon Total Cloud Area Distribution")
plt.xlabel("Total Cloud Area (dataset units)")
plt.ylabel("Frequency")
plt.tight_layout()

plt.savefig(
    FIGURE_DIR / "02_cloud_cover_distribution.png",
    dpi=300
)
plt.close()

print("Saved: Cloud-cover distribution")

# ==================================================
# 5. SPATIAL CLOUD-COVER MAP
# ==================================================

spatial_sum = None
spatial_count = None

for file in FILES:
    with xr.open_dataset(file) as ds:
        cloud = ds[VARIABLE]

        yearly_sum = cloud.fillna(0).sum(
            dim="time"
        ).values

        yearly_count = cloud.count(
            dim="time"
        ).values

        if spatial_sum is None:
            spatial_sum = np.zeros_like(
                yearly_sum, dtype=float
            )
            spatial_count = np.zeros_like(
                yearly_count, dtype=float
            )

        spatial_sum += yearly_sum
        spatial_count += yearly_count

        lat = ds["lat"].values.copy()
        lon = ds["lon"].values.copy()

spatial_mean = np.divide(
    spatial_sum,
    spatial_count,
    out=np.full_like(spatial_sum, np.nan),
    where=spatial_count > 0
)

plt.figure(figsize=(11, 7))

plt.pcolormesh(
    lon,
    lat,
    spatial_mean,
    shading="auto",
    cmap="viridis"
)

plt.colorbar(label="Mean Total Cloud Area (dataset units)")
plt.xlabel("Longitude (°E)")
plt.ylabel("Latitude (°N)")
plt.title("Mean Pre-Monsoon Cloud Cover (2010–2021)")
plt.tight_layout()

plt.savefig(
    FIGURE_DIR / "03_spatial_cloud_cover.png",
    dpi=300
)
plt.close()

print("Saved: Spatial cloud-cover map")

# ==================================================
# 6. YEAR-TO-YEAR VARIABILITY
# ==================================================

annual_rows = []
hourly_sum = np.zeros(24, dtype=float)
hourly_count = np.zeros(24, dtype=float)

for file in FILES:

    year = int(file.stem.split("_")[1])

    with xr.open_dataset(file) as ds:

        cloud = ds[VARIABLE]

        annual_mean = float(
            cloud.mean(skipna=True).values
        )

        annual_rows.append({
            "year": year,
            "mean_cloud_cover": annual_mean
        })

        # Group observations by UTC hour
        hourly_mean = cloud.groupby(
            "time.hour"
        ).mean(dim="time", skipna=True)

        hourly_valid_count = cloud.groupby(
            "time.hour"
        ).count(dim="time")

        # Aggregate across space for each hour
        for hour in range(24):
            hour_values = cloud.where(
                cloud.time.dt.hour == hour,
                drop=True
            )

            values = hour_values.values
            finite = np.isfinite(values)

            hourly_sum[hour] += float(
                np.sum(values[finite])
            )
            hourly_count[hour] += int(
                np.sum(finite)
            )

annual_df = pd.DataFrame(annual_rows)

plt.figure(figsize=(10, 6))
plt.plot(
    annual_df["year"],
    annual_df["mean_cloud_cover"],
    marker="o"
)

plt.title("Year-to-Year Pre-Monsoon Cloud Cover")
plt.xlabel("Year")
plt.ylabel("Mean Total Cloud Area (dataset units)")
plt.xticks(annual_df["year"], rotation=45)
plt.tight_layout()

plt.savefig(
    FIGURE_DIR / "04_annual_variability.png",
    dpi=300
)
plt.close()

print("Saved: Annual variability")

# ==================================================
# 7. DIURNAL VARIABILITY
# ==================================================

hourly_mean = np.divide(
    hourly_sum,
    hourly_count,
    out=np.full(24, np.nan),
    where=hourly_count > 0
)

plt.figure(figsize=(10, 6))
plt.plot(
    np.arange(24),
    hourly_mean,
    marker="o"
)

plt.title("Pre-Monsoon Diurnal Cloud-Cover Cycle")
plt.xlabel("Hour (UTC)")
plt.ylabel("Mean Total Cloud Area (dataset units)")
plt.xticks(np.arange(0, 24, 2))
plt.tight_layout()

plt.savefig(
    FIGURE_DIR / "05_diurnal_variability.png",
    dpi=300
)
plt.close()

print("Saved: Diurnal variability")

# ==================================================
# 8. SAVE SUMMARY TABLES
# ==================================================

annual_df.to_csv(
    FIGURE_DIR / "annual_cloud_cover.csv",
    index=False
)

pd.DataFrame({
    "hour_utc": np.arange(24),
    "mean_cloud_cover": hourly_mean,
    "valid_count": hourly_count.astype(int)
}).to_csv(
    FIGURE_DIR / "diurnal_cloud_cover.csv",
    index=False
)

print("\nSUCCESS: PRE-MONSOON EDA COMPLETED!")
print("Figures saved to:", FIGURE_DIR)
