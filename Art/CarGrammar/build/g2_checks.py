"""G2 9d checks on the built panels (panels.npz): gap widths along every seam, seam positions against the sheet,
window outlines against the sheet's window regions (G0 glass mask), outline and folds as G1, object list with face
counts and open-edge classes. Writes g2-checks.json and debug/window-check.png, debug/outline.png, debug/seams.npz.
System Python (numpy, PIL). Imports g1_shell for the G1 constants only (G1_NO_SAVE: G1's files are not rewritten)."""
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np
from PIL import Image, ImageDraw

os.environ["G1_NO_SAVE"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g1_shell as B  # noqa: E402

ROOT = B.ROOT
OUT = os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g2-v01")
DBG = os.path.join(OUT, "debug")
G1 = os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g1-v02")
G0 = json.load(open(os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g0-v01", "measurements.json"),
                    encoding="utf-8"))
REP1 = json.load(open(os.path.join(G1, "g1-report.json"), encoding="utf-8"))
INFO = json.load(open(os.path.join(OUT, "g2-build.json"), encoding="utf-8"))
SE = INFO["seams"]
GAP, CH = SE["GAP"], SE["CH"]
REG = G0["views"]["side"]
S_SIDE, X_MID, GROUND = REG["px_per_m"], REG["x_mid_px"], REG["ground_y_px"]

Z = np.load(os.path.join(OUT, "panels.npz"))
NAMES = sorted({k.split("__")[0] for k in Z.files})
OBJ = {}
for n in NAMES:
    F = [[int(k) for k in f if k >= 0] for f in Z[n + "__f"]]
    OBJ[n] = (np.asarray(Z[n + "__v"], float), F, np.asarray(Z[n + "__flag"], int))


def base(n):
    return n[:-2] if n.endswith(("_L", "_R")) else n


def edge_faces(F):
    ef = defaultdict(list)
    for fi, f in enumerate(F):
        for a, b in zip(f, f[1:] + f[:1]):
            ef[(min(a, b), max(a, b))].append(fi)
    return ef


EF = {n: edge_faces(o[1]) for n, o in OBJ.items()}


class SegHash:
    """Segments in a voxel hash (cell h) for nearest-segment queries."""

    def __init__(self, h=0.02):
        self.h = h
        self.cells = defaultdict(list)
        self.P0, self.P1, self.tag = [], [], []

    def add(self, p0, p1, tag):
        i = len(self.P0)
        self.P0.append(p0)
        self.P1.append(p1)
        self.tag.append(tag)
        for p in (p0, p1, 0.5 * (p0 + p1)):
            c = tuple(np.floor(p / self.h).astype(int))
            if i not in self.cells[c]:
                self.cells[c].append(i)

    def done(self):
        self.P0 = np.array(self.P0)
        self.P1 = np.array(self.P1)

    def near(self, p):
        c = np.floor(p / self.h).astype(int)
        ids = set()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    ids.update(self.cells.get((c[0] + dx, c[1] + dy, c[2] + dz), ()))
        if not ids:
            return np.zeros(0, int), np.zeros(0), np.zeros((0, 3))
        ids = np.fromiter(ids, int)
        a, b = self.P0[ids], self.P1[ids]
        ab = b - a
        t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-18), 0, 1)
        q = a + t[:, None] * ab
        return ids, np.linalg.norm(q - p, axis=1), q


# ------------------------------------------------------------------ object list, open edges, manifold
open_hash = SegHash(0.01)
open_edges = {}
for n, (V, F, fl) in OBJ.items():
    lst = []
    for (a, b), fs in EF[n].items():
        if len(fs) == 1:
            lst.append((a, b, fs[0]))
            open_hash.add(V[a], V[b], n)
    open_edges[n] = lst
open_hash.done()

