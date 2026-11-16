"""Two-step, sealed temporal evaluation. Freeze must precede any holdout access."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "data/processed/model_ready/phase3/matplotlib_cache"))
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import wasserstein_distance
from threadpoolctl import threadpool_limits
import xarray as xr

for folder in ("src/06_feature_engineering", "src/07_clustering"):
    sys.path.insert(0, str(ROOT / folder))
from ceres_features import (clean_variable, load_json, observation_ids, prepare, registry,
                            sha256, validate_schema)
from prepare_pre_monsoon import git_state
from pre_monsoon_stage2_model import project, scaled
from pre_monsoon_stage2_diagnostics import physical_profiles, population_diagnostics
from pre_monsoon_stage3_tools import (bootstrap_fractions, evaluate_metrics, nested_samples,
                                      ordering_checks, prohibit_fitting)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def run_paths(root, run_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id):
        raise ValueError("Invalid run ID")
    return root / "reports/phase3/pre_monsoon" / run_id


def preserved_inventory(root):
    files = [root / name for name in (".gitignore", "setup_project.py", "requirements-stage1.txt", "requirements-stage2.txt")]
    for name in ("src", "reports", "results", "config", "docs", "tests"):
        files.extend((root / name).rglob("*"))
    return {str(p.relative_to(root)): sha256(p) for p in sorted(set(files))
            if p.is_file() and "phase3" not in p.parts and "__pycache__" not in p.parts
            and p.suffix != ".pyc"}


def assert_hashes(root, hashes):
    for path, expected in hashes.items():
        if sha256(root / path) != expected:
            raise ValueError(f"Frozen/protected hash mismatch: {path}")


def predictions(bundle, x):
    z = scaled(bundle, x)
    scores = bundle["pca"].transform(z)[:, :bundle["selected_n_components"]]
    labels = bundle["kmeans"].predict(scores)
    distance = bundle["kmeans"].transform(scores)[np.arange(len(x)), labels]
    return labels, distance, z, scores


def freeze(root=ROOT, run_id="stage3_v1", config_path=None):
    root = Path(root).resolve()
    out = run_paths(root, run_id)
    if out.exists():
        raise FileExistsError("Stage 3 freeze already exists; overwrites are forbidden")
    config_path = Path(config_path or root / "config/pre_monsoon_stage3.json")
    config = load_json(config_path)
    if (config["season"] != "pre_monsoon" or config["fit_years"] != list(range(2010, 2017))
            or config["development_years"] != [2017, 2018] or config["holdout_years"] != [2019, 2020, 2021]
            or config["n_components"] != 3 or config["n_clusters"] != 2):
        raise ValueError("Final fitting policy is unresolved or inconsistent")
    if not (config["profile_sample_per_year"] >= config["metric_sample_per_year"]
            >= config["pooled_metric_sample_per_year"] > 0):
        raise ValueError("Invalid nested sample budgets")
    base = root / "reports/phase2/pre_monsoon" / config["stage2_run_id"]
    s2 = load_json(base / "manifest.json")
    if (s2["status"] != "complete" or s2["selected_n_components"] != 3
            or s2["selected_k"] != 2 or s2["fit_years"] != config["fit_years"]
            or s2["holdout_accessed"] or s2["holdout_evaluated"]):
        raise ValueError("Stage 2 evidence/fitting policy is incomplete")
    assert_hashes(root, s2["output_sha256"])
    assert_hashes(root, s2["code_sha256"])
    review_dir = root / "reports/phase2/pre_monsoon"
    review = load_json(review_dir / "stage2_review_manifest.json")
    if (review["status"] != "complete" or review["passed_tests"] < 19
            or sha256(base / "manifest.json") != review["main_run_manifest_sha256"]
            or sha256(review_dir / "stage2_review.md") != review["review_sha256"]):
        raise ValueError("Stage 2 scientific review/test evidence is unresolved")
    assert_hashes(root, review["tests"])
    selection = pd.read_csv(base / "cluster_selection.csv")
    chosen = selection[selection.selected]
    if len(chosen) != 1 or int(chosen.iloc[0].k) != 2 or not bool(chosen.iloc[0].admissible):
        raise ValueError("Selected cluster count lacks admissible evidence")
    if float(chosen.iloc[0].silhouette) < selection[selection.admissible].silhouette.max() - s2["config"]["silhouette_tolerance"]:
        raise ValueError("Selected k violates the recorded selection rule")
    s1_dir = review_dir / config["stage1_run_id"]
    s1 = load_json(s1_dir / "manifest.json")
    contract_path = root / "config/ceres_feature_definitions.json"
    if sha256(contract_path) != s1["contract_sha256"] or s2["contract_sha256"] != s1["contract_sha256"]:
        raise ValueError("Feature contract changed")
    assert_hashes(root, s1["protected_files"])
    contract = load_json(contract_path)
    model_path = root / "results/models/phase2/pre_monsoon" / config["stage2_run_id"] / "selected_pre_monsoon_bundle.joblib"
    bundle = joblib.load(model_path)
    if (bundle["season"] != "pre_monsoon" or bundle["fit_years"] != config["fit_years"]
            or bundle["selected_n_components"] != 3 or bundle["kmeans"].n_clusters != 2
            or bundle["contract_sha256"] != s1["contract_sha256"]
            or bundle["feature_order"] != [f["output"] for f in contract["primary"]]):
        raise ValueError("Final model/feature metadata mismatch")
    samples = pd.read_csv(s1_dir / "sample_manifest.csv")
    training = samples[samples.split == "train"].copy()
    x_parts, training_inputs = [], []
    # This loop is deliberately hard-limited to training years. No holdout hash/open here.
    for year in config["fit_years"]:
        path = (root / "data/processed/model_ready/phase2/pre_monsoon" / config["stage1_run_id"]
                / f"CERES_{year}_pre_monsoon_prepared.nc")
        expected = next(row["sha256"] for row in s2["accessed_inputs"] if row["path"] == str(path.relative_to(root)))
        if sha256(path) != expected:
            raise ValueError("Training reference changed")
        training_inputs.append(dict(year=year, path=str(path.relative_to(root)), sha256=expected))
        group = training[training.year == year]
        indices = group.flat_index.to_numpy(dtype=int)
        with xr.open_dataset(path) as ds:
            if observation_ids(ds, indices, "pre_monsoon") != group.observation_id.tolist():
                raise ValueError("Training reference identity mismatch")
            x_parts.append(np.column_stack([ds[name].values.ravel()[indices] for name in bundle["feature_order"]]))
    x = np.concatenate(x_parts).astype("float64")
    if (training.observation_id.tolist() != bundle["training_observation_ids"]
            or len(x) != s2["training_sample_count"] or bundle["scaler"].n_samples_seen_ != len(x)
            or bundle["pca"].n_samples_ != len(x)):
        raise ValueError("Fitted sample/reference mismatch")
    np.testing.assert_allclose(bundle["imputer"].statistics_, np.median(x, axis=0), atol=1e-12)
    np.testing.assert_allclose(bundle["scaler"].mean_, x.mean(axis=0), atol=1e-12)
    with prohibit_fitting(), threadpool_limits(config["threads"]):
        labels, distance, z, scores = predictions(bundle, x)
    if not np.isfinite(x).all():
        raise ValueError("The complete-case training policy was violated")
    thresholds = {f"q{int(q*100)}": float(np.quantile(distance, q, method=config["threshold_quantile_method"]))
                  for q in config["distance_quantiles"]}
    expected_holdout = []
    for year in config["holdout_years"]:
        source = next(row for row in s1["sources"] if row["year"] == year)
        prepared = Path("data/processed/model_ready/phase2/pre_monsoon") / config["stage1_run_id"] / f"CERES_{year}_pre_monsoon_prepared.nc"
        expected_holdout.append(dict(year=year, raw_path=source["path"], raw_sha256=source["sha256"],
            prepared_path=str(prepared), prepared_sha256=s1["output_sha256"][str(prepared)]))
    preserved = preserved_inventory(root)
    freeze_dir = out / "freeze"
    freeze_dir.mkdir(parents=True)
    write_json(freeze_dir / "configuration.json", config)
    write_json(freeze_dir / "feature_definitions.json", contract)
    write_json(freeze_dir / "stage2_configuration.json", s2["config"])
    (freeze_dir / "protocol.md").write_bytes((root / "docs/methodology/pre_monsoon_stage3_protocol.md").read_bytes())
    np.savez_compressed(freeze_dir / "training_reference.npz", x=x, z=z, scores=scores,
                        distance=distance, labels=labels)
    evidence_names = ["cluster_selection.csv", "pca_variance.csv", "pca_loadings.csv",
                      "pca_reconstruction.csv", "initialization_stability.csv", "sampling_stability.csv"]
    for name in evidence_names:
        (freeze_dir / name).write_bytes((base / name).read_bytes())
    write_json(freeze_dir / "frozen.json", dict(status="frozen_before_holdout_access", created_utc=utc_now(),
        final_fitting_policy=config["fitting_policy"], model_path=str(model_path.relative_to(root)),
        model_sha256=sha256(model_path), contract_sha256=sha256(contract_path),
        source_config_sha256=sha256(config_path), config=config, distance_thresholds=thresholds,
        fitting_sample_count=len(x), training_only_inputs=training_inputs,
        fitted_parameters=dict(imputer_strategy=bundle["imputer"].strategy,
            imputer_medians=bundle["imputer"].statistics_.tolist(),
            scaler_mean=bundle["scaler"].mean_.tolist(), scaler_scale=bundle["scaler"].scale_.tolist(),
            pca_whiten=bundle["pca"].whiten, pca_solver=bundle["pca"].svd_solver,
            pca_components=bundle["pca"].components_.tolist(),
            pca_explained_variance_ratio=bundle["pca"].explained_variance_ratio_.tolist(),
            kmeans_parameters=bundle["kmeans"].get_params(),
            kmeans_centers=bundle["kmeans"].cluster_centers_.tolist()),
        expected_holdout_inputs=expected_holdout, stage1_schema_config=s1["config"],
        stage1_manifest_sha256=sha256(s1_dir / "manifest.json"), stage2_manifest_sha256=sha256(base / "manifest.json"),
        stage2_review_sha256=sha256(review_dir / "stage2_review.md"), preserved_files=preserved,
        holdout_accessed=False, code_and_policy_frozen=True, git=git_state(root),
        environment={"python": platform.python_version(), "platform": platform.platform(),
            **{p: importlib.metadata.version(p) for p in ("numpy", "pandas", "xarray", "netCDF4", "scipy", "scikit-learn", "matplotlib", "joblib", "threadpoolctl")}}))
    seal = dict(status="sealed", created_utc=utc_now(), holdout_accessed=False,
                files={p.name: sha256(p) for p in sorted(freeze_dir.iterdir()) if p.is_file()})
    write_json(freeze_dir / "seal.json", seal)
    print(json.dumps(dict(status="sealed_before_holdout", thresholds=thresholds, training_rows=len(x),
                          seal_sha256=sha256(freeze_dir / "seal.json")), indent=2), flush=True)
    return seal


def load_freeze(root, run_id):
    out = run_paths(root, run_id)
    folder = out / "freeze"
    seal = load_json(folder / "seal.json")
    if seal["status"] != "sealed" or seal["holdout_accessed"]:
        raise ValueError("Missing or invalid pre-holdout seal")
    for name, digest in seal["files"].items():
        if sha256(folder / name) != digest:
            raise ValueError(f"Freeze seal mismatch: {name}")
    frozen = load_json(folder / "frozen.json")
    if frozen["status"] != "frozen_before_holdout_access" or frozen["holdout_accessed"]:
        raise ValueError("Invalid fitting-policy freeze")
    assert_hashes(root, frozen["preserved_files"])
    if sha256(root / frozen["model_path"]) != frozen["model_sha256"]:
        raise ValueError("Model changed after freeze")
    return out, folder, frozen


def holdout_input_paths(root, entry, frozen):
    if entry["year"] not in [2019, 2020, 2021] or entry not in frozen["expected_holdout_inputs"]:
        raise ValueError("Unapproved holdout input")
    for key in ("raw", "prepared"):
        path = root / entry[f"{key}_path"]
        if sha256(path) != entry[f"{key}_sha256"]:
            raise ValueError(f"Holdout {key} source hash mismatch")
    return root / entry["raw_path"], root / entry["prepared_path"]


def evaluate(root=ROOT, run_id="stage3_v1"):
    root = Path(root).resolve()
    out, freeze_dir, frozen = load_freeze(root, run_id)  # must succeed before holdout path access
    config = frozen["config"]
    contract = load_json(freeze_dir / "feature_definitions.json")
    bundle = joblib.load(root / frozen["model_path"])
    evaluation = out / "evaluation"
    figures = root / "results/figures/phase3/pre_monsoon" / run_id
    labels_dir = root / "data/processed/model_ready/phase3/pre_monsoon" / run_id
    if any(path.exists() for path in (evaluation, figures, labels_dir)):
        raise FileExistsError("Evaluation outputs already exist; do not rerun or overwrite")
    for path in (evaluation, figures, labels_dir):
        path.mkdir(parents=True)
    write_json(evaluation / "holdout_access_receipt.json", dict(status="authorized_after_seal",
        created_utc=utc_now(), seal_sha256=sha256(freeze_dir / "seal.json"), years=config["holdout_years"],
        model_sha256=frozen["model_sha256"], fitting_policy=frozen["final_fitting_policy"]))
    spec = registry(contract)
    tables = {}
    samples, sample_x, pooled_indices, metrics, details, points, summaries, bootstraps = [], [], [], [], [], [], [], []
    references = np.load(freeze_dir / "training_reference.npz")
    reference_x, reference_z, reference_scores = references["x"], references["z"], references["scores"]
    reference_distance = references["distance"]
    reference_profile = pd.read_csv(root / "reports/phase2/pre_monsoon" / config["stage2_run_id"] / "physical_profiles.csv")
    drift_rows, score_rows, area_rows, retention, reconstruction = [], [], [], [], []
    offset = 0
    with prohibit_fitting(), threadpool_limits(config["threads"]):
        for entry in frozen["expected_holdout_inputs"]:
            year = entry["year"]
            print(f"Evaluating reserved year {year}; frozen model only", flush=True)
            raw_path, prepared_path = holdout_input_paths(root, entry, frozen)
            with xr.open_dataset(raw_path, mask_and_scale=True) as raw, xr.open_dataset(prepared_path) as prepared:
                validate_schema(raw, year, contract, frozen["stage1_schema_config"])
                if (prepared.attrs["split"] != "holdout" or prepared.attrs["season"] != "pre_monsoon"
                        or prepared.attrs["feature_contract_sha256"] != frozen["contract_sha256"]):
                    raise ValueError("Holdout prepared metadata mismatch")
                canonical = prepare(raw, contract)
                xr.testing.assert_equal(canonical.coords.to_dataset(), prepared.coords.to_dataset())
                for name in canonical.data_vars:
                    xr.testing.assert_equal(canonical[name], prepared[name])
                status = prepared.status.values
                valid = np.flatnonzero(status.ravel() == 0)
                profile_indices, metric_indices, pooled = nested_samples(valid, year, config)
                x = np.column_stack([prepared[name].values.ravel()[valid] for name in bundle["feature_order"]]).astype("float64")
                if not np.isfinite(x).all():
                    raise ValueError("Eligible holdout rows must remain complete; no imputation of gaps")
                label_flat = np.where(status.ravel() == 1, -1, -2).astype("int16")
                distance_flat = np.full(status.size, np.nan)
                scores_full = np.empty((len(valid), 3))
                squared_error = np.zeros(3)
                for start in range(0, len(valid), config["batch_size"]):
                    stop = start + config["batch_size"]
                    batch_labels, distances, z, pc = predictions(bundle, x[start:stop])
                    label_flat[valid[start:stop]] = batch_labels
                    distance_flat[valid[start:stop]] = distances
                    scores_full[start:stop] = pc
                    reconstructed = bundle["pca"].inverse_transform(pc)
                    squared_error += ((z - reconstructed) ** 2).sum(axis=0)
                labels = label_flat.reshape(status.shape)
                distance_array = distance_flat.reshape(status.shape)
                labeled = xr.Dataset({"cluster": (("time", "lat", "lon"), labels)},
                                     coords={d: prepared[d] for d in ("time", "lat", "lon")})
                labeled.attrs.update(season="pre_monsoon", year=year, partition="holdout",
                    fit_years="2010-2016", model_sha256=frozen["model_sha256"],
                    freeze_seal_sha256=sha256(freeze_dir / "seal.json"))
                labeled.cluster.attrs.update(clear_label=-1, unavailable_label=-2,
                                              interpretation="descriptive frozen cloud-property partition")
                labeled.to_netcdf(labels_dir / f"CERES_{year}_pre_monsoon_labels.nc", engine="netcdf4",
                                 encoding={"cluster": {"zlib": True, "complevel": 4}})
                retention.append(dict(year=year, total=status.size, eligible=len(valid),
                    clear=int((status == 1).sum()), invalid_or_missing_area=int((status == 2).sum()),
                    incomplete_cloudy=int((status == 3).sum()), profile_sample=len(profile_indices),
                    metric_sample=len(metric_indices), pooled_sample=len(pooled),
                    sample_budget_met=len(profile_indices) == config["profile_sample_per_year"]))
                diagnostics = population_diagnostics(prepared, labels, year, "holdout", config["n_clusters"])
                for name, values in diagnostics.items():
                    tables.setdefault(name, []).extend(values)
                for q, threshold in frozen["distance_thresholds"].items():
                    summaries.append(dict(period=str(year), threshold=q, threshold_value=threshold,
                        eligible=len(valid), exceedance_fraction=float((distance_flat[valid] > threshold).mean()),
                        mean_squared_distance=float(np.mean(distance_flat[valid] ** 2)),
                        median_distance=float(np.median(distance_flat[valid])),
                        p95_distance=float(np.quantile(distance_flat[valid], .95)),
                        p99_distance=float(np.quantile(distance_flat[valid], .99))))
                for i, feature in enumerate(bundle["feature_order"]):
                    reconstruction.append(dict(year=year, feature=feature,
                        standardized_rmse=float(np.sqrt(squared_error[i] / len(valid))),
                        interpretation="algebraically near zero at full dimension; not validation"))
                    score_rows.append(dict(year=year, component=i+1, mean=float(scores_full[:, i].mean()),
                        variance=float(scores_full[:, i].var(ddof=1)),
                        fraction_of_total_score_variance=float(scores_full[:, i].var(ddof=1) / scores_full.var(axis=0, ddof=1).sum()),
                        training_mean=float(reference_scores[:, i].mean()),
                        training_variance=float(reference_scores[:, i].var(ddof=1))))
                times = pd.DatetimeIndex(prepared.time.values)
                day_rows = []
                for date in times.normalize().unique():
                    mask = times.normalize() == date
                    subset_labels = labels[mask]
                    subset_distance = distance_array[mask]
                    row = dict(date=str(date.date()), total=subset_labels.size,
                        eligible=int((subset_labels >= 0).sum()), clear=int((subset_labels == -1).sum()),
                        **{f"cluster_{k}": int((subset_labels == k).sum()) for k in range(config["n_clusters"])},
                        **{f"above_{q}": int((subset_distance > threshold).sum())
                           for q, threshold in frozen["distance_thresholds"].items()})
                    day_rows.append(row)
                daily = pd.DataFrame(day_rows)
                daily.assign(year=year).to_csv(evaluation / f"bootstrap_daily_sufficient_statistics_{year}.csv", index=False)
                bootstraps.extend(bootstrap_fractions(daily, year, config))
                weights = np.broadcast_to(np.cos(np.deg2rad(prepared.lat.values))[None, :, None], status.shape)
                for k in range(config["n_clusters"]):
                    area_rows.append(dict(year=year, cluster=k,
                        cosine_latitude_cloudy_fraction=float(weights[labels == k].sum() / weights[labels >= 0].sum())))
                frame = pd.DataFrame(dict(year=year, split="holdout", flat_index=profile_indices,
                    observation_id=observation_ids(prepared, profile_indices, "pre_monsoon"),
                    cluster=label_flat[profile_indices], distance=distance_flat[profile_indices],
                    yearly_metric=np.isin(profile_indices, metric_indices), pooled_metric=np.isin(profile_indices, pooled)))
                for name in config["profile_variables"]:
                    values, _, _ = clean_variable(raw[name], spec[name])
                    frame[name] = values.ravel()[profile_indices]
                xx = np.column_stack([prepared[name].values.ravel()[profile_indices] for name in bundle["feature_order"]]).astype("float64")
                for i, feature in enumerate(bundle["feature_order"]):
                    vals = xx[:, i]
                    drift_rows.append(dict(period=str(year), feature=feature,
                        scope="fixed_profile_sample_transformed_features", n=len(vals),
                        mean=float(vals.mean()), median=float(np.median(vals)),
                        p10=float(np.quantile(vals, .1)), p90=float(np.quantile(vals, .9)),
                        training_mean=float(reference_x[:, i].mean()), training_median=float(np.median(reference_x[:, i])),
                        mean_shift_training_sd=float((vals.mean() - reference_x[:, i].mean()) / bundle["scaler"].scale_[i]),
                        wasserstein_training_sd=float(wasserstein_distance(reference_x[:, i], vals) / bundle["scaler"].scale_[i])))
                local_metric = frame.yearly_metric.to_numpy()
                row, detail, point = evaluate_metrics(scaled(bundle, xx[local_metric]),
                    frame.loc[local_metric, "cluster"].to_numpy(), frame.loc[local_metric, "observation_id"], str(year), config)
                metrics.append(row); details.extend(detail); points.extend(point)
                pooled_indices.extend((offset + np.flatnonzero(frame.pooled_metric.to_numpy())).tolist())
                offset += len(frame)
                sample_x.append(xx); samples.append(frame)
    all_samples = pd.concat(samples, ignore_index=True)
    all_x = np.concatenate(sample_x)
    pooled_indices = np.asarray(pooled_indices, dtype=int)
    with prohibit_fitting(), threadpool_limits(config["threads"]):
        pooled_frame = all_samples.iloc[pooled_indices]
        row, detail, point = evaluate_metrics(scaled(bundle, all_x[pooled_indices]),
            pooled_frame.cluster.to_numpy(), pooled_frame.observation_id, "pooled", config)
        metrics.append(row); details.extend(detail); points.extend(point)
    profile_tables = []
    for year, frame in all_samples.groupby("year"):
        table = physical_profiles(frame.assign(split=str(year)), frame.cluster.to_numpy(), contract)
        profile_tables.append(table)
    profile_tables.append(physical_profiles(all_samples.assign(split="pooled"), all_samples.cluster.to_numpy(), contract))
    profiles = pd.concat(profile_tables, ignore_index=True).rename(columns={"split": "period"})
    profiles["scope"] = "stage3_fixed_profile_sample"
    profiles["period"] = profiles.period.astype(str)
    all_samples.to_csv(evaluation / "profile_samples_and_membership.csv", index=False)
    profiles.to_csv(evaluation / "physical_profiles.csv", index=False)
    outputs = dict(metrics=metrics, per_cluster_silhouettes=details, silhouette_observations=points,
        distance_diagnostics=summaries, feature_drift=drift_rows, fixed_pc_drift=score_rows,
        bootstrap_intervals=bootstraps, retention=retention, reconstruction=reconstruction,
        physical_ordering=ordering_checks(profiles, config), area_weighted_occurrence=area_rows, **tables)
    for name, values in outputs.items():
        table = pd.DataFrame(values)
        if {"count", "total"}.issubset(table.columns):
            table["all_cell_fraction"] = table["count"] / table.total.replace(0, np.nan)
        table.to_csv(evaluation / f"{name}.csv", index=False)
    stability_rows = []
    yearly_metrics = pd.DataFrame(metrics)
    yearly_metrics = yearly_metrics[yearly_metrics.period != "pooled"]
    for column in ("silhouette", "calinski_harabasz", "davies_bouldin", "negative_silhouette_fraction"):
        values = yearly_metrics[column].dropna().to_numpy()
        stability_rows.append(dict(endpoint=column, years=len(values),
            minimum=float(values.min()) if len(values) else np.nan,
            median=float(np.median(values)) if len(values) else np.nan,
            maximum=float(values.max()) if len(values) else np.nan,
            interpretation="three annual point estimates; not a confidence interval"))
    annual_frame = pd.DataFrame(tables["annual_occurrence"])
    for k, group in annual_frame.groupby("cluster"):
        values = group.cloudy_fraction.to_numpy()
        stability_rows.append(dict(endpoint=f"cloudy_fraction_cluster_{k}", years=len(values),
            minimum=float(values.min()), median=float(np.median(values)), maximum=float(values.max()),
            interpretation="three annual population frequencies; not a confidence interval"))
    pd.DataFrame(stability_rows).to_csv(evaluation / "temporal_stability_summary.csv", index=False)
    plot_results(root, config, evaluation, figures, freeze_dir, all_samples, all_x, bundle)
    build_report(root, config, evaluation, frozen, profiles, reference_profile)
    # Recheck all existing artifacts and the immutable model; never update a freeze.
    load_freeze(root, run_id)
    for entry in frozen["expected_holdout_inputs"]:
        holdout_input_paths(root, entry, frozen)
    receipt = dict(status="complete", created_utc=utc_now(), refitted=False, tuned=False,
        model_sha256=frozen["model_sha256"], freeze_seal_sha256=sha256(freeze_dir / "seal.json"),
        holdout_years=config["holdout_years"], profile_sample_count=len(all_samples),
        metric_periods=[r["period"] for r in metrics], existing_artifacts_preserved=True,
        output_sha256={str(p.relative_to(root)): sha256(p) for directory in (evaluation, figures, labels_dir)
                       for p in sorted(directory.iterdir()) if p.is_file()})
    write_json(out / "evaluation_manifest.json", receipt)
    print(pd.DataFrame(metrics).to_string(index=False), flush=True)
    print("Complete: frozen temporal evaluation, no model refit or tuning.", flush=True)
    return receipt


def plot_results(root, config, evaluation, figures, freeze_dir, samples, x, bundle):
    def save(name):
        plt.tight_layout(); plt.savefig(figures / name, dpi=160, bbox_inches="tight"); plt.close()
    metrics = pd.read_csv(evaluation / "metrics.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, name in zip(axes, ("silhouette", "calinski_harabasz", "davies_bouldin")):
        ax.bar(metrics.period.astype(str), metrics[name]); ax.set(title=name, xlabel="Holdout period")
    save("holdout_metrics.png")
    old = pd.read_csv(root / "reports/phase2/pre_monsoon" / config["stage2_run_id"] / "annual_occurrence.csv")
    current = pd.read_csv(evaluation / "annual_occurrence.csv")
    combined = pd.concat([old, current], ignore_index=True)
    combined.pivot(index="year", columns="cluster", values="cloudy_fraction").plot(marker="o", figsize=(10, 4))
    plt.axvspan(2018.5, 2021.5, color="grey", alpha=.12, label="Reserved holdout")
    plt.ylabel("Fraction of eligible cloudy grid-cell hours"); plt.legend(); save("annual_occurrence.png")
    intervals = pd.read_csv(evaluation / "bootstrap_intervals.csv")
    primary = intervals[intervals.primary & intervals.endpoint.str.startswith("cloudy_cluster")]
    plt.figure(figsize=(8, 4))
    for k in range(config["n_clusters"]):
        rows = primary[primary.endpoint == f"cloudy_cluster_{k}"]
        # Moving-block percentile intervals need not bracket the empirical ratio.
        plt.vlines(rows.year + .05*k, rows.lower, rows.upper, label=f"Cluster {k} 95% within-window interval")
        plt.scatter(rows.year + .05*k, rows.estimate, s=25)
    plt.ylabel("Cloudy occurrence fraction"); plt.legend(fontsize=8); save("occurrence_uncertainty.png")
    hourly = pd.read_csv(evaluation / "diurnal_occurrence.csv").groupby(["utc_hour", "cluster"])[["count", "eligible"]].sum()
    (hourly["count"] / hourly.eligible).unstack().plot(figsize=(9, 4)); plt.ylabel("Cloudy occurrence fraction (UTC)"); save("diurnal_occurrence.png")
    scores = project(bundle, x, 2)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    stride = max(1, len(x)//6000)
    axes[0].scatter(*scores[::stride].T, c=samples.cluster.iloc[::stride], cmap="coolwarm", vmin=0, vmax=1, s=3)
    color = axes[1].scatter(*scores[::stride].T, c=samples.year.iloc[::stride], cmap="viridis", s=3)
    fig.colorbar(color, ax=axes[1], ticks=config["holdout_years"], label="Holdout year")
    for ax in axes: ax.set(xlabel="Frozen PC1", ylabel="Frozen PC2")
    axes[0].set_title("Frozen labels (blue=0, red=1)"); axes[1].set_title("No holdout PCA/t-SNE fit")
    save("fixed_pca_projection.png")
    spatial = pd.read_csv(evaluation / "spatial_occurrence.csv")
    old_spatial = pd.read_csv(root / "reports/phase2/pre_monsoon" / config["stage2_run_id"] / "spatial_occurrence.csv")
    hold = spatial.groupby(["cluster", "latitude", "longitude"])[["count", "eligible"]].sum()
    changes = []
    for period in [*config["holdout_years"], "pooled"]:
        selected = spatial if period == "pooled" else spatial[spatial.year == period]
        h = selected.groupby(["cluster", "latitude", "longitude"])[["count", "eligible", "total"]].sum()
        for reference in ("train", "development"):
            d = old_spatial[old_spatial.split == reference].groupby(["cluster", "latitude", "longitude"])[["count", "eligible", "total"]].sum()
            change = h.rename(columns={c: f"{c}_holdout" for c in h.columns}).join(
                d.rename(columns={c: f"{c}_reference" for c in d.columns}))
            change["cloudy_fraction_holdout"] = change.count_holdout / change.eligible_holdout.replace(0, np.nan)
            change["cloudy_fraction_reference"] = change.count_reference / change.eligible_reference.replace(0, np.nan)
            change["cloudy_fraction_difference"] = change.cloudy_fraction_holdout - change.cloudy_fraction_reference
            change["all_cell_fraction_difference"] = change.count_holdout / change.total_holdout - change.count_reference / change.total_reference
            changes.append(change.reset_index().assign(period=str(period), reference=reference))
    pd.concat(changes, ignore_index=True).to_csv(evaluation / "spatial_reference_changes.csv", index=False)
    fig, axes = plt.subplots(3, config["n_clusters"], figsize=(10, 12), squeeze=False)
    for k in range(config["n_clusters"]):
        h = hold.loc[k].copy(); h["fraction"] = h["count"] / h.eligible.replace(0, np.nan)
        table = h.fraction.unstack("longitude")
        im = axes[0,k].pcolormesh(table.columns, table.index, table.values, shading="auto", vmin=0, vmax=1)
        axes[0,k].set_title(f"Holdout cluster {k}"); fig.colorbar(im, ax=axes[0,k])
        for row, reference in enumerate(("train", "development"), start=1):
            d = old_spatial[(old_spatial.cluster == k) & (old_spatial.split == reference)].groupby(["latitude", "longitude"])[["count", "eligible"]].sum()
            diff = (h.fraction - d["count"] / d.eligible.replace(0, np.nan)).unstack("longitude")
            im = axes[row,k].pcolormesh(diff.columns, diff.index, diff.values, shading="auto", cmap="coolwarm", vmin=-.5, vmax=.5)
            axes[row,k].set_title(f"Holdout minus {reference}, cluster {k}"); fig.colorbar(im, ax=axes[row,k])
        for ax in axes[:,k]: ax.set(xlabel="Longitude °E", ylabel="Latitude °N")
    save("spatial_occurrence_and_change.png")
    profile = pd.read_csv(evaluation / "physical_profiles.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, name in zip(axes, ("cldarea_total_1h", "cldtau_total_1h", "cldpress_top_total_1h")):
        q = profile[(profile.variable == name) & (profile.period != "pooled")]
        q.pivot(index="period", columns="cluster", values="median").plot.bar(ax=ax)
        ax.set_title(name); ax.set_ylabel(q.units.iloc[0])
    save("physical_profile_medians.png")


def build_report(root, config, evaluation, frozen, profiles, reference_profile):
    metrics = pd.read_csv(evaluation / "metrics.csv")
    distance = pd.read_csv(evaluation / "distance_diagnostics.csv")
    ordering = pd.read_csv(evaluation / "physical_ordering.csv")
    retention = pd.read_csv(evaluation / "retention.csv")
    bootstrap = pd.read_csv(evaluation / "bootstrap_intervals.csv")
    annual = pd.read_csv(evaluation / "annual_occurrence.csv")
    baseline = pd.read_csv(root / "reports/phase2/pre_monsoon" / config["stage2_run_id"] / "cluster_selection.csv")
    selected = baseline[baseline.selected].iloc[0]
    pooled = metrics[metrics.period.astype(str) == "pooled"].iloc[0]
    primary_ci = bootstrap[bootstrap.primary & bootstrap.endpoint.str.startswith("cloudy_cluster")]
    all_supported = (ordering.result == "supported").all()
    issues = []
    if pooled.silhouette < selected.silhouette:
        issues.append(f"Pooled holdout silhouette ({pooled.silhouette:.6f}) is lower than selected development ({selected.silhouette:.6f}); no adaptation was performed.")
    if pooled.davies_bouldin > selected.davies_bouldin:
        issues.append("Pooled holdout Davies-Bouldin is less favorable than development.")
    if not all_supported:
        issues.append("At least one expected physical median ordering was reversed/equal or undefined; inspect physical_ordering.csv.")
    if (annual.cloudy_fraction < config["minimum_occupancy_flag"]).any():
        issues.append("At least one cluster occupies under 1% of eligible observations in a holdout year.")
    if not retention.sample_budget_met.all():
        issues.append("At least one year has inadequate eligible support for the fixed sample budget.")
    if not issues:
        issues.append("No listed ordering/occupancy/sample-support flag fired; this does not validate natural meteorological cloud classes.")
    text = ["# Reserved 2019-2021 pre-monsoon temporal evaluation", "",
        "The frozen Stage 2 training-only model was used unchanged. No refit, hyperparameter selection, "
        "threshold recalibration, holdout t-SNE or performance-driven model choice occurred. "
        "Features: cloud area /100, log1p optical depth, top pressure (hPa); full three-PC unwhitened basis and k=2.",
        f"Fit years: {config['fit_years']}; development: {config['development_years']}; holdout: {config['holdout_years']}.",
        f"Immutable model SHA256: {frozen['model_sha256']}.",
        f"Training-only nearest-centroid distance thresholds: {frozen['distance_thresholds']}.",
        "", "## Prespecified metrics", "", "```text", metrics.to_string(index=False), "```", "",
        f"Selected development reference: silhouette {selected.silhouette:.6f}, CH {selected.calinski_harabasz:.2f}, DB {selected.davies_bouldin:.6f} (n=3000). "
        "Yearly and balanced pooled holdout samples target n=3000. CH depends on n/geometry; comparisons are descriptive.",
        "", "## Negative and inconclusive findings", "", *["- " + issue for issue in issues], "",
        "Even favorable transfer cannot establish bimodality, natural cloud types, external geographical validity, "
        "causation, convection or precipitation classes. Internal indices favor specific distance geometry. "
        "Temperature/height diagnostics are related retrievals, not independent ground truth.",
        "", "## Coverage and distance diagnostics", "", "```text", retention.to_string(index=False), "```", "",
        "```text", distance.to_string(index=False), "```", "",
        "Distance exceedance is relative to frozen training quantiles, not a calibrated probability of model failure. "
        "Full-population distortion is mean squared distance to unchanged centroids. Feature drift uses fixed profile "
        "samples and training-SD-standardized Wasserstein distance. Fixed-PC variances are reported without refitting. "
        "Three-PC reconstruction is algebraically near zero and is not evidence of generalization.",
        "", "## Original-unit profiles and interpretation", "", "```text",
        profiles[profiles.variable.isin(config["expected_ordering"])][["period", "cluster", "variable", "units", "total", "valid", "median", "p10", "p90"]].to_string(index=False), "```", "",
        f"All frozen median-ordering checks supported: {bool(all_supported)}. "
        "Cluster IDs were not changed. All 13 original-unit properties, means/quantiles and retrieval-valid denominators "
        "are in physical_profiles.csv. Water paths condition on available retrievals; missing is not zero. "
        "Profiles use uniformly sampled eligible cloudy rows, not full-population quantiles. "
        "Pressure is not height above local terrain; the two partitions remain broad overlapping mixtures.",
        "", "## Temporal/spatial stability and uncertainty", "", "```text", annual.to_string(index=False), "```", "",
        "```text", primary_ci.to_string(index=False), "```", "",
        "Annual range is the primary evidence across the three reserved years. Intervals use 1000 joint-spatial "
        "moving-day-block replicates with primary length 3 days; 1/5-day sensitivity results are also saved. "
        "Labels and model parameters remain fixed during bootstrap. These are within-window intervals, not "
        "interannual climate CIs. No independent-row inference is used. UTC diurnal cycles are not local solar time. "
        "Transitions/persistence do not bridge clear/unknown states or annual gaps; censored runs are counted. "
        "Maps and cosine-latitude weighted annual frequencies describe this domain only.",
        "", "## Limitations and provenance", "",
        "Phase 1 examined 2010-2021, including feature availability/correlations. This is a reserved Phase 2 "
        "temporal test, not historically unseen confirmatory data. There are only three holdout years, sampled "
        "profile quantiles, selective retrieval availability and residual space/time dependence. Equal-year "
        "sample weighting differs slightly from all-grid-cell-hour occurrence weighting. The window is April 15-May 14, "
        "not the full calendar pre-monsoon season. Strong model-selection stability in Stage 2 is conditional "
        "on the feature representation and does not prove natural regimes.",
        "The freeze directory contains feature definitions, protocol, exact numeric training thresholds, selection "
        "evidence, model/code/protected-file hashes, package versions and seeds. Separate profile/year-metric/pooled "
        "sample memberships are saved. New annual labels, figures and CSVs live only in Phase 3 paths. "
        "evaluation_manifest.json inventories all result hashes; the standalone verifier and test logs provide "
        "integrity evidence. No Git commit/push/merge is performed. Any adaptation after these results is a new "
        "exploratory phase requiring separate validation."]
    (evaluation / "report.md").write_text("\n".join(text) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["freeze", "evaluate"])
    parser.add_argument("--run-id", default="stage3_v1")
    args = parser.parse_args()
    (freeze if args.command == "freeze" else evaluate)(run_id=args.run_id)
