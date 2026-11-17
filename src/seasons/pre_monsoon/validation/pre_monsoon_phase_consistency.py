
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

# ==================================================
# 1. PROJECT PATHS
# ==================================================

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    ROOT / "data" / "interim"
    / "ceres_seasonal" / "pre_monsoon"
)

REPORT_DIR = (
    ROOT / "reports" / "iwp_investigation"
    / "phase_consistency"
)

REPORT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(DATA_DIR.glob("*.nc"))

if len(files) != 12:
    raise ValueError(
        f"Expected 12 NetCDF files, found {len(files)}"
    )

# ==================================================
# 2. MATCH CLOUD LAYERS
# ==================================================

layers = [
    "high",
    "mid_high",
    "mid_low",
    "low",
    "total",
]

phase_bins = [
    1.0, 1.2, 1.4, 1.6, 1.8, 2.0
]

phase_labels = [
    "1.0-1.2",
    "1.2-1.4",
    "1.4-1.6",
    "1.6-1.8",
    "1.8-2.0",
]

phase_records = []
availability_records = []
cloud_records = []
yearly_records = []

# ==================================================
# 3. PROCESS ALL YEARS
# ==================================================

for file in files:

    year = int(file.stem.split("_")[1])
    print(f"\nProcessing year: {year}")

    with xr.open_dataset(file) as ds:

        for layer in layers:

            phase_name = f"cldphase_{layer}_1h"
            iwp_name = f"iwp_{layer}_1h"
            cloud_name = f"cldarea_{layer}_1h"

            required = [
                phase_name,
                iwp_name,
                cloud_name,
            ]

            if any(v not in ds for v in required):
                print(
                    f"Skipping {layer}: missing variable"
                )
                continue

            phase = ds[phase_name].values.ravel()
            iwp = ds[iwp_name].values.ravel()
            cloud = ds[cloud_name].values.ravel()

            if not (
                len(phase) == len(iwp) == len(cloud)
            ):
                raise ValueError(
                    f"Shape mismatch: {year}, {layer}"
                )

            valid_phase = np.isfinite(phase)
            valid_iwp = np.isfinite(iwp)
            valid_cloud = np.isfinite(cloud)

            # --------------------------------------
            # A. OVERALL YEARLY AVAILABILITY
            # --------------------------------------

            yearly_records.append({
                "year": year,
                "layer": layer,
                "total_count": len(iwp),
                "phase_valid_percent":
                    100 * valid_phase.mean(),
                "iwp_valid_percent":
                    100 * valid_iwp.mean(),
                "cloud_valid_percent":
                    100 * valid_cloud.mean(),
                "phase_iwp_both_valid_percent":
                    100 * (
                        valid_phase & valid_iwp
                    ).mean(),
            })

            # --------------------------------------
            # B. PHASE DISTRIBUTION
            # --------------------------------------

            for index, label in enumerate(
                phase_labels
            ):

                lower = phase_bins[index]
                upper = phase_bins[index + 1]

                if index == len(phase_labels) - 1:
                    mask = (
                        valid_phase
                        & (phase >= lower)
                        & (phase <= upper)
                    )
                else:
                    mask = (
                        valid_phase
                        & (phase >= lower)
                        & (phase < upper)
                    )

                count = int(mask.sum())

                phase_records.append({
                    "year": year,
                    "layer": layer,
                    "phase_interval": label,
                    "sample_count": count,
                    "percent_of_valid_phase":
                        100 * count /
                        max(int(valid_phase.sum()), 1),
                })

                # ----------------------------------
                # C. IWP AVAILABILITY BY PHASE
                # ----------------------------------

                if count > 0:
                    available = int(
                        (mask & valid_iwp).sum()
                    )
                    missing = count - available

                    mean_iwp = (
                        float(np.mean(iwp[
                            mask & valid_iwp
                        ]))
                        if available > 0
                        else np.nan
                    )

                    availability_records.append({
                        "year": year,
                        "layer": layer,
                        "phase_interval": label,
                        "sample_count": count,
                        "iwp_available_count":
                            available,
                        "iwp_missing_count":
                            missing,
                        "iwp_available_percent":
                            100 * available / count,
                        "iwp_missing_percent":
                            100 * missing / count,
                        "mean_valid_iwp":
                            mean_iwp,
                    })

            # --------------------------------------
            # D. CLOUD-COVER RELATIONSHIP
            # --------------------------------------

            cloud_intervals = [
                (0, 1, "0-1"),
                (1, 50, "1-50"),
                (50, 99, "50-99"),
                (99, 100, "99-100"),
            ]

            for lower, upper, label in cloud_intervals:

                if upper == 100:
                    mask = (
                        valid_cloud
                        & (cloud >= lower)
                        & (cloud <= upper)
                    )
                else:
                    mask = (
                        valid_cloud
                        & (cloud >= lower)
                        & (cloud < upper)
                    )

                count = int(mask.sum())

                if count == 0:
                    continue

                cloud_records.append({
                    "year": year,
                    "layer": layer,
                    "cloud_interval": label,
                    "sample_count": count,
                    "iwp_available_percent":
                        100 * (
                            mask & valid_iwp
                        ).sum() / count,
                    "phase_available_percent":
                        100 * (
                            mask & valid_phase
                        ).sum() / count,
                })

    print(f"Completed year {year}")

# ==================================================
# 4. SAVE CSV REPORTS
# ==================================================

reports = {
    "01_phase_distribution.csv":
        pd.DataFrame(phase_records),

    "02_iwp_availability_by_phase.csv":
        pd.DataFrame(availability_records),

    "03_cloud_cover_relationship.csv":
        pd.DataFrame(cloud_records),

    "04_yearly_phase_iwp_summary.csv":
        pd.DataFrame(yearly_records),
}

for filename, dataframe in reports.items():

    output = REPORT_DIR / filename

    dataframe.to_csv(output, index=False)

    print(f"Saved: {output}")

# ==================================================
# 5. PRINT SUMMARY
# ==================================================

print("\n=== IWP-PHASE CONSISTENCY SUMMARY ===")

availability_df = reports[
    "02_iwp_availability_by_phase.csv"
]

if not availability_df.empty:

    summary = (
        availability_df
        .groupby(["layer", "phase_interval"])
        .agg(
            sample_count=("sample_count", "sum"),
            available_count=(
                "iwp_available_count", "sum"
            ),
        )
        .reset_index()
    )

    summary["iwp_available_percent"] = (
        100 * summary["available_count"]
        / summary["sample_count"]
    )

    print(summary.to_string(index=False))

print(
    "\nSUCCESS: PHASE CONSISTENCY ANALYSIS COMPLETED!"
)
