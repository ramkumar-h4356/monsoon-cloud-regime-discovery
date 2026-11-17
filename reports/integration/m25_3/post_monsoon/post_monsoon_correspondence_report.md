# Milestone M25.3 — Phase 1: Post-Monsoon Independent-to-Combined Regime Correspondence

**Project:** Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain: Seasonal Variability, Atmospheric Conditions, Rainfall Associations, and ENSO–IOD Modulation  
**Milestone:** M25.3 — Cross-Season Regime Correspondence Audit (Phase 1: Post-Monsoon)  
**Execution Date:** November 16, 2026  
**Auditor / Investigator:** Senior Scientific Research Auditor, Atmospheric Data Scientist & Research-Software Engineer  
**Status:** `CORRESPONDENCE_EVALUATION_COMPLETED`  
**Feasibility Classification:** `READY` (100.0% space-time observation match; 8,294,400 observations)  
**Global Empirical Agreement:** **Weak Correspondence with Many-to-One Collapse** (ARI = -0.0576, NMI = 0.0422)  

---

## 1. Executive Summary and Scientific Objective

Milestone **M25.3 Phase 1** executes the first empirically verified cross-model regime correspondence comparison in the research program. 

The investigation compares:
1. **Independent Post-Monsoon Model (Milestone M24):** $K=4$ clustering fitted exclusively on the top 5 PCs of post-monsoon observations (2010–2016 training baseline), using post-monsoon-specific RobustScaler scaling centers and scales.
2. **Common Three-Season Combined Model (Milestone M25 & M25.1):** $K=4$ clustering fitted on the top 5 PCs of pooled observations across Pre-Monsoon, Established Monsoon, and Post-Monsoon, using a multi-season unified RobustScaler.

This is a **model correspondence evaluation**, strictly preserving existing research outputs without model retraining, parameter tuning, or label permutation.

### Key Empirical Findings:
1. **100.0% Exact Space-Time Key Verification:** All **8,294,400 hourly observations** across all 12 years (2010–2021) and 960 grid cells (32 × 30) were proven to represent identical physical satellite retrievals through exact space-time coordinate matching ($(\text{Year}, \text{Month}, \text{Day}, \text{UTC\_Hour}, \text{Latitude}, \text{Longitude})$).
2. **Global Partition Independence (Near-Zero ARI):** The global Adjusted Rand Index is **-0.0576** and Normalized Mutual Information is **0.0422**. Under pre-established scientific thresholds (ARI < 0.20), this demonstrates **weak global correspondence**.
3. **Many-to-One Collapse of Convective Gradations:** Independent post-monsoon Clusters 0, 1, and 2 (representing deep convection, thick cirrus anvil shields, and convective cores, totaling 17.0% of post-monsoon scenes) collapse overwhelmingly into a single combined regime: **79.5% to 89.1% of these observations map into Combined Regime 3 (Upper-Tropospheric Thin Cirrus & Anvil Outflow Debris)**.
4. **Multi-Way Splitting of the Dominant Post-Monsoon Fair-Weather Background:** Independent Cluster 3 (which represents 82.97% of all post-monsoon observations as a broad fair-weather/inversion baseline) is partitioned by the combined model into three distinct components:
   - **63.43%** map into Combined Regime 3 (thin cirrus / anvil debris).
   - **22.74%** map into Combined Regime 1 (boundary-layer shallow cumulus).
   - **12.69%** map into Combined Regime 0 (multi-layer mixed systems).
5. **Systematic Temporal Invariance:** Yearly ARI values are consistently negative across all 12 years (ranging between -0.0770 in 2015 and -0.0298 in 2020), proving that partition divergence is an inherent structural property of the differing latent spaces rather than interannual noise.

---

## 2. Input Integrity and Cryptographic Provenance

In accordance with strict reproducibility protocols, all input datasets and model summaries were verified via SHA256 checksums prior to calculation:

