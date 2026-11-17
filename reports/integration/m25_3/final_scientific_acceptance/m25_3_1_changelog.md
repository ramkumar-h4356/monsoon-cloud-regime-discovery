# M25.3.1 Change Log — Acceptance Register Harmonization

**Date:** 2026-11-17  
**Scope:** Administrative wording harmonization in Milestone M25.3.1 acceptance register.  

## Summary of Change
- **Previous Value in Evidence Matrix (Row 4):** `CORRECTION_REQUIRED`
- **Updated Value in Revised Matrix:** `ACCEPTED_WITH_CORRECTED_REPORTING_ERRATUM`

## Rationale
In Milestone M25.3.1, the overall milestone acceptance decision was determined as:
`READY TO FREEZE WITH DOCUMENTED LIMITATIONS`.

However, Row 4 of the evidence matrix retained the draft category `CORRECTION_REQUIRED` for the Established-Monsoon population counts (where text reported 82,045 and 208,310 instead of the verified 155,834 and 134,521).

Because:
1. The underlying source data artifact (`established_monsoon_fixed_cluster_assignments.csv`) and numerical profile arrays were verified as 100% correct (155,834 for Cluster 0, 134,521 for Cluster 1, Total 290,355);
2. Zero data or model recalculation was required;
3. The erratum existed solely in the narrative reporting text;

The register wording is harmonized to `ACCEPTED_WITH_CORRECTED_REPORTING_ERRATUM`. The original `m25_3_evidence_matrix.csv` is preserved, and `m25_3_evidence_matrix_revised.csv` represents the authoritative harmonized register.
