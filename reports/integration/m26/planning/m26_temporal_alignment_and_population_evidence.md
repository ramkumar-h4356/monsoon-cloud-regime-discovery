# M26 — Technical Evidence: Temporal Alignment Semantics & Spatial Population Recalculation

**Milestone:** M26 — Rainfall Validation: Planning Revision Dossier  
**Document Version:** 2.0 (Post-Review Revision)  
**Date:** 2026-11-17  
**Author:** Antigravity Integration & Scientific Audit Agent  
**Repository (Canonical):** `D:\Project Simulator\monsoon_cloud_research`  
**Worktree (Secondary):** `D:\Project Simulator\post_monsoon_research`  
**Status:** AUDITED, VERIFIED & FORMALIZED  

---

## 1. Executive Summary

Following scientific review of the initial M26 planning submission, this document provides the explicit empirical and mathematical evidence supporting the formal revision of two foundational methodological decisions:

1. **Reassessment of D01 (Temporal Alignment):** Transition from the approximate UTC Calendar Day convention ($00:00–24:00\text{ UTC}$, 87.5% overlap) to the **Exact IMD Shifted 24-Hour Accumulation Window ($03:00\text{ UTC } D \text{ to } 03:00\text{ UTC } D+1$) for Complete Days 1–29** as the primary scientific protocol. The incomplete Day 30 (21 hours available) and the orphan 3 hours of Day 1 are cleanly excluded from the primary 24-hour analysis.
2. **Reassessment of D02 (Primary Land-Cell Population):** Resolution of the internal population inconsistency by strictly adhering to the audited M25.4 Data Quality Policy. The primary analysis population is established strictly as **Tier 1 Full Land Cells ($N=328$, $F_{\text{cov}} \ge 75\%$)**. Tier 2 Coastal Cells ($N=29$, $25\% \le F_{\text{cov}} < 75\%$) are analyzed exclusively in sensitivity analysis S1 with an explicit coastal flag.

This revision eliminates all temporal phase offset from the primary analysis, prevents incomplete daily cloud records from distorting rainfall statistics, and aligns the spatial population directly with project data quality standards.

---

## 2. Empirical Audit of CERES Timestamp Convention & Time Basis

The CERES SYN1deg Edition 4.2 hourly product was audited directly from the archived NetCDF files in `data/interim/ceres_seasonal/`:

- **Coordinate Variable:** `time` (data type: `datetime64[ns]`, attributes: `long_name = "Time"`, `delta_t = "0000-00-01 00:00:00"`).
- **Time Basis:** Coordinated Universal Time (UTC).
- **Sampling Convention:** Hourly observations are centered on the half-hour UTC:
  $$\text{Timestamp } t_h = h + 00:30:00\text{ UTC} \quad \text{representing interval } [h + 00:00:00, h + 01:00:00)\text{ UTC}$$
- **Window Length:** Exactly 720 continuous hourly records per 30-day season:
  - Pre-Monsoon: `2010-04-15T00:29:52.968Z` to `2010-05-14T23:30:07.031Z` (720 records).
  - Established Monsoon: `2010-07-15T00:29:52.968Z` to `2010-08-13T23:30:07.031Z` (720 records).
  - Post-Monsoon: `2010-10-15T00:29:52.968Z` to `2010-11-13T23:30:07.031Z` (720 records).

---

## 3. Empirical Audit of IMD Daily Rainfall Accumulation Semantics

The IMD 1.0° daily gridded rainfall dataset (`RFone_imd_rf_1x1_YYYY.nc`) was audited against official IMD specifications (Rajeevan et al., 2006; Pai et al., 2014) and repository metadata:

- **Operational Rain-Gauge Protocol:** Manual and automatic rain gauges across India are read daily at **08:30 IST** (Indian Standard Time).
- **Timezone Conversion:** $\text{IST} = \text{UTC} + 05:30$. Therefore:
  $$\text{08:30 IST} = \text{03:00 UTC}$$
- **Accumulation Interval Semantics:** In the audited IMD gridded archive, date label $D$ represents the 24-hour precipitation depth accumulated from:
  $$\text{Interval}(D) = [D\text{ 08:30 IST}, (D+1)\text{ 08:30 IST}) \equiv [D\text{ 03:00 UTC}, (D+1)\text{ 03:00 UTC})$$
- **Units:** Millimetres ($\text{mm}$), missing sentinel $-999.0$, genuine dry day $0.0\text{ mm}$.

---

## 4. Day-by-Day Space-Time Mapping & Boundary Analysis

To determine whether exact $03:00\text{ UTC} \to 03:00\text{ UTC}$ aggregation can be performed within the frozen M25 record, each of the 30 calendar days was mapped against the available 720 hourly CERES observations:

### Mapping Schedule for 30-Day Window (Example: Established Monsoon, July 15 to August 13):

