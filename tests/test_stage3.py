"""Freeze gate, no-refit evaluation, dependent bootstrap and synthetic integration."""
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
from threadpoolctl import threadpool_limits
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
for folder in ("src/06_feature_engineering", "src/07_clustering", "src/08_evaluation"):
    sys.path.insert(0, str(ROOT / folder))
from ceres_features import load_json, observation_ids, prepare, registry, sha256
from pre_monsoon_stage2_model import fit_preprocessing, kmeans, project
from pre_monsoon_stage2_diagnostics import physical_profiles, population_diagnostics
from pre_monsoon_stage3_tools import (bootstrap_fractions, evaluate_metrics, moving_day_indices,
                                     nested_samples, ordering_checks, prohibit_fitting)
from run_pre_monsoon_stage3 import evaluate, freeze, load_freeze
from verify_pre_monsoon_stage3 import verify

CONFIG = load_json(ROOT / "config/pre_monsoon_stage3.json")
CONTRACT = load_json(ROOT / "config/ceres_feature_definitions.json")


class Stage3CalculationTests(unittest.TestCase):
    def test_nested_samples_reproducible_and_not_label_selected(self):
        config = dict(CONFIG, profile_sample_per_year=50, metric_sample_per_year=20,
                      pooled_metric_sample_per_year=5)
        p, m, q = nested_samples(np.arange(200), 2019, config)
        self.assertEqual((len(p), len(m), len(q)), (50, 20, 5))
        self.assertTrue(set(q) <= set(m) <= set(p))
        for a, b in zip((p, m, q), nested_samples(np.arange(200), 2019, config)):
            np.testing.assert_array_equal(a, b)
        self.assertFalse(np.array_equal(p, nested_samples(np.arange(200), 2020, config)[0]))

    def test_moving_blocks_are_contiguous_and_non_circular(self):
        indices = moving_day_indices(30, 3, [42, 3, 2019, 3, 3], 100)
        self.assertEqual(indices.shape, (100, 30))
        self.assertTrue(((indices >= 0) & (indices < 30)).all())
        self.assertTrue((np.diff(indices.reshape(100, 10, 3), axis=2) == 1).all())
        np.testing.assert_array_equal(indices, moving_day_indices(30, 3, [42, 3, 2019, 3, 3], 100))

    def test_bootstrap_ratios_preserve_counts_and_bounds(self):
        daily = pd.DataFrame(dict(total=[100]*30, eligible=[80]*30, clear=[20]*30,
            cluster_0=[30]*30, cluster_1=[50]*30, above_q95=[4]*30, above_q99=[1]*30))
        rows = bootstrap_fractions(daily, 2019, dict(CONFIG, bootstrap_replicates=50))
        self.assertEqual(len(rows), 21)
        for row in rows:
            self.assertAlmostEqual(row["estimate"], row["lower"])
            self.assertAlmostEqual(row["lower"], row["upper"])
            self.assertTrue(0 <= row["lower"] <= row["upper"] <= 1)

    def test_undefined_metrics_and_ordering_failures_are_results(self):
        metric, details, points = evaluate_metrics(np.ones((10, 3)), np.zeros(10), list(range(10)), "2019", CONFIG)
        self.assertEqual(metric["status"], "undefined")
        self.assertTrue(np.isnan(metric["silhouette"]))
        self.assertEqual(details, [])
        self.assertEqual(points, [])
        profile = pd.DataFrame([dict(period="2019", variable=v, cluster=k, median=10.)
                                for v in CONFIG["expected_ordering"] for k in [0, 1]])
        self.assertTrue(all(r["result"] == "reversed_or_equal" for r in ordering_checks(profile, CONFIG)))

    def test_no_refit_guard(self):
        from sklearn.preprocessing import StandardScaler
        with prohibit_fitting():
            with self.assertRaisesRegex(RuntimeError, "prohibits"):
                StandardScaler().fit([[1, 2], [3, 4]])


