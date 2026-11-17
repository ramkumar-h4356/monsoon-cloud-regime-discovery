# Milestone M25.2: Scientific Review Corrections and Interpretative Alignment Note

**Project:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain: Seasonal Variability, Atmospheric Conditions, Rainfall Associations, and ENSO–IOD Modulation  
**Document Type:** Additive Scientific Review Note & Formal Correction Addendum  
**Target Milestone Document:** `docs/methodology/M25_2_three_season_methodological_reconciliation.md`  
**Date:** November 16, 2026  
**Status:** `OFFICIALLY_AMENDED_ADDITIVE_NOTE`  
**Auditor / Reviewer Role:** Senior Scientific Research Auditor, Atmospheric Data Scientist & Research-Software Engineer  

---

## 1. Executive Statement and Preservation Policy

This document provides formal, additive scientific corrections to the Milestone **M25.2** reconciliation report (`docs/methodology/M25_2_three_season_methodological_reconciliation.md`).

Following rigorous post-audit peer review, eight specific assertions in the initial M25.2 report required refined calibration to maintain strict epistemic rigor, prevent speculative or causal over-interpretation of unsupervised statistical clusterings, and ensure absolute fidelity to the underlying codebase implementations.

In accordance with scientific reproducibility standards and project constraints:
1. **Preservation of Research Outputs:** No underlying numerical models, fitted parameters, cluster assignments, or raw datasets are modified, recalculated, or regenerated.
2. **Preservation of Historical Audit:** The original M25.2 audit history is preserved in its entirety. This document operates as an explicit, authoritative addendum that supersedes preliminary phrasing without retroactive erasure.
3. **Epistemic Discipline:** All statistical partitions are characterized neutrally based on their mathematical formulations rather than premature physical or causal attributions.

---

## 2. Itemized Scientific Review Corrections

### Correction 1: $K=2$ vs. $K=4$ Explanation Formally Formulated as a Hypothesis

- **Affected Sections in M25.2:** Section 1.2, Section 9 (Clustering Methodology), Section 15 (GAP-01).
- **Initial Phrasing:** Stated that expanding feature dimensionality from 3 or 14 variables to 36 variables "naturally splits the data into four physical configurations" and resolved the difference between $K=2$ and $K=4$.
- **Review Critique:** Unsupervised clustering does not prove the existence of physical boundaries. The transition from a 2-cluster partition in 3D/14D to a 4-cluster partition in 36D is a statistical consequence of optimizing Euclidean distances over a higher-dimensional manifold with different variance structures. Claiming that nature operates with four regimes because 36 variables were clustered is an unfalsified assertion.
- **Corrected Scientific Phrasing:**
  > "The divergence between candidate cluster counts ($K=2$ in Pre-Monsoon and Established Monsoon vs. $K=4$ in Post-Monsoon and Combined 3-Season) is **hypothesized** to arise from differences in feature space dimensionality and vertical layer representation. In low-dimensional spaces dominated by total cloud area and optical thickness, Euclidean distance minimization naturally identifies two broad macroscopic groups (higher vs. lower cloud cover). In the 36-variable space, the inclusion of multi-layer cloud fraction and thermodynamic water path variables introduces orthogonal variance directions that permit the statistical identification of finer sub-groups. However, this remains a working hypothesis; it has not been proven that 36 variables uniquely dictate four true physical cloud regimes."

---

### Correction 2: Complete-Case Filtering and Observation Selection Neutrality

- **Affected Sections in M25.2:** Section 1.2, Section 7 (Missingness and Preprocessing Comparison).
- **Initial Phrasing:** Asserted that complete-case analysis "preferentially eliminates broken cloud decks, thin cirrus, and clear-sky subsidence zones where optical depth or water path retrievals are marginal."
- **Review Critique:** While complete-case filtering removes 16.0% (55,245 observations) in Established Monsoon and over 60% in Pre-Monsoon, the specific meteorological identities of the dropped observations (e.g., broken clouds vs. sensor glint vs. nocturnal retrieval failure) were not empirically profiled with marginality distributions. Attributing specific cloud types to dropped cases without data constitutes unverified conjecture.
- **Corrected Scientific Phrasing:**
  > "Complete-case deletion fundamentally alters the statistical sampling frame by discarding any observation with at least one missing variable (16.0% in Established Monsoon; >60% in Pre-Monsoon). While this ensures that distance calculations operate only on complete vectors, it risks sampling bias. However, **without empirical profiling of the excluded observations, it cannot be asserted which specific physical cloud genres (such as broken clouds or thin cirrus) were preferentially removed**. The excluded observations must be documented strictly as retrieval-ineligible cases rather than specific cloud types."

---

