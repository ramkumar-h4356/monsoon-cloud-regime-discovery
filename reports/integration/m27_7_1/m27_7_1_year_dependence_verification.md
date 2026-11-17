# M27.7.1 — Temporal Dependence and Year-Block Permutation Verification

## 1. Quantification of Intra-Year Cross-Seasonal Persistence

Across the 12 calendar years, cross-seasonal Pearson correlations for R0 prevalence are:
- Pre-monsoon vs Established monsoon: $r = +0.930$
- Established monsoon vs Post-monsoon: $r = +0.744$
- Pre-monsoon vs Post-monsoon: $r = +0.835$
- **Mean Intra-Year Correlation:** **$\bar{r} = +0.836$**

### Degrees-of-Freedom Deficit:
$$\text{VIF} = 1 + (3 - 1)(0.836) = 2.673$$
$$N_{\text{eff}} = \frac{36}{2.673} = 13.47, \quad df_{\text{eff}} = 11.47$$
Treating $N=36$ as independent inflated effective sample size by $167\%$.

---

## 2. Year-Block Permutation Reproduction ($B=100,000$)

Permuting calendar year triplets intact:
- Original pooled R0 vs DMI: naive $p = 0.00351, q = 0.01404$.
- Recomputed Year-Block permutation: **$p = 0.01248$**.
- $N_{\text{eff}}$-adjusted parametric p-value: **$p = 0.0911$**.
- Corrected pooled FDR q-value: **$q = 0.24960 > 0.10$**.

**Verdict:** Confirmed. Cross-seasonal pooling yields an exploratory artifact of seasonal pseudo-replication.
