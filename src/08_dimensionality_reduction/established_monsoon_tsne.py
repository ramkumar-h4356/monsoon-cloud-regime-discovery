from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.manifold import TSNE, trustworthiness


PROJECT_ROOT = Path(__file__).resolve().parents[2]
M3_DIR = PROJECT_ROOT / "data/processed/clustering/established_monsoon/m3_feature_preparation"
M4_DIR = PROJECT_ROOT / "data/processed/clustering/established_monsoon/m4_pca"
OUTPUT_DIR = PROJECT_ROOT / "data/processed/clustering/established_monsoon/m5_tsne"

RANDOM_STATE = 42
SAMPLE_PER_YEAR = 500
PERPLEXITIES = (30, 50)
PCA_INPUT_COMPONENTS = 10
TRUST_K = (5, 15, 30)


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(f"Required input not found: {path}")
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def _first_present(data: dict[str, np.ndarray], candidates: tuple[str, ...], label: str) -> np.ndarray:
    for key in candidates:
        if key in data:
            return data[key]
    raise ValueError(
        f"Could not find {label}. Available NPZ keys: {sorted(data)}; "
        f"expected one of {candidates}."
    )


def _load_pca_scores(path: Path) -> tuple[np.ndarray, pd.DataFrame]:
    data = _load_npz(path)
    scores = _first_present(data, ("scores", "pca_scores", "transformed", "X_scores"), "PCA scores")
    required = ("year", "date", "latitude", "longitude")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"PCA score archive is missing metadata arrays: {missing}")
    metadata = pd.DataFrame({key: data[key] for key in required})
    scores = np.asarray(scores)
    if scores.ndim != 2 or scores.shape[0] != len(metadata):
        raise ValueError(f"Invalid PCA score shape {scores.shape} for {len(metadata)} metadata rows.")
    if scores.shape[1] < PCA_INPUT_COMPONENTS:
        raise ValueError(f"Expected at least {PCA_INPUT_COMPONENTS} PCA components, found {scores.shape[1]}.")
    if not np.isfinite(scores).all():
        raise ValueError(f"Non-finite values found in PCA scores: {path}")
    metadata["year"] = pd.to_numeric(metadata["year"], errors="raise").astype(int)
    metadata["date"] = metadata["date"].astype(str)
    metadata["latitude"] = pd.to_numeric(metadata["latitude"], errors="raise")
    metadata["longitude"] = pd.to_numeric(metadata["longitude"], errors="raise")
    return scores, metadata


def load_inputs() -> tuple[dict[str, tuple[np.ndarray, pd.DataFrame]], dict[str, Any]]:
    manifest_path = M3_DIR / "established_monsoon_group_B_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"M3 manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    baseline, baseline_meta = _load_pca_scores(M4_DIR / "baseline_scores_and_metadata.npz")
    log_sensitivity, log_meta = _load_pca_scores(M4_DIR / "log_sensitivity_scores_and_metadata.npz")

    keys = ["year", "date", "latitude", "longitude"]
    if not baseline_meta[keys].equals(log_meta[keys]):
        raise ValueError("Baseline and log-sensitivity PCA metadata are not identically aligned.")
    expected_rows = int(manifest.get("complete_case_rows", len(baseline_meta)))
    if len(baseline_meta) != expected_rows:
        raise ValueError(
            f"M3 manifest expects {expected_rows} complete-case rows, "
            f"but M4 PCA scores contain {len(baseline_meta)}."
        )
    return {
        "baseline": (baseline, baseline_meta),
        "log_sensitivity": (log_sensitivity, log_meta),
    }, manifest


