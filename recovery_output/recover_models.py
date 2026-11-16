import os, json, hashlib, warnings, traceback
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import joblib

from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

ROOT = Path.cwd()
OUT = ROOT / "recovery_output"
OUT.mkdir(exist_ok=True)

BASE = ROOT / "data/processed/clustering/established_monsoon"
META = BASE / "established_monsoon_group_B_metadata.csv"
BASE_NPZ = BASE / "established_monsoon_group_B_baseline.npz"
LOG_NPZ = BASE / "established_monsoon_group_B_log_sensitivity.npz"
ASSIGN = ROOT / "results/tables/07_clustering/assignments/established_monsoon_fixed_cluster_assignments.csv"

PREP = ROOT / "src/06_feature_engineering/prepare_established_monsoon_group_b_m3.py"
EXPORT = ROOT / "src/07_clustering/established_monsoon_export_fixed_assignments.py"

report = []
checks = []
models = {}
results = {}

def log(s):
    print(s)
    report.append(str(s))

def check(name, passed, detail=""):
    checks.append({"check": name, "passed": bool(passed), "detail": str(detail)})
    log(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

log("="*72)
log("ESTABLISHED MONSOON MODEL RECOVERY REPORT")
log("="*72)
log(f"Python: {os.sys.version}")
log(f"NumPy: {np.__version__}")
log(f"Pandas: {pd.__version__}")
log(f"Scikit-learn: {sklearn.__version__}")
log(f"Joblib: {joblib.__version__}")

# ------------------------------------------------
# 3. Load original artifacts
# ------------------------------------------------

metadata = pd.read_csv(META)
assignments = pd.read_csv(ASSIGN)

with np.load(BASE_NPZ, allow_pickle=False) as z:
    X_base = z["X"].copy()
    features_base = z["features"].astype(str).tolist()

with np.load(LOG_NPZ, allow_pickle=False) as z:
    X_log = z["X"].copy()
    features_log = z["features"].astype(str).tolist()

check("Metadata rows", len(metadata) == 290355, len(metadata))
check("Assignment rows", len(assignments) == 290355, len(assignments))
check("Baseline dimensions", X_base.shape == (290355,14), X_base.shape)
check("Log dimensions", X_log.shape == (290355,14), X_log.shape)
check("Feature order", features_base == features_log, features_base)
check("Finite baseline matrix", np.isfinite(X_base).all())
check("Finite log matrix", np.isfinite(X_log).all())

key = ["year", "date", "latitude", "longitude"]

for df in (metadata, assignments):
    df["year"] = pd.to_numeric(df["year"])
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["latitude"] = pd.to_numeric(df["latitude"])
    df["longitude"] = pd.to_numeric(df["longitude"])

check(
    "Metadata-assignment row alignment",
    metadata[key].equals(assignments[key])
)

# ------------------------------------------------
# 4. Search for original serialized artifacts
# ------------------------------------------------

log("\nSERIALIZED MODEL SEARCH")

extensions = {".joblib", ".pkl", ".pickle", ".sav", ".model"}

found = []
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    if any(part.lower() in {".git", ".venv", "venv", "node_modules"} for part in p.parts):
        continue
    if p.suffix.lower() in extensions:
        found.append(str(p.relative_to(ROOT)))

if found:
    for f in found:
        log("FOUND: " + f)
else:
    log("No recognized serialized estimator/scaler files found.")

# ------------------------------------------------
# 5. Inspect original source configuration
# ------------------------------------------------

prep_text = PREP.read_text(encoding="utf-8")
export_text = EXPORT.read_text(encoding="utf-8")

log("\nORIGINAL SOURCE CONFIGURATION")
for token in [
    "StandardScaler", "np.log1p", "baseline_scaler",
    "log_scaler", "baseline_matrix", "log_sensitivity_matrix"
]:
    check("Preprocessing source: " + token, token in prep_text)

for token in [
    "MiniBatchKMeans", "random_state=SEED", "batch_size=4096",
    "n_init=10", "max_iter=200", "reassignment_ratio=0.01"
]:
    check("Exporter source: " + token, token in export_text)

# ------------------------------------------------
# 6. Reconstruct candidate fitted models
# ------------------------------------------------

log("\nMODEL RECONSTRUCTION")

candidates = [
    ("baseline_k2", X_base, 2, "baseline_k2"),
    ("log_k2", X_log, 2, "log_k2"),
    ("log_k3", X_log, 3, "log_k3"),
]

for name, X, k, assignment_column in candidates:
    log(f"\nReconstructing {name}")

    model = MiniBatchKMeans(
        n_clusters=k,
        random_state=11,
        batch_size=4096,
        n_init=10,
        max_iter=200,
        reassignment_ratio=0.01
    )

    model.fit(X)
    predicted = model.predict(X)
    original = assignments[assignment_column].to_numpy(dtype=int)

    # Cluster numbers are arbitrary. Compare partitions using
    # contingency table and adjusted Rand index.
    from sklearn.metrics import adjusted_rand_score

    ari = adjusted_rand_score(original, predicted)

    # Exact label equality is stricter than partition equality.
    exact = np.array_equal(original, predicted)

    # Compare partition equality independently of numeric labels.
    partition_equal = ari == 1.0

    check(
        name + " partition reproduction",
        partition_equal,
        f"ARI={ari:.12f}; exact numeric labels={exact}"
    )

    results[name] = {
        "ARI": float(ari),
        "exact_label_match": bool(exact),
        "partition_match": bool(partition_equal),
        "original_counts": {
            str(int(k)): int(v)
            for k, v in zip(*np.unique(original, return_counts=True))
        },
        "predicted_counts": {
            str(int(k)): int(v)
            for k, v in zip(*np.unique(predicted, return_counts=True))
        }
    }

    models[name] = model

    # Save candidate separately, clearly marked as reconstructed.
    model_path = OUT / f"RECONSTRUCTED_{name}.joblib"
    joblib.dump(model, model_path)

    log(f"Candidate saved: {model_path}")

    # Save comparison predictions separately.
    pd.DataFrame({
        "original_assignment": original,
        "reconstructed_prediction": predicted
    }).to_csv(
        OUT / f"RECONSTRUCTED_{name}_prediction_comparison.csv",
        index=False
    )

# ------------------------------------------------
# 7. Scaler recoverability investigation
# ------------------------------------------------

log("\nSCALER RECOVERY")

scaler_results = {}

for name, X in [
    ("baseline", X_base),
    ("log_sensitivity", X_log)
]:
    means = X.mean(axis=0)
    stds = X.std(axis=0, ddof=0)

    # Standardized matrices cannot reveal the original means
    # and scales of the raw input data.
    # Fit-on-standardized-data would produce approximately
    # identity transformation, NOT the original scaler.
    scaler_results[name] = {
        "matrix_mean": means.tolist(),
        "matrix_std": stds.tolist(),
        "original_scaler_recovered": False
    }

    check(
        name + " matrix standardized",
        np.allclose(means, 0, atol=1e-5) and
        np.allclose(stds, 1, atol=1e-5),
        "Means approximately zero; standard deviations approximately one"
    )

log(
    "Original scaler parameters cannot be reconstructed from standardized "
    "matrices alone. Raw pre-scaling feature data is required."
)

# ------------------------------------------------
# 8. Search for raw feature data
# ------------------------------------------------

log("\nRAW DATA SEARCH")

raw_candidates = []
for p in (ROOT / "data").rglob("*"):
    if not p.is_file():
        continue
    if p.suffix.lower() in {".csv", ".parquet", ".feather", ".pkl"}:
        if "metadata" not in p.name.lower() and "assignment" not in p.name.lower():
            raw_candidates.append(str(p.relative_to(ROOT)))

for p in raw_candidates[:100]:
    log("Possible raw data: " + p)

log(f"Possible tabular files found: {len(raw_candidates)}")

# ------------------------------------------------
# 9. Verify model prediction reproducibility
# ------------------------------------------------

log("\nMODEL VERIFICATION SUMMARY")

all_partition_match = all(
    v["partition_match"] for v in results.values()
)

all_exact_match = all(
    v["exact_label_match"] for v in results.values()
)

check(
    "All three reconstructed partitions match",
    all_partition_match
)

check(
    "All three numeric cluster labels match exactly",
    all_exact_match
)

# ------------------------------------------------
# 10. Save provenance and audit report
# ------------------------------------------------

manifest = {
    "project": "Established Monsoon",
    "artifact_type": "Reconstructed candidate models",
    "warning": (
        "These are newly reconstructed estimators, not verified original "
        "serialized fitted estimators."
    ),
    "random_state": 11,
    "batch_size": 4096,
    "n_init": 10,
    "max_iter": 200,
    "reassignment_ratio": 0.01,
    "results": results,
    "scalers": scaler_results,
    "all_partition_match": bool(all_partition_match),
    "all_exact_label_match": bool(all_exact_match),
    "checks": checks,
    "input_sha256": {
        str(p.relative_to(ROOT)): sha256(p)
        for p in [META, BASE_NPZ, LOG_NPZ, ASSIGN, PREP, EXPORT]
    }
}

with open(OUT / "recovery_manifest.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

with open(OUT / "recovery_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report))

# ------------------------------------------------
# 11. Final status
# ------------------------------------------------

log("\n" + "="*72)
log("FINAL RECOVERY STATUS")
log("="*72)

passed = sum(x["passed"] for x in checks)
failed = sum(not x["passed"] for x in checks)

log(f"Checks passed: {passed}")
log(f"Checks failed: {failed}")
log(f"Reconstructed model partitions match: {all_partition_match}")
log(f"Exact cluster labels match: {all_exact_match}")
log("Original scalers recovered: NO — raw pre-scaling data required.")
log("Original fitted estimators verified: NO — candidates are reconstructions.")
log(f"Output folder: {OUT}")

log("\nIMPORTANT:")
log("Do not replace original assignments with reconstructed predictions.")
log("Do not describe reconstructed estimators as original fitted models.")
log("Review recovery_manifest.json before using any candidate model.")

with open(OUT / "recovery_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print("\nRecovery investigation completed.")
