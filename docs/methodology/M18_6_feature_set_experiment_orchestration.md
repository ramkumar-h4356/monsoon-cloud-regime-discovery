# M18.6 — Feature-Set Experiment Orchestration

## Purpose

M18.6 creates a deterministic, resumable experiment registry for the six approved CERES feature sets. It does not load NetCDF data, perform imputation, scale matrices, or run clustering. Full data processing is reserved for M18.7.

## Feature-set membership

The runner reads `reports/feature_engineering/feature_set_registry.csv` and validates the exact approved membership counts before creating runs:

| Feature set | Expected features |
|---|---:|
| FS-A | 36 |
| FS-B | 21 |
| FS-C | 21 |
| FS-D | 21 |
| FS-E | 16 |
| FS-F | 21 |

Membership flags must be boolean-like (`true/false`, `1/0`, `yes/no`). Variable names must be unique. Family labels and exact feature order are retained in every run manifest.

## Staged experiment design

The runner avoids a full factorial experiment.

### Stage A — baseline

Six runs: one per feature set, using SA-A (conditional-median treatment without a structural-absence indicator), CA-A, RobustScaler, and equal feature weighting.

### Stage B — targeted missingness sensitivities

For each feature set:

1. MD-B with CA-A: residual-missingness indicator sensitivity.
2. SA-B with CA-A: structural-absence indicator sensitivity.
3. SA-A with CA-B: conservative cloud-area feature-screening sensitivity.

This creates 18 targeted runs. CA-B is screening-only; it does not impute cloud-area data. The current M18.4 treatment module remains the implementation authority.

### Stage C — shortlist-only scaling sensitivities

Stage C creates no runs by default. After Stage A/B results identify shortlisted feature sets, pass them using `--shortlist FS-A FS-C`. For each shortlisted set, the configured variants compare StandardScaler/equal weighting and RobustScaler/family-balanced weighting. This avoids running scaling sensitivities on every feature set before shortlisting.

### Stage D — validation policy

Every run manifest records the validation policy: year-blocked validation, no random grid-cell-hour row split as the primary method, exclusion of 2017 as a sensitivity, and training-partition-only fitting. Exact year partitions must be frozen before M18.7 processing; this milestone does not invent or execute holdout partitions.

## Registry and manifests

Outputs:

- `reports/feature_engineering/m18_experiment_registry.csv`
- `reports/feature_engineering/experiment_manifests/<run_id>.json`

Each run ID is deterministic for its experiment specification, orchestration configuration hash, and feature-registry hash. If either source changes, the run identity changes and stale completion status is not reused.

The registry tracks `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, and `SKIPPED`. Existing statuses are preserved when the same run identity is regenerated. Writes use temporary files and atomic replacement.

A run can be updated with:

```powershell
python "src/06_feature_engineering/experiment_orchestrator.py" --update-run-status "<RUN_ID>" --status RUNNING --note "processing started"
```

## Execution

From the project root:

```powershell
python "src/06_feature_engineering/experiment_orchestrator.py"
```

After shortlisting:

```powershell
python "src/06_feature_engineering/experiment_orchestrator.py" --shortlist FS-A FS-C
```

The script reads only the feature registry and JSON orchestration config. It does not modify raw NetCDF files or create model matrices.

## Acceptance criteria

- Six feature sets validated against exact expected counts.
- Stage A creates six baseline runs.
- Stage B creates 18 targeted sensitivity runs.
- Stage C remains inactive until an explicit shortlist is supplied.
- Run IDs are deterministic and source-hash-aware.
- Existing run status is resumable.
- Per-run manifests preserve feature order, family labels, and provenance.
- Registry and manifest writes are atomic.
- No full factorial, raw data processing, or clustering occurs in M18.6.
