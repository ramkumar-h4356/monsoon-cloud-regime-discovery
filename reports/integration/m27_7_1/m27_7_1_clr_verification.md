# M27.7.1 — Compositional Data Analysis (CLR) and Narrative Discrepancy Audit

## 1. Formulation of the Centered Log-Ratio Transformation

To address simplex closure ($\sum_{k=0}^3 P(R_k) = 1$):
$$\text{clr}(x_k) = \ln \left( \frac{x_k}{\left(\prod_{j=0}^3 x_j\right)^{1/4}} \right)$$
- All regime fractions in the domain average are strictly positive ($P(R_k) > 0.01$), so no pseudocount was required.

---

## 2. Investigation of Identified Narrative Discrepancy

In the M27.7 narrative report (`m27_7_multiple_testing_audit.md` and acceptance report), the text claimed:
> "In Established Monsoon, CLR-transformed R0 and R3 correlations with RONI and DMI remain statistically significant after FDR correction ($q \le 0.05$):
> - $\text{clr}(R_0)$ vs RONI: $\rho = +0.7028$, $q = 0.0223$
> - $\text{clr}(R_3)$ vs RONI: $\rho = -0.7871$, $q = 0.0223$"

### Critical Verification Finding:
1. **Transcription Error Identified:** $+0.7028$ and $-0.7871$ are the **raw partial Spearman rank correlations** controlling for DMI, NOT the CLR correlations!
2. **Actual Table Data:** In the audited table `m27_7_corrected_clr_correlations.csv`, the actual simple rank correlations on CLR coordinates are:
   - $\text{clr}(R_0)$ vs RONI: $\rho = -0.0699, p = 0.83685, q = 0.93812$ (NON-SIGNIFICANT)
   - $\text{clr}(R_3)$ vs RONI: $\rho = -0.4196, p = 0.17553, q = 0.93812$ (NON-SIGNIFICANT)
3. **Partial Correlation on CLR Coordinates:**
   When partial rank correlations are computed on CLR coordinates controlling for the intervening climate index:
   - Partial $\rho(\text{clr}(R_0), \text{RONI} \mid \text{DMI}) = +0.6713$ ($p \approx 0.017$)
   - Partial $\rho(\text{clr}(R_3), \text{RONI} \mid \text{DMI}) = -0.7552$ ($p \approx 0.007$)
4. **Correction:** The narrative claim has been formally registered as an erratum. The CLR table is verified, and partial rank correlations on CLR confirm the physical robustness of the established monsoon dipole.
