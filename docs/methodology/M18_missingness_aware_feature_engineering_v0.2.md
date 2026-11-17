# M18 — Missingness-Aware Feature Engineering and Model-Ready Dataset Design

**Status:** Design specification v0.2 — proposed, not yet approved or executed  
**Study:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain  
**Study period:** 2010–2021  
**Seasons:** pre-monsoon (15 Apr–14 May), established monsoon (15 Jul–13 Aug), post-monsoon (15 Oct–13 Nov)  
**Domain:** 6–38°N, 68–98°E  
**Primary grid:** CERES SYN1deg 1-hourly, 32 × 30 grid

## 1. Purpose

This specification defines comparable candidate feature sets and a missing-data treatment plan before producing the final model-ready matrix. It does not modify raw or existing processed data.

The clustering objective is exploratory cloud-regime discovery. IMD rainfall, RONI and DMI are not clustering inputs:
- IMD rainfall is reserved for independent association/validation.
- RONI and DMI are reserved for climate-context analysis.
- Cloud-phase variables are reserved for separate categorical profiling unless a later, explicitly designed mixed-data experiment is approved.

## 2. Observation unit and scale

The observation unit is one **grid-cell × hourly timestamp**.

There are 36 seasonal files, each with 720 timestamps and 960 grid cells:
- 25,920 hourly timestamps across all files.
- 24,883,200 grid-cell-hour observations before missing-value filtering.

Do not confuse timestamp count with grid-cell-hour sample count. Avoid loading the entire multi-feature matrix as float64 without a memory estimate. Prefer chunked processing and float32 storage after numerical validation.

## 3. Candidate pool

Start from the 36 continuous variables classified `ELIGIBLE_CANDIDATE` in `reports/data_quality/ceres_feature_screening_summary.csv`. The feature-set registry has been validated with these membership counts: FS-A 36, FS-B 21, FS-C 21, FS-D 21, FS-E 16 and FS-F 21. Reconfirm the exact variable names from the screening report when the execution pipeline is built; counts alone are not a substitute for a variable-level manifest.

Keep the following outside the initial continuous pool:
- Four high-missingness variables: `lwp_mid_high_1h`, `iwp_mid_low_1h`, `lwp_high_1h`, `iwp_low_1h`.
- Five cloud-phase variables: categorical, not continuous measurements.

The 36-variable pool remains a candidate pool, not a final feature list. Re-run schema checks against the screening report before building any matrix. The report's `variable`, `status`, and `vertical_layer` columns are expected by the current audit scripts; verify exact column names rather than silently guessing if the file changes.

The feature-set counts are a registry validation target, not proof that every family has every layer. Preserve the exact variable membership in the generated registry and record it in the transformation manifest.

## 4. Feature-set experiments

All feature sets use the same rows, study period, spatial domain, temporal windows, scaling protocol, clustering algorithm and evaluation protocol. Only the feature families differ. This makes the comparisons interpretable.

### FS-A — Full eligible candidate pool

Include all 36 eligible continuous candidates.

Purpose:
- Establish a broad baseline.
- Reveal whether correlated vertical-structure variables dominate the distance metric.
- Serve as a reference, not automatically the preferred final model.

### FS-B — Effective-height representation

Include:
- Cloud-area fraction variables (`cldarea_*`).
- Cloud optical-depth variables (`cldtau_*`).
- Eligible liquid/ice water-path variables (`lwp_*`, `iwp_*`).
- Effective cloud-height variables (`cldhght_*`).

Exclude effective-pressure, cloud-top-pressure and effective-temperature families from this variant.

Purpose: retain a single representative vertical-structure family while preserving cloud amount and physical-property information.

### FS-C — Effective-pressure representation

Include:
- Cloud-area fraction variables.
- Cloud optical-depth variables.
- Eligible liquid/ice water-path variables.
- Effective cloud-pressure variables (`cldpress_*`).

Do not include cloud-top-pressure variables (`cldpress_top_*`) in this variant. They are a distinct product definition and should be tested separately rather than duplicated alongside effective pressure.

Purpose: compare pressure-based vertical representation with FS-B.

### FS-D — Effective-temperature representation

Include:
- Cloud-area fraction variables.
- Cloud optical-depth variables.
- Eligible liquid/ice water-path variables.
- Effective cloud-temperature variables (`cldtemp_*`).

Purpose: compare temperature-based vertical representation with FS-B and FS-C.

### FS-E — Physical-property representation without vertical descriptor

Include:
- Cloud-area fraction variables.
- Cloud optical-depth variables.
- Eligible liquid/ice water-path variables.

Exclude effective height, effective pressure, cloud-top pressure and effective temperature.

