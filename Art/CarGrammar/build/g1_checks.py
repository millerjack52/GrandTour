"""G1 6g and checks: rule compliance re-measured on the built mesh, side outline against the approved sheet at the
G0 registration (body only), fold detector. Imports g1_shell (which builds the shell) and writes g1-report.json
and debug/outline.png. System Python (numpy, PIL)."""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g1_shell as B  # noqa: E402

S = B.S
OUT = B.OUT
G0 = json.load(open(os.path.join(B.ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g0-v01", "measurements.json"),
                    encoding="utf-8"))
REG = G0["views"]["side"]
S_SIDE, X_MID, GROUND = REG["px_per_m"], REG["x_mid_px"], REG["ground_y_px"]

rows = []


def row(item, source, spec, meas, unit, note=""):
    diff = None if (spec is None or meas is None) else meas - spec
    tol = B.PASS_DEG if unit == "deg" else B.PASS_M
    ok = None if diff is None else abs(diff) <= tol + 1e-12
    rows.append({"item": item, "source": source, "spec": spec, "measured": meas, "diff": diff, "unit": unit, "pass": ok, "note": note})


def plane_fit(P):
    c = P.mean(0)
    u, s, vt = np.linalg.svd(P - c)
    return c, vt[2]


def circle_fit(P):
    x, y = P[:, 0], P[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    c = np.linalg.lstsq(A, x * x + y * y, rcond=None)[0]
    return c[0], c[1], math.sqrt(c[2] + c[0] ** 2 + c[1] ** 2)


gL, gG = B.grid_L, B.grid_G
NW_L, NW_G, NA = B.N_WALL_L, B.N_WALL_G, B.N_ARC
iTL = NW_L + NA - 1  # L row of the round's top tangent
iTG = NW_G + NA - 1

# roof height
roofc = B.vG[np.abs(B.vG[:, 0]) < 0.02]
row("roof height", "H_ROOF", B.H_ROOF, float(roofc[:, 2].max()), "m")
# belt height at the doors (G0 quoted H_BELT at mid-doors, sheet x 860 px)
y_mid_doors = B.BELT_Y0
side_idx = [i for i, st in enumerate(B.L_ST) if st[0] == 2]
i_md = min(side_idx, key=lambda i: abs(gL[i, iTL, 1] - y_mid_doors))
i_ab = min(side_idx, key=lambda i: abs(gL[i, iTL, 1] - B.Y_AB))
row("belt height at mid-doors (ledge at the round's top tangent)", "H_BELT", B.H_BELT, float(gL[i_md, iTL, 2]), "m",
    f"Y {gL[i_md, iTL, 1]:.3f}; ledge anchored at BELT_ANCHOR_Y {B.BELT_Y0} (plan 7), rising {B.BELT_RISE} over {B.BELT_OVER}")


# A-pillar foot: the windscreen's side edge meets the belt (virtual sharp corner with the side wall)
zf = B.H_BELT
for _ in range(50):
    zf = float(B.ledge(float(B.G_YF(zf))))
row("A-pillar foot Y at the belt (windscreen side edge on the ledge)", "Y_A_BASE", B.Y_AB, float(B.G_YF(zf)), "m",
    f"at Z {zf:.4f} (the ledge there; G0 quoted Y_A_BASE at Z {B.H_BELT})")
row("roof front corner Y (windscreen side edge at the roof round tangent)", "Y_ROOF_F + GH-01 top (sheet A-pillar at the roof row)",
    B.Y_RF + B.BOW_TOP, float(B.G_YF(B.Z_B1)), "m", f"at Z {B.Z_B1:.4f}")
row("ledge flat width at mid-doors (round tangent to glass base)", "BS-02 ledge", B.LEDGE,
    float(gL[i_md, iTL, 0] - B.GO.point([st for st in B.G_ST if st[0] == 2][0], B.H_BELT)[0, 0]), "m",
    "round top tangent x minus G base half width")
# cowl point: G base at the centre line
p_c = B.GO.point(B.G_ST[0], B.zb[0])[0]
row("cowl point Y (G base on the centre line)", "Y_COWL", B.Y_COWL, float(p_c[1]), "m")
row("cowl point Z", "H_COWL", B.H_COWL, float(B.zb[0]), "m")
# bonnet edge: centre-line profile of L, face line and bonnet line meeting
prof = gL[0]
face = prof[(prof[:, 2] > B.H_BT) & (prof[:, 2] < B.H_BF - 0.15)]
cl = B.vL[np.abs(B.vL[:, 0]) < 1e-6]  # centre-line vertices (bonnet rows end on the centre line)
bon = cl[(cl[:, 1] > B.BE_Y + 0.15) & (cl[:, 1] < B.BE_Y + 0.60) & (cl[:, 2] > B.H_BF - 0.1)]
fa, fb = np.polyfit(face[:, 2], face[:, 1], 1)  # y = fa z + fb
ba, bb = np.polyfit(bon[:, 1], bon[:, 2], 1)    # z = ba y + bb
zc = (ba * fb + bb) / (1 - ba * fa)
yc = fa * zc + fb
row("bonnet edge Y (centre line, sharp-corner point)", "construction BONNET_EDGE_Y", B.BE_Y, float(yc), "m")
row("bonnet edge Z (centre line)", "H_BONNET_F", B.H_BF, float(zc), "m", f"6a puts the centre {B.CROWN_B} above the side edge (FR-02 crown)")
# overhangs
row("front overhang (bumper face)", "OH_F", B.OH_F, float(-B.BF_V[:, 1].min() - B.WB / 2), "m")
row("rear overhang (bumper face)", "OH_R", B.OH_R, float(B.BR_V[:, 1].max() - B.WB / 2), "m")
fz = gL[0, :NW_L]
fz = fz[(fz[:, 2] > B.H_BT) & (fz[:, 2] < B.L_RD[0][1]["zw_t"] - 0.005)]
fa2, fb2 = np.polyfit(fz[:, 2], fz[:, 1], 1)
row("lower body front face Y at the bonnet edge height (face line extended)", "BONNET_EDGE_Y", B.BE_Y, float(fa2 * B.H_BF + fb2), "m",
    f"face lean {math.degrees(math.atan(fa2)):+.2f} deg (FR-01 / RAKE_FRONT {B.RAKE_FRONT})")


# glass planes
def glass_pts(seg_set):
    P = []
    for fi, (i, r) in enumerate(B.fmapG):
        if B.gglass[fi] and B.G_ST[i][0] in seg_set and B.G_ST[i + 1][0] in seg_set:
            P.append(gG[i:i + 2, r:r + 2].reshape(-1, 3))
    return np.vstack(P)


c, n = plane_fit(glass_pts({0}))
n = n if n[1] < 0 else -n
row("windscreen rake (plane fit to the windscreen glass)", "RAKE_WS / GH-02", B.RAKE_WS, math.degrees(math.atan2(n[2], -n[1])), "deg",
    f"the plane averages a bow that shrinks from {B.BOW_BASE} to {B.BOW_TOP} up the glass")
wc = glass_pts({0})
wc = wc[np.abs(wc[:, 0]) < 0.03]
ka, kb = np.polyfit(wc[:, 2], wc[:, 1], 1)
row("windscreen rake (centre line of the glass)", "RAKE_WS / GH-02", B.RAKE_WS, math.degrees(math.atan(ka)), "deg",
    "line fit to glass vertices within 3 cm of the centre line")
c, n = plane_fit(glass_pts({4}))
n = n if n[1] > 0 else -n
row("rear screen rake (plane fit to the rear screen glass)", "RAKE_RS / GH-08", B.RAKE_RS, math.degrees(math.atan2(n[2], n[1])), "deg")
c, n = plane_fit(glass_pts({2}))
n = n if n[0] > 0 else -n
tumb = math.degrees(math.atan2(n[2], n[0]))
row("tumblehome (plane fit to the side glass) against the sheet", "TUMBLEHOME / GH-07", B.TUMB_SHEET, tumb, "deg")
row("tumblehome against the derived design value", "derived from W_ROOF (6b)", B.TUMB_DERIVED, tumb, "deg")


# round radii in their station planes
def arc_radius(grid, i, r0, stn):
    P = grid[i, r0:r0 + NA + 1]
    rho = (P[:, 0] - stn.O[0]) * stn.n[0] + (P[:, 1] - stn.O[1]) * stn.n[1]
    return circle_fit(np.c_[rho, P[:, 2]])[2]


def med_r(grid, sts, rds, seg, r0):
    v = [arc_radius(grid, i, r0, rds[i][0]) for i, st in enumerate(sts) if st[0] == seg]
    return float(np.median(v)), float(np.min(v)), float(np.max(v))


m = med_r(gG, B.G_ST, B.G_RD, 2, NW_G - 1)
row("rail round radius (side stations, median)", "GH-05", B.R_RAIL, m[0], "m", f"min {m[1]:.4f} max {m[2]:.4f}")
m = med_r(gG, B.G_ST, B.G_RD, 0, NW_G - 1)
row("roof front round radius", "GH-06", B.R_HEAD_F, m[0], "m", f"min {m[1]:.4f} max {m[2]:.4f}")
m = med_r(gG, B.G_ST, B.G_RD, 4, NW_G - 1)
row("roof rear round radius", "GH-06", B.R_HEAD_R, m[0], "m", f"min {m[1]:.4f} max {m[2]:.4f}")
m = med_r(gL, B.L_ST, B.L_RD, 2, NW_L - 1)
row("lower body belt round radius (sides)", "BS-02 car value", B.R_BELT, m[0], "m", f"min {m[1]:.4f} max {m[2]:.4f}")
m = med_r(gL, B.L_ST, B.L_RD, 0, NW_L - 1)
row("bonnet leading edge round radius", "FR-03 car value (dial)", B.R_NOSE, m[0], "m", f"min {m[1]:.4f} max {m[2]:.4f}")
# arch: lower boundary of L on the arch stations
for tag, yh in (("front", B.Y_HF), ("rear", B.Y_HR)):
    P = np.array([gL[i, 0] for i in side_idx if abs(gL[i, 0, 1] - yh) < B.ARCH_R - 0.01
                  and abs(gL[i, 0, 1] - yh) > B.ARCH_FLAT / 2 + 0.005 and gL[i, 0, 2] > B.H_SILL + 0.01])
    cy, cz, r = circle_fit(P[:, 1:3])
    row(f"arch radius {tag} (circle fit to the opening edge off the flat)", "ARCH_R", B.ARCH_R, r, "m",
        f"centre Y {cy:.4f} Z {cz:.4f} (hub {yh:.3f}, {B.HUB_Z:.3f}); {len(P)} edge vertices")
    top = np.array([gL[i, 0] for i in side_idx if abs(gL[i, 0, 1] - yh) <= B.ARCH_FLAT / 2 + 1e-6])
    flat = float(top[:, 1].max() - top[:, 1].min()) if len(top) > 1 else 0.0
    row(f"arch top flat {tag}", "ARCH_TOP_FLAT", B.ARCH_FLAT, flat, "m", f"z spread on the flat {np.ptp(top[:, 2]) * 1000:.2f} mm")
# bumpers
row("front bumper top", "H_BUMPER_T", B.H_BT, float(B.BF_V[:, 2].max()), "m")
row("front bumper bottom", "H_BUMPER_B", B.H_BB, float(B.BF_V[:, 2].min()), "m")
row("rear bumper top", "H_BUMPER_T rear (G0)", B.z_rb1, float(B.BR_V[:, 2].max()), "m")
row("rear bumper bottom", "H_BUMPER_B rear (G0)", B.z_rb0, float(B.BR_V[:, 2].min()), "m")
# roof width at the rail tangent (station nearest the roof's mid-length)
gs = [i for i, st in enumerate(B.G_ST) if st[0] == 2]
i_rm = min(gs, key=lambda i: abs(gG[i, NW_G - 1, 1] - B.Y_MID_ROOF))
row("roof width at the rail round's wall tangent", "W_ROOF", B.W_ROOF, float(2 * gG[i_rm, NW_G - 1, 0]), "m", f"station Y {gG[i_rm, NW_G - 1, 1]:.3f}")
# pillars: non-glass runs along the side at the middle wall row
r_mid = NW_G // 2
segs = []
for i in gs[:-1]:
    fi = [k for k, (a, b) in enumerate(B.fmapG) if a == i and b == r_mid]
    if fi:
        segs.append((gG[i, r_mid, 1], gG[i + 1, r_mid, 1], bool(B.gglass[fi[0]])))
runs, cur = [], None
for y0, y1, gl in segs:
    if not gl:
        cur = [y0, y1] if cur is None else [cur[0], y1]
    elif cur is not None:
        runs.append(cur)
        cur = None
if cur is not None:
    runs.append(cur)
z_mid = float(np.median(gG[gs, r_mid, 2]))


def run_near(y):
    return min(runs, key=lambda r: abs(0.5 * (r[0] + r[1]) - y))


rb, rc = run_near(B.Y_B), run_near(B.Y_C)
row("B pillar centre (non-glass run, middle wall row)", "Y_B", B.Y_B, 0.5 * (rb[0] + rb[1]), "m", f"width {rb[1] - rb[0]:.4f} (GH-09 {B.PIL_B}); z {z_mid:.3f}")
row("C pillar centre", "Y_C", B.Y_C, 0.5 * (rc[0] + rc[1]), "m", f"width {rc[1] - rc[0]:.4f} (GH-09 {B.PIL_C})")
rd_ = runs[-1]
row("D pillar front edge (glass end)", "Y_D - D/2 (GH-09)", B.Y_D_EDGE, rd_[0], "m")
ra = runs[0]
i_a = min(gs, key=lambda i: abs(gG[i, r_mid, 1] - ra[1]))
z_a = float(gG[i_a, r_mid, 2])
row("A pillar along the side (glass start minus corner end, same height)", "GH-03", B.A_WIDTH,
    float(gG[i_a, r_mid, 1] - B.GO.g(z_a)["cfy"][0]), "m", f"at z {z_a:.3f}")
zr = B.H_ROOF
for _ in range(50):
    yc_ = float(B.G_YF(zr) - B.ws_bow(zr))
    zr = float(B.roof_z(0.0, yc_))
row("roof front edge Y (windscreen centre line meets the roof plate)", "Y_ROOF_F", B.Y_RF, yc_, "m", f"at Z {zr:.4f}")
zr = B.H_ROOF
for _ in range(50):
    yr_ = float(B.G_YR(zr) + B.REAR_BOW)
    zr = float(B.roof_z(0.0, yr_))
row("roof rear edge Y (rear screen centre line meets the roof plate)", "Y_ROOF_R", B.Y_RR, yr_, "m", f"at Z {zr:.4f}")

# ------------------------------------------------------------------ outline against the sheet's side view
sheet = np.asarray(Image.open(os.path.join(B.ROOT, G0["sheet"])).convert("RGB")).astype(float)
Rr, Gg, Bb = sheet[..., 0], sheet[..., 1], sheet[..., 2]
Ll = (Rr + Gg + Bb) / 3


def opening(m):
    p = np.pad(m, 1)
    e = np.ones_like(m)
    for dy in range(3):
        for dx in range(3):
            e &= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    p = np.pad(e, 1)
    d = np.zeros_like(m)
    for dy in range(3):
        for dx in range(3):
            d |= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    return d


SOLID = opening((Ll < 165) | (Rr - Bb > 10))
K = 4
H_IMG, W_IMG = SOLID.shape
mask_img = Image.new("L", (W_IMG * K, 360 * K), 0)
dr = ImageDraw.Draw(mask_img)


def proj(P):
    return np.c_[(X_MID + P[:, 1] * S_SIDE) * K, (GROUND - P[:, 2] * S_SIDE) * K]


for V, Fc in ((B.vL, B.fL), (B.vG, B.fG), (B.BF_V, B.BF_F), (B.BR_V, np.array([list(f) + [-1] * (4 - len(f)) for f in B.BR_F]))):
    Q = proj(np.asarray(V))
    for f in Fc:
        idx = [k for k in f if k >= 0]
        dr.polygon([tuple(Q[k]) for k in idx], fill=255)
shell = np.asarray(mask_img.resize((W_IMG, 360), Image.BOX)) >= 128
x_f = int(math.ceil(X_MID + B.Y_BUMP_F * S_SIDE))
x_r = int(math.floor(X_MID + B.Y_BUMP_R * S_SIDE))
# sheet body outline points: top-most pixel per column (bumper face to bumper face; the title text above the front
# is skipped), left-most per row between the front bumper top and the bonnet edge, right-most per row between the
# rear bumper top and the belt. Shell: its silhouette boundary. Distance = 2D nearest distance (cm).
pts = []
for x in range(x_f + 1, x_r):
    a = np.where(SOLID[:358, x])[0]
    a = a[a >= 40] if x < 380 else a
    if len(a):
        pts.append((x, a[0], "upper"))
for y in range(int(GROUND - (B.H_BF - 0.02) * S_SIDE), int(GROUND - (B.H_BT + 0.01) * S_SIDE)):
    a = np.where(SOLID[y, 230:700])[0]
    if len(a):
        pts.append((230 + a[0], y, "front face"))
for y in range(int(GROUND - (B.H_BELT - 0.02) * S_SIDE), int(GROUND - (B.z_rb1 + 0.01) * S_SIDE)):
    a = np.where(SOLID[y, 900:1300])[0]
    if len(a):
        pts.append((900 + a[-1], y, "tail face"))
sb = shell & ~(np.roll(shell, 1, 0) & np.roll(shell, -1, 0) & np.roll(shell, 1, 1) & np.roll(shell, -1, 1))
by, bx = np.where(sb)
P = np.array([(p[0], p[1]) for p in pts], float)
dmin = np.empty(len(P))
for k0 in range(0, len(P), 200):
    d = np.hypot(P[k0:k0 + 200, 0:1] - bx[None], P[k0:k0 + 200, 1:2] - by[None])
    dmin[k0:k0 + 200] = d.min(1)
dcm = dmin / S_SIDE * 100
lab = np.array([p[2] for p in pts])
outline = {"method": "2D nearest distance from each sheet body-outline pixel to the shell silhouette boundary, sheet side view at "
                     "the G0 registration (%.3f px/m, ground %.2f, mid-wheelbase x %.2f)" % (S_SIDE, GROUND, X_MID),
           "all": {"samples": int(len(dcm)), "mean_cm": float(dcm.mean()), "max_cm": float(dcm.max()),
                   "max_at_px": [int(P[np.argmax(dcm), 0]), int(P[np.argmax(dcm), 1])]},
           "targets": {"mean_cm": 1.5, "max_cm": 4.0}}
for k in ("upper", "front face", "tail face"):
    sel = lab == k
    outline[k] = {"samples": int(sel.sum()), "mean_cm": float(dcm[sel].mean()), "max_cm": float(dcm[sel].max())}
ux = P[:, 0]
parts = {"bonnet (bumper face to cowl)": (x_f, X_MID + B.Y_COWL * S_SIDE), "windscreen (cowl to roof front)": (X_MID + B.Y_COWL * S_SIDE, X_MID + B.Y_RF * S_SIDE),
         "roof": (X_MID + B.Y_RF * S_SIDE, X_MID + B.Y_RR * S_SIDE), "tail (roof rear to bumper face)": (X_MID + B.Y_RR * S_SIDE, x_r)}
outline["upper_parts"] = {}
for k, (a, b) in parts.items():
    sel = (lab == "upper") & (ux >= a) & (ux < b)
    if sel.any():
        outline["upper_parts"][k] = {"mean_cm": float(dcm[sel].mean()), "max_cm": float(dcm[sel].max())}
order = np.argsort(-dcm)[:8]
outline["worst"] = [{"px": [int(P[i, 0]), int(P[i, 1])], "Y": float((P[i, 0] - X_MID) / S_SIDE), "Z": float((GROUND - P[i, 1]) / S_SIDE),
                     "cm": float(dcm[i]), "part": str(lab[i])} for i in order]
# outline debug picture over the sheet crop
crop = Image.fromarray(sheet[:358, 230:1300].astype(np.uint8))
od = ImageDraw.Draw(crop)
edge = shell[:358, 230:1300] & ~(np.roll(shell[:358, 230:1300], 1, 0) & np.roll(shell[:358, 230:1300], -1, 0)
                                  & np.roll(shell[:358, 230:1300], 1, 1) & np.roll(shell[:358, 230:1300], -1, 1))
arr = np.asarray(crop).copy()
arr[edge] = (255, 0, 255)
Image.fromarray(arr).resize((1070 * 2, 358 * 2), Image.NEAREST).save(os.path.join(B.DBG, "outline.png"))
np.save(os.path.join(B.DBG, "shell_side_mask.npy"), shell)


# ------------------------------------------------------------------ folds
def dihedrals(V, Fc, skip):
    V = np.asarray(V)
    nrm, cen, area, hmin = [], [], [], []
    for f in Fc:
        idx = [k for k in f if k >= 0]
        p = V[idx]
        n = np.cross(p[2] - p[0], p[-1] - p[1]) if len(idx) == 4 else np.cross(p[1] - p[0], p[2] - p[0])
        a = np.linalg.norm(n)
        nrm.append(n / a if a > 0 else n)
        area.append(0.5 * a)
        emax = max(np.linalg.norm(p[(k + 1) % len(idx)] - p[k]) for k in range(len(idx)))
        hmin.append(a / emax if emax > 0 else 0.0)
        cen.append(p.mean(0))
    edges = {}
    for fi, f in enumerate(Fc):
        idx = [k for k in f if k >= 0]
        for a, b in zip(idx, idx[1:] + idx[:1]):
            edges.setdefault((min(a, b), max(a, b)), []).append(fi)
    out = []
    for (a, b), fs in edges.items():
        if len(fs) != 2 or skip[a] or skip[b]:
            continue
        f1, f2 = fs
        if area[f1] < 2e-6 or area[f2] < 2e-6 or hmin[f1] < 1e-3 or hmin[f2] < 1e-3:
            continue  # degenerate slivers (thinner than 1 mm) have no meaningful normal
        ang = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(nrm[f1], nrm[f2]))))))
        out.append((ang, *(0.5 * (V[a] + V[b]))))
    return out


