# M18.4 — Missingness Treatment Experiments

## Purpose

Implement reusable, training-only missingness treatment functions for the CERES cloud-feature workflow. This milestone does not read or modify source NetCDF files and does not fit scaling parameters.

## Property strategies

- **MD-A:** Fit the median using finite training property values where the matching cloud area is positive. Use it for structural-absence and residual-missing property values. For unknown cloud availability, use the overall finite training-property median and retain a separate unknown-availability indicator.
- **MD-B:** MD-A plus a residual-missingness indicator.
- **SA-A:** Same imputation values as MD-A, without a structural-absence indicator.
- **SA-B:** Same imputation values as MD-A, with a structural-absence indicator.
- **MD-C:** Feature-level screening based on residual missingness. It is not an imputation transformer.

## Cloud-area strategies

- **CA-A:** Fit the median of finite training cloud-area values. Impute missing cloud-area values with that median and emit an availability-missing indicator. Zero is preserved as a valid observed value.
- **CA-B:** Feature-level screening based on cloud-area missingness. It is not an imputation transformer.

## Screening bands

- Missingness <= 5%: `LOW` / `INCLUDE`.
- Missingness > 5% and <= 20%: `MODERATE` / `REVIEW`.
- Missingness > 20%: `HIGH` / `EXCLUDE_PRIMARY`.

These are the project's predeclared heuristic screening bands, not universal scientific thresholds. MD-C uses residual property missingness; CA-B uses cloud-area missingness.

## Leakage prevention

`fit_*` functions must be called only on the training partition. Apply the resulting model with `transform_*` to validation/test partitions. Transformation functions never calculate medians from the data being transformed.

## Outputs and limitations

All feature arrays are returned as float32, with missingness indicators as uint8. The original input arrays are not modified. This module provides treatment primitives; M18.5 handles scaling, and later orchestration handles experiment-level dataset processing.
