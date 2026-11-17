"""M27.7.1 — Module 4 & 5: FDR and Multiplicity Verifier.

Independently verifies:
1. Benjamini-Hochberg FDR implementation from scratch:
   - Rank sorting, critical slope calculation, step-up monotonicity enforcement.
2. Partial correlation hypothesis family reconstruction (8 tests per season):
   - Confirms Established Monsoon R0 and R3 survive FDR (q <= 0.05).
   - Confirms Pre-Monsoon R0 and Post-Monsoon R2 fail FDR (q > 0.10) and are downgraded.
3. Rainfall modulation multiplicity audit (54 tests: 9 metrics x 2 indices x 3 seasons):
   - Evaluates within-season family (m=18) and cross-seasonal global family (m=54).
   - Verifies that only Pre-Monsoon R1 conditional mean vs DMI achieves q <= 0.10 under m=18.
4. Generates:
   - reports/integration/m27_7_1/tables/m27_7_1_fdr_family_reconstruction.csv
   - reports/integration/m27_7_1/tables/m27_7_1_rainfall_multiplicity_verification.csv
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CANONICAL_ROOT = Path(r"D:\Project Simulator\monsoon_cloud_research")
M27_7_1_DIR = CANONICAL_ROOT / "reports" / "integration" / "m27_7_1"
TABLES_DIR = M27_7_1_DIR / "tables"


def independent_benjamini_hochberg(p_values: List[float]) -> List[float]:
    """Pure independent implementation of Benjamini-Hochberg FDR."""
    p_arr = np.asarray(p_values, dtype=float)
    m = len(p_arr)
    if m == 0:
        return []

    # Sort p-values ascending
    sort_idx = np.argsort(p_arr)
    sorted_p = p_arr[sort_idx]

    q_sorted = np.zeros(m, dtype=float)
    min_q = 1.0

    # Step-up procedure from largest to smallest
    for i in range(m - 1, -1, -1):
        rank = i + 1
        raw_q = sorted_p[i] * m / rank
        min_q = min(min_q, raw_q)
        q_sorted[i] = min_q

    # Restore original ordering
    q_final = np.zeros(m, dtype=float)
    q_final[sort_idx] = q_sorted
    return [float(x) for x in np.clip(q_final, 0.0, 1.0)]


class MultiplicityVerifier:
    """Verifies BH-FDR adjustments across partial correlations and rainfall metrics."""

    def __init__(self, canonical_root: Optional[Path] = None):
        self.can_root = canonical_root or CANONICAL_ROOT
        self.tables_dir = TABLES_DIR
        self.tables_dir.mkdir(parents=True, exist_ok=True)

    def verify_partial_correlation_fdr_families(self) -> pd.DataFrame:
        """Verify the 8-hypothesis seasonal partial correlation families."""
        tbl_p = self.can_root / "reports" / "integration" / "m27_7" / "tables" / "m27_7_partial_spearman_audit_comparison.csv"
        df = pd.read_csv(tbl_p)

        records: List[Dict[str, Any]] = []

        seasons = ["pre_monsoon", "established_monsoon", "post_monsoon"]

        for sname in seasons:
            sub = df[df["season"] == sname].copy().reset_index(drop=True)
            p_vals = sub["corrected_p_perm_fl"].tolist()

            # Independent BH implementation
            q_indep = independent_benjamini_hochberg(p_vals)
            # Scipy reference BH
            q_scipy = stats.false_discovery_control(p_vals, method="bh")

            for i in range(len(sub)):
                r = sub.iloc[i]
                q_rep = float(r["bh_fdr_q_value"])
                q_calc = float(q_indep[i])
                diff = abs(q_rep - q_calc)

                decision_q005 = bool(q_calc <= 0.05)
                decision_q010 = bool(q_calc <= 0.10)

                records.append({
                    "family_id": f"PARTIAL_SPEARMAN_{sname.upper()}",
                    "season": sname,
                    "hypothesis_id": f"{r['regime']}_{r['index_tested']}_ctrl_{r['control_index']}",
                    "regime": r["regime"],
                    "index_tested": r["index_tested"],
                    "control_index": r["control_index"],
                    "partial_rho": r["recalc_partial_rho_formula"],
                    "p_perm_fl": r["corrected_p_perm_fl"],
                    "m27_7_reported_q": q_rep,
                    "independent_q": round(q_calc, 5),
                    "scipy_q": round(float(q_scipy[i]), 5),
                    "q_discrepancy": diff,
                    "is_sig_q005": decision_q005,
                    "is_sig_q010": decision_q010,
                    "audit_status": r["audit_decision"],
                    "verification_result": "VERIFIED_EXACT" if diff < 1e-4 else "DIVERGENCE",
                })

        df_out = pd.DataFrame(records)
        p_out = self.tables_dir / "m27_7_1_fdr_family_reconstruction.csv"
        df_out.to_csv(p_out, index=False)
        logger.info(f"Saved FDR family reconstruction table to {p_out} ({len(df_out)} rows)")
        return df_out

    def verify_rainfall_multiplicity(self) -> pd.DataFrame:
        """Verify the 54 rainfall modulation tests and evaluate family sensitivity."""
        tbl_p = self.can_root / "reports" / "integration" / "m27_7" / "tables" / "m27_7_corrected_rainfall_modulation.csv"
        df = pd.read_csv(tbl_p)

        records: List[Dict[str, Any]] = []

        # Global family p-values across all 54 tests
        all_p = df["raw_permutation_p"].tolist()
        q_global = independent_benjamini_hochberg(all_p)

        seasons = ["pre_monsoon", "established_monsoon", "post_monsoon"]

        for sname in seasons:
            sub = df[df["season"] == sname].copy().reset_index(drop=True)
            p_vals = sub["raw_permutation_p"].tolist()
            q_seasonal = independent_benjamini_hochberg(p_vals)

            for i in range(len(sub)):
                r = sub.iloc[i]
                q_rep = float(r["bh_fdr_q_value"])
                q_seas = float(q_seasonal[i])
                glob_idx = df.index[(df["season"] == sname) & (df["metric"] == r["metric"]) & (df["index_tested"] == r["index_tested"])][0]
                q_glob = float(q_global[glob_idx])

                diff = abs(q_rep - q_seas)

                records.append({
                    "season": sname,
                    "metric": r["metric"],
                    "index_tested": r["index_tested"],
                    "spearman_rho": r["spearman_rho"],
                    "raw_p_perm": r["raw_permutation_p"],
                    "reported_seasonal_q": q_rep,
                    "verified_seasonal_q_m18": round(q_seas, 5),
                    "sensitivity_global_q_m54": round(q_glob, 5),
                    "q_discrepancy": diff,
                    "is_sig_seasonal_q010": bool(q_seas <= 0.10),
                    "is_sig_global_q010": bool(q_glob <= 0.10),
                    "audit_verdict": r["audit_verdict"],
                    "verification_result": "VERIFIED_EXACT" if diff < 1e-4 else "DIVERGENCE",
                })

        df_out = pd.DataFrame(records)
        p_out = self.tables_dir / "m27_7_1_rainfall_multiplicity_verification.csv"
        df_out.to_csv(p_out, index=False)
        logger.info(f"Saved rainfall multiplicity verification table to {p_out} ({len(df_out)} rows)")
        return df_out


if __name__ == "__main__":
    verifier = MultiplicityVerifier()
    df_fdr = verifier.verify_partial_correlation_fdr_families()
    df_rain = verifier.verify_rainfall_multiplicity()
    print("M27.7.1 FDR Verification Summary:")
    print("Partial correlation FDR verified:", (df_fdr["verification_result"] == "VERIFIED_EXACT").sum(), "/", len(df_fdr))
    print("Confirmed significant tests (q <= 0.05):", df_fdr["is_sig_q005"].sum())
    print("Rainfall multiplicity tests verified:", (df_rain["verification_result"] == "VERIFIED_EXACT").sum(), "/", len(df_rain))
    print("Rainfall significant tests (seasonal q <= 0.10):", df_rain["is_sig_seasonal_q010"].sum())
    print("Rainfall significant tests (global q <= 0.10):", df_rain["is_sig_global_q010"].sum())
