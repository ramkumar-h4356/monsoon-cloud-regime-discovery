# Final handoff addendum (post-evaluation remediation)

This addendum qualifies the historical record without rewriting it. No model, feature definition, threshold, label, scientific endpoint or holdout result has been changed. No evaluation was rerun.

## Freeze scope and scientific limitations

The pre-access freeze applies to the evaluation/model-analysis code, approved fitting policy, parameters, seeds and input expectations. Presentation and completion-report helpers were produced after evaluation and have separate recorded hashes. The historical completion manifest's broad `code_frozen_before_holdout` flag must be read with this scope, not as a claim that every later post-processing script existed before access. The original flag/manifest is preserved.
Phase 1 explored 2010-2021, including holdout availability/correlations that informed feature selection. This was a reserved Phase 2 fitting/tuning holdout, not historically unseen confirmatory data. There is no independent meteorological-type validation. K-Means groups remain descriptive, overlapping cloud-property partitions; expected feature ordering is not independent validation. Temperature/height are related retrievals; no rain/convection or causal classes are established.

## Explicit development/holdout comparison

| period | n | observed_clusters | minimum_cluster_fraction | silhouette | calinski_harabasz | davies_bouldin | negative_silhouette_fraction | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2019 | 3000 | 2 | 0.461333 | 0.415992 | 2698.762455 | 0.961986 | 0.015333 | defined |
| 2020 | 3000 | 2 | 0.471333 | 0.415062 | 2674.318217 | 0.959498 | 0.015667 | defined |
| 2021 | 3000 | 2 | 0.472000 | 0.407771 | 2575.997577 | 0.976071 | 0.010667 | defined |
| pooled | 3000 | 2 | 0.488667 | 0.416583 | 2702.887303 | 0.953121 | 0.012667 | defined |

Pooled silhouette changed by -0.002288 (0.418872 -> 0.416583). Calinski-Harabasz changed by -36.205206 (2739.092510 -> 2702.887303), also less favorable. Davies-Bouldin changed by -0.000978, slightly more favorable. These are descriptive comparisons, not accuracy, equivalence or trend tests. Intervals concern within-window occurrence, not metric confidence intervals or interannual climate inference.

## Requirements supplied in the conversation

| Requirement | Status | Evidence/qualification |
| --- | --- | --- |
| PCA variance/loadings and selection | PASS | 57.208201/29.225728/13.566071%; three PCs retained. Actual dimension reduction was not achieved. |
| t-SNE parameter sensitivity/trustworthiness | PASS | 19 recorded experiments; deterministic PCA starts and genuine random-start follow-up distinguished. |
| k selection/three metrics/stability | PASS | k=2 selected from 2-10; median initialization ARI 0.998600, year-bootstrap ARI 0.993410; only five bootstrap fits. |
| Original-unit physical profiles/missingness | PASS | 13 properties; retrieval-valid denominators; no missing water path replaced by zero. |
| Temporal separation/final model | PASS | Fits 2010-2016, development 2017-2018, test 2019-2021; no final refit or tuning. |
| Historically untouched confirmatory test | LIMITED | Prior Phase 1 exposure cannot be undone. |
| Dependency/CLI handoff | REMEDIATED | New parameterized artifact-only CLI; complete installed-distribution version lock; see README.md. |
| Empty support | REMEDIATED PROSPECTIVELY | New robust_diagnostics_v2 API tested on synthetic periods; frozen legacy evaluator is intentionally not patched or rerun. |
| Report consistency/freeze scope | REMEDIATED BY ADDENDUM | CH decrease and post-evaluation helper provenance are explicit here. |
| Independent meteorological-type validation | NOT ESTABLISHED | Not claimed; requires independent evidence. |
No separate external supervisor rubric was available; this maps the PCA, t-SNE, clustering, reproducibility and reporting requirements actually supplied in the conversation.

## Safe use and remaining scope

Use the new handoff CLI for verification, reporting, plots and environment checks. It reads existing artifacts only; it does not load models or NetCDF arrays. Run/output IDs are independent and every output directory is exclusive. Never invoke old evaluation commands to reproduce this addendum. The v2 diagnostic API supports all-clear, all-unavailable, empty and one-eligible-row periods without fabricating statistics; positive-support parity is tested. It is a prospective computation layer, not a replacement claim for the sealed historical run. Integrating it into a new full scientific evaluation requires its own version/protocol and approval; do not reuse revealed holdout outcomes for model selection. No new fitting or holdout selection is part of this remediation.
The lock captures Windows CPython 3.13.7 including transitive installed distributions; it does not provide wheel hashes, an offline wheelhouse, or cross-platform bitwise guarantees. Scientific models/data remain outside ordinary Git tracking and must accompany an approved handoff archive. No Git commit, push or merge is authorized or performed.

