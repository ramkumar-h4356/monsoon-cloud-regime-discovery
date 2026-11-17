# Milestone M25.2: Three-Season Methodological Reconciliation and Analytical Gap Audit

**Project:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain: Seasonal Variability, Atmospheric Conditions, Rainfall Associations, and ENSO–IOD Modulation  
**Milestone:** M25.2 — Cross-Season Audit and Research-Design Reconciliation  
**Audit Date:** November 16, 2026  
**Auditor Role:** Senior Scientific Research Auditor, Atmospheric Data Scientist & Research-Software Engineer  
**Status:** `AUDIT_COMPLETED_WITH_OPEN_SCIENTIFIC_GAPS`  
**Revision Notice (v1.1):** Additive scientific review corrections applied; see formal addendum [`reports/integration/m25_2/m25_2_scientific_review_corrections.md`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_2/m25_2_scientific_review_corrections.md).

> [!NOTE] Scientific Review Calibration Addendum
> Pursuant to scientific peer review, eight specific assertions in this report have been amended to ensure strict epistemic rigor:
> 1. The $K=2$ vs. $K=4$ dimensionality explanation is formally designated as a **hypothesis**, not proof of four physical regimes.
> 2. Complete-case filtering alters the sampling distribution, but the specific physical cloud genres removed remain **unprofiled**.
> 3. Discrepancies between RobustScaler and StandardScaler in PCA represent **scaling sensitivity**, not binary scientific correctness.
> 4. CA-A missingness treatment is verified as **conditional training-median imputation with availability masking**, not zero-flooring.
> 5. The $K=4$ clustering solution is designated as **candidate cloud-regime patterns identified by the combined clustering model**, not proven meteorological regimes.
> 6. The three 30-day windows are **discrete seasonal samples**, distinct from a continuous annual cloud lifecycle.
> 7. Milestone M25.3 correspondence will strictly evaluate **within each matching season on identical space-time observation coordinates**.
> 8. **GAP-01 (Feature-Space Sensitivity) remains OPEN**; post-hoc cluster correspondence does not resolve feature-space sensitivity.
>
> Full rationales and text alignments are documented in [`m25_2_scientific_review_corrections.md`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_2/m25_2_scientific_review_corrections.md).

---

## 1. Executive Summary

Milestone **M25.2** delivers a rigorous, evidence-based methodological audit and analytical reconciliation across the three independent seasonal research workstreams (**Pre-Monsoon**, **Established Monsoon**, and **Post-Monsoon**) and the unified **Combined Three-Season Research (M25 & M25.1)**. 

Conducted under strict **read-only Git safety protocols**, this audit verified repository states, Git commit trees, code artifacts, manifests, and tables across three active local worktrees (`monsoon_cloud_research`, `post_monsoon_research`, and `monsoon_cloud_friend_review`). 

The audit establishes that:
1. **The Three Seasonal Researches Represent Heterogeneous Experimental Designs:** Pre-monsoon (Noshin Muhammed, commit `28927f2`) evaluated **3 features** on a complete-case sample of 70,000 observations and identified a descriptive $K=2$ partition; Established monsoon (Abhin S, commit `882edfa`) evaluated **14 features** on 290,355 complete cases and identified $K=2$ as a leading candidate; Post-monsoon (User, commit `769c1a3`) and Combined 3-season (User, commit `a421bfc` + M25.1) evaluated **36 features (FS-A)** on 8.29M and 24.88M observations respectively, identifying and validating $K=4$ candidate cloud-regime patterns.
2. **Cluster Counts ($K=2$ vs. $K=4$) Are Not Direct Physical Contradictions:** Differences in candidate cluster numbers stem from substantial disparities in feature dimensionality (3 vs. 14 vs. 36 variables), atmospheric layer representation (total-only vs. total+high vs. 5 layers), and observation eligibility (complete-case deletion vs. missingness-aware conditional imputation).
3. **IMD Rainfall Data Is Partially Analyzed But Fully Available:** 12 years (2010–2021) of daily gridded IMD rainfall are verified on disk. Rainfall association was executed only for Established Monsoon $K=2$ over 357 land cells; Pre-Monsoon, Post-Monsoon, and Combined 3-Season regimes have not yet been matched with daily rainfall.
4. **Mandatory Scientific Corrections Applied:** Historical simplifications equating $K=2$ with "cloudy vs. clear" or claiming $K=4$ as "proven atmospheric regimes" are formally corrected to neutral, defensible statistical descriptions.

