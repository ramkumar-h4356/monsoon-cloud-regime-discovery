# M25.3 — Tri-Seasonal Scientific Audit

**Milestone:** M25.3  
**Auditor:** Senior Scientific Research Auditor, Atmospheric Data Scientist & ML Researcher  
**Scope:** Rigorous methodological audit of all three seasonal correspondence workstreams against the unified M25 three-season baseline.  
**Date:** 2026-11-16  

---

## 1. Audit Dimension 1: M25 Cluster Identity Consistency

### Verification Findings
- The original M25 pipeline profiles (`combined_3season_cluster_profiles.csv`) and M25.1 validation audit (`revised_regime_taxonomy.csv`) were audited across the entire 24.88M observation record.
- Earlier draft notes used casual, conflicting names (*R0: Dry/Low, R1: Mid-Level, R2: Isolated Cirrus, R3: Deep Convection*).
- **Authoritative Physical Resolution:**
  - **R0 (12.89% overall):** Multi-Layer Mixed Convective & Congestus Systems (Top 6.17 km, 539 hPa, $\tau = 3.81$, $\text{LWP} = 45.7\text{ g/m}^2$).
  - **R1 (13.52% overall):** Boundary-Layer Shallow Cumulus & Marine Stratocumulus (Top 1.39 km, 865 hPa, $\tau = 1.49$, $\text{LWP} = 0$). Peaks in Pre-Monsoon (18.83%) and Post-Monsoon (19.15%); collapses in Established Monsoon (2.60%).
  - **R2 (1.64% overall):** Deep Convective Storm Cores & Precipitating Depressions (Top 8.0 km, 380 hPa, $\tau = 10.79$, $\text{LWP} = 122.5\text{ g/m}^2$, $\text{IWP} = 125.4\text{ g/m}^2$). Rare active severe core.
  - **R3 (71.94% overall):** Upper-Tropospheric Thin Cirrus & Convective Anvil Outflow Debris (Top 8.44 km, 402.9 hPa, cold 249 K, $\tau = 2.03$). Overwhelming monsoon dominance (81.71%).
- **Audit Decision:** Retain neutral labels **R0, R1, R2, R3** consistently across all reports. Casual descriptions are expunged.

---

## 2. Audit Dimension 2: Observation Matching & Exclusion Rules

### Verification Findings
1. **Pre-Monsoon:** Exactly 8,294,400 observations matched 1-to-1 with M25. 42,284 clear-sky observations (0.51%) were separated from fitted clusters 0 and 1, providing an exact cloudy population of 8,252,116 observations (99.49%).
2. **Established-Monsoon:** Exactly 290,355 complete-case daily observations matched 1-to-1 with M25's daily aggregation on `(year, date, latitude, longitude)`. Exactly 55,245 incomplete grid-days (15.99%) were excluded due to missing retrievals in Abhin's 14 features. Zero observations were discarded due to spatial indexing errors.
3. **Post-Monsoon:** Exactly 8,294,400 observations matched 1-to-1 with M25 on `(year, time_index, cell_id)`. Zero observations excluded.

---

## 3. Audit Dimension 3: Missingness, Imputation & Feature Spaces

### Scientific Disparity Audit
- **M25 Unified Model:** Imputed missing values using CA-A (cloud area zero-fill) and SA-A (stratum median conditional on cloud area) across 36 CERES features (FS-A), producing 100% complete-case coverage.
- **Pre-Monsoon (Noshin):** Used CA-A imputation on 36 features, but separated operational clear-sky (-1) from cloudy K=2 clustering.
- **Established-Monsoon (Abhin):** Applied strict **complete-case filtering without imputation** across a reduced 14-feature subspace (Group B: total and high clouds only), dropping 15.99% of observations. Low-cloud properties and liquid water path were omitted.
- **Post-Monsoon (M24):** Used CA-A/SA-A imputation across 36 features (FS-A).
- **Audit Conclusion:** The three independent models operated on fundamentally different mathematical subspaces. Correspondence differences reflect both seasonal meteorology and feature-space definitions.

---

## 4. Audit Dimension 4: Cluster Cardinality & Imbalance

- Pre-Monsoon used $K = 2$; Established-Monsoon evaluated $K = 2$ and $K = 3$; Post-Monsoon used $K = 4$; M25 unified model used $K = 4$.
- In Established Monsoon, M25 R3 represents 81.71% of hourly observations and 93.08% of daily dominant modes. In Post-Monsoon, M24 Cluster 3 represents 82.97% of observations.
- This heavy cluster concentration depresses contingency-based categorical indices (ARI), making continuous soft fraction profiling mathematically necessary.

---

## 5. Audit Dimension 5: Temporal Provenance & Reconstructed Models

- In commit `ad52044`, Abhin pushed `RECONSTRUCTED_baseline_k2.joblib`, `recover_models.py`, and `ram_m25_handover_manifest.json`.
- The manifest explicitly warns: *"Reconstructed models are not original serialized fitted estimators... Daily assignments: NOT CONFIRMED."*
- Our audit verifies that `established_monsoon_fixed_cluster_assignments.csv` (commit `51d3efe`) contains daily complete-case records (`year, date, latitude, longitude`), and `ad52044` reconstructed estimators reproduce these assignments with $\text{ARI} = 1.000000000000$.
- In Abhin's manifest, scaling was descriptive across 2010–2021, whereas M25 scalers were fitted strictly on 2010–2016.

---

## 6. Audit Dimension 6: Modal vs Mixture Limitations

- Discretizing 24 hourly labels into a single "dominant regime" conceals diurnal cloud transitions (e.g. morning boundary-layer cumulus evolving into afternoon deep convection).
- Therefore, hard modal ARI must not be evaluated in isolation; continuous soft regime fractions ($f_0, f_1, f_2, f_3$) are required to assess physical cloud mixture.

---

## 7. Audit Dimension 7: Statistical Significance & Inferential Discipline

- **No claims of statistical significance are made without inferential null models.**
- Reported ARI and NMI values are descriptive distance and information-theoretic metrics on complete finite populations. They describe geometric alignment, not p-values.
