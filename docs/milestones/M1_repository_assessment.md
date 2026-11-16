# M1 — Repository Assessment and Correction Plan

**Project:** Satellite Cloud Feature Grouping for Exploratory Weather Pattern Analysis  
**Component:** Established Monsoon  
**Assessment basis:** `monsoon_project_source.zip` (source-only archive, 180 files as reported by the user; 182 ZIP entries including directory entries) and `repository_inspection.txt` from the local Windows repository.  
**Assessment type:** Static source/documentation review. No project datasets were included and no project code was executed against the user's local data during this assessment.

## 1. Scope and research constraints

The assessed component covers 2010–2021, July 15–August 13 inclusive, CERES SYN1deg cloud properties over the 32 × 30 India grid (960 cells; latitude 6.5–37.5; longitude 68.5–97.5). IMD rainfall is an independent association/validation variable, while NOAA RONI and DMI are contextual variables. Rainfall and climate indices must not be used as primary cloud-clustering features. The project does not support causal claims or atmospheric-circulation claims from the current data selection.

## 2. Repository architecture observed

The source archive contains these principal stages:

| Stage | Observed location | Existing role |
|---|---|---|
| Inventory | `src/01_inventory/` | Folder/data inventory utilities |
| Validation | `src/02_validation/` | Dataset inspection, seasonal validation and scientific QC |
| Extraction | `src/03_extraction/` | CERES seasonal extraction |
| Preprocessing | `src/03_preprocessing/` | IMD rainfall and climate-index preparation |
| Aggregation | `src/04_aggregation/` | Hourly-to-daily CERES aggregation |
| Feature engineering | `src/06_feature_engineering/` | Screening, correlations, feature evidence, Group B preparation and spatial availability |
| Clustering | `src/07_clustering/` | KMeans model selection, stability, profiles, temporal/spatial analysis and rainfall association |
| Methodology | `docs/methodology/` | Research method descriptions |
| Reports | `reports/` | QC, preprocessing and feature-engineering reports |
| Results | `results/tables/` | Compact tables and experiment outputs |

The observed implementation is a collection of stage-specific scripts rather than a single orchestrated pipeline. This is not automatically a defect, but reproducible execution order, shared configuration, common validation utilities and experiment metadata should be made explicit as the project matures.

## 3. Existing implementation evidence

### 3.1 Rainfall preparation

`src/03_preprocessing/prepare_established_monsoon_rainfall.py`:
- Resolves the project root relative to `__file__`.
- Checks required inputs and refuses to overwrite existing outputs.
- Locates rainfall and coordinate variables.
- Checks the expected annual date sequence and CERES seasonal dates.
- Checks the expected target grid and coordinate match.
- Checks non-finite/infinite rainfall, negative finite values and `mm` units.
- Produces validation summaries and prepared outputs.

Further explicit checks are still required for coordinate uniqueness, finite coordinate values, coordinate monotonicity/order, and duplicate time coordinates. These checks should be added only after confirming the source data's coordinate conventions.

### 3.2 Rainfall alignment audit

`src/07_clustering/established_monsoon_rainfall_alignment_audit.py`:
- Uses year, date, latitude and longitude as alignment keys.
- Detects duplicate assignment keys.
- Checks expected daily date counts and date agreement.
- Checks assignment and rainfall coordinate sets.
- Uses a one-to-one merge validation for matched observations.
- Preserves a distinct matched-observation audit output.

The review should strengthen validation of assignment labels, year/date consistency, finite and unique coordinates, missing cluster-year combinations, missing/empty comparisons and non-finite values in every downstream summary. It should also distinguish intentionally missing rainfall from invalid data.

### 3.3 Feature preparation

`src/06_feature_engineering/established_monsoon_prepare_group_b.py`:
- Selects the Group B feature set.
- Builds a complete-case matrix.
- Creates baseline and log-transformed standardized matrices.
- Checks finite transformed outputs and negative values before log1p.

Observed issue: this script sets its root with `Path.cwd()`, making it dependent on the directory from which it is launched. Other scripts use paths relative to `__file__`. Standardize path resolution in a later, tested change. The script currently fits scalers on the full descriptive analysis matrix; this is acceptable only for the existing descriptive clustering baseline. Any held-out/predictive evaluation must fit transformations on training/reference data only.

No feature registry was present in the uploaded archive. The final registry should record physical meaning, units, selection rationale, missingness, transformation, scaling and evidence for retention/exclusion.

### 3.4 Daily aggregation

`src/04_aggregation/established_monsoon_daily_aggregation.py` contains substantial input checks, including expected dimensions, spatial grid, hourly record count, strictly increasing time, expected unique days, 24 records per day, infinite-value checks and refusal to overwrite existing outputs. The local repository inventory separately reports this file as modified and several backups as untracked. Those local changes must be preserved and reviewed before any replacement or refactor.

### 3.5 Clustering and analysis

The archive includes MiniBatchKMeans model selection and scripts for stability, physical profiles, temporal/spatial prevalence, coverage sensitivity, change-point analysis and rainfall association. The previous research record reports baseline K=2, log K=2 and log K=3 results. These are established baselines and must remain reproducible; they must not be silently replaced by a new model.

## 4. Assignment-to-implementation gap matrix

