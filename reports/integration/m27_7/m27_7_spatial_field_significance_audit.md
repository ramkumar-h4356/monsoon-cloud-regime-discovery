# M27.7 — Spatial Field Significance and Autocorrelation Audit

## 1. Problem Definition: The Spatial Autocorrelation Hazard

Milestone M27 examined spatial teleconnections across 328 Tier 1 terrestrial 1° grid cells over India.
To assess continental field significance, original M27 evaluated the number of locally significant cells ($p \le 0.05$) against a binomial distribution:
$$p_{\text{field}} = \sum_{k = K_{\text{obs}}}^{328} \binom{328}{k} (0.05)^k (0.95)^{328 - k}$$

This binomial formulation assumes that each of the 328 cells represents an independent Bernoulli trial.
However, in atmospheric and climate physics, **spatial autocorrelation is pervasive**. Precipitation systems, monsoon troughs, and synoptic depressions span hundreds to thousands of kilometers. A single weather pattern naturally induces correlated responses across dozens of contiguous grid cells.

As demonstrated by Livezey and Chen (1983), strong spatial autocorrelation dramatically inflates the variance of nominally significant grid points under the null hypothesis, rendering naive binomial p-values orders of magnitude too liberal.

---

## 2. Livezey-Chen / Walker Year-Level Spatial Permutation Test

To preserve the true spatial covariance structure, the audit implemented the **Livezey-Chen spatial permutation test** ($B = 5,000$ iterations):
1. The entire spatial field of all 328 grid cells is held fixed for each year, preserving 100% of the cross-cell spatial covariance and spatial autocorrelation.
2. The 12 annual climate index anomalies are uniformly permuted across years.
3. At each permutation $b$, cell-wise Spearman correlations are computed for all 328 cells, and the count of locally significant cells ($K^{(b)}$) is recorded.
4. The empirical field p-value is:
   $$p_{\text{field, LC}} = \frac{1 + \sum_{b=1}^B \mathbb{I}(K^{(b)} \ge K_{\text{obs}})}{B + 1}$$
5. The 95th percentile null expectation ($K_{\text{null, 95}}$) is derived directly from the empirical null distribution.

---

## 3. Audit Findings Across All 12 Spatial Tests

| Season | Spatial Field Test | Observed Significant Cells ($K_{\text{obs}}$) | Significant % | Naive Binomial $p$ | Livezey-Chen 95th Pct Null ($K_{\text{null, 95}}$) | Livezey-Chen $p_{\text{field}}$ | Audit Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Established Monsoon** | **Rainfall vs RONI** | **35** | **10.67%** | **0.00002 (Sig)** | **39.0 cells** | **0.07219** | **DOWNGRADED_OVERSTATEMENT** |
| Established Monsoon | Rainfall vs DMI | 7 | 2.13% | 0.99743 | 41.0 cells | 0.84823 | CONFIRMED_NON_SIGNIFICANT |
| Established Monsoon | R2 Convection vs RONI | 7 | 2.13% | 0.99743 | 40.0 cells | 0.83563 | CONFIRMED_NON_SIGNIFICANT |
| Established Monsoon | R2 Convection vs DMI | 4 | 1.22% | 0.99995 | 40.0 cells | 0.96041 | CONFIRMED_NON_SIGNIFICANT |
| **Pre-Monsoon** | **R2 Convection vs DMI** | **78** | **23.78%** | **0.00000 (Sig)** | **42.0 cells** | **0.02020** | **CONFIRMED_FIELD_SIGNIFICANT** |
| Pre-Monsoon | Rainfall vs RONI | 12 | 3.66% | 0.89760 | 36.0 cells | 0.64687 | CONFIRMED_NON_SIGNIFICANT |
| Pre-Monsoon | Rainfall vs DMI | 13 | 3.96% | 0.83871 | 37.0 cells | 0.59108 | CONFIRMED_NON_SIGNIFICANT |
| Pre-Monsoon | R2 Convection vs RONI | 7 | 2.13% | 0.99743 | 38.0 cells | 0.71386 | CONFIRMED_NON_SIGNIFICANT |
| Post-Monsoon | Rainfall vs RONI | 15 | 4.57% | 0.67416 | 41.0 cells | 0.34213 | CONFIRMED_NON_SIGNIFICANT |
| Post-Monsoon | Rainfall vs DMI | 1 | 0.30% | 1.00000 | 39.0 cells | 0.94421 | CONFIRMED_NON_SIGNIFICANT |
| Post-Monsoon | R2 Convection vs RONI | 15 | 4.57% | 0.67416 | 40.0 cells | 0.32833 | CONFIRMED_NON_SIGNIFICANT |
| Post-Monsoon | R2 Convection vs DMI | 17 | 5.18% | 0.47466 | 42.0 cells | 0.27554 | CONFIRMED_NON_SIGNIFICANT |

---

## 4. Key Scientific Corrections

### 1. Established Monsoon Rainfall vs RONI: Downgraded
- Original M27 declared a continental-scale teleconnection discovery with naive binomial $p = 0.00002$.
- Under Livezey-Chen permutation accounting for spatial autocorrelation, the 95th percentile null threshold is **39.0 cells** (11.9%). The observed 35 cells (10.7%) yields **$p_{\text{field, LC}} = 0.07219 > 0.05$**.
- **Correction:** Established monsoon rainfall teleconnection to RONI does **not** achieve field significance at $\alpha = 0.05$. It must be documented as an **exploratory regional tendency**, not an established continental teleconnection.

### 2. Pre-Monsoon R2 Convection vs DMI: Confirmed Robust
- Observed significant cells: **78 cells** (23.78%), far exceeding the 95th percentile null expectation of 42.0 cells.
- Livezey-Chen empirical field p-value: **$p_{\text{field, LC}} = 0.02020 \le 0.05$**.
- **Confirmation:** Robust spatial teleconnection confirmed. Positive DMI suppresses pre-monsoon convective storm cores across central and eastern India.
