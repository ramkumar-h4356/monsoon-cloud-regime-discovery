# Consolidated pre-monsoon Stage 2 review

Stage 2 is complete. Stage 3 has not started. No real holdout source/prepared NetCDF was opened, no holdout diagnostic/evaluation was performed, and no Git commit/push/merge was made.

## Verification and tests

Stage 1 feature/missingness definitions, non-holdout output hashes, split membership and sample IDs were checked before fitting. The original three features and complete valid cloudy eligibility remain unchanged.
Tests: 17 main-suite tests plus 2 supplementary tests passed (19 total, across separate runs). Synthetic tests cover temporal isolation, imputation/scaling statistics, PCA reconstruction, label permutations, degenerate metrics, whole-year bootstrap, missingness denominators, temporal run boundaries, saved-model round trips, corrupt inputs, overwrite refusal, and execution without any holdout files.
Artifact verification checked 84 main outputs, 31 recorded source/config hashes and 18 permitted input files. Reloaded preprocessing medians/means match the 70,000 training rows; scaler and PCA fitted-sample counts are exactly 70,000. All 90,000 saved sample predictions match the reloaded model and saved label files.
Full-population diagnostics cover 6,220,800 grid-cell hours, including 6,191,146 eligible cloudy observations, in nine coordinate-preserving annual label files (2010–2018). Phase 1 and Stage 1 hashes are preserved.

## Selected scientific configuration

Fit years: 2010–2016; development: 2017–2018. Training sample 70,000; development sample 20,000. No development-inclusive refit. Median imputation is inert for the complete-case population. IWP/LWP remain excluded from fitting and are never zero-filled.
PCA variance: 57.208%, 29.226%, 13.566%; two PCs retain only 86.434%. Three components are retained by the >=95% variance and <=0.25 maximum development feature-RMSE rules. This is a rotation, not a successful dimensionality reduction. With all three unwhitened PCs, Euclidean distances and the original standardized-space metrics are equivalent by construction, not independent validation.
Selected k=2 from 2–10. Development silhouette=0.4189, CH=2739.09, DB=0.9541; negative-silhouette fraction=1.300%. Median initialization ARI=0.9986; whole-year-bootstrap ARI=0.9934. k=2 has the strongest development silhouette/CH/DB among the tested candidates. Single-start initialization stability is weak for several higher k values; all candidate tables remain available.

## t-SNE follow-up and limitations

The main grid has 12 experiments; seven additional checks examine random starts at perplexities 30/100 and isolate early exaggeration. The displayed baseline perplexity is 100, selected by mean original-space trustworthiness across seeds and neighborhoods (0.9927). Trustworthiness uses the same 1,000-point subset of the fixed 3,000-point visualization sample; it measures local fidelity, not regime validity.
PCA-initialized baseline runs were identical across seeds, with neighborhood overlap 1.0. This is deterministic repeatability, not evidence of robustness to random starts. Random-start results follow:

```text
                 min    median       max
perplexity                              
30          0.770800  0.775733  0.939667
100         0.942933  0.943200  0.989933
```

The table gives pairwise 15-neighbor-overlap min/median/max on the fixed evaluation subset.

```text
                 min      mean       max
perplexity                              
30          0.991511  0.992193  0.992908
100         0.992451  0.992560  0.992702
```

The table gives min/mean/max original-space trustworthiness across random seeds, each averaged over neighborhoods 5/15/30. Distinct layouts can preserve local neighbors; global island distances/areas remain uninterpretable.
The original auto-rate exaggeration-4 experiment used learning rate 187.5, versus 62.5 at exaggeration 12; it therefore changed both effective settings. The added controlled exaggeration-4 run holds learning rate 62.5 fixed (KL=0.8624; baseline same-perplexity KL=0.8715). KL is compared here only at identical perplexity/sample; it is not a universal cross-perplexity ranking. All runs use a finite 1,500-iteration budget; global optimality or convergence beyond this budget is not established. These checks do not change the chosen PCA dimension or K-Means count.

## Physical interpretation

