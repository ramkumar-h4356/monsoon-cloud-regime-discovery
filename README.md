# Pre-monsoon CERES cloud-property workflow

The completed workflow covers April 15-May 14, 2010-2021. The final scientific
model was fitted on 70,000 sampled cloudy observations from 2010-2016;
2017-2018 was development and 2019-2021 the reserved temporal evaluation.
The fixed inputs are cloud area /100, log1p optical depth, and cloud-top
pressure. Three PCs and k=2 were retained. PCA did **not** reduce the three
input dimensions. These are descriptive cloud-property partitions, not
independently validated meteorological cloud types.

Start with the additive [final handoff addendum](reports/handoff/remediation_v1/report/SCIENTIFIC_HANDOFF.md),
[remediation test log](reports/handoff/remediation_v1/tests/all_tests.txt), and
[historical integrity receipt](reports/handoff/remediation_v1/verify/receipt.json).
These supplement the immutable research record below.

Phase 1 already explored all years, including availability/correlations that
informed feature choice. The holdout was reserved from Phase 2 fitting/tuning;
it was not historically untouched confirmatory data. This limitation cannot
be removed by repackaging or rerunning the same holdout.

## Immutable research record

- `reports/phase2/pre_monsoon/stage2_review.md`: development results and caveats.
- `reports/phase3/pre_monsoon/stage3_v1/scientific_report.md`: original final report.
- `reports/phase3/pre_monsoon/stage3_v1/freeze/`: pre-access protocol, parameter
  values, training-only thresholds, feature definitions, selection evidence and seal.
- `results/models/phase2/pre_monsoon/stage2_v1/selected_pre_monsoon_bundle.joblib`:
  unchanged training-only model. Load only trusted local joblib artifacts.
- `reports/phase3/pre_monsoon/stage3_v1/evaluation/`: metrics, original-unit
  profiles, sample memberships and temporal/spatial/uncertainty tables.
- `data/processed/model_ready/phase3/pre_monsoon/stage3_v1/`: three annual label files.

Do not edit historical files to improve a score or fix an old report. The
seal checks historical code/configuration bytes as well as models and results.
The additive remediation is under `src/10_handoff`, `environment`, and
`reports/handoff`. Old evaluation entry points are retained as historical
evidence, including their documented empty-support limitation. They are not
called by the new handoff CLI.

## Environment and fresh-machine handoff

The exact reference is 64-bit Windows with CPython 3.13.7. The complete
31-distribution version lock (including active transitive dependencies and
packaging tools) is `environment/requirements-windows-py313.lock`.
`environment/environment-reference.json` also records dependency metadata.
Historical `requirements-stage1.txt` and `requirements-stage2.txt` are unchanged.

From a fresh **byte-preserving copy** of the handoff, with CPython 3.13.7
installed, create a separate environment (commands are not needed in the
existing reference environment):

```powershell
py -3.13 -m venv data/handoff_env
& 'data/handoff_env/Scripts/python.exe' -m pip install -r environment/requirements-windows-py313.lock
& 'data/handoff_env/Scripts/python.exe' -B src/10_handoff/handoff.py environment
```

This lock does not include wheel hashes or an offline wheelhouse. A fresh
network installation was not performed during remediation. Matching active
dependency closure and `pip check` were verified in the installed reference
environment; cross-platform/bitwise equivalence is not promised.

The copy must include ignored models, prepared datasets/labels, original
reports, manifests and source files. A Git checkout alone is insufficient:
`data/` and large model artifacts are ignored, and research additions are
currently uncommitted. Preserve original bytes/line endings or the original
hashes will intentionally fail. Archive transfer or Git publication needs
separate approval. No raw-data download is required for the artifact-only
commands below; they may hash scientific file bytes but never open NetCDF
arrays or refit/predict a model. Source-data reconstruction has separate
historical scripts and is not an authorized handoff action.

## Artifact-only CLI, with independent input/output IDs

Run from the repository root using the existing parent environment:

```powershell
# Read-only: verify historical results/model/source hashes.
& '..\.venv\Scripts\python.exe' -B src/10_handoff/handoff.py verify --run-id stage3_v1
& '..\.venv\Scripts\python.exe' -B src/10_handoff/handoff.py environment

# New outputs only: use any unused output ID; the input run is unchanged.
& '..\.venv\Scripts\python.exe' -B src/10_handoff/handoff.py plot --run-id stage3_v1 --output-id delivery_001
& '..\.venv\Scripts\python.exe' -B src/10_handoff/handoff.py report --run-id stage3_v1 --output-id delivery_001 --test-log reports/handoff/remediation_v1/tests/all_tests.txt
```

`--root <path>` is a global option and precedes the command when using a
different byte-preserving repository copy. Outputs are restricted to
`reports/handoff/<output-id>/<command>/`. Each command refuses an existing
output directory; plot/report output IDs are required. There is no overwrite,
fit, selection or evaluation command. Existing run IDs in historical
reproduction snippets are intentionally refused by the historical writers.
The new commands reproduce handoff presentation/verification without rerunning
those writers. Optional `--baseline <repository-relative inventory.json>` also
checks a pre-remediation inventory; optional `--output-id` on verify/environment
saves a new receipt rather than only printing it.

## Tests and prospective empty-safe API

```powershell
# Full suite: fits only synthetic fixtures, never the real holdout model.
& '..\.venv\Scripts\python.exe' -B -m unittest discover -s tests -v
# Targeted remediation tests.
& '..\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p test_handoff_v2.py -v
```

Capture unittest stdout/stderr and its process exit status when producing a
new test receipt. The new report parser accepts the actual passing test count;
it does not assume the historical count of 25. The real remediation receipt
is `reports/handoff/remediation_v1/tests/all_tests.txt`.

`src/10_handoff/robust_diagnostics_v2.py` is a versioned prospective API:

- `evaluate_period_v2`: never transforms/predicts when there are no eligible
  rows; retains clear/unavailable labels and explicit undefined metrics.
- `population_diagnostics_v2`: preserves all-cell denominators for all-clear,
  all-unavailable and zero-time periods; no divisions by zero.
- `distance_summary` and `pc_summary`: no empty-array quantiles or singleton
  variance claims.
- `physical_profiles_v2`: retains absent clusters, missing retrievals, original
  units and denominators as explicit rows instead of fabricated zeros.
- `bootstrap_fractions_v2`: retains unsupported predeclared block lengths as
  undefined; does not shorten/select blocks based on support or results.

Positive-support compatibility is tested against the historical functions.
This API was tested on synthetic periods only. It is not patched into the
sealed legacy evaluator, and completed holdout results were not regenerated.
Integrating it into any future full evaluation requires a new version and
approved protocol. That boundary preserves the original scientific record.

## Interpretation and remaining limitations

The post-evaluation handoff addendum qualifies the historical broad
`code_frozen_before_holdout` flag: the **evaluation/model-analysis code** was
frozen; later presentation and completion helpers have separate hashes.
It explicitly reports the slightly lower pooled holdout silhouette and
Calinski-Harabasz values and the slightly more favorable Davies-Bouldin value.
No equivalence, trend, causal or classification-accuracy claim follows.

Physical profiles are sampled, with substantial phase-dependent water-path
availability. Clear sky remains separate. Internal indices favor a geometry;
five year bootstraps and three holdout years limit inference. Bootstrap
intervals are within-window, not interannual climate CIs. Other seasons share
the feature contract but require separate fitted objects and live audits.
No independent external supervisor rubric was supplied; the handoff checklist
maps the requirements provided in the conversation. Stronger meteorological
validation requires independent evidence, not tuning on the revealed holdout.
