"""Physical profiles and population diagnostics; caller supplies allowed years only."""
import numpy as np
import pandas as pd
import xarray as xr


def physical_profiles(frame, labels, contract):
    rows = []
    for (split, cluster), group in frame.assign(cluster=labels).groupby(["split", "cluster"]):
        for name in frame.columns:
            if not name.endswith("_1h"):
                continue
            values = group[name].dropna().to_numpy()
            family = next(f for f in contract["families"] if name.startswith(f + "_"))
            rows.append(dict(split=split, cluster=int(cluster), variable=name,
                units=contract["families"][family]["units"], scope="stage1_fixed_sample",
                total=len(group), valid=len(values), missing=len(group) - len(values),
                mean=float(np.mean(values)) if len(values) else np.nan,
                median=float(np.median(values)) if len(values) else np.nan,
                p10=float(np.quantile(values, .1)) if len(values) else np.nan,
                p90=float(np.quantile(values, .9)) if len(values) else np.nan))
    return pd.DataFrame(rows)


def population_diagnostics(prepared, labels, year, split, k):
    """All-cell denominators plus cloudy-only conditional frequency; no bridging years."""
    status = prepared.status.values
    annual, spatial, hourly, daily, transitions, persistence = [], [], [], [], [], []
    eligible = int((status == 0).sum())
    for cluster in range(k):
        count = int((labels == cluster).sum())
        annual.append(dict(year=year, split=split, cluster=cluster, count=count,
            eligible=eligible, total=labels.size, cloudy_fraction=count / eligible,
            all_cell_fraction=count / labels.size,
            clear=int((status == 1).sum()), unavailable=int((status >= 2).sum())))
        counts = (labels == cluster).sum(axis=0)
        cloudy = (status == 0).sum(axis=0)
        for yi, latitude in enumerate(prepared.lat.values):
            for xi, longitude in enumerate(prepared.lon.values):
                spatial.append(dict(year=year, split=split, cluster=cluster,
                    latitude=float(latitude), longitude=float(longitude), count=int(counts[yi, xi]),
                    eligible=int(cloudy[yi, xi]), total=labels.shape[0],
                    cloudy_fraction=float(counts[yi, xi] / cloudy[yi, xi]) if cloudy[yi, xi] else np.nan))
    times = pd.DatetimeIndex(prepared.time.values)
    for key, identifiers in (("utc_hour", times.hour), ("date", times.strftime("%Y-%m-%d"))):
        target = hourly if key == "utc_hour" else daily
        for value in np.unique(identifiers):
            subset = labels[identifiers == value]
            denominator = int((subset >= 0).sum())
            for cluster in range(k):
                count = int((subset == cluster).sum())
                target.append(dict(year=year, split=split, **{key: value}, cluster=cluster,
                    count=count, eligible=denominator, total=subset.size,
                    cloudy_fraction=count / denominator if denominator else np.nan))
    left, right = labels[:-1].ravel(), labels[1:].ravel()
    # Full hourly coverage is validated upstream. Clear/unknown breaks a run.
    valid = (left >= 0) & (right >= 0)
    for a in range(k):
        denominator = int(((left == a) & valid).sum())
        for b in range(k):
            count = int(((left == a) & (right == b) & valid).sum())
            transitions.append(dict(year=year, split=split, from_cluster=a, to_cluster=b,
                count=count, valid_origin_pairs=denominator,
                probability=count / denominator if denominator else np.nan))
    for cell in labels.reshape(labels.shape[0], -1).T:
        edges = np.r_[0, np.flatnonzero(cell[1:] != cell[:-1]) + 1, len(cell)]
        for start, end in zip(edges[:-1], edges[1:]):
            if cell[start] >= 0:
                persistence.append((int(cell[start]), int(end - start), start == 0 or end == len(cell)))
    runs = pd.DataFrame(persistence, columns=["cluster", "hours", "boundary_censored"])
    summaries = []
    for cluster, group in runs.groupby("cluster"):
        summaries.append(dict(year=year, split=split, cluster=int(cluster), runs=len(group),
            median_hours=float(group.hours.median()), p90_hours=float(group.hours.quantile(.9)),
            boundary_censored=int(group.boundary_censored.sum())))
    return {"annual_occurrence": annual, "spatial_occurrence": spatial,
            "diurnal_occurrence": hourly, "daily_occurrence": daily,
            "transitions": transitions, "persistence": summaries}


def cautious_interpretations(profiles, k):
    rows = []
    for cluster in range(k):
        group = profiles[(profiles.cluster == cluster) & (profiles.split == "train")].set_index("variable")
        pressure = float(group.loc["cldpress_top_total_1h", "median"])
        tau = float(group.loc["cldtau_total_1h", "median"])
        area = float(group.loc["cldarea_total_1h", "median"])
        vertical = "high-topped" if pressure < 440 else "mid-topped" if pressure < 680 else "low-topped"
        optical = "optically thin" if tau < 3.6 else "moderate optical depth" if tau < 23 else "optically thick"
        rows.append(dict(cluster=cluster, label=f"{vertical}; {optical}",
            median_cloud_area_percent=area, median_optical_depth=tau,
            median_cloud_top_pressure_hpa=pressure,
            caution="Descriptive median bins only; not validated cloud types, convection or precipitation classes. "
                    "Broad gridded mixtures and overlapping within-cluster distributions remain."))
    return pd.DataFrame(rows)