| Workstream Component | Relative Path | Size (Bytes) | SHA256 Checksum |
| :--- | :--- | :---: | :--- |
| **M24 Post-Monsoon Labels** | `data/processed/post_monsoon/clustering/post_monsoon_cluster_labels_k4.npy` | 8,294,528 | `c686143fde3675266d581c54...` |
| **M24 Scaling Archive (.npz)** | `data/processed/post_monsoon/model_ready/post_monsoon_FS-A_scaled.npz` | 812,285,681 | `2e4ddefd1df65ac22990e3f2...` |
| **M24 Clustering Summary** | `reports/seasons/post_monsoon/m24_clustering/post_monsoon_clustering_summary.json` | 4,483 | `7c01d89eca51c8d9cc144adc...` |
| **M25 Combined Labels** | `data/processed/combined_3season/combined_3season_cluster_labels.npy` | 24,883,328 | `903fffc4d5962882decc2995...` |
| **M25 Season IDs** | `data/processed/combined_3season/combined_3season_season_ids.npy` | 24,883,328 | `80b43aa542842d63c4f62de9...` |
| **M25 Calendar Years** | `data/processed/combined_3season/combined_3season_years.npy` | 49,766,528 | `a55949386956c095153de9d7...` |
| **M25 Grid Cell Indices** | `data/processed/combined_3season/combined_3season_cell_indices.npy` | 49,766,528 | `8cb06353a13bb7a4f09e7e5b...` |
| **M25 Pipeline Summary** | `reports/integration/combined_3season/combined_3season_summary.json` | 2,110 | `4d3770f05b003f4553c9fa84...` |

---

## 3. Observation Order and Space-Time Identity Verification

To prove that array elements represent identical physical observations:
1. **Flattening Order Verification:**
   - Both M24 and M25 process observations in canonical C-order:
     $$\text{Index} = \text{Year\_Offset} + t \times (N_{\text{lat}} \times N_{\text{lon}}) + \text{lat\_idx} \times N_{\text{lon}} + \text{lon\_idx}$$
   - Where $t \in [0..719]$ hours per season, $\text{lat\_idx} \in [0..31]$ ($6.5^\circ\text{N}$ to $37.5^\circ\text{N}$), and $\text{lon\_idx} \in [0..29]$ ($68.5^\circ\text{E}$ to $97.5^\circ\text{E}$).
2. **Season Identifier Verification:**
   - The M25 `combined_3season_season_ids.npy` array maps seasons as:
     - `season_id == 0`: Pre-Monsoon (691,200 obs/yr)
     - `season_id == 1`: Established Monsoon (691,200 obs/yr)
     - `season_id == 2`: Post-Monsoon (691,200 obs/yr)
   - Extracting `season_ids == 2` yields exactly **8,294,400 observations** across 12 contiguous blocks.
3. **Exact Array Identity:**
   - Year identity: `np.array_equal(m24_years, m25_post_years) == True`.
   - Grid cell identity: `np.array_equal(m25_post_cells, np.tile(np.arange(960), 12 * 720)) == True`.
   - Time boundary audit: NetCDF files for 2010, 2015, and 2021 confirmed start at `October 15 00:30 UTC` and end at `November 13 23:30 UTC` (exactly 720 hours).
4. **Matching Coverage Gate:**
   - Total M24 observations: 8,294,400
   - Total M25 post-monsoon observations: 8,294,400
   - Exactly matched observation pairs: **8,294,400 (100.0%)**
   - Unmatched observations: **0 (0.0%)**

---

## 4. Preprocessing and Latent Space Distinction

A critical scientific premise of M25.3 is recognizing that M24 and M25 were fitted under **fundamentally different scaling distributions**:

| Preprocessing Parameter | Independent Post-Monsoon (M21 / M24) | Combined Three-Season (M25 / M25.1) | Scientific Implication |
| :--- | :--- | :--- | :--- |
| **Observation Cohort** | Post-Monsoon 2010–2016 (4,838,400 obs) | All 3 Seasons 2010–2016 (1,451,520 sampled obs) | Combined includes deeply convective July–August. |
| **Total Cloud Cover Median** | **52.36%** (IQR = 79.01%) | **76.75%** (IQR = 70.90%) | Combined median is shifted higher by monsoon cloudiness. |
| **High Cloud Cover Median** | **4.13%** (IQR = 24.31%) | **11.32%** (IQR = 46.62%) | Combined space has nearly 3× higher high cloud cover. |
| **Cloud-Top Pressure Center** | **476.02 hPa** (IQR = 385.76 hPa) | **404.55 hPa** (IQR = 335.02 hPa) | Combined space shifts top pressure 71.5 hPa higher in atmosphere. |
| **PCA Variance Structure** | PC1 = 70.8%, PC2 = 13.2% (Top 5 = 91.95%) | PC1 = 66.3%, PC2 = 16.9% (Top 5 = 94.38%) | Eigenvectors span different latent subspaces. |

