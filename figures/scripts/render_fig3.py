"""
Manuscript Version 9 Figure 2 (Version 8 Figure 3) -- Downstream infrastructure consequence of the two alternative
interpretations of the shared-trace limitation (Path A / Path B, docs/81
Sections 7-8; VAL-032), for 2035_EB, future_id = 5.

Reads the grid-upgrade menu from its source TOML and the headroom/demand
multipliers from futures.csv; computes all plotted quantities (total
effective capacity per tier, Path A/B demand, the near-miss margin) from
those source values. The 150 MW tier and its cost are an illustrative screening assumption
(undocumented derivation; not an official estimate). qualification_codes is not read, plotted, or used in
any arithmetic here -- it governs which of the two demand values a consumer
is entitled to compute, not a plotted quantity.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from load_data import (
    load_iep_artefacts, validate_and_organise, load_upgrade_menu,
    load_future_multiplier, REFERENCE_HEADROOM_MW, DEMONSTRATED_FUTURE_ID,
    figure_output_dir,
)
from style import apply_style, SERIES_A, SERIES_B

apply_style()

# ---- data (all derived from source files) ----
records = load_iep_artefacts()
by_pathway = validate_and_organise(records)
eb_peak = by_pathway["2035_EB"][0]["peak_incremental_mw"]

upgrades = load_upgrade_menu()
u_headroom_mult = load_future_multiplier(DEMONSTRATED_FUTURE_ID, "U_headroom_mult")
u_inc_mult = load_future_multiplier(DEMONSTRATED_FUTURE_ID, "U_inc_mult")

headroom_mw = REFERENCE_HEADROOM_MW * u_headroom_mult
path_a_demand = eb_peak
path_b_demand = eb_peak * u_inc_mult

tier_capacity = [headroom_mw + u["capacity_MW"] for u in upgrades]
tier_cost = [u["capex_nzd"] / 1e6 for u in upgrades]
tier_name = [u["name"] for u in upgrades]
tier_upgrade_mw = [u["capacity_MW"] for u in upgrades]


def select_tier(demand_mw):
    for cap, cost, name, add_mw in zip(tier_capacity, tier_cost, tier_name, tier_upgrade_mw):
        if cap >= demand_mw:
            return cap, cost, name, add_mw
    raise ValueError(f"no tier covers demand {demand_mw} MW")


a_cap, a_cost, a_name, a_add = select_tier(path_a_demand)
b_cap, b_cost, b_name, b_add = select_tier(path_b_demand)

# Release staging edit: literal expected tier values moved to figures/scripts/verify.py
# (compared there against an expected-values file); here only the structural claim is asserted.
assert b_cap > a_cap, "Path B is expected to select a larger tier than Path A for this future"

margin_mw = path_b_demand - a_cap
print(f"headroom={headroom_mw} MW; Path A={path_a_demand:.3f} MW -> {a_name} (NZ${a_cost:.1f}M); "
      f"Path B={path_b_demand:.3f} MW -> {b_name} (NZ${b_cost:.1f}M); margin={margin_mw:.3f} MW")

# ================= figure =================
fig = plt.figure(figsize=(7.6, 4.3))
ax = fig.add_axes([0.10, 0.13, 0.60, 0.80])

ax.step(tier_capacity, tier_cost, where="pre", color="#555555", linewidth=1.5, zorder=2)
ax.scatter(tier_capacity, tier_cost, s=16, color="#555555", zorder=3)

YMAX = 92
for demand, cost, colour, tag, dx in [
    (path_a_demand, a_cost, SERIES_A, "Path A", -3),
    (path_b_demand, b_cost, SERIES_B, "Path B", 3),
]:
    ax.vlines(demand, 0, 66, color=colour, linestyle=(0, (4, 2)), linewidth=1.1, zorder=1, alpha=0.85)
    ax.scatter([demand], [cost], s=36, color=colour, zorder=5, edgecolors="white", linewidths=0.6)

ax.text(path_a_demand - 3, 70, "Path A", fontsize=8.8, color=SERIES_A, ha="right", va="bottom")
ax.text(path_b_demand + 3, 70, "Path B", fontsize=8.8, color=SERIES_B, ha="left", va="bottom")

# tier labels, placed clear of the demand lines
ax.text(58, a_cost + 3.5, f"+{a_add:g} MW\nNZ${a_cost:.1f}M", fontsize=7.6, color="#555555", ha="center", va="bottom")
ax.text(170, b_cost + 4, f"+{b_add:g} MW\nNZ${b_cost:.1f}M", fontsize=7.6, color="#555555", ha="center", va="bottom")

# explicit marker for the decisive tier boundary (kept separate from
# the routine axis ticks so the one threshold that matters is unmistakable)
ax.plot([a_cap, a_cap], [-6, -1.5], color="#222222", linewidth=1.0, zorder=4)
ax.text(a_cap, -8.5, f"{a_cap:.1f} MW\nthreshold", fontsize=7.2, color="#222222", ha="center", va="top")

ax.set_xlabel("Total effective capacity after upgrade (MW)")
ax.set_ylabel("Capital cost (NZ$ million)")
ax.set_xlim(30, 205)
ax.set_ylim(-16, YMAX)
ax.yaxis.set_major_locator(mticker.MultipleLocator(20))
ax.xaxis.set_major_locator(mticker.MultipleLocator(25))
ax.grid(axis="x", visible=False)
ax.axhline(0, color="#BBBBBB", linewidth=0.7, zorder=0)

# ---- inset: magnified view of the tier-boundary near-miss ----
inset_x0, inset_y0, inset_w, inset_h = 128, a_cost - 20, 20, (b_cost + 6) - (a_cost - 20)

inset = fig.add_axes([0.76, 0.38, 0.22, 0.30])
inset.step(tier_capacity, tier_cost, where="pre", color="#555555", linewidth=1.4, zorder=2)
inset.scatter([a_cap, b_cap], [a_cost, b_cost], s=14, color="#555555", zorder=3)
inset.vlines(path_a_demand, 0, 100, color=SERIES_A, linestyle=(0, (4, 2)), linewidth=1.1, zorder=1)
inset.vlines(path_b_demand, 0, 100, color=SERIES_B, linestyle=(0, (4, 2)), linewidth=1.1, zorder=1)
inset.scatter([path_a_demand], [a_cost], s=30, color=SERIES_A, zorder=5, edgecolors="white", linewidths=0.5)
inset.scatter([path_b_demand], [b_cost], s=30, color=SERIES_B, zorder=5, edgecolors="white", linewidths=0.5)

bracket_y = a_cost + 9
inset.annotate("", xy=(a_cap, bracket_y), xytext=(path_b_demand, bracket_y),
               arrowprops=dict(arrowstyle="|-|,widthA=0.25,widthB=0.25", color="#222222", linewidth=1.0))
inset.text((a_cap + path_b_demand) / 2, bracket_y + 2.2, f"{margin_mw:.3f} MW",
           fontsize=7.4, color="#222222", ha="center", va="bottom")

inset.set_xlim(inset_x0, inset_x0 + inset_w)
inset.set_ylim(inset_y0, inset_y0 + inset_h)
inset.set_xticks([path_a_demand, a_cap])
inset.set_xticklabels([f"{path_a_demand:.1f}", f"{a_cap:.1f}"], fontsize=6.4)
inset.set_yticks([a_cost, b_cost])
inset.set_yticklabels([f"{a_cost:.1f}", f"{b_cost:.1f}"], fontsize=6.4)
inset.grid(False)
inset.tick_params(length=2, pad=1.5)
for spine in inset.spines.values():
    spine.set_linewidth(0.6)
    spine.set_color("#888888")

# connector box on main axes showing the zoomed region, wired to the inset
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

rect = Rectangle((inset_x0, inset_y0), inset_w, inset_h,
                  fill=False, edgecolor="#AAAAAA", linewidth=0.7, linestyle=(0, (2, 2)))
ax.add_patch(rect)
for corner_main, corner_inset in [((inset_x0 + inset_w, inset_y0 + inset_h), (0, 0)),
                                    ((inset_x0 + inset_w, inset_y0), (0, 1))]:
    con = mpatches.ConnectionPatch(
        xyA=corner_inset, coordsA=inset.transAxes,
        xyB=corner_main, coordsB=ax.transData,
        color="#AAAAAA", linewidth=0.6, linestyle=(0, (2, 2)), zorder=0,
    )
    fig.add_artist(con)

OUT = figure_output_dir()
fig.savefig(OUT / "fig03_ieps_governance_consequence_gxp_upgrade.png")
fig.savefig(OUT / "fig03_ieps_governance_consequence_gxp_upgrade.pdf")
plt.close(fig)
print("Figure 3 written (PNG + PDF).")
