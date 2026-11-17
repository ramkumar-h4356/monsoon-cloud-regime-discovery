# Established Monsoon PCA Methodology

PCA is applied independently to the M3 baseline and log-sensitivity Group B
matrices. Each contains the same 290,355 complete observations and 14 features
in the exact M3 feature order. Both inputs are already transformed and
standardized by M3. M4 therefore does not refit a scaler or change the feature
set. The PCA estimator centers each matrix internally.

All 14 components are retained for diagnostics. The explained-variance table
reports individual and cumulative variance, and component counts required to
reach 80%, 90% and 95% cumulative variance. Loadings describe the direction of
each principal axis in standardized feature space. Squared loadings, expressed
as percentages per component, provide a descriptive feature-contribution
summary.

Baseline and log-sensitivity results are not assumed to have identical axes.
Component signs are arbitrary, and transformation changes can rotate the
principal directions. The workflow therefore reports principal angles between
the first 2-, 3- and 5-dimensional loading subspaces, alongside a clearly
labelled same-index loading cosine diagnostic.

PCA outputs are descriptive for this selected Established Monsoon sample.
They do not establish causal relationships, meteorological regimes, or
out-of-sample predictive performance. Group B remains a provisional feature
set pending cross-season review.
