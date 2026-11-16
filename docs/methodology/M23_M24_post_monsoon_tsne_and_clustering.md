# Milestones M23 & M24: Post-Monsoon t-SNE Manifold Learning and Cloud-Regime Clustering

**Project:** Satellite Cloud Feature Grouping for Exploratory Weather Pattern Analysis (SIH26078)  
**Season:** Post-Monsoon (October 15 – November 13, 2010–2021)  
**Study Domain:** India (6°N–38°N, 68°E–98°E; 32 × 30 grid = 960 cells)  
**Authoritative Checkpoint:** Milestones M23 & M24 Completed  
**Status:** **`COMPLETED_READY_FOR_INTERPRETATION`**  

---

## 1. Executive Summary

Following linear dimensionality reduction in Milestone M22, Milestones M23 and M24 fulfill **Objective 2** and begin **Objective 3** of the research framework:
- **Milestone M23 (Nonlinear Manifold Learning):** Evaluated $t$-distributed Stochastic Neighbor Embedding (t-SNE) across multi-perplexity settings ($\text{perp} \in [15, 30, 50]$), comparing local neighborhood preservation (trustworthiness) and physical variable alignment against linear PCA projections.
- **Milestone M24 (Unsupervised Cloud-Regime Clustering):** Segmented all $8,294,400$ post-monsoon observations across India into coherent exploratory cloud regimes using the top 5 principal components ($91.95\%$ variance retained), evaluating cluster validity metrics across $K \in [3, 4, 5, 6, 7]$.

---

## 2. Milestone M23: Nonlinear vs. Linear Dimensionality Reduction (t-SNE vs. PCA)

### 2.1 Stratified Subsampling Design
Because pairwise distance computation scales quadratically $\mathcal{O}(N^2)$ in t-SNE, a representative sample of $N = 9,996$ observations was selected using stratified temporal sampling (equal representation across all 12 study years from 2010 to 2021) and spatial coverage over the Indian subcontinent.

### 2.2 Multi-Perplexity Neighborhood Preservation (Trustworthiness)
Neighborhood trustworthiness ($k = 12$ nearest neighbors) measures how faithfully local manifolds from the original 36-dimensional feature space are preserved in the 2D projection:

| Representation | Parameter Setting | Trustworthiness ($k=12$) | KL Divergence |
|---|---|---|---|
| **Linear PCA 2D** | (PC1 vs PC2) | **$0.8047$** | N/A |
| **Nonlinear t-SNE** | Perplexity = 15 | **$0.9805$** | $1.6331$ |
| **Nonlinear t-SNE** | Perplexity = 30 | **$0.9806$** | $1.5153$ |
| **Nonlinear t-SNE** | Perplexity = 50 | **$0.9803$** | $1.4112$ |

**Scientific Insight:** t-SNE achieves a **$+0.1759$ gain (+17.6%)** in local neighborhood preservation over linear PCA. While linear PCA captures global variance and large-scale orthogonal cloud modes, t-SNE successfully resolves dense, curved manifolds separating mid-level mixed-phase clouds from deep convective cloud shields.

### 2.3 Physical Feature Correlations: PCA vs. t-SNE

Spearman rank correlations ($\rho$) between 2D coordinates and primary CERES satellite variables:

| Satellite Feature | Spearman $\rho$ (PC1) | Spearman $\rho$ (PC2) | Spearman $\rho$ (t-SNE 1) | Spearman $\rho$ (t-SNE 2) | Physical Interpretation |
|---|---|---|---|---|---|
| `cldtau_high_1h` | **$+0.815$** | $-0.142$ | $+0.494$ | $-0.187$ | High cloud optical thickness |
| `iwp_high_1h` | **$+0.827$** | $-0.107$ | $+0.492$ | $-0.160$ | High cloud ice water path |
| `lwp_mid_low_1h` | $+0.345$ | **$+0.673$** | $+0.198$ | **$+0.539$** | Mid-low liquid water path |
| `cldtau_total_1h` | $+0.656$ | $+0.438$ | $+0.359$ | $+0.489$ | Total optical thickness |
| `cldpress_top_total_1h`| $-0.426$ | $+0.125$ | **$-0.750$** | $-0.012$ | Cloud top pressure (vertical height) |
| `cldarea_total_1h` | $+0.579$ | $-0.063$ | $+0.668$ | $-0.063$ | Total fractional cloud area |

- **Linear PC1 and PC2** provide clean orthogonal axes aligned with high-ice convection and mid-low liquid water.
- **t-SNE Dimension 1** forms a strong continuous gradient of vertical cloud top height ($\rho = -0.750$ with cloud-top pressure).

---

## 3. Milestone M24: Cloud-Regime Clustering & Validation

### 3.1 Parameter Sweep & Cluster Diagnostics ($K \in [3..7]$)

Clustering was performed on the top 5 principal component scores ($91.95\%$ variance retained) using `MiniBatchKMeans` ($8,294,400$ samples):

