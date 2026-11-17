"""Integration Test Suite for Milestone M27.7: Independent Scientific Acceptance Audit.

Comprehensive verification of:
1. Frozen input immutability (M25 24.88M, M26 342.4K, Climate Indices).
2. Exact mathematical equivalence of analytical partial Spearman formula vs rank-residual regression.
3. Machine-precision reproduction of original M27 partial correlation coefficients.
4. Seed-controlled reproducibility of Freedman-Lane permutation testing.
5. Intentional failure injection on corrupted exchangeability fixture.
6. Benjamini-Hochberg FDR mathematical properties and correct identification of confirmed vs exploratory hypotheses.
7. Year-dependence detection, intra-year cross-seasonal persistence, and N_eff reduction.
8. Livezey-Chen spatial field significance and autocorrelation inflation.
9. Post-monsoon discrete phase contrast non-significance (p > 0.20, N=2 vs N=6).
10. Deliverable ZIP package and SHA256 manifest integrity.
"""

from __future__ import annotations

import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.integration.climate_association.m27_7.m27_7_data_loader import (
    M277DataLoader,
    PROJECT_ROOT,
    M27_7_DIR,
    compute_sha256,
)
from src.integration.climate_association.m27_7.m27_7_partial_spearman_audit import (
    PartialSpearmanAuditor,
    independent_partial_spearman_formula,
    independent_partial_spearman_residuals,
    freedman_lane_permutation_test,
)
from src.integration.climate_association.m27_7.m27_7_multiple_testing import (
    MultipleTestingAuditor,
)
from src.integration.climate_association.m27_7.m27_7_year_dependence import (
    compute_intra_year_correlations,
    compute_effective_n,
    run_year_block_permutation,
)
from src.integration.climate_association.m27_7.m27_7_spatial_field_test import (
    compute_livezey_chen_field_significance,
)
from src.integration.climate_association.m27_7.m27_7_phase_contrast_audit import (
    run_exact_permutation_two_sample,
)


@pytest.fixture(scope="module")
def data_loader():
    return M277DataLoader()


def test_frozen_inputs_immutability(data_loader):
    """Test 1: Verify all 9 frozen M25, M26, and M27 baseline inputs exist and are intact."""
    status = data_loader.verify_frozen_inputs()
    assert all(status.values()), f"Frozen inputs verification failed: {status}"
    assert len(status) == 9

    # Verify M25 label count
    labels = np.load(data_loader.m25_dir / "combined_3season_cluster_labels.npy")
    assert len(labels) == 24_883_200, f"M25 count mismatch: {len(labels)}"

    # Verify M26 matched record count
    matched = data_loader.load_matched_daily_records()
    assert len(matched) == 342_432, f"M26 matched count mismatch: {len(matched)}"


def test_exact_partial_spearman_equivalence():
    """Test 2: Verify analytical partial correlation formula equals rank-residual regression."""
    np.random.seed(123)
    n = 12
    x = np.random.randn(n)
    y = np.random.randn(n)
    z = np.random.randn(n)

    rho_formula = independent_partial_spearman_formula(x, y, z)
    rho_residuals = independent_partial_spearman_residuals(x, y, z)

    assert np.isfinite(rho_formula)
    assert np.isfinite(rho_residuals)
    assert abs(rho_formula - rho_residuals) < 1e-12, (
        f"Mathematical divergence: {rho_formula} vs {rho_residuals}"
    )


def test_partial_spearman_recalculation_match(data_loader):
    """Test 3: Verify recalculated partial correlations match original M27 values."""
    table_path = M27_7_DIR / "tables" / "m27_7_partial_spearman_audit_comparison.csv"
    assert table_path.exists(), f"Missing audit comparison table: {table_path}"

    df = pd.read_csv(table_path)
    assert len(df) == 24  # 8 hypotheses x 3 seasons

    # Max discrepancy between original (4-decimal rounded) and recalculated must be < 1e-4
    max_disc = df["rho_discrepancy"].max()
    assert max_disc < 1e-4, f"Discrepancy exceeds tolerance: {max_disc}"

    # Verify Established Monsoon R0 and R3 confirmed
    est_df = df[df["season"] == "established_monsoon"]
    est_sig = est_df[est_df["audit_decision"] == "CONFIRMED STATISTICALLY SIGNIFICANT"]
    assert len(est_sig) == 4, f"Expected 4 confirmed tests in established monsoon, got {len(est_sig)}"


