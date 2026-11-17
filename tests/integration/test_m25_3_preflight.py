"""
test_m25_3_preflight.py

Automated integration test suite for Milestone M25.2 Scientific Review Corrections
and Milestone M25.3 Preflight Artifact Readiness.

Verifies:
1. M25.2 Scientific Review Corrections document exists, covers all 8 corrections,
   and is referenced in M25_2_three_season_methodological_reconciliation.md.
2. Assignment artifact inventory CSV schema, rows, and verified files on disk.
3. Seasonal matching readiness table schema and feasibility classifications.
4. Preflight manifest JSON schema and consistency.
5. Physical presence and shape integrity of verified label arrays on disk.
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest


CANONICAL_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
REPORTS_INTEGRATION = CANONICAL_ROOT / "reports/integration"
DOCS_METHODOLOGY = CANONICAL_ROOT / "docs/methodology"
DATA_PROCESSED = CANONICAL_ROOT / "data/processed"


def test_m25_2_corrections_file_exists():
    """Verify that the M25.2 scientific review corrections document exists and is non-empty."""
    path = REPORTS_INTEGRATION / "m25_2/m25_2_scientific_review_corrections.md"
    assert path.exists(), f"Missing corrections file: {path}"
    content = path.read_text(encoding="utf-8")
    assert len(content) > 1000, "Corrections document is unexpectedly short"


def test_m25_2_corrections_content_coverage():
    """Verify that all 8 required scientific corrections are covered in the document."""
    path = REPORTS_INTEGRATION / "m25_2/m25_2_scientific_review_corrections.md"
    content = path.read_text(encoding="utf-8")

    assert "Correction 1" in content and "Hypothesis" in content, "Correction 1 missing"
    assert "Correction 2" in content and "Complete-Case" in content, "Correction 2 missing"
    assert "Correction 3" in content and "Scaling Sensitivity" in content, "Correction 3 missing"
    assert "Correction 4" in content and "CA-A" in content, "Correction 4 missing"
    assert "Correction 5" in content and "Candidate" in content, "Correction 5 missing"
    assert "Correction 6" in content and "30-Day Windows" in content, "Correction 6 missing"
    assert "Correction 7" in content and "matching season" in content.lower(), "Correction 7 missing"
    assert "Correction 8" in content and "GAP-01" in content and "OPEN" in content, "Correction 8 missing"

    # Specific key phrases
    assert "training median" in content.lower(), "CA-A training median missing"
    assert "unprofiled" in content.lower() or "not been profiled" in content.lower(), "Unprofiled missing"


def test_m25_2_reconciliation_document_amended():
    """Verify that M25_2_three_season_methodological_reconciliation.md contains the revision notice."""
    path = DOCS_METHODOLOGY / "M25_2_three_season_methodological_reconciliation.md"
    assert path.exists(), f"Missing methodology doc: {path}"
    content = path.read_text(encoding="utf-8")
    assert "Revision Notice (v1.1)" in content, "Revision notice missing from methodology doc"
    assert "m25_2_scientific_review_corrections.md" in content, "Link to corrections note missing"


def test_assignment_artifact_inventory_schema():
    """Verify the schema and integrity of assignment_artifact_inventory.csv."""
    path = REPORTS_INTEGRATION / "m25_3_preflight/assignment_artifact_inventory.csv"
    assert path.exists(), f"Missing inventory file: {path}"

    df = pd.read_csv(path)
    expected_cols = [
        "workstream", "artifact_name", "artifact_type", "file_format",
        "canonical_relative_path", "absolute_path", "observation_count",
        "file_size_bytes", "sha256_hash", "git_status", "disk_existence",
        "readiness_for_m25_3", "notes"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing column {col} in inventory CSV"

    assert len(df) == 17, f"Expected 17 rows, found {len(df)}"

    # Check workstreams present
    workstreams = df["workstream"].unique()
    assert any("Combined" in w for w in workstreams), "Combined workstream missing"
    assert any("Post-Monsoon" in w for w in workstreams), "Post-Monsoon workstream missing"
    assert any("Established" in w for w in workstreams), "Established Monsoon workstream missing"
    assert any("Pre-Monsoon" in w for w in workstreams), "Pre-Monsoon workstream missing"


def test_seasonal_matching_readiness_schema():
    """Verify the schema and feasibility classifications of seasonal_matching_readiness.csv."""
    path = REPORTS_INTEGRATION / "m25_3_preflight/seasonal_matching_readiness.csv"
    assert path.exists(), f"Missing readiness file: {path}"

    df = pd.read_csv(path)
    expected_cols = [
        "season_name", "combined_model_season_id", "temporal_window",
        "total_seasonal_observations_ceres", "workstream_observation_count",
        "matching_key_definition", "coordinate_precision",
        "key_uniqueness_verified", "matching_population_type",
        "feasibility_classification", "blocker_description", "unblocking_procedure"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing column {col} in readiness CSV"

    assert len(df) == 3, f"Expected 3 rows for 3 seasons, found {len(df)}"

    # Check feasibility classifications
    pre_row = df[df["season_name"] == "pre_monsoon"].iloc[0]
    est_row = df[df["season_name"] == "established_monsoon"].iloc[0]
    post_row = df[df["season_name"] == "post_monsoon"].iloc[0]

    assert pre_row["feasibility_classification"] == "BLOCKED_MISSING_ASSIGNMENT_ARTIFACT"
    assert est_row["feasibility_classification"] == "BLOCKED_MISSING_ASSIGNMENT_ARTIFACT"
    assert post_row["feasibility_classification"] == "READY"

    assert post_row["total_seasonal_observations_ceres"] == 8294400
    assert post_row["workstream_observation_count"] == 8294400


def test_m25_3_preflight_manifest_validity():
    """Verify that m25_3_preflight_manifest.json is valid and structurally complete."""
    path = REPORTS_INTEGRATION / "m25_3_preflight/m25_3_preflight_manifest.json"
    assert path.exists(), f"Missing manifest: {path}"

    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["manifest_id"] == "M25_3_PREFLIGHT_001"
    assert manifest["milestone"] == "M25.3_Preflight"
    assert manifest["overall_feasibility_status"] == "PARTIALLY_READY_POST_MONSOON_EXECUTABLE"
    assert manifest["scientific_review_corrections"]["status"] == "APPLIED_ADDITIVE_NOTE"
    assert manifest["scientific_review_corrections"]["corrections_count"] == 8

    # Workstream status
    ws = manifest["workstream_readiness"]
    assert ws["post_monsoon"]["feasibility_status"] == "READY"
    assert ws["post_monsoon"]["matched_observation_count"] == 8294400
    assert ws["combined_3season"]["feasibility_status"] == "READY"
    assert ws["combined_3season"]["total_observation_count"] == 24883200
    assert ws["pre_monsoon"]["feasibility_status"] == "BLOCKED_MISSING_ASSIGNMENT_ARTIFACT"
    assert ws["established_monsoon"]["feasibility_status"] == "BLOCKED_MISSING_ASSIGNMENT_ARTIFACT"


def test_physical_label_arrays_on_disk():
    """Verify that the existing on-disk label arrays for Combined and Post-Monsoon are readable and valid."""
    comb_path = DATA_PROCESSED / "combined_3season/combined_3season_cluster_labels.npy"
    assert comb_path.exists(), f"Missing combined labels: {comb_path}"
    comb_labels = np.load(comb_path, mmap_mode="r")
    assert comb_labels.shape == (24883200,), f"Unexpected combined labels shape: {comb_labels.shape}"
    assert comb_labels.dtype == np.uint8, f"Unexpected combined labels dtype: {comb_labels.dtype}"

    post_path = DATA_PROCESSED / "post_monsoon/clustering/post_monsoon_cluster_labels_k4.npy"
    assert post_path.exists(), f"Missing post-monsoon labels: {post_path}"
    post_labels = np.load(post_path, mmap_mode="r")
    assert post_labels.shape == (8294400,), f"Unexpected post-monsoon labels shape: {post_labels.shape}"
    assert post_labels.dtype == np.uint8, f"Unexpected post-monsoon labels dtype: {post_labels.dtype}"
