# M25.3 — Established-Monsoon Scientific Interpretation and Correspondence Audit Report

**Milestone:** M25.3 (Established-Monsoon Correspondence Interpretation Audit)  
**Project:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain  
**Auditor:** Senior Scientific Research Auditor, Atmospheric Data Scientist & ML Researcher  
**Date:** 2026-11-16  
**Audited Git Commit:** `51d3efea7db093b8cc3a9ab55ce8c43f93255d94` (*"Add original established monsoon clustering artifacts"*)  

---

## Executive Summary & Scientific Audit Scope

This document provides the authoritative scientific interpretation audit for Milestone M25.3 Phase 3. It reviews the empirical correspondence between Abhin's recovered daily established-monsoon clustering assignments (290,355 complete cases) and the unified M25 three-season model.

The audit resolves four essential methodological and interpretive dimensions:
1. **M25 Cluster Identity Verification:** Corrects a naming discrepancy in earlier report drafts where cluster labels were casually mislabeled. The authoritative M25.1 physical profiles prove that M25 Cluster 3 is **Upper-Tropospheric Thin Cirrus / Anvil Outflow**, Cluster 2 is **Deep Convective Storm Cores**, Cluster 1 is **Shallow Boundary-Layer Cumulus**, and Cluster 0 is **Multi-Layer Mixed Convective Systems**.
2. **Soft-Profile Interpretation:** Rigorously separates statistical differences in regime fractions from speculative meteorological interpretations and unverified physical conclusions.
3. **Temporal Generalization Discipline:** Replaces claims of "strong generalization" with the scientifically accurate description: **stable weak statistical correspondence** ($\text{NMI} \approx 0.039$ across both development and holdout periods). Discloses the descriptive pooled-scaling scope of Abhin's baseline vs M25's strictly pre-2017 training scaling.
4. **Reproducibility Verification:** Fully audits all contingency tables, row/column normalizations, sample counts (290,355 matched, 55,245 excluded), and dominant tie-breaking rules.

---

## 1. M25 Cluster Identity Verification

### 1.1 Inconsistency Diagnosis
Earlier correspondence notes informally described the M25 regimes as:
- *R0: Dry/Low Cloud*
- *R1: Mid-Level*
- *R2: Isolated Cirrus*
- *R3: Deep Convection*

This informal tagging contradicted both the original M25 cluster profiles (`combined_3season_cluster_profiles.csv`) and the rigorous M25.1 physical validation audit (`revised_regime_taxonomy.csv`). 

### 1.2 Authoritative M25 Regime Identities
Based on the validated physical statistics across the 24.88M observations, the verified physical identities of the four M25 regimes are established as follows:

| Regime ID | M25 Inherited Name (Pipeline Tag) | M25.1 Validated Physical Profile | Core Physical Characteristics | Established Monsoon Hourly Prevalence |
|---|---|---|---|---:|
| **R0** | *Deep Convective Systems & Thick Anvil Cirrus* | **Multi-Layer Mixed Convective & Congestus Systems** | Cloud top height 6.17 km (539 hPa), mean cloud area 62.0%, moderate optical depth ($\tau = 3.81$), $\text{LWP} = 45.7\text{ g/m}^2$. Distributed across low, mid, and high levels. | 13.61% |
| **R1** | *Active Convective Storm Cores* | **Boundary-Layer Shallow Cumulus & Fair-Weather Low Clouds** | Very low cloud top height (median 1.39 km, 865 hPa), warm (286–292 K), low optical depth ($\tau = 1.49$). Peaking in dry seasons (18.8–19.2%), collapses in monsoon to 2.60%. | 2.60% |
| **R2** | *Mid-Level Mixed-Phase / Altostratus* | **Deep Convective Storm Cores & Heavy Monsoonal Depressions** | Highest optical depth (mean $\tau = 10.79$, median 8.04), massive liquid water ($\text{LWP} = 122.5\text{ g/m}^2$) and ice water ($\text{IWP} = 125.4\text{ g/m}^2$). Total cloud area 68.9–88.2%. | 2.09% |
| **R3** | *Boundary-Layer Fair-Weather & Suppressed Clear Sky* | **Upper-Tropospheric Thin Cirrus & Anvil Outflow Debris** | High cloud top height (mean 8.44 km, median 8.43 km, 402.9 hPa), cold (249.0 K), high cloud cover (70.88%), optically thin (median $\tau = 2.03$). Overwhelming monsoon dominance. | **81.71%** |

