"""
test_m25_3_tri_seasonal_synthesis.py

Automated integration test suite for Milestone M25.3:
Integrated Tri-Seasonal Correspondence, Scientific Audit & Synthesis.
"""

from __future__ import annotations

import json
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
POST_REPO_ROOT = Path("D:/Project Simulator/post_monsoon_research")
OUTPUT_DIR = REPO_ROOT / "reports" / "integration" / "m25_3" / "tri_seasonal_synthesis"
MIRROR_DIR = POST_REPO_ROOT / "reports" / "integration" / "m25_3" / "tri_seasonal_synthesis"


def test_tri_seasonal_deliverables_existence():
    assert OUTPUT_DIR.exists(), f"Synthesis directory must exist: {OUTPUT_DIR}"
    
    expected_files = [
        "tri_seasonal_artifact_inventory.csv",
        "tri_seasonal_methodology_comparison.csv",
        "tri_seasonal_correspondence_summary.csv",
        "tri_seasonal_cluster_profiles.csv",
        "tri_seasonal_temporal_stability.csv",
        "tri_seasonal_scientific_audit.md",
        "tri_seasonal_synthesis_report.md",
        "tri_seasonal_manifest.json",
        "M25.3-integrated-tri-seasonal-synthesis.zip",
    ]
    for fname in expected_files:
        fp = OUTPUT_DIR / fname
        assert fp.exists(), f"Deliverable missing: {fname}"
        assert fp.stat().st_size > 0, f"Deliverable is empty: {fname}"
        
    expected_figures = [
        "tri_seasonal_metrics_comparison.png",
        "tri_seasonal_temporal_stability_trend.png",
    ]
    fig_dir = OUTPUT_DIR / "figures"
    assert fig_dir.exists(), "Figures directory must exist"
    for fig_name in expected_figures:
        fig_path = fig_dir / fig_name
        assert fig_path.exists(), f"Figure missing: {fig_name}"
        assert fig_path.stat().st_size > 1000, f"Figure too small / corrupt: {fig_name}"


def test_artifact_inventory_integrity():
    inv_path = OUTPUT_DIR / "tri_seasonal_artifact_inventory.csv"
    assert inv_path.exists()
    df_inv = pd.read_csv(inv_path)
    
    assert len(df_inv) >= 7, f"Expected at least 7 inventory entries, found {len(df_inv)}"
    assert (df_inv["verification_status"].str.startswith("VERIFIED")).all(), "All artifacts must be verified"
    assert (df_inv["sha256"].str.len() > 0).all(), "All SHA256 / hash tokens must be non-empty"
    # Ensure physical file rows have 64-char SHA256 hashes
    file_rows = df_inv[~df_inv["sha256"].str.startswith("VERIFIED_MATCH") & ~df_inv["sha256"].str.startswith("GIT_COMMIT")]
    assert (file_rows["sha256"].str.len() == 64).all(), "File SHA256 hashes must be valid 64-char strings"
    
    seasons = set(df_inv["season"])
    assert "Pre-Monsoon" in seasons
    assert "Established-Monsoon" in seasons
    assert "Post-Monsoon" in seasons
    assert "Combined 3-Season" in seasons


def test_methodology_comparison_schema():
    meth_path = OUTPUT_DIR / "tri_seasonal_methodology_comparison.csv"
    assert meth_path.exists()
    df_meth = pd.read_csv(meth_path)
    
    assert "dimension" in df_meth.columns
    assert "pre_monsoon" in df_meth.columns
    assert "established_monsoon" in df_meth.columns
    assert "post_monsoon" in df_meth.columns
    
    dim_map = dict(zip(df_meth["dimension"], df_meth["established_monsoon"]))
    assert "Daily Aggregation" in dim_map.get("Temporal Resolution", "")
    assert "14 features" in dim_map.get("Feature Space Count", "")
    assert "290,355" in dim_map.get("Complete Case / Retention", "")
    assert "55,245" in dim_map.get("Excluded Incomplete Obs", "")
    assert "NOT DIRECTLY COMPARABLE" in dim_map.get("Direct Design Comparability", "")


def test_correspondence_summary_metrics():
    corr_path = OUTPUT_DIR / "tri_seasonal_correspondence_summary.csv"
    assert corr_path.exists()
    df_corr = pd.read_csv(corr_path)
    
    # Pre-Monsoon cloudy-only
    pre_cloudy = df_corr[(df_corr["season"] == "Pre-Monsoon") & (df_corr["variant"] == "cloudy_only_k2")].iloc[0]
    assert pre_cloudy["matched_observations"] == 8252116
    assert abs(pre_cloudy["coverage_pct"] - 99.49) < 0.1
    assert abs(pre_cloudy["ari"] - 0.1055) < 0.005
    assert abs(pre_cloudy["nmi"] - 0.1420) < 0.005
    
    # Pre-Monsoon all obs
    pre_all = df_corr[(df_corr["season"] == "Pre-Monsoon") & (df_corr["variant"] == "all_observations_k3")].iloc[0]
    assert pre_all["matched_observations"] == 8294400
    assert abs(pre_all["coverage_pct"] - 100.0) < 0.01
    assert abs(pre_all["ari"] - 0.1011) < 0.005
    assert abs(pre_all["nmi"] - 0.1415) < 0.005
    
    # Established-Monsoon baseline
    est_base = df_corr[(df_corr["season"] == "Established-Monsoon") & (df_corr["variant"] == "baseline_k2")].iloc[0]
    assert est_base["matched_observations"] == 290355
    assert abs(est_base["coverage_pct"] - 84.01) < 0.1
    assert abs(est_base["ari"] - (-0.0023)) < 0.005
    assert abs(est_base["nmi"] - 0.0698) < 0.005
    assert "NOT DIRECTLY COMPARABLE" in est_base["design_comparability_note"]
    
    # Established-Monsoon log
    est_log = df_corr[(df_corr["season"] == "Established-Monsoon") & (df_corr["variant"] == "log_k2")].iloc[0]
    assert est_log["matched_observations"] == 290355
    assert abs(est_log["ari"] - 0.0142) < 0.005
    assert abs(est_log["nmi"] - 0.0732) < 0.005
    
    # Post-Monsoon
    post = df_corr[df_corr["season"] == "Post-Monsoon"].iloc[0]
    assert post["matched_observations"] == 8294400
    assert abs(post["coverage_pct"] - 100.0) < 0.01
    assert abs(post["ari"] - (-0.0576)) < 0.005
    assert abs(post["nmi"] - 0.0422) < 0.005