objects = {}
for n, (V, F, fl) in OBJ.items():
    nonman = sum(1 for fs in EF[n].values() if len(fs) > 2)
    cls = defaultdict(int)
    other = []
    for a, b, fi in open_edges[n]:
        if n.startswith("Glass"):
            cls["glass pane edge (round end)"] += 1
            continue
        if fl[fi] in (1, 2):
            cls["chamfer/return lip"] += 1
            continue
        m = 0.5 * (V[a] + V[b])
        ids, d, _ = open_hash.near(m)
        ok = [(i, dd) for i, dd in zip(ids, d) if dd < 0.002 and not (np.allclose(open_hash.P0[i], V[a]) and np.allclose(open_hash.P1[i], V[b]))]
        if ok:
            tags = {open_hash.tag[i] for i, _ in ok}
            cls["abuts (same object, belt junction)" if tags == {n} else "abuts another object (no-gap join)"] += 1
            continue
        if abs(m[0]) < 1e-5:
            cls["on the mirror plane"] += 1
            continue
        cls["other"] += 1
        if len(other) < 6:
            other.append([round(float(c), 4) for c in m])
    area = []
    for f in F:
        p = V[f]
        nrm = np.cross(p[2] - p[0], p[-1] - p[1]) if len(f) == 4 else np.cross(p[1] - p[0], p[2] - p[0])
        area.append(0.5 * np.linalg.norm(nrm))
    objects[n] = {"vertices": int(len(V)), "faces": int(len(F)), "faces_by_flag": {k: int((fl == i).sum()) for i, k in enumerate(("surface", "chamfer", "return"))},
                  "non_manifold_edges": int(nonman), "open_edges": int(len(open_edges[n])), "open_edge_classes": dict(cls),
                  "other_open_edges_at": other, "degenerate_faces_under_1mm2": int(sum(1 for a in area if a < 1e-6))}
print("objects:", ", ".join(f"{n} {o['faces']}" for n, o in objects.items()))

# ------------------------------------------------------------------ gap widths along every seam
# the true seam lines of a panel are its chamfer bottoms (edges shared by a chamfer face and a return face): they sit CH
# deep, GAP/2 off the seam; the gap is the distance between the two panels' lines (parallel parts only)
cham = SegHash(0.02)
cham_pts = defaultdict(list)
for n, (V, F, fl) in OBJ.items():
    if n.endswith("_R") or n.startswith("Glass"):
        continue
    for (a, b), fs in EF[n].items():
        if len(fs) == 2 and {int(fl[fs[0]]), int(fl[fs[1]])} == {1, 2}:
            cham.add(V[a], V[b], n)
cham.done()
samples = defaultdict(list)
for i in range(len(cham.P0)):
    p0, p1, n = cham.P0[i], cham.P1[i], cham.tag[i]
    d0 = p1 - p0
    L = np.linalg.norm(d0)
    if L < 1e-6:
        continue
    for w in (0.0, 0.5):
        p = p0 + w * d0
        if p[0] < -0.002:
            continue
        ids, d, q = cham.near(p)
        best = None
        for j, dd, qq in zip(ids, d, q):
            if cham.tag[j] == n or dd > 0.012:
                continue
            dj = cham.P1[j] - cham.P0[j]
            Lj = np.linalg.norm(dj)
            if Lj < 1e-6 or abs(np.dot(d0, dj)) / (L * Lj) < 0.85:
                continue
            if best is None or dd < best[0]:
                best = (dd, qq, cham.tag[j])
        if best is not None:
            key = " | ".join(sorted((base(n), base(best[2]))))
            samples[key].append((best[0], *(0.5 * (p + best[1]))))
gaps = {}
for k, s in sorted(samples.items()):
    a = np.array(s)
    d = a[:, 0]
    gaps[k] = {"samples": int(len(d)), "mean_mm": float(d.mean() * 1000), "min_mm": float(d.min() * 1000), "max_mm": float(d.max() * 1000),
               "share_within_1mm": float(np.mean(np.abs(d - GAP) <= 0.001 + 1e-9)),
               "pass": bool(np.all(np.abs(d - GAP) <= 0.001 + 1e-9))}
