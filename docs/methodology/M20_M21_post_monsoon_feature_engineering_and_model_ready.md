# Milestone M20 & M21: Post-Monsoon Missingness-Aware Feature Engineering and Model-Ready Dataset Construction

**Project:** Satellite Cloud Feature Grouping for Exploratory Weather Pattern Analysis (SIH26078)  
**Season:** Post-Monsoon (October 15 – November 13, 2010–2021)  
**Study Domain:** India (6°N–38°N, 68°E–98°E; 32 × 30 grid = 960 cells)  
**Authoritative Checkpoint:** Milestones M20 & M21 Completed  

---

## 1. Executive Summary

Milestones M20 and M21 bridge raw satellite observations into model-ready datasets specifically constructed for exploratory dimensionality reduction (Milestone M22: Principal Component Analysis) and subsequent unsupervised clustering.

- **Milestone M20 (Completed):** Comprehensive audit of missingness and structural absence across all 12 post-monsoon CERES NetCDF datasets (2010–2021). Evaluated 8,294,400 observations per variable across 36 screened variables. Validated all 6 candidate feature sets (FS-A through FS-F).
- **Milestone M21 (Completed):** Constructed the standardized Stage A baseline model-ready dataset (`FS-A`, 36 features, `CA-A` cloud area treatment, `SA-A` property treatment, `RobustScaler` scaling, equal weighting) with strict leakage-safe temporal partitioning (2010–2016 train vs. 2017–2021 holdout).

---

## 2. Milestone M20: Missingness Analysis & Classification

### 2.1 The Cloud-Area Missingness Policy
Physical cloud properties (e.g., optical depth, cloud-top pressure, water paths) cannot exist when cloud area is zero ($cldarea = 0$). Filling such structural absences with zero creates severe artificial spikes and distorts linear covariance matrices.

Under M20:
1. **Zero-fill is strictly forbidden** for cloud property variables.
2. Missing values are classified into five mutually exclusive and exhaustive codes:
   - `0 - OBSERVED`: Finite property and finite cloud area $> 0$.
   - `1 - STRUCTURAL_ABSENCE`: Missing property when matching cloud area $= 0$.
   - `2 - CLOUD_AREA_MISSING`: Missing cloud area observation.
   - `3 - RESIDUAL_MISSING`: Missing property when matching cloud area $> 0$ (unretrieved or failed satellite retrieval).
   - `4 - UNKNOWN_CLOUD_AVAILABILITY`: Missing property when matching cloud area is also missing.

### 2.2 Post-Monsoon Missingness Findings
- **High Cloud Properties:** Exhibit ~35.27% structural absence ($cldarea\_high = 0$) and $0.0\%$ residual missingness (except `iwp_high_1h` at $0.31\%$).
- **Total Cloud Properties:** Exhibit ~1.48% structural absence and $0.0\%$ residual missingness.
- **Ice Water Path (`iwp_total_1h`):** Exhibits $21.76\%$ residual missingness, placing it in the `HIGH_CONCERN / EXCLUDE_PRIMARY` sensitivity band, properly restricted to exploratory feature sets.
- **Cloud Area Total:** $100.0\%$ complete across all 12 years (0 missing values).

### 2.3 Feature-Set Validation
All six candidate feature sets passed validation:
- **FS-A (36 features):** Full candidate set across all layers (High, Mid-High, Mid-Low, Low, Total). Primary baseline.
- **FS-B (21 features):** High-confidence core properties.
- **FS-C (21 features):** Structural/radiative focus.
- **FS-D (21 features):** Microphysical profile focus.
- **FS-E (16 features):** Compact minimal set.
- **FS-F (21 features):** Phase-isolated sensitivity set.

---

## 3. Milestone M21: Model-Ready Construction Architecture

### 3.1 Strict Methodological Safeguards
1. **Leakage Safeguard (Temporal Partitioning):**
   - Training partition: **2010–2016** ($7 \text{ years} = 4,838,400 \text{ grid-cell hours}$).
   - Holdout partition: **2017–2021** ($5 \text{ years} = 3,456,000 \text{ grid-cell hours}$).
   - All imputation medians (conditional and overall) and all scaling parameters (medians and interquartile ranges) are fitted **strictly on the training partition (2010–2016)**.
   - The holdout partition is transformed strictly out-of-sample. No future data informs the scaler.
