import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "src" / "06_feature_engineering"
sys.path.insert(0, str(MODULE_DIR))

from missingness_classifier import MissingnessCode
from missingness_treatments import fit_property_treatment
from process_m18_7_datasets import (
    _count_codes,
    _fit_out_of_core_scaler,
    _fit_treatment_models,
    _model_columns,
    _parse_dataset_name,
    _transform_feature_chunk,
    calculate_storage_estimate,
    discover_input_files,
    load_feature_registry,
)


def registry_frame():
    return pd.DataFrame([
        {
            "variable": "cldarea_high_1h", "family": "cloud_area",
            "matching_cloud_area_variable": "", "FS-A": True,
        },
        {
            "variable": "cldarea_low_1h", "family": "cloud_area",
            "matching_cloud_area_variable": "", "FS-A": True,
        },
        {
            "variable": "cldhght_high_1h", "family": "effective_height",
            "matching_cloud_area_variable": "cldarea_high_1h", "FS-A": True,
        },
    ])


def test_parse_dataset_name():
    assert _parse_dataset_name(Path("CERES_2017_established_monsoon.nc")) == (
        2017, "established_monsoon"
    )


def test_parse_dataset_name_rejects_invalid_filename():
    with pytest.raises(ValueError, match="Unexpected CERES filename"):
        _parse_dataset_name(Path("bad_name.nc"))


def test_model_columns_sa_a_and_ca_a_include_unknown_and_area_availability():
    rows = registry_frame()
    columns = _model_columns(rows, {
        "property_treatment": "SA-A", "cloud_area_treatment": "CA-A"
    })
    names = [item["name"] for item in columns]
    assert "feature__cldhght_high_1h" in names
    assert "indicator__cldhght_high_1h__unknown_cloud_availability" in names
    assert "indicator__cldarea_low_1h__availability_missing" in names
    assert all(not item["scale"] for item in columns if item["kind"] == "indicator")


def test_model_columns_md_b_adds_residual_indicator():
    columns = _model_columns(registry_frame(), {
        "property_treatment": "MD-B", "cloud_area_treatment": "CA-A"
    })
    names = [item["name"] for item in columns]
    assert "indicator__cldhght_high_1h__residual_missingness" in names


def test_model_columns_sa_b_adds_structural_indicator():
    columns = _model_columns(registry_frame(), {
        "property_treatment": "SA-B", "cloud_area_treatment": "CA-A"
    })
    names = [item["name"] for item in columns]
    assert "indicator__cldhght_high_1h__structural_absence" in names


def test_model_columns_ca_b_does_not_add_area_missing_indicator():
    columns = _model_columns(registry_frame(), {
        "property_treatment": "SA-A", "cloud_area_treatment": "CA-B"
    })
    names = [item["name"] for item in columns]
    assert not any("cldarea" in name and "indicator" in name for name in names)


def test_count_codes_preserves_all_five_classes():
    codes = np.array([0, 1, 2, 3, 4, 0], dtype=np.uint8)
    result = _count_codes(codes)
    assert result == {
        "observed": 2,
        "structural_absence": 1,
        "residual_missing": 1,
        "unknown_cloud_availability": 1,
        "cloud_area_missing": 1,
    }


def test_storage_estimate_includes_indicator_bytes():
    selected = {"FS-A": registry_frame()}
    registry = registry_frame()
    estimate = calculate_storage_estimate(1000, selected, registry)
    assert estimate["experiment_count"] == 4
    assert estimate["indicator_bytes"] > 0
    assert estimate["total_uncompressed_output_bytes"] == (
        estimate["feature_and_code_bytes"] + estimate["indicator_bytes"]
    )
    assert estimate["recommended_free_space_bytes"] > estimate["total_uncompressed_output_bytes"]


