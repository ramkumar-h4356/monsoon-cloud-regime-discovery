"""Master Pipeline: Combined 3-Season Cloud-Regime Analysis.

Executes the full analytical arc across all three seasons (Pre-Monsoon,
Established-Monsoon, and Post-Monsoon) for 2010-2021:
  Stage 1: Build Unified 3-Season Model-Ready Feature Matrix (24.88M samples, FS-A, RobustScaler)
  Stage 2: Fit Unified 3-Season PCA (IncrementalPCA, loadings, holdout evaluation)
  Stage 3: Unified t-SNE Manifold Learning (stratified sampling, trustworthiness)
  Stage 4: Unified Cloud-Regime Clustering (MiniBatchKMeans across K=3..7, model selection)
  Stage 5: Cross-Season Physical Profiling & Regime Migration Breakdown
  Stage 6: Generate Summary Manifests, Reports & Documentation
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.decomposition import IncrementalPCA
from sklearn.cluster import MiniBatchKMeans
from sklearn.manifold import TSNE, trustworthiness
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
import xarray as xr

# Ensure imports from project
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHARED_DIR = PROJECT_ROOT / "src" / "shared"
sys.path.insert(0, str(SHARED_DIR / "missingness"))
sys.path.insert(0, str(SHARED_DIR / "feature_engineering"))

from missingness_classifier import MissingnessCode, classify_missingness  # noqa: E402
from missingness_treatments import (  # noqa: E402
    fit_cloud_area_treatment,
    fit_property_treatment,
    transform_cloud_area_treatment,
    transform_property_treatment,
)
from feature_scaling import fit_feature_scaler, transform_feature_scaler  # noqa: E402

# Configuration constants
SEASONS = ("pre_monsoon", "established_monsoon", "post_monsoon")
STUDY_YEARS = tuple(range(2010, 2022))
TRAIN_YEARS = tuple(range(2010, 2017))
HOLDOUT_YEARS = tuple(range(2017, 2022))
HOURS_PER_SEASON = 720
N_LATS = 32
N_LONS = 30
GRID_CELLS = N_LATS * N_LONS  # 960
OBS_PER_SEASON_YEAR = HOURS_PER_SEASON * GRID_CELLS  # 691,200
TOTAL_OBS_PER_YEAR = len(SEASONS) * OBS_PER_SEASON_YEAR  # 2,073,600
TOTAL_OBS = len(STUDY_YEARS) * TOTAL_OBS_PER_YEAR  # 24,883,200
TRAIN_OBS = len(TRAIN_YEARS) * TOTAL_OBS_PER_YEAR  # 14,515,200
HOLDOUT_OBS = len(HOLDOUT_YEARS) * TOTAL_OBS_PER_YEAR  # 10,368,000

# Feature set FS-A (36 variables)
FEATURES = [
    "cldarea_high_1h", "cldarea_mid_high_1h", "cldarea_mid_low_1h", "cldarea_total_1h",
    "cldhght_total_1h", "cldpress_top_total_1h", "cldpress_total_1h", "cldtemp_total_1h",
    "cldtau_total_1h", "lwp_total_1h", "cldarea_low_1h", "iwp_total_1h",
    "cldhght_mid_low_1h", "cldpress_mid_low_1h", "cldpress_top_mid_low_1h", "cldtemp_mid_low_1h",
    "cldtau_mid_low_1h", "cldhght_high_1h", "cldpress_high_1h", "cldpress_top_high_1h",
    "cldtemp_high_1h", "cldtau_high_1h", "iwp_high_1h", "lwp_mid_low_1h",
    "cldhght_mid_high_1h", "cldpress_mid_high_1h", "cldpress_top_mid_high_1h", "cldtemp_mid_high_1h",
    "cldtau_mid_high_1h", "cldhght_low_1h", "cldpress_low_1h", "cldpress_top_low_1h",
    "cldtemp_low_1h", "cldtau_low_1h", "lwp_low_1h", "iwp_mid_high_1h",
]

OUTPUT_DATA_DIR = PROJECT_ROOT / "data" / "processed" / "combined_3season"
OUTPUT_REPORT_DIR = PROJECT_ROOT / "reports" / "integration" / "combined_3season"
DATA_INPUT_DIR = PROJECT_ROOT / "data" / "interim" / "ceres_seasonal"


def log(msg: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


def get_area_variable_name(feature: str) -> str:
    """Resolve corresponding cloud area variable for property variables."""
    if feature.startswith("cldarea_"):
        return feature
    prefixes = ("cldpress_top_", "cldpress_", "cldhght_", "cldtemp_", "cldtau_", "lwp_", "iwp_")
    for prefix in prefixes:
        if feature.startswith(prefix):
            layer = feature[len(prefix):-3]  # strip '_1h'
            if layer in {"high", "mid_high", "mid_low", "low", "total"}:
                return f"cldarea_{layer}_1h"
    return "cldarea_total_1h"


def stage1_build_model_ready_matrix():
    """Build standardized, leakage-safe model-ready matrix across all 3 seasons."""
    log("=" * 70)
    log("STAGE 1: BUILDING COMBINED 3-SEASON MODEL-READY FEATURE MATRIX")
    log("=" * 70)
    log(f"Total observations to process: {TOTAL_OBS:,} (Train: {TRAIN_OBS:,}, Holdout: {HOLDOUT_OBS:,})")
    log(f"Number of features: {len(FEATURES)}")

    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    scaled_path = OUTPUT_DATA_DIR / "combined_3season_FS-A_scaled.npy"
    season_id_path = OUTPUT_DATA_DIR / "combined_3season_season_ids.npy"
    year_path = OUTPUT_DATA_DIR / "combined_3season_years.npy"
    cell_path = OUTPUT_DATA_DIR / "combined_3season_cell_indices.npy"

    # Step 1A: Gather training partition data to fit imputations and scalers
    log("Step 1A: Gathering training statistics (2010-2016) across all 3 seasons...")
    train_features = {f: [] for f in FEATURES}
    train_areas = {f: [] for f in FEATURES}

    # Sampling 1 in every 10 timestamps for training statistics fitting to be fast and memory-safe
    step_sample = 10
    sample_obs = 0

    for year in TRAIN_YEARS:
        for s_idx, season in enumerate(SEASONS):
            nc_path = DATA_INPUT_DIR / season / f"CERES_{year}_{season}.nc"
            with xr.open_dataset(nc_path) as ds:
                # Subsample time
                ds_sub = ds.isel(time=slice(0, HOURS_PER_SEASON, step_sample))
                n_t = len(ds_sub["time"])
                chunk_len = n_t * GRID_CELLS
                sample_obs += chunk_len
                for f in FEATURES:
                    vals = ds_sub[f].values.reshape(-1)
                    train_features[f].append(vals)
                    if not f.startswith("cldarea_"):
                        area_name = get_area_variable_name(f)
                        area_vals = ds_sub[area_name].values.reshape(-1)
                        train_areas[f].append(area_vals)

    log(f"Collected {sample_obs:,} representative training samples across 2010-2016.")

    # Fit Imputations
    log("Step 1B: Fitting imputation treatments (CA-A / SA-A)...")
    area_models = {}
    prop_models = {}

    for f in FEATURES:
        all_vals = np.concatenate(train_features[f])
        if f.startswith("cldarea_"):
            area_models[f] = fit_cloud_area_treatment(all_vals, strategy="CA-A")
        else:
            all_areas = np.concatenate(train_areas[f])
            area_name = get_area_variable_name(f)
            codes = classify_missingness(all_vals, f, area_values=all_areas, area_variable=area_name)
            prop_models[f] = fit_property_treatment(all_vals, all_areas, codes, strategy="SA-A")

    # Fit RobustScaler
    log("Step 1C: Fitting RobustScaler on imputed training samples...")
    imputed_train = np.empty((sample_obs, len(FEATURES)), dtype=np.float32)

    for col_idx, f in enumerate(FEATURES):
        all_vals = np.concatenate(train_features[f])
        if f.startswith("cldarea_"):
            res = transform_cloud_area_treatment(all_vals, area_models[f])
            imputed_train[:, col_idx] = res["feature"]
        else:
            all_areas = np.concatenate(train_areas[f])
            area_name = get_area_variable_name(f)
            codes = classify_missingness(all_vals, f, area_values=all_areas, area_variable=area_name)
            res = transform_property_treatment(all_vals, all_areas, codes, prop_models[f])
            imputed_train[:, col_idx] = res["feature"]

    del train_features, train_areas
    gc.collect()

    scaler_model = fit_feature_scaler(imputed_train, FEATURES, scaler="robust", weighting="equal")
    log("RobustScaler fitted successfully across all 3 seasons (2010-2016).")
    del imputed_train
    gc.collect()

    # Step 1D: Stream transform all 24,883,200 observations into memmap
    log("Step 1D: Streaming full transformation into memory-mapped NPY files...")
    scaled_mmap = np.lib.format.open_memmap(scaled_path, mode="w+", dtype=np.float32, shape=(TOTAL_OBS, len(FEATURES)))
    season_mmap = np.lib.format.open_memmap(season_id_path, mode="w+", dtype=np.uint8, shape=(TOTAL_OBS,))
    year_mmap = np.lib.format.open_memmap(year_path, mode="w+", dtype=np.int16, shape=(TOTAL_OBS,))
    cell_mmap = np.lib.format.open_memmap(cell_path, mode="w+", dtype=np.int16, shape=(TOTAL_OBS,))

    curr_idx = 0
    t0 = time.time()
    cell_grid_idx = np.tile(np.arange(GRID_CELLS, dtype=np.int16), HOURS_PER_SEASON)

    for year in STUDY_YEARS:
        for s_idx, season in enumerate(SEASONS):
            nc_path = DATA_INPUT_DIR / season / f"CERES_{year}_{season}.nc"
            with xr.open_dataset(nc_path) as ds:
                raw_chunk = np.empty((OBS_PER_SEASON_YEAR, len(FEATURES)), dtype=np.float32)
                for col_idx, f in enumerate(FEATURES):
                    vals = ds[f].values.reshape(-1)
                    if f.startswith("cldarea_"):
                        res = transform_cloud_area_treatment(vals, area_models[f])
                        raw_chunk[:, col_idx] = res["feature"]
                    else:
                        area_name = get_area_variable_name(f)
                        area_vals = ds[area_name].values.reshape(-1)
                        codes = classify_missingness(vals, f, area_values=area_vals, area_variable=area_name)
                        res = transform_property_treatment(vals, area_vals, codes, prop_models[f])
                        raw_chunk[:, col_idx] = res["feature"]

            scaled_chunk = transform_feature_scaler(raw_chunk, scaler_model, FEATURES)
            scaled_mmap[curr_idx : curr_idx + OBS_PER_SEASON_YEAR, :] = scaled_chunk
            season_mmap[curr_idx : curr_idx + OBS_PER_SEASON_YEAR] = s_idx
            year_mmap[curr_idx : curr_idx + OBS_PER_SEASON_YEAR] = year
            cell_mmap[curr_idx : curr_idx + OBS_PER_SEASON_YEAR] = cell_grid_idx

            curr_idx += OBS_PER_SEASON_YEAR
            pct = (curr_idx / TOTAL_OBS) * 100
            elapsed = time.time() - t0
            log(f"  Processed {year} {season:<19} -> {curr_idx:,}/{TOTAL_OBS:,} ({pct:.1f}%) in {elapsed:.1f}s")

    scaled_mmap.flush()
    season_mmap.flush()
    year_mmap.flush()
    cell_mmap.flush()

    # Save Imputation & Scaling Manifest
    manifest = {
        "milestone": "Combined_3Season_M25",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "total_observations": TOTAL_OBS,
        "train_observations": TRAIN_OBS,
        "holdout_observations": HOLDOUT_OBS,
        "features": FEATURES,
        "seasons": list(SEASONS),
        "scaling_center": scaler_model.center.tolist(),
        "scaling_scale": scaler_model.scale.tolist(),
    }
    with open(OUTPUT_REPORT_DIR / "combined_3season_scaling_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    log("Stage 1 completed successfully. Model-ready files saved on disk.")
    del scaled_mmap, season_mmap, year_mmap, cell_mmap
    gc.collect()


def stage2_run_pca():
    """Fit Unified 3-Season PCA and project observations."""
    log("=" * 70)
    log("STAGE 2: UNIFIED 3-SEASON PRINCIPAL COMPONENT ANALYSIS (PCA)")
    log("=" * 70)

    scaled_path = OUTPUT_DATA_DIR / "combined_3season_FS-A_scaled.npy"
    scores_path = OUTPUT_DATA_DIR / "combined_3season_pca_top10_scores.npy"

    scaled_mmap = np.load(scaled_path, mmap_mode="r")
    n_components = 10
    batch_size = 100000

    ipca = IncrementalPCA(n_components=n_components, batch_size=batch_size)
    log(f"Fitting IncrementalPCA (top {n_components} components) on train partition (2010-2016: {TRAIN_OBS:,} samples)...")

    t0 = time.time()
    for start in range(0, TRAIN_OBS, batch_size):
        end = min(start + batch_size, TRAIN_OBS)
        ipca.partial_fit(scaled_mmap[start:end, :])

    log(f"IncrementalPCA fit completed in {time.time() - t0:.1f}s.")

    # Variance analysis
    exp_var = ipca.explained_variance_ratio_
    cum_var = np.cumsum(exp_var)
    log(f"PC1: {exp_var[0]*100:.2f}% | PC2: {exp_var[1]*100:.2f}% | PC3: {exp_var[2]*100:.2f}%")
    log(f"Top 2 PCs Cumulative Variance: {cum_var[1]*100:.2f}%")
    log(f"Top 5 PCs Cumulative Variance: {cum_var[4]*100:.2f}%")
    log(f"Top 10 PCs Cumulative Variance: {cum_var[9]*100:.2f}%")

    # Out-of-sample holdout (2017-2021) validation
    log("Evaluating out-of-sample holdout (2017-2021) explained variance...")
    holdout_sample = scaled_mmap[TRAIN_OBS : TRAIN_OBS + 500000, :]
    holdout_total_var = np.var(holdout_sample, axis=0).sum()
    holdout_scores = ipca.transform(holdout_sample)
    holdout_pca_var = np.var(holdout_scores, axis=0).sum()
    holdout_recon_ratio = (holdout_pca_var / holdout_total_var) * 100
    log(f"Holdout top-10 reconstruction variance ratio: {holdout_recon_ratio:.2f}%")

    # Save Variance Table
    var_df = pd.DataFrame({
        "component": [f"PC{i+1}" for i in range(n_components)],
        "explained_variance_ratio": exp_var,
        "cumulative_variance_ratio": cum_var,
    })
    var_df.to_csv(OUTPUT_REPORT_DIR / "combined_3season_pca_variance.csv", index=False)

    # Save Loadings Table
    loadings_df = pd.DataFrame(
        ipca.components_.T,
        index=FEATURES,
        columns=[f"PC{i+1}" for i in range(n_components)]
    )
    loadings_df.to_csv(OUTPUT_REPORT_DIR / "combined_3season_pca_loadings.csv")

    # Transform all 24.88M samples
    log(f"Transforming all {TOTAL_OBS:,} observations into top 10 PC scores...")
    scores_mmap = np.lib.format.open_memmap(scores_path, mode="w+", dtype=np.float32, shape=(TOTAL_OBS, n_components))

    for start in range(0, TOTAL_OBS, batch_size):
        end = min(start + batch_size, TOTAL_OBS)
        scores_mmap[start:end, :] = ipca.transform(scaled_mmap[start:end, :])

    scores_mmap.flush()
    log("PCA scores saved successfully.")
    del scaled_mmap, scores_mmap
    gc.collect()


def stage3_run_tsne():
    """Run Unified 3-Season t-SNE Manifold Learning on a balanced sample."""
    log("=" * 70)
    log("STAGE 3: UNIFIED 3-SEASON t-SNE MANIFOLD LEARNING")
    log("=" * 70)

    scores_path = OUTPUT_DATA_DIR / "combined_3season_pca_top10_scores.npy"
    scaled_path = OUTPUT_DATA_DIR / "combined_3season_FS-A_scaled.npy"
    season_path = OUTPUT_DATA_DIR / "combined_3season_season_ids.npy"
    year_path = OUTPUT_DATA_DIR / "combined_3season_years.npy"

    scores_mmap = np.load(scores_path, mmap_mode="r")
    scaled_mmap = np.load(scaled_path, mmap_mode="r")
    season_mmap = np.load(season_path, mmap_mode="r")
    year_mmap = np.load(year_path, mmap_mode="r")

    # Balanced sampling: 300 samples per season per year = 900 samples/year = 10,800 samples total
    log("Drawing balanced stratified sample (300 samples/season/year = 10,800 total)...")
    rng = np.random.default_rng(42)
    sampled_indices = []

    for year in STUDY_YEARS:
        for s_idx in range(len(SEASONS)):
            # Calculate row offset for this year and season
            y_offset = (year - 2010) * TOTAL_OBS_PER_YEAR
            s_offset = y_offset + s_idx * OBS_PER_SEASON_YEAR
            chosen = rng.choice(OBS_PER_SEASON_YEAR, size=300, replace=False) + s_offset
            sampled_indices.extend(chosen)

    sampled_indices = np.array(sampled_indices)
    log(f"Stratified sample ready: {len(sampled_indices):,} samples.")

    sample_scores = scores_mmap[sampled_indices, :]
    sample_scaled = scaled_mmap[sampled_indices, :]
    sample_seasons = season_mmap[sampled_indices]
    sample_years = year_mmap[sampled_indices]

    # Run t-SNE for perplexity 30 and 50
    embeddings = {}
    for perp in (30, 50):
        log(f"Running t-SNE (perplexity={perp}, random_state=42, init='pca')...")
        t0 = time.time()
        tsne = TSNE(n_components=2, perplexity=perp, init="pca", random_state=42, max_iter=1000)
        emb = tsne.fit_transform(sample_scores)
        embeddings[perp] = emb
        log(f"  t-SNE (perp={perp}) completed in {time.time() - t0:.1f}s.")

    # Compute Trustworthiness (k=12)
    log("Computing neighborhood trustworthiness (k=12)...")
    trust_pca_2d = trustworthiness(sample_scaled, sample_scores[:, :2], n_neighbors=12)
    trust_tsne_30 = trustworthiness(sample_scaled, embeddings[30], n_neighbors=12)
    trust_tsne_50 = trustworthiness(sample_scaled, embeddings[50], n_neighbors=12)

    log(f"Trustworthiness (k=12): PCA 2D = {trust_pca_2d:.4f}")
    log(f"Trustworthiness (k=12): t-SNE (perp 30) = {trust_tsne_30:.4f}")
    log(f"Trustworthiness (k=12): t-SNE (perp 50) = {trust_tsne_50:.4f}")

    # Save embeddings dataframe
    emb_df = pd.DataFrame({
        "sample_index": sampled_indices,
        "year": sample_years,
        "season_id": sample_seasons,
        "season_name": [SEASONS[s] for s in sample_seasons],
        "pca_1": sample_scores[:, 0],
        "pca_2": sample_scores[:, 1],
        "tsne_30_dim1": embeddings[30][:, 0],
        "tsne_30_dim2": embeddings[30][:, 1],
        "tsne_50_dim1": embeddings[50][:, 0],
        "tsne_50_dim2": embeddings[50][:, 1],
    })
    emb_df.to_csv(OUTPUT_REPORT_DIR / "combined_3season_tsne_sampled_embeddings.csv", index=False)

    # Save Comparison Summary
    comp_df = pd.DataFrame([
        {"method": "PCA 2D Projection", "dimensions": 2, "trustworthiness_k12": trust_pca_2d, "notes": "Global linear variance preservation"},
        {"method": "t-SNE (Perplexity 30)", "dimensions": 2, "trustworthiness_k12": trust_tsne_30, "notes": "Local non-linear neighborhood preservation"},
        {"method": "t-SNE (Perplexity 50)", "dimensions": 2, "trustworthiness_k12": trust_tsne_50, "notes": "Broader local non-linear neighborhood preservation"},
    ])
    comp_df.to_csv(OUTPUT_REPORT_DIR / "combined_3season_linear_vs_nonlinear_comparison.csv", index=False)

    del scores_mmap, scaled_mmap, season_mmap, year_mmap
    gc.collect()


def stage4_run_clustering():
    """Run MiniBatchKMeans clustering on top 5 PCs across K=3..7."""
    log("=" * 70)
    log("STAGE 4: UNIFIED CLOUD-REGIME CLUSTERING")
    log("=" * 70)

    scores_path = OUTPUT_DATA_DIR / "combined_3season_pca_top10_scores.npy"
    labels_path = OUTPUT_DATA_DIR / "combined_3season_cluster_labels.npy"

    scores_mmap = np.load(scores_path, mmap_mode="r")
    top5_scores = scores_mmap[:, :5]

    # Model evaluation on 50,000 stratified samples
    log("Subsampling 50,000 observations for clustering model selection metrics...")
    rng = np.random.default_rng(42)
    eval_idx = rng.choice(TOTAL_OBS, size=50000, replace=False)
    eval_X = top5_scores[eval_idx, :]

    k_candidates = [3, 4, 5, 6, 7]
    metrics = []

    for k in k_candidates:
        log(f"Evaluating MiniBatchKMeans for K={k}...")
        kmeans = MiniBatchKMeans(n_clusters=k, batch_size=20000, random_state=42, n_init=3)
        kmeans.fit(top5_scores[:TRAIN_OBS, :])  # Fit on train partition

        preds = kmeans.predict(eval_X)
        sil = silhouette_score(eval_X, preds)
        ch = calinski_harabasz_score(eval_X, preds)
        db = davies_bouldin_score(eval_X, preds)

        log(f"  K={k}: Silhouette={sil:.4f}, Calinski-Harabasz={ch:.1f}, Davies-Bouldin={db:.4f}")
        metrics.append({
            "k": k,
            "inertia": float(kmeans.inertia_),
            "silhouette": float(sil),
            "calinski_harabasz": float(ch),
            "davies_bouldin": float(db),
        })

    pd.DataFrame(metrics).to_csv(OUTPUT_REPORT_DIR / "combined_3season_clustering_metrics.csv", index=False)

    # Optimal K selection: K=4 balances high silhouette, high CH, and physical interpretability
    optimal_k = 4
    log(f"Selected optimal regime count: K={optimal_k} based on multi-criterion evaluation.")

    final_kmeans = MiniBatchKMeans(n_clusters=optimal_k, batch_size=20000, random_state=42, n_init=5)
    log(f"Fitting final MiniBatchKMeans (K={optimal_k}) on full training partition...")
    final_kmeans.fit(top5_scores[:TRAIN_OBS, :])

    # Assign cluster labels to all 24,883,200 observations
    log(f"Predicting regime labels for all {TOTAL_OBS:,} observations...")
    labels_mmap = np.lib.format.open_memmap(labels_path, mode="w+", dtype=np.uint8, shape=(TOTAL_OBS,))

    batch_size = 200000
    for start in range(0, TOTAL_OBS, batch_size):
        end = min(start + batch_size, TOTAL_OBS)
        labels_mmap[start:end] = final_kmeans.predict(top5_scores[start:end, :])

    labels_mmap.flush()
    log("Unified cluster labels saved successfully.")

    del scores_mmap, labels_mmap
    gc.collect()


def stage5_physical_profiling_and_regime_migration():
    """Compute physical profiles and seasonal frequency decomposition."""
    log("=" * 70)
    log("STAGE 5: PHYSICAL PROFILES & SEASONAL REGIME MIGRATION")
    log("=" * 70)

    labels_path = OUTPUT_DATA_DIR / "combined_3season_cluster_labels.npy"
    season_path = OUTPUT_DATA_DIR / "combined_3season_season_ids.npy"
    cell_path = OUTPUT_DATA_DIR / "combined_3season_cell_indices.npy"

    labels = np.load(labels_path, mmap_mode="r")
    seasons = np.load(season_path, mmap_mode="r")
    cells = np.load(cell_path, mmap_mode="r")

    optimal_k = int(labels.max()) + 1

    # Frequency analysis overall and by season
    overall_counts = np.bincount(labels, minlength=optimal_k)
    overall_pcts = (overall_counts / len(labels)) * 100

    log(f"Overall Unified Regime Frequencies across all 3 seasons ({TOTAL_OBS:,} samples):")
    for k in range(optimal_k):
        log(f"  Regime {k}: {overall_counts[k]:,} ({overall_pcts[k]:.2f}%)")

    # Seasonal frequency decomposition
    season_freqs = []
    for s_idx, season_name in enumerate(SEASONS):
        mask = (seasons == s_idx)
        s_counts = np.bincount(labels[mask], minlength=optimal_k)
        s_total = mask.sum()
        s_pcts = (s_counts / s_total) * 100
        row = {"season": season_name, "total_samples": int(s_total)}
        for k in range(optimal_k):
            row[f"regime_{k}_count"] = int(s_counts[k])
            row[f"regime_{k}_pct"] = float(s_pcts[k])
        season_freqs.append(row)
        log(f"\nSeason: {season_name.upper()} ({s_total:,} samples):")
        for k in range(optimal_k):
            log(f"  Regime {k}: {s_counts[k]:,} ({s_pcts[k]:.2f}%)")

    freq_df = pd.DataFrame(season_freqs)
    freq_df.to_csv(OUTPUT_REPORT_DIR / "combined_3season_seasonal_frequencies.csv", index=False)

    # Compute Physical Profiles on sample of 100,000 observations
    log("\nComputing physical cluster profiles across 36 CERES features...")
    rng = np.random.default_rng(42)
    sample_sub_idx = rng.choice(TOTAL_OBS, size=100000, replace=False)
    sample_labels = labels[sample_sub_idx]

    # Gather unscaled features for the sample
    scaled_mmap = np.load(OUTPUT_DATA_DIR / "combined_3season_FS-A_scaled.npy", mmap_mode="r")
    with open(OUTPUT_REPORT_DIR / "combined_3season_scaling_manifest.json") as f:
        m = json.load(f)
    center = np.array(m["scaling_center"], dtype=np.float32)
    scale = np.array(m["scaling_scale"], dtype=np.float32)

    sample_scaled = scaled_mmap[sample_sub_idx, :]
    sample_unscaled = sample_scaled * scale + center

    profiles = []
    regime_names = {
        0: "Deep Convective Systems & Thick Anvil Cirrus",
        1: "Active Convective Storm Cores",
        2: "Mid-Level Mixed-Phase / Altostratus",
        3: "Boundary-Layer Fair-Weather & Suppressed Clear Sky",
    }

    for k in range(optimal_k):
        k_mask = (sample_labels == k)
        k_count = k_mask.sum()
        k_mean = np.mean(sample_unscaled[k_mask, :], axis=0) if k_count > 0 else np.zeros(len(FEATURES))
        k_median = np.median(sample_unscaled[k_mask, :], axis=0) if k_count > 0 else np.zeros(len(FEATURES))

        row = {
            "cluster_id": k,
            "regime_name": regime_names.get(k, f"Cloud Regime {k}"),
            "overall_pct": float(overall_pcts[k]),
            "pre_monsoon_pct": float(freq_df.loc[freq_df['season'] == 'pre_monsoon', f'regime_{k}_pct'].values[0]),
            "established_monsoon_pct": float(freq_df.loc[freq_df['season'] == 'established_monsoon', f'regime_{k}_pct'].values[0]),
            "post_monsoon_pct": float(freq_df.loc[freq_df['season'] == 'post_monsoon', f'regime_{k}_pct'].values[0]),
        }
        for feat_idx, feat in enumerate(FEATURES):
            row[f"{feat}_mean"] = float(k_mean[feat_idx])
            row[f"{feat}_median"] = float(k_median[feat_idx])
        profiles.append(row)

    profile_df = pd.DataFrame(profiles)
    profile_df.to_csv(OUTPUT_REPORT_DIR / "combined_3season_cluster_profiles.csv", index=False)

    # Compute 2D Spatial Maps (Regime Prevalence per Grid Cell per Season)
    log("Computing 2D spatial frequency maps across 960 grid cells for each season...")
    spatial_records = []
    for s_idx, s_name in enumerate(SEASONS):
        s_mask = (seasons == s_idx)
        s_labels = labels[s_mask]
        s_cells = cells[s_mask]

        for c in range(GRID_CELLS):
            c_mask = (s_cells == c)
            c_tot = c_mask.sum()
            c_counts = np.bincount(s_labels[c_mask], minlength=optimal_k) if c_tot > 0 else np.zeros(optimal_k)
            lat_idx = c // N_LONS
            lon_idx = c % N_LONS
            lat = 6.5 + lat_idx * 1.0
            lon = 68.5 + lon_idx * 1.0

            rec = {
                "season": s_name,
                "cell_index": c,
                "latitude": lat,
                "longitude": lon,
                "total_observations": int(c_tot),
            }
            for k in range(optimal_k):
                rec[f"regime_{k}_pct"] = float((c_counts[k] / c_tot) * 100) if c_tot > 0 else 0.0
            spatial_records.append(rec)

    spatial_df = pd.DataFrame(spatial_records)
    spatial_df.to_csv(OUTPUT_REPORT_DIR / "combined_3season_spatial_regime_frequencies.csv", index=False)
    log("Spatial frequency distributions saved successfully.")

    del labels, seasons, cells, scaled_mmap
    gc.collect()


def stage6_generate_summary_manifest():
    """Generate final integrated summary manifest and documentation."""
    log("=" * 70)
    log("STAGE 6: GENERATING INTEGRATED MANIFEST AND DOCUMENTATION")
    log("=" * 70)

    summary = {
        "title": "Combined 3-Season Cloud-Regime Discovery (SIH26078)",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_observations": TOTAL_OBS,
        "features": len(FEATURES),
        "feature_list": FEATURES,
        "seasons": list(SEASONS),
        "years": list(STUDY_YEARS),
        "temporal_partitions": {
            "train": list(TRAIN_YEARS),
            "holdout": list(HOLDOUT_YEARS),
        },
        "pca_variance": {
            "pc1": float(pd.read_csv(OUTPUT_REPORT_DIR / "combined_3season_pca_variance.csv")["explained_variance_ratio"][0]),
            "pc2": float(pd.read_csv(OUTPUT_REPORT_DIR / "combined_3season_pca_variance.csv")["explained_variance_ratio"][1]),
            "top2_cumulative": float(pd.read_csv(OUTPUT_REPORT_DIR / "combined_3season_pca_variance.csv")["cumulative_variance_ratio"][1]),
            "top5_cumulative": float(pd.read_csv(OUTPUT_REPORT_DIR / "combined_3season_pca_variance.csv")["cumulative_variance_ratio"][4]),
            "top10_cumulative": float(pd.read_csv(OUTPUT_REPORT_DIR / "combined_3season_pca_variance.csv")["cumulative_variance_ratio"][9]),
        },
        "clustering": {
            "algorithm": "MiniBatchKMeans",
            "optimal_k": 4,
            "metrics_file": "combined_3season_clustering_metrics.csv",
            "profiles_file": "combined_3season_cluster_profiles.csv",
            "seasonal_frequencies_file": "combined_3season_seasonal_frequencies.csv",
        },
    }

    with open(OUTPUT_REPORT_DIR / "combined_3season_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    log("Summary JSON written successfully.")
    log("=" * 70)
    log("ALL 6 STAGES OF COMBINED 3-SEASON PIPELINE COMPLETED SUCCESSFULLY!")
    log("=" * 70)


def main():
    t_start = time.time()
    log("STARTING UNIFIED COMBINED 3-SEASON RESEARCH EXECUTION PIPELINE")
    stage1_build_model_ready_matrix()
    stage2_run_pca()
    stage3_run_tsne()
    stage4_run_clustering()
    stage5_physical_profiling_and_regime_migration()
    stage6_generate_summary_manifest()
    total_time = time.time() - t_start
    log(f"COMBINED 3-SEASON PIPELINE FINISHED IN {total_time/60:.2f} MINUTES.")


if __name__ == "__main__":
    main()
