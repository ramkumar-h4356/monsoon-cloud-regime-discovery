# M27.7.1 — Synthetic Validation and Intentional Failure Fixtures Report

## 1. Intentional Failure Injection Benchmarking

To prove that verification tests do not simply pass passively, 8 deliberate statistical corruption fixtures were injected and tested:
1. **Broken Exchangeability Fixture:** Correlated or mismatched residual dimensions raise exceptions and fail exchangeability tests.
2. **Incorrect BH Step-Up Ordering:** Shuffling p-value ranks in the BH algorithm violates step-up monotonicity ($q_{(i)} \le q_{(i+1)}$), caught immediately.
3. **Independent Spatial Cell Permutation:** Permuting spatial cells independently rather than permuting whole maps artificially deflates the null distribution ($K_{\text{null,95}} = 22$ vs true 39 cells), caught by spatial autocorrelation assertions.
4. **Permuting Seasons Across Years:** Breaking seasonal triplets artificially inflates pooled significance, caught by year-block assertions.
5. **Reusing Raw p as Adjusted q:** Assertions checking $q \ge p$ catch unadjusted p-values used as q-values.
6. **Incorrect Monte Carlo Denominator:** Using $B$ instead of $B+1$ in permutation p-value calculations fails exact p-value tests.
7. **Misclassifying Sparse Groups:** Flagging a cell with $N=1$ as robust fails sparsity assertions.
8. **Collinear Variables:** Perfect collinearity produces division-by-zero, caught by graceful NaN handling assertions.
