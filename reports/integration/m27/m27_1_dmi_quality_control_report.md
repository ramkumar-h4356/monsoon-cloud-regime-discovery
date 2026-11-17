# M27.1 — NOAA DMI Quality-Control and Statistical Audit Report

**Milestone:** M27.1 — NOAA RONI and DMI Climate-Index Audit and Repository Integration Planning  
**Evaluation Date:** 2026-11-17  
**Auditor:** Senior Atmospheric Data Scientist & Statistical Reviewer  
**Target Dataset:** NOAA Dipole Mode Index (`raw_data/NOAA_DMI/dmi.had.long.csv` & `data/interim/climate_indices/dmi_2010_2021.csv`)  

---

## 1. Executive Summary

A comprehensive quality-control audit of the NOAA Dipole Mode Index (DMI) derived from the HadISST1.1 sea surface temperature reconstruction was conducted. The audit verified raw source metadata, missing-value sentinel handling, sequence completeness, distributional properties, and temporal autocorrelation across the 2010–2021 study period.

The dataset is verified to contain **exactly 144 monthly observations** spanning the complete 12-year research baseline with zero missing values, zero duplicates, and exact month-start date stamps.

---

## 2. Dataset Structure and Sentinel Handling

### 2.1 File Characteristics & Provenance
* **Raw Source Path:** `raw_data/NOAA_DMI/dmi.had.long.csv` (SHA256: `6f5772b234fa...`, 39,650 bytes).
* **Interim Path:** `data/interim/climate_indices/dmi_2010_2021.csv` (SHA256: `ec773e3fe6ae...`, 3,519 bytes).
* **Verification Parity:** 100% numerical and categorical match. Maximum absolute difference between raw and interim values across all 144 study records is **$0.000000^\circ\text{C}$**.
* **Total Raw History:** 1,884 monthly records spanning January 1870 (`1870-01-01`) through December 2026 (`2026-12-01`).
* **Missing Value Sentinel Handling:**
  * Raw file metadata states: `Date, DMI HadISST1.1  missing value -9999 https://psl.noaa.gov/data/timeseries/month/`.
  * The sentinel `-9999.000` appears only in lines 1881–1885 (August to December 2026), outside the historical period.
  * Within the 2010–2021 study period, **zero `-9999` sentinels occur**.
* **Study Scope (2010–2021):** Exactly 144 monthly records ($12\text{ years} \times 12\text{ calendar months}$).
* **Duplicate Record Count:** Exactly 0 duplicate dates. Every date is formatted as `YYYY-MM-01`.

---

## 3. Distributional Statistics (2010–2021 Study Period)

| Statistic | Value ($^\circ\text{C}$) | Notes / Interpretation |
| :--- | :---: | :--- |
| **Observation Count ($N$)** | 144 | 12 calendar months $\times$ 12 study years |
| **Mean** | $+0.087$ | Near-neutral baseline with slight positive mean |
| **Standard Deviation** | $0.308$ | Characteristic monthly IOD anomaly amplitude |
| **Median** | $+0.054$ | Typical non-event background condition |
| **Minimum** | $-0.757$ | July 2016 (Strong Negative IOD event) |
| **25th Percentile ($Q_{25}$)** | $-0.103$ | Weakly negative / neutral boundary |
| **75th Percentile ($Q_{75}$)** | $+0.294$ | Weakly positive / neutral boundary |
| **Maximum** | $+0.964$ | October 2019 (Historic Super Positive IOD event) |
| **Range** | $1.721$ | Full amplitude spanning historic positive and negative extremes |

### 3.1 Monthly Phase Classification ($N=144$, Threshold $\pm 0.40^\circ\text{C}$)
* **Positive IOD Months ($\text{DMI} \ge +0.40^\circ\text{C}$):** 22 months ($15.28\%$).
* **Neutral IOD Months ($-0.40^\circ\text{C} < \text{DMI} < +0.40^\circ\text{C}$):** 114 months ($79.17\%$).
* **Negative IOD Months ($\text{DMI} \le -0.40^\circ\text{C}$):** 8 months ($5.56\%$).

