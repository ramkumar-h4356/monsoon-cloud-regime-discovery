"""
mirror_m27_to_post_monsoon.py

Mirrors all Milestone M27 code, data, reports, tables, figures, and tests
from monsoon_cloud_research to post_monsoon_research.
Verifies byte-for-byte and SHA256 consistency.
Handles NTFS directory junctions cleanly.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

SRC_ROOT = Path("D:/Project Simulator/monsoon_cloud_research")
DST_ROOT = Path("D:/Project Simulator/post_monsoon_research")


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def safe_copy_file(src_file: Path, dst_file: Path):
    if src_file.resolve() == dst_file.resolve():
        # Physically identical via directory junction/symlink
        assert src_file.stat().st_size > 0, f"File is empty: {src_file}"
        return

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    with open(src_file, "rb") as f_in, open(dst_file, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

    src_hash = compute_sha256(src_file)
    dst_hash = compute_sha256(dst_file)
    assert src_hash == dst_hash, f"Hash mismatch on {src_file.name}: {src_hash} != {dst_hash}"
    assert src_file.stat().st_size == dst_file.stat().st_size, f"Size mismatch on {src_file.name}"


def mirror_directory(rel_dir: str):
    src_dir = SRC_ROOT / rel_dir
    dst_dir = DST_ROOT / rel_dir

    if not src_dir.exists():
        print(f"Source dir does not exist: {src_dir}")
        return

    dst_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    junction_shared = 0
    for src_file in src_dir.glob("**/*"):
        if src_file.is_file():
            rel_file = src_file.relative_to(src_dir)
            dst_file = dst_dir / rel_file
            if src_file.resolve() == dst_file.resolve():
                junction_shared += 1
            else:
                safe_copy_file(src_file, dst_file)
                copied += 1

    print(f"Successfully mirrored {rel_dir} ({copied} copied, {junction_shared} shared via junction)")


def mirror_file(rel_file: str):
    src_file = SRC_ROOT / rel_file
    dst_file = DST_ROOT / rel_file

    if not src_file.exists():
        print(f"Source file does not exist: {src_file}")
        return
    safe_copy_file(src_file, dst_file)
    print(f"Successfully mirrored file {rel_file}")


def mirror_all_m27():
    print(f"Mirroring M27 artifacts from {SRC_ROOT} to {DST_ROOT}...")

    # 1. Source files in climate_association
    mirror_directory("src/integration/climate_association")

    # 2. Processed climate data (shared via junction or copied)
    mirror_directory("data/processed/climate_indices")

    # 3. Reports, tables, and figures
    mirror_directory("reports/integration/m27")

    # 4. Tests
    mirror_file("tests/integration/test_m27_climate_modulation.py")
    mirror_file("tests/integration/test_m27_1_climate_index_readiness.py")

    print("M27 Mirroring completed successfully with SHA256 verification!")


if __name__ == "__main__":
    mirror_all_m27()
