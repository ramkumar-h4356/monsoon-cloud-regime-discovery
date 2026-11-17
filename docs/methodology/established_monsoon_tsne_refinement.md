# M5 refinement methodology

The first M5 execution used a 1,000-iteration maximum and all four t-SNE fits reported 999 iterations. This is treated as an optimization-budget warning, not proof of non-convergence.

The refinement holds the observations, feature representations, first ten PCA dimensions, perplexities, random seed, initialization and other t-SNE settings fixed. It changes only the maximum iteration budget to 3,000. Refined outputs are written to a separate directory so the original experiment remains reproducible.

Four year-coloured plots are generated. Year colour is used to inspect temporal composition in the embedding. Apparent year segregation or mixing is descriptive only; it does not establish temporal causality or a physical cloud regime.

If a fit again reaches its iteration ceiling, report the budget limitation rather than describing the optimization as converged. Compare KL divergence, trustworthiness and visual patterns with the original runs. The embedding is an exploratory representation of local neighbourhoods, not a map with reliable global distances.
