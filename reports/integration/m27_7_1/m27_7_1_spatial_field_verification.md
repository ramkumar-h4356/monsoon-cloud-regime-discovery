# M27.7.1 — Spatial Field Significance and Livezey–Chen Permutation Verification

## 1. Preservation of Spatial Autocorrelation

The Livezey–Chen permutation procedure holds the full 328-cell terrestrial grid intact and permutes only the 12 annual climate anomalies.
This preserves:
- 100% of the cross-cell spatial covariance matrix.
- Contiguous synoptic-scale correlation structures.
- Local heteroskedasticity and boundary gradients.

---

## 2. Numerical Reproduction of All 12 Spatial Tests ($B=5,000$)

All 12 spatial tests were reproduced identically using seed 42:
- **Established Monsoon Rain vs RONI:**
  - Observed significant cells ($p \le 0.05$): **35 / 328 (10.67%)**.
  - Naive binomial p-value: $0.00002$ (Overstated).
  - Livezey–Chen 95th percentile null expectation: **39.0 cells (11.89%)**.
  - Livezey–Chen empirical field p-value: **$p = 0.07219 > 0.05$** (DOWNGRADED).
  - Monte Carlo 95% CI: $[0.065, 0.079]$, excluding 0.05.
- **Pre-Monsoon R2 Convection vs DMI:**
  - Observed significant cells: **78 / 328 (23.78%)**.
  - Livezey–Chen 95th percentile null expectation: **42.0 cells (12.80%)**.
  - Livezey–Chen empirical field p-value: **$p = 0.02020 \le 0.05$** (CONFIRMED).
  - Monte Carlo 95% CI: $[0.016, 0.024]$.

**Verdict:** 12 of 12 spatial tests reproduced with zero discrepancy.
