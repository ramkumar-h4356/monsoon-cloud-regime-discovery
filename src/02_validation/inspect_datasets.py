
from pathlib import Path
import xarray as xr
import pandas as pd
from contextlib import redirect_stdout
from io import StringIO

ROOT = Path(__file__).resolve().parents[2] / "raw_data"

def inspect_netcdf(path):
    print("\n" + "=" * 75)
    print("FILE:", path.name)
    print("=" * 75)

    try:
        with xr.open_dataset(path) as ds:
            print("\nDimensions:")
            print(dict(ds.sizes))

            print("\nCoordinates:")
            for name, coord in ds.coords.items():
                print(
                    name,
                    "| dimensions:", coord.dims,
                    "| shape:", coord.shape,
                    "| units:", coord.attrs.get("units"),
                )
                if coord.size <= 10:
                    print("  Values:", coord.values)
                elif "time" in name.lower():
                    print("  First:", coord.values[0])
                    print("  Last:", coord.values[-1])

            print("\nData variables:")
            for name, var in ds.data_vars.items():
                print(
                    name,
                    "| dimensions:", var.dims,
                    "| units:", var.attrs.get("units"),
                    "| long_name:", var.attrs.get("long_name"),
                    "| missing:", var.attrs.get("_FillValue"),
                )

            print("\nGlobal attributes:")
            for key, value in ds.attrs.items():
                print(f"{key}: {value}")

    except Exception as e:
        print("ERROR:", repr(e))


def inspect_text_files():
    print("\n" + "=" * 75)
    print("NOAA FILES")
    print("=" * 75)

    dmi = ROOT / "NOAA_DMI" / "dmi.had.long.csv"
    roni = ROOT / "NOAA_RONI" / "RONI.ascii.txt"

    print("\nDMI CSV:")
    try:
        df = pd.read_csv(dmi)
        print("Columns:", list(df.columns))
        print(df.head(8).to_string(index=False))
        print("Rows:", len(df))
        print("Last rows:")
        print(df.tail(5).to_string(index=False))
    except Exception as e:
        print("DMI ERROR:", repr(e))

    print("\nRONI TXT:")
    try:
        with open(roni, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 15:
                    break
                print(line.rstrip())
    except Exception as e:
        print("RONI ERROR:", repr(e))



def run_inspection():
    print("\nCERES INSPECTION")
    ceres = ROOT / "CERES"

    for path in sorted(ceres.glob("*.nc")):
        inspect_netcdf(path)

    print("\nIMD INSPECTION")
    imd = ROOT / "IMD_Rainfall"

    for path in sorted(imd.glob("*.nc")):
        inspect_netcdf(path)

    inspect_text_files()
    print("\nINSPECTION COMPLETE")


buffer = StringIO()

with redirect_stdout(buffer):
    run_inspection()

report = buffer.getvalue()

REPORT = ROOT.parent / "reports" / "data_quality" / "inspection_report.txt"
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(report, encoding="utf-8")

print(report)
print(f"\nReport saved at: {REPORT}")