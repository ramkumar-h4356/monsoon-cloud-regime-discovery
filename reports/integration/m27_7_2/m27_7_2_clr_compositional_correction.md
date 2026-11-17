# M27.7.2 — CLR Compositional Analysis Reconciliation and Sensitivity Assessment

## 1. Executive Summary
This report formalizes the resolution of erratum **`ERR-M27.7.1-01`** and presents the definitive empirical investigation of Centered Log-Ratio (CLR) compositional transformation across three spatial populations: Full Domain, Terrestrial Land (Tier 1), and Ocean.

## 2. Input Specifications and Compositional Pipeline
- **Input Arrays**: 12 annual-seasonal regime prevalence vectors $\mathbf{P} = [P(R_0), P(R_1), P(R_2), P(R_3)]$ spanning 2010–2021 ($N=12$).
- **Valid Observation Mask**: 100% complete across all 12 years; all observed regime fractions are strictly positive ($P_k > 0$).
- **Zero-Handling Policy & Pseudocount**: Proportions are bounded by $\epsilon = 10^{-6}$ and renormalized to the unit simplex $\mathcal{S}^3$ ($\sum_{k=0}^3 P_k = 1.0$) prior to logarithmic transformation.
- **Centered Log-Ratio Mapping**: Maps the simplex $\mathcal{S}^3$ into unconstrained Euclidean space $\mathbb{R}^4$:
\[
\operatorname{clr}(P_k) = \ln\left(\frac{P_k}{g(\mathbf{P})}\right) = \ln(P_k) - \frac{1}{4}\sum_{j=0}^3 \ln(P_j)
\]
where $g(\mathbf{P})$ is the geometric mean of the four regime fractions.

## 3. Empirical Results Across Spatial Subsets (Established Monsoon)

### A. Full Indian Monsoon Domain (2,400 grid cells)
- **Simple CLR Rank Correlations**:
  - $\text{clr}(R_0)$ vs RONI: $\rho = -0.0699, p = 0.8290$ (Non-significant).
  - $\text{clr}(R_3)$ vs RONI: $\rho = -0.4196, p = 0.1745$ (Non-significant).
- **Partial CLR Rank Correlations (controlling for opposing index)**:
  - $\text{clr}(R_0)$ vs RONI $\mid$ DMI: $\rho = +0.1026, p_{\text{perm}} = 0.7518, q_{\text{bh}} = 0.9083$ (Non-significant).
  - $\text{clr}(R_3)$ vs RONI $\mid$ DMI: $\rho = -0.4660, p_{\text{perm}} = 0.1487, q_{\text{bh}} = 0.8220$ (Non-significant).
  - $\text{clr}(R_0)$ vs DMI $\mid$ RONI: $\rho = -0.2554, p_{\text{perm}} = 0.4373, q_{\text{bh}} = 0.8220$ (Non-significant).
  - $\text{clr}(R_3)$ vs DMI $\mid$ RONI: $\rho = +0.2379, p_{\text{perm}} = 0.4780, q_{\text{bh}} = 0.8220$ (Non-significant).

### B. Terrestrial Land Cells (328 Tier 1 cells)
- **Simple CLR Rank Correlations**:
  - $\text{clr}(R_0)$ vs RONI: $\rho = -0.0350, p = 0.9141$ (Non-significant).
  - $\text{clr}(R_3)$ vs RONI: $\rho = -0.0979, p = 0.7621$ (Non-significant).
- **Partial CLR Rank Correlations**:
  - $\text{clr}(R_0)$ vs RONI $\mid$ DMI: $\rho = +0.3344, p = 0.3149$ (Non-significant).
  - $\text{clr}(R_3)$ vs RONI $\mid$ DMI: $\rho = +0.0949, p = 0.7815$ (Non-significant).

### C. Marine Ocean Domain (2,072 cells)
- **Simple CLR Rank Correlations**:
  - $\text{clr}(R_0)$ vs RONI: $\rho = -0.0979, p = 0.7621$ (Non-significant).
  - $\text{clr}(R_3)$ vs RONI: $\rho = -0.4685, p = 0.1245$ (Non-significant).
- **Partial CLR Rank Correlations**:
  - $\text{clr}(R_0)$ vs RONI $\mid$ DMI: $\rho = +0.0606, p = 0.8594$ (Non-significant).
  - $\text{clr}(R_3)$ vs RONI $\mid$ DMI: $\rho = -0.5691, p = 0.0676$ (Marginal, non-significant at $\alpha = 0.05$).

## 4. Multiplicity & FDR Reconciliation
Across the complete 24-hypothesis CLR family (4 regimes $\times$ 2 climate indices $\times$ 3 seasons), **0 of 24 tests survive Benjamini–Hochberg FDR control at $q \le 0.10$**.

## 5. Methodological and Physical Interpretation
1. **Mathematical Attenuation**: In raw proportion coordinates, R3 accounts for over 80% of total cloud volume in the domain, allowing its large absolute interannual fluctuations to dominate the variance structure. In CLR coordinates, scaling relative to the geometric mean divides out dominant scale effects, attenuating bivariate rank monotonicity below statistical significance given $N=12$.
2. **Designation**: CLR analysis is officially designated as a **`Compositional Sensitivity Analysis`**.
3. **Scientific Boundaries**: CLR does **NOT** provide independent physical confirmation. The narrative report erratum (`ERR-M27.7.1-01`), where raw partial correlations were mistakenly transcribed as CLR correlations, is formally resolved. Observational statistical sensitivity cannot establish causal dynamics.
