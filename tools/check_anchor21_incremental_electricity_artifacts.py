#!/usr/bin/env python3
"""Repeatable checker for the generated anchor_21 IncrementalElectricityPack artefacts.

Authorised by docs/33_anchor21_generated_artifact_harness_authorisation.qmd, following
the scope decision in docs/32_real_output_validation_and_versioning_scope_decision.qmd
(Option B: build a repeatable harness for the 42 generated anchor_21 artefacts before
moving to v1.1 schema planning, registry-backed validation, release02_100 support, or a
ValidationArtefact/reporting layer).

This script converts the one-off creation-time validation recorded in
docs/30_anchor21_real_output_adapter_creation.qmd into a standalone, re-runnable check.

Scope (per docs/33):
  - Validates the 42 already-generated artefacts under artefacts/incremental_electricity_pack/anchor_21/
    directly against schemas/artefacts/incremental_electricity_pack.v1.0-current.schema.json.
  - Checks directory/file-set structure, filename pattern, pathway/future coverage,
    JSON parsing, schema validity, required numeric fields, p95 <= peak, absence of
    future_set_id, anchor_21 lineage, and shared-trace repeated-value consistency.
  - Does NOT call or modify tools/validate_incremental_electricity_pack_external.py.
  - Does NOT call or modify tools/check_future_id_registry.py.
  - Does NOT perform registry-backed artefact validation.
  - Does NOT perform trace-derived recomputation.
  - Does NOT generate, write, or modify any artefact, source, registry, or schema file.
  - Does NOT call the adapter script in --write or --dry-run mode.

Binding caveat carried forward from docs/28/docs/29/docs/30/docs/31:
  peak_incremental_mw and p95_incremental_mw are pathway-level trace-derived values
  repeated across futures for schema compatibility, not independently future-specific
  quantities. This script's shared-trace consistency check confirms that limitation
  remains internally consistent -- it is NOT evidence that these fields are
  future-varying.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("FAIL: the 'jsonschema' package is required but not importable.", file=sys.stderr)
    sys.exit(1)

DEFAULT_ARTIFACT_DIR = Path("artefacts/incremental_electricity_pack/anchor_21")
DEFAULT_SCHEMA_PATH = Path("schemas/artefacts/incremental_electricity_pack.v1.0-current.schema.json")

EXPECTED_PATHWAYS = ("2035_BB", "2035_EB")
EXPECTED_FUTURE_IDS = tuple(range(21))  # 0-20 inclusive
EXPECTED_ARTIFACT_COUNT = len(EXPECTED_PATHWAYS) * len(EXPECTED_FUTURE_IDS)  # 42
EXPECTED_EPOCH = 2035
EXPECTED_SCHEMA_VERSION = "v1.0-current"
EXPECTED_ARTEFACT_FAMILY = "IncrementalElectricityPack"

REQUIRED_FIELDS = (
    "artefact_id",
    "schema_version",
    "artefact_family",
    "site_id",
    "run_id",
    "future_id",
    "pathway_id",
    "epoch",
    "annual_incremental_mwh",
    "peak_incremental_mw",
    "p95_incremental_mw",
)

# Binding shared-trace repeated values, as recorded in docs/31 and docs/33.
EXPECTED_SHARED_TRACE_VALUES = {
    "2035_BB": {
        "peak_incremental_mw": 94.99880842222532,
        "p95_incremental_mw": 88.41729669896563,
    },
    "2035_EB": {
        "peak_incremental_mw": 132.99833179111545,
        "p95_incremental_mw": 123.78421537855188,
    },
}


class CheckFailure(Exception):
    """Raised to signal a check failure; caught by main() to produce a clean exit."""


def filename_for(pathway_id: str, future_id: int) -> str:
    return f"incremental_electricity_pack.anchor_21.{pathway_id}.future_{future_id}.v1.0-current.json"


def load_schema(schema_path: Path) -> dict:
    if not schema_path.exists():
        raise CheckFailure(f"schema file not found: {schema_path}")
    try:
        return json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CheckFailure(f"schema file is not valid JSON: {schema_path} ({exc})") from exc


def check_directory(artifact_dir: Path) -> list[Path]:
    if not artifact_dir.exists() or not artifact_dir.is_dir():
        raise CheckFailure(f"artefact directory not found: {artifact_dir}")
    files = sorted(artifact_dir.glob("*.json"))
    if len(files) != EXPECTED_ARTIFACT_COUNT:
        raise CheckFailure(
            f"expected exactly {EXPECTED_ARTIFACT_COUNT} JSON artefact files, found {len(files)}"
        )
    return files


def parse_filename(path: Path) -> tuple[str, int]:
    name = path.name
    prefix = "incremental_electricity_pack.anchor_21."
    suffix = ".v1.0-current.json"
    if not (name.startswith(prefix) and name.endswith(suffix)):
        raise CheckFailure(f"filename does not match authorised pattern: {name}")
    middle = name[len(prefix): -len(suffix)]
    parts = middle.split(".future_")
    if len(parts) != 2:
        raise CheckFailure(f"filename does not match authorised pattern: {name}")
    pathway_id, future_id_str = parts
    if not future_id_str.isdigit():
        raise CheckFailure(f"filename future_id segment is not an integer: {name}")
    return pathway_id, int(future_id_str)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Repeatable structural checker for the 42 generated anchor_21 "
        "IncrementalElectricityPack v1.0-current candidate artefacts."
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=DEFAULT_ARTIFACT_DIR,
        help=f"Directory containing generated anchor_21 artefacts (default: {DEFAULT_ARTIFACT_DIR})",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help=f"Path to the IncrementalElectricityPack v1.0-current schema (default: {DEFAULT_SCHEMA_PATH})",
    )
    parser.add_argument(
        "--expected-shared-trace-json",
        type=Path,
        default=None,
        help=(
            "docs/55_canonical_downstream_grid_rdm_and_anchor21_regeneration.qmd: optional override "
            "for the reference shared-trace peak_incremental_mw/p95_incremental_mw values this "
            "harness checks each artefact set's shared-trace consistency against. Default (None) "
            "uses the original hardcoded EXPECTED_SHARED_TRACE_VALUES (the historical "
            "poc_20260105_release02-derived values) exactly as before -- this override does not "
            "change what is checked, only which reference values a different, explicitly-named "
            "artefact set (built from different, genuinely-changed source data) is checked against. "
            "File format: JSON object matching EXPECTED_SHARED_TRACE_VALUES' own shape, e.g. "
            '{"2035_BB": {"peak_incremental_mw": ..., "p95_incremental_mw": ...}, "2035_EB": {...}}.'
        ),
    )
    args = parser.parse_args(argv)

    expected_shared_trace_values = EXPECTED_SHARED_TRACE_VALUES
    if args.expected_shared_trace_json is not None:
        expected_shared_trace_values = json.loads(args.expected_shared_trace_json.read_text(encoding="utf-8"))

    print("anchor_21 generated-artefact harness")
    print(f"  artefact_dir = {args.artifact_dir}")
    print(f"  schema       = {args.schema}")
    if args.expected_shared_trace_json is not None:
        print(f"  expected_shared_trace_json = {args.expected_shared_trace_json}")
    print(
        "  binding caveat: peak_incremental_mw and p95_incremental_mw are pathway-level "
        "trace-derived values repeated across futures for schema compatibility, not "
        "independently future-specific quantities."
    )
    print()

    try:
        schema = load_schema(args.schema)
        validator = jsonschema.Draft202012Validator(schema)

        files = check_directory(args.artifact_dir)

        seen: dict[str, set[int]] = {pw: set() for pw in EXPECTED_PATHWAYS}
        shared_trace_seen: dict[str, dict[str, set[float]]] = {
            pw: {"peak_incremental_mw": set(), "p95_incremental_mw": set()} for pw in EXPECTED_PATHWAYS
        }
        parsed_count = 0
        schema_valid_count = 0

        for path in files:
            filename_pathway, filename_future_id = parse_filename(path)

            if filename_pathway not in EXPECTED_PATHWAYS:
                raise CheckFailure(f"unexpected pathway in filename: {path.name} ({filename_pathway})")
            if filename_future_id > 20:
                raise CheckFailure(f"future_id above 20 present in filename: {path.name}")
            if filename_future_id < 0:
                raise CheckFailure(f"negative future_id in filename: {path.name}")

            try:
                raw_text = path.read_text(encoding="utf-8")
                artefact = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                raise CheckFailure(f"JSON parse failure: {path.name} ({exc})") from exc
            parsed_count += 1

            errors = sorted(validator.iter_errors(artefact), key=str)
            if errors:
                first = errors[0]
                raise CheckFailure(f"schema validation failed for {path.name}: {first.message}")
            schema_valid_count += 1

            missing = [f for f in REQUIRED_FIELDS if f not in artefact]
            if missing:
                raise CheckFailure(f"missing required fields in {path.name}: {missing}")

            if "future_set_id" in artefact:
                raise CheckFailure(
                    f"artefact {path.name} contains future_set_id, which v1.0-current does not permit"
                )

            if artefact["schema_version"] != EXPECTED_SCHEMA_VERSION:
                raise CheckFailure(
                    f"unexpected schema_version in {path.name}: {artefact['schema_version']!r}"
                )
            if artefact["artefact_family"] != EXPECTED_ARTEFACT_FAMILY:
                raise CheckFailure(
                    f"unexpected artefact_family in {path.name}: {artefact['artefact_family']!r}"
                )

            content_pathway = artefact["pathway_id"]
            content_future_id = artefact["future_id"]
            if content_pathway != filename_pathway or content_future_id != filename_future_id:
                raise CheckFailure(
                    f"filename/content mismatch for {path.name}: "
                    f"filename=({filename_pathway}, {filename_future_id}) "
                    f"content=({content_pathway}, {content_future_id})"
                )

            if content_pathway not in EXPECTED_PATHWAYS:
                raise CheckFailure(f"unexpected pathway_id in {path.name}: {content_pathway!r}")
            if not isinstance(content_future_id, int) or not (0 <= content_future_id <= 20):
                raise CheckFailure(f"future_id out of expected 0-20 range in {path.name}: {content_future_id!r}")
            if artefact["epoch"] != EXPECTED_EPOCH:
                raise CheckFailure(f"unexpected epoch in {path.name}: {artefact['epoch']!r}")

            for numeric_field in ("annual_incremental_mwh", "peak_incremental_mw", "p95_incremental_mw"):
                value = artefact[numeric_field]
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise CheckFailure(f"{numeric_field} is not numeric in {path.name}: {value!r}")

            if artefact["p95_incremental_mw"] > artefact["peak_incremental_mw"]:
                raise CheckFailure(
                    f"p95_incremental_mw > peak_incremental_mw in {path.name}: "
                    f"{artefact['p95_incremental_mw']} > {artefact['peak_incremental_mw']}"
                )

            seen[content_pathway].add(content_future_id)
            shared_trace_seen[content_pathway]["peak_incremental_mw"].add(artefact["peak_incremental_mw"])
            shared_trace_seen[content_pathway]["p95_incremental_mw"].add(artefact["p95_incremental_mw"])

        if parsed_count != EXPECTED_ARTIFACT_COUNT or schema_valid_count != EXPECTED_ARTIFACT_COUNT:
            raise CheckFailure(
                f"expected {EXPECTED_ARTIFACT_COUNT} parsed and schema-valid artefacts, "
                f"got parsed={parsed_count}, schema_valid={schema_valid_count}"
            )

        for pathway in EXPECTED_PATHWAYS:
            expected_ids = set(EXPECTED_FUTURE_IDS)
            actual_ids = seen[pathway]
            if actual_ids != expected_ids:
                missing_ids = sorted(expected_ids - actual_ids)
                extra_ids = sorted(actual_ids - expected_ids)
                raise CheckFailure(
                    f"future_id coverage mismatch for {pathway}: missing={missing_ids} extra={extra_ids}"
                )

        # Shared-trace consistency check: exactly one distinct value per pathway, matching docs/31.
        for pathway in EXPECTED_PATHWAYS:
            for field in ("peak_incremental_mw", "p95_incremental_mw"):
                distinct_values = shared_trace_seen[pathway][field]
                if len(distinct_values) != 1:
                    raise CheckFailure(
                        f"shared-trace inconsistency: {pathway} {field} has "
                        f"{len(distinct_values)} distinct values, expected exactly 1: {sorted(distinct_values)}"
                    )
                (actual_value,) = tuple(distinct_values)
                expected_value = expected_shared_trace_values[pathway][field]
                if actual_value != expected_value:
                    raise CheckFailure(
                        f"shared-trace repeated-value mismatch for {pathway} {field}: "
                        f"expected {expected_value}, found {actual_value}"
                    )

        print("Check results:")
        print(f"  [OK] artefact directory exists: {args.artifact_dir}")
        print(f"  [OK] exactly {EXPECTED_ARTIFACT_COUNT} JSON artefact files present")
        print("  [OK] filenames match authorised pattern")
        print(f"  [OK] pathways exactly {EXPECTED_PATHWAYS}")
        print("  [OK] future IDs exactly 0-20 for each pathway, no futures above 20, no release02_100 artefact")
        print(f"  [OK] all {EXPECTED_ARTIFACT_COUNT} JSON files parsed")
        print(f"  [OK] all {EXPECTED_ARTIFACT_COUNT} artefacts validate against {EXPECTED_SCHEMA_VERSION} schema")
        print("  [OK] all required fields present; no future_set_id present")
        print("  [OK] all schema_version/artefact_family/epoch values as expected")
        print("  [OK] all annual/peak/p95 fields numeric; p95 <= peak for every artefact")
        for pathway in EXPECTED_PATHWAYS:
            peak = expected_shared_trace_values[pathway]["peak_incremental_mw"]
            p95 = expected_shared_trace_values[pathway]["p95_incremental_mw"]
            print(
                f"  [OK] {pathway} shared-trace values consistent across all 21 futures "
                f"(peak_incremental_mw={peak}, p95_incremental_mw={p95}, shared across all futures)"
            )
        print()
        print(f"PASS: all checks passed for {EXPECTED_ARTIFACT_COUNT} anchor_21 artefacts")
        return 0

    except CheckFailure as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
