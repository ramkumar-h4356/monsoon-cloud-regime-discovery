# M27.7 — Figure Consistency, Labeling Integrity, and Corrected Visualizations

## 1. Comprehensive Audit of Original M27 Figures (fig01–fig10)

Each of the 10 original figures in `reports/integration/m27/figures/` was systematically evaluated for scientific precision, visual clarity, and labeling accuracy:

| Figure ID | Original Figure Name | Audit Evaluation | Status | Corrections Identified |
| :--- | :--- | :--- | :--- | :--- |
| **fig01** | `fig01_annual_roni_dmi_timeseries.png` | Time series of RONI and DMI anomalies. Clearly labeled quarterly and monthly values. | **PASS** | Fully compliant. |
| **fig02** | `fig02_annual_seasonal_alignment_matrix.png` | Phase alignment heatmaps across 12 years and 3 seasons. Accurate season-window alignment. | **PASS** | Fully compliant. |
| **fig03** | `fig03_regime_prevalence_vs_climate_indices.png` | Scatter plots with Spearman rho annotations. | **PASS WITH NOTE** | Annotated p-values are unadjusted for multiplicity. |
| **fig04** | `fig04_partial_rank_correlations.png` | Horizontal bar charts of partial Spearman rank correlations. | **CORRECTION REQUIRED** | Displayed unadjusted p-values and asterisks. Lacked FDR q-value distinctions; gave equal visual weight to non-surviving tests. |
| **fig05** | `fig05_seasonal_rainfall_vs_climate_indices.png` | Rainfall metrics vs RONI and DMI. | **PASS WITH NOTE** | Multiplicity caveats required in caption. |
| **fig06** | `fig06_regime_conditional_rainfall_response.png` | Bar charts of conditional rainfall by phase. | **CORRECTION REQUIRED** | Highlighted 91.1% difference in post-monsoon R2 without displaying sample sizes ($N_1=2, N_2=6$) or permutation p-value ($p=0.212$). |
| **fig07** | `fig07_enso_phase_composite_maps.png` | Spatial composite anomaly maps of rainfall and regime fractions. | **CORRECTION REQUIRED** | Claimed continental field significance based on naive binomial test ($p=0.00002$), which fails Livezey-Chen spatial permutation. |
| **fig08** | `fig08_iod_phase_composite_maps.png` | Spatial composite anomaly maps for IOD phases. | **PASS** | Accurately depicts confirmed pre-monsoon R2 suppression. |
| **fig09** | `fig09_joint_enso_iod_phase_matrix.png` | 3×3 heatmaps of rainfall and regime prevalence. | **PASS WITH NOTE** | Lacks prominent visual flagging of empty ($N=0$) and single-year ($N=1$) cells. |
| **fig10** | `fig10_sensitivity_loocv_diagnostics.png` | Leave-One-Out Cross-Validation stability plots. | **PASS** | Excellent validation of rank stability across 12 years. |

---

## 2. Specification of Corrected Publication Figures (300 DPI)

Four corrected figures were generated under `reports/integration/m27_7/figures/`:

1. **`fig04_corrected_partial_rank_correlations.png` (323 KB):**
   - Incorporates exact Benjamini-Hochberg FDR $q$-values for all partial correlations.
   - Visually partitions associations into Confirmed Significant ($q \le 0.05$, green), Exploratory Tendency ($p \le 0.05, q > 0.05$, gold), and Non-Significant ($p > 0.05$, purple).
   - Clearly highlights that only Established Monsoon R0 and R3 survive FDR control.
2. **`fig06_corrected_regime_conditional_rainfall.png` (247 KB):**
   - Explicitly annotates sample sizes ($N_1 = 2$ El Niño vs $N_2 = 6$ La Niña).
   - Annotates exact permutation p-values ($p = 0.212$ for R2, $p = 0.456$ for mean rain).
   - Reframes the post-monsoon contrast as an underpowered descriptive difference, disclaiming any established causal teleconnection.
3. **`fig07_corrected_spatial_field_significance.png` (372 KB):**
   - Contrasts the naive binomial 5% threshold (16.4 cells) with the empirical Livezey-Chen 95th percentile null threshold (36–42 cells).
   - Shows why Established Monsoon Rainfall vs RONI ($K=35$, $p_{{\text{{LC}}}} = 0.072$) fails field significance, while Pre-Monsoon R2 Convection vs DMI ($K=78$, $p_{{\text{{LC}}}} = 0.020$) is robustly confirmed.
4. **`fig08_year_dependence_diagnostics.png` (285 KB):**
   - Visualizes intra-year cross-seasonal persistence ($r_{{\text{{mean}}}} = 0.836$ for R0).
   - Plots the resulting effective sample size ($N_{{\text{{eff}}}} = 13.5$) and illustrates the substantial inflation in p-values under year-block permutation.
