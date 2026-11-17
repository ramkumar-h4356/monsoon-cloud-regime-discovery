# M27.1 — Climate-Index Dataset Inventory and Provenance Report

**Milestone:** M27.1 — NOAA RONI and DMI Climate-Index Audit and Repository Integration Planning  
**Evaluation Date:** 2026-11-17  
**Auditor:** Senior Atmospheric Data Scientist & Scientific Validation Auditor  
**Study Scope:** 2010–2021 (12 Study Years)  
**Parent Framework:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain  

---

## 1. Executive Summary

This inventory establishes the provenance, physical definitions, storage locations, cryptographic integrity, and format specifications of the two climate-index datasets required for **Milestone M27 (ENSO and IOD Climate-Mode Teleconnections and Modulation Analysis)**:
1. **NOAA Relative Oceanic Niño Index (RONI):** Tracking El Niño–Southern Oscillation (ENSO) phase variations while removing global mean tropical warming trends.
2. **NOAA Dipole Mode Index (DMI):** Tracking Indian Ocean Dipole (IOD) zonal sea surface temperature gradient variations.

Both datasets have been verified to cover the complete 12-year study period (2010–2021) with zero missing values and zero duplicate records.

---

## 2. Dataset Inventory and Cryptographic Checksums

| Dataset Identifier | Canonical File Path | Format | Byte Size | SHA256 Checksum | Record Count (Total) | Record Count (2010–2021) |
| :--- | :--- | :---: | :---: | :--- | :---: | :---: |
| **Raw RONI** | `raw_data/NOAA_RONI/RONI.ascii.txt` | ASCII Text (Whitespace) | 14,752 | `1297887f581b6190e459cbbf8bdec9a703ff65c1a229e2de4dd94285254f35c8` | 921 (1950–2026) | 144 |
| **Raw DMI** | `raw_data/NOAA_DMI/dmi.had.long.csv` | CSV (Comma-delimited) | 39,650 | `6f5772b234fa6fce4f32830b5731a003c53e83a30220d85bc371cc8e8d8f69d3` | 1,884 (1870–2026) | 144 |
| **Raw RONI Archive** | `raw_data/NOAA_RONI.zip` | ZIP Archive | 4,160 | `30df08349c6352132bda7757a056c9a3d0d4d6899ccdbfd9bf134a7477c942d8` | 1 file | — |
| **Raw DMI Archive** | `raw_data/NOAA_DMI.zip` | ZIP Archive | 9,585 | `1fd396375f289dea06077c013e9a975508eb78b437511a80345d3600543aaf8d` | 1 file | — |
| **Interim RONI (Study)** | `data/interim/climate_indices/roni_2010_2021.csv` | CSV (Comma-delimited) | 3,138 | `6600c5f060c41f0ffe2059218439c53948f1af08da2796679da0141072af3d90` | 144 (2010–2021) | 144 |
| **Interim DMI (Study)** | `data/interim/climate_indices/dmi_2010_2021.csv` | CSV (Comma-delimited) | 3,519 | `ec773e3fe6aefaec9638bfabcf458375306393eaf99418e4eec6552a0ccb5330` | 144 (2010–2021) | 144 |

---

## 3. Physical Variable Definitions and Scientific Provenance

### 3.1 Relative Oceanic Niño Index (RONI)
* **Source Organization:** National Oceanic and Atmospheric Administration (NOAA) Climate Prediction Center (CPC).
* **Physical Basis:** 
  Standard ONI computes Sea Surface Temperature (SST) anomalies in the Niño 3.4 region ($5^\circ\text{N}–5^\circ\text{S}, 170^\circ\text{W}–120^\circ\text{W}$) using ERSSTv5. However, under ongoing anthropogenically forced climate change, mean tropical SSTs have warmed, leading to an artificial upward baseline drift in standard ONI. 
  **RONI** addresses this non-stationarity by defining:
  $$\text{RONI} = \text{SST}_{\text{Niño 3.4}}^{\prime} - \text{SST}_{\text{Tropics}}^{\prime}$$
  where $\text{SST}_{\text{Tropics}}^{\prime}$ is the area-weighted SST anomaly over the global tropics ($20^\circ\text{N}–20^\circ\text{S}$).
* **Units:** Degrees Celsius ($^\circ\text{C}$).
* **Temporal Resolution:** Overlapping 3-month running seasonal means (DJF, JFM, FMA, MAM, AMJ, MJJ, JJA, JAS, ASO, SON, OND, NDJ; 12 seasons per year).
* **Missing Sentinel:** None in historical study period.
* **Header Structure:** Line 1: `SEAS   YR  ANOM`. Whitespace-delimited columns.

### 3.2 Dipole Mode Index (DMI)
* **Source Organization:** NOAA Physical Sciences Laboratory (PSL) Climate Timeseries.
* **Underlying Dataset:** Met Office Hadley Centre Sea Ice and Sea Surface Temperature data set (HadISST1.1).
* **Physical Basis:** 
  DMI measures the anomalous zonal SST gradient across the equatorial Indian Ocean:
  $$\text{DMI} = \text{SSTA}(\text{Western Pole}) - \text{SSTA}(\text{Eastern Pole})$$
  * **Western Pole:** Equatorial western Indian Ocean ($10^\circ\text{S}–10^\circ\text{N}, 50^\circ\text{E}–70^\circ\text{E}$).
  * **Eastern Pole:** Equatorial southeastern Indian Ocean ($10^\circ\text{S}–0^\circ\text{N}, 90^\circ\text{E}–110^\circ\text{E}$).
* **Units:** Degrees Celsius ($^\circ\text{C}$).
* **Temporal Resolution:** Monthly mean anomalies (12 records per calendar year, dated at `YYYY-MM-01`).
* **Missing Sentinel:** `-9999` (documented in header line: `Date, DMI HadISST1.1  missing value -9999 https://psl.noaa.gov/data/timeseries/month/`).
* **Header Structure:** Line 1 contains metadata; subsequent lines contain comma-separated `date, dmi`.

---

## 4. Study Period Coverage Verification (2010–2021)

Both datasets were subsetted and validated for the 12-year study period:
* **RONI (2010–2021):** Exactly 144 records ($12\text{ years} \times 12\text{ overlapping 3-month seasons}$).
  * First Record: `DJF 2010` ($+1.44^\circ\text{C}$).
  * Last Record: `NDJ 2021` ($-1.08^\circ\text{C}$).
  * Missing Records: 0.
  * Duplicate Records: 0.
* **DMI (2010–2021):** Exactly 144 records ($12\text{ years} \times 12\text{ calendar months}$).
  * First Record: `2010-01-01` ($+0.294^\circ\text{C}$).
  * Last Record: `2021-12-01` ($-0.011^\circ\text{C}$).
  * Missing Records: 0 (no `-9999` values inside 2010–2021).
  * Duplicate Records: 0.

---

## 5. Repository Mirroring and Worktree Parity

* Canonical Repository: `D:\Project Simulator\monsoon_cloud_research`
* Secondary Worktree: `D:\Project Simulator\post_monsoon_research`
* Storage Status:
  * Raw files reside in `raw_data/` in the primary repository.
  * Interim files in `data/interim/climate_indices/` are shared directly via NTFS filesystem junction (`Target: D:\Project Simulator\monsoon_cloud_research\data\interim\climate_indices`).
  * Cryptographic checksums and byte counts match $100\%$.

---

## 6. Audit Verdict

$$\mathbf{VERDICT:}\quad \textbf{VERIFIED — DATASET INVENTORY COMPLETE AND AUDITED}$$
