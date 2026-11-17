
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

# ============================================
# 1. PROJECT PATHS
# ============================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "ceres_seasonal"
    / "pre_monsoon"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "reports"
    / "iwp_investigation"
    / "phase_endpoint_check"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================
# 2. CLOUD LAYERS
# ============================================

LAYERS = {
    "high": "high",
    "low": "low",
    "mid_high": "mid_high",
    "mid_low": "mid_low",
    "total": "total",
}

# Exact comparisons are intentional.
# Phase values are inspected without rounding.

def classify_phase(phase):
    return {
        "exactly_1": phase == 1.0,
        "between_1_and_1_2": (
            (phase > 1.0) & (phase < 1.2)
        ),
        "exactly_1_2": phase == 1.2,
        "between_1_2_and_2": (
            (phase > 1.2) & (phase < 2.0)
        ),
        "exactly_2": phase == 2.0,
    }


# ============================================
# 3. PROCESS EACH YEAR
# ============================================

files = sorted(DATA_DIR.glob("*.nc"))

if len(files) != 12:
    raise RuntimeError(
        f"Expected 12 NetCDF files, found {len(files)} "
        f"in {DATA_DIR}"
    )

records = []
coverage_records = []

for file in files:

    print(f"\nProcessing: {file.name}")

    with xr.open_dataset(file) as ds:

        year = int(file.stem.split("_")[1])

        for layer, suffix in LAYERS.items():

            phase_name = f"cldphase_{suffix}_1h"
            iwp_name = f"iwp_{suffix}_1h"

            if phase_name not in ds or iwp_name not in ds:
                raise KeyError(
                    f"Missing {phase_name} or {iwp_name} "
                    f"in {file.name}"
                )

            phase = ds[phase_name].values
            iwp = ds[iwp_name].values

            if phase.shape != iwp.shape:
                raise ValueError(
                    f"Shape mismatch: {phase_name}, {iwp_name}"
                )

            valid_phase = np.isfinite(phase)
            valid_iwp = np.isfinite(iwp)

            groups = classify_phase(phase)

            # Include phase NaNs and any unexpected
            # phase values in the coverage audit.
            assigned = np.zeros(phase.shape, dtype=bool)

            for group_name, mask in groups.items():

                assigned |= mask

                count = int(np.count_nonzero(mask))

                available = int(
                    np.count_nonzero(mask & valid_iwp)
                )

                missing = count - available

                percent = (
                    available / count * 100
                    if count > 0
                    else np.nan
                )

                records.append({
                    "year": year,
                    "layer": layer,
                    "phase_group": group_name,
                    "sample_count": count,
                    "iwp_available_count": available,
                    "iwp_missing_count": missing,
                    "iwp_available_percent": percent,
                    "iwp_missing_percent": (
                        100 - percent
                        if count > 0
                        else np.nan
                    ),
                })

            coverage_records.append({
                "year": year,
                "layer": layer,
                "total_count": phase.size,
                "phase_missing_count": int(
                    np.count_nonzero(~valid_phase)
                ),
                "unclassified_valid_phase_count": int(
                    np.count_nonzero(
                        valid_phase & ~assigned
                    )
                ),
                "iwp_available_when_phase_missing": int(
                    np.count_nonzero(
                        ~valid_phase & valid_iwp
                    )
                ),
            })

    print(f"Completed {year}")

# ============================================
# 4. SAVE YEARLY REPORT
# ============================================

yearly = pd.DataFrame(records)

yearly_path = (
    OUTPUT_DIR / "01_yearly_phase_endpoint_iwp.csv"
)

yearly.to_csv(yearly_path, index=False)

print(f"\nSaved: {yearly_path}")

# ============================================
# 5. AGGREGATED SUMMARY
# ============================================

summary = (
    yearly.groupby(
        ["layer", "phase_group"],
        as_index=False
    )[
        [
            "sample_count",
            "iwp_available_count",
            "iwp_missing_count",
        ]
    ]
    .sum()
)

summary["iwp_available_percent"] = np.where(
    summary["sample_count"] > 0,
    summary["iwp_available_count"]
    / summary["sample_count"] * 100,
    np.nan,
)

summary["iwp_missing_percent"] = (
    100 - summary["iwp_available_percent"]
)

summary_path = (
    OUTPUT_DIR / "02_overall_phase_endpoint_iwp.csv"
)

summary.to_csv(summary_path, index=False)

# ============================================
# 6. PHASE COVERAGE AUDIT
# ============================================

coverage = pd.DataFrame(coverage_records)

coverage_path = (
    OUTPUT_DIR / "03_phase_coverage_audit.csv"
)

coverage.to_csv(coverage_path, index=False)

# ============================================
# 7. DISPLAY RESULTS
# ============================================

print("\n=== EXACT PHASE ENDPOINT RESULTS ===")

print(
    summary[
        [
            "layer",
            "phase_group",
            "sample_count",
            "iwp_available_percent",
        ]
    ].to_string(index=False)
)

print("\n=== COVERAGE AUDIT ===")

print(
    coverage[
        [
            "phase_missing_count",
            "unclassified_valid_phase_count",
            "iwp_available_when_phase_missing",
        ]
    ].sum()
)

print("\nSUCCESS: ENDPOINT VALIDATION COMPLETED!")
print(f"Reports saved to: {OUTPUT_DIR}")
