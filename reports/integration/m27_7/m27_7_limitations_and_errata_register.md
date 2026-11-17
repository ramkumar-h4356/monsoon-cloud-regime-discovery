# M27.7 — Errata Register and Documented Limitations

## 1. Formal Errata Register

This register documents all required reporting corrections to Milestone M27 text, tables, and figures:

| Erratum ID | Target M27 Report / Section | Original Text / Claim | Empirical Audit Finding | Mandatory Corrected Wording | Impacted Deliverables |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ERR-01** | `m27_regime_climate_correlations.md`, Section 3 | "Pre-monsoon R0 exhibits a statistically significant partial correlation with DMI (p=0.024)." | Raw $p=0.0236$ fails Benjamini-Hochberg FDR control ($q_{{\text{{FDR}}}} = 0.1887 > 0.10$). | "Pre-monsoon R0 displays an exploratory inverse tendency with DMI (rho=-0.647, unadjusted p=0.024, FDR q=0.189) that does not survive multiple testing correction." | Text, Table 1, Fig 04 |
| **ERR-02** | `m27_regime_climate_correlations.md`, Section 4 | "Post-monsoon R2 is significantly modulated by DMI independently of RONI (p=0.034)." | Raw $p=0.0340$ fails FDR control ($q_{{\text{{FDR}}}} = 0.2722 > 0.10$). | "Post-monsoon R2 exhibits an exploratory negative correlation with DMI (rho=-0.619, unadjusted p=0.034, FDR q=0.272) that warrants investigation in longer observational records." | Text, Table 1, Fig 04 |
| **ERR-03** | `m27_regime_climate_correlations.md`, Section 5 | "Cross-seasonal pooled analysis (N=36) confirms R0 modulation by DMI across all seasons (p=0.0035, q=0.014)." | Treating 36 seasonal observations as independent ignores strong intra-year persistence ($r_{{\text{{mean}}}} = 0.836, N_{{\text{{eff}}}} = 13.5$). Year-block permutation yields $p=0.0125, q=0.250$. | "Cross-seasonal pooling exhibits strong intra-year persistence (r=0.836, N_eff=13.5). Under year-block permutation, the pooled association yields p=0.0125 and fails FDR control (q=0.250), confirming it as an exploratory artifact of seasonal pseudo-replication." | Text, Table 1, Fig 04, Fig 08 |
| **ERR-04** | `m27_spatial_teleconnections.md`, Section 4 | "Established monsoon rainfall exhibits statistically significant continental field significance against RONI (p=0.00002)." | Naive binomial test assumed spatial independence across 328 cells. Livezey-Chen spatial permutation yields $p_{{\text{{field, LC}}}} = 0.07219 > 0.05$. | "Established monsoon rainfall exhibits localized correlations with RONI across 35 cells (10.7%), but does not achieve continental field significance under Livezey-Chen spatial permutation (p=0.072), representing an exploratory regional tendency." | Text, Table 8, Fig 07 |
| **ERR-05** | `m27_joint_climate_analysis.md`, Section 3 | "A dramatic 91.1% convective collapse in R2 convective storm core rainfall occurs under El Niño during post-monsoon." | Sample size is severely constrained ($N_1 = 2$ El Niño vs $N_2 = 6$ La Niña). Exact permutation test yields $p = 0.21412$. | "In the historical post-monsoon sample, R2 conditional rainfall was lower in 2 El Niño years compared to 6 La Niña years (-91.1%), but this difference is not statistically significant (exact permutation p=0.214) due to small sample size and wide error bounds." | Text, Table 5, Fig 06 |
| **ERR-06** | `m27_joint_climate_analysis.md`, Section 5 | "Statistically significant non-linear interaction terms reveal destructive interference between ENSO and IOD." | Zero interaction tests achieve $q_{{\text{{FDR}}}} \le 0.10$ (lowest $q \approx 0.24$). | "Multiplicative interaction terms (RONI x DMI) fail multiple comparison correction across all variables and seasons (q > 0.10), providing descriptive hypothesis-generating evidence rather than established non-linear interference." | Text, Table 6 |

---

## 2. Documented Methodological Limitations

1. **Decadal Sample Size Constraint ($N = 12$ Years):**
   - The 2010–2021 study period comprises exactly 12 annual observations per season.
   - While adequate for identifying strong bivariate and partial teleconnections ($|\rho| \ge 0.70$), this sample size has low statistical power ($< 40\%$) to detect moderate correlations ($|\rho| \approx 0.40$) or subtle interaction effects.
2. **Sparse Joint Phase Sampling:**
   - In any 12-year window, rare multi-mode combinations (e.g., El Niño coinciding with Negative IOD) have zero historical occurrences ($N = 0$).
   - Statistical inference regarding joint phase interactions must be validated using extended reanalysis or synthetic ensemble modeling.
3. **Terrestrial Mask and Boundary Constraints:**
   - Rainfall analysis is strictly restricted to India's 328 Tier 1 terrestrial cells.
   - Oceanic teleconnections over the Bay of Bengal and Arabian Sea are represented through cloud-regime fractions but lack direct in-situ IMD rainfall validation.
