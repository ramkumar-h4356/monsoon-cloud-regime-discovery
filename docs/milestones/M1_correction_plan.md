# M1 — Correction Plan and Handoff to M2

## Operating rules

- Repository: `monsoon-cloud-regime-discovery`
- Working branch: `feature/established-monsoon-analysis`
- Never switch branches, merge, commit or push without explicit authorization.
- Preserve modified and untracked work.
- Do not overwrite existing outputs; use explicit output paths and fail safely if outputs already exist.
- Do not include raw or processed NetCDF files or large intermediate data in Git.
- Use local PowerShell execution for dataset-backed validation; share compact reports for review.

## M2 work packages

### M2.1 Fresh local-state capture

From the project root, capture:

```powershell
git branch --show-current
git status --short --branch
git diff -- src/03_preprocessing/prepare_established_monsoon_rainfall.py src/07_clustering/established_monsoon_rainfall_alignment_audit.py src/04_aggregation/established_monsoon_daily_aggregation.py
git ls-files
```

Also identify whether local `tests/`, `requirements.txt`, `pyproject.toml`, `environment.yml`, README and configuration files exist but were omitted from the source archive.

### M2.2 Rainfall source validation

Review and add explicit checks, where supported by the source data:
- latitude/longitude coordinates are present, numeric and finite;
- coordinate values are unique and ordered consistently;
- time coordinates are valid, unique, ordered and normalized to daily dates;
- expected year and 30-day seasonal window agree;
- rainfall variable and dimensions are unambiguous;
- units are explicitly validated and normalized only through an approved conversion rule;
- negative finite rainfall and infinite values are rejected or explicitly handled;
- missing rainfall remains missing and is not silently imputed.

### M2.3 Cloud-assignment validation

Validate:
- required columns and types;
- year/date consistency;
- finite latitude and longitude;
- unique `(year, date, latitude, longitude)` keys;
- valid, documented cluster labels;
- expected date and grid support;
- no unexpected duplicates or invalid records.

### M2.4 Alignment and comparison validation

Use exact key matching on year, date, latitude and longitude. Check merge cardinality and report accepted, rejected, unmatched and missing-rainfall observations separately. Validate pooled, annual, within-cell and period summaries for empty groups, missing cluster-year combinations, non-finite values, minimum support, and consistency with source matched observations. Document unequal period lengths and qualifying support.

### M2.5 Tests and outputs

Add focused tests for duplicate keys, coordinate errors, date errors, invalid labels, negative/infinite rainfall, missing rainfall preservation, empty groups, insufficient support and valid one-to-one alignment. Run unit tests first, then dataset-backed validation locally. Write new reports to new canonical output paths; do not overwrite existing scientific evidence.

## M2 completion evidence

M2 is complete only when:
- targeted automated tests pass;
- the user's local data validation completes successfully;
- accepted/rejected/missing observation counts reconcile;
- annual and pooled summaries reconcile to the matched input;
- support and period limitations are documented;
- no existing data or results were overwritten;
- the user has reviewed the changes before any commit/push.