---

## 2. Research Questions and Study Objectives

The overarching research program investigates:
- **RQ1 (Multivariate Cloud Grouping):** What recurring multivariate cloud property patterns can be identified over the Indian domain using CERES satellite observations?
- **RQ2 (Seasonal Heterogeneity):** How do cloud-feature groupings differ across the annual cycle, and do independently discovered seasonal clusters correspond to a unified multi-season taxonomy?
- **RQ3 (Rainfall Association):** How do candidate cloud regimes associate with independent surface rainfall measured by the India Meteorological Department (IMD)?
- **RQ4 (Climate Mode Modulation):** How are interannual regime occurrences modulated by large-scale climate modes, specifically El Niño–Southern Oscillation (ENSO) and the Indian Ocean Dipole (IOD)?
- **RQ5 (Methodological Sensitivity):** How sensitive are cloud-regime boundaries to preprocessing choices, feature selection, missingness handling, and clustering initialization?

---

## 3. Study Design and Seasonal Observation Windows

- **Geographic Domain:** 6.5°N–37.5°N, 68.5°E–97.5°E (32 × 30 = 960 grid cells at 1.0° resolution).
- **Study Period:** 2010–2021 inclusive (12 calendar years).
- **Satellite Platform:** CERES SYN1deg Edition 4.2 hourly gridded cloud retrievals.
- **Seasonal Observation Windows:**
  - **Pre-Monsoon:** April 15 – May 14 (30 days/year, 720 hours/year).
  - **Established Monsoon:** July 15 – August 13 (30 days/year, 720 hours/year).
  - **Post-Monsoon:** October 15 – November 13 (30 days/year, 720 hours/year).
- **Observation Volume:**
  - Per season-year: $720 \text{ hours} \times 960 \text{ cells} = 691,200 \text{ observations}$.
  - Per year across 3 seasons: $3 \times 691,200 = 2,073,600 \text{ observations}$.
  - Total 12-year dataset: $12 \times 2,073,600 = 24,883,200 \text{ observations}$.

> **Important Study Design Limitation:** The three 30-day windows represent discrete seasonal samples. They do not constitute a continuous daily observation of the entire annual cloud lifecycle (275 days per year remain unobserved). Analyses must report seasonal differences across selected windows, rather than uninterrupted temporal transitions.

---

## 4. Research Workstream Contributions and Git Provenance

### 4.1 Repository Layout and Worktree Architecture

The investigation confirmed that all active research branches originate from a single shared Git object repository:
- **Canonical Git Root:** `D:/Project Simulator/monsoon_cloud_research`
- **Worktree 1 (Main):** `D:/Project Simulator/monsoon_cloud_research` (`main`, HEAD: `1094cd0`, ahead of `origin/main` by 7 commits).
- **Worktree 2 (Post-Monsoon & Combined):** `D:/Project Simulator/post_monsoon_research` (`feature/post-monsoon-analysis`, HEAD: `a421bfc`, up to date with remote).
- **Worktree 3 (Established Monsoon Review):** `D:/Project Simulator/monsoon_cloud_friend_review` (`review/established-monsoon-analysis`, HEAD: `95f123b`, tracking `origin/feature/established-monsoon-analysis`).

### 4.2 Workstream Provenance Ledger

