# M19 — Post-monsoon data integrity audit

This package adds a reproducible, read-only integrity audit for post-monsoon CERES, IMD rainfall, and NOAA RONI/DMI source files. It is designed for the isolated `feature/post-monsoon-analysis` worktree. It does not copy, rewrite, interpolate, regrid, or delete raw data.

## Important scope

- Study years: 2010–2021.
- CERES period: October 15–November 13; 720 hourly observations/year; expected 32×30 grid and 45 data variables.
- CERES timestamps are near the half-hour and can contain seconds-level encoding jitter. The audit checks order, uniqueness, date coverage, hourly spacing within tolerance, and count. It does not require exact `HH:00` timestamps.
- IMD is audited on its own native daily grid. Coordinate intersections must be used for later joins; array-index matching is prohibited.
- RONI seasonal windows remain rolling three-month observations. DMI `-9999` is counted as a missing sentinel. No climate index values are imputed.
- The processed climate CSVs are recorded as reconciliation targets; this first audit deliberately does not claim numerical source-to-processed equivalence without an explicit verified mapping.

## Install

From the isolated worktree root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-m19.txt
```

## Configure

Edit `config/m19_post_monsoon_audit.json` only if your actual project/data locations differ. The default paths are based on the source layout inspected for M19. Keep `project_root` pointing to `D:/Project Simulator/monsoon_cloud_research`; keep `output_dir` pointing to the M19 review package. Raw data remains in the original project tree.

## Run all verification together

```powershell
python -m pytest -q tests/test_m19_audit.py
if ($LASTEXITCODE -ne 0) { throw "M19 unit tests failed; audit not run." }
python src/02_validation/m19/audit.py --config config/m19_post_monsoon_audit.json
$AuditExit = $LASTEXITCODE
Write-Host "M19 audit exit code: $AuditExit"
if ($AuditExit -eq 0) { Write-Host "Readiness passed." } elseif ($AuditExit -eq 2) { Write-Warning "Audit completed, but readiness is blocked. Review the generated FAIL / NOT EVALUATED checks." } else { throw "M19 audit execution error." }
```

Exit code 0 means all required source families met the current readiness rules. Exit code 2 means the audit completed but readiness is blocked. Exit code 1 means execution failed.

## Outputs

The configured output directory receives:

- `M19_integrity_summary.json`
- `M19_file_validation.csv`
- `M19_timestamp_validation.csv`
- `M19_spatial_validation.csv`
- `M19_variable_validation.csv`
- `M19_supporting_data_validation.csv`
- `M19_errors.json`
- `M19_final_readiness_report.md`

Each check uses `PASS`, `FAIL`, or `NOT EVALUATED`; absent source data is never silently treated as a pass. The unit tests are intentionally fast and do not replace running the audit against the actual local NetCDF and NOAA files.

## Current implementation boundary

The audit validates CERES and IMD source structure and data arrays, and performs first-pass structural checks on original RONI/DMI sources. It does not yet perform cloud–rainfall association, rainfall-to-CERES cell matching, or climate-index statistical association. Those belong to the downstream analysis stage after integrity is established.
