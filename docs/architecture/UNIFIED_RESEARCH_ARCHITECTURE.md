# Unified Research Architecture: CERES Satellite Cloud-Regime Research

**Project Title:** Satellite Cloud Feature Grouping for Exploratory Weather Pattern Analysis  
**Research Period:** 2010–2021  
**Geographical Domain:** India (6°N–38°N, 68°E–98°E, 32 × 30 grid)  
**Primary Data:** CERES SYN1deg Edition 4.2 (Hourly observations, 720 records per 30-day seasonal window)  
**Supporting Datasets:** IMD Rainfall (1°×1° daily), NOAA DMI (Hadley Centre), NOAA RONI (ERSSTv5)

---

## 1. Architectural Philosophy

The consolidated architecture enforces three foundational principles:

1. **Shared Infrastructure Without Shared Fits**:
   Common algorithmic logic (missingness classification, quality audits, feature scaling engines, clustering wrappers) is implemented once in `src/shared/`. However, each season preserves its own fitted transformations, scalers, PCA projections, and clustering assignments.
   > [!IMPORTANT]
   > Do not pool observations across seasons or force identical PCA axes or cluster labels across seasons. PCA axes can invert sign or rotate between independent fits, and cluster labels are permutation-invariant.

2. **Seasonal Pipeline Independence**:
   Each seasonal window has its own dedicated directory under `src/seasons/` and `config/seasons/`:
   - **Pre-monsoon** (April 15 – May 14): Focus on dry-to-wet transition, convective initiation, and Ice Water Path (IWP) phase distributions.
   - **Established monsoon** (July 15 – August 13): Focus on monsoon depressions, daily aggregation, IMD rainfall association, within-cell contrasts, and change-point sensitivity.
   - **Post-monsoon** (October 15 – November 13): Focus on northeast monsoon, retreat dynamics, and rigorous M19 data integrity audits.

3. **Explicit Integration Layer**:
   Cross-season comparisons take place strictly within `src/integration/`, comparing physical cloud property profiles, spatial distributions, and climate indices rather than raw cluster IDs or PCA coordinates.

---

## 2. Directory Layout

```text
monsoon_cloud_research/
├── config/
│   ├── shared/                # Shared experiment configurations & plans
│   └── seasons/               # Season-specific configurations (pre, established, post)
├── data/
│   ├── raw/                   # Immutable raw datasets (CERES, IMD, NOAA)
│   ├── interim/               # Seasonal NetCDF extracts & climate index CSVs
│   └── processed/             # Fitted models, daily aggregations, and model-ready arrays
├── src/
│   ├── shared/                # Common reusable research infrastructure
│   │   ├── inventory/         # Folder and dataset inspection tools
│   │   ├── validation/        # Time, coordinate, and metadata validation
│   │   ├── extraction/        # CERES seasonal window extraction
│   │   ├── missingness/       # Missingness classifier & treatment engine
│   │   ├── feature_engineering/# Scaling, screening, and registry generation
│   │   └── orchestration/     # M18.6 & M18.7 processing pipelines
│   ├── seasons/               # Independent seasonal analysis pipelines
│   │   ├── pre_monsoon/       # Pre-monsoon EDA and validation
│   │   ├── established_monsoon/# QC v3, daily aggregation, and rainfall association
│   │   └── post_monsoon/      # M19 data integrity audit suite
│   └── integration/           # Cross-season profile & climate synthesis
├── tests/
│   ├── shared/                # Tests for shared infrastructure
│   ├── seasons/               # Tests for seasonal pipelines
│   └── integration/           # Tests for cross-season synthesis
├── reports/                   # Audit summaries, diagnostics, and figures
├── docs/                      # Scientific methodology, provenance, and migration records
└── archive/                   # Preserved experiment snapshots & transfer packages
```

---

## 3. Storage Safety & Execution Governance

Full dataset processing (e.g. M18.7 24-experiment matrix) requires up to ~95.57 GiB of storage.
- Active disk space monitoring is integrated into `process_m18_7_datasets.py`.
- Pilot execution mode (`--pilot`) processes a single experiment baseline (Stage A, FS-A) for verification before large-scale runs.
