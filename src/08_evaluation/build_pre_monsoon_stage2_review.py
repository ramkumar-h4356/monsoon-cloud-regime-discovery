"""Consolidate completed Stage 2 experiments and test receipts; no data/model fitting."""
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/06_feature_engineering"))
from ceres_features import load_json, sha256


def build(root=ROOT):
    root = Path(root)
    parent = root / "reports/phase2/pre_monsoon"
    base = parent / "stage2_v1"
    extra = parent / "stage2_tsne_sensitivity_v1"
    manifest, supplementary = load_json(base / "manifest.json"), load_json(extra / "manifest.json")
    verification = load_json(parent / "stage2_v1_verification.json")
    assert manifest["status"] == supplementary["status"] == "complete"
    assert verification["status"] == "verified"
    assert not manifest["holdout_accessed"] and not supplementary["holdout_accessed"]
    for receipt in (manifest, supplementary):
        assert all(sha256(root / p) == h for p, h in receipt["output_sha256"].items())
    logs = [parent / "stage2_tests.txt", parent / "stage2_tsne_sensitivity_tests.txt"]
    for path, count in zip(logs, [17, 2]):
        text = path.read_text(encoding="utf-8")
        assert f"Ran {count} tests" in text and text.strip().endswith("OK")
    selection = pd.read_csv(base / "cluster_selection.csv")
    chosen = selection[selection.selected].iloc[0]
    stability = pd.read_csv(extra / "seed_stability.csv")
    quality = pd.read_csv(extra / "tsne_metrics.csv")
    original = pd.read_csv(base / "tsne_metrics.csv")
    sensitivity_summary = stability.groupby("perplexity").neighbor_overlap_mean.agg(["min", "median", "max"])
    mean_trust = quality[quality.name == "random_init"].copy()
    mean_trust["mean_trust"] = mean_trust[[f"trust_scaled_original_{n}" for n in [5, 15, 30]]].mean(axis=1)
    trust_summary = mean_trust.groupby("perplexity").mean_trust.agg(["min", "mean", "max"])
    primary = original[original.tag == "baseline_p30_s42"].iloc[0]
    isolated = quality[quality.name == "controlled_exaggeration"].iloc[0]
    auto = original[original.name == "exaggeration_4"].iloc[0]
    profiles = pd.read_csv(base / "physical_profiles.csv")
    core_profiles = profiles[profiles.variable.isin(["cldarea_total_1h", "cldtau_total_1h", "cldpress_top_total_1h"])]
    report = ["# Consolidated pre-monsoon Stage 2 review", "",
        "Stage 2 is complete. Stage 3 has not started. No real holdout source/prepared NetCDF "
        "was opened, no holdout diagnostic/evaluation was performed, and no Git commit/push/merge was made.",
        "", "## Verification and tests", "",
        "Stage 1 feature/missingness definitions, non-holdout output hashes, split membership and sample IDs "
        "were checked before fitting. The original three features and complete valid cloudy eligibility remain unchanged.",
        f"Tests: 17 main-suite tests plus 2 supplementary tests passed (19 total, across separate runs). "
        "Synthetic tests cover temporal isolation, imputation/scaling statistics, PCA reconstruction, label permutations, "
        "degenerate metrics, whole-year bootstrap, missingness denominators, temporal run boundaries, saved-model "
        "round trips, corrupt inputs, overwrite refusal, and execution without any holdout files.",
        f"Artifact verification checked {verification['stage2_output_hashes']} main outputs, "
        f"{verification['stage2_code_hashes']} recorded source/config hashes and "
        f"{verification['input_files']} permitted input files. Reloaded preprocessing medians/means "
        "match the 70,000 training rows; scaler and PCA fitted-sample counts are exactly 70,000. "
        "All 90,000 saved sample predictions match the reloaded model and saved label files.",
        f"Full-population diagnostics cover {verification['population_rows']:,} grid-cell hours, "
        f"including {verification['population_eligible_rows']:,} eligible cloudy observations, "
        "in nine coordinate-preserving annual label files (2010–2018). Phase 1 and Stage 1 hashes are preserved.",
        "", "## Selected scientific configuration", "",
        "Fit years: 2010–2016; development: 2017–2018. Training sample 70,000; development sample 20,000. "
        "No development-inclusive refit. Median imputation is inert for the complete-case population. "
        "IWP/LWP remain excluded from fitting and are never zero-filled.",
        "PCA variance: 57.208%, 29.226%, 13.566%; two PCs retain only 86.434%. "
        "Three components are retained by the >=95% variance and <=0.25 maximum development feature-RMSE rules. "
        "This is a rotation, not a successful dimensionality reduction. With all three unwhitened PCs, Euclidean "
        "distances and the original standardized-space metrics are equivalent by construction, not independent validation.",
        f"Selected k={int(chosen.k)} from 2–10. Development silhouette={chosen.silhouette:.4f}, "
        f"CH={chosen.calinski_harabasz:.2f}, DB={chosen.davies_bouldin:.4f}; "
        f"negative-silhouette fraction={chosen.negative_silhouette_fraction:.3%}. "
        f"Median initialization ARI={chosen.initialization_ari_median:.4f}; "
        f"whole-year-bootstrap ARI={chosen.sampling_ari_median:.4f}. "
        "k=2 has the strongest development silhouette/CH/DB among the tested candidates. "
        "Single-start initialization stability is weak for several higher k values; all candidate tables remain available.",
        "", "## t-SNE follow-up and limitations", "",
        "The main grid has 12 experiments; seven additional checks examine random starts at perplexities 30/100 "
        "and isolate early exaggeration. The displayed baseline perplexity is 100, selected by mean original-space "
        "trustworthiness across seeds and neighborhoods (0.9927). Trustworthiness uses the same 1,000-point subset "
        "of the fixed 3,000-point visualization sample; it measures local fidelity, not regime validity.",
        "PCA-initialized baseline runs were identical across seeds, with neighborhood overlap 1.0. "
        "This is deterministic repeatability, not evidence of robustness to random starts. Random-start results follow:",
        "", "```text", sensitivity_summary.to_string(), "```", "",
        "The table gives pairwise 15-neighbor-overlap min/median/max on the fixed evaluation subset.",
        "", "```text", trust_summary.to_string(), "```", "",
        "The table gives min/mean/max original-space trustworthiness across random seeds, each averaged over "
        "neighborhoods 5/15/30. Distinct layouts can preserve local neighbors; global island distances/areas remain uninterpretable.",
        f"The original auto-rate exaggeration-4 experiment used learning rate {auto.effective_learning_rate:g}, "
        f"versus {primary.effective_learning_rate:g} at exaggeration 12; it therefore changed both effective settings. "
        f"The added controlled exaggeration-4 run holds learning rate {isolated.learning_rate:g} fixed "
        f"(KL={isolated.kl_divergence:.4f}; baseline same-perplexity KL={primary.kl_divergence:.4f}). "
        "KL is compared here only at identical perplexity/sample; it is not a universal cross-perplexity ranking. "
        "All runs use a finite 1,500-iteration budget; global optimality or convergence beyond this budget is not established. "
        "These checks do not change the chosen PCA dimension or K-Means count.",
        "", "## Physical interpretation", "", "```text",
        core_profiles[["split", "cluster", "variable", "units", "median", "p10", "p90"]].to_string(index=False),
        "```", "",
        "The two broad partitions separate sparse cloud cover with generally higher cloud-top pressure from "
        "extensive cover with lower pressure and larger optical depth. Pressure and optical-depth distributions "
        "overlap substantially. The first group's median pressure changes from about 660 hPa in training to "
        "708 hPa in development, crossing a conventional descriptive pressure bin; names must not be treated "
        "as fixed meteorological types. Pressure is not height above local terrain. Neither group establishes "
        "convection, precipitation, cloud-object morphology or causation.",
        "Profiles are sample quantiles in original units, separately by split; water-path profiles condition on "
        "available retrievals and retain missing denominators. Full occurrence maps/tables are descriptive, not "
        "tests of transfer to unseen geography. UTC diurnal cycles are not local solar time. Clear/unknown states "
        "break persistence runs; no transition bridges a year or seasonal gap. Five bootstrap replicates and "
        "seven fitting years do not provide formal confidence intervals. The analyzed pre-monsoon window is "
        "April 15–May 14, not the entire pre-monsoon calendar season.",
        "", "## Reproduction and artifacts", "",
        "```powershell",
        "& '..\\.venv\\Scripts\\python.exe' -B -m unittest discover -s tests -p 'test_stage[12].py' -v 2>&1 | Set-Content -Encoding utf8 reports/phase2/pre_monsoon/stage2_tests.txt",
        "& '..\\.venv\\Scripts\\python.exe' -B -m unittest discover -s tests -p 'test_stage2_tsne_sensitivity.py' -v 2>&1 | Set-Content -Encoding utf8 reports/phase2/pre_monsoon/stage2_tsne_sensitivity_tests.txt",
        "& '..\\.venv\\Scripts\\python.exe' -B src/07_clustering/run_pre_monsoon_stage2.py --run-id stage2_v1",
        "& '..\\.venv\\Scripts\\python.exe' -B src/08_evaluation/verify_pre_monsoon_stage2.py --run-id stage2_v1",
        "& '..\\.venv\\Scripts\\python.exe' -B src/09_visualization/pre_monsoon_stage2_tsne_sensitivity.py --run-id stage2_tsne_sensitivity_v1",
        "& '..\\.venv\\Scripts\\python.exe' -B src/08_evaluation/build_pre_monsoon_stage2_review.py",
        "```", "",
        "Commands above describe a fresh checkout/data reconstruction. Existing run IDs are intentionally refused. "
        "The actual test logs are stage2_tests.txt (17) and stage2_tsne_sensitivity_tests.txt (2). "
        "requirements-stage2.txt pins the installed packages; configs, scripts and manifests preserve all settings/seeds. "
        "Model artifacts remain season-specific; the shared feature contract is unchanged.",
        "", "Main methodology/results: [stage2_v1/report.md](stage2_v1/report.md). "
        "Baseline tables/metrics are in stage2_v1; random-start/controlled-parameter results in "
        "stage2_tsne_sensitivity_v1. Figures and models are under results/{figures,models}/phase2/pre_monsoon; "
        "annual labels are under data/processed/model_ready/phase2/pre_monsoon/stage2_v1.",
        "", "## Approval boundary", "",
        "Stop here. Before Stage 3, review/freeze the features, k=2 descriptive resolution, PCA retention, "
        "diagnostic scope and interpretation. Obtain explicit approval for a final fit policy and temporal holdout "
        "evaluation. Phase 1 already inspected 2019–2021, so that holdout is not historically unseen. "
        "No Git commit, push, merge, final refit or holdout evaluation is authorized by this report."]
    path = parent / "stage2_review.md"
    with path.open("x", encoding="utf-8") as stream:
        stream.write("\n".join(report) + "\n")
    receipt = dict(status="complete", main_run_manifest_sha256=sha256(base / "manifest.json"),
        supplementary_manifest_sha256=sha256(extra / "manifest.json"),
        review_sha256=sha256(path), review_builder_sha256=sha256(Path(__file__)),
        tests={str(p.relative_to(root)): sha256(p) for p in logs},
        passed_tests=19, holdout_accessed=False)
    with (parent / "stage2_review_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    print(path)
    print(sensitivity_summary.to_string())
    print(trust_summary.to_string())
    return receipt


if __name__ == "__main__":
    build()
