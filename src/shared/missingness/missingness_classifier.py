
from enum import IntEnum
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

REGISTRY_PATH = (
    ROOT
    / "reports"
    / "feature_engineering"
    / "feature_set_registry.csv"
)

CLOUD_AREA_VARIABLES = {
    "cldarea_high_1h",
    "cldarea_mid_high_1h",
    "cldarea_mid_low_1h",
    "cldarea_low_1h",
    "cldarea_total_1h",
}


class MissingnessCode(IntEnum):
    OBSERVED = 0
    STRUCTURAL_ABSENCE = 1
    RESIDUAL_MISSING = 2
    UNKNOWN_CLOUD_AVAILABILITY = 3
    CLOUD_AREA_MISSING = 4


CLASSIFICATION_LABELS = {
    int(MissingnessCode.OBSERVED): "OBSERVED",
    int(MissingnessCode.STRUCTURAL_ABSENCE): "STRUCTURAL_ABSENCE",
    int(MissingnessCode.RESIDUAL_MISSING): "RESIDUAL_MISSING",
    int(MissingnessCode.UNKNOWN_CLOUD_AVAILABILITY):
        "UNKNOWN_CLOUD_AVAILABILITY",
    int(MissingnessCode.CLOUD_AREA_MISSING): "CLOUD_AREA_MISSING",
}


def load_feature_registry(registry_path=REGISTRY_PATH):
    registry_path = Path(registry_path)

    if not registry_path.exists():
        raise FileNotFoundError(
            f"Feature registry not found: {registry_path}"
        )

    registry = pd.read_csv(registry_path)

    required_columns = {
        "variable",
        "matching_cloud_area_variable",
    }

    missing_columns = required_columns - set(registry.columns)

    if missing_columns:
        raise ValueError(
            f"Registry is missing columns: {sorted(missing_columns)}"
        )

    if registry["variable"].duplicated().any():
        duplicates = registry.loc[
            registry["variable"].duplicated(keep=False),
            "variable",
        ].tolist()

        raise ValueError(
            f"Duplicate variables in registry: {duplicates}"
        )

    mapping = {}

    for _, row in registry.iterrows():
        variable = str(row["variable"]).strip()

        area_value = row["matching_cloud_area_variable"]

        if pd.isna(area_value) or not str(area_value).strip():
            mapping[variable] = None
            continue

        area_variable = str(area_value).strip()

        if area_variable not in CLOUD_AREA_VARIABLES:
            raise ValueError(
                f"Invalid cloud-area mapping for {variable}: "
                f"{area_variable}"
            )

        mapping[variable] = area_variable

    return mapping


def get_matching_area_variable(variable, registry=None):
    if variable in CLOUD_AREA_VARIABLES:
        return None

    if registry is None:
        registry = load_feature_registry()

    if variable not in registry:
        raise KeyError(
            f"Variable not found in feature registry: {variable}"
        )

    area_variable = registry[variable]

    if area_variable is None:
        raise ValueError(
            f"No matching cloud-area variable for: {variable}"
        )

    return area_variable


def classify_missingness(
    values,
    variable,
    area_values=None,
    area_variable=None,
):
    values = np.asarray(values)

    if variable in CLOUD_AREA_VARIABLES:
        if area_values is not None:
            raise ValueError(
                "Do not provide area_values when classifying "
                "a cloud-area variable."
            )

        classifications = np.full(
            values.shape,
            MissingnessCode.OBSERVED,
            dtype=np.uint8,
        )

        classifications[~np.isfinite(values)] = (
            MissingnessCode.CLOUD_AREA_MISSING
        )

        return classifications

    if area_values is None:
        raise ValueError(
            f"Matching cloud-area values are required for {variable}"
        )

    if area_variable is None:
        raise ValueError(
            f"Matching cloud-area variable must be specified for {variable}"
        )

    if area_variable not in CLOUD_AREA_VARIABLES:
        raise ValueError(
            f"Invalid cloud-area variable: {area_variable}"
        )

    area_values = np.asarray(area_values)

    if values.shape != area_values.shape:
        raise ValueError(
            "Property and cloud-area arrays must have identical shapes: "
            f"{values.shape} != {area_values.shape}"
        )

    property_finite = np.isfinite(values)
    area_finite = np.isfinite(area_values)

    if np.any(area_finite & (area_values < 0)):
        raise ValueError(
            f"Negative cloud-area values found in {area_variable}"
        )

    classifications = np.full(
        values.shape,
        MissingnessCode.OBSERVED,
        dtype=np.uint8,
    )

    property_missing = ~property_finite

    classifications[
        property_missing & area_finite & (area_values == 0)
    ] = MissingnessCode.STRUCTURAL_ABSENCE

    classifications[
        property_missing & area_finite & (area_values > 0)
    ] = MissingnessCode.RESIDUAL_MISSING

    classifications[
        property_missing & ~area_finite
    ] = MissingnessCode.UNKNOWN_CLOUD_AVAILABILITY

    return classifications


def classify_registered_variable(
    values,
    variable,
    area_values=None,
    registry=None,
):
    if variable in CLOUD_AREA_VARIABLES:
        return classify_missingness(
            values=values,
            variable=variable,
        )

    area_variable = get_matching_area_variable(
        variable=variable,
        registry=registry,
    )

    return classify_missingness(
        values=values,
        variable=variable,
        area_values=area_values,
        area_variable=area_variable,
    )


def summarize_classifications(classifications):
    classifications = np.asarray(classifications)

    total = int(classifications.size)

    summary = {
        "total_values": total,
    }

    for code, label in CLASSIFICATION_LABELS.items():
        count = int(np.count_nonzero(classifications == code))

        summary[label.lower()] = count
        summary[f"{label.lower()}_pct"] = (
            100 * count / total if total else 0.0
        )

    return summary
