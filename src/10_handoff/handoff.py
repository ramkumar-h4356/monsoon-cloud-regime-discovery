"""Additive handoff CLI: verify artifacts, check environment, report or plot.

No command fits models, opens NetCDF arrays or reruns holdout evaluation.
All writes are exclusive and confined to reports/handoff/<output-id>/<command>.
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            value.update(block)
    return value.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        raise ValueError("Run/output IDs must be simple directory names")
    return value


def inside(root, relative):
    target = (Path(root) / relative).resolve()
    if not target.is_relative_to(Path(root).resolve()):
        raise ValueError("Path escapes the repository")
    return target


def run_folder(root, run_id):
    return Path(root) / "reports/phase3/pre_monsoon" / identifier(run_id)


def new_output(root, output_id, command):
    target = Path(root) / "reports/handoff" / identifier(output_id) / command
    target.mkdir(parents=True, exist_ok=False)
    return target


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def verify_artifacts(root, run_id, baseline=None):
    """Read-only verification; file bytes may be hashed, but no arrays are loaded."""
    root = Path(root).resolve()
    run = run_folder(root, run_id)
    frozen = read_json(run / "freeze/frozen.json")
    counts = {}
    cache = {}
    def check(relative, expected):
        path = inside(root, relative)
        if path not in cache:
            cache[path] = digest(path)
        if cache[path] != expected:
            raise ValueError(f"Historical artifact hash mismatch: {relative}")
    for stage in (frozen["config"]["stage1_run_id"], frozen["config"]["stage2_run_id"]):
        path = root / "reports/phase2/pre_monsoon" / stage / "manifest.json"
        manifest = read_json(path)
        for relative, expected in manifest["output_sha256"].items():
            check(relative, expected)
        for relative, expected in manifest.get("code_sha256", {}).items():
            check(relative, expected)
        counts[stage] = len(manifest["output_sha256"])
    # Supplementary Stage 2 results are tied to the signed review receipt.
    phase2 = root / "reports/phase2/pre_monsoon"
    review = read_json(phase2 / "stage2_review_manifest.json")
    for filename, key in (("stage2_review.md", "review_sha256"),
                          ("stage2_v1/manifest.json", "main_run_manifest_sha256"),
                          ("stage2_tsne_sensitivity_v1/manifest.json", "supplementary_manifest_sha256")):
        check(str((phase2 / filename).relative_to(root)), review[key])
    extra = read_json(phase2 / "stage2_tsne_sensitivity_v1/manifest.json")
    for relative, expected in extra["output_sha256"].items():
        check(relative, expected)
    counts["stage2_supplementary"] = len(extra["output_sha256"])
    seal = read_json(run / "freeze/seal.json")
    for name, expected in seal["files"].items():
        check(str((run / "freeze" / name).relative_to(root)), expected)
    for relative, expected in frozen["preserved_files"].items():
        check(relative, expected)
    check(frozen["model_path"], frozen["model_sha256"])
    evaluation = read_json(run / "evaluation_manifest.json")
    for relative, expected in evaluation["output_sha256"].items():
        check(relative, expected)
    completion = read_json(run / "completion_manifest.json")
    for filename, key in (("scientific_report.md", "report_sha256"),
                          ("evaluation_manifest.json", "evaluation_manifest_sha256"),
                          ("verification.json", "verification_sha256"),
                          ("presentation_manifest.json", "presentation_manifest_sha256"),
                          ("freeze/seal.json", "freeze_seal_sha256")):
        check(str((run / filename).relative_to(root)), completion[key])
    check("reports/phase3/pre_monsoon/stage3_all_tests.txt", completion["test_log_sha256"])
    presentation = read_json(run / "presentation_manifest.json")
    check(presentation["output_path"], presentation["output_sha256"])
    check("src/09_visualization/plot_pre_monsoon_stage3_summary.py", presentation["script_sha256"])
    check("src/08_evaluation/build_pre_monsoon_stage3_completion.py", completion["builder_sha256"])
    baseline_count = 0
    if baseline:
        inventory = read_json(inside(root, baseline))
        for relative, expected in inventory["files"].items():
            check(relative, expected)
        baseline_count = len(inventory["files"])
    access = read_json(run / "evaluation/holdout_access_receipt.json")
    if not frozen["created_utc"] < access["created_utc"] < evaluation["created_utc"]:
        raise ValueError("Historical freeze/access ordering is inconsistent")
    if evaluation["refitted"] or evaluation["tuned"]:
        raise ValueError("Unexpected historical refit/tuning flag")
    return dict(status="verified", run_id=run_id, unique_files_hashed=len(cache),
        manifest_result_counts={**counts, "stage3": len(evaluation["output_sha256"])},
        sealed_files=len(seal["files"]), frozen_protected_files=len(frozen["preserved_files"]),
        remediation_baseline_files=baseline_count, model_sha256=frozen["model_sha256"],
        historical_results_unchanged=True, netcdf_arrays_opened=False, model_loaded=False,
        estimators_fitted=False, evaluation_rerun=False,
        qualification="Pre-access freeze covers evaluation/model-analysis code. Later presentation and completion helpers have separate post-evaluation hashes.")


def check_environment(root, lock_path="environment/requirements-windows-py313.lock"):
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    from packaging.version import Version
    lock = inside(root, lock_path)
    pins = {}
    for line in lock.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        if len(list(requirement.specifier)) != 1 or not str(requirement.specifier).startswith("=="):
            raise ValueError("Lock entries must use exact version pins")
        pins[canonicalize_name(requirement.name)] = str(requirement.specifier)[2:]
    installed = {canonicalize_name(d.metadata["Name"]): d for d in metadata.distributions()}
    errors = []
    for name, version in pins.items():
        if name not in installed or installed[name].version != version:
            errors.append(f"Locked distribution mismatch: {name}=={version}")
    # Verify every active dependency of every locked distribution is also pinned
    # and satisfies installed package metadata (including environment markers).
    for name in pins:
        if name not in installed:
            continue
        for text in installed[name].requires or []:
            requirement = Requirement(text)
            if requirement.marker is not None and not requirement.marker.evaluate():
                continue
            dependency = canonicalize_name(requirement.name)
            if dependency not in pins:
                errors.append(f"Unpinned active dependency: {name} -> {requirement}")
            elif dependency in installed and Version(installed[dependency].version) not in requirement.specifier:
                errors.append(f"Unsatisfied dependency: {name} -> {requirement}")
    if (platform.python_version() != "3.13.7" or platform.system() != "Windows"
            or sys.implementation.name != "cpython" or struct.calcsize("P")*8 != 64):
        errors.append("Captured reference platform is 64-bit Windows CPython 3.13.7")
    return dict(status="matched" if not errors else "mismatch", lock_sha256=digest(lock),
        locked_distributions=len(pins), active_dependency_closure_checked=True,
        python=platform.python_version(), platform=platform.platform(), errors=errors,
        limitation="Version lock, not a wheel-hash lock or cross-platform bitwise reproducibility guarantee.")


def test_receipt(path):
    text = Path(path).read_text(encoding="utf-8")
    results = re.findall(r"Ran (\d+) tests in ([\d.]+)s\s+OK", text)
    if not results or re.search(r"^FAILED\s*\(", text, flags=re.MULTILINE):
        raise ValueError("A passing unittest receipt is required")
    count, seconds = results[-1]
    return dict(passed=int(count), seconds=float(seconds), sha256=digest(path))


def markdown_table(frame):
    def cell(value):
        return f"{value:.6f}" if isinstance(value, float) else str(value)
    return "\n".join(["| " + " | ".join(map(str, frame.columns)) + " |",
                       "| " + " | ".join("---" for _ in frame.columns) + " |",
                       *["| " + " | ".join(cell(v) for v in row) + " |" for row in frame.itertuples(index=False, name=None)]])


def report(root, run_id, output_id, test_log=None, baseline=None):
    import pandas as pd
    audit = verify_artifacts(root, run_id, baseline)
    run = run_folder(root, run_id)
    frozen = read_json(run / "freeze/frozen.json")
    selection_path = Path(root) / "reports/phase2/pre_monsoon" / frozen["config"]["stage2_run_id"] / "cluster_selection.csv"
    development = pd.read_csv(selection_path)
    development = development[development.selected].iloc[0]
    metrics = pd.read_csv(run / "evaluation/metrics.csv")
    pooled = metrics[metrics.period == "pooled"].iloc[0]
    tests = test_receipt(inside(root, test_log)) if test_log else None
    output = new_output(root, output_id, "report")
    lines = ["# Final handoff addendum (post-evaluation remediation)", "",
        "This addendum qualifies the historical record without rewriting it. No model, feature definition, "
        "threshold, label, scientific endpoint or holdout result has been changed. No evaluation was rerun.", "",
        "## Freeze scope and scientific limitations", "",
        "The pre-access freeze applies to the evaluation/model-analysis code, approved fitting policy, "
        "parameters, seeds and input expectations. Presentation and completion-report helpers were produced "
        "after evaluation and have separate recorded hashes. The historical completion manifest's broad "
        "`code_frozen_before_holdout` flag must be read with this scope, not as a claim that every later "
        "post-processing script existed before access. The original flag/manifest is preserved.",
        "Phase 1 explored 2010-2021, including holdout availability/correlations that informed feature selection. "
        "This was a reserved Phase 2 fitting/tuning holdout, not historically unseen confirmatory data. "
        "There is no independent meteorological-type validation. K-Means groups remain descriptive, "
        "overlapping cloud-property partitions; expected feature ordering is not independent validation. "
        "Temperature/height are related retrievals; no rain/convection or causal classes are established.", "",
        "## Explicit development/holdout comparison", "", markdown_table(metrics), "",
        f"Pooled silhouette changed by {pooled.silhouette-development.silhouette:+.6f} "
        f"({development.silhouette:.6f} -> {pooled.silhouette:.6f}). "
        f"Calinski-Harabasz changed by {pooled.calinski_harabasz-development.calinski_harabasz:+.6f} "
        f"({development.calinski_harabasz:.6f} -> {pooled.calinski_harabasz:.6f}), also less favorable. "
        f"Davies-Bouldin changed by {pooled.davies_bouldin-development.davies_bouldin:+.6f}, slightly more favorable. "
        "These are descriptive comparisons, not accuracy, equivalence or trend tests. Intervals concern "
        "within-window occurrence, not metric confidence intervals or interannual climate inference.", "",
        "## Requirements supplied in the conversation", "",
        "| Requirement | Status | Evidence/qualification |",
        "| --- | --- | --- |",
        "| PCA variance/loadings and selection | PASS | 57.208201/29.225728/13.566071%; three PCs retained. Actual dimension reduction was not achieved. |",
        "| t-SNE parameter sensitivity/trustworthiness | PASS | 19 recorded experiments; deterministic PCA starts and genuine random-start follow-up distinguished. |",
        "| k selection/three metrics/stability | PASS | k=2 selected from 2-10; median initialization ARI 0.998600, year-bootstrap ARI 0.993410; only five bootstrap fits. |",
        "| Original-unit physical profiles/missingness | PASS | 13 properties; retrieval-valid denominators; no missing water path replaced by zero. |",
        "| Temporal separation/final model | PASS | Fits 2010-2016, development 2017-2018, test 2019-2021; no final refit or tuning. |",
        "| Historically untouched confirmatory test | LIMITED | Prior Phase 1 exposure cannot be undone. |",
        "| Dependency/CLI handoff | REMEDIATED | New parameterized artifact-only CLI; complete installed-distribution version lock; see README.md. |",
        "| Empty support | REMEDIATED PROSPECTIVELY | New robust_diagnostics_v2 API tested on synthetic periods; frozen legacy evaluator is intentionally not patched or rerun. |",
        "| Report consistency/freeze scope | REMEDIATED BY ADDENDUM | CH decrease and post-evaluation helper provenance are explicit here. |",
        "| Independent meteorological-type validation | NOT ESTABLISHED | Not claimed; requires independent evidence. |",
        "No separate external supervisor rubric was available; this maps the PCA, t-SNE, clustering, "
        "reproducibility and reporting requirements actually supplied in the conversation.", "",
        "## Safe use and remaining scope", "",
        "Use the new handoff CLI for verification, reporting, plots and environment checks. It reads existing "
        "artifacts only; it does not load models or NetCDF arrays. Run/output IDs are independent and every "
        "output directory is exclusive. Never invoke old evaluation commands to reproduce this addendum. "
        "The v2 diagnostic API supports all-clear, all-unavailable, empty and one-eligible-row periods without "
        "fabricating statistics; positive-support parity is tested. It is a prospective computation layer, "
        "not a replacement claim for the sealed historical run. Integrating it into a new full scientific "
        "evaluation requires its own version/protocol and approval; do not reuse revealed holdout outcomes "
        "for model selection. No new fitting or holdout selection is part of this remediation.",
        "The lock captures Windows CPython 3.13.7 including transitive installed distributions; it does "
        "not provide wheel hashes, an offline wheelhouse, or cross-platform bitwise guarantees. Scientific "
        "models/data remain outside ordinary Git tracking and must accompany an approved handoff archive. "
        "No Git commit, push or merge is authorized or performed.", "",
        f"Historical verification: {audit['unique_files_hashed']} unique files checked; model SHA256 "
        f"`{audit['model_sha256']}`. Historical artifacts remain unchanged.",
        f"Current remediation test receipt: {tests['passed']} tests passed in {tests['seconds']:.3f}s; "
        f"log SHA256 `{tests['sha256']}`." if tests else "No new test receipt supplied to this report command.", "",
        "## Historical scientific report (verbatim)", "",
        (run / "scientific_report.md").read_text(encoding="utf-8")]
    destination = output / "SCIENTIFIC_HANDOFF.md"
    with destination.open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    receipt = dict(run_id=run_id, post_evaluation_addendum=True, evaluation_code_frozen_before_access=True,
        all_postprocessing_code_frozen_before_access=False, model_refitted=False,
        evaluation_rerun=False, historical_artifacts_unchanged=True, audit=audit, tests=tests,
        source_report_sha256=digest(run / "scientific_report.md"), output_sha256=digest(destination),
        script_sha256=digest(Path(__file__)))
    write_json(output / "manifest.json", receipt)
    return receipt


def plot(root, run_id, output_id):
    verify_artifacts(root, run_id)
    import pandas as pd
    import numpy as np
    os.environ.setdefault("MPLCONFIGDIR", str(Path(root) / "data/processed/handoff/matplotlib_cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    source = run_folder(root, run_id) / "evaluation/bootstrap_intervals.csv"
    rows = pd.read_csv(source)
    rows = rows[rows.primary & rows.endpoint.str.startswith("cloudy_cluster_")]
    if rows.empty:
        raise ValueError("No saved primary occurrence intervals")
    output = new_output(root, output_id, "plot")
    clusters = sorted(rows.endpoint.unique())
    figure, ax = plt.subplots(figsize=(8, 4))
    for i, name in enumerate(clusters):
        group = rows[rows.endpoint == name]
        positions = group.year + (i-(len(clusters)-1)/2)*.08
        color = f"C{i}"
        ax.vlines(positions, group.lower, group.upper, color=color, label=name.replace("cloudy_", "")+" 95% interval")
        ax.scatter(positions, group.estimate, color=color, s=28)
    ax.set_xticks(sorted(rows.year.unique())); ax.set_xlabel("Reserved year")
    ax.set_ylabel("Fraction of eligible cloudy observations")
    ax.set_title("Saved 3-day joint-spatial bootstrap; no new evaluation")
    ax.legend(fontsize=8); figure.tight_layout()
    destination = output / "occurrence_uncertainty.png"
    figure.savefig(destination, dpi=160, bbox_inches="tight"); plt.close(figure)
    receipt = dict(run_id=run_id, source_sha256=digest(source), output_sha256=digest(destination),
                   statistics_changed=False, evaluation_rerun=False, script_sha256=digest(Path(__file__)))
    write_json(output / "manifest.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify", "environment", "report", "plot"):
        command = sub.add_parser(name)
        command.add_argument("--run-id", default="stage3_v1")
        command.add_argument("--output-id", required=name in ("report", "plot"))
        command.add_argument("--baseline")
        if name == "report": command.add_argument("--test-log")
        if name == "environment": command.add_argument("--lock", default="environment/requirements-windows-py313.lock")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.command == "verify":
        result = verify_artifacts(root, args.run_id, args.baseline)
    elif args.command == "environment":
        result = check_environment(root, args.lock)
    elif args.command == "report":
        result = report(root, args.run_id, args.output_id, args.test_log, args.baseline)
    else:
        result = plot(root, args.run_id, args.output_id)
    if args.command in ("verify", "environment") and args.output_id:
        target = new_output(root, args.output_id, args.command)
        write_json(target / "receipt.json", result)
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") != "mismatch" else 1


if __name__ == "__main__":
    raise SystemExit(main())
