from __future__ import annotations
import argparse, csv, json, math, re, sys, traceback
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import xarray as xr

SEASONS = {"start": "10-15", "end": "11-13"}
EXPECTED_VARS = 45
EXPECTED_LAT, EXPECTED_LON, EXPECTED_TIME = 32, 30, 720


def status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"

def finite_unique(values):
    a = np.asarray(values)
    return bool(np.isfinite(a.astype(float)).all() and len(np.unique(a)) == len(a))

def coord_report(values, name, lower=None, upper=None):
    a = np.asarray(values, dtype=float)
    return {"coordinate": name, "count": int(a.size), "finite": bool(np.isfinite(a).all()),
            "unique": bool(np.unique(a).size == a.size), "ascending": bool(a.size < 2 or np.all(np.diff(a) > 0)),
            "minimum": float(np.nanmin(a)) if a.size else None, "maximum": float(np.nanmax(a)) if a.size else None,
            "within_expected_bounds": (bool(np.all((a >= lower) & (a <= upper))) if lower is not None and upper is not None else None)}

def expected_dates(year):
    return pd.date_range(f"{year}-10-15 00:00:00", f"{year}-11-13 23:00:00", freq="h")

def audit_time(values, year, expected_count=720, max_interval_deviation_minutes=10):
    t = pd.DatetimeIndex(pd.to_datetime(values))
    # DatetimeIndex.asi8 uses the index's native resolution (s/ms/us/ns),
    # which is not guaranteed to be nanoseconds across pandas versions.
    # Normalize explicitly before converting integer ticks to minutes.
    ticks_ns = t.to_numpy(dtype="datetime64[ns]").astype("int64")
    diffs = np.diff(ticks_ns) / 1e9 / 60 if len(t) > 1 else np.array([])
    dates_ok = bool(len(t) and (t.year == year).all() and (t.month == 10) .__or__((t.month == 11)).all())
    # Check calendar coverage independently of timestamp phase (CERES samples are near HH:30).
    expected_day_counts = {d: int(np.sum(t.date == d.date())) for d in expected_dates(year).normalize().unique()}
    day_coverage = len(expected_day_counts) == 30 and all(v == 24 for v in expected_day_counts.values())
    interval_ok = bool(len(diffs) and np.all(np.abs(diffs - 60) <= max_interval_deviation_minutes))
    return {"year": year, "count": int(len(t)), "expected_count": expected_count,
            "count_status": status(len(t) == expected_count), "unique": bool(t.is_unique),
            "monotonic_increasing": bool(t.is_monotonic_increasing), "all_year_matches": bool((t.year == year).all()),
            "window_matches": bool(len(t) and t.min().date() == datetime(year,10,15).date() and t.max().date() == datetime(year,11,13).date()),
            "all_30_days_have_24_records": day_coverage,
            "interval_minutes_min": float(np.min(diffs)) if len(diffs) else None,
            "interval_minutes_max": float(np.max(diffs)) if len(diffs) else None,
            "hourly_interval_within_tolerance": interval_ok,
            "status": status(len(t)==expected_count and t.is_unique and t.is_monotonic_increasing and (t.year==year).all() and day_coverage and interval_ok)}

def _var_attrs(var):
    attrs = dict(var.attrs)
    # xarray may move fill/valid metadata into encoding.
    for k in ("_FillValue", "missing_value", "valid_min", "valid_max"):
        if k not in attrs and k in var.encoding: attrs[k] = var.encoding[k]
    return attrs

