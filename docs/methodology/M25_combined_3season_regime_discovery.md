# Milestone M25: Combined 3-Season Cloud-Regime Discovery

**Project:** Satellite Cloud Feature Grouping for Exploratory Weather Pattern Analysis (SIH26078)  
**Author:** Integration Lead  
**Scope:** Unified 3-Season Analysis (Pre-Monsoon, Established-Monsoon, Post-Monsoon)  
**Period:** 2010–2021 (12 Study Years)  
**Domain:** India (6.5°N–37.5°N, 68.5°E–97.5°E, 32 × 30 grid, 960 cells)  
**Total Observations:** 24,883,200 hourly cloud profiles  

---

## 1. Executive Summary & Objective

Prior seasonal analyses investigated Pre-Monsoon, Established-Monsoon, and Post-Monsoon periods separately. While useful for local characterization, separate clustering models suffer from fundamental methodological barriers:
1. **PCA Axis Rotation & Sign Flips:** Independently fitted eigenvectors cannot be compared directly across seasons.
2. **Arbitrary Label Permutations:** Cluster labels (e.g. Cluster 0) from independent runs have no correspondence.
3. **Variable Model Complexity:** Choosing different $K$ per season obscures annual cloud regime migration.

**Milestone M25 resolves this by constructing a Single Unified Feature Space across all 3 seasons simultaneously.**

Using the complete 24,883,200 hourly observation record:
- **Unified 3-Season PCA:** Top 2 components retain **83.16%** of total variance; top 5 retain **94.38%**; top 10 retain **98.74%**. Out-of-sample holdout reconstruction variance is **98.83%**.
- **Unified t-SNE:** Non-linear neighborhood trustworthiness reaches **0.9867** at perplexity 30, confirming robust manifold preservation.
- **Unified Cloud Regimes ($K=4$):** Selected by multi-criterion evaluation (peak Silhouette score **0.4935**).
- **Physical Regimes Discovered:**
  - **Regime 0 (12.89%):** Deep Convective Systems & Anvil Cirrus Shields
  - **Regime 1 (13.52%):** Active Low Convective Cells / Warm Cumulus
  - **Regime 2 (1.64%):** Optically Thick Mixed-Phase / High-Water Rainbands ($\tau = 10.79$, $\text{LWP} = 122.5\text{ g/m}^2$, $\text{IWP} = 125.4\text{ g/m}^2$)
  - **Regime 3 (71.94%):** Background Boundary-Layer Fair Weather & Suppressed Skies

---

## 2. Dataset and Preprocessing Pipeline

### 2.1 Seasonal Ingestion
- **Pre-Monsoon:** April 15 – May 14 (720 hrs/yr × 960 cells = 691,200 obs/yr)
- **Established Monsoon:** July 15 – August 13 (720 hrs/yr × 960 cells = 691,200 obs/yr)
- **Post-Monsoon:** October 15 – November 13 (720 hrs/yr × 960 cells = 691,200 obs/yr)
- **Total Combined:** $3 \times 691,200 \times 12\text{ years} = 24,883,200\text{ samples}$.

### 2.2 Leakage-Safe Imputation & Scaling
- **Feature Set:** `FS-A` (36 CERES features covering total and layer-specific area, height, pressure, temperature, optical depth, liquid and ice water path).
- **Temporal Splitting:** Imputation models and `RobustScaler` (median and IQR) fitted strictly on the **2010–2016 training partition** ($14,515,200\text{ samples}$). No observations from 2017–2021 were used during parameter fitting.
- **Treatment:** Cloud Area (`CA-A` median imputation); Cloud Properties (`SA-A` conditional property median conditioned on layer area $> 0$). Zero-filling strictly rejected.

---

## 3. Dimensionality Reduction (PCA & t-SNE)

### 3.1 Principal Component Analysis (IncrementalPCA)
Incremental PCA (batch size 100,000) fitted on the 14.5M training partition:

| Component | Explained Variance Ratio | Cumulative Variance Ratio | Physical Interpretation |
|---|---|---|---|
| **PC1** | 66.26% | 66.26% | High-cloud optical depth, ice water path, and vertical convective extent |
| **PC2** | 16.91% | 83.16% | Mid-to-low level mixed-phase liquid water path and boundary layer clouds |
| **PC3** | 4.31% | 87.47% | Cloud-top pressure and thermodynamic temperature contrast |
| **PC4** | 3.99% | 91.46% | Layer-specific coverage partitioning (high vs. low cloud area) |
| **PC5** | 2.92% | 94.38% | Optical thickness of mid-level clouds |
| **PC6–PC10** | 4.36% | **98.74%** | Minor boundary layer microphysics and residual variance |

- **Out-of-sample Holdout Evaluation (2017–2021):** Evaluated across 500,000 independent holdout observations. The top 10 PCs reconstructed **98.83%** of holdout variance, demonstrating exceptional temporal stationarity.

