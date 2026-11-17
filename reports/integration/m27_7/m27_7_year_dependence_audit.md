# M27.7 — Temporal Dependence and Cross-Seasonal Pooling Audit

## 1. Problem Definition: The Pseudo-Replication Fallacy in Seasonal Pooling

In Milestone M27, a pooled cross-seasonal analysis was conducted across 36 observations:
$$N = 12 \text{ calendar years} \times 3 \text{ seasons} = 36 \text{ observations}$$

Original M27 treated these 36 points as independent observations ($df = 34$), calculating naive permutation and parametric p-values.

However, the three seasons within any given calendar year (pre-monsoon, established monsoon, post-monsoon):
1. Evolve under the same multi-year ENSO/IOD phase cycle (e.g. 2015 El Niño, 2010 La Niña).
2. Share identical interannual low-frequency atmospheric and sea-surface temperature anomalies.
3. Share long-term instrument calibration, decadal trends, and background states.

---

## 2. Intra-Year Persistence and Effective Degrees of Freedom

The audit quantified intra-year cross-seasonal Pearson correlations ($r_{\text{pre,est}}$, $r_{\text{est,post}}$, $r_{\text{pre,post}}$) across the 12 calendar years:

| Variable | $r_{\text{pre,est}}$ | $r_{\text{est,post}}$ | $r_{\text{pre,post}}$ | Mean Intra-Year $r$ | Variance Inflation Factor (VIF) | Effective Sample Size ($N_{\text{eff}}$) | Effective $df$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **R0 Prevalence** | **+0.930** | **+0.744** | **+0.835** | **+0.836** | **2.67** | **13.5** | **11.5** |
| R1 Prevalence | +0.296 | -0.037 | +0.351 | +0.203 | 1.41 | 25.6 | 23.6 |
| R2 Prevalence | -0.096 | -0.411 | +0.775 | +0.089 | 1.18 | 30.6 | 28.6 |
| R3 Prevalence | +0.475 | +0.270 | +0.589 | +0.444 | 1.89 | 19.1 | 17.1 |

### Critical Finding: Severe Degrees-of-Freedom Deficit for R0
For R0 prevalence, the mean intra-year cross-seasonal correlation is **+0.836**!
- The true effective sample size is **$N_{\text{eff}} = 13.5$**, not 36!
- The effective degrees of freedom is **$df_{\text{eff}} = 11.5$**, representing a **66% loss of independent statistical information**.

---

## 3. Year-Block Permutation Testing

To evaluate pooled statistical significance without violating temporal exchangeability, the audit implemented a **Year-Block Permutation Test** ($B = 100,000$ iterations):
- The 12 calendar year triplets are permuted as intact coherent blocks.
- This preserves the intra-year multi-seasonal covariance matrix while breaking the connection between calendar years and climate index forcing.

### Results on Original M27 Pooled "Significant" Discoveries:
In original M27, R0 vs DMI in the pooled dataset was declared significant:
- Original naive permutation: $p_{\text{naive}} = 0.00351$, reported $q_{\text{FDR}} = 0.01404$ (Claimed Significant).
- **M27.7 Year-Block Permutation:** **$p_{\text{block}} = 0.01248$**.
- **$N_{\text{eff}}$-adjusted parametric p-value:** **$p_{\text{adj}} = 0.0911$**.
- **FDR correction across pooled hypotheses:** **$q_{\text{FDR}} = 0.24960 > 0.10$**!

### Audit Verdict:
- **CORRECTION REQUIRED: DOWNGRADE TO EXPLORATORY TENDENCY / NON-ROBUST**.
- The apparent significance of pooled R0 vs DMI was an artifact of pseudo-replication caused by treating 36 non-independent seasonal observations as independent random samples.