def test_cluster_profiles_taxonomy():
    prof_path = OUTPUT_DIR / "tri_seasonal_cluster_profiles.csv"
    assert prof_path.exists()
    df_prof = pd.read_csv(prof_path)
    
    assert len(df_prof) == 4, "Must cover all 4 M25 regimes (R0, R1, R2, R3)"
    regimes = dict(zip(df_prof["m25_regime_id"], df_prof["authoritative_name"]))
    assert "Multi-Layer Mixed" in regimes["R0"]
    assert "Shallow Cumulus" in regimes["R1"]
    assert "Deep Convective" in regimes["R2"]
    assert "Thin Cirrus" in regimes["R3"]
    
    # Sum of shares must equal approximately 100% per season
    assert abs(df_prof["pre_monsoon_share_pct"].sum() - 100.0) < 0.2
    assert abs(df_prof["established_monsoon_share_pct"].sum() - 100.0) < 0.2
    assert abs(df_prof["post_monsoon_share_pct"].sum() - 100.0) < 0.2


def test_temporal_stability_metrics():
    stab_path = OUTPUT_DIR / "tri_seasonal_temporal_stability.csv"
    assert stab_path.exists()
    df_stab = pd.read_csv(stab_path)
    
    splits = set(df_stab["split"])
    assert "Training (2010-2016)" in splits
    assert "Development (2017-2018)" in splits
    assert "Holdout (2019-2021)" in splits
    
    # Verify pre-monsoon holdout generalization
    pre_holdout = df_stab[(df_stab["season"].str.startswith("Pre-Monsoon")) & (df_stab["split"].str.startswith("Holdout"))].iloc[0]
    assert pre_holdout["nmi"] > 0.14
    assert pre_holdout["ari"] > 0.10
    
    # Verify established-monsoon holdout stability
    est_holdout = df_stab[(df_stab["season"].str.startswith("Established-Monsoon")) & (df_stab["split"].str.startswith("Holdout"))].iloc[0]
    assert est_holdout["nmi"] > 0.03
    
    # Verify post-monsoon holdout stability
    post_holdout = df_stab[(df_stab["season"].str.startswith("Post-Monsoon")) & (df_stab["split"].str.startswith("Holdout"))].iloc[0]
    assert post_holdout["nmi"] > 0.03


def test_manifest_schema_and_integrity():
    man_path = OUTPUT_DIR / "tri_seasonal_manifest.json"
    assert man_path.exists()
    
    with open(man_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    assert manifest["milestone"] == "M25.3"
    assert manifest["milestone_status"] == "M25_3_COMPLETED"
    assert "workstreams" in manifest
    assert "pre_monsoon" in manifest["workstreams"]
    assert "established_monsoon" in manifest["workstreams"]
    assert "post_monsoon" in manifest["workstreams"]
    assert "m25_regimes" in manifest
    assert len(manifest["m25_regimes"]) == 4
    assert "deliverables" in manifest
    assert len(manifest["deliverables"]) >= 8


def test_handoff_zip_archive_validity():
    zip_path = OUTPUT_DIR / "M25.3-integrated-tri-seasonal-synthesis.zip"
    assert zip_path.exists()
    assert zipfile.is_zipfile(zip_path), "Must be a valid ZIP archive"
    
    with zipfile.ZipFile(zip_path, "r") as zf:
        bad_file = zf.testzip()
        assert bad_file is None, f"Corrupted file in ZIP: {bad_file}"
        namelist = zf.namelist()
        assert len(namelist) >= 10, f"Expected at least 10 items in ZIP, got {len(namelist)}"
        assert "tri_seasonal_synthesis_report.md" in namelist
        assert "tri_seasonal_manifest.json" in namelist
        assert "tri_seasonal_correspondence_summary.csv" in namelist


def test_mirroring_to_post_monsoon():
    assert MIRROR_DIR.exists(), f"Mirrored directory must exist: {MIRROR_DIR}"
    
    critical_files = [
        "tri_seasonal_artifact_inventory.csv",
        "tri_seasonal_methodology_comparison.csv",
        "tri_seasonal_correspondence_summary.csv",
        "tri_seasonal_cluster_profiles.csv",
        "tri_seasonal_temporal_stability.csv",
        "tri_seasonal_scientific_audit.md",
        "tri_seasonal_synthesis_report.md",
        "tri_seasonal_manifest.json",
    ]
    for fname in critical_files:
        src = OUTPUT_DIR / fname
        dst = MIRROR_DIR / fname
        assert dst.exists(), f"Mirrored file missing: {fname}"
        assert src.stat().st_size == dst.stat().st_size, f"Size mismatch on mirrored {fname}"