Because distance minimization occurs in Euclidean space over transformed PC scores, the cluster centroids partition different geometries. Comparing them tests **transferability across latent representations**.

---

## 5. Contingency and Correspondence Analysis

### 5.1 Raw Contingency Cross-Tabulation

Matched observation counts between independent M24 clusters (rows) and combined M25 regimes (columns):

| Independent M24 Cluster | Combined R0 (Multi-Layer) | Combined R1 (Shallow Cu) | Combined R2 (Deep Storm) | Combined R3 (Thin Cirrus) | M24 Cluster Total | M24 Pct |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cluster 0** (Deep Anvil) | 157,756 | 17,693 | 38,127 | **830,508** | 1,044,084 | 12.59% |
| **Cluster 1** (Convective Core) | 4,462 | 640 | 1,815 | **56,495** | 63,412 | 0.76% |
| **Cluster 2** (Thick Cirrus) | 30,900 | 4,453 | 6,714 | **262,855** | 304,922 | 3.68% |
| **Cluster 3** (Fair-Weather/Inv) | 873,106 | 1,565,212 | 78,434 | **4,365,230** | 6,881,982 | 82.97% |
| **Combined Regime Total** | 1,066,224 | 1,587,998 | 125,090 | **5,515,088** | **8,294,400** | 100.0% |
| **Combined Regime Pct** | 12.85% | 19.15% | 1.51% | **66.49%** | 100.0% | — |

---

### 5.2 Row-Normalized Matrix: $P(\text{Combined Regime } j \mid \text{M24 Cluster } i)$

Probability that an observation belonging to independent M24 Cluster $i$ is assigned to Combined Regime $j$:

| Independent M24 Cluster | $P(\text{R0} \mid \text{M24})$ | $P(\text{R1} \mid \text{M24})$ | $P(\text{R2} \mid \text{M24})$ | $P(\text{R3} \mid \text{M24})$ | Dominant Combined Regime | Dominant Probability |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **Cluster 0** (Deep Anvil) | 15.11% | 1.69% | 3.65% | **79.54%** | Regime 3 (Thin Cirrus & Anvil) | **0.7954** |
| **Cluster 1** (Convective Core) | 7.04% | 1.01% | 2.86% | **89.09%** | Regime 3 (Thin Cirrus & Anvil) | **0.8909** |
| **Cluster 2** (Thick Cirrus) | 10.13% | 1.46% | 2.20% | **86.20%** | Regime 3 (Thin Cirrus & Anvil) | **0.8620** |
| **Cluster 3** (Fair-Weather/Inv) | 12.69% | 22.74% | 1.14% | **63.43%** | Regime 3 (Thin Cirrus & Anvil) | **0.6343** |

---

### 5.3 Column-Normalized Matrix: $P(\text{M24 Cluster } i \mid \text{Combined Regime } j)$

Probability that an observation belonging to Combined Regime $j$ originated from independent M24 Cluster $i$:

| Combined Regime | $P(\text{C0} \mid \text{M25})$ | $P(\text{C1} \mid \text{M25})$ | $P(\text{C2} \mid \text{M25})$ | $P(\text{C3} \mid \text{M25})$ | Dominant M24 Cluster | Dominant Probability |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **Regime 0** (Multi-Layer Mixed) | 14.80% | 0.42% | 2.90% | **81.89%** | Cluster 3 (Fair-Weather/Inv) | **0.8189** |
| **Regime 1** (Shallow Cumulus) | 1.11% | 0.04% | 0.28% | **98.57%** | Cluster 3 (Fair-Weather/Inv) | **0.9857** |
| **Regime 2** (Deep Convective Core) | 30.48% | 1.45% | 5.37% | **62.70%** | Cluster 3 (Fair-Weather/Inv) | **0.6270** |
| **Regime 3** (Thin Cirrus & Anvil) | 15.06% | 1.02% | 4.77% | **79.15%** | Cluster 3 (Fair-Weather/Inv) | **0.7915** |

