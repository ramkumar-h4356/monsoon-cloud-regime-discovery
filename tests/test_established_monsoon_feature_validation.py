import numpy as np
import pandas as pd
import pytest

from established_monsoon_feature_validation import (
    FEATURES, LOG1P_FEATURES, YEARS, FeatureValidationError,
    validate_feature_names, validate_feature_frame, build_feature_registry,
    validate_registry,
)


def sample_frame():
    rows = []
    for i in range(2):
        row = {"year": 2010, "date": pd.Timestamp("2010-07-15") + pd.Timedelta(days=i),
               "latitude": 10.0, "longitude": 70.0 + i}
        row.update({f: 1.0 for f in FEATURES})
        rows.append(row)
    return pd.DataFrame(rows)


def test_feature_schema_has_fourteen_unique_features():
    assert len(FEATURES) == 14
    assert len(set(FEATURES)) == 14
    assert len(LOG1P_FEATURES) == 4


def test_exact_feature_order_accepted():
    assert validate_feature_names(FEATURES) == FEATURES


def test_duplicate_feature_names_rejected():
    with pytest.raises(FeatureValidationError):
        validate_feature_names(FEATURES[:-1] + (FEATURES[0],))


def test_reordered_feature_names_rejected():
    with pytest.raises(FeatureValidationError):
        validate_feature_names(tuple(reversed(FEATURES)))


def test_valid_feature_frame_accepted():
    validate_feature_frame(sample_frame())


def test_missing_feature_column_rejected():
    frame = sample_frame().drop(columns=[FEATURES[0]])
    with pytest.raises(FeatureValidationError):
        validate_feature_frame(frame)


def test_empty_frame_rejected():
    with pytest.raises(FeatureValidationError):
        validate_feature_frame(sample_frame().iloc[0:0])


def test_missing_metadata_rejected():
    frame = sample_frame()
    frame.loc[0, "latitude"] = np.nan
    with pytest.raises(FeatureValidationError):
        validate_feature_frame(frame)


def test_duplicate_spatiotemporal_key_rejected():
    frame = sample_frame()
    frame.loc[1, ["date", "latitude", "longitude"]] = frame.loc[0, ["date", "latitude", "longitude"]]
    with pytest.raises(FeatureValidationError):
        validate_feature_frame(frame)


def test_infinite_feature_rejected():
    frame = sample_frame()
    frame.loc[0, FEATURES[0]] = np.inf
    with pytest.raises(FeatureValidationError):
        validate_feature_frame(frame)


@pytest.mark.parametrize("feature", LOG1P_FEATURES)
def test_negative_log_feature_rejected(feature):
    frame = sample_frame()
    frame.loc[0, feature] = -0.1
    with pytest.raises(FeatureValidationError):
        validate_feature_frame(frame)


def evidence_tables():
    screening = pd.DataFrame({
        "variable": list(FEATURES), "units": ["unit"] * len(FEATURES),
        "valid_observations": [100] * len(FEATURES),
        "missing_observations": [2] * len(FEATURES),
        "missing_percentage": [2.0] * len(FEATURES),
        "standard_deviation": [1.0] * len(FEATURES),
        "constant": [False] * len(FEATURES), "years_with_data": [12] * len(FEATURES),
    })
    yearly = pd.DataFrame([
        {"year": y, "variable": f, "missing_percentage": 2.0, "valid_observations": 10}
        for f in FEATURES for y in YEARS
    ])
    integrated = pd.DataFrame({
        "variable": list(FEATURES),
        "high_correlation_partner_count": [0] * len(FEATURES),
        "high_correlation_partners": [""] * len(FEATURES),
    })
    return screening, yearly, integrated


def test_registry_builds_fourteen_rows_without_auto_exclusion():
    registry = build_feature_registry(*evidence_tables())
    validate_registry(registry)
    assert len(registry) == 14
    assert not registry["automatic_exclusion"].any()


def test_registry_flags_log1p_features():
    registry = build_feature_registry(*evidence_tables()).set_index("feature")
    for feature in LOG1P_FEATURES:
        assert registry.loc[feature, "transformation"] == "log1p then StandardScaler"


def test_registry_requires_twelve_year_records_per_feature():
    screening, yearly, integrated = evidence_tables()
    yearly = yearly[~((yearly["variable"] == FEATURES[0]) & (yearly["year"] == 2010))]
    with pytest.raises(FeatureValidationError):
        build_feature_registry(screening, yearly, integrated)


def test_registry_rejects_nonfinite_evidence():
    registry = build_feature_registry(*evidence_tables())
    registry.loc[0, "standard_deviation_original_units"] = np.nan
    with pytest.raises(FeatureValidationError):
        validate_registry(registry)


def test_registry_rejects_duplicate_feature_rows():
    registry = build_feature_registry(*evidence_tables())
    registry.loc[1, "feature"] = registry.loc[0, "feature"]
    with pytest.raises(FeatureValidationError):
        validate_registry(registry)


def test_year_date_mismatch_rejected():
    frame = sample_frame()
    frame.loc[0, "year"] = 2011
    with pytest.raises(FeatureValidationError, match="does not agree"):
        validate_feature_frame(frame)


def test_outside_season_date_rejected():
    frame = sample_frame()
    frame.loc[0, "date"] = pd.Timestamp("2010-08-14")
    with pytest.raises(FeatureValidationError, match="outside"):
        validate_feature_frame(frame)


def test_nonfinite_coordinate_metadata_rejected():
    frame = sample_frame()
    frame.loc[0, "longitude"] = np.inf
    with pytest.raises(FeatureValidationError, match="finite"):
        validate_feature_frame(frame)
