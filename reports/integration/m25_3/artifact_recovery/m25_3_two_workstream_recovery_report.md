# M25.3 — Phase 2 & Phase 3: Independent Seasonal Artifact Recovery and Provenance Verification Report

**Milestone:** M25.3 (Phases 2 & 3)  
**Project:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain  
**Auditor:** Senior Scientific Research Auditor & Atmospheric Data Scientist  
**Date:** 2026-11-16  

---

## Executive Summary

This milestone executes the independent seasonal artifact recovery, Git provenance audit, and correspondence readiness verification for two collaborative research workstreams:
1. **Workstream 1 (Noshin Muhammed — Pre-Monsoon):** Fully recovered and verified. All 21 files from the handoff package match recorded SHA256 checksums byte-for-byte. The 12 NetCDF label files covering 2010–2021 (8,294,400 grid-hour observations) match the canonical CERES coordinates identically (`np.allclose == True`). Observation matching against M25 Pre-Monsoon (`season_id == 0`) passes all gates. **Status: `VERIFIED_AND_READY_FOR_CORRESPONDENCE`**.
2. **Workstream 2 (Abhin S — Established Monsoon):** Comprehensive Git inspection and worktree audit completed. Commit `882edfa` ("Complete established monsoon M6.5 scientific documentation") on `origin/feature/established-monsoon-analysis` provides complete documentation, 14-feature screening evidence (Group B), daily aggregations, and rainfall association tables for 290,355 complete cases. However, the observation-level assignment table (`established_monsoon_fixed_cluster_assignments.csv`) and trained model bundle are absent from Git. Furthermore, Abhin's analysis was conducted on daily observations (345,600 raw) with complete-case filtering, creating both an artifact absence and a temporal/missingness granularity barrier against M25's hourly complete-domain framework. **Status: `BLOCKED_MISSING_ASSIGNMENT_ARTIFACTS`**.

---

## 1. Repository and Workspace Safety Status

### 1.1 Canonical Repository (`monsoon_cloud_research`)
- **Canonical Path:** `D:/Project Simulator/monsoon_cloud_research`
- **Current Branch:** `main` (commit `1094cd0`, ahead of origin by 7 commits).
- **Working Tree State:** Clean with respect to tracked files; uncommitted additive integration artifacts safely staged in dedicated directories.
- **Git Execution Policy:** 100% read-only. Strictly zero commits, zero pushes, zero destructive operations (`git reset`, `git clean`, `git checkout .` prohibited).

### 1.2 Friend Review Workspace (`monsoon_cloud_friend_review`)
- **Path:** `D:/Project Simulator/monsoon_cloud_friend_review`
- **Branch:** `review/established-monsoon-analysis`
- **Status:** Head commit `95f123b` ("Add established monsoon rainfall association analysis"), which is **behind `origin/feature/established-monsoon-analysis` by 4 commits**:
  - `124755d` Complete established monsoon milestones M1-M3
  - `e6f7ed1` Complete established monsoon milestone M4 PCA
  - `7ffafb5` Complete established monsoon milestone M5 t-SNE analysis
  - `882edfa` Complete established monsoon M6.5 scientific documentation
- **Local Git Object Database:** All objects for commit `882edfa` and its parents are present in `.git` and inspectable via read-only plumbing commands.

### 1.3 Remote Fetch Safeguard Policy
- Background network fetches over HTTPS can hang waiting for credentials or time out (as experienced in background task 1666).
- In compliance with scientific safety guidelines, **no network fetch was initiated without explicit user consent**.
- Therefore, the latest commit on the remote GitHub server has not been independently polled; local audits evaluate the latest verified ref `882edfa`.

---

## 2. Workstream 1: Noshin Pre-Monsoon Recovery Audit

### 2.1 Artifact Extraction and Checksum Verification
The handoff package `media_1794848995665_57d9ff2b.zip` was extracted into an isolated directory:
`reports/integration/m25_3/artifact_recovery/noshin_extracted/`

