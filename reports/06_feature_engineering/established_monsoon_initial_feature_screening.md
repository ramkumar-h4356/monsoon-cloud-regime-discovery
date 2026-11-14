# Established Monsoon: Initial Feature Screening

## Scope

- Period: 2010–2021
- Seasonal window: July 15–August 13
- Years: 12
- Physical CERES variables: 45
- Spatial grid: 32 × 30
- Daily observations per year: 30
- Diagnostic valid-hour count variables excluded.
- IMD rainfall excluded from clustering features.
- Climate indices excluded from clustering features.

## Method

Statistics were calculated from all finite daily grid-cell observations
for each physical CERES variable. Missing values were excluded from
distribution statistics and retained in missingness counts.
No imputation or zero replacement was performed.

The daily variables are the existing arithmetic daily aggregates.
Area-weighted phase alternatives were not substituted.

## Overall validation

- Variable count: 45
- Year-variable records: 540
- Total variable-day-grid observations: 15,552,000
- Exact constant variables: 0
- Declared valid-range violations: 0

## Ten variables with highest missingness

| Variable | Missing (%) | Valid observations | Units |
|---|---:|---:|---|
| iwp_low_1h | 99.9887 | 39 | g m-2 |
| lwp_high_1h | 99.7729 | 785 | g m-2 |
| iwp_mid_low_1h | 99.4201 | 2,004 | g m-2 |
| lwp_low_1h | 78.5822 | 74,020 | g m-2 |
| cldhght_low_1h | 78.5639 | 74,083 | km |
| cldtemp_low_1h | 78.5639 | 74,083 | K |
| cldtau_low_1h | 78.5639 | 74,083 | dimensionless |
| cldpress_top_low_1h | 78.5639 | 74,083 | hPa |
| cldpress_low_1h | 78.5639 | 74,083 | hPa |
| cldphase_low_1h | 78.5639 | 74,083 | dimensionless |

## Interpretation cautions

- Missingness alone does not establish scientific irrelevance.
- A zero value is not automatically invalid.
- Declared valid ranges are metadata checks, not proof of
  scientific suitability.
- Low variability must be evaluated in the context of each
  variable's physical meaning and measurement scale.
- Correlation and redundancy analysis will be conducted separately.
- This is one season's screening evidence; final feature selection
  must use a common feature set across all seasons.

## Output files

- `results/tables/06_feature_engineering/established_monsoon_variable_screening.csv`
- `results/tables/06_feature_engineering/established_monsoon_yearly_screening.csv`
- `reports/06_feature_engineering/established_monsoon_initial_feature_screening.md`
