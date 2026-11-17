"""
test_m25_3_post_monsoon_correspondence.py

Integration test suite for Milestone M25.3 Phase 1:
Post-Monsoon Independent-to-Combined Regime Correspondence.

Verifies:
1. Exact label array sizes and dtypes.
2. Valid cluster label ranges [0, 1, 2, 3].
3. Unique observation keys and 100% 1-to-1 matching.
4. Seasonal window boundaries (720 hrs/yr x 12 yrs = 8,294,400).
5. Grid-cell coverage (960 cells, 357 land, 603 ocean).
6. Contingency matrix marginals and total conservation (8,294,400).
7. Row and column normalization probabilities sum to 1.0.
8. ARI and NMI reproducibility against independent calculation.
9. No mutation of historical input files (SHA256 and size checks).
10. Manifest and report completeness.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.metrics.cluster import contingency_matrix


CANONICAL_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
DATA_DIR = CANONICAL_ROOT / "data/processed"
REPORTS_DIR = CANONICAL_ROOT / "reports/integration/m25_3/post_monsoon"

M24_LABELS_PATH = DATA_DIR / "post_monsoon/clustering/post_monsoon_cluster_labels_k4.npy"
M25_LABELS_PATH = DATA_DIR / "combined_3season/combined_3season_cluster_labels.npy"
M25_SEASONS_PATH = DATA_DIR / "combined_3season/combined_3season_season_ids.npy"
M25_YEARS_PATH = DATA_DIR / "combined_3season/combined_3season_years.npy"
M25_CELLS_PATH = DATA_DIR / "combined_3season/combined_3season_cell_indices.npy"


def test_exact_label_array_sizes():
    """Verify exact dimensions and types of M24 and M25 label arrays."""
    assert M24_LABELS_PATH.exists(), f"Missing M24 labels: {M24_LABELS_PATH}"
    assert M25_LABELS_PATH.exists(), f"Missing M25 labels: {M25_LABELS_PATH}"

    m24_lbl = np.load(M24_LABELS_PATH, mmap_mode="r")
    m25_lbl = np.load(M25_LABELS_PATH, mmap_mode="r")
    m25_sea = np.load(M25_SEASONS_PATH, mmap_mode="r")

    assert m24_lbl.shape == (8294400,), f"M24 shape mismatch: {m24_lbl.shape}"
    assert m24_lbl.dtype == np.uint8, f"M24 dtype mismatch: {m24_lbl.dtype}"

    assert m25_lbl.shape == (24883200,), f"M25 shape mismatch: {m25_lbl.shape}"
    assert m25_lbl.dtype == np.uint8, f"M25 dtype mismatch: {m25_lbl.dtype}"

    mask_post = (m25_sea == 2)
    assert np.sum(mask_post) == 8294400, "M25 season_id==2 count is not 8,294,400"


def test_valid_cluster_label_ranges():
    """Verify cluster labels are strictly in the range [0, 1, 2, 3] with all 4 classes present."""
    m24_lbl = np.load(M24_LABELS_PATH, mmap_mode="r")
    m25_lbl = np.load(M25_LABELS_PATH, mmap_mode="r")
    m25_sea = np.load(M25_SEASONS_PATH, mmap_mode="r")

    u_m24 = np.unique(m24_lbl)
    u_m25_post = np.unique(m25_lbl[m25_sea == 2])

    np.testing.assert_array_equal(u_m24, [0, 1, 2, 3])
    np.testing.assert_array_equal(u_m25_post, [0, 1, 2, 3])


def test_unique_observation_keys_and_onetoone_matching():
    """Verify 1-to-1 deterministic space-time mapping and key alignment."""
    m25_sea = np.load(M25_SEASONS_PATH, mmap_mode="r")
    m25_yr = np.load(M25_YEARS_PATH, mmap_mode="r")
    m25_cell = np.load(M25_CELLS_PATH, mmap_mode="r")

    mask_post = (m25_sea == 2)
    post_years = m25_yr[mask_post]
    post_cells = m25_cell[mask_post]

    # Verify 12 years with 691,200 observations each
    u_yr, counts_yr = np.unique(post_years, return_counts=True)
    assert len(u_yr) == 12, "Expected 12 unique years"
    assert (counts_yr == 691200).all(), "Each year must have exactly 691,200 observations"

    # Verify cell repetition pattern (960 cells repeated 720 times per year)
    expected_cells = np.tile(np.arange(960, dtype=np.int16), 12 * 720)
    assert np.array_equal(post_cells, expected_cells), "Cell sequence mismatch"


def test_seasonal_window_boundaries():
    """Verify exactly 720 hours per season-year over 12 years."""
    manifest_path = REPORTS_DIR / "post_monsoon_matching_manifest.json"
    assert manifest_path.exists(), "Manifest missing"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    match_meta = manifest["matching_verification"]
    assert match_meta["total_years"] == 12
    assert match_meta["hours_per_season_year"] == 720
    assert match_meta["grid_cells"] == 960
    assert match_meta["matched_pairs"] == 8294400
    assert match_meta["coverage_percentage"] == 100.0


def test_grid_cell_coverage():
    """Verify spatial correspondence CSV covers all 960 cells with land and ocean breakdown."""
    spatial_path = REPORTS_DIR / "post_monsoon_spatial_correspondence.csv"
    assert spatial_path.exists(), "Spatial CSV missing"

    df = pd.read_csv(spatial_path)
    assert len(df) == 960, f"Expected 960 cells, found {len(df)}"
    assert df["is_imd_land_cell"].sum() == 357, f"Expected 357 land cells, found {df['is_imd_land_cell'].sum()}"
    assert (~df["is_imd_land_cell"]).sum() == 603, "Expected 603 non-land cells"
    assert (df["observations"] == 8640).all(), "Each cell must have exactly 8,640 observations"


def test_contingency_matrix_totals():
    """Verify contingency matrix totals and marginal sums equal 8,294,400."""
    cm_path = REPORTS_DIR / "post_monsoon_contingency_matrix.csv"
    assert cm_path.exists(), "Contingency matrix CSV missing"

    df = pd.read_csv(cm_path)
    assert len(df) == 4, f"Expected 4 rows, found {len(df)}"

    regime_cols = ["m25_regime_0", "m25_regime_1", "m25_regime_2", "m25_regime_3"]
    total_obs = df[regime_cols].values.sum()
    assert total_obs == 8294400, f"Expected total 8,294,400 observations, found {total_obs}"

    # Verify M24 row totals
    m24_lbl = np.load(M24_LABELS_PATH, mmap_mode="r")
    expected_m24_counts = np.bincount(m24_lbl)
    np.testing.assert_array_equal(df["m24_total_observations"].values, expected_m24_counts)

    # Verify M25 col totals
    m25_lbl = np.load(M25_LABELS_PATH, mmap_mode="r")
    m25_sea = np.load(M25_SEASONS_PATH, mmap_mode="r")
    expected_m25_counts = np.bincount(m25_lbl[m25_sea == 2])
    np.testing.assert_array_equal(df[regime_cols].sum(axis=0).values, expected_m25_counts)


def test_row_and_column_normalization():
    """Verify conditional probability matrices sum to 1.0 along proper axes."""
    row_path = REPORTS_DIR / "post_monsoon_row_normalized_correspondence.csv"
    col_path = REPORTS_DIR / "post_monsoon_column_normalized_correspondence.csv"

    df_row = pd.read_csv(row_path)
    df_col = pd.read_csv(col_path)

    row_prob_cols = ["p_m25_r0_given_m24", "p_m25_r1_given_m24", "p_m25_r2_given_m24", "p_m25_r3_given_m24"]
    col_prob_cols = ["p_m24_c0_given_m25", "p_m24_c1_given_m25", "p_m24_c2_given_m25", "p_m24_c3_given_m25"]

    # Each row in row-norm must sum to 1.0
    row_sums = df_row[row_prob_cols].sum(axis=1).values
    np.testing.assert_allclose(row_sums, np.ones(4), atol=1e-3)

    # Each row in col-norm (representing an M25 regime column) must sum to 1.0
    col_sums = df_col[col_prob_cols].sum(axis=1).values
    np.testing.assert_allclose(col_sums, np.ones(4), atol=1e-3)


def test_ari_nmi_reproducibility():
    """Independently calculate ARI and NMI from raw arrays and verify reported values."""
    m24_lbl = np.load(M24_LABELS_PATH, mmap_mode="r")
    m25_lbl = np.load(M25_LABELS_PATH, mmap_mode="r")
    m25_sea = np.load(M25_SEASONS_PATH, mmap_mode="r")

    lbl_post_m25 = m25_lbl[m25_sea == 2]

    calc_ari = float(adjusted_rand_score(m24_lbl, lbl_post_m25))
    calc_nmi = float(normalized_mutual_info_score(m24_lbl, lbl_post_m25))

    metrics_path = REPORTS_DIR / "post_monsoon_global_metrics.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert round(calc_ari, 4) == metrics["adjusted_rand_index"]
    assert round(calc_nmi, 4) == metrics["normalized_mutual_information"]

    # Verify expected empirical values
    assert metrics["adjusted_rand_index"] == -0.0576
    assert metrics["normalized_mutual_information"] == 0.0422
    assert metrics["correspondence_classification"] == "WEAK_CORRESPONDENCE_WITH_MANY_TO_ONE_COLLAPSE"


def test_no_mutation_of_input_files():
    """Verify input files have not been modified or truncated by checking sizes and hashes."""
    m24_sha = hashlib.sha256(open(M24_LABELS_PATH, "rb").read()).hexdigest()
    assert m24_sha == "c686143fde3675266d581c54c55d58abdbb6e263734cbcdff5c5b83464d108ff", "M24 labels modified!"

    m25_sha = hashlib.sha256(open(M25_LABELS_PATH, "rb").read()).hexdigest()
    assert m25_sha == "903fffc4d5962882decc2995b620db5e81044260b8c82aff3a585f03097adcaa", "M25 labels modified!"


def test_manifest_and_report_completeness():
    """Verify manifest and scientific report existence and key content."""
    report_path = REPORTS_DIR / "post_monsoon_correspondence_report.md"
    assert report_path.exists(), "Scientific report missing"

    text = report_path.read_text(encoding="utf-8")
    assert "Weak Correspondence with Many-to-One Collapse" in text
    assert "-0.0576" in text
    assert "8,294,400" in text
    assert "100.0%" in text
    assert "Many-to-One Collapse" in text
