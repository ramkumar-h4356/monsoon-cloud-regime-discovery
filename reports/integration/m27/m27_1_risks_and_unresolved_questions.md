# M27.1 — Scientific Risks, Vulnerabilities, and Unresolved Questions

**Milestone:** M27.1 — NOAA RONI and DMI Climate-Index Audit and Repository Integration Planning  
**Evaluation Date:** 2026-11-17  
**Auditor:** Senior Atmospheric Data Scientist & Scientific Validation Auditor  
**Parent Framework:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain  

---

## 1. Executive Summary

Milestone M27 introduces interannual climate-mode variability into the established M25/M26 cloud-regime and rainfall validation architecture. Because the research period (2010–2021) contains 12 years of CERES and IMD observations, several distinct physical, statistical, and operational risks must be proactively cataloged, bounded, and mitigated prior to executing full statistical modeling.

---

## 2. Risk Matrix and Mitigation Architecture

| Risk ID | Category | Nature of Risk | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :---: | :--- |
| **RSK-M27-01** | Sample Size | **Small-N Statistical Power ($N=12$):** Bivariate rank correlation requires $|\rho| \ge 0.587$ for significance at $\alpha = 0.05$. Moderate teleconnection tendencies ($|\rho| \sim 0.35$) will fail significance thresholds. | **HIGH** | Use continuous Spearman rank correlations, exact Monte Carlo permutation tests ($B = 100,000$), and prioritize effect sizes and cross-season physical coherence over p-value thresholds alone. |
| **RSK-M27-02** | Single-Year Leverage | **Outlier Dominance (2015 Super El Niño & 2019 Super IOD):** Extreme individual years could exert disproportionate leverage on linear fits. | **HIGH** | Implement mandatory Leave-One-Out (LOO) sensitivity analyses, testing whether correlation signs and significance persist when omitting 2015 or 2019. |
| **RSK-M27-03** | Teleconnection Coupling | **ENSO–IOD Collinearity:** ENSO and IOD co-occur in key years (e.g., 2015 El Niño + pIOD; 2016 La Niña + nIOD), making univariable correlations ambiguous. | **MEDIUM** | Formally compute **Partial Spearman Correlations**, measuring the isolated ENSO effect holding DMI constant, and the isolated IOD effect holding RONI constant. |
| **RSK-M27-04** | Phase Asymmetry | **La Niña Overrepresentation:** The 2010–2021 period features 6–7 La Niña seasons but only 2–3 El Niño seasons, creating an unbalanced discrete phase comparison. | **MEDIUM** | Emphasize **continuous index regressions** across the full span of RONI ($-1.63^\circ\text{C}$ to $+2.25^\circ\text{C}$) as the primary benchmark, using discrete phase composites as secondary diagnostics. |
| **RSK-M27-05** | Seasonal Lag | **IOD Inactivity in Pre-Monsoon:** Indian Ocean Dipole dynamics are physically dormant during April–May ($\text{std } = 0.25^\circ\text{C}$). | **LOW** | Focus primary IOD hypotheses on the Established Monsoon and Post-Monsoon windows, explicitly documenting pre-monsoon IOD dormancy. |
| **RSK-M27-06** | Spatial Correlation | **False Discoveries in Field Maps:** Mapped spatial composites across 328 grid cells may exhibit false positive patches due to spatial autocorrelation. | **MEDIUM** | Apply Walker field-significance testing and binomial area exceedance criteria against the null expectation. |

---

## 3. Unresolved Scientific Questions & Recommended Decisions

### Question 1: Should M27 rely primarily on continuous index correlations or discrete phase binning?
* **Scientific Trade-Off:** Discrete binning (El Niño vs. La Niña) creates unbalanced groups ($N_{\text{El Niño}} = 2$ vs. $N_{\text{La Niña}} = 6$ in summer), severely reducing two-sample statistical power. Continuous correlation utilizes all 12 years along the full gradient of oceanic forcing.
* **Recommended Decision:** **Continuous rank correlation (Spearman $\rho$) is the primary benchmark**. Discrete phase composites will serve strictly as illustrative secondary diagnostics.

### Question 2: How should the influential 2015 Super El Niño be treated?
* **Scientific Trade-Off:** Excluding 2015 discards the most intense physical forcing event of the modern era, but retaining it could drive linear trends single-handedly.
* **Recommended Decision:** **Retain 2015 in all primary models**, but mandate a formal **Jackknife Leave-One-Out (LOO) diagnostic table** reporting all correlations with 2015 removed.

### Question 3: Should regional spatial sub-zoning be introduced in M27?
* **Scientific Trade-Off:** Indian monsoon rainfall exhibits distinct regional teleconnections (e.g., Central India vs. Northeast India vs. Southern Peninsula). However, post-project sub-zoning could alter the canonical 328-cell analysis grid established in M25/M26.
* **Recommended Decision:** **Preserve the canonical 328-cell Tier 1 terrestrial grid**. Report spatial composite maps cell-wise, and compute regional summaries only as secondary descriptive roll-ups without altering the primary analysis population.

---

## 4. Audit Verdict

$$\mathbf{VERDICT:}\quad \textbf{VERIFIED — RISKS IDENTIFIED AND MITIGATION FRAMEWORK RATIFIED}$$
