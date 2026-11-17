
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DMI_INPUT = PROJECT_ROOT / "data/raw/NOAA_DMI/dmi.had.long.csv"
RONI_INPUT = PROJECT_ROOT / "data/raw/NOAA_RONI/RONI.ascii.txt"

DMI_OUTPUT = (
    PROJECT_ROOT
    / "data/processed/climate_indices/DMI/dmi_monthly_2010_2021.csv"
)

RONI_OUTPUT = (
    PROJECT_ROOT
    / "data/processed/climate_indices/RONI/roni_seasonal_2010_2021.csv"
)

REPORT_OUTPUT = (
    PROJECT_ROOT
    / "reports/preprocessing/climate_indices_validation.md"
)

START_YEAR = 2010
END_YEAR = 2021

EXPECTED_MONTHS = 12
EXPECTED_SEASONS = [
    "DJF", "JFM", "FMA", "MAM",
    "AMJ", "MJJ", "JJA", "JAS",
    "ASO", "SON", "OND", "NDJ"
]


def prepare_dmi():
    if not DMI_INPUT.exists():
        raise FileNotFoundError(DMI_INPUT)

    dmi = pd.read_csv(DMI_INPUT, skipinitialspace=True)

    if len(dmi.columns) != 2:
        raise ValueError(
            f"Unexpected DMI columns: {list(dmi.columns)}"
        )

    dmi.columns = ["date", "dmi"]

    dmi["date"] = pd.to_datetime(
        dmi["date"], errors="coerce"
    )

    dmi["dmi"] = pd.to_numeric(
        dmi["dmi"], errors="coerce"
    )

    dmi.loc[dmi["dmi"] == -9999, "dmi"] = pd.NA

    if dmi["date"].isna().any():
        raise ValueError("DMI contains invalid dates.")

    if dmi["date"].duplicated().any():
        raise ValueError("DMI contains duplicate dates.")

    if not dmi["date"].dt.day.eq(1).all():
        raise ValueError(
            "DMI dates are not consistently month-start dates."
        )

    dmi = dmi[
        dmi["date"].dt.year.between(START_YEAR, END_YEAR)
    ].copy()

    dmi = dmi.sort_values("date").reset_index(drop=True)

    expected_count = (
        (END_YEAR - START_YEAR + 1) * EXPECTED_MONTHS
    )

    if len(dmi) != expected_count:
        raise ValueError(
            f"Expected {expected_count} DMI records, "
            f"found {len(dmi)}."
        )

    if dmi["dmi"].isna().any():
        raise ValueError(
            "Missing DMI values found in study period."
        )

    monthly_counts = dmi.groupby(
        dmi["date"].dt.year
    ).size()

    if not monthly_counts.eq(EXPECTED_MONTHS).all():
        raise ValueError(
            "DMI does not contain 12 records for every year."
        )

    return dmi


def prepare_roni():
    if not RONI_INPUT.exists():
        raise FileNotFoundError(RONI_INPUT)

    roni = pd.read_csv(
        RONI_INPUT,
        sep=r"\s+",
        engine="python"
    )

    expected_columns = ["SEAS", "YR", "ANOM"]

    if list(roni.columns) != expected_columns:
        raise ValueError(
            f"Unexpected RONI columns: {list(roni.columns)}"
        )

    roni["SEAS"] = roni["SEAS"].astype(str).str.strip()
    roni["YR"] = pd.to_numeric(
        roni["YR"], errors="coerce"
    )
    roni["ANOM"] = pd.to_numeric(
        roni["ANOM"], errors="coerce"
    )

    if roni.isna().any().any():
        raise ValueError("RONI contains missing or invalid values.")

    if not roni["YR"].mod(1).eq(0).all():
        raise ValueError("RONI contains non-integer years.")

    roni["YR"] = roni["YR"].astype(int)

    if not roni["SEAS"].isin(EXPECTED_SEASONS).all():
        raise ValueError("RONI contains unexpected season labels.")

    if roni.duplicated(["YR", "SEAS"]).any():
        raise ValueError(
            "RONI contains duplicate year-season records."
        )

    roni = roni[
        roni["YR"].between(START_YEAR, END_YEAR)
    ].copy()

    roni["season_order"] = roni["SEAS"].map(
        {season: i for i, season in enumerate(EXPECTED_SEASONS)}
    )

    roni = (
        roni.sort_values(["YR", "season_order"])
        .drop(columns="season_order")
        .reset_index(drop=True)
    )

    expected_count = (
        (END_YEAR - START_YEAR + 1) * EXPECTED_MONTHS
    )

    if len(roni) != expected_count:
        raise ValueError(
            f"Expected {expected_count} RONI records, "
            f"found {len(roni)}."
        )

    seasonal_counts = roni.groupby("YR").size()

    if not seasonal_counts.eq(EXPECTED_SEASONS.__len__()).all():
        raise ValueError(
            "RONI does not contain all 12 seasonal records per year."
        )

    return roni