def audit_ceres(folder: Path, years, cfg):
    rows, time_rows, spatial_rows, variable_rows, errors = [], [], [], [], []
    files = {int(m.group(1)): p for p in folder.glob("*.nc") if (m:=re.search(r"(20\d{2})", p.name))}
    for year in years:
        p = files.get(year)
        if p is None:
            rows.append({"dataset":"CERES","year":year,"file":"","status":"FAIL","reason":"missing annual file"}); continue
        try:
            with xr.open_dataset(p, decode_times=True, mask_and_scale=True) as ds:
                sizes = dict(ds.sizes)
                schema = sorted(ds.data_vars)
                schema_ok = len(schema)==EXPECTED_VARS and sizes.get("time")==EXPECTED_TIME and sizes.get("lat")==EXPECTED_LAT and sizes.get("lon")==EXPECTED_LON
                t = audit_time(ds["time"].values, year, cfg["ceres_expected_time_records"], cfg["hourly_tolerance_minutes"])
                time_rows.append({"dataset":"CERES", "file":p.name, **t})
                lat = coord_report(ds["lat"].values,"lat",cfg["latitude_min"],cfg["latitude_max"])
                lon = coord_report(ds["lon"].values,"lon",cfg["longitude_min"],cfg["longitude_max"])
                for cr in (lat,lon): spatial_rows.append({"dataset":"CERES","year":year,"file":p.name,**cr,"status":status(cr["finite"] and cr["unique"] and cr["ascending"] and cr["within_expected_bounds"])})
                spatial_ok = all(x["status"]=="PASS" for x in spatial_rows if x.get("year")==year)
                for name, var in ds.data_vars.items():
                    a = np.asarray(var.values)
                    finite = np.isfinite(a)
                    attrs = _var_attrs(var)
                    vmin = attrs.get("valid_min", attrs.get("valid_range", [None,None])[0] if isinstance(attrs.get("valid_range"), (list,tuple,np.ndarray)) else None)
                    vmax = attrs.get("valid_max", attrs.get("valid_range", [None,None])[1] if isinstance(attrs.get("valid_range"), (list,tuple,np.ndarray)) else None)
                    try: vmin = float(vmin) if vmin is not None else None
                    except (TypeError,ValueError): vmin=None
                    try: vmax = float(vmax) if vmax is not None else None
                    except (TypeError,ValueError): vmax=None
                    vals = a[finite]
                    below = int(np.sum(vals < vmin)) if vmin is not None else None
                    above = int(np.sum(vals > vmax)) if vmax is not None else None
                    dims_ok = tuple(var.dims)==("time","lat","lon") and tuple(var.shape)==(720,32,30)
                    variable_rows.append({"dataset":"CERES","year":year,"file":p.name,"variable":name,"dimensions":";".join(var.dims),"shape":"x".join(map(str,var.shape)),"dtype":str(var.dtype),"units":attrs.get("units",""),"finite_count":int(finite.sum()),"nan_or_masked_count":int(a.size-finite.sum()),"minimum":float(vals.min()) if vals.size else None,"maximum":float(vals.max()) if vals.size else None,"valid_min_metadata":vmin,"valid_max_metadata":vmax,"below_valid_min_count":below,"above_valid_max_count":above,"dimensions_status":status(dims_ok),"range_status":"NOT EVALUATED" if vmin is None or vmax is None else status((below or 0)==0 and (above or 0)==0)})
                year_variable_rows = [v for v in variable_rows if v.get("year") == year]
                range_failures = sum(v.get("range_status") == "FAIL" for v in year_variable_rows)
                row_ok = schema_ok and t["status"]=="PASS" and spatial_ok and range_failures == 0
                rows.append({"dataset":"CERES","year":year,"file":p.name,"dimensions":json.dumps(sizes),"variable_count":len(schema),"schema_signature":"|".join(schema),"schema_status":status(len(schema)==EXPECTED_VARS),"dimensions_status":status(schema_ok),"time_status":t["status"],"spatial_status":status(spatial_ok),"variable_range_failures":range_failures,"status":status(row_ok)})
        except Exception as e:
            rows.append({"dataset":"CERES","year":year,"file":p.name,"status":"FAIL","reason":repr(e)})
            errors.append({"dataset":"CERES","year":year,"file":p.name,"error":repr(e)})
    return rows,time_rows,spatial_rows,variable_rows,errors

