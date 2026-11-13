"""BT2 pictures and report: master-views.png, master-gloss.png, master-side.png, master-zones.png and
report.json from bt2_fields.py / bt2_blender.py outputs. System Python (numpy + PIL)."""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scaffold_cage"))
import sc_common as C  # noqa: E402

BT2_VERSION = os.environ.get("BT2_VERSION", "v01")
BT2_VARIANT = os.environ.get("BT2_VARIANT", "R100")
OUT_ROOT = os.path.join(C.ROOT, r"Art\Export\VehicleTools", "impreza-builder-bt2-" + BT2_VERSION)
OUT_DIR = os.path.join(OUT_ROOT, BT2_VARIANT) if BT2_VERSION != "v01" else OUT_ROOT
BG = (205, 207, 208)
GAP, LABEL_H = 10, 26
TARGETS = {"dist_median_cm": 1.2, "dist_p95_cm": 4.0, "fold_max_deg": 12.0, "outline_mean_cm": 1.2, "outline_max_cm": 3.5}
DEVIATIONS = [
    "7a exact symmetry: imposed as exact linear constraints dF/ds = 0 at both ends of s (and dA/dx = 0 at x = 0) by "
    "null-space elimination. With the uniform extended knots used since BT1, tying the first two coefficients would "
    "not make the end slope zero (that holds for clamped knots); the null-space form is exact for any knot placement. "
    "End slopes after the refit: wall below 1e-15, Dg below 1e-15.",
    "7a: the R spline along s (tub and greenhouse) also gets exact zero slope at both ends; the P4 tail seam came from "
    "the radius varying across the centre plane, not from the wall field (its end slope was already about 0 in v02).",
    "7c/7d penalty: the floor rule needs a target RMS; used the tub's wall target (0.5 cm) for Dg and the tub's top "
    "target (0.4 cm) for A_roof, then x SMOOTH = 4. A_roof uses ROBUST_C_CM = 1.5 like Dg.",
    "7e zones for reporting R: header = fan angle above 45 degrees, corner = up to 45 degrees.",
    "7g: where the ray meets the footprint only outboard of the tub's top tangent point (rear door / C-pillar base, "
    "12 stations at s 1.065..1.394, base up to about 2 cm outboard), the tub top has zero length; the literal rule ran "
    "the top to the centre line and put a lid across the cabin (39 cm from the blueprint).",
    "7h greenhouse roof rows: rho_k = rho_t * (1 - (k/12)^1.3), the tub's top-row spacing.",
    "7i glass: side-facing = |n_x| >= |n_y| of the face normal; the widest point at a height is the largest Dg over "
    "the side stations at that height.",
    "Carried from BT1 (accepted): penalty floor rule, robust passes (weight = base x biweight each pass), round validity "
    "and tangent-aware continuity, curve-scan start-hit filter, z_L/z_env on a 1 cm s grid.",
    "Fold detector: skips edges whose faces touch the tub lower boundary, the tub-greenhouse junction (tub top end row, "
    "greenhouse base row) or a pole (tub front and rear fan centres, greenhouse front and rear fan centres).",
]
DEVIATIONS_V02 = [
    "8.1 mid-slope rule, read as: per s row, slope_mid = median of d rho/dz over the middle third of [z_lo, z_hi]; a cell "
    "is valid while |d rho/dz - slope_mid| <= 0.35, scanning up from the middle of the range, the first failing cell "
    "ends the wall above; cells below the middle are each checked against slope_mid (no downward scan cut). Tub: z_lo = "
    "z_L with the 2 cm lower margin kept from BT1, z_hi = highest finite cell at or below z_B - 3 cm in the cabin "
    "(below any cabin cut), highest finite cell outside it. Arch cells keep their BT1 handling but are tested against "
    "slope_mid instead of the old 1.2 limit. Greenhouse: z_lo (base estimate) = lowest finite cell at least 3 cm above U, "
    "z_hi = highest finite cell. Weighted cells: tub 11,039 (v01) -> 5,755; greenhouse 3,363 -> 2,584.",
    "8.3 R60: the scale is applied to the smoothed measured R spline (after the median-of-5 and P-spline, before the "
    "cabin blend on the tub), then floored at 0.03; the round search itself is unchanged.",
    "8.4 glass vertex colour: the 7i rules evaluated at each grid vertex with the vertex normal from central differences "
    "of the station grid (one-sided at the ends); welded vertices take the max of the grid points merged into them; "
    "colour = clay 0.5 / glass 0.12 linear, FLOAT_COLOR on the point domain, Workbench colour type Attribute.",
    "8.6 corner miss: blueprint = the envelope (the clean maps) along the 45 degree ray of the station plane from "
    "(corner - 0.4, corner - 0.4); master = the first crossing of that ray with the built profile; signed + = master "
    "outside the envelope. Statistics on |miss| by zone, signed median also given.",
]


def on_grey(p):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB")


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
    return img


