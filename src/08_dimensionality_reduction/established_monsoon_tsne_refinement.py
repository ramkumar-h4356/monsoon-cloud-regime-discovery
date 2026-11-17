from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.manifold import TSNE, trustworthiness

SOURCE_DIR = Path(__file__).resolve().parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from established_monsoon_tsne import (
    M4_DIR,
    OUTPUT_DIR as ORIGINAL_OUTPUT_DIR,
    PCA_INPUT_COMPONENTS,
    PERPLEXITIES,
    RANDOM_STATE,
    SAMPLE_PER_YEAR,
    TRUST_K,
    _load_pca_scores,
    stratified_year_date_sample,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFINED_OUTPUT_DIR = (
    PROJECT_ROOT
    / "data/processed/clustering/established_monsoon/m5_tsne_refined"
)
MAX_ITERATIONS = 3000


def make_tsne(perplexity: int, random_state: int = RANDOM_STATE) -> TSNE:
    params = inspect.signature(TSNE).parameters
    iteration_key = "max_iter" if "max_iter" in params else "n_iter"
    return TSNE(
        n_components=2,
        perplexity=perplexity,
        early_exaggeration=12.0,
        learning_rate="auto",
        init="pca",
        random_state=random_state,
        method="barnes_hut",
        angle=0.5,
        **{iteration_key: MAX_ITERATIONS},
    )


def load_aligned_representations():
    baseline, baseline_meta = _load_pca_scores(
        M4_DIR / "baseline_scores_and_metadata.npz"
    )
    log_sensitivity, log_meta = _load_pca_scores(
        M4_DIR / "log_sensitivity_scores_and_metadata.npz"
    )
    columns = ["year", "date", "latitude", "longitude"]
    if not baseline_meta[columns].equals(log_meta[columns]):
        raise ValueError("Baseline and log-sensitivity metadata are not aligned.")
    return {
        "baseline": (baseline, baseline_meta),
        "log_sensitivity": (log_sensitivity, log_meta),
    }


def run_refinement(output_dir: Path = REFINED_OUTPUT_DIR):
    representations = load_aligned_representations()
    reference_meta = representations["baseline"][1]
    indices = stratified_year_date_sample(
        reference_meta,
        sample_per_year=SAMPLE_PER_YEAR,
        random_state=RANDOM_STATE,
    )
    sampled_meta = reference_meta.iloc[indices].reset_index(drop=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    sampled_meta.to_csv(output_dir / "m5_refined_sample_metadata.csv", index=False)

    summary = []
    for representation, (scores, metadata) in representations.items():
        columns = ["year", "date", "latitude", "longitude"]
        if not metadata[columns].equals(reference_meta[columns]):
            raise ValueError(f"Metadata alignment mismatch: {representation}")

        sampled_scores = scores[indices, :PCA_INPUT_COMPONENTS]

        for perplexity in PERPLEXITIES:
            print(
                f"Refined t-SNE: {representation}, perplexity={perplexity}, "
                f"n={len(indices)}, max_iter={MAX_ITERATIONS}"
            )
            model = make_tsne(perplexity)
            embedding = model.fit_transform(sampled_scores)

            if not np.isfinite(embedding).all():
                raise ValueError("Non-finite coordinates in refined embedding.")

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

            coords = sampled_meta.copy()
            coords["tsne_1"] = embedding[:, 0]
            coords["tsne_2"] = embedding[:, 1]
            coords.to_csv(output_dir / f"{stem}_coordinates.csv", index=False)

            years = sorted(coords["year"].unique().tolist())
            fig, ax = plt.subplots(figsize=(11, 8))
            scatter = ax.scatter(
                embedding[:, 0],
                embedding[:, 1],
                c=coords["year"].to_numpy(),
                cmap="turbo",
                s=7,
                alpha=0.68,
                linewidths=0,
            )
            cbar = fig.colorbar(scatter, ax=ax, ticks=years)
            cbar.set_label("Year")
            ax.set_title(
                f"Established Monsoon t-SNE — "
                f"{representation.replace('_', ' ').title()}\n"
                f"Perplexity {perplexity}; {len(indices)} observations"
            )
            ax.set_xlabel("t-SNE dimension 1")
            ax.set_ylabel("t-SNE dimension 2")
            ax.grid(alpha=0.15)
            fig.tight_layout()
            fig.savefig(output_dir / f"{stem}_by_year.png", dpi=180)
            plt.close(fig)

            trust = {
                f"trustworthiness_k_{k}": float(
                    trustworthiness(sampled_scores, embedding, n_neighbors=k)
                )
                for k in TRUST_K
            }
            summary.append({
                "representation": representation,
                "perplexity": perplexity,
                "sample_size": len(indices),
                "pca_input_components": PCA_INPUT_COMPONENTS,
                "max_iterations": MAX_ITERATIONS,
                "iterations_used": int(model.n_iter_),
                "reached_iteration_limit": bool(
                    model.n_iter_ >= MAX_ITERATIONS - 1
                ),
                "kl_divergence": float(model.kl_divergence_),
                **trust,
            })

    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(output_dir / "m5_refined_model_summary.csv", index=False)

    manifest = {
        "milestone": "M5 refinement",
        "purpose": "Convergence sensitivity and year-coloured visual diagnostics",
        "original_m5_output_preserved": str(ORIGINAL_OUTPUT_DIR),
        "refined_output": str(output_dir),
        "sample_strategy": "same deterministic 500-per-year, approximately date-balanced sample",
        "sample_per_year": SAMPLE_PER_YEAR,
        "sample_size": int(len(indices)),
        "years": sorted(sampled_meta["year"].unique().tolist()),
        "random_state": RANDOM_STATE,
        "pca_input_components": PCA_INPUT_COMPONENTS,
        "perplexities": list(PERPLEXITIES),
        "max_iterations": MAX_ITERATIONS,
        "interpretation_limits": [
            "t-SNE is an exploratory local-neighbourhood visualization.",
            "2D global distances, cluster areas and gaps are not reliable physical quantities.",
            "Year-coloured patterns show temporal composition, not causality.",
            "The sampled visualization does not replace full-data analysis.",
            "Independent embeddings cannot be compared by their coordinate axes or orientation.",
        ],
    }
    manifest["outputs"] = sorted(
        p.name for p in output_dir.iterdir() if p.is_file()
    )
    (output_dir / "established_monsoon_m5_refinement_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print("\n========== M5 REFINEMENT SUMMARY ==========")
    print(summary_df.to_string(index=False))
    print(f"Output: {output_dir.resolve()}")
    print("PASS: refined embeddings, diagnostics and plots generated.")
    return summary_df


if __name__ == "__main__":
    run_refinement()
