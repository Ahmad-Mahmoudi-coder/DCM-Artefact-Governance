#!/usr/bin/env python3
"""
External validator (first authorised scope) for IncrementalElectricityPack v1.0-current.

Authorised by docs/12_external_validator_authorisation.md.

This script performs the external-consistency checks JSON Schema cannot
express, for a single supplied IncrementalElectricityPack artefact instance:

1. Loads the artefact JSON.
2. Validates it against
   schemas/artefacts/incremental_electricity_pack.v1.0-current.schema.json.
   If this fails, the script stops and reports the schema errors; checks 3-4
   are not attempted against a structurally invalid document.
3. Checks p95_incremental_mw <= peak_incremental_mw (docs/08 Section 5's
   closing note: a cross-field constraint JSON Schema cannot express).
4. Optionally, only when --trace is supplied explicitly by the caller,
   recomputes annual_incremental_mwh, peak_incremental_mw, and
   p95_incremental_mw from the given hourly trace CSV (docs/03 Section 7's
   audit methods) and compares each against the artefact's declared value
   within --tolerance.

Explicitly out of scope for this first version (docs/12 Section 5):
automatic trace-file discovery, run_id/future_id registry resolution,
checksum validation, provenance validation (produced_by, created_at,
future_set_id, lifecycle_status), winter_peak_share, shape_cluster_label,
SignalsPack, DemandPack, ResultArtefact, pathway comparison, dispatch
recalculation, and model reruns. This script writes nothing to disk; all
output is printed to the terminal, and its exit code signals overall
pass/fail. A skipped check (no --trace supplied) does not, by itself,
cause a non-zero exit.
"""

import argparse
import csv
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

TRACE_VALUE_COLUMN = "incremental_electricity_MW"

TRACE_DERIVED_FIELDS = (
    "annual_incremental_mwh",
    "peak_incremental_mw",
    "p95_incremental_mw",
)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_schema_validator() -> Draft202012Validator:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def load_trace_values(trace_path: Path):
    """Read the hourly trace CSV, per docs/03 Section 7's
    'timestamp_utc, incremental_electricity_MW' pair convention."""
    values = []
    with trace_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if TRACE_VALUE_COLUMN not in (reader.fieldnames or []):
            raise ValueError(
                f"trace file has no '{TRACE_VALUE_COLUMN}' column; "
                f"found columns: {reader.fieldnames}"
            )
        for row in reader:
            values.append(float(row[TRACE_VALUE_COLUMN]))
    if not values:
        raise ValueError("trace file contains no data rows")
    return values


def percentile_linear(sorted_values, pct: float) -> float:
    """Linear-interpolation percentile, matching the numpy/pandas default
    ('linear' method), per docs/03 Section 7's note that the
    percentile-interpolation method should be declared explicitly."""
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (n - 1)
    lower = int(rank)
    upper = min(lower + 1, n - 1)
    fraction = rank - lower
    return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])


def within_tolerance(declared: float, computed: float, tolerance: float) -> bool:
    return abs(declared - computed) <= tolerance


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "External validator (first authorised scope) for a single "
            "IncrementalElectricityPack v1.0-current artefact instance. "
            "See docs/12_external_validator_authorisation.md."
        )
    )
    parser.add_argument(
        "--artefact",
        required=True,
        help="Path to a single IncrementalElectricityPack JSON instance.",
    )
    parser.add_argument(
        "--trace",
        required=False,
        default=None,
        help=(
            "Path to the hourly source trace CSV this artefact summarises. "
            "Must be supplied explicitly; this script does not discover it "
            "automatically. When omitted, trace-derived checks are skipped."
        ),
    )
    parser.add_argument(
        "--tolerance",
        required=False,
        type=float,
        default=0.01,
        help=(
            "Numerical tolerance for trace-derived comparisons, in the same "
            "unit as the field being compared (MW or MWh). Default: 0.01."
        ),
    )
    args = parser.parse_args()

    artefact_path = Path(args.artefact)
    print(f"Artefact: {artefact_path}")

    if not artefact_path.exists():
        print(f"[FAIL] artefact file not found: {artefact_path}")
        return 1

    instance = load_json(artefact_path)

    # Checks 1-2: schema validation (reused, not reimplemented)
    validator = load_schema_validator()
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        print(
            "[FAIL] schema validation "
            "(schemas/artefacts/incremental_electricity_pack.v1.0-current.schema.json)"
        )
        for err in errors:
            error_path = "/".join(str(p) for p in err.path) or "<root>"
            print(f"        - {error_path}: {err.message}")
        print()
        print(
            "Schema validation failed; checks 3-4 were not performed on a "
            "structurally invalid document."
        )
        return 1
    print("[OK  ] schema validation")

    all_ok = True

    # Check 3: p95_incremental_mw <= peak_incremental_mw
    peak = instance.get("peak_incremental_mw")
    p95 = instance.get("p95_incremental_mw")
    if peak is None or p95 is None:
        print(
            "[FAIL] p95_incremental_mw <= peak_incremental_mw: "
            "one or both fields missing"
        )
        all_ok = False
    elif p95 <= peak:
        print(f"[OK  ] p95_incremental_mw <= peak_incremental_mw ({p95} <= {peak})")
    else:
        print(f"[FAIL] p95_incremental_mw <= peak_incremental_mw ({p95} > {peak})")
        all_ok = False

    # Check 4: optional trace-derived checks, only when --trace is supplied
    if args.trace is None:
        for field_name in TRACE_DERIVED_FIELDS:
            print(f"[SKIP] {field_name} trace-derived check (no --trace supplied)")
    else:
        trace_path = Path(args.trace)
        if not trace_path.exists():
            print(f"[FAIL] trace file not found: {trace_path}")
            all_ok = False
        else:
            try:
                values = load_trace_values(trace_path)
            except ValueError as exc:
                print(f"[FAIL] could not read trace file: {exc}")
                all_ok = False
            else:
                sorted_values = sorted(values)
                computed = {
                    "annual_incremental_mwh": sum(values),
                    "peak_incremental_mw": max(values),
                    "p95_incremental_mw": percentile_linear(sorted_values, 95.0),
                }
                for field_name in TRACE_DERIVED_FIELDS:
                    declared_value = instance.get(field_name)
                    computed_value = computed[field_name]
                    if declared_value is None:
                        print(
                            f"[FAIL] {field_name}: field missing from artefact, "
                            "cannot compare to trace"
                        )
                        all_ok = False
                        continue
                    ok = within_tolerance(declared_value, computed_value, args.tolerance)
                    status = "OK  " if ok else "FAIL"
                    print(
                        f"[{status}] {field_name}: declared={declared_value}, "
                        f"computed={computed_value}, tolerance={args.tolerance} -> "
                        f"{'within tolerance' if ok else 'OUTSIDE TOLERANCE'}"
                    )
                    if not ok:
                        all_ok = False

    print()
    if all_ok:
        print("ALL PERFORMED CHECKS PASSED.")
        return 0
    else:
        print("ONE OR MORE PERFORMED CHECKS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
