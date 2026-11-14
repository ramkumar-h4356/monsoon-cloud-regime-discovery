# Established Monsoon: Daily CERES Temporal Aggregation

## 1. Scope

This methodology defines the conversion of hourly CERES SYN1deg Edition 4.2
(Edition 4B) data into daily gridded data for the established-monsoon period.

- Years: 2010–2021 inclusive
- Seasonal window: 15 July through 13 August
- Expected hourly records: 720 per year
- Expected daily records: 30 per year
- Expected hourly records per calendar day: 24
- Spatial domain: 6°N–38°N, 68°E–98°E
- Grid: 32 latitude × 30 longitude cells
- Variables: all 45 available cloud-property variables

The original hourly NetCDF files are immutable inputs. This stage must not
modify or replace them.

## 2. Input validation

Before aggregation, the processing pipeline must verify:

1. All 12 expected yearly files exist.
2. Each file contains the expected 720 hourly records.
3. Every calendar day has exactly 24 hourly records.
4. The time coordinate is strictly increasing.
5. The expected 45 variables are present.
6. The spatial coordinates and grid dimensions are consistent.
7. Infinite values are absent.

The source time coordinate contains small sub-hour variations associated
with its stored floating-point precision. The pipeline must group records
by their calendar date rather than round or interpolate timestamps to exact
hour boundaries.

## 3. Daily aggregation rule

For each variable and grid cell, calculate the arithmetic mean of its
available hourly observations within each calendar day.

For a daily grid-cell value:

    daily_mean = sum(valid hourly values) / number of valid hourly values

Missing observations are excluded from the sum and denominator. Missing
values must not be replaced with zero, and no imputation or interpolation
is performed.

The primary completeness requirement is at least 18 valid hourly observations
out of 24 (75%).

If fewer than 18 valid hourly observations are available, the daily value
must remain NaN.

## 4. Completeness and sensitivity analysis

For every variable, grid cell, and day, retain the number of valid hourly
observations.

The primary daily product retains values with at least 18 valid hours.
The valid-hour counts also allow retention to be evaluated under a strict
24-of-24-hour completeness criterion.

The current processing output does not generate a separate daily dataset
masked at 24 valid hours. The 24-hour result is therefore a completeness-
retention sensitivity analysis, not a second strict-threshold daily product.
It does not replace the primary 18-hour product.

A daily value calculated from 18–23 observations is a partially observed
daily mean, not a complete 24-hour daily mean. This distinction must be
preserved in metadata and subsequent interpretation.

## 5. Variable-specific handling

All 45 variables are aggregated using the same temporal arithmetic-mean
operation. Their scientific meanings and units are retained.

| Variable family | Temporal operation | Notes |
|---|---|---|
| cldarea | Arithmetic mean | Cloud area fraction |
| cldtau | Arithmetic mean | Cloud visible optical depth |
| lwp | Arithmetic mean | Liquid water path |
| iwp | Arithmetic mean | Ice water path |
| cldpress_top | Arithmetic mean | Cloud top pressure |
| cldpress | Arithmetic mean | Cloud effective pressure |
| cldtemp | Arithmetic mean | Cloud effective temperature |
| cldhght | Arithmetic mean | Cloud effective height |
| cldphase | Arithmetic mean | Retain as a continuous-valued indicator |

The cloud-phase variable has observed fractional values within the range 1–2.
It must not be rounded, converted into integer categories, or aggregated
using a categorical mode.

The supplied total-layer variables must be retained as provided. They must
not be reconstructed from the four individual cloud layers.

No variable is excluded from daily aggregation solely because its
missingness is high. Feature selection and suitability for clustering are
separate research decisions.

## 6. Scientific interpretation and limitations

The daily aggregation is a temporal operation on already gridded hourly
fields. Cloud-fraction weighting or logarithmic optical-depth weighting
must not be applied again automatically during this step.

NASA documentation available during methodology development describes
Edition 4A processing conventions. These provide context but do not by
themselves establish every exact daily aggregation detail for Edition 4.2.
The arithmetic-mean procedure here is the project's explicit temporal
aggregation rule and must not be described as an exact reproduction of
the complete NASA Edition 4.2 processing algorithm.

Missingness varies substantially across variables and cloud layers.
Some year-wise coverage patterns change around 2017–2018 even though the
inspected product and variable metadata remain consistent. The cause has
not been established.

Changes in data availability must not be interpreted as changes in actual
cloud occurrence. Coverage information must remain available for later
feature selection, temporal comparisons, and interpretation.

## 7. Output expectations

The daily processing stage must produce:

1. Daily aggregated values for all 45 variables.
2. Per-variable, per-grid-cell, per-day valid-hour counts.
3. Daily time coordinates representing the source calendar dates.
4. Metadata documenting the input product, aggregation operation,
   completeness threshold, study period, and spatial domain.
5. Validation reports covering record counts, dimensions, coordinates,
   missingness, and numerical consistency.

Processed NetCDF outputs belong under:

    data/processed/ceres_daily/

They are derived data and must not be committed to Git.

Lightweight scripts, methodology documents, validation reports, and
experiment logs should be tracked in Git.

## 8. Reproducibility requirements

The processing script must:

- Derive project paths from its own location.
- Avoid modifying source hourly files.
- Refuse to silently overwrite existing outputs.
- Use deterministic grouping and aggregation.
- Validate the exact 45-variable schema and July 15–August 13 date window.
- Preserve variable names, units, and relevant metadata.
- Record the completeness threshold in output metadata.
- Report the number of valid and rejected daily grid-cell observations.
- Support independent validation of the 18-hour and 24-hour criteria.
