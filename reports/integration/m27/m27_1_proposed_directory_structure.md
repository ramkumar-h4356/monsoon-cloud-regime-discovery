# M27.1 — Proposed Directory Structure and Code Organization

**Milestone:** M27.1 — NOAA RONI and DMI Climate-Index Audit and Repository Integration Planning  
**Evaluation Date:** 2026-11-17  
**Auditor:** Senior Atmospheric Data Scientist & Software Architect  

---

## 1. Directory Structure Architecture

To ensure complete backward compatibility with frozen M25/M26 artifacts and seamless dual-repository parity, the following directory layout is formalized for Milestone M27:

```
monsoon_cloud_research/
├── raw_data/
│   ├── NOAA_RONI/
│   │   └── RONI.ascii.txt                 # [Audited] NOAA CPC 3-month running seasonal anomalies (1950–2026)
│   └── NOAA_DMI/
│       └── dmi.had.long.csv               # [Audited] NOAA PSL HadISST1.1 monthly anomalies (1870–2026)
│
├── data/
│   ├── interim/
│   │   └── climate_indices/
│   │       ├── roni_2010_2021.csv         # [Verified] 144 seasonal records (2010–2021)
│   │       └── dmi_2010_2021.csv          # [Verified] 144 monthly records (2010–2021)
│   └── processed/
│       ├── combined_3season/              # [FROZEN M25] 24,883,200 hourly cluster labels & features
│       └── rainfall_validation/           # [FROZEN M26] 342,432 Tier 1 matched regime-rainfall records
│
├── src/
│   └── integration/
│       └── climate_association/
│           ├── m27_1_climate_index_audit.py          # [M27.1] Readiness audit and verification engine
│           ├── m27_climate_index_loader.py           # [M27 Pipeline] Aligned annual-seasonal index loader
│           ├── m27_regime_climate_correlation.py     # [M27 Pipeline] Spearman & partial correlation engine
│           ├── m27_rainfall_climate_modulation.py    # [M27 Pipeline] Terrestrial rainfall modulation & LOOCV
│           ├── m27_spatial_teleconnections.py        # [M27 Pipeline] 328-cell spatial composite anomaly engine
│           ├── m27_joint_enso_iod_interaction.py     # [M27 Pipeline] 2x2 phase matrix & co-occurrence dynamics
│           └── m27_orchestrator.py                   # [M27 Pipeline] End-to-end execution orchestrator
│
├── tests/
│   └── integration/
│       ├── test_m27_1_climate_index_readiness.py     # [M27.1] Readiness test suite (12 tests)
│       └── test_m27_climate_modulation.py            # [M27 Pipeline] Full execution integration test suite
│
└── reports/
    └── integration/
        └── m27/
            ├── m27_1_dataset_inventory_and_provenance_report.md
            ├── m27_1_roni_quality_control_report.md
            ├── m27_1_dmi_quality_control_report.md
            ├── m27_1_temporal_alignment_comparison.md
            ├── m27_1_scientific_methodology_proposal.md
            ├── m27_1_statistical_analysis_design.md
            ├── m27_1_risks_and_unresolved_questions.md
            ├── m27_1_proposed_directory_structure.md
            ├── m27_1_baseline_test_report.md
            ├── m27_1_acceptance_recommendation.md
            ├── m27_1_manifest.json
            ├── tables/                               # [M27 Output] Statistical CSV tables
            └── figures/                              # [M27 Output] Publication-quality 300 DPI figures
```

---

## 2. Worktree Mirroring Strategy

* All code, tests, and markdown reports will be mirrored to `post_monsoon_research`.
* Data in `data/interim/climate_indices/` and `data/processed/` are already linked via transparent NTFS directory junctions and will remain unmodified.
* Checksums and byte counts will be cryptographically verified after mirroring.

---

## 3. Audit Verdict

$$\mathbf{VERDICT:}\quad \textbf{VERIFIED — DIRECTORY STRUCTURE RATIFIED}$$
