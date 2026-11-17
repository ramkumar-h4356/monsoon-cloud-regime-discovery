"""
build_m26_manifest_and_zip.py

Constructs the cryptographic manifest (m26_manifest.json) and packages the
standalone handoff ZIP bundle (M26-rainfall-validation.zip) for Milestone M26.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import zipfile

REPO_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
M26_REPORT_DIR = REPO_ROOT / "reports" / "integration" / "m26"
M26_TABLES_DIR = M26_REPORT_DIR / "tables"
M26_FIGURES_DIR = M26_REPORT_DIR / "figures"
M26_PLANNING_DIR = M26_REPORT_DIR / "planning"
PROCESSED_DATA_DIR = REPO_ROOT / "data" / "processed" / "rainfall_validation"


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_manifest() -> dict:
    manifest = {
        "milestone": "M26",
        "title": "Physical Rainfall Validation of CERES-Derived Cloud Regimes using IMD 1.0-deg Gridded Daily Rainfall (2010-2021)",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "final_decision": "READY_TO_FREEZE_WITH_DOCUMENTED_LIMITATIONS",
        "core_results_summary": {
            "pooled_observations_tier1": 342432,
            "monsoon_observations_tier1": 114144,
            "tier1_terrestrial_cells": 328,
            "tier2_coastal_cells": 29,
            "tier4_ocean_cells_nan": 603,
            "r2_deep_convection_mean_mm_pooled": 11.988,
            "r1_shallow_cumulus_mean_mm_pooled": 0.461,
            "contrast_ratio_pooled": 26.0,
            "r2_deep_convection_mean_mm_monsoon": 16.675,
            "r1_shallow_cumulus_mean_mm_monsoon": 1.296,
            "contrast_ratio_monsoon": 12.87,
            "strict_majority_contrast_ratio": 38.39,
            "r3_volumetric_rainfall_share_monsoon_discrete_pct": 87.59,
            "r3_volumetric_rainfall_share_monsoon_continuous_pct": 79.39,
            "regression_beta_r2_monsoon": 19.586,
            "regression_beta_r1_monsoon": -23.314,
            "bootstrap_ci95_monsoon_contrast_r2_minus_r1": [13.406, 17.585],
            "bootstrap_se_monsoon_contrast_mm": 1.068,
            "bootstrap_p_value_empirical_resolution": "< 0.001"
        },
        "deliverables": {}
    }

    # Track reports
    reports = [
        "m26_rainfall_validation_synthesis_report.md",
        "m26_scientific_acceptance_report.md",
        "m26_1_scientific_results_audit_and_acceptance_review.md",
        "m26_execution_timings.json"
    ]
    manifest["deliverables"]["reports"] = []
    for r in reports:
        p = M26_REPORT_DIR / r
        if p.exists():
            manifest["deliverables"]["reports"].append({
                "file_name": r,
                "relative_path": f"reports/integration/m26/{r}",
                "size_bytes": p.stat().st_size,
                "sha256": compute_sha256(p)
            })

    # Track tables
    manifest["deliverables"]["tables"] = []
    for p in sorted(M26_TABLES_DIR.glob("*.csv")):
        manifest["deliverables"]["tables"].append({
            "file_name": p.name,
            "relative_path": f"reports/integration/m26/tables/{p.name}",
            "size_bytes": p.stat().st_size,
            "sha256": compute_sha256(p)
        })

    # Track figures
    manifest["deliverables"]["figures"] = []
    for p in sorted(M26_FIGURES_DIR.glob("*.png")):
        manifest["deliverables"]["figures"].append({
            "file_name": p.name,
            "relative_path": f"reports/integration/m26/figures/{p.name}",
            "size_bytes": p.stat().st_size,
            "sha256": compute_sha256(p)
        })

    # Track processed parquet datasets
    manifest["deliverables"]["datasets"] = []
    for p in sorted(PROCESSED_DATA_DIR.glob("*.parquet")):
        manifest["deliverables"]["datasets"].append({
            "file_name": p.name,
            "relative_path": f"data/processed/rainfall_validation/{p.name}",
            "size_bytes": p.stat().st_size,
            "sha256": compute_sha256(p)
        })

    return manifest


def create_handoff_zip(manifest: dict) -> Path:
    zip_path = M26_REPORT_DIR / "M26-rainfall-validation.zip"
    
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # 1. Manifest
        manifest_json_str = json.dumps(manifest, indent=2)
        zf.writestr("reports/integration/m26/m26_manifest.json", manifest_json_str)
        
        # 2. Reports
        for r in [
            "m26_rainfall_validation_synthesis_report.md",
            "m26_scientific_acceptance_report.md",
            "m26_1_scientific_results_audit_and_acceptance_review.md",
            "m26_execution_timings.json"
        ]:
            p = M26_REPORT_DIR / r
            if p.exists():
                zf.write(p, arcname=f"reports/integration/m26/{r}")
                
        # 3. Planning documents
        if M26_PLANNING_DIR.exists():
            for p in sorted(M26_PLANNING_DIR.glob("*.*")):
                zf.write(p, arcname=f"reports/integration/m26/planning/{p.name}")
                
        # 4. Tables
        for p in sorted(M26_TABLES_DIR.glob("*.csv")):
            zf.write(p, arcname=f"reports/integration/m26/tables/{p.name}")
            
        # 5. Figures
        for p in sorted(M26_FIGURES_DIR.glob("*.png")):
            zf.write(p, arcname=f"reports/integration/m26/figures/{p.name}")
            
    print(f"Handoff ZIP archive created: {zip_path} ({zip_path.stat().st_size:,} bytes)")
    return zip_path


def main():
    print("Generating M26 manifest...")
    manifest = generate_manifest()
    
    manifest_path = M26_REPORT_DIR / "m26_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to: {manifest_path}")
    
    print("Creating handoff ZIP bundle...")
    create_handoff_zip(manifest)
    print("M26 packaging complete.")


if __name__ == "__main__":
    main()