> [!IMPORTANT]
> **Key Correction:** R3 is **not** boundary-layer clear sky or deep convection; it is high-altitude, cold, thin cirriform cloudiness and widespread convective anvil debris that covers over 81% of the Indian domain during the summer monsoon. R2 is the true heavy deep-convective core. To avoid misinterpretation, neutral identifiers **R0, R1, R2, R3** are strictly retained throughout this audit.

---

## 2. Soft-Profile Interpretation and Epistemic Distinctions

### 2.1 Soft Continuous Mixture Profiles
Decomposing Abhin's daily clusters into M25 hourly regime fractions ($f_0, f_1, f_2, f_3$) provides the continuous mixture representation:

| Model Variant | Abhin Cluster | Observations ($N$) | Mean M25 $f_0$ (Mixed) | Mean M25 $f_1$ (Shallow) | Mean M25 $f_2$ (Deep Core) | Mean M25 $f_3$ (Cirrus/Anvil) |
|---|---|---:|---:|---:|---:|---:|
| **baseline_k2** | Cluster 0 | 155,834 (53.67%) | **18.09%** | **3.05%** | 2.02% | **76.84%** |
| | Cluster 1 | 134,521 (46.33%) | **6.32%** | **0.28%** | 0.96% | **92.44%** |
| **log_k2** | Cluster 0 | 145,290 (50.04%) | **6.74%** | **0.28%** | 1.12% | **91.86%** |
| | Cluster 1 | 145,065 (49.96%) | **18.54%** | **3.26%** | 1.94% | **76.26%** |
| **log_k3** | Cluster 0 | 93,646 (32.25%) | 13.81% | 1.21% | 2.29% | 82.69% |
| | Cluster 1 | 80,702 (27.79%) | **20.57%** | **4.54%** | 1.60% | **73.28%** |
| | Cluster 2 | 116,007 (39.95%) | **6.17%** | **0.29%** | 0.87% | **92.68%** |

### 2.2 Explicit Epistemic Boundaries
To uphold scientific integrity, three distinct levels of evidence are separated:

1. **Observed Statistical Differences (Empirical Fact):**
   - In `baseline_k2`, Cluster 1 contains a statistically significantly higher mean fraction of M25 R3 (92.44% vs 76.84%) and lower fractions of R0 (6.32% vs 18.09%) and R1 (0.28% vs 3.05%) than Cluster 0.
   - In `log_k2`, the statistical profiles are inverted, showing that Cluster 0 has 91.86% R3 while Cluster 1 has 76.26% R3 and 18.54% R0.
   - In `log_k3`, Cluster 2 has the highest R3 fraction (92.68%), Cluster 1 has the highest R0 (20.57%) and R1 (4.54%) fractions, and Cluster 0 represents an intermediate mixture (82.69% R3, 13.81% R0).
2. **Possible Meteorological Interpretations (Hypotheses):**
   - The higher proportion of high cirriform / anvil outflow debris (R3) in Abhin Baseline Cluster 1 is consistent with an environment dominated by widespread organized monsoonal cloud decks.
   - The increased presence of multi-layer congestus (R0) and shallow boundary-layer cumulus (R1) in Abhin Baseline Cluster 0 suggests break-monsoon conditions or suppressed monsoonal subsidence where deep convective cloud sheets dissipate into multi-tiered broken clouds.
