from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans

ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT / "data/processed/clustering/established_monsoon"
TABLE_DIR = ROOT / "results/tables/07_clustering"

OUTPUT_DIR = TABLE_DIR / "assignments"
OUTPUT_FILE = OUTPUT_DIR / "established_monsoon_fixed_cluster_assignments.csv"

METADATA_FILE = DATA_DIR / "established_monsoon_group_B_metadata.csv"
BASELINE_FILE = DATA_DIR / "established_monsoon_group_B_baseline.npz"
LOG_FILE = DATA_DIR / "established_monsoon_group_B_log_sensitivity.npz"

ANNUAL_REFERENCE = (
    TABLE_DIR / "temporal_spatial_prevalence" /
    "established_monsoon_within_year_cluster_prevalence.csv"
)

PERIOD_REFERENCE = (
    TABLE_DIR / "period_comparison" /
    "established_monsoon_period_cluster_prevalence.csv"
)

SEED = 11

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def validate_prevalence(actual, reference, keys, label):
    merged = actual.merge(
        reference,
        on=keys,
        how="outer",
        suffixes=("_actual", "_reference"),
        indicator=True
    )

    require(
        (merged["_merge"] == "both").all(),
        f"{label}: actual and reference records do not match."
    )

    require(
        (merged["observations_actual"] ==
         merged["observations_reference"]).all(),
        f"{label}: cluster observation counts differ."
    )

    difference = (
        merged["within_pct_actual"] -
        merged["within_pct_reference"]
    ).abs()

    require(
        difference.max() < 1e-9,
        f"{label}: prevalence percentage mismatch. "
        f"Maximum difference: {difference.max()}"
    )

    return float(difference.max())

def main():
    require(not OUTPUT_FILE.exists(),
            f"Refusing to overwrite existing file: {OUTPUT_FILE}")

    for path in [METADATA_FILE, BASELINE_FILE, LOG_FILE,
                 ANNUAL_REFERENCE, PERIOD_REFERENCE]:
        require(path.exists(), f"Required input missing: {path}")

    metadata = pd.read_csv(METADATA_FILE)
    baseline_archive = np.load(BASELINE_FILE)
    log_archive = np.load(LOG_FILE)

    baseline_X = baseline_archive["X"]
    log_X = log_archive["X"]

    require(len(metadata) == len(baseline_X) == len(log_X),
            "Metadata and feature matrix row counts differ.")

    require(np.array_equal(
        baseline_archive["features"],
        log_archive["features"]
    ), "Feature definitions differ between matrices.")

    require(
        metadata[["year", "date", "latitude", "longitude"]].notna().all().all(),
        "Metadata contains missing coordinates or dates."
    )

    metadata["year"] = metadata["year"].astype(int)
    metadata["date"] = pd.to_datetime(metadata["date"])
    metadata["latitude"] = metadata["latitude"].astype(float)
    metadata["longitude"] = metadata["longitude"].astype(float)

    require(
        metadata.duplicated(
            ["year", "date", "latitude", "longitude"]
        ).sum() == 0,
        "Duplicate metadata observation keys detected."
    )

    candidates = [
        ("baseline", 2, baseline_X, "baseline_k2"),
        ("log_sensitivity", 2, log_X, "log_k2"),
        ("log_sensitivity", 3, log_X, "log_k3"),
    ]

    output = metadata.copy()
    annual_records = []
    period_records = []

    for variant, k, X, column in candidates:
        print(f"Fitting {variant}, K={k}")

        model = MiniBatchKMeans(
            n_clusters=k,
            random_state=SEED,
            batch_size=4096,
            n_init=10,
            max_iter=200,
            reassignment_ratio=0.01
        )

        model.fit(X)
        labels = model.predict(X)

        require(len(labels) == len(metadata),
                f"{column}: label count mismatch.")

        require(set(np.unique(labels)) == set(range(k)),
                f"{column}: unexpected cluster identifiers.")

        output[column] = labels

        labelled = metadata[["year"]].copy()
        labelled["cluster"] = labels

        annual = (
            labelled.groupby(["year", "cluster"])
            .size()
            .rename("observations")
            .reset_index()
        )

        annual["variant"] = variant
        annual["k"] = k
        annual["within_pct"] = (
            annual["observations"] /
            annual.groupby("year")["observations"].transform("sum") * 100
        )

        annual_records.append(annual)

        labelled["period"] = np.where(
            labelled["year"] <= 2016,
            "2010_2016",
            "2017_2021"
        )

        period = (
            labelled.groupby(["period", "cluster"])
            .size()
            .rename("observations")
            .reset_index()
        )

        period["variant"] = variant
        period["k"] = k
        period["within_pct"] = (
            period["observations"] /
            period.groupby("period")["observations"].transform("sum") * 100
        )

        period_records.append(period)

    annual_actual = pd.concat(annual_records, ignore_index=True)
    period_actual = pd.concat(period_records, ignore_index=True)

    annual_reference = pd.read_csv(ANNUAL_REFERENCE).rename(
        columns={"within_year_pct": "within_pct"}
    )
    period_reference = pd.read_csv(PERIOD_REFERENCE).rename(
        columns={"within_period_pct": "within_pct"}
    )

    annual_keys = ["variant", "k", "year", "cluster"]
    period_keys = ["variant", "k", "period", "cluster"]

    annual_error = validate_prevalence(
        annual_actual,
        annual_reference,
        annual_keys,
        "Annual prevalence"
    )

    period_error = validate_prevalence(
        period_actual,
        period_reference,
        period_keys,
        "Period prevalence"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_FILE, index=False, date_format="%Y-%m-%d")

    print("\nASSIGNMENT EXPORT VALIDATED")
    print("Observations:", len(output))
    print("Years:", output["year"].nunique())
    print("Unique grid cells:",
          output[["latitude", "longitude"]].drop_duplicates().shape[0])
    print("Assignment columns:", ", ".join(
        ["baseline_k2", "log_k2", "log_k3"]
    ))
    print("Annual maximum percentage difference:", annual_error)
    print("Period maximum percentage difference:", period_error)
    print("Output:", OUTPUT_FILE)

if __name__ == "__main__":
    main()

