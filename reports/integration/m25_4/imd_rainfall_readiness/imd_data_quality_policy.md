# M25.4 — IMD Rainfall Data Quality & Missingness Policy

**Milestone:** M25.4  
**Policy Purpose:** Standard Operating Procedures for Missingness, Zero Rainfall, and Aggregation Thresholds  
**Date:** 2026-11-17  

---

## 1. Taxonomy of Data States

To prevent scientific distortion, the following five mutually exclusive observation states must be strictly distinguished in all downstream analyses:

```
+------------------------------------+---------------------------------------------------------------+
| Data State                         | Physical Meaning & Operational Treatment                      |
+------------------------------------+---------------------------------------------------------------+
| 1. Valid Precipitation (> 0 mm)    | Active rainfall recorded by rain-gauge network. Valid depth.  |
| 2. Genuine Zero Rainfall (0.0 mm)  | True meteorological dry day. Valid measurement. Not missing.  |
| 3. Partial Coastal Cell            | Cell with 25% to 75% land coverage. Aggregated with flag.     |
| 4. Ocean Structural Absence        | Marine point outside terrestrial gauge network. Preserved NaN.|
| 5. Foreign Land Absence            | Outside Indian national territory. Preserved NaN.             |
+------------------------------------+---------------------------------------------------------------+
```

---

## 2. Spatial Aggregation Threshold Policy (for 0.25° Data)

When aggregating fine-resolution $0.25^\circ$ rainfall cells into $1.0^\circ$ M25 cells, boundary and coastal cells will exhibit partial land coverage ($1 \le N_{\text{valid}} < 16$). The following tiered policy governs aggregation:

### Tier 1: Full Terrestrial Cells ($F_{\text{cov}} \ge 75\%$, $N_{\text{valid}} \ge 12$)
- **Status:** `FULL_CONFIDENCE_ON_LAND`
- **Action:** Include in all primary rainfall association, composite, and extreme event analyses.
- **Count:** Exactly 328 cells in the M25 domain.

### Tier 2: Coastal & Boundary Cells ($25\% \le F_{\text{cov}} < 75\%$, $4 \le N_{\text{valid}} \le 11$)
- **Status:** `PARTIAL_COASTAL_VALID`
- **Action:** Include in spatial maps and domain totals; include in secondary sensitivity analyses with explicit coastal flagging.
- **Count:** 29 cells in the M25 domain.

### Tier 3: Marginal / Insular Fragments ($F_{\text{cov}} < 25\%$, $1 \le N_{\text{valid}} \le 3$)
- **Status:** `EXCLUDED_INSUFFICIENT_LAND_AREA`
- **Action:** Reject from $1.0^\circ$ rainfall statistics due to high spatial sampling variance. Treated as unrepresentative of the $1^\circ$ box.

### Tier 4: Pure Marine / Foreign Cells ($F_{\text{cov}} = 0\%$, $N_{\text{valid}} = 0$)
- **Status:** `STRUCTURAL_ABSENCE_OCEAN`
- **Action:** Retain as explicit `NaN`. Strictly prohibit filling with zero.

---

## 3. Rules Against Data Corruption

1. **Zero-Filling Prohibition:** Under no circumstances shall ocean cells or unmonitored foreign territories be filled with $0.0\text{ mm}$. Doing so would artificially depress regional mean rainfall and produce spurious associations between marine clouds and extreme drought.
2. **Temporal Duplication Prohibition:** Daily rainfall depths must never be replicated 24 times into hourly slots and analyzed as hourly rain rates.
3. **Outlier Filtering Policy:** Rainfall depths up to $500\text{ mm/day}$ are physically verifiable during monsoonal cloudbursts and depression landfalls (e.g. 2018 Kerala event, max $495.1\text{ mm}$). Values shall not be capped or winsorized without meteorological justification. Values $> 1500\text{ mm/day}$ shall trigger an automated integrity halt.
