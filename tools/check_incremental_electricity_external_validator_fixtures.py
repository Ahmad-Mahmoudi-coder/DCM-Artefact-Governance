#!/usr/bin/env python3
"""
Fixture harness for the IncrementalElectricityPack external validator.

Authorised by docs/14_external_validator_fixture_harness_authorisation.md.

Scope: this harness orchestrates calls to the existing external validator
(tools/validate_incremental_electricity_pack_external.py) as a genuine
command-line subprocess, once per fixture scenario under
tests/fixtures/incremental_electricity_pack_external/, and compares each
invocation's exit code against the expected outcome already fixed in
docs/13_external_validator_trace_fixture_authorisation.md Section 5 and
confirmed manually in docs/00b_phase1_decision_log.md's 2026-08-15
fixture-creation-and-verification entry.

This harness does NOT re-implement any of the external validator's checks
(schema validation, the p95 <= peak check, or any trace-derived comparison).
It does not parse or assert against the validator's console-output wording —
only its exit code is compared against the expected outcome, per
docs/14_external_validator_fixture_harness_authorisation.md Section 6. It
does not modify the schema, any fixture, or the validator itself, does not
infer or discover additional trace files, and does not perform any check
outside the external validator's own authorised scope (docs/12). It writes
nothing to disk; all output is printed to the terminal, and its exit code
signals overall pass/fail.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_PATH = REPO_ROOT / "tools" / "validate_incremental_electricity_pack_external.py"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "incremental_electricity_pack_external"

# (scenario name, artefact filename, trace filename or None, expected result)
# expected result: "pass" (exit code 0) or "fail" (non-zero exit code)
# Matches docs/13_external_validator_trace_fixture_authorisation.md Section 5
# and docs/14_external_validator_fixture_harness_authorisation.md Section 7.
SCENARIOS = [
    (
        "valid_trace_match",
        "valid_trace_match.artefact.json",
        "valid_trace_match.trace.csv",
        "pass",
    ),
    (
        "invalid_p95_above_peak",
        "invalid_p95_above_peak.artefact.json",
        None,
        "fail",
    ),
    (
        "invalid_annual_mismatch",
        "invalid_annual_mismatch.artefact.json",
        "invalid_annual_mismatch.trace.csv",
        "fail",
    ),
    (
        "invalid_peak_mismatch",
        "invalid_peak_mismatch.artefact.json",
        "invalid_peak_mismatch.trace.csv",
        "fail",
    ),
    (
        "invalid_p95_mismatch",
        "invalid_p95_mismatch.artefact.json",
        "invalid_p95_mismatch.trace.csv",
        "fail",
    ),
    (
        "invalid_trace_missing_incremental_mw_column",
        "invalid_trace_missing_incremental_mw_column.artefact.json",
        "invalid_trace_missing_incremental_mw_column.trace.csv",
        "fail",
    ),
]


def run_scenario(artefact_path: Path, trace_path):
    """Invoke the external validator as a genuine CLI subprocess and return
    (exit_code, stdout, stderr). Uses the same Python interpreter this
    harness is running under, per docs/14 Section 5."""
    command = [sys.executable, str(VALIDATOR_PATH), "--artefact", str(artefact_path)]
    if trace_path is not None:
        command += ["--trace", str(trace_path)]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def main() -> int:
    print(f"External validator: {VALIDATOR_PATH.relative_to(REPO_ROOT)}")
    print(f"Fixtures directory: {FIXTURES_DIR.relative_to(REPO_ROOT)}\n")

    if not VALIDATOR_PATH.exists():
        print(f"FAIL: external validator not found at {VALIDATOR_PATH}")
        return 1

    all_ok = True
    for scenario_name, artefact_filename, trace_filename, expected_result in SCENARIOS:
        artefact_path = FIXTURES_DIR / artefact_filename
        trace_path = FIXTURES_DIR / trace_filename if trace_filename else None

        if not artefact_path.exists():
            print(f"[MISSING ] {scenario_name}: artefact fixture not found at {artefact_path}")
            all_ok = False
            continue
        if trace_path is not None and not trace_path.exists():
            print(f"[MISSING ] {scenario_name}: trace fixture not found at {trace_path}")
            all_ok = False
            continue

        exit_code, stdout, stderr = run_scenario(artefact_path, trace_path)
        actual_result = "pass" if exit_code == 0 else "fail"
        ok = actual_result == expected_result
        all_ok = all_ok and ok

        status = "OK      " if ok else "MISMATCH"
        trace_note = f"--trace {trace_filename}" if trace_filename else "(no --trace)"
        print(
            f"[{status}] {scenario_name} {trace_note}: "
            f"expected={expected_result}, actual={actual_result} (exit code {exit_code})"
        )
        if not ok:
            print("          --- validator output (diagnostic, not asserted against) ---")
            for line in (stdout + stderr).splitlines():
                print(f"          {line}")

    print()
    if all_ok:
        print("ALL SCENARIOS MATCH EXPECTED BEHAVIOUR.")
        return 0
    else:
        print("ONE OR MORE SCENARIOS DID NOT MATCH EXPECTED BEHAVIOUR.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
