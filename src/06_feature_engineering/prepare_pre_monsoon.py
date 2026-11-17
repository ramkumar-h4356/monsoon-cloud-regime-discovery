"""Stage 1 CLI: prepare fixed transforms and audit whole-year partitions only."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess

import numpy as np
import pandas as pd
import xarray as xr

from ceres_features import (clean_variable, load_json, observation_ids, prepare,
                            registry, sample_indices, sha256, split_map, validate_schema)

ROOT = Path(__file__).resolve().parents[2]
STATUS = ["eligible_cloudy", "clear", "invalid_or_missing_area", "incomplete_cloudy"]


def protected_snapshot(root):
    """Hash existing Phase 1 code/reports/results; never execute their writers."""
    paths = [root / "setup_project.py", root / ".gitignore"]
    for directory in ("src", "reports", "results"):
        paths.extend((root / directory).rglob("*"))
    return {str(p.relative_to(root)): sha256(p) for p in sorted(set(paths))
            if p.is_file() and "__pycache__" not in p.parts
            and "phase2" not in p.parts and p.suffix != ".pyc"}


def git_state(root):
    def git(*args):
        result = subprocess.run(["git", "-c", f"safe.directory={root.as_posix()}", *args],
                                cwd=root, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    return {"commit": git("rev-parse", "HEAD"), "status": git("status", "--short", "--branch")}


def count_status(status):
    return {name: int(np.count_nonzero(status == i)) for i, name in enumerate(STATUS)}


def feature_decisions(contract):
    selected = {f["source"]: f for f in contract["primary"]}
    rows = []
    for name, spec in registry(contract).items():
        if name in selected:
            reason = "Complementary coverage, optical thickness or vertical location"
        elif name.startswith(("iwp_", "lwp_")):
            reason = contract["exclusions"]["water_paths"]
        elif name.startswith("cldphase_"):
            reason = contract["exclusions"]["phase"]
        elif "_total_" not in name:
            reason = contract["exclusions"]["layer_properties"]
        else:
            reason = contract["exclusions"]["other_vertical_properties"]
        rows.append(dict(variable=name, input_units=spec["units"],
            valid_min=spec["range"][0], valid_max=spec["range"][1],
            selected=name in selected, output=selected.get(name, {}).get("output", ""),
            transform=selected.get(name, {}).get("transform", ""), reason=reason))
    return rows


def strata_rows(prepared, year, split):
    status = prepared.status.values
    rows = []
    # Holdout gets only year-level technical counts, not exploratory profiles.
    if split == "holdout":
        return rows
    for hour in range(24):
        subset = status[pd.DatetimeIndex(prepared.time.values).hour == hour]
        rows.append(dict(year=year, split=split, stratum="utc_hour", value=hour,
                         total=subset.size, **count_status(subset)))
    for index, latitude in enumerate(prepared.lat.values):
        subset = status[:, index, :]
        rows.append(dict(year=year, split=split, stratum="latitude", value=float(latitude),
                         total=subset.size, **count_status(subset)))
    area = prepared.cldarea_total_1h.values
    for label, mask in (("0", area == 0), ("(0,10]", (area > 0) & (area <= 10)),
                        ("(10,50]", (area > 10) & (area <= 50)),
                        ("(50,100]", (area > 50) & (area <= 100)),
                        ("missing_or_invalid", ~np.isfinite(area))):
        rows.append(dict(year=year, split=split, stratum="cloud_area_percent", value=label,
                         total=int(mask.sum()), **count_status(status[mask])))
    return rows


def run(root=ROOT, run_id="stage1_v1", config_path=None, contract_path=None):
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id):
        raise ValueError("run-id must be a simple directory name")
    config_path = Path(config_path or root / "config/pre_monsoon_stage1.json")
    contract_path = Path(contract_path or root / "config/ceres_feature_definitions.json")
    config, contract = load_json(config_path), load_json(contract_path)
    if config["season"] != "pre_monsoon":
        raise ValueError("This runner is restricted to pre_monsoon")
    splits = split_map(config)
    if set(splits) != set(range(2010, 2022)):
        raise ValueError("Stage 1 requires exactly 2010-2021")
    if config["sample_per_year"] < 0 or config["seed"] < 0:
        raise ValueError("Invalid sampling configuration")
    data_dir = root / "data/interim/ceres_seasonal/pre_monsoon"
    sources = {year: data_dir / f"CERES_{year}_pre_monsoon.nc" for year in sorted(splits)}
    if set(data_dir.glob("*.nc")) != set(sources.values()):
        raise ValueError("Missing or unexpected annual source files")
    outputs = root / "data/processed/model_ready/phase2/pre_monsoon" / run_id
    reports = root / "reports/phase2/pre_monsoon" / run_id
    if outputs.exists() or reports.exists():
        raise FileExistsError("Run paths already exist; choose a new run-id. Overwrite is forbidden.")
    baseline = protected_snapshot(root)
    source_manifest = []
    reference_grid = None
    # Preflight all years before writing any outputs.
    for year, source in sources.items():
        with xr.open_dataset(source, mask_and_scale=True) as ds:
            validate_schema(ds, year, contract, config)
            grid = (ds.lat.values.copy(), ds.lon.values.copy())
            if reference_grid is not None and any(not np.array_equal(a, b)
                                                   for a, b in zip(grid, reference_grid)):
                raise ValueError("Coordinates differ between years")
            reference_grid = grid
        source_manifest.append(dict(year=year, split=splits[year],
                                    path=str(source.relative_to(root)), sha256=sha256(source)))
    outputs.mkdir(parents=True)
    reports.mkdir(parents=True)
    # A failed run stays marked incomplete; reruns cannot accidentally reuse it.
    manifest = {"status": "incomplete", "stage": 1, "run_id": run_id,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "config": config, "feature_contract": contract,
                "config_sha256": sha256(config_path), "contract_sha256": sha256(contract_path),
                "sources": source_manifest, "git": git_state(root),
                "environment": {"python": platform.python_version(),
                                **{p: importlib.metadata.version(p)
                                   for p in ("numpy", "pandas", "xarray", "netCDF4")}},
                "fitted_objects": [], "holdout_evaluated": False,
                "flatten_order": ["time", "lat", "lon"],
                "primary_feature_order": [f["output"] for f in contract["primary"]]}
    manifest_path = reports / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    annual, missingness, strata, phase_audit, samples, spatial = [], [], [], [], [], []
    specs = registry(contract)
    feature_sources = {f["source"] for f in contract["primary"]}
    for year, source in sources.items():
        split = splits[year]
        print(f"Preparing {year} ({split})", flush=True)
        with xr.open_dataset(source, mask_and_scale=True) as ds:
            prepared = prepare(ds, contract)
            prepared.attrs.update(season="pre_monsoon", year=year, split=split,
                feature_contract_version=contract["version"],
                feature_contract_sha256=manifest["contract_sha256"],
                source_sha256=next(s["sha256"] for s in source_manifest if s["year"] == year),
                model_features=json.dumps(manifest["primary_feature_order"]),
                fitted_transforms="none", observation_id_definition=
                "season|original timestamp ns|latitude .8f|longitude .8f; derived from coordinates",
                missingness_policy=contract["missingness"])
            status = prepared.status.values
            indices = (sample_indices(prepared.eligible.values, year, config["seed"],
                                      config["sample_per_year"]) if split != "holdout"
                       else np.array([], dtype=int))
            annual.append(dict(year=year, split=split, total=status.size,
                               **count_status(status), sampled=len(indices)))
            strata.extend(strata_rows(prepared, year, split))
            if split != "holdout":
                for yi, latitude in enumerate(ds.lat.values):
                    for xi, longitude in enumerate(ds.lon.values):
                        s = status[:, yi, xi]
                        spatial.append(dict(year=year, split=split, latitude=float(latitude),
                            longitude=float(longitude), total=s.size, **count_status(s)))
            for index, obs_id in zip(indices, observation_ids(ds, indices, "pre_monsoon")):
                samples.append(dict(year=year, split=split, flat_index=int(index), observation_id=obs_id))
            # Audit all properties in development; holdout only fixed primary validity.
            for name, spec in specs.items():
                if split == "holdout" and name not in feature_sources:
                    continue
                _, missing, invalid = clean_variable(ds[name], spec)
                missingness.append(dict(year=year, split=split, variable=name, units=spec["units"],
                    model_feature=name in feature_sources, total=missing.size,
                    missing=int(missing.sum()), invalid=int(invalid.sum()),
                    valid=int((~(missing | invalid)).sum())))
            if split != "holdout":
                for layer in contract["layers"]:
                    phase, _, _ = clean_variable(ds[f"cldphase_{layer}_1h"], specs[f"cldphase_{layer}_1h"])
                    iwp, _, _ = clean_variable(ds[f"iwp_{layer}_1h"], specs[f"iwp_{layer}_1h"])
                    for label, mask in (("exactly_1", phase == 1),
                                        ("between_1_and_2", (phase > 1) & (phase < 2)),
                                        ("exactly_2", phase == 2),
                                        ("missing_or_invalid_phase", ~np.isfinite(phase))):
                        phase_audit.append(dict(year=year, split=split, layer=layer,
                            phase_group=label, total=int(mask.sum()),
                            iwp_valid=int(np.isfinite(iwp[mask]).sum()),
                            eligible=int(((status == 0) & mask).sum())))
            encoding = {name: {"zlib": True, "complevel": 4} for name in prepared.data_vars}
            prepared.to_netcdf(outputs / f"CERES_{year}_pre_monsoon_prepared.nc",
                               engine="netcdf4", encoding=encoding)
    tables = {"year_split_counts.csv": annual, "feature_missingness.csv": missingness,
              "retention_strata.csv": strata, "retention_spatial.csv": spatial,
              "phase_iwp_audit.csv": phase_audit, "sample_manifest.csv": samples,
              "feature_decisions.csv": feature_decisions(contract)}
    for name, rows in tables.items():
        pd.DataFrame(rows).to_csv(reports / name, index=False)
    after = protected_snapshot(root)
    if after != baseline:
        raise RuntimeError("Protected source/report/result content changed during run")
    for source in source_manifest:
        if sha256(root / source["path"]) != source["sha256"]:
            raise RuntimeError("Source data changed during preparation")
    manifest.update(status="complete", phase1_preserved=True, protected_files=baseline,
                    output_sha256={str(p.relative_to(root)): sha256(p)
                        for directory in (outputs, reports) for p in sorted(directory.iterdir())
                        if p.is_file() and p != manifest_path})
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    counts = pd.DataFrame(annual)
    totals = counts.groupby("split", sort=False).sum(numeric_only=True).drop(columns="year")
    summary = ["# Pre-monsoon Phase 2 Stage 1 audit", "",
               "Status: complete. No imputation, scaling, PCA, t-SNE, clustering or holdout evaluation.",
               "", "Observation: one hourly grid cell; exact timestamps and coordinates retained.",
               "Features: total cloud area / 100, log1p(total optical depth), total cloud-top pressure (hPa).",
               "Eligible: valid positive cloud area and all three valid properties; clear = area exactly zero.",
               "Missing/invalid masks are metadata, excluded from future model feature matrices.",
               "", "```text", totals.to_string(), "```", "",
               f"Sampling: up to {config['sample_per_year']} eligible rows/year, "
               f"SeedSequence([{config['seed']}, year]); no holdout sample.",
               "IWP/LWP excluded: phase-dependent availability; missing never replaced by zero.",
               "All training/development locations are held together by year. Spatial transfer is untested.",
               "Phase 1 used all years; this holdout is not historically unseen.",
               "Other seasons share definitions, but future fitted models must be season-specific.",
               "", "See manifest.json for source/output hashes, configuration, environment and Git state.",
               "See feature_missingness, retention_strata, retention_spatial and phase_iwp_audit CSVs "
               "for counts and their denominators. Holdout has only primary validity and annual counts."]
    (reports / "report.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    # Include the generated report in the final output inventory.
    manifest["output_sha256"][str((reports / "report.md").relative_to(root))] = sha256(reports / "report.md")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(totals.to_string(), flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="stage1_v1")
    args = parser.parse_args()
    run(run_id=args.run_id)