def synthetic_fixture(root):
    """Small, explicitly synthetic Stage 1/2 provenance and twelve annual NetCDFs."""
    (root / "config").mkdir()
    contract_path = root / "config/ceres_feature_definitions.json"
    contract_path.write_text(json.dumps(CONTRACT))
    config = copy.deepcopy(CONFIG)
    config.update(profile_sample_per_year=40, metric_sample_per_year=20,
                  pooled_metric_sample_per_year=8, bootstrap_replicates=30, batch_size=500)
    (root / "config/pre_monsoon_stage3.json").write_text(json.dumps(config))
    protocol = root / "docs/methodology/pre_monsoon_stage3_protocol.md"
    protocol.parent.mkdir(parents=True)
    protocol.write_text("Synthetic freeze protocol; no scientific results.\n")
    s1_dir = root / "reports/phase2/pre_monsoon/stage1_v1"
    s2_dir = root / "reports/phase2/pre_monsoon/stage2_v1"
    s1_dir.mkdir(parents=True); s2_dir.mkdir(parents=True)
    prepared_dir = root / "data/processed/model_ready/phase2/pre_monsoon/stage1_v1"
    raw_dir = root / "data/interim/ceres_seasonal/pre_monsoon"
    prepared_dir.mkdir(parents=True); raw_dir.mkdir(parents=True)
    samples, sources, prepared_hashes, training_x, input_rows, physical = [], [], {}, [], [], []
    prepared_copies = {}
    for year in range(2010, 2022):
        split = "train" if year < 2017 else "development" if year < 2019 else "holdout"
        rng = np.random.default_rng(year)
        shape = (720, 2, 3)
        ds = xr.Dataset(coords={"time": pd.date_range(f"{year}-04-15T00:30", periods=720, freq="h"),
                                "lat": np.array([10., 20.], dtype="float32"),
                                "lon": np.array([70., 80., 90.], dtype="float32")})
        for name, spec in registry(CONTRACT).items():
            ds[name] = (("time", "lat", "lon"), np.full(shape, sum(spec["range"])/2, dtype="float32"))
            ds[name].attrs["units"] = spec["units"]
        group = rng.integers(0, 2, size=shape)
        ds.cldarea_total_1h.values[:] = (10 + 80*group + rng.uniform(0, 5, shape)).astype("float32")
        ds.cldtau_total_1h.values[:] = np.expm1(rng.uniform(.1, 3, shape)).astype("float32")
        ds.cldpress_top_total_1h.values[:] = rng.uniform(100, 1000, shape).astype("float32")
        ds.cldarea_total_1h.values.ravel()[0] = 0
        raw_path = raw_dir / f"CERES_{year}_pre_monsoon.nc"
        ds.to_netcdf(raw_path, engine="netcdf4")
        sources.append(dict(year=year, split=split, path=str(raw_path.relative_to(root)), sha256=sha256(raw_path)))
        out = prepare(ds, CONTRACT)
        out.attrs.update(season="pre_monsoon", split=split, feature_contract_sha256=sha256(contract_path))
        path = prepared_dir / f"CERES_{year}_pre_monsoon_prepared.nc"
        out.to_netcdf(path, engine="netcdf4")
        prepared_hashes[str(path.relative_to(root))] = sha256(path)
        if year < 2019:
            input_rows.append(dict(year=year, path=str(path.relative_to(root)), sha256=sha256(path)))
            indices = np.arange(1, 21)
            x = np.column_stack([out[f["output"]].values.ravel()[indices] for f in CONTRACT["primary"]])
            if year < 2017: training_x.append(x)
            identities = observation_ids(out, indices, "pre_monsoon")
            part = pd.DataFrame(dict(year=year, split=split, flat_index=indices, observation_id=identities))
            for name in config["profile_variables"]:
                part[name] = ds[name].values.ravel()[indices]
            physical.append((part, x))
            samples.extend(part[["year", "split", "flat_index", "observation_id"]].to_dict("records"))
            prepared_copies[year] = out
    sample_frame = pd.DataFrame(samples)
    sample_frame.to_csv(s1_dir / "sample_manifest.csv", index=False)
    s1_config = load_json(ROOT / "config/pre_monsoon_stage1.json")
    s1_config.update(expected_shape=[720, 2, 3], expected_latitude_endpoints=[10, 20],
                     expected_longitude_endpoints=[70, 90])
    s1 = dict(config=s1_config, sources=sources, output_sha256=prepared_hashes,
              contract_sha256=sha256(contract_path), protected_files={})
    (s1_dir / "manifest.json").write_text(json.dumps(s1))
    s2_config = load_json(ROOT / "config/pre_monsoon_stage2.json")
    with threadpool_limits(1):
        bundle = fit_preprocessing(np.concatenate(training_x))
        bundle.update(season="pre_monsoon", fit_years=config["fit_years"], selected_n_components=3,
            contract_sha256=sha256(contract_path), feature_order=[f["output"] for f in CONTRACT["primary"]],
            training_observation_ids=sample_frame[sample_frame.split == "train"].observation_id.tolist())
        bundle["kmeans"] = kmeans(dict(s2_config, kmeans_n_init=2), 2, 42).fit(project(bundle, np.concatenate(training_x), 3))
    model_path = root / "results/models/phase2/pre_monsoon/stage2_v1/selected_pre_monsoon_bundle.joblib"
    model_path.parent.mkdir(parents=True); joblib.dump(bundle, model_path)
    selection = pd.DataFrame([dict(k=2, selected=True, admissible=True, silhouette=.4,
        calinski_harabasz=200., davies_bouldin=1.0)])
    selection.to_csv(s2_dir / "cluster_selection.csv", index=False)
    for name in ["pca_variance", "pca_loadings", "pca_reconstruction", "initialization_stability", "sampling_stability"]:
        pd.DataFrame([dict(synthetic=True)]).to_csv(s2_dir / f"{name}.csv", index=False)
    frames, annual, spatial = [], [], []
    with threadpool_limits(1):
        for part, x in physical:
            labels = bundle["kmeans"].predict(project(bundle, x, 3))
            frames.append(part.assign(cluster=labels))
            year = int(part.year.iloc[0]); out = prepared_copies[year]
            valid = np.flatnonzero(out.eligible.values.ravel())
            full_x = np.column_stack([out[f["output"]].values.ravel()[valid] for f in CONTRACT["primary"]])
            all_labels = np.full(out.status.shape, -1, dtype="int16")
            all_labels.ravel()[valid] = bundle["kmeans"].predict(project(bundle, full_x, 3))
            result = population_diagnostics(out, all_labels, year, part.split.iloc[0], 2)
            annual.extend(result["annual_occurrence"]); spatial.extend(result["spatial_occurrence"])
    frame = pd.concat(frames, ignore_index=True)
    physical_profiles(frame, frame.cluster.to_numpy(), CONTRACT).to_csv(s2_dir / "physical_profiles.csv", index=False)
    pd.DataFrame(annual).to_csv(s2_dir / "annual_occurrence.csv", index=False)
    pd.DataFrame(spatial).to_csv(s2_dir / "spatial_occurrence.csv", index=False)
    hashes = {str(p.relative_to(root)): sha256(p) for p in s2_dir.iterdir()}
    hashes[str(model_path.relative_to(root))] = sha256(model_path)
    s2 = dict(status="complete", selected_n_components=3, selected_k=2,
        fit_years=config["fit_years"], holdout_accessed=False, holdout_evaluated=False,
        output_sha256=hashes, code_sha256={}, contract_sha256=sha256(contract_path),
        accessed_inputs=input_rows, training_sample_count=len(np.concatenate(training_x)), config=s2_config)
    (s2_dir / "manifest.json").write_text(json.dumps(s2))
    review = s2_dir.parent / "stage2_review.md"
    review.write_text("Explicit synthetic selection evidence for integration tests.\n")
    receipt = dict(status="complete", passed_tests=19, main_run_manifest_sha256=sha256(s2_dir / "manifest.json"),
                   review_sha256=sha256(review), tests={})
    (s2_dir.parent / "stage2_review_manifest.json").write_text(json.dumps(receipt))
    return config, model_path