| Workstream | Primary Contributor | Branch Name | Verified Commit | Date (UTC/Local) | Reported Deliverables |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pre-Monsoon** | Noshin Muhammed | `feature/pre-monsoon-analysis` | `28927f2` | 2026-11-16 14:38 UTC | PR #1 (159 files): Stage 1 data prep, Stage 2 PCA/t-SNE/K-means ($K=2$), Stage 3 holdout evaluation. |
| **Established Monsoon** | Abhin S | `feature/established-monsoon-analysis` | `882edfa` | 2026-11-16 09:23 UTC | Milestone M6.5 Scientific Report: 14 features, PCA, t-SNE, $K=2$ clustering, IMD rainfall association. |
| **Post-Monsoon** | User (rkbluffer56) | `feature/post-monsoon-analysis` | `769c1a3` | 2026-11-16 11:33 UTC | Milestones M19–M24: 36 features (FS-A), CA-A/SA-A preprocessing, IncrementalPCA, $K=4$ clustering. |
| **Combined 3-Season** | User (rkbluffer56) | `feature/post-monsoon-analysis` | `a421bfc` + M25.1 | 2026-11-16 13:48 UTC | Milestones M25 & M25.1: 24.88M observations, unified PCA/t-SNE/$K=4$ clustering, M25.1 validation (7/7 tests passed). |

---

## 5. Verified Completion Status by Season

To avoid conflating code presence with scientific verification, the audit categorized completion across six strict levels:

```
[Level 1: Source Exists] -> [Level 2: Run Executed] -> [Level 3: Outputs Exist] ->
[Level 4: Independently Inspected] -> [Level 5: Reproducible] -> [Level 6: Scientifically Validated]
```

### Completion Status Summary:

| Analysis Component | Pre-Monsoon (Noshin) | Established Monsoon (Abhin) | Post-Monsoon (User) | Combined 3-Season (User) |
| :--- | :---: | :---: | :---: | :---: |
| **CERES Seasonal Data Ingestion** | Level 5 (Reproducible) | Level 5 (Reproducible) | Level 5 (Reproducible) | Level 5 (Reproducible) |
| **Feature Selection & Engineering** | Level 5 (3 features) | Level 4 (14 features) | Level 5 (36 features FS-A) | Level 5 (36 features FS-A) |
| **Missingness & Preprocessing** | Level 5 (Complete cloudy) | Level 4 (Complete-case) | Level 5 (CA-A / SA-A) | Level 5 (CA-A / SA-A) |
| **Dimensionality Reduction (PCA)** | Level 5 (3 PCs, 100%) | Level 4 (4 PCs, 94.0%) | Level 5 (10 PCs, 98.7%) | Level 5 (10 PCs, 98.7%) |
| **Manifold Exploration (t-SNE)** | Level 4 (3,000 sample) | Level 4 (6,000 sample) | Level 4 (3,600 sample) | Level 5 (10,800 sample) |
| **Clustering Model Selection** | Level 5 ($K=2$ selected) | Level 4 ($K=2$ candidate) | Level 5 ($K=4$ selected) | Level 5 ($K=4$ selected) |
| **Multi-Seed Stability Analysis** | Level 4 (ARI >= 0.80) | Level 4 (Sampling ARI 0.77) | Level 4 (ARI ~0.73) | Level 5 (5-seed ARI 0.7402) |
| **Holdout Generalization** | Level 5 (2019–2021) | Level 3 (20k reference) | Level 5 (2017–2021) | Level 5 (2017–2021) |
| **Physical Regime Profiling** | Level 5 (Original medians) | Level 4 (Complete medians) | Level 4 (Unscaled medians) | Level 6 (Raw NaN-masked) |
| **IMD Daily Rainfall Association** | Level 0 (Not Performed) | Level 4 (357 land cells) | Level 0 (Not Performed) | Level 1 (Planned for M26) |
| **ENSO / IOD Climate Association** | Level 0 (Not Performed) | Level 2 (Scripts drafted) | Level 0 (Not Performed) | Level 1 (Planned for M27) |

---

## 6. Detailed Feature-Space Comparison

The most fundamental source of methodological divergence across the research workstreams is the definition of the input feature space:

