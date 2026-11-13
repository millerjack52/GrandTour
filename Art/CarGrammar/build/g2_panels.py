"""G2 (docs/CAR_GRAMMAR_PLAN.md section 9): panels and openings as regions of the G1 v02 master grids.

The masters are re-sampled exactly: every point is a sample of the G1 v02 analytic surfaces (lower body L: station
outline x profile wall / round / top; greenhouse G: station x profile wall / round / roof). Each master is sampled on
one structured grid whose columns and rows include every seam line, both sides of each gap (seam +- (half gap +
chamfer)) and the window opening edges. Cells are assigned to panels by rules (9b); cells inside a gap strip or a window
opening are dropped. Every panel boundary that meets another panel gets a 45 degree chamfer row and a return along
the inward surface normal (9c); open lower edges get the return only. The bonnet top and the cowl strip are plan
patches on the same surfaces. Glass panes are separate patches inset along the normal with an edge round.

Writes Art/Export/VehicleTools/landcruiser-grammar-g2-v01/: panels.npz, g2-build.json. System Python (numpy)."""
import json
import math
import os
import sys
import time

import numpy as np

os.environ["G1_NO_SAVE"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g1_shell as B  # noqa: E402  (the G1 v02 masters, unchanged)

t0 = time.time()
S = B.S
OUT = os.path.join(B.ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-g2-v01")
STEP = B.STEP
N_ARC = B.N_ARC
KNOT = 0.005  # profile knots along the station coordinate (sampling, not a design value)

# ------------------------------------------------------------------ numbers (library)
LE_RAKE = S.rule("LAY-01", "rake", use="front door leading edge rake")
YB = S.rule("LAY-02", "y", use="door split (B-pillar centre)")
TE_BEHIND = S.rule("LAY-03", "behind", use="rear door trailing edge behind the rear arch front")
TE_RAKE = S.rule("LAY-03", "rake", use="rear door trailing edge rake")
SHUT_IN = S.rule("LAY-04", "inboard", use="bonnet shut line inboard of the body side")
GAP = S.rule("LAY-05", "gap", use="panel gap")
CH = S.rule("LAY-05", "chamfer", use="edge chamfer (and glass edge round)")
RET = S.rule("LAY-05", "return", use="return depth")
SPLIT = S.rule("LAY-06", "split", use="tailgate split height")
TG_HW = S.rule("LAY-06", "half_width", use="tailgate half-width")
DOOR_UP = S.rule("LAY-07", idx=0, use="door bottom above the sill")
FW = S.rule("LAY-08", idx=0, use="window frame width")
COWL_W = S.rule("LAY-09", idx=0, use="cowl strip width")
TG_UP = S.rule("LAY-11", idx=0, use="lower tailgate bottom above the rear bumper top")
GLASS_INSET = S.con("GLASS_INSET", "glass inset along the normal")
HALF = GAP / 2
E = HALF + CH  # surface edge distance from a seam
SHUT = B.XB - SHUT_IN
Z_DB = B.H_SILL + DOOR_UP
Z_TGB = B.z_rb1 + TG_UP
S.prov["seams"] = "LAY-01..12 as recorded above; door bottom = H_SILL + LAY-07; tailgate bottom = rear bumper top + LAY-11"

# A-pillar foot (the windscreen side edge on the ledge), as in G1 v02
zA = B.H_BELT
for _ in range(50):
    zA = float(B.ledge(float(B.G_YF(zA))))
YA = float(B.G_YF(zA))


def y_le(z):
    return YA + (np.asarray(z, float) - zA) * math.tan(math.radians(LE_RAKE))


Y_TEB = (B.Y_HR - B.ARCH_R) + TE_BEHIND
Z_TEB = float(B.ledge(Y_TEB))


def y_te(z):
    return Y_TEB + (np.asarray(z, float) - Z_TEB) * math.tan(math.radians(TE_RAKE))


Y_X = B.Y_HR - math.sqrt(B.ARCH_R ** 2 - (Z_DB - B.HUB_Z) ** 2)  # rear arch meets the door bottom (rocker end)
print(f"seams: A-pillar foot Y {YA:.4f} Z {zA:.4f}; trailing edge at the belt Y {Y_TEB:.4f}; rocker ends at Y {Y_X:.4f}")

# G roof targets (G1 rule) for profiles of arbitrary stations
_ptg = np.array([[stn.O[0] + rd["Pt"][0] * stn.n[0], stn.O[1] + rd["Pt"][0] * stn.n[1]] for stn, rd in B.G_RD])
_w_t = float(np.median(_ptg[[k for k, st in enumerate(B.G_ST) if st[0] == 2], 0]))
YF_M, YR_M = float(_ptg[0, 1]) + _w_t, float(_ptg[-1, 1]) - _w_t


def g_base(st):
    zs = np.arange(B.H_BELT - 0.12, B.H_BELT + 0.20, 0.0005)
    P = B.GO.point(st, zs)
    # the L raster is empty within 2 mm of the mirror line (its quads cover x >= 0 only), so at the rear centre the
    # lookup fell back to the flat plate 7.1 mm high; read it at |x| >= 2 mm (symmetric surface, flat across the centre)
    h = B.H_at(B.H_L, np.maximum(np.abs(P[:, 0]), 0.0021), P[:, 1])
    h = np.where(np.isfinite(h), h, B.z_top_L(P[:, 0], P[:, 1]))
    f = zs - h
    k = np.where((f[:-1] < 0) & (f[1:] >= 0))[0]
    i = k[0]
    t = f[i] / (f[i] - f[i + 1])
    return float(zs[i] + t * (zs[i + 1] - zs[i]))


# ------------------------------------------------------------------ profile spaces
class Space:
    """Station coordinate t (arc length round the reference outline at H_BELT, front centre 0 to rear centre t_end) and
    profile arc length s (L: from H_SILL; G: from the base). Profiles are computed exactly at knots every KNOT and
    interpolated linearly between (sub-0.1 mm)."""

    def __init__(self, kind):
        self.kind = kind
        self.O = B.LO if kind == "L" else B.GO
        g = self.O.g(B.H_BELT)
        self.y0b, self.y1b = self.O.smap[0], self.O.smap[1]
        self.len = [float(g["tfx"][0]), abs(float(g["af"][0])) * self.O.rcf, self.y1b - self.y0b,
                    abs(float(g["ar"][0])) * self.O.rcr, float(g["trx"][0])]
        self.cum = np.r_[0.0, np.cumsum(self.len)]
        self.t_end = float(self.cum[-1])
        self.cache = {}

    def st(self, t):
        t = min(max(float(t), 0.0), self.t_end)
        k = min(int(np.searchsorted(self.cum, t, side="right") - 1), 4)
        f = (t - self.cum[k]) / self.len[k]
        if k == 2:
            return (2, self.y0b + (t - self.cum[2]))
        return (k, min(max(f, 0.0), 1.0))

    def t_y(self, y):
        return float(self.cum[2] + (y - self.y0b))

    def t_rear_x(self, x):
        return float(self.cum[4] + (self.len[4] - x))

    def knot(self, k):
        if k in self.cache:
            return self.cache[k]
        t = min(k * KNOT, self.t_end)
        st = self.st(t)
        if self.kind == "L":
            stn, rd = B.solve_round(B.LO, st, B.z_top_L, B.R_L(st), B.H_BELT - 0.03, B.H_SILL + 0.10, B.H_BELT + 0.25)
            z0 = B.H_SILL
        else:
            stn, rd = B.solve_round(B.GO, st, B.roof_z, B.R_G(st), B.Z_RAIL, B.H_BELT - 0.05, B.H_ROOF + 0.10)
            z0 = g_base(st)
        zw = np.r_[np.arange(z0, rd["zw_t"], 0.002), rd["zw_t"]]
        wall = np.c_[self.O.point(st, zw), zw]
        O, n = np.array(stn.O), np.array(stn.n)
        wall[-1] = [O[0] + rd["Pw"][0] * n[0], O[1] + rd["Pw"][0] * n[1], rd["Pw"][1]]
        a2, _ = stn.arc(rd, 90)
        arc = np.c_[O[0] + a2[:, 0] * n[0], O[1] + a2[:, 0] * n[1], a2[:, 1]]
        pt = arc[-1]
        if self.kind == "L":
            rr = rd["Pt"][0] - np.arange(0.002, 1.9, 0.002)
            top = np.c_[O[0] + rr * n[0], O[1] + rr * n[1], B.z_top_L(O[0] + rr * n[0], O[1] + rr * n[1])]
        else:
            T = np.array([0.0, min(max(pt[1], YF_M), YR_M)])
            dd = np.linalg.norm(T - pt[:2])
            ts = np.arange(0.002, max(dd, 0.004), 0.002) / max(dd, 1e-9)
            ts = np.r_[ts[ts < 1], 1.0]
            xy = pt[:2][None] + ts[:, None] * (T - pt[:2])[None]
            top = np.c_[xy, B.roof_z(xy[:, 0], xy[:, 1])]
        P = np.vstack([wall, arc, top])
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        keep = np.r_[True, seg > 1e-9]
        P = P[keep]
        s = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
        i_wt = len(wall) - 1
        i_tt = len(wall) + len(arc) - 2
        T3 = np.gradient(P, s, axis=0)
        H3 = np.array([-n[1], n[0], 0.0])
        N = np.cross(H3[None], T3)
        N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-15
        if self.kind == "G":  # roof part off the station plane: analytic roof normal
            k0 = i_tt + 1
            eps = 1e-4
            gx = (B.roof_z(P[k0:, 0] + eps, P[k0:, 1]) - B.roof_z(P[k0:, 0] - eps, P[k0:, 1])) / (2 * eps)
            gy = (B.roof_z(P[k0:, 0], P[k0:, 1] + eps) - B.roof_z(P[k0:, 0], P[k0:, 1] - eps)) / (2 * eps)
            nr = np.c_[-gx, -gy, np.ones_like(gx)]
            N[k0:] = nr / np.linalg.norm(nr, axis=1, keepdims=True)
        bias = np.array([n[0], n[1], 0.3])
        N[(N @ bias) < 0] *= -1
        prof = {"t": t, "st": st, "P": P, "N": N, "s": s, "s_wt": float(s[min(i_wt, len(s) - 1)]),
                "s_tt": float(s[min(i_tt, len(s) - 1)]), "s_end": float(s[-1]), "z_wt": float(rd["zw_t"]),
                "R": float(rd["R"]), "O": O, "n": n}
        self.cache[k] = prof
        return prof

    def pair(self, t):
        t = min(max(float(t), 0.0), self.t_end)
        k = min(int(t // KNOT), int(self.t_end // KNOT))
        k1 = min(k + 1, int(math.ceil(self.t_end / KNOT)))
        tk, tk1 = k * KNOT, min(k1 * KNOT, self.t_end)
        w = 0.0 if tk1 <= tk else (t - tk) / (tk1 - tk)
        return self.knot(k), self.knot(k1), w

    def scalar(self, t, key):
        a, b, w = self.pair(t)
        return (1 - w) * a[key] + w * b[key]

    def PN(self, t, s):
        a, b, w = self.pair(t)

        def ev(pr):
            s_ = min(max(s, 0.0), pr["s"][-1])
            p = np.array([np.interp(s_, pr["s"], pr["P"][:, k]) for k in range(3)])
            nn = np.array([np.interp(s_, pr["s"], pr["N"][:, k]) for k in range(3)])
            return p, nn
        pa, na = ev(a)
        pb, nb = ev(b)
        n = (1 - w) * na + w * nb
        return (1 - w) * pa + w * pb, n / (np.linalg.norm(n) + 1e-15)

    def s_of_z(self, t, z):
        a, b, w = self.pair(t)

        def f(pr):
            iw = int(np.searchsorted(pr["s"], pr["s_wt"]))
            zz = pr["P"][:iw + 1, 2]
            return float(np.interp(z, zz, pr["s"][:iw + 1]))
        return (1 - w) * f(a) + w * f(b)

    def s_x(self, t, X, s_from):
        """First s >= s_from where the profile comes inboard of |x| = X (above H_BELT - 0.25), interpolated."""
        a, b, w = self.pair(t)

        def f(pr):
            P, s = pr["P"], pr["s"]
            ok = (s >= s_from) & (P[:, 2] > B.H_BELT - 0.25)
            g = np.abs(P[:, 0]) - X
            idx = np.where(ok & (g <= 0))[0]
            if not len(idx):
                return pr["s_end"]
            i = idx[0]
            if i == 0 or not ok[i - 1]:
                return float(s[i])
            return float(s[i - 1] + (s[i] - s[i - 1]) * g[i - 1] / (g[i - 1] - g[i]))
        return (1 - w) * f(a) + w * f(b)

    def s_where(self, t, fn, s_from=0.0, default=None):
        """First s >= s_from where fn(points) becomes True along the profile (linear between samples)."""
        a, b, w = self.pair(t)

        def f(pr):
            m = (pr["s"] >= s_from) & fn(pr["P"])
            idx = np.where(m)[0]
            if not len(idx):
                return pr["s_end"] if default is None else default
            i = idx[0]
            return float(pr["s"][i])
        return (1 - w) * f(a) + w * f(b)


SL, SG = Space("L"), Space("G")
# G base line (where the greenhouse wall meets the built lower body): the lower body's top ends exactly there
_tb = np.arange(0.0, SG.t_end + 1e-9, 0.004)
GB_LINE = np.array([np.r_[B.GO.point(SG.st(t), zb)[0], zb] for t, zb in ((t, g_base(SG.st(t))) for t in _tb)])


_SGB = {}


def s_gb_L(t):
    a, b, w = SL.pair(t)

    def f(pr):
        key = round(float(pr["t"]), 6)
        if key not in _SGB:
            _SGB[key] = f0(pr)
        return _SGB[key]

    def f0(pr):
        # where the profile first enters the G footprint (as G1's top rows), refined to the nearest point of the G base
        # line within 4 cm of that entry on the near side (x >= 0): the far side and other crossings never match
        P_, s_ = pr["P"], pr["s"]
        cand = np.where((s_ >= 0.5 * pr["s_wt"]) & (P_[:, 0] >= -0.002))[0]
        ins = B.pip(B.fp, P_[cand, :2])
        if not ins.any():
            return pr["s_end"]
        s_fp = float(s_[cand[int(np.argmax(ins))]])
        m = np.where((np.abs(s_ - s_fp) < 0.04) & (P_[:, 0] >= -0.002))[0]
        if not len(m):
            return s_fp
        Q = P_[m]
        d = np.min(np.linalg.norm(Q[:, None, :2] - GB_LINE[None, :, :2], axis=2) + np.abs(Q[:, None, 2] - GB_LINE[None, :, 2]), axis=1)
        i = int(np.argmin(d))
        return float(s_[m[i]]) if d[i] < 0.02 else s_fp
    return (1 - w) * f(a) + w * f(b)
FP_POLY = B.fp  # G footprint (full outline, plan)


def inside_fp(P):
    return B.pip(FP_POLY, np.asarray(P)[:, :2])


# ------------------------------------------------------------------ seam stations (t) in each space
T_CE = float(SL.cum[2])                       # L front corner arc end (LAY-10)
T_LB = SL.t_y(YB)                             # L B line
T_LX = SL.t_y(Y_X)                            # rocker end
T_LC = SL.t_y(B.Y_C)
T_R735 = SL.t_rear_x(float(SG.len[4]))        # L tail station under G's rear corner end
T_TG = SL.t_rear_x(TG_HW)                     # tailgate seam on the tail face
T_LAB = SL.t_y(float(SG.PN(SG.t_y(SG.y0b + B.A_WIDTH), 0.0)[0][1]))  # door skin under the A band's trailing edge
G_S0E = float(SG.cum[1])                      # windscreen face end (A corner start)
G_A = SG.t_y(SG.y0b + B.A_WIDTH)              # A-pillar trailing edge (constant offset from the corner end)
G_B, G_C = SG.t_y(YB), SG.t_y(B.Y_C)
G_QG0, G_D = SG.t_y(B.Y_C + B.PIL_C / 2), SG.t_y(B.Y_D_EDGE)
G_C3E = float(SG.cum[4])                      # G rear corner arc end (hatch side)
print(f"spaces: L t_end {SL.t_end:.3f}, G t_end {SG.t_end:.3f}; knots so far L {len(SL.cache)} G {len(SG.cache)}")


def t_le(s, t_guess=None):
    t = SL.t_y(YA) if t_guess is None else t_guess
    for _ in range(3):
        z = SL.PN(t, s)[0][2]
        t = SL.t_y(float(y_le(z)))
    return t


def t_te(s, t_guess=None):
    t = SL.t_y(Y_TEB) if t_guess is None else t_guess
    for _ in range(3):
        z = SL.PN(t, s)[0][2]
        t = SL.t_y(float(y_te(z)))
    return t


# ------------------------------------------------------------------ L master levels and region
_LCACHE = {}


def L_levels(t):
    k = round(float(t), 5)
    if k not in _LCACHE:
        _LCACHE[k] = _L_levels(k)
    return _LCACHE[k]


def _L_levels(t):
    """Seam levels (s) at station t, both gap lines of each seam; region bottom and top."""
    s_bot = SL.s_of_z(t, float(B.arch_z(np.array([SL.PN(t, 0.0)[0][1]]))[0])) if SL.st(t)[0] == 2 else 0.0
    s_wt, s_tt = SL.scalar(t, "s_wt"), SL.scalar(t, "s_tt")
    s_db, s_tgb, s_sp = SL.s_of_z(t, Z_DB), SL.s_of_z(t, Z_TGB), SL.s_of_z(t, SPLIT)
    s_shF = SL.s_x(t, SHUT + E, s_wt * 0.5)
    s_shB = SL.s_x(t, SHUT - E, s_wt * 0.5)
    s_gb = s_gb_L(t)
    if t < T_CE:
        s_top = s_tt
    elif t < t_le(s_shF):
        s_top = s_shF
    else:
        s_top = s_gb
    lv = [s_db - E, s_db + E, s_tgb - E, s_tgb + E, s_sp - E, s_sp + E, s_wt - E, s_wt + E, s_tt, s_shF, s_shB,
          s_gb - E, s_gb, SL.s_of_z(t, B.TUCK_Z2), SL.s_of_z(t, B.TUCK_Z1)]  # last two: the sill tuck round's ends
    return s_bot, s_top, lv, {"s_wt": s_wt, "s_tt": s_tt, "s_db": s_db, "s_tgb": s_tgb, "s_sp": s_sp, "s_shF": s_shF,
                              "s_shB": s_shB, "s_gb": s_gb}


def L_panel(t, s, sd):
    """Panel of a lower-body point (station t, profile s); sd = that station's seam levels."""
    if t < T_CE:
        return "front_panel" if s < sd["s_wt"] else "bonnet"
    if s > sd["s_top"] + 1e-9:
        return None
    t_le_s = t_le(s, t)
    if t < t_le_s:
        return "fender"
    if t >= T_TG:
        if s < sd["s_tgb"]:
            return "valance"
        if s < sd["s_sp"]:
            return "tailgate"
        return "hatch"
    if t >= t_te(s, t):
        return "quarter"
    if s < sd["s_db"]:
        return "rocker" if t < T_LX else ("rear_door" if s >= sd["s_bot"] else None)
    return "front_door" if t < T_LB else "rear_door"


def G_panel(t, s, sd):
    if t < G_A:
        if t < G_S0E and B.GLASS_BELT < s < sd["s_hb"]:
            return "hole_ws"
        return "cabin"
    if t >= G_C3E:
        if s >= sd["s_wt"]:
            return "cabin"
        if t > G_C3E + FW and FW < s < sd["s_wt"] - FW:
            return "hole_rs"
        return "hatch"
    if s >= sd["s_hb"]:
        return "cabin"
    if t < G_B:
        return "hole_fd" if (G_A + FW < t < G_B - FW and FW < s < sd["s_hb"] - FW) else "front_door"
    if t < G_C:
        return "hole_rd" if (G_B + FW < t < G_C - FW and FW < s < sd["s_hb"] - FW) else "rear_door"
    return "hole_q" if (G_QG0 < t < G_D and FW < s < sd["s_hb"] - FW) else "quarter"


_GCACHE = {}


def G_levels(t):
    k = round(float(t), 5)
    if k not in _GCACHE:
        _GCACHE[k] = _G_levels(k)
    return _GCACHE[k]


def _G_levels(t):
    s_wt, s_tt, s_end = SG.scalar(t, "s_wt"), SG.scalar(t, "s_tt"), SG.scalar(t, "s_end")
    s_hb = SG.s_of_z(t, SG.scalar(t, "z_wt") - B.HEADER)
    lv = [E, B.GLASS_BELT - E, B.GLASS_BELT + E, FW - E, FW + E, s_hb - FW - E, s_hb - FW + E, s_hb - E, s_hb + E,
          s_wt - FW - E, s_wt - FW + E, s_wt - E, s_wt + E, s_tt]
    return 0.0, s_end, lv, {"s_wt": s_wt, "s_tt": s_tt, "s_hb": s_hb, "s_end": s_end}


OBJ = {"front_panel": "FrontPanel", "bonnet": "Bonnet", "fender": "Fender", "rocker": "Rocker", "front_door": "FrontDoor",
       "rear_door": "RearDoor", "quarter": "Quarter", "valance": "Valance", "tailgate": "LowerTailgate", "hatch": "UpperHatch",
       "cabin": "CabinFrame", "cowl": "Cowl"}
BODY_JOIN = {"CabinFrame", "Cowl"}


# ------------------------------------------------------------------ structured master grid with seam lines
MIN_ARC_COLS = 10   # columns per plan corner arc at least (as G1's stations, min_arc 10)
ROW_TURN = 7.5      # degrees of profile turn per row at most (G1: N_ARC 12 rows over a 90-degree round)


def column_curves(seams, t0, t1, space):
    """seams: list of callables s -> t (or floats), sorted front to rear; returns list of column functions (s -> t).
    Columns every STEP, and at least MIN_ARC_COLS over each plan corner arc."""
    cols = []
    bounds = [t0] + seams + [t1]
    arcs = ((space.cum[1], space.cum[2]), (space.cum[3], space.cum[4]))

    def asfn(v):
        return v if callable(v) else (lambda s, v=v: v)
    for a, b in zip(bounds[:-1], bounds[1:]):
        fa, fb = asfn(a), asfn(b)
        w = abs(fb(0.6) - fa(0.6))
        n = max(1, int(math.ceil(w / STEP)))
        mid = 0.5 * (fa(0.6) + fb(0.6))
        for a0, a1 in arcs:
            if a0 - 1e-9 <= mid <= a1 + 1e-9:
                n = max(n, int(math.ceil(w / ((a1 - a0) / MIN_ARC_COLS) - 1e-6)))
        for k in range(n):
            cols.append(lambda s, fa=fa, fb=fb, k=k, n=n: fa(s) + (fb(s) - fa(s)) * k / n)
    cols.append(asfn(bounds[-1]))
    return cols


def build_master(space, cols, levels_fn, n_band):
    """Nodes (c, r): t = col_c(s), s = r-th sorted level at t (bands between consecutive levels subdivided by n_band[i]).
    Returns param grid T, Sg (nc, nr) and per-column seam dicts."""
    nc = len(cols)
    nr = 1 + sum(n_band)
    T = np.zeros((nc, nr))
    Sg = np.zeros((nc, nr))
    SD = []
    for c, col in enumerate(cols):
        sd = None
        t = col(0.3)
        for r in range(nr):
            s = None
            for it in range(3):
                sb, st_, lv, sd = levels_fn(t)
                full = sorted([sb] + [min(max(v, sb), st_) for v in lv] + [st_])
                sv = [full[0]]
                for i in range(len(full) - 1):
                    for j in range(1, n_band[i] + 1):
                        sv.append(full[i] + (full[i + 1] - full[i]) * j / n_band[i])
                s = sv[r]
                t_new = col(s)
                if abs(t_new - t) < 1e-7:
                    break
                t = t_new
            T[c, r], Sg[c, r] = t, s
        # rows stay in order up the column: a slanted column crossing a steep arch edge evaluates the region bottom at a
        # slightly different station per row, which could put a collapsed row below the one before it (flipped cells)
        for r in range(1, nr):
            if Sg[c, r] < Sg[c, r - 1]:
                Sg[c, r] = Sg[c, r - 1]
                T[c, r] = col(Sg[c, r])
        sb, st_, lv, sd = levels_fn(T[c, 0])
        sd["s_bot"], sd["s_top"] = sb, st_
        SD.append(sd)
    return T, Sg, SD


def band_counts(space, levels_fn, ts, nlev):
    """Rows per band (global): every STEP of profile length, and at most ROW_TURN degrees of profile turn per row."""
    mx = np.zeros(nlev + 1)
    tx = np.zeros(nlev + 1)
    for t in ts:
        sb, st_, lv, _ = levels_fn(t)
        full = sorted([sb] + [min(max(v, sb), st_) for v in lv] + [st_])
        mx = np.maximum(mx, np.diff(full))
        pr = space.pair(t)[0]
        ang = np.degrees(np.arccos(np.clip((pr["N"][1:] * pr["N"][:-1]).sum(1), -1, 1)))
        sm = 0.5 * (pr["s"][1:] + pr["s"][:-1])
        for i in range(len(full) - 1):
            sel = (sm >= full[i]) & (sm <= full[i + 1])
            tx[i] = max(tx[i], float(ang[sel].sum()))
    return [max(1, int(math.ceil(m / STEP)), int(math.ceil(a / ROW_TURN - 1e-6))) for m, a in zip(mx, tx)]


print("building the L master grid ...", flush=True)
assert float(SL.cum[1]) < T_CE - E and float(SL.cum[4]) < T_R735 and float(SL.cum[3]) > t_te(0.5) + E
L_SEAMS = [float(SL.cum[1]), T_CE - E, T_CE + E, lambda s: t_le(s) - E, lambda s: t_le(s) + E, T_LAB, T_LB - E, T_LB + E, T_LX,
           T_LC, lambda s: t_te(s) - E, lambda s: t_te(s) + E, float(SL.cum[3]), float(SL.cum[4]), T_R735, T_TG - E, T_TG + E]
L_COLS = column_curves(L_SEAMS, 0.0, SL.t_end, SL)
nb_L = band_counts(SL, L_levels, np.linspace(0, SL.t_end, 40), 15)
nb_L = [max(n, 2) for n in nb_L]
LT, LS, LSD = build_master(SL, L_COLS, L_levels, nb_L)
print(f"  L grid {LT.shape} ({time.time() - t0:.1f} s, L knots {len(SL.cache)})", flush=True)
print("building the G master grid ...", flush=True)
G_SEAMS = sorted([G_S0E - E, G_S0E + E, G_A - E, G_A + E, G_A + FW - E, G_A + FW + E, G_B - FW - E, G_B - FW + E, G_B - E,
                  G_B + E, G_B + FW - E, G_B + FW + E, G_C - FW - E, G_C - FW + E, G_C - E, G_C + E, G_QG0 - E, G_QG0 + E,
                  G_D - E, G_D + E, G_C3E - E, G_C3E + E, G_C3E + FW - E, G_C3E + FW + E, float(SG.cum[2]), float(SG.cum[3])])
G_COLS = column_curves(G_SEAMS, 0.0, SG.t_end, SG)
nb_G = band_counts(SG, G_levels, np.linspace(0, SG.t_end, 40), 14)
nb_G = [max(n, 1) for n in nb_G]
GT, GS_, GSD = build_master(SG, G_COLS, G_levels, nb_G)
print(f"  G grid {GT.shape} ({time.time() - t0:.1f} s, G knots {len(SG.cache)})", flush=True)


def eval_grid(space, T, Sg):
    P = np.zeros(T.shape + (3,))
    N = np.zeros(T.shape + (3,))
    for c in range(T.shape[0]):
        for r in range(T.shape[1]):
            P[c, r], N[c, r] = space.PN(T[c, r], Sg[c, r])
    return P, N


LP, LN = eval_grid(SL, LT, LS)
# junction row: where the lower body's top ends on the greenhouse base, snap that row onto the G1 v02 base line (the
# master's base was solved on a 3 mm raster of the lower body and sits up to about a centimetre off the round at the tail)
SNAP = []
for c in range(LT.shape[0]):
    sd = LSD[c]
    if abs(sd["s_top"] - sd["s_gb"]) > 1e-9:
        continue
    r_top = int(np.argmax(LS[c] >= sd["s_top"] - 1e-9))
    p = LP[c, r_top]
    d = np.linalg.norm(GB_LINE[:, :2] - np.r_[abs(p[0]), p[1]][None], axis=1) + np.abs(GB_LINE[:, 2] - p[2])
    k = int(np.argmin(d))
    if d[k] < 0.02:
        q = GB_LINE[k].copy()
        q[0] = math.copysign(q[0], p[0]) if p[0] != 0 else q[0]
        SNAP.append(float(np.linalg.norm(q - p)))
        LP[c, r_top:] = q
print(f"  junction row snapped on {len(SNAP)} columns, max {max(SNAP) * 1000 if SNAP else 0:.1f} mm, median {np.median(SNAP) * 1000 if SNAP else 0:.1f} mm")
GP, GN = eval_grid(SG, GT, GS_)
print(f"  grids evaluated ({time.time() - t0:.1f} s)", flush=True)


# ------------------------------------------------------------------ cell assignment
def g_panel_above(x, y):
    """Greenhouse panel whose base is nearest the plan point (for the belt junction)."""
    d = (GP[:, 0, 0] - abs(x)) ** 2 + (GP[:, 0, 1] - y) ** 2
    c = int(np.argmin(d))
    return G_panel(GT[c, 0], 1e-4, GSD[c])


_JC = [c for c in range(LP.shape[0]) if abs(LSD[c]["s_top"] - LSD[c]["s_gb"]) < 1e-9]  # L columns ending on the G base
_JTOP = np.array([LP[c, int(np.argmax(LS[c] >= LSD[c]["s_top"] - 1e-9))] for c in _JC])


def l_panel_below(x, y):
    """Lower-body panel whose top ends on the greenhouse base at this plan point; None where no L column ends there
    (the windscreen base sits on the cowl strip, a plan patch)."""
    d = (_JTOP[:, 0] - abs(x)) ** 2 + (_JTOP[:, 1] - y) ** 2
    k = int(np.argmin(d))
    if d[k] > 0.03 ** 2:
        return None
    c = _JC[k]
    return L_panel(LT[c, -1], LSD[c]["s_top"] - 1e-4, {**LSD[c]})


def assign(space_kind, T, Sg, SD, Pg):
    nc, nr = T.shape
    lab = np.full((nc - 1, nr - 1), None, dtype=object)
    gapm = np.zeros((nc - 1, nr - 1), bool)
    pf = L_panel if space_kind == "L" else G_panel
    for c in range(nc - 1):
        # seam levels of the cell: the mean of its two columns' (the cell's nodes sit on each column's own levels, so a
        # seam band's cells are centred on the mean level even where the level changes quickly between columns)
        sd = {k: 0.5 * (SD[c][k] + SD[c + 1][k]) for k in SD[c]}
        sd["s_bot"] = min(SD[c]["s_bot"], SD[c + 1]["s_bot"])
        sd["s_top"] = max(SD[c]["s_top"], SD[c + 1]["s_top"])
        for r in range(nr - 1):
            q = [(c, r), (c + 1, r), (c + 1, r + 1), (c, r + 1)]
            tc = np.mean([T[i, j] for i, j in q])
            sc = np.mean([Sg[i, j] for i, j in q])
            if abs(Sg[c, r + 1] - Sg[c, r]) < 1e-9 and abs(Sg[c + 1, r + 1] - Sg[c + 1, r]) < 1e-9:
                continue  # collapsed rows
            p = pf(tc, sc, sd)
            if p is None:
                continue
            # gap strip: the panel changes within E of the centre (along t or s)
            nb = [pf(tc - E * 0.999, sc, sd), pf(tc + E * 0.999, sc, sd), pf(tc, sc - E * 0.999, sd), pf(tc, sc + E * 0.999, sd)]
            if any(q_ is not None and q_ != p for q_ in nb):
                gapm[c, r] = True
                continue
            if p.startswith("hole"):
                gapm[c, r] = True
                continue
            lab[c, r] = p
    return lab, gapm


LSD2 = []
for c, sd in enumerate(LSD):
    LSD2.append(sd)
L_LAB, L_GAP = assign("L", LT, LS, LSD2, LP)
G_LAB, G_GAP = assign("G", GT, GS_, GSD, GP)
# belt junction: across different objects (not both fixed body) the strip next to the junction is a gap
for c in range(L_LAB.shape[0]):
    for r in range(L_LAB.shape[1]):
        p = L_LAB[c, r]
        if p in (None, "bonnet", "front_panel", "fender"):
            continue
        if LS[c, r + 1] > LSD[c]["s_gb"] - E + 1e-9 and LSD[c]["s_top"] >= LSD[c]["s_gb"] - 1e-9:
            x, y = LP[c, r + 1, 0], LP[c, r + 1, 1]
            g = g_panel_above(x, y)
            if g is not None and not g.startswith("hole") and OBJ[g] != OBJ[p] and not {OBJ[g], OBJ[p]} <= BODY_JOIN:
                L_LAB[c, r] = None
                L_GAP[c, r] = True
for c in range(G_LAB.shape[0]):
    for r in range(G_LAB.shape[1]):
        p = G_LAB[c, r]
        if p is None or GS_[c, r] > E - 1e-9:
            continue
        x, y = GP[c, r, 0], GP[c, r, 1]
        lp = l_panel_below(x, y)
        if lp is not None and OBJ[lp] != OBJ[p] and not ({OBJ[lp], OBJ[p]} <= BODY_JOIN or OBJ[lp] in ("Bonnet",)):
            G_LAB[c, r] = None
            G_GAP[c, r] = True
print(f"  cells assigned ({time.time() - t0:.1f} s): L {dict((k, int((L_LAB == k).sum())) for k in set(L_LAB.ravel()) if k)}; "
      f"G {dict((k, int((G_LAB == k).sum())) for k in set(G_LAB.ravel()) if k)}", flush=True)


# ------------------------------------------------------------------ panel meshes with chamfers and returns
CHAMFER_T = []  # local metres per unit of t at gap vertices (reported)


def panel_mesh(space, T, Sg, Pg, Ng, lab, name, open_bottom=True, gapm=None, top_gap=None):
    """Faces of the cells labelled `name`; boundary edges get a chamfer (to the true seam, half a gap from the cell
    edge's neighbour gap strip) and a return along -n; edges on the region's open lower boundary get the return only;
    edges on the mirror plane or the belt junction (no gap) get nothing."""
    nc, nr = Pg.shape[:2]
    m = lab == name
    if not m.any():
        return None
    vid = -np.ones((nc, nr), int)
    V, Fs, flag = [], [], []

    def v(c, r):
        if vid[c, r] < 0:
            vid[c, r] = len(V)
            V.append(Pg[c, r])
        return vid[c, r]
    for c in range(nc - 1):
        for r in range(nr - 1):
            if m[c, r]:
                Fs.append([v(c, r), v(c + 1, r), v(c + 1, r + 1), v(c, r + 1)])
                flag.append(0)
    # boundary edges of the cell set
    edges = {}
    for c in range(nc - 1):
        for r in range(nr - 1):
            if not m[c, r]:
                continue
            for (a, b, nbc, side) in (((c, r), (c + 1, r), (c, r - 1), "bottom"), ((c + 1, r), (c + 1, r + 1), (c + 1, r), "side"),
                                      ((c + 1, r + 1), (c, r + 1), (c, r + 1), "top"), ((c, r + 1), (c, r), (c - 1, r), "side")):
                ci, ri = nbc
                inside = 0 <= ci < nc - 1 and 0 <= ri < nr - 1 and m[ci, ri]
                if not inside:
                    edges[(a, b)] = (ci, ri, side)
    ring = {}

    def collapsed(ci, ri):
        return abs(Sg[ci, ri + 1] - Sg[ci, ri]) < 1e-9 and abs(Sg[ci + 1, ri + 1] - Sg[ci + 1, ri]) < 1e-9

    def kind_of(nb):
        ci, ri, side = nb
        if not (0 <= ci < nc - 1):
            return "none"  # mirror plane (front or rear centre)
        if side in ("top", "bottom"):  # look past zero-height (collapsed) rows to the real neighbour
            step = 1 if side == "top" else -1
            while 0 <= ri < nr - 1 and lab[ci, ri] is None and not gapm[ci, ri] and collapsed(ci, ri):
                ri += step
            # a region top that is a seam with a plan patch (the fender top at the bonnet shut line) is a gap edge
            if side == "top" and top_gap is not None and top_gap(ci) and (ri >= nr - 1 or (lab[ci, ri] is None and not gapm[ci, ri])):
                return "gap"
        if ri < 0:
            return "open" if open_bottom else "none"
        if ri >= nr - 1:
            return "none"  # region top: belt junction / plan patch join
        if lab[ci, ri] is None:
            if gapm[ci, ri]:
                return "gap"  # gap strip or window opening
            # outside the region (below the open lower edge or collapsed rows there): open edge; above: junction.
            # A bottom edge's outside neighbour is below, a top edge's above; a side edge's neighbour is below when its
            # centre lies in the lower half of its column's span.
            if side == "bottom":
                below = True
            elif side == "top":
                below = False
            else:
                sm = 0.25 * (Sg[ci, ri] + Sg[ci + 1, ri] + Sg[ci, ri + 1] + Sg[ci + 1, ri + 1])
                below = sm - Sg[ci, 0] < Sg[ci, -1] - sm
            return ("open" if open_bottom else "none") if below else "none"
        return "none"
    # per boundary vertex: direction toward the seam (sum over its boundary edges), kind
    vdir, vkind, ekind = {}, {}, {}
    vtan = {}  # per boundary vertex: 3D tangents of its column-type and row-type boundary edges (the seam directions)
    for (a, b), nb in edges.items():
        k = kind_of(nb)
        ekind[(a, b)] = k
        if k == "none":
            continue
        # outward param direction: from this cell toward the neighbour
        dt = np.sign(nb[0] - min(a[0], b[0])) if a[0] == b[0] else 0
        ds = 0
        if a[1] == b[1]:
            ds = 1 if nb[1] > min(a[1], b[1]) - 1 and nb[1] >= a[1] else -1
        if a[0] == b[0]:
            dt = 1 if nb[0] >= a[0] else -1
        e3 = Pg[b] - Pg[a]
        slot = 0 if a[0] == b[0] else 1
        for p in (a, b):
            d = vdir.get(p, np.zeros(2))
            vdir[p] = d + np.array([dt, ds])
            vkind[p] = "gap" if (vkind.get(p) == "gap" or k == "gap") else k
            tl = vtan.setdefault(p, [np.zeros(3), np.zeros(3)])
            tl[slot] = tl[slot] + (e3 if np.dot(tl[slot], e3) >= 0 else -e3)
    for p, d in vdir.items():
        c, r = p
        tq, sq = T[c, r], Sg[c, r]
        if vkind[p] == "gap":
            dd = np.sign(d)
            # the cell edge sits E (in the station parameter) off the seam; the chamfer bottom goes to GAP/2 (metres) off
            # it. Along s (arc length) that is a shift of CH; along t the station parameter is metres only at the
            # reference height, so the shift uses the local metres-per-unit of t
            # and measured square to the seam (the seam runs along the vertex's boundary edges), not along the grid line
            pa_, _ = space.PN(tq + 0.002, sq)
            pb_, _ = space.PN(tq - 0.002, sq)
            pc_, _ = space.PN(tq, sq + 0.002)
            pd_, _ = space.PN(tq, sq - 0.002)
            vt, vs = (pa_ - pb_) / 0.004, (pc_ - pd_) / 0.004

            def m_perp(v, tan):
                ln = np.linalg.norm(tan)
                if ln < 1e-9:
                    return float(np.linalg.norm(v))
                u = tan / ln
                return float(np.linalg.norm(v - np.dot(v, u) * u))
            sh_t, sh_s = 0.0, 0.0
            if dd[0] != 0:
                mp = m_perp(vt, vtan[p][0])
                sh_t = max(E - (GAP / 2) / max(mp, 1e-3), 0.0)
                CHAMFER_T.append(mp)
            if dd[1] != 0:
                mp = m_perp(vs, vtan[p][1])
                sh_s = max(E - (GAP / 2) / max(mp, 1e-3), 0.0)
                CHAMFER_T.append(mp)
            P0, n0 = space.PN(tq + dd[0] * sh_t, sq + dd[1] * sh_s)
            ring[p] = (len(V), len(V) + 1)
            V.append(P0 - CH * n0)
            V.append(P0 - (CH + RET) * n0)
        else:  # open lower edge: return only
            n0 = Ng[c, r]
            ring[p] = (vid[c, r], len(V))
            V.append(Pg[c, r] - RET * n0)
    for (a, b), nb in edges.items():
        if ekind[(a, b)] == "none" or a not in ring or b not in ring:
            continue
        ca, ra_ = ring[a]
        cb, rb_ = ring[b]
        if ca != vid[a] or cb != vid[b]:
            Fs.append([vid[b], vid[a], ca, cb])
            flag.append(1)
        Fs.append([cb, ca, ra_, rb_])
        flag.append(2)
    return np.array(V), Fs, np.array(flag)


# ------------------------------------------------------------------ plan patches: bonnet top and cowl strip
def H_plan(x, y):
    """Upper surface height of L at a plan point: the top surface, or the shoulder round where the point lies
    outboard of the side station's top tangent."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    z = B.z_top_L(x, y)
    for i in range(len(x)):
        if y[i] > SL.y0b + 1e-6:
            t = SL.t_y(y[i])
            pr_a, pr_b, w = SL.pair(t)
            xt = (1 - w) * pr_a["P"][int(np.searchsorted(pr_a["s"], pr_a["s_tt"])), 0] + w * pr_b["P"][int(np.searchsorted(pr_b["s"], pr_b["s_tt"])), 0]
            if x[i] > xt:
                zz = []
                for pr in (pr_a, pr_b):
                    i0 = int(np.searchsorted(pr["s"], pr["s_wt"]))
                    i1 = int(np.searchsorted(pr["s"], pr["s_tt"])) + 1
                    xs, zs = pr["P"][i0:i1, 0], pr["P"][i0:i1, 2]
                    o = np.argsort(xs)
                    zz.append(np.interp(x[i], xs[o], zs[o]))
                z[i] = (1 - w) * zz[0] + w * zz[1]
    return z


def plan_normal(x, y):
    e = 1e-3
    gx = (H_plan(x + e, y) - H_plan(x - e, y)) / (2 * e)
    gy = (H_plan(x, y + e) - H_plan(x, y - e)) / (2 * e)
    n = np.c_[-gx, -gy, np.ones_like(gx)]
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def resample(poly, n):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(poly, axis=0), axis=1))]
    u = np.linspace(0, d[-1], n)
    return np.c_[np.interp(u, d, poly[:, 0]), np.interp(u, d, poly[:, 1])]


def coons(F, K, Lc, Rc):
    nF, nS = len(F), len(Lc)
    out = np.zeros((nF, nS, 2))
    for i in range(nF):
        u = i / (nF - 1)
        for j in range(nS):
            v = j / (nS - 1)
            out[i, j] = ((1 - v) * F[i] + v * K[i] + (1 - u) * Lc[j] + u * Rc[j]
                         - ((1 - u) * (1 - v) * F[0] + u * (1 - v) * F[-1] + (1 - u) * v * K[0] + u * v * K[-1]))
    return out


def plan_patch_mesh(grid2, rings):
    """grid2: (nF, nS, 2) plan nodes; rings: dict side -> 'gap'/'none' with side keys 'F','K','L','R' and the true-seam
    plan offset direction for each ringed side (unit 2D vector per node)."""
    nF, nS = grid2.shape[:2]
    P = np.c_[grid2.reshape(-1, 2), H_plan(grid2[..., 0].ravel(), grid2[..., 1].ravel())].reshape(nF, nS, 3)
    V = list(P.reshape(-1, 3))
    Fs, flag = [], []

    def vid(i, j):
        return i * nS + j
    for i in range(nF - 1):
        for j in range(nS - 1):
            Fs.append([vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)])
            flag.append(0)
    side_nodes = {"F": [(i, 0) for i in range(nF)], "K": [(i, nS - 1) for i in range(nF)],
                  "L": [(0, j) for j in range(nS)], "R": [(nF - 1, j) for j in range(nS)]}
    for side, (kind, dirs) in rings.items():
        if kind != "gap":
            continue
        nodes = side_nodes[side]
        rid = []
        for (i, j), d in zip(nodes, dirs):
            q = grid2[i, j] + CH * np.asarray(d)
            z = H_plan(np.array([q[0]]), np.array([q[1]]))[0]
            n0 = plan_normal(np.array([q[0]]), np.array([q[1]]))[0]
            P0 = np.array([q[0], q[1], z])
            rid.append((len(V), len(V) + 1))
            V.append(P0 - CH * n0)
            V.append(P0 - (CH + RET) * n0)
        for k in range(len(nodes) - 1):
            a, b = vid(*nodes[k]), vid(*nodes[k + 1])
            Fs.append([b, a, rid[k][0], rid[k + 1][0]])
            flag.append(1)
            Fs.append([rid[k + 1][0], rid[k][0], rid[k][1], rid[k + 1][1]])
            flag.append(2)
    return np.array(V), Fs, np.array(flag), P


def offset_curve(poly, dist, toward):
    """Offset a plan polyline by dist along its normal pointing toward `toward` (a 2D point side test)."""
    out = []
    for k in range(len(poly)):
        a = poly[max(k - 1, 0)]
        b = poly[min(k + 1, len(poly) - 1)]
        tng = (b - a) / (np.linalg.norm(b - a) + 1e-15)
        nrm = np.array([-tng[1], tng[0]])
        if np.dot(toward - poly[k], nrm) < 0:
            nrm = -nrm
        out.append(poly[k] + dist * nrm)
    return np.array(out)


# bonnet band columns (L grid, front stations up to the corner end): its top row and its right column above the shut line
band_cols = [c for c in range(LT.shape[0]) if LT[c, 0] < T_CE - E + 1e-6]
c_last = band_cols[-1]
top_nodes = []
for c in band_cols:
    r = int(np.argmax(LS[c] >= LSD[c]["s_top"] - 1e-9))
    top_nodes.append(LP[c, r, :2])
# right column: from the top tangent down to the bonnet edge of the shut seam (s_shB) on that column
rc_nodes = [LP[c_last, r, :2] for r in range(LT.shape[1]) if LSD[c_last]["s_shB"] - 1e-9 <= LS[c_last, r] <= LSD[c_last]["s_top"] + 1e-9]
rc_nodes = rc_nodes[::-1][1:]
F_front = np.array(top_nodes + rc_nodes)
# windscreen base (G base line of the front stations up to the shut x), cowl seam lines
g_front = [c for c in range(GT.shape[0]) if GP[c, 0, 0] <= SHUT - E + 1e-6 and GT[c, 0] < G_A]
base_line = np.array([GP[c, 0, :2] for c in g_front])
base_line = base_line[np.argsort(base_line[:, 0])]
ahead = np.array([0.3, -2.0])
cowl_true = offset_curve(base_line, COWL_W, ahead)
cowl_bon = offset_curve(base_line, COWL_W + E, ahead)       # bonnet surface edge
cowl_cw = offset_curve(base_line, COWL_W - E, ahead)        # cowl strip surface edge
cowl_bon = cowl_bon[cowl_bon[:, 0] <= SHUT - E + 1e-6]
cowl_cw = cowl_cw[cowl_cw[:, 0] <= SHUT - E + 1e-6]
nF = len(F_front)
K_bon = resample(cowl_bon, nF)
nS = max(4, int(math.ceil(abs(K_bon[0, 1] - F_front[0, 1]) / STEP)) + 1)
Lc = np.c_[np.zeros(nS), np.linspace(F_front[0, 1], K_bon[0, 1], nS)]
Rc = np.c_[np.full(nS, SHUT - E), np.linspace(F_front[-1, 1], K_bon[-1, 1], nS)]
Rc[0] = F_front[-1]
BP_grid = coons(F_front, K_bon, Lc, Rc)
BP = plan_patch_mesh(BP_grid, {"K": ("gap", [np.array([0.0, 1.0])] * nF), "R": ("gap", [np.array([1.0, 0.0])] * nS)})
nFc = max(4, int(math.ceil(SHUT / STEP)) + 1)
K_cw = resample(cowl_cw, nFc)
K_base = resample(base_line[base_line[:, 0] <= SHUT - E + 1e-6], nFc)
nSc = 3
CW_grid = coons(K_cw, K_base, np.c_[np.zeros(nSc), np.linspace(K_cw[0, 1], K_base[0, 1], nSc)],
                np.c_[np.full(nSc, K_cw[-1, 0]), np.linspace(K_cw[-1, 1], K_base[-1, 1], nSc)])
CW = plan_patch_mesh(CW_grid, {"F": ("gap", [np.array([0.0, -1.0])] * nFc), "R": ("gap", [np.array([1.0, 0.0])] * nSc)})
print(f"  plan patches: bonnet top {BP_grid.shape[:2]}, cowl {CW_grid.shape[:2]} ({time.time() - t0:.1f} s)", flush=True)


# ------------------------------------------------------------------ glass panes
def pane(space, t0_, t1_, sB_fn, sT_fn, mirror_edge=None):
    """Pane over t in [t0_, t1_] (true opening edges minus half a gap), s from sB_fn(t) to sT_fn(t); inset GLASS_INSET
    along -n; edge round of radius CH turning the edge inward; mirror_edge: 't1' when the pane continues across x = 0."""
    nc = max(3, int(math.ceil((t1_ - t0_) / STEP)) + 1)
    ts = np.linspace(t0_, t1_, nc)
    rows = []
    for t in ts:
        sb, st_ = sB_fn(t), sT_fn(t)
        nr = max(3, int(math.ceil((st_ - sb) / STEP)) + 1)
        rows.append((sb, st_))
    nr = max(3, int(max(math.ceil((b - a) / STEP) for a, b in rows)) + 1)
    V = []
    grid = np.zeros((nc, nr), int)

    def add(t, s, inset):
        p, n = space.PN(t, s)
        V.append(p - (GLASS_INSET + inset) * n)
        return len(V) - 1
    # pull the pane surface back by CH from each edge, then a quarter round (3 rows) to the true pane edge
    for i, t in enumerate(ts):
        sb, st_ = rows[i]
        tt = t
        if i == 0:
            tt = t + CH
        if i == nc - 1 and mirror_edge != "t1":
            tt = t - CH
        for j in range(nr):
            s = sb + CH + (st_ - sb - 2 * CH) * j / (nr - 1)
            grid[i, j] = add(tt, s, 0.0)
    Fs, flag = [], []
    for i in range(nc - 1):
        for j in range(nr - 1):
            Fs.append([grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]])
            flag.append(0)
    # edge rounds: bottom, top, left (and right unless mirrored)
    angs = [math.radians(a) for a in (30, 60, 90)]

    def round_row(nodes_ts, dt, ds):
        prev = [grid[i, j] for (i, j) in nodes_ts]
        for a in angs:
            cur = []
            for (i, j) in nodes_ts:
                t = ts[i] + (CH if i == 0 else (-CH if (i == nc - 1 and mirror_edge != "t1") else 0.0))
                sb, st_ = rows[i]
                s = sb + CH + (st_ - sb - 2 * CH) * j / (nr - 1)
                p, n = space.PN(t + dt * CH * math.sin(a), s + ds * CH * math.sin(a))
                V.append(p - (GLASS_INSET + CH * (1 - math.cos(a))) * n)
                cur.append(len(V) - 1)
            for k in range(len(nodes_ts) - 1):
                Fs.append([prev[k], prev[k + 1], cur[k + 1], cur[k]])
                flag.append(1)
            prev = cur
    round_row([(i, 0) for i in range(nc)], 0, -1)
    round_row([(i, nr - 1) for i in range(nc)], 0, 1)
    round_row([(0, j) for j in range(nr)], -1, 0)
    if mirror_edge != "t1":
        round_row([(nc - 1, j) for j in range(nr)], 1, 0)
    return np.array(V), Fs, np.array(flag)


def hb(t):
    return SG.s_of_z(t, SG.scalar(t, "z_wt") - B.HEADER)


PANES = {
    "Glass_Windscreen": pane(SG, 0.0, G_S0E - HALF, lambda t: B.GLASS_BELT + HALF, lambda t: hb(t) - HALF, mirror_edge="t0"),
    "Glass_FrontDoor": pane(SG, G_A + FW + HALF, G_B - FW - HALF, lambda t: FW + HALF, lambda t: hb(t) - FW - HALF),
    "Glass_RearDoor": pane(SG, G_B + FW + HALF, G_C - FW - HALF, lambda t: FW + HALF, lambda t: hb(t) - FW - HALF),
    "Glass_Quarter": pane(SG, G_QG0 + HALF, G_D - HALF, lambda t: FW + HALF, lambda t: hb(t) - FW - HALF),
    "Glass_RearScreen": pane(SG, G_C3E + FW + HALF, SG.t_end, lambda t: FW + HALF, lambda t: SG.scalar(t, "s_wt") - FW - HALF,
                             mirror_edge="t1"),
}
print(f"  glass panes built ({time.time() - t0:.1f} s)", flush=True)

# ------------------------------------------------------------------ assemble objects
def _shut_top(c):
    """L column whose region top is the bonnet shut line (fender columns)."""
    return LT[c, 0] >= T_CE - 1e-9 and abs(LSD[c]["s_top"] - LSD[c]["s_shF"]) < 1e-9


PANELS = {}
for name in ("front_panel", "bonnet", "fender", "rocker", "front_door", "rear_door", "quarter", "valance", "tailgate", "hatch"):
    m = panel_mesh(SL, LT, LS, LP, LN, L_LAB, name, gapm=L_GAP, top_gap=_shut_top)
    if m is not None:
        PANELS.setdefault(OBJ[name], []).append(("L", m))
for name in ("cabin", "front_door", "rear_door", "quarter", "hatch"):
    m = panel_mesh(SG, GT, GS_, GP, GN, G_LAB, name, open_bottom=False, gapm=G_GAP)
    if m is not None:
        PANELS.setdefault(OBJ[name], []).append(("G", m))
PANELS.setdefault("Bonnet", []).append(("P", BP[:3]))
PANELS.setdefault("Cowl", []).append(("P", CW[:3]))
_ct = np.array(CHAMFER_T)
print(f"  chamfer: metres square to the seam per grid unit at gap vertices: min {_ct.min():.3f}, median {np.median(_ct):.3f}, max {_ct.max():.3f}; "
      f"shift clamped at 0 on {int(np.sum(E * _ct < GAP / 2))}", flush=True)
MIRRORED_SINGLE = {"FrontPanel", "Bonnet", "Cowl", "Valance", "LowerTailgate", "UpperHatch", "CabinFrame", "Glass_Windscreen",
                   "Glass_RearScreen"}


def weld(V, Fs, tol=1e-6):
    key = np.round(np.asarray(V) / tol).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    Vw = np.asarray(V)[first]
    F2, keep = [], []
    for k, f in enumerate(Fs):
        u = []
        for q in f:
            if inv[q] not in u:
                u.append(int(inv[q]))
        if len(u) >= 3:
            F2.append(u)
            keep.append(k)
    return Vw, F2, keep


def combine(parts):
    V, Fs, fl = [], [], []
    for _, (v, f, flag) in parts:
        off = len(V)
        V.extend(list(v))
        Fs.extend([[q + off for q in face] for face in f])
        fl.extend(list(flag))
    return np.array(V), Fs, np.array(fl)


def mirror(V, Fs):
    Vm = np.asarray(V) * np.array([-1, 1, 1])
    return Vm, [list(reversed(f)) for f in Fs]


OBJECTS = {}
for name, parts in PANELS.items():
    V, Fs, fl = combine(parts)
    if name in MIRRORED_SINGLE:
        Vm, Fm = mirror(V, Fs)
        V2 = np.vstack([V, Vm])
        F2 = Fs + [[q + len(V) for q in f] for f in Fm]
        fl2 = np.r_[fl, fl]
        Vw, Fw, keep = weld(V2, F2)
        OBJECTS[name] = (Vw, Fw, fl2[keep])
    else:
        Vw, Fw, keep = weld(V, Fs)
        OBJECTS[name + "_L"] = (Vw, Fw, fl[keep])
        Vm, Fm = mirror(Vw, Fw)
        OBJECTS[name + "_R"] = (Vm, Fm, fl[keep])
for name, (V, Fs, fl) in PANES.items():
    if name in MIRRORED_SINGLE:
        Vm, Fm = mirror(V, Fs)
        Vw, Fw, keep = weld(np.vstack([V, Vm]), Fs + [[q + len(V) for q in f] for f in Fm])
        OBJECTS[name] = (Vw, Fw, np.r_[fl, fl][keep])
    else:
        Vw, Fw, keep = weld(V, Fs)
        OBJECTS[name + "_L"] = (Vw, Fw, fl[keep])
        Vm, Fm = mirror(Vw, Fw)
        OBJECTS[name + "_R"] = (Vm, Fm, fl[keep])
print("objects: " + ", ".join(f"{k} {len(v[1])}" for k, v in OBJECTS.items()), flush=True)

# ------------------------------------------------------------------ hinges (LAY-12) for the opened picture
hinges = {}
fd = OBJECTS["FrontDoor_L"][0]
fd_s = fd[(fd[:, 2] > Z_DB) & (fd[:, 2] < B.H_BELT)]
y_hinge = float(fd_s[:, 1].min())
hinges["FrontDoor_L"] = {"origin": [B.XB, y_hinge, 0.8], "axis": [0, 0, 1], "deg": -50.0}
hinges["FrontDoor_R"] = {"origin": [-B.XB, y_hinge, 0.8], "axis": [0, 0, 1], "deg": 50.0}
bon = OBJECTS["Bonnet"][0]
k_rear = int(np.argmax(bon[:, 1]))  # the rear edge bows back to its ends (the cowl follows the bowed windscreen base):
y_rear, z_rear = float(bon[k_rear, 1]), float(bon[k_rear, 2])  # the axis through its rear-most points keeps it all ahead
hinges["Bonnet"] = {"origin": [0.0, y_rear, z_rear], "axis": [1, 0, 0], "deg": -35.0}
tg = OBJECTS["LowerTailgate"][0]
z_tg = float(tg[:, 2].min())
y_tg = float(tg[tg[:, 2] < z_tg + 0.02, 1].max())
hinges["LowerTailgate"] = {"origin": [0.0, y_tg, z_tg], "axis": [1, 0, 0], "deg": -80.0}  # top swings rearward and down
ht = OBJECTS["UpperHatch"][0]
z_ht = float(ht[:, 2].max())
y_ht = float(ht[ht[:, 2] > z_ht - 0.02, 1].min())
hinges["UpperHatch"] = {"origin": [0.0, y_ht, z_ht], "axis": [1, 0, 0], "deg": 60.0}  # bottom swings rearward and up
FOLLOW = {"Glass_FrontDoor_L": "FrontDoor_L", "Glass_FrontDoor_R": "FrontDoor_R", "Glass_RearScreen": "UpperHatch"}

os.makedirs(OUT, exist_ok=True)
pack = {}
for k, (V, Fs, fl) in OBJECTS.items():
    mx = max(len(f) for f in Fs)
    pack[k + "__v"] = np.asarray(V)
    pack[k + "__f"] = np.array([list(f) + [-1] * (mx - len(f)) for f in Fs])
    pack[k + "__flag"] = np.asarray(fl)
np.savez_compressed(os.path.join(OUT, "panels.npz"), **pack)
seams_side = {}
SEAM_INFO = {"YA": YA, "zA": zA, "Y_TEB": Y_TEB, "Z_TEB": Z_TEB, "LE_RAKE": LE_RAKE, "TE_RAKE": TE_RAKE, "YB": YB, "SHUT": SHUT,
             "Z_DB": Z_DB, "Z_TGB": Z_TGB, "SPLIT": SPLIT, "TG_HW": TG_HW, "Y_X": Y_X, "GAP": GAP, "CH": CH, "RET": RET, "FW": FW}
with open(os.path.join(OUT, "g2-build.json"), "w", encoding="utf-8") as f:
    json.dump({"objects": {k: {"vertices": int(len(v[0])), "faces": int(len(v[1]))} for k, v in OBJECTS.items()},
               "hinges": hinges, "follow": FOLLOW, "seams": SEAM_INFO, "provenance": S.prov,
               "grids": {"L": list(LT.shape), "G": list(GT.shape), "bonnet_top": list(BP_grid.shape[:2]), "cowl": list(CW_grid.shape[:2])}},
              f, indent=1, default=float)
print(f"G2 panels built in {time.time() - t0:.1f} s")
