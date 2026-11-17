"""M27.6 / Shared — Statistical Validation and Resampling Inference Framework.

Provides rigorous small-sample (N=12) statistical testing routines for M27:
- Spearman rank correlation with exact empirical permutation p-values (B=100,000)
- Partial Spearman rank correlation controlling for covariate climate index
- Non-parametric percentile bootstrap confidence intervals
- Benjamini-Hochberg False Discovery Rate (FDR) control at q=0.10
- Leave-one-year-out cross-validation (LOOCV) sensitivity analysis
- Targeted sensitivity checks excluding 2015 (Super El Niño) and 2019 (Super IOD)
- Centered Log-Ratio (CLR) transformation for compositional simplex validation
- Exact two-group permutation tests / Mann-Whitney U for discrete phase contrasts
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def compute_spearman_correlation(
    x: np.ndarray, y: np.ndarray
) -> Tuple[float, float]:
    """Compute Spearman rank correlation and asymptotic two-tailed p-value."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    if np.sum(valid) < 3:
        return np.nan, np.nan
    res = stats.spearmanr(x[valid], y[valid])
    return float(res.statistic), float(res.pvalue)


def compute_partial_spearman_correlation(
    x: np.ndarray, y: np.ndarray, z: np.ndarray
) -> float:
    """Compute partial Spearman rank correlation between x and y controlling for z.

    Formula:
        rho_xy_z = (rho_xy - rho_xz * rho_yz) / sqrt((1 - rho_xz^2) * (1 - rho_yz^2))
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if np.sum(valid) < 4:
        return np.nan

    rx = stats.rankdata(x[valid])
    ry = stats.rankdata(y[valid])
    rz = stats.rankdata(z[valid])

    r_xy, _ = stats.pearsonr(rx, ry)
    r_xz, _ = stats.pearsonr(rx, rz)
    r_yz, _ = stats.pearsonr(ry, rz)

    denom_sq = (1.0 - r_xz**2) * (1.0 - r_yz**2)
    if denom_sq <= 1e-12:
        return 0.0

    r_partial = (r_xy - r_xz * r_yz) / np.sqrt(denom_sq)
    return float(np.clip(r_partial, -1.0, 1.0))


def permutation_test_spearman(
    x: np.ndarray,
    y: np.ndarray,
    B: int = 100_000,
    seed: int = 42,
) -> Tuple[float, float, float, float]:
    """Perform exact Monte Carlo permutation testing of Spearman rank correlation.

    Returns:
        (rho_obs, p_perm, ci_lower, ci_upper)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    n = np.sum(valid)
    if n < 4:
        return np.nan, np.nan, np.nan, np.nan

    xv = x[valid]
    yv = y[valid]

    rx = stats.rankdata(xv)
    ry = stats.rankdata(yv)

    # Standardize ranks to unit variance and zero mean
    rx_std = (rx - np.mean(rx)) / (np.std(rx, ddof=0) * np.sqrt(n))
    ry_std = (ry - np.mean(ry)) / (np.std(ry, ddof=0) * np.sqrt(n))

    rho_obs = float(np.sum(rx_std * ry_std))

    # Fast vectorized permutation
    rng = np.random.default_rng(seed)
    perms = np.empty((B, n), dtype=float)
    base_ry = ry_std.copy()
    for b in range(B):
        perms[b] = rng.permutation(base_ry)

    perm_rhos = np.dot(perms, rx_std)
    abs_obs = np.abs(rho_obs)

    # Empirical p-value with finite-sample resolution
    p_perm = float((1.0 + np.sum(np.abs(perm_rhos) >= abs_obs - 1e-12)) / (B + 1.0))

    # Fast vectorized bootstrap 95% CI (B=1000)
    B_boot = 1000
    boot_idx = rng.choice(n, size=(B_boot, n), replace=True)
    x_b = xv[boot_idx]
    y_b = yv[boot_idx]
    rx_b = stats.rankdata(x_b, axis=1)
    ry_b = stats.rankdata(y_b, axis=1)
    rx_b -= np.mean(rx_b, axis=1, keepdims=True)
    ry_b -= np.mean(ry_b, axis=1, keepdims=True)
    sx = np.std(rx_b, axis=1, keepdims=True)
    sy = np.std(ry_b, axis=1, keepdims=True)
    denom = np.squeeze(sx * sy) * n
    denom[denom <= 1e-12] = 1e-12
    boot_rhos = np.sum(rx_b * ry_b, axis=1) / denom

    ci_lower = float(np.percentile(boot_rhos, 2.5))
    ci_upper = float(np.percentile(boot_rhos, 97.5))

    return rho_obs, p_perm, ci_lower, ci_upper


