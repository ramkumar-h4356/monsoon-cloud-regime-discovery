# M25.4 — IMD Gridded Rainfall Provenance and Acquisition Report

**Milestone:** M25.4  
**Subject:** Provenance, Lineage, and Technical Metadata of IMD Gridded Daily Rainfall Data  
**Date:** 2026-11-17  

---

## 1. Dataset Origin & Custody

- **Official Source:** India Meteorological Department (IMD), National Climate Centre (NCC), Pune, Ministry of Earth Sciences, Government of India.
- **Local Storage Path:** `raw_data/IMD_Rainfall/`
- **Archival Files:** 12 annual NetCDF files: `RFone_imd_rf_1x1_2010.nc` through `RFone_imd_rf_1x1_2021.nc`.
- **Primary Scientific Citations:**
  - Rajeevan, M., Bhate, J., Kale, J. D., & Lal, B. (2006). High resolution daily gridded rainfall data for the Indian region: Analysis of break and active monsoon spells. *Current Science*, 91(3), 296–306.
  - Pai, D. S., Sridhar, L., Rajeevan, M., Kshirsagar, M., & Gore, M. (2014). Development of a new high spatial resolution (0.25° × 0.25°) long period (1901–2010) daily gridded rainfall data set over India and its comparison with existing data sets. *MAUSAM*, 65(1), 1–18.

---

## 2. Technical Characteristics

- **Original Format:** Binary gridded (.grd) format converted to CF-compliant NetCDF via Climate Data Operators (CDO version 1.9.7.1) and Ferret v7.5.
- **Temporal Span:** Full 12-year continuous daily record: January 1, 2010 to December 31, 2021 (4,383 calendar days).
- **Spatial Resolution:** $1.0^\circ \times 1.0^\circ$ regular latitude-longitude grid.
- **Spatial Grid Extent:**
  - Latitude: $6.5^\circ\text{N}$ to $38.5^\circ\text{N}$ (33 points)
  - Longitude: $66.5^\circ\text{E}$ to $100.5^\circ\text{E}$ (35 points)
- **Unit of Measurement:** $\text{mm}$ (daily depth accumulation, 08:30 IST to 08:30 IST next day).
- **Missing Value Sentinel:** `-999.0` (indicates ocean and non-Indian territory).
- **Station Network Density:** Interpolated from approximately 1,800 to 2,141 daily reporting rain-gauge stations across India using Shepard’s modified angular distance weighting algorithm.
