#!/usr/bin/env python3
"""Narrow real-output adapter: IncrementalElectricityPack v1.0-current, anchor_21 only.

Authorised by docs/29_real_output_adapter_authorisation.qmd, following the
inventory in docs/28_real_output_source_inventory_and_adapter_plan.qmd.

Scope (binding, per docs/29):
  - Targets the anchor_21 future set ONLY (future_id 0-20). Never release02_100.
  - Reads real repository output files read-only. Mutates no source file.
  - Reads the future-id registry read-only, only to confirm anchor_21
    membership. Mutates no registry file.
  - Does not call or modify tools/validate_incremental_electricity_pack_external.py
    or tools/check_future_id_registry.py.
  - Does not patch the schema, does not create a v1.1-target schema, does not
    add a future_set_id field to any artefact.
  - Generates candidate IncrementalElectricityPack v1.0-current JSON artefacts
    ONLY if every required field can be populated honestly. If a required
    source file is missing or a required value cannot be derived, the script
    reports the failure and exits without writing any artefact. That is a
    valid, expected outcome of this script, not a bug.

BINDING CAVEAT (must not be hidden or omitted from any output produced by
this script or by docs/30_anchor21_real_output_adapter_creation.qmd):

    peak_incremental_mw and p95_incremental_mw are pathway-level
    trace-derived values repeated across futures for schema compatibility,
    not independently future-specific quantities.

This is because docs/28 found, on direct RDM-experiment-configuration
evidence, that every future within a pathway shares one common hourly
incremental-electricity trace file; only annual_incremental_mwh genuinely
varies per future in the real repository outputs inspected so far.

run_id and site_id are populated using explicitly labelled adapter
conventions (see RUN_ID_TEMPLATE and SITE_ID below), not resolved against any
global run-registry or site-registry. This does not resolve run_id.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Fixed, documented locations (relative to the repository root).
# ---------------------------------------------------------------------------

SET_REGISTRY_PATH = Path("registry/future_sets/future_set_registry.v1.csv")
MEMBER_REGISTRY_PATH = Path("registry/future_sets/future_member_registry.v1.csv")
SCHEMA_PATH = Path("schemas/artefacts/incremental_electricity_pack.v1.0-current.schema.json")

FUTURE_SET_ID = "anchor_21"

# Per-future annual_incremental_MWh source, one file per pathway. These are
# the explicit "21f_backup" snapshots inside the live release02 rdm/ folder,
# identified in docs/28 Section 4.
#
# docs/55_canonical_downstream_grid_rdm_and_anchor21_regeneration.qmd note: these
# module-level constants are the ORIGINAL, UNCHANGED defaults (still pointing at
# poc_20260105_release02). They are used as-is by every existing call site and by
# this script's own CLI defaults, so historical behaviour is completely unaffected.
# docs/55 added optional CLI overrides (below, in build_arg_parser/main) that let
# this same adapter be pointed at a different, explicitly-named source bundle
# (e.g. a canonical-dispatch-derived downstream bundle) without touching these
# defaults or the adapter's field-construction logic. When no override is passed,
# every path/id below is used exactly as originally authored.
RDM_SUMMARY_SOURCES = {
    "2035_BB": Path(
        "Process-Heat-RDM/Output/runs/poc_20260105_release02/rdm/"
        "rdm_summary_2035_BB__21f_backup.csv"
    ),
    "2035_EB": Path(
        "Process-Heat-RDM/Output/runs/poc_20260105_release02/rdm/"
        "rdm_summary_2035_EB__21f_backup.csv"
    ),
}

# Shared, pathway-level (not per-future) peak/p95 source. See docs/28 Section 5
# and the binding caveat above.
EPOCH_SUMMARY_PATH = Path(
    "Process-Heat-RDM/Output/runs/poc_20260105_release02/thesis_pack/"
    "incremental_electricity_epoch_summary.csv"
)

EPOCH = 2035

OUTPUT_DIR = Path("artefacts/incremental_electricity_pack/anchor_21")

SCHEMA_VERSION = "v1.0-current"
ARTEFACT_FAMILY = "IncrementalElectricityPack"

# Authorised adapter convention (docs/29 Section 6): the schema's only
# accepted site_id enum value. This is NOT a claim that the naming
# discrepancy docs/28 found (real config value "11_031") has been resolved.
SITE_ID = "edendale_fonterra"

# Authorised adapter convention (docs/29 Section 6, Section 8): an explicitly
# labelled, deterministic run_id distinct from any real run_manifest.json
# value. Does NOT resolve the global run_id registry problem.
RUN_ID_TEMPLATE = "ADAPTER-anchor21-realoutput-release02-{pathway_id}"

VALIDATION_OUTCOME = "manual_review_required"

# docs/83: qualification-stage codes are populated only for the
# anchor_21_canonical_continuous_v1 generation (identified by
# --run-id-label canonical_continuous_v1). The historical default
# generation (no --run-id-label) must omit this field entirely.
CANONICAL_CONTINUOUS_V1_RUN_ID_LABEL = "canonical_continuous_v1"
QUALIFICATION_CODES = ["FIELD_INVARIANT_ACROSS_FUTURES_WITHIN_PATHWAY"]

# Deterministic artefact_id namespace (UUID5), so repeated runs against the
# same inputs produce the same artefact_id for the same (pathway_id, future_id).
ARTEFACT_ID_NAMESPACE = uuid.NAMESPACE_URL
ARTEFACT_ID_PREFIX = "https://dcm.local/artefacts/incremental_electricity_pack/anchor_21"


class AdapterPreconditionError(Exception):
    """Raised when a required source cannot be honestly used. Not a bug."""


def read_csv_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def load_anchor21_future_ids() -> list[int]:
    """Read the registry read-only and return anchor_21's registered future_id
    values. Confirms membership only; does not modify either registry file."""
    if not SET_REGISTRY_PATH.exists():
        raise AdapterPreconditionError(f"Missing set registry file: {SET_REGISTRY_PATH}")
    if not MEMBER_REGISTRY_PATH.exists():
        raise AdapterPreconditionError(f"Missing member registry file: {MEMBER_REGISTRY_PATH}")

    set_rows = read_csv_rows(SET_REGISTRY_PATH)
    anchor_set_rows = [r for r in set_rows if r.get("future_set_id") == FUTURE_SET_ID]
    if len(anchor_set_rows) != 1:
        raise AdapterPreconditionError(
            f"Expected exactly one {FUTURE_SET_ID!r} row in the set registry, found {len(anchor_set_rows)}"
        )
    declared_count = int(anchor_set_rows[0]["future_count"])

    member_rows = read_csv_rows(MEMBER_REGISTRY_PATH)
    future_ids = sorted(
        int(r["future_id"]) for r in member_rows if r.get("future_set_id") == FUTURE_SET_ID
    )
    if len(future_ids) != declared_count:
        raise AdapterPreconditionError(
            f"{FUTURE_SET_ID!r} member count {len(future_ids)} does not match "
            f"set registry future_count {declared_count}"
        )
    expected = list(range(future_ids[0], future_ids[-1] + 1)) if future_ids else []
    if future_ids != expected:
        raise AdapterPreconditionError(f"{FUTURE_SET_ID!r} future_id values are not contiguous")

    return future_ids


def load_per_future_annual_mwh(
    pathway_id: str, expected_future_ids: list[int],
    rdm_summary_sources: dict[str, Path] = RDM_SUMMARY_SOURCES,
) -> dict[int, float]:
    source_path = rdm_summary_sources[pathway_id]
    if not source_path.exists():
        raise AdapterPreconditionError(f"Missing rdm_summary source for {pathway_id}: {source_path}")

    rows = read_csv_rows(source_path)
    values: dict[int, float] = {}
    for row in rows:
        try:
            fid = int(row["future_id"])
            annual_mwh = float(row["annual_incremental_MWh"])
        except (KeyError, ValueError) as exc:
            raise AdapterPreconditionError(
                f"Malformed row in {source_path}: could not read future_id/annual_incremental_MWh ({exc})"
            )
        values[fid] = annual_mwh

    missing = sorted(set(expected_future_ids) - set(values))
    if missing:
        raise AdapterPreconditionError(
            f"{source_path} is missing annual_incremental_MWh for future_id(s): {missing}"
        )
    return {fid: values[fid] for fid in expected_future_ids}


def load_pathway_peak_p95(
    pathway_id: str, epoch_summary_path: Path = EPOCH_SUMMARY_PATH,
) -> tuple[float, float]:
    if not epoch_summary_path.exists():
        raise AdapterPreconditionError(f"Missing epoch summary source: {epoch_summary_path}")

    rows = read_csv_rows(epoch_summary_path)
    matching = [r for r in rows if r.get("epoch_tag") == pathway_id]
    if len(matching) != 1:
        raise AdapterPreconditionError(
            f"Expected exactly one {pathway_id!r} row in {epoch_summary_path}, found {len(matching)}"
        )
    row = matching[0]
    try:
        peak_mw = float(row["peak_MW"])
        p95_mw = float(row["p95_MW"])
    except (KeyError, ValueError) as exc:
        raise AdapterPreconditionError(
            f"Malformed row in {epoch_summary_path} for {pathway_id}: could not read peak_MW/p95_MW ({exc})"
        )
    if p95_mw > peak_mw:
        raise AdapterPreconditionError(
            f"{pathway_id}: source p95_MW ({p95_mw}) exceeds peak_MW ({peak_mw}); refusing to build artefacts"
        )
    return peak_mw, p95_mw


def build_artefact_id(pathway_id: str, future_id: int, artefact_id_prefix: str = ARTEFACT_ID_PREFIX) -> str:
    name = f"{artefact_id_prefix}/{pathway_id}/future_{future_id}"
    return str(uuid.uuid5(ARTEFACT_ID_NAMESPACE, name))


def build_artefact(
    pathway_id: str, future_id: int, annual_mwh: float, peak_mw: float, p95_mw: float,
    run_id_template: str = RUN_ID_TEMPLATE, artefact_id_prefix: str = ARTEFACT_ID_PREFIX,
    include_qualification_codes: bool = False,
) -> dict:
    # docs/55: run_id_template and artefact_id_prefix are optional overrides (default to the
    # original module constants). Overriding them when the *source data* genuinely differs (a
    # different dispatch/RDM run) is required, not merely cosmetic: artefact_id is a uuid5 hash
    # of (prefix, pathway_id, future_id), so two artefacts built from genuinely different source
    # data would otherwise collide on the same artefact_id despite having different content --
    # see docs/55 Section on ARTEFACT_IDENTITY_CLARIFICATION. Still just an adapter-assigned
    # labelling convention; does not resolve any global run_id/artefact_id registry.
    artefact = {
        "artefact_id": build_artefact_id(pathway_id, future_id, artefact_id_prefix=artefact_id_prefix),
        "schema_version": SCHEMA_VERSION,
        "artefact_family": ARTEFACT_FAMILY,
        "site_id": SITE_ID,
        "run_id": run_id_template.format(pathway_id=pathway_id),
        "future_id": future_id,
        "pathway_id": pathway_id,
        "epoch": EPOCH,
        "annual_incremental_mwh": annual_mwh,
        "peak_incremental_mw": peak_mw,
        "p95_incremental_mw": p95_mw,
        "validation_outcome": VALIDATION_OUTCOME,
    }
    # docs/83 §E/§L: populate qualification_codes only for the canonical
    # continuous-v1 generation. Historical default generation omits the field.
    if include_qualification_codes:
        artefact["qualification_codes"] = list(QUALIFICATION_CODES)
    return artefact


def load_schema_validator():
    from jsonschema import Draft202012Validator

    with SCHEMA_PATH.open(encoding="utf-8") as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def generate_candidate_artefacts(
    rdm_summary_sources: dict[str, Path] = RDM_SUMMARY_SOURCES,
    epoch_summary_path: Path = EPOCH_SUMMARY_PATH,
    run_id_template: str = RUN_ID_TEMPLATE,
    artefact_id_prefix: str = ARTEFACT_ID_PREFIX,
    include_qualification_codes: bool = False,
) -> tuple[list[dict], list[str]]:
    """Build every candidate artefact in memory. Returns (artefacts, pathway_report_lines).

    Raises AdapterPreconditionError if the registry itself cannot be trusted.
    A pathway with a missing/invalid source is skipped (not fatal) and noted
    in the report, provided at least the registry precondition holds.

    docs/55: rdm_summary_sources/epoch_summary_path/run_id_template/artefact_id_prefix are
    optional overrides that all default to the original module constants -- calling this
    function with no arguments reproduces the exact original behaviour.
    """
    future_ids = load_anchor21_future_ids()

    validator = load_schema_validator()

    artefacts: list[dict] = []
    report_lines: list[str] = []

    for pathway_id in sorted(rdm_summary_sources):
        try:
            annual_by_future = load_per_future_annual_mwh(pathway_id, future_ids, rdm_summary_sources=rdm_summary_sources)
            peak_mw, p95_mw = load_pathway_peak_p95(pathway_id, epoch_summary_path=epoch_summary_path)
        except AdapterPreconditionError as exc:
            report_lines.append(f"SKIPPED {pathway_id}: {exc}")
            continue

        pathway_artefacts = []
        for future_id in future_ids:
            artefact = build_artefact(
                pathway_id=pathway_id,
                future_id=future_id,
                annual_mwh=annual_by_future[future_id],
                peak_mw=peak_mw,
                p95_mw=p95_mw,
                run_id_template=run_id_template,
                artefact_id_prefix=artefact_id_prefix,
                include_qualification_codes=include_qualification_codes,
            )
            errors = sorted(validator.iter_errors(artefact), key=str)
            if errors:
                raise AdapterPreconditionError(
                    f"Constructed artefact for {pathway_id} future_id={future_id} "
                    f"fails schema validation: {errors[0].message}"
                )
            pathway_artefacts.append(artefact)

        artefacts.extend(pathway_artefacts)
        report_lines.append(
            f"OK {pathway_id}: {len(pathway_artefacts)} artefacts "
            f"(peak_incremental_mw={peak_mw}, p95_incremental_mw={p95_mw}, shared across all futures)"
        )

    return artefacts, report_lines


def artefact_filename(artefact: dict) -> str:
    return (
        f"incremental_electricity_pack.anchor_21."
        f"{artefact['pathway_id']}.future_{artefact['future_id']}.v1.0-current.json"
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Narrow real-output adapter for IncrementalElectricityPack v1.0-current, "
            "anchor_21 only. Exactly one of --dry-run or --write is required."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect sources and report what would be generated, without writing any file.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Generate and write candidate artefact JSON files under artefacts/incremental_electricity_pack/anchor_21/.",
    )
    # docs/55_canonical_downstream_grid_rdm_and_anchor21_regeneration.qmd: optional overrides,
    # all defaulting to None. When none are supplied, every original module-level constant is
    # used exactly as before -- this reproduces this script's original behaviour byte-for-byte.
    # They exist to let this same authorised adapter be pointed at a different, explicitly-named
    # source bundle (e.g. a canonical-dispatch-derived downstream bundle) without ever touching
    # its field-construction logic, schema, or the poc_20260105_release02 defaults.
    parser.add_argument(
        "--source-bundle-dir", type=Path, default=None,
        help=(
            "Override source bundle directory (e.g. Process-Heat-RDM/Output/runs/<bundle>). "
            "If supplied, RDM_SUMMARY_SOURCES and EPOCH_SUMMARY_PATH are re-derived under this "
            "bundle using the same relative layout (rdm/rdm_summary_<pathway>.csv and "
            "thesis_pack/incremental_electricity_epoch_summary.csv) instead of the "
            "poc_20260105_release02 defaults."
        ),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Override output directory (default: artefacts/incremental_electricity_pack/anchor_21/).",
    )
    parser.add_argument(
        "--run-id-label", type=str, default=None,
        help=(
            "Override the adapter-assigned run_id/artefact_id-namespace label (default: "
            "'release02'). Use a distinct label when the source bundle is not release02, so "
            "artefacts built from genuinely different source data do not share a run_id or "
            "artefact_id with the historical release02-derived artefacts."
        ),
    )
    return parser


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.dry_run == args.write:
        print("FAIL: exactly one of --dry-run or --write must be supplied")
        return 1

    rdm_summary_sources = RDM_SUMMARY_SOURCES
    epoch_summary_path = EPOCH_SUMMARY_PATH
    run_id_template = RUN_ID_TEMPLATE
    artefact_id_prefix = ARTEFACT_ID_PREFIX
    output_dir = args.output_dir if args.output_dir is not None else OUTPUT_DIR
    include_qualification_codes = args.run_id_label == CANONICAL_CONTINUOUS_V1_RUN_ID_LABEL

    if args.source_bundle_dir is not None:
        rdm_summary_sources = {
            pathway_id: args.source_bundle_dir / "rdm" / f"rdm_summary_{pathway_id}.csv"
            for pathway_id in RDM_SUMMARY_SOURCES
        }
        epoch_summary_path = args.source_bundle_dir / "thesis_pack" / "incremental_electricity_epoch_summary.csv"

    if args.run_id_label is not None:
        run_id_template = "ADAPTER-anchor21-realoutput-" + args.run_id_label + "-{pathway_id}"
        artefact_id_prefix = ARTEFACT_ID_PREFIX + "/" + args.run_id_label

    print(f"future_set_id: {FUTURE_SET_ID}")
    print(
        "BINDING CAVEAT: peak_incremental_mw and p95_incremental_mw are pathway-level "
        "trace-derived values repeated across futures for schema compatibility, "
        "not independently future-specific quantities."
    )
    print(f"run_id convention: {run_id_template.format(pathway_id='<pathway_id>')} (adapter-assigned, not a global run_id resolution)")
    if args.source_bundle_dir is not None:
        print(f"source bundle override: {args.source_bundle_dir}")
    if include_qualification_codes:
        print(
            "qualification_codes: "
            f"{QUALIFICATION_CODES} "
            f"(attached because --run-id-label={CANONICAL_CONTINUOUS_V1_RUN_ID_LABEL})"
        )
    else:
        print("qualification_codes: omitted (historical/default generation path)")
    print()

    try:
        artefacts, report_lines = generate_candidate_artefacts(
            rdm_summary_sources=rdm_summary_sources,
            epoch_summary_path=epoch_summary_path,
            run_id_template=run_id_template,
            artefact_id_prefix=artefact_id_prefix,
            include_qualification_codes=include_qualification_codes,
        )
    except AdapterPreconditionError as exc:
        print("FAIL: precondition not met; no artefact was generated.")
        print(f" - {exc}")
        return 1

    for line in report_lines:
        print(line)

    if not artefacts:
        print("FAIL: no pathway had all required sources available; no artefact was generated.")
        return 1

    pathways_covered = sorted({a["pathway_id"] for a in artefacts})
    future_ids_covered = sorted({a["future_id"] for a in artefacts})
    print()
    print(f"Total candidate artefacts: {len(artefacts)}")
    print(f"Pathways covered: {pathways_covered}")
    print(f"future_id range covered: {future_ids_covered[0]}-{future_ids_covered[-1]} ({len(future_ids_covered)} values)")

    if args.dry_run:
        print()
        print("Dry run only: no file was written.")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for artefact in artefacts:
        out_path = output_dir / artefact_filename(artefact)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(artefact, f, indent=2, sort_keys=True)
            f.write("\n")
        written.append(out_path)

    print()
    print(f"Wrote {len(written)} artefact files under {output_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
