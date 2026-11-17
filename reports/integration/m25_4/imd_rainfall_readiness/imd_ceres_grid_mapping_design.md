# M25.4 — Technical Design: IMD Rainfall to CERES/M25 Grid Mapping Architecture

**Milestone:** M25.4  
**Scope:** Spatial and Temporal Coupling Architecture for IMD Rainfall and M25 Cloud Regimes  
**Date:** 2026-11-17  

---

## 1. Executive Summary & Grid Geometry

The M25 cloud-regime discovery framework was constructed on the canonical CERES regular $1.0^\circ \times 1.0^\circ$ latitude-longitude grid across India:
- **32 Latitude Centers:** $6.5^\circ\text{N}, 7.5^\circ\text{N}, \dots, 37.5^\circ\text{N}$
- **30 Longitude Centers:** $68.5^\circ\text{E}, 69.5^\circ\text{E}, \dots, 97.5^\circ\text{E}$
- **Total Domain Cells:** $N_{\text{cells}} = 960$

This document specifies the exact mapping mechanics for coupling IMD daily rainfall with M25 daily cloud-regime profiles under two operational scenarios:
1. **Scenario A (Direct 1.0° Native Coupling):** Using the verified local repository archive (`RFone_imd_rf_1x1_YYYY.nc`).
2. **Scenario B (Hierarchical 0.25° Fine-Scale Aggregation):** For future ingestion of the high-resolution IMD 0.25° dataset (`RF25`).

---

## 2. Scenario A: Direct 1.0° Native Coupling (Available Baseline)

### Coordinate Geometry & Bounding:
- The IMD 1.0° dataset has dimensions $33 \times 35$:
  - Latitude: $6.5^\circ\text{N}$ to $38.5^\circ\text{N}$ (33 points)
  - Longitude: $66.5^\circ\text{E}$ to $100.5^\circ\text{E}$ (35 points)
- **Direct Sub-Indexing:**
  - M25 latitude indices $0 \dots 31$ correspond exactly to IMD latitude indices $0 \dots 31$.
  - M25 longitude indices $0 \dots 29$ correspond exactly to IMD longitude indices $2 \dots 31$.
- **Mapping Function:**
  $$R_{\text{M25}}(y, d, \text{lat}_i, \text{lon}_j) = R_{\text{IMD\_1deg}}(y, d, \text{lat}_i, \text{lon}_j)$$
  where coordinate alignment is mathematically identical ($\Delta = 0.000^\circ$).

### Land/Ocean Masking:
- Of the 960 M25 cells, exactly **357 cells** represent Indian terrestrial territory with active gauge coverage.
- The remaining **603 cells** (ocean and foreign land) are encoded as `NaN` (Missing Sentinel `-999.0`).
- Rainfall-regime associations in M26 must be computed strictly across the **357 valid on-land cells**, preventing artificial contamination of regime statistics by missing ocean data.

---

## 3. Scenario B: Hierarchical 0.25° Fine-Scale Aggregation (Target Protocol)

When the 0.25° IMD gridded daily rainfall dataset is acquired, each $1.0^\circ \times 1.0^\circ$ M25 cell will contain a regular $4 \times 4$ lattice of sixteen $0.25^\circ$ sub-cells:
$$\text{Sub-cells per } 1^\circ \text{ cell} = \left(\frac{1.0^\circ}{0.25^\circ}\right) \times \left(\frac{1.0^\circ}{0.25^\circ}\right) = 4 \times 4 = 16$$

### Mathematical Formulation:
For an M25 cell centered at $(\text{lat}_C, \text{lon}_C)$, the sixteen fine cell centers are located at:
$$\text{lat}_k \in \{\text{lat}_C - 0.375^\circ, \text{lat}_C - 0.125^\circ, \text{lat}_C + 0.125^\circ, \text{lat}_C + 0.375^\circ\}$$
$$\text{lon}_m \in \{\text{lon}_C - 0.375^\circ, \text{lon}_C - 0.125^\circ, \text{lon}_C + 0.125^\circ, \text{lon}_C + 0.375^\circ\}$$

The aggregated daily rainfall depth $\bar{R}(C, d)$ is defined as the area-weighted arithmetic mean of all *valid* on-land sub-cells:
$$\bar{R}(C, d) = \frac{\sum_{k=1}^4 \sum_{m=1}^4 w_{km} \cdot R_{0.25}(k, m, d) \cdot I_{km}}{\sum_{k=1}^4 \sum_{m=1}^4 w_{km} \cdot I_{km}}$$
where:
- $w_{km} = \cos(\text{lat}_k)$ represents the spherical earth surface area weight of sub-cell $(k, m)$.
- $I_{km} \in \{0, 1\}$ is an indicator variable equal to $1$ if sub-cell $(k, m)$ contains a valid on-land measurement ($R \ge 0$), and $0$ if masked (ocean, $-999.0$).

### Spatial Coverage Fraction ($F_{\text{cov}}$):
$$F_{\text{cov}}(C) = \frac{\sum_{k=1}^4 \sum_{m=1}^4 I_{km}}{16}$$

---

## 4. Coupling with M25 Daily Cloud Regimes

Daily rainfall cannot be directly matched to hourly cloud observations without introducing severe temporal aliasing (24 duplicate rain values per day). Therefore, M26 coupling must follow the standardized integration key:
$$\text{Key} = (\text{year}, \text{date}, \text{latitude}, \text{longitude})$$

### Regime Coupling Representations:
1. **Daily Dominant Modal Regime ($M_{\text{mode}} \in \{\text{R0, R1, R2, R3}\}$):** The regime occupying the relative majority of the 24 hourly observations in cell $C$ on date $d$.
2. **Continuous Daily Regime Fractions ($f_0, f_1, f_2, f_3 \in [0, 1]$):** Where $f_r$ is the exact proportion of the 24 hours spent in regime $r$ ($\sum_{r=0}^3 f_r = 1.0$).
