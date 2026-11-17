"""Reusable validation rules for the established-monsoon rainfall workflow.

This module validates inputs and derived comparison tables. It deliberately
preserves missing rainfall as missing and never interprets missing values as 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

EXPECTED_YEARS = tuple(range(2010, 2022))
EXPECTED_DATES_PER_YEAR = 30
EXPECTED_LAT_COUNT = 32
EXPECTED_LON_COUNT = 30
START_MONTH_DAY = "07-15"
END_MONTH_DAY = "08-13"
KEYS = ["year", "date", "latitude", "longitude"]
CLUSTER_COLUMNS = {"baseline_k2": 2, "log_k2": 2, "log_k3": 3}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    count: int = 0


class RainfallValidationError(ValueError):
    """Raised when a rainfall input violates a required invariant."""


def _fail(message: str) -> None:
    raise RainfallValidationError(message)


def validate_coordinate(values: Sequence[float], name: str, expected_count: int | None = None) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        _fail(f"{name}: coordinate must be one-dimensional; got shape {arr.shape}")
    if expected_count is not None and len(arr) != expected_count:
        _fail(f"{name}: expected {expected_count} values, found {len(arr)}")
    if not np.isfinite(arr).all():
        _fail(f"{name}: non-finite coordinate values found")
    if len(np.unique(arr)) != len(arr):
        _fail(f"{name}: duplicate coordinate values found")
    if len(arr) > 1:
        delta = np.diff(arr)
        if not (np.all(delta > 0) or np.all(delta < 0)):
            _fail(f"{name}: coordinate must be strictly monotonic ascending or descending")
    return arr


def expected_dates(year: int) -> pd.DatetimeIndex:
    return pd.date_range(f"{int(year)}-{START_MONTH_DAY}", f"{int(year)}-{END_MONTH_DAY}", freq="D")


def validate_dates(values: Iterable, year: int, *, exact_window: bool = True) -> pd.DatetimeIndex:
    dates = pd.DatetimeIndex(pd.to_datetime(list(values), errors="coerce"))
    if dates.isna().any():
        _fail(f"{year}: invalid or missing date values found")
    if not dates.equals(dates.normalize()):
        _fail(f"{year}: dates must be normalized to midnight")
    if dates.has_duplicates:
        _fail(f"{year}: duplicate dates found")
    if not (dates.year == int(year)).all():
        _fail(f"{year}: date year does not match the annual file/year field")
    if exact_window and not dates.equals(expected_dates(year)):
        _fail(f"{year}: dates do not exactly match July 15–August 13")
    return dates


def validate_rainfall_values(values: np.ndarray, year: int) -> tuple[int, int]:
    arr = np.asarray(values)
    if not np.issubdtype(arr.dtype, np.number):
        _fail(f"{year}: rainfall values must be numeric")
    finite = np.isfinite(arr)
    negative = int(np.count_nonzero((arr < 0) & finite))
    infinite = int(np.count_nonzero(np.isinf(arr)))
    if infinite:
        _fail(f"{year}: {infinite} infinite rainfall values found")
    if negative:
        _fail(f"{year}: {negative} negative finite rainfall values found")
    return int(finite.sum()), int((~finite).sum())


def validate_rainfall_units(units: str | None, year: int) -> str:
    normalized = "" if units is None else str(units).strip().lower()
    accepted = {"mm", "millimeter", "millimeters", "millimetre", "millimetres"}
    if normalized not in accepted:
        _fail(f"{year}: expected daily rainfall units mm; found {units!r}")
    return "mm"


def validate_assignment_frame(
    frame: pd.DataFrame,
    *,
    expected_years: Sequence[int] = EXPECTED_YEARS,
    cluster_columns: dict[str, int] = CLUSTER_COLUMNS,
    require_all_years: bool = True,
) -> tuple[pd.DataFrame, list[ValidationIssue]]:
    required = set(KEYS) | set(cluster_columns)
    missing = sorted(required - set(frame.columns))
    if missing:
        _fail(f"Assignment file missing required columns: {missing}")

    data = frame.copy()
    data["year"] = pd.to_numeric(data["year"], errors="coerce")
    if data["year"].isna().any() or not np.equal(data["year"], np.floor(data["year"])).all():
        _fail("Assignment year contains missing or non-integer values")
    data["year"] = data["year"].astype(int)
    if not data["year"].isin(expected_years).all():
        bad = sorted(set(data.loc[~data["year"].isin(expected_years), "year"].tolist()))
        _fail(f"Assignment contains unexpected years: {bad}")

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    if data["date"].isna().any():
        _fail("Assignment date contains invalid or missing values")
    if not data["date"].equals(data["date"].dt.normalize()):
        _fail("Assignment dates must be normalized to midnight")
    if not (data["date"].dt.year == data["year"]).all():
        _fail("Assignment date year does not match year column")
    in_window = (
        (data["date"].dt.month == 7) & (data["date"].dt.day >= 15)
    ) | (
        (data["date"].dt.month == 8) & (data["date"].dt.day <= 13)
    )
    if not in_window.all():
        _fail("Assignment contains dates outside July 15–August 13")

    for column in ("latitude", "longitude"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].isna().any() or not np.isfinite(data[column].to_numpy()).all():
            _fail(f"Assignment {column} contains missing or non-finite values")

    duplicates = int(data.duplicated(KEYS).sum())
    if duplicates:
        _fail(f"Assignment contains {duplicates} duplicate year/date/latitude/longitude keys")

    for column, k in cluster_columns.items():
        labels = pd.to_numeric(data[column], errors="coerce")
        if labels.isna().any() or not np.isfinite(labels.to_numpy(dtype=float)).all():
            _fail(f"Cluster column {column} contains missing or non-finite labels")
        if not np.equal(labels, np.floor(labels)).all():
            _fail(f"Cluster column {column} contains non-integer labels")
        if ((labels < 0) | (labels >= k)).any():
            _fail(f"Cluster column {column} contains labels outside [0, {k - 1}]")
        data[column] = labels.astype(int)

    issues: list[ValidationIssue] = []
    present_years = set(data["year"].unique())
    missing_years = sorted(set(expected_years) - present_years)
    if require_all_years and missing_years:
        _fail(f"Assignment file is missing expected years: {missing_years}")

    # Missing cluster-year combinations are surfaced explicitly. They may
    # reflect genuinely absent clusters in a year, so they are warnings.
    for column, k in cluster_columns.items():
        for year in expected_years:
            observed = set(data.loc[data["year"] == year, column].unique())
            for label in sorted(set(range(k)) - observed):
                issues.append(ValidationIssue(
                    "WARNING", "MISSING_CLUSTER_YEAR", 
                    f"{column}: cluster {label} has no assignments in {year}", 1
                ))
    return data, issues


def validate_summary_frame(
    frame: pd.DataFrame,
    *,
    name: str,
    key_columns: Sequence[str],
    numeric_columns: Sequence[str],
    allow_empty: bool = False,
    nonnegative_columns: Sequence[str] = (),
) -> None:
    if frame.empty and not allow_empty:
        _fail(f"{name}: comparison produced an empty result")
    required = set(key_columns) | set(numeric_columns)
    missing = sorted(required - set(frame.columns))
    if missing:
        _fail(f"{name}: missing required columns {missing}")
    if frame.duplicated(list(key_columns)).any():
        _fail(f"{name}: duplicate summary keys found")
    for column in numeric_columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            _fail(f"{name}: {column} contains missing or non-finite values")
    for column in nonnegative_columns:
        if (pd.to_numeric(frame[column], errors="coerce") < 0).any():
            _fail(f"{name}: {column} contains negative support/count values")


def validate_matched_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = set(KEYS) | {"rainfall_mm"} | set(CLUSTER_COLUMNS)
    missing = sorted(required - set(frame.columns))
    if missing:
        _fail(f"Matched cloud-rainfall table missing columns: {missing}")
    data = frame.copy()
    data["year"] = pd.to_numeric(data["year"], errors="coerce").astype("Int64")
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    for column in ("latitude", "longitude", "rainfall_mm"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if data[KEYS].isna().any().any():
        _fail("Matched table contains missing join-key values")
    if data["rainfall_mm"].isna().any():
        _fail("Matched table contains missing rainfall; matched rows must be valid observations")
    if not np.isfinite(data["rainfall_mm"].to_numpy(dtype=float)).all():
        _fail("Matched table contains non-finite rainfall")
    if (data["rainfall_mm"] < 0).any():
        _fail("Matched table contains negative rainfall")
    if data.duplicated(KEYS).any():
        _fail("Matched table contains duplicate join keys")
    # Reuse assignment validation for the key and label invariants.
    validate_assignment_frame(data, require_all_years=False)
    return data


def build_rainfall_key_frame(
    year: int,
    dates: Sequence,
    latitudes: Sequence[float],
    longitudes: Sequence[float],
    values: np.ndarray,
) -> pd.DataFrame:
    date_index = validate_dates(dates, year)
    lat = validate_coordinate(latitudes, "latitude", EXPECTED_LAT_COUNT)
    lon = validate_coordinate(longitudes, "longitude", EXPECTED_LON_COUNT)
    arr = np.asarray(values)
    if arr.shape != (len(date_index), len(lat), len(lon)):
        _fail(f"{year}: rainfall array shape {arr.shape} does not match coordinates")
    validate_rainfall_values(arr, year)
    day_idx, lat_idx, lon_idx = np.where(np.isfinite(arr))
    return pd.DataFrame({
        "year": int(year),
        "date": date_index.to_numpy()[day_idx],
        "latitude": lat[lat_idx],
        "longitude": lon[lon_idx],
    })
