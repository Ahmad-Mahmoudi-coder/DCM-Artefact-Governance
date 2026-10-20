#!/usr/bin/env python3
"""
Producer for the first governed BiomassSupplyPack instance.

Authorised by docs/88. Implementation encodings in docs/90.
Reads ONLY biomass_supply_screen_formalised_v1/. Does not modify that
bundle, does not call biomass_supply_screen calculation functions, and
does not invent substitute values.
"""

from __future__ import annotations

import csv
import hashlib
import json
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMALISED_DIR = (
    REPO_ROOT
    / "Process-Heat-DCM"
    / "Output"
    / "runs"
    / "biomass_supply_screen_formalised_v1"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "Process-Heat-DCM"
    / "Output"
    / "runs"
    / "biomass_supply_pack_v1"
)
INSTANCE_NAME = "biomass_supply_pack.v1.0.json"
MANIFEST_NAME = "manifest.json"

SEMANTIC_VERSION = "1.0"
SCHEMA_VERSION = "v1.0-current"
ARTEFACT_FAMILY = "BiomassSupplyPack"
PRODUCER_SCRIPT_IDENTITY = "Process-Heat-DCM/src/biomass_supply_pack_producer.py"
SOURCE_FORMALISED_BUNDLE = "biomass_supply_screen_formalised_v1"
ARTEFACT_ID_NAMESPACE = uuid.NAMESPACE_URL