### Correction 3: M25.1 PCA Findings Characterized as Scaling Sensitivity

- **Affected Sections in M25.2:** Section 8.1 (PCA Comparison), Section 11 (M25 and M25.1 Audit Status).
- **Initial Phrasing:** Characterized the dominance of low-cloud optical depth in RobustScaler as an "IQR artifact" and implied that StandardScaler was the scientifically correct baseline.
- **Review Critique:** Neither `StandardScaler` nor `RobustScaler` is inherently "correct" or "incorrect." Scaling methods are mathematical conventions with distinct trade-offs: `RobustScaler` scales by the interquartile range (IQR), making it resistant to heavy tails but sensitive to sparse variables with small IQRs (such as `cldtau_low_1h`), whereas `StandardScaler` scales by standard deviation, which gives greater weight to macroscopic variables with high variance (`cldpress_top_total_1h`).
- **Corrected Scientific Phrasing:**
  > "The differences in PCA explained variance and loadings between `RobustScaler` (PC1 = 69.1% dominated by low-cloud optical depth) and `StandardScaler` (PC1 = 28.4% dominated by cloud-top pressure) represent **scaling sensitivity**, rather than mathematical error or scientific invalidity. The low-cloud weighting under `RobustScaler` arises from a compact interquartile range (IQR = 1.10), whereas `StandardScaler` distributes variance across macroscopic cloud geometry. Scientific interpretations must report these differences as sensitivity to preprocessing assumptions, rather than asserting that one transformation is definitively superior."

---

### Correction 4: Exact Verification of the CA-A Imputation Implementation

- **Affected Sections in M25.2:** Section 7 (Missingness Treatment Table), Section 16.
- **Initial Phrasing:** Referred to CA-A as "cldarea zero-floored" or "clear-sky zero-flooring".
- **Review Critique:** Code inspection of `src/shared/missingness/missingness_treatments.py` reveals that `MissingnessTreatment.CA_A` does not zero-floor cloud area. Instead, it conditionally imputes missing cloud area using the **training median** (`output[missing] = model.median`) while returning a boolean availability mask (`availability_missing = np.isnan(cldarea)`).
- **Corrected Scientific Phrasing:**
  > "In the canonical implementation (`src/shared/missingness/missingness_treatments.py`), missingness treatment **CA-A** is defined as **conditional cloud area imputation using the training median with availability masking**. Unobserved or missing cloud area values are replaced with the training median, while preserving an explicit indicator mask for retrieval status. It does not perform hard zero-flooring."

---

### Correction 5: $K=4$ Designated as Candidate Cloud-Regime Patterns

- **Affected Sections in M25.2:** Section 1 (Executive Summary), Section 9, Section 10 (Nomenclature).
- **Initial Phrasing:** Occasionally described $K=4$ as "proven atmospheric regimes" or "discovered meteorological states."
- **Review Critique:** In unsupervised machine learning, clustering identifies dense regions or partitions in a chosen latent subspace (here, 5D PCA). Calling these statistical clusters "proven atmospheric regimes" confuses statistical clustering with verified meteorological dynamics.
- **Corrected Scientific Phrasing:**
  > "The four clusters ($K=4$) identified by MiniBatchKMeans in the combined three-season analysis are formally designated as **candidate cloud-regime patterns identified by the combined clustering model**, rather than proven meteorological regimes. They represent stable, reproducible statistical partitions within the 5D PCA subspace that require empirical meteorological and dynamical validation (via IMD rainfall in M26 and reanalysis dynamics in M28) before causal physical status can be confirmed."

---

### Correction 6: Selected 30-Day Windows Distinct from Continuous Annual Lifecycle

- **Affected Sections in M25.2:** Section 3 (Study Design), Section 10 (D4 Policy).
- **Initial Phrasing:** Discussed seasonal regime shifts in ways that could be misread as continuous transitions throughout the calendar year.
- **Review Critique:** The study design samples exactly three 30-day windows per year (April 15–May 14, July 15–August 13, October 15–November 13). That totals 90 days per year; 275 days per year are entirely unobserved.
- **Corrected Scientific Phrasing:**
  > "The three 30-day seasonal windows are **discrete seasonal sampling periods**, separated by 60 to 90 unobserved calendar days. They must never be described or interpreted as capturing an uninterrupted annual lifecycle, continuous regime migration, or complete intra-seasonal transitions. All analytical findings apply strictly to the specific 30-day observational windows investigated."

---

### Correction 7: Scope of M25.3 Cross-Season Correspondence Comparisons

