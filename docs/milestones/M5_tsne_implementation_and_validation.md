# M5 — t-SNE dimensionality reduction

## Objective
Explore nonlinear local-neighbourhood structure in the Established Monsoon cloud-feature observations and compare the stability of the exploratory representation under the M3 baseline and log-sensitivity feature preparations.

## Inputs
- M4 `baseline_scores_and_metadata.npz`
- M4 `log_sensitivity_scores_and_metadata.npz`
- M3 `established_monsoon_group_B_manifest.json`

The first 10 PCA score dimensions are used as t-SNE inputs. This retains the dominant structure while reducing the input dimensionality and noise. M4 fitted PCA separately for baseline and log-sensitivity matrices; M5 preserves those two representations and uses identical sampled row indices for both.

## Sampling design
- Deterministic random seed: 42.
- Target: 500 observations per year.
- Sampling is approximately balanced across dates within each year.
- The resulting sample is expected to contain 6,000 observations for the 12 study years.
- The same sample is used for both feature representations and all perplexity settings.
- Sampling is for visualization and computational tractability; it is not a replacement for full-data inference or clustering.

## t-SNE design
Four independent embeddings are fitted:
- Baseline, perplexity 30.
- Baseline, perplexity 50.
- Log-sensitivity, perplexity 30.
- Log-sensitivity, perplexity 50.

Shared settings:
- Two output dimensions.
- PCA initialization.
- Automatic learning rate.
- Barnes-Hut approximation.
- Angle 0.5.
- Maximum 1,000 iterations.
- Random state 42.

## Diagnostics
- KL divergence and iteration count.
- Trustworthiness at neighbourhood sizes 5, 15 and 30.
- Coordinates retain year, date, latitude and longitude.
- Both feature representations use the same sampled observations.

Trustworthiness measures how well local neighbourhoods in the high-dimensional input are preserved in the low-dimensional embedding. It is a diagnostic, not a physical validation score.

## Interpretation limits
1. t-SNE is primarily a local-neighbourhood visualization technique.
2. Distances between separated groups in the 2D embedding do not reliably represent global distances in the original feature space.
3. Apparent islands or clusters are not, by themselves, evidence of physical cloud regimes.
4. The sampled embedding does not replace full-observation analyses.
5. Independently fitted t-SNE coordinate axes, orientations and locations are arbitrary. Do not compare coordinate values directly between baseline and log-sensitivity embeddings.
6. Perplexity changes the neighbourhood scale and should be interpreted as a sensitivity setting, not selected solely because it produces visually separated islands.

## Outputs
Written to `data/processed/clustering/established_monsoon/m5_tsne/`:
- `m5_tsne_sample_metadata.csv`
- Four embedding NPZ files.
- Four coordinate CSV files.
- `m5_tsne_model_summary.csv`
- `established_monsoon_m5_tsne_manifest.json`

## Validation
The implementation validates input archive alignment, finite PCA scores, expected feature dimensionality, yearly sample counts, date-balanced allocation, and finite embedding coordinates. Unit tests cover deterministic sampling, year/date balance, invalid sample sizes and a synthetic t-SNE execution.

## Status
Implementation package supplied. Local test and full-data execution must be completed by the researcher before M5 is considered validated or committed.
