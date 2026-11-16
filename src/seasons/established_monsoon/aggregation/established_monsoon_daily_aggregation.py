from pathlib import Path
import argparse
import csv
import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT / "data/interim/ceres_extracted/established_monsoon"
OUTPUT_DIR = ROOT / "data/processed/ceres_daily/established_monsoon"
REPORT_DIR = ROOT / "reports/preprocessing"

START_YEAR = 2010
END_YEAR = 2021
EXPECTED_VARIABLES = 45
EXPECTED_VARIABLE_NAMES = {
    "cldarea_high_1h", "cldarea_low_1h", "cldarea_mid_high_1h",
    "cldarea_mid_low_1h", "cldarea_total_1h",
    "cldhght_high_1h", "cldhght_low_1h", "cldhght_mid_high_1h",
    "cldhght_mid_low_1h", "cldhght_total_1h",
    "cldphase_high_1h", "cldphase_low_1h", "cldphase_mid_high_1h",
    "cldphase_mid_low_1h", "cldphase_total_1h",
    "cldpress_high_1h", "cldpress_low_1h", "cldpress_mid_high_1h",
    "cldpress_mid_low_1h", "cldpress_top_high_1h",
    "cldpress_top_low_1h", "cldpress_top_mid_high_1h",
    "cldpress_top_mid_low_1h", "cldpress_top_total_1h",
    "cldpress_total_1h",
    "cldtau_high_1h", "cldtau_low_1h", "cldtau_mid_high_1h",
    "cldtau_mid_low_1h", "cldtau_total_1h",
    "cldtemp_high_1h", "cldtemp_low_1h", "cldtemp_mid_high_1h",
    "cldtemp_mid_low_1h", "cldtemp_total_1h",
    "iwp_high_1h", "iwp_low_1h", "iwp_mid_high_1h",
    "iwp_mid_low_1h", "iwp_total_1h",
    "lwp_high_1h", "lwp_low_1h", "lwp_mid_high_1h",
    "lwp_mid_low_1h", "lwp_total_1h",
}
EXPECTED_HOURS = 720
EXPECTED_DAYS = 30
HOURS_PER_DAY = 24
MIN_VALID_HOURS = 18


def validate_input(ds, year):
    if "time" not in ds.coords:
        raise ValueError(f"{year}: missing time coordinate")

    if "lat" not in ds.coords or "lon" not in ds.coords:
        raise ValueError(f"{year}: missing spatial coordinates")

    actual_variables = set(ds.data_vars)

    if len(actual_variables) != EXPECTED_VARIABLES:
        raise ValueError(
            f"{year}: expected {EXPECTED_VARIABLES} variables, "
            f"found {len(actual_variables)}"
        )

    if actual_variables != EXPECTED_VARIABLE_NAMES:
        missing = sorted(EXPECTED_VARIABLE_NAMES - actual_variables)
        unexpected = sorted(actual_variables - EXPECTED_VARIABLE_NAMES)
        raise ValueError(
            f"{year}: variable schema mismatch. "
            f"Missing: {missing}; unexpected: {unexpected}"
        )

    if ds.sizes.get("time") != EXPECTED_HOURS:
        raise ValueError(f"{year}: expected 720 hourly records")

    if ds.sizes.get("lat") != 32 or ds.sizes.get("lon") != 30:
        raise ValueError(f"{year}: unexpected spatial dimensions")

    lat = ds["lat"].values
    lon = ds["lon"].values

    if not np.allclose(lat, np.arange(6.5, 38.0, 1.0)):
        raise ValueError(f"{year}: unexpected latitude grid")

    if not np.allclose(lon, np.arange(68.5, 98.0, 1.0)):
        raise ValueError(f"{year}: unexpected longitude grid")

    for variable in ds.data_vars:
        if ds[variable].dims != ("time", "lat", "lon"):
            raise ValueError(
                f"{year}: unexpected dimensions for {variable}: "
                f"{ds[variable].dims}"
            )

    times = ds["time"].values.astype("datetime64[ns]")

    if not np.all(np.diff(times.astype(np.int64)) > 0):
        raise ValueError(f"{year}: time coordinate is not strictly increasing")

    day_labels = times.astype("datetime64[D]")
    unique_days, records_per_day = np.unique(
        day_labels, return_counts=True
    )

    if len(unique_days) != EXPECTED_DAYS:
        raise ValueError(f"{year}: expected 30 unique calendar days")

    expected_days = np.arange(
        np.datetime64(f"{year}-07-15"),
        np.datetime64(f"{year}-08-14"),
        dtype="datetime64[D]",
    )

    if not np.array_equal(unique_days, expected_days):
        raise ValueError(
            f"{year}: calendar window must be July 15 through August 13"
        )

    if not np.all(records_per_day == HOURS_PER_DAY):
        raise ValueError(f"{year}: some days do not contain 24 records")

    if np.isinf(ds.to_array().values).any():
        raise ValueError(f"{year}: infinite values detected")

    return day_labels, unique_days


