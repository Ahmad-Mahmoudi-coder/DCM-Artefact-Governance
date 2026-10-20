"""
Supplementary figure (Version 8 Figure 2; removed from Version 9) -- Shared-trace / information-granularity result across the 21
canonical futures (IncrementalElectricityPack, 2035_EB and 2035_BB).

Reads the 42 canonical artefact JSON files only. Fails loudly (via
validate_and_organise's assertions) if peak/p95 are not in fact invariant
within a pathway, rather than silently plotting a false invariance.

Design selected after an internal comparison (fig2_dev_compare.py) between a
normalised-ratio representation and a native-unit, dual-axis representation:
the dual-axis version was rejected because annual energy (MWh) and peak/p95
(MW) are different physical quantities and cannot share one axis honestly,
forcing a secondary axis the authorisation instructs to avoid. The normalised
ratio representation keeps both quantities on one shared, dimensionless axis.

Refinement pass (second authorisation): publication-quality axis wording
(no field/variable names inside the image), and an explicit visual hierarchy
in which the annual-energy points are the primary empirical result and the
pathway-invariant peak/p95 reference is a visually subordinate line.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D

from load_data import load_iep_artefacts, validate_and_organise, figure_output_dir
from style import apply_style, SERIES_A, REFERENCE

apply_style()

records = load_iep_artefacts()
by_pathway = validate_and_organise(records)  # raises AssertionError if invariance fails

PATHWAY_LABELS = {"2035_EB": "2035 EB", "2035_BB": "2035 BB"}
PATHWAYS = ["2035_EB", "2035_BB"]

fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.55), sharey=True)

for ax, pathway in zip(axes, PATHWAYS):
    recs = by_pathway[pathway]
    base_annual = recs[0]["annual_incremental_mwh"]
    fids = [r["future_id"] for r in recs]
    ratios = [r["annual_incremental_mwh"] / base_annual for r in recs]

    # subordinate reference first (drawn behind, lighter weight, dashed)
    ax.axhline(1.0, color=REFERENCE, linewidth=1.1, linestyle=(0, (5, 3)), zorder=1, alpha=0.9)
    # primary empirical result: annual-energy points
    ax.scatter(
        fids, ratios, s=28, color=SERIES_A, zorder=3,
        edgecolors="white", linewidths=0.5,
    )

    ax.set_xlabel("Canonical future ID", labelpad=4)
    ax.set_xlim(-1, 21)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
    ax.text(0.03, 0.94, PATHWAY_LABELS[pathway], transform=ax.transAxes,
            fontsize=9, va="top", ha="left", color="#222222")
    ax.grid(axis="x", visible=False)

axes[0].set_ylabel("Annual incremental electricity,\nnormalised to future 0")
axes[0].set_ylim(0.92, 1.14)
axes[0].yaxis.set_major_locator(mticker.MultipleLocator(0.05))

legend_elems = [
    Line2D([0], [0], marker="o", linestyle="none", markerfacecolor=SERIES_A,
           markeredgecolor="white", markersize=6, label="Annual incremental electricity (per future)"),
    Line2D([0], [0], color=REFERENCE, linewidth=1.1, linestyle=(0, (5, 3)),
           label="Peak and p95: pathway-invariant"),
]
fig.legend(handles=legend_elems, loc="lower center", ncol=1, bbox_to_anchor=(0.5, 0.0),
           frameon=False, fontsize=8)

fig.tight_layout(rect=[0, 0.14, 1, 1])
OUT = figure_output_dir()
fig.savefig(OUT / "fig02_ieps_shared_trace_information_granularity.png")
fig.savefig(OUT / "fig02_ieps_shared_trace_information_granularity.pdf")
plt.close(fig)

print("Figure 2 written (PNG + PDF).")

# ---- self-verification printed to console ----
for pathway in PATHWAYS:
    recs = by_pathway[pathway]
    ratios = [r["annual_incremental_mwh"] / recs[0]["annual_incremental_mwh"] for r in recs]
    print(f"{pathway}: n_futures={len(recs)}, ratio_min={min(ratios):.4f}, ratio_max={max(ratios):.4f}, "
          f"peak={recs[0]['peak_incremental_mw']!r}, p95={recs[0]['p95_incremental_mw']!r}")
