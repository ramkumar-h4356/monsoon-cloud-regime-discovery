"""Additive remediation tests. All scientific inputs and fits here are synthetic."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import warnings

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
for folder in ("src/10_handoff", "src/06_feature_engineering", "src/07_clustering", "src/08_evaluation"):
    sys.path.insert(0, str(ROOT / folder))
import handoff
from ceres_features import load_json
from pre_monsoon_stage2_model import fit_preprocessing, project
from pre_monsoon_stage2_diagnostics import population_diagnostics, physical_profiles
from pre_monsoon_stage3_tools import bootstrap_fractions
from robust_diagnostics_v2 import (bootstrap_fractions_v2, distance_summary, evaluate_period_v2,
    pc_summary, physical_profiles_v2, population_diagnostics_v2)

CONTRACT = load_json(ROOT / "config/ceres_feature_definitions.json")
CONFIG = dict(load_json(ROOT / "config/pre_monsoon_stage3.json"), bootstrap_replicates=40)


def prepared(status):
    status = np.asarray(status, dtype="uint8")
    coords = {"time": pd.date_range("2030-04-15T00:30", periods=status.shape[0], freq="h"),
              "lat": np.arange(status.shape[1]) + 10., "lon": np.arange(status.shape[2]) + 70.}
    ds = xr.Dataset({"status": (("time", "lat", "lon"), status)}, coords=coords)
    rng = np.random.default_rng(12)
    for name in ["cloud_area_fraction", "log1p_optical_depth", "cloud_top_pressure_hpa"]:
        ds[name] = (("time", "lat", "lon"), rng.normal(size=status.shape))
    return ds


def no_inference_bundle():
    class Poison:
        def __getattr__(self, name):
            raise AssertionError(f"An estimator was touched for empty support: {name}")
    return dict(season="pre_monsoon", selected_n_components=3,
                feature_order=["cloud_area_fraction", "log1p_optical_depth", "cloud_top_pressure_hpa"],
                kmeans=SimpleNamespace(n_clusters=2), imputer=Poison(), scaler=Poison(), pca=Poison())


def fitted_synthetic_bundle():
    from sklearn.cluster import KMeans
    x = np.random.default_rng(7).normal(size=(40, 3))
    with threadpool_limits(1):
        bundle = fit_preprocessing(x)
        bundle.update(season="pre_monsoon", selected_n_components=3,
            feature_order=["cloud_area_fraction", "log1p_optical_depth", "cloud_top_pressure_hpa"])
        bundle["kmeans"] = KMeans(n_clusters=2, n_init=2, random_state=42).fit(project(bundle, x, 3))
    return bundle


class RobustSupportTests(unittest.TestCase):
    def test_empty_distance_and_singleton_pc_statistics(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            result = distance_summary([], {"q95": 2., "q99": 3.})
            self.assertEqual(result["status"], "undefined_no_eligible")
            self.assertTrue(np.isnan(result["p99_distance"]))
            for scores in (np.empty((0, 3)), np.ones((1, 3))):
                rows = pc_summary(scores, 3)
                self.assertTrue(all(np.isnan(row["variance"]) for row in rows))
        with self.assertRaises(ValueError):
            distance_summary([1], {"q95": np.nan})

    def test_positive_distance_and_pc_statistics(self):
        values = np.array([1., 2., 4.])
        result = distance_summary(values, {"q95": 2.})
        self.assertEqual(result["mean_squared_distance"], float(np.mean(values**2)))
        self.assertEqual(result["exceedance"]["q95"], 1/3)
        scores = np.arange(12).reshape(4, 3)
        rows = pc_summary(scores, 3)
        np.testing.assert_allclose([row["variance"] for row in rows], scores.var(axis=0, ddof=1))

    def test_all_clear_period_never_calls_estimators(self):
        ds = prepared(np.ones((6, 2, 3)))
        result = evaluate_period_v2(no_inference_bundle(), ds, 2030, "synthetic", {"q95": 2.})
        self.assertTrue((result["labels"] == -1).all())
        row = result["population"]["annual_occurrence"][0]
        self.assertEqual(row["clear"], 36)
        self.assertEqual(row["all_cell_fraction"], 0)
        self.assertTrue(np.isnan(row["cloudy_fraction"]))
        self.assertEqual(result["metrics"]["status"], "undefined")

    def test_all_unavailable_and_zero_time_periods(self):
        for status in (np.full((4, 1, 2), 2), np.full((4, 1, 2), 3), np.empty((0, 1, 1))):
            result = evaluate_period_v2(no_inference_bundle(), prepared(status), 2030, "synthetic", {})
            self.assertEqual(result["status"], "undefined_no_eligible")
            self.assertTrue((result["labels"] == -2).all())
            self.assertEqual(result["distances"]["n"], 0)
            self.assertEqual(len(result["population"]["annual_occurrence"]), 2)
            self.assertTrue(all(r["runs"] == 0 for r in result["population"]["persistence"]))

    def test_single_eligible_row_no_artificial_cluster_or_variance(self):
        ds = prepared(np.ones((4, 1, 2)))
        ds.status.values.ravel()[0] = 0
        result = evaluate_period_v2(fitted_synthetic_bundle(), ds, 2030, "synthetic", {"q95": 2.})
        self.assertEqual(len(result["eligible_indices"]), 1)
        self.assertEqual(result["metrics"]["observed_clusters"], 1)
        self.assertEqual(result["metrics"]["status"], "undefined")
        self.assertTrue(all(np.isnan(row["variance"]) for row in result["fixed_pcs"]))

    def test_positive_population_and_predictions_match_historical(self):
        status = np.zeros((8, 2, 3), dtype=int)
        status.ravel()[::7] = 1; status.ravel()[::11] = 2
        ds = prepared(status)
        bundle = fitted_synthetic_bundle()
        result = evaluate_period_v2(bundle, ds, 2030, "synthetic", {"q95": 2.})
        indices = np.flatnonzero(status.ravel() == 0)
        x = np.column_stack([ds[name].values.ravel()[indices] for name in bundle["feature_order"]])
        with threadpool_limits(1):
            expected = bundle["kmeans"].predict(project(bundle, x, 3))
        np.testing.assert_array_equal(result["labels"].ravel()[indices], expected)
        old = population_diagnostics(ds, result["labels"], 2030, "synthetic", 2)
        for name in old:
            pd.testing.assert_frame_equal(pd.DataFrame(result["population"][name]), pd.DataFrame(old[name]))

    def test_incomplete_eligible_and_invalid_status_rejected(self):
        ds = prepared(np.zeros((2, 1, 1)))
        ds.cloud_area_fraction.values[0,0,0] = np.nan
        with self.assertRaisesRegex(ValueError, "complete"):
            evaluate_period_v2(fitted_synthetic_bundle(), ds, 2030, "synthetic", {})
        ds = prepared(np.full((2, 1, 1), 4))
        with self.assertRaisesRegex(ValueError, "status"):
            population_diagnostics_v2(ds, np.full(ds.status.shape, -2), 2030, "synthetic", 2)

    def test_profiles_keep_empty_clusters_and_missing_retrievals(self):
        frame = pd.DataFrame({"iwp_total_1h": [np.nan]})
        result = physical_profiles_v2(frame, [0], CONTRACT, ["iwp_total_1h"], "synthetic", 2)
        self.assertEqual(result.loc[0, "missing"], 1)
        self.assertEqual(result.loc[0, "status"], "undefined_no_valid_retrievals")
        self.assertEqual(result.loc[1, "total"], 0)
        self.assertTrue(result["median"].isna().all())
        self.assertEqual(result.loc[0, "units"], "g m-2")
        empty = physical_profiles_v2(frame.iloc[:0], [], CONTRACT, ["iwp_total_1h"], "empty", 2)
        self.assertEqual(len(empty), 2)
        self.assertTrue((empty.total == 0).all())

    def test_positive_profile_values_match_historical(self):
        frame = pd.DataFrame(dict(split=["synthetic"]*4, iwp_total_1h=[1., 4., 8., 9.]))
        labels = np.array([0,0,1,1])
        old = physical_profiles(frame, labels, CONTRACT)
        new = physical_profiles_v2(frame, labels, CONTRACT, ["iwp_total_1h"], "synthetic", 2)
        for field in ["mean", "median", "p10", "p90", "total", "valid", "missing"]:
            np.testing.assert_array_equal(old[field], new[field])

    def test_empty_bootstrap_and_unsupported_lengths_remain_undefined(self):
        columns = ["total", "eligible", "clear", "cluster_0", "cluster_1", "above_q95", "above_q99"]
        empty = pd.DataFrame(columns=columns)
        result = bootstrap_fractions_v2(empty, 2030, CONFIG)
        self.assertEqual(len(result), 21)
        self.assertTrue(all(row["valid_replicates"] == 0 for row in result))
        self.assertTrue(all(row["status"] == "undefined_insufficient_days" for row in result))
        short = pd.DataFrame(dict(total=[10]*2, eligible=[8]*2, clear=[2]*2,
            cluster_0=[3]*2, cluster_1=[5]*2, above_q95=[1]*2, above_q99=[0]*2))
        rows = bootstrap_fractions_v2(short, 2030, CONFIG)
        self.assertTrue(all(r["status"] == "undefined_insufficient_days" for r in rows if r["block_days"] != 1))
        self.assertTrue(all(r["status"] == "defined" for r in rows if r["block_days"] == 1))

    def test_bootstrap_all_clear_and_positive_compatibility(self):
        daily = pd.DataFrame(dict(total=[10]*30, eligible=[0]*30, clear=[10]*30,
            cluster_0=[0]*30, cluster_1=[0]*30, above_q95=[0]*30, above_q99=[0]*30))
        result = bootstrap_fractions_v2(daily, 2030, CONFIG)
        self.assertTrue(all(r["lower"] == 1 for r in result if r["endpoint"] == "all_cell_clear"))
        self.assertTrue(all(r["valid_replicates"] == 0 for r in result if r["endpoint"].startswith("cloudy")))
        daily["eligible"] = 8; daily["clear"] = 2; daily["cluster_0"] = 3; daily["cluster_1"] = 5
        old = bootstrap_fractions(daily, 2030, CONFIG)
        new = bootstrap_fractions_v2(daily, 2030, CONFIG)
        for a, b in zip(old, new):
            for name in ["estimate", "lower", "upper", "valid_replicates", "primary"]:
                self.assertEqual(a[name], b[name])


def handoff_fixture(root, run_id="alternate_run"):
    def put(relative, value):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if isinstance(value, dict) else value, encoding="utf-8")
        return path
    model = put("results/models/model.joblib", "not loaded; byte hash only")
    old = put("src/old.py", "historical content")
    a = put("reports/phase2/pre_monsoon/stage1_v1/result.csv", "value\n1\n")
    put("reports/phase2/pre_monsoon/stage1_v1/manifest.json", {"output_sha256": {str(a.relative_to(root)): handoff.digest(a)}})
    b = put("reports/phase2/pre_monsoon/stage2_v1/result.csv", "value\n2\n")
    base = put("reports/phase2/pre_monsoon/stage2_v1/manifest.json", {"output_sha256": {str(b.relative_to(root)): handoff.digest(b)}})
    extra = put("reports/phase2/pre_monsoon/stage2_tsne_sensitivity_v1/manifest.json", {"output_sha256": {}})
    review = put("reports/phase2/pre_monsoon/stage2_review.md", "historical review")
    put("reports/phase2/pre_monsoon/stage2_review_manifest.json", dict(review_sha256=handoff.digest(review),
        main_run_manifest_sha256=handoff.digest(base), supplementary_manifest_sha256=handoff.digest(extra)))
    run = root / "reports/phase3/pre_monsoon" / run_id
    frozen = put(str((run/"freeze/frozen.json").relative_to(root)), dict(
        config={"stage1_run_id": "stage1_v1", "stage2_run_id": "stage2_v1"},
        preserved_files={str(old.relative_to(root)): handoff.digest(old)},
        model_path=str(model.relative_to(root)), model_sha256=handoff.digest(model), created_utc="2030-01-01T00:00:00"))
    seal = put(str((run/"freeze/seal.json").relative_to(root)), {"files": {"frozen.json": handoff.digest(frozen)}})
    csv = run/"evaluation/metrics.csv"; csv.parent.mkdir(parents=True)
    pd.DataFrame([dict(period="pooled", n=3000, silhouette=.416583, calinski_harabasz=2702.887303, davies_bouldin=.953121)]).to_csv(csv,index=False)
    boot = run/"evaluation/bootstrap_intervals.csv"
    pd.DataFrame([dict(year=year, endpoint=f"cloudy_cluster_{k}", primary=True, estimate=.4+.2*k,
        lower=.3+.2*k, upper=.5+.2*k) for year in [2030,2031] for k in [0,1]]).to_csv(boot,index=False)
    evaluation = put(str((run/"evaluation_manifest.json").relative_to(root)), dict(refitted=False, tuned=False,
        created_utc="2030-01-01T02:00:00", output_sha256={str(p.relative_to(root)):handoff.digest(p) for p in [csv,boot]}))
    put(str((run/"evaluation/holdout_access_receipt.json").relative_to(root)), {"created_utc":"2030-01-01T01:00:00"})
    report = put(str((run/"scientific_report.md").relative_to(root)), "Historical report stays unchanged.")
    check = put(str((run/"verification.json").relative_to(root)), {"status":"verified"})
    image = put("results/figures/old.png", "hashed only")
    plot_code = put("src/09_visualization/plot_pre_monsoon_stage3_summary.py", "historical plot code")
    build_code = put("src/08_evaluation/build_pre_monsoon_stage3_completion.py", "historical builder code")
    presentation = put(str((run/"presentation_manifest.json").relative_to(root)), dict(output_path=str(image.relative_to(root)),
        output_sha256=handoff.digest(image), script_sha256=handoff.digest(plot_code)))
    log = put("reports/phase3/pre_monsoon/stage3_all_tests.txt", "Ran 25 tests in 1.0s\n\nOK\n")
    put(str((run/"completion_manifest.json").relative_to(root)), dict(
        report_sha256=handoff.digest(report), evaluation_manifest_sha256=handoff.digest(evaluation),
        verification_sha256=handoff.digest(check), presentation_manifest_sha256=handoff.digest(presentation),
        freeze_seal_sha256=handoff.digest(seal), test_log_sha256=handoff.digest(log), builder_sha256=handoff.digest(build_code)))
    selection = root/"reports/phase2/pre_monsoon/stage2_v1/cluster_selection.csv"
    pd.DataFrame([dict(k=2,selected=True,silhouette=.418872,calinski_harabasz=2739.092510,davies_bouldin=.954099)]).to_csv(selection,index=False)
    return run


class HandoffTests(unittest.TestCase):
    def test_ids_paths_and_exclusive_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for value in ("../x", "a/b", "", "a b"):
                with self.assertRaises(ValueError): handoff.identifier(value)
            with self.assertRaises(ValueError): handoff.inside(root, "../outside")
            handoff.new_output(root,"test_delivery","report")
            with self.assertRaises(FileExistsError): handoff.new_output(root,"test_delivery","report")

    def test_receipt_accepts_current_count_and_rejects_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"tests.txt"
            path.write_text("Ran 43 tests in 2.123s\n\nOK\n")
            self.assertEqual(handoff.test_receipt(path)["passed"],43)
            path.write_text("Ran 43 tests in 2.123s\n\nFAILED (failures=1)\n")
            with self.assertRaises(ValueError): handoff.test_receipt(path)

    def test_cli_routes_custom_input_and_output_ids(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            root=Path(folder).resolve()
            with patch.object(handoff,"report",return_value={}) as mocked:
                self.assertEqual(handoff.main(["--root",folder,"report","--run-id","alternate_run","--output-id","delivery_123"]),0)
                mocked.assert_called_once_with(root,"alternate_run","delivery_123",None,None)
            with patch.object(handoff,"plot",return_value={}) as mocked:
                handoff.main(["--root",folder,"plot","--run-id","alternate_run","--output-id","delivery_123"])
                mocked.assert_called_once_with(root,"alternate_run","delivery_123")

    def test_complete_artifact_verification_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); run=handoff_fixture(root)
            result=handoff.verify_artifacts(root,"alternate_run")
            self.assertFalse(result["model_loaded"])
            self.assertFalse(result["netcdf_arrays_opened"])
            self.assertTrue(result["historical_results_unchanged"])
            (run/"evaluation/metrics.csv").write_text("changed")
            with self.assertRaisesRegex(ValueError,"hash mismatch"):
                handoff.verify_artifacts(root,"alternate_run")

    def test_report_is_additive_and_qualifies_historical_record(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); run=handoff_fixture(root)
            source=run/"scientific_report.md"; before=handoff.digest(source)
            log=root/"current_tests.txt"; log.write_text("Ran 43 tests in 2.123s\n\nOK\n")
            result=handoff.report(root,"alternate_run","new_delivery","current_tests.txt")
            text=(root/"reports/handoff/new_delivery/report/SCIENTIFIC_HANDOFF.md").read_text(encoding="utf-8")
            self.assertIn("also less favorable",text)
            self.assertIn("not historically unseen",text)
            self.assertIn("no independent meteorological-type validation",text)
            self.assertEqual(result["tests"]["passed"],43)
            self.assertFalse(result["all_postprocessing_code_frozen_before_access"])
            self.assertEqual(handoff.digest(source),before)
            with self.assertRaises(FileExistsError): handoff.report(root,"alternate_run","new_delivery")

    def test_plot_uses_custom_run_years_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); run=handoff_fixture(root); source=run/"evaluation/bootstrap_intervals.csv"
            before=handoff.digest(source)
            result=handoff.plot(root,"alternate_run","new_plot")
            self.assertEqual(result["run_id"],"alternate_run")
            self.assertTrue((root/"reports/handoff/new_plot/plot/occurrence_uncertainty.png").is_file())
            self.assertEqual(handoff.digest(source),before)
            with self.assertRaises(FileExistsError): handoff.plot(root,"alternate_run","new_plot")

    def test_reference_lock_and_dependency_closure(self):
        result=handoff.check_environment(ROOT)
        self.assertEqual(result["status"],"matched",result["errors"])
        self.assertEqual(result["locked_distributions"],31)
        self.assertTrue(result["active_dependency_closure_checked"])


if __name__ == "__main__":
    unittest.main()