| Cluster Count ($K$) | Inertia ($\times 10^9$) | Silhouette Score ($N=10\text{k}$) | Davies-Bouldin Index (Lower is Better) | Calinski-Harabasz Score | Diagnostic Assessment |
|---|---|---|---|---|---|
| **$K = 3$** | $2.317$ | **$0.724$** | **$0.950$** | **$15,711.4$** | Cleanest separation into 3 broad thermodynamic regimes |
| **$K = 4$** | $1.948$ | **$0.608$** | $1.145$ | $13,360.9$ | **Optimal exploratory meteorological balance** |
| **$K = 5$** | $1.932$ | $0.455$ | $1.083$ | $10,752.3$ | Minor sub-segmentation of convective cores |
| **$K = 6$** | $2.012$ | $0.374$ | $1.184$ | $8,584.2$ | Over-fragmentation of boundary-layer cloudiness |
| **$K = 7$** | $1.654$ | $0.138$ | $1.206$ | $8,717.3$ | Cluster dispersion degrades silhouette quality |

**Selection:** $K = 4$ provides the optimal balance between high cluster validity ($\text{Silhouette} = 0.608$) and meteorologically distinct physical regime separation.

---

### 3.2 Physical Meteorological Profiles of Discovered Cloud Regimes ($K = 4$)

Centroid properties across all $8,294,400$ observations:

| Regime ID | Observation Count | Proportion | Physical Cloud Characteristics | Meteorological Interpretation |
|---|---|---|---|---|
| **Regime 0** | $1,044,084$ | **$12.59\%$** | High cloud area ($+0.36$), high optical thickness, moderate ice path | **Deep Convective Detrainment & Cirrus Anvil Shield** |
| **Regime 1** | $63,412$ | **$0.76\%$** | Extreme ice water path ($>+2.5$), high optical depth ($>+2.0$), low cloud-top pressure | **Active Convective Storm Cores & Towering Thunderstorms** |
| **Regime 2** | $304,922$ | **$3.68\%$** | High mid-low liquid water ($+0.85$), moderate optical depth, mid-level cloud top | **Mid-Tropospheric Mixed-Phase & Stratiform Cloudiness** |
| **Regime 3** | $6,881,982$ | **$82.97\%$** | Near-zero ice, high cloud-top pressure ($\sim 850\text{ hPa}$), low fractional area | **Fair-Weather Cumulus / Boundary-Layer Inversion / Clear Sky** |

---

## 4. Generated Data & Report Artifacts

All outputs are saved in the canonical post-monsoon data and reports folders:

| Milestone | Artifact | File Path | Size | Description |
|---|---|---|---|---|
| **M23** | **t-SNE Embeddings** | `data/processed/post_monsoon/tsne/post_monsoon_tsne_sampled_embeddings.csv` | 1.52 MB | 9,996 sampled 2D embeddings across 3 perplexities |
| **M23** | **Linear vs Nonlinear CSV** | `reports/seasons/post_monsoon/m23_tsne/post_monsoon_linear_vs_nonlinear_comparison.csv` | 320 bytes | Spearman rank correlations for physical variables |
| **M23** | **t-SNE Summary JSON** | `reports/seasons/post_monsoon/m23_tsne/post_monsoon_tsne_summary.json` | 1.8 KB | Provenance, trustworthiness metrics, and insights |
| **M24** | **Cluster Labels Array** | `data/processed/post_monsoon/clustering/post_monsoon_cluster_labels_k4.npy` | 7.91 MB | $8,294,400$ uint8 cluster assignments (0..3) |
| **M24** | **Clustering Metrics CSV** | `reports/seasons/post_monsoon/m24_clustering/post_monsoon_clustering_metrics.csv` | 380 bytes | Sweep metrics ($K=3..7$) |
| **M24** | **Cluster Profiles CSV** | `reports/seasons/post_monsoon/m24_clustering/post_monsoon_cluster_profiles.csv` | 680 bytes | Physical centroid features and meteorological labels |
| **M24** | **Clustering Summary JSON**| `reports/seasons/post_monsoon/m24_clustering/post_monsoon_clustering_summary.json` | 2.5 KB | Provenance, ARI stability, and regime definitions |

---

## 5. Methodological Cautions & Boundaries (Objective 3)

In accordance with scientific integrity guidelines:
1. **Continuous Thermodynamics vs. Discrete Boxes:**
   Cloud formations exist along a continuous thermodynamic spectrum of temperature, moisture, and vertical velocity. These exploratory clusters represent statistical grouping prototypes, **not permanent or universally rigid physical categories**.
2. **Post-Monsoon Regime Dominance:**
   Regime 3 accounts for $82.97\%$ of observations, accurately reflecting the post-monsoon climatology of India (widespread dry continental air over northwestern and central India under the subtropical ridge, with active convection confined to southern peninsular India and the Bay of Bengal).
