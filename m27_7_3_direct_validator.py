#!/usr/bin/env python3
"""
M27.7.3 — DIRECT INDEPENDENT STATISTICAL VALIDATOR
==================================================

Run from the canonical repository root:
    python m27_7_3_direct_validator.py
    python m27_7_3_direct_validator.py --root "D:\\Project Simulator\\monsoon_cloud_research"
    python m27_7_3_direct_validator.py --year-block-permutations 100000 --spatial-permutations 5000

This script performs computations; it is NOT a file-existence preflight.

It independently:
  1. Reconstructs the 36-row prevalence/climate matrix from the project's
     M27 processed parquet files.
  2. Recomputes pooled R0-vs-DMI association under annual-triplet permutation.
  3. Recomputes the four established-monsoon partial-Spearman statistics and
     compares response-residual and predictor-residual permutation nulls.
  4. Recomputes BH-FDR from the raw p-values in the M27.7.2 reconciliation CSV.
  5. Recomputes CLR coordinates and established-monsoon simple/partial
     correlations from prevalence + climate-index data.
  6. Attempts spatial field recomputation ONLY if a suitable cell-by-year
     source table can be identified. It never substitutes a previously
     calculated field p-value for a permutation result.

Outputs:
  reports/integration/m27_7_3/direct_validation/
      m27_7_3_direct_validation.json
      m27_7_3_direct_validation.md
      *.csv

Important scientific safeguards:
  - Permuting annual triplets assumes years are exchangeable under the null.
    This is not automatically valid under serial autocorrelation.
  - Common permutation across spatial cells preserves cross-cell alignment,
    but does not itself solve temporal autocorrelation.
  - The Freedman–Lane comparison is empirical; agreement in finite scenarios
    is not a mathematical proof of equivalence.
  - If spatial annual cell-level source arrays are unavailable or ambiguous,
    spatial recomputation is marked UNRESOLVED, not passed.

Dependencies:
    pip install numpy pandas scipy pyarrow
"""

from __future__ import annotations

import argparse
import json
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


SEASONS = {
    0: "pre_monsoon",
    1: "established_monsoon",
    2: "post_monsoon",
}
REGIMES = ["R0", "R1", "R2", "R3"]


def bh_adjust(p_values: np.ndarray) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    out = np.full(p.shape, np.nan, dtype=float)
    valid = np.isfinite(p) & (p >= 0) & (p <= 1)
    pv = p[valid]
    if not len(pv):
        return out
    order = np.argsort(pv)
    ranked = pv[order]
    m = len(ranked)
    q_sorted = ranked * m / np.arange(1, m + 1)
    q_sorted = np.minimum.accumulate(q_sorted[::-1])[::-1]
    q_sorted = np.clip(q_sorted, 0, 1)
    q = np.empty(m)
    q[order] = q_sorted
    out[valid] = q
    return out