- **Affected Sections in M25.2:** Section 12 (Cross-Season Regime Correspondence Design).
- **Initial Phrasing:** Stated that M25.3 will compare seasonal clusters against combined clusters without explicitly defining the matching subsets.
- **Review Critique:** Comparing Pre-monsoon clusters directly to Established or Post-monsoon clusters within M25.3 would confound seasonal climatology with regime morphology. Correspondence must be strictly evaluated within the matching season and identical space-time coordinates.
- **Corrected Scientific Phrasing:**
  > "Milestone M25.3 correspondence comparisons will be conducted **strictly within each matching season and its identical space-time observation coordinates**:
  > - Pre-Monsoon independent cluster assignments ($K=2$) will be compared exclusively against Combined 3-Season assignments ($K=4$) on Pre-Monsoon space-time slices (`season_id == 0`).
  > - Established Monsoon independent cluster assignments ($K=2$) will be compared exclusively against Combined 3-Season assignments ($K=4$) on Established Monsoon space-time slices (`season_id == 1`).
  > - Post-Monsoon independent cluster assignments ($K=4$) will be compared exclusively against Combined 3-Season assignments ($K=4$) on Post-Monsoon space-time slices (`season_id == 2`).
  > No cross-seasonal contingency matrices (e.g., comparing Pre-monsoon clusters against Post-monsoon observations) will be constructed."

---

### Correction 8: GAP-01 Feature-Space Sensitivity Formally Maintained as OPEN

- **Affected Sections in M25.2:** Section 15 (Research Gap Register), Section 18 (Roadmap).
- **Initial Phrasing:** Suggested that Milestone M25.3 would resolve GAP-01 (Pre-Monsoon Feature Mismatch).
- **Review Critique:** Milestone M25.3 performs post-hoc contingency analysis and information-theoretic mapping (NMI, ARI) between existing cluster assignments. Comparing the overlap between a 3-feature cluster and a 36-feature cluster does not resolve the underlying scientific question of how the model would behave if trained on harmonized feature spaces.
- **Corrected Scientific Phrasing:**
  > "**GAP-01 (Feature-Space Sensitivity) remains formally OPEN.** Post-hoc cluster correspondence evaluated in Milestone M25.3 quantifies empirical assignment agreement between differing feature representations, but it cannot resolve feature-space sensitivity. Full resolution of GAP-01 requires a controlled sensitivity experiment evaluating whether 3-feature models and 36-feature models converge when fitted on identical observation cohorts."

---

## 3. Summary of Mandated Epistemic Terminology

| Obsolete / Unverified Terminology | Mandated Epistemic Terminology | Methodological Rationale |
| :--- | :--- | :--- |
| "36 features proven to produce four physical regimes" | "Hypothesized that feature expansion permits statistical identification of finer sub-groups" | Preserves exploratory status of unsupervised clustering. |
| "Complete-case filtering eliminates broken clouds and thin cirrus" | "Complete-case filtering alters the sampling frame; physical genres of dropped cases remain unprofiled" | Avoids unverified physical attribution of discarded data. |
| "RobustScaler low-cloud dominance is an IQR artifact; StandardScaler is correct" | "Scaling sensitivity: RobustScaler amplifies low-cloud IQR; StandardScaler weights macroscopic variance" | Acknowledges scaling as an analytical choice, not binary correctness. |
| "CA-A performs clear-sky zero-flooring" | "CA-A performs conditional median imputation with availability masking" | Accurately reflects codebase implementation (`output[missing] = median`). |
| "Four proven meteorological regimes" | "Four candidate cloud-regime patterns identified by the combined clustering model" | Distinguishes statistical cluster partitions from verified physical mechanisms. |
| "Annual cloud lifecycle / Continuous seasonal transition" | "Seasonal variations across the three discrete 30-day observation windows" | Acknowledges 275 unobserved calendar days per year. |
| "Cross-season cluster correspondence" | "Within-season correspondence on identical space-time observation coordinates" | Prevents conflation of seasonal climatology with regime definition. |
| "GAP-01 resolved by M25.3" | "GAP-01 remains OPEN; M25.3 quantifies post-hoc empirical overlap" | Acknowledges that post-hoc overlap does not harmonize feature spaces. |

---

## 4. Verification and Attestation

This addendum has been reviewed against:
- Codebase file: `src/shared/missingness/missingness_treatments.py` (CA-A verification).
- Codebase file: `src/integration/run_combined_3season_pipeline.py` (M25 array structure and coordinates).
- Codebase file: `src/integration/run_m25_1_validation.py` (M25.1 scaling sensitivity and NaN-masked profiling).
- Manifest file: `reports/integration/m25_2/m25_2_audit_manifest.json` (Audit status and open gaps).

All future milestone documents (M25.3, M25.4, M26, M27, M28) must adhere strictly to the corrected terminology established herein.