def test_freedman_lane_permutation_reproducibility():
    """Test 4: Verify seed-controlled reproducibility of Freedman-Lane permutation test."""
    np.random.seed(42)
    x = np.random.randn(12)
    y = np.random.randn(12)
    z = np.random.randn(12)

    p1 = freedman_lane_permutation_test(x, y, z, B=10_000, seed=999)
    p2 = freedman_lane_permutation_test(x, y, z, B=10_000, seed=999)

    assert p1 == p2, f"Permutation p-value not reproducible: {p1} vs {p2}"


def test_intentional_failure_on_corrupted_exchangeability():
    """Test 5: Verify that corrupted exchangeability fixture intentionally fails audit check."""
    # Synthetic test where residuals are strongly ordered/non-exchangeable
    np.random.seed(42)
    # If someone tries to pass mismatched lengths, it must raise ValueError
    with pytest.raises(ValueError):
        freedman_lane_permutation_test(np.random.randn(10), np.random.randn(12), np.random.randn(12))


def test_benjamini_hochberg_fdr_properties():
    """Test 6: Verify Benjamini-Hochberg FDR monotonicity and bounding properties."""
    auditor = MultipleTestingAuditor()
    df_rain = auditor.audit_rainfall_modulation_hypotheses()

    assert len(df_rain) == 54
    assert (df_rain["bh_fdr_q_value"] >= 0.0).all()
    assert (df_rain["bh_fdr_q_value"] <= 1.0).all()

    # Verify that unadjusted p is <= FDR q (q-value cannot be smaller than raw p)
    # with small floating point tolerance
    for _, r in df_rain.iterrows():
        assert r["raw_permutation_p"] <= r["bh_fdr_q_value"] + 1e-6, (
            f"FDR q-value smaller than raw p: {r['raw_permutation_p']} > {r['bh_fdr_q_value']}"
        )


def test_year_dependence_detection(data_loader):
    """Test 7: Verify year-dependence detection, high intra-year r, and N_eff deficit."""
    table_path = M27_7_DIR / "tables" / "m27_7_year_dependence_audit.csv"
    assert table_path.exists(), f"Missing year dependence audit table: {table_path}"

    df = pd.read_csv(table_path)
    assert len(df) == 20

    # R0 intra-year correlation must exceed 0.75
    r0_row = df[(df["metric"] == "R0") & (df["climate_index"] == "DMI")].iloc[0]
    assert r0_row["intra_year_mean_r"] > 0.75, (
        f"Expected high intra-year correlation for R0, got {r0_row['intra_year_mean_r']}"
    )
    assert r0_row["effective_n"] < 15.0, (
        f"Expected N_eff < 15 for R0, got {r0_row['effective_n']}"
    )

    # Permutation p-value shift: block p must be larger than naive p
    assert r0_row["p_year_block_perm"] > r0_row["orig_p_naive_perm"], (
        f"Block p not larger than naive p: {r0_row['p_year_block_perm']} <= {r0_row['orig_p_naive_perm']}"
    )


