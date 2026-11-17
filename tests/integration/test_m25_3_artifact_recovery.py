"""
test_m25_3_artifact_recovery.py

Automated integration test suite for Milestone M25.3:
Phase 2 & Phase 3 Independent Seasonal Artifact Recovery, Git Provenance Verification and Correspondence Readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
import zipfile
import pandas as pd
import pytest

REPO_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
RECOVERY_DIR = REPO_ROOT / "reports" / "integration" / "m25_3" / "artifact_recovery"


def test_noshin_artifact_inventory_and_checksums():
    inv_path = RECOVERY_DIR / "noshin_artifact_inventory.csv"
    check_path = RECOVERY_DIR / "noshin_checksum_verification.csv"
    
    assert inv_path.exists(), "noshin_artifact_inventory.csv must exist"
    assert check_path.exists(), "noshin_checksum_verification.csv must exist"
    
    df_inv = pd.read_csv(inv_path)
    assert len(df_inv) == 21, f"Expected 21 inventory rows, found {len(df_inv)}"
    assert (df_inv["verification_status"] == "VERIFIED_INTACT").all(), "All files must be VERIFIED_INTACT"
    
    df_check = pd.read_csv(check_path)
    assert len(df_check) >= 20, "Expected at least 20 verified entries in checksum table"
    assert df_check["match"].all(), "All calculated checksums must match recorded checksums"


def test_noshin_coordinate_and_label_integrity():
    cov_path = RECOVERY_DIR / "noshin_label_coverage.csv"
    assert cov_path.exists(), "noshin_label_coverage.csv must exist"
    
    df_cov = pd.read_csv(cov_path)
    assert len(df_cov) == 12, "Must cover exactly 12 years (2010-2021)"
    assert df_cov["year"].tolist() == list(range(2010, 2022))
    assert (df_cov["total_grid_hours"] == 691200).all(), "Every year must have exactly 691,200 grid-hours"
    
    total_obs = df_cov["total_grid_hours"].sum()
    assert total_obs == 8294400, f"Expected 8,294,400 total observations, found {total_obs}"
    
    valid_cloudy = df_cov["valid_cloudy_count"].sum()
    clear_sky = df_cov["clear_sky_count"].sum()
    assert valid_cloudy == 8252116, f"Expected 8,252,116 valid cloudy observations, found {valid_cloudy}"
    assert clear_sky == 42284, f"Expected 42,284 clear sky observations, found {clear_sky}"
    assert valid_cloudy + clear_sky == 8294400


def test_noshin_matching_gate():
    match_path = RECOVERY_DIR / "noshin_observation_matching.csv"
    assert match_path.exists(), "noshin_observation_matching.csv must exist"
    
    df_match = pd.read_csv(match_path)
    assert len(df_match) == 12
    assert df_match["grid_shape_match"].all(), "All grid shapes must match (720, 32, 30)"
    assert df_match["coordinate_match"].all(), "All coordinates must match raw CERES"
    assert (df_match["matching_gate_status"] == "PASSED_VERIFIED").all(), "All 12 matching gates must pass"


def test_abhin_provenance_and_git_ref():
    prov_path = RECOVERY_DIR / "abhin_provenance_audit.csv"
    assert prov_path.exists(), "abhin_provenance_audit.csv must exist"
    
    df_prov = pd.read_csv(prov_path)
    items = dict(zip(df_prov["audit_item"], df_prov["verified_state"]))
    assert "882edfa" in items["Latest Local Commit"], "Commit must reference 882edfa"
    assert "Abhin S" in items["Commit Author"]
    assert "UNVERIFIED" in items["Remote Server Verification"], "Must record remote verification status"


def test_abhin_missing_assignment_artifacts():
    inv_path = RECOVERY_DIR / "abhin_artifact_inventory.csv"
    match_path = RECOVERY_DIR / "abhin_observation_matching.csv"
    
    assert inv_path.exists(), "abhin_artifact_inventory.csv must exist"
    assert match_path.exists(), "abhin_observation_matching.csv must exist"
    
    df_inv = pd.read_csv(inv_path)
    missing_items = df_inv[df_inv["availability"] == "MISSING"]["artifact_name"].tolist()
    assert any("established_monsoon_fixed_cluster_assignments.csv" in m for m in missing_items), \
        "Assignment table must be explicitly recorded as MISSING"
    
    df_match = pd.read_csv(match_path)
    status_series = df_match["impact_on_correspondence"].tolist()
    assert any("CORRESPONDENCE IMPOSSIBLE WITHOUT DATA FABRICATION" in s for s in status_series)


def test_abhin_complete_case_metrics():
    cc_path = RECOVERY_DIR / "abhin_complete_case_audit.csv"
    assert cc_path.exists(), "abhin_complete_case_audit.csv must exist"
    
    df_cc = pd.read_csv(cc_path)
    dim_dict = dict(zip(df_cc["dimension"], df_cc["value"]))
    assert dim_dict["Raw Daily Observations"] == "345,600"
    assert dim_dict["Complete Case Retained"] == "290,355"
    assert dim_dict["Feature Group B"] == "14"


def test_recovery_manifest_structure():
    manifest_path = RECOVERY_DIR / "m25_3_two_workstream_recovery_manifest.json"
    assert manifest_path.exists(), "m25_3_two_workstream_recovery_manifest.json must exist"
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["milestone"] == "M25.3"
    assert data["workstreams"]["noshin_pre_monsoon"]["classification"] == "VERIFIED_AND_READY_FOR_CORRESPONDENCE"
    assert data["workstreams"]["abhin_established_monsoon"]["classification"] == "BLOCKED_MISSING_ASSIGNMENT_ARTIFACTS"
    assert len(data["deliverables"]) == 13


def test_recovery_report_contents():
    report_path = RECOVERY_DIR / "m25_3_two_workstream_recovery_report.md"
    assert report_path.exists(), "m25_3_two_workstream_recovery_report.md must exist"
    
    text = report_path.read_text(encoding="utf-8")
    assert "Executive Summary" in text
    assert "Noshin Pre-Monsoon Recovery Audit" in text
    assert "Abhin Established-Monsoon Audit" in text
    assert "Cross-Workstream Recovery Comparison" in text
    assert "VERIFIED_AND_READY_FOR_CORRESPONDENCE" in text
    assert "BLOCKED_MISSING_ASSIGNMENT_ARTIFACTS" in text


def test_handoff_zip_archives():
    p1 = RECOVERY_DIR / "M25.3-pre-monsoon-verified-handoff.zip"
    p2 = RECOVERY_DIR / "M25.3-established-monsoon-verified-handoff.zip"
    p3 = RECOVERY_DIR / "M25.3-seasonal-artifact-recovery-report.zip"
    
    for p in [p1, p2, p3]:
        assert p.exists(), f"Archive {p.name} must exist"
        assert p.stat().st_size > 0, f"Archive {p.name} must be non-empty"
        with zipfile.ZipFile(p, "r") as z:
            assert z.testzip() is None, f"Archive {p.name} failed CRC integrity test"