def audit_imd(folder: Path, years, cfg):
    rows, spatial_rows, time_rows, errors = [], [], [], []
    files={int(m.group(1)):p for p in folder.glob("*.nc") if (m:=re.search(r"(20\d{2})",p.name))}
    all_coords={}
    for year in years:
        p=files.get(year)
        if p is None:
            rows.append({"dataset":"IMD","year":year,"status":"FAIL","reason":"missing annual file"}); continue
        try:
            with xr.open_dataset(p,decode_times=True,mask_and_scale=True) as ds:
                time_name=next((x for x in ("TIME","time") if x in ds.coords),None)
                lat_name=next((x for x in ("LATITUDE","lat","latitude") if x in ds.coords),None)
                lon_name=next((x for x in ("LONGITUDE","lon","longitude") if x in ds.coords),None)
                var_name=next((x for x in ("RAINFALL","rainfall") if x in ds.data_vars),None)
                if not all((time_name,lat_name,lon_name,var_name)): raise ValueError("Expected IMD time/latitude/longitude/RAINFALL fields not found")
                t=pd.DatetimeIndex(pd.to_datetime(ds[time_name].values))
                expected_days=366 if pd.Timestamp(year=year,month=12,day=31).day_of_year==366 else 365
                tr={"dataset":"IMD","year":year,"count":len(t),"expected_count":expected_days,"unique":bool(t.is_unique),"monotonic_increasing":bool(t.is_monotonic_increasing),"year_matches":bool((t.year==year).all()),"daily_spacing":bool(len(t)<2 or np.all(np.diff(t.asi8)==24*3600*10**9)),"status":status(len(t)==expected_days and t.is_unique and t.is_monotonic_increasing and (t.year==year).all() and (len(t)<2 or np.all(np.diff(t.asi8)==24*3600*10**9)))}
                time_rows.append(tr)
                lat=coord_report(ds[lat_name].values,"latitude",cfg["latitude_min"],cfg["latitude_max"]); lon=coord_report(ds[lon_name].values,"longitude",cfg["longitude_min"],cfg["longitude_max"])
                for cr in (lat,lon): spatial_rows.append({"dataset":"IMD","year":year,"file":p.name,**cr,"status":status(cr["finite"] and cr["unique"] and cr["ascending"])})
                all_coords[year]=(np.asarray(ds[lat_name].values,dtype=float),np.asarray(ds[lon_name].values,dtype=float))
                a=np.asarray(ds[var_name].values,dtype=float); finite=np.isfinite(a)
                attrs=_var_attrs(ds[var_name]); fill=attrs.get("_FillValue",attrs.get("missing_value"))
                try: fill=float(fill) if fill is not None else None
                except (TypeError,ValueError): fill=None
                # Preserve encoded sentinel detection where mask_and_scale has not masked it.
                sentinel_count=int(np.sum(a==fill)) if fill is not None else 0
                vals=a[finite & ((a!=fill) if fill is not None else np.ones(a.shape,dtype=bool))]
                spatial_ok = all(x["status"] == "PASS" for x in spatial_rows if x.get("dataset") == "IMD" and x.get("year") == year)
                rows.append({"dataset":"IMD","year":year,"file":p.name,"time_records":len(t),"latitude_count":len(ds[lat_name]),"longitude_count":len(ds[lon_name]),"rainfall_shape":"x".join(map(str,a.shape)),"rainfall_units":attrs.get("units",""),"finite_count":int(finite.sum()),"nonfinite_count":int((~finite).sum()),"fill_sentinel_metadata":fill,"sentinel_count":sentinel_count,"valid_min":float(vals.min()) if vals.size else None,"valid_max":float(vals.max()) if vals.size else None,"negative_rainfall_count":int(np.sum(vals<0)),"time_status":tr["status"],"spatial_status":status(spatial_ok),"status":status(tr["status"]=="PASS" and spatial_ok and np.sum(vals<0)==0)})
        except Exception as e:
            rows.append({"dataset":"IMD","year":year,"file":p.name,"status":"FAIL","reason":repr(e)}); errors.append({"dataset":"IMD","year":year,"file":p.name,"error":repr(e)})
    # Coordinate intersections are exact-value intersections; no index-based matching or regridding.
    if all_coords:
        first=next(iter(all_coords.values()))
        for year,(la,lo) in all_coords.items():
            spatial_rows.append({"dataset":"IMD","year":year,"coordinate":"grid_consistency_vs_first_year","latitude_exact_match":bool(np.array_equal(la,first[0])),"longitude_exact_match":bool(np.array_equal(lo,first[1])),"status":status(np.array_equal(la,first[0]) and np.array_equal(lo,first[1]))})
    return rows,time_rows,spatial_rows,errors

def _duplicate_flag_count(frame):
    if "duplicate" not in frame.columns:
        return 0
    flags = frame["duplicate"].astype(str).str.strip().str.lower()
    return int(flags.isin({"true", "1", "yes", "y"}).sum())


