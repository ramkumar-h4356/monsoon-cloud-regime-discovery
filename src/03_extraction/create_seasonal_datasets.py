
from pathlib import Path
from datetime import date, timedelta
import argparse
import csv
import gzip
import re
import shutil
import tempfile

import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = ROOT / "raw_data" / "CERES"
OLD_CROPPED_DIR = ROOT / "data" / "interim" / "ceres_extracted"
OUTPUT_DIR = ROOT / "data" / "interim" / "ceres_seasonal"
TEMP_DIR = ROOT / "data" / "interim" / "_ceres_temp"

SOUTH, NORTH = 6.0, 38.0
WEST, EAST = 68.0, 98.0

YEARS = range(2010, 2022)

SEASONS = {
    "pre_monsoon": (4, 15, 5, 14),
    "established_monsoon": (7, 15, 8, 13),
    "post_monsoon": (10, 15, 11, 13),
}


def archive_dates(path):
    match = re.search(r"(\d{8})-(\d{8})", path.name)

    if not match:
        return None

    start = date(
        int(match.group(1)[:4]),
        int(match.group(1)[4:6]),
        int(match.group(1)[6:8])
    )

    end = date(
        int(match.group(2)[:4]),
        int(match.group(2)[4:6]),
        int(match.group(2)[6:8])
    )

    return start, end


def get_window(year, season):
    sm, sd, em, ed = SEASONS[season]

    start = date(year, sm, sd)
    end_exclusive = date(year, em, ed) + timedelta(days=1)

    return start, end_exclusive


def get_compression_encoding(ds):
    encoding = {}

    for name, variable in ds.data_vars.items():
        if variable.dtype.kind in "biufc":
            encoding[name] = {
                "zlib": True,
                "complevel": 4
            }

    return encoding


def extract_from_file(path, start, end_exclusive):
    temporary_directory = None

    try:
        source_path = path

        if path.suffix == ".gz":
            temporary_directory = tempfile.TemporaryDirectory(
                prefix="ceres_",
                dir=TEMP_DIR
            )

            source_path = Path(temporary_directory.name) / path.stem

            with gzip.open(path, "rb") as source:
                with open(source_path, "wb") as destination:
                    shutil.copyfileobj(source, destination)

        with xr.open_dataset(source_path, engine="netcdf4") as ds:

            required = {"time", "lat", "lon"}

            if not required.issubset(
                set(ds.coords) | set(ds.variables)
            ):
                raise ValueError(
                    f"Required coordinates missing in {path.name}"
                )

            times = ds["time"].values.astype("datetime64[ns]")

            start_np = np.datetime64(start.isoformat())
            end_np = np.datetime64(end_exclusive.isoformat())

            time_indices = np.flatnonzero(
                (times >= start_np) & (times < end_np)
            )

            lat_values = ds["lat"].values
            lon_values = ds["lon"].values

            lat_indices = np.flatnonzero(
                (lat_values >= SOUTH) & (lat_values <= NORTH)
            )

            lon_indices = np.flatnonzero(
                (lon_values >= WEST) & (lon_values <= EAST)
            )

            if len(time_indices) == 0:
                return None

            if len(lat_indices) == 0 or len(lon_indices) == 0:
                raise ValueError(
                    f"No spatial grid points inside domain: {path.name}"
                )

            subset = ds.isel(
                time=time_indices,
                lat=lat_indices,
                lon=lon_indices
            ).load()

        return subset

    finally:
        if temporary_directory is not None:
            temporary_directory.cleanup()


def find_legacy_source(start, end_exclusive, files):
    required_end = end_exclusive - timedelta(days=1)

    for path in files:
        dates = archive_dates(path)

        if dates is None:
            continue

        source_start, source_end = dates

        if source_start <= start and source_end >= required_end:
            return path

    raise FileNotFoundError(
        f"No existing cropped CERES file covers {start} to {required_end}"
    )


def find_post_monsoon_sources(start, end_exclusive, files):
    required_end = end_exclusive - timedelta(days=1)
    matches = []

    for path in files:
        dates = archive_dates(path)

        if dates is None:
            continue

        source_start, source_end = dates

        if source_start <= required_end and source_end >= start:
            matches.append(path)

    matches.sort(key=lambda p: archive_dates(p)[0])

    if not matches:
        raise FileNotFoundError(
            f"No original CERES archive covers {start} to {required_end}"
        )

    return matches


def validate_dataset(ds, year, season):
    start, end_exclusive = get_window(year, season)

    times = ds["time"].values.astype("datetime64[ns]")

    if len(times) != 720:
        raise ValueError(
            f"{year} {season}: expected 720 observations, "
            f"found {len(times)}"
        )

    if len(np.unique(times)) != len(times):
        raise ValueError(
            f"{year} {season}: duplicate timestamps detected"
        )

    if not np.all(times[:-1] <= times[1:]):
        raise ValueError(
            f"{year} {season}: timestamps are not sorted"
        )

    dates, counts = np.unique(
        times.astype("datetime64[D]"),
        return_counts=True
    )

    expected_days = (
        end_exclusive - start
    ).days

    if len(dates) != expected_days or not np.all(counts == 24):
        raise ValueError(
            f"{year} {season}: expected "
            f"{expected_days} days with 24 observations each"
        )

    if ds.sizes["lat"] != 32 or ds.sizes["lon"] != 30:
        raise ValueError(
            f"{year} {season}: unexpected spatial dimensions "
            f"{ds.sizes['lat']} x {ds.sizes['lon']}"
        )

    if float(ds.lat.min()) < SOUTH or float(ds.lat.max()) > NORTH:
        raise ValueError(
            f"{year} {season}: latitude outside study domain"
        )

    if float(ds.lon.min()) < WEST or float(ds.lon.max()) > EAST:
        raise ValueError(
            f"{year} {season}: longitude outside study domain"
        )


