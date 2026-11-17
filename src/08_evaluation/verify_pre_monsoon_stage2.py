"""Verify completed Stage 2 artifacts without fitting or opening holdout data."""
import argparse
import json
from pathlib import Path
import re
import sys

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/06_feature_engineering"))
sys.path.insert(0, str(ROOT / "src/07_clustering"))
from ceres_features import load_json, sha256
from pre_monsoon_stage2_model import project
from run_pre_monsoon_stage2 import ALLOWED_TRAIN, ALLOWED_DEVELOPMENT, allowed_year, input_path


def verify(root=ROOT, run_id="stage2_v1"):
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id):
        raise ValueError("Invalid run ID")
    reports = root / "reports/phase2/pre_monsoon" / run_id
    manifest = load_json(reports / "manifest.json")
    assert manifest["status"] == "complete"
    assert manifest["holdout_accessed"] is False and manifest["holdout_evaluated"] is False
    assert manifest["fit_years"] == ALLOWED_TRAIN
    assert manifest["development_years"] == ALLOWED_DEVELOPMENT
    for key in ("output_sha256", "code_sha256"):
        for path, digest in manifest[key].items():
            assert sha256(root / path) == digest, path
    for item in manifest["accessed_inputs"]:
        allowed_year(item["year"], item["split"])
        assert sha256(root / item["path"]) == item["sha256"]
    stage1_path = root / "reports/phase2/pre_monsoon" / manifest["config"]["stage1_run_id"] / "manifest.json"
    assert sha256(stage1_path) == manifest["stage1_manifest_sha256"]
    stage1 = load_json(stage1_path)
    assert all(sha256(root / path) == digest for path, digest in stage1["protected_files"].items())
    bundle = joblib.load(root / "results/models/phase2/pre_monsoon" / run_id / "selected_pre_monsoon_bundle.joblib")
    assert bundle["season"] == "pre_monsoon" and bundle["fit_years"] == ALLOWED_TRAIN
    assert bundle["contract_sha256"] == manifest["contract_sha256"]
    assert bundle["selected_n_components"] == manifest["selected_n_components"]
    samples = pd.read_csv(reports / "sample_physical_values_and_labels.csv")
    assert samples.year.isin(ALLOWED_TRAIN + ALLOWED_DEVELOPMENT).all()
    assert not samples.observation_id.duplicated().any()
    annual = pd.read_csv(reports / "annual_occurrence.csv")
    assert annual.year.isin(ALLOWED_TRAIN + ALLOWED_DEVELOPMENT).all()
    training = []
    total_rows, eligible_rows = 0, 0
    with threadpool_limits(1):
        for year in ALLOWED_TRAIN + ALLOWED_DEVELOPMENT:
            split = "train" if year in ALLOWED_TRAIN else "development"
            subset = samples[samples.year == year]
            indices = subset.flat_index.to_numpy(dtype=int)
            prepared_path = input_path(root, manifest["config"], year, split)
            label_path = root / "data/processed/model_ready/phase2/pre_monsoon" / run_id / f"CERES_{year}_pre_monsoon_labels.nc"
            with xr.open_dataset(prepared_path) as ds, xr.open_dataset(label_path) as labeled:
                assert all(np.array_equal(ds[c].values, labeled[c].values) for c in ("time", "lat", "lon"))
                x = np.column_stack([ds[name].values.ravel()[indices] for name in bundle["feature_order"]])
                predictions = bundle["kmeans"].predict(project(bundle, x, bundle["selected_n_components"]))
                np.testing.assert_array_equal(predictions, subset.cluster)
                np.testing.assert_array_equal(predictions, labeled.cluster.values.ravel()[indices])
                labels = labeled.cluster.values
                status = ds.status.values
                assert (labels[status == 1] == -1).all()
                assert (labels[status >= 2] == -2).all()
                assert (labels[status == 0] >= 0).all()
                for cluster in range(bundle["kmeans"].n_clusters):
                    row = annual[(annual.year == year) & (annual.cluster == cluster)].iloc[0]
                    assert int(row["count"]) == int((labels == cluster).sum())
                eligible_rows += int((status == 0).sum())
                total_rows += status.size
                if split == "train":
                    training.append(x)
    x_train = np.concatenate(training).astype("float64")
    np.testing.assert_allclose(bundle["imputer"].statistics_, np.median(x_train, axis=0), atol=1e-12)
    np.testing.assert_allclose(bundle["scaler"].mean_, x_train.mean(axis=0), atol=1e-12)
    assert int(bundle["scaler"].n_samples_seen_) == len(x_train)
    assert bundle["pca"].n_samples_ == len(x_train)
    assert bundle["training_observation_ids"] == samples[samples.split == "train"].observation_id.tolist()
    result = dict(status="verified", stage2_output_hashes=len(manifest["output_sha256"]),
        stage2_code_hashes=len(manifest["code_sha256"]), input_files=len(manifest["accessed_inputs"]),
        training_fitted_rows=len(x_train), sample_predictions_verified=len(samples),
        population_rows=total_rows, population_eligible_rows=eligible_rows,
        annual_label_files=9, phase1_stage1_preserved=True, holdout_accessed=False,
        verification_script_sha256=sha256(Path(__file__)))
    output = root / "reports/phase2/pre_monsoon" / f"{run_id}_verification.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="stage2_v1")
    args = parser.parse_args()
    verify(run_id=args.run_id)