Historical verification: 277 unique files checked; model SHA256 `4c26f58fcc842aa4c7da5d6547225a1d9ae25171f29f083014c31e4849233569`. Historical artifacts remain unchanged.
Current remediation test receipt: 43 tests passed in 225.630s; log SHA256 `24205e4bd537f1e4711d7c50c3480bfbfd179a9992a142683d2fcff53c5eb8ea`.

## Historical scientific report (verbatim)

# Reserved 2019-2021 pre-monsoon temporal evaluation

The frozen Stage 2 training-only model was used unchanged. No refit, hyperparameter selection, threshold recalibration, holdout t-SNE or performance-driven model choice occurred. Features: cloud area /100, log1p optical depth, top pressure (hPa); full three-PC unwhitened basis and k=2.
Fit years: [2010, 2011, 2012, 2013, 2014, 2015, 2016]; development: [2017, 2018]; holdout: [2019, 2020, 2021].
Immutable model SHA256: 4c26f58fcc842aa4c7da5d6547225a1d9ae25171f29f083014c31e4849233569.
Training-only nearest-centroid distance thresholds: {'q95': 2.197320940160277, 'q99': 3.0581464365961812}.

## Prespecified metrics

```text
period    n  observed_clusters  minimum_cluster_fraction  silhouette  calinski_harabasz  davies_bouldin  negative_silhouette_fraction  status
  2019 3000                  2                  0.461333    0.415992        2698.762455        0.961986                      0.015333 defined
  2020 3000                  2                  0.471333    0.415062        2674.318217        0.959498                      0.015667 defined
  2021 3000                  2                  0.472000    0.407771        2575.997577        0.976071                      0.010667 defined
pooled 3000                  2                  0.488667    0.416583        2702.887303        0.953121                      0.012667 defined
```

Selected development reference: silhouette 0.418872, CH 2739.09, DB 0.954099 (n=3000). Yearly and balanced pooled holdout samples target n=3000. CH depends on n/geometry; comparisons are descriptive.

## Negative and inconclusive findings

- Pooled holdout silhouette (0.416583) is lower than selected development (0.418872); no adaptation was performed.

Even favorable transfer cannot establish bimodality, natural cloud types, external geographical validity, causation, convection or precipitation classes. Internal indices favor specific distance geometry. Temperature/height diagnostics are related retrievals, not independent ground truth.

## Coverage and distance diagnostics

```text
 year  total  eligible  clear  invalid_or_missing_area  incomplete_cloudy  profile_sample  metric_sample  pooled_sample  sample_budget_met
 2019 691200    685116   6084                        0                  0           10000           3000           1000               True
 2020 691200    687277   3923                        0                  0           10000           3000           1000               True
 2021 691200    688577   2623                        0                  0           10000           3000           1000               True
```

```text
 period threshold  threshold_value  eligible  exceedance_fraction  mean_squared_distance  median_distance  p95_distance  p99_distance
   2019       q95         2.197321    685116             0.039529               1.656153         1.113997      2.102397      2.955035
   2019       q99         3.058146    685116             0.008454               1.656153         1.113997      2.102397      2.955035
   2020       q95         2.197321    687277             0.041490               1.620083         1.085741      2.104318      3.009437
   2020       q99         3.058146    687277             0.009337               1.620083         1.085741      2.104318      3.009437
   2021       q95         2.197321    688577             0.038411               1.618097         1.093996      2.070414      2.977904
   2021       q99         3.058146    688577             0.008841               1.618097         1.093996      2.070414      2.977904
```

Distance exceedance is relative to frozen training quantiles, not a calibrated probability of model failure. Full-population distortion is mean squared distance to unchanged centroids. Feature drift uses fixed profile samples and training-SD-standardized Wasserstein distance. Fixed-PC variances are reported without refitting. Three-PC reconstruction is algebraically near zero and is not evidence of generalization.

## Original-unit profiles and interpretation

