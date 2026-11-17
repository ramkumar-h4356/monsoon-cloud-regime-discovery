
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data/interim/ceres_seasonal/pre_monsoon"
OUTPUT_DIR = ROOT / "reports/data_quality"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_YEARS = range(2010, 2022)
EXPECTED_DIMS = ("time", "lat", "lon")
EXPECTED_SHAPE = (720, 32, 30)
EXPECTED_VARIABLE_COUNT = 45

rows = []
reference_schema = None

for year in EXPECTED_YEARS:
    file = DATA_DIR / f"CERES_{year}_pre_monsoon.nc"
    print(f"\nChecking {year}...")

    if not file.exists():
        rows.append({
            "year": year,
            "filename": file.name,
            "status": "FAIL",
            "reason": "File missing"
        })
        continue

    try:
        with xr.open_dataset(file) as ds:
            schema = {
                name: (
                    tuple(var.dims),
                    str(var.dtype),
                    str(var.attrs.get("units", "MISSING"))
                )
                for name, var in ds.data_vars.items()
            }

            if reference_schema is None:
                reference_schema = schema

            problems = []

            if len(schema) != EXPECTED_VARIABLE_COUNT:
                problems.append("Incorrect variable count")

            missing = set(reference_schema) - set(schema)
            extra = set(schema) - set(reference_schema)

            if missing:
                problems.append(f"Missing variables: {sorted(missing)}")

            if extra:
                problems.append(f"Unexpected variables: {sorted(extra)}")

            for name, var in ds.data_vars.items():
                if tuple(var.dims) != EXPECTED_DIMS:
                    problems.append(f"{name}: wrong dimensions")

                if tuple(var.shape) != EXPECTED_SHAPE:
                    problems.append(f"{name}: wrong shape")

                if np.dtype(var.dtype) != np.dtype("float32"):
                    problems.append(f"{name}: wrong dtype")

                if var.attrs.get("units") in (None, ""):
                    problems.append(f"{name}: missing units")

                if name in reference_schema:
                    if schema[name] != reference_schema[name]:
                        problems.append(
                            f"{name}: schema differs from reference"
                        )

            status = "PASS" if not problems else "FAIL"

            rows.append({
                "year": year,
                "filename": file.name,
                "variable_count": len(schema),
                "status": status,
                "reason": "; ".join(problems)
            })

            print(f"Status: {status}")
            if problems:
                for problem in problems:
                    print(" -", problem)

    except Exception as error:
        rows.append({
            "year": year,
            "filename": file.name,
            "status": "FAIL",
            "reason": str(error)
        })
        print("Status: FAIL -", error)

df = pd.DataFrame(rows)

report = OUTPUT_DIR / "pre_monsoon_schema_validation.csv"
df.to_csv(report, index=False)

passed = int((df["status"] == "PASS").sum())
all_passed = passed == 12

print("\n" + "=" * 60)
print("PRE-MONSOON VARIABLE SCHEMA VALIDATION")
print("=" * 60)
print("Files checked:", len(df))
print("Files passed:", passed)
print("Files failed:", len(df) - passed)
print("FINAL STATUS:", "PASS" if all_passed else "REVIEW REQUIRED")
print("Report saved to:", report)

sys.exit(0 if all_passed else 1)
