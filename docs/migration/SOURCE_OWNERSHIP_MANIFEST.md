# Source Ownership and Migration Manifest

## 1. Worktree Provenance and Relocation Matrix

| Component | Source Workspace | Canonical Path in `monsoon_cloud_research` | Ownership & Justification |
|---|---|---|---|
| **Extraction Tools** | Workspace A | `src/shared/extraction/` | Common extraction from raw CERES multi-month NetCDF subsets. |
| **Validation Utilities** | Workspace A | `src/shared/validation/` | Shared time, product, and spatial metadata validation. |
| **Missingness Engine** | Workspace A | `src/shared/missingness/` | Prefix-ordered `analyze_ceres_missingness.py`, 247-line `missingness_classifier.py`, and `missingness_treatments.py`. |
| **Feature Engineering & Scaling** | Workspace A | `src/shared/feature_engineering/` | Leakage-safe `feature_scaling.py` and `build_feature_set_registry.py`. |
| **Orchestration & Processing** | Workspace A | `src/shared/orchestration/` | M18.6 `experiment_orchestrator.py` and M18.7 `process_m18_7_datasets.py`. |
| **Pre-Monsoon Research** | Workspace A (branch `3b82164`) | `src/seasons/pre_monsoon/` | Pre-monsoon EDA, IWP investigation, and validation scripts extracted from branch package. |
| **Established Monsoon Research** | Workspace C (`monsoon_cloud_friend_review`) | `src/seasons/established_monsoon/` | QC v3, daily aggregation, IMD rainfall preparation, change-point analysis, and within-cell sensitivity suite. |
| **Post-Monsoon Research** | Workspace B (`post_monsoon_research`) | `src/seasons/post_monsoon/` | M19 data integrity audit suite (112 PASS checks) and NetCDF source inspection. |
| **Cross-Season Integration** | New Unified Tier | `src/integration/` | Physical profile comparisons, climate reconciliation, and synthesis without label-invariance assumptions. |
| **Experiment Snapshots** | Workspace A | `archive/experiment_snapshots/` | Preserved `m18_7_colab_package/` and `m18_transfer/`. |
| **Historical Review Packages** | Workspaces A & B | `archive/historical_packages/` | Preserved review package zip files. |

---

## 2. Git and Worktree Preservation

- All three original worktrees (`monsoon_cloud_research`, `post_monsoon_research`, `monsoon_cloud_friend_review`) remain physically preserved on disk.
- Zero Git destructive commands were run (`git reset`, `git clean`, branch deletion).