2. **Season Independence:**
   - Post-monsoon data is processed completely independently.
   - Observations are never pooled across pre-monsoon, established-monsoon, and post-monsoon during standardization.
3. **Memory Optimization:**
   - Streamed processing utilizing memory-mapped disk buffers (`numpy.memmap`), ensuring processing consumes $<200 \text{ MB}$ of active system RAM despite the $1.19 \text{ GB}$ uncompressed float32 volume.

### 3.2 Preprocessing Transformation Formulas
1. **Cloud Area Imputation (`CA-A`):**
   $$\tilde{A} = \begin{cases} A, & \text{if finite} \\ \text{median}_{\text{train}}(A), & \text{if missing} \end{cases}$$
2. **Property Conditional Imputation (`SA-A`):**
   $$\tilde{P} = \begin{cases} P, & \text{if } P \text{ observed} \\ \text{median}_{\text{train}}(P \mid A > 0), & \text{if structural absence or residual missing} \\ \text{median}_{\text{train}}(P), & \text{if unknown cloud availability} \end{cases}$$
3. **Robust Standardization (`RobustScaler`, equal weighting):**
   $$Z_{j} = \frac{\tilde{X}_{j} - \text{median}_{\text{train}}(X_{j})}{\text{IQR}_{\text{train}}(X_{j})}$$
   where $\text{IQR} = Q_{75} - Q_{25}$.

---

## 4. Output Artifacts and Data Provenance

All model-ready outputs are stored in the canonical post-monsoon directory:
`D:/Project Simulator/monsoon_cloud_research/data/processed/post_monsoon/model_ready/`

| Artifact | File Name | Format | Purpose |
|---|---|---|---|
| **Compressed NetCDF4** | `post_monsoon_model_ready_FS_A.nc` | NetCDF4 (zlib 4) | Archival, CF-compliant spatial/temporal exploration |
| **Fast NumPy Archive** | `post_monsoon_FS_A_scaled.npz` | Compressed NPZ | Fast data loading for scikit-learn / PCA |
| **Memory-Mapped Array** | `post_monsoon_FS_A_scaled.npy` | Raw binary NPY | Instantaneous 0ms out-of-core memory-mapped loading |
| **Processing Manifest** | `post_monsoon_model_ready_manifest_FS_A.json` | JSON | Full SHA256 provenance, partition stats, and validation |

### Output Verification Summary
- **Total Samples:** $8,294,400$
- **Total Features:** $36$ (FS-A)
- **Training Samples (2010–2016):** $4,838,400$ ($58.33\%$)
- **Holdout Samples (2017–2021):** $3,456,000$ ($41.67\%$)
- **Missing / NaN Count:** Exactly $0$ ($0.0\%$)
- **Infinite Count:** Exactly $0$ ($0.0\%$)
- **Validation Status:** `READY_FOR_PCA`

---

## 5. Handoff to Milestone M22 (Principal Component Analysis)

To load and perform PCA on the verified post-monsoon dataset:

```python
import numpy as np
from sklearn.decomposition import PCA, IncrementalPCA

# 1. Instantaneous Out-of-Core Memory-Mapped Loading (0ms, 0 RAM overhead)
X_all = np.load(
    r"D:\Project Simulator\monsoon_cloud_research\data\processed\post_monsoon\model_ready\post_monsoon_FS_A_scaled.npy",
    mmap_mode="r"
)

# 2. Load Partition Metadata
meta = np.load(
    r"D:\Project Simulator\monsoon_cloud_research\data\processed\post_monsoon\model_ready\post_monsoon_FS_A_scaled.npz"
)
train_mask = meta["train_mask"]
feature_names = meta["feature_names"]

# 3. Extract Training Split (2010-2016)
X_train = X_all[train_mask] # Shape: (4838400, 36)

# 4. Fit PCA on Training Partition
pca = PCA(n_components=10)
pca.fit(X_train)

print("Explained Variance Ratios:", pca.explained_variance_ratio_)
print("Cumulative Variance:", np.cumsum(pca.explained_variance_ratio_))
```
