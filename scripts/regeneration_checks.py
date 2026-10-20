"""Supplementary regeneration checks (beyond the 22 manuscript reproduction steps).

  python scripts/regeneration_checks.py adapter
      Re-runs the IEP adapter on the supplied canonical model outputs into
      reproduction_outputs/adapter_regenerated/ and compares the 42 regenerated artefacts with
      the supplied ones (parsed JSON; byte comparison after line-ending normalisation).
  python scripts/regeneration_checks.py bsp
      Re-runs the biomass supply screen and the BiomassSupplyPack producer in a temporary copy
      of this repository and compares the regenerated summary, allocation and instance (and the
      artefact_id) with the supplied files.
Neither check reruns the process-heat dispatch model. Exit 0 if the regenerated outputs match.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def adapter():
    out = ROOT / "reproduction_outputs" / "adapter_regenerated"
    if out.exists():
        shutil.rmtree(out)
    cmd = [PY, "tools/build_incremental_electricity_pack_anchor21_from_real_outputs.py", "--write",
           "--source-bundle-dir", "Process-Heat-DCM/Output/runs/dispatch_optimal_subset_canonical_continuous_v1",
           "--run-id-label", "canonical_continuous_v1", "--output-dir", str(out.relative_to(ROOT))]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    print(r.stdout[-600:])
    if r.returncode != 0:
        print(r.stderr); return 1
    ref = ROOT / "artefacts" / "incremental_electricity_pack" / "anchor_21_canonical_continuous_v1"
    new = sorted(out.glob("*.json"))
    parsed = sum(json.loads(p.read_text(encoding="utf-8")) == json.loads((ref / p.name).read_text(encoding="utf-8")) for p in new)
    norm = sum(p.read_bytes().replace(b"\r\n", b"\n") == (ref / p.name).read_bytes().replace(b"\r\n", b"\n") for p in new)
    print(f"regenerated: {len(new)}; parsed-JSON identical: {parsed}/42; byte-identical after line-ending normalisation: {norm}/42")
    ok = len(new) == 42 and parsed == 42 and norm == 42
    print("[PASS] adapter regeneration reproduces the supplied artefacts" if ok else "[FAIL] adapter output differs")
    return 0 if ok else 1


def bsp():
    runs = Path("Process-Heat-DCM/Output/runs")
    files = [runs / "biomass_supply_screen_formalised_v1/biomass_supply_screen_summary.csv",
             runs / "biomass_supply_screen_formalised_v1/biomass_supply_tier_allocation.csv",
             runs / "biomass_supply_pack_v1/biomass_supply_pack.v1.0.json"]
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "repo"
        shutil.copytree(ROOT, tmp, ignore=shutil.ignore_patterns("reproduction_outputs", "__pycache__", ".git"))
        for d in ["biomass_supply_screen_formalised_v1", "biomass_supply_pack_v1"]:
            shutil.rmtree(tmp / runs / d)
        for script in ["Process-Heat-DCM/src/biomass_supply_screen.py", "Process-Heat-DCM/src/biomass_supply_pack_producer.py"]:
            r = subprocess.run([PY, script], cwd=tmp, capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout, r.stderr); return 1
        ok = True
        for f in files:
            same = sha(tmp / f) == sha(ROOT / f)
            ok &= same
            print(f"[{'PASS' if same else 'FAIL'}] regenerated {f.name} identical to supplied file")
        a = json.loads((tmp / files[2]).read_text(encoding="utf-8"))["artefact_id"]
        b = json.loads((ROOT / files[2]).read_text(encoding="utf-8"))["artefact_id"]
        print(f"[{'PASS' if a == b else 'FAIL'}] artefact_id {a} == supplied {b}")
        ok &= a == b
    return 0 if ok else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"adapter": adapter, "bsp": bsp}.get(mode, lambda: (print(__doc__), 2)[1])())
