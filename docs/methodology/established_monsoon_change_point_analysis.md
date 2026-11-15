# Established Monsoon: Exploratory Change-Point Sensitivity Analysis

## 1. Objective

This analysis evaluates whether annual cluster prevalence during the Established Monsoon (July 15–August 13) exhibits a temporal change around 2016–2017.

It follows the annual spatial coverage-matched prevalence analysis. The objective is to compare candidate temporal models, not to establish a climate breakpoint or causal explanation.

## 2. Data and experimental design

- Period: 2010–2021 (12 annual observations).
- Clustering variants: baseline and log-sensitivity.
- Cluster counts: K=2 and K=3.
- Spatial coverage thresholds: 50%, 70%, and 80%.
- Prevalence measure: corrected annual equal-cell mean prevalence.
- Spatial matching: common grid-cell sets retained under each coverage threshold.
- Input: corrected annual coverage-matched cluster prevalence CSV.

The analysis evaluated constant, linear, step-change, and segmented-trend models. Candidate step and segmented breakpoints required at least three annual observations on either side.

AICc and BIC were used for exploratory model comparison.

## 3. Main findings

### 3.1 Log-sensitivity K=3

Clusters 0 and 1 consistently selected a step-change model at the 2016–2017 boundary.

This result was consistent across all three spatial coverage thresholds (50%, 70%, and 80%) and under both AICc and BIC.

For Cluster 0, the best AICc model was the 2016–2017 step model at all thresholds. Its AICc advantage over the next-best candidate ranged from approximately 7.86 to 10.59.

For Cluster 1, the corresponding AICc advantage ranged from approximately 7.77 to 11.82.

The segmented-trend model was not preferred for these two clusters. This supports a step-like redistribution rather than a gradual change in slope.

### 3.2 Log-sensitivity K=3, Cluster 2

Cluster 2 did not show the same breakpoint signature.

- At 50% coverage, the linear model was preferred by AICc, with the constant model very close.
- At 70% and 80% coverage, the constant model was preferred by AICc.
- The 2016–2017 step model was not preferred at any of the three thresholds.

Therefore, the change is not a uniform shift affecting all three clusters equally.

### 3.3 K=2 solutions

AICc selected constant models for the K=2 baseline and log-sensitivity solutions across all three thresholds.

BIC showed some different preferences at the 50% threshold, including segmented-trend models with different candidate boundaries. These results were not consistent enough to identify a robust 2016–2017 breakpoint for K=2.

## 4. Scientific interpretation

The strongest evidence is specific to the finer log-sensitivity K=3 partition.

The annual prevalence of Clusters 0 and 1 exhibits a reproducible step-like redistribution around 2016–2017. This is consistent with the earlier annual transition analysis and remains visible when using common spatial grid-cell sets under multiple coverage thresholds.

The analysis does not establish that a meteorological regime transition occurred. Cluster assignments are based on a fixed full-period feature-space partition, and the annual series contains only 12 observations.

The candidate breakpoint was selected by scanning multiple possible boundaries. The model comparison is exploratory and should not be interpreted as a formal significance test.

Spatial coverage matching reduces the influence of changing grid-cell composition, but it does not eliminate possible effects of within-cell missingness, observation counts, or temporal sampling.

No causal attribution is made.

## 5. Limitations

1. Only 12 annual observations are available.
2. Candidate breakpoint selection involves searching multiple possible boundaries.
3. Annual observations may not be statistically independent.
4. Coverage matching does not remove all missing-data effects.
5. Cluster labels describe a fixed model partition, not independently verified meteorological regimes.
6. No atmospheric circulation analysis is available in this project stage.

## 6. Conclusion

The exploratory change-point sensitivity analysis identifies a robust 2016–2017 step-like prevalence redistribution for Clusters 0 and 1 in the log-sensitivity K=3 solution.

The result persists across 50%, 70%, and 80% spatial coverage thresholds and is not reproduced in the same way by K=2 or Cluster 2.

This finding motivates independent investigation of rainfall associations. Rainfall must remain an external validation variable and must not be used as an input to the cloud clustering model.

## 7. Outputs

- `results/tables/07_clustering/change_point_analysis/all_candidate_model_scores.csv`
- `results/tables/07_clustering/change_point_analysis/best_model_by_series_corrected.csv`
- `results/tables/07_clustering/change_point_analysis/log_k3_candidate_ranking.csv`

Analysis scripts:

- `src/07_clustering/established_monsoon_change_point_analysis.py`
- `src/07_clustering/established_monsoon_correct_change_point_summary.py`
