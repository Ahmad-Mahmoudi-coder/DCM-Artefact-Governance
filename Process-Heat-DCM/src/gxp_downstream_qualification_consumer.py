"""
GXP Downstream Qualification Consumer -- Retained Reproduction Script

Persists, as a reusable script, the Path A / Path B downstream decision reproduction
first run ad hoc for docs/81 (Phase 2 Downstream Consumer Qualification Experiment) and
regression-checked once before as VAL-032. This script performs no new modelling and
introduces no new decision logic beyond one small, explicitly documented selection wrapper.

PROVENANCE
----------
- Reuses, by direct import (not by copying source), the following functions from
  Process-Heat-DCM/src/gxp_rdm_screen.py, unmodified:
    * load_upgrade_menu()
    * compute_annualised_cost()          (called internally by evaluate_upgrade_option())
    * evaluate_upgrade_option()
  These three functions are imported directly from the gxp_rdm_screen module and are not
  redefined, re-copied, or edited anywhere in this file. Their behaviour is therefore
  identical to the shipped module by construction, not merely "not altered."
- Adds exactly one new, small selection wrapper, select_adequate_upgrade(), which
  reproduces the "smallest zero-exceedance upgrade, in ascending capacity order" logic
  documented in docs/81 section 7. This wrapper did not exist in gxp_rdm_screen.py; it
  does not alter, duplicate, or replace gxp_rdm_screen.py's own cost-minimising
  evaluate_future() logic, which is not used by this script (docs/81 section 7 explains
  why: applying evaluate_future()'s annualised-cost minimisation to a single scalar peak
  would price one hour of shed against a full year of capex).
- Uses the real upgrade-menu TOML (Process-Heat-DCM/Input/configs/grid_upgrades_southland_edendale.toml),
  the real futures.csv (Process-Heat-DCM/Output/runs/dispatch_optimal_subset_canonical_continuous_v1/rdm/futures.csv),
  and the real declared peak_incremental_mw values read directly from the six governed
  IncrementalElectricityPack artefact instances named in CASES below. No synthetic or
  hand-typed input values are used anywhere in this script.

PATH A vs PATH B -- STATUS OF EACH INTERPRETATION (read before reusing this script)
------------------------------------------------------------------------------------
Path A ("naive consumer"): treats each artefact instance's declared peak_incremental_mw as
if it were already this future's own value, and uses it unmodified as the demand input for
the adequacy screen. This reproduces docs/81 section 7 exactly.

Path B ("governance-aware consumer"): applies
    adjusted_peak = peak_incremental_mw * U_inc_mult[future_id]
before the same adequacy screen. This reproduces docs/81 section 8 exactly. U_inc_mult is
the same scaling relationship gxp_rdm_screen.py's own evaluate_future() already applies
internally to the raw hourly series before computing exceedance -- it is not a new
multiplier invented for this script.

Path B in this script is an ANALYST-APPLIED interpretation, not a programmatic one:
  * This script does NOT decide, on its own, which of Path A or Path B is "correct" for a
    given case. Both paths are computed unconditionally, for every case, exactly as
    docs/81 computed them.
  * qualification_codes is read from each artefact instance ONLY for disclosure in the
    output result table and manifest. It is NOT used anywhere in this script's control
    flow to select Path A vs Path B, to branch, or to alter any calculation. (Repository-
    wide, the only script that consumes qualification_codes programmatically is
    Process-Heat-DCM/src/validate_biomass_supply_pack.py, for the BiomassSupplyPack
    family only -- confirmed by grep, 2026-09-15. No IEP/GXP script, including this one,
    reads qualification_codes programmatically.)
  * This script does not claim to have discovered, detected, or automatically inferred the
    shared-trace limitation that motivates Path B. The interpretive judgement that Path B
    is the governance-aware reading is a human judgement recorded in docs/81 sections 5,
    8 and 9; this script only reproduces the arithmetic consequence of applying that
    already-disclosed interpretation.

REQUIRED CASES
--------------
2035_EB future_id in {0, 5, 20}; 2035_BB future_id in {0, 5, 20} -- see CASES below.

WHAT THIS SCRIPT DOES NOT DO
-----------------------------
Does not modify gxp_rdm_screen.py or any other production script. Does not modify any
schema, any of the 42 IncrementalElectricityPack artefact instances, futures.csv, the
upgrade-menu TOML, or any existing validation record. Does not rerun the process-heat
dispatch model or regenerate the uncertainty ensemble. Does not change U_inc_mult=1.05 or
introduce any new uncertainty assumption. Does not implement a general qualification
engine.
"""

from __future__ import annotations

import csv
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PHD_ROOT = Path(__file__).resolve().parents[1]   # .../Process-Heat-DCM
REPO_ROOT = Path(__file__).resolve().parents[2]  # .../Decision (repo root)

if str(PHD_ROOT) not in sys.path:
    sys.path.insert(0, str(PHD_ROOT))

