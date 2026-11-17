# M25.3.1 — Scientific Audit: Pre-Monsoon Clear-Sky Semantics and M25 R3 Mapping

**Milestone:** M25.3.1  
**Investigation:** Physical vs Methodological Nature of the 100% Pre-Monsoon Clear-Sky to M25 R3 Mapping  
**Date:** 2026-11-17  

---

## 1. Executive Summary & Audit Mandate

The integrated M25.3 synthesis report observed that all **42,284 pre-monsoon clear-sky observations** ($0.51\%$ of the $8,294,400$ total population) mapped exclusively into **M25 Regime R3**. Earlier draft text loosely described this as *“confirming that zero-cloud or missing-retrieval columns belong to the cirrus/anvil background cluster.”*

This audit rigorously dissects the microphysical data, satellite retrieval mechanics, imputation rules, and vector-space geometry to establish whether this mapping represents a **genuine physical cloud-regime relationship** or an **inevitable methodological artifact**.

---

## 2. Microphysical and Retrieval Evidence

An audit of the underlying raw NetCDF records (`CERES_2010_pre_monsoon.nc` through `CERES_2021_pre_monsoon.nc`) and Noshin Muhammed’s operational label arrays reveals:

1. **Clear-Sky Definition in Source Artifacts:**
   - In Noshin’s Stage 1 and Stage 2 pipeline, `cluster == -1` is explicitly documented as `clear_label: -1` (`description: Operational cloudy-regime labels; no natural-type validation`).
   - For all 42,284 observations where `cluster == -1`, satellite-observed total cloud area is identically zero:
     $$\text{cldarea\_total\_1h} = 0.000\% \quad (\text{min} = 0.0, \text{max} = 0.0, \text{mean} = 0.0)$$
   - There are zero missing values ($\text{NaN}$) in cloud area for these records.

2. **Structural Absence of Cloud Properties:**
   - Because cloud area is zero, CERES satellite retrieval algorithms do not compute optical depth ($\tau$), cloud top pressure ($P_{\text{top}}$), cloud top temperature ($T_{\text{top}}$), liquid water path ($\text{LWP}$), or ice water path ($\text{IWP}$).
   - These variables are unretrieved ($\text{NaN}$ in raw data), representing **structural absence** (Missingness Code: `STRUCTURAL_ABSENCE`), not instrumentation failure.

3. **M25 Feature Engineering & Imputation Mechanics:**
   - The M25 pipeline processed all 24.88M observations using **CA-A** for cloud areas and **SA-A** for cloud properties.
   - For `cldarea_total_1h == 0`:
     - $\text{cldarea}$ is retained as $0.0$.
     - $\text{cldtau\_total\_1h}$, $\text{lwp\_total\_1h}$, and $\text{iwp\_total\_1h}$ are structurally imputed to $0.0$.
     - Cloud pressure and height variables are imputed to training-set conditional medians.
   - The resulting 36-variable feature vector is scaled via training-fitted `RobustScaler` and projected into the 10-dimensional PCA subspace.

---

## 3. Vector-Space Geometry & Clustering Behavior

In the M25 common 4-cluster model ($K=4$), the MiniBatchKMeans centroids in physical space are:
- **R0 (Mixed Convective):** $\tau = 3.81$, $\text{LWP} = 45.7\text{ g/m}^2$, $P_{\text{top}} = 539\text{ hPa}$.
- **R1 (Shallow Cumulus):** $\tau = 1.49$, $\text{LWP} = 0.0\text{ g/m}^2$, $P_{\text{top}} = 865\text{ hPa}$ (low level, warm).
- **R2 (Deep Convective Storms):** $\tau = 10.79$, $\text{LWP} = 122.5\text{ g/m}^2$, $\text{IWP} = 125.4\text{ g/m}^2$.
- **R3 (Thin Cirrus & Anvil Outflow):** $\tau = 2.03$, $\text{LWP} = 0.0\text{ g/m}^2$, $\text{IWP} = 26.6\text{ g/m}^2$, $P_{\text{top}} = 402.9\text{ hPa}$ (high level, cold).

When an imputed clear-sky observation ($\text{cldarea} = 0, \tau = 0, \text{LWP} = 0, \text{IWP} = 0$) is evaluated under Euclidean distance across the 10 principal components:
1. Centroids R0 and R2 are ruled out immediately due to massive Euclidean penalties from liquid and ice water paths.
2. Centroid R1 is heavily penalized because R1 is strongly anchored in boundary-layer pressure ($865\text{ hPa}$) and warm boundary-layer temperature ($285\text{ K}$).
3. **Centroid R3 has the minimal Euclidean distance.**

Consequently, **every single zero-cloud observation is mathematically forced into cluster R3.**

---

## 4. Scientific Demarcation & Resolution

To maintain rigorous epistemic discipline, the four distinct physical/methodological states must be distinguished:

```
+------------------------------------+---------------------------------------------------------------+
| Category                           | Scientific Definition & Status                                |
+------------------------------------+---------------------------------------------------------------+
| 1. Genuine Clear-Sky               | Atmosphere with 0% cloud fraction (Noshin label -1).          |
| 2. Structural Retrieval Absence    | Satellite properties unretrieved because no cloud is present.  |
| 3. Zero/Median Imputation          | Preprocessing mathematical fill (CA-A/SA-A) to enable PCA.    |
| 4. Valid Upper-Tropospheric Cirrus | Physical clouds with optical depth > 0 and ice crystals.      |
+------------------------------------+---------------------------------------------------------------+
```

### Audit Finding:
- **Clear sky and thin cirrus are NOT physically equivalent.**
- The $100\%$ mapping of clear-sky observations into M25 R3 is a **methodological artifact** of applying a 4-cluster model without a dedicated clear-sky regime.
- In M25, cluster R3 acts as an **absorbing background partition** for both physical high thin cirrus and zero-cloud columns.

### Required Correction to Reporting:
The scientific synthesis text must state:
> *"The 100% mapping of pre-monsoon clear-sky observations into M25 R3 is a mathematical consequence of zero/median imputation in continuous vector space, where zero-cloud vectors are geometrically nearest to the low-optical-depth, zero-LWP cirrus centroid. This reflects the absence of a distinct clear-sky cluster in M25 K=4, not physical equivalence between clear sky and cirrus clouds."*
