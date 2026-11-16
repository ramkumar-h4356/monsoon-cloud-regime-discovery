
from pathlib import Path
import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    ROOT / "data" / "interim"
    / "ceres_seasonal" / "pre_monsoon"
)

file = DATA_DIR / "CERES_2010_pre_monsoon.nc"

phase_vars = [
    "cldphase_high_1h",
    "cldphase_low_1h",
    "cldphase_mid_high_1h",
    "cldphase_mid_low_1h",
    "cldphase_total_1h",
]

with xr.open_dataset(file) as ds:

    for name in phase_vars:
        da = ds[name]

        values = da.values.ravel()
        values = values[np.isfinite(values)]

        print("\n" + "=" * 50)
        print("Variable:", name)
        print("Attributes:", da.attrs)

        if values.size == 0:
            print("No valid values")
            continue

        print("Minimum:", np.min(values))
        print("Maximum:", np.max(values))
        print("Mean:", np.mean(values))
        print("Median:", np.median(values))
        print("Unique value count:", len(np.unique(values)))

        print("Exactly 1:", np.sum(values == 1))
        print("Exactly 2:", np.sum(values == 2))
        print(
            "Between 1 and 2:",
            np.sum((values > 1) & (values < 2))
        )

print("\nSUCCESS: Cloud-phase inspection completed!")
