# M27.1 — Statistical Analysis Design and Small-Sample Inference Framework

**Milestone:** M27.1 — NOAA RONI and DMI Climate-Index Audit and Repository Integration Planning  
**Evaluation Date:** 2026-11-17  
**Auditor:** Senior Atmospheric Data Scientist & Statistical Reviewer  
**Focus:** Statistical Rigor, Sample-Size Limitations ($N=12$), and Resampling Inference  

---

## 1. Executive Summary

A critical challenge in interannual climate-mode teleconnection analysis is the finite sample size of the satellite-gauge era. For the 2010–2021 study period, the primary independent statistical unit is the **annual seasonal window** ($N = 12$ years).

Treating daily observations ($N = 342,432$) as independent degrees of freedom against slowly varying interannual ocean indices is a fatal pseudoreplication error. This document establishes the formal statistical testing protocol for Milestone M27, specifying exact permutation tests, rank correlations, multiple testing corrections, and compositional constraints tailored specifically to $N = 12$.

---

## 2. Sample Size and Statistical Power ($N = 12$)

### 2.1 Degrees of Freedom & Critical Correlation Thresholds
For a bivariate rank correlation with $N = 12$ independent years:
* Degrees of Freedom: $df = N - 2 = 10$.
* **Two-Tailed Critical Thresholds (Spearman Rank Correlation $\rho$):**
  * At $\alpha = 0.10$ level: $|\rho_{\text{crit}}| \approx 0.497$.
  * At $\alpha = 0.05$ level: $|\rho_{\text{crit}}| \approx 0.587$.
  * At $\alpha = 0.01$ level: $|\rho_{\text{crit}}| \approx 0.727$.
* **Statistical Power Implication:** With $N = 12$, only moderate-to-strong teleconnection signals ($|\rho| \ge 0.50$) will achieve formal statistical significance at $\alpha = 0.05$. Weak teleconnection tendencies ($0.20 \le |\rho| < 0.45$) will not reach significance, even if meteorologically real. Therefore, M27 must emphasize **effect sizes, physical coherence, and cross-season consistency** alongside p-values.

### 2.2 Exact Permutation Testing Protocol
Asymptotic Student's t-distributions for Pearson/Spearman correlations rely on large-sample central limit behavior that is imperfect at $N = 12$.
* **M27 Permutation Protocol:** All p-values will be evaluated via Monte Carlo permutation testing with $B = 100,000$ random shuffles of the climate index vector:
  $$\hat{p}_{\text{perm}} = \frac{1 + \sum_{b=1}^B \mathbb{I}(|\rho_b| \ge |\rho_{\text{observed}}|)}{B + 1}$$
* This provides exact finite-sample significance testing with empirical resolution down to $p \approx 0.00001$.

---

## 3. Phase Stratification and Contrast Testing

When comparing discrete phases (e.g., El Niño years vs. La Niña years):
* **Sample Allocation:**
  * In the established monsoon (JJA): El Niño ($N = 2$; 2012, 2015); Neutral ($N = 4$; 2014, 2018, 2019, 2011); La Niña ($N = 6$; 2010, 2013, 2016, 2017, 2020, 2021).
  * In the post-monsoon (SON): El Niño ($N = 3$; 2014, 2015, 2018); Neutral ($N = 2$; 2012, 2019); La Niña ($N = 7$; 2010, 2011, 2013, 2016, 2017, 2020, 2021).
* **Non-Parametric Rank-Sum Test:** Because subgroup sample sizes are small ($N_1 = 2, N_2 = 6$), standard parametric two-sample t-tests are invalid. M27 will employ the **Mann-Whitney U test** (Wilcoxon rank-sum) and exact two-group permutation tests.

---

## 4. Compositional Simplex Constraint in Climate Teleconnections

Because regime occurrence fractions across any seasonal window sum to unity:

$$\sum_{k=0}^3 P(R_k) = 1.0 \implies \sum_{k=0}^3 \Delta P(R_k) = 0.0$$

Any climate-induced modulation of cloud regimes is strictly zero-sum:
1. If El Niño suppresses deep convection ($\Delta P(R_2) < 0$) and congestus clouds ($\Delta P(R_0) < 0$), it **must** be compensated by an increase in shallow cumulus ($\Delta P(R_1) > 0$) or cirrus/anvil matrices ($\Delta P(R_3) > 0$).
2. Correlations between an index and regime fractions cannot be treated as four independent tests.
3. M27 will report **compositional anomaly vectors**:
   $$\vec{\Delta} P = [\Delta P(R_0), \Delta P(R_1), \Delta P(R_2), \Delta P(R_3)]^T$$
   verifying that $\sum \Delta P = 0$.

---

## 5. Multiple Hypothesis Testing Correction

Testing 4 regimes across 3 seasons against 2 climate indices generates $4 \times 3 \times 2 = 24$ correlation hypotheses.
* Uncorrected testing at $\alpha = 0.05$ risks $24 \times 0.05 \approx 1.2$ false-positive discoveries.
* **Correction Procedure:** M27 will apply the **Benjamini-Hochberg (1995) False Discovery Rate (FDR)** procedure at $q = 0.10$ across each seasonal family of hypotheses, reporting both raw permutation p-values ($p_{\text{raw}}$) and FDR-adjusted q-values ($q_{\text{FDR}}$).

---

## 6. Spatial Composite Stability and Field Significance

To determine whether mapped spatial composite patterns across the 328 Tier 1 grid cells represent physical signal rather than spatial noise:
1. **Field Significance Test:** Compute the percentage of grid cells displaying locally significant teleconnection anomalies ($p_j \le 0.05$). Compare this area against the binomial null expectation ($5\%$).
2. **Year-Resampling Bootstrap:** Execute $B = 1,000$ year-level bootstrap resamples ($N = 12$ years resampled with replacement) to construct 95% spatial confidence intervals for grid-cell anomalies.

---

## 7. Audit Verdict

$$\mathbf{VERDICT:}\quad \textbf{VERIFIED — STATISTICAL ANALYSIS DESIGN FULLY SPECIFIED}$$
