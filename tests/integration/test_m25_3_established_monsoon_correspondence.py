"""
test_m25_3_established_monsoon_correspondence.py

Automated integration test suite for Milestone M25.3:
Phase 3 Established-Monsoon Artifact Verification and Correspondence.
"""

from __future__ import annotations

import json
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
OUTPUT_DIR = REPO_ROOT / "reports" / "integration" / "m25_3" / "established_monsoon_correspondence"
RECOVERED_DIR = OUTPUT_DIR / "recovered_artifacts"


def test_recovered_artifacts_inventory_and_integrity():
    inv_path = OUTPUT_DIR / "recovered_artifacts_inventory.csv"
    assert inv_path.exists(), "recovered_artifacts_inventory.csv must exist"
    
    df_inv = pd.read_csv(inv_path)
    assert len(df_inv) == 6, f"Expected 6 recovered files, found {len(df_inv)}"
    assert (df_inv["integrity_status"] == "VERIFIED_MATCH").all()
    
    # Check physical existence of all 6 files
    for fname in df_inv["filename"]:
        fp = RECOVERED_DIR / fname
        assert fp.exists(), f"Recovered file {fname} must exist on disk"
        assert fp.stat().st_size > 0, f"Recovered file {fname} must be non-empty"


def test_schema_and_provenance_audit():
    audit_path = OUTPUT_DIR / "provenance_and_schema_audit.csv"
    assert audit_path.exists(), "provenance_and_schema_audit.csv must exist"
    
    df_audit = pd.read_csv(audit_path)
    dim_dict = dict(zip(df_audit["dimension"], df_audit["observed_value"]))
    assert dim_dict["Assignments Row Count"] == "290355"
    assert dim_dict["Missing Values in Assignments"] == "0"
    assert dim_dict["Space-Time Key Duplicates"] == "0"
    assert dim_dict["Metadata-Assignments Key Alignment"] == "True"


def test_metadata_feature_ordering():
    feat_path = OUTPUT_DIR / "metadata_feature_ordering_audit.csv"
    assert feat_path.exists(), "metadata_feature_ordering_audit.csv must exist"
    
    df_feat = pd.read_csv(feat_path)
    assert len(df_feat) == 14, "Must cover all 14 Group B variables"
    assert df_feat["header_match"].all(), "Feature headers in NPZ must match manifest ordering"


def test_m25_daily_aggregation_completeness():
    agg_path = OUTPUT_DIR / "m25_daily_regime_aggregation.csv"
    assert agg_path.exists(), "m25_daily_regime_aggregation.csv must exist"
    
    df_agg = pd.read_csv(agg_path)
    assert len(df_agg) == 345600, f"Expected 345,600 daily rows, found {len(df_agg)}"
    assert (df_agg["valid_assigned_hours"] == 24).all(), "Valid assigned hours must be 24 for all rows"
    assert (df_agg["missing_hours"] == 0).all(), "Missing hours must be 0"
    
    # Check fraction sum equals 1.0
    frac_sums = df_agg["m25_frac_k0"] + df_agg["m25_frac_k1"] + df_agg["m25_frac_k2"] + df_agg["m25_frac_k3"]
    np.testing.assert_allclose(frac_sums.values, 1.0, atol=1e-5)


def test_exact_observation_matching():
    match_path = OUTPUT_DIR / "observation_matching_report.csv"
    year_path = OUTPUT_DIR / "yearly_matching_coverage.csv"
    assert match_path.exists(), "observation_matching_report.csv must exist"
    assert year_path.exists(), "yearly_matching_coverage.csv must exist"
    
    df_match = pd.read_csv(match_path)
    metric_dict = dict(zip(df_match["metric"], df_match["value"]))
    assert metric_dict["M25 Daily Grid-Days (12 years x 30 days x 960 cells)"] == 345600
    assert metric_dict["Abhin Complete-Case Observations"] == 290355
    assert metric_dict["Exact Space-Time Key Matches"] == 290355
    assert metric_dict["M25 Observations Excluded by Abhin Complete-Case Filter"] == 55245
    assert metric_dict["Duplicate Keys in Abhin"] == 0
    assert metric_dict["Duplicate Keys in M25"] == 0
    
    df_year = pd.read_csv(year_path)
    assert len(df_year) == 12, "Must cover 12 years (2010-2021)"
    assert df_year["m25_grid_days"].sum() == 345600
    assert df_year["abhin_matched_obs"].sum() == 290355


