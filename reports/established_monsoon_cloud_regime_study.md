# Established-Monsoon Cloud-Regime Discovery
## Integrated Scientific Report

- **Period:** 2010–2021
- **Seasonal window:** 15 July–13 August (30 days/year)
**Domain:** 6.5–37.5°N, 68.5–97.5°E; 32 × 30 grid (960 cells)

## Abstract

This study explores cloud-feature groupings during the established-monsoon season over India using CERES SYN1deg observations. The workflow includes complete-case feature preparation, PCA, t-SNE, K-means model selection and clustering, physical profiling, spatial/temporal prevalence, coverage sensitivity, and external rainfall association.

There were 345,600 raw observations and 290,355 complete cases for the selected 14-feature analysis. Four PCA components retain approximately 94% of variance in both representations. K=2 is a reasonable leading candidate, although internal metrics do not establish a uniquely optimal cluster count across all criteria.

The baseline K=2 solution separates lower-coverage/lower-optical-depth observations from higher-coverage/higher-optical-depth observations. Representation sensitivity and sampling variability mean that assignments are not invariant.

Rainfall matching covers 110,314 cloud observations (37.993%) and 357 of 960 cells (about 37.2%). Rainfall conclusions are therefore conditional on a spatially restricted matched subset. The findings are exploratory and observational; they do not establish causal mechanisms or prove that the clusters are distinct meteorological regimes.

## 1. Objective and scope

The objective is to identify and interpret recurring groupings in multivariate cloud properties during a consistently sampled established-monsoon window, and to examine their spatial, temporal and rainfall-associated behaviour.

The clusters are statistical partitions in the selected feature space. Rainfall is an external association/validation variable and is not included in clustering. Contextual climate indices are not used to make causal attribution.

## 2. Data and features

The study uses 12 years (2010–2021), 30 days per year (15 July–13 August), over a 32 × 30 grid.

The Group B feature set contains:

- `cldarea_total_1h`
- `cldhght_total_1h`
- `cldphase_total_1h`
- `cldpress_total_1h`
- `cldtemp_total_1h`
- `cldtau_total_1h`
- `iwp_total_1h`
- `cldarea_high_1h`
- `cldhght_high_1h`
- `cldphase_high_1h`
- `cldpress_high_1h`
- `cldtemp_high_1h`
- `cldtau_high_1h`
- `iwp_high_1h`

The log-sensitivity representation applies `log1p` to total/high `cldtau` and `iwp`.

From 345,600 raw observations, 290,355 complete cases were retained; 55,245 incomplete observations were excluded. No imputation was used.

## 3. Dimensionality reduction

### PCA

| Representation | 3 PCs | 4 PCs | 5 PCs |
|---|---:|---:|---:|
| Baseline cumulative variance | 87.06% | 93.99% | 96.39% |
| Log-sensitivity cumulative variance | 86.53% | 93.50% | 95.84% |

Four components retain approximately 94% of variance in both representations. PCA describes linear variance structure and does not establish physical regimes.

### t-SNE

The refined workflow used the first 10 PCA components and a deterministic 6,000-observation sample (500 per year; seed 42). Four embeddings were produced for baseline/log-sensitivity and P30/P50.

Runs reached iteration 2,999 of 3,000; convergence was not demonstrated. Trustworthiness was approximately 0.988–0.998, but this does not establish physical validity or preserve global distances.

Year distributions overlapped rather than forming year-exclusive visual clusters. Same-year nearest-neighbour fractions were approximately 10.8–11%, against a global null near 8.3%.

Constrained permutation results were approximately 10.82–10.96% observed versus 8.36–8.40% null (999 permutations). These diagnostics are exploratory and their constrained null preserves approximate strata, not all autocorrelation.

t-SNE is used for local-neighbourhood exploration only; embedding distances are not physical distances.

## 4. Clustering and physical profiles

### Model selection

