# PR #1 submission manifest and archive boundary

This document records the exact conditionally approved 159-file Git submission on
feature/pre-monsoon-analysis. It is a code-and-lightweight-results package, not
a self-contained data/model archive. No frozen scientific artifact is rewritten.

## Scientific reference and report scope

The final model is results/models/phase2/pre_monsoon/stage2_v1/selected_pre_monsoon_bundle.joblib.
Its SHA256 is 4c26f58fcc842aa4c7da5d6547225a1d9ae25171f29f083014c31e4849233569.
It was fitted on the saved 70,000 observations from 2010-2016. Development
is 2017-2018; the frozen temporal evaluation is 2019-2021. Features are total
cloud area /100, log1p total optical depth, and total cloud-top pressure.
Three PCs were retained (two explain 86.433929%); actual dimensionality
reduction was not achieved. k=2 is a descriptive partition, not an independently
validated meteorological cloud type. Phase 1 previously explored holdout years.

Read reports/handoff/remediation_v1/report/SCIENTIFIC_HANDOFF.md first; it
qualifies historical wording and includes the original scientific report
verbatim. The core evaluation/model-analysis code was frozen before access;
later presentation/completion helpers have separate hashes. The immutable
Stage 3 freeze is reports/phase3/pre_monsoon/stage3_v1/freeze/frozen.json.
Development evidence is reports/phase2/pre_monsoon/stage2_review.md.
The pooled holdout scores are silhouette 0.416583, CH 2702.887303 and DB 0.953121.
Pooled silhouette/CH are slightly less favorable than development; no tuning
or refitting followed. The 43-test receipt is
reports/handoff/remediation_v1/tests/all_tests.txt. Tests fit synthetic fixtures only.

## What a Git checkout can reproduce

The code, tests, methods, summary metrics, selected coordinates and figures
below are included. All paths in reports and instructions are repository-root
relative unless explicitly presented as Markdown links or absolute historical
metadata. Source run IDs remain stage1_v1, stage2_v1,
stage2_tsne_sensitivity_v1 and stage3_v1. Do not rerun historical evaluation
writers to regenerate this submission; their existing output paths are refused.

A complete byte-preserving audit archive is required for handoff.py verify or
the historical full artifact verifiers. A Git checkout alone cannot satisfy
the archived hash inventories because models, datasets, labels, training arrays,
bulk samples, noncanonical experiments, legacy transcripts and scratch snapshot
files are intentionally excluded. Manifests retain those original references
and hashes without pretending the omitted files are present in Git.
No archive upload, Git LFS migration, model publication or new evaluation is
authorized by this submission. The complete archive remains local.

Use the Windows CPython 3.13.7 version lock under environment/; it captures
all 31 installed distributions and active dependency closure. It is not a
wheel-hash lock. No fresh network installation or offline wheelhouse was tested.
The artifact-only CLI has independent --run-id and --output-id options.
README.md documents the full-copy requirement and safe commands.

The prospective robust_diagnostics_v2 API handles empty support and has
positive-support parity tests. It was not patched into the frozen evaluator,
and no completed holdout result was recomputed for this remediation.

## Exact approved staging manifest

Files are listed literally, without wildcard staging. The two submission-control
files are .gitattributes and this document.

### Source code (15)

```text
src/06_feature_engineering/ceres_features.py
src/06_feature_engineering/prepare_pre_monsoon.py
src/07_clustering/pre_monsoon_stage2_model.py
src/07_clustering/run_pre_monsoon_stage2.py
src/08_evaluation/build_pre_monsoon_stage2_review.py
src/08_evaluation/build_pre_monsoon_stage3_completion.py
src/08_evaluation/pre_monsoon_stage2_diagnostics.py
src/08_evaluation/pre_monsoon_stage3_tools.py
src/08_evaluation/run_pre_monsoon_stage3.py
src/08_evaluation/verify_pre_monsoon_stage2.py
src/08_evaluation/verify_pre_monsoon_stage3.py
src/09_visualization/plot_pre_monsoon_stage3_summary.py
src/09_visualization/pre_monsoon_stage2_tsne_sensitivity.py
src/10_handoff/handoff.py
src/10_handoff/robust_diagnostics_v2.py
```

### Tests (5)

