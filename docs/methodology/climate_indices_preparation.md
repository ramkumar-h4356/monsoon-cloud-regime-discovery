# Climate Index Preparation

## Objective
Prepare NOAA DMI and RONI datasets for climate-context analysis
of cloud regimes over the 2010–2021 study period.

## Data sources
- DMI: NOAA PSL, HadISST1.1, monthly observations.
- RONI: NOAA, overlapping three-month seasonal observations.

## Processing
- Original source files are preserved unchanged.
- DMI missing marker (-9999) is converted to missing data.
- DMI is restricted to January 2010–December 2021.
- RONI is restricted to 2010–2021.
- Continuous index values are retained.
- No climate categories or clustering features are generated
  during this preparation stage.

## Validation
- DMI: 144 monthly records, zero missing values,
  zero duplicate dates.
- RONI: 144 seasonal records, 12 per year,
  zero missing values, zero duplicate year-season records.
- Both datasets passed independent structural validation.

## Research integration
DMI represents Indian Ocean Dipole context.
RONI represents ENSO context.
Both indices will be associated with discovered cloud regimes
after clustering. Neither is an input to the CERES clustering model.

## Temporal alignment
DMI and RONI retain their native temporal resolutions.
Alignment with each seasonal study window will be documented
during the climate-association analysis.
