import json
import sys
from pathlib import Path

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = PROJECT_ROOT / "src" / "06_feature_engineering"
sys.path.insert(0, str(MODULE_DIR))

from feature_scaling import (
    build_scaling_manifest,
    fit_feature_scaler,
    save_scaling_manifest,
    transform_feature_scaler,
)


def test_robust_scaler_fits_median_and_iqr_on_training_data():
    train = np.array([
        [1.0, 10.0],
        [2.0, 20.0],
        [3.0, 30.0],
        [100.0, 40.0],
    ])

    model = fit_feature_scaler(train, ["a", "b"], scaler="robust")

    np.testing.assert_allclose(model.center, [2.5, 25.0])
    np.testing.assert_allclose(model.scale, [25.5, 15.0])
    assert model.n_training_samples == 4


def test_standard_scaler_fits_training_mean_and_population_std():
    train = np.array([
        [1.0, 10.0],
        [3.0, 30.0],
        [5.0, 50.0],
    ])

    model = fit_feature_scaler(
        train,
        ["a", "b"],
        scaler="standard",
    )

    np.testing.assert_allclose(model.center, [3.0, 30.0])
    np.testing.assert_allclose(model.scale, [np.sqrt(8 / 3), np.sqrt(800 / 3)])


def test_validation_transform_does_not_refit_training_parameters():
    train = np.array([[1.0], [2.0], [3.0]])
    model = fit_feature_scaler(train, ["cloud_area"], scaler="standard")
    original_center = model.center.copy()
    original_scale = model.scale.copy()

    validation = np.array([[1000.0], [2000.0]])
    transformed = transform_feature_scaler(
        validation,
        model,
        ["cloud_area"],
    )

    np.testing.assert_array_equal(model.center, original_center)
    np.testing.assert_array_equal(model.scale, original_scale)
    assert transformed.dtype == np.float32
    assert transformed[0, 0] > 100


def test_robust_scaler_is_default():
    train = np.array([[1.0], [2.0], [3.0]])
    model = fit_feature_scaler(train, ["x"])
    assert model.scaler_type == "robust"


def test_equal_weighting_keeps_unit_feature_weights():
    train = np.arange(30, dtype=float).reshape(10, 3)
    model = fit_feature_scaler(
        train,
        ["a", "b", "c"],
        feature_families=["amount", "amount", "water"],
        weighting="equal",
    )

    np.testing.assert_array_equal(model.feature_weights, [1.0, 1.0, 1.0])


def test_family_balanced_weights_normalize_squared_family_contribution():
    train = np.array([
        [1.0, 10.0, 100.0],
        [2.0, 20.0, 200.0],
        [3.0, 30.0, 300.0],
        [4.0, 40.0, 400.0],
    ])

    model = fit_feature_scaler(
        train,
        ["a1", "a2", "b1"],
        feature_families=["family_a", "family_a", "family_b"],
        weighting="family_balanced",
    )

    np.testing.assert_allclose(
        model.feature_weights,
        [1 / np.sqrt(2), 1 / np.sqrt(2), 1.0],
    )
    assert np.isclose(np.sum(model.feature_weights[:2] ** 2), 1.0)
    assert np.isclose(np.sum(model.feature_weights[2:] ** 2), 1.0)


def test_binary_indicator_columns_can_remain_unscaled():
    train = np.array([
        [1.0, 0.0],
        [2.0, 1.0],
        [3.0, 0.0],
        [4.0, 1.0],
    ])

    model = fit_feature_scaler(
        train,
        ["cloud_property", "residual_missing_indicator"],
        feature_families=["water_path", None],
        weighting="family_balanced",
        scale_mask=[True, False],
    )

    output = transform_feature_scaler(
        np.array([[2.5, 0.0], [3.5, 1.0]]),
        model,
        ["cloud_property", "residual_missing_indicator"],
    )

    np.testing.assert_array_equal(output[:, 1], [0.0, 1.0])
    assert model.feature_weights[1] == 1.0
    assert model.center[1] == 0.0
    assert model.scale[1] == 1.0


def test_constant_feature_uses_safe_unit_scale():
    train = np.array([[5.0, 1.0], [5.0, 2.0], [5.0, 3.0]])
    model = fit_feature_scaler(train, ["constant", "varying"])

    assert model.scale[0] == 1.0
    output = transform_feature_scaler(train, model, ["constant", "varying"])
    np.testing.assert_array_equal(output[:, 0], [0.0, 0.0, 0.0])


