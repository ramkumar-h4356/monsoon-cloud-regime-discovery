# Methodology: t-SNE exploration for Established Monsoon

## Role in the workflow
M5 follows M3 feature preparation and M4 PCA. PCA provides an interpretable linear dimensionality-reduction baseline. t-SNE is added as a nonlinear exploratory visualization of local neighbourhood structure.

## Data representations
Two M4 PCA score representations are considered:
1. Baseline standardized feature representation.
2. Log-sensitivity representation, using the M3-defined log1p transformations before its own standardization and PCA.

For each representation, the first 10 PCA scores are passed to t-SNE. The two representations are fitted independently.

## Observation sampling
The full complete-case dataset contains 290,355 observations across 2010–2021. A reproducible visualization sample targets 500 observations per year. Within each year, sample allocation is spread as evenly as possible across the available dates. Sampling is without replacement, with seed 42.

This design avoids allowing years with more complete observations to dominate the visualization sample. It is not a probability-weighted estimate of full-period prevalence and must not be used as a substitute for full-data statistical analysis.

## Parameter sensitivity
Perplexity values 30 and 50 are evaluated for both representations using the same observations. Perplexity controls the effective neighbourhood scale in t-SNE. The comparison is intended to assess whether broad local structures are sensitive to this setting; it is not a search for the most visually attractive embedding.

## Quality diagnostics
Trustworthiness is reported at k = 5, 15 and 30. It measures the extent to which local neighbours in the high-dimensional PCA input remain neighbours in the two-dimensional embedding. KL divergence is reported as an optimization diagnostic. Neither metric establishes meteorological validity.

## Scientific cautions
t-SNE is designed to preserve local neighbourhood relationships, not global geometry. Distances between separated groups, cluster sizes, density and empty gaps in the map should not be interpreted as direct physical quantities. A visually distinct island does not prove a distinct cloud regime. Physical interpretation requires subsequent analysis of the original cloud variables, spatial/temporal coherence and independent validation evidence.

Baseline and log-sensitivity t-SNE coordinates cannot be compared point-by-point as coordinates: each embedding is independently optimized and its orientation, rotation, reflection and scale are arbitrary. Compare neighbourhood diagnostics and downstream feature profiles instead.
