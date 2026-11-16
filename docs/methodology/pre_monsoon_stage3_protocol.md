# Frozen Stage 3 protocol: reserved temporal evaluation

Approved policy: the existing pre-monsoon Stage 2 model fitted on the saved
2010-2016 sample is the final evaluation model. Do not refit on 2010-2018.
Development years 2017-2018 informed selection; holdout years are 2019-2021.
All observations represent April 15-May 14 hourly grid cells on the established
CERES domain, not an entire calendar pre-monsoon season or individual clouds.

## Mandatory gate before holdout access

The `freeze` command must verify Stage 2 selection evidence, review/test
receipts, model and recorded source/output hashes, unchanged feature contract,
and training-only model metadata/statistics. It may read training/development
artifacts and saved protocol tables, but may not hash or open holdout NetCDFs.
It saves copies of feature definitions and configuration; an explicit final
fitting policy; PCA dimension 3, k=2 and their selection evidence; model,
source/config/test/protocol hashes; source-file expectations from Stage 1;
seeds; package versions; a training reference; and numeric novelty thresholds.
Only after a complete, hashed freeze receipt exists may `evaluate` access
holdout arrays. Modified code/model/config/protected artifacts invalidate that
receipt. The evaluator never calls fit, fit_transform or an estimator factory.

Features are total cloud area /100, log1p(total optical depth), and total
cloud-top pressure in hPa, followed by the existing median imputer,
StandardScaler, full three-PC unwhitened PCA, and k=2 K-Means. Complete valid
cloudy eligibility is unchanged. The imputer is inert for eligible rows; clear
sky and unavailable retrievals are separate labels (-1 and -2). IWP/LWP and
aggregate phase remain diagnostic and never enter the distance metric.

PCA retained all three dimensions because two explain 86.433929% (below 95%)
and give maximum development feature RMSE 0.438437 (above 0.25 training SD).
Thus PCA is a rotation, not dimensionality reduction. k=2 had development
silhouette 0.418872, CH 2739.09, DB 0.954099, median initialization ARI
0.998600 and year-bootstrap ARI 0.993410. The Stage 2 selection rule, all
candidates, loadings, profiles and instability of some larger k are preserved.
These results support a coarse partition, not validated meteorological types.

## Thresholds, samples, metrics and diagnostics

Compute nearest-centroid Euclidean distance q95/q99, using the linear quantile
method on the same saved 70,000 training observations, before holdout access.
The frozen thresholds are flags only, never rejection rules or fitted updates.
Average squared distance is reported separately as distortion.

For each holdout year, uniformly sample 10,000 eligible observations using
SeedSequence([42,3,year,0]); sample 3,000 from that sample using stream 1;
sample 1,000 from those 3,000 using stream 2 for a balanced pooled n=3,000.
All sampling is without replacement and independent of labels, scores or
physical profile values beyond the fixed eligibility mask. Save original
observation IDs and flat indices. If support is inadequate, retain available
rows and explicitly flag the shortfall; never change sampling based on scores.

Report yearly and pooled silhouette, CH and DB in the training-standardized
original-feature geometry, plus per-cluster silhouette distributions and
negative fractions. Report undefined metrics if fewer than two predicted
clusters occur. Fixed n permits CH comparisons; yearly support limits and
sample weighting differences remain explicit. CH/DB's empirical group means
are descriptive diagnostic calculations, not refitted prediction centroids.

Assign every eligible holdout observation using the frozen model. Save full
coordinate-preserving annual labels, annual/daily/UTC-diurnal/spatial occurrence
with cloudy and all-cell denominators, cosine-latitude weighted annual
frequencies, consecutive-hour transitions and run-length summaries. Clear and
unavailable observations break runs; annual/seasonal gaps are never bridged;
boundary-censored runs remain counted explicitly.

On the fixed 10,000-per-year samples, report original-unit means, medians,
p10/p90 and valid/missing counts for all 13 Stage 2 profile properties, yearly
and pooled. Water-path summaries condition on valid retrievals; no missing
water path becomes zero. Compare the frozen expected ordering each year:
cluster 1 greater cloud area and optical depth, and lower cloud-top pressure.
Reversals are transfer failures, not reasons to relabel clusters.

Report feature means/quantiles, train-SD-standardized Wasserstein shifts and
fixed-PC score shifts/variances relative to the saved training reference;
distance quantiles, distortion and novelty-threshold exceedance use all eligible
observations. Full three-PC reconstruction error is algebraically near zero
and is not evidence of generalization. Use frozen PCA projections for figures;
do not fit a holdout t-SNE embedding or compare alternative k/PC counts.

Compare holdout maps to saved training and development occurrence maps.
No new geographically selected subgroups or weather-type names are chosen
from holdout results. Pressure is not height above local terrain; UTC is not
local solar time; neither cloud partition implies rain or convection.

## Dependence, uncertainty and negative findings

Primary temporal evidence is the three separate annual results and their
range. For occurrence and distance-exceedance fractions, use 1,000 joint-spatial
non-circular moving-day-block bootstrap replicates within each year. Primary
block length 3 days; frozen sensitivity lengths 1 and 5 days. Choose contiguous
blocks from starts 0..30-L, concatenate ceil(30/L) draws, then truncate to 30
days. All cells within a day move jointly. Use SeedSequence([42,3,year,3,L]).
Report percentile 2.5/97.5 intervals, not normal independent-row errors.
These are conditional within-window intervals, not interannual climate CIs;
three years and residual longer dependence limit inference. No parameter or
cluster refitting occurs in this bootstrap. Profile quantiles remain sampled;
no bootstrap confidence claim is made for cluster metrics or profile medians.

Report all metrics, physical-ordering reversals, under-1% cluster occupancy,
distance changes, undefined quantities and inconclusive findings. There is no
post-hoc quality cutoff or performance-based model choice. Stage 1 inspected
the holdout historically, so this is reserved temporal transfer evaluation,
not pristine confirmatory validation. Strong internal metrics/stability do
not establish natural cloud classes, bimodality, causation or external validity.

## Preservation and execution

New outputs live under `reports/phase3/pre_monsoon/<run_id>`,
`results/figures/phase3/pre_monsoon/<run_id>`, and
`data/processed/model_ready/phase3/pre_monsoon/<run_id>`.
Existing paths are refused. Phase 1/Stage 1/Stage 2 artifacts are hash-checked
before/after. Final tests and a standalone artifact checker reload and verify
predictions without changing model parameters. No Git commit/push/merge.

```powershell
& '..\.venv\Scripts\python.exe' -B src/08_evaluation/run_pre_monsoon_stage3.py freeze --run-id stage3_v1
& '..\.venv\Scripts\python.exe' -B src/08_evaluation/run_pre_monsoon_stage3.py evaluate --run-id stage3_v1
& '..\.venv\Scripts\python.exe' -B -m unittest discover -s tests -v
& '..\.venv\Scripts\python.exe' -B src/08_evaluation/verify_pre_monsoon_stage3.py --run-id stage3_v1
```
