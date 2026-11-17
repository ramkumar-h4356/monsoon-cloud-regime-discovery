"""M27.7.2 — Master Pipeline Orchestrator and Package Builder.

Coordinates and executes:
1. FDR and Multiplicity Reconciliation.
2. Freedman-Lane Methodology Audit.
3. Year-Block Dependence and Effective Sample Size Audit.
4. Spatial Field Permutation Verification and Algorithmic Documentation.
5. Figure Annotations and Scientific Language Audits.
6. Scientific Acceptance Report Generation.
7. Manifest Generation with SHA-256 Checksums.
8. Self-Contained Verification ZIP Package Generation and Validation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Tuple
import zipfile

import numpy as np
import pandas as pd
import scipy

from src.integration.climate_association.m27_7_2.m27_7_2_fdr_reconciler import (
    FDRReconciler,
)
from src.integration.climate_association.m27_7_2.m27_7_2_freedman_lane_auditor import (
    FreedmanLaneAuditor,
)
from src.integration.climate_association.m27_7_2.m27_7_2_year_dependence_auditor import (
    YearDependenceAuditor,
)
from src.integration.climate_association.m27_7_2.m27_7_2_spatial_field_auditor import (
    SpatialFieldAuditor,
)
from src.integration.climate_association.m27_7_2.m27_7_2_figure_and_text_auditor import (
    FigureAndTextAuditor,
)
from src.integration.climate_association.m27_7_2.m27_7_2_report_generator import (
    generate_all_reports,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CANONICAL_ROOT = Path(r"D:\Project Simulator\monsoon_cloud_research")
M27_7_2_DIR = CANONICAL_ROOT / "reports" / "integration" / "m27_7_2"
TABLES_DIR = M27_7_2_DIR / "tables"
SRC_DIR = CANONICAL_ROOT / "src" / "integration" / "climate_association" / "m27_7_2"
TEST_FILE = CANONICAL_ROOT / "tests" / "integration" / "test_m27_7_2_final_corrections.py"


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class M2772Orchestrator:
    """Master orchestrator for Milestone M27.7.2."""

    def __init__(self, canonical_root: Path = CANONICAL_ROOT):
        self.root = canonical_root
        self.out_dir = self.root / "reports" / "integration" / "m27_7_2"
        self.tables_dir = self.out_dir / "tables"
        self.src_dir = self.root / "src" / "integration" / "climate_association" / "m27_7_2"
        self.test_file = self.root / "tests" / "integration" / "test_m27_7_2_final_corrections.py"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.tables_dir.mkdir(parents=True, exist_ok=True)

    def run_all_corrections(self, fast_mode: bool = False) -> Dict[str, Any]:
        """Execute all M27.7.2 reconciliation and audit modules."""
        t_start = time.time()
        start_time_iso = datetime.now(timezone.utc).isoformat()
        logger.info(f"Starting M27.7.2 Final Reconciliation Pipeline at {start_time_iso}")

        # 1. FDR and Multiplicity Reconciliation
        logger.info("Executing Step 1: FDR Reconciler...")
        fdr_rec = FDRReconciler(canonical_root=self.root)
        if not fast_mode or not (self.tables_dir / "m27_7_2_partial_spearman_p_to_q_reconciliation.csv").exists():
            fdr_rec.run_all()

        # 2. Freedman-Lane Methodology Audit
        logger.info("Executing Step 2: Freedman-Lane Auditor...")
        fl_aud = FreedmanLaneAuditor(canonical_root=self.root)
        fl_aud.run_method_comparison()

        # 3. Year-Block Dependence and Effective Sample Size Audit
        logger.info("Executing Step 3: Year-Block Dependence Auditor...")
        yd_aud = YearDependenceAuditor(canonical_root=self.root)
        yd_aud.run_all()

        # 4. Spatial Field Permutation Auditor
        logger.info("Executing Step 4: Spatial Field Permutation Auditor...")
        sf_aud = SpatialFieldAuditor(canonical_root=self.root)
        sf_aud.verify_spatial_field_permutations()

        # 5. Figure and Text Auditor
        logger.info("Executing Step 5: Figure and Text Auditor...")
        ft_aud = FigureAndTextAuditor(canonical_root=self.root)
        ft_aud.run_all()

        # 6. Scientific Report Generation
        logger.info("Executing Step 6: Generating 10 Scientific Reports...")
        generate_all_reports(canonical_root=self.root)

        duration = time.time() - t_start
        logger.info(f"All M27.7.2 calculations completed in {duration:.2f}s")

        # 7. Compile Manifest
        logger.info("Compiling M27.7.2 manifest...")
        manifest = self.build_manifest(duration_seconds=round(duration, 2), start_iso=start_time_iso)

        # 8. Build ZIP Package
        logger.info("Building M27.7.2 verification ZIP package...")
        zip_path = self.build_zip_package()

        return {
            "status": "COMPLETED",
            "duration_seconds": duration,
            "manifest_path": self.out_dir / "m27_7_2_manifest.json",
            "zip_path": zip_path,
        }

    def build_manifest(self, duration_seconds: float, start_iso: str) -> Dict[str, Any]:
        """Generate comprehensive manifest file."""
        reports: List[Dict[str, Any]] = []
        for p in sorted(self.out_dir.glob("*.md")):
            reports.append({
                "filename": p.name,
                "relative_path": str(p.relative_to(self.root)).replace("\\", "/"),
                "size_bytes": p.stat().st_size,
                "sha256": compute_sha256(p),
            })

        tables: List[Dict[str, Any]] = []
        for p in sorted(self.tables_dir.glob("*.csv")):
            df = pd.read_csv(p)
            tables.append({
                "filename": p.name,
                "relative_path": str(p.relative_to(self.root)).replace("\\", "/"),
                "size_bytes": p.stat().st_size,
                "sha256": compute_sha256(p),
                "row_count": len(df),
                "column_count": len(df.columns),
            })

        code_modules: List[Dict[str, Any]] = []
        for p in sorted(self.src_dir.glob("*.py")):
            code_modules.append({
                "filename": p.name,
                "relative_path": str(p.relative_to(self.root)).replace("\\", "/"),
                "size_bytes": p.stat().st_size,
                "sha256": compute_sha256(p),
            })

        tests: List[Dict[str, Any]] = []
        if self.test_file.exists():
            tests.append({
                "filename": self.test_file.name,
                "relative_path": str(self.test_file.relative_to(self.root)).replace("\\", "/"),
                "size_bytes": self.test_file.stat().st_size,
                "sha256": compute_sha256(self.test_file),
            })

        manifest_data: Dict[str, Any] = {
            "milestone": "M27.7.2",
            "title": "Final Statistical Corrections, Independent Reconciliation and Scientific Acceptance",
            "project": "Satellite-Based Cloud-Regime Discovery over the Indian Monsoon Domain",
            "acceptance_verdict": "ACCEPTED WITH DOCUMENTED LIMITATIONS",
            "execution_timestamp_utc": start_iso,
            "pipeline_duration_seconds": duration_seconds,
            "environment": {
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
                "numpy_version": np.__version__,
                "pandas_version": pd.__version__,
                "scipy_version": scipy.__version__,
            },
            "random_seeds": {
                "freedman_lane_seed": 42,
                "spatial_field_permutation_seed": 42,
                "year_block_permutation_seed": 42,
                "synthetic_benchmark_seed": 2026,
            },
            "deliverables": {
                "reports": reports,
                "tables": tables,
                "code": code_modules,
                "tests": tests,
            },
            "summary_counts": {
                "num_reports": len(reports),
                "num_tables": len(tables),
                "num_code_modules": len(code_modules),
                "num_test_files": len(tests),
                "total_deliverables": len(reports) + len(tables) + len(code_modules) + len(tests),
            },
        }

        manifest_path = self.out_dir / "m27_7_2_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        logger.info(f"Saved manifest to {manifest_path}")
        return manifest_data

    def build_zip_package(self) -> Path:
        """Create M27.7.2-final-statistical-corrections.zip archive."""
        zip_path = self.out_dir / "M27.7.2-final-statistical-corrections.zip"

        files_to_pack: List[Tuple[Path, str]] = []

        # 1. Reports
        for p in sorted(self.out_dir.glob("*.md")):
            arcname = f"reports/{p.name}"
            files_to_pack.append((p, arcname))

        # 2. Tables
        for p in sorted(self.tables_dir.glob("*.csv")):
            arcname = f"tables/{p.name}"
            files_to_pack.append((p, arcname))

        # 3. Source code
        for p in sorted(self.src_dir.glob("*.py")):
            arcname = f"src/{p.name}"
            files_to_pack.append((p, arcname))

        # 4. Tests
        if self.test_file.exists():
            files_to_pack.append((self.test_file, f"tests/{self.test_file.name}"))

        # 5. Manifest
        manifest_p = self.out_dir / "m27_7_2_manifest.json"
        if manifest_p.exists():
            files_to_pack.append((manifest_p, "m27_7_2_manifest.json"))

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for filepath, arcname in files_to_pack:
                zf.write(filepath, arcname)

        with zipfile.ZipFile(zip_path, "r") as zf:
            bad_file = zf.testzip()
            if bad_file is not None:
                raise RuntimeError(f"Corrupted entry in verification package zip: {bad_file}")
            entries = zf.namelist()

        logger.info(f"Successfully generated and validated {zip_path} ({len(entries)} entries, {zip_path.stat().st_size} bytes)")
        return zip_path


def main() -> None:
    orchestrator = M2772Orchestrator()
    res = orchestrator.run_all_corrections(fast_mode=True)
    print("M27.7.2 Orchestrator completed successfully.")
    print(f"Manifest: {res['manifest_path']}")
    print(f"Zip: {res['zip_path']}")


if __name__ == "__main__":
    main()