def test_treatment_models_fit_cloud_area_and_property_for_ca_a():
    rows = registry_frame()
    area_high = np.array([0, 2, 3, 4, 5, 6], dtype=np.float32)
    area_low = np.array([0, 1, 2, 3, 4, 5], dtype=np.float32)
    prop = np.array([np.nan, 1, 2, 3, 4, 5], dtype=np.float32)
    raw = {
        "cldarea_high_1h": area_high,
        "cldarea_low_1h": area_low,
        "cldhght_high_1h": prop,
    }
    area_map = {"cldhght_high_1h": "cldarea_high_1h"}
    models, counts, screening = _fit_treatment_models(
        rows,
        {"property_treatment": "SA-A", "cloud_area_treatment": "CA-A"},
        raw,
        area_map,
    )
    assert models["cldarea_high_1h"].median == 3.5
    assert models["cldhght_high_1h"].conditional_median == 3.0
    assert counts["cldhght_high_1h"]["residual_missing"] == 0
    assert screening["cldarea_low_1h"]["decision"] == "IMPUTE_CA_A"


def test_ca_b_excludes_area_with_more_than_twenty_percent_missing():
    rows = registry_frame()
    area_high = np.array([0, 2, 3, 4, 5, 6], dtype=np.float32)
    area_low = np.array([np.nan, np.nan, 2, 3, 4, 5], dtype=np.float32)
    prop = np.array([np.nan, 1, 2, 3, 4, 5], dtype=np.float32)
    raw = {
        "cldarea_high_1h": area_high,
        "cldarea_low_1h": area_low,
        "cldhght_high_1h": prop,
    }
    area_map = {"cldhght_high_1h": "cldarea_high_1h"}
    _, _, screening = _fit_treatment_models(
        rows,
        {"property_treatment": "SA-A", "cloud_area_treatment": "CA-B"},
        raw,
        area_map,
    )
    assert screening["cldarea_low_1h"]["excluded_from_model_matrix"] is True


def test_ca_b_does_not_silently_impute_a_retained_area_feature():
    rows = registry_frame()
    area_high = np.array([0, 2, 3, 4, 5, 6], dtype=np.float32)
    area_low = np.array([0, 1, 2, 3, 4, 5], dtype=np.float32)
    prop = np.array([np.nan, 1, 2, 3, 4, 5], dtype=np.float32)
    raw = {
        "cldarea_high_1h": area_high,
        "cldarea_low_1h": area_low,
        "cldhght_high_1h": prop,
    }
    raw["cldarea_high_1h"][0] = np.nan
    with pytest.raises(ValueError, match="screening-only"):
        _fit_treatment_models(
            rows,
            {"property_treatment": "SA-A", "cloud_area_treatment": "CA-B"},
            raw,
            {"cldhght_high_1h": "cldarea_high_1h"},
        )


def test_transform_feature_chunk_creates_scaled_inputs_and_codes():
    rows = registry_frame()
    area = np.array([0, 2, 3, 4], dtype=np.float32)
    low = np.array([0, 1, 2, 3], dtype=np.float32)
    prop = np.array([np.nan, 1, 2, np.nan], dtype=np.float32)
    raw = {
        "cldarea_high_1h": area,
        "cldarea_low_1h": low,
        "cldhght_high_1h": prop,
    }
    models, _, _ = _fit_treatment_models(
        rows,
        {"property_treatment": "MD-B", "cloud_area_treatment": "CA-A"},
        raw,
        {"cldhght_high_1h": "cldarea_high_1h"},
    )
    columns, codes = _transform_feature_chunk(
        rows,
        {"property_treatment": "MD-B", "cloud_area_treatment": "CA-A"},
        raw,
        models,
        {"cldhght_high_1h": "cldarea_high_1h"},
        0,
        4,
    )
    assert "indicator__cldhght_high_1h__residual_missingness" in columns
    assert "indicator__cldhght_high_1h__unknown_cloud_availability" in columns
    assert codes["cldhght_high_1h"].shape == (4,)
    assert np.isfinite(columns["feature__cldhght_high_1h"]).all()