```text
period  cluster              variable         units  total  valid     median        p10        p90
  2019        0      cldarea_total_1h       percent   5424   5424  17.202179   1.156069  56.324425
  2019        0       cldtau_total_1h dimensionless   5424   5424   1.219203   0.299492   3.599084
  2019        0 cldpress_top_total_1h           hPa   5424   5424 703.782104 423.280701 909.024292
  2019        1      cldarea_total_1h       percent   4576   4576  96.124039  64.527573 100.000000
  2019        1       cldtau_total_1h dimensionless   4576   4576   2.711817   0.574439  12.399920
  2019        1 cldpress_top_total_1h           hPa   4576   4576 341.157990 187.115601 559.530640
  2020        0      cldarea_total_1h       percent   4739   4739  16.901409   1.315789  51.572586
  2020        0       cldtau_total_1h dimensionless   4739   4739   1.216939   0.297190   3.769128
  2020        0 cldpress_top_total_1h           hPa   4739   4739 677.468445 390.288940 901.419617
  2020        1      cldarea_total_1h       percent   5261   5261  96.078308  64.163834 100.000000
  2020        1       cldtau_total_1h dimensionless   5261   5261   2.853653   0.607486  12.447065
  2020        1 cldpress_top_total_1h           hPa   5261   5261 314.457825 186.017426 519.555908
  2021        0      cldarea_total_1h       percent   4667   4667  19.549896   1.830884  54.941177
  2021        0       cldtau_total_1h dimensionless   4667   4667   1.160189   0.276891   3.601808
  2021        0 cldpress_top_total_1h           hPa   4667   4667 665.204590 391.006714 890.184753
  2021        1      cldarea_total_1h       percent   5333   5333  96.067413  65.337532 100.000000
  2021        1       cldtau_total_1h dimensionless   5333   5333   2.544453   0.545118  11.857937
  2021        1 cldpress_top_total_1h           hPa   5333   5333 326.153015 188.538162 551.391907
pooled        0      cldarea_total_1h       percent  14830  14830  17.840376   1.379310  54.473110
pooled        0       cldtau_total_1h dimensionless  14830  14830   1.202219   0.288531   3.645358
pooled        0 cldpress_top_total_1h           hPa  14830  14830 683.432129 403.772583 902.042969
pooled        1      cldarea_total_1h       percent  15170  15170  96.078568  64.619148 100.000000
pooled        1       cldtau_total_1h dimensionless  15170  15170   2.698404   0.576952  12.249359
pooled        1 cldpress_top_total_1h           hPa  15170  15170 326.514740 187.139618 542.841125
```

All frozen median-ordering checks supported: True. Cluster IDs were not changed. All 13 original-unit properties, means/quantiles and retrieval-valid denominators are in physical_profiles.csv. Water paths condition on available retrievals; missing is not zero. Profiles use uniformly sampled eligible cloudy rows, not full-population quantiles. Pressure is not height above local terrain; the two partitions remain broad overlapping mixtures.

## Temporal/spatial stability and uncertainty

```text
 year   split  cluster  count  eligible  total  cloudy_fraction  all_cell_fraction  clear  unavailable
 2019 holdout        0 372395    685116 691200         0.543550           0.538766   6084            0
 2019 holdout        1 312721    685116 691200         0.456450           0.452432   6084            0
 2020 holdout        0 328436    687277 691200         0.477880           0.475168   3923            0
 2020 holdout        1 358841    687277 691200         0.522120           0.519157   3923            0
 2021 holdout        0 322195    688577 691200         0.467914           0.466139   2623            0
 2021 holdout        1 366382    688577 691200         0.532086           0.530067   2623            0
```

```text
 year         endpoint  block_days  primary  estimate    lower    upper  replicates  valid_replicates                                interpretation
 2019 cloudy_cluster_0           3     True  0.543550 0.490525 0.595373        1000              1000 conditional within-window percentile interval
 2019 cloudy_cluster_1           3     True  0.456450 0.404627 0.509475        1000              1000 conditional within-window percentile interval
 2020 cloudy_cluster_0           3     True  0.477880 0.447332 0.504857        1000              1000 conditional within-window percentile interval
 2020 cloudy_cluster_1           3     True  0.522120 0.495143 0.552668        1000              1000 conditional within-window percentile interval
 2021 cloudy_cluster_0           3     True  0.467914 0.429556 0.527176        1000              1000 conditional within-window percentile interval
 2021 cloudy_cluster_1           3     True  0.532086 0.472824 0.570444        1000              1000 conditional within-window percentile interval
```