```text
tests/test_handoff_v2.py
tests/test_stage1.py
tests/test_stage2.py
tests/test_stage2_tsne_sensitivity.py
tests/test_stage3.py
```

### Configurations and environment (9)

```text
config/ceres_feature_definitions.json
config/pre_monsoon_stage1.json
config/pre_monsoon_stage2.json
config/pre_monsoon_stage2_tsne_sensitivity.json
config/pre_monsoon_stage3.json
environment/environment-reference.json
environment/requirements-windows-py313.lock
requirements-stage1.txt
requirements-stage2.txt
```

### Documentation and submission controls (7)

```text
README.md
docs/methodology/pre_monsoon_stage1_protocol.md
docs/methodology/pre_monsoon_stage2_protocol.md
docs/methodology/pre_monsoon_stage3_protocol.md
environment/LOCKFILE.md
.gitattributes
docs/submission/PR1_SUBMISSION.md
```

### Reports and provenance (34)

```text
reports/handoff/remediation_v1/environment/pip_check.txt
reports/handoff/remediation_v1/environment/receipt.json
reports/handoff/remediation_v1/historical_inventory.json
reports/handoff/remediation_v1/plot/manifest.json
reports/handoff/remediation_v1/remediation_manifest.json
reports/handoff/remediation_v1/report/SCIENTIFIC_HANDOFF.md
reports/handoff/remediation_v1/report/manifest.json
reports/handoff/remediation_v1/tests/all_tests.txt
reports/handoff/remediation_v1/verify/receipt.json
reports/phase2/pre_monsoon/stage1_serialization_verification.json
reports/phase2/pre_monsoon/stage1_v1/manifest.json
reports/phase2/pre_monsoon/stage1_v1/report.md
reports/phase2/pre_monsoon/stage2_review.md
reports/phase2/pre_monsoon/stage2_review_manifest.json
reports/phase2/pre_monsoon/stage2_tests.txt
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_tests.txt
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/manifest.json
reports/phase2/pre_monsoon/stage2_v1/manifest.json
reports/phase2/pre_monsoon/stage2_v1/report.md
reports/phase2/pre_monsoon/stage2_v1_verification.json
reports/phase3/pre_monsoon/stage3_all_tests.txt
reports/phase3/pre_monsoon/stage3_v1/completion_manifest.json
reports/phase3/pre_monsoon/stage3_v1/evaluation/holdout_access_receipt.json
reports/phase3/pre_monsoon/stage3_v1/evaluation/report.md
reports/phase3/pre_monsoon/stage3_v1/evaluation_manifest.json
reports/phase3/pre_monsoon/stage3_v1/freeze/configuration.json
reports/phase3/pre_monsoon/stage3_v1/freeze/feature_definitions.json
reports/phase3/pre_monsoon/stage3_v1/freeze/frozen.json
reports/phase3/pre_monsoon/stage3_v1/freeze/protocol.md
reports/phase3/pre_monsoon/stage3_v1/freeze/seal.json
reports/phase3/pre_monsoon/stage3_v1/freeze/stage2_configuration.json
reports/phase3/pre_monsoon/stage3_v1/presentation_manifest.json
reports/phase3/pre_monsoon/stage3_v1/scientific_report.md
reports/phase3/pre_monsoon/stage3_v1/verification.json
```

### Figures (27)

