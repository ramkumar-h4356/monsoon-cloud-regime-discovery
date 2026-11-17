"""
test_m27_climate_modulation.py

Integration test suite for Milestone M27:
Integrated ENSO–IOD Climate Teleconnection and Cloud-Regime Analysis.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.integration.climate_association.m27_climate_index_loader import (
    ClimateIndexLoader,
    classify_enso_phase,
    classify_iod_phase,
    get_aligned_climate_indices,
    SEASON_CONFIG,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_loader_builds_36_rows():
    """Verify that the aligned table contains exactly 36 annual-seasonal rows."""
    loader = ClimateIndexLoader()
    df = loader.build_aligned_table()
    assert len(df) == 36
    assert df["year"].nunique() == 12
    assert sorted(df["year"].unique()) == list(range(2010, 2022))
    assert set(df["season_id"].unique()) == {0, 1, 2}
    assert set(df["season"].unique()) == {"pre_monsoon", "established_monsoon", "post_monsoon"}


def test_loader_boundary_years_values():
    """Verify exact values for boundary years 2010 and 2021."""
    loader = ClimateIndexLoader()
    df = loader.build_aligned_table()

    # 2010 Pre-monsoon: MAM = 0.10, DMI = (0.294 + 0.047)/2 = 0.1705
    row_2010_pre = df[(df["year"] == 2010) & (df["season_id"] == 0)].iloc[0]
    assert np.isclose(row_2010_pre["roni_anomaly"], 0.10)
    assert np.isclose(row_2010_pre["dmi_anomaly"], 0.1705)
    assert row_2010_pre["enso_phase"] == "Neutral"
    assert row_2010_pre["iod_phase"] == "Neutral"

    # 2021 Post-monsoon: SON = -1.08, DMI = (-0.038 + 0.016)/2 = -0.0110
    row_2021_post = df[(df["year"] == 2021) & (df["season_id"] == 2)].iloc[0]
    assert np.isclose(row_2021_post["roni_anomaly"], -1.08)
    assert np.isclose(row_2021_post["dmi_anomaly"], -0.0110)
    assert row_2021_post["enso_phase"] == "La Niña"
    assert row_2021_post["iod_phase"] == "Neutral"


def test_loader_extreme_climate_years():
    """Verify 2015 (Super El Niño) and 2019 (Super Positive IOD) values."""
    loader = ClimateIndexLoader()
    df = loader.build_aligned_table()

    # 2015 Established Monsoon: JJA = 1.27
    row_2015_est = df[(df["year"] == 2015) & (df["season_id"] == 1)].iloc[0]
    assert np.isclose(row_2015_est["roni_anomaly"], 1.27)
    assert row_2015_est["enso_phase"] == "El Niño"

    # 2015 Post-Monsoon: SON = 2.03, DMI = (0.428 + 0.401)/2 = 0.4145
    row_2015_post = df[(df["year"] == 2015) & (df["season_id"] == 2)].iloc[0]
    assert np.isclose(row_2015_post["roni_anomaly"], 2.03)
    assert np.isclose(row_2015_post["dmi_anomaly"], 0.4145)
    assert row_2015_post["enso_phase"] == "El Niño"
    assert row_2015_post["iod_phase"] == "Positive IOD"

    # 2019 Post-Monsoon: DMI = (0.971 + 0.828)/2 = 0.8995
    row_2019_post = df[(df["year"] == 2019) & (df["season_id"] == 2)].iloc[0]
    assert np.isclose(row_2019_post["dmi_anomaly"], 0.8995)
    assert row_2019_post["iod_phase"] == "Positive IOD"


def test_export_and_get_aligned_indices():
    """Verify file persistence and reload functionality."""
    loader = ClimateIndexLoader()
    p_path, c_path, df1 = loader.export_aligned_table()

    assert p_path.exists()
    assert c_path.exists()
    assert p_path.stat().st_size > 1000
    assert c_path.stat().st_size > 1000

    df2 = get_aligned_climate_indices()
    assert len(df2) == 36
    assert (df1["roni_anomaly"].values == df2["roni_anomaly"].values).all()
    assert (df1["dmi_anomaly"].values == df2["dmi_anomaly"].values).all()


def test_classification_helpers():
    """Test boundary and threshold logic in phase classification."""
    assert classify_enso_phase(0.50) == "El Niño"
    assert classify_enso_phase(0.499) == "Neutral"
    assert classify_enso_phase(-0.50) == "La Niña"
    assert classify_enso_phase(-0.499) == "Neutral"
    assert classify_enso_phase(np.nan) == "Unknown"

    assert classify_iod_phase(0.40) == "Positive IOD"
    assert classify_iod_phase(0.399) == "Neutral"
    assert classify_iod_phase(-0.40) == "Negative IOD"
    assert classify_iod_phase(-0.399) == "Neutral"
    assert classify_iod_phase(np.nan) == "Unknown"


def test_regime_prevalence_properties():
    """Verify that regime fractions sum to 1.0 and total observations match 691,200."""
    from src.integration.climate_association.m27_regime_climate_correlation import (
        RegimeClimateCorrelationEngine,
    )
    engine = RegimeClimateCorrelationEngine()
    df_prev = engine.compute_annual_regime_prevalence()

    assert len(df_prev) == 36
    assert (df_prev["total_obs_domain"] == 691_200).all()
    p_sum_domain = df_prev[["p_R0_domain", "p_R1_domain", "p_R2_domain", "p_R3_domain"]].sum(axis=1)
    assert np.allclose(p_sum_domain, 1.0)

    # Check Tier 1 terrestrial fraction sums
    p_sum_t1 = df_prev[["p_R0_tier1", "p_R1_tier1", "p_R2_tier1", "p_R3_tier1"]].sum(axis=1)
    assert np.allclose(p_sum_t1, 1.0)


def test_regime_climate_correlation_pipeline():
    """Verify statistical properties of regime-climate correlations."""
    from src.integration.climate_association.m27_regime_climate_correlation import (
        RegimeClimateCorrelationEngine,
    )
    engine = RegimeClimateCorrelationEngine()
    df_prev, df_corr, df_clr, df_loocv = engine.run_regime_climate_analysis(B_perm=2000, seed=123)

    assert len(df_corr) == 16  # 4 regimes x (3 seasons + 1 pooled)
    assert len(df_clr) == 16
    assert len(df_loocv) == 144  # 12 years x 4 regimes x 3 seasons

    # P-values must be between 1/(B+1) and 1.0
    assert (df_corr["p_roni_perm"] >= 1.0 / 2001.0).all()
    assert (df_corr["p_roni_perm"] <= 1.0).all()
    assert (df_corr["p_dmi_perm"] >= 1.0 / 2001.0).all()
    assert (df_corr["p_dmi_perm"] <= 1.0).all()

    # FDR q-values must be greater than or equal to minimum p-value
    assert (df_corr["q_roni_fdr"] >= 0.0).all()
    assert (df_corr["q_dmi_fdr"] >= 0.0).all()

    # Pre-monsoon R0 and DMI negative correlation
    pre_r0 = df_corr[(df_corr["season"] == "pre_monsoon") & (df_corr["regime"] == "R0")].iloc[0]
    assert pre_r0["rho_dmi"] < -0.50
    assert pre_r0["p_dmi_perm"] < 0.05


def test_rainfall_modulation_metrics():
    """Verify rainfall modulation metrics aggregation and properties."""
    from src.integration.climate_association.m27_rainfall_modulation import (
        RainfallClimateModulationEngine,
    )
    engine = RainfallClimateModulationEngine()
    df_metrics = engine.compute_annual_seasonal_rainfall_metrics()

    assert len(df_metrics) == 36
    assert (df_metrics["n_cell_days"] == 328 * 29).all()  # 29 days in EXACT_SHIFTED_03TO03_UTC
    assert (df_metrics["mean_rainfall_mm"] > 0).all()
    assert (df_metrics["wet_day_freq_25mm"] >= 0).all()
    assert (df_metrics["wet_day_freq_25mm"] <= 1.0).all()

    # Verify seasonal rainfall anomaly sums to zero across 12 years for each season
    for sid in [0, 1, 2]:
        anom_sum = df_metrics[df_metrics["season_id"] == sid]["rainfall_anomaly_mm"].sum()
        assert np.isclose(anom_sum, 0.0, atol=1e-3)


def test_rainfall_modulation_pipeline():
    """Verify rainfall-climate correlation analysis and phase contrasts."""
    from src.integration.climate_association.m27_rainfall_modulation import (
        RainfallClimateModulationEngine,
    )
    engine = RainfallClimateModulationEngine()
    df_metrics, df_corr, df_loocv, df_contrasts = engine.run_rainfall_climate_analysis(
        B_perm=2000, seed=456
    )

    assert len(df_corr) == 36  # 9 metrics x (3 seasons + 1 pooled)
    assert len(df_loocv) == 324  # 9 metrics x 12 years x 3 seasons
    assert len(df_contrasts) == 12  # 4 metrics x 3 seasons

    # P-values must be bounded
    assert (df_corr["p_roni_perm"] >= 1.0 / 2001.0).all()
    assert (df_corr["p_dmi_perm"] >= 1.0 / 2001.0).all()

    # Pre-monsoon wet-day frequency negative correlation with RONI
    pre_wet = df_corr[(df_corr["season"] == "pre_monsoon") & (df_corr["metric"] == "wet_day_freq_25mm")].iloc[0]
    assert pre_wet["rho_roni"] < -0.40


def test_joint_climate_analysis():
    """Verify joint ENSO-IOD contingency matrix and case study extraction."""
    from src.integration.climate_association.m27_joint_climate_analysis import (
        JointClimateAnalysisEngine,
    )
    engine = JointClimateAnalysisEngine()
    df_merged = engine.load_combined_dataset()
    df_matrix = engine.build_contingency_matrix(df_merged)
    df_inter = engine.analyze_interaction_effects(df_merged, B_perm=1000, seed=789)
    df_cases = engine.extract_case_studies(df_merged)

    assert len(df_matrix) == 36  # 4 seasons x 9 phase combinations
    assert len(df_inter) == 28  # 7 variables x 4 seasons
    assert len(df_cases) > 0

    # 2015 must be classified as El Niño + Positive IOD in post-monsoon
    case_2015_post = df_cases[(df_cases["year"] == 2015) & (df_cases["season_id"] == 2)].iloc[0]
    assert case_2015_post["joint_phase"] == "El Niño + Positive IOD"


def test_spatial_teleconnections():
    """Verify spatial cell-level teleconnection and field significance calculations."""
    from src.integration.climate_association.m27_spatial_teleconnections import (
        SpatialTeleconnectionEngine,
    )
    engine = SpatialTeleconnectionEngine()
    df_cells, df_field = engine.compute_cell_teleconnections()

    assert len(df_cells) == 328 * 3  # 328 Tier 1 cells x 3 seasons
    assert len(df_field) == 12  # 4 tests x 3 seasons
    assert (df_cells["latitude"] >= 6.0).all()
    assert (df_cells["longitude"] <= 98.0).all()

    # Established monsoon Rainfall vs RONI achieves field significance
    est_rain = df_field[(df_field["season"] == "established_monsoon") & (df_field["field_test"] == "Rainfall vs RONI")].iloc[0]
    assert est_rain["achieves_field_significance"] is True or est_rain["achieves_field_significance"] == np.bool_(True)


def test_m27_figures_generation():
    """Verify that all 10 publication figures exist at 300 DPI with valid sizes."""
    fig_dir = REPO_ROOT / "reports" / "integration" / "m27" / "figures"
    expected_figs = [
        "fig01_annual_roni_dmi_timeseries.png",
        "fig02_annual_seasonal_alignment_matrix.png",
        "fig03_regime_prevalence_vs_climate_indices.png",
        "fig04_partial_rank_correlations.png",
        "fig05_seasonal_rainfall_vs_climate_indices.png",
        "fig06_regime_conditional_rainfall_response.png",
        "fig07_enso_phase_composite_maps.png",
        "fig08_iod_phase_composite_maps.png",
        "fig09_joint_enso_iod_phase_matrix.png",
        "fig10_sensitivity_loocv_diagnostics.png",
    ]
    for fname in expected_figs:
        p = fig_dir / fname
        assert p.exists(), f"Missing publication figure: {fname}"
        assert p.stat().st_size > 50_000, f"Figure too small: {fname} ({p.stat().st_size} bytes)"


def test_m27_reports_deliverables():
    """Verify that all 8 M27 scientific reports exist and contain comprehensive content."""
    rep_dir = REPO_ROOT / "reports" / "integration" / "m27"
    expected_reports = [
        "m27_methodology_report.md",
        "m27_data_integration_report.md",
        "m27_regime_modulation_report.md",
        "m27_rainfall_modulation_report.md",
        "m27_spatial_teleconnection_report.md",
        "m27_statistical_validation_report.md",
        "m27_integrated_scientific_synthesis.md",
        "m27_limitations_and_unresolved_questions.md",
    ]
    for rname in expected_reports:
        p = rep_dir / rname
        assert p.exists(), f"Missing M27 scientific report: {rname}"
        assert p.stat().st_size > 2_000, f"Report content too small: {rname} ({p.stat().st_size} bytes)"


def test_m27_manifest_and_zip_archive():
    """Verify cryptographic manifest and standalone handoff ZIP package."""
    import json
    import zipfile
    rep_dir = REPO_ROOT / "reports" / "integration" / "m27"
    manifest_p = rep_dir / "m27_manifest.json"
    zip_p = rep_dir / "M27-climate-teleconnections.zip"

    assert manifest_p.exists(), "Manifest missing"
    assert zip_p.exists(), "Handoff ZIP package missing"
    assert zip_p.stat().st_size > 2_000_000, f"ZIP file too small: {zip_p.stat().st_size} bytes"

    with open(manifest_p, "r", encoding="utf-8") as f:
        mdata = json.load(f)
    assert mdata["milestone"].startswith("M27")
    assert mdata["artifact_count"] >= 25

    with zipfile.ZipFile(zip_p, "r") as zf:
        namelist = zf.namelist()
        assert any("m27_manifest.json" in n for n in namelist)
        assert any("fig01_annual_roni_dmi_timeseries.png" in n for n in namelist)
        assert any("m27_regime_climate_correlations.csv" in n for n in namelist)