def _compare_numeric_series(left, right, tolerance=1e-8):
    left = pd.to_numeric(left, errors="coerce").reset_index(drop=True)
    right = pd.to_numeric(right, errors="coerce").reset_index(drop=True)
    if len(left) != len(right):
        return False, False, None
    missing_match = bool(left.isna().equals(right.isna()))
    valid = left.notna() & right.notna()
    if not missing_match:
        return False, False, None
    if not valid.any():
        return True, True, 0.0
    delta = np.abs(left[valid].to_numpy(dtype=float) - right[valid].to_numpy(dtype=float))
    max_abs = float(delta.max()) if delta.size else 0.0
    return bool(np.all(delta <= tolerance)), True, max_abs


def reconcile_roni(original, processed, years):
    """Compare NOAA RONI seasonal source records to the processed 2010-2021 CSV.

    Keys are (year, three-month season code). The rolling seasonal labels are
    preserved; they are never expanded into monthly observations.
    """
    source = original.copy()
    source.columns = ["year", "season", "value"]
    source["year"] = pd.to_numeric(source["year"], errors="coerce")
    source["season"] = source["season"].astype(str).str.strip().str.upper()
    source["value"] = pd.to_numeric(source["value"], errors="coerce")
    source = source[source["year"].isin(years)].copy()
    source["year"] = source["year"].astype(int)
    sentinel_count = int((source["value"] == -9999).sum())
    source.loc[source["value"] == -9999, "value"] = np.nan

    proc = processed.copy()
    proc.columns = [str(c).strip().lower() for c in proc.columns]
    required = {"season", "year", "roni_anomaly"}
    if not required.issubset(proc.columns):
        raise ValueError(f"RONI processed CSV requires columns {sorted(required)}; found {list(proc.columns)}")
    proc = proc[["season", "year", "roni_anomaly"] + (["duplicate"] if "duplicate" in proc.columns else [])].copy()
    proc["year"] = pd.to_numeric(proc["year"], errors="coerce")
    proc["season"] = proc["season"].astype(str).str.strip().str.upper()
    proc["roni_anomaly"] = pd.to_numeric(proc["roni_anomaly"], errors="coerce")
    proc = proc[proc["year"].isin(years)].copy()
    proc["year"] = proc["year"].astype(int)
    proc_duplicates = int(proc.duplicated(["year", "season"]).sum())
    source_duplicates = int(source.duplicated(["year", "season"]).sum())
    duplicate_flags = _duplicate_flag_count(proc)

    seasons = {"DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"}
    expected_keys = {(int(y), season) for y in years for season in seasons}
    source_keys = set(zip(source["year"], source["season"]))
    proc_keys = set(zip(proc["year"], proc["season"]))
    source_structure = len(source) == len(expected_keys) and source_keys == expected_keys
    processed_structure = len(proc) == len(expected_keys) and proc_keys == expected_keys

    merged = source.merge(proc, on=["year", "season"], how="outer", indicator=True, validate="one_to_one")
    keys_match = bool((merged["_merge"] == "both").all()) and len(merged) == len(expected_keys)
    values_match, missingness_match, max_abs = _compare_numeric_series(
        merged.loc[merged["_merge"] == "both", "value"],
        merged.loc[merged["_merge"] == "both", "roni_anomaly"],
    )
    missing_source = int(source["value"].isna().sum())
    missing_processed = int(proc["roni_anomaly"].isna().sum())
    ok = (source_structure and processed_structure and keys_match and
          source_duplicates == 0 and proc_duplicates == 0 and duplicate_flags == 0 and
          sentinel_count == 0 and missing_source == 0 and missing_processed == 0 and
          values_match and missingness_match)
    return {
        "dataset": "RONI processed reconciliation",
        "records_in_period": len(source),
        "processed_records": len(proc),
        "expected_records": len(expected_keys),
        "source_duplicate_keys": source_duplicates,
        "processed_duplicate_keys": proc_duplicates,
        "processed_duplicate_flags": duplicate_flags,
        "missing_source_anomaly": missing_source,
        "missing_processed_anomaly": missing_processed,
        "sentinel_minus_9999": sentinel_count,
        "seasonal_structure_preserved": bool(source_structure and processed_structure),
        "keys_match": keys_match,
        "missingness_match": missingness_match,
        "values_match_within_1e-8": values_match,
        "max_absolute_difference": max_abs,
        "status": status(ok),
    }


