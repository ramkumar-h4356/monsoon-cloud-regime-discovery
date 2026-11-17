"""Reproducible development-only experiments. No holdout NetCDF access."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import sys
import time

import joblib
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[2]
    / "data/processed/model_ready/phase2/matplotlib_cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.manifold import TSNE, trustworthiness
from sklearn.metrics import adjusted_rand_score
from sklearn.neighbors import NearestNeighbors
from threadpoolctl import threadpool_limits
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/06_feature_engineering"))
sys.path.insert(0, str(ROOT / "src/08_evaluation"))
from ceres_features import clean_variable, load_json, observation_ids, registry, sha256, split_map
from prepare_pre_monsoon import git_state
from pre_monsoon_stage2_model import (cluster_metrics, fit_preprocessing, initialization_stability,
    kmeans, matched_jaccard, pca_reconstruction, project, scaled, select_components, select_k,
    year_bootstrap_indices)
from pre_monsoon_stage2_diagnostics import (cautious_interpretations, physical_profiles,
                                           population_diagnostics)

ALLOWED_TRAIN = list(range(2010, 2017))
ALLOWED_DEVELOPMENT = [2017, 2018]


def allowed_year(year, split):
    if not ((split == "train" and year in ALLOWED_TRAIN)
            or (split == "development" and year in ALLOWED_DEVELOPMENT)):
        raise ValueError(f"Stage 2 forbids input year/split {year}/{split}")


def input_path(root, config, year, split, prepared=True):
    allowed_year(year, split)
    if prepared:
        return (root / "data/processed/model_ready/phase2/pre_monsoon" / config["stage1_run_id"]
                / f"CERES_{year}_pre_monsoon_prepared.nc")
    return root / f"data/interim/ceres_seasonal/pre_monsoon/CERES_{year}_pre_monsoon.nc"


def verify_stage1(root, config):
    if config["season"] != "pre_monsoon":
        raise ValueError("Only pre_monsoon is authorized")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", config["stage1_run_id"]):
        raise ValueError("Invalid Stage 1 run ID")
    reports = root / "reports/phase2/pre_monsoon" / config["stage1_run_id"]
    manifest = load_json(reports / "manifest.json")
    if manifest["status"] != "complete" or not manifest["phase1_preserved"]:
        raise ValueError("Stage 1 is not complete/preserved")
    splits = split_map(manifest["config"])
    if (manifest["config"]["train_years"] != ALLOWED_TRAIN
            or manifest["config"]["development_years"] != ALLOWED_DEVELOPMENT
            or manifest["config"]["holdout_years"] != [2019, 2020, 2021]):
        raise ValueError("Stage 1 temporal protocol changed")
    contract_path = root / "config/ceres_feature_definitions.json"
    if sha256(contract_path) != manifest["contract_sha256"]:
        raise ValueError("Shared feature definitions changed after Stage 1")
    contract = load_json(contract_path)
    expected = ["cloud_area_fraction", "log1p_optical_depth", "cloud_top_pressure_hpa"]
    if manifest["primary_feature_order"] != expected or [f["output"] for f in contract["primary"]] != expected:
        raise ValueError("Unexpected primary feature order")
    protected = dict(manifest["protected_files"])
    for path, digest in protected.items():
        if sha256(root / path) != digest:
            raise ValueError(f"Protected Stage 1/Phase 1 artifact changed: {path}")
    verified = []
    # Do not even hash holdout NetCDFs. Stage 1 report tables are protocol records only.
    prepared_paths = {str(input_path(root, config, y, s).relative_to(root))
                      for y, s in splits.items() if s != "holdout"}
    for path, digest in manifest["output_sha256"].items():
        if path.endswith(".nc") and path not in prepared_paths:
            continue
        if sha256(root / path) != digest:
            raise ValueError(f"Stage 1 artifact hash mismatch: {path}")
        verified.append(path)
    samples = pd.read_csv(reports / "sample_manifest.csv")
    if samples.observation_id.duplicated().any():
        raise ValueError("Duplicate sample observation IDs")
    counts = pd.read_csv(reports / "year_split_counts.csv")
    for row in samples[["year", "split"]].drop_duplicates().itertuples(index=False):
        allowed_year(row.year, row.split)
    for year in ALLOWED_TRAIN + ALLOWED_DEVELOPMENT:
        row = counts[counts.year == year]
        sample = samples[samples.year == year]
        if len(row) != 1 or len(sample) != int(row.iloc[0].sampled) or len(sample) == 0:
            raise ValueError("Stage 1 sample counts do not match manifest")
        if not (sample.split == splits[year]).all():
            raise ValueError("Sample split leakage")
    return manifest, contract, samples, protected, verified


def load_samples(root, config, contract, samples, stage1):
    features = stage1["primary_feature_order"]
    specs = registry(contract)
    x_parts, physical_parts, accessed = [], [], []
    for year in ALLOWED_TRAIN + ALLOWED_DEVELOPMENT:
        split = "train" if year in ALLOWED_TRAIN else "development"
        part = samples[samples.year == year].copy().reset_index(drop=True)
        indices = part.flat_index.to_numpy(dtype=int)
        pp = input_path(root, config, year, split)
        raw = input_path(root, config, year, split, prepared=False)
        for path in (pp, raw):
            accessed.append(dict(path=str(path.relative_to(root)), sha256=sha256(path), year=year, split=split))
        expected_raw = next(s["sha256"] for s in stage1["sources"] if s["year"] == year)
        if accessed[-1]["sha256"] != expected_raw:
            raise ValueError("Source hash differs from Stage 1")
        with xr.open_dataset(pp) as ds:
            if (ds.attrs["split"] != split or ds.attrs["season"] != "pre_monsoon"
                    or ds.attrs["feature_contract_sha256"] != stage1["contract_sha256"]):
                raise ValueError("Prepared metadata mismatch")
            if not ds.eligible.values.ravel()[indices].all():
                raise ValueError("Sample includes ineligible observations")
            if observation_ids(ds, indices, "pre_monsoon") != part.observation_id.tolist():
                raise ValueError("Sample identity mismatch")
            x = np.column_stack([ds[name].values.ravel()[indices] for name in features]).astype("float64")
            if not np.isfinite(x).all():
                raise ValueError("Stage 1 eligible sample must be complete")
        with xr.open_dataset(raw) as ds:
            for name in config["profile_variables"]:
                values, _, _ = clean_variable(ds[name], specs[name])
                part[name] = values.ravel()[indices]
        x_parts.append(x)
        physical_parts.append(part)
    return np.concatenate(x_parts), pd.concat(physical_parts, ignore_index=True), accessed


def fixed_subset(indices, size, seed):
    indices = np.asarray(indices)
    return np.sort(np.random.default_rng(seed).choice(indices, min(size, len(indices)), replace=False))


def balanced_subset(years, size, seed):
    years = np.asarray(years)
    unique = np.unique(years)
    allocations = [size // len(unique) + (i < size % len(unique)) for i in range(len(unique))]
    return np.sort(np.concatenate([fixed_subset(np.flatnonzero(years == y), n, seed + int(y))
                                   for y, n in zip(unique, allocations)]))


def save_plot(path):
    plt.tight_layout()
    plt.savefig(path, dpi=160, bbox_inches="tight")
    plt.close()


def plot_pca(bundle, feature_names, figures):
    pca = bundle["pca"]
    pcs = np.arange(1, pca.n_components_ + 1)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(pcs, pca.explained_variance_ratio_)
    axes[0].set(xlabel="Principal component", ylabel="Training explained variance fraction", xticks=pcs)
    axes[1].plot(pcs, np.cumsum(pca.explained_variance_ratio_), "o-")
    axes[1].axhline(.95, color="grey", linestyle="--", label="95%")
    axes[1].set(xlabel="Components retained", ylabel="Cumulative training variance", xticks=pcs, ylim=(0, 1.03))
    axes[1].legend()
    fig.suptitle("Pre-monsoon PCA fitted on 2010–2016 sample")
    save_plot(figures / "pca_scree.png")
    plt.figure(figsize=(8, 3))
    plt.imshow(pca.components_, cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")
    plt.xticks(range(len(feature_names)), feature_names, rotation=15, ha="right")
    plt.yticks(range(len(pcs)), [f"PC{i}" for i in pcs])
    plt.colorbar(label="Signed component coefficient")
    save_plot(figures / "pca_coefficients.png")


def cluster_experiments(x, frame, bundle, n_components, config, reports, models):
    training = frame.split.to_numpy() == "train"
    development = ~training
    z = scaled(bundle, x)
    scores = bundle["pca"].transform(z)[:, :n_components]
    train_eval = fixed_subset(np.flatnonzero(training), config["metric_sample_size"], config["seed"] + 1)
    dev_eval = fixed_subset(np.flatnonzero(development), config["metric_sample_size"], config["seed"] + 2)
    pd.DataFrame(dict(sample_row=np.r_[train_eval, dev_eval],
        split=frame.iloc[np.r_[train_eval, dev_eval]].split.to_numpy(),
        observation_id=frame.iloc[np.r_[train_eval, dev_eval]].observation_id.to_numpy())).to_csv(
            reports / "metric_sample_ids.csv", index=False)
    metrics, per_cluster, initialization, bootstrap, fit_rows = [], [], [], [], []
    fitted = {}
    base_inertia = float(((scores[training] - scores[training].mean(axis=0)) ** 2).sum())
    fit_rows.append(dict(k=1, inertia=base_inertia, iterations=0, seconds=0, converged=True))
    for k in config["k_values"]:
        print(f"K-Means k={k}: main fit, metrics and initialization stability", flush=True)
        start = time.perf_counter()
        model = kmeans(config, k, config["seed"]).fit(scores[training])
        fitted[k] = model
        joblib.dump(model, models / f"kmeans_k{k}.joblib")
        fit_rows.append(dict(k=k, inertia=float(model.inertia_), iterations=int(model.n_iter_),
            seconds=time.perf_counter() - start, converged=bool(model.n_iter_ < config["kmeans_max_iter"])))
        for split, indices in (("train", train_eval), ("development", dev_eval)):
            labels = model.predict(scores[indices])
            for space, values in (("retained_pca", scores), ("scaled_original", z)):
                row, details = cluster_metrics(values[indices], labels)
                metrics.append(dict(k=k, split=split, space=space,
                    distortion=float(np.min(model.transform(scores[indices]), axis=1).dot(
                        np.min(model.transform(scores[indices]), axis=1)) / len(indices)), **row))
                per_cluster.extend(dict(k=k, split=split, space=space, **d) for d in details)
        predictions = {}
        for seed in config["initialization_seeds"]:
            alternative = kmeans(config, k, seed, n_init=1).fit(scores[training])
            predictions[seed] = alternative.predict(scores[development])
        initialization.extend(initialization_stability(predictions, k))
    # Same bootstrap year draws for every k; the entire preprocessing is refitted.
    train_x = x[training]
    train_years = frame.loc[training, "year"].to_numpy()
    reference_x = x[development]
    baseline_labels = {k: model.predict(scores[development]) for k, model in fitted.items()}
    for seed in config["bootstrap_seeds"]:
        indices, chosen_years = year_bootstrap_indices(train_years, seed)
        boot_bundle = fit_preprocessing(train_x[indices])
        boot_scores = project(boot_bundle, train_x[indices], n_components)
        boot_reference = project(boot_bundle, reference_x, n_components)
        for k, main in fitted.items():
            print(f"Year-bootstrap seed={seed}, k={k}", flush=True)
            alternative = kmeans(config, k, seed, n_init=config["bootstrap_n_init"]).fit(boot_scores)
            prediction = alternative.predict(boot_reference)
            mean_j, min_j = matched_jaccard(baseline_labels[k], prediction, k)
            # Map each centroid back through its own fit into common transformed-feature units.
            def centers_in_feature_space(preprocessing, centers):
                pca = preprocessing["pca"]
                zz = centers @ pca.components_[:n_components] + pca.mean_
                return preprocessing["scaler"].inverse_transform(zz)
            a = centers_in_feature_space(bundle, main.cluster_centers_)
            b = centers_in_feature_space(boot_bundle, alternative.cluster_centers_)
            distance = np.linalg.norm((a[:, None] - b[None, :]) / bundle["scaler"].scale_, axis=2)
            ri, ci = linear_sum_assignment(distance)
            bootstrap.append(dict(k=k, seed=seed, chosen_years=json.dumps(chosen_years.tolist()),
                ari=float(adjusted_rand_score(baseline_labels[k], prediction)),
                matched_jaccard_mean=mean_j, matched_jaccard_min=min_j,
                centroid_displacement_training_sd=float(distance[ri, ci].mean())))
    selected, selection = select_k(metrics, initialization, bootstrap, config)
    for name, rows in (("kmeans_metrics", metrics), ("per_cluster_silhouettes", per_cluster),
                       ("initialization_stability", initialization), ("sampling_stability", bootstrap),
                       ("kmeans_fits", fit_rows)):
        pd.DataFrame(rows).to_csv(reports / f"{name}.csv", index=False)
    selection.to_csv(reports / "cluster_selection.csv", index=False)
    # Keep all candidates even when no scientifically admissible resolution exists.
    return selected, fitted, scores, metrics, selection


def tsne_experiments(x, frame, bundle, n_components, labels, config, reports, figures):
    indices = balanced_subset(frame.year.to_numpy(), config["tsne_sample_size"], config["seed"] + 3)
    input_pcs = project(bundle, x[indices], max(2, n_components))
    original = scaled(bundle, x[indices])
    trust_indices = fixed_subset(np.arange(len(indices)), config["tsne_trust_sample_size"], config["seed"] + 4)
    sample = frame.iloc[indices][["year", "split", "observation_id"]].copy()
    sample["sample_row"] = indices
    sample["trust_evaluation"] = np.isin(np.arange(len(indices)), trust_indices)
    sample["cluster"] = labels[indices]
    sample.to_csv(reports / "tsne_sample_ids.csv", index=False)
    experiments = [dict(name="baseline", perplexity=p, seed=seed, learning_rate="auto",
                        early_exaggeration=12, init="pca")
                   for p in config["tsne_perplexities"] for seed in config["tsne_seeds"]]
    experiments += [dict(perplexity=config["tsne_perplexities"][1], seed=config["seed"], **spec)
                    for spec in config["tsne_sensitivities"]]
    records, embeddings, neighbor_sets = [], {}, {}
    for spec in experiments:
        tag = f"{spec['name']}_p{spec['perplexity']}_s{spec['seed']}"
        print(f"t-SNE {tag}", flush=True)
        start = time.perf_counter()
        estimator = TSNE(n_components=2, perplexity=spec["perplexity"], random_state=spec["seed"],
            learning_rate=spec["learning_rate"], early_exaggeration=spec["early_exaggeration"],
            init=spec["init"], max_iter=config["tsne_max_iter"], method="barnes_hut", n_jobs=1)
        embedding = estimator.fit_transform(input_pcs)
        elapsed = time.perf_counter() - start
        embeddings[tag] = embedding
        pd.DataFrame(dict(observation_id=sample.observation_id.to_numpy(),
            tsne_1=embedding[:, 0], tsne_2=embedding[:, 1], cluster=sample.cluster.to_numpy(),
            year=sample.year.to_numpy())).to_csv(reports / f"tsne_{tag}.csv", index=False)
        record = dict(tag=tag, **spec, seconds=elapsed, kl_divergence=float(estimator.kl_divergence_),
            iterations=int(estimator.n_iter_), effective_learning_rate=float(estimator.learning_rate_),
            pca_dimensions=max(2, n_components))
        for space, values in (("pca", input_pcs), ("scaled_original", original)):
            for neighbors in config["trust_neighbors"]:
                record[f"trust_{space}_{neighbors}"] = float(trustworthiness(
                    values[trust_indices], embedding[trust_indices], n_neighbors=neighbors))
        records.append(record)
        neighbors = min(15, len(trust_indices) - 1)
        nn = NearestNeighbors(n_neighbors=neighbors + 1).fit(embedding[trust_indices])
        nearest = nn.kneighbors(embedding[trust_indices], return_distance=False)[:, 1:]
        neighbor_sets[tag] = nearest
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        a = axes[0].scatter(*embedding.T, c=sample.cluster, cmap="tab10", s=4, alpha=.65)
        fig.colorbar(a, ax=axes[0], label="K-Means label (from feature/PCA space)")
        b = axes[1].scatter(*embedding.T, c=sample.year, cmap="viridis", s=4, alpha=.65)
        fig.colorbar(b, ax=axes[1], label="Year (2010–2018 only)")
        for ax in axes:
            ax.set(xlabel="t-SNE 1 (arbitrary)", ylabel="t-SNE 2 (arbitrary)")
        fig.suptitle(f"Exploratory pre-monsoon t-SNE: {tag}; not evidence of discrete regimes")
        save_plot(figures / f"tsne_{tag}.png")
    table = pd.DataFrame(records)
    table.to_csv(reports / "tsne_metrics.csv", index=False)
    stability = []
    from itertools import combinations
    for perplexity in config["tsne_perplexities"]:
        group = table[(table.name == "baseline") & (table.perplexity == perplexity)]
        for a, b in combinations(group.tag, 2):
            overlap = [len(set(x) & set(y)) / len(x)
                       for x, y in zip(neighbor_sets[a], neighbor_sets[b])]
            stability.append(dict(perplexity=perplexity, tag_a=a, tag_b=b,
                                  neighbor_overlap_mean=float(np.mean(overlap))))
    pd.DataFrame(stability).to_csv(reports / "tsne_seed_stability.csv", index=False)
    columns = [f"trust_scaled_original_{n}" for n in config["trust_neighbors"]]
    ranked = table[table.name == "baseline"].copy()
    ranked["mean_original_trust"] = ranked[columns].mean(axis=1)
    ranking = ranked.groupby("perplexity").mean_original_trust.mean().sort_values(ascending=False)
    return {"display_perplexity": float(ranking.index[0]),
            "mean_original_trust": float(ranking.iloc[0]),
            "sample_size": len(indices), "pca_dimensions": max(2, n_components),
            "experiments": len(table)}


def full_population(root, config, contract, bundle, n_components, model, frame, reports, figures, labels_dir):
    rows = {}
    area_rows = []
    for year in ALLOWED_TRAIN + ALLOWED_DEVELOPMENT:
        split = "train" if year in ALLOWED_TRAIN else "development"
        print(f"Population diagnostics {year} ({split})", flush=True)
        with xr.open_dataset(input_path(root, config, year, split)) as prepared:
            status = prepared.status.values
            labels = np.where(status == 1, -1, -2).astype("int16")
            valid = np.flatnonzero(status.ravel() == 0)
            x = np.column_stack([prepared[name].values.ravel()[valid] for name in bundle["feature_order"]])
            predictions = np.empty(len(valid), dtype="int16")
            batch = config["prediction_batch_size"]
            for start in range(0, len(valid), batch):
                predictions[start:start + batch] = model.predict(project(bundle, x[start:start + batch], n_components))
            labels.ravel()[valid] = predictions
            labeled = xr.Dataset({"cluster": (("time", "lat", "lon"), labels)},
                                 coords={d: prepared[d] for d in ("time", "lat", "lon")})
            labeled.attrs.update(season="pre_monsoon", split=split, fit_years="2010-2016",
                                 contract_sha256=bundle["contract_sha256"], model_scope="stage2_training_only")
            labeled.cluster.attrs.update(clear_label=-1, unavailable_label=-2,
                                         description="Operational cloudy-regime labels; no natural-type validation")
            labeled.to_netcdf(labels_dir / f"CERES_{year}_pre_monsoon_labels.nc", engine="netcdf4",
                             encoding={"cluster": {"zlib": True, "complevel": 4}})
            diagnostics = population_diagnostics(prepared, labels, year, split, model.n_clusters)
            for name, values in diagnostics.items():
                rows.setdefault(name, []).extend(values)
            weights = np.broadcast_to(np.cos(np.deg2rad(prepared.lat.values))[None, :, None], labels.shape)
            denominator = float(weights[labels >= 0].sum())
            for cluster in range(model.n_clusters):
                area_rows.append(dict(year=year, split=split, cluster=cluster,
                    cosine_latitude_cloudy_fraction=float(weights[labels == cluster].sum() / denominator)))
    for name, values in rows.items():
        pd.DataFrame(values).to_csv(reports / f"{name}.csv", index=False)
    pd.DataFrame(area_rows).to_csv(reports / "area_weighted_occurrence.csv", index=False)
    annual = pd.DataFrame(rows["annual_occurrence"])
    annual.pivot(index="year", columns="cluster", values="cloudy_fraction").plot(marker="o", figsize=(9, 4))
    plt.ylabel("Fraction of eligible cloudy grid-cell hours")
    plt.title("Training-model regime occurrence: training and development years")
    save_plot(figures / "annual_occurrence.png")
    hourly = pd.DataFrame(rows["diurnal_occurrence"]).groupby(["utc_hour", "cluster"])[["count", "eligible"]].sum()
    (hourly["count"] / hourly["eligible"]).unstack().plot(figsize=(9, 4))
    plt.ylabel("Fraction of eligible cloudy observations")
    plt.title("2010–2018 UTC diurnal occurrence; not local solar time")
    save_plot(figures / "diurnal_occurrence.png")
    spatial = pd.DataFrame(rows["spatial_occurrence"]).groupby(["cluster", "latitude", "longitude"])[["count", "eligible"]].sum().reset_index()
    fig, axes = plt.subplots(1, model.n_clusters, figsize=(4 * model.n_clusters, 4), squeeze=False)
    for cluster, ax in enumerate(axes[0]):
        part = spatial[spatial.cluster == cluster].copy()
        part["fraction"] = part["count"] / part.eligible.replace(0, np.nan)
        table = part.pivot(index="latitude", columns="longitude", values="fraction")
        image = ax.pcolormesh(table.columns, table.index, table.values, vmin=0, vmax=1, shading="auto")
        ax.set(title=f"Cluster {cluster}", xlabel="Longitude °E", ylabel="Latitude °N")
        fig.colorbar(image, ax=ax, label="Cloudy occurrence fraction")
    fig.suptitle("2010–2018 descriptive spatial occurrence")
    save_plot(figures / "spatial_occurrence.png")


def run(root=ROOT, run_id="stage2_v1", config_path=None):
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id):
        raise ValueError("Invalid run ID")
    config_path = Path(config_path or root / "config/pre_monsoon_stage2.json")
    config = load_json(config_path)
    reports = root / "reports/phase2/pre_monsoon" / run_id
    figures = root / "results/figures/phase2/pre_monsoon" / run_id
    models = root / "results/models/phase2/pre_monsoon" / run_id
    labels_dir = root / "data/processed/model_ready/phase2/pre_monsoon" / run_id
    if any(p.exists() for p in (reports, figures, models, labels_dir)):
        raise FileExistsError("Stage 2 run paths exist; overwrite forbidden")
    stage1, contract, samples, protected, verified = verify_stage1(root, config)
    x, frame, accessed = load_samples(root, config, contract, samples, stage1)
    for directory in (reports, figures, models, labels_dir):
        directory.mkdir(parents=True)
    manifest_path = reports / "manifest.json"
    manifest = dict(status="incomplete", stage=2, season="pre_monsoon", run_id=run_id,
        created_utc=datetime.now(timezone.utc).isoformat(), config=config,
        contract_sha256=stage1["contract_sha256"], stage1_verified_artifacts=verified,
        stage1_manifest_sha256=sha256(root / "reports/phase2/pre_monsoon" / config["stage1_run_id"] / "manifest.json"),
        fit_years=ALLOWED_TRAIN, development_years=ALLOWED_DEVELOPMENT,
        holdout_accessed=False, holdout_evaluated=False, accessed_inputs=accessed,
        git=git_state(root), environment={"python": platform.python_version(),
            **{p: importlib.metadata.version(p) for p in
               ("numpy", "pandas", "xarray", "netCDF4", "scipy", "scikit-learn", "matplotlib", "joblib", "threadpoolctl")}},
        code_sha256={str(p.relative_to(root)): sha256(p) for folder in ("src", "config", "tests", "docs/methodology")
                     for p in (root / folder).rglob("*") if p.is_file() and p.suffix in (".py", ".json", ".md")},
        config_sha256=sha256(config_path))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with threadpool_limits(limits=config["threads"]):
        training = frame.split.to_numpy() == "train"
        bundle = fit_preprocessing(x[training])
        bundle.update(season="pre_monsoon", feature_order=stage1["primary_feature_order"],
            contract_sha256=stage1["contract_sha256"], fit_years=ALLOWED_TRAIN,
            training_observation_ids=frame.loc[training, "observation_id"].tolist(),
            eligibility_policy="Stage 1 complete valid cloudy observations only")
        reconstruction = pca_reconstruction(bundle, x[training], x[~training])
        n_components = select_components(reconstruction, config["pca_variance_target"],
                                         config["pca_max_development_feature_rmse"])
        bundle["selected_n_components"] = n_components
        joblib.dump(bundle, models / "preprocessing_pca.joblib")
        pd.DataFrame(reconstruction).to_csv(reports / "pca_reconstruction.csv", index=False)
        pd.DataFrame(reconstruction).pivot(index="n_components", columns="split",
            values="max_feature_rmse").plot(marker="o", figsize=(7, 4))
        plt.axhline(config["pca_max_development_feature_rmse"], color="grey", linestyle="--")
        plt.ylabel("Maximum per-feature reconstruction RMSE (training SD)")
        save_plot(figures / "pca_reconstruction.png")
        pca = bundle["pca"]
        pd.DataFrame(dict(component=np.arange(1, pca.n_components_ + 1),
            eigenvalue=pca.explained_variance_, individual_variance=pca.explained_variance_ratio_,
            cumulative_variance=np.cumsum(pca.explained_variance_ratio_))).to_csv(reports / "pca_variance.csv", index=False)
        z = scaled(bundle, x[training])
        scores = pca.transform(z)
        correlations = np.corrcoef(z.T, scores.T)[:x.shape[1], x.shape[1]:]
        loadings = [dict(component=i + 1, feature=feature, coefficient=float(pca.components_[i, j]),
            feature_pc_correlation=float(correlations[j, i]))
            for i in range(pca.n_components_) for j, feature in enumerate(bundle["feature_order"])]
        pd.DataFrame(loadings).to_csv(reports / "pca_loadings.csv", index=False)
        pd.DataFrame(dict(feature=bundle["feature_order"], imputation_median=bundle["imputer"].statistics_,
            scaling_mean=bundle["scaler"].mean_, scaling_std=bundle["scaler"].scale_,
            training_n=int(training.sum()))).to_csv(reports / "preprocessing_statistics.csv", index=False)
        plot_pca(bundle, bundle["feature_order"], figures)
        plt.figure(figsize=(8, 3))
        plt.imshow(correlations.T, cmap="coolwarm", vmin=-1, vmax=1, aspect="auto")
        plt.xticks(range(x.shape[1]), bundle["feature_order"], rotation=15, ha="right")
        plt.yticks(range(pca.n_components_), [f"PC{i+1}" for i in range(pca.n_components_)])
        plt.colorbar(label="Empirical training feature–PC correlation")
        save_plot(figures / "pca_correlation_loadings.png")
        selected_k, fitted, all_scores, metrics, selection = cluster_experiments(
            x, frame, bundle, n_components, config, reports, models)
        pd.DataFrame(metrics).query("space == 'scaled_original'").pivot(
            index="k", columns="split", values="silhouette").plot(marker="o", figsize=(8, 4))
        plt.ylabel("Silhouette (common scaled original space)")
        save_plot(figures / "cluster_silhouettes.png")
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        common = pd.DataFrame(metrics).query("space == 'scaled_original'")
        for ax, metric, title in zip(axes, ["calinski_harabasz", "davies_bouldin"],
                                    ["Calinski–Harabasz (higher favorable)", "Davies–Bouldin (lower favorable)"]):
            common.pivot(index="k", columns="split", values=metric).plot(ax=ax, marker="o")
            ax.set_ylabel(title)
        save_plot(figures / "cluster_ch_db.png")
        fits = pd.read_csv(reports / "kmeans_fits.csv")
        plt.figure(figsize=(7, 4))
        plt.plot(fits.k, fits.inertia, "o-")
        plt.xlabel("k"); plt.ylabel("Training inertia (retained PC space)")
        save_plot(figures / "cluster_elbow.png")
        if selected_k is None:
            manifest.update(status="no_admissible_cluster_count", selected_n_components=n_components)
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            (reports / "report.md").write_text("# Stage 2\nNo k passed preregistered stability/occupancy criteria. "
                "Review tables before further work; holdout remains untouched.\n", encoding="utf-8")
            return manifest
        model = fitted[selected_k]
        labels = model.predict(all_scores)
        bundle["kmeans"] = model
        joblib.dump(bundle, models / "selected_pre_monsoon_bundle.joblib")
        frame.assign(cluster=labels).to_csv(reports / "sample_physical_values_and_labels.csv", index=False)
        profiles = physical_profiles(frame, labels, contract)
        profiles.to_csv(reports / "physical_profiles.csv", index=False)
        interpretations = cautious_interpretations(profiles, selected_k)
        interpretations.to_csv(reports / "cautious_interpretations.csv", index=False)
        # Fixed selected k across all PC dimensions, scored in a common space.
        sensitivities = []
        dev_indices = fixed_subset(np.flatnonzero(~training), config["metric_sample_size"], config["seed"] + 2)
        for dimension in range(1, pca.n_components_ + 1):
            ss = project(bundle, x, dimension)
            alternative = kmeans(config, selected_k, config["seed"]).fit(ss[training])
            pred = alternative.predict(ss[dev_indices])
            row, _ = cluster_metrics(scaled(bundle, x[dev_indices]), pred)
            sensitivities.append(dict(n_components=dimension, k=selected_k,
                ari_to_selected=float(adjusted_rand_score(labels[dev_indices], pred)), **row))
        pd.DataFrame(sensitivities).to_csv(reports / "pca_clustering_sensitivity.csv", index=False)
        tsne = tsne_experiments(x, frame, bundle, n_components, labels, config, reports, figures)
        # PCA labels are independent of nonlinear embedding geometry.
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        idx = balanced_subset(frame.year, config["tsne_sample_size"], config["seed"] + 3)
        projection = project(bundle, x[idx], 2)
        axes[0].scatter(*projection.T, c=labels[idx], cmap="tab10", s=4)
        axes[1].scatter(*projection.T, c=frame.iloc[idx].year, cmap="viridis", s=4)
        for ax in axes:
            ax.set(xlabel="PC1", ylabel="PC2")
        axes[0].set_title("Training-model cluster labels")
        axes[1].set_title("Year (2010–2018)")
        save_plot(figures / "pca_labeled.png")
        for name in ("cldarea_total_1h", "cldtau_total_1h", "cldpress_top_total_1h"):
            profile = profiles[profiles.variable == name]
            profile.pivot(index="cluster", columns="split", values="median").plot.bar(figsize=(7, 4))
            plt.ylabel(f"Median {name} ({profile.units.iloc[0]})")
            save_plot(figures / f"physical_profile_{name}.png")
        full_population(root, config, contract, bundle, n_components, model, frame,
                        reports, figures, labels_dir)
    if any(sha256(root / path) != digest for path, digest in protected.items()):
        raise RuntimeError("Protected Phase 1/Stage 1 artifacts changed")
    if any(sha256(root / row["path"]) != row["sha256"] for row in accessed):
        raise RuntimeError("Stage 2 inputs changed during experiments")
    manifest.update(status="complete", selected_n_components=n_components, selected_k=selected_k,
        training_sample_count=int(training.sum()), development_sample_count=int((~training).sum()),
        tsne=tsne, phase1_stage1_preserved=True,
        pca_variance_threshold_dimensions={str(q): int(np.searchsorted(np.cumsum(pca.explained_variance_ratio_), q) + 1)
                                           for q in (.8, .9, .95)})
    selected = selection[selection.k == selected_k].iloc[0]
    report = ["# Pre-monsoon Stage 2 methodology and actual results", "",
        "Status: complete. Training fits: 2010–2016 only. Development diagnostics: 2017–2018 only.",
        "Holdout access/evaluation: none. No development-inclusive final refit.", "",
        f"Training sample: {int(training.sum()):,}; development: {int((~training).sum()):,}.",
        "Observation: hourly CERES grid cell; complete valid cloudy cases. Clear sky stays separate.",
        "Inputs: cloud area fraction, log1p optical depth, cloud-top pressure (hPa).",
        "Median imputer, StandardScaler and full-SVD unwhitened PCA fit on training sample only.",
        "Imputation is inert on this complete sample; no water-path gaps are filled.", "",
        f"Selected PCA components: {n_components}; criteria: >=95% training variance and "
        "maximum development per-feature reconstruction RMSE <=0.25 training SD.",
        f"Training explained variance fractions: {pca.explained_variance_ratio_.tolist()}.",
        "Component coefficients and feature-PC correlations are reported separately.", "",
        f"Selected operational cluster count: {selected_k}. Development silhouette "
        f"(common standardized space): {selected.silhouette:.4f}; CH: {selected.calinski_harabasz:.2f}; "
        f"DB: {selected.davies_bouldin:.4f}.",
        f"Median initialization ARI: {selected.initialization_ari_median:.4f}; "
        f"median year-bootstrap ARI: {selected.sampling_ari_median:.4f}.",
        "Selection: smallest admissible k within 0.02 of best development silhouette; "
        "minimum occupancy 1%, initialization/bootstrap median ARI >=0.8. All k metrics retained.", "",
        f"t-SNE: {tsne['experiments']} experiments on {tsne['sample_size']} fixed year-balanced points, "
        f"{tsne['pca_dimensions']} input PCs. Display perplexity: {tsne['display_perplexity']:g}; "
        f"mean original-space trustworthiness: {tsne['mean_original_trust']:.4f}.",
        "All seeds, trustworthiness neighborhoods, parameter sensitivities and coordinate tables are saved.",
        "Cluster labels come from feature/PCA space, never t-SNE. Island size/distance has no physical interpretation.",
        "", "## Cautious physical summaries (training sampled medians)", "", "```text",
        interpretations[["cluster", "label", "median_cloud_area_percent", "median_optical_depth",
                         "median_cloud_top_pressure_hpa"]].to_string(index=False), "```", "",
        "Pressure/optical-depth bins are descriptive, not validated cloud types or evidence of convection/rainfall.",
        "physical_profiles.csv includes original-unit spread and valid/missing denominators separately by split.",
        "Profile quantiles use the fixed sample. Annual/spatial/diurnal/daily occurrence and transitions use "
        "every eligible 2010–2018 observation; clear and unavailable labels remain explicit.",
        "", "## Limitations and remaining work", "",
        "K-Means partitions continuous, potentially non-spherical mixtures. Good internal metrics do not prove "
        "discrete meteorological regimes. Review per-cluster silhouette distributions and bootstrap variability.",
        "Only seven training years and two development years; five year bootstraps give limited stability evidence, "
        "not formal confidence intervals. Sample rows remain spatially/temporally dependent.",
        "Equal-year fitting samples differ slightly from full-population weighting. Grid-cell weighting is primary; "
        "cosine-latitude-weighted annual frequencies are a descriptive sensitivity. UTC is not local solar time.",
        "Water-path profiles are conditional on retrieval availability; phase is an aggregate index. "
        "No additional physics variable was used for fitting.",
        "Phase 1 examined 2010–2021; the reserved holdout is not historically unseen. "
        "Other seasons require separate fits under the unchanged shared contract.",
        "Stage 3 requires approval: review/freeze selected configuration and scientific interpretations, then "
        "separately authorize any development-inclusive final refit and final temporal holdout evaluation.", "",
        "See docs/methodology/pre_monsoon_stage2_protocol.md and config/pre_monsoon_stage2.json for exact rules. "
        "manifest.json records input/output/code/config hashes, versions, Git state and all accessed data years."]
    (reports / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest["output_sha256"] = {str(p.relative_to(root)): sha256(p)
        for directory in (reports, figures, models, labels_dir) for p in sorted(directory.iterdir())
        if p.is_file() and p != manifest_path}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("status", "selected_n_components", "selected_k", "tsne")}, indent=2), flush=True)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="stage2_v1")
    args = parser.parse_args()
    run(run_id=args.run_id)
