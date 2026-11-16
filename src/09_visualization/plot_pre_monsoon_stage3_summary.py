"""Presentation-only plot from sealed evaluation CSVs; no new statistics or fitting."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "data/processed/model_ready/phase3/matplotlib_cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(ROOT / "src/06_feature_engineering"))
from ceres_features import sha256


def plot(root=ROOT):
    root = Path(root)
    out = root / "reports/phase3/pre_monsoon/stage3_v1"
    source = out / "evaluation/bootstrap_intervals.csv"
    manifest = json.loads((out / "evaluation_manifest.json").read_text(encoding="utf-8"))
    if sha256(source) != manifest["output_sha256"][str(source.relative_to(root))]:
        raise ValueError("Evaluation CSV hash mismatch")
    target = root / "results/figures/phase3/pre_monsoon/stage3_v1_presentation"
    target.mkdir(parents=True, exist_ok=False)
    intervals = pd.read_csv(source)
    primary = intervals[intervals.primary]
    plt.figure(figsize=(8, 4))
    for cluster in (0, 1):
        rows = primary[primary.endpoint == f"cloudy_cluster_{cluster}"]
        color = f"C{cluster}"
        positions = rows.year + (-.04 if cluster == 0 else .04)
        plt.vlines(positions, rows.lower, rows.upper, color=color,
                   label=f"Cluster {cluster}: 95% within-window interval")
        plt.scatter(positions, rows.estimate, color=color, s=28)
    plt.xticks([2019, 2020, 2021]); plt.xlabel("Reserved holdout year")
    plt.ylabel("Fraction of eligible cloudy observations")
    plt.title("Frozen-model occurrence; 3-day joint-spatial block bootstrap")
    plt.legend(fontsize=8); plt.tight_layout()
    image = target / "occurrence_uncertainty.png"
    plt.savefig(image, dpi=160, bbox_inches="tight"); plt.close()
    receipt = dict(statistics_unchanged=True, model_refitted=False,
        purpose="Matched categorical colors/integer year ticks only; original evaluation figure retained.",
        script_sha256=sha256(Path(__file__)), input_sha256=sha256(source),
        output_path=str(image.relative_to(root)), output_sha256=sha256(image))
    with (out / "presentation_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
    print(image)
    return receipt


if __name__ == "__main__":
    plot()