```text
reports/handoff/remediation_v1/plot/occurrence_uncertainty.png
results/figures/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/controlled_exaggeration_p30_s42.png
results/figures/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p100_s42.png
results/figures/phase2/pre_monsoon/stage2_v1/annual_occurrence.png
results/figures/phase2/pre_monsoon/stage2_v1/cluster_ch_db.png
results/figures/phase2/pre_monsoon/stage2_v1/cluster_elbow.png
results/figures/phase2/pre_monsoon/stage2_v1/cluster_silhouettes.png
results/figures/phase2/pre_monsoon/stage2_v1/diurnal_occurrence.png
results/figures/phase2/pre_monsoon/stage2_v1/pca_coefficients.png
results/figures/phase2/pre_monsoon/stage2_v1/pca_correlation_loadings.png
results/figures/phase2/pre_monsoon/stage2_v1/pca_labeled.png
results/figures/phase2/pre_monsoon/stage2_v1/pca_reconstruction.png
results/figures/phase2/pre_monsoon/stage2_v1/pca_scree.png
results/figures/phase2/pre_monsoon/stage2_v1/physical_profile_cldarea_total_1h.png
results/figures/phase2/pre_monsoon/stage2_v1/physical_profile_cldpress_top_total_1h.png
results/figures/phase2/pre_monsoon/stage2_v1/physical_profile_cldtau_total_1h.png
results/figures/phase2/pre_monsoon/stage2_v1/spatial_occurrence.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_baseline_p100_s42.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_baseline_p10_s42.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_baseline_p30_s42.png
results/figures/phase3/pre_monsoon/stage3_v1/annual_occurrence.png
results/figures/phase3/pre_monsoon/stage3_v1/diurnal_occurrence.png
results/figures/phase3/pre_monsoon/stage3_v1/fixed_pca_projection.png
results/figures/phase3/pre_monsoon/stage3_v1/holdout_metrics.png
results/figures/phase3/pre_monsoon/stage3_v1/physical_profile_medians.png
results/figures/phase3/pre_monsoon/stage3_v1/spatial_occurrence_and_change.png
results/figures/phase3/pre_monsoon/stage3_v1_presentation/occurrence_uncertainty.png
```

### Lightweight CSV outputs (62)

```text
reports/phase2/pre_monsoon/stage1_v1/feature_decisions.csv
reports/phase2/pre_monsoon/stage1_v1/feature_missingness.csv
reports/phase2/pre_monsoon/stage1_v1/phase_iwp_audit.csv
reports/phase2/pre_monsoon/stage1_v1/retention_spatial.csv
reports/phase2/pre_monsoon/stage1_v1/retention_strata.csv
reports/phase2/pre_monsoon/stage1_v1/year_split_counts.csv
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/controlled_exaggeration_p30_s42.csv
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p100_s42.csv
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/seed_stability.csv
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/tsne_metrics.csv
reports/phase2/pre_monsoon/stage2_v1/annual_occurrence.csv
reports/phase2/pre_monsoon/stage2_v1/area_weighted_occurrence.csv
reports/phase2/pre_monsoon/stage2_v1/cautious_interpretations.csv
reports/phase2/pre_monsoon/stage2_v1/cluster_selection.csv
reports/phase2/pre_monsoon/stage2_v1/daily_occurrence.csv
reports/phase2/pre_monsoon/stage2_v1/diurnal_occurrence.csv
reports/phase2/pre_monsoon/stage2_v1/initialization_stability.csv
reports/phase2/pre_monsoon/stage2_v1/kmeans_fits.csv
reports/phase2/pre_monsoon/stage2_v1/kmeans_metrics.csv
reports/phase2/pre_monsoon/stage2_v1/metric_sample_ids.csv
reports/phase2/pre_monsoon/stage2_v1/pca_clustering_sensitivity.csv
reports/phase2/pre_monsoon/stage2_v1/pca_loadings.csv
reports/phase2/pre_monsoon/stage2_v1/pca_reconstruction.csv
reports/phase2/pre_monsoon/stage2_v1/pca_variance.csv
reports/phase2/pre_monsoon/stage2_v1/per_cluster_silhouettes.csv
reports/phase2/pre_monsoon/stage2_v1/persistence.csv
reports/phase2/pre_monsoon/stage2_v1/physical_profiles.csv
reports/phase2/pre_monsoon/stage2_v1/preprocessing_statistics.csv
reports/phase2/pre_monsoon/stage2_v1/sampling_stability.csv
reports/phase2/pre_monsoon/stage2_v1/spatial_occurrence.csv
reports/phase2/pre_monsoon/stage2_v1/transitions.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_baseline_p100_s42.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_metrics.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_sample_ids.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_seed_stability.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/annual_occurrence.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/area_weighted_occurrence.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/bootstrap_daily_sufficient_statistics_2019.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/bootstrap_daily_sufficient_statistics_2020.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/bootstrap_daily_sufficient_statistics_2021.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/bootstrap_intervals.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/daily_occurrence.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/distance_diagnostics.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/diurnal_occurrence.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/feature_drift.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/fixed_pc_drift.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/metrics.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/per_cluster_silhouettes.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/persistence.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/physical_ordering.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/physical_profiles.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/reconstruction.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/retention.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/spatial_occurrence.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/temporal_stability_summary.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/transitions.csv
reports/phase3/pre_monsoon/stage3_v1/freeze/cluster_selection.csv
reports/phase3/pre_monsoon/stage3_v1/freeze/initialization_stability.csv
reports/phase3/pre_monsoon/stage3_v1/freeze/pca_loadings.csv
reports/phase3/pre_monsoon/stage3_v1/freeze/pca_reconstruction.csv
reports/phase3/pre_monsoon/stage3_v1/freeze/pca_variance.csv
reports/phase3/pre_monsoon/stage3_v1/freeze/sampling_stability.csv
```

