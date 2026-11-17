M18.6 — FEATURE-SET EXPERIMENT ORCHESTRATION

EXTRACT
Extract this ZIP directly into the project root:
D:\Project Simulator\monsoon_cloud_research
Allow the existing src, tests, docs, and config folders to merge.

FILES
config/m18_experiment_orchestration.json
src/06_feature_engineering/experiment_orchestrator.py
tests/test_experiment_orchestrator.py
docs/methodology/M18_6_feature_set_experiment_orchestration.md

TEST
python -m pytest tests/test_experiment_orchestrator.py -v

RUN (after tests pass)
python "src/06_feature_engineering/experiment_orchestrator.py"

OPTIONAL STAGE C SHORTLIST (do not run until shortlist is justified)
python "src/06_feature_engineering/experiment_orchestrator.py" --shortlist FS-A FS-C

The runner expects the existing validated feature registry at:
reports/feature_engineering/feature_set_registry.csv

OUTPUTS
reports/feature_engineering/m18_experiment_registry.csv
reports/feature_engineering/experiment_manifests/<run_id>.json

This milestone creates run plans and manifests only. It does not load or modify CERES NetCDF data, build matrices, impute, scale, or cluster. Those belong to M18.7 and later.
