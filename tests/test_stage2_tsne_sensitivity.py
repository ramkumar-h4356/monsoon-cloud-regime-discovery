"""Test stochastic t-SNE checks without refitting the scientific preprocessing."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from threadpoolctl import threadpool_limits
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/09_visualization"))
from test_stage2 import fixture
from run_pre_monsoon_stage2 import run as main_run
from pre_monsoon_stage2_tsne_sensitivity import experiment_specs, run
from ceres_features import load_json, sha256


class TSNESensitivityTests(unittest.TestCase):
    def test_controlled_settings_and_random_seed_grid(self):
        config = load_json(ROOT / "config/pre_monsoon_stage2_tsne_sensitivity.json")
        specs = experiment_specs(config)
        self.assertEqual(len(specs), 7)
        self.assertEqual({s["learning_rate"] for s in specs}, {62.5})
        self.assertEqual(sum(s["init"] == "random" for s in specs), 6)
        self.assertEqual(specs[-1]["early_exaggeration"], 4)

    def test_saved_sample_sensitivity_without_holdout_or_preprocessing_fit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            with threadpool_limits(1):
                main_run(root, "synthetic_base")
            config = load_json(ROOT / "config/pre_monsoon_stage2_tsne_sensitivity.json")
            config.update(base_run_id="synthetic_base", perplexities=[5, 10], seeds=[42, 73],
                          fixed_learning_rate=50, max_iter=300, controlled_perplexity=5)
            path = root / "config/pre_monsoon_stage2_tsne_sensitivity.json"
            path.write_text(json.dumps(config))
            original_open = xr.open_dataset
            def guarded_open(path, *args, **kwargs):
                self.assertFalse(any(f"CERES_{year}_" in str(path) for year in [2019, 2020, 2021]))
                return original_open(path, *args, **kwargs)
            with patch("xarray.open_dataset", side_effect=guarded_open), \
                    patch("sklearn.impute.SimpleImputer.fit", side_effect=AssertionError("refit forbidden")), \
                    patch("sklearn.preprocessing.StandardScaler.fit", side_effect=AssertionError("refit forbidden")):
                result = run(root, "synthetic_sensitivity")
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["experiments"], 5)
            self.assertFalse(result["fitted_preprocessing"])
            self.assertFalse(result["holdout_accessed"])
            self.assertTrue(all(item["year"] < 2019 for item in result["inputs"]))
            self.assertTrue(all(sha256(root / p) == h for p, h in result["output_sha256"].items()))
            with self.assertRaises(FileExistsError):
                run(root, "synthetic_sensitivity")


if __name__ == "__main__":
    unittest.main()
