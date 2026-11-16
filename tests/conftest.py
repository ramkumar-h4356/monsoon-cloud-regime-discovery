from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

VALIDATION_DIR = ROOT / "src" / "02_validation"
FEATURE_ENGINEERING_DIR = ROOT / "src" / "06_feature_engineering"

sys.path.insert(0, str(VALIDATION_DIR))
sys.path.insert(0, str(FEATURE_ENGINEERING_DIR))
