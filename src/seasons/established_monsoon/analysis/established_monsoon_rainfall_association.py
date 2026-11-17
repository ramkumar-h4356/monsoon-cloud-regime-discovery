from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]

ASSIGNMENT_FILE = (
    ROOT / "results/tables/07_clustering/assignments/"
    "established_monsoon_fixed_cluster_assignments.csv"
)
RAINFALL_DIR = ROOT / "data/processed/rainfall_daily/established_monsoon"
OUTPUT_DIR = ROOT / "results/tables/07_clustering/rainfall_association"

MATCHED_FILE = OUTPUT_DIR / "established_monsoon_cloud_rainfall_matched.csv"
ANNUAL_FILE = OUTPUT_DIR / "established_monsoon_rainfall_by_year.csv"
PERIOD_FILE = OUTPUT_DIR / "established_monsoon_rainfall_by_period.csv"
POOLED_FILE = OUTPUT_DIR / "established_monsoon_rainfall_pooled.csv"

WET_DAY_THRESHOLD_MM = 2.5

KEYS = ["year", "date", "latitude", "longitude"]

MODELS = [
    ("baseline", 2, "baseline_k2"),
    ("log_sensitivity", 2, "log_k2"),
    ("log_sensitivity", 3, "log_k3"),
]

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def find_coord(ds, candidates):
    lookup = {name.lower(): name for name in ds.coords}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    raise ValueError(f"Coordinate not found: {candidates}")

def load_rainfall(assignments):
    rainfall_frames = []

    for year in range(2010, 2022):
        print(f"Loading rainfall: {year}")

        path = RAINFALL_DIR / f"IMD_{year}_established_monsoon_daily.nc"

        if not path.exists():
            raise FileNotFoundError(path)

        with xr.open_dataset(path) as ds:
            time_name = find_coord(ds, ["TIME", "time"])
            lat_name = find_coord(ds, ["LATITUDE", "latitude", "lat"])
            lon_name = find_coord(ds, ["LONGITUDE", "longitude", "lon"])

            rainfall_name = next(
                (name for name in ds.data_vars
                 if name.lower() == "rainfall"),
                None
            )

            require(rainfall_name is not None,
                    f"{year}: RAINFALL variable missing.")

            rainfall = ds[rainfall_name].transpose(
                time_name, lat_name, lon_name
            )

            values = np.asarray(rainfall.values, dtype=float)
            dates = pd.DatetimeIndex(
                pd.to_datetime(ds[time_name].values)
            ).normalize()

            latitudes = np.asarray(ds[lat_name].values, dtype=float)
            longitudes = np.asarray(ds[lon_name].values, dtype=float)

            require(values.shape == (30, 32, 30),
                    f"{year}: unexpected rainfall shape {values.shape}.")

            require(len(dates) == 30,
                    f"{year}: expected 30 rainfall dates.")

            require(np.isfinite(values).sum() > 0,
                    f"{year}: no valid rainfall observations.")

            valid = np.isfinite(values)

            if (values[valid] < 0).any():
                raise ValueError(
                    f"{year}: negative valid rainfall values detected."
                )

            day_idx, lat_idx, lon_idx = np.where(valid)

            frame = pd.DataFrame({
                "year": year,
                "date": dates[day_idx],
                "latitude": latitudes[lat_idx],
                "longitude": longitudes[lon_idx],
                "rainfall_mm": values[day_idx, lat_idx, lon_idx]
            })

            rainfall_frames.append(frame)

    return pd.concat(rainfall_frames, ignore_index=True)

def summarize(frame, group_columns):
    records = []

    for group_key, group in frame.groupby(
        group_columns, sort=True, observed=True
    ):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)

        rainfall = group["rainfall_mm"].to_numpy(dtype=float)

        record = dict(zip(group_columns, group_key))
        record.update({
            "observations": len(rainfall),
            "mean_mm": float(np.mean(rainfall)),
            "median_mm": float(np.median(rainfall)),
            "q25_mm": float(np.quantile(rainfall, 0.25)),
            "q75_mm": float(np.quantile(rainfall, 0.75)),
            "q90_mm": float(np.quantile(rainfall, 0.90)),
            "q95_mm": float(np.quantile(rainfall, 0.95)),
            "positive_rainfall_pct": float(
                np.mean(rainfall > 0) * 100
            ),
            "wet_day_pct": float(
                np.mean(rainfall >= WET_DAY_THRESHOLD_MM) * 100
            ),
        })

        records.append(record)

    return pd.DataFrame(records)