def mirrored(V, Fc, flags):
    V = np.asarray(V)
    n = len(V)
    Vm = V * np.array([-1, 1, 1])
    allV = np.vstack([V, Vm])
    key = np.round(allV / 1e-6).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    F2 = [[inv[k] for k in f if k >= 0] for f in Fc] + [[inv[k + n] for k in f if k >= 0][::-1] for f in Fc]
    fl = np.zeros(len(first), bool)
    fl[inv[np.where(np.r_[flags, flags])[0]]] = True
    return allV[first], F2, fl


tuck_z = 0.5 * (B.TUCK_Z1 + B.TUCK_Z2)
tuck_half = 0.5 * (B.TUCK_Z1 - B.TUCK_Z2) + 0.004
# junction band: L vertices within 1 cm (plan) of G's base line, where L's top strip narrows to millimetres
fpl = B.fp[: len(B.fp) // 2]
seg_a, seg_b = fpl[:-1], fpl[1:]


def dist_to_poly(P2):
    ab = seg_b - seg_a
    t = np.clip(((P2[:, None, :] - seg_a[None]) * ab[None]).sum(2) / (ab * ab).sum(1)[None], 0, 1)
    q = seg_a[None] + t[..., None] * ab[None]
    return np.linalg.norm(P2[:, None, :] - q, axis=2).min(1)


near = np.zeros(len(B.vL), bool)
hi = B.vL[:, 2] > B.H_BELT - 0.08
near[hi] = dist_to_poly(np.abs(B.vL[hi, :2])) < 0.01
skipL = B.vfL["lower"] | B.vfL["junction"] | B.vfL["pole"]
skipL_band = skipL | near
VL2, FL2, sL = mirrored(B.vL, B.fL, skipL)
VG2, FG2, sG = mirrored(B.vG, B.fG, B.vfG["base"] | B.vfG["pole"])
dl = dihedrals(VL2, FL2, sL)
dg = dihedrals(VG2, FG2, sG)
allf = sorted([(a, x, y, z, "L") for a, x, y, z in dl] + [(a, x, y, z, "G") for a, x, y, z in dg], reverse=True)
not_tuck = [f for f in allf if not (f[4] == "L" and abs(f[3] - tuck_z) < tuck_half)]
VL3, FL3, sL3 = mirrored(B.vL, B.fL, skipL_band)
dl3 = dihedrals(VL3, FL3, sL3)
band = sorted([(a, x, y, z, "L") for a, x, y, z in dl3 if abs(z - tuck_z) >= tuck_half] + [(a, x, y, z, "G") for a, x, y, z in dg], reverse=True)
folds = {"max_with_1cm_junction_band_and_without_tuck_deg": band[0][0], "at_band": list(map(float, band[0][1:4])),
         "object_band": band[0][4], "over_12_band": int(sum(1 for f in band if f[0] > 12)),
         "max_deg": allf[0][0], "at": list(map(float, allf[0][1:4])), "object": allf[0][4],
         "over_12": int(sum(1 for f in allf if f[0] > 12)),
         "max_excluding_sill_tuck_deg": not_tuck[0][0], "at_excluding_tuck": list(map(float, not_tuck[0][1:4])),
         "object_excluding_tuck": not_tuck[0][4], "over_12_excluding_tuck": int(sum(1 for f in not_tuck if f[0] > 12)),
         "edges_measured": len(allf), "target_deg": 12.0,
         "top": [{"deg": f[0], "at": list(map(float, f[1:4])), "object": f[4]} for f in not_tuck[:12]]}

tk = [f for f in allf if f[4] == "L" and abs(f[3] - tuck_z) < tuck_half]
folds["sill_tuck_crease_max_deg"] = tk[0][0] if tk else None
folds["sill_tuck_crease_edges_over_12"] = int(sum(1 for f in tk if f[0] > 12))


# ------------------------------------------------------------------ cameras matching the sheet's views (for Blender)
def centre_x(rows_, x0, x1):
    c = []
    for y in rows_:
        a = np.where(SOLID[y, x0:x1])[0]
        if len(a):
            c.append(x0 + 0.5 * (a[0] + a[-1]))
    return float(np.median(c))


V = G0["views"]
cams = {}
win = {"side": (230, 0, 1300, 358), "front": (270, 680, 650, 1000), "rear": (870, 680, 1260, 1000), "top": (270, 345, 1240, 705)}
x0, y0, x1, y1 = win["side"]
cams["side"] = {"win": win["side"], "s": S_SIDE, "loc": [8.0, ((x0 + x1) / 2 - X_MID) / S_SIDE, (GROUND - (y0 + y1) / 2) / S_SIDE],
                "dir": [-1, 0, 0]}
xc_f = centre_x(range(792, 809), 270, 650)
x0, y0, x1, y1 = win["front"]
sf, gf = V["front"]["px_per_m"], V["front"]["ground_y_px"]
cams["front"] = {"win": win["front"], "s": sf, "loc": [((x0 + x1) / 2 - xc_f) / sf, -8.0, (gf - (y0 + y1) / 2) / sf], "dir": [0, 1, 0],
                 "centre_px": xc_f}
xc_r = centre_x(range(790, 860), 870, 1260)
x0, y0, x1, y1 = win["rear"]
sr, gr_ = V["rear"]["px_per_m"], V["rear"]["ground_y_px"]
cams["rear"] = {"win": win["rear"], "s": sr, "loc": [-((x0 + x1) / 2 - xc_r) / sr, 8.0, (gr_ - (y0 + y1) / 2) / sr], "dir": [0, -1, 0],
                "centre_px": xc_r}
st_ = V["top"]["px_per_m"]
ytc = []
for x in range(650, 880):
    a = np.where(SOLID[360:690, x])[0]
    if len(a):
        ytc.append(360 + 0.5 * (a[0] + a[-1]))
yc_t = float(np.median(ytc))
x0, y0, x1, y1 = win["top"]
cams["top"] = {"win": win["top"], "s": st_, "loc": [(yc_t - (y0 + y1) / 2) / st_, B.Y_BUMP_F + ((x0 + x1) / 2 - V["top"]["front_x_px"]) / st_, 8.0],
               "dir": [0, 0, -1], "centre_px": yc_t}
for k, c in cams.items():
    x0, y0, x1, y1 = c["win"]
    c["res"] = [2 * (x1 - x0), 2 * (y1 - y0)]
    c["ortho"] = max(x1 - x0, y1 - y0) / c["s"]

report = {"cameras": cams, "compliance": rows, "outline": outline, "folds": folds, "tumblehome": {"derived_deg": B.TUMB_DERIVED, "sheet_deg": B.TUMB_SHEET,
                                                                               "measured_on_mesh_deg": tumb},
          "provenance": B.S.prov}
with open(os.path.join(OUT, "g1-report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=1, default=float)
print(f"{'item':62s} {'spec':>9s} {'meas':>9s} {'diff':>9s}  pass")
for r in rows:
    sp = "-" if r["spec"] is None else f"{r['spec']:.4f}"
    me = "-" if r["measured"] is None else f"{r['measured']:.4f}"
    di = "-" if r["diff"] is None else f"{r['diff']:+.4f}"
    print(f"{r['item'][:62]:62s} {sp:>9s} {me:>9s} {di:>9s}  {r['pass']}")
print("outline", json.dumps({k: v for k, v in outline.items() if k not in ("targets", "worst", "method")}, default=float))
print("folds", {k: v for k, v in folds.items() if k != "top"})
