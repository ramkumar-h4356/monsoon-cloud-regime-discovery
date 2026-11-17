import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "06_feature_engineering" / "prepare_m18_7_processing_preflight.py"
spec = importlib.util.spec_from_file_location("m18_7_preflight", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_partition_policy_keeps_2017_in_primary_descriptive_fit():
    plan = json.loads((MODULE_PATH.parents[2] / "config" / "m18_7_processing_plan.json").read_text())
    primary = plan["processing_partitions"]["primary_descriptive_fit"]
    assert primary["include_2017"] is True
    assert primary["fit_years"] == [2010, 2021]


def test_temporal_transfer_split_has_no_year_overlap():
    plan = json.loads((MODULE_PATH.parents[2] / "config" / "m18_7_processing_plan.json").read_text())
    split = plan["processing_partitions"]["temporal_transfer_diagnostic"]
    train = set(range(split["fit_years"][0], split["fit_years"][1] + 1))
    holdout = set(range(split["transform_years"][0], split["transform_years"][1] + 1))
    assert train.isdisjoint(holdout)
    assert split["transition_diagnostic_year"] not in train | holdout


def test_exclude_2017_sensitivity_excludes_transition_year():
    plan = json.loads((MODULE_PATH.parents[2] / "config" / "m18_7_processing_plan.json").read_text())
    split = plan["processing_partitions"]["exclude_2017_sensitivity"]
    assert split["exclude_2017"] is True
    assert 2017 not in range(split["fit_years"][0], split["fit_years"][1] + 1)


def test_storage_estimate_uses_float32_and_uint8_code_arrays():
    selected = {"FS-A": pd.DataFrame({"variable": ["a", "b"]})}
    result = module.estimate_storage(100, selected, 4)
    assert result["FS-A"]["estimated_bytes_per_experiment"] == 100 * 2 * 5


def test_membership_parser_accepts_boolean_and_text():
    assert module._membership(True, "x", "FS-A") is True
    assert module._membership("False", "x", "FS-A") is False


def test_membership_parser_rejects_null():
    with pytest.raises(ValueError, match="Null membership"):
        module._membership(np.nan, "x", "FS-A")


def test_membership_parser_rejects_invalid_text():
    with pytest.raises(ValueError, match="Invalid membership"):
        module._membership("maybe", "x", "FS-A")


def test_registry_count_mismatch_is_rejected(tmp_path):
    row = {
        "variable": ["a"], "family": ["f"],
        "matching_cloud_area_variable": [np.nan],
    }
    for feature_set in module.FEATURE_SET_IDS:
        row[feature_set] = [True]
    path = tmp_path / "registry.csv"
    pd.DataFrame(row).to_csv(path, index=False)
    expected = {feature_set: 1 for feature_set in module.FEATURE_SET_IDS}
    expected["FS-A"] = 2
    with pytest.raises(ValueError, match="expected 2 features, found 1"):
        module.load_registry(path, expected)


def test_registry_rejects_duplicate_variable_names(tmp_path):
    row = {
        "variable": ["a", "a"], "family": ["f", "f"],
        "matching_cloud_area_variable": [np.nan, np.nan],
    }
    for feature_set in module.FEATURE_SET_IDS:
        row[feature_set] = [True, False]
    path = tmp_path / "registry.csv"
    pd.DataFrame(row).to_csv(path, index=False)
    expected = {feature_set: 1 for feature_set in module.FEATURE_SET_IDS}
    with pytest.raises(ValueError, match="blank or duplicate"):
        module.load_registry(path, expected)