alld = np.concatenate([np.array(s)[:, 0] for s in samples.values()])
gap_summary = {"target_mm": GAP * 1000, "tolerance_mm": 1.0, "samples": int(len(alld)), "mean_mm": float(alld.mean() * 1000),
               "min_mm": float(alld.min() * 1000), "max_mm": float(alld.max() * 1000),
               "share_within_1mm": float(np.mean(np.abs(alld - GAP) <= 0.001 + 1e-9)),
               "method": "distance from each chamfer-bottom line point (vertices and edge midpoints, x >= 0) to the nearest "
                         "parallel (|cos| >= 0.85) chamfer-bottom segment of another panel within 12 mm; both sides of each seam sampled"}
np.savez_compressed(os.path.join(DBG, "seams.npz"), **{k.replace(" | ", "__"): np.array(s) for k, s in samples.items()})
print("gaps:", ", ".join(f"{k} {v['mean_mm']:.2f} [{v['min_mm']:.2f}, {v['max_mm']:.2f}]" for k, v in gaps.items()))


# ------------------------------------------------------------------ seam positions against the sheet
def mids(*pairs):
    out = []
    for a, b in pairs:
        k = " | ".join(sorted((a, b)))
        if k in samples:
            out.append(np.array(samples[k])[:, 1:])
    return np.vstack(out) if out else np.zeros((0, 3))


def sheet_Y(line, z):
    yp = GROUND - z * S_SIDE
    return (line["a"] + line["b"] * yp - X_MID) / S_SIDE


SL_ = G0["extras"]["shut_lines"]
LEl, Bl, TEl = SL_["front door leading edge"], SL_["front door rear edge (B)"], SL_["rear door trailing edge"]


def at_z(M, z, half=0.008):
    sel = M[np.abs(M[:, 2] - z) <= half]
    return (float(sel[:, 1].mean()), int(len(sel))) if len(sel) else (None, 0)


def fit_rows(line):
    y0, y1 = line["y"]
    return (GROUND - y1) / S_SIDE, (GROUND - y0) / S_SIDE


positions = []


def pos_row(item, M, z, line, note=""):
    y, n = at_z(M, z)
    ys = float(sheet_Y(line, z))
    positions.append({"item": item, "z": float(z), "model_Y": y, "sheet_Y": ys, "diff_cm": None if y is None else (y - ys) * 100,
                      "samples": n, "note": note})


side = lambda M: M[M[:, 0] > 0.5]  # noqa: E731
LE = side(mids(("Fender", "FrontDoor"), ("Fender", "Rocker")))
LEdoor = side(mids(("Fender", "FrontDoor")))
z_le_top = float(LEdoor[:, 2].max()) - 0.004
z_le_bot = float(LE[:, 2].min()) + 0.004
z0, z1 = fit_rows(LEl)
pos_row("front door leading edge at the belt (top of the fender | door seam)", LEdoor, z_le_top, LEl,
        f"sheet line fitted over z {z0:.3f}-{z1:.3f}, extrapolated here")
pos_row("front door leading edge, middle of the sheet's fitted rows", LE, 0.5 * (z0 + z1), LEl)
pos_row("front door leading edge at the sill (bottom of the fender | rocker seam)", LE, z_le_bot, LEl,
        f"sheet line fitted over z {z0:.3f}-{z1:.3f}, extrapolated here")
BL = side(mids(("FrontDoor", "RearDoor")))
BLl = BL[BL[:, 2] < B.H_BELT]
z0, z1 = fit_rows(Bl)
pos_row("B line (front door | rear door), middle of the sheet's fitted rows", BLl, 0.5 * (z0 + z1), Bl)
pos_row("B line at the door bottom", BLl, float(BLl[:, 2].min()) + 0.004, Bl, "sheet line extrapolated")
pos_row("B line at the belt", BLl, float(BLl[:, 2].max()) - 0.004, Bl, "sheet line extrapolated")
TE = side(mids(("Quarter", "RearDoor")))
TEl_ = TE[TE[:, 2] < B.H_BELT + 0.01]
z0, z1 = fit_rows(TEl)
pos_row("rear door trailing edge at the belt (top of the door | quarter seam)", TEl_, float(TEl_[:, 2].max()) - 0.004, TEl,
        f"sheet line fitted over z {z0:.3f}-{z1:.3f}, extrapolated here")
