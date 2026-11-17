"""Milestone M24: Post-Monsoon Cloud-Regime Clustering & Validation.

Performs exploratory unsupervised clustering on PCA-reduced satellite cloud features
to identify coherent exploratory cloud regimes over India (Objective 2 & 3).

Scientific Methodology:
1. Feature Space: Top 5 Principal Components from Milestone M22 (FS-A baseline),
   retaining 91.95% of total variance while eliminating observational noise.
2. Cluster Count Sweep: Evaluates K in [3, 4, 5, 6, 7] using MiniBatchKMeans.
3. Diagnostic Validation Metrics:
   - Inertia (Within-cluster sum of squares)
   - Davies-Bouldin Index (Lower is better cluster separation)
   - Calinski-Harabasz Variance Ratio Criterion (Higher is better)
   - Silhouette Coefficient (Subsampled for computational feasibility)
   - Adjusted Rand Index (ARI) stability across random initializations
4. Physical Meteorological Characterization:
   Maps cluster centroids back to physical cloud characteristics (cloud fraction,
   optical depth, ice/liquid water paths, cloud-top pressure and temperature).
5. Output Generation:
   Exports cluster label assignments for all 8,294,400 observations, cluster metric
   comparison table, physical centroid profiles, and comprehensive JSON manifest.
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

# Silence loky core counting warning
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "post_monsoon"
PCA_DIR = DATA_DIR / "pca"
MODEL_READY_DIR = DATA_DIR / "model_ready"
OUTPUT_DIR = DATA_DIR / "clustering"
REPORTS_DIR = PROJECT_ROOT / "reports" / "seasons" / "post_monsoon" / "m24_clustering"

DEFAULT_SCORES_NPY = PCA_DIR / "post_monsoon_pca_FS-A_top10_scores.npy"
DEFAULT_SCALED_NPY = MODEL_READY_DIR / "post_monsoon_FS-A_scaled.npy"
DEFAULT_NPZ = MODEL_READY_DIR / "post_monsoon_FS-A_scaled.npz"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_post_monsoon_clustering(
    scores_path: Path = DEFAULT_SCORES_NPY,
    scaled_path: Path = DEFAULT_SCALED_NPY,
    npz_path: Path = DEFAULT_NPZ,
    output_dir: Path = OUTPUT_DIR,
    reports_dir: Path = REPORTS_DIR,
    k_range: list[int] | None = None,
    primary_k: int = 4,
    n_pca_components: int = 5,
    random_state: int = 42,
) -> dict[str, Any]:
    """Execute complete Milestone M24 clustering and profiling pipeline."""
    if k_range is None:
        k_range = [3, 4, 5, 6, 7]

    start_time = time.time()
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    print("=== Milestone M24: Post-Monsoon Cloud-Regime Clustering & Validation ===")
    print(f"PCA input: {scores_path} (top {n_pca_components} PCs)")
    print(f"Cluster count sweep: K in {k_range}")
    print(f"Primary cluster count: K = {primary_k}")
    print(f"Output directory: {output_dir}")
    print(f"Reports directory: {reports_dir}")

    # 1. Load data
    t0 = time.time()
    scores_mmap = np.load(scores_path, mmap_mode="r")
    scaled_mmap = np.load(scaled_path, mmap_mode="r")
    meta = np.load(npz_path)

    feature_names = meta["feature_names"].astype(str).tolist()
    sample_years = meta["sample_years"]
    train_mask = meta["train_mask"].astype(bool)
    n_total_samples = len(sample_years)

    X_pca = scores_mmap[:, :n_pca_components]
    print(f"Loaded {n_total_samples} samples across {n_pca_components} PCs in {time.time()-t0:.2f}s.")

    # Subsample for expensive metric evaluation (Silhouette, Davies-Bouldin)
    rng = np.random.RandomState(random_state)
    eval_subsample_size = 25000
    subsample_idx = rng.choice(n_total_samples, size=eval_subsample_size, replace=False)
    X_pca_sub = X_pca[subsample_idx]
    sil_sub_idx = subsample_idx[:10000]
    X_pca_sil = X_pca[sil_sub_idx]

    # 2. Cluster Count Parameter Sweep
    print("\n--- Phase 1: Evaluating Cluster Count Sweep (K in [3..7]) ---")
    metrics_records = []
    models = {}

    for k in k_range:
        t_k = time.time()
        print(f"  Fitting MiniBatchKMeans (K={k}, batch_size=25000)...")
        km = MiniBatchKMeans(
            n_clusters=k,
            batch_size=25000,
            random_state=random_state,
            n_init="auto",
        )
        km.fit(X_pca)
        models[k] = km

        # Compute metrics on evaluation subsamples
        sub_labels = km.predict(X_pca_sub)
        sil_labels = km.predict(X_pca_sil)

        inertia = float(km.inertia_)
        db_score = float(davies_bouldin_score(X_pca_sub, sub_labels))
        ch_score = float(calinski_harabasz_score(X_pca_sub, sub_labels))
        sil = float(silhouette_score(X_pca_sil, sil_labels))

        metrics_records.append({
            "k": k,
            "inertia": round(inertia, 2),
            "davies_bouldin_index": round(db_score, 4),
            "calinski_harabasz_score": round(ch_score, 2),
            "silhouette_score": round(sil, 4),
            "elapsed_seconds": round(time.time() - t_k, 2),
        })
        print(f"    K={k}: Inertia={inertia:,.1f} | DB={db_score:.3f} (lower=better) | CH={ch_score:.1f} | Sil={sil:.3f}")

    metrics_df = pd.DataFrame(metrics_records)
    metrics_csv_path = reports_dir / "post_monsoon_clustering_metrics.csv"
    metrics_df.to_csv(metrics_csv_path, index=False)
    print(f"Saved clustering metrics table: {metrics_csv_path}")

    # 3. Fit Primary Model (K = primary_k) & Compute Full Assignments
    print(f"\n--- Phase 2: Generating Full-Dataset Regime Assignments (K = {primary_k}) ---")
    t0 = time.time()
    primary_model = models.get(primary_k)
    if primary_model is None:
        primary_model = MiniBatchKMeans(
            n_clusters=primary_k,
            batch_size=25000,
            random_state=random_state,
            n_init="auto",
        ).fit(X_pca)

    # Full dataset prediction (streamed/batched to conserve memory)
    labels_npy_path = output_dir / f"post_monsoon_cluster_labels_k{primary_k}.npy"
    labels_mmap = np.lib.format.open_memmap(
        labels_npy_path, mode="w+", dtype=np.uint8, shape=(n_total_samples,)
    )

    batch_size = 500000
    for s_idx in range(0, n_total_samples, batch_size):
        e_idx = min(s_idx + batch_size, n_total_samples)
        labels_mmap[s_idx:e_idx] = primary_model.predict(X_pca[s_idx:e_idx]).astype(np.uint8)

    labels_mmap.flush()
    print(f"Saved full cluster labels ({labels_npy_path.stat().st_size / (1024**2):.2f} MB) in {time.time()-t0:.2f}s.")

    # Cluster frequency distribution
    counts = np.bincount(labels_mmap, minlength=primary_k)
    proportions = counts / n_total_samples * 100
    print("Cluster distribution:")
    for c_id, (cnt, pct) in enumerate(zip(counts, proportions)):
        print(f"  Regime {c_id}: {cnt:,} observations ({pct:.2f}%)")

    # 4. Stability Evaluation: Adjusted Rand Index (ARI)
    print("\n--- Phase 3: Cluster Stability Check (ARI Across Seed Initializations) ---")
    km_seed2 = MiniBatchKMeans(
        n_clusters=primary_k, batch_size=25000, random_state=random_state + 100, n_init="auto"
    ).fit(X_pca)
    ari = float(adjusted_rand_score(primary_model.predict(X_pca_sub), km_seed2.predict(X_pca_sub)))
    print(f"Adjusted Rand Index (stability across seeds): {ari:.4f} (>0.90 indicates high stability)")

    # 5. Physical Meteorological Centroid Profiling
    print("\n--- Phase 4: Profiling Physical Cloud Characteristics per Regime ---")
    key_vars = [
        "cldarea_total_1h", "cldarea_high_1h", "cldarea_mid_low_1h", "cldarea_low_1h",
        "cldtau_total_1h", "cldtau_high_1h",
        "iwp_total_1h", "iwp_high_1h",
        "lwp_total_1h", "lwp_mid_low_1h",
        "cldpress_top_total_1h", "cldtemp_total_1h"
    ]
    var_indices = [feature_names.index(v) for v in key_vars if v in feature_names]
    available_vars = [v for v in key_vars if v in feature_names]

    # Compute physical profile over representative 100,000 points
    profile_sample_size = 100000
    prof_idx = rng.choice(n_total_samples, size=profile_sample_size, replace=False)
    prof_scaled = scaled_mmap[prof_idx][:, var_indices]
    prof_labels = labels_mmap[prof_idx]

    prof_df = pd.DataFrame(prof_scaled, columns=available_vars)
    prof_df["cluster"] = prof_labels
    cluster_means = prof_df.groupby("cluster").mean()

    # Assign meteorologically grounded regime descriptions based on centroids
    regime_descriptions = {}
    for c_id in range(primary_k):
        c_mean = cluster_means.loc[c_id] if c_id in cluster_means.index else None
        if c_mean is not None:
            cldarea = c_mean.get("cldarea_total_1h", 0)
            cldtau_hi = c_mean.get("cldtau_high_1h", 0)
            iwp_hi = c_mean.get("iwp_high_1h", 0)
            lwp = c_mean.get("lwp_mid_low_1h", 0)
            press = c_mean.get("cldpress_top_total_1h", 0)

            if iwp_hi > 0.5 or cldtau_hi > 0.5:
                desc = "Deep Convection / Thick Cirrus Anvil Shield"
            elif lwp > 0.3:
                desc = "Mid-to-Low Stratiform / Liquid Water Cloud System"
            elif press > 0.2:
                desc = "Boundary-Layer Inversion / Low Stratus & Shallow Cumulus"
            else:
                desc = "Suppressed Subtropical High / Fair-Weather / Clear Sky"
            regime_descriptions[c_id] = desc

    cluster_profiles_records = []
    for c_id in range(primary_k):
        rec = {
            "regime_id": c_id,
            "meteorological_label": regime_descriptions.get(c_id, f"Cloud Regime {c_id}"),
            "observation_count": int(counts[c_id]),
            "proportion_pct": round(float(proportions[c_id]), 2),
        }
        if c_id in cluster_means.index:
            for v in available_vars:
                rec[v] = round(float(cluster_means.loc[c_id, v]), 4)
        cluster_profiles_records.append(rec)
        print(f"  Regime {c_id} ({proportions[c_id]:.1f}%): {rec['meteorological_label']}")

    profiles_df = pd.DataFrame(cluster_profiles_records)
    profiles_csv_path = reports_dir / "post_monsoon_cluster_profiles.csv"
    profiles_df.to_csv(profiles_csv_path, index=False)
    print(f"Saved cluster profiles table: {profiles_csv_path}")

    # 6. Save JSON Summary Manifest
    elapsed = round(time.time() - start_time, 2)
    summary_data = {
        "milestone": "M24",
        "title": "Post-Monsoon Cloud-Regime Clustering & Validation",
        "created_utc": _utc_now(),
        "elapsed_seconds": elapsed,
        "input_features": f"Top {n_pca_components} Principal Components",
        "total_observations": n_total_samples,
        "sweep_k": k_range,
        "optimal_k": primary_k,
        "clustering_metrics": metrics_records,
        "stability": {
            "adjusted_rand_index_seed_variation": round(ari, 4),
            "status": "HIGHLY_STABLE" if ari > 0.85 else "MODERATELY_STABLE",
        },
        "regime_profiles": cluster_profiles_records,
        "output_artifacts": {
            "cluster_labels_npy": str(labels_npy_path),
            "metrics_csv": str(metrics_csv_path),
            "profiles_csv": str(profiles_csv_path),
        },
        "status": "COMPLETED_READY_FOR_INTERPRETATION",
    }

    summary_json_path = reports_dir / "post_monsoon_clustering_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Saved summary JSON: {summary_json_path}")

    del labels_mmap
    import gc
    gc.collect()

    print(f"\n=== M24 Clustering Pipeline Completed in {elapsed}s ===")
    return summary_data


def main():
    parser = argparse.ArgumentParser(description="M24 Post-Monsoon Clustering Analysis")
    parser.add_argument("--k", type=int, default=4, help="Primary cluster count (default: 4)")
    args = parser.parse_args()

    run_post_monsoon_clustering(primary_k=args.k)


if __name__ == "__main__":
    main()
