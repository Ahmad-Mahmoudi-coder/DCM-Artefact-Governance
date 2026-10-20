"""Verification checks for the DCM artefact-governance figure data (release version).

Release staging edit: rewritten from the original verify.py so that it (i) uses
repository-relative paths, (ii) contains no hard-coded values taken from cited
third-party sources, and (iii) runs the Figure 3 checks only when the externally
grid-upgrade menu is present (it is included in the package). The manuscript-reported
screening values are compared with figures/expected/paper_reported_screening_values.json.
Exit code 0 = every performed check passed.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

from load_data import (
    REPO_ROOT, ARTEFACT_DIR, UPGRADE_TOML, load_iep_artefacts, validate_and_organise,
    load_upgrade_menu, load_future_multiplier, upgrade_menu_available,
    REFERENCE_HEADROOM_MW, DEMONSTRATED_FUTURE_ID,
)

HERE = Path(__file__).resolve().parent
EXPECTED = REPO_ROOT / "figures" / "expected" / "paper_reported_screening_values.json"
ok = True


def check(label, cond):
    global ok
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    if not cond:
        ok = False


def skip(label, why):
    print(f"[SKIP] {label} ({why})")


records = load_iep_artefacts()
by_pathway = validate_and_organise(records)

# 1-3. Figure 2 data structure
for pathway in ["2035_EB", "2035_BB"]:
    recs = by_pathway[pathway]
    check(f"1. 21 futures present for {pathway}", len(recs) == 21)
    base = recs[0]["annual_incremental_mwh"]
    ratios = [r["annual_incremental_mwh"] / base for r in recs]
    check(f"2. {pathway} annual-energy ratio range within [0.94, 1.11]", 0.94 <= min(ratios) and max(ratios) <= 1.11)
    check(f"2. {pathway} annual-energy ratio varies across futures", max(ratios) - min(ratios) > 0.05)
    check(f"3. {pathway} peak_incremental_mw invariant across 21 futures", len({r["peak_incremental_mw"] for r in recs}) == 1)
    check(f"3. {pathway} p95_incremental_mw invariant across 21 futures", len({r["p95_incremental_mw"] for r in recs}) == 1)

# 4. Figure 2 plotting: discrete markers, no smoothing (static source check)
fig2_src = (HERE / "render_fig2.py").read_text(encoding="utf-8")
check("4. Figure 2 script contains no regression/fit/smoothing call",
      not any(t in fig2_src for t in ["polyfit", "lowess", "rolling", "interp1d", "UnivariateSpline"]))
check("4. Figure 2 script uses discrete markers (scatter) only", "ax.scatter(" in fig2_src and "ax.plot(" not in fig2_src)

# 5-8. Figure 3 / Section 5.2 screening checks (grid-upgrade menu required)
if not upgrade_menu_available():
    skip("5-8. Figure 3 screening checks", "grid-upgrade menu not present")
else:
    upgrades = load_upgrade_menu()
    caps = [u["capacity_MW"] for u in upgrades]
    costs = [u["capex_nzd"] for u in upgrades]
    check("5. upgrade menu capacities strictly increasing", all(a < b for a, b in zip(caps, caps[1:])))
    check("5. upgrade menu capital costs non-decreasing", all(a <= b for a, b in zip(costs, costs[1:])))
    eb_peak = by_pathway["2035_EB"][0]["peak_incremental_mw"]
    headroom = REFERENCE_HEADROOM_MW * load_future_multiplier(DEMONSTRATED_FUTURE_ID, "U_headroom_mult")
    demand_a = eb_peak
    demand_b = eb_peak * load_future_multiplier(DEMONSTRATED_FUTURE_ID, "U_inc_mult")

    def select(d):
        for u in upgrades:
            if headroom + u["capacity_MW"] >= d:
                return u, headroom + u["capacity_MW"]
        raise ValueError("no tier covers demand")

    (ua, cap_a), (ub, cap_b) = select(demand_a), select(demand_b)
    margin = demand_b - cap_a
    check("6/7. Path B selects a larger tier than Path A (tier change)", ub["capacity_MW"] > ua["capacity_MW"])
    print(f"    headroom={headroom:.3f} MW; Path A demand={demand_a:.6f} -> +{ua['capacity_MW']:g} MW; "
          f"Path B demand={demand_b:.6f} -> +{ub['capacity_MW']:g} MW; margin={margin:.6f} MW")
    if not EXPECTED.is_file():
        skip("6-8. comparison with manuscript-reported values", f"{EXPECTED.relative_to(REPO_ROOT)} not present")
    else:
        e = json.loads(EXPECTED.read_text(encoding="utf-8"))
        check("5. tier capacities match manuscript", sorted(caps) == sorted(e["menu_tier_capacities_MW"]))
        check("6. Path A tier and capital cost match manuscript",
              ua["capacity_MW"] == e["path_a_tier_capacity_MW"] and abs(ua["capex_nzd"] / 1e6 - e["path_a_tier_capex_nzd_million"]) < 0.05)
        check("7. Path B tier and capital cost match manuscript",
              ub["capacity_MW"] == e["path_b_tier_capacity_MW"] and abs(ub["capex_nzd"] / 1e6 - e["path_b_tier_capex_nzd_million"]) < 0.05)
        check("8. effective headroom matches manuscript", abs(headroom - e["effective_headroom_MW"]) < 1e-9)
        check("8. Path B demand matches manuscript (3 dp)", round(demand_b, 3) == e["path_b_demand_MW"])
        check("8. threshold matches manuscript (1 dp)", round(cap_a, 1) == e["threshold_MW"])
        check("8. near-miss margin matches manuscript (3 dp)", round(margin, 3) == e["margin_MW"])

# 9. canonical artefacts present and unchanged relative to MANIFEST.sha256 (when present)
files = sorted(Path(ARTEFACT_DIR).glob("*.json"))
check("9. exactly 42 canonical artefact files present", len(files) == 42)
manifest = REPO_ROOT / "MANIFEST.sha256"
if manifest.is_file():
    recorded = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, rel = line.split(None, 1)
            recorded[rel.strip().lstrip("*")] = digest
    mismatch = [f.name for f in files
                if recorded.get(str(f.relative_to(REPO_ROOT)).replace("\\", "/")) != hashlib.sha256(f.read_bytes()).hexdigest()]
    check("9. canonical artefacts match MANIFEST.sha256", not mismatch)
else:
    skip("9. SHA-256 comparison", "MANIFEST.sha256 not present")

# 10/11. figure pipeline opens no file in write mode except through savefig
src = "".join((HERE / n).read_text(encoding="utf-8") for n in ["load_data.py", "render_fig2.py", "render_fig3.py", "style.py"])
check("10/11. no write-mode open() in the figure pipeline", not re.findall(r'open\([^)]*["\']w', src))

print("\nALL PERFORMED CHECKS PASSED" if ok else "\nONE OR MORE CHECKS FAILED")
sys.exit(0 if ok else 1)
