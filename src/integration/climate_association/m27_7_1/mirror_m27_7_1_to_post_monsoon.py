"""M27.7.1 — Dual-Repository Mirroring and Byte-for-Byte Parity Enforcer.

Mirrors all M27.7.1 deliverables from canonical monsoon_cloud_research
to post_monsoon_research, and validates exact 100% SHA-256 parity.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import shutil
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CANONICAL_ROOT = Path(r"D:\Project Simulator\monsoon_cloud_research")
SECONDARY_ROOT = Path(r"D:\Project Simulator\post_monsoon_research")


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def mirror_and_verify() -> Tuple[bool, int, List[Tuple[str, str, str]]]:
    """Mirror M27.7.1 files and verify SHA-256 parity."""
    # Target folders and files
    items_to_mirror = [
        ("src/integration/climate_association/m27_7_1", True),
        ("reports/integration/m27_7_1", True),
        ("tests/integration/test_m27_7_1_verification.py", False),
    ]

    for rel_path, is_dir in items_to_mirror:
        src = CANONICAL_ROOT / rel_path
        dst = SECONDARY_ROOT / rel_path
        if is_dir:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            logger.info(f"Mirrored directory {src} -> {dst}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            logger.info(f"Mirrored file {src} -> {dst}")

    # Exhaustive verification of all mirrored files
    all_files: List[Path] = []

    # 1. Source files
    src_dir = CANONICAL_ROOT / "src" / "integration" / "climate_association" / "m27_7_1"
    all_files.extend([p for p in src_dir.glob("*.py")])

    # 2. Report and Table files
    rep_dir = CANONICAL_ROOT / "reports" / "integration" / "m27_7_1"
    all_files.extend([p for p in rep_dir.rglob("*") if p.is_file()])

    # 3. Test file
    test_file = CANONICAL_ROOT / "tests" / "integration" / "test_m27_7_1_verification.py"
    if test_file.exists():
        all_files.append(test_file)

    results: List[Tuple[str, str, str]] = []
    all_matched = True

    for can_path in all_files:
        rel = can_path.relative_to(CANONICAL_ROOT)
        sec_path = SECONDARY_ROOT / rel

        if not sec_path.exists():
            logger.error(f"Missing file in secondary worktree: {rel}")
            all_matched = False
            results.append((str(rel), "MISSING", "MISSING"))
            continue

        can_sha = compute_sha256(can_path)
        sec_sha = compute_sha256(sec_path)
        is_match = (can_sha == sec_sha)
        if not is_match:
            logger.error(f"SHA-256 mismatch on {rel}: {can_sha} vs {sec_sha}")
            all_matched = False
        results.append((str(rel), can_sha, sec_sha))

    logger.info(f"Dual-repo verification complete: {len(results)} files checked. Parity status: {all_matched}")
    return all_matched, len(results), results


def main() -> None:
    success, total_count, _ = mirror_and_verify()
    if not success:
        print("Mirroring parity failed!")
        exit(1)
    print(f"Dual-repository mirroring successful! 100% SHA-256 parity verified across {total_count} files.")


if __name__ == "__main__":
    main()