```text
      split  cluster              variable         units     median        p10        p90
development        0      cldarea_total_1h       percent  16.875000   1.123595  55.968689
development        0       cldtau_total_1h dimensionless   1.150926   0.277419   3.603850
development        0 cldpress_top_total_1h           hPa 707.873840 420.727966 911.635498
development        1      cldarea_total_1h       percent  95.869751  64.856422 100.000000
development        1       cldtau_total_1h dimensionless   2.656630   0.525309  11.561245
development        1 cldpress_top_total_1h           hPa 336.052734 194.964554 554.606567
      train        0      cldarea_total_1h       percent  21.291475   2.104486  58.621746
      train        0       cldtau_total_1h dimensionless   0.806352   0.170163   3.008969
      train        0 cldpress_top_total_1h           hPa 660.194336 305.497040 892.598572
      train        1      cldarea_total_1h       percent  94.436737  63.953503 100.000000
      train        1       cldtau_total_1h dimensionless   2.450413   0.503359  10.090227
      train        1 cldpress_top_total_1h           hPa 333.587524 189.136047 529.525330
```

The two broad partitions separate sparse cloud cover with generally higher cloud-top pressure from extensive cover with lower pressure and larger optical depth. Pressure and optical-depth distributions overlap substantially. The first group's median pressure changes from about 660 hPa in training to 708 hPa in development, crossing a conventional descriptive pressure bin; names must not be treated as fixed meteorological types. Pressure is not height above local terrain. Neither group establishes convection, precipitation, cloud-object morphology or causation.
Profiles are sample quantiles in original units, separately by split; water-path profiles condition on available retrievals and retain missing denominators. Full occurrence maps/tables are descriptive, not tests of transfer to unseen geography. UTC diurnal cycles are not local solar time. Clear/unknown states break persistence runs; no transition bridges a year or seasonal gap. Five bootstrap replicates and seven fitting years do not provide formal confidence intervals. The analyzed pre-monsoon window is April 15–May 14, not the entire pre-monsoon calendar season.

## Reproduction and artifacts

```powershell
& '..\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p 'test_stage[12].py' -v 2>&1 | Set-Content -Encoding utf8 reports/phase2/pre_monsoon/stage2_tests.txt
& '..\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p 'test_stage2_tsne_sensitivity.py' -v 2>&1 | Set-Content -Encoding utf8 reports/phase2/pre_monsoon/stage2_tsne_sensitivity_tests.txt
& '..\.venv\Scripts\python.exe' -B src/07_clustering/run_pre_monsoon_stage2.py --run-id stage2_v1
& '..\.venv\Scripts\python.exe' -B src/08_evaluation/verify_pre_monsoon_stage2.py --run-id stage2_v1
& '..\.venv\Scripts\python.exe' -B src/09_visualization/pre_monsoon_stage2_tsne_sensitivity.py --run-id stage2_tsne_sensitivity_v1
& '..\.venv\Scripts\python.exe' -B src/08_evaluation/build_pre_monsoon_stage2_review.py
```

Commands above describe a fresh checkout/data reconstruction. Existing run IDs are intentionally refused. The actual test logs are stage2_tests.txt (17) and stage2_tsne_sensitivity_tests.txt (2). requirements-stage2.txt pins the installed packages; configs, scripts and manifests preserve all settings/seeds. Model artifacts remain season-specific; the shared feature contract is unchanged.

Main methodology/results: [stage2_v1/report.md](stage2_v1/report.md). Baseline tables/metrics are in stage2_v1; random-start/controlled-parameter results in stage2_tsne_sensitivity_v1. Figures and models are under results/{figures,models}/phase2/pre_monsoon; annual labels are under data/processed/model_ready/phase2/pre_monsoon/stage2_v1.

## Approval boundary

Stop here. Before Stage 3, review/freeze the features, k=2 descriptive resolution, PCA retention, diagnostic scope and interpretation. Obtain explicit approval for a final fit policy and temporal holdout evaluation. Phase 1 already inspected 2019–2021, so that holdout is not historically unseen. No Git commit, push, merge, final refit or holdout evaluation is authorized by this report.
