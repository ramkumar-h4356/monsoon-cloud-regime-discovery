import sys
from pathlib import Path

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = PROJECT_ROOT / "src" / "06_feature_engineering"
sys.path.insert(0, str(MODULE_DIR))

from missingness_classifier import MissingnessCode
from missingness_treatments import (
    assess_ca_b_feature,
    assess_feature_eligibility,
    assess_md_c_feature,
    fit_cloud_area_treatment,
    fit_property_treatment,
    transform_cloud_area_treatment,
    transform_property_treatment,
)


def training_data():
    values = np.array([2.0, 4.0, 100.0, np.nan, np.nan, np.nan])
    area = np.array([1.0, 2.0, np.nan, 0.0, np.nan, 5.0])
    codes = np.array([
        MissingnessCode.OBSERVED,
        MissingnessCode.OBSERVED,
        MissingnessCode.OBSERVED,
        MissingnessCode.STRUCTURAL_ABSENCE,
        MissingnessCode.UNKNOWN_CLOUD_AVAILABILITY,
        MissingnessCode.RESIDUAL_MISSING,
    ], dtype=np.uint8)
    return values, area, codes


def test_property_model_uses_training_only_medians():
    values, area, codes = training_data()
    model = fit_property_treatment(values, area, codes, strategy="MD-A")
    assert model.conditional_median == 3.0
    assert model.overall_median == 4.0


def test_md_a_imputes_structural_residual_and_unknown_values():
    values, area, codes = training_data()
    model = fit_property_treatment(values, area, codes, "MD-A")
    result = transform_property_treatment(values, area, codes, model)

    np.testing.assert_allclose(
        result["feature"],
        np.array([2.0, 4.0, 100.0, 3.0, 4.0, 3.0], dtype=np.float32),
    )
    np.testing.assert_array_equal(
        result["unknown_cloud_availability"], [0, 0, 0, 0, 1, 0]
    )
    assert "residual_missingness" not in result
    assert "structural_absence" not in result


def test_md_b_adds_residual_missingness_indicator():
    values, area, codes = training_data()
    model = fit_property_treatment(values, area, codes, "MD-B")
    result = transform_property_treatment(values, area, codes, model)
    np.testing.assert_array_equal(
        result["residual_missingness"], [0, 0, 0, 0, 0, 1]
    )


def test_sa_b_adds_structural_absence_indicator():
    values, area, codes = training_data()
    model = fit_property_treatment(values, area, codes, "SA-B")
    result = transform_property_treatment(values, area, codes, model)
    np.testing.assert_array_equal(
        result["structural_absence"], [0, 0, 0, 1, 0, 0]
    )


def test_sa_a_has_no_structural_indicator():
    values, area, codes = training_data()
    model = fit_property_treatment(values, area, codes, "SA-A")
    result = transform_property_treatment(values, area, codes, model)
    assert "structural_absence" not in result


def test_transform_does_not_refit_on_new_data():
    train_values, train_area, train_codes = training_data()
    model = fit_property_treatment(
        train_values, train_area, train_codes, "MD-A"
    )
    test_values = np.array([np.nan, 10000.0])
    test_area = np.array([0.0, 1.0])
    test_codes = np.array([
        MissingnessCode.STRUCTURAL_ABSENCE,
        MissingnessCode.OBSERVED,
    ], dtype=np.uint8)

    result = transform_property_treatment(
        test_values, test_area, test_codes, model
    )
    assert result["feature"][0] == 3.0
    assert result["feature"][1] == 10000.0
    assert model.conditional_median == 3.0


@pytest.mark.parametrize(
    "missing_pct, band, decision",
    [
        (0, "LOW", "INCLUDE"),
        (5, "LOW", "INCLUDE"),
        (5.01, "MODERATE", "REVIEW"),
        (20, "MODERATE", "REVIEW"),
        (20.01, "HIGH", "EXCLUDE_PRIMARY"),
        (100, "HIGH", "EXCLUDE_PRIMARY"),
    ],
)
def test_feature_eligibility_bands(missing_pct, band, decision):
    result = assess_feature_eligibility(missing_pct)
    assert result["band"] == band
    assert result["decision"] == decision


def test_md_c_uses_residual_missingness():
    assert assess_md_c_feature(12.0) == {
        "band": "MODERATE",
        "decision": "REVIEW",
    }


def test_ca_b_uses_cloud_area_missingness():
    assert assess_ca_b_feature(20.57) == {
        "band": "HIGH",
        "decision": "EXCLUDE_PRIMARY",
    }


def test_ca_b_is_screening_only_not_imputation():
    with pytest.raises(ValueError, match="screening"):
        fit_cloud_area_treatment(np.array([1.0, np.nan]), strategy="CA-B")


def test_invalid_missingness_percentage_is_rejected():
    with pytest.raises(ValueError):
        assess_feature_eligibility(101)


def test_cloud_area_model_uses_training_median():
    model = fit_cloud_area_treatment(
        np.array([0.0, 2.0, 4.0, np.nan]), "CA-A"
    )
    assert model.median == 2.0
    assert model.training_missing_pct == 25.0


def test_ca_a_imputes_missing_area_and_adds_indicator():
    model = fit_cloud_area_treatment(
        np.array([0.0, 2.0, 4.0, np.nan]), "CA-A"
    )
    result = transform_cloud_area_treatment(
        np.array([np.nan, 5.0, 0.0]), model
    )
    np.testing.assert_allclose(result["feature"], [2.0, 5.0, 0.0])
    np.testing.assert_array_equal(
        result["availability_missing"], [1, 0, 0]
    )


def test_cloud_area_transform_uses_fitted_median():
    model = fit_cloud_area_treatment(
        np.array([2.0, 4.0, np.nan]), "CA-A"
    )
    result = transform_cloud_area_treatment(
        np.array([np.nan, 10000.0]), model
    )
    assert result["feature"][0] == 3.0
    assert result["feature"][1] == 10000.0


def test_negative_cloud_area_is_rejected():
    with pytest.raises(ValueError, match="Negative cloud-area"):
        fit_cloud_area_treatment(np.array([1.0, -1.0]))


def test_property_classification_inconsistency_is_rejected():
    with pytest.raises(ValueError, match="inconsistent"):
        fit_property_treatment(
            np.array([np.nan]),
            np.array([0.0]),
            np.array([MissingnessCode.RESIDUAL_MISSING]),
        )


def test_missing_training_property_values_are_rejected():
    with pytest.raises(ValueError, match="without finite training values"):
        fit_property_treatment(
            np.array([np.nan]),
            np.array([0.0]),
            np.array([MissingnessCode.STRUCTURAL_ABSENCE]),
        )


def test_property_transform_rejects_shape_mismatch():
    values, area, codes = training_data()
    model = fit_property_treatment(values, area, codes)
    with pytest.raises(ValueError, match="identical shapes"):
        transform_property_treatment(values, area[:-1], codes, model)
