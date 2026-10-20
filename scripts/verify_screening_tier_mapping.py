"""Verify the Figure 2 / Section 5.2 screening values directly from the screening implementation.

Added for release v1.0.0. Imports the retained wrapper's select_adequate_upgrade() (which calls
gxp_rdm_screen.evaluate_upgrade_option() unmodified) and the unmodified load_upgrade_menu(), and:
  1. reads the declared 2035_EB future_5 peak and the future_5 multipliers from the supplied inputs;
  2. computes Path A and Path B demand and runs the actual selection for each;
  3. locates every tier boundary empirically, by bisection on the actual selection function, and
     compares it with headroom + added capacity (no mapping is inferred from labels);
  4. compares all values with figures/expected/paper_reported_screening_values.json.
Writes reproduction_outputs/screening_tier_mapping.json. Exit 0 only if every check passes.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Process-Heat-DCM" / "src"))
import pandas as pd  # noqa: E402
import gxp_downstream_qualification_consumer as consumer  # noqa: E402  (retained wrapper)

PATHWAY, FUTURE = "2035_EB", 5
expected = json.loads((ROOT / "figures/expected/paper_reported_screening_values.json").read_text())
ok = True


def check(label, cond):
    global ok
    ok &= bool(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


upgrades, assumptions = consumer.load_upgrade_menu(consumer.UPGRADE_TOML)
frow = pd.read_csv(consumer.FUTURES_CSV).set_index("future_id").loc[FUTURE].to_dict()
frow["future_id"] = FUTURE
peak = consumer.load_artefact(PATHWAY, FUTURE)["peak_incremental_mw"]
headroom = consumer.BASE_HEADROOM_MW * float(frow["U_headroom_mult"])
demand_a = peak
demand_b = peak * float(frow["U_inc_mult"])


def select(d):
    name, cap, _ = consumer.select_adequate_upgrade(d, headroom, upgrades, assumptions, frow)
    return name, cap


name_a, cap_a = select(demand_a)
name_b, cap_b = select(demand_b)
by_name = {u["name"]: u for u in upgrades}

# Empirical tier boundaries: largest demand for which each tier is still selected.
ordered = sorted(upgrades, key=lambda u: float(u["capacity_MW"]))
boundaries = []
for u in ordered:
    nominal = headroom + float(u["capacity_MW"])
    lo, hi = nominal - 1.0, nominal + 1.0
    if select(lo)[0] != u["name"]:
        boundaries.append({"tier": u["name"], "boundary_found": None})
        continue
    for _ in range(80):
        mid = (lo + hi) / 2
        if select(mid)[0] == u["name"]:
            lo = mid
        else:
            hi = mid
    boundaries.append({"tier": u["name"], "added_MW": float(u["capacity_MW"]),
                       "configured_base_capex_nzd": float(u["capex_nzd"]),
                       "effective_capacity_threshold_MW": nominal, "boundary_found_MW": lo})

print(f"headroom = 50.0 x U_headroom_mult {frow['U_headroom_mult']} = {headroom:.6f} MW")
print(f"Path A demand = declared peak = {demand_a:.6f} MW -> {name_a} (+{cap_a:g} MW)")
print(f"Path B demand = peak x U_inc_mult {frow['U_inc_mult']} = {demand_b:.6f} MW -> {name_b} (+{cap_b:g} MW)")
for b in boundaries:
    print(f"  tier {b['tier']}: threshold {b.get('effective_capacity_threshold_MW')} MW; "
          f"selection boundary found at {b.get('boundary_found_MW')}")

thr_a = headroom + cap_a
check("selection boundaries equal headroom + added capacity (within the code's 1e-6 MW tolerance)",
      all(b["boundary_found_MW"] is not None and 0 <= b["boundary_found_MW"] - b["effective_capacity_threshold_MW"] <= 1.01e-6
          for b in boundaries))
check("thresholds are 42.5, 63.5, 74.5, 139.5, 192.5 MW",
      [round(b["effective_capacity_threshold_MW"], 6) for b in boundaries] == [42.5, 63.5, 74.5, 139.5, 192.5])
check(f"effective headroom = {expected['effective_headroom_MW']} MW", round(headroom, 6) == expected["effective_headroom_MW"])
check("Path A demand = 132.998 MW (3 dp)", round(demand_a, 3) == 132.998)
check(f"Path B demand = {expected['path_b_demand_MW']} MW (3 dp)", round(demand_b, 3) == expected["path_b_demand_MW"])
check(f"Path A selects +{expected['path_a_tier_capacity_MW']} MW", cap_a == expected["path_a_tier_capacity_MW"])
check(f"Path B selects +{expected['path_b_tier_capacity_MW']} MW", cap_b == expected["path_b_tier_capacity_MW"])
check(f"Path A threshold = {expected['threshold_MW']} MW", round(thr_a, 6) == expected["threshold_MW"])
check(f"Path B exceedance = {expected['margin_MW']} MW (3 dp)", round(demand_b - thr_a, 3) == expected["margin_MW"])
check("configured base costs NZ$55.9M (+97 MW) and NZ$75.0M (+150 MW)",
      by_name[name_a]["capex_nzd"] / 1e6 == expected["path_a_tier_capex_nzd_million"]
      and by_name[name_b]["capex_nzd"] / 1e6 == expected["path_b_tier_capex_nzd_million"])
check("selection does not depend on cost (same result with all capex set to 0)",
      all(consumer.select_adequate_upgrade(d, headroom, [dict(u, capex_nzd=0.0) for u in upgrades], assumptions, frow)[0] == n
          for d, n in [(demand_a, name_a), (demand_b, name_b)]))

out = ROOT / "reproduction_outputs"
out.mkdir(exist_ok=True)
(out / "screening_tier_mapping.json").write_text(json.dumps({
    "pathway_id": PATHWAY, "future_id": FUTURE, "headroom_MW": headroom,
    "U_headroom_mult": frow["U_headroom_mult"], "U_inc_mult": frow["U_inc_mult"],
    "U_upgrade_capex_mult_not_used_in_selection": frow["U_upgrade_capex_mult"],
    "path_a": {"demand_MW": demand_a, "tier": name_a, "added_MW": cap_a},
    "path_b": {"demand_MW": demand_b, "tier": name_b, "added_MW": cap_b},
    "exceedance_MW": demand_b - thr_a, "tiers": boundaries}, indent=2))
print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
