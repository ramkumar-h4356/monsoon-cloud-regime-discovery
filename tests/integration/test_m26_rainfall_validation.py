"""
test_m26_rainfall_validation.py

Automated integration test suite for Milestone M26:
Physical Rainfall Validation of CERES-Derived Cloud Regimes using IMD 1.0-deg Gridded Daily Rainfall (2010-2021).
"""

from __future__ import annotations

import json
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
import pytest

# Dynamic root resolution so tests run seamlessly in both canonical and worktree environments
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CANONICAL_REPO_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")

PROCESSED_DATA_DIR = REPO_ROOT / "data" / "processed" / "rainfall_validation"
M26_REPORT_DIR = REPO_ROOT / "reports" / "integration" / "m26"
M26_TABLES_DIR = M26_REPORT_DIR / "tables"
M26_FIGURES_DIR = M26_REPORT_DIR / "figures"
FROZEN_M25_DIR = REPO_ROOT / "data" / "processed" / "combined_3season"

RAW_IMD_DIR = REPO_ROOT / "raw_data" / "IMD_Rainfall"
if not (RAW_IMD_DIR / "RFone_imd_rf_1x1_2010.nc").exists():
    RAW_IMD_DIR = CANONICAL_REPO_ROOT / "raw_data" / "IMD_Rainfall"


def test_primary_matched_dataset_integrity():
    """Verify primary matched dataset row counts, valid hours, and column specifications."""
    primary_path = PROCESSED_DATA_DIR / "m26_cloud_rainfall_matched_primary.parquet"
    assert primary_path.exists(), f"Primary matched dataset missing: {primary_path}"
    
    df = pd.read_parquet(primary_path)
    
    # 12 years x 3 seasons x 29 days x 328 Tier 1 cells = 342,432 rows
    assert len(df) == 342432, f"Expected 342,432 rows, got {len(df)}"
    
    required_cols = [
        "year", "season_id", "season_name", "day_index", "date", "cell_index",
        "latitude", "longitude", "valid_cloud_hours", "is_complete_24h",
        "count_r0", "count_r1", "count_r2", "count_r3",
        "frac_r0", "frac_r1", "frac_r2", "frac_r3",
        "dominant_regime", "tie_occurred", "alignment_convention",
        "quality_tier", "is_valid_land", "rainfall_mm", "is_dry_day", "is_wet_day_25"
    ]
    for col in required_cols:
        assert col in df.columns, f"Required column missing: {col}"
        
    # All rows must have exactly 24 valid hours (100% complete shifted window)
    assert (df["valid_cloud_hours"] == 24).all(), "All primary rows must have exactly 24 valid assigned hours"
    assert (df["is_complete_24h"] == True).all(), "All primary rows must have is_complete_24h == True"
    
    # Regime assignments must be in {0, 1, 2, 3}
    assert set(df["dominant_regime"].unique()).issubset({0, 1, 2, 3}), "Dominant regime out of range"
    
    # Tier 1 strictness
    assert (df["quality_tier"] == "TIER_1_FULL_LAND").all(), "All primary rows must be Quality Tier 1"
    assert (df["is_valid_land"] == True).all(), "All primary rows must be valid land"
    
    # Distinct cell count
    assert df["cell_index"].nunique() == 328, "Expected exactly 328 distinct Tier 1 cells"
    assert df["day_index"].nunique() == 29, "Expected 29 days"


def test_sensitivity_s1_dataset_integrity():
    """Verify Sensitivity S1 (All-Land: Tier 1 + Tier 2 Coastal) dataset integrity."""
    s1_path = PROCESSED_DATA_DIR / "m26_cloud_rainfall_matched_s1_all_land.parquet"
    assert s1_path.exists(), f"S1 matched dataset missing: {s1_path}"
    
    df = pd.read_parquet(s1_path)
    
    # 12 years x 3 seasons x 29 days x 357 cells = 372,708 rows
    assert len(df) == 372708, f"Expected 372,708 rows, got {len(df)}"
    
    tier1_count = (df["quality_tier"] == "TIER_1_FULL_LAND").sum()
    tier2_count = (df["quality_tier"] == "TIER_2_COASTAL").sum()
    
    assert tier1_count == 342432, f"Expected 342,432 Tier 1 rows, got {tier1_count}"
    assert tier2_count == 30276, f"Expected 30,276 Tier 2 rows, got {tier2_count}"
    
    assert df["cell_index"].nunique() == 357, "Expected exactly 357 distinct land cells in S1"