Annual range is the primary evidence across the three reserved years. Intervals use 1000 joint-spatial moving-day-block replicates with primary length 3 days; 1/5-day sensitivity results are also saved. Labels and model parameters remain fixed during bootstrap. These are within-window intervals, not interannual climate CIs. No independent-row inference is used. UTC diurnal cycles are not local solar time. Transitions/persistence do not bridge clear/unknown states or annual gaps; censored runs are counted. Maps and cosine-latitude weighted annual frequencies describe this domain only.

## Limitations and provenance

Phase 1 examined 2010-2021, including feature availability/correlations. This is a reserved Phase 2 temporal test, not historically unseen confirmatory data. There are only three holdout years, sampled profile quantiles, selective retrieval availability and residual space/time dependence. Equal-year sample weighting differs slightly from all-grid-cell-hour occurrence weighting. The window is April 15-May 14, not the full calendar pre-monsoon season. Strong model-selection stability in Stage 2 is conditional on the feature representation and does not prove natural regimes.
The freeze directory contains feature definitions, protocol, exact numeric training thresholds, selection evidence, model/code/protected-file hashes, package versions and seeds. Separate profile/year-metric/pooled sample memberships are saved. New annual labels, figures and CSVs live only in Phase 3 paths. evaluation_manifest.json inventories all result hashes; the standalone verifier and test logs provide integrity evidence. No Git commit/push/merge is performed. Any adaptation after these results is a new exploratory phase requiring separate validation.

## Completed validation and execution record

All 25 available tests passed in 223.843 seconds. Tests use synthetic data for fitting and gate checks; the real Stage 3 evaluation never fits a model.
Independent verification checked 36 result hashes, all 30,000 profile-sample predictions, reproducible nested sample IDs, training-only distance thresholds, and 3 reopened label files covering 2,073,600 original grid-cell hours. All 198 protected prior artifacts/code/configuration files and the final model are unchanged. All six holdout raw/prepared source hashes still match Stage 1 expectations.
Pre-access freeze timestamp: 2026-11-16T13:14:38.360780+00:00; authorized access receipt: 2026-11-16T13:15:35.642362+00:00. The immutable freeze and its seal existed before the first real holdout open.
The original evaluation figures/results are retained. A presentation-only uncertainty figure uses matched categorical colors and integer year ticks; presentation_manifest.json hashes its unchanged input CSV, plotting script and output image. No statistic, endpoint or model setting changed.

Execution commands from the repository root:

```powershell
& '..\.venv\Scripts\python.exe' -B src/08_evaluation/run_pre_monsoon_stage3.py freeze --run-id stage3_v1
& '..\.venv\Scripts\python.exe' -B src/08_evaluation/run_pre_monsoon_stage3.py evaluate --run-id stage3_v1
& '..\.venv\Scripts\python.exe' -B -m unittest discover -s tests -v
& '..\.venv\Scripts\python.exe' -B src/08_evaluation/verify_pre_monsoon_stage3.py --run-id stage3_v1
& '..\.venv\Scripts\python.exe' -B src/09_visualization/plot_pre_monsoon_stage3_summary.py
& '..\.venv\Scripts\python.exe' -B src/08_evaluation/build_pre_monsoon_stage3_completion.py
```

The test process stdout/stderr was saved to reports/phase3/pre_monsoon/stage3_all_tests.txt. Existing run/output paths are refused. Reproduction requires fresh output paths, equivalent source data and the pinned Stage 2 environment. No dependency upgrade was needed for Stage 3.

New source files: config/pre_monsoon_stage3.json; docs/methodology/pre_monsoon_stage3_protocol.md; src/08_evaluation/{pre_monsoon_stage3_tools,run_pre_monsoon_stage3,verify_pre_monsoon_stage3,build_pre_monsoon_stage3_completion}.py; src/09_visualization/plot_pre_monsoon_stage3_summary.py; tests/test_stage3.py. All evaluation/code/configuration changes are new files. No existing tracked file, Phase 1/Stage 2 artifact or Git history was modified; no commit/push/merge.

Artifacts: freeze/ contains the immutable pre-access configuration, feature definitions, selection evidence and training reference; evaluation/ contains CSVs and the original scientific report; verification.json and evaluation_manifest.json contain validation/provenance. Figures are in results/figures/phase3/pre_monsoon/stage3_v1 and stage3_v1_presentation; annual labels are in data/processed/model_ready/phase3/pre_monsoon/stage3_v1.