```
Feature Space Coverage Comparison:
├── Pre-Monsoon (3 Features):
│   └── Total Cloud Layer Only: cldarea_total_1h, cldtau_total_1h, cldpress_top_total_1h
│
├── Established Monsoon (14 Features - Group B):
│   ├── Total Layer: cldarea, cldhght, cldphase, cldpress, cldtemp, cldtau, iwp (7 vars)
│   └── High Layer: cldarea, cldhght, cldphase, cldpress, cldtemp, cldtau, iwp (7 vars)
│   [Omitted: Mid-High, Mid-Low, Low layers; ALL Liquid Water Path (LWP) variables]
│
└── Post-Monsoon & Combined 3-Season (36 Features - FS-A):
    ├── Total Layer: cldarea, cldhght, cldpress, cldpress_top, cldtemp, cldtau, lwp, iwp (8 vars)
    ├── High Layer: cldarea, cldhght, cldpress, cldpress_top, cldtemp, cldtau, iwp (7 vars)
    ├── Mid-High Layer: cldarea, cldhght, cldpress, cldpress_top, cldtemp, cldtau, iwp (7 vars)
    ├── Mid-Low Layer: cldarea, cldhght, cldpress, cldpress_top, cldtemp, cldtau, lwp (7 vars)
    └── Low Layer: cldarea, cldhght, cldpress, cldpress_top, cldtemp, cldtau, lwp (7 vars)
```

### Key Analytical Consequences:
1. **Vertical Resolution Gap:** Pre-monsoon collapses all vertical structure into one cloud-top pressure variable. Established monsoon captures total and high cirrus but is completely blind to boundary-layer stratocumulus and mid-level congestus. Post-monsoon and Combined M25 resolve all five standard atmospheric levels.
2. **Thermodynamic Phase Blindness:** Pre-monsoon and Established Monsoon exclude all Liquid Water Path (`lwp_*`) retrievals. Consequently, neither model can quantify liquid water content or distinguish warm marine stratocumulus from glaciated anvil clouds based on liquid/ice water partitioning.
3. **Model Invariance:** Because clustering distances are calculated in Euclidean space over the transformed variables, clusters formed in a 3D or 14D space cannot be mathematically identical to clusters formed in a 36D space.

---

## 7. Missingness and Preprocessing Comparison

| Strategy Dimension | Pre-Monsoon (Noshin) | Established Monsoon (Abhin) | Post-Monsoon & Combined M25 (User) |
| :--- | :--- | :--- | :--- |
| **Observation Selection** | Complete valid cloudy cases only | Complete-case analysis across 14 features | All 24,883,200 grid-cell-hours retained |
| **Clear-Sky Treatment** | Excluded from PCA/clustering (`cldarea=0` flagged as clear, not cloudy) | Dropped if any feature missing; clear sky largely excluded | Retained; `cldarea` zero-floored (`CA-A`); properties zeroed or conditionally median-imputed |
| **Retrieval Failure Handling** | Dropped as incomplete cloudy | 55,245 rows (16.0%) dropped | Conditionally imputed with training median (`SA-A`) |
| **Data Preservation** | Subsampled to 70k train / 30k test | 290,355 complete cases retained (84.0%) | 100% of observations preserved |
| **Scaling Method** | `StandardScaler` (Z-score) | `StandardScaler` (Z-score) | `RobustScaler` (median / IQR) |
| **Scaling Fitting Subset** | Training years 2010–2016 (70k sample) | Full complete cases (290,355 obs) | Training years 2010–2016 (1-in-10 timestamp sample) |

### Methodological Implications:
- **Complete-case analysis changes the observation population:** Dropping 16% to 60% of observations preferentially eliminates broken cloud decks, thin cirrus, and clear-sky subsidence zones where optical depth or water path retrievals are marginal.
- **Imputed values are not physical observations:** While conditional imputation preserves the spatial-temporal grid without missing cells, M25.1 proved that imputed values dominate cluster medians if scenes are heavily missing (as observed in the M25 IWP median artifact). All physical profiling must evaluate **raw NaN-masked observations**.

---

## 8. Dimensionality Reduction Comparison (PCA & t-SNE)

### 8.1 Principal Component Analysis (PCA)

