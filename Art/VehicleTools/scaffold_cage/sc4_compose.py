"""SC4 part 2 (system Python): compose side-comparison.png, views.png, cage-wire.png, gloss.png from the
renders of sc4_review.py, and write report.json (numbers, acceptance, deviations).

Plan: docs/SCAFFOLD_CAGE_PLAN.md section 5.
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sc_common as C  # noqa: E402

BG = (205, 207, 208)
GAP = 10
LABEL_H = 26
ACC = {"fit_max_mm": 2.0, "dist_median_cm": 0.6, "dist_p95_cm": 2.0, "upper_mean_cm": 1.0, "upper_max_cm": 3.0,
       "arch_max_cm": 1.5}
ACC_V2 = {"dist_median_cm": 0.8, "dist_p95_cm": 3.0, "upper_mean_cm": 1.0, "upper_max_cm": 3.0, "arch_p95_cm": 2.0}
DEVIATIONS = [
    "SC1 hole fill of R seeded from the image border and from every pixel outside E (2,908 px filled; a "
    "border-only fill would add 62,225 px, 58,566 of them the gap under the car closed by the ground shadow).",
    "SC2 wing centre-plane classifier: blade rows = thin top pair with a gap below and underside within 0.10 m of "
    "the median underside (ceiling 1.2435 m).",
    "SC2 symmetrise: cells valid on one side only set empty (TOP 221, FRONT 33, REAR 33, SIDE 0).",
    "SC2 inpaint only where the raw map had body; TOP cells beyond the body half-width (from SIDE) left empty (90 cells).",
    "SC2 SIDE/TOP/FRONT exclusion boxes tightened or widened to the measured parts plus about 3 cm (see sc2-clean.json).",
    "SC4 cage-wire edge visibility: an edge sample is drawn if the ray from the camera meets the limit surface no "
    "earlier than 3 cm before the sample.",
    "SC4 distance exclusions: SIDE boxes by (Y, Z), TOP boxes by (|X|, Y) at any height, the FRONT lamp-pod box by "
    "(|X|, Z) on the front cap only (Y <= Y_FRONT), arch openings as in SC2.",
]


DEVIATIONS_V2 = [
    "v02 SC2 lamp-pod FRONT box top raised 0.86 -> 0.89 m: with s2 about 1.03 at the nose the pod measured "
    "Z 0.66..0.86, so the v01 box no longer had a margin.",
    "v02 s2: the reference top is taken at the upper edge of the top filled pixel (row - 0.5); the mesh top "
    "is found by ray casts with bisection to 0.02 px; columns whose reference or mesh top lies in an SC1 box are excluded.",
    "v02 T end blend: z_T = TOP[x_T, Y] looked up at the blended x_T, then the same median 7 cm + Gaussian 3 cm "
    "as in v01.",
]


def on_grey(path, size=None):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im)
    out = bg.convert("RGB")
    if size:
        out = out.resize(size, Image.LANCZOS)
    return out


def label(img, text):
    out = Image.new("RGB", (img.width, img.height + LABEL_H), (255, 255, 255))
    out.paste(img, (0, LABEL_H))
    ImageDraw.Draw(out).text((8, 6), text, fill=(0, 0, 0))
    return out


def ticks(img):
    d = ImageDraw.Draw(img)
    d.line([0, C.PX_GROUND, img.width, C.PX_GROUND], fill=(0, 140, 0), width=1)
    for cx, cy in C.WHEEL_PX:
        d.line([cx, cy - 14, cx, cy + 14], fill=(0, 140, 0), width=2)
        d.line([cx - 14, cy, cx + 14, cy], fill=(0, 140, 0), width=2)
        d.line([cx, C.PX_GROUND - 12, cx, C.PX_GROUND + 12], fill=(0, 140, 0), width=2)
    return img


def outline(mask):
    e = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
    o = e.copy()
    o[1:] |= e[:-1]
    o[:, 1:] |= e[:, :-1]
    return o


def stack(rows, gap=GAP):
    W = max(r.width for r in rows)
    H = sum(r.height for r in rows) + gap * (len(rows) - 1)
    out = Image.new("RGB", (W, H), (255, 255, 255))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + gap
    return out


def side_by_side(cols, gap=GAP):
    W = sum(c.width for c in cols) + gap * (len(cols) - 1)
    H = max(c.height for c in cols)
    out = Image.new("RGB", (W, H), (255, 255, 255))
    x = 0
    for c in cols:
        out.paste(c, (x, 0))
        x += c.width + gap
    return out


def main():
    rv = C.load_json("sc4-review.json")
    R = rv["renders"]
    # side-comparison
    ref = Image.open(C.REF_SIDE).convert("RGB")
    row1 = label(ticks(ref.copy()), "approved reference (02-side-profile.png)")
    clay = ticks(on_grey(R["side_cage"]))
    row2 = label(clay, "evaluated cage in clay with wheel proxies (Workbench, same frame: 400 px/m, mid-wheelbase x 893, ground y 757)")
    a = np.asarray(Image.open(R["wire_side"]).convert("RGBA"))[:, :, 3]  # cage only, same side camera
    sil = a > 127
    wheels_only = None
    arr = np.asarray(ref).copy()
    arr[outline(sil)] = [255, 0, 255]
    row3 = label(ticks(Image.fromarray(arr)), "cage outline (magenta, cage only) over the reference")
    stack([row1, row2, row3]).save(os.path.join(C.OUT_DIR, "side-comparison.png"))

    # views
    names = [("front", "front"), ("rear", "rear"), ("front34", "front three-quarter"), ("rear34", "rear three-quarter")]
    top = [label(on_grey(R[f"view_{k}_scaffold"]), f"corrected scaffold, {t}") for k, t in names]
    bot = [label(on_grey(R[f"view_{k}_cage"]), f"cage (subdivided), {t}") for k, t in names]
    stack([side_by_side(top), side_by_side(bot)]).save(os.path.join(C.OUT_DIR, "views.png"))

    # cage-wire
    wire = json.load(open(os.path.join(C.OUT_DIR, "sc4-wire.json"), encoding="utf-8"))
    tiles = []
    for v, title in (("front34", "front three-quarter"), ("side", "side (reference frame)")):
        img = on_grey(R[f"wire_{v}"])
        d = ImageDraw.Draw(img)
        for seg in wire[v]["segments"]:
            for p, q in zip(seg[:-1], seg[1:]):
                if p[2] and q[2]:
                    d.line([p[0], p[1], q[0], q[1]], fill=(20, 40, 160), width=2)
        if v == "side":
            img = img.resize((int(img.width * 800 / img.height), 800), Image.LANCZOS)
        tiles.append(label(img, f"control cage edges (blue, visible ones) over the subdivided surface, {title}"))
    side_by_side(tiles).save(os.path.join(C.OUT_DIR, "cage-wire.png"))

    # gloss
    rows = []
    for mc, title in (("metal_carpaint", "matcap metal_carpaint"), ("check_reflection_horizontal", "matcap check_reflection_horizontal")):
        if f"gloss_{mc}_front34" not in R:
            continue
        rows.append(side_by_side([label(on_grey(R[f"gloss_{mc}_front34"]), f"{title}, front three-quarter"),
                                  label(on_grey(R[f"gloss_{mc}_rear34"]), f"{title}, rear three-quarter")]))
    stack(rows).save(os.path.join(C.OUT_DIR, "gloss.png"))

    # report.json
    fit = rv["fit_residual"]
    dist = rv["distance_to_scaffold"]
    up = rv["side_silhouette"]["upper_contour"]
    ar = rv["side_silhouette"]["arch_edge"]
    acc = {
        "fit_max_mm": [fit["max_mm"], ACC["fit_max_mm"], fit["max_mm"] < ACC["fit_max_mm"]],
        "dist_median_cm": [dist["median_cm"], ACC["dist_median_cm"], dist["median_cm"] <= ACC["dist_median_cm"]],
        "dist_p95_cm": [dist["p95_cm"], ACC["dist_p95_cm"], dist["p95_cm"] <= ACC["dist_p95_cm"]],
        "upper_mean_cm": [up["mean_cm"], ACC["upper_mean_cm"], up["mean_cm"] <= ACC["upper_mean_cm"]],
        "upper_max_cm": [up["max_cm"], ACC["upper_max_cm"], up["max_cm"] <= ACC["upper_max_cm"]],
        "arch_max_cm": [ar["max_cm"], ACC["arch_max_cm"], ar["max_cm"] <= ACC["arch_max_cm"]],
        "topology_ok": [rv["topology"]["nonmanifold_other_than_lower_boundary"], 0,
                        rv["topology"]["nonmanifold_other_than_lower_boundary"] == 0 and rv["topology"]["all_quads"]],
    }
    if C.V2:
        acc = {
            "dist_median_cm": [dist["median_cm"], ACC_V2["dist_median_cm"], dist["median_cm"] <= ACC_V2["dist_median_cm"]],
            "dist_p95_cm": [dist["p95_cm"], ACC_V2["dist_p95_cm"], dist["p95_cm"] <= ACC_V2["dist_p95_cm"]],
            "upper_mean_cm_150_1700": [up["mean_cm"], ACC_V2["upper_mean_cm"], up["mean_cm"] <= ACC_V2["upper_mean_cm"]],
            "upper_max_cm_150_1700": [up["max_cm"], ACC_V2["upper_max_cm"], up["max_cm"] <= ACC_V2["upper_max_cm"]],
            "arch_p95_cm": [ar["p95_cm"], ACC_V2["arch_p95_cm"], ar["p95_cm"] <= ACC_V2["arch_p95_cm"]],
            "topology_ok": acc["topology_ok"],
        }
    report = {
        "plan_revision": 5 if C.V2 else 4,
        "SC1": {k: C.load_json("side-fit.json")[k] for k in ("iou_smoothed", "bumper_offset_px", "WIDTH_SCALE", "d_k", "s_k", "boxes_px")},
        "SC2": {"check": {k: v for k, v in C.load_json("sc2-check.json").items() if k != "wing"},
                "wing": {k: v for k, v in C.load_json("sc2-check.json")["wing"].items() if k != "profile"},
                "clean": C.load_json("sc2-clean.json")},
        "SC3": {k: v for k, v in C.load_json("cage-lines.json").items() if k not in ("lines",)},
        "SC3_fit": {k: v for k, v in C.load_json("sc3-fit.json").items() if k != "fitted_cage"},
        "SC4": {k: v for k, v in rv.items() if k not in ("renders", "cage_top_row_px")},
        "acceptance": acc,
        "deviations": DEVIATIONS + (DEVIATIONS_V2 if C.V2 else []),
        "pictures": {n: os.path.join(C.OUT_DIR, n) for n in ("side-comparison.png", "views.png", "cage-wire.png", "gloss.png")},
    }
    C.save_json("report.json", report)
    for k, v in acc.items():
        print(f"{k:16s} value {v[0]:.3f} limit {v[1]} -> {'PASS' if v[2] else 'FAIL'}")


if __name__ == "__main__":
    main()
