"""BiomassSupplyPack schema self-check (VAL-044): valid Draft 2020-12, closed, 29 required fields.

Added for the paper-specific release. Exit 3 if the schema file is absent.
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "artefacts" / "biomass_supply_pack.v1.0-current.schema.json"
if not SCHEMA.is_file():
    print(f"[SKIP] BSP schema not present: {SCHEMA.relative_to(ROOT)}")
    sys.exit(3)
s = json.loads(SCHEMA.read_text(encoding="utf-8"))
Draft202012Validator.check_schema(s)
checks = [("schema is valid Draft 2020-12", True),
          ("additionalProperties is false (closed)", s.get("additionalProperties") is False),
          (f"required field count = {len(s['required'])} (manuscript: 29)", len(s["required"]) == 29)]
for label, cond in checks:
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
sys.exit(0 if all(c for _, c in checks) else 1)
