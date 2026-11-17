# Established Monsoon — Stage 3 Validation Report

## 1. Processing scope

- Product: CERES SYN1deg Edition 4.2 (Edition 4B)
- Study period: 2010–2021
- Seasonal window: July 15–August 13, inclusive
- Hourly input: 720 records per year
- Daily output: 30 records per year
- Spatial domain: 6°N–38°N, 68°E–98°E
- Grid: 32 × 30 (1-degree resolution)
- Variables: 45 cloud-property variables
- Primary completeness threshold: 18 valid hours out of 24

## 2. Processing outputs

- 12 yearly daily NetCDF datasets generated.
- 12 yearly CSV completeness reports generated.
- 360 daily time records across the 12-year collection.
- Each daily dataset contains 45 aggregated variables and 45 valid-hour count variables.
- Processed NetCDF files are excluded from Git.

## 3. Independent daily-output validation

- Independent checks performed: 168.
- Failed checks: 0.
- All 12 years passed.
- Daily means for all 45 variables matched independent calculations.
- Valid-hour counts for all 45 variables matched independent calculations.
- The 18-hour masking rule was verified.
- Daily dates, dimensions, metadata, and CSV-to-NetCDF count consistency were verified.
- No infinite daily values were detected.

## 4. Strengthened source-input validation

The updated aggregation validation function was run against all 12 original hourly files.

- All 12 yearly files passed.
- Exact 45-variable schema verified.
- No missing or unexpected variable names.
- Exact July 15–August 13 calendar window verified.
- 720 hourly records per year verified.
- 24 records per calendar day verified.
- Spatial grid and coordinate checks passed.
- No infinite source values detected.

## 5. Completeness summary

| Metric | Result |
|---|---:|
| Variable-year reports | 540 |
| Variable-day-grid-cell observations | 15,552,000 |
| Retained at 18 hours | 9,836,094 (63.25%) |
| Retained at 24 hours | 6,041,727 (38.85%) |

The percentages represent retention across variable × day × grid-cell observations.
They are not percentages of unique geographic grid cells.

### Year-wise completeness

| Year | Retention at 18 hours | Retention at 24 hours |
|---:|---:|---:|
| 2010 | 61.11% | 38.32% |
| 2011 | 62.70% | 38.26% |
| 2012 | 63.23% | 37.68% |
| 2013 | 61.81% | 37.26% |
| 2014 | 62.16% | 37.96% |
| 2015 | 63.66% | 38.87% |
| 2016 | 63.07% | 38.78% |
| 2017 | 65.07% | 39.69% |
| 2018 | 63.99% | 39.77% |
| 2019 | 64.14% | 40.48% |
| 2020 | 63.15% | 39.53% |
| 2021 | 64.88% | 39.60% |

### Variable-wise completeness

| Variable | Retention at 18 hours | Retention at 24 hours |
|---|---:|---:|
| `cldarea_high_1h` | 100.00% | 100.00% |
| `cldarea_low_1h` | 79.30% | 78.83% |
| `cldarea_mid_high_1h` | 100.00% | 100.00% |
| `cldarea_mid_low_1h` | 100.00% | 100.00% |
| `cldarea_total_1h` | 100.00% | 100.00% |
| `cldhght_high_1h` | 84.68% | 42.57% |
| `cldhght_low_1h` | 21.44% | 3.79% |
| `cldhght_mid_high_1h` | 70.33% | 22.97% |
| `cldhght_mid_low_1h` | 48.69% | 11.98% |
| `cldhght_total_1h` | 100.00% | 99.68% |
| `cldphase_high_1h` | 84.68% | 42.57% |
| `cldphase_low_1h` | 21.44% | 3.79% |
| `cldphase_mid_high_1h` | 70.33% | 22.97% |
| `cldphase_mid_low_1h` | 48.69% | 11.98% |
| `cldphase_total_1h` | 100.00% | 99.68% |
| `cldpress_high_1h` | 84.68% | 42.57% |
| `cldpress_low_1h` | 21.44% | 3.79% |
| `cldpress_mid_high_1h` | 70.33% | 22.97% |
| `cldpress_mid_low_1h` | 48.69% | 11.98% |
| `cldpress_top_high_1h` | 84.68% | 42.57% |
| `cldpress_top_low_1h` | 21.44% | 3.79% |
| `cldpress_top_mid_high_1h` | 70.33% | 22.97% |
| `cldpress_top_mid_low_1h` | 48.69% | 11.98% |
| `cldpress_top_total_1h` | 100.00% | 99.68% |
| `cldpress_total_1h` | 100.00% | 99.68% |
| `cldtau_high_1h` | 84.68% | 42.57% |
| `cldtau_low_1h` | 21.44% | 3.79% |
| `cldtau_mid_high_1h` | 70.33% | 22.97% |
| `cldtau_mid_low_1h` | 48.69% | 11.98% |
| `cldtau_total_1h` | 100.00% | 99.68% |
| `cldtemp_high_1h` | 84.68% | 42.57% |
| `cldtemp_low_1h` | 21.44% | 3.79% |
| `cldtemp_mid_high_1h` | 70.33% | 22.97% |
| `cldtemp_mid_low_1h` | 48.69% | 11.98% |
| `cldtemp_total_1h` | 100.00% | 99.68% |
| `iwp_high_1h` | 84.01% | 42.23% |
| `iwp_low_1h` | 0.01% | 0.00% |
| `iwp_mid_high_1h` | 57.15% | 7.77% |
| `iwp_mid_low_1h` | 0.58% | 0.02% |
| `iwp_total_1h` | 94.17% | 70.73% |
| `lwp_high_1h` | 0.23% | 0.02% |
| `lwp_low_1h` | 21.42% | 3.77% |
| `lwp_mid_high_1h` | 35.36% | 7.65% |
| `lwp_mid_low_1h` | 47.83% | 11.59% |
| `lwp_total_1h` | 75.22% | 39.65% |

## 6. Aggregation methodology

- Arithmetic mean of available hourly observations for each calendar day.
- Missing hourly observations are excluded from the mean and denominator.
- Daily values with fewer than 18 valid hours remain NaN.
- Valid-hour counts are retained separately for every variable, day, and grid cell.
- No zero replacement, imputation, or interpolation.
- Cloud-phase variables remain continuous-valued; no rounding or categorical mode is applied.
- Supplied total-layer variables are retained rather than reconstructed.

The 24-hour comparison measures completeness retention using valid-hour counts.
The current pipeline does not generate a separate 24-hour-masked daily dataset.

## 7. Scientific limitations

- Daily values based on 18–23 observations are partially observed daily means.
- Completeness varies substantially across variables and cloud layers.
- Some year-wise coverage patterns change around 2017–2018; their cause has not been established.
- Changes in data availability must not be interpreted as changes in actual cloud occurrence.
- This arithmetic aggregation is the project's explicit temporal rule, not an exact reproduction of the full NASA Edition 4.2 processing algorithm.
- Feature selection and clustering suitability remain separate research decisions.

## 8. Reproducibility references

- `src/04_aggregation/established_monsoon_daily_aggregation.py`
- `docs/methodology/established_monsoon_daily_aggregation.md`
- `reports/preprocessing/established_monsoon_daily_aggregation_2010.csv` through `2021.csv`

Original hourly NetCDF files and processed daily NetCDF files are not included in this report or Git.

## 9. Final status

**Stage 3 daily temporal aggregation: completed and independently validated.**

- Overall 18-hour retention: 63.25%.
- Overall 24-hour retention: 38.85%.
- Independent daily-output validation: 168 checks passed, zero failures.
- Strengthened source validation: 12 of 12 years passed.