def outline(mask):
    e = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
    o = e.copy()
    o[1:] |= e[:-1]
    o[:, 1:] |= e[:, :-1]
    return o


def stack(rows):
    W = max(r.width for r in rows)
    out = Image.new("RGB", (W, sum(r.height for r in rows) + GAP * (len(rows) - 1)), (255, 255, 255))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + GAP
    return out


def row(cols):
    out = Image.new("RGB", (sum(c.width for c in cols) + GAP * (len(cols) - 1), max(c.height for c in cols)), (255, 255, 255))
    x = 0
    for c in cols:
        out.paste(c, (x, 0))
        x += c.width + GAP
    return out


def main():
    rv = json.load(open(os.path.join(OUT_DIR, "bt2-review.json"), encoding="utf-8"))
    fd = json.load(open(os.path.join(OUT_DIR, "bt2-fields.json"), encoding="utf-8"))
    R = rv["renders"]
    names = [("front", "front"), ("rear", "rear"), ("front34", "front three-quarter"), ("rear34", "rear three-quarter")]
    stack([row([label(on_grey(R[f"view_{k}_blueprint"]), f"blueprint, {t}") for k, t in names]),
           row([label(on_grey(R[f"view_{k}_master"]), f"body master (tub + greenhouse), {t}") for k, t in names])]).save(
        os.path.join(OUT_DIR, "master-views.png"))
    rows = []
    for mc, t in (("metal_carpaint", "car paint"), ("check_reflection_horizontal", "stripes")):
        rows.append(row([label(on_grey(R[f"gloss_{mc}_front34"]), f"{t}, front three-quarter"),
                         label(on_grey(R[f"gloss_{mc}_rear34"]), f"{t}, rear three-quarter")]))
    stack(rows).save(os.path.join(OUT_DIR, "master-gloss.png"))
    clay = label(ticks(on_grey(R["side_master_wheels"])), "body master in clay with wheel proxies (reference frame)")
    ref = Image.open(C.REF_SIDE).convert("RGB")
    a = np.asarray(Image.open(R["side_master_only"]).convert("RGBA"))[:, :, 3] > 127
    arr = np.asarray(ref).copy()
    arr[outline(a)] = [255, 0, 255]
    stack([clay, label(ticks(Image.fromarray(arr)), "body master outline (magenta) over the approved side image")]).save(
        os.path.join(OUT_DIR, "master-side.png"))
    side = on_grey(R["zones_side"])
    side = side.resize((int(side.width * 560 / side.height), 560), Image.LANCZOS)
    stack([row([label(on_grey(R["zones_front34"]), "zones: grey body, dark glass tint, front three-quarter"),
                label(on_grey(R["zones_rear34"]), "rear three-quarter")]),
           row([label(side, "side"), label(on_grey(R["zones_front"]), "front")])]).save(os.path.join(OUT_DIR, "master-zones.png"))

    dist, fold, outl = rv["distance"], rv["folds"], rv["upper_outline"]
    acc = {
        "dist_median_cm": [dist["median_cm"], TARGETS["dist_median_cm"], dist["median_cm"] <= TARGETS["dist_median_cm"]],
        "dist_p95_cm": [dist["p95_cm"], TARGETS["dist_p95_cm"], dist["p95_cm"] <= TARGETS["dist_p95_cm"]],
        "fold_max_deg": [fold["max_deg"], TARGETS["fold_max_deg"], fold["max_deg"] <= TARGETS["fold_max_deg"]],
        "outline_mean_cm": [outl["mean_cm"], TARGETS["outline_mean_cm"], outl["mean_cm"] <= TARGETS["outline_mean_cm"]],
        "outline_max_cm": [outl["max_cm"], TARGETS["outline_max_cm"], outl["max_cm"] <= TARGETS["outline_max_cm"]],
    }
    report = {"stage": "BT2 greenhouse master", "targets": acc, "distance": dist, "folds": fold, "upper_outline": outl,
              "centre_profile": rv["centre_profile"], "dimensions": rv["dimensions"], "tub": fd["tub"], "greenhouse": fd["greenhouse"],
              "deviations": DEVIATIONS + (DEVIATIONS_V02 if BT2_VERSION != "v01" else []),
              "variant": fd.get("variant"), "round_scale": fd.get("round_scale"),
              "R_measured_by_zone": fd.get("R_measured_by_zone"), "corner_miss_by_zone": fd.get("corner_miss_by_zone"),
              "pictures": {n: os.path.join(OUT_DIR, n) for n in ("master-views.png", "master-gloss.png", "master-side.png", "master-zones.png")}
              | {"gh-fields.png": os.path.join(OUT_DIR, "debug", "gh-fields.png")}}
    with open(os.path.join(OUT_DIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    for k, v in acc.items():
        print(f"{k:16s} {v[0]:.3f} target {v[1]} -> {'PASS' if v[2] else 'FAIL'}")


if __name__ == "__main__":
    main()