## Excluded currently untracked files (42)

These remain unchanged locally, including the process receipt with a local
absolute interpreter path and the legacy noisy PowerShell transcript.
Embedding/figure omissions are canonical-selection choices for repository
size, not deletion or suppression of experiment metrics; all experiment
metrics and historical provenance remain included.

```text
reports/data_quality/inspection_report_backup.txt
reports/handoff/remediation_v1/tests/process.json
reports/phase2/pre_monsoon/stage1_tests.txt
reports/phase2/pre_monsoon/stage1_v1/sample_manifest.csv
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p100_s101.csv
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p100_s73.csv
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p30_s101.csv
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p30_s42.csv
reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p30_s73.csv
reports/phase2/pre_monsoon/stage2_v1/sample_physical_values_and_labels.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_baseline_p100_s101.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_baseline_p100_s73.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_baseline_p10_s101.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_baseline_p10_s42.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_baseline_p10_s73.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_baseline_p30_s101.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_baseline_p30_s42.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_baseline_p30_s73.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_exaggeration_4_p30_s42.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_learning_rate_200_p30_s42.csv
reports/phase2/pre_monsoon/stage2_v1/tsne_random_init_p30_s42.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/profile_samples_and_membership.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/silhouette_observations.csv
reports/phase3/pre_monsoon/stage3_v1/evaluation/spatial_reference_changes.csv
reports/phase3/pre_monsoon/stage3_v1/freeze/training_reference.npz
results/figures/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p100_s101.png
results/figures/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p100_s73.png
results/figures/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p30_s101.png
results/figures/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p30_s42.png
results/figures/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/random_init_p30_s73.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_baseline_p100_s101.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_baseline_p100_s73.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_baseline_p10_s101.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_baseline_p10_s73.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_baseline_p30_s101.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_baseline_p30_s73.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_exaggeration_4_p30_s42.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_learning_rate_200_p30_s42.png
results/figures/phase2/pre_monsoon/stage2_v1/tsne_random_init_p30_s42.png
results/figures/phase3/pre_monsoon/stage3_v1/occurrence_uncertainty.png
src/03_extraction/create_seasonal_datasets_backup.py
src/09_visualization/pre_monsoon.py
```

## Ignored local files (65)

All remain outside the index. There are 48 NetCDF files (source/crop, prepared
and label datasets), 11 serialized model bundles, and six cache files. Do not
force-add them. training_reference.npz is not ignored by the historical
.gitignore, so it is excluded by the literal manifest above. The historical
.gitignore is itself byte-hashed and is deliberately unchanged.

