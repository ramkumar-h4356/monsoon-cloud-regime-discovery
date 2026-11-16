"""Stateless CERES preparation. No estimators or data-dependent fitted transforms."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def registry(contract):
    return {f"{family}_{layer}_1h": spec
            for family, spec in contract["families"].items()
            for layer in contract["layers"]}


def split_map(config):
    result = {}
    for split in ("train", "development", "holdout"):
        years = config[f"{split}_years"]
        if not years:
            raise ValueError("Each split must contain whole years")
        for year in years:
            if year in result:
                raise ValueError(f"Overlapping split year: {year}")
            result[year] = split
    if not (max(config["train_years"]) < min(config["development_years"])
            and max(config["development_years"]) < min(config["holdout_years"])):
        raise ValueError("Splits must be chronologically separated")
    return result


def validate_schema(ds, year, contract, config):
    expected = registry(contract)
    if set(ds.data_vars) != set(expected):
        raise ValueError("Dataset does not match the explicit 45-variable contract")
    if tuple(ds.sizes[d] for d in ("time", "lat", "lon")) != tuple(config["expected_shape"]):
        raise ValueError("Unexpected dataset shape")
    for name, spec in expected.items():
        da = ds[name]
        if set(da.dims) != {"time", "lat", "lon"} or da.ndim != 3:
            raise ValueError(f"Incorrect dimensions: {name}")
        if da.attrs.get("units") != spec["units"]:
            raise ValueError(f"Incorrect units: {name}")
        if da.dtype != np.dtype("float32"):
            raise ValueError(f"Incorrect dtype: {name}")
    for coord, key in (("lat", "latitude"), ("lon", "longitude")):
        values = ds[coord].values
        if not np.isfinite(values).all() or not np.all(np.diff(values) > 0):
            raise ValueError(f"Invalid coordinate: {coord}")
        if not np.allclose(values[[0, -1]], config[f"expected_{key}_endpoints"]):
            raise ValueError(f"Unexpected coordinate domain: {coord}")
    times = pd.DatetimeIndex(ds.time.values)
    sm, sd, em, ed = contract["season_windows"][config["season"]]
    start = pd.Timestamp(year, sm, sd)
    stop = pd.Timestamp(year, em, ed) + pd.Timedelta(days=1)
    slots = times.floor("h")
    expected_slots = pd.date_range(start, stop, freq="h", inclusive="left")
    if (times.hasnans or not times.is_monotonic_increasing or slots.has_duplicates
            or not slots.equals(expected_slots)):
        raise ValueError("Incomplete, duplicate or out-of-season hourly slots")


def clean_variable(da, spec):
    """Separate missing retrievals from finite but invalid physical values."""
    values = np.asarray(da.transpose("time", "lat", "lon").values, dtype=np.float32)
    missing = np.isnan(values) | (values == -999.0)
    for key in ("_FillValue", "missing_value"):
        for source in (da.attrs, da.encoding):
            if key in source:
                for sentinel in np.asarray(source[key]).ravel():
                    missing |= values == float(sentinel)
    lower, upper = spec["range"]
    invalid = ~missing & (~np.isfinite(values) | (values < lower) | (values > upper))
    clean = np.where(missing | invalid, np.nan, values)
    return clean, missing, invalid


def prepare(ds, contract):
    specs = registry(contract)
    fields = {}
    raw = {}
    for feature in contract["primary"]:
        name = feature["source"]
        values, missing, invalid = clean_variable(ds[name], specs[name])
        raw[name] = values
        fields[name] = (("time", "lat", "lon"), values)
        fields[f"{name}__missing"] = (("time", "lat", "lon"), missing.astype("uint8"))
        fields[f"{name}__invalid"] = (("time", "lat", "lon"), invalid.astype("uint8"))
        transform = feature["transform"]
        if transform == "percent_to_fraction":
            transformed = values / 100.0
        elif transform == "log1p":
            transformed = np.log1p(values)
        elif transform == "identity":
            transformed = values.copy()
        else:
            raise ValueError(f"Unknown transformation: {transform}")
        fields[feature["output"]] = (("time", "lat", "lon"), transformed)
    area = raw["cldarea_total_1h"]
    complete = np.logical_and.reduce([np.isfinite(v) for v in raw.values()])
    # Mutually exclusive statuses preserve the full denominator.
    status = np.full(area.shape, 3, dtype="uint8")
    status[np.isfinite(area) & (area > 0) & complete] = 0
    status[np.isfinite(area) & (area == 0)] = 1
    status[~np.isfinite(area)] = 2
    fields["status"] = (("time", "lat", "lon"), status)
    fields["eligible"] = (("time", "lat", "lon"), (status == 0).astype("uint8"))
    out = xr.Dataset(fields, coords={d: ds[d] for d in ("time", "lat", "lon")})
    out["hourly_slot"] = ("time", ds.time.values.astype("datetime64[h]").astype("datetime64[ns]"))
    out["status"].attrs.update(flag_values=np.arange(4, dtype="uint8"),
        flag_meanings="eligible_cloudy clear invalid_or_missing_area incomplete_cloudy")
    for feature in contract["primary"]:
        out[feature["source"]].attrs["units"] = specs[feature["source"]]["units"]
        out[feature["output"]].attrs.update(units=feature["units"], transform=feature["transform"])
    return out


def sample_indices(eligible, year, seed, size):
    indices = np.flatnonzero(np.asarray(eligible).ravel())
    rng = np.random.default_rng(np.random.SeedSequence([seed, year]))
    return np.sort(rng.choice(indices, min(size, len(indices)), replace=False))


def observation_ids(ds, indices, season):
    ti, yi, xi = np.unravel_index(indices, (ds.sizes["time"], ds.sizes["lat"], ds.sizes["lon"]))
    return [f"{season}|{np.datetime_as_string(ds.time.values[t], unit='ns')}|"
            f"{float(ds.lat.values[y]):.8f}|{float(ds.lon.values[x]):.8f}"
            for t, y, x in zip(ti, yi, xi)]