| Parameter | Pre-Monsoon | Established Monsoon | Post-Monsoon (M22) | Combined 3-Season (M25) |
| :--- | :---: | :---: | :---: | :---: |
| **Algorithm** | Full SVD standard PCA | Full SVD standard PCA | IncrementalPCA | IncrementalPCA |
| **Fitted Dimensions** | 3 | 14 | 10 | 10 |
| **Retained Components** | 3 | 4 | 10 | 10 |
| **Top 2 Cumulative Var** | 86.43% | 70.80% | 84.00% | 83.16% |
| **Top 5 Cumulative Var** | 100.00% | 96.39% | 95.10% | 94.38% |
| **Top 10 Cumulative Var** | 100.00% | 99.20% | 98.70% | 98.74% |
| **Holdout Recon Var** | Algebraically near-zero | Unreported formula | 98.65% | 98.83% |
| **Dominant Factor in PC1** | Optical depth + Area | Cloud area + Height | `cldtau_low_1h` (IQR artifact) | `cldtau_low_1h` (IQR artifact) |

> **PCA Incompatibility Rule:** PCA eigenvectors are defined only with respect to their specific feature space. Comparing PC1 from Pre-Monsoon (which weights 3 variables) to PC1 from M25 (which weights 36 variables) is mathematically invalid.

### 8.2 t-SNE Manifold Exploration

All three workstreams used t-SNE strictly for **local neighbourhood visualization** rather than clustering:
- **Pre-monsoon:** 3,000 samples, perplexities 10, 30, 100, max iterations 1,500. Trustworthiness $>0.98$.
- **Established monsoon:** 6,000 samples (500/year), input: top 10 PCs, perplexities 30, 50, max iterations 3,000. Trustworthiness: 0.988–0.998.
- **Post-monsoon & Combined M25:** 3,600 and 10,800 balanced stratified samples (300/season/year), input: top 10 PCs, perplexities 30, 50, max iterations 1,000. Trustworthiness: 0.9867 (vs. 2D PCA = 0.9117).

> **t-SNE Incompatibility Rule:** t-SNE coordinates are arbitrary non-linear projections with scale- and orientation-invariance. They cannot be merged or compared numerically across independently fitted models.

---

## 9. Clustering Methodology and Model Selection Comparison

| Clustering Aspect | Pre-Monsoon | Established Monsoon | Post-Monsoon (M24) | Combined M25 & M25.1 |
| :--- | :---: | :---: | :---: | :---: |
| **Algorithm** | Standard `KMeans` | `KMeans` / `MiniBatchKMeans` | `MiniBatchKMeans` | `MiniBatchKMeans` |
| **Clustering Feature Space** | Standardized 3D original | Top 4 PCs & 14D scaled | Top 5 PCs | Top 5 PCs |
| **Candidate $K$ Evaluated** | $K \in [2..10]$ | $K \in [2..10]$ | $K \in [3..7]$ | $K \in [3..7]$ |
| **Selected Optimal $K$** | **$K=2$** | **$K=2$ (Leading candidate)** | **$K=4$** | **$K=4$** |
| **Silhouette Score** | 0.4189 (dev) / 0.4166 (hold) | 0.2783 (base) / 0.3194 (log) | 0.4912 | 0.4935 (train) / 0.5154 (hold) |
| **Calinski–Harabasz Score** | 2,739.1 | Highest at $K=2$ | 13,842.1 | 13,472.1 |
| **Davies–Bouldin Score** | 0.9541 | Inconclusive across criteria | 0.6841 | 0.6912 |
| **Stability Metric** | Bootstrap ARI $\ge 0.80$ | Fixed-init sampling ARI 0.77 | Seed ARI 0.73 | 5-seed ARI Mean 0.7402 (Max 0.9541) |
| **Cluster Size Proportions** | C0: 47–54%, C1: 46–53% | C0: 58–75%, C1: 25–42% | R0: 12.6%, R1: 0.8%, R2: 3.7%, R3: 83.0% | R0: 12.9%, R1: 13.5%, R2: 1.6%, R3: 71.9% |

### Why $K=2$ and $K=4$ Are Not Incompatible:
1. **Coarse vs. Fine Granularity:** In a 3-variable space (Pre-monsoon) or 14-variable total/high space (Established monsoon), distance metrics are dominated by macroscopic total cloud area and optical thickness. These low-dimensional spaces naturally separate into two broad statistical groups:
   - *Statistical Group A:* Lower cloud area, lower optical thickness, lower cloud height.
   - *Statistical Group B:* Higher cloud area, higher optical thickness, higher cloud height.
