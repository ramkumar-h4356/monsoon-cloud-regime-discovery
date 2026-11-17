"""
test_m27_1_climate_index_readiness.py

Automated integration test suite for Milestone M27.1:
NOAA RONI and DMI Climate-Index Audit and Repository Integration Planning.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CANONICAL_REPO_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")

RAW_RONI_PATH = REPO_ROOT / "raw_data" / "NOAA_RONI" / "RONI.ascii.txt"
if not RAW_RONI_PATH.exists():
    RAW_RONI_PATH = CANONICAL_REPO_ROOT / "raw_data" / "NOAA_RONI" / "RONI.ascii.txt"

RAW_DMI_PATH = REPO_ROOT / "raw_data" / "NOAA_DMI" / "dmi.had.long.csv"
if not RAW_DMI_PATH.exists():
    RAW_DMI_PATH = CANONICAL_REPO_ROOT / "raw_data" / "NOAA_DMI" / "dmi.had.long.csv"

INTERIM_RONI_PATH = REPO_ROOT / "data" / "interim" / "climate_indices" / "roni_2010_2021.csv"
INTERIM_DMI_PATH = REPO_ROOT / "data" / "interim" / "climate_indices" / "dmi_2010_2021.csv"

FROZEN_M25_DIR = REPO_ROOT / "data" / "processed" / "combined_3season"
FROZEN_M26_DIR = REPO_ROOT / "data" / "processed" / "rainfall_validation"
M27_REPORT_DIR = REPO_ROOT / "reports" / "integration" / "m27"


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def test_raw_climate_index_files_exist():
    """Verify raw NOAA RONI and DMI files exist and match audited checksums."""
    assert RAW_RONI_PATH.exists(), f"Raw RONI missing: {RAW_RONI_PATH}"
    assert RAW_DMI_PATH.exists(), f"Raw DMI missing: {RAW_DMI_PATH}"
    
    roni_sha = compute_sha256(RAW_RONI_PATH)
    dmi_sha = compute_sha256(RAW_DMI_PATH)
    
    assert roni_sha == "1297887f581b6190e459cbbf8bdec9a703ff65c1a229e2de4dd94285254f35c8"
    assert dmi_sha == "6f5772b234fa6fce4f32830b5731a003c53e83a30220d85bc371cc8e8d8f69d3"


def test_interim_climate_index_files_exist():
    """Verify interim climate index files exist and match audited checksums."""
    assert INTERIM_RONI_PATH.exists(), f"Interim RONI missing: {INTERIM_RONI_PATH}"
    assert INTERIM_DMI_PATH.exists(), f"Interim DMI missing: {INTERIM_DMI_PATH}"
    
    roni_sha = compute_sha256(INTERIM_RONI_PATH)
    dmi_sha = compute_sha256(INTERIM_DMI_PATH)
    
    assert roni_sha == "6600c5f060c41f0ffe2059218439c53948f1af08da2796679da0141072af3d90"
    assert dmi_sha == "ec773e3fe6aefaec9638bfabcf458375306393eaf99418e4eec6552a0ccb5330"


def test_roni_raw_vs_interim_parity():
    """Verify exact parity between raw RONI and interim RONI for 2010-2021."""
    df_raw = pd.read_csv(RAW_RONI_PATH, sep=r"\s+")
    df_raw_study = df_raw[(df_raw["YR"] >= 2010) & (df_raw["YR"] <= 2021)].reset_index(drop=True)
    df_interim = pd.read_csv(INTERIM_RONI_PATH)
    
    assert len(df_raw_study) == 144
    assert len(df_interim) == 144
    assert df_interim["roni_anomaly"].isna().sum() == 0
    assert (df_raw_study["SEAS"].values == df_interim["season"].values).all()
    assert (df_raw_study["YR"].values == df_interim["year"].values).all()
    
    max_diff = np.max(np.abs(df_raw_study["ANOM"].values - df_interim["roni_anomaly"].values))
    assert max_diff < 1e-6, f"RONI numerical mismatch: {max_diff}"


def test_dmi_raw_vs_interim_parity():
    """Verify exact parity between raw DMI and interim DMI for 2010-2021."""
    df_raw = pd.read_csv(RAW_DMI_PATH, skipinitialspace=True)
    df_raw.columns = ["date", "dmi"]
    df_raw["date"] = pd.to_datetime(df_raw["date"])
    df_raw["dmi"] = pd.to_numeric(df_raw["dmi"], errors="coerce")
    df_raw_study = df_raw[(df_raw["date"].dt.year >= 2010) & (df_raw["date"].dt.year <= 2021)].reset_index(drop=True)
    
    df_interim = pd.read_csv(INTERIM_DMI_PATH)
    df_interim["date"] = pd.to_datetime(df_interim["date"])
    
    assert len(df_raw_study) == 144
    assert len(df_interim) == 144
    assert df_interim["dmi_anomaly"].isna().sum() == 0
    assert (df_raw_study["date"].values == df_interim["date"].values).all()
    
    max_diff = np.max(np.abs(df_raw_study["dmi"].values - df_interim["dmi_anomaly"].values))
    assert max_diff < 1e-6, f"DMI numerical mismatch: {max_diff}"


def test_roni_season_cycle_completeness():
    """Verify complete 12 running 3-month seasons per year in RONI."""
    df = pd.read_csv(INTERIM_RONI_PATH)
    expected_seasons = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    
    for yr in range(2010, 2022):
        yr_seasons = df[df["year"] == yr]["season"].tolist()
        assert yr_seasons == expected_seasons, f"Season cycle corrupted in {yr}: {yr_seasons}"


def test_dmi_month_cycle_completeness():
    """Verify complete 12 calendar months per year in DMI."""
    df = pd.read_csv(INTERIM_DMI_PATH)
    df["date"] = pd.to_datetime(df["date"])
    
    for yr in range(2010, 2022):
        yr_months = df[df["date"].dt.year == yr]["date"].dt.month.tolist()
        assert yr_months == list(range(1, 13)), f"Month cycle corrupted in {yr}: {yr_months}"


def test_temporal_alignment_continuity():
    """Verify that all 12 study years have valid aligned DMI and RONI index values."""
    df_roni = pd.read_csv(INTERIM_RONI_PATH)
    df_dmi = pd.read_csv(INTERIM_DMI_PATH)
    df_dmi["date"] = pd.to_datetime(df_dmi["date"])
    
    for yr in range(2010, 2022):
        # Pre-monsoon: MAM & (Apr+May)/2
        mam = df_roni[(df_roni["year"] == yr) & (df_roni["season"] == "MAM")]["roni_anomaly"].iloc[0]
        apr_d = df_dmi[(df_dmi["date"] == f"{yr}-04-01")]["dmi_anomaly"].iloc[0]
        may_d = df_dmi[(df_dmi["date"] == f"{yr}-05-01")]["dmi_anomaly"].iloc[0]
        assert np.isfinite(mam) and np.isfinite(apr_d) and np.isfinite(may_d)
        
        # Established monsoon: JJA & (Jul+Aug)/2
        jja = df_roni[(df_roni["year"] == yr) & (df_roni["season"] == "JJA")]["roni_anomaly"].iloc[0]
        jul_d = df_dmi[(df_dmi["date"] == f"{yr}-07-01")]["dmi_anomaly"].iloc[0]
        aug_d = df_dmi[(df_dmi["date"] == f"{yr}-08-01")]["dmi_anomaly"].iloc[0]
        assert np.isfinite(jja) and np.isfinite(jul_d) and np.isfinite(aug_d)
        
        # Post-monsoon: SON & (Oct+Nov)/2
        son = df_roni[(df_roni["year"] == yr) & (df_roni["season"] == "SON")]["roni_anomaly"].iloc[0]
        oct_d = df_dmi[(df_dmi["date"] == f"{yr}-10-01")]["dmi_anomaly"].iloc[0]
        nov_d = df_dmi[(df_dmi["date"] == f"{yr}-11-01")]["dmi_anomaly"].iloc[0]
        assert np.isfinite(son) and np.isfinite(oct_d) and np.isfinite(nov_d)


def test_frozen_m25_artifacts_unmodified():
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


def test_frozen_m26_artifacts_unmodified():
    """Assert frozen M26 rainfall validation artifacts are intact and unmodified."""
    assert FROZEN_M26_DIR.exists()
    p_primary = FROZEN_M26_DIR / "m26_cloud_rainfall_matched_primary.parquet"
    assert p_primary.exists(), "Primary M26 parquet missing"
    assert p_primary.stat().st_size > 2_000_000, "Primary M26 parquet size corrupted"
    
    df = pd.read_parquet(p_primary)
    assert len(df) == 342432, f"Expected 342,432 rows, got {len(df)}"


def test_m27_1_deliverables_existence():
    """Verify existence and non-zero size of all M27.1 reports."""
    expected_reports = [
        "m27_1_dataset_inventory_and_provenance_report.md",
        "m27_1_roni_quality_control_report.md",
        "m27_1_dmi_quality_control_report.md",
        "m27_1_temporal_alignment_comparison.md",
        "m27_1_scientific_methodology_proposal.md",
        "m27_1_statistical_analysis_design.md",
        "m27_1_risks_and_unresolved_questions.md",
        "m27_1_proposed_directory_structure.md",
    ]
    for r in expected_reports:
        p = M27_REPORT_DIR / r
        assert p.exists(), f"Missing M27.1 deliverable: {r}"
        assert p.stat().st_size > 1_000, f"M27.1 deliverable too small: {r}"
