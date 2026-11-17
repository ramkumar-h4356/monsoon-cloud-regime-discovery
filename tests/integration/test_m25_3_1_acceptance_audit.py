"""
test_m25_3_1_acceptance_audit.py

Automated integration test suite for Milestone M25.3.1:
Final Scientific Consistency and Acceptance Audit.
"""

from __future__ import annotations

import json
from pathlib import Path
import zipfile
import pandas as pd
import pytest

REPO_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
POST_REPO_ROOT = Path("D:/Project Simulator/post_monsoon_research")
OUTPUT_DIR = REPO_ROOT / "reports" / "integration" / "m25_3" / "final_scientific_acceptance"
MIRROR_DIR = POST_REPO_ROOT / "reports" / "integration" / "m25_3" / "final_scientific_acceptance"


def test_acceptance_deliverables_existence():
    assert OUTPUT_DIR.exists(), f"Audit directory must exist: {OUTPUT_DIR}"
    
    expected_files = [
        "m25_3_final_acceptance_audit.md",
        "m25_3_evidence_matrix.csv",
        "seasonal_window_verification.csv",
        "spatial_grid_verification.csv",
        "established_population_reconciliation.csv",
        "premonsoon_clear_sky_semantics_audit.md",
        "temporal_stability_claim_audit.md",
        "statistical_claim_audit.csv",
        "m25_3_acceptance_manifest.json",
        "M25.3.1-final-scientific-acceptance-audit.zip",
    ]
    for fname in expected_files:
        fp = OUTPUT_DIR / fname
        assert fp.exists(), f"Deliverable missing: {fname}"
        assert fp.stat().st_size > 0, f"Deliverable is empty: {fname}"


def test_seasonal_window_verification():
    csv_path = OUTPUT_DIR / "seasonal_window_verification.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    
    assert len(df) == 3, "Must cover Pre, Established, and Post monsoon"
    season_map = dict(zip(df["season"], df["actual_analyzed_window"]))
    
    assert season_map["Pre-Monsoon"] == "April 15 - May 14"
    assert season_map["Established-Monsoon"] == "July 15 - August 13"
    assert season_map["Post-Monsoon"] == "October 15 - November 13"
    
    assert (df["days_per_year"] == 30).all()
    assert (df["years_analyzed"] == 12).all()
    assert (df["total_hours_per_cell"] == 8640).all()


def test_spatial_grid_verification():
    csv_path = OUTPUT_DIR / "spatial_grid_verification.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    
    dim_map = dict(zip(df["dimension"], df["actual_data_extracted"]))
    assert "32 points" in dim_map.get("Latitude Coordinates", "")
    assert "30 points" in dim_map.get("Longitude Coordinates", "")
    assert "960 grid cells" in dim_map.get("Grid Cell Count", "")
    assert "1.0 deg" in dim_map.get("Spatial Resolution", "")


def test_established_population_reconciliation():
    csv_path = OUTPUT_DIR / "established_population_reconciliation.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    
    item_map = dict(zip(df["metric_item"], df["true_empirical_count"]))
    assert item_map["Total Established-Monsoon Complete Cases"] == 290355
    assert item_map["Excluded Incomplete Grid-Days"] == 55245
    assert item_map["Baseline K=2 Cluster 0"] == 155834
    assert item_map["Baseline K=2 Cluster 1"] == 134521
    assert item_map["Log K=2 Cluster 0"] == 145290
    assert item_map["Log K=2 Cluster 1"] == 145065
    assert item_map["Log K=3 Cluster 0"] == 93646
    assert item_map["Log K=3 Cluster 1"] == 80702
    assert item_map["Log K=3 Cluster 2"] == 116007
    
    # Check that sum of clusters equals total complete cases
    assert item_map["Baseline K=2 Cluster 0"] + item_map["Baseline K=2 Cluster 1"] == 290355
    assert item_map["Log K=2 Cluster 0"] + item_map["Log K=2 Cluster 1"] == 290355
    assert (item_map["Log K=3 Cluster 0"] + item_map["Log K=3 Cluster 1"] + item_map["Log K=3 Cluster 2"]) == 290355


def test_evidence_matrix_schema_and_classifications():
    csv_path = OUTPUT_DIR / "m25_3_evidence_matrix.csv"
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    
    assert len(df) == 8, f"Must cover all 8 audit questions, found {len(df)}"
    valid_classes = {"VERIFIED", "EXPLAINED_DIFFERENCE", "CORRECTION_REQUIRED", "UNRESOLVED"}
    assert set(df["finding_classification"]).issubset(valid_classes)


def test_acceptance_manifest_schema_and_decision():
    man_path = OUTPUT_DIR / "m25_3_acceptance_manifest.json"
    assert man_path.exists()
    
    with open(man_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    assert manifest["milestone"] == "M25.3.1"
    assert manifest["parent_milestone"] == "M25.3"
    assert manifest["final_decision"] == "READY_TO_FREEZE_WITH_DOCUMENTED_LIMITATIONS"
    assert "audited_dimensions" in manifest
    assert len(manifest["deliverables"]) >= 9


def test_zip_archive_integrity():
    zip_path = OUTPUT_DIR / "M25.3.1-final-scientific-acceptance-audit.zip"
    assert zip_path.exists()
    assert zipfile.is_zipfile(zip_path)
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.testzip() is None, "ZIP must not be corrupted"
        namelist = zf.namelist()
        assert len(namelist) >= 9
        assert "m25_3_final_acceptance_audit.md" in namelist
        assert "m25_3_evidence_matrix.csv" in namelist
        assert "seasonal_window_verification.csv" in namelist


def test_mirroring_to_post_monsoon():
    assert MIRROR_DIR.exists(), f"Mirrored directory must exist: {MIRROR_DIR}"
    
    for fname in [
        "m25_3_final_acceptance_audit.md",
        "m25_3_evidence_matrix.csv",
        "seasonal_window_verification.csv",
        "spatial_grid_verification.csv",
        "established_population_reconciliation.csv",
        "m25_3_acceptance_manifest.json",
    ]:
        src = OUTPUT_DIR / fname
        dst = MIRROR_DIR / fname
        assert dst.exists(), f"Mirrored file missing: {fname}"
        assert src.stat().st_size == dst.stat().st_size, f"Size mismatch on {fname}"