All 21 extracted files were subjected to independent SHA256 hashing and cross-checked against `pre-monsoon-checksums.csv` and Git commit `28927f2292c62a6673a5afce77ff2720c6fc8f19`:
- **12 NetCDF Label Files:** 2010–2018 (`phase2/stage2_v1`) and 2019–2021 (`phase3/stage3_v1`). All 12 files matched their recorded hashes exactly (e.g., 2010: `cfd7b506...`, 2018: `8ac4a57f...`, 2021: `a80148b2...`).
- **Model Bundle:** `selected_pre_monsoon_bundle.joblib` (5,034,737 bytes, SHA256 `4c26f58fcc842aa4c7da5d6547225a1d9ae25171f29f083014c31e4849233569`) verified intact.
- **Configurations and Manifests:** All 5 JSON metadata files matched commit `28927f2` byte-for-byte.

### 2.2 Reporting Script Failure Post-Mortem
During initial extraction verification, two script errors occurred in the execution harness:
1. `PermissionError [Errno 13]`: Caused by an assumption that all entries in the extraction root were flat files; attempting `open()` on the directory `config` triggered an OS permission error.
2. `TypeError`: Caused by a UTF-8 BOM (`\ufeff"File"`) in the CSV header causing column lookup fallback to `None`.
**Resolution:** Neither error indicated data corruption. Once handled with `utf-8-sig` and directory-aware tree traversal, all 21 files verified with 100% integrity.

### 2.3 12-Year NetCDF Coordinate Verification (Task-1740)
Every year (2010–2021) was verified against the canonical raw CERES files at `data/interim/ceres_seasonal/pre_monsoon/CERES_{year}_pre_monsoon.nc`:
- **Latitude Match:** Exactly 32 grid points (6.5°N to 37.5°N, 1.0° spacing), `np.allclose == True`.
- **Longitude Match:** Exactly 30 grid points (68.5°E to 97.5°E, 1.0° spacing), `np.allclose == True`.
- **Time Match:** Exactly 720 time steps per season (30 days × 24h), `np.allclose == True`.
- **Total Population:** Exactly 720 × 32 × 30 = 691,200 grid-hour observations per year. Total across 12 years: **8,294,400 observations**, matching M25 Pre-Monsoon identically.

### 2.4 Label Distribution
- **Cluster 0:** 4,204,697 observations (50.69%)
- **Cluster 1:** 4,047,419 observations (48.80%)
- **Clear Sky (-1):** 42,284 observations (0.51%)
- **Unavailable (-2):** 0 observations (0.00%)
- **Total Cloudy Observations:** 8,252,116 observations (99.49%)

**Classification:** `VERIFIED_AND_READY_FOR_CORRESPONDENCE`.

---

## 3. Workstream 2: Abhin Established-Monsoon Audit

### 3.1 Git Tree and Provenance Audit
Inspection of `origin/feature/established-monsoon-analysis` at commit `882edfa` ("Complete established monsoon M6.5 scientific documentation") reveals extensive scientific documentation:
- Comprehensive final report: `reports/established_monsoon_cloud_regime_study.md`
- Complete feature screening tables (Group B: 14 features retained)
- Daily CERES aggregations and aligned IMD rainfall tables (2010–2021)
- Pooled and annual rainfall contrast tables for `baseline_k2`, `log_k2`, and `log_k3`

### 3.2 Critical Artifact Gap: Missing Observation Assignments
A systematic tree search across all committed files and local worktrees confirmed:
- `results/tables/07_clustering/assignments/established_monsoon_fixed_cluster_assignments.csv` is **NOT committed**.
- No trained Joblib model bundle or gridded NetCDF label files were committed to Git.
- The summary table `established_monsoon_rainfall_cluster_year_coverage.csv` records aggregate counts per cluster per year (totaling 290,355 complete cases), but does not provide observation-level identifiers, timestamps, or grid coordinates.

