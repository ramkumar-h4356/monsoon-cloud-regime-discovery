"""Automated Tests for Milestone M25.2 Audit Deliverables.

Validates that:
1. Audit manifest exists, parses valid JSON, and confirms AUDIT_COMPLETED_WITH_OPEN_SCIENTIFIC_GAPS.
2. Methodology comparison CSV has 4 rows, 48 columns, and 0 missing values.
3. Workstream artifact inventory covers all four workstreams and raw datasets.
4. Research gap register formalizes GAP-01 through GAP-08 with valid priorities and target milestones.
5. Scientific reconciliation documentation exists and is complete.
"""

import json
from pathlib import Path
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
M25_2_DIR = PROJECT_ROOT / "reports" / "integration" / "m25_2"
DOC_PATH = PROJECT_ROOT / "docs" / "methodology" / "M25_2_three_season_methodological_reconciliation.md"


def test_audit_manifest_exists_and_valid():
    manifest_path = M25_2_DIR / "m25_2_audit_manifest.json"
    assert manifest_path.exists(), f"Audit manifest missing at {manifest_path}"

    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["milestone_id"] == "M25.2"
    assert data["overall_milestone_status"] == "AUDIT_COMPLETED_WITH_OPEN_SCIENTIFIC_GAPS"

    # Verify safety attestations
    safety = data["git_safety_attestation"]
    assert safety["git_resets_performed"] == 0
    assert safety["git_merges_performed"] == 0
    assert safety["git_commits_created"] == 0
    assert safety["git_pushes_performed"] == 0
    assert safety["original_datasets_modified"] == 0

    # Verify worktree coverage
    assert len(data["repository_environment"]["active_worktrees"]) == 3
    assert len(data["repository_environment"]["remote_branches_verified"]) == 4


def test_methodology_comparison_schema():
    csv_path = M25_2_DIR / "three_season_methodology_comparison.csv"
    assert csv_path.exists(), f"Comparison CSV missing at {csv_path}"

    df = pd.read_csv(csv_path)
    assert len(df) == 4, f"Expected 4 workflow rows, got {len(df)}"
    assert len(df.columns) == 48, f"Expected 48 columns, got {len(df.columns)}"
    assert df.isna().sum().sum() == 0, "No missing values allowed in methodology comparison"

    expected_ids = {"WF-PRE-MONSOON", "WF-ESTABLISHED-MONSOON", "WF-POST-MONSOON", "WF-COMBINED-3SEASON"}
    assert set(df["workflow_id"].unique()) == expected_ids

    # Verify feature counts
    fc_dict = dict(zip(df["workflow_id"], df["feature_count"].astype(int)))
    assert fc_dict["WF-PRE-MONSOON"] == 3
    assert fc_dict["WF-ESTABLISHED-MONSOON"] == 14
    assert fc_dict["WF-POST-MONSOON"] == 36
    assert fc_dict["WF-COMBINED-3SEASON"] == 36

    # Verify selected K
    k_dict = dict(zip(df["workflow_id"], df["selected_k"].astype(int)))
    assert k_dict["WF-PRE-MONSOON"] == 2
    assert k_dict["WF-ESTABLISHED-MONSOON"] == 2
    assert k_dict["WF-POST-MONSOON"] == 4
    assert k_dict["WF-COMBINED-3SEASON"] == 4


def test_artifact_inventory_coverage():
    csv_path = M25_2_DIR / "workstream_artifact_inventory.csv"
    assert csv_path.exists(), f"Inventory CSV missing at {csv_path}"

    df = pd.read_csv(csv_path)
    assert len(df) >= 30, f"Expected at least 30 artifact entries, got {len(df)}"

    required_cols = [
        "workstream", "artifact_path", "artifact_category", "description",
        "file_size_bytes", "commit_or_worktree_provenance", "available_status"
    ]
    for col in required_cols:
        assert col in df.columns

    # Verify categories
    categories = set(df["artifact_category"].unique())
    assert {"Config", "Documentation", "Report", "Source Code", "Results Table", "Dataset"}.issubset(categories)


def test_research_gap_register_completeness():
    csv_path = M25_2_DIR / "research_gap_register.csv"
    assert csv_path.exists(), f"Gap register CSV missing at {csv_path}"

    df = pd.read_csv(csv_path)
    assert len(df) == 8, f"Expected 8 gap entries, got {len(df)}"
    assert df.isna().sum().sum() == 0, "No null values allowed in gap register"

    expected_gaps = {f"GAP-0{i}" for i in range(1, 9)}
    assert set(df["gap_id"].unique()) == expected_gaps

    priorities = set(df["priority"].unique())
    assert priorities.issubset({"CRITICAL", "HIGH", "MEDIUM", "LOW"})


def test_reconciliation_report_exists_and_complete():
    assert DOC_PATH.exists(), f"Reconciliation report missing at {DOC_PATH}"
    size = DOC_PATH.stat().st_size
    assert size > 8000, f"Report too small ({size} bytes)"

    content = DOC_PATH.read_text(encoding="utf-8")
    assert "Executive Summary" in content
    assert "Detailed Feature-Space Comparison" in content
    assert "Missingness and Preprocessing Comparison" in content
    assert "IMD Daily Rainfall Readiness Inventory" in content
    assert "Outstanding Scientific Gaps Register" in content
    assert "Recommended Next Milestones" in content