Purpose: determine whether cloud amount and optical/water properties provide useful regime separation without a separate vertical descriptor.

### FS-F — Cloud-top-pressure sensitivity

Include the FS-E families plus eligible cloud-top-pressure variables (`cldpress_top_*`), but exclude effective pressure (`cldpress_*` excluding `cldpress_top_*`), effective height and effective temperature.

Purpose: test cloud-top pressure as an alternative vertical descriptor. This is a sensitivity experiment, not a default choice.

**Configuration rule:** apply include rules first, then exclusions. Because `cldpress_top_` begins with `cldpress_`, do not use a broad `cldpress_` exclusion for FS-F. Use the anchored exclusion pattern `^cldpress_(?!top_).*$` for effective pressure only.

**Important:** Family membership is resolved from the actual 36-variable screening report. The patterns above are selection rules, not a claim that every named family has every layer represented.

## 5. Missingness taxonomy

For each layer-specific property, join it to the corresponding cloud-area variable for the same layer and same grid-cell/hour. The validated mapping covers `cldhght_*`, `cldpress_*`, `cldpress_top_*`, `cldtemp_*`, `cldtau_*`, `lwp_*` and `iwp_*`. Extract the layer suffix and map it to `cldarea_{layer}_1h`, using the valid layers `high`, `mid_high`, `mid_low`, `low` and `total`. Test `cldpress_top_` before `cldpress_` so the cloud-top-pressure family is not parsed as an invalid `top_*` layer. Cloud-area variables do not map to themselves.

Classify each observation into:

1. **Observed property:** property is finite.
2. **Cloud-absence-associated undefined property:** matching cloud area is finite and exactly zero, while the property is missing.
3. **Residual missing property:** matching cloud area is finite and positive, while the property is missing.
4. **Unknown cloud availability:** matching cloud area is itself missing.

Do not infer cloud absence when the matching cloud-area value is missing. Do not convert all missing values to zero.

The broader regenerated area-association audit and production regression tests now validate the layer mapping. In particular, all five `cldpress_top_*` variables map to their matching cloud-area variables across 12 years and 3 seasons (180 aggregate records). In those audit records, property missingness was associated with zero cloud area in all reported cases, while no missingness was reported for positive cloud area. This is evidence for those variables and the audited records only; it does not establish that every missing value in every CERES variable is structural. The production mapping tests passed all 35 property-family/layer combinations, along with invalid-name and missing-partner cases.

## 6. Proposed transformation experiments

The following are candidate treatments to compare, not yet executed decisions.

### MD-A — Conditional-median baseline

For each layer-specific property:
- Keep the matching cloud-area feature in the feature set.
- For observations where cloud area is exactly zero and the property is missing, mark the property as structurally undefined.
- For numerical matrix construction, replace structurally undefined property values with the median of that property's observed values where matching cloud area is positive.
- For residual missingness where cloud area is positive, use the same conditional median, fitted on the training partition only.
- If cloud area is missing, do not label the property as structurally undefined. Treat it as unresolved missingness and use the fitted feature median only for the numerical matrix, retaining a separate diagnostic mask.

After robust scaling, a conditional-median fill maps to the median (approximately zero after centering), while the cloud-area feature retains the cloud-absence information. This is a modelling convention and must be tested against sensitivity alternatives.

### MD-B — Conditional-median plus residual-missingness indicators

Use MD-A and add a binary indicator for residual missingness when cloud area is positive. Do not add an indicator for structural absence if the cloud-area feature already represents it; test that separately only if justified.

Purpose: assess whether retrieval availability itself is influencing clusters.

### MD-C — Conservative feature exclusion

Use the MD-A treatment, but exclude a feature from a given experiment if its residual missingness among positive-area observations exceeds a predeclared threshold or is highly unstable across seasons/years.

Initial diagnostic bands (heuristics, to be reviewed):
- ≤5% residual missingness: low concern.
- >5% to 20%: retain only with sensitivity analysis.
- >20%: exclude from the primary variant unless a strong scientific justification exists.

These are project screening thresholds, not NASA quality thresholds.

### SA-A — Structural-absence indicator sensitivity

Use the MD-A imputation treatment and add an indicator only for cloud-absence-associated undefined values (property missing while matching cloud area is finite and zero). This tests whether explicitly encoding structural absence changes the result. It is a sensitivity experiment, not an assumption that undefined physical properties have a meaningful numeric zero.

### SA-B — Combined structural- and residual-indicator sensitivity

Use the MD-A imputation treatment and add separate indicators for structural-absence-associated missingness and residual missingness. Compare this with MD-A, MD-B and SA-A to isolate the contribution of each indicator type.

### MD-D — Indicator comparison protocol