def build_seasonal_dataset(
    year,
    season,
    legacy_files,
    raw_files
):
    start, end_exclusive = get_window(year, season)

    if season in ("pre_monsoon", "established_monsoon"):

        source = find_legacy_source(
            start,
            end_exclusive,
            legacy_files
        )

        print(f"    Reading existing crop: {source.name}")

        result = extract_from_file(
            source,
            start,
            end_exclusive
        )

        if result is None:
            raise ValueError(
                f"No observations found in {source.name}"
            )

        sources = [source.name]

    else:

        source_files = find_post_monsoon_sources(
            start,
            end_exclusive,
            raw_files
        )

        parts = []

        for source in source_files:
            print(f"    Reading original archive: {source.name}")

            part = extract_from_file(
                source,
                start,
                end_exclusive
            )

            if part is not None:
                parts.append(part)

        if not parts:
            raise ValueError(
                f"No post-monsoon observations found for {year}"
            )

        result = xr.concat(
            parts,
            dim="time",
            data_vars="all",
            coords="minimal",
            compat="equals",
            join="exact"
        ).sortby("time")

        sources = [source.name for source in source_files]

    validate_dataset(result, year, season)

    return result, sources


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Recreate existing seasonal output files"
    )

    args = parser.parse_args()

    if not OLD_CROPPED_DIR.exists():
        raise FileNotFoundError(
            f"Existing cropped directory not found: {OLD_CROPPED_DIR}"
        )

    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"Raw CERES directory not found: {RAW_DIR}"
        )

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    legacy_files = sorted(
        OLD_CROPPED_DIR.rglob("*.nc")
    )

    raw_files = sorted(
        list(RAW_DIR.glob("*.nc")) +
        list(RAW_DIR.glob("*.nc.gz"))
    )

    if not legacy_files:
        raise FileNotFoundError(
            "No existing cropped NetCDF files found"
        )

    if not raw_files:
        raise FileNotFoundError(
            "No original CERES NetCDF archives found"
        )

    print("\nCERES SEASONAL DATASET GENERATION")
    print("---------------------------------")
    print("Existing cropped files:", len(legacy_files))
    print("Original raw files:", len(raw_files))
    print("Study years: 2010-2021")
    print("Spatial domain: 6-38 N, 68-98 E")

    manifest = []
    failures = []

    for season in SEASONS:

        season_dir = OUTPUT_DIR / season
        season_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nSEASON: {season}")

        for year in YEARS:

            filename = f"CERES_{year}_{season}.nc"
            output_path = season_dir / filename

            print(f"\n  {year}")

            if output_path.exists() and not args.overwrite:
                print("    Existing output found; validating it.")

                with xr.open_dataset(output_path) as existing:
                    validate_dataset(existing, year, season)

                    manifest.append({
                        "year": year,
                        "season": season,
                        "filename": str(output_path.relative_to(ROOT)),
                        "observations": existing.sizes["time"],
                        "lat": existing.sizes["lat"],
                        "lon": existing.sizes["lon"],
                        "size_mb": round(
                            output_path.stat().st_size / (1024 ** 2), 2
                        ),
                        "source_files": "Existing validated output",
                        "status": "VALIDATED_EXISTING"
                    })

                continue

            try:
                dataset, sources = build_seasonal_dataset(
                    year,
                    season,
                    legacy_files,
                    raw_files
                )

                temporary_output = output_path.with_name(
                    output_path.stem + ".tmp.nc"
                )

                dataset.to_netcdf(
                    temporary_output,
                    engine="netcdf4",
                    encoding=get_compression_encoding(dataset)
                )

                dataset.close()

                with xr.open_dataset(temporary_output) as check:
                    validate_dataset(check, year, season)

                temporary_output.replace(output_path)

                size_mb = round(
                    output_path.stat().st_size / (1024 ** 2), 2
                )

                manifest.append({
                    "year": year,
                    "season": season,
                    "filename": str(output_path.relative_to(ROOT)),
                    "observations": 720,
                    "lat": 32,
                    "lon": 30,
                    "size_mb": size_mb,
                    "source_files": "; ".join(sources),
                    "status": "SUCCESS"
                })

                print(f"    SUCCESS: {output_path.name}")
                print(f"    Size: {size_mb} MB")

            except Exception as error:
                failures.append({
                    "year": year,
                    "season": season,
                    "error": str(error)
                })

                print(f"    FAILED: {error}")

    manifest_path = OUTPUT_DIR / "seasonal_manifest.csv"

    with open(manifest_path, "w", newline="", encoding="utf-8") as file:
        columns = [
            "year",
            "season",
            "filename",
            "observations",
            "lat",
            "lon",
            "size_mb",
            "source_files",
            "status"
        ]

        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(manifest)

    print("\nFINAL REPORT")
    print("------------")
    print("Successful/validated:", len(manifest))
    print("Failed:", len(failures))
    print("Expected datasets:", 36)
    print("Manifest:", manifest_path)

    if failures:
        print("\nFAILURES:")

        for failure in failures:
            print(
                failure["year"],
                failure["season"],
                failure["error"]
            )

        raise SystemExit(
            "\nExtraction incomplete. Review failures before distribution."
        )

    if len(manifest) != 36:
        raise SystemExit(
            "\nExpected 36 validated datasets. Do not distribute yet."
        )

    print("\nALL 36 SEASONAL DATASETS VALIDATED.")


if __name__ == "__main__":
    main()
