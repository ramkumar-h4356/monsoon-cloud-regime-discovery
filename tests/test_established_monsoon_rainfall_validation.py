import numpy as np
import pandas as pd
import pytest

from established_monsoon_rainfall_validation import (
    RainfallValidationError,
    build_rainfall_key_frame,
    validate_assignment_frame,
    validate_coordinate,
    validate_dates,
    validate_matched_frame,
    validate_rainfall_units,
    validate_rainfall_values,
    validate_summary_frame,
)


def valid_assignments():
    rows = []
    for day in pd.date_range("2010-07-15", "2010-08-13"):
        for lat, lon in [(10.5, 70.5), (11.5, 71.5)]:
            rows.append({
                "year": 2010, "date": day, "latitude": lat, "longitude": lon,
                "baseline_k2": 0, "log_k2": 1, "log_k3": 2,
            })
    return pd.DataFrame(rows)


def test_coordinate_accepts_strictly_ascending_and_descending():
    assert validate_coordinate([1, 2, 3], "lat").tolist() == [1, 2, 3]
    assert validate_coordinate([3, 2, 1], "lon").tolist() == [3, 2, 1]


@pytest.mark.parametrize("values", [[1, 1, 2], [1, np.nan, 3], [1, 3, 2]])
def test_coordinate_rejects_duplicates_nonfinite_and_nonmonotonic(values):
    with pytest.raises(RainfallValidationError):
        validate_coordinate(values, "latitude")


def test_coordinate_checks_expected_count():
    with pytest.raises(RainfallValidationError, match="expected 32"):
        validate_coordinate([1, 2], "latitude", 32)


def test_dates_accept_exact_established_monsoon_window():
    dates = pd.date_range("2010-07-15", "2010-08-13")
    assert len(validate_dates(dates, 2010)) == 30


@pytest.mark.parametrize("dates", [
    pd.date_range("2010-07-16", "2010-08-14"),
    list(pd.date_range("2010-07-15", "2010-08-13")) + [pd.Timestamp("2010-07-15")],
    [pd.Timestamp("2011-07-15")],
])
def test_dates_reject_wrong_window_duplicates_and_year_mismatch(dates):
    with pytest.raises(RainfallValidationError):
        validate_dates(dates, 2010)


def test_rainfall_values_preserve_nan_and_reject_negative_or_infinite():
    valid, missing = validate_rainfall_values(np.array([0.0, 2.5, np.nan]), 2010)
    assert (valid, missing) == (2, 1)
    with pytest.raises(RainfallValidationError, match="negative"):
        validate_rainfall_values(np.array([1.0, -0.1]), 2010)
    with pytest.raises(RainfallValidationError, match="infinite"):
        validate_rainfall_values(np.array([1.0, np.inf]), 2010)


def test_units_accept_mm_aliases_and_reject_unknown_units():
    assert validate_rainfall_units("millimetres", 2010) == "mm"
    with pytest.raises(RainfallValidationError):
        validate_rainfall_units("kg m-2 s-1", 2010)


def test_assignment_validation_detects_duplicate_keys():
    frame = valid_assignments()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(RainfallValidationError, match="duplicate"):
        validate_assignment_frame(frame, expected_years=[2010])


def test_assignment_validation_checks_cluster_label_range():
    frame = valid_assignments()
    frame.loc[0, "log_k3"] = 3
    with pytest.raises(RainfallValidationError, match="outside"):
        validate_assignment_frame(frame, expected_years=[2010])


def test_assignment_validation_reports_missing_cluster_year_as_warning():
    frame = valid_assignments()
    frame["log_k3"] = 0
    _, issues = validate_assignment_frame(frame, expected_years=[2010])
    assert sum(issue.code == "MISSING_CLUSTER_YEAR" and "log_k3" in issue.message for issue in issues) == 2


def test_key_frame_includes_only_finite_rainfall_cells():
    dates = pd.date_range("2010-07-15", "2010-08-13")
    lat = np.arange(32, dtype=float)
    lon = np.arange(30, dtype=float)
    values = np.full((30, 32, 30), np.nan)
    values[0, 0, 0] = 0.0
    values[1, 1, 1] = 3.0
    keys = build_rainfall_key_frame(2010, dates, lat, lon, values)
    assert len(keys) == 2
    assert keys["year"].eq(2010).all()


def test_summary_validation_rejects_empty_duplicate_and_nonfinite():
    schema = dict(name="annual", key_columns=["year", "cluster"],
                  numeric_columns=["mean_mm"], nonnegative_columns=[])
    with pytest.raises(RainfallValidationError, match="empty"):
        validate_summary_frame(pd.DataFrame(), **schema)
    duplicate = pd.DataFrame({"year": [2010, 2010], "cluster": [0, 0], "mean_mm": [1, 2]})
    with pytest.raises(RainfallValidationError, match="duplicate"):
        validate_summary_frame(duplicate, **schema)
    nonfinite = pd.DataFrame({"year": [2010], "cluster": [0], "mean_mm": [np.inf]})
    with pytest.raises(RainfallValidationError, match="non-finite"):
        validate_summary_frame(nonfinite, **schema)


def test_matched_frame_requires_valid_nonnegative_unique_observations():
    frame = valid_assignments().iloc[:1].copy()
    frame["rainfall_mm"] = 0.0
    checked = validate_matched_frame(frame)
    assert len(checked) == 1
    frame.loc[0, "rainfall_mm"] = np.nan
    with pytest.raises(RainfallValidationError, match="missing rainfall"):
        validate_matched_frame(frame)
