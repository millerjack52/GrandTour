"""G0 4b and 4c: register the approved Land Cruiser 80 sheet and measure the hard points (schema/hardpoints.md)
and the "measure" rule rows from it by image analysis.

Input : Art/References/Vehicles/LandCruiser80_v01/01_exterior_proportions_v2.png (1536 x 1024; side, top,
        front, rear views)
Output: Art/Export/VehicleTools/landcruiser-grammar-g0-v01/measurements.json (every value with its pixel
        evidence and the drawing primitives used by draw_lc80_hardpoints.py).

Frame: metres, X lateral, front = -Y, Z up, origin mid-wheelbase on the ground. Pixel coordinates are image
(x right, y down); a boundary between pixel rows k-1 and k is written k - 0.5.
System Python with numpy and PIL only.
"""
import json
import math
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SHEET = os.path.join(ROOT, "Art", "References", "Vehicles", "LandCruiser80_v01", "01_exterior_proportions_v2.png")
OUT_DIR = os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g0-v01")

WB_M = 2.850  # real car, Toyota global vehicle lineage page (verified)
SCALE_TOL = 0.03

# view windows (x0, y0, x1, y1) on the sheet
SIDE_WIN = (230, 0, 1300, 358)
TOP_WIN = (270, 360, 1240, 690)
FRONT_WIN = (270, 680, 650, 1000)
REAR_WIN = (870, 680, 1260, 1000)

IM = np.asarray(Image.open(SHEET).convert("RGB")).astype(float)
H_IMG, W_IMG = IM.shape[:2]
R, G, B = IM[..., 0], IM[..., 1], IM[..., 2]
L = (R + G + B) / 3.0
IVORY = (R - B >= 12) & (L >= 140)
GLASS = (B - R >= 4) & (L >= 80) & (L <= 210)
DARK = L < 110
DARKN = DARK & (np.abs(R - B) < 15)  # neutral dark: tyres, cladding, bumpers (not the red tail lamps)
ORANGE = (R - B >= 25) & ~IVORY


def _erode(m):
    p = np.pad(m, 1, constant_values=False)
    out = np.ones_like(m)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            out &= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    return out


def _dilate(m):
    p = np.pad(m, 1, constant_values=False)
    out = np.zeros_like(m)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            out |= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    return out


# object mask: not background grey; a 3x3 opening removes the 1-2 px guide lines drawn on the sheet
SOLID = _dilate(_erode((L < 165) | (R - B > 10)))

RES = {"sheet": os.path.relpath(SHEET, ROOT), "image_size": [W_IMG, H_IMG], "views": {}, "hardpoints": {}, "rules": {},
       "extras": {}, "real_car": {}, "draw": [], "notes": []}


def draw(kind, sub, **kw):
    d = {"kind": kind, "sub": sub}
    d.update({k: (np.round(v, 2).tolist() if isinstance(v, np.ndarray) else v) for k, v in kw.items()})
    RES["draw"].append(d)


def rnd(v, n=3):
    return None if v is None else float(round(float(v), n))


# ------------------------------------------------------------------ scans
def left_sil(y, x0, x1, mask=SOLID):
    row = mask[y, x0:x1]
    i = np.argmax(row)
    return x0 + i - 0.5 if row[i] else None


def right_sil(y, x0, x1, mask=SOLID):
    row = mask[y, x0:x1]
    if not row.any():
        return None
    return x0 + len(row) - 1 - np.argmax(row[::-1]) + 0.5


def top_sil(x, y0, y1, mask=SOLID):
    c = mask[y0:y1, x]
    i = np.argmax(c)
    return y0 + i - 0.5 if c[i] else None


def bottom_sil(x, y0, y1, mask=SOLID):
    c = mask[y0:y1, x]
    if not c.any():
        return None
    return y0 + len(c) - 1 - np.argmax(c[::-1]) + 0.5


def robust_line(u, v, k=2.5, iters=4):
    """Fit v = a + b u with MAD rejection; returns a, b, rms, n_used, mask."""
    u = np.asarray(u, float)
    v = np.asarray(v, float)
    m = np.isfinite(u) & np.isfinite(v)
    for _ in range(iters):
        A = np.c_[np.ones(m.sum()), u[m]]
        a, b = np.linalg.lstsq(A, v[m], rcond=None)[0]
        r = v - (a + b * u)
        mad = np.median(np.abs(r[m])) + 0.3
        m2 = np.isfinite(u) & np.isfinite(v) & (np.abs(r) <= k * 1.4826 * mad)
        if m2.sum() == m.sum():
            break
        m = m2
    r = v - (a + b * u)
    return float(a), float(b), float(np.sqrt(np.mean(r[m] ** 2))), int(m.sum()), m