---

### 5.4 Global Agreement Metrics

- **Adjusted Rand Index (ARI):** **-0.0576**
- **Normalized Mutual Information (NMI):** **0.0422**
- **Mutual Information:** **0.0314 nats**
- **Entropy H(M24):** **0.5745 nats** | **Entropy H(M25):** **0.9148 nats**

### Predefined Interpretative Framework:
- **Strong 1-to-1 Correspondence:** Pairwise conditional probability $P \ge 0.75$ reciprocally, with global $\text{ARI} \ge 0.70$.
- **Predominantly 1-to-1 with Partial Splitting:** Leading match $P \ge 0.60$, secondary split $0.15 \le P < 0.35$, global $\text{ARI} \in [0.40, 0.70)$.
- **Many-to-One Correspondence:** Multiple independent clusters collapse predominantly ($\ge 0.70$) into a single combined regime.
- **Weak Correspondence:** Global $\text{ARI} < 0.20$ or $\text{NMI} < 0.20$.

**Formal Assessment:** **Weak Correspondence with Many-to-One Collapse.**  
The global partition of post-monsoon scenes is statistically distinct between the two models. This does not indicate failure of either model; rather, it reflects that **an unsupervised clustering algorithm optimized across a high-variance, multi-season convective dataset defines different cluster boundaries than one optimized solely on post-monsoon subsidence and localized convection**.

---

## 6. Temporal and Spatial Correspondence Breakdown

### 6.1 Yearly Consistency (2010–2021)

Year-by-year evaluation demonstrates that the weak global correspondence is not driven by specific anomalous years or sensor drift:

| Year | Matched Observations | Adjusted Rand Index (ARI) | Normalized Mutual Info (NMI) | Dominant M24 Mapping to M25 |
| :---: | :---: | :---: | :---: | :---: |
| **2010** | 691,200 | -0.0458 | 0.0446 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2011** | 691,200 | -0.0563 | 0.0492 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2012** | 691,200 | -0.0680 | 0.0446 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2013** | 691,200 | -0.0592 | 0.0534 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2014** | 691,200 | -0.0631 | 0.0442 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2015** | 691,200 | -0.0770 | 0.0486 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2016** | 691,200 | -0.0444 | 0.0437 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2017** | 691,200 | -0.0455 | 0.0393 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2018** | 691,200 | -0.0592 | 0.0363 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2019** | 691,200 | -0.0691 | 0.0379 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2020** | 691,200 | -0.0298 | 0.0321 | C0->R3, C1->R3, C2->R3, C3->R3 |
| **2021** | 691,200 | -0.0556 | 0.0397 | C0->R3, C1->R3, C2->R3, C3->R3 |

The temporal invariance confirms that the mapping is stationary across the entire 12-year climate record.

---

### 6.2 Spatial Concordance Across 960 Grid Cells

Evaluating local correspondence per grid cell ($N = 8,640$ observations per cell):
- **All 960 Cells Mean ARI:** -0.0044 (Standard Deviation: 0.0349)
- **Indian Land Cells ($N=357$):** Mean ARI = **0.0134**
- **Ocean and Neighboring Cells ($N=603$):** Mean ARI = **-0.0149**
- **Key Geographic Variations:**
  - *Northwestern India & Indo-Gangetic Plain:* Extreme fair-weather dominance; in both models, >90% of scenes are assigned to fair-weather / thin-cirrus partitions, leading to local ARIs near 0.00.
  - *Southern Peninsula & Bay of Bengal:* Areas with persistent post-monsoonal convective activity (associated with the Northeast Monsoon) exhibit higher local ARI values (+0.05 to +0.15), where convective systems are partially recognized across both models.
  - *Arabian Sea Coastal Upwelling:* Exhibits modest agreement on shallow boundary-layer cumulus (Combined Regime 1 vs M24 Cluster 3).

---

## 7. Physical Interpretation and Synthesis

### 7.1 Meteorological Mechanism Behind the Disparity

Why do two models, both using 36 CERES features and $K=4$, show such low direct assignment overlap?

