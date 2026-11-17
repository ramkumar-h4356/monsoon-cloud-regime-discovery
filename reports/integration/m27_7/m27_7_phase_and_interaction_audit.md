# M27.7 — Discrete Phase Contrasts and Phase Matrix Sparsity Audit

## 1. Audit of Discrete Phase Contrasts and the Reported "91.1% Convective Collapse"

In M27 report sections analyzing post-monsoon climate associations, prominent narrative emphasis was placed on:
> "a dramatic 91.1% convective collapse in R2 convective storm core rainfall under El Niño during post-monsoon (from 8.93 to 0.79 mm/day)."

The audit independently verified the raw underlying data and sample sizes:
- **Post-Monsoon El Niño Years ($N_1 = 2$):** 2015, 2018.
  - Mean R2 conditional rainfall: **0.7944 mm/day**.
- **Post-Monsoon La Niña Years ($N_2 = 6$):** 2010, 2011, 2013, 2016, 2017, 2020.
  - Mean R2 conditional rainfall: **8.9335 mm/day**.
- Nominal difference: **$-8.1390$ mm/day** ($-91.1\%$).

### Rigorous Statistical Hypothesis Testing
- **Two-Sample Exact Permutation Test ($B = 100,000$):** **$p_{\text{perm}} = 0.21412$**.
- **Mann-Whitney U Test:** $U = 2.0$, **$p_{\text{MWU}} = 0.254$**.
- **Terrestrial Mean Rainfall Difference ($-61.8\%$):** **$p_{\text{perm}} = 0.45594$**.

### Scientific Verdict and Correction:
- **UNDERPOWERED DESCRIPTIVE OBSERVATION (NON-SIGNIFICANT).**
- An empirical contrast based on only $N_1 = 2$ events cannot support claims of a statistically validated teleconnection or "convective collapse".
- With $p = 0.214$, this contrast fails standard significance thresholds by a wide margin.
- **Reporting Erratum:** The narrative must reframe this observation as an exploratory, underpowered historical difference with wide confidence bounds.

---

## 2. Sparsity and Power Audit of the 3×3 Joint ENSO × IOD Phase Matrix

Original M27 constructed a $3 \times 3$ phase matrix partitioning the 12 study years into 9 joint combinations (El Niño / Neutral / La Niña $\times$ Positive IOD / Neutral / Negative IOD).

### Matrix Occupancy Summary Across Seasons:
| Season | Total Cells | Empty Cells ($N=0$) | Single-Year Cells ($N=1$) | Two-Year Cells ($N=2$) | Robust Cells ($N \ge 3$) | Underpowered Cell % | Usability Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Pre-Monsoon | 9 | 4 | 2 | 0 | 3 | 66.7% | HIGHLY_SPARSE_DESCRIPTIVE_ONLY |
| Established Monsoon | 9 | 4 | 2 | 0 | 3 | 66.7% | HIGHLY_SPARSE_DESCRIPTIVE_ONLY |
| Post-Monsoon | 9 | 4 | 2 | 1 | 2 | 77.8% | HIGHLY_SPARSE_DESCRIPTIVE_ONLY |
| Pooled (All Seasons) | 9 | 2 | 1 | 2 | 4 | 55.6% | HIGHLY_SPARSE_DESCRIPTIVE_ONLY |

### Key Observations:
1. Across individual seasons, **66.7% to 77.8% of the joint matrix cells are severely underpowered ($N < 3$)**, with 4 combinations completely unobserved ($N = 0$).
2. Only 2 to 3 cells per season have sufficient sample size ($N \ge 3$) for descriptive statistics.
3. In post-monsoon, the "El Niño + Positive IOD" cell has $N = 0$, and "El Niño + Neutral" has $N = 2$.
4. **Mandatory Reporting Limitation:** The $3 \times 3$ phase matrix must be presented strictly as a sparse descriptive taxonomy of observed events, with explicit sample count annotations and no claims of inferential joint-distribution modeling.