def test_calendar_day_dataset_integrity():
    """Verify UTC Calendar Day matched dataset (30 days, 87.5% overlap)."""
    cal_path = PROCESSED_DATA_DIR / "m26_cloud_rainfall_matched_calendar.parquet"
    assert cal_path.exists(), f"Calendar matched dataset missing: {cal_path}"
    
    df = pd.read_parquet(cal_path)
    
    # 12 years x 3 seasons x 30 days x 357 land cells = 385,560 rows
    assert len(df) == 385560, f"Expected 385,560 rows, got {len(df)}"
    assert df["day_index"].min() == 1
    assert df["day_index"].max() == 30
    assert df["day_index"].nunique() == 30


def test_zero_rainfall_and_ocean_nan_preservation():
    """Assert genuine 0.0 mm dry days exist and verify ocean cells are strictly NaN (anti-zero-filling mandate)."""
    primary_path = PROCESSED_DATA_DIR / "m26_cloud_rainfall_matched_primary.parquet"
    df_prim = pd.read_parquet(primary_path)
    
    zero_rain_count = (df_prim["rainfall_mm"] == 0.0).sum()
    assert zero_rain_count > 0, "Genuine dry days (0.0 mm) must exist"
    assert (df_prim["rainfall_mm"] >= 0.0).all(), "No negative rainfall values allowed"
    
    # Check raw daily IMD table for ocean NaN preservation
    imd_path = PROCESSED_DATA_DIR / "m26_imd_rainfall_daily.parquet"
    assert imd_path.exists(), f"IMD daily table missing: {imd_path}"
    df_imd = pd.read_parquet(imd_path)
    
    # 12 years x 3 seasons x 30 days x 960 domain cells = 1,036,800
    assert len(df_imd) == 1036800
    
    # Ocean cells (Tier 4, 603 cells) must be NaN and never filled with 0.0
    ocean_records = df_imd[df_imd["quality_tier"] == "TIER_4_OCEAN"]
    assert len(ocean_records) == 12 * 3 * 30 * 603, "Ocean record count mismatch"
    assert ocean_records["rainfall_mm"].isna().all(), "Ocean cells must be strictly NaN (zero-filling prohibited)"


def test_regime_rainfall_rank_ordering():
    """Assert physical hierarchy: R2 (Deep Convection) > R0 > R3 > R1 (Shallow Cumulus)."""
    pooled_summary_path = M26_TABLES_DIR / "m26_regime_rainfall_pooled_summary.csv"
    assert pooled_summary_path.exists()
    
    df_pooled = pd.read_csv(pooled_summary_path)
    means = dict(zip(df_pooled["dominant_regime"], df_pooled["mean_rainfall_mm"]))
    wet_pct = dict(zip(df_pooled["dominant_regime"], df_pooled["wet_day_25_pct"]))
    
    # Hierarchy check
    assert means[2] > means[0] > means[1], "R2 must exceed R0, and R0 must exceed R1 in mean rainfall"
    assert means[2] > means[3] > means[1], "R2 must exceed R3, and R3 must exceed R1 in mean rainfall"
    
    # Wet-day frequency check
    assert wet_pct[2] > wet_pct[1], "Deep convection must have significantly higher wet-day frequency than shallow cumulus"
    
    # Contrast ratio check: R2 / R1 > 10.0
    contrast_ratio = means[2] / means[1]
    assert contrast_ratio > 10.0, f"Expected contrast ratio > 10.0, got {contrast_ratio:.2f}"
    
    # Established monsoon specific checks
    season_path = M26_TABLES_DIR / "m26_regime_rainfall_by_season.csv"
    assert season_path.exists()
    df_season = pd.read_csv(season_path)
    df_est = df_season[df_season["season_name"] == "established_monsoon"]
    est_means = dict(zip(df_est["dominant_regime"], df_est["mean_rainfall_mm"]))
    
    assert est_means[2] > 15.0, f"Established monsoon R2 mean should be > 15 mm/day, got {est_means[2]}"
    assert (est_means[2] / est_means[1]) > 10.0, "Established monsoon contrast ratio must exceed 10.0"


