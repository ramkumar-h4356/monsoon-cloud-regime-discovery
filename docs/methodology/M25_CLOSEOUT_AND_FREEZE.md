# Milestone M25 Closeout and Freeze Record

**Project:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain  
**Milestones Closed & Frozen:** M25 (Combined Discovery), M25.1 (Validation), M25.2 (Reconciliation Audit), M25.3 (Tri-Seasonal Synthesis), M25.3.1 (Acceptance Audit)  
**Status:** **FROZEN WITH DOCUMENTED LIMITATIONS**  
**Date of Freeze:** 2026-11-17  

---

## 1. Frozen Baseline Architecture & Parameters

1. **Authoritative Cloud-Regime Taxonomy (M25.1):**
   - **R0:** Multi-Layer Mixed Convective & Congestus Systems ($Z_{top} = 6.17\text{ km}, P_{top} = 539.0\text{ hPa}, \tau = 3.81, \text{LWP} = 45.7\text{ g/m}^2, \text{IWP} = 19.2\text{ g/m}^2$). Overall prevalence: 12.89%.
   - **R1:** Boundary-Layer Shallow Cumulus & Fair-Weather Low Clouds ($Z_{top} = 1.39\text{ km}, P_{top} = 865.0\text{ hPa}, \tau = 1.49, \text{LWP} = 0.0, \text{IWP} = 0.0$). Overall prevalence: 13.52%. (Peaks at 18.83% Pre-Monsoon, collapses to 2.60% Monsoon).
   - **R2:** Deep Convective Storm Cores & Precipitating Depressions ($Z_{top} = 8.00\text{ km}, P_{top} = 380.0\text{ hPa}, \tau = 10.79, \text{LWP} = 122.5\text{ g/m}^2, \text{IWP} = 125.4\text{ g/m}^2$). Overall prevalence: 1.64%. (Peaks at 2.09% Monsoon).
   - **R3:** Upper-Tropospheric Thin Cirrus & Anvil Outflow Debris ($Z_{top} = 8.44\text{ km}, P_{top} = 402.9\text{ hPa}, \tau = 2.03, \text{LWP} = 0.0, \text{IWP} = 26.6\text{ g/m}^2$). Overall prevalence: 71.94%. (Massive monsoon daily mode: 93.08%).

2. **Approved Seasonal Date Windows (12 Years, 2010–2021):**
   - **Pre-Monsoon:** April 15 00:29 UTC – May 14 23:30 UTC (30 days/yr, 720 h/yr)
   - **Established-Monsoon:** July 15 00:29 UTC – August 13 23:30 UTC (30 days/yr, 720 h/yr)
   - **Post-Monsoon:** October 15 00:29 UTC – November 13 23:30 UTC (30 days/yr, 720 h/yr)

3. **Canonical Spatial Grid:**
   - 32 latitude cells ($6.5^\circ\text{N} - 37.5^\circ\text{N}$ at $1.0^\circ$ resolution).
   - 30 longitude cells ($68.5^\circ\text{E} - 97.5^\circ\text{E}$ at $1.0^\circ$ resolution).
   - Total cells: 960 regular grid cells.
   - Total observations: $24,883,200$ grid-hours across 12 years and 3 seasons.

4. **Final Validated Correspondence Metrics:**
   - **Pre-Monsoon (Hourly, 36 Features):** Cloudy-only $\text{ARI} = +0.1055, \text{NMI} = 0.1420$; All-obs $\text{ARI} = +0.1011, \text{NMI} = 0.1415$. Holdout $\text{NMI} = 0.1480$. Clean bimodal separation.
   - **Established-Monsoon (Daily Aggregation, 14 Features):** Baseline $K=2$ $\text{ARI} = -0.0023, \text{NMI} = 0.0698$; Log $K=2$ $\text{ARI} = +0.0142, \text{NMI} = 0.0732$. Complete cases: $N = 290,355$ (Cluster 0: 155,834; Cluster 1: 134,521). Incomplete cases excluded: 55,245.
   - **Post-Monsoon (Hourly, 36 Features):** M24 $K=4$ $\text{ARI} = -0.0576, \text{NMI} = 0.0422$. Holdout $\text{NMI} = 0.0418$. Many-to-one collapse into R3.

---

## 2. Documented Limitations & Epistemic Boundaries

1. **Experimental Comparability:** Established-monsoon daily clustering (14-feature complete-case subspace) is **NOT directly comparable** to hourly 36-feature models (Pre/Post-Monsoon). Metrics must never be averaged across these incompatible experimental designs.
2. **Clear-Sky Absorption:** The 100% mapping of pre-monsoon clear-sky observations into M25 R3 is a **continuous vector-space artifact of K-means without an explicit clear-sky class**, not physical equivalence between clear sky and cirrus clouds.
3. **Temporal Generalization:** Flat holdout NMI metrics ($pprox 0.04$) reflect **temporal partition consistency of weak correspondence**, not robust physical generalization.
4. **Physical Reality of Regimes:** Statistical clusters represent continuous geometric partitions of the cloud optical/microphysical spectrum. Independent gauge and radar collocation (M26) is required to determine whether they represent discrete meteorological entities.

---

## 3. Cryptographic Verification & Artifact Provenance

- **M25.3 Tri-Seasonal Synthesis Package:**
  - File: `M25.3-integrated-tri-seasonal-synthesis.zip`
  - Size: 290,723 bytes
  - SHA256: `6fc59af15b235a5feb6b6fda0cfabc3d950173554f17268278f7d5b8eb2f874c`
  - Integrity: Verified (CRC32 checked)
- **M25.3.1 Final Scientific Acceptance Package:**
  - File: `M25.3.1-final-scientific-acceptance-audit.zip`
  - Size: 14,064 bytes
  - SHA256: `1f93bf40ddb61625783e63f0163afada7d16d444349bdb904bb4334828ff198b`
  - Integrity: Verified (CRC32 checked)

---

## 4. Milestone Freeze Order

Milestones **M25, M25.1, M25.2, M25.3, and M25.3.1 are hereby formally FROZEN**.
No further retraining, reclustering, date adjustment, coordinate transformation, or feature recalculation shall occur for these milestones. All future research proceeds under Milestone M26.
