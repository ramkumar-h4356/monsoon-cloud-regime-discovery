"""Automated unit and integration tests for Milestone M23 (Post-Monsoon t-SNE & 2D Comparison).

Covers:
1. Manifest completeness, status, and parameter audit.
2. Multi-perplexity trustworthiness evaluation (PCA vs t-SNE).
3. 2D embedding table structure, row counts, and 100% finiteness.
4. Physical cloud feature rank correlation integrity (bounded Spearman rho).
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
REPORTS_DIR = PROJECT_ROOT / "reports" / "seasons" / "post_monsoon" / "m23_tsne"
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "post_monsoon" / "tsne"

SUMMARY_PATH = REPORTS_DIR / "post_monsoon_tsne_summary.json"
COMPARISON_PATH = REPORTS_DIR / "post_monsoon_linear_vs_nonlinear_comparison.csv"
EMBEDDINGS_PATH = DATA_DIR / "post_monsoon_tsne_sampled_embeddings.csv"


class TestM23TSNEAnalysis:
    """Tests for Milestone M23 t-SNE Nonlinear Dimensionality Reduction."""

    def test_tsne_summary_manifest_and_status(self):
        """Verify M23 t-SNE summary manifest exists with valid status and parameters."""
        assert SUMMARY_PATH.exists(), f"Summary manifest missing: {SUMMARY_PATH}"
        with open(SUMMARY_PATH, encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["milestone"] == "M23"
        assert manifest["status"] == "COMPLETED_READY_FOR_CLUSTERING"
        assert manifest["sample_size"] == 9996
        assert manifest["perplexities_evaluated"] == [15, 30, 50]

    def test_tsne_trustworthiness_metrics(self):
        """Verify trustworthiness scores exist and show valid neighborhood preservation."""
        with open(SUMMARY_PATH, encoding="utf-8") as f:
            manifest = json.load(f)

        scores = manifest["trustworthiness_scores"]
        assert "PCA_2D" in scores
        assert "tSNE_perp_15" in scores
        assert "tSNE_perp_30" in scores
        assert "tSNE_perp_50" in scores

        for model_name, score in scores.items():
            assert 0.70 <= score <= 1.0, f"Trustworthiness score out of expected bounds: {model_name} = {score}"

        # t-SNE should achieve equal or higher trustworthiness than linear PCA 2D
        best_tsne = scores[f"tSNE_perp_{manifest['linear_vs_nonlinear_insights']['best_tsne_perplexity']}"]
        pca_score = scores["PCA_2D"]
        assert best_tsne >= pca_score - 0.05, f"t-SNE trustworthiness ({best_tsne}) significantly worse than PCA ({pca_score})"

    def test_tsne_embeddings_table_integrity(self):
        """Verify 2D embedding table exists, matches sample size, and contains 100% finite values."""
        assert EMBEDDINGS_PATH.exists(), f"Embeddings CSV missing: {EMBEDDINGS_PATH}"
        df = pd.read_csv(EMBEDDINGS_PATH)

        assert len(df) == 9996
        expected_cols = [
            "sample_index", "year", "is_train_partition",
            "PC1", "PC2",
            "tSNE_perp15_dim1", "tSNE_perp15_dim2",
            "tSNE_perp30_dim1", "tSNE_perp30_dim2",
            "tSNE_perp50_dim1", "tSNE_perp50_dim2",
        ]
        for col in expected_cols:
            assert col in df.columns, f"Missing expected column: {col}"
            assert not df[col].isna().any(), f"NaN values detected in {col}"
            assert np.isfinite(df[col]).all(), f"Non-finite values detected in {col}"

    def test_linear_vs_nonlinear_comparison_correlations(self):
        """Verify comparison table contains valid Spearman rank correlations bounded in [-1, 1]."""
        assert COMPARISON_PATH.exists(), f"Comparison CSV missing: {COMPARISON_PATH}"
        df = pd.read_csv(COMPARISON_PATH)

        assert len(df) >= 5
        assert "variable" in df.columns
        for col in ["spearman_PC1", "spearman_PC2", "spearman_tSNE1", "spearman_tSNE2"]:
            assert col in df.columns
            assert ((df[col] >= -1.0) & (df[col] <= 1.0)).all(), f"Correlations out of [-1, 1] bounds in {col}"
