#!/usr/bin/env python3
"""
Schema test harness for IncrementalElectricityPack v1.0-current.

Authorised by docs/10_schema_test_harness_authorisation.md.

Scope: JSON Schema structural validation only. This script checks that the
fixture files under schemas/examples/ produce the pass/fail behaviour
against schemas/artefacts/incremental_electricity_pack.v1.0-current.schema.json
already documented in docs/09_schema_fixture_authorisation.md Section 4 and
docs/00b_phase1_decision_log.md, plus the two qualification_codes fixtures
authorised by docs/83.

This script does NOT check derivation consistency, source hourly traces,
run_id/future_id foreign-key resolution, units beyond the schema's own
keywords, provenance, or checksums. See
docs/10_schema_test_harness_authorisation.md Section 5 for the full list
of exclusions. It writes nothing to disk; all output is printed to the
terminal, and its exit code signals overall pass/fail.
"""

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = (
    REPO_ROOT
    / "schemas"
    / "artefacts"
    / "incremental_electricity_pack.v1.0-current.schema.json"
)
EXAMPLES_DIR = REPO_ROOT / "schemas" / "examples"

# (filename, expected_result, expected_keyword)
# expected_result: "pass" or "fail"
# expected_keyword: the JSON Schema validator keyword expected to appear on
# the first reported error for a failing fixture, or None for a fixture
# expected to pass. Matches docs/09_schema_fixture_authorisation.md Section 4.
FIXTURES = [
    ("incremental_electricity_pack.valid.v1.0-current.json", "pass", None),
    ("incremental_electricity_pack.invalid.missing_future_id.json", "fail", "required"),
    (
        "incremental_electricity_pack.valid.derivation_inconsistent_schema_only.json",
        "pass",
        None,
    ),
    (
        "incremental_electricity_pack.invalid.future_id_out_of_bounds.json",
        "fail",
        "maximum",
    ),
    (
        "incremental_electricity_pack.invalid.extra_checksum_field.json",
        "fail",
        "additionalProperties",
    ),
    (
        "incremental_electricity_pack.invalid.duplicate_warning_codes.json",
        "fail",
        "uniqueItems",
    ),
    (
        "incremental_electricity_pack.valid.qualification_codes.json",
        "pass",
        None,
    ),
    (
        "incremental_electricity_pack.invalid.unrecognised_qualification_code.json",
        "fail",
        "enum",
    ),
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    print(f"Schema: {SCHEMA_PATH.relative_to(REPO_ROOT)}")

    schema = load_json(SCHEMA_PATH)

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        print(f"FAIL: schema is not a valid Draft 2020-12 schema: {exc}")
        return 1
    print("Schema is a valid Draft 2020-12 document.\n")

    validator = Draft202012Validator(schema)

    all_ok = True
    for filename, expected_result, expected_keyword in FIXTURES:
        fixture_path = EXAMPLES_DIR / filename
        if not fixture_path.exists():
            print(f"[MISSING ] {filename}: fixture file not found at {fixture_path}")
            all_ok = False
            continue

        instance = load_json(fixture_path)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))

        actual_result = "fail" if errors else "pass"
        actual_keyword = errors[0].validator if errors else None

        result_matches = actual_result == expected_result
        keyword_matches = expected_keyword is None or actual_keyword == expected_keyword
        ok = result_matches and keyword_matches
        all_ok = all_ok and ok

        status = "OK      " if ok else "MISMATCH"
        detail = f"expected={expected_result}"
        if expected_keyword:
            detail += f"/{expected_keyword}"
        detail += f", actual={actual_result}"
        if actual_keyword:
            detail += f"/{actual_keyword}"

        print(f"[{status}] {filename}: {detail}")

    print()
    if all_ok:
        print("ALL FIXTURES MATCH EXPECTED BEHAVIOUR.")
        return 0
    else:
        print("ONE OR MORE FIXTURES DID NOT MATCH EXPECTED BEHAVIOUR.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