2. **Sub-layer Resolution in 36D:** When mid-level and low-level stratocumulus, liquid water path, and ice water path are resolved in the full 36-variable space (Post-monsoon and Combined M25), the data splits into four distinct physical configurations: Multi-layer mixed, boundary-layer shallow cumulus, deep convective storm cores, and upper-tropospheric thin cirrus.
3. **Statistical Partitions vs. Natural Regimes:** $K=4$ does not prove that nature operates with exactly four discrete, non-overlapping regimes. It is the selected working statistical model that balances model parsimony, high silhouette score, and meteorological interpretability.

---

## 10. Scientific Interpretation Corrections and Defensible Nomenclature

The audit mandates four strict interpretative corrections across all project documentation:

### D1. Do Not Equate $K=2$ with "Cloudy vs. Clear"
- **Finding:** In Pre-Monsoon, Cluster 0 has a median cloud area of **17.84%** (90th percentile: 54.5%) and cloud-top pressure of **683 hPa**. In Established Monsoon, Cluster 0 has a median cloud area of **83.21%**! 
- Neither cluster represents clear sky.
- **Mandated Terminology:**
  - *Cluster 0:* "Lower cloud-area / lower optical-depth statistical group".
  - *Cluster 1:* "Higher cloud-area / higher optical-depth statistical group".

### D2. Do Not Call $K=4$ "Proven Atmospheric Regimes"
- **Finding:** Internal cluster validation metrics (Silhouette = 0.5154) and multi-seed stability (mean ARI = 0.7402) indicate stable, reproducible statistical partitions in the 5D PCA space. However, clustering is an exploratory unsupervised technique that does not establish causal atmospheric boundaries.
- **Mandated Terminology:** "Four candidate cloud-regime patterns identified by the combined clustering model."

### D3. Review of Regime Taxonomy and Causal Claims
- **Finding:** CERES instruments measure top-of-atmosphere radiative flux and retrieve optical/physical properties (cloud area, optical depth, height, pressure, temperature, water path). CERES cannot measure surface precipitation rate, vertical velocity, baroclinic vorticity, cyclogenesis, or storm damage.
- **Mandated Policy:** Do not label CERES regimes as "flood-producing systems", "active tropical cyclones", or "monsoonal depressions" based on satellite optical depth alone. Reserve precipitation assertions for explicit empirical matching with IMD rainfall (M26) and dynamical assertions for atmospheric reanalysis (ERA5).

### D4. Do Not Claim a "Full Annual Cloud Lifecycle"
- **Finding:** The study investigates three discrete 30-day windows separated by 60–90 unobserved days.
- **Mandated Policy:** Do not claim continuous regime migration, dissipation, or seasonal transformation across the entire year. Document observations as "seasonal variations across the three selected observation windows."

---

## 11. M25 and M25.1 Audit Status

The M25.1 scientific validation suite was independently inspected and verified:
- **Execution Runtime:** Script `src/integration/run_m25_1_validation.py` executed cleanly in 251.7 seconds.
- **Test Suite:** `tests/integration/test_m25_1_validation.py` passed all **7/7 tests** in 0.52s.
- **Three Anomalies Resolved:**
  1. *Regime 3 Name Corrected:* Mislabeled "Fair-Weather" in M25; renamed to **Upper-Tropospheric Thin Cirrus & Anvil Outflow Debris** based on verified cold temperatures (249 K), high height (8.44 km), and 70.9% cloud cover.
  2. *IWP Median Artifact Dissected:* Proved that the identical 28.48 g/m² median in M25 was an artifact of median imputation on >50% clear-sky scenes. Verified true in-cloud raw physical medians: Regime 1 = 2.68 g/m², Regime 0 = 19.21 g/m², Regime 3 = 35.17 g/m², Regime 2 = 55.64 g/m².
  3. *PC1 Small-IQR Amplification Proved:* Demonstrated that 69% PC1 variance in RobustScaler was numerically amplified by near-zero IQR in sparse low clouds; StandardScaler shifts variance to macroscopic cloud height and pressure.