def generate_report(dmi, roni):
    lines = [
        "# NOAA Climate Indices Preparation and Validation",
        "",
        "## Study period",
        "",
        f"- Start year: {START_YEAR}",
        f"- End year: {END_YEAR}",
        "",
        "## DMI validation",
        "",
        "- Source: NOAA PSL DMI HadISST1.1",
        "- Temporal resolution: Monthly",
        "- Original missing marker: -9999",
        f"- Processed records: {len(dmi)}",
        f"- Missing values: {dmi['dmi'].isna().sum()}",
        f"- Duplicate dates: {dmi['date'].duplicated().sum()}",
        f"- First date: {dmi['date'].min().date()}",
        f"- Last date: {dmi['date'].max().date()}",
        f"- Minimum DMI: {dmi['dmi'].min():.3f}",
        f"- Maximum DMI: {dmi['dmi'].max():.3f}",
        f"- Mean DMI: {dmi['dmi'].mean():.3f}",
        "",
        "## RONI validation",
        "",
        "- Source: NOAA RONI",
        "- Temporal resolution: Overlapping three-month seasons",
        f"- Processed records: {len(roni)}",
        f"- Missing values: {roni.isna().sum().sum()}",
        f"- Duplicate year-season records: "
        f"{roni.duplicated(['YR', 'SEAS']).sum()}",
        f"- First year: {roni['YR'].min()}",
        f"- Last year: {roni['YR'].max()}",
        f"- Minimum RONI: {roni['ANOM'].min():.3f}",
        f"- Maximum RONI: {roni['ANOM'].max():.3f}",
        f"- Mean RONI: {roni['ANOM'].mean():.3f}",
        "",
        "## Methodological notes",
        "",
        "- Original source files remain unchanged.",
        "- DMI values are retained as monthly continuous anomalies.",
        "- RONI values are retained as overlapping three-month "
        "continuous anomalies.",
        "- Both outputs are restricted to 2010-2021.",
        "- No ENSO or IOD categories are assigned at this stage.",
        "- No climate indices are included in the CERES clustering "
        "feature matrix.",
        "- Climate indices will be aligned with cloud-regime results "
        "during the subsequent climate-association analysis.",
        "",
        "## Validation result",
        "",
        "**PASS:** Both datasets passed the implemented structural "
        "and study-period validation checks.",
        "",
    ]

    REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )


def main():
    print("Preparing NOAA DMI...")
    dmi = prepare_dmi()

    print("Preparing NOAA RONI...")
    roni = prepare_roni()

    DMI_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    RONI_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    dmi.to_csv(DMI_OUTPUT, index=False)
    roni.to_csv(RONI_OUTPUT, index=False)

    generate_report(dmi, roni)

    print("\n========== PREPARATION COMPLETE ==========")
    print(f"DMI records: {len(dmi)}")
    print(f"RONI records: {len(roni)}")
    print(f"DMI output: {DMI_OUTPUT}")
    print(f"RONI output: {RONI_OUTPUT}")
    print(f"Validation report: {REPORT_OUTPUT}")


if __name__ == "__main__":
    main()
