from dataclasses import dataclass

import numpy as np

from missingness_classifier import MissingnessCode


PROPERTY_STRATEGIES = {"MD-A", "MD-B", "SA-A", "SA-B"}


@dataclass(frozen=True)
class PropertyTreatmentModel:
    strategy: str
    conditional_median: float
    overall_median: float


@dataclass(frozen=True)
class CloudAreaTreatmentModel:
    strategy: str
    median: float
    training_missing_pct: float


def _validate_same_shape(*arrays):
    shapes = [np.asarray(array).shape for array in arrays]
    if len(set(shapes)) != 1:
        raise ValueError(
            f"Input arrays must have identical shapes: {shapes}"
        )


def _validate_property_inputs(values, area_values, classifications):
    values = np.asarray(values, dtype=np.float64)
    area_values = np.asarray(area_values, dtype=np.float64)

    raw_classifications = np.asarray(classifications)
    if not np.issubdtype(raw_classifications.dtype, np.integer):
        if not np.isfinite(raw_classifications).all() or not np.equal(
            raw_classifications, np.floor(raw_classifications)
        ).all():
            raise ValueError("Classifications must contain integer codes.")

    classifications = raw_classifications.astype(np.uint8)
    _validate_same_shape(values, area_values, classifications)

    valid_codes = {
        int(code)
        for code in MissingnessCode
        if code != MissingnessCode.CLOUD_AREA_MISSING
    }
    if not np.isin(classifications, list(valid_codes)).all():
        raise ValueError("Invalid property missingness classification.")

    if np.any(np.isfinite(area_values) & (area_values < 0)):
        raise ValueError("Negative cloud-area values are not allowed.")

    property_finite = np.isfinite(values)
    if np.any(
        property_finite
        & (classifications != MissingnessCode.OBSERVED)
    ):
        raise ValueError(
            "Finite property values must be classified as OBSERVED."
        )
    if np.any(
        ~property_finite
        & (classifications == MissingnessCode.OBSERVED)
    ):
        raise ValueError(
            "Missing property values cannot be classified as OBSERVED."
        )

    expected_structural = (
        ~property_finite
        & np.isfinite(area_values)
        & (area_values == 0)
    )
    expected_residual = (
        ~property_finite
        & np.isfinite(area_values)
        & (area_values > 0)
    )
    expected_unknown = ~property_finite & ~np.isfinite(area_values)

    checks = (
        (
            MissingnessCode.STRUCTURAL_ABSENCE,
            expected_structural,
            "Structural-absence classifications are inconsistent.",
        ),
        (
            MissingnessCode.RESIDUAL_MISSING,
            expected_residual,
            "Residual-missing classifications are inconsistent.",
        ),
        (
            MissingnessCode.UNKNOWN_CLOUD_AVAILABILITY,
            expected_unknown,
            "Unknown-cloud-availability classifications are inconsistent.",
        ),
    )
    for code, expected, message in checks:
        if not np.array_equal(classifications == code, expected):
            raise ValueError(message)

    return values, area_values, classifications


def fit_property_treatment(
    train_values,
    train_area_values,
    train_classifications,
    strategy="MD-A",
):
    """Fit training-only medians for MD-A/MD-B/SA-A/SA-B.

    All four strategies use the same imputation values. They differ only in
    which missingness indicators are emitted during transformation.
    """
    if strategy not in PROPERTY_STRATEGIES:
        raise ValueError(f"Unsupported property strategy: {strategy}")

    values, area_values, classifications = _validate_property_inputs(
        train_values,
        train_area_values,
        train_classifications,
    )

    finite_property = np.isfinite(values)
    if not finite_property.any():
        raise ValueError(
            "Cannot fit property treatment without finite training values."
        )

    conditional_mask = (
        finite_property
        & np.isfinite(area_values)
        & (area_values > 0)
        & (classifications == MissingnessCode.OBSERVED)
    )
    if not conditional_mask.any():
        raise ValueError(
            "No finite training property values with positive cloud area."
        )

    return PropertyTreatmentModel(
        strategy=strategy,
        conditional_median=float(np.median(values[conditional_mask])),
        overall_median=float(np.median(values[finite_property])),
    )


