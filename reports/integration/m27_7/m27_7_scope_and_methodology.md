# M27.7 — Independent Scientific Acceptance Audit: Scope and Methodology

## 1. Executive Context and Authority

- **Project Title:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain: Seasonal Variability, Atmospheric Conditions, Rainfall Associations, and ENSO–IOD Modulation Analysis
- **Milestone:** M27.7 — Independent Scientific Acceptance Audit and Statistical Correction
- **Audited Target:** Milestone M27 (Climate Teleconnection Analysis, M27.1–M27.6)
- **Repositories Audited:**
  - Canonical: `D:\\Project Simulator\\monsoon_cloud_research` (Branch `main`)
  - Secondary Worktree: `D:\\Project Simulator\\post_monsoon_research` (Branch `feature/post-monsoon-analysis`)
- **Baseline Test Status:** 114 passing unit and integration tests (`pytest tests/integration/test_m27_climate_modulation.py`)

This audit was conducted under the core principle that **scientific validity, methodological transparency, and statistical defensibility supersede any desire to preserve original findings**.

---

## 2. Non-Negotiable Audit Constraints

1. **Frozen Input Immutability:**
   - Frozen M25 combined 3-season arrays ($N = 24,883,200$ hourly grid-cell observations, MiniBatchKMeans $K=4$, IncrementalPCA top-10) remain strictly immutable.
   - Frozen M26 matched daily rainfall dataset ($N = 342,432$ grid-cell days, 328 Tier 1 cells, 12 years 2010–2021) remain strictly immutable.
   - Raw NOAA RONI (`RONI.ascii.txt`) and DMI (`dmi.had.long.csv`) climate index files remain untouched.
2. **Original M27 Output Preservation:**
   - Original M27 processed parquet files, 14 summary tables, 10 figures, and 8 narrative reports are preserved without overwriting as immutable audit inputs.
   - All M27.7 audit scripts, corrected tables, figures, and reports reside in dedicated `m27_7` directories:
     - Implementation: `src/integration/climate_association/m27_7/`
     - Deliverables: `reports/integration/m27_7/`
3. **Zero Git Mutations:**
   - No git commits, staging, branch switching, rebasing, resets, or remote pushes were executed during this audit.
4. **Complete Repository Parity:**
   - Canonical and secondary worktrees maintain byte-identical SHA256 parity across all implementation and report files.

---

## 3. Methodological Pillars of the Audit

The audit evaluated seven specific potential statistical vulnerabilities:
1. **Mathematical Formulation of Partial Spearman Rank Correlation:** Verified the algebraic formula against rank-residual regression and computed permutation p-values using Freedman-Lane exchangeability ($B = 100,000$).
2. **Multiple Comparison Corrections:** Applied Benjamini-Hochberg False Discovery Rate (FDR, $q \le 0.05$ and $q \le 0.10$) and family-wise Bonferroni correction across all 54 rainfall modulation tests, 21 interaction tests, and 24 CLR compositional tests.
3. **Temporal Dependence and Cross-Seasonal Pooling:** Evaluated repeated-year dependence in the $N=36$ pooled dataset, calculated intra-year cross-seasonal persistence ($r_{\\text{intra}}$), estimated effective degrees of freedom ($N_{\\text{eff}}$), and implemented a year-block permutation test ($B = 100,000$).
4. **Spatial Field Significance under Spatial Autocorrelation:** Audited the naive binomial independence assumption across 328 cells and implemented the Livezey-Chen / Walker year-level spatial permutation test ($B = 5,000$).
5. **Sample Size Limitations in Discrete Phase Contrasts:** Re-evaluated the reported "91.1% convective collapse" in post-monsoon R2 under El Niño ($N_1 = 2$) vs La Niña ($N_2 = 6$) using exact permutation and Mann-Whitney U tests.
6. **Joint ENSO × IOD Phase Matrix Sparsity:** Audited sample distribution across the $3 \\times 3$ grid to identify severely underpowered combinations ($N < 3$).
7. **Figure Integrity and Narrative Consistency:** Inspected all 10 M27 figures for unadjusted significance markers, missing sample counts, and narrative overstatements, generating 4 corrected publication figures at 300 DPI.