def test_out_of_core_scaler_matches_expected_robust_parameters():
    rows = pd.DataFrame([
        {"variable": "cldarea_high_1h", "family": "cloud_area"},
    ])
    raw = {"cldarea_high_1h": np.array([0, 1, 2, 3, 4], dtype=np.float32)}
    models = {"cldarea_high_1h": None}
    columns = _model_columns(rows, {
        "property_treatment": "SA-A", "cloud_area_treatment": "CA-B"
    })
    # For CA-B, the area is complete and is not imputed.
    model = _fit_out_of_core_scaler(
        rows,
        {"scaler": "robust", "weighting": "equal", "cloud_area_treatment": "CA-B"},
        models,
        raw,
        {},
        5,
        columns,
    )
    idx = model.feature_names.index("feature__cldarea_high_1h")
    assert model.center[idx] == 2.0
    assert model.scale[idx] == 2.0
    assert model.n_training_samples == 5


def test_out_of_core_scaler_standard_parameters():
    rows = pd.DataFrame([
        {"variable": "cldarea_high_1h", "family": "cloud_area"},
    ])
    raw = {"cldarea_high_1h": np.array([1, 2, 3, 4], dtype=np.float32)}
    columns = _model_columns(rows, {
        "property_treatment": "SA-A", "cloud_area_treatment": "CA-B"
    })
    model = _fit_out_of_core_scaler(
        rows,
        {"scaler": "standard", "weighting": "equal", "cloud_area_treatment": "CA-B"},
        {}, raw, {}, 4, columns,
    )
    idx = model.feature_names.index("feature__cldarea_high_1h")
    assert model.center[idx] == pytest.approx(2.5)
    assert model.scale[idx] == pytest.approx(np.std([1, 2, 3, 4], ddof=0))


def test_discover_input_files_checks_and_orders_single_synthetic_file(tmp_path):
    season_dir = tmp_path / "pre_monsoon"
    season_dir.mkdir()
    times = pd.date_range("2010-04-15", periods=2, freq="h")
    ds = xr.Dataset(
        {"x": (("time", "lat", "lon"), np.ones((2, 2, 2), dtype=np.float32))},
        coords={"time": times, "lat": [1.0, 2.0], "lon": [10.0, 11.0]},
    )
    ds.to_netcdf(season_dir / "CERES_2010_pre_monsoon.nc", engine="scipy")
    expected = {
        "datasets": 1,
        "start_year": 2010,
        "end_year": 2010,
        "seasons": ["pre_monsoon"],
        "timestamps_per_dataset": 2,
        "latitude_count": 2,
        "longitude_count": 2,
    }
    records, lat, lon = discover_input_files(tmp_path, expected)
    assert len(records) == 1
    assert records[0]["year"] == 2010
    np.testing.assert_array_equal(lat, [1.0, 2.0])
    np.testing.assert_array_equal(lon, [10.0, 11.0])


def test_load_feature_registry_rejects_wrong_feature_count(tmp_path):
    path = tmp_path / "registry.csv"
    frame = registry_frame()
    for feature_set in ("FS-B", "FS-C", "FS-D", "FS-E", "FS-F"):
        frame[feature_set] = False
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="FS-B"):
        load_feature_registry(path, {"FS-A": 3, "FS-B": 1})


def test_out_of_core_scaler_family_balanced_weights():
    rows = pd.DataFrame([
        {"variable": "a", "family": "cloud_area"},
        {"variable": "b", "family": "cloud_area"},
    ])
    raw = {
        "a": np.array([1, 2, 3, 4], dtype=np.float32),
        "b": np.array([10, 20, 30, 40], dtype=np.float32),
    }
    columns = [
        {"name": "feature__a", "kind": "feature", "source_variable": "a", "indicator_type": None, "family": "cloud_area", "scale": True},
        {"name": "feature__b", "kind": "feature", "source_variable": "b", "indicator_type": None, "family": "cloud_area", "scale": True},
    ]
    model = _fit_out_of_core_scaler(
        rows,
        {"scaler": "robust", "weighting": "family_balanced", "cloud_area_treatment": "CA-B"},
        {}, raw, {}, 4, columns,
    )
    np.testing.assert_allclose(model.feature_weights, [1 / np.sqrt(2), 1 / np.sqrt(2)])


