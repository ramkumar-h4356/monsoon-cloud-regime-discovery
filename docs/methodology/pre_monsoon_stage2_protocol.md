# Stage 2 protocol: development-only cloud-property partitions

This protocol and JSON configuration are written before the real-data run.
No Stage 2 function reads 2019-2021 source/prepared NetCDFs, generates holdout
diagnostics, or refits on development observations. Stage 1 artifacts are
immutable inputs. Existing Phase 1 code, CSVs and figures are preserved.

## Verification and population

Verify the Stage 1 manifest's protected-file hashes, contract hash, non-holdout
output hashes, ordered features and whole-year split/sample membership. Re-run
the existing tests (their holdout examples are synthetic only). Only years
explicitly listed as training (2010-2016) and development (2017-2018) may be
opened by the Stage 2 input functions. The sample contains 10,000 eligible
cloudy observations per year: 70,000 training and 20,000 development rows.
Sampling equally by year gives a slightly different weighting from the full
eligible population; full-population occurrence is reported separately.

Features remain cloud area / 100, log1p optical depth, and cloud-top pressure
in hPa, in the Stage 1 order. Clear and incomplete observations remain outside
the cloudy-regime model. Fit a median SimpleImputer on training rows only as a
persisted safety step; because eligible rows are complete it is inert, and it
does not admit additional observations. Do not impute IWP/LWP or use diagnostic
properties for clustering. Fit StandardScaler and unwhitened full-SVD PCA on
the same training sample only. Development receives transform/predict only.

## PCA criteria

Report every eigenvalue, individual/cumulative explained variance, coefficients
and empirical feature-PC correlations (different quantities). Plot scree,
cumulative variance and signed coefficient/correlation heatmaps. Compare
1/2/3 PCs using training and development standardized reconstruction RMSE,
including each feature. Choose the smallest dimension with >=95% training
variance AND maximum development feature RMSE <=0.25 training standard
deviations. Keeping all three is legitimate; do not force reduction. The full
3-PC representation is equivalent to the standardized original metric up to
an orthogonal rotation; no whitening is used. Report thresholds at 80/90/95%
and a selected-k clustering sensitivity across all PC dimensions.

## K-Means and stability

Evaluate k=2..10: a broad, manageable range for three complementary properties,
not a presupposed count of meteorological cloud types. Include k=1 inertia as
a reference. Fit on the 70,000 training sample with K-Means++, n_init=30,
max_iter=500, tol=1e-4, seed=42, one computational thread. Every candidate is
evaluated on fixed 3,000-row train/development subsets. Record inertia,
per-observation distortion, convergence, cluster occupancy, silhouette,
negative silhouette fraction, Calinski-Harabasz (CH) and Davies-Bouldin (DB).
Higher silhouette/CH and lower DB are favorable. Always report common
standardized-original-space scores as well as retained-PC-space scores;
never compare differing-dimension scores as though their geometry were equal.

Initialization stability: five independent seeds with a single initialization,
predicting a common development reference. Report all pairwise adjusted Rand
indices (ARI) and optimally matched mean/minimum cluster Jaccard scores.
The selected production candidate retains 30 restarts, not one.

Sampling stability: five whole-training-year bootstrap replicates, preserving
within-season spatial/temporal dependence in the sampled rows and retaining
year multiplicity. Refit the imputer/scaler/PCA and K-Means (10 starts) for each
replicate, using the same selected PC count. Compare labels on the common
development reference against the original training-only candidate. Report
ARI and matched Jaccard, chosen years, and physical centroid displacement.
This is a limited stability experiment, not an independent-observation CI.

Choose the smallest k within 0.02 of the best development silhouette in the
common standardized space, among solutions with >=1% minimum development
cluster occupancy and median initialization AND bootstrap ARI >=0.8. CH/DB,
elbow, per-cluster silhouettes, physical profiles and variability are reported
as corroborating/contradictory evidence, not hidden in an arbitrary weighted
score. If no candidate passes, report no selected k instead of weakening the
criteria. A selected k is an operational descriptive resolution, not proof of
discrete natural regimes. Physical plausibility must be reviewed before Stage 3.

## t-SNE

Use a fixed approximately year-balanced 3,000-row subset of the Stage 1
training/development sample. Fit t-SNE only on this permitted visualization
sample after training-fitted transformations. Use at least two PCs for t-SNE
even if a one-PC clustering representation passes the PCA rule; report this
distinction. Baseline perplexities 10/30/100 crossed with seeds 42/73/101,
PCA initialization, automatic learning rate, early exaggeration 12 and 1,500
iterations. Additional seed-42/perplexity-30 runs separately vary learning
rate (200), exaggeration (4), and random initialization.

On the same fixed 1,000-observation evaluation subset, measure trustworthiness
at neighborhoods 5/15/30 relative to both retained t-SNE-input PCs and scaled
original features. Report runtime, KL divergence, iterations, effective
learning rate and 15-neighbor overlap across seeds. KL is not comparable as a
universal quality objective across perplexities. Choose a display setting
using mean original-space trustworthiness across seeds/neighborhoods, retaining
all experiments. Plots label model cluster and year, with explicit exploratory
titles. Do not cluster the t-SNE coordinates or interpret island distance or
area as physical separation/prevalence. No holdout t-SNE transform is attempted.

## Profiles and population diagnostics

Compute original-unit means/medians/p10/p90 and valid/missing denominators on
the fixed 90,000-row sample, separately for training and development. Diagnostic
variables include unused total pressure/temperature/height/phase/water paths
and layer cloud areas. Water-path summaries condition on valid retrievals;
availability is reported so absence is never read as zero. Profile quantiles
are sampled, not full-population quantiles.

Apply the selected training-only model in batches to every eligible row in
2010-2018. Save coordinate-preserving labels (-1 clear, -2 unavailable), annual,
daily, UTC diurnal and spatial occurrence with cloudy and all-cell denominators.
Report consecutive-hour transitions and run lengths separately within each
year/grid cell; clear/unknown breaks runs and boundary-censored runs are counted.
No transition is constructed across seasonal/year gaps. UTC is not local
solar time; maps describe this domain, not spatial transfer. Grid-cell weighting
is primary; cosine-latitude-weighted annual frequencies are an additional
descriptive sensitivity. No causal or rainfall claim follows from these data.

## Reproducibility, boundaries and commands

All outputs go to new run IDs beneath Phase 2 report/figure/model/label paths.
Existing output directories are refused. Record source and output hashes,
config/code hashes, package versions, Git state, fixed sample identities,
seeds, fit years, sample counts, feature order, and selected configuration.
Use a serialized bundle carrying season/contract hash/fit years. Load only
trusted local joblib artifacts. Stage 1 contracts remain shared; fitted
objects remain pre-monsoon specific. No development-inclusive final refit is
performed; that and any holdout evaluation require Stage 3 approval.

```powershell
& '..\.venv\Scripts\python.exe' -B -m unittest discover -s tests -v
& '..\.venv\Scripts\python.exe' -B src/07_clustering/run_pre_monsoon_stage2.py --run-id stage2_v1
```

Reference APIs: [PCA](https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html),
[t-SNE](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.TSNE.html),
[trustworthiness](https://scikit-learn.org/stable/modules/generated/sklearn.manifold.trustworthiness.html),
[clustering metrics](https://scikit-learn.org/stable/modules/clustering.html).
Pin and inspect installed API signatures rather than relying on future defaults.
