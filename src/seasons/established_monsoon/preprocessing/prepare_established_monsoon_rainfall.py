from pathlib import Path
import csv
import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = ROOT / "data/raw/imd_rainfall/IMD_Rainfall"
CERES_DIR = ROOT / "data/processed/ceres_daily/established_monsoon"
OUTPUT_DIR = ROOT / "data/processed/rainfall_daily/established_monsoon"
REPORT_DIR = ROOT / "reports/preprocessing"

START_MONTH_DAY = "07-15"
END_MONTH_DAY = "08-13"
EXPECTED_YEARS = range(2010, 2022)
EXPECTED_LAT_COUNT = 32
EXPECTED_LON_COUNT = 30


def find_coord(ds, candidates):
    lookup = {name.lower(): name for name in ds.coords}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    raise ValueError(f"Coordinate not found: {candidates}")


def check_no_overwrite(paths):
    existing = [str(p) for p in paths if p.exists()]
    if existing:
        raise FileExistsError(
            "Refusing to overwrite existing files:\n" + "\n".join(existing)
        )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    prepared = {}
    daily_rows = []
    yearly_masks = {}
    yearly_summary = []

    target_files = []

    for year in EXPECTED_YEARS:
        target_files.extend([
            OUTPUT_DIR / f"IMD_{year}_established_monsoon_daily.nc",
            REPORT_DIR / f"imd_rainfall_daily_{year}.csv"
        ])

    target_files.append(
        REPORT_DIR / "imd_established_monsoon_preparation_validation.md"
    )
    check_no_overwrite(target_files)

    print("Starting IMD rainfall preparation validation")

    for year in EXPECTED_YEARS:
        source_path = INPUT_DIR / f"RFone_imd_rf_1x1_{year}.nc"
        ceres_path = CERES_DIR / f"CERES_{year}_established_monsoon_daily.nc"

        if not source_path.exists() or not ceres_path.exists():
            raise FileNotFoundError(
                f"Missing source or CERES file for {year}"
            )

        print(f"Validating {year}")

        with xr.open_dataset(source_path) as imd, \
             xr.open_dataset(ceres_path) as ceres:

            if "RAINFALL" not in imd.data_vars:
                raise ValueError(f"{year}: RAINFALL variable missing")

            lat_name = find_coord(imd, ["LATITUDE", "latitude", "lat"])
            lon_name = find_coord(imd, ["LONGITUDE", "longitude", "lon"])
            time_name = find_coord(imd, ["TIME", "time"])

            ceres_lat_name = find_coord(
                ceres, ["latitude", "lat", "LATITUDE"]
            )
            ceres_lon_name = find_coord(
                ceres, ["longitude", "lon", "LONGITUDE"]
            )
            ceres_time_name = find_coord(ceres, ["time", "TIME"])

            target_lat = np.asarray(
                ceres[ceres_lat_name].values
            )
            target_lon = np.asarray(
                ceres[ceres_lon_name].values
            )

            if len(target_lat) != EXPECTED_LAT_COUNT:
                raise ValueError(f"{year}: unexpected CERES latitude size")

            if len(target_lon) != EXPECTED_LON_COUNT:
                raise ValueError(f"{year}: unexpected CERES longitude size")

            source_lat = np.asarray(imd[lat_name].values)
            source_lon = np.asarray(imd[lon_name].values)

            if not np.isin(target_lat, source_lat).all():
                raise ValueError(f"{year}: latitude coordinate mismatch")

            if not np.isin(target_lon, source_lon).all():
                raise ValueError(f"{year}: longitude coordinate mismatch")

            source_dates = np.asarray(
                imd[time_name].values
            ).astype("datetime64[D]")

            expected_full_dates = np.arange(
                np.datetime64(f"{year}-01-01"),
                np.datetime64(f"{year + 1}-01-01"),
                dtype="datetime64[D]"
            )

            if not np.array_equal(source_dates, expected_full_dates):
                raise ValueError(f"{year}: incomplete or invalid annual dates")

            dates = np.arange(
                np.datetime64(f"{year}-{START_MONTH_DAY}"),
                np.datetime64(f"{year}-08-14"),
                dtype="datetime64[D]"
            )

            ceres_dates = np.asarray(
                ceres[ceres_time_name].values
            ).astype("datetime64[D]")

            if not np.array_equal(ceres_dates, dates):
                raise ValueError(f"{year}: CERES daily dates do not match")

            selected = imd["RAINFALL"].sel({
                lat_name: target_lat,
                lon_name: target_lon
            }).sel({
                time_name: dates
            })

            values = np.asarray(
                selected.transpose(time_name, lat_name, lon_name).values,
                dtype=np.float32
            )

            if values.shape != (30, 32, 30):
                raise ValueError(
                    f"{year}: unexpected rainfall shape {values.shape}"
                )

            if np.isinf(values).any():
                raise ValueError(f"{year}: infinite rainfall values found")

            finite = np.isfinite(values)

            if ((values < 0) & finite).any():
                raise ValueError(f"{year}: negative rainfall values found")

            if selected.attrs.get("units", "").strip().lower() != "mm":
                raise ValueError(
                    f"{year}: expected rainfall units mm, "
                    f"found {selected.attrs.get('units')}"
                )

            valid_per_day = finite.sum(axis=(1, 2))
            always_valid = finite.all(axis=0)
            always_missing = (~finite).all(axis=0)
            intermittent = ~(always_valid | always_missing)

            yearly_masks[year] = always_valid.copy()

            for index, date in enumerate(dates):
                daily_values = values[index]
                daily_finite = np.isfinite(daily_values)

                valid_values = daily_values[daily_finite]

                daily_rows.append({
                    "year": year,
                    "date": str(date),
                    "valid_cells": int(daily_finite.sum()),
                    "missing_cells": int((~daily_finite).sum()),
                    "mean_rainfall_mm": (
                        float(valid_values.mean())
                        if valid_values.size else ""
                    ),
                    "minimum_rainfall_mm": (
                        float(valid_values.min())
                        if valid_values.size else ""
                    ),
                    "maximum_rainfall_mm": (
                        float(valid_values.max())
                        if valid_values.size else ""
                    )
                })

            yearly_summary.append({
                "year": year,
                "records": len(dates),
                "valid_observations": int(finite.sum()),
                "valid_cells_each_day_min": int(valid_per_day.min()),
                "valid_cells_each_day_max": int(valid_per_day.max()),
                "always_valid_cells": int(always_valid.sum()),
                "always_missing_cells": int(always_missing.sum()),
                "intermittent_cells": int(intermittent.sum())
            })

            output = xr.Dataset(
                {
                    "RAINFALL": (
                        ("time", "latitude", "longitude"),
                        values
                    )
                },
                coords={
                    "time": dates,
                    "latitude": target_lat,
                    "longitude": target_lon
                },
                attrs={
                    "title": "IMD daily rainfall - established monsoon",
                    "source": "IMD 1-degree daily gridded rainfall",
                    "study_year": year,
                    "study_period": "July 15 to August 13",
                    "units": "mm",
                    "spatial_alignment": (
                        "Exact coordinate selection using CERES daily grid"
                    ),
                    "missing_data_policy": (
                        "Missing observations preserved; not replaced by zero"
                    ),
                    "processing": (
                        "Date and coordinate selection only; "
                        "no temporal averaging or spatial interpolation"
                    )
                }
            )

            output["RAINFALL"].attrs.update({
                "long_name": "Daily rainfall",
                "units": "mm"
            })

            prepared[year] = output

    # Compare the spatial masks across all years.
    mask_stack = np.stack([
        yearly_masks[year] for year in EXPECTED_YEARS
    ])

    stable_valid = mask_stack.all(axis=0)
    stable_missing = (~mask_stack).all(axis=0)
    variable_mask = ~(stable_valid | stable_missing)

    print("\nCross-year mask comparison")
    print("Valid in every year:", int(stable_valid.sum()))
    print("Missing in every year:", int(stable_missing.sum()))
    print("Changes between years:", int(variable_mask.sum()))

    # Write NetCDF files only after all years have passed validation.
    temporary_files = []

    try:
        for year, dataset in prepared.items():
            final_path = (
                OUTPUT_DIR /
                f"IMD_{year}_established_monsoon_daily.nc"
            )
            temp_path = final_path.with_name(final_path.name + ".tmp")

            dataset.to_netcdf(
                temp_path,
                engine="netcdf4",
                encoding={
                    "RAINFALL": {
                        "zlib": True,
                        "complevel": 4,
                        "dtype": "float32",
                        "_FillValue": np.float32(-999.0)
                    }
                }
            )
            temporary_files.append((temp_path, final_path))

        for temp_path, final_path in temporary_files:
            temp_path.replace(final_path)

    except Exception:
        for temp_path, _ in temporary_files:
            if temp_path.exists():
                temp_path.unlink()
        raise

    # Write one daily coverage CSV per year.
    for year in EXPECTED_YEARS:
        report_path = REPORT_DIR / f"imd_rainfall_daily_{year}.csv"

        with report_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "year", "date", "valid_cells", "missing_cells",
                    "mean_rainfall_mm", "minimum_rainfall_mm",
                    "maximum_rainfall_mm"
                ]
            )
            writer.writeheader()
            writer.writerows([
                row for row in daily_rows if row["year"] == year
            ])

    report_path = (
        REPORT_DIR /
        "imd_established_monsoon_preparation_validation.md"
    )

    total_valid = sum(
        row["valid_observations"] for row in yearly_summary
    )

    lines = [
        "# IMD Established Monsoon Rainfall Preparation Report",
        "",
        "## Processing scope",
        "",
        "- Years: 2010–2021",
        "- Window: July 15–August 13, inclusive",
        "- Daily records: 30 per year",
        "- Spatial grid: 32 × 30",
        "- Rainfall variable: RAINFALL",
        "- Units: mm",
        "- Spatial method: exact coordinate selection",
        "- Temporal method: exact date selection",
        "- No interpolation or temporal averaging performed",
        "",
        "## Annual validation",
        "",
        "| Year | Records | Valid observations | Always valid cells | Always missing cells | Intermittent cells |",
        "|---:|---:|---:|---:|---:|---:|"
    ]

    for row in yearly_summary:
        lines.append(
            f"| {row['year']} | {row['records']} | "
            f"{row['valid_observations']} | "
            f"{row['always_valid_cells']} | "
            f"{row['always_missing_cells']} | "
            f"{row['intermittent_cells']} |"
        )

    lines.extend([
        "",
        "## Cross-year spatial mask",
        "",
        f"- Cells valid throughout every year: {int(stable_valid.sum())}",
        f"- Cells missing throughout every year: {int(stable_missing.sum())}",
        f"- Cells whose yearly validity changes: {int(variable_mask.sum())}",
        "",
        "## Collection summary",
        "",
        f"- Years processed: {len(prepared)}",
        f"- Daily records: {len(prepared) * 30}",
        f"- Valid rainfall observations: {total_valid}",
        f"- NetCDF outputs: {len(prepared)}",
        f"- Daily CSV reports: {len(prepared)}",
        "",
        "## Scientific handling",
        "",
        "- Original daily rainfall values were retained in millimetres.",
        "- Missing observations were preserved as missing.",
        "- Missing observations were not converted to zero.",
        "- No spatial interpolation was applied.",
        "- No additional daily aggregation was performed.",
        "- Rainfall remains independent of clustering inputs.",
        "",
        "**Status: rainfall daily extraction and validation completed.**"
    ])

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for dataset in prepared.values():
        dataset.close()

    print("\nPROCESSING COMPLETED")
    print("Years:", len(prepared))
    print("Daily records:", len(prepared) * 30)
    print("Valid observations:", total_valid)
    print("NetCDF outputs:", OUTPUT_DIR)
    print("Validation report:", report_path)


if __name__ == "__main__":
    main()
