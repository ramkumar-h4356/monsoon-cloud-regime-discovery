
"""
M5 COMPLETE VALIDATION — CONSTRAINED PERMUTATION EDITION

Run from repository root:
    python run_m5_complete_validation.py

Reuses:
    M4 PCA score archives
    Four M5 refined t-SNE embeddings
    Existing M5 global-permutation validation results

Adds:
    Spatially and seasonally constrained year-label permutations
    Two stratification sensitivity configurations
    Comparison against the global permutation baseline

Does not rerun t-SNE or modify existing M4/M5 outputs.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
)
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import KNeighborsClassifier


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "src" / "08_dimensionality_reduction"

if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

try:
    from established_monsoon_tsne import (
        M4_DIR,
        PCA_INPUT_COMPONENTS,
        RANDOM_STATE,
        _load_pca_scores,
    )
except Exception as exc:
    raise SystemExit(f"Cannot import existing M5 module: {exc}")

REFINED_DIR = (
    ROOT
    / "data/processed/clustering/established_monsoon/m5_tsne_refined"
)

OUTPUT_DIR = (
    ROOT
    / "data/processed/clustering/established_monsoon/m5_validation"
)

REPRESENTATIONS = ["baseline", "log_sensitivity"]
PERPLEXITIES = [30, 50]

NEIGHBOUR_K = 15
PERMUTATIONS = 999

KNN_K = 15
CV_FOLDS = 5

# Primary constrained null:
# 4 latitude bins × 4 longitude bins × 5-day seasonal blocks.
PRIMARY_CONFIG = {
    "name": "primary_4x4_spatial_5day",
    "spatial_bins": 4,
    "seasonal_block_days": 5,
}

# Sensitivity null:
# 3 latitude bins × 3 longitude bins × 10-day seasonal blocks.
SENSITIVITY_CONFIG = {
    "name": "sensitivity_3x3_spatial_10day",
    "spatial_bins": 3,
    "seasonal_block_days": 10,
}


# ============================================================
# 2. INPUT LOADING
# ============================================================

def require_file(path):
    if not path.is_file():
        raise FileNotFoundError(f"Required input missing:\n{path}")


def load_pca():

    baseline, baseline_meta = _load_pca_scores(
        M4_DIR / "baseline_scores_and_metadata.npz"
    )

    log_scores, log_meta = _load_pca_scores(
        M4_DIR / "log_sensitivity_scores_and_metadata.npz"
    )

    columns = ["year", "date", "latitude", "longitude"]

    if not baseline_meta[columns].reset_index(drop=True).equals(
        log_meta[columns].reset_index(drop=True)
    ):
        raise ValueError("M4 metadata are not aligned.")

    return {
        "baseline": (baseline, baseline_meta.reset_index(drop=True)),
        "log_sensitivity": (log_scores, log_meta.reset_index(drop=True)),
    }


def load_embedding(representation, perplexity, metadata):

    stem = f"{representation}_perplexity_{perplexity}"

    csv_path = REFINED_DIR / f"{stem}_coordinates.csv"
    npz_path = REFINED_DIR / f"{stem}_embedding.npz"

    require_file(csv_path)
    require_file(npz_path)

    coords = pd.read_csv(csv_path)

    with np.load(npz_path, allow_pickle=False) as archive:

        embedding = archive["embedding"].copy()
        sample_indices = archive["sample_indices"].astype(int, copy=True)

        archive_year = archive["year"].copy()
        archive_date = archive["date"].astype(str, copy=True)
        archive_lat = archive["latitude"].copy()
        archive_lon = archive["longitude"].copy()

    if len(sample_indices) != len(coords):
        raise ValueError(f"Sample size mismatch: {stem}")

    if embedding.shape != (len(sample_indices), 2):
        raise ValueError(f"Embedding shape mismatch: {stem}")

    if (
        len(sample_indices) == 0
        or sample_indices.min() < 0
        or sample_indices.max() >= len(metadata)
    ):
        raise ValueError(f"Invalid sample indices: {stem}")

    expected = metadata.iloc[sample_indices].reset_index(drop=True)

    checks = [
        np.array_equal(coords["year"], expected["year"]),
        np.array_equal(
            coords["date"].astype(str),
            expected["date"].astype(str),
        ),
        np.allclose(coords["latitude"], expected["latitude"]),
        np.allclose(coords["longitude"], expected["longitude"]),
        np.array_equal(archive_year, expected["year"]),
        np.array_equal(
            archive_date,
            expected["date"].astype(str).to_numpy(),
        ),
        np.allclose(archive_lat, expected["latitude"]),
        np.allclose(archive_lon, expected["longitude"]),
    ]

    if not all(checks):
        raise ValueError(f"Metadata alignment failed: {stem}")

    if not np.isfinite(embedding).all():
        raise ValueError(f"Invalid coordinates: {stem}")

    coords = coords.copy()
    coords["tsne_1"] = embedding[:, 0]
    coords["tsne_2"] = embedding[:, 1]

    return coords, sample_indices


# ============================================================
# 3. NEIGHBOURHOOD CALCULATION
# ============================================================

def get_neighbours(coords):

    xy = coords[["tsne_1", "tsne_2"]].to_numpy(dtype=float)

    if len(xy) <= NEIGHBOUR_K:
        raise ValueError("Insufficient observations.")

    tree = cKDTree(xy)

    # Remove the observation itself.
    return tree.query(
        xy,
        k=NEIGHBOUR_K + 1,
    )[1][:, 1:]


# ============================================================
# 4. GLOBAL PERMUTATION REFERENCE
# ============================================================

def global_permutation_test(years, neighbour_indices):

    observed = float(
        np.mean(years[neighbour_indices] == years[:, None])
    )

    rng = np.random.default_rng(RANDOM_STATE)

    null = np.empty(PERMUTATIONS)

    for i in range(PERMUTATIONS):

        shuffled = rng.permutation(years)

        null[i] = np.mean(
            shuffled[neighbour_indices] == shuffled[:, None]
        )

    return {
        "observed_fraction": observed,
        "null_mean": float(null.mean()),
        "null_std": float(null.std(ddof=1)),
        "p_value": float(
            (1 + np.count_nonzero(null >= observed))
            / (PERMUTATIONS + 1)
        ),
    }


# ============================================================
# 5. CONSTRAINED STRATA
# ============================================================

def build_strata(coords, config):

    lat = coords["latitude"].to_numpy(dtype=float)
    lon = coords["longitude"].to_numpy(dtype=float)

    dates = pd.to_datetime(coords["date"], errors="raise")

    # Day position within the established monsoon period.
    reference = pd.Timestamp("2001-07-15")

    seasonal_dates = dates.map(
        lambda d: pd.Timestamp(2001, d.month, d.day)
    )

    day_position = (
        seasonal_dates - reference
    ).dt.days.to_numpy()

    if np.any(day_position < 0):
        raise ValueError(
            "Unexpected date before July 15 in established-monsoon sample."
        )

    n_bins = config["spatial_bins"]

    # Fixed geographical bins spanning the selected India grid.
    lat_edges = np.linspace(6.5, 37.5, n_bins + 1)
    lon_edges = np.linspace(68.5, 97.5, n_bins + 1)

    lat_bin = pd.cut(
        lat,
        bins=lat_edges,
        labels=False,
        include_lowest=True,
    )

    lon_bin = pd.cut(
        lon,
        bins=lon_edges,
        labels=False,
        include_lowest=True,
    )

    if pd.isna(lat_bin).any() or pd.isna(lon_bin).any():
        raise ValueError("Some observations fall outside spatial bin limits.")

    day_block = (
        day_position // config["seasonal_block_days"]
    )

    # Each stratum represents broad geography and seasonal position.
    strata = (
        pd.Series(lat_bin.astype(int)).astype(str)
        + "_"
        + pd.Series(lon_bin.astype(int)).astype(str)
        + "_"
        + pd.Series(day_block).astype(str)
    ).to_numpy()

    return strata


# ============================================================
# 6. CONSTRAINED PERMUTATION TEST
# ============================================================

def constrained_permutation_test(
    coords,
    neighbour_indices,
    config,
):

    years = coords["year"].to_numpy()

    strata = build_strata(coords, config)

    # Precompute indices belonging to each stratum.
    groups = [
        np.flatnonzero(strata == group)
        for group in np.unique(strata)
    ]

    movable_groups = [group for group in groups if len(group) > 1]

    movable_observations = sum(
        len(group) for group in movable_groups
    )

    observed = float(
        np.mean(years[neighbour_indices] == years[:, None])
    )

    rng = np.random.default_rng(
        RANDOM_STATE + config["spatial_bins"]
        + config["seasonal_block_days"]
    )

    null = np.empty(PERMUTATIONS)

    for permutation in range(PERMUTATIONS):

        shuffled = years.copy()

        # Shuffle labels only within their own spatial/date stratum.
        for group in movable_groups:
            shuffled[group] = rng.permutation(shuffled[group])

        null[permutation] = np.mean(
            shuffled[neighbour_indices] == shuffled[:, None]
        )

    null_mean = float(null.mean())
    null_std = float(null.std(ddof=1))

    p_value = float(
        (1 + np.count_nonzero(null >= observed))
        / (PERMUTATIONS + 1)
    )

    z_score = (
        float((observed - null_mean) / null_std)
        if null_std > 0 else None
    )

    return {
        "observed_fraction": observed,
        "constrained_null_mean": null_mean,
        "constrained_null_std": null_std,
        "constrained_p_value": p_value,
        "constrained_z_score": z_score,
        "strata_count": len(groups),
        "movable_strata_count": len(movable_groups),
        "movable_observation_fraction": (
            movable_observations / len(years)
        ),
        "spatial_bins_per_axis": config["spatial_bins"],
        "seasonal_block_days": config["seasonal_block_days"],
        "permutations": PERMUTATIONS,
    }


# ============================================================
# 7. ORIGINAL PCA-SPACE YEAR CLASSIFICATION
# ============================================================

def classify_year(scores, metadata, sample_indices):

    x = scores[
        sample_indices,
        :PCA_INPUT_COMPONENTS
    ]

    y = metadata.iloc[
        sample_indices
    ]["year"].to_numpy()

    selected = metadata.iloc[sample_indices]

    groups = (
        selected["year"].astype(str)
        + "_"
        + selected["date"].astype(str)
    ).to_numpy()

    splitter = GroupKFold(n_splits=CV_FOLDS)

    predictions = np.empty_like(y)

    for train, test in splitter.split(x, y, groups):

        model = KNeighborsClassifier(
            n_neighbors=KNN_K,
            weights="distance",
            metric="euclidean",
        )

        model.fit(x[train], y[train])

        predictions[test] = model.predict(x[test])

    return {
        "accuracy": float(accuracy_score(y, predictions)),
        "balanced_accuracy": float(
            balanced_accuracy_score(y, predictions)
        ),
        "macro_f1": float(
            f1_score(
                y,
                predictions,
                average="macro",
                zero_division=0,
            )
        ),
    }


# ============================================================
# 8. COMPLETE PIPELINE
# ============================================================

def run():

    print("=" * 72)
    print("M5 CONSTRAINED TEMPORAL AND SPATIAL VALIDATION")
    print("=" * 72)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    require_file(
        M4_DIR / "baseline_scores_and_metadata.npz"
    )

    require_file(
        M4_DIR / "log_sensitivity_scores_and_metadata.npz"
    )

    require_file(
        REFINED_DIR / "m5_refined_model_summary.csv"
    )

    representations = load_pca()

    all_rows = []
    classification_rows = []

    reference_indices = None

    configurations = [
        PRIMARY_CONFIG,
        SENSITIVITY_CONFIG,
    ]

    print("\n[1/4] Running constrained permutation tests")

    for representation in REPRESENTATIONS:

        scores, metadata = representations[representation]

        for perplexity in PERPLEXITIES:

            print(
                f"\n{representation}, perplexity={perplexity}"
            )

            coords, sample_indices = load_embedding(
                representation,
                perplexity,
                metadata,
            )

            if reference_indices is None:
                reference_indices = sample_indices

            elif not np.array_equal(
                reference_indices,
                sample_indices,
            ):
                raise ValueError(
                    "The four embeddings do not use identical samples."
                )

            neighbour_indices = get_neighbours(coords)

            years = coords["year"].to_numpy()

            global_result = global_permutation_test(
                years,
                neighbour_indices,
            )

            for config in configurations:

                constrained_result = constrained_permutation_test(
                    coords,
                    neighbour_indices,
                    config,
                )

                all_rows.append({
                    "representation": representation,
                    "perplexity": perplexity,
                    "configuration": config["name"],
                    **global_result,
                    **constrained_result,
                })

    print("\n[2/4] Evaluating original PCA-space year information")

    for representation, (scores, metadata) in representations.items():

        result = classify_year(
            scores,
            metadata,
            reference_indices,
        )

        classification_rows.append({
            "representation": representation,
            **result,
        })

    results_df = pd.DataFrame(all_rows)

    classification_df = pd.DataFrame(
        classification_rows
    )

    print("\n[3/4] Saving results")

    results_df.to_csv(
        OUTPUT_DIR / "m5_constrained_permutation_results.csv",
        index=False,
    )

    classification_df.to_csv(
        OUTPUT_DIR / "m5_pca_year_classification_final.csv",
        index=False,
    )

    limitations = [
        "The constrained permutation preserves year counts within broad spatial and seasonal strata.",
        "Spatial bins and seasonal blocks are approximations, not exact matching.",
        "The constrained null does not preserve every spatial or temporal dependency.",
        "Strata with one observation cannot be permuted.",
        "Results depend on the chosen spatial bin and seasonal block resolution.",
        "Permutation p-values are exploratory and do not establish causality.",
        "Year classification is a diagnostic of temporal information, not cloud-regime validation.",
        "All t-SNE fits reached their 3000-iteration ceiling; convergence was not demonstrated.",
    ]

    manifest = {
        "milestone": "M5 constrained validation",
        "sample_size": int(len(reference_indices)),
        "permutations": PERMUTATIONS,
        "neighbour_k": NEIGHBOUR_K,
        "primary_configuration": PRIMARY_CONFIG,
        "sensitivity_configuration": SENSITIVITY_CONFIG,
        "random_state": RANDOM_STATE,
        "representations": REPRESENTATIONS,
        "perplexities": PERPLEXITIES,
        "limitations": limitations,
        "outputs": [
            "m5_constrained_permutation_results.csv",
            "m5_pca_year_classification_final.csv",
            "m5_constrained_validation_manifest.json",
            "m5_constrained_validation_report.txt",
        ],
    }

    with open(
        OUTPUT_DIR / "m5_constrained_validation_manifest.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(manifest, file, indent=2)

    report = [
        "M5 CONSTRAINED TEMPORAL AND SPATIAL VALIDATION",
        "=" * 65,
        "",
        results_df.to_string(index=False),
        "",
        "ORIGINAL PCA YEAR CLASSIFICATION",
        "-" * 65,
        classification_df.to_string(index=False),
        "",
        "LIMITATIONS",
        "-" * 65,
        *[f"- {item}" for item in limitations],
    ]

    with open(
        OUTPUT_DIR / "m5_constrained_validation_report.txt",
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(report))

    print("\n[4/4] COMPLETE")

    print("\nCONSTRAINED PERMUTATION RESULTS")

    print(
        results_df[
            [
                "representation",
                "perplexity",
                "configuration",
                "observed_fraction",
                "null_mean",
                "constrained_null_mean",
                "constrained_p_value",
                "movable_observation_fraction",
            ]
        ].to_string(index=False)
    )

    print("\nPCA CLASSIFICATION")

    print(classification_df.to_string(index=False))

    print("\nOUTPUT DIRECTORY:")
    print(OUTPUT_DIR)

    print("\nM5 constrained validation completed.")
    print("Existing M4 and M5 embedding files were not modified.")


if __name__ == "__main__":

    try:
        run()

    except Exception as error:

        print("\nVALIDATION FAILED")
        print(f"{type(error).__name__}: {error}")

        traceback.print_exc()

        raise SystemExit(1)
