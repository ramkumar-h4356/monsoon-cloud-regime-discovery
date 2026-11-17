M18.5 — Leakage-Safe Imputation and Scaling Engine

PACKAGE CONTENTS
  src/06_feature_engineering/feature_scaling.py
  tests/test_feature_scaling.py
  docs/methodology/M18_5_leakage_safe_imputation_and_scaling.md

INSTALL
1. Extract this ZIP directly into:
   D:\Project Simulator\monsoon_cloud_research
2. Allow the project folders to merge.
3. This package does not modify source CERES NetCDF files or existing M18 modules.

DEPENDENCIES
  numpy
  scikit-learn

TEST
From the project root, run:
  python -m pytest tests/test_feature_scaling.py -v

EXPECTED
  23 tests should pass.

USAGE OVERVIEW
- Fit only on training rows using fit_feature_scaler().
- Transform validation/test rows using transform_feature_scaler().
- Use scaler="robust" for the baseline and scaler="standard" for sensitivity.
- Use weighting="equal" for equal-feature weighting or
  weighting="family_balanced" with registry-derived family labels.
- Set scale_mask=False for binary missingness indicators that must remain 0/1.
- Save parameters using save_scaling_manifest().

Do not commit until the tests pass. Raw datasets are not included.