---

## 4. Seasonal Cycle and Autocorrelation Structure of DMI

### 4.1 Physical Seasonality of the Dipole Mode Index
Unlike ENSO in the Pacific (which exhibits multiannual persistence), the Indian Ocean Dipole possesses an intrinsically locked annual cycle governed by the seasonal reversal of the Indian monsoon winds:
1. **Inception Phase (May–June):** Thermocline anomalies begin developing along the Sumatra/Java coast.
2. **Development Phase (July–August):** Zonal wind anomalies intensify; the cross-basin SST gradient widens.
3. **Peak Phase (September–November):** Dipole achieves maximum amplitude and atmospheric coupling (SON).
4. **Dissipation Phase (December–January):** The arrival of the northwest monsoon rapidly deepens the thermocline in the eastern basin, collapsing the dipole.

### 4.2 Serial Correlation & Independence
* **Lag-1 Autocorrelation ($r_{\text{lag-1}}$):** **$r = 0.7496$** ($p < 10^{-26}$).
* **Lag-2 Autocorrelation ($r_{\text{lag-2}}$):** **$r = 0.4632$** ($p < 10^{-8}$).
* **Lag-6 Autocorrelation ($r_{\text{lag-6}}$):** **$r = -0.0652$** (statistically indistinguishable from zero, reflecting annual reset).

### 4.3 Scientific Implication for Milestone M27
Because the IOD peaks in boreal autumn (September–November) and is weak or inactive during pre-monsoon (April–May):
* **Pre-Monsoon (Apr 15–May 14):** DMI exhibits minimal active dipole dynamics ($\text{mean } = +0.076^\circ\text{C}$, $\text{std } = 0.25^\circ\text{C}$).
* **Established Monsoon (Jul 15–Aug 13):** DMI reflects the developing dipole state ($\text{std } = 0.38^\circ\text{C}$).
* **Post-Monsoon (Oct 15–Nov 13):** DMI captures the peak mature dipole state ($\text{std } = 0.39^\circ\text{C}$, maximum variance and teleconnection potential).
* **Sampling Rule for M27:** For each seasonal sampling window across the 12 years, M27 must use a single representative 2-month average (or window-weighted average), yielding **$N = 12$ independent seasonal observations**.

---

## 5. Major Historical IOD Events Captured in 2010–2021

The 12-year study window captures the two strongest and most prominent IOD events in modern satellite records:
1. **The 2019 "Super" Positive IOD:**
   * One of the most intense positive IOD events on record.
   * Monthly values: August $= +0.516^\circ\text{C}$, September $= +0.946^\circ\text{C}$, October $= +0.964^\circ\text{C}$, November $= +0.835^\circ\text{C}$.
   * Post-monsoon average (Oct–Nov): **$+0.900^\circ\text{C}$**.
2. **The 2016 Strong Negative IOD:**
   * Pronounced cool western / warm eastern dipole following the 2015 El Niño.
   * Monthly values: June $= -0.443^\circ\text{C}$, July $= -0.757^\circ\text{C}$, August $= -0.442^\circ\text{C}$, September $= -0.584^\circ\text{C}$, October $= -0.428^\circ\text{C}$.
   * Established monsoon average (Jul–Aug): **$-0.600^\circ\text{C}$**.
3. **The 2015 Co-occurring Positive IOD:**
   * Accompanied the 2015 Super El Niño: July $= +0.468^\circ\text{C}$, August $= +0.323^\circ\text{C}$, October $= +0.485^\circ\text{C}$, November $= +0.342^\circ\text{C}$.

---

## 6. Audit Verdict

$$\mathbf{VERDICT:}\quad \textbf{VERIFIED — DMI DATASET FULLY AUDITED AND METHODOLOGICALLY QUALIFIED}$$
