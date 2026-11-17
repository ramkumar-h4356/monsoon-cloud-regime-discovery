# Monsoon Cloud Research: Satellite Cloud Feature Grouping for Exploratory Weather Pattern Analysis

Unified, reproducible research codebase investigating satellite-derived cloud characteristics using CERES SYN1deg Edition 4.2 data (2010–2021) over India (6°N–38°N, 68°E–98°E).

## Seasons Covered
1. **Pre-monsoon:** April 15 – May 14
2. **Established monsoon:** July 15 – August 13
3. **Post-monsoon:** October 15 – November 13

## Structure
- `src/shared/`: Shared infrastructure for missingness, feature scaling, validation, extraction, and orchestration.
- `src/seasons/`: Independent seasonal analysis pipelines for pre-monsoon, established-monsoon, and post-monsoon.
- `src/integration/`: Cross-season physical comparisons and climate reconciliation (label-invariant).
- `tests/`: 252 comprehensive unit and integration tests across all tiers.
- `data/`: Raw, interim, and processed seasonal datasets.
- `reports/`: Audit summaries, feature registries, and seasonal validation reports.
- `docs/`: Scientific methodology, dataset provenance, and architecture records.
- `archive/`: Preserved experiment snapshots and historical review packages.

## Running Tests
```bash
pytest tests
```
