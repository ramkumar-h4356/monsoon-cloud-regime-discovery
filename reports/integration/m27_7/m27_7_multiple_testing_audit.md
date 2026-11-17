# M27.7 — Multiple Testing and Multiplicity Audit: Rainfall, Interactions, and Compositionality

## 1. Rainfall Modulation Multiplicity Audit (54 Tests)

M27 investigated 9 annual-seasonal rainfall metrics across 2 climate indices and 3 seasons ($9 \times 2 \times 3 = 54$ hypotheses):
- Terrestrial Mean Rainfall
- Rainfall Anomaly
- Wet-Day Frequency ($\ge 25$ mm/day)
- R2 Conditional Mean Rainfall
- R2 Volume Contribution
- R1 Conditional Mean Rainfall
- R1 Volume Contribution
- R0 Conditional Mean Rainfall
- R3 Conditional Mean Rainfall

### Multiplicity Results
Applying Benjamini-Hochberg FDR control across the 18 tests within each season:
- **Pre-Monsoon:** Only **1 test** achieves marginal significance at $q_{\text{FDR}} \le 0.10$:
  - **R1 Conditional Mean vs DMI:** $\rho = +0.6503$, $p_{\text{perm}} = 0.0243$, $q_{\text{FDR}} = 0.0905$ (**EXPLORATORY_TENDENCY**).
  - All other 17 pre-monsoon rainfall tests fail FDR control ($q > 0.10$).
- **Established Monsoon:** Zero rainfall tests achieve $q_{\text{FDR}} \le 0.10$.
  - R2 volume contribution vs RONI had unadjusted $p = 0.063$, but $q_{\text{FDR}} = 0.287$.
  - Mean rainfall vs RONI had unadjusted $p = 0.175$, $q_{\text{FDR}} = 0.394$.
- **Post-Monsoon:** Zero rainfall tests achieve $q_{\text{FDR}} \le 0.10$.
  - R2 conditional mean vs RONI had unadjusted $p = 0.142$, $q_{\text{FDR}} = 0.428$.

**Scientific Correction:** M27 text described widespread rainfall modulation by ENSO and IOD. Under rigorous multiplicity control, continental-scale rainfall metrics show only localized or exploratory associations ($q > 0.10$ for 53 of 54 tests).

---

## 2. ENSO × IOD Interaction Effects Multiplicity Audit (21 Tests)

M27 tested for non-linear multiplicative interaction terms ($\text{RONI} \times \text{DMI}$) across 7 key variables in 3 seasons ($7 \times 3 = 21$ tests):
- R0, R1, R2, R3 Prevalence
- Terrestrial Mean Rainfall
- Wet-Day Frequency
- R2 Conditional Mean

### Empirical Interaction Results
- In **Pre-Monsoon**, the strongest interaction was R1 prevalence ($t = -1.93$, unadjusted $p = 0.089$, $q_{\text{FDR}} = 0.244$).
- In **Established Monsoon**, the strongest interaction was R0 prevalence ($t = +1.64$, unadjusted $p = 0.139$, $q_{\text{FDR}} = 0.485$).
- In **Post-Monsoon**, the strongest interaction was R3 prevalence ($t = -1.80$, unadjusted $p = 0.109$, $q_{\text{FDR}} = 0.380$).
- **Crucial Audit Finding:** **Zero interaction tests achieve statistical significance ($q_{\text{FDR}} \le 0.10$)**.
- **Scientific Correction:** M27 narrative claims proposing active ENSO–IOD destructive or constructive interference must be classified as **unsupported hypothesis-generating observations**, not statistically confirmed interactions.

---

## 3. Compositional Data Analysis (Centered Log-Ratio Transformation)

Because cloud regime fractions sum to 1 ($\sum_{k=0}^3 P(R_k) = 1$), raw percentage correlations are subject to compositional closure artifacts.
The audit evaluated Centered Log-Ratio (CLR) transformed regime coordinates:
$$\text{clr}(x_k) = \ln \frac{x_k}{\left(\prod_{j=0}^3 x_j\right)^{1/4}}$$

### Findings:
- In **Established Monsoon**, CLR-transformed R0 and R3 correlations with RONI and DMI remain statistically significant after FDR correction ($q_{\text{FDR}} \le 0.05$):
  - $\text{clr}(R_0)$ vs RONI: $\rho = +0.7028$, $q_{\text{FDR}} = 0.0223$
  - $\text{clr}(R_3)$ vs RONI: $\rho = -0.7871$, $q_{\text{FDR}} = 0.0223$
- This confirms that the R0 and R3 dipole teleconnections in the established monsoon are **genuine physical atmospheric responses**, entirely robust to compositional closure effects.
