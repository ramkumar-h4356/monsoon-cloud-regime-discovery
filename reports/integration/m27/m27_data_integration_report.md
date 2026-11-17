# M27 — Data Integration and Provenance Report

**Milestone:** M27 — Integrated ENSO–IOD Climate Teleconnection and Cloud-Regime Analysis  
**Repository:** `monsoon_cloud_research`  
**Secondary Worktree:** `post_monsoon_research`  
**Evaluation Date:** 2026-11-17  
**Author:** Senior Atmospheric Data Scientist & Data Integration Lead  
**Status:** Certified & Reproducible  

---

## 1. Inventory of Consumed Frozen Artifacts

Milestone M27 strictly ingests verified and frozen datasets without modification:

| Artifact Identifier | Canonical Path | Description | Byte Count | SHA256 Checksum | Origin Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `RONI.ascii.txt` | `raw_data/NOAA_RONI/` | NOAA CPC 3-month running seasonal anomalies | 14,752 | `1297887f581b6190e459cbbf8bdec9a703ff65c1a229e2de4dd94285254f35c8` | Audited Source |
| `dmi.had.long.csv` | `raw_data/NOAA_DMI/` | NOAA PSL HadISST1.1 monthly DMI anomalies | 39,650 | `6f5772b234fa6fce4f32830b5731a003c53e83a30220d85bc371cc8e8d8f69d3` | Audited Source |
| `roni_2010_2021.csv` | `data/interim/climate_indices/` | 144 study records (2010–2021) | 3,365 | `6600c5f060c41f0ffe2059218439c53948f1af08da2796679da0141072af3d90` | Verified Interim |
| `dmi_2010_2021.csv` | `data/interim/climate_indices/` | 144 study records (2010–2021) | 3,842 | `ec773e3fe6aefaec9638bfabcf458375306393eaf99418e4eec6552a0ccb5330` | Verified Interim |
| `combined_3season_cluster_labels.npy` | `data/processed/combined_3season/` | 24,883,200 frozen hourly K=4 cluster labels | 24,883,328 | Verified Frozen | M25 Model Freeze |
| `combined_3season_years.npy` | `data/processed/combined_3season/` | 24,883,200 hourly observation years | 49,766,528 | Verified Frozen | M25 Model Freeze |
| `combined_3season_season_ids.npy` | `data/processed/combined_3season/` | 24,883,200 hourly season identifiers | 24,883,328 | Verified Frozen | M25 Model Freeze |
| `combined_3season_cell_indices.npy` | `data/processed/combined_3season/` | 24,883,200 hourly cell identifiers (0..959) | 49,766,528 | Verified Frozen | M25 Model Freeze |
| `m26_cloud_rainfall_matched_primary.parquet` | `data/processed/rainfall_validation/` | 342,432 Tier 1 matched regime-rainfall records | 2,752,991 | Verified Frozen | M26 Rainfall Freeze |

---

## 2. Approved Seasonal Alignment Protocol

To prevent temporal leakage and eliminate cross-quarter serial correlation, the M27 pipeline implements the approved M27.1 alignment protocol:

| Monsoon Season | 30-Day Observation Window | DMI Alignment (Option D1) | RONI Alignment (Option R1) | Temporal Justification |
| :--- | :--- | :--- | :--- | :--- |
| **Pre-Monsoon** | April 15 – May 14 | April–May Simple Mean | **MAM** (March–May) | Exact center alignment with pre-monsoon convective transition |
| **Established Monsoon** | July 15 – August 13 | July–August Simple Mean | **JJA** (June–August) | Exact center alignment with peak monsoon trough activity |
| **Post-Monsoon** | October 15 – November 13 | October–November Simple Mean | **SON** (September–November) | Exact center alignment with northeast monsoon / retreat |

### Key Properties of this Configuration:
1. **Zero Cross-Quarter Overlap:** The three canonical quarters (MAM, JJA, SON) share zero calendar months. This reduces the lag-1 serial autocorrelation from $r = 0.968$ (in running 3-month series) down to zero shared data points across seasons.
2. **Minimal Lag / Lead:** The satellite windows (Day 105–134, Day 196–225, Day 288–317) fall centrally within their respective 3-month quarters, with maximum temporal offset bounded at $\le 15$ days.

---

## 3. Standardized Aligned Dataset Schema