```
+--------+------------------+------------------------------+--------------------+----------------+-------------------------+
| Window | Calendar Date    | IMD Physical UTC Accumulation| CERES Timestamps   | Valid Available| Boundary Status         |
| Day #  | Label (D)        | Window [Start, End)          | Matched            | Hours in M25   | & Treatment             |
+--------+------------------+------------------------------+--------------------+----------------+-------------------------+
| [D-0]  | July 14 (Prior)  | Jul 14 03:00 - Jul 15 03:00  | Jul 15 00:30-02:30 | 3 hours (M25)  | EXCLUDED (Orphan hours) |
| Day 01 | July 15          | Jul 15 03:00 - Jul 16 03:00  | 07-15 03:30 - 02:30| 24 hours       | COMPLETE MATCH (100.0%) |
| Day 02 | July 16          | Jul 16 03:00 - Jul 17 03:00  | 07-16 03:30 - 02:30| 24 hours       | COMPLETE MATCH (100.0%) |
| Day 03 | July 17          | Jul 17 03:00 - Jul 18 03:00  | 07-17 03:30 - 02:30| 24 hours       | COMPLETE MATCH (100.0%) |
| ...    | ...              | ...                          | ...                | ...            | ...                     |
| Day 27 | August 10        | Aug 10 03:00 - Aug 11 03:00  | 08-10 03:30 - 02:30| 24 hours       | COMPLETE MATCH (100.0%) |
| Day 28 | August 11        | Aug 11 03:00 - Aug 12 03:00  | 08-11 03:30 - 02:30| 24 hours       | COMPLETE MATCH (100.0%) |
| Day 29 | August 12        | Aug 12 03:00 - Aug 13 03:00  | 08-12 03:30 - 02:30| 24 hours       | COMPLETE MATCH (100.0%) |
| Day 30 | August 13 (Final)| Aug 13 03:00 - Aug 14 03:00  | 08-13 03:30 - 23:30| 21 hours       | INCOMPLETE (Shortfall)  |
+--------+------------------+------------------------------+--------------------+----------------+-------------------------+
```

### Key Analytical Findings:
1. **Days 1 through 29 (29 complete days per season):**
   - Every single day possesses **exactly 24 consecutive hourly observations** in the frozen M25 record.
   - Temporal overlap with the physical IMD accumulation window is **100.0%**.
   - Zero phase shift; zero hourly missingness; zero observation synthesis.
2. **Day 1 Early Morning (3 orphan hours):**
   - July 15 00:30, 01:30, and 02:30 UTC belong to the accumulation cycle of July 14 ($D-0$), which is outside the approved 30-day window. These 3 hours cannot form a complete daily record and are excluded.
3. **Day 30 Final Hours (21 hours available, 3 hours missing):**
   - August 13 03:00 to August 14 03:00 UTC requires observations from August 14 00:30, 01:30, and 02:30 UTC.
   - In the frozen M25 record, the seasonal window terminates strictly at August 13 23:30 UTC (Hour index 719).
4. **Feasibility of Boundary Recovery from Source Data:**
   - Could the 3 missing hours of August 14 be predicted from raw CERES data?
   - While raw CERES observations for August 14 exist in cropped NetCDF files, the frozen M25 model artifacts (`combined_3season_cluster_labels.npy`) exist **strictly for the 720 seasonal hours**.
   - Predicting labels for August 14 would require executing feature scaling, PCA projection, and KMeans inference on out-of-sample data. This would violate the project charter restricting all M26 work to the frozen M25 cluster assignments.
   - Therefore, recovering out-of-window hours is **scientifically unviable without breaking the M25 freeze**.
5. **Handling the Day 30 Shortfall:**
   - Silently treating a 21-hour cloud summary as a complete 24-hour observation would artificially distort daily regime fractions and bias rainfall associations on the final day.
   - **Recommended Scientific Solution:** Formally exclude Day 30 from the primary analysis.
   - **Data Retention:** Retaining 29 complete days out of 30 preserves **96.67% of the total temporal window** while guaranteeing 100% physical temporal alignment.

---

## 5. Recalculation of Spatial Populations & Observation Counts

### Spatial Cell Classification (M25.4 Quality Policy):
- **Canonical M25 Domain:** 960 grid cells ($32 \times 30$).
- **Tier 1 Full Terrestrial Cells ($F_{\text{cov}} \ge 75\%$, $N_{\text{valid}} \ge 12$):** Exactly **328 cells**.
- **Tier 2 Coastal & Boundary Cells ($25\% \le F_{\text{cov}} < 75\%$, $4 \le N_{\text{valid}} \le 11$):** Exactly **29 cells**.
- **Total Terrestrial Footprint (Tier 1 + Tier 2):** Exactly **357 cells**.
- **Tier 3 Marginal / Insular Cells ($F_{\text{cov}} < 25\%$):** Exactly **0 cells** at $1.0^\circ$ resolution.
- **Tier 4 Marine & Foreign Structural Absence:** Exactly **603 cells** (preserved as `NaN`).

