from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUTPUT = ROOT / "docs/methodology/established_monsoon_rainfall_association.md"

if OUTPUT.exists():
    raise FileExistsError(f"Refusing to overwrite existing report: {OUTPUT}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

report = r"""
# Established Monsoon: Cloud-Regime and Rainfall Association Analysis

## 1. Objective

This analysis examines how satellite-derived cloud clusters are associated
with daily rainfall during the Established Monsoon period (15 July–13 August)
for 2010–2021.

Rainfall is used as an independent validation and association variable.
It is not included in the cloud-clustering feature matrix.

The analysis is descriptive. It does not establish causal relationships
between cloud properties and rainfall.

## 2. Data alignment and sample construction

Cloud-cluster assignments were exported using the same fitted-model
configuration used in the temporal, spatial, and period-prevalence analyses.

Models examined:

- Baseline feature representation, K=2.
- Log-sensitivity feature representation, K=2.
- Log-sensitivity feature representation, K=3.

The assignments contain 290,355 complete-case cloud observations.

Daily IMD rainfall was aligned by date, latitude, and longitude.
The alignment audit confirmed matching dates and coordinates across all
12 annual files.

Rainfall availability:

- 10,710 valid rainfall grid-cell-day records per year.
- 128,520 valid rainfall records across all years.
- 110,314 observations with both a cloud assignment and valid rainfall.
- 180,041 cloud assignment observations without valid rainfall.

Only the 110,314 matched observations were used in the rainfall association
analysis. Missing rainfall values were not replaced with zero or imputed.

## 3. Rainfall distributions by cluster

An operational wet-day threshold of at least 2.5 mm/day was used.

### 3.1 Pooled distributions

| Model | Cluster | N | Mean rainfall (mm) | Median (mm) | Wet-day frequency |
|---|---:|---:|---:|---:|---:|
| Baseline K=2 | 0 | 60,663 | 6.900 | 0.784 | 38.356% |
| Baseline K=2 | 1 | 49,651 | 12.504 | 3.197 | 52.998% |
| Log K=2 | 0 | 54,370 | 12.690 | 3.436 | 54.033% |
| Log K=2 | 1 | 55,944 | 6.247 | 0.558 | 36.115% |
| Log K=3 | 0 | 31,610 | 10.702 | 2.530 | 50.158% |
| Log K=3 | 1 | 34,620 | 4.740 | 0.181 | 30.413% |
| Log K=3 | 2 | 44,084 | 12.183 | 3.093 | 52.622% |

Cluster identifiers are specific to each fitted model and must not be
compared across models as if they represented identical clusters.

The log-based solutions identify a lower-rainfall cluster:
Cluster 1 in both the K=2 and K=3 log-sensitivity models.

For log K=3, Clusters 0 and 2 have more similar rainfall distributions
than either has with Cluster 1.

The baseline K=2 solution produces the opposite rainfall ordering from
the log-sensitivity K=2 solution. This difference is important and should
be retained in the interpretation rather than hidden.

## 4. Annual consistency

Annual pairwise contrasts were calculated separately for each year.

For log K=2, the Cluster 0 minus Cluster 1 contrast was positive in
11 of 12 years for mean rainfall and 12 of 12 years for wet-day frequency.

For log K=3:

- Cluster 0 minus Cluster 1 was positive in all 12 years for mean rainfall
  and wet-day frequency.
- Cluster 1 minus Cluster 2 was negative in all 12 years for both measures.
- Cluster 0 and Cluster 2 showed weaker separation.

The baseline K=2 result differed: Cluster 0 minus Cluster 1 was positive
in only 1 of 12 years for mean rainfall and 0 of 12 years for wet-day
frequency.

These annual results support the consistency of the lower-rainfall
Cluster 1 in the log-sensitivity solutions.

## 5. Within-cell, within-year comparison

To reduce the influence of persistent geographical differences and
broad annual rainfall differences, rainfall was compared within the same
grid cell and year.

For each grid cell-year, mean rainfall was calculated separately for
each cluster. Pairwise differences were then calculated only where both
clusters were represented.

Overall equally weighted cell-year contrasts:

| Model comparison | Paired cell-years | Mean difference (mm) | Median difference (mm) | Positive (%) | Negative (%) |
|---|---:|---:|---:|---:|---:|
| Baseline K=2: C0-C1 | 4,169 | -5.542 | -2.579 | 28.424 | 68.266 |
| Log K=2: C0-C1 | 4,194 | 6.004 | 3.334 | 72.246 | 24.297 |
| Log K=3: C0-C1 | 3,640 | 5.133 | 2.995 | 70.055 | 26.126 |
| Log K=3: C0-C2 | 3,792 | -2.620 | -1.042 | 40.876 | 55.986 |
| Log K=3: C1-C2 | 3,866 | -7.162 | -4.394 | 21.650 | 75.479 |

For log K=3, the C0-C1 contrast was positive in every year, and the
C1-C2 contrast was negative in every year.

This supports a persistent rainfall ordering within grid cells and years,
rather than an association arising only from broad geographical or
annual differences.

These comparisons are descriptive and do not treat grid-cell-years as
independent inferential samples.

## 6. Minimum-support sensitivity

Within-cell comparisons were repeated after requiring each cluster to
have at least 1, 5, or 10 rainfall observations within a cell-year.

For log K=3:

| Comparison | Minimum observations | Paired cell-years | Mean difference (mm) | Median difference (mm) |
|---|---:|---:|---:|---:|
| C0-C1 | 1 | 3,640 | 5.133 | 2.995 |
| C0-C1 | 5 | 1,245 | 4.243 | 2.532 |
| C0-C1 | 10 | 70 | 1.724 | 1.217 |
| C0-C2 | 1 | 3,792 | -2.620 | -1.042 |
| C0-C2 | 5 | 2,233 | -3.047 | -1.228 |
| C0-C2 | 10 | 413 | -3.321 | -1.546 |
| C1-C2 | 1 | 3,866 | -7.162 | -4.394 |
| C1-C2 | 5 | 2,277 | -5.489 | -3.490 |
| C1-C2 | 10 | 702 | -4.150 | -2.724 |


The K=3 C0-C1 comparison becomes sparse at higher support thresholds.
Its direction remains positive, but only 70 cell-years remain at the
10-observation threshold. This is insufficient for a broad spatial
claim about the magnitude of the contrast.

The log K=2 contrast remains positive under the higher support
thresholds and is more spatially supported.

## 7. Period comparison

The analysis compared 2010–2016 with 2017–2021 using the same grid cells
in both periods.

For each grid cell and period, qualifying cell-year rainfall contrasts
were averaged. Only cells with estimates in both periods were retained.

### 7.1 Paired spatial period results

| Model comparison | Paired cells | Pre-period difference (mm) | Post-period difference (mm) | Change (mm) |
|---|---:|---:|---:|---:|
| Baseline K=2: C0-C1 | 332 | -4.805 | -6.970 | -2.165 |
| Log K=2: C0-C1 | 335 | 5.177 | 7.237 | 2.060 |
| Log K=3: C0-C1 | 158 | 4.696 | 5.190 | 0.494 |
| Log K=3: C0-C2 | 240 | -2.451 | -4.229 | -1.778 |
| Log K=3: C1-C2 | 232 | -5.055 | -6.752 | -1.697 |

The rainfall ordering remains the same across the two periods for the
log-sensitivity comparisons.

The log K=3 C0-C1 contrast changes only modestly. Spatial changes are
mixed rather than uniform.

### 7.2 Period support sensitivity

The paired spatial comparison was repeated while requiring each grid
cell to have qualifying observations in at least 1, 2, 3, or 4 different
years in each period.

For log K=2, C0-C1 remains positive in both periods at every threshold.
The mean change ranges from approximately 1.67 to 2.06 mm.

For log K=3, C0-C1 remains positive in both periods, but paired-cell
support declines from 158 cells at threshold 1 to 20 cells at threshold 4.
The mean change remains positive but is small, ranging from approximately
0.49 to 1.13 mm.

For log K=3, C1-C2 remains negative in both periods, with most retained
cells showing a further decrease. However, the number of paired cells
also decreases as support requirements become stricter.

The period support analysis therefore supports persistence of the
rainfall ordering more strongly than it supports a spatially uniform
change in rainfall contrast.

## 8. Interpretation alongside cluster prevalence

The cloud-cluster prevalence analysis identified a pronounced
2016–2017 redistribution in the log K=3 solution.

The rainfall analysis indicates that the lower-rainfall character of
Cluster 1 persists across the two periods. The within-cell rainfall
contrast does not show an equally strong or spatially uniform transition.

These are distinct findings:

1. Cluster prevalence describes how frequently each cluster occurs.
2. Cluster-rainfall association describes rainfall differences between
   observations assigned to those clusters.

A change in cluster prevalence does not necessarily imply a change in
the rainfall characteristics associated with each cluster.

## 9. Limitations

- Rainfall comparisons use only matched cloud-assignment and valid
  rainfall observations.
- Rainfall availability is spatially restricted and must not be treated
  as complete coverage of the cloud-assignment dataset.
- The wet-day threshold of 2.5 mm/day is an operational definition.
- Cluster labels are model-specific.
- Within-cell and period comparisons reduce some spatial and temporal
  confounding but do not establish causality.
- Grid-cell and cell-year observations are spatially and temporally
  dependent. Descriptive percentages and means are not independent
  inferential evidence.
- Higher minimum-support thresholds substantially reduce the number
  of available paired cells, especially for log K=3 C0-C1.
- The analysis does not establish a meteorological cause for the
  2016–2017 cluster-prevalence transition.
- No circulation mechanism is inferred from these rainfall comparisons.

## 10. Overall conclusion

The log-sensitivity clustering solutions show a consistent association
between Cluster 1 and lower rainfall. This ordering is supported by
pooled distributions, annual contrasts, within-cell comparisons, and
minimum-support sensitivity analyses.

For log K=3, Clusters 0 and 2 have more similar rainfall associations
than either has with Cluster 1.

The rainfall ordering persists between 2010–2016 and 2017–2021.
Evidence for a substantial and spatially uniform change in the
within-cell rainfall contrast is weaker, particularly for the
log K=3 C0-C1 comparison under stricter support requirements.

The findings should be interpreted as descriptive cloud-regime/rainfall
associations, not causal relationships or proof of a climate-driven
regime transition.
"""

OUTPUT.write_text(report.strip() + "\n", encoding="utf-8")
print("Created:", OUTPUT)
