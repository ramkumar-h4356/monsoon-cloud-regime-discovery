"""Tests for the cross-season integration layer."""

from pathlib import Path
import pytest
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(PROJECT_ROOT / "src" / "integration" / "seasonal_comparison"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "integration" / "climate_association"))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "integration" / "synthesis"))

from compare_seasonal_profiles import summarize_seasonal_coverage, SEASONS, STUDY_YEARS
from reconcile_climate_indices import load_dmi_data, load_roni_data
from cross_season_synthesis import synthesize_research_status


def test_seasonal_dataset_coverage():
    coverage = summarize_seasonal_coverage()
    assert len(coverage) == 3
    for season in SEASONS:
        assert coverage[season]["found_files"] == 12
        assert coverage[season]["status"] == "COMPLETE"
        assert sorted(coverage[season]["years"]) == list(STUDY_YEARS)


def test_climate_index_reconciliation_sources():
    dmi = load_dmi_data()
    roni = load_roni_data()
    assert not dmi.empty
    assert not roni.empty
    assert "year" in dmi.columns
    assert "year" in roni.columns


def test_cross_season_synthesis_summary():
    result = synthesize_research_status()
    assert result["datasets"]["total_seasonal_netcdf"] == 36
    assert result["feature_registry"]["registered_variables"] == 36
    assert "READY FOR DOWNSTREAM ANALYSIS" in result["seasonal_milestones"]["post_monsoon"]