def test_transform_rejects_feature_order_mismatch():
    train = np.array([[1.0, 10.0], [2.0, 20.0]])
    model = fit_feature_scaler(train, ["a", "b"])

    with pytest.raises(ValueError, match="names/order"):
        transform_feature_scaler(train, model, ["b", "a"])


def test_transform_rejects_wrong_number_of_columns():
    model = fit_feature_scaler(np.array([[1.0, 2.0]]), ["a", "b"])

    with pytest.raises(ValueError, match="2D"):
        transform_feature_scaler(np.array([1.0, 2.0]), model, ["a", "b"])


def test_fit_rejects_nan_before_scaling():
    with pytest.raises(ValueError, match="NaN or infinite"):
        fit_feature_scaler(np.array([[1.0], [np.nan]]), ["x"])


def test_fit_rejects_infinity_before_scaling():
    with pytest.raises(ValueError, match="NaN or infinite"):
        fit_feature_scaler(np.array([[1.0], [np.inf]]), ["x"])


def test_fit_rejects_duplicate_feature_names():
    with pytest.raises(ValueError, match="unique"):
        fit_feature_scaler(np.ones((3, 2)), ["x", "x"])


def test_fit_rejects_empty_matrix():
    with pytest.raises(ValueError, match="at least one sample"):
        fit_feature_scaler(np.empty((0, 2)), ["a", "b"])


def test_fit_rejects_invalid_scaler_type():
    with pytest.raises(ValueError, match="Unsupported scaler"):
        fit_feature_scaler(np.ones((3, 1)), ["x"], scaler="minmax")


def test_fit_rejects_invalid_weighting_type():
    with pytest.raises(ValueError, match="Unsupported weighting"):
        fit_feature_scaler(np.ones((3, 1)), ["x"], weighting="custom")


def test_family_balanced_requires_family_for_each_scaled_feature():
    with pytest.raises(ValueError, match="requires a non-empty family"):
        fit_feature_scaler(
            np.ones((3, 2)),
            ["a", "b"],
            feature_families=["family_a", None],
            weighting="family_balanced",
        )


def test_family_balanced_accepts_missing_family_for_unscaled_indicator():
    train = np.array([[1.0, 0.0], [2.0, 1.0], [3.0, 0.0]])
    model = fit_feature_scaler(
        train,
        ["a", "indicator"],
        feature_families=["family_a", None],
        weighting="family_balanced",
        scale_mask=[True, False],
    )
    np.testing.assert_array_equal(model.feature_weights, [1.0, 1.0])


def test_transform_rejects_non_finite_validation_data():
    model = fit_feature_scaler(np.array([[1.0], [2.0]]), ["x"])
    with pytest.raises(ValueError, match="NaN or infinite"):
        transform_feature_scaler(np.array([[np.nan]]), model, ["x"])


def test_manifest_contains_train_only_provenance_and_parameters():
    train = np.array([[1.0, 0.0], [2.0, 1.0], [3.0, 0.0]])
    model = fit_feature_scaler(
        train,
        ["cloud_property", "missing_indicator"],
        feature_families=["cloud", None],
        weighting="family_balanced",
        scale_mask=[True, False],
    )

    manifest = build_scaling_manifest(model)
    assert manifest["fit_scope"] == "training_partition_only"
    assert manifest["feature_order"] == ["cloud_property", "missing_indicator"]
    assert manifest["output_dtype"] == "float32"
    json.dumps(manifest, allow_nan=False)


def test_manifest_can_be_saved_with_additional_metadata(tmp_path):
    model = fit_feature_scaler(np.array([[1.0], [2.0]]), ["cloud_area"])
    output_path = save_scaling_manifest(
        model,
        tmp_path / "reports" / "scaling_manifest.json",
        metadata={"experiment": "FS-A_MD-A_robust"},
    )

    assert output_path.exists()
    content = json.loads(output_path.read_text(encoding="utf-8"))
    assert content["metadata"]["experiment"] == "FS-A_MD-A_robust"


def test_scaling_mask_must_match_feature_count():
    with pytest.raises(ValueError, match="one boolean per feature"):
        fit_feature_scaler(
            np.ones((3, 2)),
            ["a", "b"],
            scale_mask=[True],
        )


def test_at_least_one_feature_must_be_scaled():
    with pytest.raises(ValueError, match="At least one feature"):
        fit_feature_scaler(
            np.ones((3, 2)),
            ["a", "b"],
            scale_mask=[False, False],
        )
