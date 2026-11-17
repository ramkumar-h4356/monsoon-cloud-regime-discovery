# M27.7.1 — Partial Spearman Rank Correlation Mathematical Verification

## 1. Mathematical Formulation vs Residualized Rank Regression

The analytical partial Spearman rank correlation formula:
$$r_{xy.z} = \frac{r_{xy} - r_{xz} r_{yz}}{\sqrt{(1 - r_{xz}^2)(1 - r_{yz}^2)}}$$
was compared against independent OLS residual regression on ranked coordinates across 9 synthetic corner cases:
1. Random Gaussian variables ($N=12$): $|\Delta \rho| = 1.11 \times 10^{-16}$ (PASS)
2. Known strong positive partial association ($X = 0.8 Y + 0.5 Z + \epsilon$): $|\Delta \rho| = 0.0$ (PASS)
3. Known strong negative partial association ($X = -0.8 Y + 0.5 Z + \epsilon$): $|\Delta \rho| = 1.11 \times 10^{-16}$ (PASS)
4. Spurious correlation induced by Z (partial $\rho \approx 0$): $|\Delta \rho| = 0.0$ (PASS)
5. Heavy tied ranks with discrete integer categories: $|\Delta \rho| = 3.33 \times 10^{-16}$ (PASS)
6. Degenerate variable with zero variance: returns NaN in both implementations (PASS)
7. Missing observations (NaN handling): $|\Delta \rho| = 0.0$ (PASS)
8. Near-perfect collinearity ($X \approx Z$): returns NaN in both implementations due to zero residual variance (PASS)
9. Small sample boundary ($N=4, df=1$): $|\Delta \rho| = 0.0$ (PASS)

**Conclusion:** Maximum divergence between the analytical formula and residual regression across all valid tests is $3.33 \times 10^{-16}$, proving complete mathematical identity to double precision.

---

## 2. Independent Empirical Reproduction

All 24 seasonal partial correlations from frozen M25 prevalence and aligned climate indices were independently recomputed:
- Maximum discrepancy with M27.7 reported values: **$4.95 \times 10^{-5}$** (attributable entirely to 4-decimal rounding in source tables).
- Number of matching cases: **24 / 24 (100.0%)**.
- Output table: `reports/integration/m27_7_1/tables/m27_7_1_partial_spearman_numerical_reproduction.csv`.
