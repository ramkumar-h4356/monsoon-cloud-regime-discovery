# M27.1 — Scientific Methodology Proposal for Climate-Mode Teleconnections (M27)

**Milestone:** M27.1 — NOAA RONI and DMI Climate-Index Audit and Repository Integration Planning  
**Evaluation Date:** 2026-11-17  
**Auditor:** Senior Atmospheric Data Scientist & Research Methodologist  
**Parent Framework:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain  

---

## 1. Research Objectives and Scope

Milestone M27 investigates the large-scale climate dynamics governing the interannual variability of the four frozen M25 cloud regimes (R0, R1, R2, R3) and their associated surface rainfall signatures (validated in M26) across the Indian subcontinent.

The research framework addresses six central scientific questions:
1. **ENSO-Regime Teleconnection:** Does the El Niño–Southern Oscillation (measured by NOAA RONI) systematically modulate the seasonal occurrence frequency of convective (R2/R0) versus suppressed (R1) cloud regimes?
2. **IOD-Regime Teleconnection:** Does the Indian Ocean Dipole (measured by NOAA DMI) modulate cloud-regime prevalence, particularly during its peak boreal autumn phase?
3. **ENSO-Rainfall Modulation:** How do El Niño and La Niña phases alter total seasonal terrestrial rainfall and wet-day probabilities over the 328 Tier 1 Indian grid cells?
4. **IOD-Rainfall Modulation:** How do positive and negative IOD phases modulate regional monsoon precipitation?
5. **Conditional Regime–Rainfall Changes:** Does the rainfall efficiency of individual regimes change under different climate states (e.g., does convective R2 produce more or less rain per occurrence during El Niño vs. La Niña)?
6. **Joint Climate Interaction:** How do co-occurring ENSO and IOD modes (e.g., 2015 El Niño + Positive IOD vs. 2010 La Niña + Negative IOD vs. 2019 pure Super-IOD) jointly reinforce or counteract cloud-regime anomalies?

---

## 2. Consumed Frozen Artifacts (Zero-Mutation Policy)

Milestone M27 strictly consumes frozen outputs from M25 and M26 without modification:

| Artifact Identifier | Canonical Path | Description | Milestone Origin |
| :--- | :--- | :--- | :---: |
| `combined_3season_cluster_labels.npy` | `data/processed/combined_3season/` | 24,883,200 frozen hourly K=4 cluster labels | M25 (Frozen) |
| `combined_3season_years.npy` | `data/processed/combined_3season/` | Hourly observation year identifiers (2010–2021) | M25 (Frozen) |
| `combined_3season_season_ids.npy` | `data/processed/combined_3season/` | Hourly season identifiers (0=Pre, 1=Est, 2=Post) | M25 (Frozen) |
| `m26_daily_regime_aggregation_primary.parquet` | `data/processed/rainfall_validation/` | 1,002,240 grid-day aggregated regime counts/fractions | M26 (Frozen) |
| `m26_cloud_rainfall_matched_primary.parquet` | `data/processed/rainfall_validation/` | 342,432 Tier 1 matched regime-rainfall records | M26 (Frozen) |
| `m26_regime_rainfall_by_year.csv` | `reports/integration/m26/tables/` | Annual regime prevalence and rainfall summary table | M26 (Frozen) |
| `m26_spatial_regime_rainfall_by_cell.csv` | `reports/integration/m26/tables/` | Cell-wise spatial regime frequency and rainfall rates | M26 (Frozen) |

---

## 3. Methodological Workflow Design

### 3.1 Aggregation to Annual-Seasonal Units
To prevent pseudoreplication and false degrees of freedom, the primary statistical unit is the **annual seasonal summary** ($N = 12$ years per season):
1. **Regime Occurrence Fraction:**
   $$P(R_k \mid y, s) = \frac{\sum_{i \in (y, s)} \mathbb{I}(d_i = k)}{N_{\text{obs}}(y, s)}$$
2. **Seasonal Terrestrial Mean Rainfall:**
   $$\bar{R}(y, s) = \frac{1}{N_{\text{obs}}(y, s)} \sum_{i \in (y, s)} R_i$$
3. **Regime Conditional Mean Rainfall:**
   $$\bar{R}_k(y, s) = \frac{\sum_{i \in (y, s), d_i = k} R_i}{\sum_{i \in (y, s)} \mathbb{I}(d_i = k)}$$

### 3.2 Phase Categorization Framework
While continuous regressions remain primary, categorical phases will be delineated using internationally recognized operational thresholds:
* **ENSO Phases (RONI Canonical Quarter):**
  * **El Niño (Warm Phase):** $\text{RONI} \ge +0.50^\circ\text{C}$
  * **Neutral Phase:** $-0.50^\circ\text{C} < \text{RONI} < +0.50^\circ\text{C}$
  * **La Niña (Cold Phase):** $\text{RONI} \le -0.50^\circ\text{C}$
* **IOD Phases (DMI Bi-Monthly Mean):**
  * **Positive IOD:** $\text{DMI} \ge +0.40^\circ\text{C}$
  * **Neutral IOD:** $-0.40^\circ\text{C} < \text{DMI} < +0.40^\circ\text{C}$
  * **Negative IOD:** $\text{DMI} \le -0.40^\circ\text{C}$

### 3.3 Continuous and Partial Correlation Analysis
Because ENSO and IOD are partially coupled via Walker circulation shifts, M27 will compute both simple and partial non-parametric correlations:
1. **Spearman Rank Correlation:** $\rho(P(R_k), \text{RONI})$ and $\rho(P(R_k), \text{DMI})$.
2. **Partial Spearman Correlation:**
   $$\rho_{\text{partial}}(P(R_k), \text{RONI} \mid \text{DMI}) = \frac{\rho_{R, \text{RONI}} - \rho_{R, \text{DMI}} \rho_{\text{RONI}, \text{DMI}}}{\sqrt{(1 - \rho_{R, \text{DMI}}^2)(1 - \rho_{\text{RONI}, \text{DMI}}^2)}}$$
   Isolating the independent Pacific teleconnection from the equatorial Indian Ocean dipole state.

### 3.4 Spatial Teleconnection Composite Mapping
For each of the 328 Tier 1 grid cells ($j = 1, \dots, 328$), compute spatial anomaly composites:
$$\Delta P_j(R_k) = \overline{P}_j(R_k \mid \text{El Niño}) - \overline{P}_j(R_k \mid \text{La Niña})$$
$$\Delta \bar{R}_j = \bar{R}_j(\text{El Niño}) - \bar{R}_j(\text{La Niña})$$
Mapping geographic dipole structures across the Indian landmass (e.g., Northwest suppression vs. Southeast coastal response).

---

## 4. Methodological Safeguards

1. **No Causal Inferences from Small Sample Size:** With $N = 12$ years, statistical associations must be presented as descriptive teleconnection composites, avoiding definitive causal assertions.
2. **Exact Resampling Inference:** P-values for 12-point correlations must be verified using exact permutation tests ($12!$ permutations) rather than asymptotic t-distributions.
3. **Invariance Checks:** Sensitivity to alignment conventions (Option D1 vs D2; Option R1 vs R2/R3) must be systematically reported.

---

## 5. Audit Verdict

$$\mathbf{VERDICT:}\quad \textbf{VERIFIED — SCIENTIFIC METHODOLOGY PROPOSAL QUALIFIED AND APPROVED}$$