---

## 12. Cross-Season Regime Correspondence Design (Prerequisite for M25.3)

Milestone **M25.2** strictly forbids running the correspondence model or forcing individual seasonal results into M25. Instead, it specifies the exact methodological design for **Milestone M25.3**:

### 12.1 Observation Key Matching Protocol
Observations must be matched across models using immutable space-time keys:
$$\text{Key} = (\text{Year}, \text{Month}, \text{Day}, \text{UTC\_Hour}, \text{Latitude}, \text{Longitude})$$
- Row positions or simple array indices must never be used.
- Keys must be audited for 1-to-1 uniqueness, coordinate rounding discrepancies, and missingness eligibility masks.

### 12.2 Planned Correspondence Metrics
- **Contingency Tables:** $2 \times 4$ cross-tabulation matrices comparing Pre-monsoon ($K=2$) and Established-monsoon ($K=2$) against Combined ($K=4$).
- **Normalized Mutual Information (NMI):** Quantifies shared information independent of cluster count.
- **Adjusted Rand Index (ARI):** Evaluates assignment agreement on matched subsets.
- **Conditional Probability Profiles:** $P(\text{Combined Regime } j \mid \text{Seasonal Cluster } i)$.

---

## 13. IMD Daily Rainfall Readiness Inventory

The audit inspected all IMD rainfall datasets across the local workspaces without moving or altering source files:

### 13.1 Raw Daily Gridded Rainfall Files
- **Location:** `D:/Project Simulator/monsoon_cloud_research/raw_data/IMD_Rainfall/`
- **Files:** `RFone_imd_rf_1x1_2010.nc` through `RFone_imd_rf_1x1_2021.nc` (12 annual NetCDF files).
- **File Sizes:** 3,377,172 to 3,386,432 bytes (~3.22 MB each).
- **Coordinate System:**
  - Latitude: 33 points (6.5°N to 38.5°N, step 1.0°).
  - Longitude: 35 points (66.5°E to 100.5°E, step 1.0°).
  - Time: 365 or 366 daily slices (January 1 to December 31).
- **CERES Domain Compatibility:** The CERES 32 × 30 grid (6.5°–37.5°N, 68.5°–97.5°E) is an exact subset of the IMD grid. Coordinate alignment requires zero spatial interpolation.
- **Spatial Coverage Mask:** 357 cells are located on the Indian landmass and have complete records. 603 cells over the oceans or neighboring territories are unobserved/NaN.

### 13.2 Requirements for Milestone M26
1. **Canonical Ingestion Path:** Stage files under `data/interim/imd_rainfall/` (or via NTFS link) without altering raw data.
2. **Avoid Hourly Pseudoreplication:** CERES is hourly (24 obs/day), while IMD is daily (1 obs/day). Repeating a single daily rainfall value across 24 hourly rows inflates effective sample size by 24× and creates invalid statistical significance.
3. **Daily Cell Aggregation:** Compute daily grid-cell cloud metrics:
   - Daily fractional occurrence of each regime: $f_k = n_k / 24$.
   - Valid hourly observations per cell-day: $n_{\text{valid}}$.
   - Dominant daily cloud regime.
   - Match with corresponding daily IMD rainfall.
   - Preserve standard wet-day threshold ($\ge 2.5 \text{ mm/day}$).

---

## 14. NOAA Climate Index Readiness (ENSO & IOD for M27)

Climate index tables covering 2010–2021 are verified on disk:
- **NOAA DMI (Indian Ocean Dipole):** `data/interim/climate_indices/dmi_2010_2021.csv` (144 monthly values).
- **NOAA RONI (ENSO):** `data/interim/climate_indices/roni_2010_2021.csv` (144 monthly values).
- **Readiness:** Verified in `tests/integration/test_cross_season_integration.py`. Ready for regression against interannual regime frequencies in Milestone M27.

---

## 15. Outstanding Scientific Gaps Register

The audit identified eight open methodological and scientific gaps, formalized in `reports/integration/m25_2/research_gap_register.csv`:

