
from pathlib import Path
import xarray as xr

data_dir = Path(
    "data/interim/ceres_seasonal/pre_monsoon"
)

files = sorted(data_dir.glob("*.nc"))

if not files:
    raise FileNotFoundError(
        "No NetCDF files found."
    )

with xr.open_dataset(files[0]) as ds:

    print("\n=== DATASET INFORMATION ===")
    print("File:", files[0].name)

    print("\n=== GLOBAL ATTRIBUTES ===")
    for key, value in ds.attrs.items():
        print(f"{key}: {value}")

    variables = [
        "cldphase_total_1h",
        "cldphase_low_1h",
        "cldphase_mid_low_1h",
        "cldphase_mid_high_1h",
        "cldphase_high_1h",
        "iwp_total_1h",
        "lwp_total_1h",
    ]

    print("\n=== VARIABLE METADATA ===")

    for name in variables:

        if name not in ds:
            print(f"\n{name}: NOT FOUND")
            continue

        variable = ds[name]

        print(f"\nVARIABLE: {name}")
        print("Data type:", variable.dtype)
        print("Dimensions:", variable.dims)

        print("Attributes:")
        for key, value in variable.attrs.items():
            print(f"  {key}: {value}")

print("\nMETADATA INSPECTION COMPLETE")