def test_multivariable_regression_coefficients():
    """Verify continuous fraction multivariable regression resolves sum-to-one constraint and confirms physics."""
    reg_path = M26_TABLES_DIR / "m26_continuous_fraction_regressions.csv"
    assert reg_path.exists()
    
    df_reg = pd.read_csv(reg_path)
    df_all = df_reg[df_reg["season"] == "all_seasons"]
    coefs = dict(zip(df_all["parameter"], df_all["coefficient"]))
    pvals = dict(zip(df_all["parameter"], df_all["p_value"]))
    vifs = df_all["vif"].dropna().tolist()
    
    # Convective fraction must have positive marginal effect
    assert coefs["beta_R2 (Deep Convection)"] > 0, "R2 marginal coefficient must be positive"
    assert pvals["beta_R2 (Deep Convection)"] < 0.001, "R2 coefficient must be highly significant (p < 0.001)"
    
    # Shallow cumulus must have negative marginal effect
    assert coefs["beta_R1 (Shallow Cumulus)"] < 0, "R1 marginal coefficient must be negative"
    assert pvals["beta_R1 (Shallow Cumulus)"] < 0.001, "R1 coefficient must be highly significant (p < 0.001)"
    
    # Multicollinearity check: VIF must be < 2.0 with R3 omitted
    for vif in vifs:
        assert float(vif) < 2.0, f"VIF should be < 2.0, got {vif}"


def test_bootstrap_confidence_interval_exclusion_of_zero():
    """Verify that spatial-temporal block bootstrap 95% CIs for R2 - R1 exclude zero."""
    boot_path = M26_TABLES_DIR / "m26_block_bootstrap_confidence_intervals.csv"
    assert boot_path.exists()
    
    df_boot = pd.read_csv(boot_path)
    
    # Established monsoon contrast
    row_est_contrast = df_boot[
        (df_boot["season"] == "established_monsoon") & 
        (df_boot["regime_id"] == "CONTRAST_R2_MINUS_R1")
    ].iloc[0]
    
    assert row_est_contrast["ci95_mean_lower_mm"] > 10.0, "Lower 95% CI bound for R2-R1 must be > 10 mm/day"
    assert row_est_contrast["ci95_mean_upper_mm"] > row_est_contrast["ci95_mean_lower_mm"]
    assert row_est_contrast["bootstrap_se_mean"] > 0.0


def test_sensitivity_invariance():
    """Verify regime rainfall hierarchy is strictly invariant across all 4 sensitivity dimensions."""
    sens_path = M26_TABLES_DIR / "m26_sensitivity_analysis_results.csv"
    assert sens_path.exists()
    
    df_sens = pd.read_csv(sens_path)
    variants = df_sens["variant_name"].unique()
    
    for var in variants:
        df_var = df_sens[df_sens["variant_name"] == var]
        means = dict(zip(df_var["regime_id"], df_var["mean_rainfall_mm"]))
        assert means["R2"] > means["R0"], f"Invariance violated in {var}: R2 not > R0"
        assert means["R0"] > means["R1"], f"Invariance violated in {var}: R0 not > R1"
        assert means["R3"] > means["R1"], f"Invariance violated in {var}: R3 not > R1"
        assert means["R2"] > means["R3"], f"Invariance violated in {var}: R2 not > R3"


