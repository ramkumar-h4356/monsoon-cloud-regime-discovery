
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = PROJECT_ROOT / "src" / "06_feature_engineering"

sys.path.insert(0, str(MODULE_DIR))

from missingness_classifier import (
    MissingnessCode,
    classify_missingness,
    classify_registered_variable,
    get_matching_area_variable,
    load_feature_registry,
    summarize_classifications,
)


def test_property_missingness_classification():
    values = np.array([10.0, np.nan, np.nan, np.nan])
    area = np.array([np.nan, 0.0, 5.0, np.nan])

    result = classify_missingness(
        values=values,
        variable="cldhght_high_1h",
        area_values=area,
        area_variable="cldarea_high_1h",
    )

    expected = np.array([
        MissingnessCode.OBSERVED,
        MissingnessCode.STRUCTURAL_ABSENCE,
        MissingnessCode.RESIDUAL_MISSING,
        MissingnessCode.UNKNOWN_CLOUD_AVAILABILITY,
    ], dtype=np.uint8)

    np.testing.assert_array_equal(result, expected)


def test_cloud_area_missingness_classification():
    values = np.array([0.0, np.nan, 5.0])

    result = classify_missingness(
        values=values,
        variable="cldarea_low_1h",
    )

    expected = np.array([
        MissingnessCode.OBSERVED,
        MissingnessCode.CLOUD_AREA_MISSING,
        MissingnessCode.OBSERVED,
    ], dtype=np.uint8)

    np.testing.assert_array_equal(result, expected)


def test_finite_property_remains_observed_when_area_is_missing():
    values = np.array([2.5, 3.5])
    area = np.array([np.nan, 0.0])

    result = classify_missingness(
        values=values,
        variable="lwp_total_1h",
        area_values=area,
        area_variable="cldarea_total_1h",
    )

    assert np.all(result == MissingnessCode.OBSERVED)


def test_negative_cloud_area_is_rejected():
    values = np.array([np.nan])
    area = np.array([-1.0])

    with pytest.raises(ValueError, match="Negative cloud-area"):
        classify_missingness(
            values=values,
            variable="cldhght_high_1h",
            area_values=area,
            area_variable="cldarea_high_1h",
        )


def test_array_shape_mismatch_is_rejected():
    with pytest.raises(ValueError, match="identical shapes"):
        classify_missingness(
            values=np.array([1.0, np.nan]),
            variable="cldhght_high_1h",
            area_values=np.array([1.0]),
            area_variable="cldarea_high_1h",
        )


def test_missing_area_array_is_rejected():
    with pytest.raises(ValueError, match="required"):
        classify_missingness(
            values=np.array([np.nan]),
            variable="cldhght_high_1h",
        )


def test_invalid_area_variable_is_rejected():
    with pytest.raises(ValueError, match="Invalid cloud-area"):
        classify_missingness(
            values=np.array([np.nan]),
            variable="cldhght_high_1h",
            area_values=np.array([0.0]),
            area_variable="unknown_area",
        )


def test_registry_contains_expected_cloud_top_mappings():
    registry = load_feature_registry()

    expected = {
        "cldpress_top_high_1h": "cldarea_high_1h",
        "cldpress_top_mid_high_1h": "cldarea_mid_high_1h",
        "cldpress_top_mid_low_1h": "cldarea_mid_low_1h",
        "cldpress_top_low_1h": "cldarea_low_1h",
        "cldpress_top_total_1h": "cldarea_total_1h",
    }

    for variable, area_variable in expected.items():
        assert get_matching_area_variable(
            variable,
            registry,
        ) == area_variable


def test_registered_variable_classification():
    registry = load_feature_registry()

    result = classify_registered_variable(
        values=np.array([np.nan, np.nan]),
        variable="cldpress_top_high_1h",
        area_values=np.array([0.0, 10.0]),
        registry=registry,
    )

    expected = np.array([
        MissingnessCode.STRUCTURAL_ABSENCE,
        MissingnessCode.RESIDUAL_MISSING,
    ], dtype=np.uint8)

    np.testing.assert_array_equal(result, expected)


def test_classification_summary():
    values = np.array([
        MissingnessCode.OBSERVED,
        MissingnessCode.OBSERVED,
        MissingnessCode.STRUCTURAL_ABSENCE,
        MissingnessCode.RESIDUAL_MISSING,
    ], dtype=np.uint8)

    summary = summarize_classifications(values)

    assert summary["total_values"] == 4
    assert summary["observed"] == 2
    assert summary["structural_absence"] == 1
    assert summary["residual_missing"] == 1

