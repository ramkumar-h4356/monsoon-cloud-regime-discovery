M18.4 — Missingness Treatment Experiments

PACKAGE CONTENTS
  src/06_feature_engineering/missingness_treatments.py
  tests/test_missingness_treatments.py
  docs/methodology/M18_4_missingness_treatment_experiments.md

INSTALL
1. Close any editor that may be modifying these files.
2. Extract this ZIP into the root of:
   D:\Project Simulator\monsoon_cloud_research
3. Allow folders/files to merge. The ZIP paths are project-relative.
4. This package assumes M18.3 is already present:
   src/06_feature_engineering/missingness_classifier.py

TEST
From the project root, run:
   python -m pytest tests/test_missingness_treatments.py -v

Do not commit until the tests pass. The package does not include or modify raw
CERES NetCDF datasets. CA-B is screening-only; use assess_ca_b_feature rather
than attempting to fit an imputation model for CA-B.
