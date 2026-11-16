# Project stage index — current handoff

## Completed analysis stages represented in this bundle

1. CERES seasonal structural and variable screening.
2. Spatial coordinate compatibility audit between CERES and IMD.
3. Paired feature correlation analysis, annual stability and cross-season comparison.
4. Missingness analysis across the 36 seasonal CERES datasets.
5. Actual timestamp/UTC-hour integrity and product metadata audit.
6. Focused 2015–2018 missingness discontinuity investigation.
7. M18 missingness-aware feature engineering and feature-set experiment design.
8. Feature-set registry generation and validation.

## Registry execution result

The registry generator was executed against the supplied `ceres_feature_screening_summary.csv`.

- 36 eligible candidates found.
- No duplicate variable names.
- No unclassified variable families.
- Layer mappings passed.
- FS-A: 36 features
- FS-B: 21 features
- FS-C: 21 features
- FS-D: 21 features
- FS-E: 16 features
- FS-F: 21 features

This validates registry construction only. It does not validate scientific suitability, final imputation, scaling, or clustering.

## Pending stages

- Decide and implement the missingness transformation experiments (MD-A/MD-B/MD-C).
- Produce transformed matrices by feature set, with train-only fit safeguards where temporal holdouts are used.
- Run sensitivity experiments, including exclusion of 2017.
- Select and validate clustering algorithms and cluster counts.
- Interpret clusters and test their associations with independent IMD rainfall, RONI and DMI data.
- Prepare final figures, results, limitations and research write-up.

## Files intentionally not included

- Raw CERES NetCDF, IMD rainfall source data, NOAA source files, and large extracted/interim datasets.
- Large spatial-by-cell discontinuity CSV that was not uploaded into this working session.
- Earlier source scripts already present in the user's local repository but whose exact source contents were not available in this packaging session (metadata audit, post-monsoon audit, spatial audit, feature screening, paired correlations, correlation stability, cross-season correlations and missingness scripts). They are not recreated or overwritten here.

Those local files remain in the user's repository and should be retained. This ZIP is a consolidated handoff of all accessible reports and newly prepared M18 assets, not a replacement for the entire raw-data repository.
