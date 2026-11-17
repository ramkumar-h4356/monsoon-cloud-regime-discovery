# M27.7.2 — Year-Block Dependence and Effective Sample Size Methodological Correction

## 1. Executive Summary
This report resolves the interpretation of the effective sample size ($N_{\text{eff}} \approx 13.47$) derived in M27.7 and verified in M27.7.1.

## 2. Methodological Correction: "13.47 Independent Years" is Rejected
In earlier narrative summaries, the value $13.47$ was occasionally phrased as "13.47 independent years". This phrasing is **scientifically invalid and formally rejected**:
- The observational record contains **exactly 12 calendar years** (2010–2021). A repeated-measures sample cannot contain more independent years than calendar years observed.
- The correct statistical interpretation: The pooled dataset contains $36$ seasonal observations ($12 \text{ years} \times 3 \text{ seasons}$). Due to high intra-year cross-seasonal persistence (mean $\bar{r} = +0.836$), these 36 clustered observations provide approximately as much statistical information as **$13.47$ independent seasonal observations**.

## 3. Variance Inflation Arithmetic
Under Kish's repeated measures cluster design effect:
\[
\text{VIF} = 1 + (k - 1)\bar{r} = 1 + (3 - 1)(0.8363) = 2.6726 \approx 2.673
\]
\[
N_{\text{eff}} = \frac{N_{\text{nominal}}}{\text{VIF}} = \frac{36}{2.6726} = 13.470 \approx 13.47 \text{ effective observations}
\]
The associated degrees of freedom heuristic ($df_{\text{eff}} = N_{\text{eff}} - 2 = 11.47$) is a descriptive summary metric, not an inferentially valid degree of freedom for parametric Student's t or F distributions.

## 4. Year-Block Permutation Verification
To test pooled relationships without assuming independence across seasons within the same year, the Year-Block Permutation Test permutes full 3-season annual triplets together:
- Naive pooled R0 vs DMI: $p_{\text{naive}} = 0.00351, q_{\text{naive}} = 0.01404$ (falsely significant).
- Year-block permutation: $p_{\text{block}} = 0.01248, q_{\text{block}} = 0.24960 > 0.10$ (non-significant).

### Final Recommendation
Season-specific $N=12$ analyses remain the primary basis for seasonal teleconnection inference. All pooled 36-observation analyses are classified as **exploratory descriptive summaries**.
