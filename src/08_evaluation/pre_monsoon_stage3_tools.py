"""Pure frozen-evaluation calculations; no estimator fitting."""
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.manifold import TSNE
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_samples
from sklearn.preprocessing import StandardScaler


@contextmanager
def prohibit_fitting():
    """Turn accidental estimator fitting into a hard error, including indirect calls."""
    with ExitStack() as stack:
        for cls in (SimpleImputer, StandardScaler, PCA, KMeans, TSNE):
            for name in ("fit", "fit_transform", "fit_predict", "partial_fit"):
                if hasattr(cls, name):
                    stack.enter_context(patch.object(cls, name, side_effect=RuntimeError(
                        "Stage 3 prohibits estimator fitting")))
        yield


def nested_samples(eligible, year, config):
    eligible = np.asarray(eligible, dtype=int)
    def choose(population, size, stream):
        rng = np.random.default_rng(np.random.SeedSequence(
            [config["seed"], config["stage_seed_namespace"], year, stream]))
        return np.sort(rng.choice(population, min(size, len(population)), replace=False))
    profile = choose(eligible, config["profile_sample_per_year"], 0)
    metric = choose(profile, config["metric_sample_per_year"], 1)
    pooled = choose(metric, config["pooled_metric_sample_per_year"], 2)
    return profile, metric, pooled


def evaluate_metrics(z, labels, identities, period, config):
    labels = np.asarray(labels)
    unique, counts = np.unique(labels, return_counts=True)
    row = dict(period=str(period), n=len(labels), observed_clusters=len(unique),
        minimum_cluster_fraction=float(counts.min() / len(labels)) if len(labels) else np.nan,
        silhouette=np.nan, calinski_harabasz=np.nan, davies_bouldin=np.nan,
        negative_silhouette_fraction=np.nan, status="undefined")
    details, points = [], []
    if 1 < len(unique) < len(labels):
        values = silhouette_samples(z, labels)
        row.update(silhouette=float(values.mean()),
                   calinski_harabasz=float(calinski_harabasz_score(z, labels)),
                   davies_bouldin=float(davies_bouldin_score(z, labels)),
                   negative_silhouette_fraction=float((values < 0).mean()), status="defined")
        for cluster in range(config["n_clusters"]):
            s = values[labels == cluster]
            details.append(dict(period=str(period), cluster=cluster, n=len(s),
                mean=float(s.mean()) if len(s) else np.nan,
                median=float(np.median(s)) if len(s) else np.nan,
                p10=float(np.quantile(s, .1)) if len(s) else np.nan,
                p90=float(np.quantile(s, .9)) if len(s) else np.nan,
                negative_fraction=float((s < 0).mean()) if len(s) else np.nan))
        points = [dict(period=str(period), observation_id=identity, cluster=int(label), silhouette=float(value))
                  for identity, label, value in zip(identities, labels, values)]
    return row, details, points


def moving_day_indices(n_days, block_days, seed, replicates):
    if not 1 <= block_days <= n_days:
        raise ValueError("Block length exceeds the annual window")
    rng = np.random.default_rng(np.random.SeedSequence(seed))
    starts = rng.integers(0, n_days - block_days + 1,
                          size=(replicates, int(np.ceil(n_days / block_days))))
    return (starts[:, :, None] + np.arange(block_days)).reshape(replicates, -1)[:, :n_days]


def bootstrap_fractions(daily, year, config):
    """Daily sufficient statistics preserve all within-day spatial dependence."""
    rows = []
    endpoints = [(f"cloudy_cluster_{k}", f"cluster_{k}", "eligible")
                 for k in range(config["n_clusters"])]
    endpoints += [(f"all_cell_cluster_{k}", f"cluster_{k}", "total")
                  for k in range(config["n_clusters"])]
    endpoints += [("all_cell_clear", "clear", "total")]
    endpoints += [(f"distance_above_q{int(q*100)}", f"above_q{int(q*100)}", "eligible")
                  for q in config["distance_quantiles"]]
    for length in [config["bootstrap_primary_days"], *config["bootstrap_sensitivity_days"]]:
        indices = moving_day_indices(len(daily), length,
            [config["seed"], config["stage_seed_namespace"], year, 3, length], config["bootstrap_replicates"])
        for endpoint, numerator, denominator in endpoints:
            a, b = daily[numerator].to_numpy(), daily[denominator].to_numpy()
            total_denominator = b.sum()
            num, den = a[indices].sum(axis=1), b[indices].sum(axis=1)
            fractions = np.divide(num, den, out=np.full(len(den), np.nan), where=den != 0)
            finite = fractions[np.isfinite(fractions)]
            ci = np.percentile(finite, config["interval_percentiles"]) if len(finite) else [np.nan, np.nan]
            rows.append(dict(year=year, endpoint=endpoint, block_days=length,
                primary=length == config["bootstrap_primary_days"],
                estimate=float(a.sum() / total_denominator) if total_denominator else np.nan,
                lower=float(ci[0]), upper=float(ci[1]), replicates=config["bootstrap_replicates"],
                valid_replicates=len(finite), interpretation="conditional within-window percentile interval"))
    return rows


def ordering_checks(profiles, config):
    rows = []
    for period, group in profiles.groupby("period", sort=False):
        for variable, expected in config["expected_ordering"].items():
            selected = group[group.variable == variable].set_index("cluster")
            a = float(selected.loc[0, "median"]) if 0 in selected.index else np.nan
            b = float(selected.loc[1, "median"]) if 1 in selected.index else np.nan
            defined = np.isfinite(a) and np.isfinite(b)
            supported = (b > a if expected == "cluster_1_greater" else b < a) if defined else False
            rows.append(dict(period=str(period), variable=variable, expected=expected,
                cluster_0_median=a, cluster_1_median=b,
                result="supported" if supported else "reversed_or_equal" if defined else "undefined"))
    return rows