def main():
    for path in [
        MATCHED_FILE, ANNUAL_FILE, PERIOD_FILE, POOLED_FILE
    ]:
        require(not path.exists(),
                f"Refusing to overwrite existing output: {path}")

    assignments = pd.read_csv(ASSIGNMENT_FILE)

    assignments["date"] = pd.to_datetime(
        assignments["date"]
    ).dt.normalize()

    assignments["year"] = assignments["year"].astype(int)
    assignments["latitude"] = assignments["latitude"].astype(float)
    assignments["longitude"] = assignments["longitude"].astype(float)

    require(
        assignments.duplicated(KEYS).sum() == 0,
        "Duplicate assignment keys detected."
    )

    require(
        assignments[["baseline_k2", "log_k2", "log_k3"]]
        .notna().all().all(),
        "Missing cluster assignments detected."
    )

    rainfall = load_rainfall(assignments)

    require(
        rainfall.duplicated(KEYS).sum() == 0,
        "Duplicate rainfall observation keys detected."
    )

    matched = assignments.merge(
        rainfall,
        on=KEYS,
        how="inner",
        validate="one_to_one"
    )

    require(
        len(matched) == 110314,
        f"Matched count differs from alignment audit: {len(matched)}"
    )

    require(
        matched["rainfall_mm"].notna().all(),
        "Missing rainfall values found after inner join."
    )

    matched["period"] = np.where(
        matched["year"] <= 2016,
        "2010_2016",
        "2017_2021"
    )

    print("\n===== MATCHED DATA =====")
    print("Cloud assignments:", len(assignments))
    print("Valid rainfall records:", len(rainfall))
    print("Matched observations:", len(matched))
    print("Wet-day threshold:", WET_DAY_THRESHOLD_MM, "mm")

    annual_results = []
    period_results = []
    pooled_results = []

    for variant, k, label_column in MODELS:
        print(f"\n===== {variant}, K={k} =====")

        frame = matched[
            KEYS + ["rainfall_mm", "period", label_column]
        ].rename(columns={label_column: "cluster"})

        frame["variant"] = variant
        frame["k"] = k

        annual_results.append(
            summarize(
                frame,
                ["variant", "k", "year", "cluster"]
            )
        )

        period_results.append(
            summarize(
                frame,
                ["variant", "k", "period", "cluster"]
            )
        )

        pooled_results.append(
            summarize(
                frame,
                ["variant", "k", "cluster"]
            )
        )

    annual = pd.concat(annual_results, ignore_index=True)
    period = pd.concat(period_results, ignore_index=True)
    pooled = pd.concat(pooled_results, ignore_index=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    matched.to_csv(MATCHED_FILE, index=False, date_format="%Y-%m-%d")
    annual.to_csv(ANNUAL_FILE, index=False)
    period.to_csv(PERIOD_FILE, index=False)
    pooled.to_csv(POOLED_FILE, index=False)

    print("\n===== POOLED RAINFALL PROFILES =====")
    print(pooled.round(3).to_string(index=False))

    print("\n===== PERIOD RAINFALL PROFILES =====")
    print(period.round(3).to_string(index=False))

    print("\n===== ANNUAL SAMPLE COUNTS =====")
    print(
        annual[
            ["variant", "k", "year", "cluster", "observations"]
        ].to_string(index=False)
    )

    print("\n===== OUTPUTS =====")
    print("Matched observations:", MATCHED_FILE)
    print("Annual summaries:", ANNUAL_FILE)
    print("Period summaries:", PERIOD_FILE)
    print("Pooled summaries:", POOLED_FILE)

if __name__ == "__main__":
    main()
