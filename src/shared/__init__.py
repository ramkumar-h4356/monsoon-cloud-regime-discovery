"""Shared research infrastructure package.

Provides common tools for dataset extraction, validation, missingness analysis,
feature scaling, registry generation, and experiment orchestration across seasons.
"""

import sys
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parent

# Ensure shared subpackages can locate each other's modules
_SUBDIRS = [
    "inventory",
    "validation",
    "extraction",
    "missingness",
    "feature_engineering",
    "orchestration",
    "reporting",
]

for _sub in _SUBDIRS:
    _p = str(SHARED_DIR / _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)
