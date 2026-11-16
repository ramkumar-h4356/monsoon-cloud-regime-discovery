# M4 Execution Instructions

Run from the repository root in the active project environment:

```powershell
python -m pytest tests/test_established_monsoon_pca.py -q
python src/08_dimensionality_reduction/established_monsoon_pca.py
```

Expected input directory:
`data/processed/clustering/established_monsoon/m3_feature_preparation/`

Output directory:
`data/processed/clustering/established_monsoon/m4_pca/`

The script fits baseline PCA first, then log-sensitivity PCA. Full-SVD PCA is
used because there are only 14 features; it retains all 14 components.
The score arrays are stored in compressed NPZ files with matching observation
identifiers to avoid very large CSV files.

After execution, inspect:
- `established_monsoon_m4_pca_manifest.json`
- `baseline_explained_variance.csv`
- `log_sensitivity_explained_variance.csv`
- `baseline_loadings.csv`
- `log_sensitivity_loadings.csv`
- `baseline_log_subspace_comparison.csv`