def stratified_year_date_sample(
    metadata: pd.DataFrame,
    sample_per_year: int = SAMPLE_PER_YEAR,
    random_state: int = RANDOM_STATE,
) -> np.ndarray:
    """Select a deterministic, approximately date-balanced sample within every year."""
    if sample_per_year < 2:
        raise ValueError("sample_per_year must be at least 2.")
    required = {"year", "date"}
    if not required.issubset(metadata.columns):
        raise ValueError(f"Metadata must contain {sorted(required)}.")
    rng = np.random.default_rng(random_state)
    selected: list[int] = []

    for year in sorted(metadata["year"].unique()):
        year_indices = metadata.index[metadata["year"] == year].to_numpy()
        dates = sorted(metadata.loc[year_indices, "date"].astype(str).unique())
        if len(year_indices) < sample_per_year:
            raise ValueError(
                f"Year {year} has only {len(year_indices)} rows; "
                f"cannot draw {sample_per_year} observations."
            )
        if not dates:
            raise ValueError(f"No dates found for year {year}.")
        base, remainder = divmod(sample_per_year, len(dates))
        date_order = np.array(dates, dtype=object)
        rng.shuffle(date_order)
        extra_dates = set(date_order[:remainder].tolist())
        year_selected: list[int] = []
        for date in dates:
            group = metadata.index[
                (metadata["year"] == year) & (metadata["date"].astype(str) == date)
            ].to_numpy()
            take = base + (1 if date in extra_dates else 0)
            if len(group) < take:
                raise ValueError(
                    f"Year {year}, date {date} has {len(group)} rows; "
                    f"requires {take} for date-balanced sampling."
                )
            year_selected.extend(rng.choice(group, size=take, replace=False).tolist())
        if len(year_selected) != sample_per_year:
            raise RuntimeError(f"Internal sampling error for year {year}: {len(year_selected)} rows.")
        selected.extend(year_selected)

    result = np.array(sorted(selected), dtype=np.int64)
    if len(np.unique(result)) != len(result):
        raise RuntimeError("Sampling produced duplicate row indices.")
    return result


def _make_tsne(perplexity: int, random_state: int) -> TSNE:
    params = inspect.signature(TSNE).parameters
    iteration_key = "max_iter" if "max_iter" in params else "n_iter"
    kwargs = {
        "n_components": 2,
        "perplexity": perplexity,
        "early_exaggeration": 12.0,
        "learning_rate": "auto",
        "init": "pca",
        "random_state": random_state,
        "method": "barnes_hut",
        "angle": 0.5,
        iteration_key: 1000,
    }
    return TSNE(**kwargs)


def run_tsne(
    scores: np.ndarray,
    perplexity: int,
    random_state: int = RANDOM_STATE,
) -> tuple[np.ndarray, float, int]:
    if scores.ndim != 2 or scores.shape[0] <= perplexity:
        raise ValueError(
            f"t-SNE requires a 2D matrix with more rows than perplexity; "
            f"received shape {scores.shape}, perplexity={perplexity}."
        )
    model = _make_tsne(perplexity, random_state)
    embedding = model.fit_transform(scores)
    if not np.isfinite(embedding).all():
        raise ValueError("t-SNE generated non-finite embedding coordinates.")
    return embedding, float(model.kl_divergence_), int(model.n_iter_)