| Requirement | Current evidence | Assessment / required action |
|---|---|---|
| M1 repository assessment | Source archive and local Git inventory reviewed | Assessment documented here; current local Git state must be refreshed before changes |
| M2 rainfall validation/alignment | Preparation and alignment audit scripts exist | Partial: add comprehensive coordinate, date, assignment, schema, support and summary checks |
| M3 feature preparation | Screening, correlations, Group B matrix and spatial evidence exist | Partial: feature registry, explicit variance/missingness decisions, reproducible manifest and path/config consistency |
| M4 PCA | No PCA implementation identified in the source archive | Not implemented in supplied source; create full reproducible PCA workflow after M3 |
| M5 t-SNE | No t-SNE implementation identified in the source archive | Not implemented in supplied source; create reproducible parameter experiments after M3 |
| M6 clustering | MiniBatchKMeans selection/stability/profile scripts exist | Partial: preserve existing baselines; compare justified candidate methods and PCA-space clustering; document selection evidence |
| M7 profiling and spatial-temporal analysis | Multiple scripts and result tables exist | Substantially implemented; review integration, support, dependence and consistency after final model selection |
| M8 rainfall reassociation | Existing rainfall association scripts and results exist | Partial: rerun against final assignments and retain baseline-model sensitivity |
| M9 scientific documentation and tests | Methodology and reports exist | Partial: no automated test suite was present in the source archive; add tests, experiment registry and integrated scientific report |
| M10 Git review package | Existing Git history and local uncommitted inventory reported | Pending: final status review, selective staging plan and user-approved commits only |

**Important:** “Not identified” means not present in the uploaded source archive. It does not prove that no such work exists elsewhere on the user's computer. Confirm before creating duplicate implementations.

## 5. Test and configuration inventory

The uploaded source archive did not contain a `tests/` directory, test files, a dependency manifest such as `requirements.txt`/`pyproject.toml`, or a project README. The source-only packaging filter may have excluded files not matching its selected extensions or files larger than 5 MB. Therefore, these are archive-level findings, not definitive claims about the complete local repository.

A static Python syntax parse of the 50 Python source files in the archive completed with zero syntax errors. This does not establish runtime correctness, numerical validity or compatibility with the user's local environment. No dataset-backed test suite was run as part of M1.

## 6. Local Git preservation inventory

The uploaded local inspection report identified branch `feature/established-monsoon-analysis`, synchronized with its remote at the time of inspection, and latest commit `95f123b`. It also identified:
- A modified `src/04_aggregation/established_monsoon_daily_aggregation.py`.
- Numerous untracked feature-engineering and clustering scripts.
- Untracked methodology and scientific-review documents.
- Untracked compact result tables and reports.
- Aggregation backup files.

This inventory is time-specific. Before M2, run a fresh `git status --short --branch` and preserve the current worktree. Do not use `git add .`, discard changes, rewrite history, commit or push without explicit user approval. Never stage raw or processed NetCDF datasets or large intermediate data.

## 7. Main risks and controls

1. **Uncommitted work risk:** the aggregation refactor and untracked analysis work may be lost by broad edits. Control: inspect diffs and exact file ownership before touching files.
2. **Path dependence:** scripts using `Path.cwd()` may fail when launched from another directory. Control: use a consistent project-root resolver and test invocation from multiple working directories.
3. **Data leakage:** fitting transformations before defining evaluation partitions can bias held-out evaluation. Control: distinguish descriptive full-sample clustering from train/reference-fitted evaluation.
4. **Missingness/support bias:** cloud feature and rainfall coverage vary across cells and years. Control: retain support counts, report qualifying cells/years and perform sensitivity analyses.
5. **Model-selection overclaim:** internal scores alone do not establish scientifically meaningful regimes. Control: combine stability, profiles, spatial/temporal behaviour and independent rainfall associations.
6. **Short temporal record:** 12 annual observations limit change-point inference. Control: describe results as exploratory and avoid causal claims.
7. **t-SNE interpretation:** embedding distances and axes are not physical coordinates or global distances. Control: restrict interpretation to local-neighbourhood structure and report parameters/seeds.
8. **Missing runtime environment/data:** archive review cannot prove data-backed execution. Control: execute scripts and tests locally and inspect compact outputs.

## 8. Recommended execution sequence

1. M2: strengthen rainfall preparation and alignment validation without changing the established matching definition.
2. M3: finalize feature registry, preparation manifest, missingness/variance/redundancy decisions and model-ready matrices.
3. M4: PCA on the validated matrix, with explained/cumulative variance, eigenvalues, scores, loadings, component thresholds and sensitivity.
4. M5: reproducible t-SNE parameter grid and embedding metadata; interpret local structure only.
5. M6: preserve existing KMeans baselines; compare justified alternatives and feature-space/PCA-space models; assess stability and original-unit profiles.
6. M7: integrate final model profiles and spatial-temporal prevalence with support and dependence limitations.
7. M8: reassociate rainfall using final assignments while retaining baseline K=2, log K=2 and log K=3 comparisons.
8. M9: automated tests, experiment registry, scientific report and end-to-end reproducibility checks.
9. M10: final worktree review, selective Git staging proposal and user-approved submission.

## 9. M1 exit criteria

- [x] Source archive inventory inspected.
- [x] Main source stages and selected implementation files reviewed.
- [x] Assignment-to-implementation gap matrix prepared.
- [x] Preservation risks and dependencies documented.
- [x] Recommended milestone order documented.
- [ ] User confirms that this assessment matches the intended current repository state.
- [ ] Fresh local Git status and any excluded test/config files are checked before M2.

M1 is therefore **assessment-complete from the supplied archive**, with local-state confirmation remaining before implementation begins.
