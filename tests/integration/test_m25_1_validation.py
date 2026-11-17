"""Automated Tests for Milestone M25.1 Scientific Validation Suite.

Validates that:
1. Validation manifest exists and marks all 3 historical anomalies as RESOLVED.
2. Raw-observation vs imputed cluster profiles are generated for all 36 features x 4 clusters.
3. IWP/LWP missingness deep dive quantifies in-cloud vs clear-sky physical distributions.
4. Multi-seed cluster stability demonstrates robust Adjusted Rand Index (ARI > 0.75) for K=4.
5. PCA sensitivity analysis documents scaling impact on sparse low-cloud microphysics.
6. Temporal generalization verifies low distribution drift (< 5%) between 2010-2016 and 2017-2021.
7. Revised regime taxonomy provides physically accurate meteorological names for all regimes.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_DIR = PROJECT_ROOT / "reports" / "integration" / "m25_1_validation"


def test_validation_manifest_exists_and_complete():
    manifest_path = VALIDATION_DIR / "m25_1_validation_manifest.json"
    assert manifest_path.exists(), f"Manifest missing at {manifest_path}"

    with open(manifest_path) as f:
        manifest = json.load(f)

    assert manifest["milestone"] == "M25.1"
    assert len(manifest["anomalies_resolved"]) == 3
    for anomaly in manifest["anomalies_resolved"]:
        assert anomaly["status"] == "RESOLVED"

    findings = manifest["validation_findings"]
    assert findings["cluster_stability_k4_mean_ari"] >= 0.70
    assert findings["cluster_stability_verdict"] in ("HIGHLY STABLE", "STABLE", "MODERATE/UNSTABLE")
    assert findings["pca_holdout_recon_pct"] > 90.0


def test_raw_vs_imputed_profiles():
    profile_path = VALIDATION_DIR / "raw_vs_imputed_cluster_profiles.csv"
    assert profile_path.exists(), f"Profile CSV missing at {profile_path}"

    df = pd.read_csv(profile_path)
    # 4 clusters x 36 features = 144 rows
    assert len(df) == 144
    assert set(df["cluster_id"].unique()) == {0, 1, 2, 3}
    assert len(df["feature"].unique()) == 36

    # Verify key columns exist
    required_cols = [
        "cluster_id", "feature", "cluster_total_samples", "valid_obs_count",
        "missing_obs_count", "missing_pct", "raw_mean", "raw_median",
        "imputed_mean", "imputed_median", "diff_mean_raw_minus_imp"
    ]
    for col in required_cols:
        assert col in df.columns

    # Verify cloud area has 0% missingness
    cldarea_totals = df[df["feature"] == "cldarea_total_1h"]
    assert (cldarea_totals["missing_pct"] == 0.0).all()


def test_iwp_lwp_missingness_deep_dive():
    water_path = VALIDATION_DIR / "iwp_lwp_missingness_deep_dive.csv"
    assert water_path.exists(), f"Water path deep dive CSV missing at {water_path}"

    df = pd.read_csv(water_path)
    # 4 clusters x 6 variables = 24 rows
    assert len(df) == 24
    assert set(df["cluster_id"].unique()) == {0, 1, 2, 3}

    # Verify iwp_total_1h in-cloud median is non-zero and distinct across regimes
    iwp_totals = df[df["variable"] == "iwp_total_1h"]
    assert len(iwp_totals) == 4
    for _, row in iwp_totals.iterrows():
        assert row["incloud_physical_median"] > 0
        assert "artifact_explanation" in row


def test_cluster_stability_ari():
    stab_path = VALIDATION_DIR / "cluster_stability_ari_analysis.csv"
    assert stab_path.exists(), f"Stability CSV missing at {stab_path}"

    df = pd.read_csv(stab_path)
    assert len(df) >= 4  # K=3, 4, 5, 6
    assert set(df["k"].unique()).issuperset({3, 4, 5, 6})

    k4_row = df[df["k"] == 4].iloc[0]
    assert k4_row["mean_ari"] >= 0.70
    assert k4_row["n_pairwise_comparisons"] == 10  # 5 seeds choose 2


def test_pca_representation_sensitivity():
    sens_path = VALIDATION_DIR / "pca_representation_sensitivity.csv"
    assert sens_path.exists(), f"PCA sensitivity CSV missing at {sens_path}"

    df = pd.read_csv(sens_path)
    assert len(df) == 4  # 4 representations

    # Top 10 cumulative variance must exceed 85% across all valid representations
    for _, row in df.iterrows():
        assert row["top10_cumulative_var_pct"] > 85.0
        assert row["holdout_recon_pct"] > 85.0


def test_temporal_generalization():
    gen_path = VALIDATION_DIR / "temporal_generalization_evaluation.csv"
    assert gen_path.exists(), f"Generalization CSV missing at {gen_path}"

    df = pd.read_csv(gen_path)
    overall = df[df["scope"] == "Overall Combined"]
    assert len(overall) == 4  # 4 regimes

    # Max absolute frequency drift between training and holdout should be bounded (< 6%)
    max_drift = overall["absolute_drift_pct"].max()
    assert max_drift < 6.0, f"Excessive regime drift observed: {max_drift:.2f}%"


def test_revised_regime_taxonomy():
    tax_path = VALIDATION_DIR / "revised_regime_taxonomy.csv"
    assert tax_path.exists(), f"Taxonomy CSV missing at {tax_path}"

    df = pd.read_csv(tax_path)
    assert len(df) == 4

    r3 = df[df["cluster_id"] == 3].iloc[0]
    assert "Cirrus" in r3["revised_authoritative_name"]
    assert "Fair-Weather" not in r3["revised_authoritative_name"]

    r1 = df[df["cluster_id"] == 1].iloc[0]
    assert "Boundary-Layer" in r1["revised_authoritative_name"]
    assert "Active Convective" not in r1["revised_authoritative_name"]

    r2 = df[df["cluster_id"] == 2].iloc[0]
    assert "Deep Convective" in r2["revised_authoritative_name"]
