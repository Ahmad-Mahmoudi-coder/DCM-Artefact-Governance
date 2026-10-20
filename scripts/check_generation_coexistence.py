"""Historical / canonical IEP generation coexistence check (VAL-019).

Added for the paper-specific release: VAL-019 was recorded from a harness run plus manual
inspection. This script makes the identity part repeatable: both directories hold 42
artefacts, every (pathway_id, future_id) pair has distinct artefact_id and run_id across
the two generations, and no artefact_id is shared between them. Exit 0 if all hold.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "artefacts" / "incremental_electricity_pack"
gens = {g: {(a["pathway_id"], a["future_id"]): a for a in
            (json.loads(p.read_text(encoding="utf-8")) for p in sorted((BASE / g).glob("*.json")))}
        for g in ["anchor_21", "anchor_21_canonical_continuous_v1"]}
hist, canon = gens["anchor_21"], gens["anchor_21_canonical_continuous_v1"]
checks = [
    ("historical generation has 42 artefacts", len(hist) == 42),
    ("canonical generation has 42 artefacts", len(canon) == 42),
    ("same (pathway, future) key set in both generations", set(hist) == set(canon)),
    ("artefact_id differs for every pair", all(hist[k]["artefact_id"] != canon[k]["artefact_id"] for k in hist)),
    ("run_id differs for every pair", all(hist[k]["run_id"] != canon[k]["run_id"] for k in hist)),
    ("no artefact_id collision across the 84 artefacts",
     len({a["artefact_id"] for a in list(hist.values()) + list(canon.values())}) == 84),
]
for label, cond in checks:
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
sys.exit(0 if all(c for _, c in checks) else 1)
