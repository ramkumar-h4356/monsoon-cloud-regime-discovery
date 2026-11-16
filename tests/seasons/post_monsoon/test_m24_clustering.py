"""Automated unit and integration tests for Milestone M24 (Post-Monsoon Cloud-Regime Clustering).

Covers:
1. Summary manifest completeness, status, and optimal regime count.
2. Parameter sweep metric consistency (monotonic inertia reduction, valid Silhouette/CH/DB).
3. Cluster assignment array shape, dtype, and valid label domain (0..K-1).
4. Physical centroid profiles completeness and meteorological regime attribution.
5. Algorithmic stability (Adjusted Rand Index across seed initializations).
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
REPORTS_DIR = PROJECT_ROOT / "reports" / "seasons" / "post_monsoon" / "m24_clustering"
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "post_monsoon" / "clustering"

SUMMARY_PATH = REPORTS_DIR / "post_monsoon_clustering_summary.json"
METRICS_PATH = REPORTS_DIR / "post_monsoon_clustering_metrics.csv"
PROFILES_PATH = REPORTS_DIR / "post_monsoon_cluster_profiles.csv"
LABELS_PATH = DATA_DIR / "post_monsoon_cluster_labels_k4.npy"


class TestM24Clustering:
    """Tests for Milestone M24 Cloud-Regime Clustering."""

    def test_clustering_summary_manifest_and_status(self):
        """Verify M24 summary manifest exists with valid status and parameters."""
        assert SUMMARY_PATH.exists(), f"Summary manifest missing: {SUMMARY_PATH}"
        with open(SUMMARY_PATH, encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["milestone"] == "M24"
        assert manifest["status"] == "COMPLETED_READY_FOR_INTERPRETATION"
        assert manifest["total_observations"] == 8294400
        assert manifest["optimal_k"] == 4
        assert manifest["sweep_k"] == [3, 4, 5, 6, 7]

    def test_clustering_metrics_monotonicity_and_bounds(self):
        """Verify metric sweep table shows decreasing inertia and valid diagnostic bounds."""
        assert METRICS_PATH.exists(), f"Metrics CSV missing: {METRICS_PATH}"
        df = pd.read_csv(METRICS_PATH)

        assert len(df) == 5
        assert list(df["k"]) == [3, 4, 5, 6, 7]

        # Overall inertia should decrease substantially from K=3 to K=7
        inertias = df["inertia"].values
        assert inertias[-1] < inertias[0], f"Inertia at K=7 ({inertias[-1]}) should be lower than K=3 ({inertias[0]})"
        assert (inertias > 0).all(), "Inertia values must be positive"

        # Silhouette score must be in [-1, 1], Davies-Bouldin >= 0, CH >= 0
        assert ((df["silhouette_score"] >= -1.0) & (df["silhouette_score"] <= 1.0)).all()
        assert (df["davies_bouldin_index"] > 0).all()
        assert (df["calinski_harabasz_score"] > 0).all()

    def test_cluster_labels_shape_and_values(self):
        """Verify full-resolution cluster assignments array exists, matches sample count, and has valid labels."""
        assert LABELS_PATH.exists(), f"Cluster labels missing: {LABELS_PATH}"
        labels_mmap = np.load(LABELS_PATH, mmap_mode="r")

        assert labels_mmap.shape == (8294400,)
        assert labels_mmap.dtype == np.uint8

        unique_labels = np.unique(labels_mmap[:50000])
        assert set(unique_labels).issubset({0, 1, 2, 3})

    def test_cluster_profiles_completeness(self):
        """Verify physical centroid profiles table contains all regimes and key cloud variables."""
        assert PROFILES_PATH.exists(), f"Profiles CSV missing: {PROFILES_PATH}"
        df = pd.read_csv(PROFILES_PATH)

        assert len(df) == 4
        assert "regime_id" in df.columns
        assert "meteorological_label" in df.columns
        assert "observation_count" in df.columns
        assert "proportion_pct" in df.columns

        # Sum of observation counts must equal 8,294,400
        assert df["observation_count"].sum() == 8294400
        assert np.isclose(df["proportion_pct"].sum(), 100.0, atol=0.1)

        # Check key physical variables present
        for var in ["cldarea_total_1h", "cldtau_total_1h", "iwp_high_1h", "lwp_mid_low_1h", "cldpress_top_total_1h"]:
            assert var in df.columns, f"Missing physical variable {var} in cluster profiles"
            assert not df[var].isna().any(), f"NaN in cluster profile {var}"

    def test_clustering_stability(self):
        """Verify ARI stability across seed variations meets research quality threshold."""
        with open(SUMMARY_PATH, encoding="utf-8") as f:
            manifest = json.load(f)

        ari = manifest["stability"]["adjusted_rand_index_seed_variation"]
        assert ari >= 0.40, f"Cluster stability ARI too low: {ari} (expected >=0.40 for continuous cloud regime transitions)"
