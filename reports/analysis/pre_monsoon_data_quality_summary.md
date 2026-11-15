# CERES Pre-Monsoon Data Quality and Scientific Findings

## 1. Dataset

- Source: CERES SYN1deg Edition 4.2
- Period: 2010–2021
- Season: April 15 – May 14
- Domain: 6°N–38°N, 68°E–98°E
- Spatial grid: 32 × 30
- Temporal resolution: Hourly
- Files analyzed: 12 NetCDF files

## 2. Dataset Integrity

All 12 annual files passed the final integrity audit.

Each file contains 720 hourly records. No duplicate timestamps, missing hourly slots, or unexpected hourly slots were identified.

Spatial coordinates were consistent across all years.

The recorded timestamp intervals vary slightly around one hour, despite complete hourly coverage.

## 3. Missing-Data Assessment

Missing-data analysis identified substantial differences in variable availability.

Ice water path and liquid water path have particularly high missingness in certain cloud layers.

For example, low-cloud ice water path has approximately 95.6% missing observations across the full dataset.

Missing values should not automatically be replaced with zero.

## 4. Cloud-Phase Interpretation

CERES cloud particle phase ranges from 1 to 2.

According to CERES documentation:

- Phase 1.0 represents liquid-water cloud pixels.
- Phase 2.0 represents ice-cloud pixels.
- Intermediate values represent aggregated combinations of liquid and ice cloud pixels.

The analysis found that IWP was unavailable at phase = 1.0 and available at valid phase values greater than 1.0 across the investigated layers.

This relationship is consistent with phase-dependent retrieval availability.

## 5. Correlation Analysis

A reproducible sample of 120,000 observations was analyzed using Pearson correlation.

Twenty-five variable pairs had absolute correlations of at least 0.90 with at least 1,000 valid paired observations.

Strong relationships were identified among cloud pressure, cloud-top pressure, cloud temperature, and cloud height.

These correlations suggest possible feature redundancy but do not independently justify removing variables.

## 6. Preprocessing Recommendations

1. Preserve missing-value masks and distinguish missing observations from physical zero values.
2. Account for cloud-phase-dependent availability when using IWP and LWP.
3. Consider cloud area and optical depth as primary exploratory feature candidates.
4. Evaluate pressure, temperature, and height redundancy before selecting vertical-structure features.
5. Assess missingness and paired observation counts before interpreting correlations.
6. Document any imputation, exclusion, or transformation decisions.

## 7. Limitations

Correlation results are based on sampled observations and may be affected by spatial and temporal dependence.

The investigation does not establish causation or independently validate all retrieval algorithms.

No independent final clustering model was developed as part of this assignment.

## 8. References

- NASA CERES SYN1deg data products: https://ceres.larc.nasa.gov/data/
- NASA CERES SSF Collection Guide: https://ceres.larc.nasa.gov/documents/collect_guide/pdf/SSF_CG_R2V1.pdf
- NASA Earthdata cloud-phase explanation: https://forum.earthdata.nasa.gov/viewtopic.php?t=4939

## 9. Supporting Outputs

- `reports/data_quality/`
- `reports/scientific_checks/`
- `reports/iwp_investigation/`
- `reports/feature_analysis/`
- `results/figures/pre_monsoon/`
