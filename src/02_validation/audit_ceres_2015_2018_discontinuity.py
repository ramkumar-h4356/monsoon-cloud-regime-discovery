from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]
SEASON_ROOT = ROOT / "data" / "interim" / "ceres_seasonal"
FEATURE_REPORT = ROOT / "reports" / "data_quality" / "ceres_feature_screening_summary.csv"
OUTPUT = ROOT / "reports" / "data_quality"

YEARS = {2015, 2016, 2017, 2018}
SEASONS = {"pre_monsoon", "established_monsoon", "post_monsoon"}
LON_BINS = [68, 78, 88, 98]
LON_LABELS = ["68-78E", "78-88E", "88-98E"]
LAT_BINS = [6, 16, 26, 38]
LAT_LABELS = ["6-16N", "16-26N", "26-38N"]


def get_year(path):
    match = re.search(r"(?:19|20)\d{2}", path.stem)
    if not match:
        raise ValueError(f"Cannot determine year from {path.name}")
    return int(match.group())


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    feature_table = pd.read_csv(FEATURE_REPORT)
    candidates = feature_table[
        feature_table["status"].eq("ELIGIBLE_CANDIDATE")
    ].copy()

    variables = candidates["variable"].tolist()
    layer_lookup = dict(zip(candidates["variable"], candidates["vertical_layer"]))

    selected_files = []
    for season in sorted(SEASONS):
        season_dir = SEASON_ROOT / season
        if not season_dir.exists():
            raise FileNotFoundError(season_dir)

        for path in sorted(season_dir.rglob("*.nc")):
            year = get_year(path)
            if year in YEARS:
                selected_files.append((season, year, path))

    expected = len(YEARS) * len(SEASONS)
    if len(selected_files) != expected:
        raise RuntimeError(
            f"Expected {expected} files for 2015-2018; found {len(selected_files)}"
        )

    annual_rows = []
    hourly_rows = []
    spatial_rows = []
    band_rows = []
    area_rows = []
    metadata_rows = []

    for season, year, path in selected_files:
        print(f"Processing {year} {season}: {path.name}")

        with xr.open_dataset(
            path, decode_times=True, mask_and_scale=True
        ) as ds:
            required_coords = {"time", "lat", "lon"}
            if not required_coords.issubset(ds.coords):
                raise ValueError(
                    f"{path.name} must have time, lat and lon coordinates"
                )

            times = pd.DatetimeIndex(pd.to_datetime(ds["time"].values))
            if len(times) != 720 or not times.is_monotonic_increasing:
                raise ValueError(f"Unexpected time coordinate in {path.name}")

            lat = np.asarray(ds["lat"].values)
            lon = np.asarray(ds["lon"].values)
            if len(lat) != 32 or len(lon) != 30:
                raise ValueError(f"Unexpected spatial grid in {path.name}")

            lat_grid, lon_grid = np.meshgrid(lat, lon, indexing="ij")
            lon_band = pd.cut(
                lon_grid.ravel(), bins=LON_BINS,
                labels=LON_LABELS, right=False, include_lowest=True
            )
            lat_band = pd.cut(
                lat_grid.ravel(), bins=LAT_BINS,
                labels=LAT_LABELS, right=False, include_lowest=True
            )

            attrs = {str(k): str(v) for k, v in ds.attrs.items()}
            metadata_rows.append({
                "year": year,
                "season": season,
                "file": path.name,
                "global_attributes_json": json.dumps(attrs, ensure_ascii=False)
            })

            utc_hours = times.hour.to_numpy()

            arrays = {}
            for variable in variables:
                if variable not in ds:
                    raise KeyError(f"{variable} missing from {path.name}")
                values = np.asarray(ds[variable].values)
                if values.shape != (720, 32, 30):
                    raise ValueError(
                        f"{variable} has unexpected shape {values.shape} in {path.name}"
                    )
                arrays[variable] = values

                finite = np.isfinite(values)
                missing = ~finite
                n_total = int(values.size)
                n_finite = int(finite.sum())
                n_missing = int(missing.sum())

                annual_rows.append({
                    "year": year,
                    "season": season,
                    "variable": variable,
                    "total_observations": n_total,
                    "finite_observations": n_finite,
                    "missing_observations": n_missing,
                    "missing_fraction": n_missing / n_total,
                    "zero_observations": int((values[finite] == 0).sum()),
                })

                for hour in range(24):
                    hour_mask = utc_hours == hour
                    hour_values = values[hour_mask]
                    hour_missing = int((~np.isfinite(hour_values)).sum())
                    hour_total = int(hour_values.size)
                    hourly_rows.append({
                        "year": year,
                        "season": season,
                        "variable": variable,
                        "utc_hour": hour,
                        "total_observations": hour_total,
                        "missing_observations": hour_missing,
                        "missing_fraction": (
                            hour_missing / hour_total if hour_total else np.nan
                        ),
                    })

                cell_missing = missing.mean(axis=0).ravel()
                for cell, fraction in enumerate(cell_missing):
                    spatial_rows.append({
                        "year": year,
                        "season": season,
                        "variable": variable,
                        "latitude": float(lat_grid.ravel()[cell]),
                        "longitude": float(lon_grid.ravel()[cell]),
                        "missing_fraction": float(fraction),
                    })

                spatial_frame = pd.DataFrame({
                    "missing_fraction": cell_missing,
                    "longitude_band": lon_band.astype(str),
                    "latitude_band": lat_band.astype(str),
                })
                grouped = (
                    spatial_frame.groupby(
                        ["longitude_band", "latitude_band"],
                        observed=False
                    )["missing_fraction"]
                    .agg(["mean", "median", "min", "max", "count"])
                    .reset_index()
                )
                for record in grouped.to_dict("records"):
                    band_rows.append({
                        "year": year,
                        "season": season,
                        "variable": variable,
                        **record,
                    })

                layer = layer_lookup.get(variable)
                area_variable = f"cldarea_{layer}_1h" if layer else None

                if (
                    area_variable
                    and area_variable in arrays
                    and not variable.startswith("cldarea_")
                ):
                    area = arrays[area_variable]
                    area_finite = np.isfinite(area)
                    zero_area = area_finite & (area == 0)
                    positive_area = area_finite & (area > 0)

                    for label, condition in [
                        ("area_zero", zero_area),
                        ("area_positive", positive_area),
                        ("area_missing", ~area_finite),
                    ]:
                        count = int(condition.sum())
                        missing_count = int((missing & condition).sum())
                        area_rows.append({
                            "year": year,
                            "season": season,
                            "variable": variable,
                            "matching_area_variable": area_variable,
                            "area_condition": label,
                            "observations": count,
                            "missing_observations": missing_count,
                            "missing_fraction": (
                                missing_count / count if count else np.nan
                            ),
                        })

    annual = pd.DataFrame(annual_rows)
    hourly = pd.DataFrame(hourly_rows)
    spatial = pd.DataFrame(spatial_rows)
    bands = pd.DataFrame(band_rows)
    area = pd.DataFrame(area_rows)
    metadata = pd.DataFrame(metadata_rows)

    # Explicit year-to-year contrasts, especially 2016 versus 2017.
    pivot = annual.pivot_table(
        index=["season", "variable"],
        columns="year",
        values="missing_fraction",
        aggfunc="first"
    ).reset_index()

    for year in sorted(YEARS):
        if year not in pivot.columns:
            raise RuntimeError(f"Missing annual result for {year}")

    pivot["delta_2017_vs_2016"] = pivot[2017] - pivot[2016]
    pivot["delta_2018_vs_2017"] = pivot[2018] - pivot[2017]
    pivot["delta_2016_vs_2015"] = pivot[2016] - pivot[2015]

    annual.to_csv(OUTPUT / "ceres_2015_2018_missingness_by_dataset.csv", index=False)
    pivot.to_csv(OUTPUT / "ceres_2015_2018_missingness_year_contrasts.csv", index=False)
    hourly.to_csv(OUTPUT / "ceres_2015_2018_missingness_by_utc_hour.csv", index=False)
    spatial.to_csv(OUTPUT / "ceres_2015_2018_spatial_missingness_by_cell.csv", index=False)
    bands.to_csv(OUTPUT / "ceres_2015_2018_spatial_missingness_by_region.csv", index=False)
    area.to_csv(OUTPUT / "ceres_2015_2018_cloud_area_conditioned_missingness.csv", index=False)
    metadata.to_csv(OUTPUT / "ceres_2015_2018_global_metadata.csv", index=False)

    # Compact summary for quality-control and Git documentation.
    summary = {
        "years": sorted(YEARS),
        "seasons": sorted(SEASONS),
        "files_processed": len(selected_files),
        "candidate_variables": len(variables),
        "spatial_grid": [32, 30],
        "records": {
            "dataset_variable": len(annual),
            "utc_hour": len(hourly),
            "spatial_cell": len(spatial),
            "spatial_region": len(bands),
            "cloud_area_conditioned": len(area),
        },
        "important_interpretation": (
            "The 2016-to-2017 difference is a diagnostic discontinuity, "
            "not proof of a satellite or retrieval cause. Global attributes "
            "may not identify the GEO source contributing to each grid cell."
        ),
    }

    with open(
        OUTPUT / "ceres_2015_2018_discontinuity_audit_summary.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(summary, f, indent=2)

    print("\nAUDIT COMPLETE")
    print(json.dumps(summary, indent=2))
    print(f"\nReports saved in: {OUTPUT}")


if __name__ == "__main__":
    main()
