# M27.7.2 — Discrepancy, Errata, and Limitation Register

## 1. Executive Summary
This register records all discrepancies identified, investigated, and formally resolved across Milestones M27.7, M27.7.1, and M27.7.2.

## 2. Formally Logged Errata and Resolutions

| Erratum ID | Target Deliverable | Original Finding | Reconciled M27.7.2 Finding | Resolution Status |
|---|---|---|---|---|
| **`ERR-M27.7.2-01`** | Established Monsoon FDR Reporting | Reported $q = 0.0223$ inherited from M27.7 | Independent FDR directly from reproduced p-values yields $q = 0.03740$ (perm) and $q = 0.03041$ (Student t) | **RESOLVED**: Tables and reports updated to reconciled $q = 0.0374$; statistical significance at $q \le 0.05$ confirmed. |
| **`ERR-M27.7.2-02`** | Freedman–Lane Method Naming | Phrased as conventional Freedman–Lane | Permutes predictor residuals $(e_X)$ rather than response residuals $(e_Y)$ | **RESOLVED**: Classified as mathematically equivalent variant under linear partial correlation projection duality. |
| **`ERR-M27.7.2-03`** | Effective Sample Size Phrasing | Described as "13.47 independent years" | Observational span is 12 calendar years; 13.47 represents effective observation count under Kish repeated-measures VIF | **RESOLVED**: Narrative corrected to "approximate effective observation count under design effect". |
| **`ERR-M27.7.2-04`** | Spatial Field Method Designation | Named Livezey–Chen without vector qualification | Applies common year permutation to climate index vectors across fixed 328-cell field | **RESOLVED**: Formally designated as "Year-block spatial field permutation test (Livezey–Chen field counting formulation)". |
| **`ERR-M27.7.2-05`** | CLR Narrative Transcription Error (`ERR-01`) | Copied partial Spearman values into CLR text | Simple CLR correlations are non-significant; partial CLR correlations preserve convective dipole | **RESOLVED**: Narrative erratum corrected; framed as compositional sensitivity analysis. |
| **`ERR-M27.7.2-06`** | Secondary Repo Raw Climate Data (`ERR-02`) | Raw NOAA climate files missing in secondary worktree | `raw_data` was gitignored; mirrored files to worktree | **RESOLVED**: Raw climate files restored; 100% SHA-256 parity achieved. |

## 3. Permanent Documented Limitations
1. Sample size $N=12$ interannual points creates coarse permutation lattices.
2. 30-day seasonal windows do not capture complete annual lifecycle transitions.
3. Observational statistical associations cannot establish dynamical atmospheric causation without coupled modeling.