Compare MD-A, MD-B, SA-A and SA-B under otherwise identical feature sets, rows, imputation values, scaling, clustering algorithm/parameters and random seeds. If cluster assignments strongly track missingness indicators, investigate potential retrieval-system artifacts before interpreting regimes. MD-D is a comparison protocol, not a separate imputation algorithm.

## 7. Imputation and scaling safeguards

- Fit imputation statistics and scalers on the training data only during temporal holdout or stability experiments.
- Never fit an imputer or scaler using validation/test years.
- For a final descriptive model fitted to the full study period, record that all-period statistics were used.
- Use robust scaling as the initial candidate because cloud properties may be skewed and contain outliers; compare with standard z-score scaling.
- Preserve physical zero values in cloud-area fraction and other variables where zero is valid.
- Do not standardize categorical cloud-phase codes as continuous values.
- Keep a row-level quality/availability mask outside the feature matrix; retain separate masks for structural absence, residual missingness and unknown cloud availability.
- Do not replace structurally undefined properties with numeric zero. The conditional-median fill is a computational convention; compare it with the indicator sensitivities before selecting a primary treatment.
- Record all imputation values, feature order, scaler parameters, source file names and code/config versions.

## 8. Feature-family weighting

The full 36-feature set may overweight vertical structure because several correlated variables describe related properties.

Compare:
- Equal weight per standardized feature.
- Family-balanced weighting, where each feature family's total squared contribution is normalized so a large family does not dominate solely because it contains more variables.

Do not choose weights after inspecting which option gives the preferred scientific story. Predefine the comparison and report both.

## 9. Spatial and temporal validation

- Use predefined contiguous year-block holdouts or block resampling rather than random row splits as the primary temporal robustness check. Record the exact held-out years before fitting.
- Fit imputation statistics and scalers separately within each training partition; never allow validation-year information into preprocessing.
- Include a fit excluding 2017 and compare assignments/profiles with the all-year fit.
- Assess whether cluster profiles are stable across the three seasonal windows.
- Account for spatial and temporal autocorrelation; millions of grid-cell-hour rows are not millions of independent atmospheric samples.
- Use spatial/temporal block resampling or aggregated diagnostics for uncertainty, rather than naive independent-row standard errors.

## 10. 2017 discontinuity handling

Retain 2017 in the primary study period. Do not remove it solely because missingness changed.

Required sensitivity comparisons:
- All years 2010–2021.
- Excluding 2017.
- If feasible, pre-2017 versus post-transition period summaries, with the transition described as a possible observing-system discontinuity rather than a proven cause.

No satellite-specific attribution should be made from the current global metadata alone.

## 11. Model-ready dataset outputs

The eventual pipeline should produce:
- A feature-set registry listing exact variables for FS-A through FS-F.
- A row index with timestamp, UTC hour, latitude, longitude, year and season.
- A separate availability/missingness mask.
- One transformed matrix per feature-set × missingness-treatment experiment.
- A transformation manifest with feature order, units, fill values, scaling parameters, input file list, software versions and random seeds.
- A report of dropped rows/features and residual missingness after transformation.

Keep raw CERES, IMD, RONI and DMI files out of Git. Track scripts, configuration, small reports and documentation only.

## 12. Approval gates before execution

Do not generate the final model-ready matrix until:
1. Exact 36-feature membership is resolved from the screening CSV and FS-A–FS-F variable membership/counts are validated.
2. Cloud-area-to-property layer mapping is validated for every included layer-specific property.
3. Variable definitions and units are checked.
4. MD-A is compared with MD-B and the structural-absence sensitivities SA-A and SA-B.
5. The 2017 sensitivity experiment is included in the evaluation plan.
6. Year-blocked validation partitions are defined before fitting, with preprocessing fitted on training partitions only.
7. Memory requirements and chunking strategy are tested on a small sample.
8. Raw datasets and large intermediate outputs remain outside Git.

## 13. Current status

This document defines a proposed experiment design. It does not claim that a final feature set, imputation method, cluster count or clustering algorithm has been selected.

## 14. Revision notes for v0.2

- Added explicit structural-absence indicator sensitivities (SA-A and SA-B) alongside the residual-missingness indicator experiment (MD-B).
- Clarified that MD-D is a controlled comparison protocol, not a separate imputation algorithm.
- Corrected the FS-F selection rule so cloud-top pressure (`cldpress_top_*`) is retained while effective pressure (`cldpress_*`, excluding the top-pressure family) is excluded.
- Recorded the validated cloud-area layer mapping and its production regression-test status.
- Added explicit feature-set membership-count targets and strengthened year-blocked validation and execution gates.

**Execution status remains unchanged:** no model-ready feature matrix, imputation, scaling or clustering experiment is claimed to have been executed by this specification.
