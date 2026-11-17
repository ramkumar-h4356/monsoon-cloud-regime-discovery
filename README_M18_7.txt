M18.7 — FULL DATASET PROCESSING

PACKAGE CONTENTS
  config/m18_7_processing_plan.json
  src/06_feature_engineering/process_m18_7_datasets.py
  tests/test_m18_7_processor.py
  docs/methodology/M18_7_full_dataset_processing.md

PREREQUISITES ALREADY IN YOUR PROJECT
  src/06_feature_engineering/missingness_classifier.py       (M18.3)
  src/06_feature_engineering/missingness_treatments.py       (M18.4)
  src/06_feature_engineering/feature_scaling.py              (M18.5)
  src/06_feature_engineering/experiment_orchestrator.py      (M18.6)
  config/m18_experiment_orchestration.json                  (M18.6)
  reports/feature_engineering/feature_set_registry.csv
  reports/feature_engineering/m18_experiment_registry.csv
  reports/feature_engineering/m18_7_processing_preflight.json
  data/interim/ceres_seasonal/<season>/*.nc

DEPENDENCIES
  numpy, pandas, xarray, scikit-learn, netCDF4, pytest
  netCDF4 is required for compressed NetCDF4 output.

INSTALL
  Extract this ZIP directly into:
    D:\Project Simulator\monsoon_cloud_research
  Allow the config, src, tests, and docs folders to merge.
  Do not move individual files manually.

STEP 1 — TEST THE PROCESSOR
  python -m pytest tests/test_m18_7_processor.py -v

STEP 2 — RECALCULATE STORAGE INCLUDING INDICATORS
  python "src/06_feature_engineering/process_m18_7_datasets.py" --estimate

The previous preflight estimate of 63.03 GiB counted feature and missingness-code
arrays but not all treatment indicators. The processor's updated estimate for the
current registry is approximately 79.30 GiB uncompressed, with a recommended
free-space threshold of approximately 95.57 GiB. The command checks current disk
space; do not proceed if it reports insufficient space.

STEP 3 — RUN ONE PILOT EXPERIMENT ONLY
  python "src/06_feature_engineering/process_m18_7_datasets.py" --pilot

This selects the Stage A FS-A baseline. It writes one NetCDF4 output and one JSON
processing manifest. It does not process all 24 experiments.

EXPECTED OUTPUT LOCATIONS
  data/processed/m18_model_ready/<run_id>.nc
  reports/feature_engineering/m18_7_processing_manifests/<run_id>.json
  reports/feature_engineering/m18_experiment_registry.csv (status updated)

The processor writes temporary memory maps under data/processed/m18_work and
removes them after each run. Raw CERES NetCDF files are never modified.

IMPORTANT
  Do not run --all yet. First send the --estimate output and the --pilot output
  so the pilot file, disk usage, and manifest can be reviewed. After pilot approval,
  use:
    python "src/06_feature_engineering/process_m18_7_datasets.py" --all
  Completed runs are skipped automatically. Do not commit generated NetCDF4
  outputs or temporary data to Git.
