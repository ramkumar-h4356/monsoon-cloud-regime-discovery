"""M27.2 — Climate-Index Loader and Alignment Engine.

Standardizes, validates, and aligns NOAA Relative Oceanic Niño Index (RONI)
and Dipole Mode Index (DMI) with the three 30-day satellite cloud-regime
observation windows for 2010–2021 (36 annual-seasonal observations).

Alignment Protocol:
- Pre-monsoon (April 15 – May 14):
    DMI: April–May simple mean
    RONI: MAM (March–May) canonical quarter
- Established monsoon (July 15 – August 13):
    DMI: July–August simple mean
    RONI: JJA (June–August) canonical quarter
- Post-monsoon (October 15 – November 13):
    DMI: October–November simple mean
    RONI: SON (September–November) canonical quarter

Classification Thresholds:
- ENSO (RONI):
    El Niño: RONI >= +0.50 °C
    Neutral: -0.50 °C < RONI < +0.50 °C
    La Niña: RONI <= -0.50 °C
- IOD (DMI):
    Positive IOD: DMI >= +0.40 °C
    Neutral: -0.40 °C < DMI < +0.40 °C
    Negative IOD: DMI <= -0.40 °C
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "climate_indices"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "climate_indices"
REPORTS_TABLES_DIR = PROJECT_ROOT / "reports" / "integration" / "m27" / "tables"

# Canonical seasonal definitions
SEASON_CONFIG = [
    {
        "season_id": 0,
        "season": "pre_monsoon",
        "window_name": "April 15 - May 14",
        "roni_quarter": "MAM",
        "dmi_months": [4, 5],
        "dmi_label": "04-05",
    },
    {
        "season_id": 1,
        "season": "established_monsoon",
        "window_name": "July 15 - August 13",
        "roni_quarter": "JJA",
        "dmi_months": [7, 8],
        "dmi_label": "07-08",
    },
    {
        "season_id": 2,
        "season": "post_monsoon",
        "window_name": "October 15 - November 13",
        "roni_quarter": "SON",
        "dmi_months": [10, 11],
        "dmi_label": "10-11",
    },
]

ENSO_EL_NINO_THRESH = 0.50
ENSO_LA_NINA_THRESH = -0.50
IOD_POS_THRESH = 0.40
IOD_NEG_THRESH = -0.40


def classify_enso_phase(roni_val: float, threshold: float = ENSO_EL_NINO_THRESH) -> str:
    """Classify ENSO phase based on continuous RONI anomaly."""
    if np.isnan(roni_val):
        return "Unknown"
    if roni_val >= threshold:
        return "El Niño"
    elif roni_val <= -threshold:
        return "La Niña"
    else:
        return "Neutral"


def classify_iod_phase(dmi_val: float, threshold: float = IOD_POS_THRESH) -> str:
    """Classify IOD phase based on continuous DMI anomaly."""
    if np.isnan(dmi_val):
        return "Unknown"
    if dmi_val >= threshold:
        return "Positive IOD"
    elif dmi_val <= -threshold:
        return "Negative IOD"
    else:
        return "Neutral"


class ClimateIndexLoader:
    """Loader and alignment orchestrator for M27 climate teleconnection analysis."""

    def __init__(
        self,
        interim_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        tables_dir: Optional[Path] = None,
    ):
        self.interim_dir = interim_dir or INTERIM_DIR
        self.output_dir = output_dir or PROCESSED_DIR
        self.tables_dir = tables_dir or REPORTS_TABLES_DIR

        self.roni_path = self.interim_dir / "roni_2010_2021.csv"
        self.dmi_path = self.interim_dir / "dmi_2010_2021.csv"

    def load_interim_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load and validate interim RONI and DMI files."""
        if not self.roni_path.exists():
            raise FileNotFoundError(f"Interim RONI file missing: {self.roni_path}")
        if not self.dmi_path.exists():
            raise FileNotFoundError(f"Interim DMI file missing: {self.dmi_path}")

        df_roni = pd.read_csv(self.roni_path)
        df_dmi = pd.read_csv(self.dmi_path)

        # Integrity checks
        if len(df_roni) != 144:
            raise ValueError(f"Expected 144 RONI rows, got {len(df_roni)}")
        if len(df_dmi) != 144:
            raise ValueError(f"Expected 144 DMI rows, got {len(df_dmi)}")

        if df_roni["duplicate"].any():
            raise ValueError("Duplicate rows detected in interim RONI dataset")
        if df_dmi["duplicate"].any():
            raise ValueError("Duplicate rows detected in interim DMI dataset")

        if df_roni["roni_anomaly"].isna().any():
            raise ValueError("NaN values detected in interim RONI anomaly series")
        if df_dmi["dmi_anomaly"].isna().any():
            raise ValueError("NaN values detected in interim DMI anomaly series")

        df_dmi["date"] = pd.to_datetime(df_dmi["date"])
        return df_roni, df_dmi

    def build_aligned_table(self) -> pd.DataFrame:
        """Construct the 36-row standardized annual-seasonal table (2010-2021)."""
        df_roni, df_dmi = self.load_interim_data()
        records: List[Dict[str, Union[int, str, float]]] = []

        for yr in range(2010, 2022):
            for cfg in SEASON_CONFIG:
                s_id = cfg["season_id"]
                s_name = cfg["season"]
                s_win = cfg["window_name"]
                r_qtr = cfg["roni_quarter"]
                d_months = cfg["dmi_months"]
                d_label = cfg["dmi_label"]

                # Extract RONI anomaly
                r_sub = df_roni[(df_roni["year"] == yr) & (df_roni["season"] == r_qtr)]
                if len(r_sub) != 1:
                    raise ValueError(f"Expected 1 RONI record for {yr} {r_qtr}, found {len(r_sub)}")
                roni_val = float(r_sub["roni_anomaly"].iloc[0])

                # Extract DMI anomalies and compute simple mean
                d_sub = df_dmi[(df_dmi["date"].dt.year == yr) & (df_dmi["date"].dt.month.isin(d_months))]
                if len(d_sub) != len(d_months):
                    raise ValueError(f"Expected {len(d_months)} DMI records for {yr} months {d_months}, found {len(d_sub)}")
                dmi_val = float(d_sub["dmi_anomaly"].mean())

                enso_phase = classify_enso_phase(roni_val)
                iod_phase = classify_iod_phase(dmi_val)
                joint_phase = f"{enso_phase} + {iod_phase}"

                records.append({
                    "year": int(yr),
                    "season": str(s_name),
                    "season_id": int(s_id),
                    "season_window": str(s_win),
                    "roni_quarter": str(r_qtr),
                    "roni_anomaly": float(round(roni_val, 4)),
                    "enso_phase": str(enso_phase),
                    "dmi_months": str(d_label),
                    "dmi_anomaly": float(round(dmi_val, 4)),
                    "iod_phase": str(iod_phase),
                    "joint_phase": str(joint_phase),
                    "source_roni": "NOAA CPC RONI.ascii.txt",
                    "source_dmi": "NOAA PSL HadISST1.1 dmi.had.long.csv",
                })

        df_aligned = pd.DataFrame(records)

        # Post-construction validation
        assert len(df_aligned) == 36, f"Expected 36 aligned records, got {len(df_aligned)}"
        assert df_aligned["year"].nunique() == 12, "Expected 12 unique years"
        assert set(df_aligned["season_id"].unique()) == {0, 1, 2}, "Expected season_ids 0, 1, 2"

        return df_aligned

    def export_aligned_table(self) -> Tuple[Path, Path, pd.DataFrame]:
        """Save aligned climate indices table to parquet and CSV."""
        df_aligned = self.build_aligned_table()

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tables_dir.mkdir(parents=True, exist_ok=True)

        parquet_path = self.output_dir / "m27_climate_indices_aligned.parquet"
        csv_path = self.tables_dir / "m27_climate_indices_aligned.csv"

        df_aligned.to_parquet(parquet_path, index=False)
        df_aligned.to_csv(csv_path, index=False)

        logger.info(f"Exported aligned table to {parquet_path} ({parquet_path.stat().st_size} bytes)")
        logger.info(f"Exported aligned table to {csv_path} ({csv_path.stat().st_size} bytes)")

        return parquet_path, csv_path, df_aligned


def get_aligned_climate_indices(reload: bool = False) -> pd.DataFrame:
    """Helper function to load or construct the aligned climate indices table."""
    parquet_path = PROCESSED_DIR / "m27_climate_indices_aligned.parquet"
    if parquet_path.exists() and not reload:
        return pd.read_parquet(parquet_path)
    loader = ClimateIndexLoader()
    _, _, df = loader.export_aligned_table()
    return df


if __name__ == "__main__":
    loader = ClimateIndexLoader()
    p_path, c_path, df = loader.export_aligned_table()
    print("M27.2 Climate Index Alignment Complete:")
    print(df.to_string())
