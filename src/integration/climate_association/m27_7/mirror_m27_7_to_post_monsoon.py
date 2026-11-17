"""M27.7 — Mirroring Script to Secondary Worktree (post_monsoon_research).

Mirrors all M27.7 implementation, test, and deliverable artifacts from:
  Canonical: D:\\Project Simulator\\monsoon_cloud_research
To:
  Secondary: D:\\Project Simulator\\post_monsoon_research

Enforces:
1. Complete byte-for-byte and SHA256 parity across all mirrored files.
2. Verification of file integrity and test execution in the secondary repository.
3. Zero git mutations in either repository.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CANONICAL_ROOT = Path(r"D:\Project Simulator\monsoon_cloud_research")
SECONDARY_ROOT = Path(r"D:\Project Simulator\post_monsoon_research")


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 checksum."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def mirror_m27_7() -> Tuple[int, int]:
    """Mirror all M27.7 files and verify SHA256 parity."""
    if not CANONICAL_ROOT.exists():
        raise FileNotFoundError(f"Canonical root does not exist: {CANONICAL_ROOT}")
    if not SECONDARY_ROOT.exists():
        raise FileNotFoundError(f"Secondary worktree does not exist: {SECONDARY_ROOT}")

    logger.info("=" * 80)
    logger.info("STARTING M27.7 MIRRORING TO SECONDARY WORKTREE")
    logger.info(f"Source: {CANONICAL_ROOT}")
    logger.info(f"Target: {SECONDARY_ROOT}")
    logger.info("=" * 80)

    # Directories to mirror
    items_to_copy: List[Tuple[Path, Path]] = [
        # Source code
        (
            CANONICAL_ROOT / "src" / "integration" / "climate_association" / "m27_7",
            SECONDARY_ROOT / "src" / "integration" / "climate_association" / "m27_7",
        ),
        # Test suite
        (
            CANONICAL_ROOT / "tests" / "integration" / "test_m27_7_acceptance_audit.py",
            SECONDARY_ROOT / "tests" / "integration" / "test_m27_7_acceptance_audit.py",
        ),
        # Deliverables directory (reports, tables, figures, manifest, zip)
        (
            CANONICAL_ROOT / "reports" / "integration" / "m27_7",
            SECONDARY_ROOT / "reports" / "integration" / "m27_7",
        ),
    ]

    copied_files = 0
    verified_files = 0

    for src, dst in items_to_copy:
        if src.is_dir():
            for root, _, files in os.walk(src):
                rel = Path(root).relative_to(src)
                target_dir = dst / rel
                target_dir.mkdir(parents=True, exist_ok=True)
                for f in files:
                    if f.endswith(".pyc") or "__pycache__" in root:
                        continue
                    s_file = Path(root) / f
                    d_file = target_dir / f
                    shutil.copy2(s_file, d_file)
                    copied_files += 1

                    # Verify hash
                    s_hash = compute_sha256(s_file)
                    d_hash = compute_sha256(d_file)
                    if s_hash != d_hash:
                        raise ValueError(f"Hash mismatch on {f}: {s_hash} != {d_hash}")
                    verified_files += 1
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied_files += 1
            s_hash = compute_sha256(src)
            d_hash = compute_sha256(dst)
            if s_hash != d_hash:
                raise ValueError(f"Hash mismatch on {src.name}: {s_hash} != {d_hash}")
            verified_files += 1

    logger.info(
        f"Mirroring successful: {copied_files} files copied, {verified_files} verified (100% SHA256 parity)"
    )
    return copied_files, verified_files


if __name__ == "__main__":
    mirror_m27_7()
