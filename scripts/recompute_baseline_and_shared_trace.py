"""Independent recomputation of the IEP baseline values and the shared-trace pattern.

Added for the paper-specific release (no retained script previously reproduced these).
It does not import the external validator: trace statistics are recomputed with numpy
(sum, max, linear-interpolation 95th percentile) directly from the two canonical hourly
traces, then compared with the declared values in the 42 canonical IEP artefacts.

Reproduces (manuscript Version 9, Section 5.1; formerly also Figure 2 of Version 8):
  * future_0 baseline values for 2035_EB and 2035_BB, and the size of the difference
    between the independently recomputed and declared annual values;
  * peak/p95 identical across all 21 futures within each pathway;
  * annual value of every future = baseline trace sum x U_inc_mult (futures.csv);
  * annual ratio range relative to future_0 and the number of distinct levels.
Writes reproduction_outputs/iep_baseline_and_shared_trace.json; exit 0 if all checks pass.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "Process-Heat-DCM" / "Output" / "runs" / "dispatch_optimal_subset_canonical_continuous_v1"
ART = ROOT / "artefacts" / "incremental_electricity_pack" / "anchor_21_canonical_continuous_v1"
OUT = ROOT / "reproduction_outputs"
# Values as reported in the manuscript (project-generated results).
REPORTED = {
    "2035_EB": {"annual_mwh_2dp": 827272.72, "peak_mw_3dp": 132.998, "p95_mw_3dp": 123.784},
    "2035_BB": {"annual_mwh_2dp": 480121.21, "peak_mw_3dp": 92.594, "p95_mw_3dp": 83.380},
}
REPORTED_MAX_ANNUAL_DIFF_MWH = 1.16e-10   # "differ by no more than 1.16 x 10^-10 MWh"
REPORTED_RATIO_RANGE = (0.95, 1.10)
REPORTED_DISTINCT_LEVELS = 16

ok = True
def check(label, cond):
    global ok
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    ok = ok and bool(cond)

def load_trace(pathway):
    path = CANON / f"epoch{pathway}" / "dispatch" / "optimal_subset_run" / "signals" / f"incremental_electricity_MW_{pathway}.csv"
    with open(path, newline="") as fh:
        vals = np.array([float(r["incremental_electricity_MW"]) for r in csv.DictReader(fh)], dtype=float)
    return vals

futures = {int(r["future_id"]): r for r in csv.DictReader(open(ROOT / "Process-Heat-DCM/Output/runs/dispatch_optimal_subset_canonical_continuous_v1/rdm/futures.csv", newline=""))}
arts = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ART.glob("*.json"))]
check("42 canonical artefacts loaded", len(arts) == 42)

summary = {}
max_annual_diff = 0.0
for pathway in ["2035_EB", "2035_BB"]:
    v = load_trace(pathway)
    check(f"{pathway}: trace has 8760 hourly values", v.size == 8760)
    comp = {"annual": float(np.sum(v)), "peak": float(np.max(v)), "p95": float(np.percentile(v, 95, method="linear"))}
    recs = sorted([a for a in arts if a["pathway_id"] == pathway], key=lambda a: a["future_id"])
    base = recs[0]
    check(f"{pathway}: future_0 present", base["future_id"] == 0)
    d_annual = abs(base["annual_incremental_mwh"] - comp["annual"])
    max_annual_diff = max(max_annual_diff, d_annual)
    check(f"{pathway}: future_0 peak equals recomputed trace maximum exactly", base["peak_incremental_mw"] == comp["peak"])
    check(f"{pathway}: future_0 p95 equals recomputed linear 95th percentile exactly", base["p95_incremental_mw"] == comp["p95"])
    check(f"{pathway}: future_0 annual within 1e-6 MWh of recomputed trace sum (diff={d_annual:.3e})", d_annual <= 1e-6)
    r = REPORTED[pathway]
    check(f"{pathway}: values match manuscript rounding",
          round(base["annual_incremental_mwh"], 2) == r["annual_mwh_2dp"] and round(base["peak_incremental_mw"], 3) == r["peak_mw_3dp"]
          and round(base["p95_incremental_mw"], 3) == r["p95_mw_3dp"])
    check(f"{pathway}: peak identical across 21 futures", len({a["peak_incremental_mw"] for a in recs}) == 1)
    check(f"{pathway}: p95 identical across 21 futures", len({a["p95_incremental_mw"] for a in recs}) == 1)
    worst = max(abs(a["annual_incremental_mwh"] - base["annual_incremental_mwh"] * float(futures[a["future_id"]]["U_inc_mult"]))
                / base["annual_incremental_mwh"] for a in recs)
    check(f"{pathway}: annual = future_0 annual x U_inc_mult for all 21 futures (max rel. diff {worst:.1e})", worst <= 1e-12)
    ratios = [a["annual_incremental_mwh"] / base["annual_incremental_mwh"] for a in recs]
    levels = sorted({round(x, 9) for x in ratios})
    check(f"{pathway}: ratio range {min(ratios):.4f}-{max(ratios):.4f} matches manuscript (0.95-1.10)",
          (round(min(ratios), 2), round(max(ratios), 2)) == REPORTED_RATIO_RANGE)
    check(f"{pathway}: {len(levels)} distinct annual levels (manuscript: sixteen)", len(levels) == REPORTED_DISTINCT_LEVELS)
    summary[pathway] = {"recomputed": comp, "declared_future_0": {k: base[k] for k in ["annual_incremental_mwh", "peak_incremental_mw", "p95_incremental_mw"]},
                        "abs_diff_annual_mwh": d_annual, "ratio_min": min(ratios), "ratio_max": max(ratios), "distinct_levels": len(levels)}

check(f"max |annual difference| across baselines = {max_annual_diff:.3e} MWh (manuscript: <= 1.16e-10)",
      max_annual_diff <= REPORTED_MAX_ANNUAL_DIFF_MWH)
summary["max_abs_annual_diff_mwh"] = max_annual_diff
summary["all_checks_passed"] = ok
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "iep_baseline_and_shared_trace.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print("\nALL CHECKS PASSED" if ok else "\nONE OR MORE CHECKS FAILED")
sys.exit(0 if ok else 1)