class Stage3IntegrationTests(unittest.TestCase):
    def test_gate_freeze_evaluation_and_immutable_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, model_path = synthetic_fixture(root)
            original_hash = sha256(model_path)
            original_open = xr.open_dataset
            def no_holdout_open(path, *args, **kwargs):
                self.assertFalse(any(f"CERES_{y}_" in str(path) for y in [2019, 2020, 2021]))
                return original_open(path, *args, **kwargs)
            with patch("xarray.open_dataset", side_effect=no_holdout_open):
                with self.assertRaises(FileNotFoundError):
                    evaluate(root, "unsealed")
                freeze(root, "synthetic_stage3")
            result = evaluate(root, "synthetic_stage3")
            self.assertEqual(result["status"], "complete")
            self.assertFalse(result["refitted"])
            self.assertEqual(sha256(model_path), original_hash)
            checked = verify(root, "synthetic_stage3")
            self.assertEqual(checked["sample_predictions"], 120)
            out = root / "reports/phase3/pre_monsoon/synthetic_stage3"
            metrics = pd.read_csv(out / "evaluation/metrics.csv")
            self.assertEqual(len(metrics), 4)
            self.assertEqual(int(metrics[metrics.period == "pooled"].iloc[0].n), 24)
            for path, digest in result["output_sha256"].items():
                self.assertEqual(sha256(root / path), digest)
            with self.assertRaises(FileExistsError):
                evaluate(root, "synthetic_stage3")
            with self.assertRaises(FileExistsError):
                freeze(root, "synthetic_stage3")
            # An altered protocol invalidates the gate before any holdout can open.
            altered = dict(config, seed=99)
            (root / "config/pre_monsoon_stage3.json").write_text(json.dumps(altered))
            with patch("xarray.open_dataset", side_effect=no_holdout_open):
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    load_freeze(root, "synthetic_stage3")


if __name__ == "__main__":
    unittest.main()