REQUIRED_SUMMARY_KEYS = (
    "regional_pool_total_tonnes_per_year",
    "regional_pool_total_tj_per_year",
    "conditional_tonnes_per_year",
    "canonical_bb1_annual_fuel_MWh",
    "canonical_bb1_annual_fuel_GJ",
    "bb1_share_of_regional_pool_mass_basis_pct",
    "bb1_share_of_regional_pool_energy_basis_pct",
    "physical_limit_binding_indicator",
    "source_vintage_note",
    "regional_resource_quantity_character",
    "geographic_boundary",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def as_float(value: str, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"STOP: required numeric field {field!r} is not parseable: {value!r}") from exc


def as_bool(value: str, field: str) -> bool:
    text = str(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise SystemExit(f"STOP: required boolean field {field!r} is not parseable: {value!r}")


def load_summary(path: Path) -> dict:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise SystemExit(f"STOP: expected exactly one formalised summary row, found {len(rows)}")
    return rows[0]


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_artefact_id(
    formalised_summary_sha256: str,
    assumptions_toml_sha256: str,
    upstream_bundle: str,
) -> str:
    name = (
        f"{ARTEFACT_FAMILY}/{SEMANTIC_VERSION}/"
        f"{formalised_summary_sha256}/{assumptions_toml_sha256}/{upstream_bundle}"
    )
    return str(uuid.uuid5(ARTEFACT_ID_NAMESPACE, name))


def require_copied(value: object, field: str) -> object:
    if value is None or value == "":
        raise SystemExit(f"STOP: required value {field!r} cannot be populated from the formalised bundle")
    return value


def build_instance(summary: dict, manifest: dict, formalised_summary_sha256: str) -> dict:
    for key in REQUIRED_SUMMARY_KEYS:
        require_copied(summary.get(key), key)

    resource_character = summary["regional_resource_quantity_character"]
    expected_character = (
        "STATIC_EXTERNALLY_SOURCED_MULTI_YEAR_AVERAGE_not_computed_or_rederived"
    )
    if resource_character != expected_character:
        raise SystemExit(
            "STOP: formalised resource-quantity character does not match the "
            f"authorised Layer-2 token: {resource_character!r}"
        )
    if summary["geographic_boundary"] != "Southland-only":
        raise SystemExit(
            "STOP: formalised geographic_boundary is not Southland-only: "
            f"{summary['geographic_boundary']!r}"
        )

    evidence_ids = list(require_copied(manifest.get("evidence_ids"), "evidence_ids"))
    source_ids = list(manifest.get("source_ids") or [])
    upstream = str(require_copied(manifest.get("canonical_upstream_dispatch_bundle"), "canonical_upstream_dispatch_bundle"))
    toml_sha = str(require_copied(manifest.get("assumptions_toml_sha256"), "assumptions_toml_sha256"))
    bb1_path = str(require_copied(manifest.get("canonical_bb1_summary_input_path"), "canonical_bb1_summary_input_path"))
    toml_path = str(require_copied(manifest.get("assumptions_toml_path"), "assumptions_toml_path"))

    artefact_id = build_artefact_id(formalised_summary_sha256, toml_sha, upstream)

    return {
        "artefact_id": artefact_id,
        "semantic_version": SEMANTIC_VERSION,
        "schema_version": SCHEMA_VERSION,
        "artefact_family": ARTEFACT_FAMILY,
        "supported_decision_claim_class": "REGIONAL_SCREENING_BOUNDED",
        "geographic_boundary": "Southland-only",
        "temporal_resolution": "ANNUAL_AGGREGATE",
        "resource_quantity_character": expected_character,
        "competing_demand_treatment": "PARTIAL_STATIC_NETTING",
        "accessibility_radius": 100,
        "accessibility_basis": "ELIGIBILITY_SCOPING",
        "transport_cost_distance_basis": 60,
        "contractual_access_status": "NOT_ESTABLISHED",
        "regional_pool_total_tonnes_per_year": as_float(
            summary["regional_pool_total_tonnes_per_year"],
            "regional_pool_total_tonnes_per_year",
        ),
        "regional_pool_total_tj_per_year": as_float(
            summary["regional_pool_total_tj_per_year"],
            "regional_pool_total_tj_per_year",
        ),
        "conditional_tonnes_per_year": as_float(
            summary["conditional_tonnes_per_year"],
            "conditional_tonnes_per_year",
        ),
        "canonical_bb1_annual_fuel_MWh": as_float(
            summary["canonical_bb1_annual_fuel_MWh"],
            "canonical_bb1_annual_fuel_MWh",
        ),
        "canonical_bb1_annual_fuel_GJ": as_float(
            summary["canonical_bb1_annual_fuel_GJ"],
            "canonical_bb1_annual_fuel_GJ",
        ),
        "bb1_share_of_regional_pool_mass_basis_pct": as_float(
            summary["bb1_share_of_regional_pool_mass_basis_pct"],
            "bb1_share_of_regional_pool_mass_basis_pct",
        ),
        "bb1_share_of_regional_pool_energy_basis_pct": as_float(
            summary["bb1_share_of_regional_pool_energy_basis_pct"],
            "bb1_share_of_regional_pool_energy_basis_pct",
        ),
        "physical_limit_binding_indicator": as_bool(
            summary["physical_limit_binding_indicator"],
            "physical_limit_binding_indicator",
        ),
        "evidence_ids": evidence_ids,
        "source_ids": source_ids,
        "evidence_source_vintage": str(summary["source_vintage_note"]),
        "canonical_upstream_dispatch_bundle": upstream,
        "canonical_bb1_summary_input_path": bb1_path,
        "assumptions_toml_sha256": toml_sha,
        "assumptions_toml_path": toml_path,
        "producer_script_identity": PRODUCER_SCRIPT_IDENTITY,
        "source_formalised_bundle": SOURCE_FORMALISED_BUNDLE,
    }


def write_outputs(instance: dict, formalised_summary_sha256: str, formalised_manifest_sha256: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    instance_path = OUTPUT_DIR / INSTANCE_NAME
    instance_text = json.dumps(instance, indent=2, ensure_ascii=False) + "\n"
    instance_path.write_text(instance_text, encoding="utf-8")
    instance_sha256 = hashlib.sha256(instance_path.read_bytes()).hexdigest()
    manifest = {
        "bundle_version": "biomass_supply_pack_v1",
        "semantic_version": SEMANTIC_VERSION,
        "schema_version": SCHEMA_VERSION,
        "artefact_family": ARTEFACT_FAMILY,
        "artefact_id": instance["artefact_id"],
        "supported_decision_claim_class": instance["supported_decision_claim_class"],
        "source_formalised_bundle": SOURCE_FORMALISED_BUNDLE,
        "producer_script_identity": PRODUCER_SCRIPT_IDENTITY,
        "authorising_documents": [
            "docs/87_phase3d_biomasssupplypack_governance_and_artefact_boundary_design.qmd",
            "docs/88_phase3d_biomasssupplypack_implementation_authorisation.qmd",
            "docs/89_phase3d_biomasssupplypack_layer1_result_scope_vocabulary_proposal.qmd",
            "docs/90_phase3d_biomasssupplypack_implementation_decisions.qmd",
        ],
        "output_files": [INSTANCE_NAME, MANIFEST_NAME],
        "output_file_sha256": {INSTANCE_NAME: instance_sha256},
        "source_file_sha256": {
            "biomass_supply_screen_summary.csv": formalised_summary_sha256,
            "manifest.json": formalised_manifest_sha256,
        },
        "assumptions_toml_sha256": instance["assumptions_toml_sha256"],
        "note": (
            "Sidecar identity/hash record for the first BiomassSupplyPack instance. "
            "Not a schema instance. Does not modify any legacy biomass bundle."
        ),
    }
    (OUTPUT_DIR / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] wrote {instance_path}")
    print(f"[OK] artefact_id={instance['artefact_id']}")
    print(f"[OK] instance_sha256={instance_sha256}")


def main() -> None:
    summary_path = FORMALISED_DIR / "biomass_supply_screen_summary.csv"
    manifest_path = FORMALISED_DIR / "manifest.json"
    if not summary_path.is_file() or not manifest_path.is_file():
        raise SystemExit("STOP: authorised formalised bundle is missing required files")
    summary_sha = sha256_file(summary_path)
    manifest_sha = sha256_file(manifest_path)
    instance = build_instance(load_summary(summary_path), load_manifest(manifest_path), summary_sha)
    write_outputs(instance, summary_sha, manifest_sha)


if __name__ == "__main__":
    main()
