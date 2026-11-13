"""BT1 v02: tub-variants.png (car-paint matcap, front and rear three-quarter, one labelled row per variant)
and variants.json (the 4g numbers side by side). System Python (PIL)."""
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("BT_VERSION", "v02")
import bt_paths as BP  # noqa: E402

VARIANTS = ["P1", "P4", "P16"]
BG = (205, 207, 208)


def on_grey(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def main():
    rows = []
    table = {}
    for v in VARIANTS:
        d = os.path.join(BP.OUT_ROOT, v)
        rv = json.load(open(os.path.join(d, "bt1-review.json"), encoding="utf-8"))
        rep = json.load(open(os.path.join(d, "report.json"), encoding="utf-8"))
        r = rv["renders"]
        a = on_grey(r["gloss_metal_carpaint_front34"])
        b = on_grey(r["gloss_metal_carpaint_rear34"])
        lam = rep["fits"]["wall"]["penalty"]
        lab = Image.new("RGB", (a.width + b.width + 10, 34), (255, 255, 255))
        ImageDraw.Draw(lab).text((8, 10), f"{v}: penalty = v01 x {BP.PENALTY_FACTOR if False else {'P1': 1, 'P4': 4, 'P16': 16}[v]} "
                                          f"(wall {lam:.3g}, A_front {rep['fits']['A_front']['penalty']:.3g}, "
                                          f"A_rear {rep['fits']['A_rear']['penalty']:.3g}); car-paint matcap, front and rear three-quarter",
                                 fill=(0, 0, 0))
        row = Image.new("RGB", (a.width + b.width + 10, a.height + 34), (255, 255, 255))
        row.paste(lab, (0, 0))
        row.paste(a, (0, 34))
        row.paste(b, (a.width + 10, 34))
        rows.append(row)
        table[v] = {
            "fits": {k: {kk: rep["fits"][k].get(kk) for kk in ("penalty", "weighted_rms_cm", "p95_cm", "robust_weighted_rms_cm",
                                                               "cells_zeroed_by_biweight")} for k in ("wall", "A_front", "A_rear")},
            "distance": {k: rep["distance"][k] for k in ("median_cm", "p95_cm", "max_cm", "max_at")},
            "folds": {k: rep["folds"][k] for k in ("max_deg", "at", "edges_over_10deg")},
            "centre_profile": {k: rep["centre_profile"][k] for k in ("mean_cm", "max_cm")},
            "R_by_zone": rep["rounds"]["by_zone"], "dimensions": {k: rep["dimensions"][k] for k in ("width_doors_m", "length_m")},
            "targets": rep["targets"],
        }
    W = max(r.width for r in rows)
    out = Image.new("RGB", (W, sum(r.height for r in rows) + 10 * (len(rows) - 1)), (255, 255, 255))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + 10
    out.save(os.path.join(BP.OUT_ROOT, "tub-variants.png"))
    with open(os.path.join(BP.OUT_ROOT, "variants.json"), "w", encoding="utf-8") as f:
        json.dump(table, f, indent=1)
    print("wrote", os.path.join(BP.OUT_ROOT, "tub-variants.png"))


if __name__ == "__main__":
    main()
