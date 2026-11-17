# M26 — Rainfall Validation: Comprehensive Repository Inspection Report

**Milestone:** M26 — Rainfall Validation: Repository Inspection and Implementation Planning  
**Date:** 2026-11-17  
**Author:** Antigravity Integration & Scientific Audit Agent  
**Repository (Canonical):** `D:\Project Simulator\monsoon_cloud_research` (Branch `main`)  
**Worktree (Secondary):** `D:\Project Simulator\post_monsoon_research` (Branch `feature/post-monsoon-analysis`)  
**Audit Status:** AUDITED & VERIFIED — READY FOR IMPLEMENTATION PLANNING  

---

## 1. Executive Summary & Purpose

Milestone M26 initiates the physical rainfall validation of the unified M25 three-season cloud-regime discovery framework. Following the formal freeze of Milestone M25 (and its acceptance audits M25.1, M25.2, M25.3, M25.3.1, and M25.4), M26 evaluates whether the four discovered cloud regimes (R0, R1, R2, R3) exhibit statistically and meteorologically distinguishable surface precipitation signatures across the Indian subcontinent.

In strict adherence to the project charter:
1. **M25 Model Freeze:** The M25 model ($K=4$, MiniBatchKMeans, IncrementalPCA top 10, 36 features, CA-A/SA-A median imputation) is **formally frozen**. It shall NOT be retrained, modified, re-parameterized, or overwritten.
2. **Dataset Sanctity:** The raw CERES SYN1deg Ed4.2 satellite observations and the IMD 1.0° daily gridded rainfall dataset are preserved without modification.
3. **No External Substitution:** Analysis is performed strictly against the audited local IMD 1.0° gridded archive (`RFone`). The fine-resolution 0.25° product (`RF25`) is not present in the local repository and shall not be fabricated or substituted.
4. **Strict Scope Control:** No ENSO/IOD climate modulation analysis is conducted (reserved for M27); no geographical zone-wise clustering/splitting is introduced (reserved for later extensions).
5. **Zero Git Mutations:** No git commits, pushes, merges, rebases, branch switches, resets, cleans, or staging operations were or will be performed during this planning phase.

This inspection report establishes the exact empirical baseline of existing data assets, schemas, aggregation utilities, quality policies, test infrastructure, and preliminary analyses.

---

## 2. Frozen M25 Model Artifacts & Data Schema Audit

The M25 unified three-season cloud-regime discovery model represents $24,883,200$ hourly grid-cell observations spanning 12 years (2010–2021), 3 seasonal windows (Pre-Monsoon, Established Monsoon, Post-Monsoon), 30 calendar days per window (720 hours/window), and 960 spatial grid cells ($32 \times 30$ domain at 1.0° resolution).

All primary M25 data arrays reside in `data/processed/combined_3season/` and were independently audited for byte size, array shape, data type, and cryptographic SHA256 checksum:

| Artifact Name | Shape | Dtype | File Size (Bytes) | SHA256 Checksum | Verification Status |
|:---|:---:|:---:|---:|:---|:---:|
| `combined_3season_cluster_labels.npy` | `(24883200,)` | `uint8` | 24,883,328 | `903fffc4d5962882decc2995b620db5e81044260b8c82aff3a585f03097adcaa` | **VERIFIED** |
| `combined_3season_cell_indices.npy` | `(24883200,)` | `int16` | 49,766,528 | `8cb06353a13bb7a4f09e7e5b7aed6d91c97ebb2df590dfdafb50713c98aac15f` | **VERIFIED** |
| `combined_3season_years.npy` | `(24883200,)` | `int16` | 49,766,528 | `a55949386956c095153de9d7e3c6df0ab7e23a3aac163401b9c4cc62b31e1620` | **VERIFIED** |
| `combined_3season_season_ids.npy` | `(24883200,)` | `uint8` | 24,883,328 | `80b43aa542842d63c4f62de98164daedefde7e9f8073ca48bd7235ec7b40c3dd` | **VERIFIED** |
| `combined_3season_pca_top10_scores.npy` | `(24883200, 10)` | `float32` | 995,328,128 | `d3e1bcf4dc7e74d43016eeb3d1fc73fc669c3ef5821cdb3014da3533c77478f6` | **VERIFIED** |
| `combined_3season_FS-A_scaled.npy` | `(24883200, 36)` | `float32` | 3,583,180,928 | `57dcc0d30029a781cd9d92347a445f8de58eff15802bebaf7e7592b943df5530` | **VERIFIED** |