### Comprehensive Observation Count Geometry:

| Dataset / Analysis Protocol | Grid Cells | Days / Season | Obs / Year-Season | Obs / Season (12 yr) | Total Observations (36 seasons) | Status / Role |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Primary Analysis (Exact Shifted, Tier 1)** | **328** | **29** | **9,512** | **114,144** | **342,432** | **PRIMARY BENCHMARK** |
| **Sensitivity S1 (Coastal Ingestion: Tier 1 + Tier 2)** | 357 | 29 | 10,353 | 124,236 | 372,708 | Sensitivity (Tier 2 flagged) |
| *— Tier 2 Coastal Cells Alone* | *29* | *29* | *841* | *10,092* | *30,276* | Diagnostic Subset |
| **Sensitivity S2 (Calendar Day UTC, Tier 1)** | 328 | 30 | 9,840 | 118,080 | 354,240 | Temporal Sensitivity (87.5% overlap) |
| **Sensitivity S3 (Calendar Day UTC, Tier 1 + Tier 2)** | 357 | 30 | 10,710 | 128,520 | 385,560 | Legacy Abhin Baseline |
| **Sensitivity S4 (Shifted Window with Day 30 at 21h)**| 328 | 30 | 9,840 | 118,080 | 354,240 | Incomplete Day Sensitivity |
| **Structural Ocean Absences (Tier 4, 29-day)** | 603 | 29 | 17,487 | 209,844 | 629,532 | Preserved `NaN` (Zero-filling banned)|
| **Full Domain Cloud Table (29-day grid)** | 960 | 29 | 27,840 | 334,080 | 1,002,240 | Intermediate Daily Cloud Array |
| **Full Domain Cloud Table (30-day grid)** | 960 | 30 | 28,800 | 345,600 | 1,036,800 | Intermediate Daily Cloud Array |

---

## 6. Revised Scientific Methodological Decisions

### Revised D01: Daily Temporal Alignment
- **Primary Convention:** Exact IMD Shifted 24-Hour Accumulation Window ($03:00\text{ UTC } D \text{ to } 03:00\text{ UTC } D+1$) for Days 1–29.
- **Hourly Components:** 24 consecutive half-hour centered CERES observations ($\{D\text{ 03:30 \dots 23:30}\} \cup \{(D+1)\text{ 00:30 \dots 02:30}\}$).
- **Temporal Overlap:** 100.0% physical overlap with the IMD rain-gauge accumulation cycle.
- **Matched Days per Season:** Exactly 29 complete days ($1,044$ complete seasonal days across 12 years and 3 seasons).
- **Boundary Exclusions:** Day 1 early morning (00:00–03:00 UTC, 3 hours) and Day 30 (August 13 03:00–24:00 UTC, 21 hours) are excluded from the primary 24-hour analysis.
- **Sensitivity Protocol:** Compare primary results against Sensitivity S2 (UTC Calendar Day, 30 days, 87.5% overlap) and Sensitivity S4 (Shifted window including Day 30 under a 21-hour threshold).

### Revised D02: Primary Land-Cell Population
- **Primary Population:** Tier 1 Full Land Cells ($N=328$, $F_{\text{cov}} \ge 75\%$, $N_{\text{valid}} \ge 12$).
- **Primary Sample Size:** Exactly **342,432 grid-day observations**.
- **Scientific Justification:** Tier 1 cells possess full interior gauge support, minimizing spatial interpolation error and coastal boundary distortion.
- **Sensitivity Protocol:** In Sensitivity S1, ingest the 29 Tier 2 Coastal Cells ($N=357$, $372,708$ observations) with an explicit `quality_tier = 'TIER_2_COASTAL'` indicator to evaluate coastal orographic and sea-breeze rainfall impacts.

---

## 7. Reconciled Impacts on Downstream Components

1. **Statistical Inference & Sample Sizes:**
   - Primary sample size per season is $114,144$ grid-days (total $342,432$ observations).
   - Regime R2 ($1.64\%$ prevalence) contributes approximately $1,870$ primary grid-days during the Established Monsoon, providing robust statistical power for non-parametric quantiles and spatial block bootstrapping.
2. **Spatial Block Bootstrapping:**
   - Resampling grid uses contiguous $3^\circ \times 3^\circ$ spatial blocks across moving temporal blocks of 5 consecutive days within the 29-day seasonal record.
3. **Automated Test Assertions:**
   - Unit tests will assert exact observation counts: $N_{\text{primary}} = 342,432$, $N_{\text{tier2}} = 30,276$, $N_{\text{land\_total}} = 372,708$.
   - Asserts 24/24 valid hours for all primary matched records.
