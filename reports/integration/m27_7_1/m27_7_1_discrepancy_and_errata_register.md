# M27.7.1 — Discrepancy, Errata, and Limitation Register

## 1. New Errata Identified during M27.7.1 Verification

| Erratum ID | Location | Erroneous Claim | Empirical Verification Finding | Corrected Guidance |
| :--- | :--- | :--- | :--- | :--- |
| **ERR-M27.7.1-01** | `m27_7_multiple_testing_audit.md`, Section 3 & `m27_7_independent_scientific_acceptance_report.md`, Section 2 | "In Established Monsoon, CLR-transformed R0 and R3 correlations with RONI remain statistically significant after FDR (rho=+0.7028, rho=-0.7871)." | Narrative transcription error. These values are the raw partial Spearman correlations. In table `m27_7_corrected_clr_correlations.csv`, simple CLR rank correlations are -0.0699 (q=0.938) and -0.4196 (q=0.938), which are non-significant. | "Simple rank correlations on CLR coordinates are non-significant; however, partial Spearman correlations on CLR coordinates (+0.671 and -0.755) confirm the established monsoon convective-stratiform dipole." |
| **ERR-M27.7.1-02** | `m27_7_multiple_testing_audit.md`, Section 1 | "Pre-monsoon R1 conditional mean vs DMI achieves q=0.0905." | Verified under seasonal family (m=18); however, under a broader cross-seasonal family (m=54), q=0.218. | State both within-season (m=18, q=0.0905) and global (m=54, q=0.218) family sensitivities transparently. |

---

## 2. Confirmed M27.7 Errata Register

All six errata established in M27.7 (ERR-01 through ERR-06) were independently verified and re-confirmed as essential corrections to original M27 reporting.
