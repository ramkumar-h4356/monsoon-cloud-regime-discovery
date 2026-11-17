"""
test_m25_4_imd_readiness.py

Automated integration test suite for Milestone M25.4:
Unified IMD Rainfall Data-Readiness Audit and Milestone M25 Closeout Verification.
"""

from __future__ import annotations

import json
from pathlib import Path
import zipfile
import pandas as pd
import pytest

REPO_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
POST_REPO_ROOT = Path("D:/Project Simulator/post_monsoon_research")

M25_3_ACCEPTANCE_DIR = REPO_ROOT / "reports" / "integration" / "m25_3" / "final_scientific_acceptance"
M25_4_OUTPUT_DIR = REPO_ROOT / "reports" / "integration" / "m25_4" / "imd_rainfall_readiness"
M25_4_MIRROR_DIR = POST_REPO_ROOT / "reports" / "integration" / "m25_4" / "imd_rainfall_readiness"
DOCS_METHODOLOGY_DIR = REPO_ROOT / "docs" / "methodology"


def test_m25_3_closeout_and_revised_matrix():
    revised_matrix_path = M25_3_ACCEPTANCE_DIR / "m25_3_evidence_matrix_revised.csv"
    assert revised_matrix_path.exists(), "m25_3_evidence_matrix_revised.csv must exist"
    
    df_revised = pd.read_csv(revised_matrix_path)
    row_est = df_revised[df_revised["audit_question"].str.contains("Established-Monsoon Population Counts")].iloc[0]
    assert row_est["finding_classification"] == "ACCEPTED_WITH_CORRECTED_REPORTING_ERRATUM"
    
    changelog_path = M25_3_ACCEPTANCE_DIR / "m25_3_1_changelog.md"
    assert changelog_path.exists(), "m25_3_1_changelog.md must exist"
    
    freeze_doc = DOCS_METHODOLOGY_DIR / "M25_CLOSEOUT_AND_FREEZE.md"
    assert freeze_doc.exists(), "M25_CLOSEOUT_AND_FREEZE.md must exist"


def test_imd_readiness_deliverables_existence():
    assert M25_4_OUTPUT_DIR.exists(), f"M25.4 directory must exist: {M25_4_OUTPUT_DIR}"
    
    expected_files = [
        "imd_rainfall_artifact_inventory.csv",
        "imd_rainfall_provenance_report.md",
        "imd_temporal_coverage_by_year.csv",
        "imd_seasonal_coverage_summary.csv",
        "imd_spatial_grid_verification.csv",
        "imd_missingness_audit.csv",
        "imd_value_quality_audit.csv",
        "imd_ceres_grid_mapping_design.md",
        "imd_daily_integration_schema.json",
        "imd_data_quality_policy.md",
        "m25_4_readiness_report.md",
        "m25_4_manifest.json",
        "M25.4-IMD-rainfall-data-readiness.zip",
    ]
    for fname in expected_files:
        fp = M25_4_OUTPUT_DIR / fname
        assert fp.exists(), f"Missing M25.4 deliverable: {fname}"
        assert fp.stat().st_size > 0, f"M25.4 deliverable is empty: {fname}"


def test_imd_rainfall_artifact_inventory():
    inv_path = M25_4_OUTPUT_DIR / "imd_rainfall_artifact_inventory.csv"
    assert inv_path.exists()
    df_inv = pd.read_csv(inv_path)
    
    # 12 verified files + 1 gap record
    assert len(df_inv) == 13
    df_valid = df_inv[df_inv["integrity_status"] == "VERIFIED_VALID"]
    assert len(df_valid) == 12
    assert (df_valid["sha256"].str.len() == 64).all()
    assert (df_valid["format"].str.contains("NetCDF")).all()
    
    # Check physical existence of raw files
    for rpath in df_valid["relative_path"]:
        full_p = REPO_ROOT / rpath
        assert full_p.exists(), f"Raw IMD file must exist: {full_p}"
        assert full_p.stat().st_size > 3_000_000, f"Raw IMD file too small: {full_p}"
        
    df_gap = df_inv[df_inv["integrity_status"] == "BLOCKED_FILE_NOT_FOUND"]
    assert len(df_gap) == 1
    assert "0.25" in df_gap.iloc[0]["spatial_resolution"]


def test_imd_temporal_coverage():
    yr_path = M25_4_OUTPUT_DIR / "imd_temporal_coverage_by_year.csv"
    assert yr_path.exists()
    df_yr = pd.read_csv(yr_path)
    
    assert len(df_yr) == 12
    assert (df_yr["pre_monsoon_days"] == 30).all()
    assert (df_yr["established_monsoon_days"] == 30).all()
    assert (df_yr["post_monsoon_days"] == 30).all()
    assert (df_yr["total_study_days_in_year"] == 90).all()
    assert (df_yr["missing_study_days"] == 0).all()
    assert (df_yr["duplicate_dates_count"] == 0).all()
    assert (df_yr["temporal_readiness"] == "COMPLETE").all()
    
    seas_path = M25_4_OUTPUT_DIR / "imd_seasonal_coverage_summary.csv"
    assert seas_path.exists()
    df_seas = pd.read_csv(seas_path)
    
    assert len(df_seas) == 36, "12 years x 3 seasons = 36 records"
    assert (df_seas["observed_days"] == 30).all()
    assert (df_seas["coverage_pct"] == 100.0).all()
    assert (df_seas["negative_values_count"] == 0).all()
    assert (df_seas["valid_land_cells"] == 357).all()
    assert (df_seas["masked_ocean_foreign_cells"] == 603).all()