def intersect(l1, l2):
    """Lines in the form x = a + b y ('xy') or y = a + b x ('yx'); returns (x, y)."""
    def to_abc(l):
        form, a, b = l
        return (1.0, -b, a) if form == "xy" else (-b, 1.0, a)  # x - b y = a  or  -b x + y = a
    a1, b1, c1 = to_abc(l1)
    a2, b2, c2 = to_abc(l2)
    det = a1 * b2 - a2 * b1
    return (c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det


def fit_circle(P):
    P = np.asarray(P, float)
    x, y = P[:, 0], P[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    c = np.linalg.lstsq(A, x * x + y * y, rcond=None)[0]
    r = math.sqrt(c[2] + c[0] ** 2 + c[1] ** 2)
    return c[0], c[1], r, np.hypot(x - c[0], y - c[1]) - r


def bil(x, y):
    x0, y0 = int(x), int(y)
    fx, fy = x - x0, y - y0
    return (L[y0, x0] * (1 - fx) * (1 - fy) + L[y0, x0 + 1] * fx * (1 - fy) + L[y0 + 1, x0] * (1 - fx) * fy
            + L[y0 + 1, x0 + 1] * fx * fy)


def ray_profile(cx, cy, a_deg, k0, k1, step=0.25):
    t = math.radians(a_deg)
    ks = np.arange(k0, k1, step)
    return ks, np.array([bil(cx + k * math.cos(t), cy + k * math.sin(t)) for k in ks]), (math.cos(t), math.sin(t))


def crossing(ks, v, j_from, j_to, level):
    """First k (sub-sample) in [j_from, j_to) where v crosses level (either direction)."""
    for j in range(j_from, min(j_to, len(v) - 1)):
        if (v[j] - level) * (v[j + 1] - level) <= 0 and v[j] != v[j + 1]:
            return ks[j] + (ks[1] - ks[0]) * (v[j] - level) / (v[j] - v[j + 1])
    return None


# ------------------------------------------------------------------ 4b side view registration
def rim_circle(gx, gy):
    """Steel rim outer edge (light rim against the dark tyre) on rays; skips rays along the vertical guide line."""
    cx, cy = gx, gy
    for _ in range(3):
        P = []
        for a in range(0, 360, 3):
            if min(abs(a - 90), abs(a - 270)) < 10:
                continue
            ks, v, (dx, dy) = ray_profile(cx, cy, a, 37, 62)
            n = 16  # 4 px of dark
            for i in range(len(ks) - n):
                if np.all(v[i:i + n] < 90):
                    j0 = max(0, i - 12)
                    mid = 0.5 * (v[j0:i + 1].max() + v[i:i + n].min())
                    k = crossing(ks, v, j0, i + n, mid)
                    if k is not None:
                        P.append((cx + k * dx, cy + k * dy))
                    break
        P = np.array(P)
        x0, y0, r, res = fit_circle(P)
        keep = np.abs(res) < 2.5 * max(np.median(np.abs(res)), 0.3)
        cx, cy, r, res = fit_circle(P[keep])
    return cx, cy, r, P[keep], float(np.sqrt(np.mean(res ** 2)))


def tyre_edges(cx, cy, sectors):
    """Tyre outer edge against the background on rays: midpoint crossing between the tyre and the first
    background-bright sample."""
    out = []
    for a0, a1 in sectors:
        for a in np.arange(a0, a1 + 0.01, 2.0):
            ks, v, (dx, dy) = ray_profile(cx, cy, a, 58, 100)
            i = int(np.argmax(v > 140))
            if v[i] <= 140:
                continue
            lo = float(np.median(v[max(0, i - 12):i]))
            k = crossing(ks, v, max(0, i - 12), i + 1, 0.5 * (lo + v[i]))
            if k is not None:
                out.append((cx + k * dx, cy + k * dy, float(a), float(k)))
    return np.array(out)


rims = [rim_circle(430, 280), rim_circle(984, 280)]
(xf, yf, rf, Pf, rmsf), (xr, yr, rr, Pr, rmsr) = rims
WB_PX = xr - xf
S = WB_PX / WB_M  # side view px per metre
X_MID = 0.5 * (xf + xr)
tyres = []
for (cx, cy, *_rest) in rims:
    side = tyre_edges(cx, cy, ((12, 48), (132, 168)))
    bot = tyre_edges(cx, cy, ((82, 98),))
    tyres.append((side, bot))
# rear wheel: its lower-left sector meets the running-board bracket shadow; use only sectors with background outside
r_side = [np.median(tyres[0][0][:, 3]), np.median(tyres[1][0][tyres[1][0][:, 2] < 90, 3])]
r_bot = [np.median(tyres[0][1][:, 3]), np.median(tyres[1][1][:, 3])]
GROUND = float(np.mean([yf + r_bot[0], yr + r_bot[1]]))


def Ym(x):
    return (x - X_MID) / S


def Zm(y):
    return (GROUND - y) / S


RES["views"]["side"] = {
    "role": "authority",
    "front_hub_px": [rnd(xf, 2), rnd(yf, 2)], "rear_hub_px": [rnd(xr, 2), rnd(yr, 2)],
    "rim_fit_rms_px": [rnd(rmsf, 2), rnd(rmsr, 2)], "rim_radius_px": [rnd(rf, 2), rnd(rr, 2)],
    "wheelbase_px": rnd(WB_PX, 2), "px_per_m": rnd(S, 3), "ground_y_px": rnd(GROUND, 2), "x_mid_px": rnd(X_MID, 2),
    "hub_level_difference_px": rnd(yr - yf, 2),
    "method": "hub = centre of a circle fitted to the steel rim's outer edge (rays every 3 deg, rays along the "
              "vertical guide line skipped); ground = hub y + tyre radius straight down (82..98 deg rays)"}
for (cx, cy, r, P, _), tag in zip(rims, ("front", "rear")):
    draw("circle", "reg", c=[cx, cy], r=r, label=None)
    draw("cross", "reg", c=[cx, cy], label=f"{tag} hub")
draw("hline", "reg", y=GROUND, x=[SIDE_WIN[0], SIDE_WIN[2]], label="ground Z=0")


# ------------------------------------------------------------------ hard point helper
def hp(name, value, unit, source, conf, evidence, real=None, **extra):
    d = {"value": rnd(value, 3 if unit == "m" else 1), "unit": unit, "source": source, "confidence": conf,
         "evidence": evidence}
    if real is not None:
        d["real_car"] = real
    d.update(extra)
    RES["hardpoints"][name] = d


TYRE_R_PX = float(np.mean(r_side))
hp("WB", WB_M, "m", "real-car data (registration)", "measured",
   f"hub centres x {xf:.2f} / {xr:.2f} px (rim circle fits, rms {rmsf:.2f} / {rmsr:.2f} px) -> {WB_PX:.2f} px = 2.850 m; "
   f"side scale {S:.3f} px/m; hub rows differ by {yr - yf:+.2f} px",
   real={"value": 2.850, "status": "verified", "source": "toyota-global vehicle lineage id60013935: 2850 mm"})
hp("TYRE_R", TYRE_R_PX / S, "m", "sheet pixels", "measured",
   f"tyre edge radius from the hub on rays 12-48 and 132-168 deg (background outside): front median "
   f"{r_side[0]:.2f} px, rear {r_side[1]:.2f} px (rear lower-left sector dropped: running-board bracket); "
   f"straight down only {r_bot[0]:.2f} / {r_bot[1]:.2f} px = static loaded radius {np.mean(r_bot) / S:.3f} m "
   f"(the drawn tyre is flattened at the contact)",
   real={"value": 0.396, "status": "unverified", "source": "275/70R16 (Fable's recollection): 203.2 + 192.5 mm"},
   static_loaded_radius_m=rnd(np.mean(r_bot) / S))
for (side, bot), (cx, cy, *_r) in zip(tyres, rims):
    for p in side:
        draw("point", "reg", c=[p[0], p[1]])
    for p in bot:
        draw("point", "reg", c=[p[0], p[1]])

# ------------------------------------------------------------------ overall length, roof, clipping
rows_bumper = range(200, 272)
fl = [(left_sil(y, SIDE_WIN[0], 700), y) for y in rows_bumper]
x_front, y_front = min((v, y) for v, y in fl if v is not None)
rl = [(right_sil(y, 900, SIDE_WIN[2]), y) for y in rows_bumper]
x_rear, y_rear = max((v, y) for v, y in rl if v is not None)
LENGTH_PX = x_rear - x_front
LENGTH_M = LENGTH_PX / S
cols = [x for x in range(660, 1130)]
tops = np.array([top_sil(x, 0, 120) for x in cols], float)
i_roof = int(np.nanargmin(tops))
Y_ROOF_PX = float(tops[i_roof])
roof_clear = Y_ROOF_PX + 0.5  # rows of background above the roof outline
hp("OH_F", (xf - x_front) / S, "m", "sheet pixels", "measured",
   f"front bumper face x {x_front:.1f} px (left-most object pixel over rows 200-271, at row {y_front}); front hub x {xf:.2f}")
hp("OH_R", (x_rear - xr) / S, "m", "sheet pixels", "measured",
   f"rear bumper face x {x_rear:.1f} px (right-most object pixel over rows 200-271, at row {y_rear}); rear hub x {xr:.2f}")
hp("H_ROOF", Zm(Y_ROOF_PX), "m", "sheet pixels", "measured",
   f"roof top outline y {Y_ROOF_PX:.1f} px at x {cols[i_roof]} (top-most object pixel over x 660-1129); ground y {GROUND:.2f}",
   real={"value": 1.900, "status": "verified", "source": "toyota-global id60013935: height 1900 mm (Fable's note said 1.86)"})
RES["views"]["side"]["length_px"] = rnd(LENGTH_PX, 1)
RES["views"]["side"]["roof_clipped"] = bool(Y_ROOF_PX < 1)
RES["views"]["side"]["roof_margin_px"] = rnd(roof_clear, 1)
RES["real_car"]["length"] = {"sheet_m": rnd(LENGTH_M), "real_m": 4.820, "status": "verified",
                             "source": "toyota-global id60013935: 4820 mm (HDJ81V, HZJ81V; FJ80G 4970)",
                             "difference_m": rnd(LENGTH_M - 4.820)}
draw("vline", "dims", x=x_front, y=[150, 300], label=f"bumper face OH_F")
draw("vline", "dims", x=x_rear, y=[150, 300], label=f"bumper face OH_R")
draw("hline", "gh", y=Y_ROOF_PX, x=[cols[0], cols[-1]], label="H_ROOF", label_at="mid")

# ------------------------------------------------------------------ side lines: bonnet, face, windscreen, roof, tail
bx = np.arange(350, 531)
by = np.array([top_sil(x, 90, 200) for x in bx], float)
ba, bb, brms, bn, _ = robust_line(bx, by)
BONNET = ("yx", ba, bb)
fy = np.arange(160, 205)
fxv = np.array([left_sil(y, SIDE_WIN[0], 450) for y in fy], float)
fa, fb, frms, fn, _ = robust_line(fy, fxv)
FACE = ("xy", fa, fb)
wy = np.arange(44, 97)
wxv = np.array([left_sil(y, 520, 720) for y in wy], float)
wa, wb, wrms, wn, _ = robust_line(wy, wxv)
WS = ("xy", wa, wb)
rx = np.arange(700, 1111)
ryv = np.array([top_sil(x, 0, 80) for x in rx], float)
ra, rb, rrms, rn, _ = robust_line(rx, ryv)
ROOF = ("yx", ra, rb)
ty = np.arange(44, 113)
txv = np.array([right_sil(y, 1000, SIDE_WIN[2]) for y in ty], float)
ta, tb, trms, tn, _ = robust_line(ty, txv)
TAIL_UP = ("xy", ta, tb)
ly = np.arange(128, 200)
lxv = np.array([right_sil(y, 1000, SIDE_WIN[2]) for y in ly], float)
la, lb, lrms, ln_, _ = robust_line(ly, lxv)
TAIL_LO = ("xy", la, lb)

cowl = intersect(WS, BONNET)
roof_f = intersect(WS, ROOF)
roof_r = intersect(ROOF, TAIL_UP)
lead = intersect(BONNET, FACE)


def rake_deg(b_xy):
    """Angle from vertical of a line x = a + b y (image); positive = top rearward (leans back)."""
    return math.degrees(math.atan(-b_xy))  # y up the image is -y; rearward is +x


RAKE_WS = rake_deg(wb)
RAKE_FRONT = rake_deg(fb)
RAKE_RS = -rake_deg(tb)  # rear faces: positive = top forward (leans forward)
RAKE_REAR = -rake_deg(lb)
hp("RAKE_WS", RAKE_WS, "deg", "sheet pixels", "measured",
   f"windscreen silhouette (centre line) left edge over rows 44-96, x = {wa:.1f} + {wb:.4f} y (rms {wrms:.2f} px, n {wn}); "
   f"positive = top rearward")
hp("RAKE_FRONT", RAKE_FRONT, "deg", "sheet pixels", "measured",
   f"front face (lamp and grille panel) left silhouette over rows 160-204, x = {fa:.1f} + {fb:.4f} y (rms {frms:.2f}, n {fn}); "
   f"positive = top rearward")
hp("RAKE_RS", RAKE_RS, "deg", "sheet pixels", "measured",
   f"tail silhouette above the belt (D-pillar / tailgate glass frame) rows 44-112, x = {ta:.1f} + {tb:.4f} y (rms {trms:.2f}, n {tn}); "
   f"positive = top forward")
hp("RAKE_REAR", RAKE_REAR, "deg", "sheet pixels", "measured",
   f"tail silhouette below the belt rows 128-199 (tail lamp side included), x = {la:.1f} + {lb:.4f} y (rms {lrms:.2f}, n {ln_}); "
   f"positive = top forward")
hp("H_COWL", Zm(cowl[1]), "m", "sheet pixels", "derived",
   f"windscreen line meets the bonnet top line (y = {ba:.1f} + {bb:.4f} x over x 350-530, rms {brms:.2f}) at ({cowl[0]:.1f}, {cowl[1]:.1f}) px; "
   f"the side silhouette of a plan-bowed windscreen is its centre line")
hp("Y_COWL", Ym(cowl[0]), "m", "sheet pixels", "derived", f"same point, x {cowl[0]:.1f} px")
hp("Y_ROOF_F", Ym(roof_f[0]), "m", "sheet pixels", "derived",
   f"windscreen line meets the roof top line (y = {ra:.2f} + {rb:.5f} x over x 700-1110, rms {rrms:.2f}) at ({roof_f[0]:.1f}, {roof_f[1]:.1f}) px")
hp("Y_ROOF_R", Ym(roof_r[0]), "m", "sheet pixels", "derived",
   f"roof top line meets the upper tail line at ({roof_r[0]:.1f}, {roof_r[1]:.1f}) px")
hp("H_BONNET_F", Zm(lead[1]), "m", "sheet pixels", "derived",
   f"bonnet top line meets the front face line at ({lead[0]:.1f}, {lead[1]:.1f}) px (sharp-corner point; the drawn edge is rounded)")
for l, y0, y1, sub, lab in ((WS, roof_f[1], cowl[1] + 10, "gh", f"windscreen {RAKE_WS:.1f} deg"),
                            (FACE, lead[1] - 5, 206, "fr", f"front face {RAKE_FRONT:.1f} deg"),
                            (TAIL_UP, roof_r[1] - 3, 125, "gh", f"rear screen / D {RAKE_RS:.1f} deg"),
                            (TAIL_LO, 125, 210, "fr", f"tail face {RAKE_REAR:.1f} deg")):
    draw("line", sub, p=[l[1] + l[2] * y0, y0], q=[l[1] + l[2] * y1, y1], label=lab, label_at="mid")
draw("line", "fr", p=[lead[0] - 3, BONNET[1] + BONNET[2] * (lead[0] - 3)], q=[cowl[0] + 5, BONNET[1] + BONNET[2] * (cowl[0] + 5)],
     label="bonnet top line", label_at="mid")
draw("line", "gh", p=[roof_f[0] - 5, ROOF[1] + ROOF[2] * (roof_f[0] - 5)], q=[roof_r[0] + 5, ROOF[1] + ROOF[2] * (roof_r[0] + 5)], label=None)
for pnt, lab in ((cowl, "cowl"), (roof_f, "roof front"), (roof_r, "roof rear"), (lead, "bonnet edge")):
    draw("cross", "gh" if lab.startswith("roof") or lab == "cowl" else "fr", c=list(pnt), label=lab)

# bonnet leading edge round: gap from the sharp corner to the silhouette along the bisector
bis = np.array([1.0, 1.0]) / math.sqrt(2)  # into the body (rearward and down)
gap = None
for k in np.arange(0, 40, 0.25):
    x, y = lead[0] + k * bis[0], lead[1] + k * bis[1]
    if SOLID[int(round(y)), int(round(x))]:
        gap = k
        break
corner_angle = math.radians(90 + math.degrees(math.atan(bb)) + RAKE_FRONT)  # interior angle bonnet/face
r_lead = gap / (1 / math.sin(corner_angle / 2) - 1) / S if gap else None

# ------------------------------------------------------------------ belt, glass bottom
belt_pts, glass_pts = [], []
for x in range(600, 1126):
    colG = GLASS[60:136, x]
    if not colG.any():
        continue
    gb = 60 + len(colG) - 1 - np.argmax(colG[::-1])
    for y in range(gb + 1, 145):
        if IVORY[y:y + 4, x].all():
            belt_pts.append((x, y - 0.5))
            break
    glass_pts.append((x, gb + 0.5))
belt_pts = np.array(belt_pts)
glass_pts = np.array(glass_pts)
bta, btb, btrms, btn, btm = robust_line(belt_pts[:, 0], belt_pts[:, 1])
gla, glb, glrms, gln, _ = robust_line(glass_pts[:, 0], glass_pts[:, 1])
y_belt_mid = bta + btb * 860
H_BELT = Zm(y_belt_mid)
hp("H_BELT", H_BELT, "m", "sheet pixels", "measured",
   f"top of the body-colour door skin under the side glass, {btn} columns x 600-1125: y = {bta:.2f} + {btb:.5f} x "
   f"(rms {btrms:.2f} px), {y_belt_mid:.1f} px at mid-doors; the glass itself ends {gla + glb * 860:.1f} px "
   f"(black belt moulding between, {(y_belt_mid - (gla + glb * 860)) / S * 1000:.0f} mm)",
   glass_bottom_m=rnd(Zm(gla + glb * 860)))
draw("line", "gh", p=[585, bta + btb * 585], q=[1135, bta + btb * 1135], label="H_BELT", label_at="mid")

# ------------------------------------------------------------------ pillars (column vote over the DLO band)
band = slice(50, 111)
gfrac = GLASS[band, :].mean(0)
pill_runs, x = [], 590
while x < 1200:
    if gfrac[x] < 0.25:
        x0 = x
        while x < 1200 and gfrac[x] < 0.25:
            x += 1
        pill_runs.append((x0, x - 1))
    x += 1
pill_runs = [r_ for r_ in pill_runs if r_[1] - r_[0] + 1 >= 10]
RES["extras"]["pillar_runs_px"] = pill_runs


def run_near(xc):
    return min(pill_runs, key=lambda r_: abs(0.5 * (r_[0] + r_[1]) - xc))


Bp, Cp = run_near(770), run_near(935)
# D pillar: from the last glass column to the tail silhouette at the belt band
Dp0 = run_near(1150)[0]
y_dp = int(round(y_belt_mid - 8))
Dp1 = right_sil(y_dp, 1000, SIDE_WIN[2]) - 0.5
pill = {"B": (Bp[0] - 0.5, Bp[1] + 0.5), "C": (Cp[0] - 0.5, Cp[1] + 0.5), "D": (Dp0 - 0.5, Dp1 + 0.5)}
for k, (p0, p1) in pill.items():
    hp(f"Y_{k}", Ym(0.5 * (p0 + p1)), "m", "sheet pixels", "measured",
       f"{k}-pillar = columns with glass in under 25 % of rows 50-110: x {p0:.1f}-{p1:.1f} px (width {(p1 - p0) / S:.3f} m)"
       + ("; the D pillar's rear edge is the tail silhouette at row %d" % y_dp if k == "D" else ""),
       width_m=rnd((p1 - p0) / S))
    draw("vline", "lay", x=0.5 * (p0 + p1), y=[30, y_belt_mid + 4], label=f"Y_{k}", label_at="bottom")
    draw("span", "gh", x=[p0, p1], y=y_belt_mid - 22, label=f"{k} {(p1 - p0) / S:.3f}")

# A pillar: body-colour strip between the windscreen glass and the door glass, rows 50-105; its centre line
# extrapolated to the belt
a_pts = []
for y in range(50, 106):
    xs = np.where(IVORY[y, 560:680])[0]
    if len(xs) < 3:
        continue
    runs = np.split(xs, np.where(np.diff(xs) > 1)[0] + 1)
    run = max(runs, key=len)
    if len(run) >= 3:
        a_pts.append((y, 560 + 0.5 * (run[0] + run[-1]), len(run)))
a_pts = np.array(a_pts)
aa, ab, arms, an, _ = robust_line(a_pts[:, 0], a_pts[:, 1])
x_abase = aa + ab * y_belt_mid
hp("Y_A_BASE", Ym(x_abase), "m", "sheet pixels", "derived",
   f"A-pillar body-colour strip centre over rows 50-105: x = {aa:.1f} + {ab:.4f} y (rms {arms:.2f}, n {an}), at the belt row "
   f"{y_belt_mid:.1f}: x {x_abase:.1f} px (the mirror hides the pillar base itself)")
draw("line", "gh", p=[aa + ab * 45, 45], q=[x_abase, y_belt_mid], label="A pillar")
draw("cross", "lay", c=[x_abase, y_belt_mid], label="Y_A_BASE")
# A pillar seen width (GH-03): from the windscreen silhouette to the door glass front edge
a_w = []
for y in range(50, 100):
    xl = left_sil(y, 520, 720)
    g = np.where(GLASS[y, int(xl) + 20:720])[0]
    if xl is None or not len(g):
        continue
    # the first glass after the windscreen glass strip and the pillar: door glass = first glass run after a gap >= 8 px
    gx = int(xl) + 20 + g
    gaps = np.where(np.diff(gx) >= 8)[0]
    if len(gaps):
        a_w.append((y, gx[gaps[0]] + 0.5, gx[gaps[0] + 1] - 0.5))
a_w = np.array(a_w)
A_PILLAR_W = float(np.median(a_w[:, 2] - a_w[:, 1])) / S if len(a_w) else None

# ------------------------------------------------------------------ sill, cladding
sill, clad_top = [], []
for x in list(range(585, 755)) + list(range(772, 890)):
    c = L[:, x]
    yt = None
    for y in range(205, 240):
        if np.all(c[y:y + 5] < 135):
            yt = y
            break
    if yt is None:
        continue
    for y in range(262, 300):
        if c[y] > 135:
            sill.append((x, y - 0.5))
            break
    clad_top.append((x, yt - 0.5))
sill = np.array(sill)
clad_top = np.array(clad_top)
y_sill = float(np.median(sill[:, 1]))
y_clad = float(np.median(clad_top[:, 1]))
hp("H_SILL", Zm(y_sill), "m", "sheet pixels", "measured",
   f"body lower edge at the doors (first bright row under the dark rocker, x 585-889 minus the B-pillar shut line): median y "
   f"{y_sill:.1f} px (IQR {np.percentile(sill[:, 1], 25):.1f}-{np.percentile(sill[:, 1], 75):.1f}); the running board below "
   f"(to about y 289) is a separate part")
draw("hline", "bs", y=y_sill, x=[560, 910], label="H_SILL")
draw("hline", "bs", y=y_clad, x=[560, 910], label="cladding top")

# underbody between the wheels (side) and the lowest point between the front tyres (front view, below)
ub = []
for x in range(550, 890):  # behind the front mudflap, ahead of the rear tyre
    if 760 <= x <= 766:
        continue
    d = np.where(L[200:int(GROUND) - 2, x] < 100)[0]
    if len(d):
        ub.append((x, 200 + d.max() + 0.5))
ub = np.array(ub)
i_ub = int(np.argmax(ub[:, 1]))
GC_SIDE = Zm(ub[i_ub, 1])

# ------------------------------------------------------------------ arches and flares (side)
arch = {}
for tag, (cx, cy, *_r) in zip(("front", "rear"), rims):
    pts_in, pts_out = [], []
    for a in np.arange(195, 346, 3):
        ks, v, (dx, dy) = ray_profile(cx, cy, a, 70, 140)
        # going outward: tyre -> dark wheel well (<35) -> flare face (~80) -> lighter flare top -> outline -> ivory
        # the well: first run of >= 2 px below 35; the flare: first sample after it that starts >= 2 px above 50
        i0 = next((i for i in range(len(v) - 8) if np.all(v[i:i + 8] < 35)), None)
        if i0 is None:
            continue
        j = next((i for i in range(i0, len(v) - 8) if np.all(v[i:i + 8] >= 50)), None)
        if j is None:
            continue
        k_in = crossing(ks, v, max(i0, j - 8), j + 1, 45)
        jj = j
        if k_in is None:
            continue
        k_out = None
        for i in range(jj + 4, len(v)):
            if v[i] > 185:
                k_out = crossing(ks, v, i - 6, i + 1, 160)
                break
        pts_in.append((cx + k_in * dx, cy + k_in * dy, a, k_in))
        if k_out is not None:
            pts_out.append((cx + k_out * dx, cy + k_out * dy, a, k_out))
    pts_in, pts_out = np.array(pts_in), np.array(pts_out)
    rad = pts_in[:, 3]
    side_sel = (np.abs(pts_in[:, 2] - 270) >= 40)
    top_sel = (np.abs(pts_in[:, 2] - 270) <= 25)
    ytop = pts_in[top_sel, 1]
    arch[tag] = {"centre": (cx, cy), "in": pts_in, "out": pts_out, "r_side_px": float(np.median(rad[side_sel])),
                 "r_top_px": float(cy - ytop.min()), "r_all_med_px": float(np.median(rad)),
                 "flat_px": 0.0,
                 "band_px": float(np.median([o[3] - i_[3] for i_ in pts_in for o in pts_out if o[2] == i_[2]]))}
    # squared top: a flat at the top of a circle of the side radius sits r_side - r_top lower than the circle top;
    # its length is the chord of the side circle at that height (0 when the top is not lower than the sides)
    rs_, rt_ = arch[tag]["r_side_px"], arch[tag]["r_top_px"]
    arch[tag]["flat_px"] = 2 * math.sqrt(rs_ ** 2 - rt_ ** 2) if rt_ < rs_ else 0.0
    for p in pts_in:
        draw("point", "bs", c=[p[0], p[1]])
    for p in pts_out:
        draw("point", "bs2", c=[p[0], p[1]])
    draw("arc", "bs", c=[cx, cy], r=arch[tag]["r_all_med_px"], a=[195, 345], label=f"arch {tag}")
ARCH_R = np.mean([arch[t]["r_all_med_px"] for t in arch]) / S
ARCH_FLAT = np.mean([arch[t]["flat_px"] for t in arch]) / S
hp("ARCH_R", ARCH_R, "m", "sheet pixels", "measured",
   "arch opening = inner edge of the flare (dark wheel well -> flare face, luminance 45 crossing) on rays every 3 deg from "
   "195 to 345 deg about each hub: median radius front %.1f px, rear %.1f px; sides only %.1f / %.1f, top %.1f / %.1f"
   % (arch["front"]["r_all_med_px"], arch["rear"]["r_all_med_px"], arch["front"]["r_side_px"], arch["rear"]["r_side_px"],
      arch["front"]["r_top_px"], arch["rear"]["r_top_px"]))
hp("ARCH_TOP_FLAT", ARCH_FLAT, "m", "sheet pixels", "measured",
   "equivalent flat: chord of the side-radius circle at the opening's top height (rays 245-295 deg), 2 sqrt(r_side^2 - r_top^2) "
   "when the top sits lower than the side circle, else 0: front %.1f px, rear %.1f px (radius sides/top front %.1f/%.1f, rear %.1f/%.1f px)"
   % (arch["front"]["flat_px"], arch["rear"]["flat_px"], arch["front"]["r_side_px"], arch["front"]["r_top_px"],
      arch["rear"]["r_side_px"], arch["rear"]["r_top_px"]))

# ------------------------------------------------------------------ shut lines (thin dark lines in the ivory)
lines = []
for y in range(135, 206):
    for x in range(545, 1000):
        if L[y, x] < 150 and L[y, x - 3] > 185 and L[y, x + 3] > 185 and np.all(L[y, x - 2:x + 3] >= L[y, x]):
            lines.append((x, y))
lines = np.array(lines)
shut = {}
for tag, xc in (("front door leading edge", 571), ("front door rear edge (B)", 763), ("rear door trailing edge", 948)):
    sel = lines[np.abs(lines[:, 0] - xc) <= 9]
    if len(sel) < 10:
        continue
    a_, b_, rms_, n_, _ = robust_line(sel[:, 1], sel[:, 0])
    shut[tag] = {"a": a_, "b": b_, "rms": rms_, "n": n_, "y": [int(sel[:, 1].min()), int(sel[:, 1].max())]}
    y_lo, y_hi = 127, int(sel[:, 1].max())
    draw("line", "lay", p=[a_ + b_ * y_hi, y_hi], q=[a_ + b_ * y_lo, y_lo], label=None)

# ------------------------------------------------------------------ bumpers (side)
def bumper_rows(x0, x1):
    tops_, bots_ = [], []
    for x in range(x0, x1):
        c = DARKN[190:300, x]
        for y in range(len(c) - 10):
            if c[y:y + 10].sum() >= 8:
                tops_.append(190 + y - 0.5)
                yy = y
                while yy < len(c) and (c[yy] or c[yy:yy + 3].any()):
                    yy += 1
                bots_.append(190 + yy - 0.5)
                break
    return float(np.median(tops_)), float(np.median(bots_))


yb_t, yb_b = bumper_rows(int(x_front) + 4, int(x_front) + 40)
yr_t, yr_b = bumper_rows(int(x_rear) - 40, int(x_rear) - 4)
hp("H_BUMPER_T", Zm(yb_t), "m", "sheet pixels", "measured",
   f"front bumper bar top: first row of a mostly dark 10-row run in columns {int(x_front) + 4}-{int(x_front) + 39}, median y {yb_t:.1f} px; "
   f"rear bar {Zm(yr_t):.3f} m (y {yr_t:.1f})", rear_m=rnd(Zm(yr_t)))
hp("H_BUMPER_B", Zm(yb_b), "m", "sheet pixels", "measured",
   f"front bumper bar bottom (end of that dark run, tow hooks excluded by the column range), median y {yb_b:.1f} px; rear bar "
   f"{Zm(yr_b):.3f} m (y {yr_b:.1f})", rear_m=rnd(Zm(yr_b)))
draw("hline", "fr", y=yb_t, x=[x_front - 5, x_front + 110], label="bumper top")
draw("hline", "fr", y=yb_b, x=[x_front - 5, x_front + 110], label="bumper bottom")
draw("hline", "fr", y=yr_t, x=[x_rear - 110, x_rear + 5], label=None)
draw("hline", "fr", y=yr_b, x=[x_rear - 110, x_rear + 5], label=None)
# bumper side length (wrap): the bar's dark run from the face rearward at mid-height ends at the black wheel-well gap
yb_mid = int(round(0.5 * (yb_t + yb_b)))
wrap_end = []
for y in range(yb_mid - 8, yb_mid + 9):
    for x in range(int(x_front) + 10, int(x_front) + 160):
        if L[y, x] < 40 and np.all(L[y, x:x + 4] < 40):
            wrap_end.append(x - 0.5)
            break
x_wrap = float(np.median(wrap_end))
yr_mid = int(round(0.5 * (yr_t + yr_b)))
wrap_end_r = []
for y in range(yr_mid - 8, yr_mid + 9):
    for x in range(int(x_rear) - 10, int(x_rear) - 200, -1):
        if L[y, x] < 40 and np.all(L[y, x - 3:x + 1] < 40):
            wrap_end_r.append(x + 0.5)
            break
x_wrap_r = float(np.median(wrap_end_r)) if wrap_end_r else None
face_at_bumper = FACE[1] + FACE[2] * (yb_t - 2)
draw("span", "fr", x=[x_front, x_wrap], y=yb_mid, label="bumper side length")

# ------------------------------------------------------------------ headlamp in the side view
hl = [(x, y) for y in range(150, 200) for x in range(int(x_front), int(x_front) + 70) if GLASS[y, x] or ORANGE[y, x] or (L[y, x] < 110)]

# ------------------------------------------------------------------ 4b: front and rear views
def view_basics(win, cx_guess):
    x0, y0, x1, y1 = win
    # roof top: top-most object pixel over the middle columns (guide column excluded by the opening)
    cols_ = [x for x in range(cx_guess - 80, cx_guess + 81) if abs(x - cx_guess) > 3]
    tt = [(top_sil(x, y0, y0 + 60), x) for x in cols_]
    y_roof, x_roof = min((t, x) for t, x in tt if t is not None)
    # ground: bottom of the tyres (dark) in the outer 60 px of the object at rows near the bottom
    yb = y1 - 30
    xl = left_sil(yb, x0, x1)
    xr_ = right_sil(yb, x0, x1)
    bots = []
    for x in list(range(int(xl) + 4, int(xl) + 50)) + list(range(int(xr_) - 50, int(xr_) - 4)):
        c = L[yb - 40:y1, x] < 100
        if c.any():
            bots.append(yb - 40 + len(c) - 1 - np.argmax(c[::-1]) + 0.5)
    return y_roof, x_roof, float(np.median(bots))


H_ROOF_M = Zm(Y_ROOF_PX)
views = {}
for name, win, cg in (("front", FRONT_WIN, 459), ("rear", REAR_WIN, 1065)):
    y_roof, x_roof, ground = view_basics(win, cg)
    s_v = (ground - y_roof) / H_ROOF_M
    views[name] = {"win": win, "y_roof": y_roof, "x_roof": x_roof, "ground": ground, "s": s_v}
    RES["views"][name] = {"roof_top_y_px": rnd(y_roof, 1), "ground_y_px": rnd(ground, 1), "height_px": rnd(ground - y_roof, 1),
                          "px_per_m": rnd(s_v, 3), "ratio_to_side": rnd(s_v / S, 4),
                          "disagrees_over_3pct": bool(abs(s_v / S - 1) > SCALE_TOL),
                          "method": "scale = roof height in px / the side view's H_ROOF (%.3f m)" % H_ROOF_M}
    draw("hline", "reg", y=ground, x=[win[0], win[2]], label=f"{name} ground")
    draw("hline", "reg", y=y_roof, x=[win[0] + 60, win[2] - 60], label=None)

# top view scale from the length
tl = [left_sil(y, TOP_WIN[0], 700) for y in range(380, 670) if abs(y - 521) > 2]
tr = [right_sil(y, 900, TOP_WIN[2]) for y in range(380, 670) if abs(y - 521) > 2]
xt0 = min(v for v in tl if v is not None)
xt1 = max(v for v in tr if v is not None)
s_top = (xt1 - xt0) / LENGTH_M
RES["views"]["top"] = {"front_x_px": rnd(xt0, 1), "rear_x_px": rnd(xt1, 1), "length_px": rnd(xt1 - xt0, 1), "px_per_m": rnd(s_top, 3),
                       "ratio_to_side": rnd(s_top / S, 4), "disagrees_over_3pct": bool(abs(s_top / S - 1) > SCALE_TOL),
                       "method": "scale = object length in px / the side view's length (%.3f m)" % LENGTH_M}
draw("vline", "reg", x=xt0, y=[372, 676], label=None)
draw("vline", "reg", x=xt1, y=[372, 676], label=None)


def VZ(view, y):
    return (views[view]["ground"] - y) / views[view]["s"]


def VX(view, dx_px):
    return dx_px / views[view]["s"]


# --- front view widths
fv = views["front"]
F0, FY0, F1, FY1 = FRONT_WIN


def widths(rows, x0, x1):
    out = []
    for y in rows:
        a_ = left_sil(y, x0, x1)
        b_ = right_sil(y, x0, x1)
        if a_ is not None and b_ is not None:
            out.append((y, a_, b_, b_ - a_))
    return np.array(out)


wb_rows = widths(range(792, 809), F0, F1)
W_BODY_PX = float(np.median(wb_rows[:, 3]))
wf_rows = widths(range(818, 859), F0, F1)
W_FLARE_PX = float(np.median(wf_rows[:, 3]))
x_cf = float(np.median(0.5 * (wb_rows[:, 1] + wb_rows[:, 2])))
hp("W_BODY", VX("front", W_BODY_PX), "m", "sheet pixels", "measured",
   f"front view, object width over rows 792-808 (below the mirrors, above the flares and lamps): median {W_BODY_PX:.1f} px "
   f"(x {np.median(wb_rows[:, 1]):.1f}-{np.median(wb_rows[:, 2]):.1f}); front-view scale")
hp("W_FLARE", VX("front", W_FLARE_PX), "m", "sheet pixels", "measured",
   f"front view, object width over rows 818-858 (flares; mirrors above, bumper below): median {W_FLARE_PX:.1f} px "
   f"(x {np.median(wf_rows[:, 1]):.1f}-{np.median(wf_rows[:, 2]):.1f})",
   real={"value": 1.900, "status": "verified", "source": "toyota-global id60013935: width 1900 mm (HZJ81V 1830); Fable's note said 1.93"})
draw("span", "dims", x=[np.median(wb_rows[:, 1]), np.median(wb_rows[:, 2])], y=800, label="W_BODY")
draw("span", "bs", x=[np.median(wf_rows[:, 1]), np.median(wf_rows[:, 2])], y=840, label="W_FLARE")

# tumblehome: greenhouse silhouette above the mirrors
def tumble(win, rows):
    x0, _, x1, _ = win
    pts = widths(rows, x0, x1)
    la_, lb_, lrms_, ln__, _ = robust_line(pts[:, 0], pts[:, 1])
    ra_, rb_, rrms_, rn_, _ = robust_line(pts[:, 0], pts[:, 2])
    ang_l = math.degrees(math.atan(lb_))   # left edge moves outward (smaller x) going down -> negative b
    ang_r = math.degrees(math.atan(rb_))
    return (la_, lb_, lrms_), (ra_, rb_, rrms_), 0.5 * (-ang_l + ang_r), (ang_l, ang_r)


ftop = int(fv["y_roof"] + 14)
fl_, fr_, TUMB_F, angs_f = tumble(FRONT_WIN, range(ftop, 751))
rv = views["rear"]
rtop = int(rv["y_roof"] + 14)
rl_, rr_, TUMB_R, angs_r = tumble(REAR_WIN, range(rtop, 751))
hp("TUMBLEHOME", 0.5 * (TUMB_F + TUMB_R), "deg", "sheet pixels", "measured",
   f"greenhouse silhouette above the mirrors, front view rows {ftop}-750: left x = {fl_[0]:.1f} + {fl_[1]:.4f} y (rms {fl_[2]:.2f}), "
   f"right x = {fr_[0]:.1f} + {fr_[1]:.4f} y (rms {fr_[2]:.2f}) -> {TUMB_F:.1f} deg; rear view rows {rtop}-750 -> {TUMB_R:.1f} deg",
   front_deg=rnd(TUMB_F, 1), rear_deg=rnd(TUMB_R, 1))
for (a_, b_, _), y0, y1 in ((fl_, fv["y_roof"], 790), (fr_, fv["y_roof"], 790), (rl_, rv["y_roof"], 790), (rr_, rv["y_roof"], 790)):
    draw("line", "gh", p=[a_ + b_ * y0, y0], q=[a_ + b_ * y1, y1], label=None)

# roof width between the rail rounds: the tumblehome lines meet the roof top row (sharp corners)
W_ROOF_PX = (fr_[0] + fr_[1] * fv["y_roof"]) - (fl_[0] + fl_[1] * fv["y_roof"])
hp("W_ROOF", VX("front", W_ROOF_PX), "m", "sheet pixels", "derived",
   f"front view: the two greenhouse side lines at the roof top row y {fv['y_roof']:.1f} are {W_ROOF_PX:.1f} px apart "
   f"(sharp-corner width, rail rounds excluded)")
draw("span", "gh", x=[fl_[0] + fl_[1] * fv["y_roof"], fr_[0] + fr_[1] * fv["y_roof"]], y=fv["y_roof"] - 6, label="W_ROOF")

# tyres in the front and rear views: track and width
def tyre_runs(view):
    x0, _, x1, _ = views[view]["win"]
    g = views[view]["ground"]
    out = []
    for y in range(int(g - 0.12 * views[view]["s"]), int(g - 0.05 * views[view]["s"])):
        d = np.where(DARK[y, x0:x1])[0] + x0
        runs = np.split(d, np.where(np.diff(d) > 2)[0] + 1)
        runs = [r_ for r_ in runs if len(r_) >= 25]
        if len(runs) >= 2:
            out.append((y, runs[0][0] - 0.5, runs[0][-1] + 0.5, runs[-1][0] - 0.5, runs[-1][-1] + 0.5))
    return np.array(out)


tf = tyre_runs("front")
trr = tyre_runs("rear")
trk_f = float(np.median(0.5 * (tf[:, 3] + tf[:, 4]) - 0.5 * (tf[:, 1] + tf[:, 2])))
trk_r = float(np.median(0.5 * (trr[:, 3] + trr[:, 4]) - 0.5 * (trr[:, 1] + trr[:, 2])))
tw_f = float(np.median(np.r_[tf[:, 2] - tf[:, 1], tf[:, 4] - tf[:, 3]]))
tw_r = float(np.median(np.r_[trr[:, 2] - trr[:, 1], trr[:, 4] - trr[:, 3]]))
hp("TRACK_F", VX("front", trk_f), "m", "sheet pixels", "measured",
   f"front view: tyre-centre distance over rows {int(tf[0, 0])}-{int(tf[-1, 0])} (5-12 cm above the ground, tyre runs of dark pixels): "
   f"median {trk_f:.1f} px", real={"value": 1.595, "status": "unverified", "source": "Fable's recollection; not on the Toyota pages"})
hp("TRACK_R", VX("rear", trk_r), "m", "sheet pixels", "measured",
   f"rear view: same rule, rows {int(trr[0, 0])}-{int(trr[-1, 0])}: median {trk_r:.1f} px",
   real={"value": 1.615, "status": "unverified", "source": "Fable's recollection; not on the Toyota pages"})
hp("TYRE_W", VX("front", tw_f), "m", "sheet pixels", "measured",
   f"front view tyre run width median {tw_f:.1f} px (rear view {VX('rear', tw_r):.3f} m, {tw_r:.1f} px); includes the sidewall bulge",
   real={"value": 0.275, "status": "unverified", "source": "275/70R16 (Fable's recollection)"}, rear_m=rnd(VX("rear", tw_r)))
for t, view in ((tf, "front"), (trr, "rear")):
    ym = float(np.median(t[:, 0]))
    draw("span", "reg", x=[np.median(0.5 * (t[:, 1] + t[:, 2])), np.median(0.5 * (t[:, 3] + t[:, 4]))], y=ym, label=f"track {view}")
    for c in (1, 3):
        draw("vline", "reg", x=float(np.median(0.5 * (t[:, c] + t[:, c + 1]))), y=[ym - 20, views[view]["ground"]], label=None)

# ground clearance: lowest underbody point between the front tyres (front view)
gcs = []
lo_x = int(np.median(tf[:, 2])) + 6
hi_x = int(np.median(tf[:, 3])) - 6
for x in range(lo_x, hi_x):
    if abs(x - x_cf) < 4:
        continue
    # the dark mass hanging from the body: start at the bumper bottom region and follow it down across gaps of <= 3 px
    c = L[850:int(fv["ground"]) + 1, x] < 100
    y = next((i for i in range(0, 40) if c[i]), None)
    if y is None:
        continue
    while y < len(c) - 1 and (c[y + 1] or c[y + 2:y + 5].any()):
        y += 1
    if 850 + y < fv["ground"] - 6:
        gcs.append((x, 850 + y + 0.5))
gcs = np.array(gcs)
i_gc = int(np.argmax(gcs[:, 1]))
hp("GROUND_CLEAR", VZ("front", gcs[i_gc, 1]), "m", "sheet pixels", "measured",
   f"front view: lowest dark underbody pixel between the front tyres (x {lo_x}-{hi_x}) at ({gcs[i_gc, 0]:.0f}, {gcs[i_gc, 1]:.1f}) px; "
   f"side view lowest underbody between the wheels (running board / tank) {GC_SIDE:.3f} m at ({ub[i_ub, 0]:.0f}, {ub[i_ub, 1]:.1f})",
   real={"value": 0.220, "status": "unverified", "source": "Fable's recollection; not on the Toyota pages"},
   side_underbody_m=rnd(GC_SIDE))
draw("hline", "dims", y=gcs[i_gc, 1], x=[lo_x, hi_x], label="GROUND_CLEAR")

# headlamp (front view): housing with the side marker and two round lenses, left side
hl_top, hl_bot = [], []
for x in range(318, 376):
    c = IVORY[790:870, x]
    ys = np.where(~c[10:])[0]
    if not len(ys):
        continue
    t_ = 800 + ys[0]
    rest = np.where(c[t_ - 790 + 5:])[0]
    if len(rest):
        hl_top.append(t_ - 0.5)
        hl_bot.append(t_ + 5 + rest[0] - 0.5)
y_hl_t, y_hl_b = float(np.median(hl_top)), float(np.median(hl_bot))
# left edge: last ivory column before the housing at mid-height; right edge: the light seam between housing and grille
ym_hl = int(round(0.5 * (y_hl_t + y_hl_b)))
rowI = np.where(IVORY[ym_hl, 290:330])[0]
x_hl_l = 290 + rowI.max() + 0.5 if len(rowI) else None
seam = {x: float(np.mean(L[int(y_hl_t) + 3:int(y_hl_b) - 2, x])) for x in range(370, 396)}
x_dip = next(x for x in range(370, 395) if seam[x] < 50)
x_hl_r = next(x for x in range(x_dip, 395) if seam[x] > 55) - 0.5
x_marker = max(x for y in range(int(y_hl_t), int(y_hl_b)) for x in range(int(x_hl_l), int(x_hl_l) + 30) if ORANGE[y, x]) + 0.5
HL_W = (x_hl_r - x_hl_l) / fv["s"]
HL_H = (y_hl_b - y_hl_t) / fv["s"]
H_LAMP_F = VZ("front", 0.5 * (y_hl_t + y_hl_b))
hp("H_LAMP", H_LAMP_F, "m", "sheet pixels", "measured",
   f"front view headlamp housing rows {y_hl_t:.1f}-{y_hl_b:.1f} px (first non-body-colour row under the bonnet front and "
   f"first body-colour row under the housing, median over columns 318-375) -> centre, front-view scale")
draw("box", "fr", x=[x_hl_l, x_hl_r], y=[y_hl_t, y_hl_b], label="headlamp")
draw("box", "fr", x=[2 * x_cf - x_hl_r, 2 * x_cf - x_hl_l], y=[y_hl_t, y_hl_b], label=None)

# bonnet crown (front view): top edge of the bonnet ivory against the cowl / wipers
bon = []
for x in range(352, 568):
    if abs(x - x_cf) < 4:
        continue
    for y in range(760, 800):
        if IVORY[y:y + 3, x].all() and not IVORY[y - 1, x]:
            bon.append((x, y - 0.5))
            break
bon = np.array(bon)
cq = np.polyfit(bon[:, 0] - x_cf, bon[:, 1], 2)
half = 0.5 * (bon[:, 0].max() - bon[:, 0].min())
crown_px = cq[0] * half ** 2
CROWN = VX("front", crown_px)
draw("poly", "fr", pts=[[float(x), float(np.polyval(cq, x - x_cf))] for x in np.linspace(bon[:, 0].min(), bon[:, 0].max(), 30)],
     label="bonnet top (front)")

# rear view: tailgate split, rear screen
rcx = float(np.median([0.5 * (a_ + b_) for _, a_, b_, _ in widths(range(790, 860), REAR_WIN[0], REAR_WIN[2])]))
split = []
for x in range(int(rcx) - 100, int(rcx) + 100):
    if abs(x - rcx) < 30:
        continue  # emblem, wiper, plate
    c = L[800:830, x]
    j = int(np.argmin(c))
    if c[j] < 185 and IVORY[800 + j - 3, x] and IVORY[800 + j + 3, x]:
        split.append((x, 800 + j))
split = np.array(split)
y_split = float(np.median(split[:, 1]))
rs_top, rs_bot = [], []
for x in range(int(rcx) - 90, int(rcx) + 90):
    if abs(x - rcx) < 4:
        continue
    y0_ = int(rv["y_roof"]) + 2
    c = IVORY[y0_:830, x]
    t_ = next((i for i in range(len(c) - 5) if not c[i:i + 5].any()), None)  # first 5-row run without body colour
    if t_ is None:
        continue
    b_ = next((i for i in range(t_ + 5, len(c) - 4) if c[i:i + 4].all()), None)  # first 4-row body-colour run after it
    if b_ is not None:
        rs_top.append(y0_ + t_ - 0.5)
        rs_bot.append(y0_ + b_ - 0.5)
y_rs_t, y_rs_b = float(np.median(rs_top)), float(np.median(rs_bot))
Z_RS_BASE = VZ("rear", y_rs_b)
y_side_rsb = GROUND - Z_RS_BASE * S
x_side_rsb = TAIL_UP[1] + TAIL_UP[2] * y_side_rsb
hp("Y_RS_BASE", Ym(x_side_rsb), "m", "sheet pixels", "derived",
   f"rear view: rear screen (glass with its black frame) rows {y_rs_t:.1f}-{y_rs_b:.1f} px at the centre +-90 px -> base Z "
   f"{Z_RS_BASE:.3f} m; side view upper tail line at that height x {x_side_rsb:.1f} px", z_m=rnd(Z_RS_BASE))
draw("hline", "lay", y=y_split, x=[rcx - 130, rcx + 130], label="tailgate split")
draw("hline", "gh", y=y_rs_b, x=[rcx - 110, rcx + 110], label="rear screen base")
draw("cross", "gh", c=[x_side_rsb, y_side_rsb], label="Y_RS_BASE")

# top view cross-check of widths (inconsistent with the front view; reported only)
tw = []
for x in range(650, 880):
    t_ = top_sil(x, TOP_WIN[1], TOP_WIN[3])
    b_ = bottom_sil(x, TOP_WIN[1], TOP_WIN[3])
    if t_ is not None and b_ is not None:
        tw.append(b_ - t_)
roofw = []
for x in range(720, 1100):
    if abs(x - 763) < 4:
        continue
    gl = np.where(GLASS[380:470, x])[0]
    gl2 = np.where(GLASS[560:670, x])[0]
    if len(gl) and len(gl2):
        roofw.append((560 + gl2.min() - 0.5) - (380 + gl.max() + 0.5))
RES["views"]["top"]["body_width_doors_m"] = rnd(np.median(tw) / s_top)
xm_top = 765
draw("span", "dims", x=[top_sil(xm_top, TOP_WIN[1], TOP_WIN[3]), bottom_sil(xm_top, TOP_WIN[1], TOP_WIN[3])], y=None, xv=xm_top,
     label="top view body width %.3f m (not used)" % (np.median(tw) / s_top))
RES["views"]["top"]["roof_panel_width_m"] = rnd(np.median(roofw) / s_top) if roofw else None
RES["views"]["top"]["note"] = ("widths in the top view are %.0f %% narrower than in the front view at the same scale "
                               "(W/L = %.3f against the front view's W/H x side H/L = %.3f): the top view is not used for widths"
                               % (100 * (1 - (np.median(tw) / s_top) / VX("front", W_BODY_PX)), np.median(tw) / (xt1 - xt0),
                                  VX("front", W_BODY_PX) / LENGTH_M))

# ------------------------------------------------------------------ rule rows measured
def rule(rid, default, measured, unit, evidence, status="measured"):
    RES["rules"][rid] = {"default": default, "measured": measured, "unit": unit, "evidence": evidence, "status": status}


rule("GH-02", "RAKE_WS 32 (28 to 38)", rnd(RAKE_WS, 1), "deg", "= RAKE_WS (side silhouette of the windscreen)")
rule("GH-07", "6 (4 to 9)", rnd(0.5 * (TUMB_F + TUMB_R), 1), "deg",
     f"= TUMBLEHOME; front view {TUMB_F:.1f}, rear view {TUMB_R:.1f}; left/right front {-angs_f[0]:.1f}/{angs_f[1]:.1f}")
rule("GH-09", "B 0.090, C 0.110, D 0.150", {k: rnd((p1 - p0) / S) for k, (p0, p1) in pill.items()}, "m",
     "visible pillar between glass areas (body colour plus black frames), side view; D = last glass to the tail silhouette")
rule("GH-10", "straight horizontal at H_BELT", {"H_BELT": rnd(H_BELT), "rise_to_rear_m": rnd(-btb * (1125 - 600) / S),
                                                 "over_m": rnd((1125 - 600) / S), "rms_m": rnd(btrms / S, 4)}, "m",
     f"belt line fit over x 600-1125 px: slope {btb:.5f} px/px (negative = rises to the rear)")
for t in arch:
    pass
rule("BS-05", "margin 0.080, flat 0.35 x dia",
     {"ARCH_R": rnd(ARCH_R), "margin": rnd(ARCH_R - TYRE_R_PX / S), "flat_m": rnd(ARCH_FLAT),
      "flat_over_arch_dia": rnd(ARCH_FLAT / (2 * ARCH_R), 2),
      "radius_side_vs_top_m": {t: [rnd(arch[t]["r_side_px"] / S), rnd(arch[t]["r_top_px"] / S)] for t in arch}}, "m",
     "margin = ARCH_R - TYRE_R; flat as ARCH_TOP_FLAT; a squared top would show a smaller radius at the top than at the sides")
rule("BS-06", "0.070 out, 0.060 tall; cladding 0.120 tall",
     {"flare_out": rnd(VX("front", 0.5 * (W_FLARE_PX - W_BODY_PX))),
      "flare_band_side": rnd(np.mean([arch[t]["band_px"] for t in arch]) / S),
      "cladding_tall": rnd((y_sill - y_clad) / S)}, "m",
     f"out = (W_FLARE - W_BODY) / 2 in the front view; flare band = radial width of the flare seen from the side (opening edge to "
     f"the body-colour edge, median front {arch['front']['band_px']:.1f} / rear {arch['rear']['band_px']:.1f} px); cladding = dark band "
     f"from y {y_clad:.1f} to the sill {y_sill:.1f} px at the doors (includes the darker rocker strip)")
rule("FR-01", "5 (0 to 10)", rnd(RAKE_FRONT, 1), "deg", "= RAKE_FRONT, positive = top rearward (leans back)")
rule("FR-02", "crown 0.025; fall 0.040",
     {"crown": rnd(CROWN), "fall": rnd((BONNET[1] + BONNET[2] * lead[0] - (BONNET[1] + BONNET[2] * cowl[0])) / S)}, "m",
     f"crown = sag of a parabola through the bonnet top edge in the front view over x {bon[:, 0].min():.0f}-{bon[:, 0].max():.0f} "
     f"(half width {half:.0f} px, {crown_px:.1f} px); fall = bonnet top line height at the cowl minus at the leading edge, side view")
rule("FR-04", "0.180 tall, 0.100 out, wraps 0.250",
     {"tall": rnd((yb_b - yb_t) / S), "out": rnd((face_at_bumper - x_front) / S), "side_length": rnd((x_wrap - x_front) / S),
      "rear_tall": rnd((yr_b - yr_t) / S), "rear_side_length": None}, "m",
     f"side view: bar rows {yb_t:.1f}-{yb_b:.1f}; out = front face line at the bar top (x {face_at_bumper:.1f}) minus the bar face "
     f"(x {x_front:.1f}); side length = bar face to the black wheel-well gap at mid-height (x {x_wrap:.1f}); rear bar side length not separable: the bar runs into the dark flare at the same luminance")
rule("FR-05", "0.200 x 0.120", {"housing_w": rnd(HL_W), "housing_h": rnd(HL_H), "lamps_only_w": rnd((x_hl_r - x_marker) / fv["s"]),
                                 "H_LAMP": rnd(H_LAMP_F),
                                 "centre_x_from_cl": rnd(VX("front", x_cf - 0.5 * (x_hl_l + x_hl_r)))}, "m",
     f"front view left housing (side marker + two round lenses in one dark frame) x {x_hl_l:.1f}-{x_hl_r:.1f}, y {y_hl_t:.1f}-{y_hl_b:.1f} px; "
     f"lamps only = marker's inner edge x {x_marker:.1f} to the frame's outer edge")
rule("RR-01", "3 (0 to 6)", rnd(RAKE_REAR, 1), "deg", "= RAKE_REAR, positive = top forward")
y_front_axle = Ym(xf)
rule("LAY-02", "0.48", rnd((RES["hardpoints"]["Y_B"]["value"] - y_front_axle) / WB_M, 3), "fraction of WB",
     "(Y_B - front axle Y) / WB")
td = shut.get("rear door trailing edge")
if td:
    x_td = td["a"] + td["b"] * 170
    fr_out = arch["rear"]["out"]
    x_flare_front = fr_out[:, 0].min()
    x_open_front = arch["rear"]["centre"][0] - arch["rear"]["r_side_px"]
    rule("LAY-03", "0.060 ahead of the rear arch",
         {"to_flare_outer_edge": rnd((x_flare_front - x_td) / S), "to_opening_front": rnd((x_open_front - x_td) / S),
          "trailing_edge_rake_deg": rnd(math.degrees(math.atan(td["b"])), 1)}, "m",
         f"rear door trailing edge line x = {td['a']:.1f} + {td['b']:.4f} y (rows {td['y'][0]}-{td['y'][1]}, rms {td['rms']:.2f}); "
         f"flare outer edge's front-most point x {x_flare_front:.1f}; opening front (hub - side radius) x {x_open_front:.1f}; "
         f"negative = the edge is behind that point (the door is cut round the arch)")
rule("LAY-06", "split at H_BELT", {"split_z": rnd(VZ("rear", y_split)), "H_BELT": rnd(H_BELT),
                                   "difference": rnd(VZ("rear", y_split) - H_BELT)}, "m",
     f"rear view: thin horizontal line across the tailgate below the rear screen at median y {y_split:.1f} px "
     f"({len(split)} columns); rear screen frame bottom y {y_rs_b:.1f} ({Z_RS_BASE:.3f} m)")
# extras (rows not marked "measure" but measured on the way)
RES["extras"]["GH-03 A-pillar width seen from the side"] = {"default": 0.090, "measured": rnd(A_PILLAR_W),
                                                            "evidence": "rows 50-99: windscreen silhouette edge to the door glass front edge, median"}
RES["extras"]["GH-08 rear screen rake"] = {"default": "8 (3 to 15)", "measured": rnd(RAKE_RS, 1), "evidence": "= RAKE_RS"}
fd = shut.get("front door leading edge")
if fd:
    RES["extras"]["LAY-01 front door leading edge rake"] = {"default": 5, "measured": rnd(math.degrees(math.atan(-fd["b"])), 1),
                                                           "evidence": f"x = {fd['a']:.1f} + {fd['b']:.4f} y over rows {fd['y'][0]}-{fd['y'][1]}; positive = top rearward"}
RES["extras"]["FR-03 bonnet leading edge round"] = {"default": 0.035, "measured": rnd(r_lead),
                                                    "evidence": f"gap {gap} px from the sharp corner to the silhouette along the bisector"}
RES["extras"]["mirror span front view"] = rnd(VX("front", float(np.median(widths(range(758, 784), F0, F1)[:, 3]))))
RES["extras"]["shut_lines"] = {k: {kk: (rnd(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in shut.items()}
RES["real_car"]["height"] = {"sheet_m": rnd(H_ROOF_M), "real_m": 1.900, "status": "verified", "difference_m": rnd(H_ROOF_M - 1.900)}
RES["real_car"]["width"] = {"sheet_m": rnd(VX("front", W_FLARE_PX)), "real_m": 1.900, "status": "verified",
                            "difference_m": rnd(VX("front", W_FLARE_PX) - 1.900)}
RES["real_car"]["wheelbase"] = {"sheet_m": WB_M, "real_m": 2.850, "status": "verified (registration)"}

os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "measurements.json"), "w", encoding="utf-8") as f:
    json.dump(RES, f, indent=1)

# console summary
print(f"side: hubs ({xf:.2f},{yf:.2f}) ({xr:.2f},{yr:.2f}) WB {WB_PX:.2f} px  s {S:.3f} px/m  ground {GROUND:.2f}  roof y {Y_ROOF_PX}")
for v in ("front", "rear", "top"):
    print(v, RES["views"][v])
for k, v in RES["hardpoints"].items():
    print(f"  {k:12s} {v['value']} {v['unit']}")
for k, v in RES["rules"].items():
    print(f"  {k:7s} default {v['default']}  measured {v['measured']}")
for k, v in RES["extras"].items():
    print(f"  extra {k}: {v}")
print(RES["real_car"])
