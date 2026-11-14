
from pathlib import Path
from datetime import date, timedelta
import csv

import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data" / "interim" / "ceres_seasonal"
REPORT_DIR = ROOT / "reports" / "data_quality"

SEASONS = {
    "pre_monsoon": (4, 15, 5, 14),
    "established_monsoon": (7, 15, 8, 13),
    "post_monsoon": (10, 15, 11, 13),
}

YEARS = range(2010, 2022)


def expected_window(year, season):
    sm, sd, em, ed = SEASONS[season]

    start = date(year, sm, sd)
    end = date(year, em, ed) + timedelta(days=1)

    return start, end


def get_fill_values(variable, global_attrs):
    candidates = []

    for key in ("_FillValue", "missing_value"):
        value = variable.attrs.get(key)

        if value is None:
            value = variable.encoding.get(key)

        if value is not None:
            for item in np.asarray(value).flatten():
                if np.issubdtype(np.asarray(item).dtype, np.number):
                    candidates.append(float(item))

    for key in ("Fill_Value", "fill_value"):
        value = global_attrs.get(key)

        if value is not None:
            for item in np.asarray(value).flatten():
                if np.issubdtype(np.asarray(item).dtype, np.number):
                    candidates.append(float(item))

    return list(set(candidates))


def inspect_variable(variable, global_attrs):
    values = np.asarray(variable.values)

    result = {
        "dtype": str(values.dtype),
        "dimensions": ",".join(variable.dims),
        "units": variable.attrs.get("units", ""),
        "long_name": variable.attrs.get("long_name", ""),
        "total_values": values.size,
        "missing_values": "",
        "nonfinite_values": "",
        "fill_value_occurrences": "",
        "missing_percent": "",
        "minimum": "",
        "maximum": "",
    }

    if np.issubdtype(values.dtype, np.number):
        finite = np.isfinite(values)
        missing_count = int(np.count_nonzero(~finite))

        fill_values = get_fill_values(variable, global_attrs)

        fill_mask = np.zeros(values.shape, dtype=bool)

        for fill_value in fill_values:
            fill_mask |= values == fill_value

        valid_mask = finite & ~fill_mask
        valid_values = values[valid_mask]

        result["missing_values"] = missing_count
        result["nonfinite_values"] = int(
            np.count_nonzero(~finite)
        )
        result["fill_value_occurrences"] = int(
            np.count_nonzero(fill_mask & finite)
        )
        result["missing_percent"] = round(
            100 * (missing_count + np.count_nonzero(fill_mask & finite))
            / values.size,
            4
        )

        if valid_values.size:
            result["minimum"] = float(np.min(valid_values))
            result["maximum"] = float(np.max(valid_values))

    del values

    return result


def validate_time(ds, year, season):
    start, end = expected_window(year, season)

    times = ds.time.values.astype("datetime64[ns]")

    if len(times) != 720:
        raise ValueError(f"Expected 720 records, found {len(times)}")

    if np.isnat(times).any():
        raise ValueError("Missing or invalid timestamps found")

    if np.unique(times).size != len(times):
        raise ValueError("Duplicate timestamps found")

    if not np.all(times[:-1] < times[1:]):
        raise ValueError("Timestamps are not strictly increasing")

    start_np = np.datetime64(start.isoformat())
    end_np = np.datetime64(end.isoformat())

    if np.any(times < start_np) or np.any(times >= end_np):
        raise ValueError("Timestamps outside expected seasonal window")

    dates, counts = np.unique(
        times.astype("datetime64[D]"),
        return_counts=True
    )

    if len(dates) != 30 or not np.all(counts == 24):
        raise ValueError(
            "Expected 30 days with 24 observations per day"
        )