def reconcile_dmi(original, processed, years):
    """Compare NOAA monthly DMI source values to the processed monthly CSV."""
    source = original[["date", "value"]].copy() if {"date", "value"}.issubset(original.columns) else original.copy()
    source.columns = ["date", "value"]
    source["date"] = pd.to_datetime(source["date"], errors="coerce")
    source["value"] = pd.to_numeric(source["value"], errors="coerce")
    unparseable = int(source["date"].isna().sum())
    source = source[source["date"].notna() & source["date"].dt.year.isin(years)].copy()
    source["month"] = source["date"].dt.to_period("M")
    sentinel_count = int((source["value"] == -9999).sum())
    source.loc[source["value"] == -9999, "value"] = np.nan

    proc = processed.copy()
    proc.columns = [str(c).strip().lower() for c in proc.columns]
    required = {"date", "dmi_anomaly"}
    if not required.issubset(proc.columns):
        raise ValueError(f"DMI processed CSV requires columns {sorted(required)}; found {list(proc.columns)}")
    proc = proc[["date", "dmi_anomaly"] + (["duplicate"] if "duplicate" in proc.columns else [])].copy()
    proc["date"] = pd.to_datetime(proc["date"], errors="coerce")
    proc["dmi_anomaly"] = pd.to_numeric(proc["dmi_anomaly"], errors="coerce")
    proc = proc[proc["date"].notna() & proc["date"].dt.year.isin(years)].copy()
    proc["month"] = proc["date"].dt.to_period("M")
    proc_duplicates = int(proc["month"].duplicated().sum())
    source_duplicates = int(source["month"].duplicated().sum())
    duplicate_flags = _duplicate_flag_count(proc)
    expected_months = pd.period_range(f"{min(years)}-01", f"{max(years)}-12", freq="M")
    expected_keys = set(expected_months)
    source_keys = set(source["month"])
    proc_keys = set(proc["month"])
    source_coverage = source_keys == expected_keys and len(source) == len(expected_keys)
    processed_coverage = proc_keys == expected_keys and len(proc) == len(expected_keys)

    merged = source.merge(proc, on="month", how="outer", indicator=True, validate="one_to_one")
    keys_match = bool((merged["_merge"] == "both").all()) and len(merged) == len(expected_keys)
    matched = merged[merged["_merge"] == "both"]
    values_match, missingness_match, max_abs = _compare_numeric_series(matched["value"], matched["dmi_anomaly"])
    missing_source = int(source["value"].isna().sum())
    missing_processed = int(proc["dmi_anomaly"].isna().sum())
    ok = (unparseable == 0 and source_coverage and processed_coverage and keys_match and
          source_duplicates == 0 and proc_duplicates == 0 and duplicate_flags == 0 and
          sentinel_count == 0 and missing_source == 0 and missing_processed == 0 and
          values_match and missingness_match)
    return {
        "dataset": "DMI processed reconciliation",
        "records_in_period": len(source),
        "processed_records": len(proc),
        "expected_records": len(expected_keys),
        "source_duplicate_months": source_duplicates,
        "processed_duplicate_months": proc_duplicates,
        "processed_duplicate_flags": duplicate_flags,
        "unparseable_source_dates": unparseable,
        "missing_source_anomaly": missing_source,
        "missing_processed_anomaly": missing_processed,
        "sentinel_minus_9999": sentinel_count,
        "source_monthly_coverage": len(source_keys),
        "processed_monthly_coverage": len(proc_keys),
        "keys_match": keys_match,
        "missingness_match": missingness_match,
        "values_match_within_1e-8": values_match,
        "max_absolute_difference": max_abs,
        "status": status(ok),
    }