### M25 Regimes & Physical Taxonomy:
- **Regime 0 (R0) — Multi-Layer Mixed Convective & Congestus:**
  - Characteristics: Intermediate cloud-top height ($Z_{\text{top}} = 6.17\text{ km}$), moderate optical depth ($\tau = 3.81$), substantial liquid water path ($\text{LWP} = 45.7\text{ g/m}^2$), moderate ice path ($\text{IWP} = 34.2\text{ g/m}^2$).
  - Overall Prevalence: $12.89\%$ ($3,207,445$ hours).
- **Regime 1 (R1) — Boundary-Layer Shallow Cumulus:**
  - Characteristics: Low cloud-top height ($Z_{\text{top}} = 1.39\text{ km}$), thin optical depth ($\tau = 1.49$), zero liquid and ice water path ($\text{LWP} = 0.0, \text{IWP} = 0.0$).
  - Overall Prevalence: $13.52\%$ ($3,364,212$ hours). Highly seasonal (pre-monsoon peak $18.83\%$, monsoon drop to $2.60\%$).
- **Regime 2 (R2) — Deep Convective Storm Cores:**
  - Characteristics: High cloud top ($Z_{\text{top}} = 8.00\text{ km}$), massive optical depth ($\tau = 10.79$), heavy liquid and ice loading ($\text{LWP} = 122.5\text{ g/m}^2, \text{IWP} = 125.4\text{ g/m}^2$).
  - Overall Prevalence: $1.64\%$ ($408,085$ hours). Climatological peak during Established Monsoon ($2.09\%$). Expected primary rain producer.
- **Regime 3 (R3) — Upper-Tropospheric Thin Cirrus & Anvil Outflow:**
  - Characteristics: Very high cloud top ($Z_{\text{top}} = 8.44\text{ km}$), low optical depth ($\tau = 2.03$), zero liquid water ($\text{LWP} = 0.0$), modest ice path ($\text{IWP} = 26.6\text{ g/m}^2$).
  - Overall Prevalence: $71.94\%$ ($17,903,458$ hours). Regional matrix across India; daily dominant mode in Established Monsoon reaches $93.08\%$.

---

## 3. Audited IMD 1.0° Daily Gridded Rainfall Dataset

The physical rainfall dataset resides in `raw_data/IMD_Rainfall/` and consists of 12 annual CF-1.6 NetCDF files (`RFone_imd_rf_1x1_YYYY.nc` for $YYYY \in [2010, 2021]$).

### Metadata and Coordinate Schema:
- **Global Origin:** India Meteorological Department (IMD), National Climate Centre (NCC), Pune.
- **Conversion Pipeline:** Converted from native binary `.grd` to NetCDF using CDO v1.9.7.1 and Ferret v7.5.
- **Dimensions:**
  - `TIME`: 365 days (common years) or 366 days (leap years: 2012, 2016, 2020). Total daily steps = 4,383.
  - `LATITUDE`: 33 regular points, spanning $6.5^\circ\text{N}$ to $38.5^\circ\text{N}$ with $\Delta = 1.0^\circ$.
  - `LONGITUDE`: 35 regular points, spanning $66.5^\circ\text{E}$ to $100.5^\circ\text{E}$ with $\Delta = 1.0^\circ$.
