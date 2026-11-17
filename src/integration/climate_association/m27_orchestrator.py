"""M27 — Master End-to-End Orchestrator.

Orchestrates the complete research pipeline for Milestone M27:
Integrated ENSO–IOD Climate Teleconnection and Cloud-Regime Analysis.

Execution Stages:
1. M27.2: Climate-Index Loader and Alignment Engine
2. M27.3: Cloud-Regime Modulation Engine
3. M27.4: Rainfall Modulation Engine
4. M27.5: Joint ENSO–IOD and Spatial Teleconnections Engines
5. M27.6: Publication-Quality Figure Suite (10 figures at 300 DPI)
6. Deliverable Verification, Cryptographic Manifest Generation, and Standalone ZIP Packaging
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List
import zipfile

import pandas as pd

from src.integration.climate_association.m27_climate_index_loader import (
    ClimateIndexLoader,
)
from src.integration.climate_association.m27_regime_climate_correlation import (
    RegimeClimateCorrelationEngine,
)
from src.integration.climate_association.m27_rainfall_modulation import (
    RainfallClimateModulationEngine,
)
from src.integration.climate_association.m27_joint_climate_analysis import (
    JointClimateAnalysisEngine,
)
from src.integration.climate_association.m27_spatial_teleconnections import (
    SpatialTeleconnectionEngine,
)
from src.integration.climate_association.generate_m27_figures import (
    M27FigureGenerator,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPORTS_DIR = PROJECT_ROOT / "reports" / "integration" / "m27"
TABLES_DIR = REPORTS_DIR / "tables"
FIGURES_DIR = REPORTS_DIR / "figures"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "climate_indices"


def compute_sha256(filepath: Path) -> str:
    """Compute cryptographic SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class M27Orchestrator:
    """Master orchestrator for executing the complete M27 pipeline."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or PROJECT_ROOT
        self.reports_dir = REPORTS_DIR
        self.tables_dir = TABLES_DIR
        self.figures_dir = FIGURES_DIR
        self.processed_dir = PROCESSED_DIR

    def run_all(self, B_perm: int = 100_000, seed: int = 42) -> Dict[str, Any]:
        """Execute all M27 stages sequentially and generate deliverables."""
        start_time = time.time()
        logger.info("================================================================================")
        logger.info("STARTING M27: INTEGRATED ENSO-IOD CLIMATE TELECONNECTION AND CLOUD-REGIME PIPELINE")
        logger.info("================================================================================")

        # ---------------------------------------------------------
        # STAGE 1: M27.2 Climate Index Loader & Alignment
        # ---------------------------------------------------------
        logger.info("\n--- [Stage 1/6] Running M27.2 Climate Index Loader & Alignment ---")
        t0 = time.time()
        loader = ClimateIndexLoader()
        loader.export_aligned_table()
        logger.info(f"Stage 1 completed in {time.time() - t0:.2f}s")

        # ---------------------------------------------------------
        # STAGE 2: M27.3 Cloud-Regime Modulation Engine
        # ---------------------------------------------------------
        logger.info("\n--- [Stage 2/6] Running M27.3 Cloud-Regime Modulation Engine ---")
        t0 = time.time()
        regime_engine = RegimeClimateCorrelationEngine()
        regime_engine.export_all(B_perm=B_perm, seed=seed)
        logger.info(f"Stage 2 completed in {time.time() - t0:.2f}s")

        # ---------------------------------------------------------
        # STAGE 3: M27.4 Rainfall Modulation Engine
        # ---------------------------------------------------------
        logger.info("\n--- [Stage 3/6] Running M27.4 Rainfall Modulation Engine ---")
        t0 = time.time()
        rain_engine = RainfallClimateModulationEngine()
        rain_engine.export_all(B_perm=B_perm, seed=seed)
        logger.info(f"Stage 3 completed in {time.time() - t0:.2f}s")

        # ---------------------------------------------------------
        # STAGE 4: M27.5 Joint ENSO-IOD & Spatial Engines
        # ---------------------------------------------------------
        logger.info("\n--- [Stage 4/6] Running M27.5 Joint Climate & Spatial Teleconnections ---")
        t0 = time.time()
        joint_engine = JointClimateAnalysisEngine()
        joint_engine.export_all(B_perm=B_perm, seed=seed)

        spatial_engine = SpatialTeleconnectionEngine()
        spatial_engine.export_all()
        logger.info(f"Stage 4 completed in {time.time() - t0:.2f}s")

        # ---------------------------------------------------------
        # STAGE 5: M27.6 Figure Generation Suite
        # ---------------------------------------------------------
        logger.info("\n--- [Stage 5/6] Generating Publication Figures (300 DPI) ---")
        t0 = time.time()
        fig_gen = M27FigureGenerator()
        fig_paths = fig_gen.generate_all_figures()
        logger.info(f"Stage 5 completed in {time.time() - t0:.2f}s")

        # ---------------------------------------------------------
        # STAGE 6: Manifest & Packaging
        # ---------------------------------------------------------
        logger.info("\n--- [Stage 6/6] Generating Cryptographic Manifest & Standalone ZIP Archive ---")
        t0 = time.time()
        manifest_path, zip_path = self.build_manifest_and_zip()
        logger.info(f"Stage 6 completed in {time.time() - t0:.2f}s")

        total_duration = time.time() - start_time
        logger.info("================================================================================")
        logger.info(f"M27 PIPELINE EXECUTION COMPLETED SUCCESSFULLY IN {total_duration:.2f}s")
        logger.info("================================================================================")

        return {
            "status": "SUCCESS",
            "duration_seconds": round(total_duration, 2),
            "manifest_path": str(manifest_path),
            "zip_path": str(zip_path),
            "figures_count": len(fig_paths),
        }

    def build_manifest_and_zip(self) -> Tuple[Path, Path]:
        """Generate m27_manifest.json and M27-climate-teleconnections.zip."""
        manifest_records: List[Dict[str, Any]] = []

        # 1. Collect Processed Data files
        for p in sorted(self.processed_dir.glob("m27_*.parquet")):
            manifest_records.append({
                "category": "processed_data",
                "relative_path": str(p.relative_to(self.project_root)).replace("\\", "/"),
                "size_bytes": p.stat().st_size,
                "sha256": compute_sha256(p),
            })

        # 2. Collect Table files
        for p in sorted(self.tables_dir.glob("m27_*.csv")):
            manifest_records.append({
                "category": "tables",
                "relative_path": str(p.relative_to(self.project_root)).replace("\\", "/"),
                "size_bytes": p.stat().st_size,
                "sha256": compute_sha256(p),
            })

        # 3. Collect Figure files
        for p in sorted(self.figures_dir.glob("fig*.png")):
            manifest_records.append({
                "category": "figures",
                "relative_path": str(p.relative_to(self.project_root)).replace("\\", "/"),
                "size_bytes": p.stat().st_size,
                "sha256": compute_sha256(p),
            })

        # 4. Collect Code files
        code_dir = self.project_root / "src" / "integration" / "climate_association"
        for p in sorted(code_dir.glob("m27_*.py")) + sorted(code_dir.glob("generate_m27_*.py")) + sorted(code_dir.glob("mirror_m27_*.py")):
            manifest_records.append({
                "category": "source_code",
                "relative_path": str(p.relative_to(self.project_root)).replace("\\", "/"),
                "size_bytes": p.stat().st_size,
                "sha256": compute_sha256(p),
            })

        # 5. Collect Test files
        test_dir = self.project_root / "tests" / "integration"
        for p in sorted(test_dir.glob("test_m27_*.py")):
            manifest_records.append({
                "category": "tests",
                "relative_path": str(p.relative_to(self.project_root)).replace("\\", "/"),
                "size_bytes": p.stat().st_size,
                "sha256": compute_sha256(p),
            })

        manifest_data = {
            "milestone": "M27 — Integrated ENSO–IOD Climate Teleconnection and Cloud-Regime Analysis",
            "study_period": "2010–2021",
            "sample_size": "N=12 independent annual seasons",
            "spatial_domain": "328 Tier 1 Indian terrestrial grid cells (6°N–38°N, 68°E–98°E)",
            "frozen_dependencies": {
                "m25_cloud_regimes": "combined_3season_cluster_labels.npy (K=4: R0, R1, R2, R3)",
                "m26_rainfall_validation": "m26_cloud_rainfall_matched_primary.parquet (342,432 rows)",
                "noaa_roni": "RONI.ascii.txt (SHA256: 1297887f...)",
                "noaa_dmi": "dmi.had.long.csv (SHA256: 6f5772b2...)",
            },
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "artifact_count": len(manifest_records),
            "artifacts": manifest_records,
        }

        manifest_path = self.reports_dir / "m27_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # 6. Build Standalone Handoff ZIP Archive
        zip_path = self.reports_dir / "M27-climate-teleconnections.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            zf.write(manifest_path, arcname=f"reports/integration/m27/{manifest_path.name}")
            # Add all items in manifest
            for item in manifest_records:
                full_path = self.project_root / item["relative_path"]
                if full_path.exists():
                    zf.write(full_path, arcname=item["relative_path"])

        logger.info(f"Generated manifest: {manifest_path} ({manifest_path.stat().st_size} bytes)")
        logger.info(f"Generated standalone zip: {zip_path} ({zip_path.stat().st_size} bytes)")

        return manifest_path, zip_path


if __name__ == "__main__":
    orchestrator = M27Orchestrator()
    res = orchestrator.run_all(B_perm=100_000)
    print("M27 Orchestrator Output:")
    print(json.dumps(res, indent=2))
