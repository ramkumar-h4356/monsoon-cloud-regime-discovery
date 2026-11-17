# NOAA Climate Indices Preparation and Validation

## Study period

- Start year: 2010
- End year: 2021

## DMI validation

- Source: NOAA PSL DMI HadISST1.1
- Temporal resolution: Monthly
- Original missing marker: -9999
- Processed records: 144
- Missing values: 0
- Duplicate dates: 0
- First date: 2010-01-01
- Last date: 2021-12-01
- Minimum DMI: -0.757
- Maximum DMI: 0.964
- Mean DMI: 0.087

## RONI validation

- Source: NOAA RONI
- Temporal resolution: Overlapping three-month seasons
- Processed records: 144
- Missing values: 0
- Duplicate year-season records: 0
- First year: 2010
- Last year: 2021
- Minimum RONI: -1.630
- Maximum RONI: 2.250
- Mean RONI: -0.207

## Methodological notes

- Original source files remain unchanged.
- DMI values are retained as monthly continuous anomalies.
- RONI values are retained as overlapping three-month continuous anomalies.
- Both outputs are restricted to 2010-2021.
- No ENSO or IOD categories are assigned at this stage.
- No climate indices are included in the CERES clustering feature matrix.
- Climate indices will be aligned with cloud-regime results during the subsequent climate-association analysis.

## Validation result

**PASS:** Both datasets passed the implemented structural and study-period validation checks.