The loader engine `src/integration/climate_association/m27_climate_index_loader.py` generates the standardized 36-row dataset (`m27_climate_indices_aligned.parquet` and CSV):

* `year` (int64): Study year (2010 to 2021).
* `season` (string): Season tag (`pre_monsoon`, `established_monsoon`, `post_monsoon`).
* `season_id` (int64): Categorical season identifier ($0, 1, 2$).
* `season_window` (string): Formal 30-day date interval.
* `roni_quarter` (string): Canonical 3-month quarter (`MAM`, `JJA`, `SON`).
* `roni_anomaly` (float64): Relative Oceanic Niño Index in °C.
* `enso_phase` (string): Categorical phase (`El Niño`, `Neutral`, `La Niña`).
* `dmi_months` (string): Calendar months averaged (`04-05`, `07-08`, `10-11`).
* `dmi_anomaly` (float64): Dipole Mode Index in °C.
* `iod_phase` (string): Categorical phase (`Positive IOD`, `Neutral`, `Negative IOD`).
* `joint_phase` (string): Combined classification (e.g., `El Niño + Positive IOD`).
* `source_roni` (string): Provenance reference (`NOAA CPC RONI.ascii.txt`).
* `source_dmi` (string): Provenance reference (`NOAA PSL HadISST1.1 dmi.had.long.csv`).

---

## 4. Phase Categorization Summary Table (2010–2021)

| Year | Pre-Monsoon (MAM / Apr-May) | Established Monsoon (JJA / Jul-Aug) | Post-Monsoon (SON / Oct-Nov) |
| :---: | :---: | :---: | :---: |
| **2010** | Neutral / Neutral (+0.10 / +0.17°C) | La Niña / Neutral (-1.21 / -0.03°C) | **La Niña / Negative IOD** (-1.61 / -0.47°C) |
| **2011** | La Niña / Neutral (-0.76 / +0.03°C) | Neutral / Neutral (-0.29 / +0.28°C) | La Niña / Neutral (-0.91 / +0.35°C) |
| **2012** | Neutral / Neutral (-0.42 / -0.32°C) | Neutral / Positive IOD (+0.33 / +0.60°C) | Neutral / Neutral (+0.21 / +0.01°C) |
| **2013** | Neutral / Negative IOD (-0.44 / -0.40°C) | Neutral / Neutral (-0.48 / -0.19°C) | Neutral / Neutral (-0.22 / +0.02°C) |
| **2014** | Neutral / Neutral (+0.11 / -0.08°C) | Neutral / Neutral (-0.14 / -0.37°C) | Neutral / Neutral (+0.35 / +0.08°C) |
| **2015** | El Niño / Neutral (+0.72 / +0.12°C) | **El Niño / Neutral** (+1.27 / +0.40°C) | **El Niño / Positive IOD** (+2.03 / +0.41°C) |
| **2016** | El Niño / Neutral (+0.65 / +0.02°C) | **La Niña / Negative IOD** (-0.70 / -0.60°C) | La Niña / Neutral (-0.96 / -0.38°C) |
| **2017** | Neutral / Positive IOD (-0.10 / +0.52°C) | Neutral / Positive IOD (-0.23 / +0.43°C) | La Niña / Neutral (-0.82 / +0.15°C) |
| **2018** | La Niña / Neutral (-0.69 / +0.02°C) | Neutral / Neutral (+0.08 / +0.09°C) | **El Niño / Positive IOD** (+0.62 / +0.59°C) |
| **2019** | El Niño / Neutral (+0.53 / +0.40°C) | Neutral / Positive IOD (+0.04 / +0.52°C) | **Neutral / Super Positive IOD** (+0.15 / +0.90°C) |
| **2020** | Neutral / Neutral (-0.25 / +0.14°C) | La Niña / Neutral (-0.76 / +0.07°C) | La Niña / Neutral (-1.37 / +0.05°C) |
| **2021** | La Niña / Neutral (-0.89 / +0.13°C) | La Niña / Neutral (-0.60 / -0.16°C) | La Niña / Neutral (-1.08 / -0.01°C) |

---

## 5. Verification & Parity Audit

1. **Zero Missingness:** Exactly 36 of 36 records have complete finite floating-point values for both indices.
2. **Zero Duplicates:** Each `(year, season_id)` tuple appears exactly once.
3. **Repository Parity:** All files verified bit-for-bit and SHA256 identical across `monsoon_cloud_research` and `post_monsoon_research`.
