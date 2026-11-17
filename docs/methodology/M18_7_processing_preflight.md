# M18.7 — Full Dataset Processing: Partition and Resource Preflight

## Purpose

This preflight freezes the processing partitions and verifies the local inputs and storage requirements before the large transformations begin. It does not transform or modify any CERES file.

## Observation unit and inputs

The observation unit remains one grid-cell × hourly timestamp. Expected input is 36 seasonal NetCDF files (2010–2021 × three seasons), 720 timestamps per file, and a common 32 × 30 grid. This is 25,920 timestamps and 24,883,200 grid-cell-hour observations.

The script verifies exact feature-set membership counts from the existing registry, all selected variables in every input file, matching spatial coordinates, monotonic unique timestamps, and the complete year-season inventory.

## Frozen partition policy

### 1. Primary descriptive dataset

Fit and transform on all years 2010–2021, retaining 2017. This is the final full-period exploratory dataset; because all study years contribute to fitting, it must not be described as a held-out validation result.

### 2. Temporal-transfer diagnostic

Fit imputation and scaling on 2010–2016. Transform 2018–2021 without refitting. Process 2017 separately as a transition diagnostic and do not include it in the primary temporal holdout score. This comparison tests transfer to later observations, but any difference may reflect both atmospheric changes and the previously observed 2017 observing-system discontinuity.

### 3. Exclude-2017 sensitivity

Fit and transform on 2010–2016 and 2018–2021, excluding 2017. Compare the resulting downstream cloud-regime profiles and assignments with the all-year analysis.

No random row split is used. Entire years are kept together to reduce temporal leakage. Spatial/temporal dependence still means grid-cell-hour rows are not independent samples; uncertainty analysis belongs in M18.8 and later clustering evaluation.

## Output design for the subsequent processor

- NetCDF4 with compression and float32 feature values.
- One output file per registered experiment.
- A separate uint8 missingness-code tensor; diagnostic masks are not silently treated as continuous physical features.
- Processing chunks contain 24 timestamps at a time, with exact input ordering retained.
- Atomic publish: write temporary output, validate dimensions/finite values/metadata, then rename to final output.
- Raw CERES NetCDF files remain read-only and excluded from Git.

## Storage estimate

The preflight reports a conservative uncompressed lower-bound estimate for feature values (4 bytes each) plus one uint8 missingness code per feature observation. NetCDF compression may reduce actual storage; added indicator variables and metadata may increase it. The estimate is a planning aid, not a guarantee.

## Execution

```powershell
python "src/06_feature_engineering/prepare_m18_7_processing_preflight.py"
```

Output: `reports/feature_engineering/m18_7_processing_preflight.json`.

A successful preflight means the inputs and configuration are structurally ready. It does not mean the model-ready matrices have been generated.
