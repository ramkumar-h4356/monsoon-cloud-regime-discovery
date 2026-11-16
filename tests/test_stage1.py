"""Run with python -B -m unittest discover -s tests -v (no pytest required)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/06_feature_engineering"))
from ceres_features import (clean_variable, load_json, observation_ids, prepare,
                            registry, sample_indices, sha256, split_map, validate_schema)
from prepare_pre_monsoon import run

CONTRACT = load_json(ROOT / "config/ceres_feature_definitions.json")
CONFIG = load_json(ROOT / "config/pre_monsoon_stage1.json")


def synthetic(year):
    times = pd.date_range(f"{year}-04-15T00:30:00", periods=720, freq="h")
    coords = {"time": times, "lat": [6.5, 37.5], "lon": [68.5, 97.5]}
    ds = xr.Dataset(coords=coords)
    for name, spec in registry(CONTRACT).items():
        midpoint = sum(spec["range"]) / 2
        ds[name] = (("time", "lat", "lon"), np.full((720, 2, 2), midpoint, dtype="float32"))
        ds[name].attrs["units"] = spec["units"]
    # Four distinct population states; remaining observations are eligible.
    ds.cldarea_total_1h.values.ravel()[0] = 0
    ds.cldtau_total_1h.values.ravel()[0] = np.nan
    ds.cldarea_total_1h.values.ravel()[1] = np.nan
    ds.cldtau_total_1h.values.ravel()[2] = np.nan
    ds.cldpress_top_total_1h.values.ravel()[3] = np.inf
    ds.iwp_low_1h.values[:] = np.nan
    ds.cldphase_low_1h.values[:] = 1
    return ds


def synthetic_config():
    config = dict(CONFIG)
    config["expected_shape"] = [720, 2, 2]
    config["sample_per_year"] = 20
    return config


class FeatureTests(unittest.TestCase):
    def test_registry_and_season_compatibility(self):
        self.assertEqual(len(registry(CONTRACT)), 45)
        self.assertEqual(set(CONTRACT["season_windows"]),
                         {"pre_monsoon", "established_monsoon", "post_monsoon"})
        self.assertEqual([f["source"] for f in CONTRACT["primary"]],
                         ["cldarea_total_1h", "cldtau_total_1h", "cldpress_top_total_1h"])

    def test_masks_and_stateless_transforms(self):
        ds = synthetic(2010)
        out = prepare(ds, CONTRACT)
        np.testing.assert_array_equal(out.status.values.ravel()[:5], [1, 2, 3, 3, 0])
        self.assertEqual(int(out.eligible.sum()), 2876)
        self.assertAlmostEqual(float(out.cloud_area_fraction.values.ravel()[4]), 0.5)
        self.assertAlmostEqual(float(out.log1p_optical_depth.values.ravel()[4]), np.log1p(200), places=5)
        self.assertEqual(float(out.cloud_top_pressure_hpa.values.ravel()[4]), 550)
        self.assertEqual(int(out.cldpress_top_total_1h__invalid.values.ravel()[3]), 1)
        self.assertNotIn("iwp_low_1h", out)
        self.assertTrue(np.isnan(ds.iwp_low_1h.values).all())

    def test_fill_and_invalid_values_are_not_zero(self):
        da = xr.DataArray(np.array([-999, -888, np.nan, np.inf, -1, 0, 100, 101],
                                   dtype="float32").reshape(2, 2, 2), dims=("time", "lat", "lon"))
        da.attrs["missing_value"] = -888
        clean, missing, invalid = clean_variable(da, {"range": [0, 100]})
        self.assertEqual(int(missing.sum()), 3)
        self.assertEqual(int(invalid.sum()), 3)
        self.assertEqual(int(np.isfinite(clean).sum()), 2)
        self.assertEqual(clean.ravel()[5], 0)

    def test_dimension_order_and_ids(self):
        ds = synthetic(2010)
        first = prepare(ds, CONTRACT)
        other = prepare(ds.transpose("lon", "time", "lat"), CONTRACT)
        xr.testing.assert_equal(first, other)
        ids = observation_ids(ds, np.arange(8), "pre_monsoon")
        self.assertEqual(len(set(ids)), 8)
        self.assertIn("00:30:00.000000000", ids[0])
        self.assertEqual(str(first.hourly_slot.values[0]), "2010-04-15T00:00:00.000000000")

    def test_schema_rejects_units_and_hour_duplicates(self):
        ds = synthetic(2010)
        validate_schema(ds, 2010, CONTRACT, synthetic_config())
        ds.cldarea_total_1h.attrs["units"] = "fraction"
        with self.assertRaisesRegex(ValueError, "units"):
            validate_schema(ds, 2010, CONTRACT, synthetic_config())
        ds = synthetic(2010)
        times = ds.time.values.copy()
        times[1] = times[0] + np.timedelta64(1, "m")
        ds = ds.assign_coords(time=times)
        with self.assertRaisesRegex(ValueError, "hourly"):
            validate_schema(ds, 2010, CONTRACT, synthetic_config())

    def test_temporal_disjointness(self):
        mapping = split_map(CONFIG)
        self.assertEqual(mapping[2016], "train")
        self.assertEqual(mapping[2017], "development")
        self.assertEqual(mapping[2019], "holdout")
        bad = dict(CONFIG, development_years=[2016, 2017])
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            split_map(bad)
        with self.assertRaisesRegex(ValueError, "chronologically"):
            split_map(dict(CONFIG, train_years=[2018], development_years=[2017]))

    def test_sampling_reproducibility_and_empty_population(self):
        mask = np.arange(100) % 2 == 0
        a = sample_indices(mask, 2010, 42, 10)
        np.testing.assert_array_equal(a, sample_indices(mask, 2010, 42, 10))
        self.assertTrue(mask[a].all())
        self.assertEqual(len(set(a)), 10)
        self.assertFalse(np.array_equal(a, sample_indices(mask, 2010, 43, 10)))
        self.assertEqual(len(sample_indices(np.zeros(5), 2010, 42, 10)), 0)


class IntegrationTests(unittest.TestCase):
    def test_full_run_preservation_holdout_isolation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config/ceres_feature_definitions.json").write_text(json.dumps(CONTRACT))
            (root / "config/pre_monsoon_stage1.json").write_text(json.dumps(synthetic_config()))
            source_dir = root / "data/interim/ceres_seasonal/pre_monsoon"
            source_dir.mkdir(parents=True)
            for year in range(2010, 2022):
                ds = synthetic(year)
                ds.to_netcdf(source_dir / f"CERES_{year}_pre_monsoon.nc", engine="netcdf4",
                             encoding={v: {"_FillValue": -999.0} for v in ds.data_vars})
            phase1 = root / "reports/data_quality/keep.csv"
            phase1.parent.mkdir(parents=True)
            phase1.write_text("original Phase 1\n")
            original_hash = sha256(phase1)
            first = run(root, "synthetic_a")
            self.assertEqual(first["status"], "complete")
            self.assertEqual(first["fitted_objects"], [])
            self.assertFalse(first["holdout_evaluated"])
            self.assertEqual(sha256(phase1), original_hash)
            reports = root / "reports/phase2/pre_monsoon/synthetic_a"
            counts = pd.read_csv(reports / "year_split_counts.csv")
            self.assertEqual(int(counts.total.sum()), 34560)
            self.assertTrue((counts.eligible_cloudy == 2876).all())
            self.assertTrue((counts[STATUS_COLUMNS].sum(axis=1) == counts.total).all())
            samples = pd.read_csv(reports / "sample_manifest.csv")
            self.assertEqual(len(samples), 180)
            self.assertFalse((samples.split == "holdout").any())
            self.assertFalse(samples.observation_id.duplicated().any())
            phase = pd.read_csv(reports / "phase_iwp_audit.csv")
            self.assertFalse((phase.split == "holdout").any())
            low = phase[(phase.layer == "low") & (phase.phase_group == "exactly_1")]
            self.assertTrue((low.iwp_valid == 0).all())
            with self.assertRaises(FileExistsError):
                run(root, "synthetic_a")
            with self.assertRaises(ValueError):
                run(root, "../escape")
            # Change every holdout's primary distribution; training/development artifacts stay equal.
            for year in CONFIG["holdout_years"]:
                ds = synthetic(year)
                ds.cldarea_total_1h.values[:] = 99
                ds.cldtau_total_1h.values[:] = 399
                ds.to_netcdf(source_dir / f"CERES_{year}_pre_monsoon.nc", engine="netcdf4")
            run(root, "synthetic_b")
            other = root / "reports/phase2/pre_monsoon/synthetic_b"
            self.assertEqual((reports / "sample_manifest.csv").read_bytes(),
                             (other / "sample_manifest.csv").read_bytes())
            self.assertEqual((reports / "phase_iwp_audit.csv").read_bytes(),
                             (other / "phase_iwp_audit.csv").read_bytes())
            for year in CONFIG["train_years"] + CONFIG["development_years"]:
                base = root / "data/processed/model_ready/phase2/pre_monsoon"
                filename = f"CERES_{year}_pre_monsoon_prepared.nc"
                with xr.open_dataset(base / "synthetic_a" / filename) as a, \
                        xr.open_dataset(base / "synthetic_b" / filename) as b:
                    xr.testing.assert_equal(a, b)
                    self.assertEqual(a.attrs["fitted_transforms"], "none")


STATUS_COLUMNS = ["eligible_cloudy", "clear", "invalid_or_missing_area", "incomplete_cloudy"]

if __name__ == "__main__":
    unittest.main()