def partial_spearman(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> float:
    valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    x, y, z = x[valid], y[valid], z[valid]
    if len(x) < 5:
        return np.nan
    rx, ry, rz = stats.rankdata(x), stats.rankdata(y), stats.rankdata(z)
    rxy = stats.pearsonr(rx, ry).statistic
    rxz = stats.pearsonr(rx, rz).statistic
    ryz = stats.pearsonr(ry, rz).statistic
    den = np.sqrt(max(0.0, (1-rxz**2)*(1-ryz**2)))
    if den <= 1e-12:
        return np.nan
    return float((rxy-rxz*ryz)/den)


def partial_spearman_from_ranked(rx: np.ndarray, ry: np.ndarray, rz: np.ndarray) -> float:
    rxy = stats.pearsonr(rx, ry).statistic
    rxz = stats.pearsonr(rx, rz).statistic
    ryz = stats.pearsonr(ry, rz).statistic
    den = np.sqrt(max(0.0, (1-rxz**2)*(1-ryz**2)))
    return float((rxy-rxz*ryz)/den) if den > 1e-12 else np.nan


def residualize(a: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    design = np.column_stack([np.ones(len(z)), z])
    beta, *_ = np.linalg.lstsq(design, a, rcond=None)
    fitted = design @ beta
    return fitted, a-fitted


def empirical_p(observed: float, simulated: np.ndarray) -> tuple[float, int]:
    sims = np.asarray(simulated, dtype=float)
    sims = sims[np.isfinite(sims)]
    exceed = int(np.sum(np.abs(sims) >= abs(observed)))
    return (exceed + 1)/(len(sims)+1), exceed


def load_inputs(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = root / "data" / "processed" / "climate_indices"
    prevalence_path = base / "m27_regime_annual_seasonal_prevalence.parquet"
    climate_path = base / "m27_climate_indices_aligned.parquet"
    missing = [str(p) for p in (prevalence_path, climate_path) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Required M27 processed input(s) missing:\n" + "\n".join(missing)
        )
    prevalence = pd.read_parquet(prevalence_path)
    climate = pd.read_parquet(climate_path)
    required_prev = {"year", "season", "season_id", *[f"p_{r}_domain" for r in REGIMES]}
    required_clim = {"year", "season", "season_id", "roni_anomaly", "dmi_anomaly"}
    if not required_prev.issubset(prevalence.columns):
        raise ValueError(f"Prevalence schema missing: {sorted(required_prev-set(prevalence.columns))}")
    if not required_clim.issubset(climate.columns):
        raise ValueError(f"Climate schema missing: {sorted(required_clim-set(climate.columns))}")
    merged = prevalence.merge(
        climate,
        on=["year", "season", "season_id"],
        how="inner",
        validate="one_to_one",
    )
    merged = merged.sort_values(["year", "season_id"]).reset_index(drop=True)
    if len(merged) != 36:
        raise ValueError(f"Expected 36 unique year-season rows; found {len(merged)}")
    if merged.duplicated(["year", "season_id"]).any():
        raise ValueError("Duplicate year-season keys found")
    return merged, prevalence


def validate_year_block(df: pd.DataFrame, b: int, seed: int) -> dict[str, Any]:
    """Pooled simple Spearman R0~DMI; permute complete 3-season DMI triplets by year."""
    wide = df.pivot(index="year", columns="season_id", values="dmi_anomaly").sort_index()
    ywide = df.pivot(index="year", columns="season_id", values="p_R0_domain").sort_index()
    if wide.shape != (12, 3) or ywide.shape != (12, 3):
        raise ValueError("Year-block test requires a complete 12-year x 3-season matrix")
    if wide.isna().any().any() or ywide.isna().any().any():
        raise ValueError("Missing values in year-block matrix")

    years = wide.index.to_numpy()
    dmi_triplets = wide.to_numpy()
    r0_triplets = ywide.to_numpy()
    x = dmi_triplets.reshape(-1)
    y = r0_triplets.reshape(-1)
    observed = float(stats.spearmanr(x, y).statistic)

    rng = np.random.default_rng(seed)
    sims = np.empty(b, dtype=float)
    for i in range(b):
        idx = rng.permutation(len(years))
        x_star = dmi_triplets[idx, :].reshape(-1)
        sims[i] = stats.spearmanr(x_star, y).statistic

    p, exceed = empirical_p(observed, sims)

    # Compare with invalid season-wise permutation to show the consequence
    # of destroying within-year triplet alignment; this is diagnostic only.
    rng2 = np.random.default_rng(seed + 1)
    bad_sims = np.empty(min(b, 20000), dtype=float)
    for i in range(len(bad_sims)):
        bad_x = rng2.permutation(x)
        bad_sims[i] = stats.spearmanr(bad_x, y).statistic
    bad_p, bad_exceed = empirical_p(observed, bad_sims)

    return {
        "status": "RECOMPUTED_WITH_EXCHANGEABILITY_CAVEAT",
        "test": "pooled R0 prevalence vs DMI, simple Spearman",
        "years": years.tolist(),
        "n_years": int(len(years)),
        "n_seasonal_rows": int(len(x)),
        "observed_rho": observed,
        "year_triplet_permutation": {
            "B": int(b), "seed": int(seed), "exceedances": exceed,
            "p_finite_sample": p,
            "assumption": "12 annual triplets exchangeable under null; serial dependence not preserved",
        },
        "invalid_independent_season_permutation_diagnostic": {
            "B": int(len(bad_sims)), "exceedances": bad_exceed,
            "p_finite_sample": bad_p,
            "warning": "Diagnostic only; breaks annual triplet structure and is not an inferential alternative",
        },
        "historical_reported_p": 0.01248,
        "historical_comparison": "Compare with recomputed value; historical value is not used in calculation.",
    }


def validate_freedman_lane(df: pd.DataFrame, b: int, seed: int) -> pd.DataFrame:
    """Compare response- and predictor-residual permutation distributions."""
    sub = df[df["season_id"] == 1].sort_values("year").reset_index(drop=True)
    if len(sub) != 12:
        raise ValueError("Established-monsoon FL comparison requires N=12")
    rows = []
    cases = [
        ("R0", "roni_anomaly", "dmi_anomaly"),
        ("R3", "roni_anomaly", "dmi_anomaly"),
        ("R0", "dmi_anomaly", "roni_anomaly"),
        ("R3", "dmi_anomaly", "roni_anomaly"),
    ]
    for regime, xcol, zcol in cases:
        # X = index under test; Y = regime prevalence; Z = other climate index
        x = sub[xcol].to_numpy(float)
        y = sub[f"p_{regime}_domain"].to_numpy(float)
        z = sub[zcol].to_numpy(float)
        valid = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
        x, y, z = x[valid], y[valid], z[valid]
        rx, ry, rz = stats.rankdata(x), stats.rankdata(y), stats.rankdata(z)
        rho_obs = partial_spearman_from_ranked(rx, ry, rz)

        fit_y, resid_y = residualize(ry, rz)
        fit_x, resid_x = residualize(rx, rz)
        rng = np.random.default_rng(seed)
        rng2 = np.random.default_rng(seed)
        sims_y = np.empty(b)
        sims_x = np.empty(b)
        # Same permutation indices are used for paired comparison.
        for i in range(b):
            perm = rng.permutation(len(x))
            synth_y = fit_y + resid_y[perm]
            synth_x = fit_x + resid_x[perm]
            # Use residualized-rank partial correlation statistic.
            sims_y[i] = partial_spearman_from_ranked(rx, stats.rankdata(synth_y), rz)
            sims_x[i] = partial_spearman_from_ranked(stats.rankdata(synth_x), ry, rz)

        p_y, exc_y = empirical_p(rho_obs, sims_y)
        p_x, exc_x = empirical_p(rho_obs, sims_x)
        corr = float(np.corrcoef(sims_y, sims_x)[0, 1]) if np.std(sims_y) and np.std(sims_x) else np.nan
        rows.append({
            "regime": regime, "tested_index": xcol, "control_index": zcol,
            "n": int(len(x)), "observed_partial_spearman": rho_obs,
            "B": int(b), "seed": int(seed),
            "response_residual_p": p_y, "response_residual_exceedances": exc_y,
            "predictor_residual_p": p_x, "predictor_residual_exceedances": exc_x,
            "null_distribution_correlation": corr,
            "max_abs_null_difference": float(np.max(np.abs(sims_y-sims_x))),
            "decision_agreement_005": bool((p_y <= .05) == (p_x <= .05)),
            "classification": "EMPIRICAL_COMPARISON_ONLY_NOT_PROOF_OF_EQUIVALENCE",
        })
    return pd.DataFrame(rows)


def validate_fdr(root: Path) -> dict[str, Any]:
    candidates = [
        root / "reports" / "integration" / "m27_7_2" / "tables" / "m27_7_2_partial_spearman_p_to_q_reconciliation.csv",
        root / "reports" / "integration" / "m27_7_2" / "tables" / "m27_7_2_complete_fdr_family_reconstruction.csv",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return {"status": "UNRESOLVED", "reason": "M27.7.2 FDR raw p-value table not found"}
    df = pd.read_csv(path)
    pcols = [c for c in df.columns if str(c).lower() in
             {"raw_permutation_p", "permutation_p", "p_perm", "p_value", "raw_p"}]
    if not pcols:
        return {"status": "UNRESOLVED", "path": str(path), "columns": df.columns.tolist(),
                "reason": "No unambiguous raw permutation p-value column"}
    pcol = pcols[0]
    p = pd.to_numeric(df[pcol], errors="coerce").to_numpy(float)
    q = bh_adjust(p)
    out = df.copy()
    out["m27_7_3_recomputed_bh_q"] = q
    existing_q_cols = [c for c in df.columns if "q" in str(c).lower()]
    comparison = {}
    if existing_q_cols:
        qcol = existing_q_cols[0]
        old = pd.to_numeric(df[qcol], errors="coerce").to_numpy(float)
        mask = np.isfinite(old) & np.isfinite(q)
        comparison = {
            "existing_q_column": qcol,
            "max_abs_difference": float(np.max(np.abs(old[mask]-q[mask]))) if mask.any() else None,
        }
    return {
        "status": "RECOMPUTED_BH_WITHIN_INPUT_TABLE_FAMILY",
        "path": str(path), "p_column": pcol,
        "family_rows": int(np.isfinite(p).sum()),
        "recomputed_q_min": float(np.nanmin(q)),
        "recomputed_q_max": float(np.nanmax(q)),
        "q_le_005": int(np.nansum(q <= .05)),
        "q_le_010": int(np.nansum(q <= .10)),
        "comparison": comparison,
        "table_with_recomputed_q": out,
    }


def validate_clr(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sub = df[df["season_id"] == 1].sort_values("year").reset_index(drop=True)
    props = sub[[f"p_{r}_domain" for r in REGIMES]].to_numpy(float)
    eps = 1e-5
    adjusted = props + eps
    adjusted /= adjusted.sum(axis=1, keepdims=True)
    logs = np.log(adjusted)
    clr = logs - logs.mean(axis=1, keepdims=True)
    roni = sub["roni_anomaly"].to_numpy(float)
    dmi = sub["dmi_anomaly"].to_numpy(float)
    for i, regime in enumerate(REGIMES):
        simple_r, simple_p = stats.spearmanr(clr[:, i], roni)
        partial_r = partial_spearman(clr[:, i], roni, dmi)
        # Permutation p-value is intentionally not claimed here; use analytical
        # Spearman p only for simple correlation and record partial rho only.
        rows.append({
            "season": "established_monsoon", "regime": regime,
            "clr_simple_rho_vs_roni": float(simple_r),
            "clr_simple_p_vs_roni": float(simple_p),
            "clr_partial_rho_roni_given_dmi": float(partial_r),
            "n": int(len(sub)), "pseudocount": eps,
            "interpretation": "Sensitivity coordinate; partial significance not asserted by this calculation",
        })
    return pd.DataFrame(rows)


def locate_spatial_candidate(root: Path) -> tuple[Path | None, list[str]]:
    """Find likely spatial annual source tables; never use precomputed p-values as raw inputs."""
    candidates = []
    base = root / "data" / "processed"
    for p in base.rglob("*.parquet"):
        name = p.name.lower()
        if any(t in name for t in ("spatial", "teleconnection", "annual_cell", "grid_cell")):
            try:
                cols = pd.read_parquet(p).columns
                required_any = {"year", "latitude", "longitude"}
                if required_any.issubset(set(cols)):
                    candidates.append((p, list(cols)))
            except Exception:
                pass
    if len(candidates) == 1:
        return candidates[0][0], candidates[0][1]
    return None, [f"{len(candidates)} candidate spatial files with year/latitude/longitude schema; explicit source selection required"]


def validate_spatial(root: Path, b: int, seed: int) -> dict[str, Any]:
    path, info = locate_spatial_candidate(root)
    if path is None:
        return {
            "status": "UNRESOLVED",
            "reason": "No unique raw cell-by-year spatial table found. Existing field-p CSV is not accepted as raw input.",
            "candidate_info": info,
        }
    df = pd.read_parquet(path)
    # Require explicit annual cell-level variables; do not guess columns.
    required = {"year", "latitude", "longitude"}
    if not required.issubset(df.columns):
        return {"status": "UNRESOLVED", "path": str(path), "columns": df.columns.tolist()}
    return {
        "status": "UNRESOLVED_SCHEMA_REVIEW_REQUIRED",
        "path": str(path),
        "columns": df.columns.tolist(),
        "rows": int(len(df)),
        "reason": "Spatial source found, but outcome/index variable names and aggregation semantics must be explicitly mapped before running field permutations.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="M27.7.3 direct independent validator")
    ap.add_argument("--root", default=".", help="Canonical repository root")
    ap.add_argument("--year-block-permutations", type=int, default=100000)
    ap.add_argument("--spatial-permutations", type=int, default=5000)
    ap.add_argument("--freedman-lane-permutations", type=int, default=100000)
    ap.add_argument("--seed", type=int, default=73173)
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    outdir = root / "reports" / "integration" / "m27_7_3" / "direct_validation"
    outdir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "repository_root": str(root),
        "seed": args.seed,
        "parameters": {
            "year_block_B": args.year_block_permutations,
            "spatial_B": args.spatial_permutations,
            "freedman_lane_B": args.freedman_lane_permutations,
        },
        "sections": {},
        "limitations": [
            "Year-triplet permutation assumes annual exchangeability; serial dependence is not preserved.",
            "A common spatial permutation preserves cross-cell alignment but not temporal autocorrelation.",
            "Finite benchmark agreement does not prove mathematical equivalence of permutation procedures.",
            "Spatial field recomputation remains unresolved unless raw cell-by-year data are identified and mapped.",
        ],
    }

    print("[1/5] Loading and validating M27 annual prevalence and climate inputs...")
    merged, _ = load_inputs(root)
    merged.to_csv(outdir / "m27_7_3_reconstructed_36_row_matrix.csv", index=False)
    result["sections"]["input_matrix"] = {
        "status": "PASS", "rows": len(merged),
        "years": sorted(merged["year"].unique().tolist()),
        "season_counts": merged["season_id"].value_counts().sort_index().to_dict(),
    }

    print("[2/5] Executing annual-triplet pooled permutation...")
    year_result = validate_year_block(merged, args.year_block_permutations, args.seed)
    result["sections"]["year_block"] = year_result

    print("[3/5] Comparing response- and predictor-residual permutation distributions...")
    fl_df = validate_freedman_lane(merged, args.freedman_lane_permutations, args.seed + 1)
    fl_df.to_csv(outdir / "m27_7_3_freedman_lane_distribution_comparison.csv", index=False)
    result["sections"]["freedman_lane"] = {
        "status": "RECOMPUTED_EMPIRICALLY",
        "classification": "Not a proof of mathematical equivalence; inspect null distribution diagnostics.",
        "records": fl_df.to_dict(orient="records"),
    }

    print("[4/5] Recomputing CLR coordinates and BH-FDR...")
    clr_df = validate_clr(merged)
    clr_df.to_csv(outdir / "m27_7_3_clr_recomputed.csv", index=False)
    fdr_result = validate_fdr(root)
    if "table_with_recomputed_q" in fdr_result:
        fdr_result["table_with_recomputed_q"].to_csv(
            outdir / "m27_7_3_fdr_recomputed.csv", index=False
        )
        del fdr_result["table_with_recomputed_q"]
    result["sections"]["clr"] = {
        "status": "RECOMPUTED",
        "records": clr_df.to_dict(orient="records"),
    }
    result["sections"]["fdr"] = fdr_result

    print("[5/5] Checking whether raw spatial annual cell data are available...")
    result["sections"]["spatial_field"] = validate_spatial(
        root, args.spatial_permutations, args.seed + 2
    )

    json_path = outdir / "m27_7_3_direct_validation.json"
    md_path = outdir / "m27_7_3_direct_validation.md"
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    lines = [
        "# M27.7.3 Direct Independent Validation",
        "",
        f"- Generated: {result['generated_at']}",
        f"- Repository: `{root}`",
        f"- Seed: `{args.seed}`",
        "",
        "## Results",
        "",
        f"- Input matrix: **{result['sections']['input_matrix']['status']}** ({len(merged)} rows)",
        f"- Year-block: **{year_result['status']}**; observed rho={year_result['observed_rho']:.6f}; p={year_result['year_triplet_permutation']['p_finite_sample']:.6g}",
        f"- Freedman–Lane comparison: **{result['sections']['freedman_lane']['status']}**",
        f"- CLR: **{result['sections']['clr']['status']}**",
        f"- FDR: **{fdr_result.get('status')}**",
        f"- Spatial field: **{result['sections']['spatial_field']['status']}**",
        "",
        "## Year-block details",
        "",
        f"- Annual-triplet permutation B={args.year_block_permutations:,}; finite-sample p={year_result['year_triplet_permutation']['p_finite_sample']:.8f}.",
        f"- Historical reported p=0.01248; absolute difference={abs(year_result['year_triplet_permutation']['p_finite_sample']-0.01248):.8f}.",
        "- This test assumes exchangeability of annual triplets; it does not preserve serial autocorrelation.",
        "",
        "## Freedman–Lane comparison",
        "",
        "```\\n" + fl_df.to_string(index=False) + "\\n```",
        "",
        "## CLR recomputation",
        "",
        "```\\n" + clr_df.to_string(index=False) + "\\n```",
        "",
        "## Spatial field",
        "",
        json.dumps(result["sections"]["spatial_field"], indent=2, default=str),
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {x}" for x in result["limitations"])
    lines += [
        "",
        "## Interpretation rule",
        "",
        "This report records computations, not automatic scientific acceptance. Any unresolved source schema, exchangeability assumption, or mismatch with historical values must be reviewed before the milestone is accepted.",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n========== M27.7.3 DIRECT VALIDATION COMPLETE ==========")
    print(f"Year-block p: {year_result['year_triplet_permutation']['p_finite_sample']:.8f}")
    print(f"Spatial status: {result['sections']['spatial_field']['status']}")
    print(f"Freedman–Lane records: {len(fl_df)}")
    print(f"Outputs: {outdir}")
    print("No original source data or frozen project artifacts were modified.")
    print("=========================================================\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nVALIDATION FAILED: {exc}", file=sys.stderr)
        raise