def test_contingency_matrices_and_normalization():
    for var in ["baseline_k2", "log_k2", "log_k3"]:
        cm_path = OUTPUT_DIR / f"contingency_{var}.csv"
        assert cm_path.exists(), f"contingency_{var}.csv must exist"
        cm_df = pd.read_csv(cm_path, index_col=0)
        assert cm_df.values.sum() == 290355, f"Contingency matrix sum must equal 290,355 for {var}"
        
    df_row = pd.read_csv(OUTPUT_DIR / "row_normalized_correspondence.csv")
    row_sums = df_row[["p_m25_k0", "p_m25_k1", "p_m25_k2", "p_m25_k3"]].sum(axis=1)
    np.testing.assert_allclose(row_sums.values, 1.0, atol=1e-5)


def test_soft_assignment_profiles():
    soft_path = OUTPUT_DIR / "soft_assignment_profiles.csv"
    assert soft_path.exists(), "soft_assignment_profiles.csv must exist"
    
    df_soft = pd.read_csv(soft_path)
    assert len(df_soft) == 7, "2 baseline + 2 log_k2 + 3 log_k3 = 7 profile rows"
    
    # For baseline_k2, Cluster 1 has higher convective fraction f3 than Cluster 0
    b_c0 = df_soft[(df_soft["variant"] == "baseline_k2") & (df_soft["abhin_cluster"] == 0)].iloc[0]
    b_c1 = df_soft[(df_soft["variant"] == "baseline_k2") & (df_soft["abhin_cluster"] == 1)].iloc[0]
    assert b_c1["m25_f3_mean"] > b_c0["m25_f3_mean"]
    assert b_c1["m25_f3_mean"] > 0.90
    assert b_c0["m25_f0_mean"] > b_c1["m25_f0_mean"]


def test_splitwise_metrics():
    split_path = OUTPUT_DIR / "splitwise_correspondence_metrics.csv"
    assert split_path.exists(), "splitwise_correspondence_metrics.csv must exist"
    
    df_split = pd.read_csv(split_path)
    splits = df_split["temporal_split"].unique().tolist()
    assert "Training (2010-2016)" in splits
    assert "Development (2017-2018)" in splits
    assert "Holdout (2019-2021)" in splits
    assert "Pooled (2010-2021)" in splits
    assert not df_split["ari"].isna().any()
    assert not df_split["nmi"].isna().any()


def test_manifest_report_and_figures():
    manifest_path = OUTPUT_DIR / "m25_3_established_monsoon_manifest.json"
    report_path = OUTPUT_DIR / "m25_3_established_monsoon_correspondence_report.md"
    assert manifest_path.exists(), "Manifest must exist"
    assert report_path.exists(), "Report must exist"
    
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["milestone"] == "M25.3"
    assert data["matching_results"]["matched_exact_obs"] == 290355
    
    fig_dir = OUTPUT_DIR / "figures"
    for fig_name in ["contingency_heatmaps.png", "soft_assignment_fractions.png", "yearly_nmi_trend.png"]:
        fp = fig_dir / fig_name
        assert fp.exists(), f"Figure {fig_name} must exist"
        assert fp.stat().st_size > 0, f"Figure {fig_name} must be non-empty"


def test_handoff_zip_validity():
    zip_path = OUTPUT_DIR / "M25.3-established-monsoon-correspondence.zip"
    assert zip_path.exists(), "M25.3-established-monsoon-correspondence.zip must exist"
    assert zip_path.stat().st_size > 1000000, "ZIP archive should contain full deliverables and data"
    
    with zipfile.ZipFile(zip_path, "r") as z:
        assert z.testzip() is None, "ZIP file must pass CRC integrity check"
