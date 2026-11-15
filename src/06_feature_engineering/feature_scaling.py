"""Leakage-safe scaling for M18 feature matrices.

Only training data may be passed to fit_feature_scaler(). Validation/test
partitions must be passed to transform_feature_scaler() with the returned
model. Binary diagnostic indicators can be preserved as 0/1 by setting their
entries in scale_mask to False.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
from sklearn.preprocessing import RobustScaler, StandardScaler


SCALER_TYPES = {"robust", "standard"}
WEIGHTING_TYPES = {"equal", "family_balanced"}


@dataclass(frozen=True)
class FeatureScalingModel:
    scaler_type: str
    weighting: str
    feature_names: tuple[str, ...]
    feature_families: tuple[Optional[str], ...]
    scale_mask: tuple[bool, ...]
    center: np.ndarray
    scale: np.ndarray
    feature_weights: np.ndarray
    n_training_samples: int
    quantile_range: tuple[float, float]


def _validate_feature_names(feature_names, n_features):
    names = tuple(str(name).strip() for name in feature_names)
    if len(names) != n_features:
        raise ValueError(
            f"Expected {n_features} feature names, received {len(names)}."
        )
    if any(not name for name in names):
        raise ValueError("Feature names must be non-empty.")
    if len(set(names)) != len(names):
        raise ValueError("Feature names must be unique.")
    return names


def _validate_matrix(values, label):
    try:
        matrix = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a numeric 2D matrix.") from exc

    if matrix.ndim != 2:
        raise ValueError(
            f"{label} must be 2D (samples x features); got shape {matrix.shape}."
        )
    if matrix.shape[0] == 0 or matrix.shape[1] == 0:
        raise ValueError(f"{label} must contain at least one sample and feature.")
    if not np.isfinite(matrix).all():
        raise ValueError(
            f"{label} contains NaN or infinite values. Complete imputation "
            "before scaling."
        )
    return matrix


def fit_feature_scaler(
    train_values,
    feature_names: Sequence[str],
    scaler: str = "robust",
    feature_families: Optional[Sequence[Optional[str]]] = None,
    weighting: str = "equal",
    scale_mask: Optional[Sequence[bool]] = None,
) -> FeatureScalingModel:
    """Fit scaling parameters using training data only.

    Parameters
    ----------
    train_values:
        2D matrix shaped (training samples, features). It must already be
        imputed and finite. Never pass validation/test rows here.
    feature_names:
        Exact column names in matrix order.
    scaler:
        ``"robust"`` (median/IQR, baseline) or ``"standard"`` (mean/std,
        sensitivity).
    feature_families:
        One family label per feature. Required for family-balanced weighting
        for every column selected by ``scale_mask``. Binary indicator columns
        can use ``None`` when their ``scale_mask`` entry is False.
    weighting:
        ``"equal"`` applies unit weight to every feature. ``"family_balanced"``
        applies 1/sqrt(number of scaled features in that family) to each
        scaled feature, normalizing each family's sum of squared weights to 1.
    scale_mask:
        Optional boolean mask. False columns are left unchanged (apart from
        float32 output conversion) and are not included in family counts.
        Use this for binary missingness indicators that should remain 0/1.
    """
    matrix = _validate_matrix(train_values, "train_values")
    n_samples, n_features = matrix.shape

    names = _validate_feature_names(feature_names, n_features)

    scaler = str(scaler).lower().strip()
    if scaler not in SCALER_TYPES:
        raise ValueError(
            f"Unsupported scaler {scaler!r}. Choose 'robust' or 'standard'."
        )

    weighting = str(weighting).lower().strip()
    if weighting not in WEIGHTING_TYPES:
        raise ValueError(
            "Unsupported weighting. Choose 'equal' or 'family_balanced'."
        )

    if scale_mask is None:
        mask = np.ones(n_features, dtype=bool)
    else:
        mask = np.asarray(scale_mask)
        if mask.ndim != 1 or mask.size != n_features:
            raise ValueError("scale_mask must contain one boolean per feature.")
        if not np.isin(mask, [True, False]).all():
            raise ValueError("scale_mask must contain only boolean values.")
        mask = mask.astype(bool, copy=False)

    if not mask.any():
        raise ValueError("At least one feature must be selected for scaling.")

    if feature_families is None:
        families = tuple(None for _ in range(n_features))
    else:
        raw_families = tuple(feature_families)
        if len(raw_families) != n_features:
            raise ValueError(
                "feature_families must contain one entry per feature."
            )
        normalized = []
        for index, family in enumerate(raw_families):
            if family is None:
                normalized.append(None)
            else:
                family_name = str(family).strip()
                if not family_name:
                    normalized.append(None)
                else:
                    normalized.append(family_name)
        families = tuple(normalized)

    if weighting == "family_balanced":
        missing_family_indices = [
            index
            for index, is_scaled in enumerate(mask)
            if is_scaled and families[index] is None
        ]
        if missing_family_indices:
            raise ValueError(
                "family_balanced weighting requires a non-empty family for "
                f"every scaled feature; missing at columns {missing_family_indices}."
            )

    center = np.zeros(n_features, dtype=np.float64)
    scale = np.ones(n_features, dtype=np.float64)

    selected = matrix[:, mask]
    if scaler == "robust":
        fitted_scaler = RobustScaler(
            with_centering=True,
            with_scaling=True,
            quantile_range=(25.0, 75.0),
        )
        fitted_scaler.fit(selected)
        selected_center = fitted_scaler.center_
        selected_scale = fitted_scaler.scale_
        quantile_range = (25.0, 75.0)
    else:
        fitted_scaler = StandardScaler(
            with_mean=True,
            with_std=True,
        )
        fitted_scaler.fit(selected)
        selected_center = fitted_scaler.mean_
        selected_scale = fitted_scaler.scale_
        quantile_range = (25.0, 75.0)

    center[mask] = np.asarray(selected_center, dtype=np.float64)
    scale[mask] = np.asarray(selected_scale, dtype=np.float64)

    if not np.isfinite(center).all() or not np.isfinite(scale).all():
        raise ValueError("Fitted scaling parameters are not finite.")
    if np.any(scale <= 0):
        raise ValueError("Fitted scaling parameters must be positive.")

    weights = np.ones(n_features, dtype=np.float64)
    if weighting == "family_balanced":
        family_counts = {}
        for index, is_scaled in enumerate(mask):
            if is_scaled:
                family = families[index]
                family_counts[family] = family_counts.get(family, 0) + 1

        for index, is_scaled in enumerate(mask):
            if is_scaled:
                weights[index] = 1.0 / np.sqrt(family_counts[families[index]])

    return FeatureScalingModel(
        scaler_type=scaler,
        weighting=weighting,
        feature_names=names,
        feature_families=families,
        scale_mask=tuple(bool(value) for value in mask),
        center=center,
        scale=scale,
        feature_weights=weights,
        n_training_samples=int(n_samples),
        quantile_range=quantile_range,
    )


def transform_feature_scaler(
    values,
    model: FeatureScalingModel,
    feature_names: Sequence[str],
) -> np.ndarray:
    """Transform any partition with a previously fitted training model."""
    if not isinstance(model, FeatureScalingModel):
        raise TypeError("model must be a FeatureScalingModel.")

    matrix = _validate_matrix(values, "values")
    names = _validate_feature_names(feature_names, matrix.shape[1])

    if names != model.feature_names:
        raise ValueError(
            "Feature names/order do not match the fitted scaling model. "
            "Reorder the matrix or fit a separate model."
        )
    if matrix.shape[1] != model.center.size:
        raise ValueError("Input feature count does not match the fitted model.")

    transformed = (matrix - model.center) / model.scale
    transformed *= model.feature_weights

    output = transformed.astype(np.float32)
    if not np.isfinite(output).all():
        raise ValueError(
            "Transformed values are not finite after float32 conversion."
        )
    return output


def build_scaling_manifest(model: FeatureScalingModel) -> dict:
    """Return JSON-serializable provenance for the fitted scaler."""
    if not isinstance(model, FeatureScalingModel):
        raise TypeError("model must be a FeatureScalingModel.")

    return {
        "scaler_type": model.scaler_type,
        "weighting": model.weighting,
        "fit_scope": "training_partition_only",
        "n_training_samples": model.n_training_samples,
        "feature_order": list(model.feature_names),
        "feature_families": list(model.feature_families),
        "scale_mask": list(model.scale_mask),
        "center": model.center.tolist(),
        "scale": model.scale.tolist(),
        "feature_weights": model.feature_weights.tolist(),
        "robust_quantile_range": list(model.quantile_range),
        "output_dtype": "float32",
    }


def save_scaling_manifest(
    model: FeatureScalingModel,
    output_path,
    metadata: Optional[dict] = None,
) -> Path:
    """Write scaler provenance as JSON; no pickle or executable object data."""
    manifest = build_scaling_manifest(model)
    if metadata:
        manifest["metadata"] = metadata

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2, allow_nan=False)
    return output_path