def aggregate_year(year):
    input_path = INPUT_DIR / f"CERES_{year}_established_monsoon.nc"
    output_path = OUTPUT_DIR / (
        f"CERES_{year}_established_monsoon_daily.nc"
    )
    report_path = REPORT_DIR / (
        f"established_monsoon_daily_aggregation_{year}.csv"
    )

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    if output_path.exists() or report_path.exists():
        raise FileExistsError(
            f"Output or report already exists for {year}. "
            "Refusing to overwrite."
        )

    print(f"\nProcessing {year}...", flush=True)

    with xr.open_dataset(input_path) as source:
        day_labels, daily_dates = validate_input(source, year)

        output_variables = {}
        report_rows = []

        for variable in source.data_vars:
            daily_source = source[variable].assign_coords(
                day=("time", day_labels)
            )

            grouped = daily_source.groupby("day")

            valid_count = grouped.count(dim="time")
            daily_mean = grouped.mean(
                dim="time",
                skipna=True
            )

            daily_mean = daily_mean.where(
                valid_count >= MIN_VALID_HOURS
            )

            daily_mean = daily_mean.rename({"day": "time"})
            valid_count = valid_count.rename({"day": "time"})

            daily_mean.attrs = dict(source[variable].attrs)
            daily_mean.attrs["temporal_aggregation"] = (
                "Arithmetic mean of valid hourly observations"
            )
            daily_mean.attrs["minimum_valid_hours"] = MIN_VALID_HOURS
            daily_mean.attrs["maximum_hours_per_day"] = HOURS_PER_DAY

            count_name = f"{variable}_valid_hour_count"

            valid_count.attrs = {
                "long_name": f"Valid hourly observation count for {variable}",
                "units": "hours",
                "valid_min": 0,
                "valid_max": HOURS_PER_DAY,
            }

            output_variables[variable] = daily_mean
            output_variables[count_name] = valid_count.astype(np.uint8)

            count_values = valid_count.values

            total = count_values.size
            retained_18 = int(np.sum(count_values >= 18))
            retained_24 = int(np.sum(count_values == 24))

            report_rows.append({
                "year": year,
                "variable": variable,
                "total_daily_grid_cells": total,
                "retained_at_18_hours": retained_18,
                "retained_at_18_hours_pct": (
                    100.0 * retained_18 / total
                ),
                "retained_at_24_hours": retained_24,
                "retained_at_24_hours_pct": (
                    100.0 * retained_24 / total
                ),
                "mean_valid_hours": float(np.mean(count_values)),
            })

            print(f"  Aggregated {variable}", flush=True)

        output = xr.Dataset(
            output_variables,
            coords={
                "time": daily_dates,
                "lat": source["lat"].values,
                "lon": source["lon"].values,
            }
        )

        output.attrs = {
            "title": "CERES Established Monsoon Daily Aggregated Data",
            "source_product": "CERES SYN1deg Edition 4.2 (Edition 4B)",
            "source_doi": (
                "10.5067/Terra-Aqua-NOAA20/CERES/SYN1deg1Hour_L3.004B"
            ),
            "study_season": "Established Monsoon",
            "study_year": year,
            "daily_aggregation": "Arithmetic mean of valid hourly values",
            "minimum_valid_hours": MIN_VALID_HOURS,
            "maximum_hours_per_day": HOURS_PER_DAY,
            "sensitivity_threshold": "24 valid hours",
            "missing_value_policy": "Preserve as NaN; no imputation",
            "source_hourly_records_per_day": HOURS_PER_DAY,
            "spatial_domain": "6N-38N, 68E-98E",
            "grid_resolution": "1 degree",
            "processing_note": (
                "Daily values with fewer than 18 valid hourly observations "
                "are masked. Valid-hour counts are stored separately."
            ),
        }

        encoding = {}

        for name in output.data_vars:
            if name.endswith("_valid_hour_count"):
                encoding[name] = {
                    "dtype": "uint8",
                    "zlib": True,
                    "complevel": 4,
                }
            else:
                encoding[name] = {
                    "dtype": "float32",
                    "_FillValue": np.float32(np.nan),
                    "zlib": True,
                    "complevel": 4,
                    "shuffle": True,
                }

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        temporary_output = output_path.with_name(
            output_path.stem + ".tmp.nc"
        )

        try:
            output.to_netcdf(
                temporary_output,
                engine="netcdf4",
                encoding=encoding
            )
            temporary_output.rename(output_path)
        finally:
            if temporary_output.exists():
                temporary_output.unlink()

    try:
        with report_path.open(
            "w", newline="", encoding="utf-8"
        ) as report_file:
            writer = csv.DictWriter(
                report_file,
                fieldnames=list(report_rows[0].keys())
            )
            writer.writeheader()
            writer.writerows(report_rows)
    except Exception:
        if output_path.exists():
            output_path.unlink()
        raise

    print(f"\nCreated: {output_path}")
    print(f"Created: {report_path}")
    print(f"Variables processed: {len(report_rows)}")


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate established-monsoon CERES hourly data."
    )

    parser.add_argument("--start-year", type=int, default=START_YEAR)
    parser.add_argument("--end-year", type=int, default=END_YEAR)

    args = parser.parse_args()

    if not START_YEAR <= args.start_year <= END_YEAR:
        parser.error("Invalid start year")

    if not START_YEAR <= args.end_year <= END_YEAR:
        parser.error("Invalid end year")

    if args.start_year > args.end_year:
        parser.error("Start year must not exceed end year")

    years = range(args.start_year, args.end_year + 1)

    for year in years:
        aggregate_year(year)

    print("\nDaily aggregation completed successfully.")


if __name__ == "__main__":
    main()
