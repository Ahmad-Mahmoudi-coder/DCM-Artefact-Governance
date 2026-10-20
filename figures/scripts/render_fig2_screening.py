"""Manuscript Figure 2 (final, Version 9): screening sensitivity for 2035_EB future_5.

Capacity-threshold step plot of the grid-adequacy screen. Every plotted quantity comes from the
supplied inputs and the retained screening implementation:
  * declared peak: canonical IEP artefact 2035_EB future_5;
  * U_headroom_mult and U_inc_mult: rdm/futures.csv (future_id 5);
  * tiers: grid_upgrades_southland_edendale.toml via the unmodified load_upgrade_menu();
  * tier selection: the retained wrapper's select_adequate_upgrade(), which calls
    gxp_rdm_screen.evaluate_upgrade_option() unmodified.
The step function is built from headroom + added capacity, and each step is checked against the
actual selection function on both sides of its threshold before plotting. Costs are not plotted:
the screen selects the smallest tier whose effective capacity covers demand, independent of cost.

Output: fig2_screening_sensitivity_2035EB_future5.{pdf,png} in reproduction_outputs/figures/
(or FIG_OUT_DIR). The PNG is the image placed in the manuscript (15.9 cm wide, 600 dpi).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Process-Heat-DCM" / "src"))
from load_data import figure_output_dir, DEMONSTRATED_FUTURE_ID  # noqa: E402
from style import apply_style, SERIES_A, SERIES_B, INK  # noqa: E402
import gxp_downstream_qualification_consumer as consumer  # noqa: E402

PATHWAY = "2035_EB"
apply_style()
# DejaVu Sans ships with Matplotlib, so the rendering does not depend on system fonts.
matplotlib.rcParams.update({"font.sans-serif": ["DejaVu Sans"], "svg.hashsalt": "paper1-fig2", "pdf.compression": 6})

# ---------------- data from inputs and the actual screening code ----------------
upgrades, assumptions = consumer.load_upgrade_menu(consumer.UPGRADE_TOML)
frow = pd.read_csv(consumer.FUTURES_CSV).set_index("future_id").loc[DEMONSTRATED_FUTURE_ID].to_dict()
frow["future_id"] = DEMONSTRATED_FUTURE_ID
headroom = consumer.BASE_HEADROOM_MW * float(frow["U_headroom_mult"])
peak = consumer.load_artefact(PATHWAY, DEMONSTRATED_FUTURE_ID)["peak_incremental_mw"]
demand = {"A": peak, "B": peak * float(frow["U_inc_mult"])}


def select(d):
    return consumer.select_adequate_upgrade(d, headroom, upgrades, assumptions, frow)[1]


tiers = sorted(float(u["capacity_MW"]) for u in upgrades)          # added MW: 0, 21, 32, 97, 150
thresholds = [headroom + t for t in tiers]                         # 42.5 ... 192.5 MW
for t, thr in zip(tiers, thresholds):                              # mapping confirmed from the code
    assert select(thr - 1e-3) == t and select(thr) == t, (t, thr)
    assert select(thr + 1e-3) != t, (t, thr)
sel = {k: select(v) for k, v in demand.items()}
thr_a = headroom + sel["A"]
exceed = demand["B"] - thr_a
assert sel["B"] > sel["A"]

# ---------------- figure ----------------
CM = 1 / 2.54
fig, (ax, az) = plt.subplots(1, 2, figsize=(15.9 * CM, 6.6 * CM),
                             gridspec_kw={"width_ratios": [1.55, 1.0], "wspace": 0.12})


def step_xy(x0, x1):
    """Selected added capacity as a function of demand on [x0, x1] (right-closed steps)."""
    xs, ys = [x0], [select(x0)]
    for t, thr in zip(tiers[:-1], thresholds[:-1]):
        if x0 < thr < x1:
            xs += [thr, thr]
            ys += [t, tiers[tiers.index(t) + 1]]
    xs.append(x1)
    ys.append(select(x1) if x1 <= thresholds[-1] else tiers[-1])
    return xs, ys


MARK = {"A": dict(color=SERIES_A, marker="o"), "B": dict(color=SERIES_B, marker="s")}
LABEL = {"A": f"Path A: declared peak {demand['A']:.3f} MW",
         "B": f"Path B: peak × {float(frow['U_inc_mult']):.2f} = {demand['B']:.3f} MW"}

# (a) whole menu
xs, ys = step_xy(0.0, thresholds[-1])   # above the largest threshold no menu tier is adequate
ax.plot(xs, ys, color=INK, linewidth=1.3, zorder=2, label="Selected tier (screen)")
for thr in thresholds:
    ax.axvline(thr, color="#BBBBBB", linewidth=0.6, linestyle=(0, (2, 2)), zorder=0)
for k in "AB":
    ax.scatter([demand[k]], [sel[k]], s=26, zorder=4, edgecolors="white", linewidths=0.5,
               label=LABEL[k], **MARK[k])
ax.set_xlim(0, 200)
ax.set_ylim(-8, 165)
ax.set_xticks([0, 50, 100, 150, 200])
ax.set_yticks(tiers)
ax.set_yticklabels(["None", "+21 MW", "+32 MW", "+97 MW", "+150 MW"])
ax.grid(False)
ax.set_xlabel("Peak incremental demand (MW)")
ax.set_ylabel("Selected upgrade tier")
ax.text(0.01, 0.99, "(a)", transform=ax.transAxes, ha="left", va="top", fontsize=9, fontweight="bold")
ax.axvspan(131.5, 141.0, color="#EEEEEE", zorder=0)
ax.legend(loc="lower right", fontsize=7, handlelength=1.6, borderaxespad=0.3)

# (b) zoom on the 97 MW tier threshold
zx0, zx1 = 131.5, 141.0
xs, ys = step_xy(zx0, zx1)
az.plot(xs, ys, color=INK, linewidth=1.3, zorder=2)
az.axvline(thr_a, color=INK, linewidth=0.8, linestyle=(0, (4, 2)), zorder=1)
for k in "AB":
    az.scatter([demand[k]], [sel[k]], s=30, zorder=4, edgecolors="white", linewidths=0.5, **MARK[k])
az.annotate(f"{demand['A']:.3f} MW\n→ +{sel['A']:g} MW", (demand["A"], sel["A"]), xytext=(0, 9),
            textcoords="offset points", ha="center", va="bottom", fontsize=7, color=SERIES_A)
az.annotate(f"{demand['B']:.3f} MW → +{sel['B']:g} MW", (demand["B"], sel["B"]), xytext=(-8, 0),
            textcoords="offset points", ha="right", va="center", fontsize=7, color=SERIES_B)
yb = 120
az.annotate("", xy=(thr_a, yb), xytext=(demand["B"], yb),
            arrowprops=dict(arrowstyle="|-|,widthA=0.25,widthB=0.25", color=INK, linewidth=0.8,
                            shrinkA=0, shrinkB=0))
az.text(thr_a - 0.15, yb, f"exceedance\n{exceed:.3f} MW", ha="right", va="center", fontsize=7)
az.text(thr_a - 0.15, 75, f"+{sel['A']:g} MW tier\nthreshold\n{thr_a:.3f} MW", ha="right", va="center", fontsize=7)
az.set_xlim(zx0, zx1)
az.set_ylim(-8, 165)
az.set_xticks([132, 134, 136, 138, 139.5])
az.set_xticklabels(["132", "134", "136", "138", "139.5"])
az.set_yticks(tiers)
az.set_yticklabels([])
az.grid(False)
az.set_xlabel("Peak incremental demand (MW)")
az.text(0.02, 0.99, "(b)", transform=az.transAxes, ha="left", va="top", fontsize=9, fontweight="bold")

fig.subplots_adjust(left=0.105, right=0.985, bottom=0.17, top=0.97)
out = figure_output_dir()
stem = "fig2_screening_sensitivity_2035EB_future5"
fig.savefig(out / f"{stem}.png", dpi=600, metadata={"Software": None})
fig.savefig(out / f"{stem}.pdf", metadata={"CreationDate": None, "ModDate": None, "Producer": None, "Creator": None})
plt.close(fig)
print(f"headroom={headroom:.3f} MW; Path A {demand['A']:.3f} MW -> +{sel['A']:g} MW; "
      f"Path B {demand['B']:.3f} MW -> +{sel['B']:g} MW; threshold {thr_a:.3f} MW; exceedance {exceed:.3f} MW")
print(f"wrote {out / stem}.png and .pdf")
