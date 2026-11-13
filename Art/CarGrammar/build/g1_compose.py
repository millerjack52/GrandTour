"""G1 6h pictures: shell-views.png, shell-gloss.png, shell-side.png, shell-quarters.png from the Blender renders and
the approved sheet. Composition helpers from body_builder/bt2_compose.py. System Python (numpy, PIL)."""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "Art", "VehicleTools", "body_builder"))
import bt2_compose as P  # noqa: E402  (on_grey, label, row, stack)

OUT = os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g1-v02")
RD = os.path.join(OUT, "debug", "renders")
rep = json.load(open(os.path.join(OUT, "g1-report.json"), encoding="utf-8"))
g0 = json.load(open(os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g0-v01", "measurements.json"), encoding="utf-8"))
sheet = Image.open(os.path.join(ROOT, g0["sheet"])).convert("RGB")


def crop(win, k=1):
    c = sheet.crop(tuple(win))
    return c.resize((c.width * k, c.height * k), Image.LANCZOS) if k != 1 else c


def half(img):
    return img.resize((img.width // 2, img.height // 2), Image.LANCZOS)


def main():
    cams = rep["cameras"]
    order = ["side", "front", "rear", "top"]
    top_row = [P.label(crop(cams[k]["win"]), f"sheet, {k} view") for k in order]
    bot_row = [P.label(half(P.on_grey(os.path.join(RD, f"view_{k}.png"))), f"G1 shell, {k} (matching orthographic camera, "
                                                                         f"{cams[k]['s']:.1f} px/m)") for k in order]
    P.stack([P.row(top_row), P.row(bot_row)]).save(os.path.join(OUT, "shell-views.png"))

    tiles = []
    for mc, name in (("metal_carpaint", "car paint"), ("check_reflection_horizontal", "stripes")):
        tiles.append(P.row([P.label(P.on_grey(os.path.join(RD, f"gloss_{mc}_{k}.png")), f"{name}, {k.replace('34', ' three-quarter')}")
                            for k in ("front34", "rear34")]))
    P.stack(tiles).save(os.path.join(OUT, "shell-gloss.png"))

    side = Image.open(os.path.join(RD, "view_side.png")).convert("RGBA")
    base = crop(cams["side"]["win"], 2).convert("RGBA")
    over = base.copy()
    over.alpha_composite(side)
    a = np.asarray(side)[..., 3] >= 128
    edge = a & ~(np.roll(a, 1, 0) & np.roll(a, -1, 0) & np.roll(a, 1, 1) & np.roll(a, -1, 1))
    edge = edge | np.roll(edge, 1, 0) | np.roll(edge, 1, 1)
    arr = np.asarray(base.convert("RGB")).copy()
    arr[edge] = (255, 0, 255)
    o = rep["outline"]
    P.stack([P.label(over.convert("RGB"), "G1 shell in clay (glass tint, wheels) over the sheet's side view at the G0 registration "
                                          "(194.552 px/m, hubs 429.38 / 983.86 px, ground 349.79)"),
             P.label(Image.fromarray(arr), f"shell outline (magenta) over the sheet; body outline mean {o['all']['mean_cm']:.2f} cm, "
                                           f"max {o['all']['max_cm']:.2f} cm (targets 1.5 / 4)")]).save(os.path.join(OUT, "shell-side.png"))

    P.row([P.label(P.on_grey(os.path.join(RD, f"quarter_{k}.png")), f"G1 shell, clay with glass tint and wheels, "
                                                                    f"{k.replace('34', ' three-quarter')}") for k in ("front34", "rear34")]
          ).save(os.path.join(OUT, "shell-quarters.png"))
    print("pictures written")


if __name__ == "__main__":
    main()