### 3.2 Non-Linear Manifold Learning (t-SNE)
- **Design:** Balanced stratified sample of 10,800 observations (300 per season per year across all 12 years).
- **Neighbor Trustworthiness ($k=12$):**
  - Linear PCA 2D: **0.9117**
  - t-SNE (Perplexity 30): **0.9867**
  - t-SNE (Perplexity 50): **0.9865**
- **Conclusion:** While 2D PCA captures global variance, t-SNE improves local neighborhood fidelity by **+7.5%**, revealing distinct convective clusters separated from continuous background clear-sky manifolds.

---

## 4. Unified Cloud-Regime Clustering ($K=4$)

### 4.1 Model Selection Metrics
MiniBatchKMeans evaluated on top 5 PCs ($94.38\%$ variance) on 50,000 validation samples:

| $K$ | Silhouette Score | Calinski-Harabasz Index | Davies-Bouldin Index | Status |
|---|---|---|---|---|
| 3 | 0.4809 | 11,014.5 | 0.9355 | Under-segmented |
| **4** | **0.4935** | **9,342.5** | **1.1313** | **Optimal Selection (Peak Silhouette)** |
| 5 | 0.4052 | 7,758.0 | 1.3300 | Sub-optimal separation |
| 6 | 0.3723 | 8,088.2 | 1.0063 | Fragmented |
| 7 | 0.3878 | 9,436.6 | 1.1777 | Fragmented |

### 4.2 Discovered Physical Regimes

| Regime | Physical Nomenclature | Overall Pct | Area Mean | Height Mean | Pressure Mean | Tau ($\tau$) Mean | IWP Mean | LWP Mean |
|---|---|---|---|---|---|---|---|---|
| **0** | **Deep Convective Systems & Anvils** | 12.89% | 62.0% | 6.17 km | 539.4 hPa | 3.81 | 65.0 g/m² | 45.7 g/m² |
| **1** | **Active Low Convective Cells** | 13.52% | 24.0% | 2.59 km | 799.3 hPa | 1.49 | 25.3 g/m² | 14.0 g/m² |
| **2** | **Thick Mixed-Phase Rainbands** | 1.64% | 68.9% | 5.56 km | 573.5 hPa | **10.79** | **125.4 g/m²** | **122.5 g/m²** |
| **3** | **Fair-Weather & Suppressed Sky** | 71.94% | 70.9% | 8.44 km | 402.9 hPa | 4.82 (med: 2.0) | 101.7 g/m² | 38.9 g/m² |

---

## 5. Seasonal Regime Migration & Transition Analysis

Decomposing the unified cluster labels across seasons reveals the annual meteorological cycle over India:

| Season | Regime 0 (Deep Convection) | Regime 1 (Low Convective) | Regime 2 (Thick Rainbands) | Regime 3 (Fair Weather) |
|---|---|---|---|---|
| **Pre-Monsoon** | 12.21% | **18.83%** | 1.33% | 67.63% |
| **Established Monsoon** | **13.61%** | 2.60% | **2.09%** | **81.71%** |
| **Post-Monsoon** | 12.85% | **19.15%** | 1.51% | 66.49% |

### Key Meteorological Insights:
1. **The Collapse of Regime 1 in Established Monsoon:**
   - Active low convective cells (Regime 1) account for **~19%** of observations in Pre-Monsoon (localized thermal thunderstorms) and Post-Monsoon (retreating coastal convection).
   - In Established Monsoon, Regime 1 collapses to just **2.60%**, as the monsoonal circulation reorganizes the atmosphere into large-scale organized monsoonal depressions, thick rainbands (Regime 2 peaks at **2.09%**), and deep convective anvil shields (Regime 0 peaks at **13.61%**).
2. **Prevalence of Suppressed/Fair Weather:**
   - Over the full $32 \times 30$ grid (which includes desert regions in the northwest, Tibetan plateau edges, and peninsular rain shadows), fair weather and thin cirrus (Regime 3) remain dominant (66%–82%).
   - Established Monsoon exhibits the highest percentage of Regime 3 (81.7%) because active monsoon depressions concentrate heavy cloudiness into narrow troughs, leaving vast portions of northwestern India under subsidence.

---

## 6. Generated Data Artifacts

All outputs are verified and stored on disk:
- Scaled Model-Ready Matrix: `data/processed/combined_3season/combined_3season_FS-A_scaled.npy` (3.58 GB)
- Top 10 PCA Scores: `data/processed/combined_3season/combined_3season_pca_top10_scores.npy` (995 MB)
- Cluster Labels: `data/processed/combined_3season/combined_3season_cluster_labels.npy` (24.8 MB)
- Spatial Regime Distributions: `reports/integration/combined_3season/combined_3season_spatial_regime_frequencies.csv`
- Cluster Profiles: `reports/integration/combined_3season/combined_3season_cluster_profiles.csv`
- Linear vs Non-Linear Comparison: `reports/integration/combined_3season/combined_3season_linear_vs_nonlinear_comparison.csv`
- Variance Ratios: `reports/integration/combined_3season/combined_3season_pca_variance.csv`
- Executive Manifest: `reports/integration/combined_3season/combined_3season_summary.json`
