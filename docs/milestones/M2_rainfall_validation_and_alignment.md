# M2 — Rainfall Preparation and Alignment Validation

## Purpose

Strengthen the Established Monsoon rainfall data contract without changing the scientific role of rainfall. IMD rainfall remains an independent association/validation variable and is not a cloud-clustering input.

## Existing workflow retained

The existing project continues to prepare daily IMD rainfall for July 15–August 13, 2010–2021, select the CERES 32 × 30 grid using exact coordinates, preserve missing observations, and match cloud assignments by year, date, latitude and longitude. No interpolation, regridding, zero-filling or temporal aggregation is introduced.

## Added validation module

`src/02_validation/established_monsoon_rainfall_validation.py` centralizes checks for:

- one-dimensional, finite, unique, strictly monotonic coordinates;
- expected coordinate counts;
- exact 30-day seasonal date windows, date uniqueness, normalized timestamps and year consistency;
- numeric rainfall values, infinite values and negative finite rainfall;
- daily rainfall units expressed as mm or an accepted spelling equivalent;
- assignment schema, expected years, date window, finite coordinates, duplicate join keys and valid integer cluster labels;
- explicit warnings for missing cluster-year combinations;
- matched-table uniqueness and valid rainfall;
- non-empty comparison tables, required schemas, duplicate summary keys, finite numeric metrics and nonnegative support counts.

## New preflight runner

Run from the repository root:

```powershell
python src/02_validation/validate_established_monsoon_rainfall_pipeline.py
```

The runner validates all 12 prepared annual rainfall NetCDF files against the fixed cluster assignment table. It verifies the exact daily window and 32 × 30 coordinate grid, then constructs valid rainfall keys from finite observations and performs a one-to-one exact-key join. It also validates the existing matched-observation table against a freshly recomputed join and checks the existing pooled, annual, within-cell, and period-comparison result tables for required schemas, duplicate keys, empty outputs, non-finite metrics and invalid support counts.

It writes two new compact audit tables:

- `reports/data_quality/established_monsoon_rainfall_pipeline_validation.csv`
- `reports/data_quality/established_monsoon_rainfall_cluster_year_coverage.csv`

The runner refuses to overwrite either report. It reads existing data only and does not alter NetCDF files, assignment tables or existing analysis outputs. The established comparison periods are unequal in duration (2010–2016: seven years; 2017–2021: five years); the existing period outputs and support-sensitivity table are validated but are not reinterpreted as equal-duration samples.

## Missingness and support interpretation

A cloud assignment without a finite rainfall observation is not treated as a zero-rainfall observation. It is counted as an unmatched assignment. Valid rainfall cells without a corresponding cloud assignment are also counted separately. Missing cluster-year combinations are recorded as support warnings rather than silently treated as zero prevalence.

## Tests

Run the unit tests from the repository root:

```powershell
python -m pytest tests/test_established_monsoon_rainfall_validation.py -q
```

The tests cover coordinate ordering and uniqueness, date windows and year consistency, rainfall missing/negative/infinite values, units, assignment duplicates and cluster labels, cluster-year warnings, exact finite-key extraction, matched records and summary-table validation. Static schema validation was also checked against the compact pooled, annual, within-cell and period result tables in the uploaded source archive; all 11 checked tables passed that static check. Runtime validation against the local NetCDF files remains to be executed by the user.

## Scope boundary

This milestone adds a reusable validation contract and a read-only preflight audit. It does not regenerate the rainfall NetCDF files or replace existing rainfall association findings. The preflight runner must be executed against the user's local data before the M2 runtime validation can be declared complete.