def test_m26_deliverables_existence():
    """Verify existence and non-zero size of all 13 CSV tables, 4 figures, and synthesis report."""
    expected_tables = [
        "m26_regime_rainfall_pooled_summary.csv",
        "m26_regime_rainfall_by_season.csv",
        "m26_regime_rainfall_by_year.csv",
        "m26_rainfall_threshold_sensitivity.csv",
        "m26_extreme_event_attribution.csv",
        "m26_continuous_fraction_correlations.csv",
        "m26_partial_spearman_correlations.csv",
        "m26_continuous_fraction_regressions.csv",
        "m26_convective_decile_composites.csv",
        "m26_spatial_regime_rainfall_by_cell.csv",
        "m26_temporal_regime_transitions.csv",
        "m26_sensitivity_analysis_results.csv",
        "m26_block_bootstrap_confidence_intervals.csv",
    ]
    for tbl in expected_tables:
        p = M26_TABLES_DIR / tbl
        assert p.exists(), f"Missing table: {tbl}"
        assert p.stat().st_size > 0, f"Empty table: {tbl}"
        
    expected_figures = [
        "fig1_regime_rainfall_distributions_by_season.png",
        "fig2_spatial_rainfall_composites_by_regime.png",
        "fig3_convective_fraction_vs_rainfall_deciles.png",
        "fig4_sensitivity_comparison_matrix.png",
    ]
    for fig in expected_figures:
        p = M26_FIGURES_DIR / fig
        assert p.exists(), f"Missing figure: {fig}"
        assert p.stat().st_size > 10_000, f"Figure too small: {fig}"
        
    report_path = M26_REPORT_DIR / "m26_rainfall_validation_synthesis_report.md"
    assert report_path.exists(), "Synthesis report missing"
    assert report_path.stat().st_size > 15_000, "Synthesis report too short"
    
    acceptance_path = M26_REPORT_DIR / "m26_scientific_acceptance_report.md"
    assert acceptance_path.exists(), "Acceptance report missing"
    assert acceptance_path.stat().st_size > 5_000, "Acceptance report too short"
    
    audit_review_path = M26_REPORT_DIR / "m26_1_scientific_results_audit_and_acceptance_review.md"
    assert audit_review_path.exists(), "Audit review report missing"
    assert audit_review_path.stat().st_size > 5_000, "Audit review report too short"


def test_m26_manifest_and_zip_validity():
    """Verify cryptographic manifest and handoff ZIP archive integrity."""
    manifest_path = M26_REPORT_DIR / "m26_manifest.json"
    assert manifest_path.exists(), "Manifest missing"
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    assert manifest["milestone"] == "M26"
    assert manifest["final_decision"] in ["ACCEPTED_AND_SCIENTIFICALLY_VALIDATED", "READY_TO_FREEZE_WITH_DOCUMENTED_LIMITATIONS"]
    assert len(manifest["deliverables"]["tables"]) == 13
    assert len(manifest["deliverables"]["figures"]) == 4
    assert len(manifest["deliverables"]["datasets"]) == 6
    
    zip_path = M26_REPORT_DIR / "M26-rainfall-validation.zip"
    assert zip_path.exists(), "Handoff ZIP missing"
    assert zipfile.is_zipfile(zip_path), "Not a valid ZIP file"
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.testzip() is None, "ZIP file corrupted"
        names = zf.namelist()
        assert "reports/integration/m26/m26_manifest.json" in names
        assert "reports/integration/m26/m26_rainfall_validation_synthesis_report.md" in names
        assert "reports/integration/m26/m26_scientific_acceptance_report.md" in names
        assert "reports/integration/m26/m26_1_scientific_results_audit_and_acceptance_review.md" in names
        assert "reports/integration/m26/figures/fig1_regime_rainfall_distributions_by_season.png" in names


def test_no_frozen_m25_artifact_mutation():
    """Assert frozen M25 3-season arrays are intact and unmodified."""
    assert FROZEN_M25_DIR.exists()
    
    expected_m25_files = [
        "combined_3season_cell_indices.npy",
        "combined_3season_cluster_labels.npy",
        "combined_3season_FS-A_scaled.npy",
        "combined_3season_pca_top10_scores.npy",
        "combined_3season_season_ids.npy",
        "combined_3season_years.npy",
    ]
    for fname in expected_m25_files:
        p = FROZEN_M25_DIR / fname
        assert p.exists(), f"Missing frozen M25 file: {fname}"
        assert p.stat().st_size > 20_000_000, f"Frozen M25 file size corrupted: {fname}"


def test_no_raw_imd_mutation():
    """Assert raw IMD NetCDF files exist and have non-zero sizes."""
    assert RAW_IMD_DIR.exists()
    
    for yr in range(2010, 2022):
        nc_name = f"RFone_imd_rf_1x1_{yr}.nc"
        p = RAW_IMD_DIR / nc_name
        assert p.exists(), f"Missing raw IMD NetCDF: {nc_name}"
        assert p.stat().st_size > 3_000_000, f"Raw IMD file too small: {nc_name}"
