"""Standalone frozen-model/artifact validation; no refitting or report mutation."""
import argparse
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/06_feature_engineering"))
from ceres_features import observation_ids, sha256
from pre_monsoon_stage3_tools import nested_samples, prohibit_fitting
from run_pre_monsoon_stage3 import holdout_input_paths, load_freeze, predictions, write_json


def verify(root=ROOT, run_id="stage3_v1"):
    root = Path(root).resolve()
    out, folder, frozen = load_freeze(root, run_id)
    receipt = json.loads((out / "evaluation_manifest.json").read_text(encoding="utf-8"))
    if receipt["status"] != "complete" or receipt["refitted"] or receipt["tuned"]:
        raise ValueError("Evaluation was not completed under the frozen policy")
    for path, digest in receipt["output_sha256"].items():
        if sha256(root / path) != digest:
            raise ValueError(f"Result hash mismatch: {path}")
    bundle = joblib.load(root / frozen["model_path"])
    config = frozen["config"]
    reference = np.load(folder / "training_reference.npz")
    with prohibit_fitting(), threadpool_limits(config["threads"]):
        _, distance, _, _ = predictions(bundle, reference["x"])
        np.testing.assert_allclose(distance, reference["distance"], atol=1e-12)
        for q in config["distance_quantiles"]:
            expected = float(np.quantile(distance, q, method=config["threshold_quantile_method"]))
            if expected != frozen["distance_thresholds"][f"q{int(q*100)}"]:
                raise ValueError("Training-only novelty threshold mismatch")
        samples = pd.read_csv(out / "evaluation/profile_samples_and_membership.csv")
        annual = pd.read_csv(out / "evaluation/annual_occurrence.csv")
        if samples.observation_id.duplicated().any():
            raise ValueError("Duplicate profile identities")
        checked, population = 0, 0
        for entry in frozen["expected_holdout_inputs"]:
            year = entry["year"]
            _, prepared_path = holdout_input_paths(root, entry, frozen)
            path = root / "data/processed/model_ready/phase3/pre_monsoon" / run_id / f"CERES_{year}_pre_monsoon_labels.nc"
            with xr.open_dataset(prepared_path) as source, xr.open_dataset(path) as labeled:
                if not all(np.array_equal(source[c].values, labeled[c].values) for c in ("time", "lat", "lon")):
                    raise ValueError("Label coordinates changed")
                group = samples[samples.year == year]
                indices = group.flat_index.to_numpy(dtype=int)
                if observation_ids(source, indices, "pre_monsoon") != group.observation_id.tolist():
                    raise ValueError("Saved holdout identities changed")
                valid = np.flatnonzero(source.status.values.ravel() == 0)
                profile, metric, pooled = nested_samples(valid, year, config)
                np.testing.assert_array_equal(profile, indices)
                np.testing.assert_array_equal(np.isin(indices, metric), group.yearly_metric)
                np.testing.assert_array_equal(np.isin(indices, pooled), group.pooled_metric)
                x = np.column_stack([source[name].values.ravel()[indices] for name in bundle["feature_order"]])
                prediction, distance, _, _ = predictions(bundle, x)
                np.testing.assert_array_equal(prediction, group.cluster)
                np.testing.assert_allclose(distance, group.distance, atol=1e-12)
                np.testing.assert_array_equal(prediction, labeled.cluster.values.ravel()[indices])
                labels, status = labeled.cluster.values, source.status.values
                if not ((labels[status == 1] == -1).all() and (labels[status >= 2] == -2).all()
                        and (labels[status == 0] >= 0).all()):
                    raise ValueError("Eligibility label convention changed")
                for k in range(config["n_clusters"]):
                    expected = int((labels == k).sum())
                    actual = int(annual[(annual.year == year) & (annual.cluster == k)].iloc[0]["count"])
                    if expected != actual:
                        raise ValueError("Full-population label/count mismatch")
                checked += len(group); population += status.size
    result = dict(status="verified", output_hashes=len(receipt["output_sha256"]),
        sample_predictions=checked, population_rows=population, annual_files=3,
        model_unchanged=True, existing_artifacts_preserved=True,
        thresholds_reproduced_from_training_only=True, nested_sampling_reproduced=True,
        frozen_seal_sha256=sha256(folder / "seal.json"), verifier_sha256=sha256(Path(__file__)))
    write_json(out / "verification.json", result)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="stage3_v1")
    args = parser.parse_args()
    verify(run_id=args.run_id)
