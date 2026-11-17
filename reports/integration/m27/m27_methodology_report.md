# M27 — Scientific Methodology Report: ENSO–IOD Climate Teleconnections

**Milestone:** M27 — Integrated ENSO–IOD Climate Teleconnection and Cloud-Regime Analysis  
**Repository:** `monsoon_cloud_research`  
**Secondary Worktree:** `post_monsoon_research`  
**Evaluation Date:** 2026-11-17  
**Author:** Senior Atmospheric Data Scientist & Statistical Climatologist  
**Status:** Certified & Reproducible  

---

## 1. Executive Summary & Research Framework

Milestone M27 investigates the large-scale climate modes governing the interannual variability of the four frozen M25 cloud regimes ($R_0, R_1, R_2, R_3$) and their surface rainfall signatures (validated in M26) over the Indian subcontinent. The analysis spans the 12-year satellite-gauge study period (2010–2021) and encompasses the three approved 30-day observation windows:
* **Pre-Monsoon:** April 15 – May 14
* **Established Monsoon:** July 15 – August 13
* **Post-Monsoon:** October 15 – November 13

The climate drivers investigated are:
1. **NOAA Relative Oceanic Niño Index (RONI):** Measuring Central-to-Eastern Pacific sea surface temperature (SST) anomalies relative to the tropical mean baseline, eliminating false warming trends.
2. **NOAA Dipole Mode Index (DMI):** Measuring the zonal SST gradient between the western equatorial Indian Ocean ($50^\circ\text{E}–70^\circ\text{E}, 10^\circ\text{S}–10^\circ\text{N}$) and south-eastern equatorial Indian Ocean ($90^\circ\text{E}–110^\circ\text{E}, 10^\circ\text{S}–0^\circ\text{N}$).

---

## 2. Statistical Unit of Analysis & Independence Principle

A fundamental methodological principle of M27 is the prevention of pseudoreplication:
* Daily observations ($N = 342,432$) and hourly cloud observations ($N = 24,883,200$) are strongly autocorrelated and cannot be treated as independent degrees of freedom against slowly varying interannual ocean indices.
* Consequently, the primary independent statistical unit is strictly the **annual-seasonal summary** ($N = 12$ independent years per season, $df = 10$).
* Across the 3 seasons, exactly 36 annual-seasonal records are constructed.

---

## 3. Mathematical & Algorithmic Formulation

### 3.1 Non-Parametric Spearman Rank Association
Because climate indices and regime occurrence fractions exhibit non-normal distributions and potential non-linear monotonic relationships, the primary association metric is the Spearman rank correlation:

$$\rho(x, y) = 1 - \frac{6 \sum_{i=1}^N d_i^2}{N(N^2 - 1)}$$

where $d_i = \text{rank}(x_i) - \text{rank}(y_i)$. Standard fractional ranking is applied for tied values.

### 3.2 Partial Rank Correlation
Because ENSO and IOD are coupled via the atmospheric Walker circulation (with positive IOD often co-occurring with El Niño), simple bivariate correlations risk conflating Pacific and Indian Ocean forcing. M27 isolates the independent teleconnection using partial Spearman correlation:

$$\rho_{\text{partial}}(x, y \mid z) = \frac{\rho_{xy} - \rho_{xz} \rho_{yz}}{\sqrt{(1 - \rho_{xz}^2)(1 - \rho_{yz}^2)}}$$

Where $x$ is the cloud regime fraction or rainfall metric, $y$ is the primary climate index (e.g., RONI), and $z$ is the controlling covariate index (e.g., DMI).

### 3.3 Exact Monte Carlo Permutation Testing ($B = 100,000$)
Given the finite sample size ($N = 12$), asymptotic Gaussian and Student's $t$ approximations are unreliable. Significance testing is evaluated via exact Monte Carlo permutation:
1. The climate index vector $y$ is permuted randomly $B = 100,000$ times, preserving the fixed marginal ranks of $x$.
2. For each permutation $b \in \{1, \dots, B\}$, the permutation statistic $\rho_b$ is computed.
3. The empirical two-tailed $p$-value is calculated with finite-sample resolution:

$$\hat{p}_{\text{perm}} = \frac{1 + \sum_{b=1}^B \mathbb{I}(|\rho_b| \ge |\rho_{\text{obs}}|)}{B + 1}$$

Ensuring exact numerical bounding ($p \ge 1 / (100,001) \approx 0.00001$).

### 3.4 Compositional Simplex Constraints & CLR Transformation
Because the four cloud regimes form an exhaustive partition of every observation window:

$$\sum_{k=0}^3 P(R_k \mid y, s) = 1.0 \implies \sum_{k=0}^3 \Delta P(R_k) = 0.0$$

Any climate-induced shift is strictly zero-sum. To verify that bivariate correlations are not artifacts of compositional closure, M27 executes a parallel sensitivity analysis using the **Centered Log-Ratio (CLR)** transformation:

$$\text{clr}(P)_k = \ln\left(\frac{P(R_k)}{g(P)}\right), \quad g(P) = \left(\prod_{j=0}^3 P(R_j)\right)^{1/4}$$

Correlating $\text{clr}(P)_k$ against RONI and DMI verifies that empirical inferences are invariant to the simplex geometry.

### 3.5 Spatial Field Significance (Livezey–Chen / Walker Formulation)
When testing teleconnection signals across the 328 Tier 1 grid cells, false-positive discoveries can occur by chance. M27 tests field significance by comparing the observed count of locally significant cells ($k_{\text{sig}}$ with local $p_j \le 0.05$) against the binomial null expectation ($\pi_0 = 0.05$):

$$p_{\text{field}} = \sum_{m = k_{\text{sig}}}^{M} \binom{M}{m} \pi_0^m (1 - \pi_0)^{M - m}$$

Where $M = 328$. A spatial field is declared significant only when $p_{\text{field}} < 0.05$.

---

## 4. Multiple Testing Control (Benjamini–Hochberg FDR)

Testing 4 regimes across 3 seasons against 2 climate indices produces predefined hypothesis families. To prevent inflation of type I errors, the Benjamini–Hochberg (1995) procedure is applied at false discovery rate $q = 0.10$ within each seasonal family, ensuring rigorous error control.

---

## 5. Methodological Safeguards & Non-Causal Compliance

1. **Strictly Observational:** All regression slopes and correlations are designated as descriptive empirical associations. No causal claims are asserted.
2. **Underpowered Phase Combinations:** When stratifying by discrete phases (e.g., El Niño vs. La Niña), sample sizes per cell are documented explicitly. Phase combinations with $N < 3$ years are designated as underpowered for inferential hypothesis testing.
3. **Zero Git Mutations:** Implementation strictly adhered to zero Git operations.