```text
data/interim/ceres_extracted/pre_monsoon/CERES_2010_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2011_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2012_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2013_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2014_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2015_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2016_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2017_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2018_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2019_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2020_pre_monsoon.nc
data/interim/ceres_extracted/pre_monsoon/CERES_2021_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2010_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2011_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2012_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2013_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2014_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2015_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2016_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2017_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2018_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2019_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2020_pre_monsoon.nc
data/interim/ceres_seasonal/pre_monsoon/CERES_2021_pre_monsoon.nc
data/processed/handoff/matplotlib_cache/fontlist-v3.11.0.json
data/processed/model_ready/phase2/matplotlib_cache/fontlist-v3.11.0.json
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2010_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2011_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2012_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2013_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2014_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2015_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2016_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2017_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2018_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2019_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2020_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2021_pre_monsoon_prepared.nc
data/processed/model_ready/phase2/pre_monsoon/stage2_v1/CERES_2010_pre_monsoon_labels.nc
data/processed/model_ready/phase2/pre_monsoon/stage2_v1/CERES_2011_pre_monsoon_labels.nc
data/processed/model_ready/phase2/pre_monsoon/stage2_v1/CERES_2012_pre_monsoon_labels.nc
data/processed/model_ready/phase2/pre_monsoon/stage2_v1/CERES_2013_pre_monsoon_labels.nc
data/processed/model_ready/phase2/pre_monsoon/stage2_v1/CERES_2014_pre_monsoon_labels.nc
data/processed/model_ready/phase2/pre_monsoon/stage2_v1/CERES_2015_pre_monsoon_labels.nc
data/processed/model_ready/phase2/pre_monsoon/stage2_v1/CERES_2016_pre_monsoon_labels.nc
data/processed/model_ready/phase2/pre_monsoon/stage2_v1/CERES_2017_pre_monsoon_labels.nc
data/processed/model_ready/phase2/pre_monsoon/stage2_v1/CERES_2018_pre_monsoon_labels.nc
data/processed/model_ready/phase3/matplotlib_cache/fontlist-v3.11.0.json
data/processed/model_ready/phase3/pre_monsoon/stage3_v1/CERES_2019_pre_monsoon_labels.nc
data/processed/model_ready/phase3/pre_monsoon/stage3_v1/CERES_2020_pre_monsoon_labels.nc
data/processed/model_ready/phase3/pre_monsoon/stage3_v1/CERES_2021_pre_monsoon_labels.nc
results/models/phase2/pre_monsoon/stage2_v1/kmeans_k10.joblib
results/models/phase2/pre_monsoon/stage2_v1/kmeans_k2.joblib
results/models/phase2/pre_monsoon/stage2_v1/kmeans_k3.joblib
results/models/phase2/pre_monsoon/stage2_v1/kmeans_k4.joblib
results/models/phase2/pre_monsoon/stage2_v1/kmeans_k5.joblib
results/models/phase2/pre_monsoon/stage2_v1/kmeans_k6.joblib
results/models/phase2/pre_monsoon/stage2_v1/kmeans_k7.joblib
results/models/phase2/pre_monsoon/stage2_v1/kmeans_k8.joblib
results/models/phase2/pre_monsoon/stage2_v1/kmeans_k9.joblib
results/models/phase2/pre_monsoon/stage2_v1/preprocessing_pca.joblib
results/models/phase2/pre_monsoon/stage2_v1/selected_pre_monsoon_bundle.joblib
src/02_validation/__pycache__/pre_monsoon_final_integrity.cpython-313.pyc
src/03_extraction/__pycache__/create_seasonal_datasets.cpython-313.pyc
src/09_visualization/__pycache__/pre_monsoon.cpython-313.pyc
```

## Byte preservation and whitespace discrepancy

core.autocrlf is true in the original environment. The existing 54 tracked
Phase 1 text files are CRLF in the working tree and LF in Git. .gitattributes
makes their checkout convention explicit. New research files use -text so
the exact bytes in source/manifests/reports survive check-in/checkout. The
existing UTF-16 inspection report and PNGs remain non-normalized.
No git add --renormalize, blanket staging, scientific-file cleanup or manifest
regeneration is permitted. Before staging, filtered Git object hashes must
match raw bytes for every new submission file and match the original index
objects for every previously tracked file.

CRLF terminators are recognized by whitespace checks; other checks remain
enabled. Six immutable generated reports/logs contain existing table-padding
spaces or a terminal blank line. Preserve them and disclose cached-check
warnings rather than changing their hashed content:

```text
reports/handoff/remediation_v1/report/SCIENTIFIC_HANDOFF.md
reports/handoff/remediation_v1/tests/all_tests.txt
reports/phase2/pre_monsoon/stage1_v1/report.md
reports/phase2/pre_monsoon/stage2_review.md
reports/phase2/pre_monsoon/stage2_tests.txt
reports/phase3/pre_monsoon/stage3_all_tests.txt
```

## Approval boundary

Only this literal manifest may be staged. Staging is authorized conditionally
on the preflight checks; committing, pushing, merging and editing PR #1 remain
unauthorized. Prior Phase 1/Stage 2/Stage 3 files, hashes and results must stay
unchanged. Git HEAD references embedded in old manifests are historical
provenance, not claims about a future submission commit.