def read_climate_sources(cfg):
    rows=[]; errors=[]
    years=list(cfg["years"])
    roni=Path(cfg["roni_original"]); dmi=Path(cfg["dmi_original"])
    if roni.exists():
        try:
            df=pd.read_csv(roni,sep=r"\s+",comment="#",engine="python")
            cols={str(c).strip().lower():c for c in df.columns}
            y=next((cols[k] for k in cols if k in ("yr","year")),None)
            seas=next((cols[k] for k in cols if k in ("seas","season")),None)
            val=next((cols[k] for k in cols if "anom" in k),None)
            if not all((y,seas,val)): raise ValueError(f"RONI columns not recognized: {list(df.columns)}")
            original=df[[y,seas,val]].copy()
            original.columns=["year","season","value"]
            original["year"]=pd.to_numeric(original["year"],errors="coerce")
            original["season"]=original["season"].astype(str).str.strip().str.upper()
            original["value"]=pd.to_numeric(original["value"],errors="coerce")
            x=original[original.year.isin(years)].copy()
            x["year"]=x["year"].astype(int)
            source_dup=int(x.duplicated(["year","season"]).sum())
            sentinel=int((x.value==-9999).sum())
            x.loc[x.value==-9999,"value"]=np.nan
            season_codes={"DJF","JFM","FMA","MAM","AMJ","MJJ","JJA","JAS","ASO","SON","OND","NDJ"}
            expected={(int(yr),ss) for yr in years for ss in season_codes}
            keys=set(zip(x.year,x.season))
            missing=int(x.value.isna().sum())
            source_ok=(len(x)==len(expected) and keys==expected and source_dup==0 and sentinel==0 and missing==0)
            rows.append({"dataset":"RONI original","records_in_period":len(x),"expected_records":len(expected),"duplicate_keys":source_dup,"missing_anomaly":missing,"sentinel_minus_9999":sentinel,"seasonal_structure_preserved":bool(keys==expected),"status":status(source_ok)})
            processed=Path(cfg["roni_processed"])
            if processed.exists():
                xp=pd.read_csv(processed)
                rows.append(reconcile_roni(x, xp, years))
            else:
                rows.append({"dataset":"RONI processed reconciliation","status":"NOT EVALUATED","reason":"configured processed CSV not found"})
        except Exception as e:
            errors.append({"dataset":"RONI","error":repr(e)})
            rows.append({"dataset":"RONI original","status":"FAIL","reason":repr(e)})
    else:
        rows.append({"dataset":"RONI original","status":"NOT EVALUATED","reason":"configured source file not found"})

    if dmi.exists():
        try:
            raw=pd.read_csv(dmi)
            date_col=next((c for c in raw.columns if "date" in c.lower() or "time" in c.lower()),None)
            val_col=next((c for c in raw.columns if "dmi" in c.lower() or "anom" in c.lower()),None)
            if date_col is None or val_col is None: raise ValueError(f"DMI columns not recognized: {list(raw.columns)}")
            original=raw[[date_col,val_col]].copy(); original.columns=["date","value"]
            original["date"]=pd.to_datetime(original["date"],errors="coerce")
            original["value"]=pd.to_numeric(original["value"],errors="coerce")
            unparseable=int(original.date.isna().sum())
            x=original[original.date.notna() & original.date.dt.year.isin(years)].copy()
            x["month"]=x.date.dt.to_period("M")
            dup=int(x.month.duplicated().sum()); sentinel=int((x.value==-9999).sum())
            x.loc[x.value==-9999,"value"]=np.nan
            expected=pd.period_range(f"{min(years)}-01",f"{max(years)}-12",freq="M")
            missing=int(x.value.isna().sum())
            source_ok=(unparseable==0 and len(x)==len(expected) and set(x.month)==set(expected) and dup==0 and sentinel==0 and missing==0)
            rows.append({"dataset":"DMI original","records_in_period":len(x),"duplicate_months":dup,"unparseable_dates":unparseable,"missing_after_sentinel_conversion":missing,"sentinel_minus_9999":sentinel,"monthly_coverage_expected":len(expected),"monthly_coverage_observed":int(x.month.nunique()),"status":status(source_ok)})
            processed=Path(cfg["dmi_processed"])
            if processed.exists():
                xp=pd.read_csv(processed)
                rows.append(reconcile_dmi(x, xp, years))
            else:
                rows.append({"dataset":"DMI processed reconciliation","status":"NOT EVALUATED","reason":"configured processed CSV not found"})
        except Exception as e:
            errors.append({"dataset":"DMI","error":repr(e)})
            rows.append({"dataset":"DMI original","status":"FAIL","reason":repr(e)})
    else:
        rows.append({"dataset":"DMI original","status":"NOT EVALUATED","reason":"configured source file not found"})
    return rows,errors

def write_csv(path, rows):
    if not rows: path.write_text("status\nNOT EVALUATED\n",encoding="utf-8"); return
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)

