"""Prospective, empty-safe diagnostics. Historical evaluators remain unchanged.

This is an additive v2 API for synthetic tests or separately approved future
use. It is not plugged into or run over the completed temporal evaluation.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/08_evaluation"))
from pre_monsoon_stage2_diagnostics import population_diagnostics as historical_population
from pre_monsoon_stage3_tools import bootstrap_fractions, evaluate_metrics, prohibit_fitting


def safe_ratio(numerator, denominator):
    return float(numerator / denominator) if denominator else np.nan


def distance_summary(distance, thresholds):
    values = np.asarray(distance, dtype=float)
    if any(not np.isfinite(value) or value < 0 for value in thresholds.values()):
        raise ValueError("Frozen thresholds must be finite and nonnegative")
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Distances must be finite, nonnegative eligible-row values")
    if values.size == 0:
        return dict(status="undefined_no_eligible", n=0, mean_squared_distance=np.nan,
                    median_distance=np.nan, p95_distance=np.nan, p99_distance=np.nan,
                    exceedance={key: np.nan for key in thresholds})
    return dict(status="defined", n=int(values.size),
                mean_squared_distance=float(np.mean(values**2)),
                median_distance=float(np.median(values)),
                p95_distance=float(np.quantile(values, .95)),
                p99_distance=float(np.quantile(values, .99)),
                exceedance={key: float((values > value).mean()) for key, value in thresholds.items()})


def pc_summary(scores, n_components):
    scores = np.asarray(scores, dtype=float)
    if scores.ndim != 2 or scores.shape[1] != n_components or not np.isfinite(scores).all():
        raise ValueError("Invalid fixed-PC score matrix")
    n = len(scores)
    variance = scores.var(axis=0, ddof=1) if n > 1 else np.full(n_components, np.nan)
    mean = scores.mean(axis=0) if n else np.full(n_components, np.nan)
    total = float(variance.sum())
    fractions = variance / total if np.isfinite(total) and total > 0 else np.full(n_components, np.nan)
    return [dict(component=i+1, n=n, mean=float(mean[i]), variance=float(variance[i]),
                 fraction_of_total_score_variance=float(fractions[i]),
                 status="defined" if n > 1 and total > 0 else "undefined_variance_support")
            for i in range(n_components)]


def bootstrap_fractions_v2(daily, year, config):
    """No adaptive block lengths: unsupported lengths retain undefined rows."""
    required = ["total", "eligible", "clear", *[f"cluster_{i}" for i in range(config["n_clusters"])],
                *[f"above_q{int(q*100)}" for q in config["distance_quantiles"]]]
    if not set(required).issubset(daily.columns):
        raise ValueError("Missing daily sufficient-statistic columns")
    endpoints = [(f"cloudy_cluster_{i}", f"cluster_{i}", "eligible") for i in range(config["n_clusters"])]
    endpoints += [(f"all_cell_cluster_{i}", f"cluster_{i}", "total") for i in range(config["n_clusters"])]
    endpoints += [("all_cell_clear", "clear", "total")]
    endpoints += [(f"distance_above_q{int(q*100)}", f"above_q{int(q*100)}", "eligible")
                  for q in config["distance_quantiles"]]
    result = []
    for length in [config["bootstrap_primary_days"], *config["bootstrap_sensitivity_days"]]:
        if len(daily) >= length:
            one = dict(config, bootstrap_primary_days=length, bootstrap_sensitivity_days=[])
            rows = bootstrap_fractions(daily, year, one)
            for row in rows:
                row["primary"] = length == config["bootstrap_primary_days"]
                row["status"] = "defined" if row["valid_replicates"] else "undefined_no_denominator"
            result.extend(rows)
        else:
            for endpoint, numerator, denominator in endpoints:
                result.append(dict(year=year, endpoint=endpoint, block_days=length,
                    primary=length == config["bootstrap_primary_days"],
                    estimate=safe_ratio(daily[numerator].sum(), daily[denominator].sum()),
                    lower=np.nan, upper=np.nan, replicates=config["bootstrap_replicates"],
                    valid_replicates=0, status="undefined_insufficient_days",
                    interpretation="Prespecified block length unsupported; not shortened or tuned"))
    return result


def physical_profiles_v2(frame, labels, contract, variables, period, k):
    """Keep missing clusters/retrievals visible, with original-unit denominators."""
    labels = np.asarray(labels)
    if len(labels) != len(frame) or not np.isin(labels, np.arange(k)).all():
        raise ValueError("Invalid eligible-sample profile labels")
    rows = []
    for cluster in range(k):
        subset = frame.loc[labels == cluster]
        for name in variables:
            if name not in frame.columns:
                raise ValueError(f"Missing physical property column: {name}")
            family = next((f for f in sorted(contract["families"], key=len, reverse=True)
                           if name.startswith(f+"_")), None)
            if family is None:
                raise ValueError(f"Unknown physical property: {name}")
            values = subset[name].dropna().to_numpy()
            if not np.isfinite(values).all():
                raise ValueError("Profile inputs must use the fixed physical-validity mask")
            rows.append(dict(period=str(period), cluster=cluster, variable=name,
                units=contract["families"][family]["units"], scope="prospective_v2_sample",
                total=len(subset), valid=len(values), missing=len(subset)-len(values),
                mean=float(values.mean()) if len(values) else np.nan,
                median=float(np.median(values)) if len(values) else np.nan,
                p10=float(np.quantile(values, .1)) if len(values) else np.nan,
                p90=float(np.quantile(values, .9)) if len(values) else np.nan,
                status="defined" if len(values) else "undefined_no_observations" if not len(subset)
                       else "undefined_no_valid_retrievals"))
    return pd.DataFrame(rows)


def population_diagnostics_v2(prepared, labels, year, split, k):
    status = np.asarray(prepared.status.values)
    labels = np.asarray(labels)
    if status.shape != labels.shape or status.ndim != 3:
        raise ValueError("Status/labels must share (time, lat, lon) shape")
    if not np.isin(status, [0, 1, 2, 3]).all():
        raise ValueError("Unexpected eligibility status")
    if not ((labels[status == 1] == -1).all() and (labels[status >= 2] == -2).all()
            and ((labels[status == 0] >= 0) & (labels[status == 0] < k)).all()):
        raise ValueError("Labels disagree with eligibility or configured cluster IDs")
    if np.count_nonzero(status == 0):
        return historical_population(prepared, labels, year, split, k)
    # Preserve all-cell denominators and explicit zero-count rows for every
    # configured group, including when time itself is empty. Never call models.
    tables = {name: [] for name in ("annual_occurrence", "spatial_occurrence",
                                   "diurnal_occurrence", "daily_occurrence", "transitions", "persistence")}
    for cluster in range(k):
        tables["annual_occurrence"].append(dict(year=year, split=split, cluster=cluster,
            count=0, eligible=0, total=status.size, cloudy_fraction=np.nan,
            all_cell_fraction=safe_ratio(0, status.size), clear=int((status == 1).sum()),
            unavailable=int((status >= 2).sum()), status="undefined_no_eligible"))
        for latitude in prepared.lat.values:
            for longitude in prepared.lon.values:
                tables["spatial_occurrence"].append(dict(year=year, split=split, cluster=cluster,
                    latitude=float(latitude), longitude=float(longitude), count=0, eligible=0,
                    total=status.shape[0], cloudy_fraction=np.nan,
                    all_cell_fraction=safe_ratio(0, status.shape[0])))
        tables["persistence"].append(dict(year=year, split=split, cluster=cluster, runs=0,
            median_hours=np.nan, p90_hours=np.nan, boundary_censored=0, status="undefined_no_runs"))
        for target in range(k):
            tables["transitions"].append(dict(year=year, split=split, from_cluster=cluster,
                to_cluster=target, count=0, valid_origin_pairs=0, probability=np.nan))
    times = pd.DatetimeIndex(prepared.time.values)
    for key, identifiers, table in (("utc_hour", times.hour, "diurnal_occurrence"),
                                    ("date", times.strftime("%Y-%m-%d"), "daily_occurrence")):
        for value in np.unique(identifiers):
            total = int((identifiers == value).sum()) * status.shape[1] * status.shape[2]
            for cluster in range(k):
                tables[table].append(dict(year=year, split=split, **{key: value}, cluster=cluster,
                    count=0, eligible=0, total=total, cloudy_fraction=np.nan,
                    all_cell_fraction=safe_ratio(0, total)))
    return tables


def evaluate_period_v2(bundle, prepared, year, split, thresholds):
    """Empty-safe inference/diagnostics API; no selection, fitting or file writes.

    Caller provides an already-fitted seasonal bundle. For zero eligible rows
    no estimator transform or predict method is invoked. Existing evaluation
    results are never loaded, patched, regenerated or overwritten here.
    """
    if bundle["season"] != "pre_monsoon":
        raise ValueError("Wrong seasonal bundle")
    if tuple(prepared.status.dims) != ("time", "lat", "lon"):
        raise ValueError("Expected explicit (time, lat, lon) status dimensions")
    status = prepared.status.values
    indices = np.flatnonzero(status.ravel() == 0)
    labels = np.where(status == 1, -1, -2).astype("int16")
    n_components = bundle["selected_n_components"]
    k = bundle["kmeans"].n_clusters
    scores = np.empty((0, n_components))
    z = np.empty((0, len(bundle["feature_order"])))
    distances = np.array([], dtype=float)
    with prohibit_fitting():
        if len(indices):
            x = np.column_stack([prepared[name].values.ravel()[indices] for name in bundle["feature_order"]])
            if not np.isfinite(x).all():
                raise ValueError("Eligible rows must be complete; no population-expanding imputation")
            z = bundle["scaler"].transform(bundle["imputer"].transform(x))
            scores = bundle["pca"].transform(z)[:, :n_components]
            prediction = bundle["kmeans"].predict(scores)
            distances = bundle["kmeans"].transform(scores)[np.arange(len(x)), prediction]
            labels.ravel()[indices] = prediction
    tables = population_diagnostics_v2(prepared, labels, year, split, k)
    metric, per_cluster, points = evaluate_metrics(z, labels.ravel()[indices], indices,
                                                   str(year), {"n_clusters": k})
    return dict(labels=labels, eligible_indices=indices, population=tables,
                distances=distance_summary(distances, thresholds), fixed_pcs=pc_summary(scores, n_components),
                metrics=metric, per_cluster_metrics=per_cluster, silhouette_points=points,
                status="defined" if len(indices) else "undefined_no_eligible")
