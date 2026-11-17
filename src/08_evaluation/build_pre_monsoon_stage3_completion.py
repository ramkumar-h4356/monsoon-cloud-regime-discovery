"""Append test/integrity receipts to the immutable evaluation report; no new analysis."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/06_feature_engineering"))
from ceres_features import load_json, sha256
from run_pre_monsoon_stage3 import load_freeze, write_json


def build(root=ROOT, run_id="stage3_v1"):
    root = Path(root).resolve()
    out, folder, frozen = load_freeze(root, run_id)
    evaluation = load_json(out / "evaluation_manifest.json")
    verification = load_json(out / "verification.json")
    presentation = load_json(out / "presentation_manifest.json")
    if evaluation["status"] != "complete" or verification["status"] != "verified":
        raise ValueError("Missing completed evaluation/verification")
    for path, digest in evaluation["output_sha256"].items():
        if sha256(root / path) != digest:
            raise ValueError(f"Result changed: {path}")
    if sha256(root / presentation["output_path"]) != presentation["output_sha256"]:
        raise ValueError("Presentation figure changed")
    for entry in frozen["expected_holdout_inputs"]:
        for kind in ("raw", "prepared"):
            if sha256(root / entry[f"{kind}_path"]) != entry[f"{kind}_sha256"]:
                raise ValueError("Source data changed")
    access = load_json(out / "evaluation/holdout_access_receipt.json")
    if not frozen["created_utc"] < access["created_utc"] < evaluation["created_utc"]:
        raise ValueError("Freeze/access/completion sequence is inconsistent")
    log = root / "reports/phase3/pre_monsoon/stage3_all_tests.txt"
    text = log.read_text(encoding="utf-8")
    match = re.search(r"Ran (\d+) tests in ([\d.]+)s\s+OK", text)
    if match is None or int(match.group(1)) != 25:
        raise ValueError("Full 25-test passing receipt is missing")
    appendix = ["", "## Completed validation and execution record", "",
        f"All {match.group(1)} available tests passed in {match.group(2)} seconds. "
        "Tests use synthetic data for fitting and gate checks; the real Stage 3 evaluation never fits a model.",
        f"Independent verification checked {verification['output_hashes']} result hashes, all "
        f"{verification['sample_predictions']:,} profile-sample predictions, reproducible nested sample IDs, "
        f"training-only distance thresholds, and {verification['annual_files']} reopened label files covering "
        f"{verification['population_rows']:,} original grid-cell hours. All {len(frozen['preserved_files'])} "
        "protected prior artifacts/code/configuration files and the final model are unchanged. "
        "All six holdout raw/prepared source hashes still match Stage 1 expectations.",
        f"Pre-access freeze timestamp: {frozen['created_utc']}; authorized access receipt: {access['created_utc']}. "
        "The immutable freeze and its seal existed before the first real holdout open.",
        "The original evaluation figures/results are retained. A presentation-only uncertainty figure uses "
        "matched categorical colors and integer year ticks; presentation_manifest.json hashes its unchanged "
        "input CSV, plotting script and output image. No statistic, endpoint or model setting changed.",
        "", "Execution commands from the repository root:", "", "```powershell",
        "& '..\\.venv\\Scripts\\python.exe' -B src/08_evaluation/run_pre_monsoon_stage3.py freeze --run-id stage3_v1",
        "& '..\\.venv\\Scripts\\python.exe' -B src/08_evaluation/run_pre_monsoon_stage3.py evaluate --run-id stage3_v1",
        "& '..\\.venv\\Scripts\\python.exe' -B -m unittest discover -s tests -v",
        "& '..\\.venv\\Scripts\\python.exe' -B src/08_evaluation/verify_pre_monsoon_stage3.py --run-id stage3_v1",
        "& '..\\.venv\\Scripts\\python.exe' -B src/09_visualization/plot_pre_monsoon_stage3_summary.py",
        "& '..\\.venv\\Scripts\\python.exe' -B src/08_evaluation/build_pre_monsoon_stage3_completion.py",
        "```", "",
        "The test process stdout/stderr was saved to reports/phase3/pre_monsoon/stage3_all_tests.txt. "
        "Existing run/output paths are refused. Reproduction requires fresh output paths, equivalent source data "
        "and the pinned Stage 2 environment. No dependency upgrade was needed for Stage 3.",
        "", "New source files: config/pre_monsoon_stage3.json; docs/methodology/pre_monsoon_stage3_protocol.md; "
        "src/08_evaluation/{pre_monsoon_stage3_tools,run_pre_monsoon_stage3,verify_pre_monsoon_stage3,"
        "build_pre_monsoon_stage3_completion}.py; src/09_visualization/plot_pre_monsoon_stage3_summary.py; "
        "tests/test_stage3.py. All evaluation/code/configuration changes are new files. "
        "No existing tracked file, Phase 1/Stage 2 artifact or Git history was modified; no commit/push/merge.",
        "", "Artifacts: freeze/ contains the immutable pre-access configuration, feature definitions, selection "
        "evidence and training reference; evaluation/ contains CSVs and the original scientific report; "
        "verification.json and evaluation_manifest.json contain validation/provenance. Figures are in "
        "results/figures/phase3/pre_monsoon/stage3_v1 and stage3_v1_presentation; annual labels are in "
        "data/processed/model_ready/phase3/pre_monsoon/stage3_v1."]
    report = out / "scientific_report.md"
    with report.open("x", encoding="utf-8") as stream:
        stream.write((out / "evaluation/report.md").read_text(encoding="utf-8") + "\n".join(appendix) + "\n")
    receipt = dict(status="complete", tests_passed=25, model_refitted=False, tuned=False,
        code_frozen_before_holdout=True, freeze_seal_sha256=sha256(folder / "seal.json"),
        evaluation_manifest_sha256=sha256(out / "evaluation_manifest.json"),
        verification_sha256=sha256(out / "verification.json"),
        test_log_sha256=sha256(log), report_sha256=sha256(report),
        presentation_manifest_sha256=sha256(out / "presentation_manifest.json"),
        builder_sha256=sha256(Path(__file__)), earlier_artifacts_preserved=True)
    write_json(out / "completion_manifest.json", receipt)
    print(json.dumps(receipt, indent=2))
    return receipt


if __name__ == "__main__":
    build()
