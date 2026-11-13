"""G2 9e pictures: panels-quarters.png, panels-open.png, panels-side.png, panels-gloss.png from the Blender renders
(g2_blender.py), the panels (panels.npz) and the approved sheet. Composition helpers from body_builder/bt2_compose.py.
System Python (numpy, PIL)."""
import json
import os
import sys
from collections import defaultdict

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Art", "VehicleTools", "body_builder"))
import bt2_compose as P  # noqa: E402  (on_grey, label, row, stack)

OUT = os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g2-v01")
RD = os.path.join(OUT, "debug", "renders")
G1 = os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g1-v02")
rep1 = json.load(open(os.path.join(G1, "g1-report.json"), encoding="utf-8"))
chk = json.load(open(os.path.join(OUT, "g2-checks.json"), encoding="utf-8"))
g0 = json.load(open(os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g0-v01", "measurements.json"), encoding="utf-8"))
sheet = Image.open(os.path.join(ROOT, g0["sheet"])).convert("RGB")
REG = g0["views"]["side"]
S_SIDE, X_MID, GROUND = REG["px_per_m"], REG["x_mid_px"], REG["ground_y_px"]


def crop(win, k=1):
    c = sheet.crop(tuple(win))
    return c.resize((c.width * k, c.height * k), Image.LANCZOS) if k != 1 else c


def seam_lines():
    """Chamfer-bottom polylines (each panel's true seam and opening edge, GAP/2 off the seam) on the near side."""
    z = np.load(os.path.join(OUT, "panels.npz"))
    segs = []
    for n in sorted({k.split("__")[0] for k in z.files}):
        if n.endswith("_R") or n.startswith("Glass"):
            continue
        V = z[n + "__v"]
        fl = z[n + "__flag"]
        ef = defaultdict(list)
        for i, f in enumerate(z[n + "__f"]):
            f = [int(k) for k in f if k >= 0]
            for a, b in zip(f, f[1:] + f[:1]):
                ef[(min(a, b), max(a, b))].append(i)
        for (a, b), fs in ef.items():
            if len(fs) == 2 and {int(fl[fs[0]]), int(fl[fs[1]])} == {1, 2} and min(V[a, 0], V[b, 0]) > 0.3:
                segs.append((V[a], V[b]))
    return segs


def main():
    q = [P.label(P.on_grey(os.path.join(RD, f"quarter_{k}.png")), f"G2 panels, clay (a grey per panel), glass dark, wheels; "
                                                                   f"{k.replace('34', ' three-quarter')}") for k in ("front34", "rear34")]
    P.row(q).save(os.path.join(OUT, "panels-quarters.png"))

    o = [P.label(P.on_grey(os.path.join(RD, f"open_{k}.png")), f"opened about the LAY-12 hinges: front doors 50, bonnet 35, lower "
                                                                f"tailgate dropped 80, hatch 60; {k.replace('34', ' three-quarter')}")
         for k in ("front34", "rear34")]
    P.row(o).save(os.path.join(OUT, "panels-open.png"))

    g = [P.label(P.on_grey(os.path.join(RD, f"gloss_{k}.png")), f"car paint (metal_carpaint matcap), {k.replace('34', ' three-quarter')}")
         for k in ("front34", "rear34")]
    P.row(g).save(os.path.join(OUT, "panels-gloss.png"))

    cam = rep1["cameras"]["side"]
    x0, y0 = cam["win"][0], cam["win"][1]
    side = Image.open(os.path.join(RD, "view_side.png")).convert("RGBA")
    base = crop(cam["win"], 2).convert("RGBA")
    over = base.copy()
    over.alpha_composite(side)
    lines = base.convert("RGB").copy()
    dr = ImageDraw.Draw(lines)
    for a, b in seam_lines():
        pa = ((X_MID + a[1] * S_SIDE - x0) * 2, (GROUND - a[2] * S_SIDE - y0) * 2)
        pb = ((X_MID + b[1] * S_SIDE - x0) * 2, (GROUND - b[2] * S_SIDE - y0) * 2)
        dr.line([pa, pb], fill=(255, 0, 255), width=2)
    ol = chk["outline"]["all"]
    P.stack([P.label(over.convert("RGB"), "G2 panels in clay over the sheet's side view at the G0 registration (194.552 px/m, "
                                          "hubs 429.38 / 983.86 px, ground 349.79); body outline mean "
                                          f"{ol['mean_cm']:.2f} cm, max {ol['max_cm']:.2f} cm"),
             P.label(lines, "seam and opening lines (each panel's chamfer bottom, 3 mm off the seam) in magenta over the sheet, "
                            "near side (x > 0.3 m)")]).save(os.path.join(OUT, "panels-side.png"))
    print("pictures written")


if __name__ == "__main__":
    main()
