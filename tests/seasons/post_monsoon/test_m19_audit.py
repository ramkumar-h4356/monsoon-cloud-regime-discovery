import sys
from pathlib import Path
import numpy as np
import pandas as pd
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODULE_DIR = PROJECT_ROOT / "src" / "seasons" / "post_monsoon" / "validation"
sys.path.insert(0, str(MODULE_DIR))
from audit import audit_time, coord_report, finite_unique, reconcile_roni, reconcile_dmi

def test_finite_unique():
    assert finite_unique([1,2,3])
    assert not finite_unique([1,1,3])
    assert not finite_unique([1,np.nan,3])

def test_coordinate_report_detects_duplicates_and_order():
    r=coord_report([1,2,3],"lat",0,4)
    assert r["finite"] and r["unique"] and r["ascending"] and r["within_expected_bounds"]
    r=coord_report([1,1,3],"lat",0,4)
    assert not r["unique"]

def test_ceres_time_accepts_half_hour_centered_hourly_data():
    t=pd.date_range("2010-10-15 00:30",periods=720,freq="h")
    r=audit_time(t,2010)
    assert r["status"]=="PASS"

def test_ceres_time_rejects_missing_record():
    t=pd.date_range("2010-10-15 00:30",periods=720,freq="h").delete(100)
    r=audit_time(t,2010)
    assert r["status"]=="FAIL"



def test_roni_processed_reconciliation_matches_all_rolling_seasons():
    seasons = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    source_rows = [(year, season, float(i) / 10) for year in (2010, 2011) for i, season in enumerate(seasons)]
    source = pd.DataFrame(source_rows, columns=["year", "season", "value"])
    processed = source.rename(columns={"value": "roni_anomaly"}).assign(duplicate=False)
    result = reconcile_roni(source, processed, [2010, 2011])
    assert result["status"] == "PASS"
    assert result["seasonal_structure_preserved"] is True
    assert result["values_match_within_1e-8"] is True


def test_dmi_processed_reconciliation_detects_value_mismatch():
    dates = pd.date_range("2010-01-01", periods=24, freq="MS")
    source = pd.DataFrame({"date": dates, "value": np.arange(24, dtype=float) / 10})
    processed = pd.DataFrame({"date": dates, "dmi_anomaly": np.arange(24, dtype=float) / 10, "duplicate": False})
    good = reconcile_dmi(source, processed, [2010, 2011])
    assert good["status"] == "PASS"
    processed.loc[3, "dmi_anomaly"] += 0.01
    bad = reconcile_dmi(source, processed, [2010, 2011])
    assert bad["status"] == "FAIL"
    assert bad["values_match_within_1e-8"] is False
