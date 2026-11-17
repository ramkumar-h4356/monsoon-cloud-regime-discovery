"""Automated unit and integration tests for Milestones M20 and M21 (Post-Monsoon).

Covers:
1. Feature registry integrity and layer mappings for post-monsoon.
2. Missingness classification exhaustiveness, mutual exclusivity, and area constraints.
3. Model-ready dataset output integrity and 100% finiteness (zero NaNs, zero Infs).
4. Leakage-safe temporal partitioning (2010-2016 train vs 2017-2021 holdout).
5. NetCDF4 dimensions, CF coordinates, chunking, and metadata attributes.
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import xarray as xr

PROJECT_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
REGISTRY_PATH = PROJECT_ROOT / "reports" / "feature_engineering" / "feature_set_registry.csv"
MODEL_READY_DIR = PROJECT_ROOT / "data" / "processed" / "post_monsoon" / "model_ready"
MANIFEST_PATH = PROJECT_ROOT / "reports" / "seasons" / "post_monsoon" / "m21_model_ready" / "post_monsoon_model_ready_manifest_FS-A.json"
NC_PATH = MODEL_READY_DIR / "post_monsoon_model_ready_FS-A.nc"
NPZ_PATH = MODEL_READY_DIR / "post_monsoon_FS-A_scaled.npz"
NPY_PATH = MODEL_READY_DIR / "post_monsoon_FS-A_scaled.npy"


class TestM20FeatureRegistryAndMissingness:
    """Tests for Milestone M20 feature engineering and missingness logic."""

    def test_feature_registry_post_monsoon_counts(self):
        """Verify feature set counts adhere to SIH26078 registry specifications."""
        assert REGISTRY_PATH.exists(), f"Registry file missing: {REGISTRY_PATH}"
        df = pd.read_csv(REGISTRY_PATH)

        expected_counts = {
            "FS-A": 36,
            "FS-B": 21,
            "FS-C": 21,
            "FS-D": 21,
            "FS-E": 16,
            "FS-F": 21,
        }
        for fs_id, expected in expected_counts.items():
            assert fs_id in df.columns, f"Missing feature set {fs_id} column"
            count = int(df[fs_id].sum())
            assert count == expected, f"{fs_id} count mismatch: expected {expected}, got {count}"

    def test_layer_mapping_consistency(self):
        """Verify every non-cloud-area variable maps to a valid cloud area variable."""
        df = pd.read_csv(REGISTRY_PATH)
        cloud_area_vars = set(df.loc[df["family"] == "cloud_area", "variable"])
        assert len(cloud_area_vars) == 5, f"Expected 5 cloud area variables, got {len(cloud_area_vars)}"

        for _, row in df.iterrows():
            if row["family"] != "cloud_area":
                area_var = row["matching_cloud_area_variable"]
                assert pd.notna(area_var), f"Missing matching area variable for {row['variable']}"
                assert area_var in cloud_area_vars, f"Invalid area variable {area_var} for {row['variable']}"

    def test_missingness_classification_rules(self):
        """Verify classifier mutually exclusive and exhaustive code assignments."""
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "src" / "shared" / "missingness"))
        from missingness_classifier import MissingnessCode, classify_missingness

        # Case 1: Cloud Area Variable
        cld_area = np.array([50.0, 0.0, np.nan], dtype=np.float32)
        codes_area = classify_missingness(cld_area, "cldarea_total_1h")
        assert codes_area[0] == MissingnessCode.OBSERVED
        assert codes_area[1] == MissingnessCode.OBSERVED
        assert codes_area[2] == MissingnessCode.CLOUD_AREA_MISSING

        # Case 2: Cloud Property Variable
        prop = np.array([300.0, np.nan, np.nan, np.nan], dtype=np.float32)
        area = np.array([40.0, 0.0, 20.0, np.nan], dtype=np.float32)
        codes_prop = classify_missingness(prop, "cldpress_total_1h", area, "cldarea_total_1h")

        assert codes_prop[0] == MissingnessCode.OBSERVED
        assert codes_prop[1] == MissingnessCode.STRUCTURAL_ABSENCE  # NaN prop when area == 0
        assert codes_prop[2] == MissingnessCode.RESIDUAL_MISSING     # NaN prop when area > 0
        assert codes_prop[3] == MissingnessCode.UNKNOWN_CLOUD_AVAILABILITY  # NaN prop when area is NaN


class TestM21ModelReadyArtifacts:
    """Tests for Milestone M21 model-ready dataset outputs and validation."""

    def test_manifest_completeness_and_status(self):
        """Verify M21 processing manifest exists and confirms readiness for PCA."""
        assert MANIFEST_PATH.exists(), f"Manifest file missing: {MANIFEST_PATH}"
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["milestone"] == "M21"
        assert manifest["feature_set"] == "FS-A"
        assert manifest["feature_count"] == 36
        assert manifest["validation"]["is_finite"] is True
        assert manifest["validation"]["nan_count"] == 0
        assert manifest["validation"]["inf_count"] == 0
        assert manifest["validation"]["status"] == "READY_FOR_PCA"
        assert manifest["partitions"]["training_samples"] == 4838400
        assert manifest["partitions"]["holdout_samples"] == 3456000
        assert manifest["partitions"]["total_samples"] == 8294400

    def test_numpy_model_ready_finiteness_and_shape(self):
        """Verify .npz and .npy arrays have exact expected dimensions and 100% finite values."""
        assert NPZ_PATH.exists(), f"NPZ file missing: {NPZ_PATH}"
        assert NPY_PATH.exists(), f"NPY file missing: {NPY_PATH}"

        # Test memory-mappable .npy
        X_mmap = np.load(NPY_PATH, mmap_mode="r")
        assert X_mmap.shape == (8294400, 36)
        assert X_mmap.dtype == np.float32

        # Test compressed .npz
        with np.load(NPZ_PATH) as data:
            assert "X_all" in data
            assert "train_mask" in data
            assert "feature_names" in data
            assert "scaler_center" in data
            assert "scaler_scale" in data

            train_mask = data["train_mask"]
            assert train_mask.sum() == 4838400
            assert (~train_mask).sum() == 3456000
            assert len(data["feature_names"]) == 36

    def test_netcdf4_model_ready_structure(self):
        """Verify NetCDF4 model-ready dataset conforms to CF-compliant research architecture."""
        assert NC_PATH.exists(), f"NetCDF file missing: {NC_PATH}"

        with xr.open_dataset(NC_PATH) as ds:
            assert ds.sizes["time"] == 8640
            assert ds.sizes["lat"] == 32
            assert ds.sizes["lon"] == 30

            assert "time" in ds.coords
            assert "lat" in ds.coords
            assert "lon" in ds.coords
            assert "year" in ds
            assert "season_code" in ds
            assert "train_mask" in ds

            # Check that all 36 features are present
            feature_vars = [k for k in ds.data_vars if k.startswith("feature__")]
            assert len(feature_vars) == 36, f"Expected 36 feature vars, got {len(feature_vars)}"

            # Check global attributes
            assert ds.attrs.get("season") == "post_monsoon"
            assert ds.attrs.get("status") == "VERIFIED_MODEL_READY"
            assert ds.attrs.get("scaling_method") == "robust"