def schema_signature(ds):
    signature = {}

    for name, variable in ds.data_vars.items():
        signature[name] = (
            tuple(variable.dims),
            str(variable.dtype),
            variable.attrs.get("units", "")
        )

    return signature


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    file_report = []
    variable_report = []
    schema_report = []

    reference_lat = None
    reference_lon = None
    reference_schema = None

    total_files = 0
    passed_files = 0

    for season in SEASONS:
        for year in YEARS:

            path = (
                DATA_DIR
                / season
                / f"CERES_{year}_{season}.nc"
            )

            total_files += 1
            errors = []

            print(f"\nChecking {year} - {season}")

            if not path.exists():
                file_report.append({
                    "year": year,
                    "season": season,
                    "filename": str(path),
                    "status": "MISSING",
                    "errors": "File not found"
                })
                continue

            try:
                with xr.open_dataset(
                    path,
                    engine="netcdf4"
                ) as ds:

                    if not {"time", "lat", "lon"}.issubset(ds.variables):
                        raise ValueError(
                            "Required time, lat or lon variable missing"
                        )

                    try:
                        validate_time(ds, year, season)
                    except Exception as error:
                        errors.append(f"TIME: {error}")

                    lat = ds.lat.values
                    lon = ds.lon.values

                    if reference_lat is None:
                        reference_lat = lat.copy()
                        reference_lon = lon.copy()
                    else:
                        if not np.array_equal(lat, reference_lat):
                            errors.append("Latitude coordinates differ")

                        if not np.array_equal(lon, reference_lon):
                            errors.append("Longitude coordinates differ")

                    if len(lat) != 32 or len(lon) != 30:
                        errors.append(
                            f"Unexpected spatial dimensions: "
                            f"{len(lat)} x {len(lon)}"
                        )

                    if (
                        lat.min() < 6 or lat.max() > 38
                        or lon.min() < 68 or lon.max() > 98
                    ):
                        errors.append(
                            "Coordinates outside study domain"
                        )

                    current_schema = schema_signature(ds)

                    if reference_schema is None:
                        reference_schema = current_schema
                    else:
                        if current_schema != reference_schema:
                            errors.append(
                                "Variable schema differs from reference"
                            )

                    if current_schema != reference_schema:
                        schema_report.append({
                            "year": year,
                            "season": season,
                            "issue": "Variable schema mismatch"
                        })

                    global_attrs = ds.attrs

                    for name, variable in ds.data_vars.items():
                        details = inspect_variable(
                            variable,
                            global_attrs
                        )

                        variable_report.append({
                            "year": year,
                            "season": season,
                            "variable": name,
                            **details
                        })

                status = "PASS" if not errors else "REVIEW"

                if status == "PASS":
                    passed_files += 1

                file_report.append({
                    "year": year,
                    "season": season,
                    "filename": path.name,
                    "status": status,
                    "errors": "; ".join(errors),
                    "size_mb": round(
                        path.stat().st_size / (1024 ** 2), 2
                    )
                })

                print(f"  {status}")

            except Exception as error:
                file_report.append({
                    "year": year,
                    "season": season,
                    "filename": path.name,
                    "status": "ERROR",
                    "errors": str(error)
                })

                print(f"  ERROR: {error}")

    def write_csv(filename, rows):
        if not rows:
            return

        output = REPORT_DIR / filename

        with open(
            output,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(rows[0].keys())
            )
            writer.writeheader()
            writer.writerows(rows)

    write_csv("seasonal_file_quality.csv", file_report)
    write_csv("seasonal_variable_quality.csv", variable_report)
    write_csv("seasonal_schema_issues.csv", schema_report)

    print("\nQUALITY VALIDATION SUMMARY")
    print("--------------------------")
    print("Files checked:", total_files)
    print("Files passed:", passed_files)
    print("Files requiring review:", total_files - passed_files)
    print("Variables inspected:", len(variable_report))
    print("Reports saved:", REPORT_DIR)

    if passed_files != 36:
        print("\nSome files require review.")
    else:
        print("\nAll 36 files passed structural quality checks.")


if __name__ == "__main__":
    main()
