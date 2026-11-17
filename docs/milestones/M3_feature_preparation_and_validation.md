# M3 — Feature Preparation and Validation

## Objective

Formalize and validate the existing Established Monsoon Group B feature preparation without replacing previous results.

## Existing evidence retained

- 14 Group B features.
- Existing pooled Group B complete-case coverage: 84.01%.
- Existing complete-case matrix reported as 290,355 × 14.
- Existing incomplete observations excluded without imputation.
- Existing baseline StandardScaler and log1p sensitivity retained.

## New implementation

- `src/06_feature_engineering/established_monsoon_feature_validation.py`
  - Feature schema and transformation definitions.
  - Annual dataset validation.
  - Metadata/key and matrix validation.
  - Registry construction and validation.
- `src/06_feature_engineering/prepare_established_monsoon_group_b_m3.py`
  - Uses paths relative to the script/project root.
  - Validates all 12 annual datasets and consistent grid.
  - Builds complete-case baseline and log-sensitivity matrices.
  - Writes outputs only to the new M3-specific directory.
  - Produces a feature registry, aligned metadata and JSON manifest.
- `tests/test_established_monsoon_feature_validation.py`
  - Unit tests for schema, metadata, missingness, non-finite values, log domain and registry integrity.

## Important interpretation

The registry is an evidence ledger, not an automated feature-selection algorithm. High correlation does not prove interchangeability. No automatic feature exclusion or imputation is introduced.

The full-period scaler fit preserves the existing descriptive unsupervised baseline. It must not be reused as a leakage-safe train/test evaluation. Predictive or held-out workflows must fit preprocessing on training/reference data only.

## Local execution

From the repository root:

```powershell
python -m pytest tests/test_established_monsoon_feature_validation.py -q
python src/06_feature_engineering/prepare_established_monsoon_group_b_m3.py
```

Expected output directory:

`data/processed/clustering/established_monsoon/m3_feature_preparation/`

## Completion gate

M3 is not considered runtime-verified until:
- Unit tests pass locally.
- All 12 local annual NetCDF files pass validation.
- Generated matrices are finite and have matching metadata row counts.
- Registry contains exactly 14 unique features.
- Manifest and matrix dimensions agree.
- Existing outputs remain unchanged.
