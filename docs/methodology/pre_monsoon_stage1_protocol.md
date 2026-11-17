# Pre-monsoon Phase 2: Stage 1 protocol

Stage 1 prepares data and audits eligibility. It fits no imputer, scaler, PCA,
t-SNE, clustering algorithm, or other estimator and does not evaluate a holdout
model. Phase 1 artifacts remain authoritative and are not regenerated.

## Observation and target population

One observation is one CERES SYN1deg Edition 4.2 hourly grid cell. Coordinates
and original nanosecond timestamps are retained. An auxiliary floored hourly
slot handles the documented midpoint timestamp jitter without rounding into
the next hour. Array stacking order is time, latitude, longitude. An observation
ID combines season, original timestamp, latitude and longitude. Annual NetCDFs
retain all rows; sample manifests store explicit IDs and flat indices.

The primary discovery population is valid cloudy observations with positive
total cloud area and valid total optical depth and cloud-top pressure. Exact
zero valid cloud area is recorded separately as clear sky. Positive-area rows
with unavailable optical/vertical properties remain incomplete cloudy, not
clear sky. Missing or invalid area remains unknown. The four statuses are
mutually exclusive and sum to the original population. Near-clear positive
cloud area remains eligible if its properties are valid; threshold sensitivity
is reserved for a later, development-only experiment.

The initial estimand weights grid-cell hours equally. This is not equal Earth
area: cosine-latitude-weighted summaries/fitting are a later sensitivity. It is
not an individual-cloud classification or a joint optical-depth/pressure
histogram. Spatial transfer to unseen locations is not tested.

## Features and missingness

| Input | Input units | Fixed transform | Output |
|---|---|---|---|
| cldarea_total_1h | percent | divide by 100 | cloud_area_fraction (1) |
| cldtau_total_1h | dimensionless | log1p | log1p_optical_depth (1) |
| cldpress_top_total_1h | hPa | identity | cloud_top_pressure_hpa (hPa) |

Coverage, optical thickness, and vertical position are complementary physical
axes. Phase 1 recommends these families. Top and effective pressure correlate
at about 0.998 in the saved exploratory sample, so effective pressure,
temperature, and height are excluded to avoid duplicate vertical weighting.
Phase remains diagnostic: intermediate values are aggregate indices, not
categorical liquid/ice or a validated ice fraction.

IWP and LWP are excluded from the primary model. The full Phase 1 reports show
low IWP missingness of 95.598%, high LWP 91.453%, total IWP 19.227%, and total
LWP 8.436%. Endpoint audits link IWP unavailability to phase exactly 1. These
are condition-dependent retrievals; no missing water path becomes a zero.
Layer variables also have substantial selective availability, including low
cloud area. No layer-sum or absent-layer assumptions are introduced.

CF decoding, encoded fill values, and the CERES -999 sentinel are handled.
NaN/sentinels are missing; infinities and finite out-of-contract-range values
are invalid. Both masks survive for each selected input. Invalid values become
NaN before transformation. Bounds are physical contract values, not estimated
quantiles. No clipping, imputation, centering, or learned scaling occurs.
Raw selected values and fixed transformed values are stored. Only the three
ordered outputs in the contract may become future model features; missingness
flags, eligibility, timestamps and coordinates are audit metadata.

Complete cases may still select a biased cloudy population. Retention is
audited by year, UTC hour, latitude, grid cell, cloud-area band and aggregate
phase group in training/development. All tables retain denominators. A later
imputation sensitivity requires scientific justification and training-only
fitting. Missingness indicators are not automatically distance features.

## Whole-year separation

- Training: 2010-2016 (7 years; 4,838,400 unfiltered rows).
- Development: 2017-2018 (2 years; 1,382,400 unfiltered rows).
- Holdout: 2019-2021 (3 years; 2,073,600 unfiltered rows).

Every hour and location from a year belongs to one partition. No random
grid-cell/hour train-test split is allowed: it would mix nearby locations and
adjacent weather observations. Complete seasons are separated by long calendar
gaps. Dependence within each season remains; later uncertainty/stability must
use year/day blocks, not independent-row bootstrap. Shared geography across
years is intentional for temporal generalization over this domain.

Later tuning may use forward folds wholly within 2010-2016 (for example,
2010-2013 -> 2014 and 2010-2014 -> 2015-2016), followed by development checks in
2017-2018. Each fold must fit all learned transforms on its training portion.
Do not treat a pipeline fitted on all training years as valid for earlier
within-training folds. Before final holdout evaluation, freeze all choices;
any refit on 2010-2018 must be explicitly recorded as a separate final fit.

Stage 1 holdout access is limited to source/schema validation, primary validity
and annual eligibility counts plus applying fixed arithmetic transforms. No
holdout sample, distribution profiles, IWP/phase exploration, fitted statistics,
or model evaluation is produced. Counts cannot be used to tune the feature
set. Phase 1 already explored all years, so this is a Phase 2 fitting/tuning
holdout, not historically unseen data. Three holdout years provide limited
independent temporal replication.

## Reproducibility and seasonal compatibility

Full eligible populations are retained; the manifest additionally selects up
to 10,000 eligible rows per training/development year, without replacement,
using NumPy SeedSequence([42, year]). Membership is reproducible and independent
of file traversal order and holdout values. This is a computational sample,
not a claim of statistical independence. No holdout sampling occurs.

The explicit 45-variable registry and ordered primary features are shared
across pre-, established-, and post-monsoon windows. Schema validation enforces
units, dtype, full hourly coverage and grid consistency; transposed arrays are
normalized explicitly. Other seasons require their own audits/configuration;
the current CLI deliberately permits only pre-monsoon. Future fitted objects
must carry season and feature-contract hash and be fitted separately. PC axes
and cluster IDs from separate seasonal fits will not be inherently comparable.

## Commands and new artifacts

From the repository root, using the existing parent environment:

```powershell
& '..\.venv\Scripts\python.exe' -B -m unittest discover -s tests -v
& '..\.venv\Scripts\python.exe' -B src/06_feature_engineering/prepare_pre_monsoon.py --run-id stage1_v1
```

Tests use standard-library unittest plus the existing scientific packages;
pytest and scikit-learn are not required. No Phase 1 writer is imported.

- `data/processed/model_ready/phase2/pre_monsoon/<run_id>/`: twelve prepared NetCDFs.
- `reports/phase2/pre_monsoon/<run_id>/`: counts, missingness, retention strata,
  spatial retention, development IWP/phase audit, sample manifest, generated
  report, source/output hashes, configuration, package versions, and Git state.

Existing run directories cause failure rather than overwrite. Missing or
unexpected inputs, changed units/schema, incomplete hours, and mismatched grids
fail preflight. A failed run remains marked incomplete; use a new run ID after
resolving the cause. Existing code/report/result files and all source NetCDFs
are hashed before/after to verify preservation. NetCDF source files remain
ignored by Git, so manifests provide provenance for local datasets. No commit,
push, merge, or Git configuration/history change is part of this workflow.

The absence of established/post-monsoon files locally prevents live validation
for those seasons even though saved Phase 1 reports describe 36 passing files.
Stage 2 requires separate approval and an appropriate pinned modeling environment.
