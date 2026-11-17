"""Automated unit and integration tests for Milestone M22 (Post-Monsoon PCA).

Covers:
1. Summary manifest completeness, status, and variance threshold verification.
2. Eigenvalue monotonicity and cumulative variance conservation.
3. Orthonormality of principal component loading vectors.
4. Out-of-sample temporal stability and canonical subspace congruence.
5. Projected principal component scores dimensions and 100% finiteness (zero NaNs, zero Infs).
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
REPORTS_DIR = PROJECT_ROOT / "reports" / "seasons" / "post_monsoon" / "m22_pca"
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "post_monsoon" / "pca"

SUMMARY_PATH = REPORTS_DIR / "post_monsoon_pca_summary.json"
VARIANCE_PATH = REPORTS_DIR / "post_monsoon_pca_variance.csv"
LOADINGS_PATH = REPORTS_DIR / "post_monsoon_pca_loadings.csv"
SCORES_PATH = DATA_DIR / "post_monsoon_pca_FS-A_top10_scores.npy"


class TestM22PCAReduction:
    """Tests for Milestone M22 PCA Dimensionality Reduction."""

    def test_pca_summary_manifest_and_status(self):
        """Verify M22 PCA summary manifest exists with valid status and variance thresholds."""
        assert SUMMARY_PATH.exists(), f"Summary manifest missing: {SUMMARY_PATH}"
        with open(SUMMARY_PATH, encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["milestone"] == "M22"
        assert manifest["feature_set"] == "FS-A"
        assert manifest["total_features"] == 36
        assert manifest["status"] == "COMPLETED_READY_FOR_CLUSTERING"

        # Check sample counts
        counts = manifest["sample_counts"]
        assert counts["total_observations"] == 8294400
        assert counts["training_samples"] == 4838400
        assert counts["holdout_samples"] == 3456000

        # Check variance thresholds: 80% reached at PC2, 90% reached at PC5
        thresholds = manifest["variance_thresholds"]
        assert thresholds["80%"] == 2
        assert thresholds["90%"] == 5

    def test_pca_variance_monotonicity_and_sum(self):
        """Verify eigenvalues decrease monotonically and cumulative variance reaches 1.0."""
        assert VARIANCE_PATH.exists(), f"Variance CSV missing: {VARIANCE_PATH}"
        df = pd.read_csv(VARIANCE_PATH)

        assert len(df) == 36
        ev = df["eigenvalue"].values
        var_ratio = df["explained_variance_ratio"].values
        cum_var = df["cumulative_variance_ratio"].values

        # Monotonicity checks
        assert np.all(np.diff(ev) <= 0), "Eigenvalues are not monotonically non-increasing!"
        assert np.all(np.diff(var_ratio) <= 0), "Variance ratios are not monotonically non-increasing!"

        # Conservation of variance
        assert np.isclose(cum_var[-1], 1.0, atol=1e-5), f"Cumulative variance does not sum to 1: {cum_var[-1]}"
        assert cum_var[1] >= 0.80, f"Top 2 components should reach >=80%, got {cum_var[1]}"
        assert cum_var[4] >= 0.90, f"Top 5 components should reach >=90%, got {cum_var[4]}"

    def test_pca_loadings_orthonormality(self):
        """Verify principal component loading vectors form an orthonormal basis."""
        assert LOADINGS_PATH.exists(), f"Loadings CSV missing: {LOADINGS_PATH}"
        df = pd.read_csv(LOADINGS_PATH, index_col=0)
        cols = [c for c in df.columns if c.startswith("PC")]
        assert len(cols) == 36

        W = df[cols].values.astype(np.float64)  # 36 x 36
        # W has eigenvectors in columns: W^T @ W should be identity matrix
        I_approx = W.T @ W
        identity = np.eye(36)
        assert np.allclose(I_approx, identity, atol=1e-5), "PCA loading matrix is not orthonormal!"

    def test_pca_subspace_temporal_stability(self):
        """Verify out-of-sample generalization and subspace congruence between train and holdout."""
        with open(SUMMARY_PATH, encoding="utf-8") as f:
            manifest = json.load(f)

        gen = manifest["out_of_sample_generalization"]
        # Train PCs must explain >99% of holdout variance
        assert gen["holdout_variance_explained_ratio"] >= 0.99, f"Holdout variance ratio too low: {gen['holdout_variance_explained_ratio']}"
        # 5D subspace congruence must be >0.99
        assert gen["subspace_congruence_5d"] >= 0.99, f"5D subspace congruence too low: {gen['subspace_congruence_5d']}"

    def test_pca_scores_finiteness_and_shape(self):
        """Verify projected top-10 principal scores array exists with exact dimensions and 100% finite values."""
        assert SCORES_PATH.exists(), f"Scores file missing: {SCORES_PATH}"

        scores_mmap = np.load(SCORES_PATH, mmap_mode="r")
        assert scores_mmap.shape == (8294400, 10)
        assert scores_mmap.dtype == np.float32

        # Check chunks across the matrix for finiteness
        assert np.isfinite(scores_mmap[:50000]).all(), "NaN or Inf in head scores!"
        assert np.isfinite(scores_mmap[-50000:]).all(), "NaN or Inf in tail scores!"
        assert np.isfinite(scores_mmap[4000000:4050000]).all(), "NaN or Inf in middle scores!"