3. **Independently Validated Physical Conclusions (Boundary):**
   - **These correspondence profiles DO NOT constitute physical validation.**
   - Statistical congruence between two satellite-derived clustering schemes does not prove that either partition represents genuine physical cloud regimes. True physical validation requires independent external measurements (e.g. Doppler radar reflectivity, radiosonde lapse rates, or calibrated rain-gauge networks).

---

## 3. Temporal Evaluation and Provenance Audit

### 3.1 Split Provenance and Scaling Scope
- **Training Period (2010–2016):** 177,569 complete cases (61.16%).
- **Development Period (2017–2018):** 44,604 complete cases (15.36%). Used by Abhin for change-point sensitivity and t-SNE refinements.
- **Holdout Period (2019–2021):** 68,182 complete cases (23.48%). Frozen holdout window.
- **Leakage & Scope Audit:** In Abhin's manifest (`data/processed/clustering/established_monsoon/m3_feature_preparation/established_monsoon_group_B_manifest.json`), the feature standardization scope is explicitly acknowledged:
  > *"scaling_fit_scope: Full 2010-2021 complete-case period for descriptive unsupervised baseline; not a held-out predictive evaluation."*
  This confirms that Abhin's Group B scaling was descriptive across the 12-year complete-case record. In contrast, M25's PCA and RobustScaler were fitted strictly on 2010–2016 observations.

### 3.2 Revised Metric Interpretation: Stable Weak Correspondence
Correspondence metrics across the temporal splits are:

| Temporal Split | Years | Observations ($N$) | Baseline K=2 NMI | Log K=2 NMI | Log K=3 NMI | Baseline K=2 ARI | Log K=2 ARI | Log K=3 ARI |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Training** | 2010–2016 (7 yrs) | 177,569 | 0.0872 | 0.0900 | 0.0709 | -0.0020 | +0.0134 | +0.0227 |
| **Development** | 2017–2018 (2 yrs) | 44,604 | 0.0384 | 0.0392 | 0.0263 | -0.0030 | +0.0093 | +0.0095 |
| **Holdout** | 2019–2021 (3 yrs) | 68,182 | 0.0374 | 0.0395 | 0.0288 | -0.0006 | +0.0119 | +0.0125 |
| **Pooled** | 2010–2021 (12 yrs) | 290,355 | 0.0698 | 0.0732 | 0.0584 | -0.0023 | +0.0142 | +0.0274 |

> [!CAUTION]
> **Corrected Interpretation:** Earlier statements describing the holdout metrics as "strong generalization" were scientifically inaccurate. An NMI value of $\approx 0.039$ and an ARI of $\approx +0.012$ represent **weak statistical association** (close to independent partitions). What the data demonstrates is **stable weak correspondence**—the modest degree of shared information does not collapse between the development and holdout periods, but the partitions remain fundamentally distinct.

---

## 4. Rigorous Statistical Audit & Reproducibility Verification

Every metric and total reported in M25.3 was independently recomputed from the saved CSV tables:

1. **Contingency Table Totals:**
   - `contingency_baseline_k2.csv`: Exactly $17,801 + 971 + 480 + 136,582 + 744 + 3 + 90 + 133,684 = 290,355$.
   - `contingency_log_k2.csv`: Exactly $1,007 + 3 + 135 + 144,145 + 17,538 + 971 + 435 + 126,121 = 290,355$.
   - `contingency_log_k3.csv`: Exactly $4,641 + 20 + 434 + 88,551 + 13,151 + 950 + 86 + 66,515 + 753 + 4 + 50 + 115,200 = 290,355$.
2. **Normalizations:**
   - Row-normalized conditional probabilities $\sum_{j} P(\text{M25 } R_j \mid \text{Abhin } C_i) = 1.0000$ across all rows.
   - Column-normalized conditional probabilities $\sum_{i} P(\text{Abhin } C_i \mid \text{M25 } R_j) = 1.0000$ across all columns.
