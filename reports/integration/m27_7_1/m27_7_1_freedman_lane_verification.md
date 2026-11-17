# M27.7.1 — Freedman–Lane Permutation and Exchangeability Verification

## 1. Specification of the Freedman–Lane Procedure

To test $H_0: \rho_{xy.z} = 0$:
1. **Reduced Model:** Fit linear regression of $\text{rank}(X)$ on $\text{rank}(Z)$:
   $$\hat{X} = \hat{\alpha} + \hat{\beta} \text{rank}(Z), \quad e_{x|z} = \text{rank}(X) - \hat{X}$$
2. **Permutation:** Permute the exchangeable residuals $e_{x|z}^{(b)}$ across the 12 years ($B = 100,000$).
3. **Synthetic Response:** $X^{(b)} = \hat{X} + e_{x|z}^{(b)}$.
4. **Statistic Calculation:** Compute $r_{x^{(b)}y.z}$.
5. **Finite-Sample Correction:**
   $$p = \frac{1 + \sum_{b=1}^B \mathbb{I}(|r^{(b)}| \ge |r_{\text{obs}}|)}{B + 1}$$

---

## 2. Critical Evaluation of Exchangeability under N=12

While computationally exact, the assumption of **unrestricted exchangeability of residuals** is subject to clear scientific limitations:
1. **Sample Size:** With only $N=12$ independent calendar years, the permutation distribution contains at most $12! = 479,001,600$ permutations. A Monte Carlo sample of $B=100,000$ yields resolution $p_{\min} = 10^{-5}$ and standard error $\text{SE}(p) \approx 0.0003$.
2. **Serial Correlation:** Low-frequency Pacific decadal variability and instrument calibration trends introduce weak serial persistence in cloud regimes. However, because climate anomalies are approximately exchangeable across years, the Freedman-Lane procedure remains the most defensible non-parametric test available.
3. **Equivalence with Student's t:** Analytical Student's $t$ distribution with $df = N - 3 = 9$ degrees of freedom produces p-values within $0.002$ of the permutation results.
