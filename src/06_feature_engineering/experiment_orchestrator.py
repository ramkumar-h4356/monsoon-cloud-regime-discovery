"""M18.6 staged feature-set experiment orchestration.

This module creates a deterministic experiment registry and per-run manifests.
It does not load CERES NetCDF data or execute imputation, scaling, or clustering.
Those operations are handled by subsequent M18 milestones.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "m18_experiment_orchestration.json"
DEFAULT_REGISTRY = (
    PROJECT_ROOT
    / "reports"
    / "feature_engineering"
    / "feature_set_registry.csv"
)
DEFAULT_RUN_REGISTRY = (
    PROJECT_ROOT
    / "reports"
    / "feature_engineering"
    / "m18_experiment_registry.csv"
)
DEFAULT_MANIFEST_DIR = (
    PROJECT_ROOT / "reports" / "feature_engineering" / "experiment_manifests"
)

VALID_STATUSES = {"PENDING", "RUNNING", "COMPLETED", "FAILED", "SKIPPED"}
FEATURE_SET_IDS = ("FS-A", "FS-B", "FS-C", "FS-D", "FS-E", "FS-F")
REGISTRY_REQUIRED_COLUMNS = {
    "variable",
    "family",
    "matching_cloud_area_variable",
    *FEATURE_SET_IDS,
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_write_text(path: Path, content: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    _atomic_write_text(path, frame.to_csv(index=False, lineterminator="\n"))


def load_config(config_path: Path) -> tuple[dict, str]:
    config_path = Path(config_path)
    raw = config_path.read_bytes()
    try:
        config = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid orchestration JSON: {config_path}") from exc

    required = {"expected_feature_counts", "stage_a", "stage_b", "stage_c"}
    missing = required - set(config)
    if missing:
        raise ValueError(f"Orchestration config missing keys: {sorted(missing)}")
    return config, _sha256_bytes(raw)


def _parse_membership(value, column: str, variable: str) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        raise ValueError(f"Null membership for {variable} in {column}")
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise ValueError(
        f"Invalid membership value {value!r} for {variable} in {column}"
    )


def load_feature_registry(registry_path: Path, expected_counts: dict) -> tuple[pd.DataFrame, dict, str]:
    registry_path = Path(registry_path)
    if not registry_path.exists():
        raise FileNotFoundError(f"Feature registry not found: {registry_path}")

    frame = pd.read_csv(registry_path)
    missing = REGISTRY_REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Feature registry missing columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Feature registry contains no rows.")

    frame["variable"] = frame["variable"].astype(str).str.strip()
    if frame["variable"].eq("").any():
        raise ValueError("Feature registry contains an empty variable name.")
    if frame["variable"].duplicated().any():
        duplicates = frame.loc[
            frame["variable"].duplicated(keep=False), "variable"
        ].tolist()
        raise ValueError(f"Duplicate feature registry variables: {duplicates}")

    selected = {}
    for feature_set in FEATURE_SET_IDS:
        selected_mask = [
            _parse_membership(value, feature_set, variable)
            for value, variable in zip(frame[feature_set], frame["variable"])
        ]
        selected[feature_set] = frame.loc[selected_mask].copy()
        expected = int(expected_counts.get(feature_set, -1))
        observed = len(selected[feature_set])
        if expected < 0:
            raise ValueError(f"No expected feature count configured for {feature_set}")
        if observed != expected:
            raise ValueError(
                f"{feature_set} membership mismatch: expected {expected}, got {observed}"
            )

    digest = sha256_file(registry_path)
    return frame, selected, digest


def _normalize_feature_set_list(values: Iterable[str], label: str) -> list[str]:
    result = [str(value).strip().upper() for value in values]
    invalid = sorted(set(result) - set(FEATURE_SET_IDS))
    if invalid:
        raise ValueError(f"Invalid {label} feature sets: {invalid}")
    if len(result) != len(set(result)):
        raise ValueError(f"Duplicate feature sets in {label}.")
    return result


def build_experiment_specs(config: dict, shortlisted_feature_sets=None) -> list[dict]:
    """Build the deliberately staged (non-factorial) experiment plan."""
    specs = []
    stage_a = config["stage_a"]
    stage_b = config["stage_b"]

    stage_a_sets = _normalize_feature_set_list(
        stage_a.get("feature_sets", FEATURE_SET_IDS), "stage_a"
    )
    stage_b_sets = _normalize_feature_set_list(
        stage_b.get("feature_sets", stage_a_sets), "stage_b"
    )

    for feature_set in stage_a_sets:
        specs.append({
            "stage": "A",
            "feature_set": feature_set,
            "property_treatment": stage_a.get("property_treatment", "SA-A"),
            "cloud_area_treatment": stage_a.get("cloud_area_treatment", "CA-A"),
            "scaler": stage_a.get("scaler", "robust"),
            "weighting": stage_a.get("weighting", "equal"),
            "purpose": "baseline",
        })

    for variant in stage_b.get("variants", []):
        for feature_set in stage_b_sets:
            specs.append({
                "stage": "B",
                "feature_set": feature_set,
                "property_treatment": variant["property_treatment"],
                "cloud_area_treatment": variant["cloud_area_treatment"],
                "scaler": stage_a.get("scaler", "robust"),
                "weighting": stage_a.get("weighting", "equal"),
                "purpose": variant["purpose"],
            })

    if shortlisted_feature_sets is None:
        shortlisted_feature_sets = config["stage_c"].get("shortlisted_feature_sets", [])
    stage_c_sets = _normalize_feature_set_list(
        shortlisted_feature_sets, "stage_c shortlist"
    )
    unknown_shortlist = sorted(set(stage_c_sets) - set(stage_a_sets))
    if unknown_shortlist:
        raise ValueError(
            f"Stage C shortlist contains feature sets absent from Stage A: {unknown_shortlist}"
        )

    for variant in config["stage_c"].get("variants", []):
        for feature_set in stage_c_sets:
            specs.append({
                "stage": "C",
                "feature_set": feature_set,
                "property_treatment": variant.get("property_treatment", "SA-A"),
                "cloud_area_treatment": variant.get("cloud_area_treatment", "CA-A"),
                "scaler": variant["scaler"],
                "weighting": variant["weighting"],
                "purpose": variant["purpose"],
            })

    return specs


def _make_run_id(spec: dict, config_hash: str, registry_hash: str) -> str:
    identity = {
        "spec": spec,
        "config_sha256": config_hash,
        "feature_registry_sha256": registry_hash,
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    suffix = _sha256_bytes(canonical.encode("utf-8"))[:12]
    return (
        f"M18-{spec['stage']}-{spec['feature_set']}-"
        f"{spec['property_treatment']}-{spec['cloud_area_treatment']}-"
        f"{spec['scaler']}-{spec['weighting']}-{suffix}"
    )


def create_experiment_registry(
    config: dict,
    config_hash: str,
    selected_features: dict,
    registry_hash: str,
    existing_registry_path: Path | None = None,
    shortlisted_feature_sets=None,
) -> tuple[pd.DataFrame, list[dict]]:
    specs = build_experiment_specs(config, shortlisted_feature_sets)
    previous = {}
    if existing_registry_path is not None and Path(existing_registry_path).exists():
        old = pd.read_csv(existing_registry_path, dtype=str).fillna("")
        if "run_id" in old.columns:
            previous = {row["run_id"]: row for row in old.to_dict("records")}

    records = []
    manifests = []
    now = _utc_now()

    for spec in specs:
        feature_set = spec["feature_set"]
        feature_frame = selected_features[feature_set]
        feature_names = feature_frame["variable"].astype(str).tolist()
        families = [
            None if pd.isna(value) or not str(value).strip() else str(value).strip()
            for value in feature_frame["family"].tolist()
        ]
        run_id = _make_run_id(spec, config_hash, registry_hash)
        old = previous.get(run_id, {})
        status = old.get("status", "PENDING") or "PENDING"
        if status not in VALID_STATUSES:
            status = "PENDING"
        created = old.get("created_utc", "") or now
        updated = old.get("updated_utc", "") or created
        note = old.get("note", "")
        manifest_relative = (
            Path("reports") / "feature_engineering" / "experiment_manifests"
            / f"{run_id}.json"
        )

        record = {
            "run_id": run_id,
            "stage": spec["stage"],
            "feature_set": feature_set,
            "feature_count": len(feature_names),
            "property_treatment": spec["property_treatment"],
            "cloud_area_treatment": spec["cloud_area_treatment"],
            "scaler": spec["scaler"],
            "weighting": spec["weighting"],
            "purpose": spec["purpose"],
            "status": status,
            "created_utc": created,
            "updated_utc": updated,
            "config_sha256": config_hash,
            "feature_registry_sha256": registry_hash,
            "manifest_path": manifest_relative.as_posix(),
            "note": note,
        }
        records.append(record)

        manifests.append({
            "schema_version": "1.0",
            "milestone": "M18.6",
            "run_id": run_id,
            "status": status,
            "experiment": spec,
            "feature_count": len(feature_names),
            "feature_order": feature_names,
            "feature_families": families,
            "provenance": {
                "config_sha256": config_hash,
                "feature_registry_sha256": registry_hash,
                "fit_scope": "training_partition_only",
                "source_netcdf_modified": False,
            },
            "validation_policy": config.get("validation_policy", {}),
            "execution_policy": config.get("execution_policy", {}),
            "created_utc": created,
        })

    return pd.DataFrame(records), manifests


def write_experiment_outputs(
    registry_frame: pd.DataFrame,
    manifests: list[dict],
    output_registry: Path,
    manifest_dir: Path,
) -> None:
    output_registry = Path(output_registry)
    manifest_dir = Path(manifest_dir)
    for manifest in manifests:
        path = manifest_dir / f"{manifest['run_id']}.json"
        _atomic_write_text(path, json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    _atomic_write_csv(registry_frame, output_registry)


def update_run_status(
    registry_path: Path,
    run_id: str,
    status: str,
    note: str = "",
) -> pd.DataFrame:
    status = str(status).strip().upper()
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid run status {status!r}; choose {sorted(VALID_STATUSES)}")

    registry_path = Path(registry_path)
    if not registry_path.exists():
        raise FileNotFoundError(registry_path)
    frame = pd.read_csv(registry_path, dtype=str).fillna("")
    matches = frame.index[frame["run_id"] == run_id].tolist()
    if len(matches) != 1:
        raise KeyError(f"Expected exactly one run_id match for {run_id!r}; found {len(matches)}")

    index = matches[0]
    frame.at[index, "status"] = status
    frame.at[index, "updated_utc"] = _utc_now()
    frame.at[index, "note"] = str(note)
    _atomic_write_csv(frame, registry_path)

    manifest_path = Path(frame.at[index, "manifest_path"])
    if not manifest_path.is_absolute():
        manifest_path = PROJECT_ROOT / manifest_path
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = status
        manifest["status_note"] = str(note)
        manifest["updated_utc"] = frame.at[index, "updated_utc"]
        _atomic_write_text(
            manifest_path,
            json.dumps(manifest, indent=2, allow_nan=False) + "\n",
        )
    return frame


def run_orchestrator(
    registry_path: Path = DEFAULT_REGISTRY,
    config_path: Path = DEFAULT_CONFIG,
    output_registry: Path = DEFAULT_RUN_REGISTRY,
    manifest_dir: Path = DEFAULT_MANIFEST_DIR,
    shortlisted_feature_sets=None,
) -> pd.DataFrame:
    config, config_hash = load_config(config_path)
    _, selected, registry_hash = load_feature_registry(
        registry_path, config["expected_feature_counts"]
    )
    existing = Path(output_registry) if Path(output_registry).exists() else None
    registry_frame, manifests = create_experiment_registry(
        config=config,
        config_hash=config_hash,
        selected_features=selected,
        registry_hash=registry_hash,
        existing_registry_path=existing,
        shortlisted_feature_sets=shortlisted_feature_sets,
    )
    write_experiment_outputs(
        registry_frame, manifests, output_registry, manifest_dir
    )
    return registry_frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_RUN_REGISTRY)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument(
        "--shortlist", nargs="*", default=None,
        help="Optional shortlisted feature sets for Stage C, e.g. FS-A FS-C.",
    )
    parser.add_argument("--update-run-status", metavar="RUN_ID")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES))
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    if args.update_run_status:
        if not args.status:
            parser.error("--status is required with --update-run-status")
        frame = update_run_status(
            args.output, args.update_run_status, args.status, args.note
        )
    else:
        frame = run_orchestrator(
            registry_path=args.registry,
            config_path=args.config,
            output_registry=args.output,
            manifest_dir=args.manifest_dir,
            shortlisted_feature_sets=args.shortlist,
        )

    print("\n========== M18.6 EXPERIMENT ORCHESTRATION ==========")
    print(f"Registered runs: {len(frame)}")
    print("Runs by stage:")
    print(frame.groupby("stage").size().to_string())
    print("\nRuns by status:")
    print(frame.groupby("status").size().to_string())
    print(f"\nRegistry: {args.output}")
    print(f"Manifests: {args.manifest_dir}")


if __name__ == "__main__":
    main()
