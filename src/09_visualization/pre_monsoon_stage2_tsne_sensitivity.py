"""Random-start t-SNE robustness and controlled exaggeration on saved development sample."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "data/processed/model_ready/phase2/matplotlib_cache"))
import joblib
import matplotlib
matplotlib.use("Agg")
from matplotlib.colors import BoundaryNorm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.manifold import TSNE, trustworthiness
from sklearn.neighbors import NearestNeighbors
from threadpoolctl import threadpool_limits
import xarray as xr

for folder in ("src/06_feature_engineering", "src/07_clustering"):
    sys.path.insert(0, str(ROOT / folder))
from ceres_features import load_json, observation_ids, sha256
from pre_monsoon_stage2_model import project, scaled
from run_pre_monsoon_stage2 import input_path, save_plot


def experiment_specs(config):
    specs = [dict(name="random_init", perplexity=p, seed=s, init="random",
                  learning_rate=config["fixed_learning_rate"],
                  early_exaggeration=config["early_exaggeration"])
             for p in config["perplexities"] for s in config["seeds"]]
    specs.append(dict(name="controlled_exaggeration", perplexity=config["controlled_perplexity"],
        seed=config["controlled_seed"], init="pca", learning_rate=config["fixed_learning_rate"],
        early_exaggeration=config["controlled_exaggeration"]))
    return specs


def run(root=ROOT, run_id="stage2_tsne_sensitivity_v1", config_path=None):
    root = Path(root).resolve()
    config_path = Path(config_path or root / "config/pre_monsoon_stage2_tsne_sensitivity.json")
    config = load_json(config_path)
    if not all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value)
               for value in (run_id, config["base_run_id"])):
        raise ValueError("Invalid run ID")
    reports = root / "reports/phase2/pre_monsoon" / run_id
    figures = root / "results/figures/phase2/pre_monsoon" / run_id
    if reports.exists() or figures.exists():
        raise FileExistsError("Sensitivity run already exists")
    base = root / "reports/phase2/pre_monsoon" / config["base_run_id"]
    manifest = load_json(base / "manifest.json")
    if manifest["status"] != "complete" or manifest["holdout_accessed"]:
        raise ValueError("Requires a complete development-only base run")
    model_path = root / "results/models/phase2/pre_monsoon" / config["base_run_id"] / "selected_pre_monsoon_bundle.joblib"
    if sha256(model_path) != manifest["output_sha256"][str(model_path.relative_to(root))]:
        raise ValueError("Model hash mismatch")
    bundle = joblib.load(model_path)
    if bundle["season"] != "pre_monsoon" or bundle["fit_years"] != list(range(2010, 2017)):
        raise ValueError("Wrong seasonal model or fit years")
    sample = pd.read_csv(base / "tsne_sample_ids.csv")
    physical = pd.read_csv(base / "sample_physical_values_and_labels.csv")
    for filename in ("tsne_sample_ids.csv", "sample_physical_values_and_labels.csv"):
        path = base / filename
        if sha256(path) != manifest["output_sha256"][str(path.relative_to(root))]:
            raise ValueError("Saved sample hash mismatch")
    chosen = physical.iloc[sample.sample_row.to_numpy(dtype=int)].reset_index(drop=True)
    if chosen.observation_id.tolist() != sample.observation_id.tolist():
        raise ValueError("Saved sample identity mismatch")
    x = np.empty((len(sample), len(bundle["feature_order"])))
    accessed = []
    for year, group in chosen.groupby("year", sort=True):
        split = str(group.split.iloc[0])
        path = input_path(root, manifest["config"], int(year), split)
        digest = sha256(path)
        expected = next(row["sha256"] for row in manifest["accessed_inputs"]
                        if row["path"] == str(path.relative_to(root)))
        if digest != expected:
            raise ValueError("Prepared data hash mismatch")
        accessed.append(dict(year=int(year), split=split, path=str(path.relative_to(root)), sha256=digest))
        with xr.open_dataset(path) as ds:
            indices = group.flat_index.to_numpy(dtype=int)
            if observation_ids(ds, indices, "pre_monsoon") != group.observation_id.tolist():
                raise ValueError("Prepared sample identity mismatch")
            x[group.index] = np.column_stack([ds[name].values.ravel()[indices] for name in bundle["feature_order"]])
    trust_indices = np.flatnonzero(sample.trust_evaluation.to_numpy(dtype=bool))
    pcs = project(bundle, x, max(2, bundle["selected_n_components"]))
    original = scaled(bundle, x)
    reports.mkdir(parents=True)
    figures.mkdir(parents=True)
    receipt = dict(status="incomplete", config=config, code_sha256=sha256(Path(__file__)),
        config_sha256=sha256(config_path), base_manifest_sha256=sha256(base / "manifest.json"),
        inputs=accessed, fitted_preprocessing=False, changed_cluster_selection=False,
        holdout_accessed=False, sample_size=len(x))
    receipt_path = reports / "manifest.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    rows, neighbors = [], {}
    with threadpool_limits(config["threads"]):
        for spec in experiment_specs(config):
            tag = f"{spec['name']}_p{spec['perplexity']}_s{spec['seed']}"
            print(f"Supplementary t-SNE: {tag}", flush=True)
            start = time.perf_counter()
            estimator = TSNE(n_components=2, random_state=spec["seed"],
                perplexity=spec["perplexity"], init=spec["init"], learning_rate=spec["learning_rate"],
                early_exaggeration=spec["early_exaggeration"], max_iter=config["max_iter"], n_jobs=1)
            embedding = estimator.fit_transform(pcs)
            row = dict(tag=tag, **spec, seconds=time.perf_counter() - start,
                kl_divergence=float(estimator.kl_divergence_), iterations=int(estimator.n_iter_))
            for space, values in (("pca", pcs), ("scaled_original", original)):
                for n in manifest["config"]["trust_neighbors"]:
                    row[f"trust_{space}_{n}"] = float(trustworthiness(values[trust_indices],
                        embedding[trust_indices], n_neighbors=n))
            rows.append(row)
            nearest = NearestNeighbors(n_neighbors=min(16, len(trust_indices))).fit(embedding[trust_indices])
            neighbors[tag] = nearest.kneighbors(embedding[trust_indices], return_distance=False)[:, 1:]
            pd.DataFrame(dict(observation_id=sample.observation_id, tsne_1=embedding[:, 0],
                tsne_2=embedding[:, 1], cluster=sample.cluster, year=sample.year)).to_csv(reports / f"{tag}.csv", index=False)
            fig, axes = plt.subplots(1, 2, figsize=(11, 4))
            k = bundle["kmeans"].n_clusters
            palette = plt.get_cmap("tab10", k)
            norm = BoundaryNorm(np.arange(k + 1) - .5, k)
            color = axes[0].scatter(*embedding.T, c=sample.cluster, cmap=palette, norm=norm, s=4, alpha=.65)
            fig.colorbar(color, ax=axes[0], ticks=np.arange(k), label="Feature-space K-Means label")
            color = axes[1].scatter(*embedding.T, c=sample.year, cmap="viridis", s=4, alpha=.65)
            fig.colorbar(color, ax=axes[1], ticks=sorted(sample.year.unique()), label="Year (2010–2018)")
            for ax in axes:
                ax.set(xlabel="t-SNE 1 (arbitrary)", ylabel="t-SNE 2 (arbitrary)")
            fig.suptitle(f"Exploratory random-start/parameter sensitivity: {tag}")
            save_plot(figures / f"{tag}.png")
    from itertools import combinations
    table = pd.DataFrame(rows)
    table.to_csv(reports / "tsne_metrics.csv", index=False)
    stability = []
    for perplexity in config["perplexities"]:
        tags = table[(table.name == "random_init") & (table.perplexity == perplexity)].tag
        for a, b in combinations(tags, 2):
            overlap = [len(set(x) & set(y)) / len(x) for x, y in zip(neighbors[a], neighbors[b])]
            stability.append(dict(perplexity=perplexity, tag_a=a, tag_b=b,
                                  neighbor_overlap_mean=float(np.mean(overlap))))
    pd.DataFrame(stability).to_csv(reports / "seed_stability.csv", index=False)
    receipt.update(status="complete", experiments=len(table),
        output_sha256={str(p.relative_to(root)): sha256(p)
                       for folder in (reports, figures) for p in sorted(folder.iterdir())
                       if p.is_file() and p != receipt_path})
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(table[["tag", "kl_divergence"]].to_string(index=False), flush=True)
    print(pd.DataFrame(stability).to_string(index=False), flush=True)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="stage2_tsne_sensitivity_v1")
    args = parser.parse_args()
    run(run_id=args.run_id)
