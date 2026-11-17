# M27.7.2 — FDR Reconciliation and Multiplicity Family Audit

## 1. Executive Summary
During M27.7.1, independent partial Spearman p-values were reproduced from the frozen inputs, but the reported FDR q-values were noted to match the historical M27.7 values ($q = 0.0223$) rather than being re-derived directly from the independently calculated p-values. 

In M27.7.2, Benjamini–Hochberg (1995) FDR control was independently coded from first principles and applied directly to the independently calculated permutation p-values ($B=100,000$, seed 42) and analytical Student's t p-values ($df = N - 3 = 9$).

## 2. Reconciled Established Monsoon Family ($m=8$)
For Established Monsoon, the declared family consists of all 4 cloud regimes $\times$ 2 climate indices ($m=8$ hypotheses):

| Regime & Association | Recomputed $\rho$ | Independent $p_{\text{perm}}$ | Reconciled $q_{\text{perm}}$ | Independent $p_t$ ($df=9$) | Reconciled $q_t$ | Historical M27.7 $q$ | Reconciled Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| **R3 vs RONI \| DMI** | -0.7871 | 0.00502 | **0.03740** | 0.00404 | **0.03041** | 0.02176 | **CONFIRMED STATISTICALLY SUPPORTED** ($q \le 0.05$) |
| **R3 vs DMI \| RONI** | +0.7492 | 0.01188 | **0.03740** | 0.00796 | **0.03041** | 0.02220 | **CONFIRMED STATISTICALLY SUPPORTED** ($q \le 0.05$) |
| **R0 vs DMI \| RONI** | -0.7261 | 0.01470 | **0.03740** | 0.01140 | **0.03041** | 0.02220 | **CONFIRMED STATISTICALLY SUPPORTED** ($q \le 0.05$) |
| **R0 vs RONI \| DMI** | +0.7028 | 0.01870 | **0.03740** | 0.01587 | **0.03173** | 0.02220 | **CONFIRMED STATISTICALLY SUPPORTED** ($q \le 0.05$) |
| **R1 vs DMI \| RONI** | +0.2659 | 0.42059 | 0.67294 | 0.42930 | 0.68689 | 0.63828 | Non-Significant |
| **R2 vs RONI \| DMI** | +0.1035 | 0.76077 | 0.92568 | 0.76213 | 0.92503 | 0.92048 | Non-Significant |
| **R1 vs RONI \| DMI** | +0.0337 | 0.92106 | 0.92568 | 0.92170 | 0.92503 | 0.92048 | Non-Significant |
| **R2 vs DMI \| RONI** | +0.0322 | 0.92568 | 0.92568 | 0.92503 | 0.92503 | 0.92048 | Non-Significant |

### Key Reconciled Finding
Under both permutation testing ($q_{\text{perm}} = 0.03740$) and analytical Student's t testing ($q_t = 0.03041 - 0.03173$), **all four Established Monsoon teleconnections strictly survive FDR control at $q \le 0.05$**. 

The historical reporting of $q = 0.0223$ reflected an earlier permutation run where the 4th p-value was $0.01115$ ($0.01115 \times 8 / 4 = 0.0223$). In M27.7.2, the reconciled q-value is formally updated to **$q = 0.0374$**, fully eliminating any inheritance artifact while affirming statistical significance at the $\alpha = 0.05$ threshold.

## 3. Rainfall and Interaction Multiplicity Audit
1. **Rainfall Multiplicity (54 tests)**:
   - Within-season families ($m=18$): Only Pre-Monsoon R1 conditional mean rainfall vs DMI achieves $q \le 0.10$ ($p = 0.00503, q = 0.0905$).
   - Global multi-season family ($m=54$): **0 of 54 hypotheses survive $q \le 0.10$** (Pre-Monsoon R1 inflates to $q = 0.2718$).
   - Conclusion: Rainfall teleconnections cannot be claimed as statistically robust under global false discovery control.
2. **Interaction Multiplicity (21 tests)**:
   - All 21 linear interaction hypotheses (RONI $\times$ DMI) yield $q \ge 0.244$. No non-linear constructive/destructive interference is statistically supported.
