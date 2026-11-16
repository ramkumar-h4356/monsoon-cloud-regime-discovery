import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = PROJECT_ROOT / "src" / "06_feature_engineering"
sys.path.insert(0, str(MODULE_DIR))

from experiment_orchestrator import (
    build_experiment_specs,
    create_experiment_registry,
    load_feature_registry,
    update_run_status,
    write_experiment_outputs,
)


CONFIG = {
    "expected_feature_counts": {
        "FS-A": 6, "FS-B": 4, "FS-C": 4,
        "FS-D": 4, "FS-E": 3, "FS-F": 4,
    },
    "stage_a": {
        "feature_sets": ["FS-A", "FS-B", "FS-C", "FS-D", "FS-E", "FS-F"],
        "property_treatment": "SA-A",
        "cloud_area_treatment": "CA-A",
        "scaler": "robust",
        "weighting": "equal",
    },
    "stage_b": {
        "feature_sets": ["FS-A", "FS-B", "FS-C", "FS-D", "FS-E", "FS-F"],
        "variants": [
            {"property_treatment": "MD-B", "cloud_area_treatment": "CA-A", "purpose": "md_b"},
            {"property_treatment": "SA-B", "cloud_area_treatment": "CA-A", "purpose": "sa_b"},
            {"property_treatment": "SA-A", "cloud_area_treatment": "CA-B", "purpose": "ca_b"},
        ],
    },
    "stage_c": {
        "shortlisted_feature_sets": [],
        "variants": [
            {"scaler": "standard", "weighting": "equal", "purpose": "standard"},
            {"scaler": "robust", "weighting": "family_balanced", "purpose": "family"},
        ],
    },
    "validation_policy": {"year_blocked": True},
    "execution_policy": {"staged_not_full_factorial": True},
}


def make_registry(path):
    rows = []
    memberships = {
        "FS-A": set(range(6)),
        "FS-B": set(range(4)),
        "FS-C": set(range(4)),
        "FS-D": set(range(4)),
        "FS-E": set(range(3)),
        "FS-F": set(range(4)),
    }
    for index in range(6):
        row = {
            "variable": f"feature_{index}",
            "family": f"family_{index % 2}",
            "matching_cloud_area_variable": "cldarea_high_1h",
        }
        for feature_set, included in memberships.items():
            row[feature_set] = index in included
        rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_stage_a_and_b_create_24_runs_without_full_factorial():
    specs = build_experiment_specs(CONFIG)
    assert len(specs) == 24
    assert sum(spec["stage"] == "A" for spec in specs) == 6
    assert sum(spec["stage"] == "B" for spec in specs) == 18
    assert {spec["feature_set"] for spec in specs} == {
        "FS-A", "FS-B", "FS-C", "FS-D", "FS-E", "FS-F"
    }


def test_stage_c_is_not_created_without_shortlist():
    specs = build_experiment_specs(CONFIG)
    assert not any(spec["stage"] == "C" for spec in specs)


def test_stage_c_runs_only_for_explicit_shortlist():
    specs = build_experiment_specs(CONFIG, ["FS-A", "FS-C"])
    stage_c = [spec for spec in specs if spec["stage"] == "C"]
    assert len(stage_c) == 4
    assert {spec["feature_set"] for spec in stage_c} == {"FS-A", "FS-C"}


def test_invalid_shortlist_is_rejected():
    with pytest.raises(ValueError, match="Invalid stage_c"):
        build_experiment_specs(CONFIG, ["FS-Z"])


def test_duplicate_shortlist_is_rejected():
    with pytest.raises(ValueError, match="Duplicate feature sets"):
        build_experiment_specs(CONFIG, ["FS-A", "FS-A"])


