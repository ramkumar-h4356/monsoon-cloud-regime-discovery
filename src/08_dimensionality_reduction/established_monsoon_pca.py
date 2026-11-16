"""M4 PCA for the Established Monsoon Group B feature matrices.

Consumes the exact standardized matrices produced by M3. It does not refit
feature transformations or scaling. PCA itself centers each input matrix,
as required by sklearn's PCA implementation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA


PROJECT_ROOT = Path(__file__).resolve().parents[2]
M3_DIR = (
    PROJECT_ROOT / "data" / "processed" / "clustering"
    / "established_monsoon" / "m3_feature_preparation"
)
M4_DIR = (
    PROJECT_ROOT / "data" / "processed" / "clustering"
    / "established_monsoon" / "m4_pca"
)
MANIFEST_NAME = "established_monsoon_group_B_manifest.json"


def _numeric_finite(name: str, array: np.ndarray) -> None:
    if not np.issubdtype(array.dtype, np.number):
        raise ValueError(f"{name} must be numeric; got {array.dtype}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains NaN or infinite values")


def validate_inputs(
    baseline: np.ndarray,
    log_sensitivity: np.ndarray,
    baseline_features: np.ndarray,
    log_features: np.ndarray,
    metadata: pd.DataFrame,
    expected_features: list[str] | None = None,
) -> None:
    """Validate matrix dimensions, values, feature order and row alignment."""
    _numeric_finite("baseline X", baseline)
    _numeric_finite("log-sensitivity X", log_sensitivity)

    if baseline.ndim != 2 or log_sensitivity.ndim != 2:
        raise ValueError("Both feature matrices must be two-dimensional.")
    if baseline.shape != log_sensitivity.shape:
        raise ValueError("Baseline and log-sensitivity shapes differ.")
    if baseline.shape[1] < 2:
        raise ValueError("PCA requires at least two features.")
    if baseline_features.ndim != 1 or log_features.ndim != 1:
        raise ValueError("Feature-name arrays must be one-dimensional.")
    if not np.array_equal(baseline_features, log_features):
        raise ValueError("Baseline and log-sensitivity feature orders differ.")
    if len(baseline_features) != baseline.shape[1]:
        raise ValueError("Feature-name count does not match matrix columns.")
    if expected_features is not None and baseline_features.tolist() != expected_features:
        raise ValueError("Matrix feature order differs from the M3 manifest.")
    if len(metadata) != baseline.shape[0]:
        raise ValueError("Metadata row count does not match matrix observations.")
    required = {"year", "date", "latitude", "longitude"}
    missing = required.difference(metadata.columns)
    if missing:
        raise ValueError(f"Metadata is missing required columns: {sorted(missing)}")
    if metadata[list(required)].isna().any().any():
        raise ValueError("Observation metadata contains missing identifiers.")


def fit_pca(matrix: np.ndarray) -> tuple[PCA, np.ndarray]:
    """Fit full-SVD PCA to an already transformed and standardized matrix."""
    _numeric_finite("PCA input", matrix)
    model = PCA(svd_solver="full")
    scores = model.fit_transform(matrix)
    _numeric_finite("PCA scores", scores)
    return model, scores


def variance_threshold_components(
    explained_variance_ratio: np.ndarray,
    thresholds: tuple[float, ...] = (0.80, 0.90, 0.95),
) -> dict[str, int]:
    cumulative = np.cumsum(explained_variance_ratio)
    result: dict[str, int] = {}
    for threshold in thresholds:
        matches = np.flatnonzero(cumulative >= threshold)
        result[f"{int(threshold * 100)}_percent"] = (
            int(matches[0] + 1) if len(matches) else len(cumulative)
        )
    return result


def principal_angles_degrees(
    components_a: np.ndarray, components_b: np.ndarray, k: int
) -> np.ndarray:
    """Principal angles between the first-k loading subspaces (degrees)."""
    if components_a.shape != components_b.shape:
        raise ValueError("PCA component arrays must have identical shapes.")
    if k < 1 or k > min(components_a.shape[0], components_b.shape[0]):
        raise ValueError("Invalid subspace dimension k.")
    qa = components_a[:k].T
    qb = components_b[:k].T
    singular_values = np.linalg.svd(qa.T @ qb, compute_uv=False)
    singular_values = np.clip(singular_values, -1.0, 1.0)
    return np.degrees(np.arccos(singular_values))


def _write_model_outputs(
    label: str,
    model: PCA,
    scores: np.ndarray,
    features: list[str],
    metadata: pd.DataFrame,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    n_components = len(model.explained_variance_ratio_)
    component_names = [f"PC{i + 1}" for i in range(n_components)]

    variance = pd.DataFrame({
        "component": component_names,
        "explained_variance": model.explained_variance_,
        "explained_variance_ratio": model.explained_variance_ratio_,
        "explained_variance_percent": model.explained_variance_ratio_ * 100,
        "cumulative_explained_variance_ratio": np.cumsum(
            model.explained_variance_ratio_
        ),
        "cumulative_explained_variance_percent": np.cumsum(
            model.explained_variance_ratio_
        ) * 100,
        "singular_value": model.singular_values_,
    })
    variance.to_csv(output_dir / f"{label}_explained_variance.csv", index=False)

    loadings = pd.DataFrame(model.components_.T, columns=component_names)
    loadings.insert(0, "feature", features)
    loadings.to_csv(output_dir / f"{label}_loadings.csv", index=False)

    contributions = model.components_.T ** 2 * 100
    contribution_df = pd.DataFrame(contributions, columns=component_names)
    contribution_df.insert(0, "feature", features)
    contribution_df.to_csv(
        output_dir / f"{label}_feature_contributions_percent.csv", index=False
    )

    # Store scores and row identifiers together to preserve exact observation
    # correspondence without producing a very large CSV.
    score_payload = {
        "scores": scores.astype(np.float64, copy=False),
        "year": metadata["year"].to_numpy(),
        "date": metadata["date"].astype(str).to_numpy(dtype="U10"),
        "latitude": metadata["latitude"].to_numpy(dtype=np.float64),
        "longitude": metadata["longitude"].to_numpy(dtype=np.float64),
        "features": np.asarray(features, dtype="U"),
    }
    np.savez_compressed(output_dir / f"{label}_scores_and_metadata.npz", **score_payload)

    thresholds = variance_threshold_components(model.explained_variance_ratio_)
    return {
        "matrix": label,
        "observations": int(scores.shape[0]),
        "features": int(scores.shape[1]),
        "components": n_components,
        "variance_threshold_components": thresholds,
        "pc1_pc2_variance_percent": float(
            np.sum(model.explained_variance_ratio_[:2]) * 100
        ),
        "output_files": [
            f"{label}_explained_variance.csv",
            f"{label}_loadings.csv",
            f"{label}_feature_contributions_percent.csv",
            f"{label}_scores_and_metadata.npz",
        ],
    }


def run(m3_dir: Path = M3_DIR, output_dir: Path = M4_DIR) -> dict[str, Any]:
    manifest_path = m3_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(f"M3 manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    baseline_path = m3_dir / manifest["baseline_matrix"]
    log_path = m3_dir / manifest["log_sensitivity_matrix"]
    metadata_path = m3_dir / manifest["metadata"]

    for path in (baseline_path, log_path, metadata_path):
        if not path.exists():
            raise FileNotFoundError(f"Required M3 input not found: {path}")

    with np.load(baseline_path, allow_pickle=False) as baseline_data:
        baseline = baseline_data["X"]
        baseline_features = baseline_data["features"]
    with np.load(log_path, allow_pickle=False) as log_data:
        log_matrix = log_data["X"]
        log_features = log_data["features"]

    metadata = pd.read_csv(metadata_path)
    expected_features = manifest.get("features_in_order")
    validate_inputs(
        baseline, log_matrix, baseline_features, log_features,
        metadata, expected_features,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    features = baseline_features.astype(str).tolist()

    print("Fitting baseline PCA (full SVD)...")
    baseline_model, baseline_scores = fit_pca(baseline)
    baseline_summary = _write_model_outputs(
        "baseline", baseline_model, baseline_scores, features, metadata, output_dir
    )
    del baseline_scores, baseline

    print("Fitting log-sensitivity PCA (full SVD)...")
    log_model, log_scores = fit_pca(log_matrix)
    log_summary = _write_model_outputs(
        "log_sensitivity", log_model, log_scores, features, metadata, output_dir
    )
    del log_scores, log_matrix

    comparison_rows = []
    for k in (2, 3, 5):
        if k <= len(features):
            angles = principal_angles_degrees(
                baseline_model.components_, log_model.components_, k
            )
            comparison_rows.append({
                "subspace_dimension": k,
                "mean_principal_angle_degrees": float(np.mean(angles)),
                "maximum_principal_angle_degrees": float(np.max(angles)),
            })
    pd.DataFrame(comparison_rows).to_csv(
        output_dir / "baseline_log_subspace_comparison.csv", index=False
    )

    component_cosines = np.sum(
        baseline_model.components_ * log_model.components_, axis=1
    )
    pd.DataFrame({
        "component": [f"PC{i + 1}" for i in range(len(component_cosines))],
        "absolute_loading_cosine_same_index": np.abs(component_cosines),
        "signed_loading_cosine_same_index": component_cosines,
    }).to_csv(output_dir / "same_index_component_loading_similarity.csv", index=False)

    result = {
        "project_component": "Established Monsoon",
        "milestone": "M4",
        "method": "sklearn PCA with full SVD",
        "input_note": (
            "Consumes M3 standardized matrices as-is; no new feature scaling, "
            "imputation, row filtering, or feature reordering is performed. "
            "PCA centers each input matrix internally."
        ),
        "feature_order": features,
        "baseline": baseline_summary,
        "log_sensitivity": log_summary,
        "subspace_comparison": comparison_rows,
        "row_alignment": (
            "Scores NPZ files contain year/date/latitude/longitude arrays in "
            "the same row order as the M3 metadata and score matrix."
        ),
    }
    (output_dir / "established_monsoon_m4_pca_manifest.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print("\n========== M4 PCA SUMMARY ==========")
    print(f"Observations: {baseline_summary['observations']:,}")
    print(f"Features: {len(features)}")
    print("Baseline variance thresholds:", baseline_summary["variance_threshold_components"])
    print("Log-sensitivity variance thresholds:", log_summary["variance_threshold_components"])
    print(f"Output: {output_dir.resolve()}")
    print("PASS: both PCA runs and output metadata validated.")
    return result


if __name__ == "__main__":
    run()
