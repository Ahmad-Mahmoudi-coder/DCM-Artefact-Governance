"""Check that the regenerated manuscript Figure 2 is identical to the published file.

Added for release v1.0.0. Compares the SHA-256 of
reproduction_outputs/figures/fig2_screening_sensitivity_2035EB_future5.{png,pdf}
with figures/published/. The published PNG is the image placed in the manuscript.
Byte identity is expected with the pinned requirements (Matplotlib 3.11.1 and its bundled
DejaVu Sans font); if it fails on another platform, compare the images visually and report it.
"""
import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
regen = Path(os.environ.get("FIG_OUT_DIR", ROOT / "reproduction_outputs" / "figures"))
ok = True
for ext in ("png", "pdf"):
    name = f"fig2_screening_sensitivity_2035EB_future5.{ext}"
    a, b = regen / name, ROOT / "figures" / "published" / name
    if not a.exists():
        print(f"[FAIL] regenerated {name} not found (run figures/scripts/render_fig2_screening.py first)")
        ok = False
        continue
    ha, hb = (hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b))
    same = ha == hb
    ok &= same
    print(f"[{'PASS' if same else 'FAIL'}] {name}: regenerated {ha[:16]}… published {hb[:16]}…")
sys.exit(0 if ok else 1)