def run(output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    representations, m3_manifest = load_inputs()
    reference_meta = representations["baseline"][1]
    indices = stratified_year_date_sample(reference_meta)
    sampled_meta = reference_meta.iloc[indices].reset_index(drop=True)

    expected_years = sorted(reference_meta["year"].unique().tolist())
    sample_counts = sampled_meta.groupby("year").size().to_dict()
    if any(sample_counts.get(year, 0) != SAMPLE_PER_YEAR for year in expected_years):
        raise RuntimeError(f"Yearly sample allocation is not balanced: {sample_counts}")

    output_dir.mkdir(parents=True, exist_ok=True)
    sampled_meta.to_csv(output_dir / "m5_tsne_sample_metadata.csv", index=False)

    summaries = []
    for representation, (all_scores, metadata) in representations.items():
        if not metadata[["year", "date", "latitude", "longitude"]].equals(
            reference_meta[["year", "date", "latitude", "longitude"]]
        ):
            raise ValueError(f"Metadata alignment changed for {representation}.")
        sampled_scores = all_scores[indices, :PCA_INPUT_COMPONENTS]
        for perplexity in PERPLEXITIES:
            print(
                f"Running t-SNE: representation={representation}, "
                f"sample={len(indices)}, PCA dimensions={PCA_INPUT_COMPONENTS}, "
                f"perplexity={perplexity}..."
            )
            embedding, kl, iterations = run_tsne(sampled_scores, perplexity)
            stem = f"{representation}_perplexity_{perplexity}"
            np.savez_compressed(
                output_dir / f"{stem}_embedding.npz",
                embedding=embedding,
                year=sampled_meta["year"].to_numpy(),
                date=sampled_meta["date"].to_numpy(dtype="U10"),
                latitude=sampled_meta["latitude"].to_numpy(),
                longitude=sampled_meta["longitude"].to_numpy(),
                sample_indices=indices,
            )
            coordinates = sampled_meta.copy()
            coordinates["tsne_1"] = embedding[:, 0]
            coordinates["tsne_2"] = embedding[:, 1]
            coordinates.to_csv(output_dir / f"{stem}_coordinates.csv", index=False)

            trust = {}
            for k in TRUST_K:
                if k < len(sampled_scores) // 2:
                    trust[f"trustworthiness_k_{k}"] = float(
                        trustworthiness(sampled_scores, embedding, n_neighbors=k)
                    )
            summaries.append({
                "representation": representation,
                "perplexity": perplexity,
                "sample_size": len(indices),
                "pca_input_components": PCA_INPUT_COMPONENTS,
                "kl_divergence": kl,
                "iterations": iterations,
                **trust,
            })

    summary_df = pd.DataFrame(summaries)
    summary_df.to_csv(output_dir / "m5_tsne_model_summary.csv", index=False)

    manifest = {
        "milestone": "M5",
        "method": "t-SNE",
        "source": "M4 PCA score archives; first 10 PCA dimensions",
        "sample_strategy": "500 observations per year, approximately balanced across dates",
        "sample_per_year": SAMPLE_PER_YEAR,
        "sample_size_total": int(len(indices)),
        "years": expected_years,
        "random_state": RANDOM_STATE,
        "perplexities": list(PERPLEXITIES),
        "pca_input_components": PCA_INPUT_COMPONENTS,
        "tsne": {
            "n_components": 2,
            "init": "pca",
            "learning_rate": "auto",
            "method": "barnes_hut",
            "angle": 0.5,
            "max_iterations": 1000,
        },
        "interpretation_limits": [
            "t-SNE is an exploratory visualization of local neighbourhood structure.",
            "Distances between well-separated groups in the 2D embedding are not reliable global distances.",
            "Cluster-like shapes in the embedding are not, by themselves, evidence of physical cloud regimes.",
            "The sampled embedding does not replace analyses using the full observation dataset.",
            "Baseline and log-sensitivity embeddings are fitted independently; their coordinate axes and orientations are not directly comparable.",
        ],
        "m3_manifest_complete_case_rows": m3_manifest.get("complete_case_rows"),
        "outputs": sorted(p.name for p in output_dir.iterdir() if p.is_file()),
    }
    (output_dir / "established_monsoon_m5_tsne_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print("\n========== M5 t-SNE SUMMARY ==========")
    print(f"Total observations available: {len(reference_meta):,}")
    print(f"Observations sampled: {len(indices):,}")
    print(f"Years: {expected_years}")
    print(f"Representations: {', '.join(representations)}")
    print(f"Perplexities: {PERPLEXITIES}")
    print(summary_df.to_string(index=False))
    print(f"Output: {output_dir.resolve()}")
    print("PASS: all t-SNE embeddings and metadata validated.")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Established Monsoon M5 t-SNE analysis.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