- **Variable Name:** `RAINFALL` (`dims = ('TIME', 'LATITUDE', 'LONGITUDE')`, dtype = `float32`).
- **Units:** Millimetres ($\text{mm}$), representing daily accumulated rainfall depth.
- **Missing Value Sentinel:** `-999.0` (attributes `_FillValue = -999.0f`, `missing_value = -999.0f`).
- **Genuine Meteorological Zeros:** Value $0.0\text{ mm}$ represents verified zero rainfall (dry gauge day). It is NOT missing.

### Spatial Mapping to Canonical M25 Grid:
The canonical M25 domain spans 32 latitudes ($6.5^\circ - 37.5^\circ\text{N}$) and 30 longitudes ($68.5^\circ - 97.5^\circ\text{E}$):
$$\text{M25 Lat Index } i \in [0, 31] \iff \text{IMD Lat Index } i \in [0, 31] \quad (6.5^\circ\text{N} \dots 37.5^\circ\text{N})$$
$$\text{M25 Lon Index } j \in [0, 29] \iff \text{IMD Lon Index } j+2 \in [2, 31] \quad (68.5^\circ\text{E} \dots 97.5^\circ\text{E})$$
Coordinate difference between M25 grid centers and IMD grid centers is identically zero ($\Delta = 0.000^\circ$). No spatial regridding, interpolation, or coordinate re-projection is required.

### Land-Sea Mask Invariance:
Within the $32 \times 30 = 960$ cells of the M25 domain:
- **Valid Terrestrial Gauge Cells:** Exactly **357 cells**.
- **Masked Cells (Ocean & Foreign Land):** Exactly **603 cells**.
- **Temporal Invariance:** Across all 1,080 seasonal days (12 years $\times$ 3 seasons $\times$ 30 days), the land-sea mask is **100% time-invariant**. No cell flips between valid and missing across the 12-year archive.

---

## 4. Existing Daily Aggregation Utilities & Precedents

Repository inspection identified two existing daily aggregation implementations:

### A. Feature-Level Daily Aggregation (Abhin, Established Monsoon)
- Location: `src/seasons/established_monsoon/aggregation/established_monsoon_daily_aggregation.py`
- Approach: Aggregated 45 continuous CERES features daily by calendar day (`times.astype("datetime64[D]")`).
- Filtering Rule: Applied `MIN_VALID_HOURS = 18` (complete-case filter). If fewer than 18 valid hours existed across all 45 features, the grid-day was dropped.
- Outcome: Generated 290,355 daily records out of 345,600 theoretical grid-days (15.99% attrition rate due to complete-case requirement).

### B. M25 Cluster-Label Daily Aggregation (M25.3 Established Monsoon Correspondence)
- Location: `src/integration/run_m25_3_established_monsoon_correspondence.py` (`phase_c_m25_daily_aggregation`)
- Approach: Operates on frozen M25 cluster labels ($K \in \{0, 1, 2, 3\}$).
- Reshaped M25 hourly labels for Season 1 into `(12, 30, 24, 960)`.
- Computed:
  1. Hourly histogram of regime counts: $\text{count}_k = \sum_{h=0}^{23} \mathbb{I}(R_{y,d,h,c} == k)$.
  2. Continuous soft fractions: $f_k = \text{count}_k / 24.0$.
  3. Dominant daily regime: $R_{\text{dom}} = \operatorname{argmax}_k(\text{count}_k)$.
  4. Tie occurrences flag: `tie_occurred = (sorted_counts[-1] == sorted_counts[-2])`.
- Outcome: 345,600 exhaustive grid-days for Established Monsoon (zero attrition because M25 has complete labels).

**Takeaway for M26:**
M26 requires daily aggregation across **ALL THREE SEASONS** ($3 \times 345,600 = 1,036,800$ total grid-days). The Phase C methodology provides the exact mathematical blueprint for M26 daily regime aggregation.

---