def run(config_path: Path):
    cfg=json.loads(config_path.read_text(encoding="utf-8")); base=Path(cfg["project_root"]); out=Path(cfg["output_dir"]); out.mkdir(parents=True,exist_ok=True)
    def resolve(v):
        p=Path(v); return p if p.is_absolute() else base/p
    years=cfg["years"]
    ceres=resolve(cfg["ceres_dir"]); imd=resolve(cfg["imd_dir"])
    c_rows,c_time,c_space,c_vars,c_err=audit_ceres(ceres,years,cfg)
    i_rows,i_time,i_space,i_err=audit_imd(imd,years,cfg)
    climate,climate_err=read_climate_sources({**cfg,"roni_original":str(resolve(cfg["roni_original"])),"roni_processed":str(resolve(cfg["roni_processed"])),"dmi_original":str(resolve(cfg["dmi_original"])),"dmi_processed":str(resolve(cfg["dmi_processed"]))})
    tables={"M19_file_validation.csv":c_rows+i_rows,"M19_timestamp_validation.csv":c_time+i_time,"M19_spatial_validation.csv":c_space+i_space,"M19_variable_validation.csv":c_vars,"M19_supporting_data_validation.csv":climate}
    for name,rows in tables.items(): write_csv(out/name,rows)
    errors=c_err+i_err+climate_err
    (out/"M19_errors.json").write_text(json.dumps(errors,indent=2,default=str),encoding="utf-8")
    all_rows=sum(tables.values(),[]); evaluated=[r for r in all_rows if r.get("status") in ("PASS","FAIL")]; failed=sum(r.get("status")=="FAIL" for r in evaluated)
    # Readiness is deliberately strict: missing/unevaluated required source families block readiness.
    families={"CERES":bool(c_rows) and all(r.get("status")=="PASS" for r in c_rows),"IMD":bool(i_rows) and all(r.get("status")=="PASS" for r in i_rows),"Climate indices":bool(climate) and all(r.get("status") == "PASS" for r in climate) and any(r.get("dataset")=="RONI original" and r.get("status")=="PASS" for r in climate) and any(r.get("dataset")=="DMI original" and r.get("status")=="PASS" for r in climate)}
    summary={"project":"M19 post-monsoon data integrity audit","years":years,"season_window":"October 15-November 13","generated_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),"input_paths":{"ceres":str(ceres),"imd":str(imd)},"counts":{"checks_evaluated":len(evaluated),"pass":sum(r.get("status")=="PASS" for r in evaluated),"fail":failed,"not_evaluated":sum(r.get("status")=="NOT EVALUATED" for r in all_rows)},"source_family_readiness":families,"overall_readiness":"READY FOR DOWNSTREAM ANALYSIS" if all(families.values()) and failed==0 else "NOT READY - REVIEW FAILURES / UNEVALUATED CHECKS","raw_data_modified":False}
    (out/"M19_integrity_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    report=["# M19 Post-monsoon Data Integrity Report","",f"**Overall status:** {summary['overall_readiness']}",f"**Study years:** {years[0]}–{years[-1]}","**Window:** October 15–November 13 (720 hourly CERES records per year expected)","","## Source-family readiness"]+[f"- {k}: {v}" for k,v in families.items()]+["","## Check totals",f"- PASS: {summary['counts']['pass']}",f"- FAIL: {summary['counts']['fail']}",f"- NOT EVALUATED: {summary['counts']['not_evaluated']}","","## Interpretation and limitations","- CERES timestamp checks allow small timestamp-centering jitter; hourly spacing is tested with a configurable tolerance, not exact HH:00 matching.","- CERES metadata valid_min/valid_max checks are reported per variable. A range failure is evidence for review, not automatic data correction.","- IMD coordinates are audited separately. CERES and IMD grids must be joined by coordinate values/intersection, never by array index.","- RONI rolling three-month season labels are preserved; they are not converted into independent monthly observations.","- DMI -9999 values are counted as missing sentinels. No missing climate values are imputed.","- Processed climate CSVs are listed for reconciliation; automatic equality is not claimed unless the source schema mapping is explicitly validated.","- This audit does not regrid, interpolate, overwrite, or modify raw datasets.","","## Generated tables"]+[f"- {n}" for n in tables]+["- M19_errors.json","- M19_integrity_summary.json"]
    (out/"M19_final_readiness_report.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2)); return summary

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--config",default="config/m19_post_monsoon_audit.json"); args=ap.parse_args()
    try: result=run(Path(args.config)); sys.exit(0 if result["overall_readiness"].startswith("READY") else 2)
    except Exception:
        traceback.print_exc(); sys.exit(1)