def test_storage_estimate_has_twenty_four_runs_for_six_sets():
    # The estimate helper follows four Stage A/B runs per feature set.
    frames = {}
    for fs in ("FS-A", "FS-B", "FS-C", "FS-D", "FS-E", "FS-F"):
        frames[fs] = pd.DataFrame([
            {"variable": f"cldarea_{fs}_1h", "family": "cloud_area"},
            {"variable": f"property_{fs}_1h", "family": "effective_height"},
        ])
    estimate = calculate_storage_estimate(100, frames, pd.DataFrame())
    assert estimate["experiment_count"] == 24
    assert len(estimate["per_run"]) == 24


def test_output_model_matrix_order_is_deterministic():
    rows = registry_frame()
    experiment = {"property_treatment": "SA-B", "cloud_area_treatment": "CA-A"}
    first = _model_columns(rows, experiment)
    second = _model_columns(rows, experiment)
    assert [item["name"] for item in first] == [item["name"] for item in second]


def test_missingness_classification_codes_are_not_scaled_columns():
    rows = registry_frame()
    columns = _model_columns(rows, {
        "property_treatment": "SA-A", "cloud_area_treatment": "CA-A"
    })
    assert not any("missingness_code" in item["name"] for item in columns)


def test_netcdf4_writer_creates_compressed_output_schema(tmp_path):
    netcdf4 = pytest.importorskip("netCDF4")
    from feature_scaling import FeatureScalingModel
    from process_m18_7_datasets import _create_netcdf_output, _validate_written_output

    output = tmp_path / "pilot.nc.tmp"
    columns = [
        {
            "name": "feature__cldarea_high_1h", "kind": "feature",
            "source_variable": "cldarea_high_1h", "indicator_type": None,
            "family": "cloud_area", "scale": True,
        },
        {
            "name": "indicator__cldarea_high_1h__availability_missing",
            "kind": "indicator", "source_variable": "cldarea_high_1h",
            "indicator_type": "availability_missing", "family": None,
            "scale": False,
        },
    ]
    model = FeatureScalingModel(
        scaler_type="robust", weighting="equal",
        feature_names=tuple(item["name"] for item in columns),
        feature_families=("cloud_area", None),
        scale_mask=(True, False),
        center=np.array([2.0, 0.0]),
        scale=np.array([1.0, 1.0]),
        feature_weights=np.array([1.0, 1.0]),
        n_training_samples=8,
        quantile_range=(25.0, 75.0),
    )
    _create_netcdf_output(
        output,
        ["cldarea_high_1h"],
        columns,
        ["cldarea_high_1h"],
        np.array([10.0, 11.0], dtype=np.float32),
        np.array([70.0, 71.0], dtype=np.float32),
        np.array(["2010-04-15T00", "2010-04-15T01"], dtype="datetime64[h]"),
        [2010, 2010],
        [1, 1],
        {
            "stage": "A", "feature_set": "FS-A",
            "property_treatment": "SA-A", "cloud_area_treatment": "CA-A",
            "scaler": "robust", "weighting": "equal",
        },
        "test-run",
        [{"path": Path("input.nc"), "size_bytes": 100, "mtime_ns": 1}],
        model,
        24,
    )
    with netcdf4.Dataset(output, "a") as ds:
        ds.variables["feature__cldarea_high_1h"][:, :, :] = 0.5
        ds.variables["indicator__cldarea_high_1h__availability_missing"][:, :, :] = 0
        ds.variables["missingness_code__cldarea_high_1h"][:, :, :] = 0
    with netcdf4.Dataset(output, "r") as ds:
        assert ds.dimensions["time"].size == 2
        assert ds.variables["feature__cldarea_high_1h"].filters()["zlib"] is True
        assert "missingness_code__cldarea_high_1h" in ds.variables
        assert ds.variables["season_code"][:].tolist() == [1, 1]
        assert ds.getncattr("processing_partition") == "primary_descriptive_fit"
    validation = _validate_written_output(
        output, 2, 2, 2, columns, ["cldarea_high_1h"], "test-run", 24
    )
    assert validation["status"] == "PASS"


