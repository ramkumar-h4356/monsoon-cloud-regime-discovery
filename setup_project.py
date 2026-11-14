
from pathlib import Path

ROOT = Path(__file__).resolve().parent

folders = [
    "data/interim/ceres_extracted",
    "data/interim/imd_subset",
    "data/interim/climate_indices",

    "data/processed/ceres_daily",
    "data/processed/rainfall_daily",
    "data/processed/aligned_datasets",
    "data/processed/model_ready",

    "src/01_inventory",
    "src/02_validation",
    "src/03_extraction",
    "src/04_aggregation",
    "src/05_spatial_alignment",
    "src/06_feature_engineering",
    "src/07_clustering",
    "src/08_evaluation",
    "src/09_visualization",

    "reports/inventory",
    "reports/data_quality",
    "reports/preprocessing",
    "reports/analysis",

    "results/figures",
    "results/tables",
    "results/cluster_profiles",
    "results/models",

    "docs/research_design",
    "docs/methodology",
    "docs/data_dictionary",
    "docs/experiment_logs",

    "config"
]

for folder in folders:
    path = ROOT / folder
    path.mkdir(parents=True, exist_ok=True)
    print("Created/verified:", path.relative_to(ROOT))

print("\nProject directory setup complete.")
