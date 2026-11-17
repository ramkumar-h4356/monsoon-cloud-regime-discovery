"""Cross-season research synthesis module.

Aggregates inventory, dataset integrity, missingness baselines, and seasonal
readiness across Pre-monsoon, Established monsoon, and Post-monsoon pipelines.
"""

from pathlib import Path
import json
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUT_DIR = REPORTS_DIR / "integration"


def synthesize_research_status(output_path: Path | None = None) -> dict:
    # Check post-monsoon M19 audit report
    m19_summary_path = REPORTS_DIR / "seasons" / "post_monsoon" / "m19_verification" / "M19_integrity_summary.json"
    m19_status = "NOT_EVALUATED"
    if m19_summary_path.exists():
        with open(m19_summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            m19_status = data.get("overall_readiness", "UNKNOWN")
    
    # Check feature set registry
    reg_path = REPORTS_DIR / "feature_engineering" / "feature_set_registry.csv"
    reg_count = 0
    if reg_path.exists():
        reg_df = pd.read_csv(reg_path)
        reg_count = len(reg_df)
    
    # Check seasonal netcdf files
    seasonal_data_dir = PROJECT_ROOT / "data" / "interim" / "ceres_seasonal"
    pre_count = len(list((seasonal_data_dir / "pre_monsoon").glob("*.nc")))
    est_count = len(list((seasonal_data_dir / "established_monsoon").glob("*.nc")))
    post_count = len(list((seasonal_data_dir / "post_monsoon").glob("*.nc")))

    synthesis = {
        "project": "Satellite Cloud Feature Grouping for Exploratory Weather Pattern Analysis",
        "study_period": "2010-2021",
        "domain": "India (6-38N, 68-98E, 32x30 grid)",
        "datasets": {
            "pre_monsoon_files": pre_count,
            "established_monsoon_files": est_count,
            "post_monsoon_files": post_count,
            "total_seasonal_netcdf": pre_count + est_count + post_count,
            "expected_seasonal_netcdf": 36,
        },
        "feature_registry": {
            "registered_variables": reg_count,
            "expected_candidates": 36,
        },
        "seasonal_milestones": {
            "pre_monsoon": "EDA and IWP investigation complete",
            "established_monsoon": "QC v3, daily aggregation, and rainfall association complete",
            "post_monsoon": f"M19 data integrity audit status: {m19_status}",
        },
        "architecture_status": "CONSOLIDATED_UNIFIED"
    }

    target_file = output_path or (OUTPUT_DIR / "cross_season_synthesis_summary.json")
    try:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(synthesis, f, indent=2)
    except OSError:
        pass

    return synthesis


if __name__ == "__main__":
    result = synthesize_research_status()
    print(json.dumps(result, indent=2))
