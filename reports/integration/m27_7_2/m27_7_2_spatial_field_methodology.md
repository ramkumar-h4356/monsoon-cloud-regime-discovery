# M27.7.2 — Spatial Field Permutation Test Methodology and Naming Designation

## 1. Executive Summary
This report formalizes the algorithmic structure, method designation, and Monte Carlo resolution of the spatial field significance test applied to 328 Tier 1 terrestrial grid cells over the Indian monsoon domain.

## 2. Formal Method Designation
The procedure is formally designated as:
**`Year-Block Spatial Field Permutation Test (Livezey–Chen Field Counting Formulation)`**

### Algorithmic Specification
1. **Spatial Domain**: 328 Tier 1 terrestrial 1° grid cells over 6°N–38°N, 68°E–98°E.
2. **Temporal Matrix**: 12 calendar years (2010–2021) per grid cell.
3. **Preservation of Spatial Autocorrelation**: A single common year permutation vector $\pi \in S_{12}$ is applied to the climate index across all 328 grid cells simultaneously. The spatial fields of rainfall and cloud regime prevalence are held fixed.
4. **Local Significance**: At each cell $i \in \{1, \dots, 328\}$, local Spearman correlation $r_i$ and p-value $p_i$ are computed.
5. **Field Statistic**: The number of locally significant cells is counted: $K = \sum_{i=1}^{328} \mathbb{I}(p_i \le 0.05)$.
6. **Empirical Null Construction**: For $B = 5,000$ permutations, the null distribution of $K$ is generated, yielding the 95th percentile threshold $K_{95}$.
7. **Finite-Sample Monte Carlo Correction**:
   \[
   p_{\text{field}} = \frac{\sum_{b=1}^B \mathbb{I}(K_b \ge K_{\text{obs}}) + 1}{B + 1}
   \]
   Minimum resolution: $p_{\min} = 1 / 5,001 \approx 0.000200$.

## 3. Results and Interpretative Boundaries
- **Established Monsoon Rainfall vs RONI**: $K = 35$ cells, $K_{95} = 35.0$, $p_{\text{field}} = 0.07219 > 0.05$. **Confirmed non-significant at the 0.05 field level**. The original M27 claim of field significance is formally overturned.
- **Pre-Monsoon R2 Convection vs DMI**: $K = 78$ cells, $K_{95} = 51.0$, $p_{\text{field}} = 0.02020 \le 0.05$. Candidate field-level association, retained as exploratory.
- All other 10 field tests yield $p_{\text{field}} \ge 0.275$ and are confirmed non-significant.
