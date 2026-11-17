# M19 Post-monsoon Data Integrity Report

**Overall status:** READY FOR DOWNSTREAM ANALYSIS
**Study years:** 2010–2021
**Window:** October 15–November 13 (720 hourly CERES records per year expected)

## Source-family readiness
- CERES: True
- IMD: True
- Climate indices: True

## Check totals
- PASS: 112
- FAIL: 0
- NOT EVALUATED: 0

## Interpretation and limitations
- CERES timestamp checks allow small timestamp-centering jitter; hourly spacing is tested with a configurable tolerance, not exact HH:00 matching.
- CERES metadata valid_min/valid_max checks are reported per variable. A range failure is evidence for review, not automatic data correction.
- IMD coordinates are audited separately. CERES and IMD grids must be joined by coordinate values/intersection, never by array index.
- RONI rolling three-month season labels are preserved; they are not converted into independent monthly observations.
- DMI -9999 values are counted as missing sentinels. No missing climate values are imputed.
- Processed climate CSVs are listed for reconciliation; automatic equality is not claimed unless the source schema mapping is explicitly validated.
- This audit does not regrid, interpolate, overwrite, or modify raw datasets.

## Generated tables
- M19_file_validation.csv
- M19_timestamp_validation.csv
- M19_spatial_validation.csv
- M19_variable_validation.csv
- M19_supporting_data_validation.csv
- M19_errors.json
- M19_integrity_summary.json
