# Monsoon Cloud Regime Discovery — Consolidated Project Bundle

This ZIP is organized relative to the project root. It gathers the accessible reports and current M18 design/registry work so the files can be installed in one extraction.

## Install

Extract the ZIP into:

`D:\Project Simulator\monsoon_cloud_research`

Allow the folders to merge. This archive does not contain raw data and does not replace the full repository.

## Included

- M18 methodology document and experiment configuration.
- 2015–2018 discontinuity audit source.
- Feature-set registry generator source.
- Available data-quality reports from screening, spatial checks, correlations, missingness, timestamp/product metadata and discontinuity analysis.
- Generated FS-A through FS-F registry files and validation report.

See `docs/PROJECT_STAGE_INDEX.md` for exact scope, completed work and pending stages.

## Registry generator

Run from project root:

```powershell
python -m py_compile src\06_feature_engineering\build_feature_set_registry.py
python src\06_feature_engineering\build_feature_set_registry.py
```

The registry generator reads `reports/data_quality/ceres_feature_screening_summary.csv` and writes:

- `reports/feature_engineering/feature_set_registry.csv`
- `reports/feature_engineering/feature_set_definitions.json`
- `reports/feature_engineering/feature_set_registry_validation.json`

The attached screening report was used to validate the generator:
36 eligible candidates, no duplicate names, no unclassified families, layer checks passed.
Feature counts: FS-A=36, FS-B=21, FS-C=21, FS-D=21, FS-E=16, FS-F=21.

## Existing local scripts

Your Git status showed these earlier scripts already exist in your local repository. Their exact source contents were not available in this packaging session, so this ZIP intentionally does not replace or reconstruct them:

- `src/02_validation/audit_ceres_time_and_product_metadata.py`
- `src/02_validation/audit_post_monsoon_and_supporting_data.py`
- `src/02_validation/audit_spatial_and_metadata_compatibility.py`
- Earlier feature-screening, paired-correlation, correlation-stability, cross-season-correlation and missingness scripts under `src/06_feature_engineering/`

Keep your local copies of those files.

## Included audit results

The 2015–2018 discontinuity audit was already run successfully on your Windows machine. The accessible summary, year contrasts, regional patterns, UTC-hour report and cloud-area-conditioned report are included.

The timestamp/product metadata outputs are included. The time/metadata audit source remains in your local repository and is not overwritten by this bundle.

Some generated reports were not uploaded into this packaging session and therefore cannot be included, notably the full cell-level 2015–2018 spatial missingness output and some pooled correlation matrices. They remain in your local project if already present.

## Git

No staging, commit or push has been performed by this bundle creation.

After extraction, inspect changes:

```powershell
git status --short
```

Do not use `git add .`. Keep raw datasets and large NetCDF/GZIP files out of Git. Stage only deliberately selected scripts, configuration, documentation and compact reports after review.

## Dependencies used by included Python scripts

- numpy
- pandas
- xarray
- netCDF4 (or another xarray-supported NetCDF backend)

Install only if missing:

```powershell
python -m pip install numpy pandas xarray netCDF4
```