pos_row("rear door trailing edge, middle of the sheet's fitted rows", TEl_, 0.5 * (z0 + z1), TEl)


def rake(M, z0, z1):
    s = M[(M[:, 2] >= z0) & (M[:, 2] <= z1)]
    k = np.polyfit(s[:, 2], s[:, 1], 1)[0]
    return float(math.degrees(math.atan(-k)))  # positive = top rearward (bottom forward)


rakes = {"leading edge (LAY-01 7.4, top rearward)": rake(LE, *fit_rows(LEl)),
         "trailing edge (LAY-03 6.4, bottom forward)": -rake(TEl_, *fit_rows(TEl)),
         "B line": rake(BLl, *fit_rows(Bl))}
SH = mids(("Bonnet", "Fender"))
SH = SH[SH[:, 0] > 0]
SHr = SH[SH[:, 1] > -1.95]  # the run along the fender top (ahead of that the seam turns down the bonnet band's side at the corner end)
shut = {"model_x_median_along_the_fender_top": float(np.median(SHr[:, 0])), "inboard_median_cm": float((B.XB - np.median(SHr[:, 0])) * 100),
        "model_x_mean": float(SH[:, 0].mean()), "model_x_min": float(SH[:, 0].min()), "model_x_max": float(SH[:, 0].max()),
        "body_side_XB": float(B.XB), "inboard_mean_cm": float((B.XB - SH[:, 0].mean()) * 100), "LAY-04_cm": 6.0,
        "samples": int(len(SH)), "sheet": "no sheet reference: the side view does not show it and the top view's widths are "
                                         "17 % narrow (G0 note)"}
SP = mids(("LowerTailgate", "UpperHatch"))
split = {"model_z_mean": float(SP[:, 2].mean()), "model_z_min": float(SP[:, 2].min()), "model_z_max": float(SP[:, 2].max()),
         "sheet_z (rear view, LAY-06)": float(G0["rules"]["LAY-06"]["measured"]["split_z"]),
         "diff_cm": float((SP[:, 2].mean() - G0["rules"]["LAY-06"]["measured"]["split_z"]) * 100), "samples": int(len(SP))}
print("positions:", "; ".join(f"{p['item'][:40]} {p['diff_cm']:+.2f} cm" for p in positions if p["diff_cm"] is not None))

# ------------------------------------------------------------------ sheet masks
sheet = np.asarray(Image.open(os.path.join(ROOT, G0["sheet"])).convert("RGB")).astype(float)
Rr, Gg, Bb = sheet[..., 0], sheet[..., 1], sheet[..., 2]
Ll = (Rr + Gg + Bb) / 3
GLASS = (Bb - Rr >= 4) & (Ll >= 80) & (Ll <= 210)  # G0 glass mask (measure_lc80_sheet.py)


def dil(m, k=1):
    for _ in range(k):
        p = np.pad(m, 1)
        o = np.zeros_like(m)
        for dy in range(3):
            for dx in range(3):
                o |= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
        m = o
    return m


def ero(m, k=1):
    return ~dil(~m, k)


GLASS_C = ero(dil(GLASS, 2), 2)  # closed: reflections and frame lines inside the glass filled
H_IMG, W_IMG = GLASS.shape
K = 4


def poly_mask(polys, proj, shape):
    img = Image.new("L", (shape[1] * K, shape[0] * K), 0)
    dr = ImageDraw.Draw(img)
    for P in polys:
        Q = proj(P) * K
        dr.polygon([tuple(q) for q in Q], fill=255)
    return np.asarray(img.resize((shape[1], shape[0]), Image.BOX)) >= 128


def boundary(m):
    return m & ~ero(m, 1)


def proj_side(P):
    return np.c_[X_MID + P[:, 1] * S_SIDE, GROUND - P[:, 2] * S_SIDE]