def transform_property_treatment(
    values,
    area_values,
    classifications,
    model,
):
    """Transform a split using fitted medians; never refits on this split."""
    values, area_values, classifications = _validate_property_inputs(
        values,
        area_values,
        classifications,
    )
    if not isinstance(model, PropertyTreatmentModel):
        raise TypeError("model must be a PropertyTreatmentModel.")
    if model.strategy not in PROPERTY_STRATEGIES:
        raise ValueError(f"Unsupported property strategy: {model.strategy}")

    output = values.astype(np.float32, copy=True)
    structural = classifications == MissingnessCode.STRUCTURAL_ABSENCE
    residual = classifications == MissingnessCode.RESIDUAL_MISSING
    unknown = (
        classifications == MissingnessCode.UNKNOWN_CLOUD_AVAILABILITY
    )

    output[structural | residual] = model.conditional_median
    output[unknown] = model.overall_median

    if not np.isfinite(output).all():
        raise ValueError("Property treatment produced non-finite values.")

    result = {
        "feature": output,
        "unknown_cloud_availability": unknown.astype(np.uint8),
    }
    if model.strategy == "MD-B":
        result["residual_missingness"] = residual.astype(np.uint8)
    if model.strategy == "SA-B":
        result["structural_absence"] = structural.astype(np.uint8)

    return result


def assess_feature_eligibility(missing_pct):
    """Apply the predeclared <=5%, 5-20%, >20% screening bands."""
    missing_pct = float(missing_pct)
    if not np.isfinite(missing_pct) or not 0 <= missing_pct <= 100:
        raise ValueError("Missingness percentage must be between 0 and 100.")

    if missing_pct <= 5:
        return {"band": "LOW", "decision": "INCLUDE"}
    if missing_pct <= 20:
        return {"band": "MODERATE", "decision": "REVIEW"}
    return {"band": "HIGH", "decision": "EXCLUDE_PRIMARY"}


def assess_md_c_feature(residual_missing_pct):
    """Screen a property feature using residual missingness, not total missingness."""
    return assess_feature_eligibility(residual_missing_pct)


def assess_ca_b_feature(cloud_area_missing_pct):
    """Screen a cloud-area feature; CA-B does not impute or transform it."""
    return assess_feature_eligibility(cloud_area_missing_pct)


def fit_cloud_area_treatment(train_area_values, strategy="CA-A"):
    """Fit the CA-A training median. CA-B is screening-only."""
    if strategy != "CA-A":
        raise ValueError(
            "Only CA-A has an imputation model; use assess_ca_b_feature "
            "for CA-B feature screening."
        )

    values = np.asarray(train_area_values, dtype=np.float64)
    if values.size == 0:
        raise ValueError("Cloud-area training array is empty.")

    finite = np.isfinite(values)
    if np.any(values[finite] < 0):
        raise ValueError("Negative cloud-area values are not allowed.")
    if not finite.any():
        raise ValueError(
            "Cannot fit cloud-area treatment without finite training values."
        )

    missing_pct = 100 * float((~finite).sum()) / values.size
    return CloudAreaTreatmentModel(
        strategy="CA-A",
        median=float(np.median(values[finite])),
        training_missing_pct=missing_pct,
    )


def transform_cloud_area_treatment(values, model):
    """Apply CA-A using training median and preserve an availability mask."""
    if not isinstance(model, CloudAreaTreatmentModel):
        raise TypeError("model must be a CloudAreaTreatmentModel.")
    if model.strategy != "CA-A":
        raise ValueError("Cloud-area transform only supports CA-A.")

    values = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(values)
    if np.any(values[finite] < 0):
        raise ValueError("Negative cloud-area values are not allowed.")

    missing = ~finite
    output = values.astype(np.float32, copy=True)
    output[missing] = model.median

    return {
        "feature": output,
        "availability_missing": missing.astype(np.uint8),
    }
