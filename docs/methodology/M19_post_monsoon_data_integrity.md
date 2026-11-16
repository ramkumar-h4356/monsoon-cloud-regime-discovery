# M19 methodology: post-monsoon data integrity

## Purpose

Establish whether the selected 2010–2021 post-monsoon inputs are structurally and numerically suitable for later exploratory analysis. The audit is read-only and records provenance through configured source paths and filenames.

## CERES temporal validation

The selected interval is October 15 through November 13 inclusive. It contains 30 calendar days and therefore 720 hourly observations. CERES time coordinates observed during source inspection are centered near HH:30, with small seconds-level jitter. Validation therefore checks 720 records, uniqueness, monotonic order, all 30 dates represented by 24 records each, and consecutive intervals within the configured tolerance. It does not round or rewrite timestamps.

## CERES spatial and variable validation

Each annual file is expected to contain 32 latitude centres, 30 longitude centres and 45 data variables. Coordinate checks include finite values, uniqueness, ascending order and configured broad geographic bounds. Each data variable is inspected for dimensions, shape, dtype, units, finite/missing counts, extrema and metadata valid-range violations. Metadata ranges are diagnostics; violations are reported, never clipped or corrected automatically.

## IMD rainfall validation

Each annual file is expected to contain daily records for the complete calendar year (365 or 366 days), ordered and unique, with one-day spacing. Latitude and longitude are audited independently from CERES. The IMD grid is not assumed to have the same shape or ordering as CERES. Later association must use coordinate-value intersection and documented temporal aggregation, not array indices. Negative finite rainfall values are flagged for investigation.

## Climate-index provenance

Original NOAA files are authoritative. DMI `-9999` is treated as a missing sentinel for counting, not as a physical anomaly. RONI is retained as a sequence of rolling three-month seasons; seasonal labels are not reinterpreted as independent months. Processed CSVs are identified as reconciliation targets, but this version does not declare source-to-processed numerical equality without a validated mapping.

## Missingness and decision rules

NaN/non-finite values, encoded fill values, and physical-range violations are reported separately where metadata permits. Missing observations are not imputed. `PASS` means the specific implemented check was met; `FAIL` means a check was evaluated and violated; `NOT EVALUATED` means evidence or a supported mapping was unavailable. Overall readiness is blocked when a required source family is absent, fails, or lacks a required validation.

## Limitations

The audit does not establish scientific validity of every CERES retrieval, guarantee spatial representativeness, resolve all product-specific quality flags, or validate downstream cloud–rainfall associations. It does not regrid, interpolate, or alter source files. A passing integrity audit is necessary but not sufficient for scientific interpretation.
