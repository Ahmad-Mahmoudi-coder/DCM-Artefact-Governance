"""Shared restrained academic style for the DCM artefact-governance figure scripts."""
import matplotlib as mpl

INK = "#222222"
GRID = "#D9D9D9"
SERIES_A = "#1F4E79"    # dark blue -- primary series / Path A
SERIES_B = "#C0622A"    # muted burnt orange -- secondary series / Path B (colour-blind distinguishable from blue)
REFERENCE = "#8A8A8A"   # grey -- invariant reference line
FILL_LIGHT = "#EDEDED"

def apply_style():
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 9,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.linewidth": 0.8,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "legend.frameon": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",
        "savefig.dpi": 300,
        "figure.dpi": 150,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
    })
