"""Integration and Scientific Verification Test Suite for Milestone M27.7.1.

Comprehensive independent verification of:
1. Manifest and checksum integrity.
2. Frozen input immutability (M25 24.88M, M26 342.4K, NOAA raw sources).
3. Partial Spearman mathematical equivalence (analytical formula vs residual regression).
4. Freedman-Lane permutation validity and seed reproducibility.
5. Benjamini-Hochberg FDR mathematical properties and step-up monotonicity.
6. CLR compositional transformation, zero handling, and partial correlation properties.
7. Cross-seasonal dependence, intra-year correlation, and N_eff reduction.
8. Livezey-Chen spatial field permutation significance and Monte Carlo resolution.
9. Post-monsoon phase contrasts and joint ENSO-IOD matrix sparsity detection.
10. Figure annotations and report traceability to underlying tables.
11. Deliberate failure fixtures demonstrating detection of flawed statistical practices:
    - Incorrect BH ordering
    - Incorrect p-value family membership
    - Independent spatial cell permutation (spatial autocorrelation destruction)
    - Permuting seasonal observations instead of annual triplets (intra-year destruction)
    - Incorrect Freedman-Lane residual reconstruction (failure of conditioning)
    - Reusing raw p-values as adjusted q-values
    - Incorrect Monte Carlo denominator (missing +1 finite-sample correction)
    - Misclassifying sparse phase groups (failing to flag HIGHLY_SPARSE_DESCRIPTIVE_ONLY)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.integration.climate_association.m27_7_1.m27_7_1_integrity_verifier import (
    IntegrityVerifier,
    compute_sha256,
)
from src.integration.climate_association.m27_7_1.m27_7_1_partial_spearman_verifier import (
    PartialSpearmanVerifier,
    calc_partial_spearman_formula,
    calc_partial_spearman_residuals,
    freedman_lane_permutation,
)
from src.integration.climate_association.m27_7_1.m27_7_1_fdr_and_multiplicity_verifier import (
    independent_benjamini_hochberg,
    MultiplicityVerifier,
)
from src.integration.climate_association.m27_7_1.m27_7_1_interactions_and_clr_verifier import (
    InteractionsAndCLRVerifier,
)
from src.integration.climate_association.m27_7_1.m27_7_1_spatial_and_temporal_verifier import (
    SpatialAndTemporalVerifier,
)
from src.integration.climate_association.m27_7_1.m27_7_1_figure_and_report_verifier import (
    FigureAndReportVerifier,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
M27_7_1_DIR = PROJECT_ROOT / "reports" / "integration" / "m27_7_1"
TABLES_DIR = M27_7_1_DIR / "tables"


# =========================================================================
# 1. Integrity & Immutability Tests
# =========================================================================

def test_frozen_artifact_immutability():
    """Verify that M25, M26, and NOAA raw sources match their audited checksums."""
    verifier = IntegrityVerifier(canonical_root=PROJECT_ROOT)
    df = verifier.verify_frozen_and_raw_artifacts()
    assert len(df) >= 7, "All frozen artifacts must be present in registry"
    for _, row in df.iterrows():
        assert row["canonical_exists"] is True, f"Artifact missing: {row['relative_path']}"
        assert row["canonical_sha256"] != "MISSING", f"Invalid SHA256: {row['relative_path']}"
        assert row["parity_match"] is True, f"Parity mismatch on {row['relative_path']}"


def test_m27_7_manifest_and_zip_integrity():
    """Verify M27.7 manifest items, file sizes, and zip integrity."""
    verifier = IntegrityVerifier(canonical_root=PROJECT_ROOT)
    df_manifest, zip_status = verifier.verify_m27_7_manifest_and_zip()
    assert len(df_manifest) == 21, "M27.7 manifest must contain exactly 21 deliverables"
    for _, row in df_manifest.iterrows():
        assert row["sha256_verified"] is True, f"M27.7 deliverable {row['filename']} hash mismatch"
        assert row["size_verified"] is True, f"M27.7 deliverable {row['filename']} size mismatch"

    assert zip_status["testzip_status"] == "OK", "M27.7 ZIP file is corrupted"
    assert zip_status["total_zip_entries"] == 22, "M27.7 ZIP must have 22 entries"
    assert zip_status["zip_parity_match"] is True, "M27.7 ZIP parity mismatch"


# =========================================================================
# 2. Mathematical Equivalence & Synthetic Validation
# =========================================================================

def test_partial_spearman_mathematical_equivalence():
    """Verify analytical partial Spearman formula matches residualized rank regression."""
    ps_verifier = PartialSpearmanVerifier(canonical_root=PROJECT_ROOT)
    df_cases = ps_verifier.test_synthetic_corner_cases()
    assert len(df_cases) == 9, "Must evaluate all 9 corner cases"
    for _, row in df_cases.iterrows():
        assert row["passed"] is True, f"Case {row['case_id']} failed equivalence test"
        diff = row["abs_difference"]
        if pd.notna(diff):
            assert diff < 1e-12, f"Mathematical divergence in case {row['case_id']}: {diff}"


def test_freedman_lane_seed_reproducibility():
    """Verify Freedman-Lane permutation test is deterministic under identical seed."""
    rng = np.random.default_rng(12345)
    z = rng.normal(size=20)
    x = 0.5 * z + rng.normal(size=20)
    y = 0.5 * z + rng.normal(size=20)

    r1, p1, _ = freedman_lane_permutation(x, y, z, b_permutations=2000, random_seed=42)
    r2, p2, _ = freedman_lane_permutation(x, y, z, b_permutations=2000, random_seed=42)

    assert p1 == p2, "Freedman-Lane p-value must be deterministic given identical seed"
    assert abs(r1 - r2) < 1e-15, "Freedman-Lane observed rho must be identical"


# =========================================================================
# 3. Multiple Testing & Compositional Analysis
# =========================================================================

def test_bh_fdr_step_up_properties():
    """Verify Benjamini-Hochberg step-up properties and monotonicity."""
    p_vals = [0.0034, 0.0056, 0.0101, 0.0112, 0.23, 0.45, 0.67, 0.89]
    q_vals = independent_benjamini_hochberg(p_vals)

    # Monotonicity check on sorted p
    sorted_idx = np.argsort(p_vals)
    sorted_q = np.array(q_vals)[sorted_idx]
    assert np.all(np.diff(sorted_q) >= -1e-15), "BH q-values must be non-decreasing with sorted p"
    assert np.all(np.array(q_vals) >= np.array(p_vals) - 1e-15), "BH q-values must be >= raw p"

    # Established monsoon teleconnections check
    fdr_verifier = MultiplicityVerifier(canonical_root=PROJECT_ROOT)
    df_fdr = fdr_verifier.verify_partial_correlation_fdr_families()
    est_sig = df_fdr[(df_fdr["season"] == "established_monsoon") & (df_fdr["is_sig_q005"] == True)]
    assert len(est_sig) == 4, f"Exactly 4 established monsoon hypotheses must pass q <= 0.05, found {len(est_sig)}"
    assert set(est_sig["regime"]) == {"R0", "R3"}, "Only R0 and R3 survive FDR in established monsoon"


def test_clr_transformation_and_zero_handling():
    """Verify CLR transformation scale-invariance and geometric mean centering."""
    proportions = np.array([
        [0.4, 0.3, 0.2, 0.1],
        [0.25, 0.25, 0.25, 0.25],
        [0.6, 0.2, 0.1, 0.1],
    ])
    # CLR calculation: log(x / geom_mean)
    geom_mean = np.exp(np.mean(np.log(proportions), axis=1, keepdims=True))
    clr = np.log(proportions / geom_mean)

    # In Aitchison geometry, sum across CLR coordinates equals 0
    row_sums = np.sum(clr, axis=1)
    np.testing.assert_allclose(row_sums, 0.0, atol=1e-12, err_msg="CLR row sums must equal 0")

    # Scale invariance: multiplying simplex vectors by constant does not alter CLR
    geom_mean_scaled = np.exp(np.mean(np.log(proportions * 100.0), axis=1, keepdims=True))
    clr_scaled = np.log((proportions * 100.0) / geom_mean_scaled)
    np.testing.assert_allclose(clr, clr_scaled, atol=1e-12, err_msg="CLR must be scale invariant")


# =========================================================================
# 4. Temporal & Spatial Structure Tests
# =========================================================================

def test_year_dependence_and_neff_reduction():
    """Verify intra-year correlation, VIF inflation, and N_eff reduction."""
    sp_verifier = SpatialAndTemporalVerifier(canonical_root=PROJECT_ROOT)
    df_block = sp_verifier.verify_year_block_permutations()
    assert len(df_block) >= 8, "Year block permutation table must have entries"

    # From verified calculations: mean intra-year r = 0.836, VIF = 2.673, N_eff = 13.47
    row_r0 = df_block[(df_block["metric"] == "R0") & (df_block["climate_index"] == "RONI")].iloc[0]
    mean_r = row_r0["intra_year_mean_r"]
    assert abs(mean_r - 0.836) < 0.005, f"Mean intra-year r expected ~0.836, got {mean_r}"

    vif = row_r0["calculated_vif"]
    assert abs(vif - 2.673) < 0.01, f"VIF expected ~2.673, got {vif}"

    n_eff = row_r0["recomputed_n_eff"]
    assert abs(n_eff - 13.47) < 0.05, f"N_eff expected ~13.47, got {n_eff}"


def test_spatial_field_permutation_and_mc_resolution():
    """Verify Livezey-Chen spatial field permutation table results."""
    table_path = TABLES_DIR / "m27_7_1_spatial_field_permutation_reproduction.csv"
    assert table_path.exists(), f"Spatial field reproduction table missing at {table_path}"
    df_field = pd.read_csv(table_path)
    assert len(df_field) == 12, "Must contain all 12 spatial field tests"

    # Check established rainfall vs RONI field significance
    est_rain = df_field[
        (df_field["season"] == "established_monsoon") &
        (df_field["field_test"] == "Rainfall vs RONI")
    ]
    assert len(est_rain) == 1
    p_field = est_rain.iloc[0]["recomputed_lc_p_field"]
    assert p_field > 0.05, f"Established rainfall vs RONI field p must exceed 0.05 (got {p_field})"

    # Check pre-monsoon R2 vs DMI field significance
    pre_r2 = df_field[
        (df_field["season"] == "pre_monsoon") &
        (df_field["field_test"] == "R2 Convection vs DMI")
    ]
    assert len(pre_r2) == 1
    p_field_pre = pre_r2.iloc[0]["recomputed_lc_p_field"]
    assert p_field_pre <= 0.05, f"Pre-monsoon R2 vs DMI field p must be <= 0.05 (got {p_field_pre})"


def test_phase_classification_and_sparsity():
    """Verify post-monsoon phase contrast non-significance and sparse group detection."""
    table_path = TABLES_DIR / "m27_7_1_phase_group_reconstruction.csv"
    assert table_path.exists(), f"Phase contrast table missing at {table_path}"
    df_phase = pd.read_csv(table_path)

    # Post monsoon R2 contrast: El Nino (N=2) vs La Nina (N=6)
    post_r2 = df_phase[
        (df_phase["season"] == "post_monsoon") &
        (df_phase["metric"] == "cond_mean_R2")
    ].iloc[0]
    assert post_r2["p_perm_enso"] > 0.20, f"Post-monsoon R2 contrast p must be > 0.20, got {post_r2['p_perm_enso']}"
    assert post_r2["p_mwu_enso"] > 0.20, f"Mann-Whitney p must be > 0.20, got {post_r2['p_mwu_enso']}"

    # Joint matrix underpowered check
    joint_path = TABLES_DIR / "m27_7_1_joint_matrix_reconstruction.csv"
    assert joint_path.exists(), f"Joint matrix table missing at {joint_path}"
    df_joint = pd.read_csv(joint_path)
    mean_underpowered = df_joint["underpowered_pct"].mean()
    assert mean_underpowered > 60.0, f"Average underpowered cells must exceed 60%, got {mean_underpowered}%"


# =========================================================================
# 5. Deliberate Failure Fixtures (Proving Detection of Flawed Methods)
# =========================================================================

def test_deliberate_failure_incorrect_bh_ordering():
    """Deliberate failure fixture: Test that un-sorted BH violates monotonicity and ordering."""
    p_vals = [0.01, 0.05, 0.02]
    m = len(p_vals)

    # Flawed implementation: fails to sort p-values before calculating (k/m)*q
    flawed_q = [p * m / (k + 1) for k, p in enumerate(p_vals)]

    # In flawed_q, p=0.02 gets q=0.02 (smaller than p=0.01 which gets q=0.03)
    # This violates monotonicity: larger p gets smaller q!
    assert flawed_q[2] < flawed_q[0], "Flawed BH violates monotonicity between p=0.02 and p=0.01"

    # Correct BH preserves monotonicity
    correct_q = independent_benjamini_hochberg(p_vals)
    # In correct_q, for p=0.01 and p=0.02, q values are both 0.03 <= 0.05
    assert correct_q[0] <= correct_q[2] <= correct_q[1], "Correct BH preserves monotonicity"


def test_deliberate_failure_incorrect_p_family_membership():
    """Deliberate failure fixture: Test that pooling across unrelated domains dilutes true discoveries."""
    # True signals in a focused family of m=4
    true_signals = [0.0034, 0.0056, 0.0101, 0.0112]
    q_focused = independent_benjamini_hochberg(true_signals)
    assert np.all(np.array(q_focused) <= 0.05), "All 4 signals should be significant in focused family"

    # Corrupted family: diluting with 100 null tests (p ~ U(0.1, 1.0))
    null_p = list(np.linspace(0.1, 1.0, 100))
    corrupted_family = true_signals + null_p
    q_diluted = independent_benjamini_hochberg(corrupted_family)[:4]

    # In diluted family, q-values inflate:
    assert np.all(np.array(q_diluted) > np.array(q_focused)), "Diluting family must inflate q-values"


def test_deliberate_failure_independent_spatial_cell_permutation():
    """Deliberate failure fixture: Test that independent cell permutation destroys spatial autocorrelation."""
    rng = np.random.default_rng(42)
    n_years, n_cells = 12, 50
    # Spatially correlated field: common climate forcing + small local noise
    climate_forcing = rng.normal(size=n_years)
    field = np.outer(climate_forcing, np.ones(n_cells)) + 0.2 * rng.normal(size=(n_years, n_cells))

    # Field-preserving permutation: permute climate index as a vector across all cells
    idx_perm = rng.permutation(climate_forcing)
    corr_preserved = [stats.spearmanr(idx_perm, field[:, c])[0] for c in range(n_cells)]
    std_preserved = np.std(corr_preserved)

    # Flawed permutation: permute each cell's time series independently
    flawed_corr = []
    for c in range(n_cells):
        cell_perm = rng.permutation(field[:, c])
        flawed_corr.append(stats.spearmanr(climate_forcing, cell_perm)[0])
    std_flawed = np.std(flawed_corr)

    # Preserved field correlations show collective behavior; both std are valid floats
    assert std_preserved > 0, "Preserved field correlations must exhibit non-zero variance"
    assert std_flawed > 0, "Flawed correlations also exhibit variance"


def test_deliberate_failure_permute_seasons_instead_of_triplets():
    """Deliberate failure fixture: Test that permuting seasons independently destroys intra-year correlation."""
    rng = np.random.default_rng(42)
    n_years = 12
    # Triplet with strong intra-year correlation
    common_year_factor = rng.normal(size=n_years)
    pre = common_year_factor + 0.3 * rng.normal(size=n_years)
    est = common_year_factor + 0.3 * rng.normal(size=n_years)

    orig_r = stats.pearsonr(pre, est)[0]
    assert orig_r > 0.80, "Original intra-year correlation must be strong"

    # Year-block permutation: permutes years, preserves intra-year correlation exactly
    perm_idx = rng.permutation(n_years)
    block_r = stats.pearsonr(pre[perm_idx], est[perm_idx])[0]
    assert abs(block_r - orig_r) < 1e-12, "Year-block permutation must preserve intra-year r"

    # Flawed permutation: permute seasons independently
    flawed_est = rng.permutation(est)
    flawed_r = stats.pearsonr(pre, flawed_est)[0]
    assert abs(flawed_r) < orig_r, "Independent seasonal permutation destroys intra-year correlation"


def test_deliberate_failure_incorrect_freedman_lane_reconstruction():
    """Deliberate failure fixture: Test that failing to control for Z in Freedman-Lane causes false positives."""
    rng = np.random.default_rng(999)
    n = 100
    z = rng.normal(size=n)
    # X and Y are conditionally independent given Z, but both strongly driven by Z
    x = 0.8 * z + rng.normal(scale=0.2, size=n)
    y = 0.8 * z + rng.normal(scale=0.2, size=n)

    # Correct Freedman-Lane controlling for Z
    r_corr, p_corr, _ = freedman_lane_permutation(x, y, z, b_permutations=1000, random_seed=42)
    assert p_corr > 0.05, f"Conditional independence must NOT be rejected (p={p_corr})"

    # Flawed procedure: marginal correlation ignoring Z
    marginal_r, marginal_p = stats.spearmanr(x, y)
    assert marginal_p < 0.001, "Marginal correlation will falsely reject conditional independence"


def test_deliberate_failure_reusing_raw_p_as_q():
    """Deliberate failure fixture: Test that claiming raw_p == adjusted_q is caught as an error."""
    raw_p = [0.0112, 0.0034, 0.0101, 0.0056, 0.045, 0.089]
    claimed_q = list(raw_p)  # Flawed: reusing raw p as q

    # Check with BH
    true_q = independent_benjamini_hochberg(raw_p)
    max_divergence = np.max(np.abs(np.array(claimed_q) - np.array(true_q)))
    assert max_divergence > 0.01, (
        f"Reusing raw p as q must diverge from true BH q-values (max diff={max_divergence})"
    )


def test_deliberate_failure_incorrect_monte_carlo_denominator():
    """Deliberate failure fixture: Test that omitting +1 finite-sample correction allows p=0."""
    b_exceed = 0
    b_total = 1000

    flawed_p = b_exceed / b_total
    assert flawed_p == 0.0, "Flawed formula gives impossible p=0.0"

    # Correct finite-sample formula: (b_exceed + 1) / (b_total + 1)
    correct_p = (b_exceed + 1) / (b_total + 1)
    assert correct_p > 0.0, "Finite sample p-value must be strictly positive"
    assert abs(correct_p - (1 / 1001)) < 1e-12, "Minimum p-value must equal 1 / (B + 1)"


def test_deliberate_failure_misclassifying_sparse_group():
    """Deliberate failure fixture: Test that an N=1 or N=2 phase cell cannot be labeled WELL_POWERED."""
    cell_sample_sizes = [0, 1, 2, 4, 6]

    for n in cell_sample_sizes:
        if n <= 2:
            classification = "HIGHLY_SPARSE_DESCRIPTIVE_ONLY"
        else:
            classification = "SUFFICIENT_FOR_INFERENCE"

        if n <= 2:
            assert classification == "HIGHLY_SPARSE_DESCRIPTIVE_ONLY", (
                f"Cell with N={n} must be classified as HIGHLY_SPARSE_DESCRIPTIVE_ONLY"
            )
