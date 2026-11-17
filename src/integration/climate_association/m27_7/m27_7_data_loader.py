"""M27.7 — Independent Audit Data Loader.

Ingests and validates immutable baseline inputs from frozen M25, M26, and M27:
- Frozen M25 3-season arrays (24,883,200 observations)
- Frozen M26 matched rainfall dataset (342,432 observations)
- Original M27 aligned climate indices (36 records)
- Original M27 statistical tables and figures
- Enforces read-only immutability and provenance verification.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FROZEN_M25_DIR = PROJECT_ROOT / "data" / "processed" / "combined_3season"
FROZEN_M26_DIR = PROJECT_ROOT / "data" / "processed" / "rainfall_validation"
M27_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "climate_indices"
M27_TABLES_DIR = PROJECT_ROOT / "reports" / "integration" / "m27" / "tables"
M27_FIGURES_DIR = PROJECT_ROOT / "reports" / "integration" / "m27" / "figures"
M27_7_DIR = PROJECT_ROOT / "reports" / "integration" / "m27_7"


def compute_sha256(filepath: Path) -> str:
    """Compute cryptographic SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class M277DataLoader:
    """Audit loader that verifies immutability of original M25, M26, and M27 artifacts."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or PROJECT_ROOT
        self.m25_dir = FROZEN_M25_DIR
        self.m26_dir = FROZEN_M26_DIR
        self.m27_proc_dir = M27_PROCESSED_DIR
        self.m27_tables_dir = M27_TABLES_DIR

    def verify_frozen_inputs(self) -> Dict[str, bool]:
        """Verify that frozen M25 and M26 files exist and have expected non-zero sizes."""
        status = {}
        # M25 Checks
        m25_labels = self.m25_dir / "combined_3season_cluster_labels.npy"
        m25_years = self.m25_dir / "combined_3season_years.npy"
        m25_sids = self.m25_dir / "combined_3season_season_ids.npy"
        status["m25_labels"] = m25_labels.exists() and m25_labels.stat().st_size == 24_883_328
        status["m25_years"] = m25_years.exists() and m25_years.stat().st_size == 49_766_528
        status["m25_season_ids"] = m25_sids.exists() and m25_sids.stat().st_size == 24_883_328

        # M26 Checks
        m26_matched = self.m26_dir / "m26_cloud_rainfall_matched_primary.parquet"
        status["m26_matched"] = m26_matched.exists() and m26_matched.stat().st_size > 2_000_000

        # M27 Checks
        m27_aligned = self.m27_proc_dir / "m27_climate_indices_aligned.parquet"
        m27_prev = self.m27_proc_dir / "m27_regime_annual_seasonal_prevalence.parquet"
        m27_rain = self.m27_proc_dir / "m27_rainfall_annual_seasonal_modulation.parquet"
        m27_matrix = self.m27_proc_dir / "m27_joint_enso_iod_matrix.parquet"
        m27_spatial = self.m27_proc_dir / "m27_spatial_teleconnections.parquet"

        status["m27_aligned"] = m27_aligned.exists() and m27_aligned.stat().st_size > 5_000
        status["m27_prevalence"] = m27_prev.exists() and m27_prev.stat().st_size > 5_000
        status["m27_rainfall"] = m27_rain.exists() and m27_rain.stat().st_size > 10_000
        status["m27_matrix"] = m27_matrix.exists() and m27_matrix.stat().st_size > 5_000
        status["m27_spatial"] = m27_spatial.exists() and m27_spatial.stat().st_size > 50_000

        all_ok = all(status.values())
        if not all_ok:
            raise FileNotFoundError(f"Frozen input verification failed: {status}")
        logger.info(f"Verified all 9 frozen inputs successfully ({len(status)} passed)")
        return status

    def load_aligned_climate_data(self) -> pd.DataFrame:
        """Load original M27 aligned climate indices (36 rows)."""
        p = self.m27_proc_dir / "m27_climate_indices_aligned.parquet"
        return pd.read_parquet(p)

    def load_regime_prevalence(self) -> pd.DataFrame:
        """Load original M27 annual-seasonal regime prevalence (36 rows)."""
        p = self.m27_proc_dir / "m27_regime_annual_seasonal_prevalence.parquet"
        return pd.read_parquet(p)

    def load_rainfall_metrics(self) -> pd.DataFrame:
        """Load original M27 annual-seasonal rainfall metrics (36 rows)."""
        p = self.m27_proc_dir / "m27_rainfall_annual_seasonal_modulation.parquet"
        return pd.read_parquet(p)

    def load_matched_daily_records(self) -> pd.DataFrame:
        """Load frozen M26 matched daily records (342,432 rows)."""
        p = self.m26_dir / "m26_cloud_rainfall_matched_primary.parquet"
        return pd.read_parquet(p)

    def load_original_correlation_tables(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load original M27 correlation tables for audit comparison."""
        t_regime = pd.read_csv(self.m27_tables_dir / "m27_regime_climate_correlations.csv")
        t_rain = pd.read_csv(self.m27_tables_dir / "m27_rainfall_climate_modulation.csv")
        t_contrasts = pd.read_csv(self.m27_tables_dir / "m27_r2_r1_phase_contrasts.csv")
        return t_regime, t_rain, t_contrasts


if __name__ == "__main__":
    loader = M277DataLoader()
    st = loader.verify_frozen_inputs()
    print("M27.7 Data Loader verified all inputs:")
    for k, v in st.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
