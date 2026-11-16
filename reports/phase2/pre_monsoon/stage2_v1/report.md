# Pre-monsoon Stage 2 methodology and actual results

Status: complete. Training fits: 2010–2016 only. Development diagnostics: 2017–2018 only.
Holdout access/evaluation: none. No development-inclusive final refit.

Training sample: 70,000; development: 20,000.
Observation: hourly CERES grid cell; complete valid cloudy cases. Clear sky stays separate.
Inputs: cloud area fraction, log1p optical depth, cloud-top pressure (hPa).
Median imputer, StandardScaler and full-SVD unwhitened PCA fit on training sample only.
Imputation is inert on this complete sample; no water-path gaps are filled.

Selected PCA components: 3; criteria: >=95% training variance and maximum development per-feature reconstruction RMSE <=0.25 training SD.
Training explained variance fractions: [0.5720820103510135, 0.29225728376235754, 0.135660705886629].
Component coefficients and feature-PC correlations are reported separately.

Selected operational cluster count: 2. Development silhouette (common standardized space): 0.4189; CH: 2739.09; DB: 0.9541.
Median initialization ARI: 0.9986; median year-bootstrap ARI: 0.9934.
Selection: smallest admissible k within 0.02 of best development silhouette; minimum occupancy 1%, initialization/bootstrap median ARI >=0.8. All k metrics retained.

t-SNE: 12 experiments on 3000 fixed year-balanced points, 3 input PCs. Display perplexity: 100; mean original-space trustworthiness: 0.9927.
All seeds, trustworthiness neighborhoods, parameter sensitivities and coordinate tables are saved.
Cluster labels come from feature/PCA space, never t-SNE. Island size/distance has no physical interpretation.

## Cautious physical summaries (training sampled medians)

```text
 cluster                       label  median_cloud_area_percent  median_optical_depth  median_cloud_top_pressure_hpa
       0  mid-topped; optically thin                  21.291475              0.806352                     660.194336
       1 high-topped; optically thin                  94.436737              2.450413                     333.587524
```

Pressure/optical-depth bins are descriptive, not validated cloud types or evidence of convection/rainfall.
physical_profiles.csv includes original-unit spread and valid/missing denominators separately by split.
Profile quantiles use the fixed sample. Annual/spatial/diurnal/daily occurrence and transitions use every eligible 2010–2018 observation; clear and unavailable labels remain explicit.

## Limitations and remaining work

K-Means partitions continuous, potentially non-spherical mixtures. Good internal metrics do not prove discrete meteorological regimes. Review per-cluster silhouette distributions and bootstrap variability.
Only seven training years and two development years; five year bootstraps give limited stability evidence, not formal confidence intervals. Sample rows remain spatially/temporally dependent.
Equal-year fitting samples differ slightly from full-population weighting. Grid-cell weighting is primary; cosine-latitude-weighted annual frequencies are a descriptive sensitivity. UTC is not local solar time.
Water-path profiles are conditional on retrieval availability; phase is an aggregate index. No additional physics variable was used for fitting.
Phase 1 examined 2010–2021; the reserved holdout is not historically unseen. Other seasons require separate fits under the unchanged shared contract.
Stage 3 requires approval: review/freeze selected configuration and scientific interpretations, then separately authorize any development-inclusive final refit and final temporal holdout evaluation.

See docs/methodology/pre_monsoon_stage2_protocol.md and config/pre_monsoon_stage2.json for exact rules. manifest.json records input/output/code/config hashes, versions, Git state and all accessed data years.