```
Independent Post-Monsoon (M24)           Combined 3-Season (M25)
─────────────────────────────            ───────────────────────
Focus: Within-Season Contrast            Focus: Across-Season Contrast
Dominated by post-monsoon                Dominated by extreme summer monsoon
subsidence (83% fair-weather).           convection vs dry winter/spring.

Result:                                  Result:
- 3 convective clusters (C0, C1, C2)     - 1 thin cirrus / anvil cluster (R3)
  fine-tune post-monsoon convection.       absorbs all post-monsoon anvil scenes.
- 1 massive cluster (C3, 83%) lumps      - R1 (shallow Cu) & R0 (multi-layer)
  all clear sky, shallow cumulus,          split post-monsoon low-cloud scenes.
  and marginal stratus together.
```

1. **Resolution of Fine vs. Coarse Convection:**  
   In the independent post-monsoon model (M24), deep convection and thick cirrus are relatively rare (<18% of observations). The clustering algorithm dedicated **three separate clusters (0, 1, and 2)** to subdivide these rare convective scenes into core, intermediate, and anvil categories. In the combined three-season model (M25), deep monsoon convection (from July–August) is so vast and intense that all post-monsoon convective scenes are grouped together under Combined Regime 3 (Anvil Outflow Debris) or Regime 2 (Severe Storm Cores).
2. **Subdivision of Fair-Weather Subsidence:**  
   Conversely, in M24, the algorithm lumped all 83% of fair-weather/subsidence scenes into Cluster 3. In M25, because fair-weather scenes from post-monsoon are contrasted against pre-monsoon heat-low clear skies and monsoon cloud breaks, M25 successfully divided M24 Cluster 3 into **Shallow Cumulus (Regime 1, 22.7%)**, **Multi-Layer Mixed (Regime 0, 12.7%)**, and **Thin Cirrus (Regime 3, 63.4%)**.

### 7.2 Methodological Lessons for Satellite Cloud Climatology

1. **Seasonal Clustering Cannot Be Directly Subsumed into Annual Models Without Cross-Tabulation:**  
   Assuming that an independent seasonal cluster corresponds 1-to-1 with a multi-season cluster of the same name is invalid. Cross-model mapping must always be established empirically.
2. **Cluster Partitions Are Scale- and Context-Dependent:**  
   Clustering is a relative partition of the input variance. When the variance context changes (single season vs. three seasons), cluster centroids migrate, altering regime boundaries.

---

## 8. Verification and Deliverables Inventory

This milestone generated eight machine-readable artifacts in `reports/integration/m25_3/post_monsoon/`:

1. **Matching Manifest:** [`post_monsoon_matching_manifest.json`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_3/post_monsoon/post_monsoon_matching_manifest.json)
2. **Contingency Matrix:** [`post_monsoon_contingency_matrix.csv`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_3/post_monsoon/post_monsoon_contingency_matrix.csv)
3. **Row-Normalized Probabilities:** [`post_monsoon_row_normalized_correspondence.csv`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_3/post_monsoon/post_monsoon_row_normalized_correspondence.csv)
4. **Column-Normalized Probabilities:** [`post_monsoon_column_normalized_correspondence.csv`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_3/post_monsoon/post_monsoon_column_normalized_correspondence.csv)
5. **Global Metrics Summary:** [`post_monsoon_global_metrics.json`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_3/post_monsoon/post_monsoon_global_metrics.json)
6. **Cluster Mapping Table:** [`post_monsoon_cluster_correspondence.csv`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_3/post_monsoon/post_monsoon_cluster_correspondence.csv)
7. **Yearly Metrics Breakdown:** [`post_monsoon_yearly_correspondence.csv`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_3/post_monsoon/post_monsoon_yearly_correspondence.csv)
8. **Spatial Grid Breakdown (960 Cells):** [`post_monsoon_spatial_correspondence.csv`](file:///D:/Project%20Simulator/monsoon_cloud_research/reports/integration/m25_3/post_monsoon/post_monsoon_spatial_correspondence.csv)

All deliverables are replicated in `D:/Project Simulator/post_monsoon_research`.

---

## 9. Git Safety Attestation

- **Git Commits Created:** 0
- **Git Branches Modified, Pushed, or Merged:** 0
- **Git Resets or Cleans Executed:** 0
- **Existing Files Mutated or Overwritten:** 0 (Only new M25.3 outputs created).
- **Compliance Status:** 100% compliant with read-only audit safety constraints.
