
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

# -----------------------------------------
# 1. Project paths
# -----------------------------------------

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    ROOT / "data" / "interim"
    / "ceres_seasonal" / "pre_monsoon"
)

OUTPUT_DIR = ROOT / "reports" / "scientific_checks"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(DATA_DIR.glob("*.nc"))

print("=== PRE-MONSOON SCIENTIFIC CHECKS ===")
print("Files found:", len(files))

if len(files) != 12:
    raise ValueError(
        f"Expected 12 NetCDF files, found {len(files)}"
    )

# -----------------------------------------
# 2. Variables to investigate
# -----------------------------------------

CLOUD = "cldarea_total_1h"
IWP = "iwp_low_1h"

cloud_results = []
iwp_results = []
consistency_results = []

# -----------------------------------------
# 3. Analyze each year
# -----------------------------------------

for file in files:

    year = int(file.stem.split("_")[1])
    print(f"\nProcessing {year}...")

    with xr.open_dataset(file) as ds:

        if CLOUD not in ds or IWP not in ds:
            raise KeyError(
                f"Required variables missing in {file.name}"
            )

        cloud = ds[CLOUD].values.astype(float)
        iwp = ds[IWP].values.astype(float)

        # ---------------------------------
        # CHECK 1: Cloud-cover extremes
        # ---------------------------------

        valid_cloud = cloud[np.isfinite(cloud)]

        if valid_cloud.size == 0:
            raise ValueError(
                f"No valid cloud observations in {year}"
            )

        cloud_results.append({
            "year": year,
            "valid_count": valid_cloud.size,
            "near_clear_percent":
                100 * np.mean(valid_cloud <= 1),
            "near_overcast_percent":
                100 * np.mean(valid_cloud >= 99),
            "exact_zero_percent":
                100 * np.mean(valid_cloud == 0),
            "exact_100_percent":
                100 * np.mean(valid_cloud == 100),
            "mean_cloud_cover":
                np.mean(valid_cloud),
            "median_cloud_cover":
                np.median(valid_cloud),
            "min_cloud_cover":
                np.min(valid_cloud),
            "max_cloud_cover":
                np.max(valid_cloud)
        })

        # ---------------------------------
        # CHECK 2: IWP missingness
        # ---------------------------------

        missing_iwp = ~np.isfinite(iwp)
        valid_iwp = np.isfinite(iwp)

        cloudy = np.isfinite(cloud) & (cloud > 1)
        clear = np.isfinite(cloud) & (cloud <= 1)

        def missing_percent(mask):
            count = np.count_nonzero(mask)
            if count == 0:
                return np.nan
            return (
                100 * np.count_nonzero(
                    missing_iwp & mask
                ) / count
            )

        iwp_results.append({
            "year": year,
            "total_observations": iwp.size,
            "missing_iwp_percent":
                100 * np.mean(missing_iwp),
            "missing_when_clear_percent":
                missing_percent(clear),
            "missing_when_cloudy_percent":
                missing_percent(cloudy),
            "valid_iwp_count":
                np.count_nonzero(valid_iwp),
            "valid_iwp_zero_percent":
                100 * np.mean(iwp[valid_iwp] == 0)
                if valid_iwp.any() else np.nan,
            "negative_iwp_count":
                np.count_nonzero(
                    valid_iwp & (iwp < 0)
                )
        })

        # ---------------------------------
        # CHECK 3: Cloud-cover consistency
        # ---------------------------------

        invalid_cloud = (
            np.isfinite(cloud)
            & ((cloud < 0) | (cloud > 100))
        )

        consistency_results.append({
            "year": year,
            "cloud_below_zero_count":
                np.count_nonzero(
                    np.isfinite(cloud) & (cloud < 0)
                ),
            "cloud_above_100_count":
                np.count_nonzero(
                    np.isfinite(cloud) & (cloud > 100)
                ),
            "invalid_cloud_percent":
                100 * np.mean(invalid_cloud),
            "cloud_missing_percent":
                100 * np.mean(~np.isfinite(cloud))
        })

    print(f"Completed {year}")

# -----------------------------------------
# 4. Save CSV reports
# -----------------------------------------

cloud_df = pd.DataFrame(cloud_results)
iwp_df = pd.DataFrame(iwp_results)
consistency_df = pd.DataFrame(consistency_results)

cloud_df.to_csv(
    OUTPUT_DIR / "cloud_extremes.csv",
    index=False
)

iwp_df.to_csv(
    OUTPUT_DIR / "iwp_missingness.csv",
    index=False
)

consistency_df.to_csv(
    OUTPUT_DIR / "cloud_consistency.csv",
    index=False
)

# -----------------------------------------
# 5. Display summary
# -----------------------------------------

print("\n=== CLOUD EXTREMES ===")
print(cloud_df.to_string(index=False))

print("\n=== IWP MISSINGNESS ===")
print(iwp_df.to_string(index=False))

print("\n=== CLOUD CONSISTENCY ===")
print(consistency_df.to_string(index=False))

print("\nSUCCESS: SCIENTIFIC CHECKS COMPLETED!")
print("Reports saved to:", OUTPUT_DIR)
