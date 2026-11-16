# M4 — PCA Implementation and Validation

## Scope
M4 applies Principal Component Analysis separately to the M3 Group B baseline
and log-sensitivity matrices for the Established Monsoon period (2010–2021).

## Inputs
- `established_monsoon_group_B_baseline.npz`
- `established_monsoon_group_B_log_sensitivity.npz`
- `established_monsoon_group_B_metadata.csv`
- `established_monsoon_group_B_feature_registry.csv` (retained as M3 evidence;
  PCA feature order is enforced from the M3 JSON manifest and NPZ arrays)
- `established_monsoon_group_B_manifest.json`

Expected matrix shape: 290,355 observations × 14 features.

## Method
- Use the M3 standardized matrices without re-fitting a scaler.
- Fit independent `sklearn.decomposition.PCA(svd_solver="full")` models.
- PCA internally centers each input matrix.
- Retain all 14 components in the output.
- Calculate explained variance, cumulative explained variance, loadings,
  squared-loading feature contributions, and 80/90/95% component thresholds.
- Preserve observation row alignment in compressed score files by storing
  year, date, latitude and longitude arrays alongside scores.
- Compare baseline and log-sensitivity loading subspaces using principal angles
  for dimensions 2, 3 and 5.

## Interpretation cautions
- PCA is descriptive dimensionality reduction, not a predictive evaluation.
- The M3 full-period scaling scope is retained; no held-out predictive claims
  are made.
- Component signs are arbitrary.
- Same-index component loading similarity is descriptive only. Principal
  angles compare subspaces and are more appropriate when component axes rotate.
- Feature contributions are squared loadings expressed as percentages per
  component; they are not causal effects.
- High correlation or a large loading does not make distinct physical variables
  interchangeable.
- The 14-feature Group B set remains provisional and is not cross-season
  validated.

## Outputs
All generated files are written to:
`data/processed/clustering/established_monsoon/m4_pca/`

The output directory is ignored by the repository's existing `data/` rule.
No M3 input or existing clustering result is overwritten.

## Validation
The implementation validates numeric finiteness, matrix shape, exact feature
order, metadata row count and required observation identifiers before fitting.
Unit tests use synthetic data and do not substitute for the user's full
290,355-row local execution.
