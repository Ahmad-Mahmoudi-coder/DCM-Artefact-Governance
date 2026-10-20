"""Retrospective Path A / Path B screening replay across all 42 canonical IEP artefacts.

Added for the paper-specific release: the manuscript (Version 9, Sections 4.3 and 5.2)
reports a retrospective application of the retained wrapper's calculation functions to
all 42 artefacts, but no script for it was previously retained. This script applies the
retained consumer's select_adequate_upgrade() wrapper (which calls gxp_rdm_screen's
evaluate_upgrade_option()) to every artefact, unchanged.

Requires the grid-upgrade menu (Process-Heat-DCM/Input/configs/grid_upgrades_southland_edendale.toml).
Reported result checked: the selected tier changes in four cases (2035_EB futures 3, 5,
7 and 18) and, within the retained six-case subset, only 2035_EB future 5 changes.
Writes reproduction_outputs/all42_screening_replay.csv; exit 0 if the reported pattern is reproduced.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Process-Heat-DCM"))
from src.gxp_downstream_qualification_consumer import (  # noqa: E402
    ARTEFACT_DIR, BASE_HEADROOM_MW, CASES, FUTURES_CSV, UPGRADE_TOML,
    load_upgrade_menu, select_adequate_upgrade,
)

REPORTED_CHANGES = {("2035_EB", 3), ("2035_EB", 5), ("2035_EB", 7), ("2035_EB", 18)}

ap = argparse.ArgumentParser()
ap.add_argument("--out", type=Path, default=ROOT / "reproduction_outputs" / "all42_screening_replay.csv")
args = ap.parse_args()

if not Path(UPGRADE_TOML).is_file():
    print("[SKIP] grid-upgrade menu not found")
    sys.exit(3)

upgrades, assumptions = load_upgrade_menu(UPGRADE_TOML)
futures = pd.read_csv(FUTURES_CSV)
rows = []
for p in sorted(Path(ARTEFACT_DIR).glob("*.json")):
    a = json.loads(p.read_text(encoding="utf-8"))
    frow = futures.loc[futures["future_id"] == a["future_id"]].iloc[0].to_dict()
    headroom = BASE_HEADROOM_MW * float(frow["U_headroom_mult"])
    demand_a = a["peak_incremental_mw"]
    demand_b = demand_a * float(frow["U_inc_mult"])
    name_a, cap_a, _ = select_adequate_upgrade(demand_a, headroom, upgrades, assumptions, frow)
    name_b, cap_b, _ = select_adequate_upgrade(demand_b, headroom, upgrades, assumptions, frow)
    rows.append({"pathway_id": a["pathway_id"], "future_id": a["future_id"], "artefact_id": a["artefact_id"],
                 "reference_headroom_mw": headroom, "path_a_demand_mw": demand_a, "path_a_selected_upgrade": name_a,
                 "path_a_selected_capacity_MW": cap_a, "path_b_demand_mw": demand_b, "path_b_selected_upgrade": name_b,
                 "path_b_selected_capacity_MW": cap_b, "tier_changes": name_a != name_b})
rows.sort(key=lambda r: (r["pathway_id"], r["future_id"]))
args.out.parent.mkdir(parents=True, exist_ok=True)
with open(args.out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

changes = {(r["pathway_id"], r["future_id"]) for r in rows if r["tier_changes"]}
subset_changes = {c for c in changes if c in set(CASES)}
print(f"artefacts screened: {len(rows)}")
print(f"tier changes: {sorted(changes)}")
print(f"tier changes within the retained six-case subset {CASES}: {sorted(subset_changes)}")
ok = len(rows) == 42 and changes == REPORTED_CHANGES and subset_changes == {("2035_EB", 5)}
print("[PASS] reported all-42 pattern reproduced" if ok else "[FAIL] result differs from the manuscript")
sys.exit(0 if ok else 1)