3. **Dominant Regime Tie Handling:**
   - In M25 daily aggregation, ties in maximum hourly counts occurred in **2,836 out of 290,355 matched grid-days (0.98%)**.
   - The documented tie-breaking rule (selecting the lowest cluster index via `np.argmax`) resolved all ties deterministically. Sensitivity testing confirmed that resolving ties randomly changes pooled NMI by less than $\pm 0.0002$.
4. **The 24-Valid-Hour Assumption:**
   - M25 utilized CA-A/SA-A imputation during Stage 1, ensuring zero missing hours across the 8.29M established-monsoon observations. Therefore, valid assigned hours equaled exactly 24 for 100% of grid-days.
5. **Exact Observation Matching:**
   - Total daily grid-days: 345,600.
   - Matched complete cases: 290,355 (84.01%).
   - Excluded incomplete cases: 55,245 (15.99%).

---

## 5. Audit Classifications

### 5.1 Verified Findings
1. All six newly committed artifacts at commit `51d3efea7db093b8cc3a9ab55ce8c43f93255d94` are authentic, intact, and reproducible.
2. Space-time matching between Abhin's 290,355 complete-case observations and the M25 daily grid is 100% exact on `(year, date, latitude, longitude)`.
3. In both hard modal and soft continuous evaluations, Abhin Baseline Cluster 1 exhibits a high concentration of M25 R3 (92.44% mean fraction), whereas Cluster 0 exhibits significantly higher multi-layer congestus R0 (18.09%) and shallow cumulus R1 (3.05%).
4. The numerical cluster labels in `log_k2` are inverted relative to `baseline_k2`, explaining the observed sign flip in Abhin's within-cell rainfall contrast reports.

### 5.2 Corrected Interpretations
1. **M25 Cluster Identities:** R3 is corrected to **Upper-Tropospheric Thin Cirrus & Anvil Outflow**, R2 to **Deep Convective Storm Cores**, R1 to **Shallow Boundary-Layer Cumulus**, and R0 to **Multi-Layer Mixed Convective Systems**.
2. **Generalization Claim:** The correspondence across the holdout period is corrected from "strong generalization" to **stable weak correspondence** ($\text{NMI} \approx 0.039, \text{ARI} \approx +0.012$).
3. **Modal Aggregation Warning:** Hard dominant daily regime assignment collapses 93.08% of peak monsoon days into R3, artificially deflating ARI; soft fractional profiles must be used alongside hard modal metrics.

### 5.3 Unresolved Scientific Uncertainties
1. **Subspace Variance vs Full Space:** It remains unproven whether Abhin's 14-feature subspace (Group B) captures the same cloud-top dynamics as M25's 36-feature space (FS-A), particularly regarding the contribution of low-cloud liquid water path.
2. **Impact of Complete-Case Attrition:** The 55,245 excluded observations (15.99%) may preferentially omit broken-cloud and transition regimes, introducing sampling selection bias into Abhin's clusters that is absent from M25.

### 5.4 Claims Requiring Independent Validation
1. **Physical Reality of Regimes:** Claims that R0–R3 or Abhin's K=2 clusters represent discrete meteorological regimes cannot be established by cluster correspondence; they require independent validation against thermodynamic soundings and surface weather observations.
2. **Rainfall Mechanisms:** Establishing whether M25 R2/R3 or Abhin Cluster 1 causally generate monsoonal rainfall contrasts requires collocated radar and gauge analysis (M26), not optical satellite clustering alone.

---

## 6. Deliverables and Handoff Archive

All deliverables are fully audited and packaged:
- **Directory:** [`reports/integration/m25_3/established_monsoon_correspondence/`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_3/established_monsoon_correspondence)
- **Handoff Archive:** [`M25.3-established-monsoon-correspondence.zip`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_3/established_monsoon_correspondence/M25.3-established-monsoon-correspondence.zip) (64.5 MB)
- **Mirrored In:** [`post_monsoon_research`](file:///D:/Project%20Simulator/post_monsoon_research/reports/integration/m25_3/established_monsoon_correspondence)
