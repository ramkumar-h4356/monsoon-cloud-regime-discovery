"""Training-only preprocessing, PCA diagnostics and reproducible cluster tools."""
from itertools import combinations

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score,
                             davies_bouldin_score, silhouette_samples)
from sklearn.preprocessing import StandardScaler


def fit_preprocessing(x_train):
    x_train = np.asarray(x_train, dtype="float64")
    if x_train.ndim != 2 or np.isinf(x_train).any() or np.isnan(x_train).all(axis=0).any():
        raise ValueError("Training features must have finite support in every column")
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    filled = imputer.fit_transform(x_train)
    scaler = StandardScaler().fit(filled)
    if (scaler.var_ <= 0).any():
        raise ValueError("Constant training features require a revised feature contract")
    standardized = scaler.transform(filled)
    pca = PCA(n_components=x_train.shape[1], svd_solver="full", whiten=False).fit(standardized)
    return {"imputer": imputer, "scaler": scaler, "pca": pca}


def scaled(bundle, x):
    return bundle["scaler"].transform(bundle["imputer"].transform(np.asarray(x, dtype="float64")))


def project(bundle, x, n_components):
    return bundle["pca"].transform(scaled(bundle, x))[:, :n_components]


def pca_reconstruction(bundle, x_train, x_development):
    pca = bundle["pca"]
    rows = []
    for split, values in (("train", x_train), ("development", x_development)):
        z = scaled(bundle, values)
        scores = pca.transform(z)
        for n in range(1, pca.n_components_ + 1):
            reconstructed = scores[:, :n] @ pca.components_[:n] + pca.mean_
            rmse = np.sqrt(np.mean((z - reconstructed) ** 2, axis=0))
            rows.append(dict(split=split, n_components=n,
                             cumulative_variance=float(pca.explained_variance_ratio_[:n].sum()),
                             standardized_rmse=float(np.sqrt(np.mean((z - reconstructed) ** 2))),
                             max_feature_rmse=float(rmse.max()),
                             **{f"feature_{i}_rmse": float(v) for i, v in enumerate(rmse)}))
    return rows


def select_components(rows, target, max_rmse):
    eligible = [r["n_components"] for r in rows if r["split"] == "development"
                and r["cumulative_variance"] >= target - 1e-12
                and r["max_feature_rmse"] <= max_rmse]
    if not eligible:
        raise ValueError("No PCA dimension satisfies the documented retention criteria")
    return min(eligible)


def kmeans(config, k, seed, n_init=None):
    return KMeans(n_clusters=k, init="k-means++", n_init=n_init or config["kmeans_n_init"],
                  max_iter=config["kmeans_max_iter"], tol=config["kmeans_tolerance"],
                  algorithm="lloyd", random_state=seed)


def cluster_metrics(x, labels):
    labels = np.asarray(labels)
    unique, counts = np.unique(labels, return_counts=True)
    result = {"n": len(labels), "observed_clusters": len(unique),
              "minimum_cluster_fraction": float(counts.min() / len(labels)),
              "silhouette": np.nan, "calinski_harabasz": np.nan, "davies_bouldin": np.nan,
              "negative_silhouette_fraction": np.nan}
    per_cluster = []
    if 1 < len(unique) < len(labels):
        silhouettes = silhouette_samples(x, labels)
        result.update(silhouette=float(silhouettes.mean()),
                      calinski_harabasz=float(calinski_harabasz_score(x, labels)),
                      davies_bouldin=float(davies_bouldin_score(x, labels)),
                      negative_silhouette_fraction=float((silhouettes < 0).mean()))
        for label in unique:
            s = silhouettes[labels == label]
            per_cluster.append(dict(cluster=int(label), n=len(s), silhouette=float(s.mean()),
                                    negative_fraction=float((s < 0).mean())))
    return result, per_cluster


def matched_jaccard(a, b, k):
    matrix = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            union = np.count_nonzero((a == i) | (b == j))
            matrix[i, j] = np.count_nonzero((a == i) & (b == j)) / union if union else 0
    ri, ci = linear_sum_assignment(-matrix)
    return float(matrix[ri, ci].mean()), float(matrix[ri, ci].min())


def initialization_stability(predictions, k):
    rows = []
    for (seed_a, a), (seed_b, b) in combinations(predictions.items(), 2):
        mean_j, min_j = matched_jaccard(a, b, k)
        rows.append(dict(k=k, seed_a=seed_a, seed_b=seed_b,
                         ari=float(adjusted_rand_score(a, b)),
                         matched_jaccard_mean=mean_j, matched_jaccard_min=min_j))
    return rows


def year_bootstrap_indices(years, seed):
    """Resample whole seasonal-year blocks, including multiplicity; never development."""
    years = np.asarray(years)
    unique = np.unique(years)
    chosen = np.random.default_rng(seed).choice(unique, len(unique), replace=True)
    return np.concatenate([np.flatnonzero(years == year) for year in chosen]), chosen


def select_k(metrics, initialization, sampling, config):
    """Smallest stable solution within a fixed development-silhouette tolerance."""
    import pandas as pd
    base = pd.DataFrame(metrics)
    base = base[(base.split == "development") & (base.space == "scaled_original")].copy()
    init = pd.DataFrame(initialization).groupby("k").ari.median()
    boot = pd.DataFrame(sampling).groupby("k").ari.median()
    base["initialization_ari_median"] = base.k.map(init)
    base["sampling_ari_median"] = base.k.map(boot)
    base["admissible"] = ((base.minimum_cluster_fraction >= config["minimum_cluster_fraction"])
        & (base.initialization_ari_median >= config["minimum_stability_ari"])
        & (base.sampling_ari_median >= config["minimum_stability_ari"])
        & (base.observed_clusters == base.k) & base.silhouette.notna())
    acceptable = base[base.admissible]
    if acceptable.empty:
        return None, base  # report ambiguity rather than silently relaxing thresholds
    best = acceptable.silhouette.max()
    chosen = int(acceptable[acceptable.silhouette >= best - config["silhouette_tolerance"]].k.min())
    base["selected"] = base.k == chosen
    return chosen, base
