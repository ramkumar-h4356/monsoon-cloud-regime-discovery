# Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain

## Project Overview

This project aims to discover recurring cloud regimes over the Indian monsoon domain using satellite observations and unsupervised machine learning.

The study investigates how cloud properties, spatial distributions, and regime occurrence vary across different phases of the Indian monsoon. It also explores associations between identified cloud regimes, rainfall patterns, and large-scale climate phenomena such as El Niño–Southern Oscillation (ENSO) and the Indian Ocean Dipole (IOD).

## Research Objectives

1. Identify recurring cloud regimes using CERES satellite observations.
2. Analyse the spatial distribution and seasonal variability of the identified regimes.
3. Investigate associations between cloud regimes and independent rainfall observations.
4. Examine interannual variations in cloud-regime occurrence in the context of ENSO and IOD.
5. Evaluate cluster quality, stability, and sensitivity to methodological choices.

## Study Design

- **Study period:** 2010–2021
- **Geographical domain:** 6°N–38°N, 68°E–98°E
- **Primary dataset:** CERES SYN1deg Edition 4.2

### Seasonal Windows

| Season | Study period |
|---|---|
| Pre-monsoon | April 15 – May 14 |
| Established monsoon | July 15 – August 13 |
| Post-monsoon | October 15 – November 13 |

The study contains 36 seasonal datasets, with 720 hourly observations per dataset.

## Data Sources

| Dataset | Purpose |
|---|---|
| CERES | Primary cloud-property observations for clustering |
| IMD rainfall | Independent rainfall association and validation |
| NOAA RONI | ENSO climate context |
| NOAA DMI | Indian Ocean Dipole climate context |

Rainfall and climate indices are not used as inputs to the primary cloud-regime clustering model.

## Methodology

1. Data inventory and quality assessment.
2. Seasonal extraction and temporal aggregation.
3. Feature engineering and preprocessing.
4. Unsupervised clustering of cloud properties.
5. Cluster evaluation and stability analysis.
6. Spatial and seasonal variability analysis.
7. Association analysis with rainfall, ENSO, and IOD.

A common preprocessing pipeline and clustering model will be used across the study period to maintain comparability of cluster labels between seasons and years.

The identified clusters are treated as exploratory recurring cloud regimes. Observational associations will not be interpreted as direct causal relationships.

## Repository Structure

```text
monsoon-cloud-regime-discovery/
├── config/
├── data/
├── docs/
├── raw_data/
├── reports/
├── results/
├── src/
├── .gitignore
└── README.md
```

Large raw and generated scientific datasets are maintained separately and are not committed to this repository. Lightweight metadata, source code, documentation, and selected research outputs can be version-controlled.

## Collaboration

The repository is intended for collaborative research and development. Code changes should be developed on dedicated branches and integrated into the main branch through pull requests.

## Project Status

Data acquisition, seasonal dataset generation, and initial structural validation have been completed. Further data-quality assessment, feature engineering, clustering, and scientific analysis are ongoing.