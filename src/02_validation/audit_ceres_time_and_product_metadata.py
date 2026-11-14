
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]

SEASON_ROOT = ROOT / "data" / "interim" / "ceres_seasonal"
MISSINGNESS_REPORT = (
    ROOT / "reports" / "data_quality" /
    "ceres_missingness_by_dataset.csv"
)
OUTPUT = ROOT / "reports" / "data_quality"

SEASONS = {
    "pre_monsoon",
    "established_monsoon",
    "post_monsoon",
}


def extract_year(path):
    match = re.search(r"(?:19|20)\d{2}", path.stem)
    if not match:
        raise ValueError(f"Cannot identify year: {path}")
    return int(match.group())


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    candidates = pd.read_csv(MISSINGNESS_REPORT)
    variables = sorted(candidates["variable"].unique())

    metadata_records = []
    hourly_records = []
    timestamp_records = []

    files = []

    for season in sorted(SEASONS):
        season_dir = SEASON_ROOT / season

        if not season_dir.exists():
            raise FileNotFoundError(season_dir)

        files.extend(
            (season, path)
            for path in sorted(season_dir.rglob("*.nc"))
        )

    if len(files) != 36:
        raise ValueError(
            f"Expected 36 seasonal files, found {len(files)}"
        )

    for season, path in files:
        year = extract_year(path)

        print(f"Auditing {season} {year}: {path.name}")

        with xr.open_dataset(
            path,
            decode_times=True,
            mask_and_scale=True
        ) as ds:

            if "time" not in ds.coords:
                raise ValueError(f"No time coordinate: {path}")

            times = pd.DatetimeIndex(
                pd.to_datetime(ds["time"].values)
            )

            if len(times) != 720:
                raise ValueError(
                    f"Unexpected time count in {path}: {len(times)}"
                )

            actual_hours = times.hour.to_numpy()
            index_hours = np.arange(len(times)) % 24

            timestamp_records.append({
                "season": season,
                "year": year,
                "file": path.name,
                "first_timestamp": str(times[0]),
                "last_timestamp": str(times[-1]),
                "time_count": len(times),
                "unique_utc_hours": sorted(
                    times.hour.unique().tolist()
                ),
                "index_hour_match_fraction": float(
                    np.mean(actual_hours == index_hours)
                ),
                "timestamps_monotonic": bool(
                    times.is_monotonic_increasing
                ),
                "duplicate_timestamps": int(
                    times.duplicated().sum()
                ),
            })

            attrs = {
                str(key): str(value)
                for key, value in ds.attrs.items()
            }

            metadata_records.append({
                "season": season,
                "year": year,
                "file": path.name,
                "global_attributes_json": json.dumps(
                    attrs,
                    ensure_ascii=False
                ),
            })

            for variable in variables:
                if variable not in ds:
                    raise KeyError(
                        f"{variable} missing from {path.name}"
                    )

                values = ds[variable].values

                if values.shape[0] != len(times):
                    raise ValueError(
                        f"Unexpected dimensions for {variable}"
                    )

                for hour in range(24):
                    mask = actual_hours == hour

                    subset = values[mask]

                    total = subset.size
                    finite = int(np.isfinite(subset).sum())
                    missing = total - finite

                    hourly_records.append({
                        "season": season,
                        "year": year,
                        "variable": variable,
                        "utc_hour": hour,
                        "total_observations": total,
                        "missing_observations": missing,
                        "finite_observations": finite,
                        "missing_fraction": (
                            missing / total if total else np.nan
                        ),
                    })

    metadata_df = pd.DataFrame(metadata_records)
    timestamp_df = pd.DataFrame(timestamp_records)
    hourly_df = pd.DataFrame(hourly_records)

    pooled_hourly = (
        hourly_df.groupby(
            ["season", "variable", "utc_hour"],
            as_index=False
        )
        .agg(
            total_observations=("total_observations", "sum"),
            missing_observations=("missing_observations", "sum"),
            finite_observations=("finite_observations", "sum"),
        )
    )

    pooled_hourly["missing_fraction"] = (
        pooled_hourly["missing_observations"]
        / pooled_hourly["total_observations"]
    )

    metadata_df.to_csv(
        OUTPUT / "ceres_product_metadata_by_dataset.csv",
        index=False
    )

    timestamp_df.to_csv(
        OUTPUT / "ceres_timestamp_audit.csv",
        index=False
    )

    hourly_df.to_csv(
        OUTPUT / "ceres_actual_utc_hour_missingness_by_dataset.csv",
        index=False
    )

    pooled_hourly.to_csv(
        OUTPUT / "ceres_actual_utc_hour_missingness_by_season.csv",
        index=False
    )

    summary = {
        "files_checked": len(files),
        "candidate_variables": len(variables),
        "timestamp_monotonic_files": int(
            timestamp_df["timestamps_monotonic"].sum()
        ),
        "files_with_duplicate_timestamps": int(
            (timestamp_df["duplicate_timestamps"] > 0).sum()
        ),
        "files_with_perfect_index_hour_match": int(
            (
                timestamp_df["index_hour_match_fraction"] == 1
            ).sum()
        ),
        "mean_index_hour_match_fraction": float(
            timestamp_df["index_hour_match_fraction"].mean()
        ),
        "note": (
            "UTC-hour missingness is calculated using decoded "
            "NetCDF timestamps. Global metadata is retained "
            "as text for product/version/source inspection."
        ),
    }

    with open(
        OUTPUT / "ceres_time_metadata_audit_summary.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(summary, file, indent=2)

    print("\nAUDIT COMPLETE")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