K-means model selection examined K=2–10. K=2 had the highest silhouette and Calinski–Harabasz scores for both representations.

Baseline K=2 silhouette was 0.2783; log-sensitivity K=2 silhouette was 0.3194.

Davies–Bouldin did not select K=2 for both representations. K=2 is therefore a leading interpretable candidate, not a uniquely optimal solution.

### Baseline K=2 physical medians

| Feature | Cluster 0 | Cluster 1 |
|---|---:|---:|
| Total cloud area | 83.21% | 99.33% |
| Total cloud height | 8.35 | 10.93 |
| Total optical depth | 2.87 | 8.02 |
| Total ice water path | 51.73 | 175.72 |
| High-cloud area | 29.30% | 69.08% |
| High-cloud optical depth | 1.91 | 8.55 |

Cluster 0 has lower cloud coverage, optical depth and IWP; Cluster 1 has higher values.

Numeric labels are arbitrary. The log-sensitivity K=2 labels are reversed relative to baseline physical interpretation, so compare profiles, not raw label numbers.

### Sampling stability

A five-seed initialization check reported mean ARI 0.7606 (baseline K=2) and 0.7911 (log-sensitivity K=2). This is initialization stability, not sampling stability.

The corrected fixed-init sampling experiment used:
- 20,000-observation reference set
- 270,355-observation training pool
- Fractions 50%, 70%, 80%
- 10 repetitions per fraction
- 60 model fits

Mean pairwise ARI:

| Representation | 50% | 70% | 80% |
|---|---:|---:|---:|
| Baseline | 0.7566 | 0.5753 | 0.7766 |
| Log sensitivity | 0.8120 | 0.8404 | 0.8220 |

Log-sensitivity had higher mean agreement at all tested fractions. Baseline stability was lower at 70%, with some smaller-cluster proportions as low as 25.22%.

Pairwise ARIs share fitted models and are not independent. MiniBatchKMeans diagnostics showed 1–3 iterations despite `max_iter=200`; `max_no_improvement` early stopping may explain stopping before the maximum. These iteration counts alone do not prove failed convergence. No convergence-control rerun is claimed.

### Cross-representation agreement (M6.3)

M6.3 compared baseline and log-sensitivity assignments on 20,000 reference observations.

| Training fraction | Mean ARI | Mean AMI | Label-aligned agreement |
|---|---:|---:|---:|
| 50% | 0.61665 | 0.57064 | 88.67% |
| 70% | 0.63871 | 0.57868 | 89.76% |
| 80% | 0.44115 | 0.46146 | 82.30% |

Agreement is moderate and lower at 80%. Label-aligned agreement is not interchangeable with ARI/AMI. Similar cluster proportions do not imply identical assignments.

**Provenance:** M6.3's manifest names `results/tables/07_clustering/sampling_stability_controlled/m6_2_controlled_reference_predictions.csv` as input. It used the earlier controlled M6.2 experiment (model random state 20351116), not the later `sampling_stability_fixed_init` experiment (model random state 20761116). M6.3 is interpreted using its recorded input; it is not presented as a comparison based on the later fixed-init experiment.

## 5. Spatial and temporal analysis

Annual coverage matching retained:
- 816 cells at a 50% threshold
- 701 cells at a 70% threshold
- 591 cells at an 80% threshold

Corrected prevalence accounts for absent cluster counts as zero only among eligible cells with observations. Eligibility filtering is necessary to avoid treating unobserved cells as observed zeros.

Temporal/spatial prevalence, period comparisons, availability robustness and change-point analyses provide descriptive context. They do not remove all retrieval or sampling bias. Change-point candidates are statistical descriptions, not causal evidence of climate transitions.

## 6. External rainfall association

### Availability mask

Rainfall was available for 357 of 960 cells, with the same mask on all 360 study days.

Of 290,355 complete-case cloud observations, 110,314 were matched (37.993%).

