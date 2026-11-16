"""Validation and registry helpers for Established Monsoon Group B features.

This module deliberately does not impute missing physical observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

YEARS = tuple(range(2010, 2022))
EXPECTED_DAYS = 30
EXPECTED_LAT = 32
EXPECTED_LON = 30
EXPECTED_ROWS_PER_YEAR = EXPECTED_DAYS * EXPECTED_LAT * EXPECTED_LON

FEATURES = (
    "cldarea_total_1h",
    "cldhght_total_1h",
    "cldphase_total_1h",
    "cldpress_total_1h",
    "cldtemp_total_1h",
    "cldtau_total_1h",
    "iwp_total_1h",
    "cldarea_high_1h",
    "cldhght_high_1h",
    "cldphase_high_1h",
    "cldpress_high_1h",
    "cldtemp_high_1h",
    "cldtau_high_1h",
    "iwp_high_1h",
)

LOG1P_FEATURES = (
    "cldtau_total_1h",
    "iwp_total_1h",
    "cldtau_high_1h",
    "iwp_high_1h",
)

MEANINGS = {
    "cldarea_total_1h": "Total-cloud area fraction/coverage",
    "cldhght_total_1h": "Total-cloud height",
    "cldphase_total_1h": "Total-cloud phase property",
    "cldpress_total_1h": "Total-cloud pressure property",
    "cldtemp_total_1h": "Total-cloud temperature property",
    "cldtau_total_1h": "Total-cloud optical depth",
    "iwp_total_1h": "Total-cloud ice water path",
    "cldarea_high_1h": "High-cloud area fraction/coverage",
    "cldhght_high_1h": "High-cloud height",
    "cldphase_high_1h": "High-cloud phase property",
    "cldpress_high_1h": "High-cloud pressure property",
    "cldtemp_high_1h": "High-cloud temperature property",
    "cldtau_high_1h": "High-cloud optical depth",
    "iwp_high_1h": "High-cloud ice water path",
}

SELECTION_REASON = (
    "Provisional Group B feature: selected in the existing project because "
    "the 14-variable total/high-cloud set balances physical breadth and "
    "spatial complete-case representativeness. This is not a claim that the "
    "feature is universally optimal or cross-season validated."
)

REQUIRED_METADATA = ("year", "date", "latitude", "longitude")


class FeatureValidationError(ValueError):
    """Raised when a feature matrix or annual input violates its contract."""


def validate_feature_names(feature_names: Iterable[str]) -> tuple[str, ...]:
    names = tuple(feature_names)
    if len(names) != len(set(names)):
        raise FeatureValidationError("Feature names contain duplicates.")
    if names != FEATURES:
        missing = sorted(set(FEATURES) - set(names))
        extra = sorted(set(names) - set(FEATURES))
        raise FeatureValidationError(
            f"Feature schema/order mismatch; missing={missing}, extra={extra}."
        )
    return names


def validate_annual_dataset(ds, year: int) -> None:
    """Validate dimensions, dates, coordinates, feature schema and values."""
    if year not in YEARS:
        raise FeatureValidationError(f"Unexpected year: {year}")
    expected_sizes = {"time": EXPECTED_DAYS, "lat": EXPECTED_LAT, "lon": EXPECTED_LON}
    actual_sizes = {k: int(v) for k, v in ds.sizes.items()}
    if actual_sizes != expected_sizes:
        raise FeatureValidationError(
            f"{year}: expected dimensions {expected_sizes}, got {actual_sizes}"
        )
    for coord in ("time", "lat", "lon"):
        if coord not in ds.coords:
            raise FeatureValidationError(f"{year}: missing coordinate {coord}")
        values = np.asarray(ds[coord].values)
        if values.ndim != 1 or not np.isfinite(
            values.astype("datetime64[ns]").astype("int64")
            if coord == "time" else values.astype(float)
        ).all():
            raise FeatureValidationError(f"{year}: invalid {coord} coordinate")
        if len(np.unique(values)) != len(values):
            raise FeatureValidationError(f"{year}: duplicate {coord} coordinate")
        if len(values) > 1:
            ordered = np.diff(values.astype("datetime64[ns]").astype("int64")
                               if coord == "time" else values.astype(float))
            if not (np.all(ordered > 0) or np.all(ordered < 0)):
                raise FeatureValidationError(
                    f"{year}: {coord} must be strictly monotonic"
                )

    expected_dates = pd.date_range(f"{year}-07-15", periods=EXPECTED_DAYS).values.astype("datetime64[D]")
    actual_dates = np.asarray(ds["time"].values).astype("datetime64[D]")
    if not np.array_equal(actual_dates, expected_dates):
        raise FeatureValidationError(f"{year}: expected dates July 15–August 13.")

    for feature in FEATURES:
        if feature not in ds.data_vars:
            raise FeatureValidationError(f"{year}: missing feature {feature}")
        variable = ds[feature]
        if tuple(variable.dims) != ("time", "lat", "lon"):
            raise FeatureValidationError(
                f"{year}: {feature} dimensions must be (time, lat, lon)"
            )
        values = np.asarray(variable.values, dtype=np.float64)
        if np.isinf(values).any():
            raise FeatureValidationError(f"{year}: {feature} contains infinity")
        finite = values[np.isfinite(values)]
        if feature in LOG1P_FEATURES and finite.size and np.any(finite < 0):
            raise FeatureValidationError(
                f"{year}: {feature} has negative values; log1p is not valid."
            )


def validate_feature_frame(frame: pd.DataFrame) -> None:
    missing_cols = [c for c in (*REQUIRED_METADATA, *FEATURES) if c not in frame.columns]
    if missing_cols:
        raise FeatureValidationError(f"Missing columns: {missing_cols}")
    if frame.empty:
        raise FeatureValidationError("Feature frame is empty.")
    if frame[list(REQUIRED_METADATA)].isna().any().any():
        raise FeatureValidationError("Metadata contains missing values.")
    if frame.duplicated(list(REQUIRED_METADATA)).any():
        raise FeatureValidationError("Duplicate year/date/latitude/longitude keys.")
    numeric_year = pd.to_numeric(frame["year"], errors="coerce")
    if numeric_year.isna().any() or not np.equal(numeric_year, np.floor(numeric_year)).all():
        raise FeatureValidationError("Year metadata must contain finite integer years.")
    years = set(numeric_year.astype(int))
    if not years.issubset(set(YEARS)):
        raise FeatureValidationError(f"Unexpected years in feature frame: {sorted(years - set(YEARS))}")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    if dates.isna().any() or not dates.equals(dates.dt.normalize()):
        raise FeatureValidationError("Date metadata must contain valid normalized dates.")
    if not np.array_equal(dates.dt.year.to_numpy(), numeric_year.astype(int).to_numpy()):
        raise FeatureValidationError("Year metadata does not agree with date metadata.")
    month_day = dates.dt.strftime("%m-%d")
    if not month_day.between("07-15", "08-13").all():
        raise FeatureValidationError("Dates fall outside July 15–August 13.")
    for coordinate in ("latitude", "longitude"):
        coord_values = pd.to_numeric(frame[coordinate], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(coord_values).all():
            raise FeatureValidationError(f"{coordinate} metadata must be finite numeric values.")
    values = frame.loc[:, FEATURES].to_numpy(dtype=np.float64)
    if np.isinf(values).any():
        raise FeatureValidationError("Feature matrix contains infinite values.")
    for feature in LOG1P_FEATURES:
        finite = values[:, FEATURES.index(feature)]
        finite = finite[np.isfinite(finite)]
        if finite.size and np.any(finite < 0):
            raise FeatureValidationError(f"{feature} contains negative values.")


def build_feature_registry(screening: pd.DataFrame, yearly: pd.DataFrame,
                           integrated: pd.DataFrame) -> pd.DataFrame:
    """Join existing evidence into a registry; do not auto-exclude features."""
    required_screen = {"variable", "units", "valid_observations",
                       "missing_observations", "missing_percentage",
                       "standard_deviation", "constant", "years_with_data"}
    if not required_screen.issubset(screening.columns):
        raise FeatureValidationError(
            f"Screening table missing columns: {sorted(required_screen - set(screening.columns))}"
        )
    if not {"year", "variable", "missing_percentage", "valid_observations"}.issubset(yearly.columns):
        raise FeatureValidationError("Yearly screening table schema is incomplete.")
    if "variable" not in integrated.columns:
        raise FeatureValidationError("Integrated feature evidence lacks variable column.")

    screen = screening.set_index("variable")
    integ = integrated.set_index("variable")
    records = []
    for feature in FEATURES:
        if feature not in screen.index or feature not in integ.index:
            raise FeatureValidationError(f"Missing screening evidence for {feature}")
        annual = yearly[yearly["variable"] == feature]
        if len(annual) != len(YEARS) or set(annual["year"].astype(int)) != set(YEARS):
            raise FeatureValidationError(f"{feature}: expected one screening row per year.")
        row = screen.loc[feature]
        if isinstance(row, pd.DataFrame):
            raise FeatureValidationError(f"Duplicate screening rows for {feature}")
        integrated_row = integ.loc[feature]
        if isinstance(integrated_row, pd.DataFrame):
            raise FeatureValidationError(f"Duplicate integrated evidence rows for {feature}")
        records.append({
            "feature": feature,
            "meaning": MEANINGS[feature],
            "units": str(row["units"]),
            "cloud_scope": "total" if "_total_" in feature else "high",
            "selection_reason": SELECTION_REASON,
            "total_observations": int(row["valid_observations"] + row["missing_observations"]),
            "valid_observations": int(row["valid_observations"]),
            "missing_observations": int(row["missing_observations"]),
            "missing_percentage": float(row["missing_percentage"]),
            "maximum_annual_missing_percentage": float(annual["missing_percentage"].max()),
            "standard_deviation_original_units": float(row["standard_deviation"]),
            "constant": bool(row["constant"]),
            "years_with_data": int(row["years_with_data"]),
            "transformation": "log1p then StandardScaler" if feature in LOG1P_FEATURES else "StandardScaler",
            "scaling": "StandardScaler",
            "high_correlation_partner_count": int(integrated_row.get("high_correlation_partner_count", 0)),
            "high_correlation_partners": str(integrated_row.get("high_correlation_partners", "")),
            "automatic_exclusion": False,
            "review_status": "ESTABLISHED_MONSOON_EVIDENCE; CROSS_SEASON_REVIEW_PENDING",
        })
    return pd.DataFrame.from_records(records)


def validate_registry(registry: pd.DataFrame) -> None:
    if len(registry) != len(FEATURES):
        raise FeatureValidationError(f"Expected {len(FEATURES)} registry rows.")
    if registry["feature"].tolist() != list(FEATURES):
        raise FeatureValidationError("Registry feature order/schema mismatch.")
    if registry["feature"].duplicated().any():
        raise FeatureValidationError("Registry contains duplicate features.")
    if registry["automatic_exclusion"].astype(bool).any():
        raise FeatureValidationError("No automatic feature exclusions are permitted.")
    numeric = registry[["missing_percentage", "maximum_annual_missing_percentage",
                        "standard_deviation_original_units"]].to_numpy(dtype=float)
    if not np.isfinite(numeric).all():
        raise FeatureValidationError("Registry contains non-finite evidence.")
    if ((registry["missing_percentage"] < 0) | (registry["missing_percentage"] > 100)).any():
        raise FeatureValidationError("Missing percentage must be between 0 and 100.")
