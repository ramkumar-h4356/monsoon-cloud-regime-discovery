# M27 — Register of Documented Limitations and Unresolved Questions

**Milestone:** M27 — Integrated ENSO–IOD Climate Teleconnection and Cloud-Regime Analysis  
**Repository:** `monsoon_cloud_research`  
**Secondary Worktree:** `post_monsoon_research`  
**Evaluation Date:** 2026-11-17  
**Author:** Senior Atmospheric Data Scientist & Research Quality Officer  
**Status:** Certified & Formally Logged  

---

## 1. Executive Summary

In adherence to research transparency, this register logs the explicit methodological, statistical, observational, and computational limitations governing Milestone M27. Future milestones and downstream publications must cite these documented constraints.

---

## 2. Register of Documented Limitations

### L01 — Small Sample Size Limitation ($N = 12$ Independent Years)
* **Description:** The study period spans 2010–2021 ($N = 12$ years). With $df = 10$, bivariate Spearman rank correlation requires $|\rho| \ge 0.587$ to achieve statistical significance at $\alpha = 0.05$ ($|\rho| \ge 0.497$ at $\alpha = 0.10$).
* **Consequence:** Moderate teleconnection tendencies ($0.25 \le |\rho| < 0.45$) cannot reach formal significance, even if meteorologically real.
* **Mitigation:** M27 reports exact empirical effect sizes, bootstrap 95% confidence intervals, and Monte Carlo permutation p-values ($B = 100,000$), emphasizing physical coherence alongside significance.

### L02 — Observational and Non-Causal Association Principle
* **Description:** Milestone M27 analyzes observational associations between ocean indices, satellite-derived cloud regimes, and rain-gauge measurements.
* **Consequence:** Observed regressions and correlations cannot establish direct mechanistic causality in isolation from atmospheric dynamical models.
* **Mitigation:** All narrative reporting strictly uses non-causal language (e.g., "empirical association", "teleconnection composite", "statistical modulation") and avoids causal assertions.

### L03 — Underpowered Discrete Climate-Phase Combinations
* **Description:** Delineating continuous climate indices into discrete categories ($\text{RONI} \ge \pm 0.50^\circ\text{C}$, $\text{DMI} \ge \pm 0.40^\circ\text{C}$) results in severely unbalanced cell counts:
  * In the established monsoon, only 1 study year (2015) meets the strict El Niño threshold ($\text{RONI} \ge +0.50^\circ\text{C}$).
  * In the post-monsoon, El Niño contains only 2 years (2015, 2018).
* **Consequence:** Parametric and non-parametric two-sample hypothesis tests between discrete phase groups are severely underpowered.
* **Mitigation:** Continuous rank regressions remain the primary inferential tool. Discrete phase tables explicitly record sample sizes and mark combinations with $N < 3$ as underpowered descriptive benchmarks.

### L04 — Sub-Seasonal Temporal Representation (30-Day Windows)
* **Description:** The three frozen M25 seasonal windows cover 30 days per year:
  * Pre-Monsoon: April 15 – May 14 (Day 105–134)
  * Established Monsoon: July 15 – August 13 (Day 196–225)
  * Post-Monsoon: October 15 – November 13 (Day 288–317)
* **Consequence:** The analysis does not sample monsoon onset (late May / June) or withdrawal (September / early October). Interannual variations in onset/withdrawal dates are not captured in the 30-day fixed windows.

### L05 — Temporal Averaging Offset in Climate Indices
* **Description:** To eliminate cross-quarter serial overlap, RONI is sampled as canonical 3-month quarters (MAM, JJA, SON) and DMI as 2-month means (Apr-May, Jul-Aug, Oct-Nov).
* **Consequence:** A minor temporal offset ($\le 15$ days) exists between the 30-day cloud window and the 3-month/2-month climate index averages.
* **Mitigation:** The M27.1 audit verified that alternative 3-month running quarters (AMJ, JAS, OND) introduce post-window temporal leakage. The canonical configuration was certified as the scientifically optimal trade-off.

### L06 — Spatial Domain Masking (Terrestrial vs. Marine Extent)
* **Description:** The M25 cloud regimes were discovered across the complete 960-cell marine-terrestrial domain ($6^\circ\text{N}–38^\circ\text{N}, 68^\circ\text{E}–98^\circ\text{E}$). However, IMD daily rainfall validation is restricted to the 328 Tier 1 Indian terrestrial grid cells.
* **Consequence:** Spatial teleconnection anomaly maps and rainfall validations reflect landmass processes and do not quantify marine precipitation over the Arabian Sea and Bay of Bengal.

### L07 — Absence of Direct Vertical Radar/Lidar Microphysics
* **Description:** CERES SYN1deg Ed4.2 hourly observations provide top-of-atmosphere radiative fluxes, cloud fraction, optical depth, and cloud-top pressure, but lack active vertical radar profiling (e.g., CloudSat CPR / CALIPSO CALIOP).
* **Consequence:** Inferences regarding detailed hydrometeor phase partitions or stratiform rain fractions must rely on bulk optical/radiational regime proxies rather than in-situ microphysics.

---

## 3. Unresolved Questions for Future Investigation

1. **Pacemaker GCM Simulations:** Would atmospheric general circulation model (AGCM) experiments forced by observed 2015 Pacific vs. Indian Ocean SSTs reproduce the exact partial teleconnection dipole between R0 and R3?
2. **Sub-Daily Diurnal Cycle Shifts:** Does El Niño alter the diurnal timing of convective initiation (e.g., delaying peak afternoon convection) in addition to reducing daily mean rainfall?
3. **Decadal Non-Stationarity:** How do the teleconnections discovered in the 2010–2021 satellite era compare with earlier decades (e.g., 1980–2000), given ongoing global warming and shifts in Indian Ocean baseline SSTs?