def test_registry_membership_counts_are_validated(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    _, selected, digest = load_feature_registry(path, CONFIG["expected_feature_counts"])
    assert len(selected["FS-A"]) == 6
    assert len(selected["FS-E"]) == 3
    assert len(digest) == 64


def test_registry_count_mismatch_is_rejected(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    bad_counts = dict(CONFIG["expected_feature_counts"])
    bad_counts["FS-A"] = 5
    with pytest.raises(ValueError, match="membership mismatch"):
        load_feature_registry(path, bad_counts)


def test_duplicate_registry_variables_are_rejected(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    frame = pd.read_csv(path)
    frame.loc[1, "variable"] = frame.loc[0, "variable"]
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="Duplicate feature registry"):
        load_feature_registry(path, CONFIG["expected_feature_counts"])


def test_invalid_membership_values_are_rejected(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    frame = pd.read_csv(path, dtype={"FS-A": object})
    frame.loc[0, "FS-A"] = "maybe"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="Invalid membership"):
        load_feature_registry(path, CONFIG["expected_feature_counts"])


def test_run_ids_are_stable_for_same_inputs(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    _, selected, digest = load_feature_registry(path, CONFIG["expected_feature_counts"])
    first, _ = create_experiment_registry(CONFIG, "config-hash", selected, digest)
    second, _ = create_experiment_registry(CONFIG, "config-hash", selected, digest)
    assert first["run_id"].tolist() == second["run_id"].tolist()


def test_registry_and_manifests_include_feature_order_and_hashes(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    _, selected, digest = load_feature_registry(path, CONFIG["expected_feature_counts"])
    frame, manifests = create_experiment_registry(CONFIG, "config-hash", selected, digest)
    assert len(frame) == 24
    assert len(manifests) == 24
    assert manifests[0]["feature_order"] == selected["FS-A"]["variable"].tolist()
    assert manifests[0]["provenance"]["feature_registry_sha256"] == digest
    assert manifests[0]["provenance"]["source_netcdf_modified"] is False


def test_existing_run_status_is_resumed(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    _, selected, digest = load_feature_registry(path, CONFIG["expected_feature_counts"])
    old_frame, _ = create_experiment_registry(CONFIG, "config-hash", selected, digest)
    old_frame.loc[0, "status"] = "COMPLETED"
    old_path = tmp_path / "old_registry.csv"
    old_frame.to_csv(old_path, index=False)
    resumed, _ = create_experiment_registry(
        CONFIG, "config-hash", selected, digest, existing_registry_path=old_path
    )
    assert resumed.loc[0, "status"] == "COMPLETED"
    assert (resumed.loc[1:, "status"] == "PENDING").all()


def test_changed_registry_hash_invalidates_old_run_identity(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    _, selected, digest = load_feature_registry(path, CONFIG["expected_feature_counts"])
    first, _ = create_experiment_registry(CONFIG, "config-hash", selected, digest)
    second, _ = create_experiment_registry(CONFIG, "config-hash", selected, "changed-hash")
    assert first.loc[0, "run_id"] != second.loc[0, "run_id"]
    assert second.loc[0, "status"] == "PENDING"


def test_outputs_are_written_and_resume_files_exist(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    _, selected, digest = load_feature_registry(path, CONFIG["expected_feature_counts"])
    frame, manifests = create_experiment_registry(CONFIG, "config-hash", selected, digest)
    output = tmp_path / "reports" / "registry.csv"
    manifest_dir = tmp_path / "reports" / "manifests"
    write_experiment_outputs(frame, manifests, output, manifest_dir)
    assert output.exists()
    assert len(list(manifest_dir.glob("*.json"))) == 24
    assert json.loads(next(manifest_dir.glob("*.json")).read_text())


def test_status_update_changes_registry_and_manifest(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    _, selected, digest = load_feature_registry(path, CONFIG["expected_feature_counts"])
    frame, manifests = create_experiment_registry(CONFIG, "config-hash", selected, digest)
    output = tmp_path / "reports" / "registry.csv"
    manifest_dir = tmp_path / "reports" / "manifests"
    write_experiment_outputs(frame, manifests, output, manifest_dir)

    # Update function resolves manifest paths relative to the project root; use
    # a project-relative path for this isolated test by temporarily patching root.
    import experiment_orchestrator as module
    original_root = module.PROJECT_ROOT
    module.PROJECT_ROOT = tmp_path
    try:
        relative_manifest = Path("reports") / "manifests" / f"{frame.loc[0, 'run_id']}.json"
        stored = pd.read_csv(output)
        stored.loc[0, "manifest_path"] = relative_manifest.as_posix()
        stored.to_csv(output, index=False)
        updated = update_run_status(output, frame.loc[0, "run_id"], "RUNNING", "started")
        assert updated.loc[0, "status"] == "RUNNING"
        manifest = json.loads((tmp_path / relative_manifest).read_text())
        assert manifest["status"] == "RUNNING"
        assert manifest["status_note"] == "started"
    finally:
        module.PROJECT_ROOT = original_root


def test_invalid_status_is_rejected(tmp_path):
    path = make_registry(tmp_path / "feature_registry.csv")
    _, selected, digest = load_feature_registry(path, CONFIG["expected_feature_counts"])
    frame, manifests = create_experiment_registry(CONFIG, "config-hash", selected, digest)
    output = tmp_path / "reports" / "registry.csv"
    write_experiment_outputs(frame, manifests, output, tmp_path / "manifests")
    with pytest.raises(ValueError, match="Invalid run status"):
        update_run_status(output, frame.loc[0, "run_id"], "MAYBE")
