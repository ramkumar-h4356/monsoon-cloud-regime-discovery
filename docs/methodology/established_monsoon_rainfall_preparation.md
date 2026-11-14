# Established Monsoon IMD Rainfall Preparation

## 1. Scope

Prepare independent daily rainfall observations for the established-monsoon
study window, July 15 through August 13, for 2010–2021.

The rainfall source is the IMD 1-degree daily gridded rainfall product.
The source variable is `RAINFALL`, with units of millimetres.

## 2. Spatial alignment

The IMD source grid is 33 × 35. The CERES established-monsoon grid is
32 × 30.

The target latitude and longitude coordinates are selected directly from
the IMD coordinates using exact coordinate matching.

No interpolation, regridding, or spatial averaging is performed.

## 3. Temporal selection

The 30 calendar dates from July 15 through August 13 are selected from
each annual IMD file.

The source already contains daily rainfall values. No additional temporal
averaging or aggregation is applied.

The selected dates must exactly match the corresponding CERES daily dates.

## 4. Missing observations

Missing values decoded from the NetCDF fill-value metadata remain missing.

Missing rainfall observations are not replaced with zero. Zero is retained
only when it is an actual finite rainfall observation.

The spatial validity mask is assessed within each year and compared across
years. Cross-year mask stability is reported rather than assumed.

## 5. Output

One NetCDF file per year is written under:

`data/processed/rainfall_daily/established_monsoon/`

Each output contains:

- `RAINFALL`
- `time`
- `latitude`
- `longitude`

One daily coverage CSV per year and a consolidated validation report
are written under `reports/preprocessing/`.

## 6. Scientific role

Rainfall is an independent validation and association variable. It is
not included as an input to the CERES cloud-regime clustering model.

## 7. Reproducibility

Processing is implemented in:

`src/03_preprocessing/prepare_established_monsoon_rainfall.py`

Original IMD NetCDF files remain unchanged and are excluded from Git.
Processed NetCDF files are also excluded from Git.
