"""Training isolation, metrics, time diagnostics and synthetic Stage 2 integration."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from threadpoolctl import threadpool_limits
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
for folder in ("src/06_feature_engineering", "src/07_clustering", "src/08_evaluation"):
    sys.path.insert(0, str(ROOT / folder))
from ceres_features import load_json, observation_ids, prepare, registry, sha256
from pre_monsoon_stage2_model import (cluster_metrics, fit_preprocessing, initialization_stability,
    matched_jaccard, pca_reconstruction, project, scaled, select_components, select_k, year_bootstrap_indices)
from pre_monsoon_stage2_diagnostics import physical_profiles, population_diagnostics
from run_pre_monsoon_stage2 import allowed_year, balanced_subset, input_path, run, verify_stage1

CONTRACT = load_json(ROOT / "config/ceres_feature_definitions.json")
STAGE1_CONFIG = load_json(ROOT / "config/pre_monsoon_stage1.json")
CONFIG = load_json(ROOT / "config/pre_monsoon_stage2.json")


class Stage2UnitTests(unittest.TestCase):
    def test_training_only_fit_and_imputation(self):
        x = np.array([[1, 2, 3], [2, 4, 5], [3, 6, 8], [4, 8, np.nan]], dtype=float)
        bundle = fit_preprocessing(x)
        np.testing.assert_allclose(bundle["imputer"].statistics_, [2.5, 5, 5])
        mean = bundle["scaler"].mean_.copy()
        median = bundle["imputer"].statistics_.copy()
        scaled(bundle, [[1000000, 2000000, np.nan]])
        np.testing.assert_array_equal(bundle["scaler"].mean_, mean)
        np.testing.assert_array_equal(bundle["imputer"].statistics_, median)
        self.assertEqual(bundle["scaler"].n_samples_seen_, 4)
        with self.assertRaises(ValueError):
            fit_preprocessing([[1, np.nan], [2, np.nan]])

    def test_pca_criteria_and_full_dimension_distances(self):
        rng = np.random.default_rng(11)
        x = rng.normal(size=(100, 3))
        bundle = fit_preprocessing(x)
        rows = pca_reconstruction(bundle, x, x + .1)
        self.assertEqual(select_components(rows, .95, .25), 3)
        self.assertAlmostEqual(np.linalg.norm(scaled(bundle, x)[0] - scaled(bundle, x)[1]),
                               np.linalg.norm(project(bundle, x, 3)[0] - project(bundle, x, 3)[1]))
        self.assertLess(max(r["max_feature_rmse"] for r in rows if r["n_components"] == 3), 1e-12)

    def test_metrics_and_permutation_stability(self):
        x = np.array([[0, 0], [.1, 0], [0, .1], [10, 10], [10.1, 10], [10, 10.1]])
        labels = np.array([0, 0, 0, 1, 1, 1])
        metrics, details = cluster_metrics(x, labels)
        self.assertGreater(metrics["silhouette"], .9)
        self.assertEqual(len(details), 2)
        self.assertEqual(matched_jaccard(labels, 1 - labels, 2), (1.0, 1.0))
        rows = initialization_stability({42: labels, 73: 1 - labels}, 2)
        self.assertEqual(rows[0]["ari"], 1)
        invalid, _ = cluster_metrics(x, np.zeros(len(x)))
        self.assertTrue(np.isnan(invalid["silhouette"]))

    def test_year_blocks_and_year_balanced_sampling(self):
        years = np.repeat([2010, 2011, 2012], 10)
        indices, chosen = year_bootstrap_indices(years, 42)
        self.assertEqual(len(indices), len(years))
        for year in np.unique(chosen):
            expected = int((chosen == year).sum())
            for index in np.flatnonzero(years == year):
                self.assertEqual(int((indices == index).sum()), expected)
        sample = balanced_subset(years, 14, 42)
        self.assertLessEqual(pd.Series(years[sample]).value_counts().max()
                             - pd.Series(years[sample]).value_counts().min(), 1)

    def test_holdout_paths_are_forbidden(self):
        for year in [2009, 2019, 2020, 2021, 2022]:
            with self.assertRaises(ValueError):
                input_path(ROOT, CONFIG, year, "train")
        with self.assertRaises(ValueError):
            allowed_year(2018, "train")
        with self.assertRaises(ValueError):
            allowed_year(2016, "development")

    def test_selection_does_not_silently_relax(self):
        metrics = [dict(k=k, split="development", space="scaled_original", silhouette=s,
                        minimum_cluster_fraction=.2, observed_clusters=k)
                   for k, s in [(2, .5), (3, .51), (4, .55)]]
        stable = [dict(k=k, ari=.95) for k in [2, 3, 4]]
        selected, _ = select_k(metrics, stable, stable, CONFIG)
        self.assertEqual(selected, 4)
        unstable = [dict(k=k, ari=.2) for k in [2, 3, 4]]
        self.assertIsNone(select_k(metrics, stable, unstable, CONFIG)[0])

    def test_physical_profiles_keep_retrieval_denominators(self):
        frame = pd.DataFrame(dict(split=["train"] * 4, iwp_total_1h=[np.nan, 4, np.nan, 8]))
        profiles = physical_profiles(frame, np.zeros(4, dtype=int), CONTRACT)
        self.assertEqual(profiles.iloc[0].valid, 2)
        self.assertEqual(profiles.iloc[0]["missing"], 2)
        self.assertEqual(profiles.iloc[0]["mean"], 6)
        self.assertEqual(profiles.iloc[0].units, "g m-2")

    def test_persistence_breaks_on_clear_and_never_crosses_years(self):
        labels = np.array([0, 0, -1, 1, 1, 0], dtype="int16").reshape(6, 1, 1)
        ds = xr.Dataset({"status": (("time", "lat", "lon"), np.where(labels == -1, 1, 0))},
            coords={"time": pd.date_range("2010-04-15", periods=6, freq="h"), "lat": [10], "lon": [70]})
        result = population_diagnostics(ds, labels, 2010, "train", 2)
        transitions = pd.DataFrame(result["transitions"])
        self.assertEqual(int(transitions["count"].sum()), 3)
        self.assertEqual(sum(r["runs"] for r in result["persistence"]), 3)
        self.assertEqual(sum(r["count"] for r in result["annual_occurrence"]), 5)


def fixture(root):
    (root / "config").mkdir()
    contract_path = root / "config/ceres_feature_definitions.json"
    contract_path.write_text(json.dumps(CONTRACT))
    config = copy.deepcopy(CONFIG)
    config.update(k_values=[2, 3], kmeans_n_init=2, kmeans_max_iter=100,
        initialization_seeds=[42, 73], bootstrap_seeds=[307, 401], bootstrap_n_init=2,
        metric_sample_size=60, minimum_cluster_fraction=.001, minimum_stability_ari=0,
        tsne_sample_size=120, tsne_trust_sample_size=80, trust_neighbors=[3, 5],
        tsne_perplexities=[5, 10], tsne_seeds=[42, 73], tsne_max_iter=300,
        tsne_sensitivities=[], prediction_batch_size=50)
    (root / "config/pre_monsoon_stage2.json").write_text(json.dumps(config))
    reports = root / "reports/phase2/pre_monsoon/stage1_v1"
    reports.mkdir(parents=True)
    prepared_dir = root / "data/processed/model_ready/phase2/pre_monsoon/stage1_v1"
    prepared_dir.mkdir(parents=True)
    raw_dir = root / "data/interim/ceres_seasonal/pre_monsoon"
    raw_dir.mkdir(parents=True)
    samples, counts, sources, hashes = [], [], [], {}
    for year in range(2010, 2019):
        split = "train" if year < 2017 else "development"
        rng = np.random.default_rng(year)
        shape = (30, 2, 3)
        group = rng.integers(0, 3, size=shape)
        ds = xr.Dataset(coords={"time": pd.date_range(f"{year}-04-15T00:30", periods=30, freq="h"),
                                "lat": [10., 20.], "lon": [70., 80., 90.]})
        for name, spec in registry(CONTRACT).items():
            values = np.full(shape, sum(spec["range"]) / 2, dtype="float32")
            ds[name] = (("time", "lat", "lon"), values)
            ds[name].attrs["units"] = spec["units"]
        ds.cldarea_total_1h.values[:] = (np.array([25, 60, 95])[group] + rng.normal(0, 1, shape)).astype("float32")
        ds.cldtau_total_1h.values[:] = (np.array([2, 10, 60])[group] + rng.uniform(0, 1, shape)).astype("float32")
        ds.cldpress_top_total_1h.values[:] = (np.array([850, 550, 200])[group] + rng.normal(0, 3, shape)).astype("float32")
        raw_path = raw_dir / f"CERES_{year}_pre_monsoon.nc"
        ds.to_netcdf(raw_path, engine="netcdf4")
        sources.append(dict(year=year, split=split, sha256=sha256(raw_path)))
        out = prepare(ds, CONTRACT)
        out.attrs.update(split=split, season="pre_monsoon", feature_contract_sha256=sha256(contract_path))
        path = prepared_dir / f"CERES_{year}_pre_monsoon_prepared.nc"
        out.to_netcdf(path, engine="netcdf4")
        hashes[str(path.relative_to(root))] = sha256(path)
        indices = np.arange(0, np.prod(shape), 2)
        for index, identity in zip(indices, observation_ids(ds, indices, "pre_monsoon")):
            samples.append(dict(year=year, split=split, flat_index=int(index), observation_id=identity))
        counts.append(dict(year=year, split=split, sampled=len(indices)))
    for name, rows in (("sample_manifest.csv", samples), ("year_split_counts.csv", counts)):
        path = reports / name
        pd.DataFrame(rows).to_csv(path, index=False)
        hashes[str(path.relative_to(root))] = sha256(path)
    manifest = dict(status="complete", phase1_preserved=True, config=STAGE1_CONFIG,
        contract_sha256=sha256(contract_path), protected_files={}, output_sha256=hashes,
        primary_feature_order=[f["output"] for f in CONTRACT["primary"]], sources=sources)
    (reports / "manifest.json").write_text(json.dumps(manifest))
    return config


class Stage2IntegrationTests(unittest.TestCase):
    def test_synthetic_end_to_end_without_any_holdout_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = fixture(root)
            real_open = xr.open_dataset
            opened = []
            def guarded_open(path, *args, **kwargs):
                path = str(path)
                self.assertFalse(any(f"CERES_{year}_" in path for year in [2019, 2020, 2021]))
                opened.append(path)
                return real_open(path, *args, **kwargs)
            with patch("xarray.open_dataset", side_effect=guarded_open), threadpool_limits(1):
                result = run(root, "synthetic_stage2")
            self.assertEqual(result["status"], "complete")
            self.assertFalse(result["holdout_accessed"])
            self.assertEqual(result["fit_years"], list(range(2010, 2017)))
            self.assertTrue(all(s["year"] < 2019 for s in result["accessed_inputs"]))
            self.assertGreater(len(opened), 0)
            self.assertTrue(all(sha256(root / p) == h for p, h in result["output_sha256"].items()))
            bundle = joblib.load(root / "results/models/phase2/pre_monsoon/synthetic_stage2/selected_pre_monsoon_bundle.joblib")
            self.assertEqual(bundle["scaler"].n_samples_seen_, 630)
            self.assertEqual(len(bundle["training_observation_ids"]), 630)
            self.assertTrue(all("2017-" not in s and "2018-" not in s for s in bundle["training_observation_ids"]))
            report_dir = root / "reports/phase2/pre_monsoon/synthetic_stage2"
            profiles = pd.read_csv(report_dir / "physical_profiles.csv")
            self.assertIn("g m-2", profiles.units.tolist())
            labels = pd.read_csv(report_dir / "sample_physical_values_and_labels.csv")
            x = np.column_stack([labels.cldarea_total_1h / 100, np.log1p(labels.cldtau_total_1h),
                                 labels.cldpress_top_total_1h])
            predicted = bundle["kmeans"].predict(project(bundle, x, bundle["selected_n_components"]))
            self.assertEqual(adjusted_rand_score(labels.cluster, predicted), 1)
            with self.assertRaises(FileExistsError):
                run(root, "synthetic_stage2")
            # A corrupted Stage 1 input must fail before new outputs are created.
            source = root / "data/processed/model_ready/phase2/pre_monsoon/stage1_v1/CERES_2010_pre_monsoon_prepared.nc"
            with source.open("ab") as stream:
                stream.write(b"changed")
            with self.assertRaisesRegex(ValueError, "hash"):
                verify_stage1(root, config)


if __name__ == "__main__":
    unittest.main()