# Reused verbatim, unmodified, by direct import -- NOT copied/redefined in this file.
from src.gxp_rdm_screen import (  # noqa: E402
    load_upgrade_menu,
    evaluate_upgrade_option,
)

# Release staging edit: optional UPGRADE_MENU_TOML override of the menu path.
UPGRADE_TOML = Path(os.environ.get(
    "UPGRADE_MENU_TOML", str(PHD_ROOT / "Input" / "configs" / "grid_upgrades_southland_edendale.toml")))
FUTURES_CSV = PHD_ROOT / "Output" / "runs" / "dispatch_optimal_subset_canonical_continuous_v1" / "rdm" / "futures.csv"
ARTEFACT_DIR = REPO_ROOT / "artefacts" / "incremental_electricity_pack" / "anchor_21_canonical_continuous_v1"

# Same base constant as gxp_rdm_screen.py's load_or_generate_headroom() deterministic PoC
# fallback (line ~168): base_headroom = 50.0. Reused here as a documented scalar constant
# rather than by calling that function, which expects a DatetimeIndex for an hourly series,
# not a single-point screen (docs/81 section 7).
BASE_HEADROOM_MW = 50.0

CASES = [
    ("2035_EB", 0), ("2035_EB", 5), ("2035_EB", 20),
    ("2035_BB", 0), ("2035_BB", 5), ("2035_BB", 20),
]


def _rel(path: Path) -> str:
    """Repository-relative path, or 'external:<name>' for inputs supplied outside the repository."""
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT)).replace(os.sep, '/')
    except ValueError:
        return f"external:{Path(path).name}"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_artefact(pathway_id: str, future_id: int) -> dict:
    fname = f"incremental_electricity_pack.anchor_21.{pathway_id}.future_{future_id}.v1.0-current.json"
    fpath = ARTEFACT_DIR / fname
    data = json.loads(fpath.read_text())
    return {
        "path": _rel(fpath),
        "artefact_id": data["artefact_id"],
        "peak_incremental_mw": data["peak_incremental_mw"],
        "qualification_codes": data.get("qualification_codes", []),
        "sha256": sha256_of(fpath),
    }


def select_adequate_upgrade(demand_mw: float, headroom_mw: float, upgrades: list, assumptions: dict, future_row: dict):
    """
    New wrapper (not present in gxp_rdm_screen.py): select the smallest-capacity upgrade
    option, in ascending capacity order, for which evaluate_upgrade_option() reports zero
    exceedance (hours_exceed == 0). Reproduces docs/81 section 7's documented selection
    rule exactly. Calls evaluate_upgrade_option() unmodified, via direct import, for every
    candidate; performs no cost-minimisation and does not call evaluate_future().
    """
    incremental = pd.Series([demand_mw])
    headroom = pd.Series([headroom_mw])
    ordered = sorted(upgrades, key=lambda u: float(u.get("capacity_MW", 0)))
    trace = []
    for upgrade in ordered:
        metrics = evaluate_upgrade_option(incremental, headroom, upgrade, assumptions, future_row, dt_h=1.0)
        trace.append({
            "upgrade_name": upgrade["name"],
            "capacity_MW": float(upgrade.get("capacity_MW", 0)),
            "max_exceed_MW": metrics["max_exceed_MW"],
            "hours_exceed": metrics["hours_exceed"],
        })
        if metrics["hours_exceed"] == 0:
            return upgrade["name"], float(upgrade.get("capacity_MW", 0)), trace
    return None, None, trace


def run():
    upgrades, assumptions = load_upgrade_menu(UPGRADE_TOML)  # unmodified, reused function
    futures_df = pd.read_csv(FUTURES_CSV)

    results = []
    for pathway_id, future_id in CASES:
        artefact = load_artefact(pathway_id, future_id)
        peak = artefact["peak_incremental_mw"]

        frow = futures_df.loc[futures_df["future_id"] == future_id].iloc[0].to_dict()
        u_headroom_mult = float(frow["U_headroom_mult"])
        u_inc_mult = float(frow["U_inc_mult"])
        headroom_mw = BASE_HEADROOM_MW * u_headroom_mult

        # Path A -- naive consumer: demand = declared peak, as-is (docs/81 section 7)
        demand_a = peak
        name_a, cap_a, _trace_a = select_adequate_upgrade(demand_a, headroom_mw, upgrades, assumptions, frow)

        # Path B -- governance-aware consumer: demand = declared peak * U_inc_mult[future_id]
        # (docs/81 section 8)
        demand_b = peak * u_inc_mult
        name_b, cap_b, _trace_b = select_adequate_upgrade(demand_b, headroom_mw, upgrades, assumptions, frow)

        results.append({
            "pathway_id": pathway_id,
            "future_id": future_id,
            "artefact_id": artefact["artefact_id"],
            "artefact_path": artefact["path"],
            "artefact_sha256": artefact["sha256"],
            "qualification_codes": ";".join(artefact["qualification_codes"]),
            "declared_peak_incremental_mw": peak,
            "U_headroom_mult": u_headroom_mult,
            "U_inc_mult": u_inc_mult,
            "reference_headroom_mw": headroom_mw,
            "path_a_demand_mw": demand_a,
            "path_a_selected_upgrade": name_a,
            "path_a_selected_capacity_MW": cap_a,
            "path_b_demand_mw": demand_b,
            "path_b_selected_upgrade": name_b,
            "path_b_selected_capacity_MW": cap_b,
            "path_a_b_diverge": (name_a != name_b),
        })

    return results, upgrades, assumptions


