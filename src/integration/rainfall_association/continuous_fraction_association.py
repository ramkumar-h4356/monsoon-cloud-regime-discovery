"""
M26 — Continuous Regime Fraction Rainfall Association Module

Analyzes daily rainfall as a continuous function of the soft regime fraction vector:
f = (f0, f1, f2, f3) where sum(fk) = 1.0.

Computes:
1. Spearman rank correlations and partial correlations between rainfall and regime fractions.
2. Decile response curves of rainfall intensity and wet-day probability across convective fractions.
3. Multivariable regression resolving the compositional sum-to-one constraint by referencing
   Regime R3 (thin cirrus) as the baseline category:
   Rainfall = beta_0 + beta_1 * f0 + beta_2 * f1 + beta_3 * f2 + epsilon.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import scipy.stats as stats

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data/processed/rainfall_validation"
TABLES_DIR = ROOT / "reports/integration/m26/tables"

REGIME_LABELS = {
    "f0": "R0: Mixed Convective & Congestus",
    "f1": "R1: Boundary-Layer Shallow Cumulus",
    "f2": "R2: Deep Convective Storm Cores",
    "f3": "R3: Thin Cirrus & Anvil Outflow (Baseline)",
}


def compute_spearman_correlations(df_primary: pd.DataFrame) -> pd.DataFrame:
    """Compute Spearman rank correlations between rainfall and regime fractions."""
    print("--- Computing Spearman Rank Correlations ---")
    rows = []
    
    seasons = ["all_seasons", "pre_monsoon", "established_monsoon", "post_monsoon"]
    fraction_cols = ["frac_r0", "frac_r1", "frac_r2", "frac_r3"]
    
    for s_name in seasons:
        sub = df_primary if s_name == "all_seasons" else df_primary[df_primary["season_name"] == s_name]
        rain = sub["rainfall_mm"].to_numpy(dtype=float)
        
        for f_col in fraction_cols:
            f_vals = sub[f_col].to_numpy(dtype=float)
            r, p = stats.spearmanr(rain, f_vals)
            
            # Parametric Pearson correlation as well
            r_pearson, p_pearson = stats.pearsonr(rain, f_vals)
            
            rows.append({
                "season": s_name,
                "fraction_variable": f_col,
                "regime_name": REGIME_LABELS[f_col.replace("frac_r", "f")],
                "observations": len(rain),
                "spearman_rho": round(float(r), 4),
                "spearman_pvalue": float(p),
                "pearson_r": round(float(r_pearson), 4),
                "pearson_pvalue": float(p_pearson),
            })
            
    df_corr = pd.DataFrame(rows)
    out_file = TABLES_DIR / "m26_continuous_fraction_correlations.csv"
    df_corr.to_csv(out_file, index=False)
    print(f"Saved continuous fraction correlations to: {out_file}")
    return df_corr


def compute_partial_correlations(df_primary: pd.DataFrame) -> pd.DataFrame:
    """
    Compute partial Spearman correlation between rainfall and convective/congestus fractions,
    controlling for other regimes.
    """
    print("--- Computing Partial Spearman Correlations ---")
    rows = []
    
    # We use ranked variables to compute partial correlation via inverted correlation matrix
    for s_name in ["all_seasons", "pre_monsoon", "established_monsoon", "post_monsoon"]:
        sub = df_primary if s_name == "all_seasons" else df_primary[df_primary["season_name"] == s_name]
        
        cols = ["rainfall_mm", "frac_r0", "frac_r1", "frac_r2"]
        sub_ranks = sub[cols].rank()
        cov = sub_ranks.corr(method="pearson").values
        inv_cov = np.linalg.inv(cov)
        
        # Partial correlation between rain (idx 0) and variable j:
        # r_part(0, j | others) = - inv_cov[0, j] / sqrt(inv_cov[0, 0] * inv_cov[j, j])
        for j, col in enumerate(["frac_r0", "frac_r1", "frac_r2"], start=1):
            r_part = -inv_cov[0, j] / np.sqrt(inv_cov[0, 0] * inv_cov[j, j])
            
            rows.append({
                "season": s_name,
                "target_fraction": col,
                "regime_name": REGIME_LABELS[col.replace("frac_r", "f")],
                "controlled_variables": "other 2 non-baseline fractions",
                "partial_spearman_rho": round(float(r_part), 4),
            })
            
    df_part = pd.DataFrame(rows)
    out_file = TABLES_DIR / "m26_partial_spearman_correlations.csv"
    df_part.to_csv(out_file, index=False)
    print(f"Saved partial Spearman correlations to: {out_file}")
    return df_part


def fit_multivariable_regressions(df_primary: pd.DataFrame) -> pd.DataFrame:
    """
    Fit multivariable linear regression of rainfall on continuous fractions:
    Rain = beta_0 + beta_1*f0 + beta_2*f1 + beta_3*f2 + eps (R3 omitted as reference).
    """
    print("--- Fitting Multivariable Compositional Regressions ---")
    rows = []
    
    seasons = ["all_seasons", "pre_monsoon", "established_monsoon", "post_monsoon"]
    
    for s_name in seasons:
        sub = df_primary if s_name == "all_seasons" else df_primary[df_primary["season_name"] == s_name]
        
        y = sub["rainfall_mm"].to_numpy(dtype=float)
        X = sub[["frac_r0", "frac_r1", "frac_r2"]].to_numpy(dtype=float)
        n, p = X.shape
        
        # Add constant
        X_design = np.column_stack([np.ones(n), X])
        
        # OLS fit: beta = (X'X)^-1 X'y
        beta = np.linalg.lstsq(X_design, y, rcond=None)[0]
        residuals = y - X_design @ beta
        rss = float(np.sum(residuals**2))
        tss = float(np.sum((y - np.mean(y))**2))
        r_squared = 1.0 - (rss / tss) if tss > 0 else 0.0
        
        # Variance of coefficients
        df_e = n - (p + 1)
        sigma2 = rss / df_e
        var_beta = sigma2 * np.linalg.inv(X_design.T @ X_design)
        se_beta = np.sqrt(np.diagonal(var_beta))
        t_stats = beta / se_beta
        p_values = 2.0 * (1.0 - stats.t.cdf(np.abs(t_stats), df=df_e))
        
        # Variance Inflation Factor for X
        x_corr = np.corrcoef(X, rowvar=False)
        vifs = np.diagonal(np.linalg.inv(x_corr))
        
        param_names = ["Intercept (Pure R3 Baseline)", "beta_R0 (Mixed Congestus)", "beta_R1 (Shallow Cumulus)", "beta_R2 (Deep Convection)"]
        vif_vals = [np.nan, round(float(vifs[0]), 2), round(float(vifs[1]), 2), round(float(vifs[2]), 2)]
        
        for k_idx in range(len(param_names)):
            rows.append({
                "season": s_name,
                "parameter": param_names[k_idx],
                "coefficient": round(float(beta[k_idx]), 3),
                "std_error": round(float(se_beta[k_idx]), 4),
                "t_statistic": round(float(t_stats[k_idx]), 2),
                "p_value": float(p_values[k_idx]),
                "vif": vif_vals[k_idx],
                "model_r_squared": round(r_squared, 4),
                "observations": n,
            })
            
    df_reg = pd.DataFrame(rows)
    out_file = TABLES_DIR / "m26_continuous_fraction_regressions.csv"
    df_reg.to_csv(out_file, index=False)
    print(f"Saved multivariable regressions to: {out_file}")
    return df_reg


def compute_convective_decile_composites(df_primary: pd.DataFrame) -> pd.DataFrame:
    """Compute rainfall composite statistics binned by convective fraction (f2) levels."""
    print("--- Computing Convective Fraction Decile Composites ---")
    bins = [-0.001, 0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.0]
    bin_labels = ["0% Convective", "0.1-5%", "5-10%", "10-15%", "15-20%", "20-30%", "30-50%", ">50% Convective"]
    
    rows = []
    for s_name in ["all_seasons", "established_monsoon"]:
        sub = df_primary if s_name == "all_seasons" else df_primary[df_primary["season_name"] == s_name]
        
        sub = sub.copy()
        sub["f2_bin"] = pd.cut(sub["frac_r2"], bins=bins, labels=bin_labels)
        
        for b_label, grp in sub.groupby("f2_bin", observed=True):
            rain = grp["rainfall_mm"].to_numpy(dtype=float)
            rain_valid = rain[np.isfinite(rain)]
            
            n = len(rain_valid)
            if n == 0:
                continue
                
            rows.append({
                "season": s_name,
                "convective_fraction_bin": str(b_label),
                "observations": n,
                "mean_rainfall_mm": round(float(np.mean(rain_valid)), 3),
                "median_rainfall_mm": round(float(np.median(rain_valid)), 3),
                "q75_rainfall_mm": round(float(np.quantile(rain_valid, 0.75)), 3),
                "q90_rainfall_mm": round(float(np.quantile(rain_valid, 0.90)), 3),
                "wet_day_25_pct": round(float(np.mean(rain_valid >= 2.5) * 100.0), 2),
                "extreme_exceed_35mm_pct": round(float(np.mean(rain_valid >= 35.5) * 100.0), 2),
            })
            
    df_dec = pd.DataFrame(rows)
    out_file = TABLES_DIR / "m26_convective_decile_composites.csv"
    df_dec.to_csv(out_file, index=False)
    print(f"Saved convective decile composites to: {out_file}")
    return df_dec


def run_continuous_fraction_analysis() -> None:
    """Execute all continuous fraction association routines."""
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    p_path = DATA_DIR / "m26_cloud_rainfall_matched_primary.parquet"
    if not p_path.exists():
        raise FileNotFoundError(f"Primary matched dataset missing: {p_path}")
        
    df_primary = pd.read_parquet(p_path)
    compute_spearman_correlations(df_primary)
    compute_partial_correlations(df_primary)
    fit_multivariable_regressions(df_primary)
    compute_convective_decile_composites(df_primary)


if __name__ == "__main__":
    run_continuous_fraction_analysis()
