"""Single reproduction entry point for the paper-specific release.

Usage (from the repository root, in an environment built from requirements-paper.txt):
    python reproduce.py            # run every step whose inputs are present
    python reproduce.py --list     # list steps, manuscript items and required inputs

Each step runs as a separate process; its console output is saved under
reproduction_outputs/logs/. Steps whose inputs are absent are reported as
SKIPPED (not as passes). Nothing outside reproduction_outputs/ is written.
Exit status: 0 if every performed step met its expectation, 1 otherwise.

Steps S01-S22 (25 steps) reproduce the manuscript's reported checks and values (manuscript
Version 9). S20 verifies the screening tier mapping from the screening code; S21 renders manuscript
Figure 2 and S22 confirms it is identical to the published file. S11 and S15 render the two
Version 8 data figures, which are kept as supplementary checks and are not in Version 9.
Steps E1-E2 are supplementary regeneration checks (IEP adapter; BSP producer chain).
All inputs needed by every step are included in this package.

This entry point re-executes the governance checks, recomputations, screening
calculations and figures from the supplied inputs. It does not rerun the upstream
process-heat dispatch model, regenerate the hourly traces, or regenerate the
future-specific multipliers; those are supplied as inputs.
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "reproduction_outputs"
LOGS = OUT / "logs"
PHD = ROOT / "Process-Heat-DCM"
CANON = PHD / "Output" / "runs" / "dispatch_optimal_subset_canonical_continuous_v1"
ART = ROOT / "artefacts" / "incremental_electricity_pack" / "anchor_21_canonical_continuous_v1"
TRACE = {p: CANON / f"epoch{p}" / "dispatch" / "optimal_subset_run" / "signals" / f"incremental_electricity_MW_{p}.csv"
         for p in ["2035_EB", "2035_BB"]}
MENU = Path(os.environ.get("UPGRADE_MENU_TOML", PHD / "Input" / "configs" / "grid_upgrades_southland_edendale.toml"))
BSP_SCHEMA = ROOT / "schemas" / "artefacts" / "biomass_supply_pack.v1.0-current.schema.json"
BSP_VALIDATOR = PHD / "src" / "validate_biomass_supply_pack.py"
BSP_INSTANCE = PHD / "Output" / "runs" / "biomass_supply_pack_v1" / "biomass_supply_pack.v1.0.json"
BSP_FIXTURES = ROOT / "schemas" / "examples"


def display(cmd):
    """Command line for logs, with machine-specific absolute paths shown relative to the repository."""
    parts = ["python" if c == sys.executable else str(c) for c in cmd]
    return " ".join(str(Path(c).relative_to(ROOT)) if Path(c).is_absolute() and str(c).startswith(str(ROOT)) else c for c in parts)


def art(p, f):
    return str(ART / f"incremental_electricity_pack.anchor_21.{p}.future_{f}.v1.0-current.json")


PY = sys.executable
INPUTS = {
    "core": lambda: ART.is_dir() and all(t.is_file() for t in TRACE.values()),
    "upgrade_menu": lambda: MENU.is_file(),
    "bsp": lambda: BSP_SCHEMA.is_file() and BSP_VALIDATOR.is_file() and BSP_INSTANCE.is_file(),
}

# (id, description, manuscript item / record, required input, command, expected exit code, cwd)
STEPS = [
    ("S01", "IEP schema fixture harness (8 fixtures)", "Table 3: VAL-001 (VAL-026 fixture re-run)", "core",
     [PY, "tools/check_incremental_electricity_schema_fixtures.py"], 0, ROOT),
    ("S02", "External-validator fixture harness (6 scenarios, 11 files)", "Table 3: VAL-002; Section 5.1", "core",
     [PY, "tools/check_incremental_electricity_external_validator_fixtures.py"], 0, ROOT),
    ("S03", "Future-set registry integrity", "VAL-003 (not cited in the manuscript)", "core",
     [PY, "tools/check_future_id_registry.py", "--check-integrity"], 0, ROOT),
    ("S04", "Canonical 42-artefact harness: schema, p95<=peak, shared-trace values", "Table 3: VAL-006/VAL-017; Section 5.1", "core",
     [PY, "tools/check_anchor21_incremental_electricity_artifacts.py", "--artifact-dir", str(ART),
      "--expected-shared-trace-json", "reports/validation/canonical_continuous_v1_expected_shared_trace.json"], 0, ROOT),
    ("S05", "Historical 42-artefact harness (default invocation)", "VAL-007 (supports VAL-019)", "core",
     [PY, "tools/check_anchor21_incremental_electricity_artifacts.py"], 0, ROOT),
    ("S06", "Historical/canonical identity coexistence", "Table 3: VAL-019; Section 5.1", "core",
     [PY, "scripts/check_generation_coexistence.py"], 0, ROOT),
    ("S07", "Real-trace check, 2035_EB future_0", "Table 3: VAL-020, VAL-050; Section 5.1", "core",
     [PY, "tools/validate_incremental_electricity_pack_external.py", "--artefact", art("2035_EB", 0),
      "--trace", str(TRACE["2035_EB"]), "--tolerance", "0.01"], 0, ROOT),
    ("S08", "Real-trace check, 2035_BB future_0", "Table 3: VAL-021, VAL-050; Section 5.1", "core",
     [PY, "tools/validate_incremental_electricity_pack_external.py", "--artefact", art("2035_BB", 0),
      "--trace", str(TRACE["2035_BB"]), "--tolerance", "0.01"], 0, ROOT),
    ("S09", "Real-trace boundary diagnostic, 2035_EB future_5 (expected annual-field failure)", "Table 3: VAL-022; Section 5.1", "core",
     [PY, "tools/validate_incremental_electricity_pack_external.py", "--artefact", art("2035_EB", 5),
      "--trace", str(TRACE["2035_EB"]), "--tolerance", "0.01"], 1, ROOT),
    ("S10", "Independent baseline recomputation and shared-trace pattern", "Section 5.1: baseline values, recomputation difference, 0.95-1.10 range, sixteen levels", "core",
     [PY, "scripts/recompute_baseline_and_shared_trace.py"], 0, ROOT),
    ("S11", "Render supplementary shared-trace figure (Figure 2 of v8; removed from v9)", "Supplementary (not a v9 figure)", "core",
     [PY, "render_fig2.py"], 0, ROOT / "figures" / "scripts"),
    ("S12", "Figure-data verification, including the manuscript values of Section 5.2", "Section 5.1 pattern; Section 5.2 values", "core",
     [PY, "verify.py"], 0, ROOT / "figures" / "scripts"),
    ("S13", "Retained downstream consumer, six cases", "Sections 4.3, 5.2 (six cases); VAL-051 (not cited in v9)", "upgrade_menu",
     [PY, "Process-Heat-DCM/src/gxp_downstream_qualification_consumer.py", "--out-dir",
      str(OUT / "gxp_downstream_qualification_consumer_v1")], 0, ROOT),
    ("S14", "All-42 retrospective screening replay", "Sections 4.3, 5.2, 6.2, 7 (four of 42 tier changes)", "upgrade_menu",
     [PY, "scripts/replay_all42_screening.py"], 0, ROOT),
    ("S15", "Render Version 8 Figure 3 layout (superseded by S21; supplementary)", "Supplementary; Section 5.2 (VAL-032, not cited in v9)", "upgrade_menu",
     [PY, "render_fig3.py"], 0, ROOT / "figures" / "scripts"),
    ("S16", "BSP schema self-check", "Section 5.3 (29 required fields); VAL-044 (not cited in v9)", "bsp",
     [PY, "scripts/check_bsp_schema.py"], 0, ROOT),
    ("S17", "BSP instance validation: arithmetic, checksum, identity, provenance IDs", "Section 5.3 (arithmetic, checksum); released instance", "bsp",
     [PY, str(BSP_VALIDATOR), str(BSP_INSTANCE)], 0, ROOT),
    ("S18", "BSP structured-field qualification consumer", "Section 5.3 (bounded consumer)", "bsp",
     [PY, str(BSP_VALIDATOR), str(BSP_INSTANCE), "--mode", "qualification-consumer"], 0, ROOT),
]
for name, expect in [("valid.regional_screening_bounded", 0), ("invalid.additional_property", 1),
                     ("invalid.dynamic_competing_demand", 1), ("invalid.equal_distance_bases", 1)]:
    STEPS.append((f"S19.{name.split('.')[1][:12]}", f"BSP fixture {name} (expected {'pass' if expect == 0 else 'fail'})",
                  "Section 5.3 (four authored fixtures)", "bsp",
                  [PY, str(BSP_VALIDATOR), str(BSP_FIXTURES / f"biomass_supply_pack.{name}.json")], expect, ROOT))

STEPS += [
    ("S20", "Screening tier mapping and Figure 2 values from the screening code", "Section 5.2; Figure 2", "upgrade_menu",
     [PY, "scripts/verify_screening_tier_mapping.py"], 0, ROOT),
    ("S21", "Render manuscript Figure 2 (final)", "Figure 2", "upgrade_menu",
     [PY, "render_fig2_screening.py"], 0, ROOT / "figures" / "scripts"),
    ("S22", "Regenerated Figure 2 identical to the published file", "Figure 2", "upgrade_menu",
     [PY, "scripts/check_figure2_matches_published.py"], 0, ROOT),
]


STEPS.append(("E1", "Supplementary: re-run IEP adapter and compare with the 42 supplied artefacts",
              "Section 4.1 (adapter); VAL-015/016/024 (not cited)", "core",
              [PY, "scripts/regeneration_checks.py", "adapter"], 0, ROOT))
STEPS.append(("E2", "Supplementary: re-run BSP screen and producer in a temporary copy and compare",
              "Section 4.4 (BSP producer); identity of the supplied instance", "bsp",
              [PY, "scripts/regeneration_checks.py", "bsp"], 0, ROOT))


def compare_consumer_output():
    """If the reference consumer result is present, compare the regenerated table with it."""
    ref = PHD / "Output" / "runs" / "gxp_downstream_qualification_consumer_v1" / "gxp_downstream_qualification_consumer_result.csv"
    new = OUT / "gxp_downstream_qualification_consumer_v1" / "gxp_downstream_qualification_consumer_result.csv"
    if not (ref.is_file() and new.is_file()):
        return None
    a, b = list(csv.DictReader(open(ref, newline=""))), list(csv.DictReader(open(new, newline="")))
    return a == b


def main():
    ap = argparse.ArgumentParser(description="Reproduce the paper's checks, recomputations and figures.")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for sid, desc, item, req, cmd, exp, cwd in STEPS:
            print(f"{sid:10s} [{req}] {desc} -- {item}")
        return 0
    LOGS.mkdir(parents=True, exist_ok=True)
    avail = {k: f() for k, f in INPUTS.items()}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg")
    results = []
    for sid, desc, item, req, cmd, exp, cwd in STEPS:
        if not avail[req]:
            status, code = "SKIPPED (input absent: " + req + ")", None
        else:
            if Path(cwd) == ROOT:  # pass repository-relative paths so logs carry no machine-specific locations
                cmd = [c if c == PY else (str(Path(c).relative_to(ROOT)) if Path(str(c)).is_absolute() and str(c).startswith(str(ROOT)) else c) for c in cmd]
            t0 = time.time()
            p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
            (LOGS / f"{sid}.log").write_text(f"$ {display(cmd)}\n(cwd={Path(cwd).relative_to(ROOT) if Path(cwd) != ROOT else '.'})\n\n"
                                              + p.stdout + ("\n[stderr]\n" + p.stderr if p.stderr else ""), encoding="utf-8")
            code = p.returncode
            status = "PASS" if code == exp else f"FAIL (exit {code}, expected {exp})"
            if sid == "S13" and code == 0:
                same = compare_consumer_output()
                if same is False:
                    status = "FAIL (result differs from reference consumer output)"
                elif same is True:
                    status += " (identical to reference result table)"
        results.append({"step": sid, "description": desc, "manuscript_item": item, "requires": req,
                        "expected_exit": exp, "exit": code, "status": status})
        print(f"{sid:10s} {status:60s} {desc}")
    (OUT / "reproduction_summary.json").write_text(json.dumps({"inputs_available": avail, "steps": results}, indent=2), encoding="utf-8")
    failed = [r for r in results if r["status"].startswith("FAIL")]
    skipped = [r for r in results if r["status"].startswith("SKIPPED")]
    print(f"\n{len(results) - len(failed) - len(skipped)} passed, {len(failed)} failed, {len(skipped)} skipped "
          f"(summary: reproduction_outputs/reproduction_summary.json)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