if __name__ == "__main__":
    _parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    _parser.add_argument("--out-dir", type=Path, default=None,
                         help="Output directory (default: Process-Heat-DCM/Output/runs/gxp_downstream_qualification_consumer_v1)")
    _args = _parser.parse_args()
    results, upgrades, assumptions = run()

    print(f"{'pathway':10s} {'future':7s} {'PathA demand':>13s} {'PathA sel':>28s} {'PathB demand':>13s} {'PathB sel':>28s} {'diverge':>8s}")
    for r in results:
        print(f"{r['pathway_id']:10s} {r['future_id']:<7d} {r['path_a_demand_mw']:>13.6f} {r['path_a_selected_upgrade']:>28s} {r['path_b_demand_mw']:>13.6f} {r['path_b_selected_upgrade']:>28s} {str(r['path_a_b_diverge']):>8s}")

    out_dir = _args.out_dir or (PHD_ROOT / "Output" / "runs" / "gxp_downstream_qualification_consumer_v1")
    out_dir.mkdir(parents=True, exist_ok=True)

    result_csv = out_dir / "gxp_downstream_qualification_consumer_result.csv"
    fieldnames = list(results[0].keys())
    with open(result_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow(r)

    manifest = {
        "bundle_version": "gxp_downstream_qualification_consumer_v1",
        "output_run_id": "gxp_downstream_qualification_consumer_v1",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authorising_instruction": "User instruction accepting the Next-Revision Evidence & "
                                    "Contribution Decision Report's recommendation, with "
                                    "terminology correction (\"retrospective staged capability "
                                    "comparison\", not \"governance ablation\"); Task A: persist "
                                    "the existing GXP downstream consumer. 2026-09-15.",
        "script_identity": "Process-Heat-DCM/src/gxp_downstream_qualification_consumer.py",
        "reused_unmodified_functions_by_direct_import": [
            "Process-Heat-DCM/src/gxp_rdm_screen.py:load_upgrade_menu",
            "Process-Heat-DCM/src/gxp_rdm_screen.py:compute_annualised_cost (called internally by evaluate_upgrade_option)",
            "Process-Heat-DCM/src/gxp_rdm_screen.py:evaluate_upgrade_option",
        ],
        "new_logic_added": [
            "select_adequate_upgrade() -- smallest zero-exceedance upgrade, ascending "
            "capacity order (docs/81 section 7 wrapper); not present in gxp_rdm_screen.py"
        ],
        "inputs": {
            "upgrade_menu_toml": _rel(UPGRADE_TOML),
            "upgrade_menu_toml_sha256": sha256_of(UPGRADE_TOML),
            "futures_csv": _rel(FUTURES_CSV),
            "futures_csv_sha256": sha256_of(FUTURES_CSV),
            "artefact_instances": [
                {"pathway_id": r["pathway_id"], "future_id": r["future_id"],
                 "path": r["artefact_path"], "sha256": r["artefact_sha256"]}
                for r in results
            ],
        },
        "comparison_source": "docs/81_phase2_downstream_consumer_qualification_experiment.qmd sections 7-8",
        "path_a_status": "reproduces docs/81 section 7 (naive consumer) exactly",
        "path_b_status": "reproduces docs/81 section 8 (governance-aware consumer) exactly; "
                          "Path B remains an ANALYST-APPLIED interpretation in this script -- "
                          "qualification_codes is read here only for disclosure in the result "
                          "table/manifest, and is NOT used programmatically to select between "
                          "Path A and Path B or to alter any calculation.",
        # Release staging edit: derived from the computed results rather than a hard-coded string.
        "known_flip_case": "; ".join(
            f"{r['pathway_id']} future_id={r['future_id']}: Path A selects {r['path_a_selected_upgrade']} "
            f"({r['path_a_selected_capacity_MW']:g} MW), Path B selects {r['path_b_selected_upgrade']} "
            f"({r['path_b_selected_capacity_MW']:g} MW)" for r in results if r["path_a_b_diverge"]),
        "does_not_claim": [
            "does not claim autonomous discovery of the shared-trace limitation",
            "does not claim qualification_codes is consumed programmatically by any IEP/GXP script",
            "does not modify gxp_rdm_screen.py, any schema, any artefact instance, futures.csv, "
            "the upgrade-menu TOML, or any existing validation record",
        ],
    }
    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nWrote {result_csv}")
    print(f"Wrote {out_dir / 'manifest.json'}")