Rainfall validation is restricted to this spatial subset and cannot be generalized to all 960 cells without qualification. This does not invalidate clustering because rainfall was not a clustering input.

### Observed contrasts

Pooled rainfall summaries:

- Baseline K=2: Cluster 0 mean 6.90 mm / wet-day fraction 38.36%; Cluster 1 mean 12.50 mm / 53.00%.
- Log K=2: Cluster 0 mean 12.69 mm / 54.03%; Cluster 1 mean 6.25 mm / 36.11%.

Within-cell mean contrast (Cluster 0 minus Cluster 1) was -5.542 mm for baseline K=2 and +6.004 mm for log K=2.

The sign reversal is consistent with reversed numeric cluster labels; interpret by physical profiles. These are observational associations, not causal effects.

### Rainfall uncertainty (M6.4)

M6.4 used crossed resampling of 12 years and spatial blocks, with 2,000 replicates, 3°×3° and 5°×5° blocks, and support thresholds 1, 5 and 10.

For baseline K=2:
- Support ≥1: mean contrast -5.542 mm; 3° interval [-7.598, -3.607]; 5° interval [-7.930, -3.507].
- Support ≥10: mean contrast -4.238 mm; 3° interval [-6.063, -2.511]; 5° interval [-6.184, -2.549].

For log K=2:
- Support ≥1: mean contrast +6.004 mm; 3° interval [4.135, 7.940]; 5° interval [4.044, 8.164].
- Support ≥10: mean contrast +4.958 mm; 3° interval [3.170, 7.033]; 5° interval [3.038, 7.088].

K=2 contrasts remained directionally consistent across tested block sizes and support thresholds. Some K=3 strict-support comparisons were fragile and had limited support.

Intervals are conditional on the observed rainfall mask and matched observations; they do not correct for missing rainfall outside covered cells. Degree-based blocks are not equal-area. Bootstrap proportions are descriptive, not p-values. Twelve years limit temporal inference, and observations may be dependent.

## 7. Integrated conclusions

1. The selected cloud features contain substantial correlated structure; four PCs retain about 94% of variance in both representations.
2. Baseline K=2 has an interpretable lower- versus higher-cloud-property contrast.
3. K=2 is a leading candidate, not uniquely optimal by every internal metric.
4. Sampling and representation affect assignments; log-sensitivity was more stable in the fixed-init sampling experiment, while M6.3 found moderate cross-representation agreement.
5. t-SNE supports exploratory local-neighbourhood inspection, not physical-distance or regime claims.
6. Coverage-aware spatial/temporal analysis is necessary when interpreting prevalence changes.
7. Rainfall contrasts are directionally consistent for K=2 in the matched subset, but the mask covers only about 37.2% of cells.

## 8. Limitations

- Complete-case filtering excludes 55,245 of 345,600 raw observations.
- The selected 30-day window does not represent the entire monsoon season.
- K-means results depend on representation, sampling and model configuration.
- Internal metrics do not prove physical correctness.
- Fixed-init MiniBatchKMeans runs stopped after 1–3 iterations under the recorded early-stopping configuration.
- M6.3 used earlier controlled M6.2 predictions, not the later fixed-init predictions.
- t-SNE reached the iteration cap without demonstrated convergence.
- Rainfall matching is restricted to 357 cells and 110,314 observations.
- Rainfall associations are observational, not causal.
- Bootstrap uncertainty is conditional on rainfall availability and selected block definitions.
- The 12-year record and spatial/temporal dependence constrain inference.

## 9. Conclusion

The project develops an integrated exploratory workflow for cloud-feature groupings during the established-monsoon window over India.

PCA reveals compact structure, and K=2 provides an interpretable leading partition. However, sampling and representation sensitivity show that assignments are not invariant.

Rainfall analysis provides descriptive external association evidence only for the matched subset. Further physical validation, broader rainfall coverage and independent-period evaluation would be required before treating the clusters as robust meteorological regimes or making predictive claims.
