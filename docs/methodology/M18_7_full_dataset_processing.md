# M18.7 — Full Dataset Processing

## Purpose

M18.7 executes the 24 Stage A/B experiments registered by M18.6 and produces one compressed NetCDF4 model-ready file per experiment. Each output retains the original time/latitude/longitude structure and contains:

- scaled continuous feature variables (`feature__*`, float32);
- treatment indicators (`indicator__*`, uint8, kept as 0/1 and not scaled);
- a separate missingness classification array for each retained feature (`missingness_code__*`, uint8).

The original CERES NetCDF files are read-only and are never modified.

## Processing scope

This M18.7 execution processes the **primary descriptive partition only**:

- fit years: 2010–2021 inclusive;
- transform years: 2010–2021 inclusive;
- 2017 remains included and is retained as an explicit year coordinate;
- 36 seasonal input files;
- 25,920 hourly timestamps;
- 960 grid cells;
- 24,883,200 grid-cell-hour observations per experiment.

Because imputation and scaling parameters are fitted over the complete 2010–2021 period, these outputs are suitable for full-period descriptive exploratory cloud-regime discovery. They are **not** a held-out temporal validation result. The 2010–2016 to 2018–2021 temporal-transfer diagnostic and the exclude-2017 sensitivity are deferred to M18.8, where their training/holdout boundaries will be enforced separately.

## Registered experiment design

M18.6 registers 24 Stage A/B experiments:

- Stage A: six feature-set baselines (FS-A through FS-F), SA-A + CA-A, RobustScaler, equal weighting.
- Stage B: six feature sets for each of three sensitivities: MD-B + CA-A, SA-B + CA-A, and SA-A + CA-B.

No Stage C scaling sensitivity is executed because no shortlist has been approved yet.

## Missingness treatment integration

### Property features

The M18.3 classifier is applied using each feature's registry-defined matching cloud-area variable:

- 0: observed;
- 1: structural absence (property missing and area exactly zero);
- 2: residual missingness (property missing and area positive);
- 3: unknown cloud availability (property missing and area missing).

The M18.4 treatment functions fit conditional and overall medians using the complete declared primary descriptive fit partition. The fitted medians are then applied to chunks without refitting. MD-B emits a residual-missingness indicator; SA-B emits a structural-absence indicator. All property strategies retain the unknown-cloud-availability indicator supplied by the M18.4 transformer.

### Cloud-area features

- CA-A fits the finite training median, imputes missing cloud-area values, and emits an availability-missing indicator. A measured zero remains zero.
- CA-B is screening-only. Based on the M18.2 audit, `cldarea_low_1h` has 20.567773% missing values and is excluded under the predeclared `>20%` band. The other four cloud-area variables have no missing values and remain. If CA-B encounters a retained cloud-area feature with missing values, processing stops rather than silently imputing it.

The excluded low-cloud-area variable remains available internally during property classification; it is omitted only from the CA-B model matrix.

## Scaling

The processor uses an out-of-core, per-feature fit to avoid constructing the full 24.9-million-row matrix in RAM. It applies the same declared scaling definitions as M18.5:

- RobustScaler baseline: training-partition median and interquartile range;
- StandardScaler sensitivity support: training-partition mean and population standard deviation;
- equal weighting or family-balanced weighting;
- binary treatment indicators are left unscaled.

M18.7 Stage A/B runs use RobustScaler and equal weighting. The out-of-core implementation computes exact per-feature percentiles/means over the complete primary fit partition, then applies those fixed parameters to output chunks. Scaling parameters, feature order, families, masks, weights, and sample count are recorded in each processing manifest.

## Memory and storage strategy

1. One experiment is processed at a time.
2. Selected raw feature arrays are staged as temporary float32 memory-mapped files under `data/processed/m18_work/`.
3. Input is read in 24-hour chunks.
4. Treatment medians and scaling parameters are fitted one feature at a time.
5. The model-ready NetCDF4 is written with zlib compression level 4 and chunked time writes.
6. The output is written to a temporary file, checked, hashed, and atomically renamed.
7. Temporary raw memory maps are deleted after each experiment.

The M18.7 storage estimate includes feature values, missingness codes, and treatment indicators. For the current registry and observation count, the uncompressed estimate is approximately **79.30 GiB**, with a recommended free-space threshold of approximately **95.57 GiB** including a peak raw-work allowance and safety reserve. This is higher than the M18.7 preflight's earlier 63.03 GiB estimate because that estimate counted feature and code arrays but did not include the treatment-indicator arrays.

NetCDF compression may reduce actual disk usage. The processor recalculates available disk space before a full `--all` batch and checks the selected run before a pilot.

## Reproducibility and recovery

- M18.6 configuration and feature-registry hashes must match the registered run table.
- The M18.7 preflight report must be present, have `PASS` status, and match the current input file and observation counts.
- One output NetCDF4 and one JSON processing manifest are written per run.
- The manifest records input inventory metadata, feature order, treatment decisions, missingness counts, scaling parameters, output size, and output SHA-256.
- M18.6 run statuses are updated to RUNNING, COMPLETED, or FAILED.
- Completed runs are skipped on resume. A completed output/manifest pair can recover a registry status update if the process was interrupted after the output was safely published.
- A stale or unverifiable output is not overwritten automatically.

## Output paths

- NetCDF4 outputs: `data/processed/m18_model_ready/<run_id>.nc`
- Temporary work: `data/processed/m18_work/<run_id>/` (removed after each run)
- Processing manifests: `reports/feature_engineering/m18_7_processing_manifests/<run_id>.json`
- Run statuses: `reports/feature_engineering/m18_experiment_registry.csv` and the M18.6 per-run manifests.

Do not commit generated NetCDF4 model-ready outputs or temporary work directories to Git. Commit the processor, tests, configuration, and methodology only.

## Execution order

1. Run the processor tests.
2. Run `--estimate` to recalculate the indicator-inclusive storage requirement and current free space.
3. Run `--pilot` for the Stage A FS-A baseline only.
4. Inspect the pilot NetCDF4 and processing manifest, then confirm the run is marked COMPLETED.
5. Only after pilot review, run `--all` to process the remaining registered experiments. Completed runs are skipped automatically.

## Limitations

- M18.7 does not perform PCA, t-SNE, clustering, rainfall association, or scientific interpretation.
- The primary descriptive fit uses all 2010–2021 years, so it must not be described as a temporal holdout evaluation.
- Temporal-transfer and exclude-2017 sensitivity processing remain M18.8 work.
- CA-B's retained area variables must be complete; the processor intentionally fails rather than inventing an imputation rule for a screening-only strategy.


## Timestamp interval handling correction

The processor requires each source file to contain the expected number of timestamps,
with strictly increasing, unique time coordinates. It does not require every adjacent
timestamp to be exactly one hour apart. Any observed interval differences are retained
and recorded in the input manifest (minimum, median, maximum interval and count of
non-hourly intervals). No missing timestamps are synthesized and no temporal
interpolation is performed. Output time coordinates are stored as seconds since the
Unix epoch so minute-level source timestamps are not truncated to whole hours.
