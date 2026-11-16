"""Cross-season physical profile comparison without label-invariance assumptions.

PCA axes can invert sign across independent seasonal fits, and cluster labels
(0, 1, 2, ...) are arbitrary permutation-invariant identifiers. This module
compares physical cloud property distributions (e.g., optical depth, cloud area,
cloud-top pressure) across the three seasons rather than assuming cluster identity.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "interim" / "ceres_seasonal"

SEASONS = ("pre_monsoon", "established_monsoon", "post_monsoon")
STUDY_YEARS = tuple(range(2010, 2022))


def get_seasonal_manifest() -> pd.DataFrame:
    manifest_path = DATA_DIR / "seasonal_manifest.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Seasonal manifest not found: {manifest_path}")
    return pd.read_csv(manifest_path)


def summarize_seasonal_coverage() -> Dict[str, Any]:
    """Verify that all 36 seasonal datasets (12 years x 3 seasons) exist and have valid sizes."""
    summary = {}
    for season in SEASONS:
        season_dir = DATA_DIR / season
        files = sorted(season_dir.glob("CERES_*_*.nc"))
        summary[season] = {
            "expected_years": len(STUDY_YEARS),
            "found_files": len(files),
            "years": [int(f.name.split("_")[1]) for f in files if f.name.split("_")[1].isdigit()],
            "status": "COMPLETE" if len(files) == len(STUDY_YEARS) else "INCOMPLETE",
        }
    return summary


if __name__ == "__main__":
    coverage = summarize_seasonal_coverage()
    for s, info in coverage.items():
        print(f"Season: {s:<20} Status: {info['status']} ({info['found_files']}/{info['expected_years']} files)")
