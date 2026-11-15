# M18.5 — Leakage-Safe Imputation and Scaling Engine

## Purpose

This milestone adds a reusable scaler for the imputed feature matrices produced by M18.4. It supports the predeclared robust-scaling baseline, standard-scaling sensitivity, and equal-feature versus family-balanced weighting.

## Input contract

- Input is a 2D numeric matrix: samples × features.
- Missing values must already have been handled by the selected M18.4 treatment. The scaler rejects NaN and infinity rather than silently imputing.
- `feature_names` must identify every matrix column in exact order and contain no duplicates.
- `feature_families` supplies the registry-derived family for each continuous feature when family-balanced weighting is evaluated.
- Binary missingness/availability indicators may be kept as 0/1 by setting their `scale_mask` entry to `False`. Such columns are not included in family counts or family weights.

## Supported scaling

### Robust baseline

`RobustScaler` is fitted on the training partition, using median centering and the 25th–75th percentile range (IQR). This is the primary candidate because cloud properties may be skewed and contain outliers.

### Standard sensitivity

`StandardScaler` is fitted on the same training partition using the training mean and population standard deviation. This is a sensitivity comparison, not an automatic replacement for the robust baseline.

## Feature weighting

- `equal`: multiplier 1 for every feature after scaling.
- `family_balanced`: for each scaled continuous feature in a family containing `n_f` features, apply multiplier `1 / sqrt(n_f)`. Therefore the sum of squared multipliers within each family is 1. This normalizes family-level squared weighting so a larger family does not receive more total weight merely because it contains more variables.

Family-balanced weighting is a sensitivity experiment. It does not prove that different physical families are equally important, and robust-scaled features can still have different variances because of distribution shape and tails.

## Leakage safeguards

1. Call `fit_feature_scaler()` with training rows only.
2. Apply the returned model to validation/test rows using `transform_feature_scaler()`.
3. Do not call `fit_feature_scaler()` separately on validation/test data.
4. The transform checks the exact feature-name order to prevent column-order mistakes.
5. The model records training sample count, feature order, center, scale, family labels, weighting multipliers and fit scope.

For a final descriptive model fitted to the entire 2010–2021 study period, the manifest must explicitly record that the full-period matrix was used as the final model's fitting scope. That is distinct from temporal-holdout experiments, which must fit on training years only.

## Output

`transform_feature_scaler()` returns a finite `float32` matrix. The optional JSON manifest records the scaler and weighting parameters without serializing executable Python objects.

## Important limitation

This module does not perform chunked out-of-core fitting or create full model-ready datasets. M18.6/M18.7 orchestration will decide training partitions, manage chunks, and integrate feature-set/treatment combinations. The M18.5 module defines and tests the scaling behavior those later steps must use.