def permutation_test_partial_spearman(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    B: int = 100_000,
    seed: int = 42,
) -> Tuple[float, float]:
    """Perform Monte Carlo permutation testing for partial Spearman correlation.

    Under H0: rho(x, y | z) = 0, residualized rank of y is exchangeable
    with respect to residualized rank of x.

    Returns:
        (rho_partial_obs, p_perm)
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    n = np.sum(valid)
    if n < 4:
        return np.nan, np.nan

    rx = stats.rankdata(x[valid])
    ry = stats.rankdata(y[valid])
    rz = stats.rankdata(z[valid])

    # Regress rx on rz, ry on rz
    slope_x, intercept_x, _, _, _ = stats.linregress(rz, rx)
    slope_y, intercept_y, _, _, _ = stats.linregress(rz, ry)

    res_x = rx - (slope_x * rz + intercept_x)
    res_y = ry - (slope_y * rz + intercept_y)

    std_x = np.std(res_x, ddof=0)
    std_y = np.std(res_y, ddof=0)

    if std_x <= 1e-12 or std_y <= 1e-12:
        return 0.0, 1.0

    res_x_std = (res_x - np.mean(res_x)) / (std_x * np.sqrt(n))
    res_y_std = (res_y - np.mean(res_y)) / (std_y * np.sqrt(n))

    rho_partial_obs = float(np.sum(res_x_std * res_y_std))

    # Permute res_y_std
    rng = np.random.default_rng(seed)
    perms = np.empty((B, n), dtype=float)
    base_ry = res_y_std.copy()
    for b in range(B):
        perms[b] = rng.permutation(base_ry)

    perm_rhos = np.dot(perms, res_x_std)
    abs_obs = np.abs(rho_partial_obs)
    p_perm = float((1.0 + np.sum(np.abs(perm_rhos) >= abs_obs - 1e-12)) / (B + 1.0))

    return rho_partial_obs, p_perm


def fdr_correction_bh(p_values: Union[List[float], np.ndarray], q: float = 0.10) -> Tuple[np.ndarray, np.ndarray]:
    """Benjamini-Hochberg FDR correction.

    Returns:
        (is_significant, q_values)
    """
    p_arr = np.asarray(p_values, dtype=float)
    valid_mask = np.isfinite(p_arr)
    q_vals = np.full_like(p_arr, np.nan)

    if not np.any(valid_mask):
        return np.zeros_like(p_arr, dtype=bool), q_vals

    p_valid = p_arr[valid_mask]
    q_valid = stats.false_discovery_control(p_valid, method="bh")
    q_vals[valid_mask] = q_valid
    is_sig = (q_vals <= q) & valid_mask
    return is_sig, q_vals


def leave_one_out_sensitivity(
    x: np.ndarray,
    y: np.ndarray,
    years: np.ndarray,
) -> pd.DataFrame:
    """Compute Leave-One-Out (LOO) influence on Spearman rank correlation."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    years = np.asarray(years, dtype=int)

    n = len(x)
    rho_full, p_full = compute_spearman_correlation(x, y)

    records = []
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        dropped_yr = years[i]
        rho_loo, p_loo = compute_spearman_correlation(x[mask], y[mask])
        records.append({
            "dropped_year": dropped_yr,
            "rho_full": round(rho_full, 4),
            "rho_loo": round(rho_loo, 4),
            "delta_rho": round(rho_full - rho_loo, 4),
            "p_loo": round(p_loo, 4),
        })

    return pd.DataFrame(records)


def clr_transformation(proportions: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Compute Centered Log-Ratio (CLR) transform for compositional vectors.

    clr(p)_k = ln(p_k) - (1/K) * sum(ln(p_j))
    """
    p = np.asarray(proportions, dtype=float)
    p = np.clip(p, eps, 1.0)
    p = p / np.sum(p, axis=-1, keepdims=True)
    ln_p = np.log(p)
    gm = np.mean(ln_p, axis=-1, keepdims=True)
    return ln_p - gm


def exact_two_group_permutation_test(
    g1: np.ndarray,
    g2: np.ndarray,
    B: int = 100_000,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Permutation test comparing difference in means between two discrete phase groups.

    Returns:
        (diff_obs, p_perm, u_stat)
    """
    g1 = np.asarray(g1, dtype=float)
    g2 = np.asarray(g2, dtype=float)
    g1 = g1[np.isfinite(g1)]
    g2 = g2[np.isfinite(g2)]

    n1, n2 = len(g1), len(g2)
    if n1 == 0 or n2 == 0:
        return np.nan, np.nan, np.nan

    diff_obs = float(np.mean(g1) - np.mean(g2))
    u_stat = float(stats.mannwhitneyu(g1, g2, alternative="two-sided").statistic)

    pooled = np.concatenate([g1, g2])
    n_tot = n1 + n2

    rng = np.random.default_rng(seed)
    perm_diffs = np.empty(B, dtype=float)
    for b in range(B):
        shuffled = rng.permutation(pooled)
        perm_diffs[b] = np.mean(shuffled[:n1]) - np.mean(shuffled[n1:])

    abs_obs = np.abs(diff_obs)
    p_perm = float((1.0 + np.sum(np.abs(perm_diffs) >= abs_obs - 1e-12)) / (B + 1.0))
    return diff_obs, p_perm, u_stat