## 5. Review of Existing Rainfall Analysis Scripts in the Repository

The repository contains several scripts developed by Abhin for established-monsoon rainfall analysis:
- `src/seasons/established_monsoon/analysis/established_monsoon_rainfall_alignment_audit.py`
- `src/seasons/established_monsoon/analysis/established_monsoon_rainfall_association.py`
- `src/seasons/established_monsoon/analysis/established_monsoon_rainfall_period_comparison.py`
- `src/seasons/established_monsoon/analysis/established_monsoon_within_cell_rainfall_analysis.py`

### Findings from Prior Script Audit:
1. **Model Scope:** Prior scripts exclusively evaluated Abhin's single-season established-monsoon clustering models (`baseline_k2`, `log_k2`, `log_k3`). They did NOT evaluate the unified M25 three-season model (R0–R3).
2. **Seasonal Scope:** Prior scripts analyzed only Season 1 (July 15–August 13). Neither Pre-Monsoon (Season 0) nor Post-Monsoon (Season 2) was ever joined with rainfall.
3. **Statistical Metrics:** Established precedents for reporting:
   - Sample size $N$, mean rainfall, median rainfall, 25th, 75th, 90th, and 95th percentiles.
   - Positive rainfall occurrence fraction: $P(R > 0)$.
   - Official IMD wet-day occurrence fraction: $P(R \ge 2.5\text{ mm})$.
4. **Data Pre-Extraction:** Abhin generated intermediate extracted files in `data/processed/rainfall_daily/established_monsoon/IMD_YYYY_established_monsoon_daily.nc`.
   *Decision for M26:* To avoid maintaining isolated per-season copies and ensure complete reproducibility across all 3 seasons, M26 will extract and validate rainfall directly from `raw_data/IMD_Rainfall/` in a clean, unified integration pipeline.

---

## 6. M25.4 Quality Control & Missingness Policy Compliance

M25.4 established the standard operating policy for IMD rainfall processing (`reports/integration/m25_4/imd_rainfall_readiness/imd_data_quality_policy.md`). M26 strictly incorporates these principles:

1. **Taxonomy of States:**
   - State 1: Valid positive precipitation ($R > 0.0\text{ mm}$).
   - State 2: Genuine dry day ($R = 0.0\text{ mm}$). Must be retained in probability of occurrence and mean rainfall calculations.
   - State 3: Partial coastal cells ($25\% \le F_{\text{cov}} < 75\%$, 29 cells). Flagged for sensitivity analysis.
   - State 4: Ocean structural absence (603 cells). Preserved strictly as `NaN`.
2. **Zero-Filling Prohibition:** Ocean cells and unmonitored foreign territories shall NEVER be filled with zero. Converting ocean `NaN` to zero would introduce 651,240 spurious dry observations ($603 \times 30 \times 36$), catastrophically corrupting regional rainfall statistics.
3. **Extreme Value Policy:** Values up to $500\text{ mm/day}$ are physically valid (historical maximum $495.08\text{ mm}$ during the August 2018 Kerala floods at cell $10.5^\circ\text{N}, 76.5^\circ\text{E}$). No capping or winsorizing. Any reading $> 1500\text{ mm/day}$ triggers an immediate pipeline halt.

---

## 7. Test Infrastructure & Baseline Verification

The integration test suite in `tests/integration/` serves as the regression gate for the repository:
- **Baseline Test Execution:** Executed on 2026-11-17 across 10 test modules.
- **Results:** Exactly **78 passed out of 78 tests** (100% passing in 5.50s).
- **Regressions:** Zero regressions detected.
- **Baseline Record:** Serialized to `reports/integration/m26/planning/m26_baseline_test_results.json`.

---

## 8. Repository Inspection Sign-Off

All required assets, schemas, metadata, precedents, and constraints for Milestone M26 have been inspected, documented, and verified. The repository is fully prepared for the formulation and execution of the M26 Implementation Plan.
