# M3 Methodology: Established Monsoon Feature Preparation

## Scope

This milestone formalizes the existing 14-variable Group B feature set for the Established Monsoon component (2010–2021; July 15–August 13; 32 × 30 spatial grid).

## Feature selection status

Group B is retained as the project's provisional working feature set. The existing evidence reports 84.01% pooled complete-case spatial coverage for Group B. This selection balances total-cloud and high-cloud properties while retaining more spatial support than the broader Group C set. It is not claimed to be universally optimal, and cross-season comparability remains pending.

## Registry

The generated registry records each feature's descriptive meaning, units taken from the existing screening evidence, cloud scope, selection rationale, pooled missingness, maximum annual missingness, original-unit standard deviation, year coverage, transformation, scaling, and high-correlation partners.

Correlation partners are evidence for review, not automatic reasons to remove a feature. No feature is automatically excluded by the registry.

## Missingness and matrix construction

The preparation workflow validates all 12 annual daily datasets, the 30-day date window, coordinate uniqueness/order, consistent 32 × 30 grid, expected feature dimensions, and finite/non-negative constraints for variables transformed with log1p.

The model-ready matrices use complete cases across all 14 features. No imputation and no zero replacement are performed. Metadata (year, date, latitude, longitude) is retained in a separate aligned table.

## Transformations

Two descriptive unsupervised representations are prepared:

1. Baseline: StandardScaler applied to the 14 original variables.
2. Log sensitivity: log1p applied to `cldtau_total_1h`, `iwp_total_1h`, `cldtau_high_1h`, and `iwp_high_1h`, followed by StandardScaler.

The four log-transformed variables are checked for negative finite values before transformation.

## Scaling and leakage

To preserve comparability with the existing full-period clustering baseline, the default descriptive workflow fits each scaler on the full 2010–2021 complete-case matrix. This is not a held-out predictive evaluation. Any future train/test, forecasting, or predictive evaluation must fit imputation/transformation/scaling parameters on training/reference data only and apply the fitted parameters to held-out data.

## Outputs

The M3 script writes to a new directory, leaving the existing Group B matrices untouched:

`data/processed/clustering/established_monsoon/m3_feature_preparation/`

It creates baseline and log-sensitivity NPZ matrices, aligned metadata, a feature registry, and a JSON manifest recording row counts, feature order, transformations, and scaling scope.
