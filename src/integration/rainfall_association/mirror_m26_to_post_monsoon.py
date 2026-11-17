"""
mirror_m26_to_post_monsoon.py

Mirrors all Milestone M26 code, data, reports, and tests from monsoon_cloud_research
to post_monsoon_research, verifying byte-for-byte and SHA256 consistency.
Handles NTFS directory junctions cleanly without copying files onto themselves.
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
        # Files are physically identical via directory junction/symlink
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
    
    assert src_file.exists(), f"Source file does not exist: {src_file}"
    safe_copy_file(src_file, dst_file)
    print(f"Successfully mirrored file {rel_file}")


def main():
    print(f"Mirroring from {SRC_ROOT} to {DST_ROOT}...")
    
    # 1. Processed Data
    mirror_directory("data/processed/rainfall_validation")
    
    # 2. Reports
    mirror_directory("reports/integration/m26")
    
    # 3. Code
    mirror_directory("src/integration/rainfall_association")
    
    # 4. Tests
    mirror_file("tests/integration/test_m26_rainfall_validation.py")
    
    print("All M26 files mirrored and cryptographically verified byte-for-byte!")


if __name__ == "__main__":
    main()