def test_preflight_report_must_pass_and_match_observation_count(tmp_path):
    from process_m18_7_datasets import validate_preflight_report

    report_path = tmp_path / "preflight.json"
    report_path.write_text(json.dumps({
        "status": "PASS",
        "processing_executed": False,
        "input_validation": {
            "file_count": 36,
            "grid_cell_hour_observations": 12345,
        },
    }), encoding="utf-8")
    report = validate_preflight_report(report_path, 12345, 36)
    assert report["status"] == "PASS"
    with pytest.raises(ValueError, match="observation count"):
        validate_preflight_report(report_path, 12346, 36)


def test_preflight_report_rejects_non_pass_status(tmp_path):
    from process_m18_7_datasets import validate_preflight_report

    report_path = tmp_path / "preflight.json"
    report_path.write_text(json.dumps({
        "status": "REVIEW",
        "processing_executed": False,
        "input_validation": {
            "file_count": 36,
            "grid_cell_hour_observations": 12345,
        },
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="PASS status"):
        validate_preflight_report(report_path, 12345, 36)


def test_ca_b_excluded_area_keeps_diagnostic_missingness_codes():
    rows = registry_frame()
    raw = {
        "cldarea_high_1h": np.array([0, 1, 2, 3], dtype=np.float32),
        "cldarea_low_1h": np.array([np.nan, 1, 2, 3], dtype=np.float32),
        "cldhght_high_1h": np.array([1, 2, 3, 4], dtype=np.float32),
    }
    models, _, _ = _fit_treatment_models(
        rows,
        {"property_treatment": "SA-A", "cloud_area_treatment": "CA-B"},
        raw,
        {"cldhght_high_1h": "cldarea_high_1h"},
    )
    columns, codes = _transform_feature_chunk(
        rows,
        {"property_treatment": "SA-A", "cloud_area_treatment": "CA-B"},
        raw,
        models,
        {"cldhght_high_1h": "cldarea_high_1h"},
        0,
        4,
        excluded_features={"cldarea_low_1h"},
    )
    assert "feature__cldarea_low_1h" not in columns
    assert "cldarea_low_1h" in codes
    assert codes["cldarea_low_1h"].tolist() == [4, 0, 0, 0]


def test_discover_input_files_preserves_irregular_monotonic_timestamps(tmp_path):
    season_dir = tmp_path / "established_monsoon"
    season_dir.mkdir()
    times = pd.to_datetime([
        "2010-07-15T00:30:00",
        "2010-07-15T01:30:00",
        "2010-07-15T04:30:00",
    ])
    ds = xr.Dataset(
        {"x": (("time", "lat", "lon"), np.ones((3, 2, 2), dtype=np.float32))},
        coords={"time": times, "lat": [1.0, 2.0], "lon": [10.0, 11.0]},
    )
    ds.to_netcdf(
        season_dir / "CERES_2010_established_monsoon.nc",
        engine="scipy",
    )
    expected = {
        "datasets": 1,
        "start_year": 2010,
        "end_year": 2010,
        "seasons": ["established_monsoon"],
        "timestamps_per_dataset": 3,
        "latitude_count": 2,
        "longitude_count": 2,
    }

    records, _, _ = discover_input_files(tmp_path, expected)

    assert records[0]["time_count"] == 3
    assert records[0]["timestamp_diagnostics"]["interval_count"] == 2
    assert records[0]["timestamp_diagnostics"]["min_interval_seconds"] == 3600
    assert records[0]["timestamp_diagnostics"]["max_interval_seconds"] == 10800
    assert records[0]["timestamp_diagnostics"]["non_hourly_interval_count"] == 1
    assert records[0]["times"][0] == pd.Timestamp("2010-07-15T00:30:00")
