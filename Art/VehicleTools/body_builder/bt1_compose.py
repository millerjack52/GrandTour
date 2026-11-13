"""BT1 pictures and report: tub-views.png, tub-gloss.png, tub-side.png and report.json from the renders
and numbers written by bt1_fields.py and bt1_blender.py. System Python (numpy + PIL).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scaffold_cage"))
import sc_common as C  # noqa: E402

sys.path.insert(0, HERE)
import bt_paths as BP  # noqa: E402

OUT_DIR = BP.OUT_DIR
BG = (205, 207, 208)
GAP = 10
LABEL_H = 26
TARGETS = {"dist_median_cm": 1.0, "dist_p95_cm": 3.5, "fold_max_deg": 12.0, "profile_mean_cm": 1.0, "profile_max_cm": 2.5}
DEVIATIONS = [
    "Penalty strength (4c, 4d): the RMS targets are below what the knot spacing can reach even with no penalty "
    "(floors in report.json fits.*.rms_floor_cm; wall 0.686 cm vs 0.5), and a near-zero penalty leaves the weight-0 "
    "regions unconstrained (wall field values from -50 to +7 m). Used the largest penalty whose weighted RMS stays "
    "within floor + target (the plan's budget read as what smoothing may cost above the best fit). A first try with "
    "1.25 x floor (wall penalty 0.011) left visible flutes at the nose and tail at the knot scale.",
    "Top fits (4d): TOP cells that were inpainted in v02 (bonnet scoop, roof scoop, wing end-plate feet, mirror, "
    "wing-rejected cells) get weight 0.3, as the plan does for the inpainted arch openings in the wall field.",
    "Cowl and backlight scans (4d): a scan that meets the slope at its very first position (no flat surface before "
    "it) counts as no detection; the backlight scan discarded x = 0.64..0.80 (9 points, all at y = 2.00).",
    "Curve fits (4d): the one rejection pass drops points more than 2.5 x the first-fit RMS off.",
    "Rounds (4e): the offset curves are intersected as polylines (coarse 1 cm, then 2 mm). A centre is kept only "
    "if the circle does not cut the used parts of the two curves (2 % tolerance), the arc turns the short way, the wall "
    "tangent is below the wall/top corner and the top tangent inward of it. Where several centres would remain, the R "
    "search takes the one that best matches the envelope and the mesh stations the one nearest the previous "
    "station's centre (in the final run every station had exactly one valid centre).",
    "Envelope profile for R (4e): rays from (rho_c - 0.4, z_c - 0.4), the point 0.4 m inside the corner along both "
    "axes, so the 45-degree ray passes through the corner; 25 rays 15..75 degrees; RMS of point-to-profile distance.",
    "R smoothing (4e): the P-spline along s (knots 0.50) uses penalty 0.1; the cabin blend runs over the 0.15 m "
    "outside each end of the cabin zone, so R is exactly 0.03 inside it.",
    "Mesh (4f): stations spaced 0.02998 m (206 stations from the front to the rear centre plane). The rear fan "
    "never meets the backlight-base curve (y_bl(0) + 0.02 = 1.70 < Y_FAN_REAR = 1.72), so its top rows end at the "
    "rear fan centre: a second pole.",
    "Fold detector (4g): edges whose faces touch a lower-boundary vertex or one of the two fan-centre poles are "
    "skipped.",
    "Distance check (4g): SIDE boxes by (Y, Z), TOP boxes by (|X|, Y) at any height, the lamp-pod FRONT box by "
    "(|X|, Z) on the front fan (Y < -1.60) only; arch openings as in SC2.",
    "Centre-line profile (4g): vertical ray at x = 0; bonnet = Y < y_cowl(0) - 0.02, deck = Y > y_bl(0) + 0.02; "
    "a column is skipped when the reference or tub top lies in an SC1 box.",
]


DEVIATIONS_V2 = [
    "v02 robust fits: each of the four passes sets weight = base weight x biweight of the current residual "
    "(c = 2.0 cm), not a running product over passes.",
    "v02 penalties: the v01 penalties (wall 0.7739, A_front 0.4123, A_rear 0.2063) x 1, 4, 16, fixed; no new "
    "selection, although the top fits now weight inpainted cells 0.",
    "v02 wall rows: where z_env lies within 2 cm of the wall tangent point or above it, the 31 wall rows are spread "
    "evenly from z_L instead (count in report.json env_row_fallback_stations).",
    "v02 z_L / z_env: computed on a 1 cm grid of s and taken at the nearest fine sample for each station, so a leg "
    "falls between two stations as before; z_L smoothing runs separately on each run of samples outside the arches.",
]


def on_grey(path):
    im = Image.open(path).convert("RGBA")
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
    rv = json.load(open(os.path.join(OUT_DIR, "bt1-review.json"), encoding="utf-8"))
    fields = json.load(open(os.path.join(OUT_DIR, "bt1-fields.json"), encoding="utf-8"))
    R = rv["renders"]
    names = [("front", "front"), ("rear", "rear"), ("front34", "front three-quarter"), ("rear34", "rear three-quarter")]
    top = row([label(on_grey(R[f"view_{k}_blueprint"]), f"blueprint (corrected scaffold), {t}") for k, t in names])
    bot = row([label(on_grey(R[f"view_{k}_tub"]), f"tub master, {t}") for k, t in names])
    stack([top, bot]).save(os.path.join(OUT_DIR, "tub-views.png"))
    rows = []
    for mc, title in (("metal_carpaint", "matcap metal_carpaint"), ("check_reflection_horizontal", "matcap check_reflection_horizontal")):
        if f"gloss_{mc}_front34" in R:
            rows.append(row([label(on_grey(R[f"gloss_{mc}_front34"]), f"{title}, front three-quarter"),
                             label(on_grey(R[f"gloss_{mc}_rear34"]), f"{title}, rear three-quarter")]))
    stack(rows).save(os.path.join(OUT_DIR, "tub-gloss.png"))
    clay = label(ticks(on_grey(R["side_tub_wheels"])), "tub master in clay with wheel proxies (reference frame: 400 px/m, mid-wheelbase x 893, ground y 757)")
    ref = Image.open(C.REF_SIDE).convert("RGB")
    a = np.asarray(Image.open(R["side_tub_only"]).convert("RGBA"))[:, :, 3] > 127
    arr = np.asarray(ref).copy()
    arr[outline(a)] = [255, 0, 255]
    ov = label(ticks(Image.fromarray(arr)), "tub outline (magenta) over the approved side image")
    stack([clay, ov]).save(os.path.join(OUT_DIR, "tub-side.png"))

    dist, fold, prof = rv["distance"], rv["folds"], rv["centre_profile"]
    acc = {
        "dist_median_cm": [dist["median_cm"], TARGETS["dist_median_cm"], dist["median_cm"] <= TARGETS["dist_median_cm"]],
        "dist_p95_cm": [dist["p95_cm"], TARGETS["dist_p95_cm"], dist["p95_cm"] <= TARGETS["dist_p95_cm"]],
        "fold_max_deg": [fold["max_deg"], TARGETS["fold_max_deg"], fold["max_deg"] <= TARGETS["fold_max_deg"]],
        "profile_mean_cm": [prof["mean_cm"], TARGETS["profile_mean_cm"], prof["mean_cm"] <= TARGETS["profile_mean_cm"]],
        "profile_max_cm": [prof["max_cm"], TARGETS["profile_max_cm"], prof["max_cm"] <= TARGETS["profile_max_cm"]],
    }
    report = {
        "stage": "BT1 tub master", "version": BP.VERSION, "variant": BP.VARIANT if BP.V2 else None, "fits": {"wall": fields["wall"], **{k: v for k, v in fields["tops"].items()}},
        "rounds": fields["rounds"], "ends": fields["ends"], "mesh": fields["mesh"], "frame": fields["frame"],
        "cowl_curve": fields["cowl_curve"], "backlight_curve": fields["backlight_curve"],
        "distance": dist, "folds": fold, "centre_profile": prof, "dimensions": rv["dimensions"],
        "wheel_proxies": rv["wheel_proxies"], "targets": acc, "deviations": [d for d in DEVIATIONS if not (BP.V2 and d.startswith("Top fits (4d)"))] + (DEVIATIONS_V2 if BP.V2 else []),
        "lower_line": fields.get("lower_line"), "env_row_fallback_stations": fields.get("env_row_fallback_stations"),
        "pictures": {n: os.path.join(OUT_DIR, n) for n in ("tub-views.png", "tub-gloss.png", "tub-side.png")}
        | {"tub-fields.png": os.path.join(OUT_DIR, "debug", "tub-fields.png")},
    }
    with open(os.path.join(OUT_DIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    for k, v in acc.items():
        print(f"{k:16s} {v[0]:.3f} target {v[1]} -> {'PASS' if v[2] else 'FAIL'}")


if __name__ == "__main__":
    main()
