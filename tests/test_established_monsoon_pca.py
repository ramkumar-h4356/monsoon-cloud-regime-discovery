from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PCA_DIR = ROOT / "src" / "08_dimensionality_reduction"
sys.path.insert(0, str(PCA_DIR))

import numpy as np
import pandas as pd
import pytest

from established_monsoon_pca import (
    fit_pca,
    principal_angles_degrees,
    validate_inputs,
    variance_threshold_components,
)


def sample_inputs():
    rng = np.random.default_rng(42)
    x = rng.normal(size=(40, 4))
    features = np.array(["a", "b", "c", "d"])
    metadata = pd.DataFrame({
        "year": np.repeat(2010, 40),
        "date": ["2010-07-15"] * 40,
        "latitude": np.linspace(6.5, 37.5, 40),
        "longitude": np.linspace(68.5, 97.5, 40),
    })
    return x, features, metadata


def test_valid_inputs_pass():
    x, features, metadata = sample_inputs()
    validate_inputs(x, x.copy(), features, features.copy(), metadata, features.tolist())


def test_nonfinite_matrix_rejected():
    x, features, metadata = sample_inputs()
    x[0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN or infinite"):
        validate_inputs(x, x.copy(), features, features.copy(), metadata)


def test_feature_order_mismatch_rejected():
    x, features, metadata = sample_inputs()
    with pytest.raises(ValueError, match="feature orders differ"):
        validate_inputs(x, x.copy(), features, features[::-1], metadata)


def test_metadata_row_mismatch_rejected():
    x, features, metadata = sample_inputs()
    with pytest.raises(ValueError, match="Metadata row count"):
        validate_inputs(x, x.copy(), features, features.copy(), metadata.iloc[:-1])


def test_expected_feature_order_enforced():
    x, features, metadata = sample_inputs()
    with pytest.raises(ValueError, match="manifest"):
        validate_inputs(x, x.copy(), features, features.copy(), metadata, ["d", "c", "b", "a"])


def test_pca_variance_sums_to_one():
    x, _, _ = sample_inputs()
    model, scores = fit_pca(x)
    assert scores.shape == (40, 4)
    assert np.isclose(model.explained_variance_ratio_.sum(), 1.0)


def test_variance_thresholds():
    ratios = np.array([0.5, 0.25, 0.15, 0.10])
    assert variance_threshold_components(ratios) == {
        "80_percent": 3, "90_percent": 3, "95_percent": 4
    }


def test_identical_subspaces_have_zero_angles():
    components = np.eye(4)
    angles = principal_angles_degrees(components, components.copy(), 2)
    assert np.allclose(angles, 0.0)


def test_principal_angles_are_bounded():
    a = np.eye(4)
    b = np.roll(np.eye(4), 1, axis=0)
    angles = principal_angles_degrees(a, b, 2)
    assert np.all((angles >= 0) & (angles <= 90))
