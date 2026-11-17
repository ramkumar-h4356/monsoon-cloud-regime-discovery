# Methodology: Initial CERES Feature Screening

## Objective

Describe the statistical distributions and data completeness of
the 45 physical CERES cloud variables before feature selection.

## Data

- CERES daily aggregates for 2010–2021.
- July 15 through August 13 for each year.
- 30 days × 32 latitude cells × 30 longitude cells per year.
- 12 years and 45 physical variables.

## Exclusions

The `_valid_hour_count` variables are diagnostics and are not
physical cloud features. Rainfall and climate indices are not
included as clustering inputs.

## Statistics

For each variable, calculate valid and missing observation counts,
missing percentage, minimum, maximum, mean, median, standard
deviation, percentiles (1, 5, 25, 75, 95, 99), interquartile range,
zero count, zero percentage and exact-constant status.

The same statistics are calculated separately for each year.

## Missing data and ranges

Non-finite missing values are excluded from distribution statistics
but included in missingness counts. No imputation or zero filling
is performed. Observations are checked against the declared
valid_min and valid_max metadata.

## Interpretation

This is descriptive screening, not final feature selection.
No variable is automatically removed based on missingness,
zero frequency, range, or variability. Correlation, redundancy,
physical interpretation, and cross-season consistency are
separate decision stages.

## Aggregation

The existing arithmetic daily aggregates are analysed. The
area-weighted phase alternative remains a separate sensitivity
question and is not substituted in this screening.
