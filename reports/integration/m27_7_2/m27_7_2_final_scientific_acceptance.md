# M27.7.2 — Final Scientific Acceptance Decision Dossier

## 1. Final Milestone Verdict

### **ACCEPTED WITH DOCUMENTED LIMITATIONS**

## 2. Formal Technical Justification
Following independent re-calculation, algorithmic comparison, and narrative auditing:
1. **Established Monsoon Regime Teleconnections**: The four teleconnections between cloud regimes and climate indices (R0 positive with RONI $\rho = +0.7028$, R3 negative with RONI $\rho = -0.7871$, R0 negative with DMI $\rho = -0.7261$, R3 positive with DMI $\rho = +0.7492$) are **reproduced at float precision, robust to conditioning, survive independent FDR control ($q = 0.0374 \le 0.05$), and are preserved in compositional coordinates**.
2. **Conservative Downgrades Confirmed**: Pre-Monsoon R0 ($q=0.189$), Post-Monsoon R2 ($q=0.272$), all 54 rainfall modulation tests (global $q > 0.10$), all 21 interaction hypotheses ($q \ge 0.244$), and Established Monsoon rainfall spatial field significance ($p=0.07219 > 0.05$) are **confirmed non-significant and downgraded to exploratory**.
3. **Methodological Defensibility**: The predictor-residual permutation variant is verified as mathematically equivalent to conventional Freedman–Lane for linear partial correlation; the Year-Block Spatial Field Permutation Test is accurately documented; and the effective sample size ($N_{\text{eff}} \approx 13.47$) is correctly interpreted as a repeated-measures design effect.
4. **Reproducibility & Hygiene**: 59 integration tests pass in both repositories with zero failures, 100.0% byte-for-byte SHA-256 parity is established, and zero Git mutations were introduced.

This closes Milestone M27 as scientifically defensible, transparent, and fully reconciled.
