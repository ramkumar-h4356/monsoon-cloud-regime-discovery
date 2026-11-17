# M25.3.1 — Scientific Audit: Temporal Stability and Generalization Claims

**Milestone:** M25.3.1  
**Investigation:** Audit of Model Fitting Periods, Holdout Generalization Claims, and Evaluation Scopes  
**Date:** 2026-11-17  

---

## 1. Scope of Audit

The integrated M25.3 synthesis report evaluated cluster correspondence across three temporal partitions:
- **Training Period:** 2010–2016 (7 years)
- **Development Period:** 2017–2018 (2 years)
- **Holdout Period:** 2019–2021 (3 years)

The synthesis report noted that holdout metrics were very similar to development metrics and described this as *“confirming robust generalization.”* This audit evaluates the validity of that claim by examining model fitting scopes, preprocessing boundaries, and metric definitions.

---

## 2. Model Fitting Scopes Across Workstreams

| Workstream | Scaling Fit Scope | PCA Fit Scope | Clustering Fit Scope | Holdout Status (2019–2021) |
|---|---|---|---|---|
| **Pre-Monsoon (Noshin)** | 2010–2016 only | 2010–2016 only | 2010–2016 only | **Strict Out-of-Sample Holdout** (Frozen Stage 2 bundle evaluated in Stage 3) |
| **Established-Monsoon (Abhin)** | **2010–2021 Full Period** | **2010–2021 Full Period** | **2010–2021 Full Period** | **In-Sample Sub-Slice** (Descriptive baseline fitted over all 12 years) |
| **Post-Monsoon (M24)** | 2010–2016 only | 2010–2016 only | 2010–2016 only | **Strict Out-of-Sample Holdout** |
| **Combined 3-Season (M25)** | 2010–2016 only | 2010–2016 only | 2010–2016 only | **Strict Out-of-Sample Holdout** (10.37M holdout observations) |

### Critical Finding on Established Monsoon:
- Abhin S’s recovered manifest (`established_monsoon_group_B_manifest.json`) explicitly documents that the Group B baseline was fitted on **all 290,355 complete cases spanning 2010–2021**.
- This was an approved exploratory design for an unsupervised climatological study, but it means that for Abhin’s model, the 2019–2021 observations were **already present during scaler and cluster fitting**.
- Therefore, Established-Monsoon split metrics evaluate **temporal stability of descriptive partition correspondence**, NOT genuine out-of-sample generalization.

---

## 3. Dissecting the "Generalization" Claim

### What the Empirical Metrics Actually Show:
- **Pre-Monsoon:** Dev $\text{NMI} = 0.1532 \rightarrow$ Holdout $\text{NMI} = 0.1480$ ($\text{ARI} = +0.1169$).
  - Noshin’s model was frozen before holdout evaluation. The consistency of $\text{NMI} \approx 0.15$ demonstrates genuine **out-of-sample stability of the bimodal partition**.
- **Post-Monsoon:** Dev $\text{NMI} = 0.0410 \rightarrow$ Holdout $\text{NMI} = 0.0418$ ($\text{ARI} = -0.0578$).
  - The metric is completely flat, but its magnitude ($\text{NMI} \approx 0.04$) is close to zero.
- **Established-Monsoon:** Dev $\text{NMI} = 0.0392 \rightarrow$ Holdout $\text{NMI} = 0.0395$ ($\text{ARI} = +0.0119$).
  - Similarly, the metric is flat, but its magnitude is tiny ($\text{NMI} \approx 0.04$).

### Scientific Audit Correction:
- Claiming that an $\text{NMI}$ of $0.04$ demonstrates *“robust generalization”* is **scientifically unsupportable**.
- An $\text{NMI}$ of $0.04$ indicates that the two cluster partitions share only about $4\%$ of their mutual information—i.e., they are largely distinct geometric representations.
- The fact that the value is stable ($0.0410$ vs $0.0418$) proves **temporal consistency of weak correspondence**, NOT *robust physical generalization*.

---

## 4. Required Terminology Standardization

All project reports must replace misleading claims of "generalization" with rigorous definitions:

1. **Temporal Partition Consistency:** The observed cross-model correspondence does not fluctuate erratically over time, confirming that geometric alignment is not driven by peculiar weather anomalies in single years.
2. **Stable Weak Correspondence:** For Established Monsoon and Post-Monsoon, the correspondence is consistently weak ($\text{NMI} \approx 0.04$), reflecting fundamental methodological divergences (daily aggregation vs hourly scale; 14 features vs 36 features; many-to-one collapse).
3. **Out-of-Sample Generalization:** Reserved strictly for models where scalers, dimensionality reduction, and clusterers were frozen on training data (Pre-Monsoon, Post-Monsoon, and M25).