cams = REP1["cameras"]
VF, VR = G0["views"]["front"], G0["views"]["rear"]


def proj_front(P):
    return np.c_[cams["front"]["centre_px"] + P[:, 0] * VF["px_per_m"], VF["ground_y_px"] - P[:, 2] * VF["px_per_m"]]


def proj_rear(P):
    return np.c_[cams["rear"]["centre_px"] - P[:, 0] * VR["px_per_m"], VR["ground_y_px"] - P[:, 2] * VR["px_per_m"]]


# ------------------------------------------------------------------ window outlines against the sheet's glass regions
PANE_VIEWS = {"Glass_FrontDoor_L": ("side", proj_side, S_SIDE), "Glass_RearDoor_L": ("side", proj_side, S_SIDE),
              "Glass_Quarter_L": ("side", proj_side, S_SIDE), "Glass_Windscreen": ("front", proj_front, VF["px_per_m"]),
              "Glass_RearScreen": ("rear", proj_rear, VR["px_per_m"])}
windows = {}
dbg_tiles = {}
for n, (view, pj, s) in PANE_VIEWS.items():
    V, F, fl = OBJ[n]
    pm = poly_mask([V[f] for f in F], pj, GLASS.shape)
    ys, xs = np.where(pm)
    y0, y1, x0, x1 = max(ys.min() - 30, 0), min(ys.max() + 30, H_IMG), max(xs.min() - 30, 0), min(xs.max() + 30, W_IMG)
    g = GLASS_C[y0:y1, x0:x1]
    pmc = pm[y0:y1, x0:x1]
    seed = g & pmc
    for _ in range(400):  # the sheet glass regions the pane overlaps (geodesic reconstruction inside the mask)
        nxt = dil(seed, 1) & g
        if (nxt == seed).all():
            break
        seed = nxt
    # outer envelope of the glass region (seats, pillars and frames seen through the glass are not glass-coloured and
    # can open to the edge): per row from the left-most to the right-most glass pixel, per column from the top-most to
    # the bottom-most, both
    rowf = np.zeros_like(seed)
    colf = np.zeros_like(seed)
    for i in range(seed.shape[0]):
        w_ = np.where(seed[i])[0]
        if len(w_):
            rowf[i, w_[0]:w_[-1] + 1] = True
    for j in range(seed.shape[1]):
        w_ = np.where(seed[:, j])[0]
        if len(w_):
            colf[w_[0]:w_[-1] + 1, j] = True
    seed = rowf & colf
    sb = boundary(seed)
    mb = boundary(pmc)
    py, px = np.where(mb)
    sy, sx = np.where(sb)
    if len(sy) == 0:
        windows[n] = {"view": view, "note": "no sheet glass region under the pane"}
        continue
    d_ms = np.array([np.hypot(sx - x, sy - y).min() for x, y in zip(px, py)]) / s * 100
    d_sm = np.array([np.hypot(px - x, py - y).min() for x, y in zip(sx, sy)]) / s * 100
    inter, uni = (seed & pmc).sum(), (seed | pmc).sum()
    windows[n] = {"view": view, "px_per_m": s, "pane_to_sheet_mean_cm": float(d_ms.mean()), "pane_to_sheet_median_cm": float(np.median(d_ms)),
                  "pane_to_sheet_max_cm": float(d_ms.max()), "sheet_to_pane_median_cm": float(np.median(d_sm)),
                  "sheet_to_pane_mean_cm": float(d_sm.mean()), "sheet_to_pane_max_cm": float(d_sm.max()),
                  "area_pane_cm2": float(pmc.sum() / s ** 2 * 1e4), "area_sheet_cm2": float(seed.sum() / s ** 2 * 1e4),
                  "iou": float(inter / uni)}
    crop = sheet[y0:y1, x0:x1].astype(np.uint8).copy()
    crop[sb] = (0, 200, 255)
    crop[mb] = (255, 0, 255)
    dbg_tiles[n] = Image.fromarray(crop).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.NEAREST)
