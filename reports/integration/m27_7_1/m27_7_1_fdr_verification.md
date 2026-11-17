# M27.7.1 — Multiple Testing and False Discovery Rate Verification

## 1. Independent Implementation of Benjamini–Hochberg Algorithm

A pure, independent implementation of the Benjamini–Hochberg step-up procedure was coded and verified against SciPy's `false_discovery_control(method='bh')`:
- Discrepancy across all tests: **0.000000**.
- Monotonicity and bounding ($0 \le q \le 1$ and $q \ge p$) confirmed.

---

## 2. Partial Spearman Hypothesis Families (8 Tests per Season)

The declared family comprises 4 regimes $\times$ 2 climate indices = 8 tests within each season:
- **Established Monsoon:** 4 tests achieve $q_{\text{FDR}} \le 0.05$:
  - R0 vs RONI | DMI: $\rho = +0.7028, p = 0.0112, q = 0.0223$ (CONFIRMED)
  - R3 vs RONI | DMI: $\rho = -0.7871, p = 0.0034, q = 0.0223$ (CONFIRMED)
  - R0 vs DMI | RONI: $\rho = -0.7261, p = 0.0101, q = 0.0223$ (CONFIRMED)
  - R3 vs DMI | RONI: $\rho = +0.7492, p = 0.0056, q = 0.0223$ (CONFIRMED)
- **Pre-Monsoon:** R0 vs DMI has raw $p = 0.0236$, but $q = 0.1887 > 0.10$ (DOWNGRADED).
- **Post-Monsoon:** R2 vs DMI has raw $p = 0.0340$, but $q = 0.2722 > 0.10$ (DOWNGRADED).

---

## 3. Rainfall Multiplicity Sensitivity (54 Tests)

- Under the seasonal family ($m=18$): only Pre-Monsoon R1 conditional mean vs DMI achieves $q = 0.0905 \le 0.10$.
- Under the global cross-seasonal family ($m=54$): **0 tests achieve $q \le 0.10$** (Pre-monsoon R1 has $q_{\text{global}} = 0.218$).
- Output table: `reports/integration/m27_7_1/tables/m27_7_1_rainfall_multiplicity_verification.csv`.
