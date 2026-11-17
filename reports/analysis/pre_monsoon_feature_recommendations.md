# Pre-Monsoon CERES Feature Recommendations

## 1. Objective

Evaluate the suitability of CERES cloud-property variables for downstream cloud-regime research using data availability, physical relevance, and feature redundancy.

This document provides exploratory recommendations, not a finalized clustering feature set.

## 2. Correlation Analysis

A reproducible sample of 120,000 observations from 2010–2021 was analyzed using Pearson correlation.

Twenty-five variable pairs showed absolute correlation coefficients of at least 0.90, with at least 1,000 paired observations.

Strong correlations were observed among cloud pressure, cloud-top pressure, cloud temperature, and cloud height.

These variables describe related aspects of cloud vertical structure and may contain redundant information.

## 3. Feature Recommendations

| Feature group | Recommendation | Scientific justification |
|---|---|---|
| Cloud area | Primary candidate | Describes cloud coverage |
| Cloud optical depth | Primary candidate | Represents cloud optical characteristics |
| Cloud-top pressure | Primary candidate | Describes cloud vertical structure |
| Cloud temperature | Evaluate redundancy | Strongly associated with pressure and height |
| Cloud height | Evaluate redundancy | Strongly associated with pressure and temperature |
| Liquid water path | Conditional candidate | Availability varies by cloud layer |
| Ice water path | Conditional candidate | Substantial phase-dependent missingness |
| Cloud phase | Conditional candidate | Requires careful treatment of aggregated phase values |

## 4. Missing-Value Considerations

The analysis identified substantial missingness in several water-path variables.

Low-cloud IWP had approximately 95.6% missing observations across the complete study period.

IWP availability was strongly associated with cloud-phase values.

Missing observations must not automatically be interpreted as zero water content.

## 5. Redundancy Considerations

The sampled correlation analysis identified strong relationships among vertical-structure variables.

A reduced feature representation may be useful, but decisions should consider physical interpretation, missingness, and the intended downstream analysis.

Strong correlation alone does not justify removing a variable.

## 6. Recommended Preprocessing Approach

1. Retain original missing-value masks.
2. Evaluate missingness by year, cloud layer, and cloud phase.
3. Apply physically justified missing-value treatment.
4. Evaluate scaling and normalization before downstream distance-based analysis.
5. Investigate highly correlated variables before feature selection.
6. Avoid automatically replacing missing IWP and LWP values with zero.
7. Document all feature-selection and preprocessing decisions.

## 7. Limitations

Correlation estimates were derived from sampled observations and pairwise-complete data.

Different variable pairs may have different valid observation populations.

These recommendations should be evaluated by the wider project team before final model development.

## 8. Supporting Outputs

- `reports/feature_analysis/01_correlation_matrix.csv`
- `reports/feature_analysis/02_feature_availability.csv`
- `reports/feature_analysis/03_all_correlation_pairs.csv`
- `reports/feature_analysis/04_strong_correlations.csv`
- `results/figures/pre_monsoon/06_correlation_heatmap.png`

## 9. Conclusion

Cloud area, optical depth, and a suitable vertical-structure variable are reasonable candidates for further investigation.

Water-path variables require careful missingness assessment.

The findings provide evidence to inform subsequent feature engineering without independently developing a clustering model.
