from pathlib import Path
import json
import re
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SCREENING_REPORT = (
    ROOT / "reports" / "data_quality" /
    "ceres_feature_screening_summary.csv"
)
OUTPUT_DIR = ROOT / "reports" / "feature_engineering"

EXPECTED_CANDIDATES = 36
ELIGIBLE_STATUS = "ELIGIBLE_CANDIDATE"

BASE_FAMILIES = ("cldarea_", "cldtau_", "lwp_", "iwp_")


def family_of(variable):
    """Classify variable names, checking cloud-top pressure before pressure."""
    ordered = (
        ("cldpress_top_", "cloud_top_pressure"),
        ("cldarea_", "cloud_area"),
        ("cldtau_", "optical_depth"),
        ("cldhght_", "effective_height"),
        ("cldpress_", "effective_pressure"),
        ("cldtemp_", "effective_temperature"),
        ("lwp_", "liquid_water_path"),
        ("iwp_", "ice_water_path"),
    )
    for prefix, family in ordered:
        if variable.startswith(prefix):
            return family
    return "unclassified"


def layer_from_name(variable):
    """Extract layer token from supported CERES variable naming patterns."""
    match = re.search(
        r"_(total|high|mid_high|mid_low|low)_1h$",
        variable
    )
    return match.group(1) if match else None


def feature_set_membership(variable):
    """Return deterministic membership for FS-A through FS-F."""
    family = family_of(variable)
    base = family in {
        "cloud_area",
        "optical_depth",
        "liquid_water_path",
        "ice_water_path",
    }

    membership = {
        "FS-A": True,
        "FS-B": base or family == "effective_height",
        "FS-C": base or family == "effective_pressure",
        "FS-D": base or family == "effective_temperature",
        "FS-E": base,
        "FS-F": base or family == "cloud_top_pressure",
    }
    return membership


def validate_columns(df):
    required = {"variable", "status", "vertical_layer"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            "Screening report is missing required columns: "
            + ", ".join(sorted(missing))
        )


def main():
    if not SCREENING_REPORT.exists():
        raise FileNotFoundError(
            f"Required screening report not found: {SCREENING_REPORT}"
        )

    df = pd.read_csv(SCREENING_REPORT)
    validate_columns(df)

    eligible = df.loc[
        df["status"].astype(str).str.strip().eq(ELIGIBLE_STATUS)
    ].copy()

    if eligible["variable"].isna().any():
        raise ValueError("Eligible candidate list contains blank variable names.")

    eligible["variable"] = eligible["variable"].astype(str).str.strip()

    duplicates = eligible["variable"].duplicated(keep=False)
    if duplicates.any():
        names = sorted(eligible.loc[duplicates, "variable"].unique())
        raise ValueError(f"Duplicate eligible variable names: {names}")

    if len(eligible) != EXPECTED_CANDIDATES:
        raise ValueError(
            f"Expected {EXPECTED_CANDIDATES} eligible candidates, "
            f"found {len(eligible)}. Review the screening report before proceeding."
        )

    rows = []
    issues = []

    for _, record in eligible.iterrows():
        variable = record["variable"]
        family = family_of(variable)
        name_layer = layer_from_name(variable)
        report_layer = (
            str(record["vertical_layer"]).strip()
            if pd.notna(record["vertical_layer"])
            else ""
        )

        if family == "unclassified":
            issues.append(f"Unclassified variable family: {variable}")

        if name_layer is None:
            issues.append(f"Could not infer layer from variable name: {variable}")

        if report_layer and name_layer and report_layer != name_layer:
            issues.append(
                f"Layer mismatch for {variable}: "
                f"report={report_layer}, name={name_layer}"
            )

        membership = feature_set_membership(variable)

        matching_area = (
            f"cldarea_{name_layer}_1h"
            if name_layer and family not in {"cloud_area"}
            else ""
        )

        rows.append({
            "variable": variable,
            "family": family,
            "layer_from_name": name_layer or "",
            "screening_vertical_layer": report_layer,
            "matching_cloud_area_variable": matching_area,
            **membership,
        })

    registry = pd.DataFrame(rows)

    candidate_names = set(registry["variable"])
    area_names = set(
        registry.loc[
            registry["family"].eq("cloud_area"), "variable"
        ]
    )

    # Validate matching cloud-area names against the eligible pool.
    for row in registry.itertuples(index=False):
        area_var = row.matching_cloud_area_variable
        if area_var and area_var not in area_names:
            issues.append(
                f"{row.variable} maps to {area_var}, "
                "which is not in the eligible cloud-area candidate pool."
            )

    set_definitions = {}
    for set_id in ("FS-A", "FS-B", "FS-C", "FS-D", "FS-E", "FS-F"):
        selected = registry.loc[registry[set_id], "variable"].tolist()
        families = (
            registry.loc[registry[set_id], "family"]
            .value_counts()
            .sort_index()
            .to_dict()
        )
        set_definitions[set_id] = {
            "feature_count": len(selected),
            "variables": selected,
            "family_counts": families,
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    registry_path = OUTPUT_DIR / "feature_set_registry.csv"
    definitions_path = OUTPUT_DIR / "feature_set_definitions.json"
    validation_path = OUTPUT_DIR / "feature_set_registry_validation.json"

    registry.to_csv(registry_path, index=False)

    definitions = {
        "specification": "M18 feature-set registry",
        "source": str(SCREENING_REPORT.relative_to(ROOT)),
        "eligible_candidate_count": len(eligible),
        "feature_sets": set_definitions,
        "notes": [
            "FS-A through FS-F are candidate experiment definitions, not final selections.",
            "Cloud-phase variables are not included in this continuous-feature registry.",
            "Feature family classification is based on CERES variable prefixes.",
            "Layer mappings are checked against both variable names and screening report metadata.",
            "A cloud-area match is expected only where the corresponding layer cloud-area variable is part of the eligible candidate pool."
        ],
    }

    with open(definitions_path, "w", encoding="utf-8") as f:
        json.dump(definitions, f, indent=2)

    validation = {
        "source_report_exists": True,
        "eligible_candidates_expected": EXPECTED_CANDIDATES,
        "eligible_candidates_found": len(eligible),
        "duplicate_variable_names": False,
        "unclassified_variables": int(
            registry["family"].eq("unclassified").sum()
        ),
        "feature_set_counts": {
            key: value["feature_count"]
            for key, value in set_definitions.items()
        },
        "issues": issues,
        "passed": len(issues) == 0,
        "interpretation": (
            "A passed registry validates names, family classification and "
            "declared layer mappings. It does not validate scientific suitability, "
            "missing-data treatment, or clustering performance."
        ),
    }

    with open(validation_path, "w", encoding="utf-8") as f:
        json.dump(validation, f, indent=2)

    print("\nFEATURE-SET REGISTRY")
    print("--------------------")
    for set_id, details in set_definitions.items():
        print(f"{set_id}: {details['feature_count']} features")

    print("\nVALIDATION")
    print(json.dumps(validation, indent=2))

    print("\nOUTPUTS")
    print(registry_path)
    print(definitions_path)
    print(validation_path)

    if issues:
        print(
            "\nRegistry generated with validation issues. "
            "Do not proceed to model-ready matrix creation."
        )
        sys.exit(2)

    print("\nRegistry validation passed.")


if __name__ == "__main__":
    main()