print("windows:", ", ".join(f"{n} {w.get('pane_to_sheet_mean_cm', float('nan')):.2f}/{w.get('sheet_to_pane_mean_cm', float('nan')):.2f} cm"
                            for n, w in windows.items()))
Wt = sum(t.width for t in dbg_tiles.values()) + 10 * len(dbg_tiles)
Ht = max(t.height for t in dbg_tiles.values())
canvas = Image.new("RGB", (Wt, Ht + 24), (255, 255, 255))
xx = 0
dr = ImageDraw.Draw(canvas)
for n, t in dbg_tiles.items():
    canvas.paste(t, (xx, 24))
    dr.text((xx + 4, 4), f"{n}: pane magenta, sheet glass cyan", fill=(0, 0, 0))
    xx += t.width + 10
canvas.save(os.path.join(DBG, "window-check.png"))

# ------------------------------------------------------------------ outline against the sheet's side view (as G1)
def opening(m):
    return dil(ero(m, 1), 1)


SOLID = opening((Ll < 165) | (Rr - Bb > 10))
s1 = np.load(os.path.join(G1, "shell-mesh.npz"))
polys = []
for n, (V, F, fl) in OBJ.items():
    polys += [V[f] for f in F]
for k in ("BF", "BR"):
    Vb = s1[k + "_v"]
    polys += [Vb[[q for q in f if q >= 0]] for f in s1[k + "_f"]]
shell = poly_mask(polys, proj_side, (360, W_IMG))
x_f = int(math.ceil(X_MID + B.Y_BUMP_F * S_SIDE))
x_r = int(math.floor(X_MID + B.Y_BUMP_R * S_SIDE))
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
outline = {"method": "as G1: 2D nearest distance from each sheet body-outline pixel to the silhouette boundary of all panels, "
                     "glass and the G1 bumpers, sheet side view at the G0 registration",
           "all": {"samples": int(len(dcm)), "mean_cm": float(dcm.mean()), "max_cm": float(dcm.max()),
                   "max_at_px": [int(P[np.argmax(dcm), 0]), int(P[np.argmax(dcm), 1])]},
           "targets": {"mean_cm": 1.5, "max_cm": 4.0}}
for k in ("upper", "front face", "tail face"):
    sel = lab == k
    outline[k] = {"samples": int(sel.sum()), "mean_cm": float(dcm[sel].mean()), "max_cm": float(dcm[sel].max())}
g1o = REP1["outline"]["all"]
outline["G1_v02_for_comparison"] = {"mean_cm": g1o["mean_cm"], "max_cm": g1o["max_cm"]}
order = np.argsort(-dcm)[:6]
outline["worst"] = [{"Y": float((P[i, 0] - X_MID) / S_SIDE), "Z": float((GROUND - P[i, 1]) / S_SIDE), "cm": float(dcm[i]),
                     "part": str(lab[i])} for i in order]
crop = sheet[:358, 230:1300].astype(np.uint8).copy()
crop[sb[:358, 230:1300]] = (255, 0, 255)
Image.fromarray(crop).resize((1070 * 2, 358 * 2), Image.NEAREST).save(os.path.join(DBG, "outline.png"))
print(f"outline: mean {dcm.mean():.2f} cm, max {dcm.max():.2f} cm (G1 v02 {g1o['mean_cm']:.2f} / {g1o['max_cm']:.2f})")

