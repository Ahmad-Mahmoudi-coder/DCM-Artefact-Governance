#!/usr/bin/env python3
"""
Independent validator for BiomassSupplyPack v1.0-current.

Authorised by docs/88 sections 7 and 9. Encodings in docs/90.
Checks structural conformity, authorised arithmetic, identity,
record-level provenance, Layer-1/Layer-2 controlled values, and the
structured-field qualification-consumer demonstration.

Does not claim source credibility, exact transcription from unheld
primary reports, extraction fidelity, physical truth of the external
resource estimate, or model re-derivation of that estimate.
Layer 1 is a claim class, not a validation outcome.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    REPO_ROOT
    / "schemas"
    / "artefacts"
    / "biomass_supply_pack.v1.0-current.schema.json"
)
FORMALISED_SUMMARY = (
    REPO_ROOT
    / "Process-Heat-DCM"
    / "Output"
    / "runs"
    / "biomass_supply_screen_formalised_v1"
    / "biomass_supply_screen_summary.csv"
)
EVIDENCE_REGISTER = REPO_ROOT / "references" / "evidence_register.csv"
SOURCE_REGISTER = REPO_ROOT / "references" / "source_register.csv"
TOML_CANDIDATES = (
    REPO_ROOT / "Process-Heat-DCM" / "Input" / "configs" / "biomass_supply_screen_assumptions.toml",
)

ARITHMETIC_TOLERANCE = 1e-9
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
FORBIDDEN_SCHEMA_PHRASES = (
    "validated resource",
    "confirmed feasible",
    "certified estimate",
    "physically true pool",
    "source authority confirmed",
)
UNSUPPORTED_FIELD_NAMES = (
    "seasonal_resource_profile",
    "monthly_resource_profile",
    "gis_geometry",
    "transport_route",
    "storage_state",
    "dynamic_competing_demand",
    "resource_depletion_state",
    "contractual_access_records",
    "southland_otago_combined_pool",
    "site_feasibility_status",
    "qualification_codes",
    "model_input_ids",
)
CONSUMER_ALLOWED_FIELDS = (
    "supported_decision_claim_class",
    "geographic_boundary",
    "temporal_resolution",
    "resource_quantity_character",
    "competing_demand_treatment",
    "accessibility_radius",
    "accessibility_basis",
    "transport_cost_distance_basis",
    "contractual_access_status",
    "regional_pool_total_tonnes_per_year",
    "conditional_tonnes_per_year",
    "bb1_share_of_regional_pool_mass_basis_pct",
    "physical_limit_binding_indicator",
)
COST_FIELDS = (
    "weighted_delivered_cost_nzd_per_gj_low",
    "weighted_delivered_cost_nzd_per_gj_mid",
    "weighted_delivered_cost_nzd_per_gj_high",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _shown(path: Path) -> str:
    """Release staging edit: repository-relative path for console output."""
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return Path(path).name


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def register_ids(path: Path, column: str) -> set[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {row[column].strip() for row in reader if row.get(column)}


def resolve_toml_path(declared: str) -> Path | None:
    declared_path = Path(declared)
    if declared_path.is_file():
        return declared_path
    for candidate in TOML_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def expected_artefact_id(instance: dict) -> str:
    summary_sha = sha256_file(FORMALISED_SUMMARY)
    name = (
        f"{instance['artefact_family']}/{instance['semantic_version']}/"
        f"{summary_sha}/{instance['assumptions_toml_sha256']}/"
        f"{instance['canonical_upstream_dispatch_bundle']}"
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def check_schema_wording(schema: dict, failures: list[str]) -> None:
    blob = json.dumps(schema).lower()
    for phrase in FORBIDDEN_SCHEMA_PHRASES:
        if phrase in blob:
            failures.append(f"schema wording contains forbidden phrase: {phrase!r}")


def validate_instance(instance: dict, schema: dict, failures: list[str], notes: list[str]) -> None:
    validator = Draft202012Validator(schema)
    schema_errors = sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    for err in schema_errors:
        path = ".".join(str(part) for part in err.path) or "<root>"
        failures.append(f"schema: {path}: {err.message}")
    if schema_errors:
        return

    for name in UNSUPPORTED_FIELD_NAMES:
        if name in instance:
            failures.append(f"unsupported field present: {name}")

    if instance.get("supported_decision_claim_class") != "REGIONAL_SCREENING_BOUNDED":
        failures.append("Layer 1 is not the signed-off token REGIONAL_SCREENING_BOUNDED")

    if instance.get("accessibility_radius") == instance.get("transport_cost_distance_basis"):
        failures.append(
            "accessibility_radius equals transport_cost_distance_basis; "
            "60 km cost basis and 100 km eligibility framing must remain distinct"
        )

    pool_t = float(instance["regional_pool_total_tonnes_per_year"])
    req_t = float(instance["conditional_tonnes_per_year"])
    mass_share = float(instance["bb1_share_of_regional_pool_mass_basis_pct"])
    computed_mass = 100.0 * req_t / pool_t
    if abs(computed_mass - mass_share) > ARITHMETIC_TOLERANCE:
        failures.append(
            f"mass-basis pool share arithmetic mismatch: declared={mass_share} computed={computed_mass}"
        )
    else:
        notes.append(f"mass-basis share recomputed={computed_mass}")

    fuel_gj = float(instance["canonical_bb1_annual_fuel_GJ"])
    pool_tj = float(instance["regional_pool_total_tj_per_year"])
    energy_share = float(instance["bb1_share_of_regional_pool_energy_basis_pct"])
    computed_energy = 100.0 * (fuel_gj / 1000.0) / pool_tj
    if abs(computed_energy - energy_share) > ARITHMETIC_TOLERANCE:
        failures.append(
            f"energy-basis pool share arithmetic mismatch: declared={energy_share} computed={computed_energy}"
        )
    else:
        notes.append(f"energy-basis share recomputed={computed_energy}")

    binding = instance["physical_limit_binding_indicator"]
    if computed_mass < 100.0 and binding is not False:
        failures.append(
            "physical_limit_binding_indicator is inconsistent with mass-basis share < 100"
        )

    if any(field in instance for field in COST_FIELDS) and "price_basis_status" not in instance:
        failures.append("delivered-cost fields are present without price_basis_status")

    artefact_id = str(instance.get("artefact_id", ""))
    if not UUID_RE.match(artefact_id):
        failures.append("artefact_id is missing or not a UUID")
    if artefact_id in {instance.get("semantic_version"), instance.get("schema_version")}:
        failures.append("artefact_id is not distinct from semantic_version/schema_version")
    expected_id = expected_artefact_id(instance)
    if artefact_id.lower() != expected_id.lower():
        failures.append(
            f"artefact_id does not match deterministic UUID5 from authorised inputs: expected {expected_id}"
        )
    else:  # release staging edit: report the passed identity check explicitly
        notes.append(f"artefact_id {artefact_id} matches deterministic UUID5 from the formalised summary, assumptions TOML and upstream bundle")

    toml_path = resolve_toml_path(str(instance.get("assumptions_toml_path", "")))
    if toml_path is None:
        failures.append("assumptions TOML path does not resolve to a readable file")
    else:
        live_sha = sha256_file(toml_path)
        if live_sha != instance["assumptions_toml_sha256"]:
            failures.append(
                f"assumptions_toml_sha256 mismatch: declared={instance['assumptions_toml_sha256']} live={live_sha}"
            )
        else:
            notes.append(f"assumptions_toml_sha256 recomputed={live_sha}")

    if not instance.get("evidence_ids"):
        failures.append("record-level evidence_ids is empty")
    if not instance.get("evidence_source_vintage"):
        failures.append("record-level evidence_source_vintage is empty")

    evidence_ids = register_ids(EVIDENCE_REGISTER, "evidence_id")
    source_ids = register_ids(SOURCE_REGISTER, "source_id")
    for evid in instance.get("evidence_ids", []):
        if evid not in evidence_ids:
            failures.append(f"evidence_id not present in evidence register (read-only lookup): {evid}")
    for src in instance.get("source_ids", []):
        if src not in source_ids:
            failures.append(f"source_id not present in source register (read-only lookup): {src}")
    notes.append(f"register lookup: {len(instance.get('evidence_ids', []))} evidence_ids and "  # release staging edit
                 f"{len(instance.get('source_ids', []))} source_ids checked against references/")

    if FORMALISED_SUMMARY.is_file() and not instance.get("canonical_upstream_dispatch_bundle"):
        failures.append("upstream run identity is empty")


def run_validate(artefact_path: Path) -> int:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    failures: list[str] = []
    notes: list[str] = []
    check_schema_wording(schema, failures)
    instance = load_json(artefact_path)
    validate_instance(instance, schema, failures, notes)
    print(f"artefact: {_shown(artefact_path)}")
    print(f"schema: {_shown(SCHEMA_PATH)}")
    for note in notes:
        print(f"NOTE: {note}")
    if failures:
        print("RESULT: FAIL")
        for item in failures:
            print(f"FAIL: {item}")
        return 1
    print("RESULT: PASS")
    print("Layer 1 is a claim class, not a validation outcome.")
    print(
        "Validator does not certify source authority, transcription, "
        "extraction fidelity, or physical truth of external estimates."
    )
    return 0


def run_qualification_consumer(artefact_path: Path) -> int:
    raw = load_json(artefact_path)
    viewed = {key: raw[key] for key in CONSUMER_ALLOWED_FIELDS if key in raw}
    unread = sorted(set(raw) - set(CONSUMER_ALLOWED_FIELDS))
    print(f"artefact: {_shown(artefact_path)}")
    print("consumer_fields_read:")
    print(json.dumps(viewed, indent=2, sort_keys=True))
    print("consumer_fields_not_read:")
    print(json.dumps(unread, indent=2))

    layer1 = viewed.get("supported_decision_claim_class")
    layer2_ok = (
        viewed.get("geographic_boundary") == "Southland-only"
        and viewed.get("temporal_resolution") == "ANNUAL_AGGREGATE"
        and viewed.get("resource_quantity_character")
        == "STATIC_EXTERNALLY_SOURCED_MULTI_YEAR_AVERAGE_not_computed_or_rederived"
        and viewed.get("competing_demand_treatment") == "PARTIAL_STATIC_NETTING"
        and viewed.get("accessibility_basis") == "ELIGIBILITY_SCOPING"
        and viewed.get("contractual_access_status") == "NOT_ESTABLISHED"
        and viewed.get("accessibility_radius") != viewed.get("transport_cost_distance_basis")
    )
    numerics_would_look_supportable = (
        float(viewed.get("regional_pool_total_tonnes_per_year", 0))
        > float(viewed.get("conditional_tonnes_per_year", 0))
        and viewed.get("physical_limit_binding_indicator") is False
    )

    if layer1 == "REGIONAL_SCREENING_BOUNDED" and layer2_ok:
        interpretation = (
            "BOUNDED_REGIONAL_SCREENING: current structured fields support "
            "no demonstrated regional-level physical shortfall under the "
            "declared boundary conditions; they do not establish "
            "unconditional site-level physical feasibility."
        )
        site_feasibility_established = False
        print(f"interpretation: {interpretation}")
        print(f"site_feasibility_established: {site_feasibility_established}")
        print(f"numeric_fields_alone_would_look_supportable: {numerics_would_look_supportable}")
        print("RESULT: PASS")
        print(
            "Structured Layer 1 + Layer 2 constrain the claim to bounded "
            "regional screening and reject unconditional site-level feasibility."
        )
        return 0

    print("interpretation: UNABLE_TO_REACH_BOUNDED_REGIONAL_SCREENING")
    print("site_feasibility_established: False")
    print("RESULT: FAIL")
    print("Structured fields did not produce the authorised Path-B-equivalent reading.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a BiomassSupplyPack instance.")
    parser.add_argument("artefact", type=Path)
    parser.add_argument(
        "--mode",
        choices=("validate", "qualification-consumer"),
        default="validate",
    )
    args = parser.parse_args()
    artefact_path = args.artefact.resolve()
    if not artefact_path.is_file():
        print(f"FAIL: artefact not found: {artefact_path}", file=sys.stderr)
        return 2
    if args.mode == "qualification-consumer":
        return run_qualification_consumer(artefact_path)
    return run_validate(artefact_path)


if __name__ == "__main__":
    sys.exit(main())
