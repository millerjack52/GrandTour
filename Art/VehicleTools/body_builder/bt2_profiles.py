"""BT2 v02 debug: station-plane profiles (envelope points against the fitted wall, top and the built round) for
a greenhouse side-rail station, the windscreen header, a tub front-side and a tub tail station.
Writes debug/station-profiles.png. System Python (PIL)."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bt2_fields as B  # noqa: E402

SC = 900  # px per metre
SPAN = 0.55


BIND_COL = {"SIDE": (0, 0, 0), "TOP": (255, 140, 0), "FRONT": (150, 0, 200), "REAR": (150, 0, 200)}


def binding(env, fr, s, E):
    """Which envelope map limits each envelope point (smallest |margin|)."""
    Ox, Oy, nx, ny = [float(np.atleast_1d(v)[0]) for v in fr(s)]
    out = []
    for e in E:
        x, y, z = Ox + e[0] * nx, Oy + e[0] * ny, e[1]
        m = {"SIDE": float(env.side(y, z)) - abs(x), "TOP": float(env.top(abs(x), y)) - z,
             "FRONT": y - float(env.front(abs(x), z)), "REAR": float(env.rear(abs(x), z)) - y}
        out.append(min(m, key=lambda k: abs(m[k]) if np.isfinite(m[k]) else 9.0))
    return out


def tile(d, tag, title, bind):
    E, wall, top, prof, corner, R = (d[tag + k] for k in ("_E", "_wall", "_top", "_prof", "_corner", "_R"))
    cx, cz = corner if np.all(np.isfinite(corner)) else prof[len(prof) // 2]
    W = H = int(SPAN * SC)
    im = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    x0, z0 = cx - SPAN * 0.7, cz - SPAN * 0.7

    def P(r, z):
        return ((r - x0) * SC, H - (z - z0) * SC)

    for g in np.arange(np.floor(x0 * 20) / 20, x0 + SPAN, 0.05):
        dr.line([P(g, z0), P(g, z0 + SPAN)], fill=(235, 235, 235))
    for g in np.arange(np.floor(z0 * 20) / 20, z0 + SPAN, 0.05):
        dr.line([P(x0, g), P(x0 + SPAN, g)], fill=(235, 235, 235))
    for arr, col in ((wall, (0, 0, 255)), (top, (220, 0, 0))):
        pts = [P(a, b) for a, b in arr if x0 - 0.2 < a < x0 + SPAN + 0.2 and z0 - 0.2 < b < z0 + SPAN + 0.2]
        if len(pts) > 1:
            dr.line(pts, fill=col, width=1)
    dr.line([P(a, b) for a, b in prof], fill=(0, 160, 0), width=3)
    for (a, b), k in zip(E, bind):
        p = P(a, b)
        dr.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], outline=BIND_COL[k], width=2)
    p = P(cx, cz)
    dr.line([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], fill=(255, 0, 255), width=2)
    dr.line([p[0] - 6, p[1] + 6, p[0] + 6, p[1] - 6], fill=(255, 0, 255), width=2)
    q0 = P(cx - 0.4, cz - 0.4)
    dr.line([q0, P(cx + 0.1, cz + 0.1)], fill=(150, 150, 150), width=1)
    dr.text((6, 4), f"{title}  s={float(d[tag + '_s'][0]):.3f}  R used {R[0]:.3f} (measured {R[1]:.3f})", fill=(0, 0, 0))
    dr.text((6, 18), "circles = blueprint envelope (rays 15..75 deg), limited by", fill=(0, 0, 0))
    dr.text((6, 46), "SIDE map (black), TOP (orange), FRONT/REAR (purple); blue = wall field, red = top field", fill=(0, 0, 0))
    dr.text((6, 32), "green = built profile, magenta x = wall/top corner, grey = 45 deg ray; grid 5 cm", fill=(0, 0, 0))
    return im


def main():
    d = np.load(os.path.join(B.OUT_DIR, "bt2-profiles-debug.npz"))
    env = B.F.Envelope(np.load(os.path.join(B.F.IN_DIR, "maps.npz")))
    spec = [("gh_side_rail", "greenhouse side rail", B.gframe), ("gh_windscreen_header", "windscreen header (centre plane)", B.gframe),
            ("tub_front_side", "tub front side", B.F.frame), ("tub_tail", "tub tail", B.F.frame)]
    tiles = []
    for tag, title, fr in spec:
        bind = binding(env, fr, float(d[tag + "_s"][0]), d[tag + "_E"])
        print(tag, " ".join(bind))
        tiles.append(tile(d, tag, title, bind))
    W = sum(t.width for t in tiles) + 10 * 3
    out = Image.new("RGB", (W, tiles[0].height), (255, 255, 255))
    x = 0
    for t in tiles:
        out.paste(t, (x, 0))
        x += t.width + 10
    out.save(os.path.join(B.DEBUG_DIR, "station-profiles.png"))
    print(out.size)


if __name__ == "__main__":
    main()
