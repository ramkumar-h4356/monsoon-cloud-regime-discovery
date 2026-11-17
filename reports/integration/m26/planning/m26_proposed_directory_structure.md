# M26 — Proposed Directory and File Structure Architecture (Revised)

**Milestone:** M26 — Rainfall Validation: Repository Inspection and Implementation Planning  
**Document Version:** 2.0 (Post-Review Revision)  
**Date:** 2026-11-17  
**Author:** Antigravity Integration & Scientific Audit Agent  
**Repository (Canonical):** `D:\Project Simulator\monsoon_cloud_research`  
**Worktree (Secondary):** `D:\Project Simulator\post_monsoon_research`  
**Status:** PROPOSED, REVISED & FORMALIZED  

---

## 1. Directory Structure Overview

To preserve the architectural integrity of the repository, maintain clear separation of concerns, and ensure 100% test reproducibility, Milestone M26 organizes all code, tests, planning documents, tables, reports, and packaging archives into structured, dedicated directories:

```
monsoon_cloud_research/
├── reports/
│   └── integration/
│       └── m26/
│           ├── planning/                                        # Phase 1: Planning Deliverables (Current Baseline)
│           │   ├── m26_repository_inspection_report.md          # Comprehensive repository inspection & artifact audit
│           │   ├── m26_implementation_plan.md                   # Revised implementation plan (Reassessed D01 & D02)
│           │   ├── m26_scientific_methodology_decision_register.csv # Revised scientific decision register
│           │   ├── m26_risks_and_unresolved_questions.md        # Revised risk & limitation register
│           │   ├── m26_temporal_alignment_and_population_evidence.md # Explicit temporal & spatial mathematical proof
│           │   ├── m26_planning_revision_changelog.md           # Formal before-and-after change log
│           │   ├── m26_baseline_test_results.json               # Pre-implementation test baseline (78 passed)
│           │   └── m26_proposed_directory_structure.md          # Architectural file & directory layout
│           ├── tables/                                          # Phase 2: Statistical Output Tables
│           │   ├── m26_regime_rainfall_pooled_summary.csv       # Primary pooled regime statistics (Tier 1, 29 days)
│           │   ├── m26_regime_rainfall_by_season.csv            # Season-stratified regime statistics
│           │   ├── m26_regime_rainfall_by_year.csv              # Annual stability metrics (2010–2021)
│           │   ├── m26_continuous_fraction_correlations.csv     # Soft regime fraction Spearman correlations
│           │   ├── m26_continuous_fraction_regressions.csv      # Multivariable Tobit/OLS regression models
│           │   ├── m26_sensitivity_analysis_results.csv         # 4-dimensional sensitivity matrix (S1, S2, S3, S4)
│           │   ├── m26_block_bootstrap_confidence_intervals.csv # Autocorrelation-corrected 95% CIs
│           │   └── m26_extreme_event_attribution.csv            # Attribution of Q95+ extreme events
│           ├── figures/                                         # Phase 2: Scientific Diagnostic Plots (300 DPI)
│           │   ├── fig1_regime_rainfall_distributions_by_season.png
│           │   ├── fig2_spatial_rainfall_composites_by_regime.png
│           │   ├── fig3_convective_fraction_vs_rainfall_deciles.png
│           │   └── fig4_sensitivity_comparison_matrix.png
│           ├── m26_rainfall_validation_synthesis_report.md      # Final Peer-Review Caliber Synthesis Report
│           ├── m26_manifest.json                                # Complete Cryptographic & Metadata Manifest
│           └── M26-rainfall-validation.zip                      # Standalone Handoff Archive Bundle
│
├── src/
│   └── integration/
│       └── rainfall_association/                               # Implementation Modules
│           ├── __init__.py
│           ├── daily_regime_aggregation.py                      # Aggregates hourly M25 labels to daily summaries
│           ├── imd_rainfall_loader.py                           # Slices, subsets & QC-tags IMD daily rainfall
│           ├── spatial_temporal_join.py                         # Joins cloud summaries with rainfall (year, date, lat, lon)
│           ├── regime_rainfall_statistics.py                    # Parametric & non-parametric rainfall statistics
│           ├── continuous_fraction_association.py               # Soft continuous fraction correlations & regressions
│           ├── sensitivity_suite.py                             # 4-dimensional sensitivity perturbation matrix
│           ├── statistical_inference_framework.py               # Spatial block bootstrap & permutation tests
│           └── m26_orchestrator.py                              # End-to-end automated execution pipeline
│
├── tests/
│   └── integration/
│       ├── test_cross_season_integration.py                     # (Existing M25 test)
│       ├── test_m25_1_validation.py                             # (Existing M25.1 test)
│       ├── test_m25_2_audit.py                                  # (Existing M25.2 test)
│       ├── test_m25_3_1_acceptance_audit.py                     # (Existing M25.3.1 test)
│       ├── test_m25_3_artifact_recovery.py                      # (Existing M25.3 test)
│       ├── test_m25_3_established_monsoon_correspondence.py     # (Existing M25.3 test)
│       ├── test_m25_3_post_monsoon_correspondence.py            # (Existing M25.3 test)
│       ├── test_m25_3_preflight.py                              # (Existing M25.3 test)
│       ├── test_m25_3_tri_seasonal_synthesis.py                 # (Existing M25.3 test)
│       ├── test_m25_4_imd_readiness.py                          # (Existing M25.4 test)
│       └── test_m26_rainfall_validation.py                      # New: Dedicated M26 Test Suite (10+ tests)
│
└── data/
    └── processed/
        └── rainfall_validation/                                 # Intermediate Preprocessed Arrays (Excluded from git)
            ├── .gitkeep
            ├── m26_daily_regime_aggregation.parquet             # Vectorized 3-season daily cloud table
            └── m26_cloud_rainfall_matched.parquet               # Master joined analysis dataset (342,432 Tier 1 rows)
```

