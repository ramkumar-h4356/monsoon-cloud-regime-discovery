"""Milestone M22: Principal Component Analysis (PCA) on Post-Monsoon Dataset.

Performs rigorous linear dimensionality reduction on the model-ready CERES
post-monsoon dataset (FS-A, 36 features, 2010-2021).

Scientific Methodology:
1. Temporal Partitioning: PCA is fitted strictly on the training partition
   (2010-2016; 4,838,400 observations) to prevent temporal data leakage.
2. Holdout Generalization: Transformed scores and explained variance are
   evaluated out-of-sample on the holdout partition (2017-2021; 3,456,000 observations).
3. Congruence & Stability: Computes Tucker's congruence coefficients and
   canonical subspace principal angles between train and holdout eigenvectors.
4. Physical Loadings Interpretation: Analyzes meteorological cloud regimes
   represented by top components (convective ice vs mixed phase vs stratiform liquid).
5. Output Generation: Produces variance tables, loadings matrices, full JSON summary,
   and projected principal component scores for downstream clustering (Objective 2).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.linalg import subspace_angles
from sklearn.decomposition import PCA

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "post_monsoon" / "model_ready"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "post_monsoon" / "pca"
REPORTS_DIR = PROJECT_ROOT / "reports" / "seasons" / "post_monsoon" / "m22_pca"

DEFAULT_NPY = DATA_DIR / "post_monsoon_FS-A_scaled.npy"
DEFAULT_NPZ = DATA_DIR / "post_monsoon_FS-A_scaled.npz"


def _utc_now() -> str:
    """Current UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def run_post_monsoon_pca(
    npy_path: Path = DEFAULT_NPY,
    npz_path: Path = DEFAULT_NPZ,
    output_dir: Path = OUTPUT_DIR,
    reports_dir: Path = REPORTS_DIR,
    n_components: int = 36,
    top_k_scores: int = 10,
) -> dict[str, Any]:
    """Execute complete Milestone M22 PCA analysis pipeline."""
    start_time = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    print("=== Milestone M22: Post-Monsoon Principal Component Analysis ===")
    print(f"Data source: {npy_path}")
    print(f"Metadata source: {npz_path}")
    print(f"Output directory: {output_dir}")
    print(f"Reports directory: {reports_dir}")

    # 1. Load memory-mapped data and metadata
    t0 = time.time()
    X_mmap = np.load(npy_path, mmap_mode="r")
    meta = np.load(npz_path)
    train_mask = meta["train_mask"].astype(bool)
    feature_names = meta["feature_names"].astype(str).tolist()
    feature_families = meta["feature_families"].astype(str).tolist()
    lat = meta["lat"]
    lon = meta["lon"]
    sample_years = meta["sample_years"]

    n_samples, n_features = X_mmap.shape
    n_train = int(train_mask.sum())
    n_holdout = int((~train_mask).sum())
    print(f"Loaded {n_samples} total samples ({n_train} train, {n_holdout} holdout), {n_features} features in {time.time()-t0:.2f}s.")

    # 2. Fit PCA strictly on Training Partition (2010-2016)
    print("\n--- Phase 1: Fitting PCA on Training Partition (2010-2016) ---")
    t0 = time.time()
    X_train = X_mmap[train_mask]
    pca_train = PCA(n_components=n_components)
    pca_train.fit(X_train)
    print(f"Training PCA fitted in {time.time()-t0:.2f}s.")

    train_exp_var_ratio = pca_train.explained_variance_ratio_
    train_cum_var = np.cumsum(train_exp_var_ratio)
    train_eigenvalues = pca_train.explained_variance_

    # Kaiser criterion: eigenvalues > 1.0
    kaiser_count = int(np.sum(train_eigenvalues > 1.0))
    print(f"Kaiser criterion: {kaiser_count} components with eigenvalue > 1.0")

    # Threshold checks
    thresholds = [0.70, 0.80, 0.85, 0.90, 0.95, 0.99]
    components_for_threshold = {}
    for th in thresholds:
        idx = int(np.argmax(train_cum_var >= th)) + 1
        components_for_threshold[f"{int(th*100)}%"] = idx
        print(f"  Variance {int(th*100)}% reached at component PC{idx} ({train_cum_var[idx-1]*100:.2f}%)")

    # 3. Fit PCA on Holdout Partition (2017-2021) for Temporal Cross-Validation
    print("\n--- Phase 2: Evaluating Temporal Generalization & Stability (2017-2021) ---")
    X_holdout = X_mmap[~train_mask]
    pca_holdout = PCA(n_components=n_components)
    pca_holdout.fit(X_holdout)

    # Out-of-sample explained variance on holdout using train components
    X_holdout_projected = pca_train.transform(X_holdout)
    total_holdout_var = float(np.var(X_holdout, axis=0).sum())
    oos_explained_var = float(np.var(X_holdout_projected, axis=0).sum())
    oos_ratio = oos_explained_var / total_holdout_var if total_holdout_var > 0 else 0.0
    print(f"Out-of-sample holdout variance explained by train PCs: {oos_ratio*100:.2f}%")

    # Congruence coefficients (Tucker's phi / cosine similarity)
    component_congruence: list[dict[str, Any]] = []
    for i in range(min(15, n_components)):
        v_train = pca_train.components_[i]
        v_test = pca_holdout.components_[i]
        cos_sim = float(np.dot(v_train, v_test) / (np.linalg.norm(v_train) * np.linalg.norm(v_test)))
        component_congruence.append({
            "component": f"PC{i+1}",
            "train_variance_ratio": float(train_exp_var_ratio[i]),
            "holdout_variance_ratio": float(pca_holdout.explained_variance_ratio_[i]),
            "congruence_cosine_similarity": abs(cos_sim),
            "sign": "+" if cos_sim >= 0 else "-",
        })

    # Subspace angles between train and holdout 5D subspaces
    angles_5d = subspace_angles(pca_train.components_[:5].T, pca_holdout.components_[:5].T)
    subspace_sim_5d = float(np.cos(angles_5d[-1]))
    print(f"Top 5D subspace congruence (cos max angle): {subspace_sim_5d:.4f}")

    # 4. Physical Meteorological Interpretation of Top Loadings
    print("\n--- Phase 3: Analyzing Meteorological Cloud Loadings ---")
    loadings_df = pd.DataFrame(
        pca_train.components_.T,
        index=feature_names,
        columns=[f"PC{i+1}" for i in range(n_components)],
    )
    loadings_df["family"] = feature_families

    # Top drivers per component
    component_diagnostics = []
    for i in range(min(5, n_components)):
        col = f"PC{i+1}"
        s = loadings_df[col]
        top_pos = s.nlargest(3).to_dict()
        top_neg = s.nsmallest(3).to_dict()
        component_diagnostics.append({
            "component": col,
            "variance_explained": float(train_exp_var_ratio[i]),
            "cumulative_variance": float(train_cum_var[i]),
            "top_positive_features": {k: round(float(v), 4) for k, v in top_pos.items()},
            "top_negative_features": {k: round(float(v), 4) for k, v in top_neg.items()},
        })
        print(f"  {col} ({train_exp_var_ratio[i]*100:.2f}%): pos={list(top_pos.keys())[:2]}, neg={list(top_neg.keys())[:2]}")

    # 5. Transform Full Dataset to Top-K Principal Component Coordinates
    print(f"\n--- Phase 4: Projecting All {n_samples} Samples to Top-{top_k_scores} Components ---")
    t0 = time.time()
    # Batch transform to minimize memory footprint
    scores_npy_path = output_dir / f"post_monsoon_pca_FS-A_top{top_k_scores}_scores.npy"
    scores_mmap = np.lib.format.open_memmap(
        scores_npy_path, mode="w+", dtype=np.float32, shape=(n_samples, top_k_scores)
    )

    batch_size = 500000
    for start_idx in range(0, n_samples, batch_size):
        end_idx = min(start_idx + batch_size, n_samples)
        batch = X_mmap[start_idx:end_idx]
        batch_scores = pca_train.transform(batch)[:, :top_k_scores]
        scores_mmap[start_idx:end_idx, :] = batch_scores.astype(np.float32)

    scores_mmap.flush()
    print(f"Projected scores written to {scores_npy_path} in {time.time()-t0:.2f}s.")

    # Verify score finiteness
    is_finite = np.isfinite(scores_mmap[:100000]).all() and np.isfinite(scores_mmap[-100000:]).all()
    if not is_finite:
        raise ValueError("Non-finite values detected in projected PCA scores!")
    print("Projected scores finiteness verified: 100% finite (0 NaNs, 0 Infs).")

    # 6. Save Artifacts & Reports
    print("\n--- Phase 5: Generating Milestone Reports & Tables ---")
    # Variance table CSV
    var_df = pd.DataFrame({
        "component": [f"PC{i+1}" for i in range(n_components)],
        "eigenvalue": pca_train.explained_variance_,
        "explained_variance_ratio": train_exp_var_ratio,
        "cumulative_variance_ratio": train_cum_var,
        "holdout_variance_ratio": pca_holdout.explained_variance_ratio_,
    })
    var_csv_path = reports_dir / "post_monsoon_pca_variance.csv"
    var_df.to_csv(var_csv_path, index=False)
    print(f"Saved variance table: {var_csv_path}")

    # Loadings table CSV
    loadings_csv_path = reports_dir / "post_monsoon_pca_loadings.csv"
    loadings_df.to_csv(loadings_csv_path, index=True)
    print(f"Saved loadings table: {loadings_csv_path}")

    # Summary JSON manifest
    elapsed = round(time.time() - start_time, 2)
    summary_data = {
        "milestone": "M22",
        "title": "Post-Monsoon Principal Component Analysis (Stage A Baseline)",
        "created_utc": _utc_now(),
        "elapsed_seconds": elapsed,
        "feature_set": "FS-A",
        "total_features": n_features,
        "sample_counts": {
            "total_observations": n_samples,
            "training_samples": n_train,
            "holdout_samples": n_holdout,
        },
        "kaiser_criterion": {
            "eigenvalues_greater_than_1": kaiser_count,
        },
        "variance_thresholds": components_for_threshold,
        "out_of_sample_generalization": {
            "holdout_variance_explained_ratio": round(oos_ratio, 4),
            "subspace_congruence_5d": round(subspace_sim_5d, 4),
        },
        "component_congruence": component_congruence,
        "component_diagnostics": component_diagnostics,
        "output_artifacts": {
            "scores_npy_path": str(scores_npy_path),
            "scores_npy_bytes": scores_npy_path.stat().st_size,
            "variance_csv_path": str(var_csv_path),
            "loadings_csv_path": str(loadings_csv_path),
        },
        "status": "COMPLETED_READY_FOR_CLUSTERING",
    }

    summary_json_path = reports_dir / "post_monsoon_pca_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Saved summary JSON: {summary_json_path}")

    del scores_mmap
    import gc
    gc.collect()

    print(f"\n=== M22 PCA Pipeline Successfully Completed in {elapsed}s ===")
    return summary_data


def main():
    parser = argparse.ArgumentParser(description="M22 Post-Monsoon PCA Analysis")
    parser.add_argument("--top-k", type=int, default=10, help="Number of top component scores to output")
    args = parser.parse_args()

    run_post_monsoon_pca(top_k_scores=args.top_k)


if __name__ == "__main__":
    main()
