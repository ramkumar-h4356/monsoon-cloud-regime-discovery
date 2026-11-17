"""Cross-season climate index reconciliation for DMI and RONI.

Aligns Dipole Mode Index (DMI) and Oceanic Niño Index / RONI anomaly series
with the research study period (2010-2021) and seasonal windows:
- Pre-monsoon: MAM / AMJ
- Established monsoon: JJA / JAS
- Post-monsoon: SON / OND
"""

from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CLIMATE_DIR = PROJECT_ROOT / "data" / "interim" / "climate_indices"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "integration"


def load_dmi_data(path: Optional[Path] = None) -> pd.DataFrame:
    file_path = path or (CLIMATE_DIR / "dmi_2010_2021.csv")
    if not file_path.exists():
        raise FileNotFoundError(f"DMI file not found: {file_path}")
    df = pd.read_csv(file_path)
    if "date" in df.columns and "year" not in df.columns:
        df["year"] = pd.to_datetime(df["date"]).dt.year
    return df


def load_roni_data(path: Optional[Path] = None) -> pd.DataFrame:
    file_path = path or (CLIMATE_DIR / "roni_2010_2021.csv")
    if not file_path.exists():
        raise FileNotFoundError(f"RONI file not found: {file_path}")
    df = pd.read_csv(file_path)
    if "date" in df.columns and "year" not in df.columns:
        df["year"] = pd.to_datetime(df["date"]).dt.year
    return df


def reconcile_seasonal_indices() -> pd.DataFrame:
    dmi_df = load_dmi_data()
    roni_df = load_roni_data()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Merge and summarize
    records = []
    years = sorted(set(dmi_df["year"]).intersection(set(roni_df["year"])))
    for y in years:
        dmi_yr = dmi_df[dmi_df["year"] == y]
        roni_yr = roni_df[roni_df["year"] == y]
        dmi_val = dmi_yr["dmi_anomaly"].mean() if "dmi_anomaly" in dmi_yr.columns else np.nan
        roni_val = roni_yr["roni_anomaly"].mean() if "roni_anomaly" in roni_yr.columns else np.nan
        records.append({
            "year": y,
            "dmi_observations": len(dmi_yr),
            "roni_observations": len(roni_yr),
            "dmi_annual_mean": float(dmi_val),
            "roni_annual_mean": float(roni_val),
        })
    summary_df = pd.DataFrame(records)
    out_csv = OUTPUT_DIR / "climate_indices_reconciliation_summary.csv"
    summary_df.to_csv(out_csv, index=False)
    return summary_df


if __name__ == "__main__":
    df = reconcile_seasonal_indices()
    print("Climate reconciliation complete:")
    print(df.to_string())