---

## 2. Directory Roles & Content Governance

### 1. `reports/integration/m26/planning/`
- **Purpose:** Houses all Phase 1 inspection, implementation planning, methodological decision registers, risk analyses, technical evidence, change logs, and baseline test verifications.
- **Auditing Policy:** Once accepted, these planning files establish the frozen scope of M26.

### 2. `reports/integration/m26/tables/`
- **Purpose:** Stores tabular CSV deliverables detailing regime rainfall distributions, annual stability, soft-fraction regressions, sensitivity tests, and block-bootstrap confidence intervals.
- **Format:** Comma-separated values (CSV) with UTF-8 encoding, complete header schemas, and explicit physical units in column names (e.g., `mean_rainfall_mm`, `p_wet_day_pct`).

### 3. `reports/integration/m26/figures/`
- **Purpose:** Stores publication-grade diagnostic plots (300 DPI PNG) illustrating seasonal rainfall histograms, spatial composites, convective response curves, and sensitivity grids.

### 4. `src/integration/rainfall_association/`
- **Purpose:** Contains all production-grade, modular Python code implementing the M26 pipeline.
- **Standards:** Clean PEP 8 compliance, deterministic execution, type hinting, comprehensive docstrings, modular error handling, and zero external unverified dependencies.

### 5. `tests/integration/test_m26_rainfall_validation.py`
- **Purpose:** Automated pytest test suite executing alongside the existing 78 integration tests.
- **Coverage:** Tests daily aggregation completeness, spatial coordinate equality, one-to-one joining ($342,432$ primary records, $372,708$ S1 records), dry-day/ocean NaN preservation, regime rank-order stability, and sensitivity invariance.

### 6. `data/processed/rainfall_validation/`
- **Purpose:** Local intermediate storage for high-performance serialized arrays (`.parquet` format) to allow rapid re-analysis without re-aggregating the $24.8\text{M}$ hourly M25 labels on every run.
- **Git Policy:** Ignored by Git via `.gitignore` to prevent repository bloat; fully reproducible on demand via `m26_orchestrator.py`.

---

## 3. Mirroring Policy for Secondary Worktree

Following established project protocol:
- All planning deliverables in `reports/integration/m26/planning/` must be identically mirrored into the secondary worktree:  
  `D:\Project Simulator\post_monsoon_research\reports\integration\m26\planning\`
- File integrity between both worktrees is verified via exact byte counts and SHA256 checksum comparison.