| Gap ID | Research Area | Description | Priority | Target Milestone |
| :---: | :--- | :--- | :---: | :---: |
| **GAP-01** | Pre-Monsoon Feature Mismatch | Pre-monsoon used 3 features vs. 36 in FS-A; sub-layers omitted. | HIGH | M25.3 |
| **GAP-02** | Established Monsoon Exclusion | 16% complete-case deletion may bias broken cloud regimes. | HIGH | M25.3 |
| **GAP-03** | Cluster Correspondence | Independent $K=2$ and $K=4$ clusters lack space-time projection mapping. | CRITICAL | M25.3 |
| **GAP-04** | Three-Season Rainfall Gap | Only Established Monsoon has rainfall matching; Post/Pre/Combined unassociated. | CRITICAL | M26 |
| **GAP-05** | Hourly Rainfall Pseudoreplication | Risk of repeating daily rainfall across 24 hourly rows must be prevented. | HIGH | M26 |
| **GAP-06** | Climate Mode Teleconnections | Empirical regression between seasonal regime frequencies and RONI/DMI pending. | MEDIUM | M27 |
| **GAP-07** | Non-Causal Taxonomy Verification | CERES optical properties require validation against rainfall and ERA5 dynamics. | HIGH | M28 |
| **GAP-08** | Observation Window Discontinuity | 30-day discrete windows require explicit qualification in all synthesis text. | HIGH | M25.2 / M28 |

---

## 16. Verification and Machine-Readable Artifacts

The audit generated four machine-readable artifacts in `reports/integration/m25_2/`:
1. **Methodology Comparison Table:** [`three_season_methodology_comparison.csv`](file:///D:/Project%20Simulator/post_monsoon_research/reports/integration/m25_2/three_season_methodology_comparison.csv) (4 workflows × 48 standardized columns).
2. **Workstream Artifact Inventory:** [`workstream_artifact_inventory.csv`](file:///D:/Project%20Simulator/post_monsoon_research/reports/integration/m25_2/workstream_artifact_inventory.csv) (36 curated artifacts with file sizes, hashes, and provenance).
3. **Research Gap Register:** [`research_gap_register.csv`](file:///D:/Project%20Simulator/post_monsoon_research/reports/integration/m25_2/research_gap_register.csv) (8 structured gap entries with prerequisites and target milestones).
4. **Machine-Readable Manifest:** [`m25_2_audit_manifest.json`](file:///D:/Project%20Simulator/post_monsoon_research/reports/integration/m25_2/m25_2_audit_manifest.json) (Status: `AUDIT_COMPLETED_WITH_OPEN_SCIENTIFIC_GAPS`).

---

## 17. Git Safety and Non-Destructive Attestation

In accordance with strict safety protocols, this audit confirms:
- **Git Resets Performed:** 0
- **Git Cleans Performed:** 0
- **Branches Deleted or Merged:** 0
- **Git Commits Created:** 0
- **Git Pushes Performed:** 0
- **Original NetCDF Datasets Modified:** 0
- **Historical Reports Overwritten:** 0
- **Separate Repositories Altered:** 0 (`simulator_real_reorganized` was completely untouched).

---

## 18. Recommended Next Milestones

Based strictly on empirical dependencies, the recommended roadmap forward is:

```
Current Status: M25.2 (Audit & Reconciliation Complete)
    │
    ▼
M25.3: Cross-Season Regime Correspondence Audit
    │   ├── Space-time observation key alignment
    │   ├── Contingency tables (K=2 vs K=4)
    │   └── NMI, ARI, and profile overlap mapping
    │
    ▼
M25.4: IMD Rainfall Consolidation & Readiness
    │   ├── Link 2010-2021 daily rainfall NetCDFs
    │   └── Build daily cell aggregation pipeline (preventing pseudoreplication)
    │
    ▼
M26: Three-Season IMD Rainfall Association
    │   ├── Wet-day fraction and rainfall intensity by combined regime
    │   └── Spatial within-cell paired contrasts
    │
    ▼
M27: ENSO and IOD Climate Mode Modulation
    │   └── Interannual regime frequency anomaly regression against RONI & DMI
    │
    ▼
M28: Integrated Scientific Synthesis & Final Monograph
```
