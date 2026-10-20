"""
Reproducible data-loading module for the DCM artefact-governance figure scripts.

Reads ONLY existing, already-authorised source files:
  - the 42 canonical IncrementalElectricityPack artefact JSON files
    (artefacts/incremental_electricity_pack/anchor_21_canonical_continuous_v1/)
  - Process-Heat-DCM/Input/configs/grid_upgrades_southland_edendale.toml
  - Process-Heat-DCM/Output/runs/dispatch_optimal_subset_canonical_continuous_v1/rdm/futures.csv

No source file is modified. No model is rerun. All quantities used in the
figures are computed here from these files; none are hand-typed constants
(other than the fixed reference-headroom base of 50 MW and the demonstrated
future_id = 5 case, both of which are documented, already-authorised values
from docs/81 Sections 7-8 / VAL-032 -- not new evidence).
"""
import json
import glob
import csv
import tomllib
import os
from pathlib import Path

# Release staging edit: repository-relative defaults (previously absolute container paths).
REPO_ROOT = Path(__file__).resolve().parents[2]

ARTEFACT_DIR = os.environ.get(
    "IEP_ARTEFACT_DIR",
    str(REPO_ROOT / "artefacts" / "incremental_electricity_pack" / "anchor_21_canonical_continuous_v1"),
)
UPGRADE_TOML = os.environ.get(
    "UPGRADE_TOML",
    str(REPO_ROOT / "Process-Heat-DCM" / "Input" / "configs" / "grid_upgrades_southland_edendale.toml"),
)
FUTURES_CSV = os.environ.get(
    "FUTURES_CSV",
    str(REPO_ROOT / "Process-Heat-DCM" / "Output" / "runs" / "dispatch_optimal_subset_canonical_continuous_v1" / "rdm" / "futures.csv"),
)

REFERENCE_HEADROOM_MW = 50.0  # documented base constant, docs/81 Section 7
DEMONSTRATED_FUTURE_ID = 5    # the future_id docs/81 Section 8 / VAL-032 use for Path A/B


def load_iep_artefacts():
    records = []
    paths = sorted(glob.glob(os.path.join(ARTEFACT_DIR, "*.json")))
    for path in paths:
        with open(path) as f:
            records.append(json.load(f))
    return records


def validate_and_organise(records):
    """Fail loudly if the expected 21x2 invariant structure does not hold."""
    assert len(records) == 42, f"expected 42 canonical artefacts, found {len(records)}"

    by_pathway = {}
    for r in records:
        by_pathway.setdefault(r["pathway_id"], []).append(r)

    assert set(by_pathway.keys()) == {"2035_EB", "2035_BB"}, (
        f"unexpected pathway set: {sorted(by_pathway.keys())}"
    )

    for pathway, recs in by_pathway.items():
        assert len(recs) == 21, f"{pathway}: expected 21 futures, found {len(recs)}"
        future_ids = sorted(r["future_id"] for r in recs)
        assert future_ids == list(range(21)), (
            f"{pathway}: future_id set is not exactly 0..20: {future_ids}"
        )
        recs.sort(key=lambda r: r["future_id"])

        peaks = {round(r["peak_incremental_mw"], 9) for r in recs}
        p95s = {round(r["p95_incremental_mw"], 9) for r in recs}
        assert len(peaks) == 1, (
            f"{pathway}: peak_incremental_mw is NOT invariant across futures "
            f"({len(peaks)} distinct values) -- refusing to plot a false invariance"
        )
        assert len(p95s) == 1, (
            f"{pathway}: p95_incremental_mw is NOT invariant across futures "
            f"({len(p95s)} distinct values) -- refusing to plot a false invariance"
        )

    return by_pathway


def figure_output_dir():
    """Release staging edit: output directory (FIG_OUT_DIR or reproduction_outputs/figures), created if absent."""
    out = Path(os.environ.get("FIG_OUT_DIR", str(REPO_ROOT / "reproduction_outputs" / "figures")))
    out.mkdir(parents=True, exist_ok=True)
    return out


def upgrade_menu_available():
    return os.path.isfile(UPGRADE_TOML)


def load_upgrade_menu():
    if not upgrade_menu_available():
        raise FileNotFoundError(
            "Grid-upgrade menu not found (Process-Heat-DCM/Input/configs/grid_upgrades_southland_edendale.toml or UPGRADE_TOML). It is part of this package; restore it from the release archive.")
    with open(UPGRADE_TOML, "rb") as f:
        data = tomllib.load(f)
    upgrades = data["upgrades"]
    upgrades = sorted(upgrades, key=lambda u: u["capacity_MW"])
    return upgrades


def load_future_multiplier(future_id, column):
    with open(FUTURES_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row["future_id"]) == future_id:
                return float(row[column])
    raise KeyError(f"future_id {future_id} not found in {FUTURES_CSV}")


if __name__ == "__main__":
    recs = load_iep_artefacts()
    by_pathway = validate_and_organise(recs)
    for pathway, rr in by_pathway.items():
        peak = rr[0]["peak_incremental_mw"]
        p95 = rr[0]["p95_incremental_mw"]
        print(f"{pathway}: peak={peak!r} MW, p95={p95!r} MW (invariant, n=21 confirmed)")
        for r in rr:
            pass
    upgrades = load_upgrade_menu()
    print("\nUpgrade menu (from TOML):")
    for u in upgrades:
        print(f"  {u['name']}: +{u['capacity_MW']} MW, NZ${u['capex_nzd']/1e6:.1f}M")
    hm = load_future_multiplier(DEMONSTRATED_FUTURE_ID, "U_headroom_mult")
    im = load_future_multiplier(DEMONSTRATED_FUTURE_ID, "U_inc_mult")
    print(f"\nfuture_id={DEMONSTRATED_FUTURE_ID}: U_headroom_mult={hm}, U_inc_mult={im}")
    print(f"effective headroom = {REFERENCE_HEADROOM_MW} * {hm} = {REFERENCE_HEADROOM_MW*hm} MW")