# ------------------------------------------------------------------ folds on the panel surfaces (seams, chamfers and returns excluded)
tuck_z = 0.5 * (B.TUCK_Z1 + B.TUCK_Z2)
tuck_half = 0.5 * (B.TUCK_Z1 - B.TUCK_Z2) + 0.004
fpl = B.fp[: len(B.fp) // 2]
seg_a, seg_b = fpl[:-1], fpl[1:]


def dist_to_poly(P2):
    ab = seg_b - seg_a
    t = np.clip(((P2[:, None, :] - seg_a[None]) * ab[None]).sum(2) / (ab * ab).sum(1)[None], 0, 1)
    q = seg_a[None] + t[..., None] * ab[None]
    return np.linalg.norm(P2[:, None, :] - q, axis=2).min(1)


fold_all = []
for n, (V, F, fl) in OBJ.items():
    if n.endswith("_R"):
        continue
    nrm, area, hmin = [], [], []
    for f in F:
        p = V[f]
        nv = np.cross(p[2] - p[0], p[-1] - p[1]) if len(f) == 4 else np.cross(p[1] - p[0], p[2] - p[0])
        a = np.linalg.norm(nv)
        nrm.append(nv / a if a > 0 else nv)
        area.append(0.5 * a)
        emax = max(np.linalg.norm(p[(k + 1) % len(f)] - p[k]) for k in range(len(f)))
        hmin.append(a / emax if emax > 0 else 0.0)
    near = np.zeros(len(V), bool)
    hi = V[:, 2] > B.H_BELT - 0.08
    if hi.any():
        near[hi] = dist_to_poly(np.abs(V[hi, :2])) < 0.01
    for (a, b), fs in EF[n].items():
        if len(fs) != 2:
            continue
        f1, f2 = fs
        if fl[f1] != 0 or fl[f2] != 0:
            continue
        if area[f1] < 2e-6 or area[f2] < 2e-6 or hmin[f1] < 1e-3 or hmin[f2] < 1e-3:
            continue
        ang = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(nrm[f1], nrm[f2]))))))
        m = 0.5 * (V[a] + V[b])
        fold_all.append((ang, float(m[0]), float(m[1]), float(m[2]), n, bool(near[a] or near[b]), abs(m[2] - tuck_z) < tuck_half))
fold_all.sort(key=lambda f: -f[0])
nt = [f for f in fold_all if not f[6]]
nb = [f for f in nt if not f[5]]
folds = {"edges_measured": len(fold_all), "target_deg": 12.0,
         "max_deg": fold_all[0][0], "at": list(fold_all[0][1:4]), "object": fold_all[0][4], "over_12": int(sum(1 for f in fold_all if f[0] > 12)),
         "max_excluding_sill_tuck_deg": nt[0][0], "at_excluding_tuck": list(nt[0][1:4]), "object_excluding_tuck": nt[0][4],
         "over_12_excluding_tuck": int(sum(1 for f in nt if f[0] > 12)),
         "max_without_tuck_and_1cm_junction_band_deg": nb[0][0], "at_band": list(nb[0][1:4]), "object_band": nb[0][4],
         "over_12_band": int(sum(1 for f in nb if f[0] > 12)),
         "top": [{"deg": f[0], "at": [round(c, 4) for c in f[1:4]], "object": f[4], "junction_band": f[5]} for f in nt[:10]],
         "top_without_band": [{"deg": f[0], "at": [round(c, 4) for c in f[1:4]], "object": f[4]} for f in nb[:16]],
         "over_12_by_object_without_band": {o: int(sum(1 for f in nb if f[0] > 12 and f[4] == o)) for o in sorted({f[4] for f in nb if f[0] > 12})},
         "G1_v02_for_comparison": {k: REP1["folds"][k] for k in ("max_excluding_sill_tuck_deg", "max_with_1cm_junction_band_and_without_tuck_deg")}}
tk = [f for f in fold_all if f[6]]
folds["sill_tuck_crease_max_deg"] = tk[0][0] if tk else None
print(f"folds: max {folds['max_deg']:.1f} at {folds['object']}, excl tuck {folds['max_excluding_sill_tuck_deg']:.1f} "
      f"({folds['object_excluding_tuck']}), excl tuck+band {folds['max_without_tuck_and_1cm_junction_band_deg']:.1f}")

rep = {"objects": objects, "gaps": {"summary": gap_summary, "seams": gaps},
       "seam_positions": {"rows": positions, "rakes_deg": rakes, "bonnet_shut_line": shut, "tailgate_split": split},
       "windows": windows, "outline": outline, "folds": folds}
with open(os.path.join(OUT, "g2-checks.json"), "w", encoding="utf-8") as f:
    json.dump(rep, f, indent=1, default=float)
print("g2-checks.json written")