def test_imd_spatial_grid_and_mask():
    spat_path = M25_4_OUTPUT_DIR / "imd_spatial_grid_verification.csv"
    assert spat_path.exists()
    df_spat = pd.read_csv(spat_path)
    
    param_map = dict(zip(df_spat["parameter"], df_spat["canonical_m25_ceres_grid"]))
    assert "32 points" in param_map.get("Latitude Span & Coordinates", "")
    assert "30 points" in param_map.get("Longitude Span & Coordinates", "")
    assert "960 cells" in param_map.get("Grid Cell Count & Overlap", "")
    
    land_map = dict(zip(df_spat["parameter"], df_spat["imd_1deg_dataset"]))
    assert "357 on-land" in land_map.get("Land vs Ocean Cell Coverage in M25 Domain", "")


def test_imd_missingness_and_quality():
    miss_path = M25_4_OUTPUT_DIR / "imd_missingness_audit.csv"
    assert miss_path.exists()
    df_miss = pd.read_csv(miss_path)
    
    cat_map = dict(zip(df_miss["category"], df_miss["m25_domain_daily_cell_count"]))
    assert cat_map.get("Structural Sentinel (-999.0)", "") == "603"
    assert cat_map.get("Negative Values (< 0.0 mm, excluding -999.0)", "") == "0"
    
    val_path = M25_4_OUTPUT_DIR / "imd_value_quality_audit.csv"
    assert val_path.exists()
    df_val = pd.read_csv(val_path)
    met_map = dict(zip(df_val["metric"], df_val["value"]))
    assert met_map.get("Negative Value Count (excluding -999.0 sentinel)") == "0 (0.000%)"
    assert met_map.get("Overall Value Quality Status") == "PASSED_HIGH_INTEGRITY"


def test_imd_integration_schema():
    schema_path = M25_4_OUTPUT_DIR / "imd_daily_integration_schema.json"
    assert schema_path.exists()
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    assert schema["title"] == "M25_IMD_Daily_Rainfall_Integration_Table"
    req_fields = set(schema["required"])
    assert {"year", "date", "latitude", "longitude", "rainfall_mm", "quality_flag"}.issubset(req_fields)


def test_readiness_decisions_and_manifest():
    man_path = M25_4_OUTPUT_DIR / "m25_4_manifest.json"
    assert man_path.exists()
    
    with open(man_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    assert manifest["milestone"] == "M25.4"
    assert manifest["final_decision_1deg_existing"] == "READY_WITH_LIMITATIONS"
    assert manifest["final_decision_025deg_target"] == "BLOCKED_FILE_NOT_FOUND"
    assert manifest["inventory_summary"]["temporal_coverage_pct"] == 100.0
    assert manifest["inventory_summary"]["valid_on_land_gauge_cells"] == 357
    assert manifest["inventory_summary"]["canonical_m25_domain_cells"] == 960


def test_handoff_zip_validity():
    zip_path = M25_4_OUTPUT_DIR / "M25.4-IMD-rainfall-data-readiness.zip"
    assert zip_path.exists()
    assert zipfile.is_zipfile(zip_path)
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.testzip() is None, "ZIP must not be corrupted"
        namelist = zf.namelist()
        assert len(namelist) >= 12
        assert "m25_4_readiness_report.md" in namelist
        assert "imd_rainfall_artifact_inventory.csv" in namelist
        assert "imd_temporal_coverage_by_year.csv" in namelist
        assert "imd_seasonal_coverage_summary.csv" in namelist


def test_mirroring_to_post_monsoon():
    assert M25_4_MIRROR_DIR.exists(), f"Mirrored directory must exist: {M25_4_MIRROR_DIR}"
    
    check_files = [
        "imd_rainfall_artifact_inventory.csv",
        "imd_rainfall_provenance_report.md",
        "imd_temporal_coverage_by_year.csv",
        "imd_seasonal_coverage_summary.csv",
        "imd_spatial_grid_verification.csv",
        "imd_missingness_audit.csv",
        "imd_value_quality_audit.csv",
        "m25_4_readiness_report.md",
        "m25_4_manifest.json",
    ]
    for fname in check_files:
        src = M25_4_OUTPUT_DIR / fname
        dst = M25_4_MIRROR_DIR / fname
        assert dst.exists(), f"Mirrored file missing: {fname}"
        assert src.stat().st_size == dst.stat().st_size, f"Size mismatch on mirrored {fname}"
