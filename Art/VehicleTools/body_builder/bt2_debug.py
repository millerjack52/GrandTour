"""BT2 debug picture debug/gh-fields.png: greenhouse wall field Dg over (s, z) with weights, robust drops and
residuals; base, wall tangent and corner heights; header/rail R along s; A_roof cells and the footprint on TOP."""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bt2_fields as B  # noqa: E402

SC = 3


def main():
    d = np.load(os.path.join(B.OUT_DIR, "bt2-fields-debug.npz"))
    maps = np.load(os.path.join(B.F.IN_DIR, "maps.npz"))
    s, z, rho, w, wr, pred = d["gs"], d["gz"], d["grho"], d["gw"], d["gw_rob"], d["gpred"]
    cw = 2 * SC
    W, H = len(s) * cw, len(z) * cw

    def img(rgb):
        a = np.transpose(rgb, (1, 0, 2))[::-1].astype(np.uint8)
        return Image.fromarray(a).resize((W, H), Image.NEAREST)

    g = np.clip(pred / 1.3, 0, 1) * 200 + 40
    rgb = np.stack([g, g, g], -1)
    rgb[w == 0] = rgb[w == 0] * 0.55 + np.array([0, 0, 110]) * 0.45
    zr = (w > 0) & (wr == 0)
    rgb[zr] = rgb[zr] * 0.4 + np.array([255, 120, 0]) * 0.6
    rgb[~np.isfinite(rho)] = [250, 220, 220]
    p1 = img(rgb)
    r = pred - rho
    gg = np.clip(0.5 + r / 0.04, 0, 1)
    rgb2 = np.stack([255 * gg, 160 + 0 * gg, 255 * (1 - gg)], -1)
    rgb2[w == 0] = [235, 235, 235]
    p2 = img(rgb2)

    def sx(v):
        return (v - s[0]) / (s[1] - s[0]) * cw + cw / 2

    def zy(v):
        return H - ((v - z[0]) / (z[1] - z[0]) * cw + cw / 2)

    for p, t in ((p1, "Dg(s,z) (grey 0..1.3 m); blue tint w=0, orange dropped by the biweight, pink no crossing; magenta base, orange wall tangent, red corner"),
                 (p2, "residual Dg - rho where w>0 (red +2 cm, blue -2 cm)")):
        dr = ImageDraw.Draw(p)
        sg = d["sg"]
        dr.line([(sx(a), zy(b)) for a, b in zip(sg, d["zbase"])], fill=(255, 0, 255), width=2)
        dr.line([(sx(a), zy(b)) for a, b in zip(sg, d["zwt"])], fill=(255, 150, 0), width=2)
        dr.line([(sx(a), zy(b)) for a, b in zip(sg, d["zcorner"]) if np.isfinite(b)], fill=(255, 0, 0), width=1)
        for v in (B.Y_GF, B.Y_GR):
            dr.line([sx(v), 0, sx(v), H], fill=(0, 200, 255))
        dr.text((6, 4), t, fill=(255, 255, 255) if p is p1 else (0, 0, 0))
    RH = 220
    pr = Image.new("RGB", (W, RH), (255, 255, 255))
    dr = ImageDraw.Draw(pr)

    def ry(v):
        return RH - 20 - v / 0.32 * (RH - 40)

    for v in (0.0, 0.1, 0.2, 0.3):
        dr.line([0, ry(v), W, ry(v)], fill=(225, 225, 225))
        dr.text((4, ry(v) - 12), f"{v:.1f}", fill=(120, 120, 120))
    sg = d["sg"]
    for a, b in zip(sg, d["Rs"]):
        if np.isfinite(b):
            dr.ellipse([sx(a) - 2, ry(b) - 2, sx(a) + 2, ry(b) + 2], outline=(120, 120, 120))
    dr.line([(sx(a), ry(b)) for a, b in zip(sg, d["Rg"])], fill=(0, 0, 255), width=2)
    for v in (B.Y_GF, B.Y_GR):
        dr.line([sx(v), 0, sx(v), RH], fill=(0, 200, 255))
    dr.text((6, 4), "header / rail R along s: grey R* per station, blue final R (median of 5, P-spline, exact end slopes)", fill=(0, 0, 0))
    T = maps["TOP"]
    xs, ys = maps["xs"], maps["ys"]
    gt = np.clip((T - 0.2) / 1.55, 0, 1) * 200 + 40
    rgbt = np.stack([gt, gt, gt], -1)
    rgbt[~np.isfinite(T)] = [255, 240, 240]
    rm = d["roof_mask"]
    rgbt[rm] = rgbt[rm] * 0.7 + np.array([0, 160, 90]) * 0.3
    a = np.transpose(rgbt, (1, 0, 2))
    a = np.transpose(a, (1, 0, 2))[::-1].astype(np.uint8)
    k = 2
    pt = Image.fromarray(np.ascontiguousarray(a)).resize((a.shape[1] * k, a.shape[0] * k), Image.NEAREST)
    d2 = ImageDraw.Draw(pt)
    nx = len(xs)

    def P(xv, yv):
        return ((yv - ys[0]) / 0.01 * k + k / 2, (nx - 1 - xv / 0.01) * k + k / 2)

    fp = d["footprint"]
    d2.line([P(x, y) for x, y in fp], fill=(255, 0, 255), width=2)
    d2.text((6, 4), "clean TOP: green tint A_roof cells; magenta greenhouse footprint (base curve)", fill=(0, 0, 160))
    Wt = max(W, pt.width)
    out = Image.new("RGB", (Wt, H * 2 + RH + pt.height + 30), (255, 255, 255))
    y = 0
    for im in (p1, p2, pr, pt):
        out.paste(im, (0, y))
        y += im.height + 10
    out.save(os.path.join(B.DEBUG_DIR, "gh-fields.png"))
    print(out.size)


if __name__ == "__main__":
    main()
