# M27.7 — Partial Spearman Rank Correlation and Multiplicity Audit

## 1. Mathematical Formulation and Equivalence Verification

Partial Spearman rank correlation assesses the monotonic relationship between regime prevalence ($X$) and a primary climate index ($Y$), while controlling for the confounding influence of an intervening climate mode ($Z$):
$$r_{xy.z} = \frac{r_{xy} - r_{xz} r_{yz}}{\sqrt{(1 - r_{xz}^2)(1 - r_{yz}^2)}}$$

where $r_{uv}$ represents the Spearman rank correlation between variables $u$ and $v$.

### Equivalence to Rank-Residual Regression
In linear regression of ranked variables, let $e_{x|z}$ and $e_{y|z}$ be the ordinary least squares residuals:
$$e_{x|z} = \text{rank}(X) - \hat{\beta}_x \text{rank}(Z)$$
$$e_{y|z} = \text{rank}(Y) - \hat{\beta}_y \text{rank}(Z)$$

The Pearson correlation between $e_{x|z}$ and $e_{y|z}$ is mathematically identical to $r_{xy.z}$.

### Empirical Verification Result
- Across all 32 seasonal and pooled partial correlation tests in M27, the maximum absolute difference between the analytical formula and rank-residual regression was:
  $$\max |\Delta \rho| = 0.0000000000000000$$
- Across all tests, recalculated partial Spearman values matched original M27 values to machine precision ($|\Delta \rho| < 10^{-6}$).

---

## 2. Exchangeability and Null Hypothesis Testing (Freedman-Lane Permutation)

In partial correlation testing with sample size $N=12$, naive permutation of $X$ destroys the variance structure shared with the covariate $Z$. 
The audit implemented the **Freedman-Lane permutation scheme** ($B = 100,000$ iterations):
1. Fit linear model of $\text{rank}(X)$ on $\text{rank}(Z)$, obtaining fitted values $\hat{X}$ and residuals $e_{x|z}$.
2. Permute the exchangeable residuals $e_{x|z}^{(b)}$.
3. Construct synthetic responses $X^{(b)} = \hat{X} + e_{x|z}^{(b)}$.
4. Compute $r_{x^{(b)}y.z}$.
5. Compute the empirical two-tailed p-value.

Analytical Student's $t$ p-values with $df = N - 3 = 9$ degrees of freedom were also computed:
$$t = r_{xy.z} \sqrt{\frac{df}{1 - r_{xy.z}^2}}$$

---

## 3. Multiple Testing Correction and Empirical Verdicts

Original M27 conducted 8 partial tests per season (4 regimes $\times$ 2 climate indices). Applying the Benjamini-Hochberg False Discovery Rate (BH-FDR) within each season yields definitive scientific classifications:

### Established Monsoon (Season 1) — ROBUSTLY CONFIRMED
In established monsoon, **four partial teleconnections achieve statistical significance after rigorous FDR correction ($q_{\text{FDR}} \le 0.05$)**:
- **R0 vs RONI | DMI:** $\rho = +0.7028$, $p_{\text{perm}} = 0.0112$, $q_{\text{FDR}} = 0.0223$ (**CONFIRMED STATISTICALLY SIGNIFICANT**)
- **R3 vs RONI | DMI:** $\rho = -0.7871$, $p_{\text{perm}} = 0.0034$, $q_{\text{FDR}} = 0.0223$ (**CONFIRMED STATISTICALLY SIGNIFICANT**)
- **R0 vs DMI | RONI:** $\rho = -0.7261$, $p_{\text{perm}} = 0.0101$, $q_{\text{FDR}} = 0.0223$ (**CONFIRMED STATISTICALLY SIGNIFICANT**)
- **R3 vs DMI | RONI:** $\rho = +0.7492$, $p_{\text{perm}} = 0.0056$, $q_{\text{FDR}} = 0.0223$ (**CONFIRMED STATISTICALLY SIGNIFICANT**)

### Pre-Monsoon (Season 0) — DOWNGRADED TO EXPLORATORY
- **R0 vs DMI | RONI:** Original M27 reported unadjusted $p = 0.0236$. However, after adjusting for the 8 seasonal tests, **$q_{\text{FDR}} = 0.1887 > 0.10$**.
- **Audit Decision:** **CORRECTION REQUIRED: DOWNGRADE TO EXPLORATORY**. This association does not meet the standard threshold for statistical discovery.

### Post-Monsoon (Season 2) — DOWNGRADED TO EXPLORATORY
- **R2 vs DMI | RONI:** Original M27 reported unadjusted $p = 0.0340$. After adjusting for 8 seasonal tests, **$q_{\text{FDR}} = 0.2722 > 0.10$**.
- **Audit Decision:** **CORRECTION REQUIRED: DOWNGRADE TO EXPLORATORY**.

### Summary of Audit Classifications
| Season | Hypotheses Tested | Confirmed Significant ($q \le 0.05$) | Exploratory Tendency ($p \le 0.05, q > 0.05$) | Confirmed Non-Significant |
| :--- | :---: | :---: | :---: | :---: |
| Pre-Monsoon | 8 | 0 | 1 (R0 vs DMI) | 7 |
| Established Monsoon | 8 | 4 (R0, R3 vs RONI & DMI) | 0 | 4 |
| Post-Monsoon | 8 | 0 | 1 (R2 vs DMI) | 7 |
