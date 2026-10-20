#!/usr/bin/env python3
"""Standalone future-id registry checker.

Authorised by docs/24_future_id_registry_checker_authorisation.qmd, scoped by
docs/23_future_id_registry_validator_scope_decision.qmd.

This script checks the two future-id registry files created in
docs/22_future_id_registry_creation.qmd:

    registry/future_sets/future_set_registry.v1.csv    (set-level table)
    registry/future_sets/future_member_registry.v1.csv (member-level table)

It supports exactly two modes:

  --check-integrity
      Registry-integrity mode: checks that the two registry files are
      internally consistent (correct headers, expected row counts, unique
      future_set_id values, member/set count consistency, contiguous
      future_id ranges per set, no banned or unconfirmed future sets, no
      duplicate (future_set_id, future_id) pairs).

  --future-set-id / --future-id
      Pair-lookup mode: checks whether a supplied (future_set_id, future_id)
      pair exists in the member registry.

Both modes may be supplied together; the script exits 0 only if every
requested check passes.

Out of scope, by explicit authorisation (docs/24 Section 7): this script does
not validate IncrementalElectricityPack artefact instances, does not import
or call tools/validate_incremental_electricity_pack_external.py, does not
read hourly trace files, does not perform JSON Schema validation, does not
patch or interpret the v1.0-current schema, does not add a future_set_id
field to any artefact, does not resolve run_id, does not check provenance or
checksums, and does not use any database, provenance-standard, or
visualisation tooling. This script uses only the Python standard library and
mutates no file.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

DEFAULT_SET_REGISTRY = "registry/future_sets/future_set_registry.v1.csv"
DEFAULT_MEMBER_REGISTRY = "registry/future_sets/future_member_registry.v1.csv"

EXPECTED_SET_HEADER = [
    "future_set_id",
    "source_file",
    "source_role",
    "epoch",
    "pathway_scope",
    "future_count",
    "construction_method_or_status",
    "notes",
]

EXPECTED_MEMBER_HEADER = ["future_set_id", "future_id"]

EXPECTED_SET_ROW_COUNT = 2
EXPECTED_MEMBER_ROW_COUNT = 121

BANNED_FUTURE_SET_IDS = {"TEST_unserved_fix"}
UNCONFIRMED_FUTURE_COUNT = 200


def read_csv_exact_header(path: Path, expected_header: list[str]):
    """Read a CSV file, returning (header_matches, actual_header, rows_as_dicts).

    Fully blank lines (as seen in some repository CSV snapshots) are skipped.
    """
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        raw_rows = [row for row in reader if row]
    if not raw_rows:
        return False, [], []
    header = raw_rows[0]
    matches = header == expected_header
    rows = [dict(zip(header, row)) for row in raw_rows[1:]]
    return matches, header, rows


def load_registries(set_path: Path, member_path: Path):
    """Load both registry files read-only. Returns a dict of results and errors."""
    result = {
        "errors": [],
        "set_header": None,
        "set_rows": None,
        "member_header": None,
        "member_rows": None,
    }
    if not set_path.exists():
        result["errors"].append(f"Missing set registry file: {set_path}")
    if not member_path.exists():
        result["errors"].append(f"Missing member registry file: {member_path}")
    if result["errors"]:
        return result

    set_matches, set_header, set_rows = read_csv_exact_header(set_path, EXPECTED_SET_HEADER)
    member_matches, member_header, member_rows = read_csv_exact_header(
        member_path, EXPECTED_MEMBER_HEADER
    )
    result["set_header"] = set_header
    result["set_rows"] = set_rows
    result["member_header"] = member_header
    result["member_rows"] = member_rows

    if not set_matches:
        result["errors"].append(
            f"Set registry header mismatch: expected {EXPECTED_SET_HEADER}, got {set_header}"
        )
    if not member_matches:
        result["errors"].append(
            f"Member registry header mismatch: expected {EXPECTED_MEMBER_HEADER}, got {member_header}"
        )
    return result


def check_integrity(set_path: Path, member_path: Path):
    """Registry-integrity mode. Returns (ok, list_of_error_strings)."""
    loaded = load_registries(set_path, member_path)
    errors = list(loaded["errors"])

    if loaded["set_rows"] is None or loaded["member_rows"] is None:
        # Missing file(s); nothing further can be safely checked.
        return False, errors

    set_header_ok = loaded["set_header"] == EXPECTED_SET_HEADER
    member_header_ok = loaded["member_header"] == EXPECTED_MEMBER_HEADER
    if not set_header_ok or not member_header_ok:
        # Header errors already recorded above; row keys cannot be trusted.
        return False, errors

    set_rows = loaded["set_rows"]
    member_rows = loaded["member_rows"]

    if len(set_rows) != EXPECTED_SET_ROW_COUNT:
        errors.append(
            f"Set registry expected {EXPECTED_SET_ROW_COUNT} data row(s), found {len(set_rows)}"
        )
    if len(member_rows) != EXPECTED_MEMBER_ROW_COUNT:
        errors.append(
            f"Member registry expected {EXPECTED_MEMBER_ROW_COUNT} data row(s), found {len(member_rows)}"
        )

    set_ids = [r["future_set_id"] for r in set_rows]
    dup_set_ids = sorted({x for x in set_ids if set_ids.count(x) > 1})
    if dup_set_ids:
        errors.append(f"Duplicate future_set_id in set registry: {dup_set_ids}")

    set_id_set = set(set_ids)

    future_count_map = {}
    for row in set_rows:
        fsid = row["future_set_id"]
        raw_count = row["future_count"]
        try:
            future_count_map[fsid] = int(raw_count)
        except ValueError:
            errors.append(f"Non-integer future_count for {fsid!r}: {raw_count!r}")

    if BANNED_FUTURE_SET_IDS & set_id_set:
        errors.append(
            f"Banned future_set_id present in set registry: {sorted(BANNED_FUTURE_SET_IDS & set_id_set)}"
        )
    member_banned = {r["future_set_id"] for r in member_rows} & BANNED_FUTURE_SET_IDS
    if member_banned:
        errors.append(f"Banned future_set_id present in member registry: {sorted(member_banned)}")

    unconfirmed_rows = [
        fsid for fsid, count in future_count_map.items() if count == UNCONFIRMED_FUTURE_COUNT
    ]
    if unconfirmed_rows:
        errors.append(
            f"Unconfirmed {UNCONFIRMED_FUTURE_COUNT}-future set present in set registry: "
            f"{sorted(unconfirmed_rows)}"
        )

    unknown_refs = sorted({r["future_set_id"] for r in member_rows} - set_id_set)
    if unknown_refs:
        errors.append(f"Member registry references unknown future_set_id values: {unknown_refs}")

    parsed_members = []
    for row in member_rows:
        raw_fid = row["future_id"]
        try:
            fid = int(raw_fid)
        except ValueError:
            errors.append(
                f"Non-integer future_id in member registry: {raw_fid!r} "
                f"(future_set_id={row.get('future_set_id')!r})"
            )
            continue
        parsed_members.append((row["future_set_id"], fid))

    pair_counts: dict[tuple[str, int], int] = {}
    for pair in parsed_members:
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    dup_pairs = sorted(pair for pair, count in pair_counts.items() if count > 1)
    if dup_pairs:
        errors.append(f"Duplicate (future_set_id, future_id) pairs: {dup_pairs}")

    members_by_set: dict[str, list[int]] = {}
    for fsid, fid in parsed_members:
        members_by_set.setdefault(fsid, []).append(fid)

    for fsid in sorted(set_id_set):
        unique_ids = sorted(set(members_by_set.get(fsid, [])))
        expected_count = future_count_map.get(fsid)
        actual_count = len(unique_ids)
        if expected_count is not None and actual_count != expected_count:
            errors.append(
                f"future_count mismatch for {fsid!r}: set registry declares {expected_count}, "
                f"member registry has {actual_count} unique member(s)"
            )
        if not unique_ids:
            errors.append(f"{fsid!r} has no member rows in the member registry")
            continue
        expected_range = list(range(unique_ids[0], unique_ids[-1] + 1))
        contiguous = unique_ids == expected_range
        starts_at_zero = unique_ids[0] == 0
        if not contiguous or not starts_at_zero:
            errors.append(
                f"{fsid!r} future_id values are not a contiguous run starting at 0: "
                f"got range {unique_ids[0]}-{unique_ids[-1]}, count {len(unique_ids)}"
            )

    return (len(errors) == 0), errors


def check_pair_lookup(set_path: Path, member_path: Path, future_set_id: str, future_id: int):
    """Pair-lookup mode. Returns (ok, list_of_message_strings)."""
    errors = []
    if not set_path.exists():
        errors.append(f"Missing set registry file: {set_path}")
    if not member_path.exists():
        errors.append(f"Missing member registry file: {member_path}")
    if errors:
        return False, errors

    matches, member_header, member_rows = read_csv_exact_header(member_path, EXPECTED_MEMBER_HEADER)
    if not matches:
        errors.append(
            f"Member registry header mismatch: expected {EXPECTED_MEMBER_HEADER}, got {member_header}"
        )
        return False, errors

    for row in member_rows:
        try:
            row_future_id = int(row["future_id"])
        except (KeyError, ValueError):
            continue
        if row.get("future_set_id") == future_set_id and row_future_id == future_id:
            return True, [f"Pair found: {future_set_id},{future_id}"]

    return False, [f"Pair not found in member registry: {future_set_id},{future_id}"]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Standalone integrity and pair-lookup checker for the future-id registry."
    )
    parser.add_argument("--set-registry", default=DEFAULT_SET_REGISTRY)
    parser.add_argument("--member-registry", default=DEFAULT_MEMBER_REGISTRY)
    parser.add_argument("--check-integrity", action="store_true")
    parser.add_argument("--future-set-id", default=None)
    parser.add_argument("--future-id", default=None)
    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    set_path = Path(args.set_registry)
    member_path = Path(args.member_registry)

    has_set_id = args.future_set_id is not None
    has_future_id_arg = args.future_id is not None

    if has_set_id != has_future_id_arg:
        print("FAIL: --future-set-id and --future-id must be supplied together")
        return 1

    do_pair_lookup = has_set_id and has_future_id_arg

    if not args.check_integrity and not do_pair_lookup:
        print(
            "FAIL: nothing to do; supply --check-integrity and/or "
            "--future-set-id together with --future-id"
        )
        return 1

    overall_ok = True

    if args.check_integrity:
        ok, errors = check_integrity(set_path, member_path)
        if ok:
            print("PASS registry integrity")
        else:
            print("FAIL registry integrity")
            for error in errors:
                print(f" - {error}")
        overall_ok = overall_ok and ok

    if do_pair_lookup:
        try:
            future_id = int(args.future_id)
        except ValueError:
            print(f"FAIL pair lookup: --future-id must be an integer, got {args.future_id!r}")
            overall_ok = False
        else:
            ok, messages = check_pair_lookup(set_path, member_path, args.future_set_id, future_id)
            if ok:
                print(f"PASS pair lookup: {args.future_set_id} {future_id}")
            else:
                print(f"FAIL pair lookup: {args.future_set_id} {future_id}")
                for message in messages:
                    print(f" - {message}")
            overall_ok = overall_ok and ok

    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
