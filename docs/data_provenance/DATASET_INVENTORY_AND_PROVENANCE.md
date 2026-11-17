# Dataset Inventory and Data Provenance

## 1. Domain and Grid Coordinates

- **Latitude Range:** 6.0°N to 38.0°N (32 grid cells at 1.0° resolution)
- **Longitude Range:** 68.0°E to 98.0°E (30 grid cells at 1.0° resolution)
- **Spatial Grid:** 32 × 30 = 960 grid cells per hourly observation
- **Observation Count per Seasonal Window:** 720 hourly records (30 days × 24 hours)
- **Hourly Observation Count per Year:** 960 × 720 = 691,200 observations per seasonal file

---

## 2. Primary Dataset: CERES SYN1deg Edition 4.2

### Raw Multi-Month Subsets (`raw_data/CERES/`)
1. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20100401-20110531.nc`
2. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20110703-20120531.nc`
3. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20121003-20131130.nc`
4. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20140104-20150331.nc`
5. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20150407-20150531.nc`
6. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20150601-20160531.nc`
7. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20160708-20170531.nc`
8. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20171009-20181130.nc`
9. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20190110-20200331.nc`
10. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20200412-20210531.nc`
11. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20210714-20211031.nc`
12. `CERES_SYN1deg-1H_Terra-Aqua-NOAA20_Ed4.2_Subset_20211101-20211130.nc`

### Interim Seasonal Extractions (`data/interim/ceres_seasonal/`)
All 36 seasonal NetCDF files verified intact (720 hourly records each):
- **Pre-monsoon** (April 15 – May 14): `CERES_2010_pre_monsoon.nc` to `CERES_2021_pre_monsoon.nc` (12 files)
- **Established monsoon** (July 15 – August 13): `CERES_2010_established_monsoon.nc` to `CERES_2021_established_monsoon.nc` (12 files)
- **Post-monsoon** (October 15 – November 13): `CERES_2010_post_monsoon.nc` to `CERES_2021_post_monsoon.nc` (12 files)

---

## 3. Supporting Datasets

### IMD Gridded Rainfall (`raw_data/IMD_Rainfall/`)
- Daily gridded rainfall files at 1.0°×1.0° resolution: `RFone_imd_rf_1x1_2010.nc` through `RFone_imd_rf_1x1_2021.nc`.
- Extracted daily seasonal CSVs in `data/processed/established_monsoon/daily_rainfall/`.
- Coordinate intersection matching enforced; array index matching strictly prohibited.

### NOAA Climate Indices (`data/interim/climate_indices/` and `raw_data/`)
- **NOAA DMI:** `dmi.had.long.csv` (Hadley Centre Dipole Mode Index anomaly).
- **NOAA RONI:** `RONI.ascii.txt` (ERSSTv5 Real-time Oceanic Niño Index rolling seasonal anomalies).
