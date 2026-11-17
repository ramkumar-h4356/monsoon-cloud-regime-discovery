# Pre-monsoon Phase 2 Stage 1 audit

Status: complete. No imputation, scaling, PCA, t-SNE, clustering or holdout evaluation.

Observation: one hourly grid cell; exact timestamps and coordinates retained.
Features: total cloud area / 100, log1p(total optical depth), total cloud-top pressure (hPa).
Eligible: valid positive cloud area and all three valid properties; clear = area exactly zero.
Missing/invalid masks are metadata, excluded from future model feature matrices.

```text
               total  eligible_cloudy  clear  invalid_or_missing_area  incomplete_cloudy  sampled
split                                                                                            
train        4838400          4818467  19933                        0                  0    70000
development  1382400          1372679   9721                        0                  0    20000
holdout      2073600          2060970  12630                        0                  0        0
```

Sampling: up to 10000 eligible rows/year, SeedSequence([42, year]); no holdout sample.
IWP/LWP excluded: phase-dependent availability; missing never replaced by zero.
All training/development locations are held together by year. Spatial transfer is untested.
Phase 1 used all years; this holdout is not historically unseen.
Other seasons share definitions, but future fitted models must be season-specific.

See manifest.json for source/output hashes, configuration, environment and Git state.
See feature_missingness, retention_strata, retention_spatial and phase_iwp_audit CSVs for counts and their denominators. Holdout has only primary validity and annual counts.
