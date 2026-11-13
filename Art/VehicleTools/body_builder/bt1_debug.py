"""BT1 debug picture debug/tub-fields.png: wall field over (s, z) with weights and residuals, R along s,
cowl and backlight curves on TOP. System Python (numpy + PIL).
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bt1_fields as F  # noqa: E402

SC = 2  # px per cm


def to_img(a, lo, hi):
    g = np.clip((a - lo) / (hi - lo), 0, 1)
    return (40 + 200 * g)


def main():
    d = np.load(os.path.join(F.OUT_DIR, "bt1-fields-debug.npz"))
    info = json.load(open(os.path.join(F.OUT_DIR, "bt1-fields.json"), encoding="utf-8"))
    maps = np.load(os.path.join(F.IN_DIR, "maps.npz"))
    s, z, rho, w, pred = d["s"], d["z"], d["rho"], d["w"], d["pred"]
    ns, nz = len(s), len(z)
    cw = 2 * SC  # cell 2 cm
    W = ns * cw
    H = nz * cw

    def panel_field():
        g = to_img(pred, 0.0, 1.1)
        rgb = np.stack([g, g, g], -1)
        rgb[w == 0] = rgb[w == 0] * 0.55 + np.array([0, 0, 110]) * 0.45
        rgb[w == F.ARCH_WEIGHT] = rgb[w == F.ARCH_WEIGHT] * 0.6 + np.array([0, 140, 0]) * 0.4
        if "w_robust" in d.files:
            zr = (w > 0) & (d["w_robust"] == 0)
            rgb[zr] = rgb[zr] * 0.4 + np.array([255, 120, 0]) * 0.6
        img = np.transpose(rgb, (1, 0, 2))[::-1].astype(np.uint8)
        im = Image.fromarray(img).resize((W, H), Image.NEAREST)
        return im

    def panel_resid():
        r = pred - rho
        g = np.clip(0.5 + r / 0.04, 0, 1)
        rgb = np.stack([255 * g, 255 * (1 - np.abs(g - 0.5) * 2) * 0.6 + 100, 255 * (1 - g)], -1)
        rgb[w == 0] = [235, 235, 235]
        img = np.transpose(rgb, (1, 0, 2))[::-1].astype(np.uint8)
        return Image.fromarray(img).resize((W, H), Image.NEAREST)

    def sx(sv):
        return (sv - s[0]) / (s[1] - s[0]) * cw + cw / 2

    def zy(zv):
        return H - ((zv - z[0]) / (z[1] - z[0]) * cw + cw / 2)

    def overlay(im, title):
        dr = ImageDraw.Draw(im)
        st = info["stations"]
        sm = d["s_mesh"]
        dr.line([(sx(a), zy(b)) for a, b in zip(sm, [m["z_L"] for m in st])], fill=(255, 0, 255), width=2)
        if "z_env" in d.files:
            dr.line([(sx(a), zy(b)) for a, b in zip(sm, d["z_env"])], fill=(0, 255, 255), width=1)
        dr.line([(sx(a), zy(b)) for a, b in zip(sm, d["zw_t"])], fill=(255, 150, 0), width=2)
        dr.line([(sx(a), zy(b)) for a, b in zip(sm, d["corner_z"]) if np.isfinite(b)], fill=(255, 0, 0), width=1)
        for v, c in ((F.Y_FAN_FRONT, (0, 200, 255)), (F.Y_FAN_REAR, (0, 200, 255)), (F.Y_CAB0, (255, 255, 0)), (F.Y_CAB1, (255, 255, 0))):
            dr.line([sx(v), 0, sx(v), H], fill=c, width=1)
        dr.text((6, 4), title, fill=(255, 255, 255))
        return im

    p1 = overlay(panel_field(), "wall field Dw(s,z) (grey 0..1.1 m); blue tint w=0, green tint w=0.3, orange = zeroed by the biweight; magenta z_L, cyan z_env, orange line wall tangent, red corner; cyan verticals fan limits, yellow cabin zone")
    p2 = overlay(panel_resid(), "residual Dw - rho where w>0 (red +2 cm, blue -2 cm)")
    # R along s
    RH = 240
    pr = Image.new("RGB", (W, RH), (255, 255, 255))
    dr = ImageDraw.Draw(pr)
    sm = d["s_mesh"]

    Rmax = F.R_RANGE[1] + 0.02

    def ry(R):
        return RH - 20 - R / Rmax * (RH - 40)

    for Rv in np.arange(0.0, Rmax, 0.1):
        dr.line([0, ry(Rv), W, ry(Rv)], fill=(220, 220, 220))
        dr.text((4, ry(Rv) - 12), f"{Rv:.1f}", fill=(120, 120, 120))
    for a, b in zip(sm, d["R_star"]):
        if np.isfinite(b):
            dr.ellipse([sx(a) - 2, ry(b) - 2, sx(a) + 2, ry(b) + 2], outline=(120, 120, 120))
    for a, b in zip(sm, d["R_med"]):
        if np.isfinite(b):
            dr.point((sx(a), ry(b)), fill=(0, 150, 0))
    dr.line([(sx(a), ry(b)) for a, b in zip(sm, d["R_sp"])], fill=(255, 0, 0), width=1)
    dr.line([(sx(a), ry(b)) for a, b in zip(sm, d["R_fin"])], fill=(0, 0, 255), width=2)
    for v in (F.Y_FAN_FRONT, F.Y_FAN_REAR, F.Y_CAB0, F.Y_CAB1):
        dr.line([sx(v), 0, sx(v), RH], fill=(0, 200, 255), width=1)
    dr.text((6, 4), "R along s: grey R* per station, green median of 5, red P-spline, blue final R (cabin 0.03 with blends)", fill=(0, 0, 0))
    # TOP with cowl / backlight
    T = maps["TOP"]
    xs, ys = maps["xs"], maps["ys"]
    g = to_img(T, 0.2, 1.75)
    rgb = np.stack([g, g, g], -1)
    rgb[~np.isfinite(T)] = [255, 240, 240]
    for mk, col in ((d["A_front_mask"], (0, 90, 200)), (d["A_rear_mask"], (200, 90, 0))):
        rgb[mk] = rgb[mk] * 0.75 + np.array(col) * 0.25
    img = np.transpose(rgb, (1, 0, 2))[:, ::-1][::-1].astype(np.uint8)  # rows = X (centre at bottom), cols = Y
    img = np.transpose(rgb, (1, 0, 2)).astype(np.uint8)  # rows = Y, cols = X
    img = np.transpose(img, (1, 0, 2))[::-1]  # rows = X descending, cols = Y
    k = 2
    pt = Image.fromarray(np.ascontiguousarray(img)).resize((img.shape[1] * k, img.shape[0] * k), Image.NEAREST)
    d2 = ImageDraw.Draw(pt)
    nx = len(xs)

    def P(xv, yv):
        return ((yv - ys[0]) / 0.01 * k + k / 2, (nx - 1 - xv / 0.01) * k + k / 2)

    for pts, co, col in ((d["cowl_pts"], info["cowl_curve"], (255, 0, 0)), (d["bl_pts"], info["backlight_curve"], (255, 0, 255))):
        for xv, yv in pts:
            p = P(xv, yv)
            d2.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], outline=col)
        xx = np.linspace(0, 1.1, 60)
        d2.line([P(a, co[0] + co[1] * a * a) for a in xx], fill=col, width=2)
    d2.text((6, 4), "clean TOP (Y across, X up from the centre line); blue tint A_front cells, orange tint A_rear cells; "
                    "red cowl points and fit, magenta backlight points and fit", fill=(0, 0, 160))
    Wt = max(W, pt.width)
    out = Image.new("RGB", (Wt, H * 2 + RH + pt.height + 30), (255, 255, 255))
    y = 0
    for im in (p1, p2, pr, pt):
        out.paste(im, (0, y))
        y += im.height + 10
    out.save(os.path.join(F.DEBUG_DIR, "tub-fields.png"))
    print(out.size)


if __name__ == "__main__":
    main()
