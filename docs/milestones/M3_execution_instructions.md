# M3 execution instructions

Extract this package into the repository root. It adds new files and does not replace the existing Group B preparation script or existing model matrices.

Run from the repository root:

```powershell
python -m pytest tests/test_established_monsoon_feature_validation.py -q
python src/06_feature_engineering/prepare_established_monsoon_group_b_m3.py
```

The preparation script requires the 12 annual CERES daily NetCDF files and these existing evidence tables:
- `results/tables/06_feature_engineering/established_monsoon_variable_screening.csv`
- `results/tables/06_feature_engineering/established_monsoon_yearly_screening.csv`
- `results/tables/06_feature_engineering/established_monsoon_integrated_feature_evidence.csv`

It writes only to:
`data/processed/clustering/established_monsoon/m3_feature_preparation/`

Do not commit generated NPZ matrices or large data outputs. Review the manifest, registry and validation output before deciding what compact artifacts to retain in Git.