### 3.3 Methodological Mismatch vs M25
Even if the 290,355 assignments were available, direct row-to-row correspondence with M25 would encounter fundamental scientific barriers:
1. **Temporal Granularity:** Abhin aggregated CERES to **daily** means (30 days × 960 cells = 28,800 observations/year; 345,600 total). M25 operates on **hourly** observations (720 hours × 960 cells = 691,200 observations/year; 8,294,400 total).
2. **Missingness Strategy:** Abhin applied strict **complete-case filtering** across 14 features, excluding 55,245 observations (15.99% attrition) without imputation. M25 used CA-A / SA-A zero-fill and median imputation across 36 features, retaining 100% of observations.
3. **Feature Space:** Abhin selected 14 total and high cloud properties (Group B), omitting low and mid-cloud layers. M25 retained all 36 features across all layers and microphysics.
4. **Cluster Cardinality:** Abhin selected K=2 as the leading model, whereas M25 selected K=4.

**Classification:** `BLOCKED_MISSING_ASSIGNMENT_ARTIFACTS`.

---

## 4. Cross-Workstream Recovery Comparison

| Dimension | Noshin Pre-Monsoon (Workstream 1) | Abhin Established Monsoon (Workstream 2) |
|---|---|---|
| **Archive / Branch** | `media_1794848995665_57d9ff2b.zip` | `origin/feature/established-monsoon-analysis` |
| **Git Commit Reference** | `28927f2292c62a6673a5afce77ff2720c6fc8f19` | `882edfa41f1750e39a3f2d2b51296ceca23bc624` |
| **Integrity Verification** | 21 / 21 files verified against SHA256 checksums | Summary tables verified; assignment files missing |
| **Temporal Granularity** | Hourly (720 hours / season) | Daily Aggregation (30 days / season) |
| **Total Study Population** | 8,294,400 grid-hour observations | 345,600 daily grid observations |
| **Missingness Treatment** | CA-A zero-fill imputation (100% complete) | Complete-case filtering (290,355 retained; 55,245 dropped) |
| **Feature Space** | FS-A (36 variables across 4 cloud layers) | Group B (14 variables; total and high clouds only) |
| **Cluster Labels Available** | 12 NetCDF files (100% coverage: 2010–2021) | 0 files (hourly/daily cluster arrays not committed) |
| **Model Bundle Available** | `selected_pre_monsoon_bundle.joblib` | None |
| **Coordinate Alignment** | Exact match with raw CERES and M25 (`np.allclose == True`) | N/A (no spatial label arrays available) |
| **Readiness Status** | `VERIFIED_AND_READY_FOR_CORRESPONDENCE` | `BLOCKED_MISSING_ASSIGNMENT_ARTIFACTS` |

---

## 5. Handoff Package Inventory

The following packages have been created in `reports/integration/m25_3/artifact_recovery/`:
1. `M25.3-pre-monsoon-verified-handoff.zip`: Contains verified original NetCDF label files, model bundle, configuration JSONs, verification manifests, and verification checksums.
2. `M25.3-established-monsoon-verified-handoff.zip`: Contains verified reports, coverage summaries, complete-case audits, and formal missing-artifact disclosure documentation.
3. `M25.3-seasonal-artifact-recovery-report.zip`: Consolidated package containing all 11 audit CSVs, manifest, and this technical report.

---

## 6. Recommendations and Next Actions

1. **Pre-Monsoon Workstream:** Proceed with Pre-Monsoon Correspondence Analysis (M25.3 Phase 2). The matching key `(Year, Month, Day, UTC_Hour, Latitude, Longitude)` is mathematically verified, and 8,252,116 valid cloudy observations are primed for contingency mapping against M25 K=4.
2. **Established-Monsoon Workstream:**
   - Maintain the formal gate status `BLOCKED_MISSING_ASSIGNMENT_ARTIFACTS`. Under no circumstances should synthetic assignments be generated.
   - If the user provides explicit authorization and network credentials, a bounded `git fetch` can be performed to verify if Abhin pushed commits beyond `882edfa`.
   - Alternatively, request that Abhin provide the missing `established_monsoon_fixed_cluster_assignments.csv` or model bundle before scheduling correspondence analysis.