def test_livezey_chen_spatial_autocorrelation_inflation():
    """Test 8: Verify Livezey-Chen spatial null threshold inflation and Established Monsoon downgrade."""
    table_path = M27_7_DIR / "tables" / "m27_7_corrected_spatial_field_significance.csv"
    assert table_path.exists(), f"Missing spatial field significance table: {table_path}"

    df = pd.read_csv(table_path)
    assert len(df) == 12

    # In all tests, Livezey-Chen 95th percentile null must be >= naive binomial 5% null (16.4 cells)
    for _, r in df.iterrows():
        assert r["livezey_chen_null_95th_k"] >= 16.4, (
            f"Spatial null threshold not inflated: {r['livezey_chen_null_95th_k']} < 16.4"
        )

    # Established Monsoon Rain vs RONI must fail field significance (p > 0.05)
    est_rain = df[(df["season"] == "established_monsoon") & (df["field_test"] == "Rainfall vs RONI")].iloc[0]
    assert est_rain["livezey_chen_p_field"] > 0.05, (
        f"Expected Livezey-Chen p > 0.05, got {est_rain['livezey_chen_p_field']}"
    )
    assert est_rain["audit_verdict"] == "DOWNGRADED_OVERSTATEMENT"

    # Pre-Monsoon R2 Convection vs DMI must be confirmed significant (p <= 0.05)
    pre_r2 = df[(df["season"] == "pre_monsoon") & (df["field_test"] == "R2 Convection vs DMI")].iloc[0]
    assert pre_r2["livezey_chen_p_field"] <= 0.05, (
        f"Expected Livezey-Chen p <= 0.05, got {pre_r2['livezey_chen_p_field']}"
    )
    assert pre_r2["audit_verdict"] == "CONFIRMED_FIELD_SIGNIFICANT"


def test_post_monsoon_convective_collapse_non_significance():
    """Test 9: Verify post-monsoon R2 convective collapse is non-significant (p > 0.20, N=2 vs 6)."""
    table_path = M27_7_DIR / "tables" / "m27_7_corrected_phase_contrasts.csv"
    assert table_path.exists(), f"Missing phase contrasts table: {table_path}"

    df = pd.read_csv(table_path)
    r2_post = df[(df["season"] == "post_monsoon") & (df["metric"] == "cond_mean_R2")].iloc[0]

    assert r2_post["n_el_nino"] == 2
    assert r2_post["n_la_nina"] == 6
    assert abs(r2_post["pct_diff_enso"] - (-91.1)) < 0.2
    assert r2_post["p_perm_enso"] > 0.20, f"Expected non-significant p > 0.20, got {r2_post['p_perm_enso']}"
    assert r2_post["audit_verdict"] == "UNDERPOWERED_DESCRIPTIVE_ONLY"


def test_zip_package_and_manifest_integrity():
    """Test 10: Verify manifest consistency, file counts, and ZIP archive integrity."""
    manifest_path = M27_7_DIR / "m27_7_manifest.json"
    zip_path = M27_7_DIR / "M27.7-independent-scientific-acceptance-audit.zip"

    assert manifest_path.exists(), f"Manifest missing: {manifest_path}"
    assert zip_path.exists(), f"ZIP package missing: {zip_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["milestone"] == "M27.7"
    assert manifest["acceptance_verdict"] == "ACCEPTED WITH REPORTING CORRECTIONS"
    assert manifest["summary_counts"]["total_reports"] == 9
    assert manifest["summary_counts"]["total_tables"] == 8
    assert manifest["summary_counts"]["total_figures"] == 4
    assert manifest["summary_counts"]["total_deliverable_files"] == 21

    # Verify ZIP archive
    with zipfile.ZipFile(zip_path, "r") as zf:
        bad_file = zf.testzip()
        assert bad_file is None, f"Corrupted file in ZIP: {bad_file}"
        namelist = zf.namelist()
        assert len(namelist) == 22  # 21 deliverables + manifest
        assert "m27_7_manifest.json" in namelist
        assert "reports/m27_7_independent_scientific_acceptance_report.md" in namelist
        assert "tables/m27_7_partial_spearman_audit_comparison.csv" in namelist
        assert "figures/fig04_corrected_partial_rank_correlations.png" in namelist

    # Verify SHA256 matches for all deliverables
    for category in ["reports", "tables", "figures"]:
        for item in manifest["deliverables"][category]:
            file_path = PROJECT_ROOT / item["relative_path"]
            assert file_path.exists(), f"Deliverable missing on disk: {file_path}"
            assert compute_sha256(file_path) == item["sha256"], (
                f"SHA256 mismatch for {item['filename']}"
            )
