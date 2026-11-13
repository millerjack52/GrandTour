"""G1 (docs/CAR_GRAMMAR_PLAN.md section 6, 6a-6g): the Land Cruiser 80 shell from rules.

Lower body L and greenhouse G are lofts of rounded rectangles over height (stations follow the outline parameter at
every height); the round between wall and top is a true arc in the station plane through the wall tangent point
(body_builder's rolling-ball construction, bt1_fields.Station.round / arc). Bonnet plate, belt ledge and roof plate
are analytic. Every design number is read through g1_spec (grammar.py); the JSON lists the row of each.

Writes Art/Export/VehicleTools/landcruiser-grammar-g1-v01/: shell-mesh.npz, g1-build.json, debug/plan.png.
System Python (numpy, PIL)."""
import json
import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
ROOT = os.path.normpath(os.path.join(LIB, "..", ".."))
BB = os.path.join(ROOT, "Art", "VehicleTools", "body_builder")
sys.path.insert(0, HERE)
sys.path.insert(0, BB)
from g1_spec import Spec  # noqa: E402
import bt1_fields as F  # noqa: E402  (Station.round / Station.arc / seg_intersections: rolling-ball rounds)

OUT = os.path.join(ROOT, "Art", "Export", "VehicleTools", "landcruiser-grammar-" + "g1-v02")
DBG = os.path.join(OUT, "debug")

# sampling only (plan 6f), not design values
STEP = 0.03          # stations along the outline, rows up the walls and across tops
N_ARC = 12           # rows across each round
DZ = 0.002           # wall section sampling for the round solve
DR = 0.002           # top section sampling for the round solve
D_ORG = 1.2          # station origin set back inside the outline (m)
WELD = 1e-6
PASS_M, PASS_DEG = 0.005, 0.5

t0 = time.time()
S = Spec()
rad = math.radians

# ------------------------------------------------------------------ numbers (all through the library)
WB = S.hp("WB")
TYRE_R = S.hp("TYRE_R")
HUB_Z = S.hp("TYRE_R", "hub height (owner: hub at TYRE_R)")
TYRE_W = S.hp("TYRE_W", "wheel width")
TRACK_F, TRACK_R = S.hp("TRACK_F"), S.hp("TRACK_R")
OH_F, OH_R = S.hp("OH_F"), S.hp("OH_R")
W_BODY, W_FLARE, W_ROOF = S.hp("W_BODY"), S.hp("W_FLARE"), S.hp("W_ROOF")
H_SILL, H_BELT, H_COWL = S.hp("H_SILL"), S.hp("H_BELT"), S.hp("H_COWL")
H_BF, H_ROOF = S.hp("H_BONNET_F"), S.hp("H_ROOF")
H_BT, H_BB = S.hp("H_BUMPER_T"), S.hp("H_BUMPER_B")
Y_COWL, Y_AB = S.hp("Y_COWL"), S.hp("Y_A_BASE")
Y_RF, Y_RR, Y_RSB = S.hp("Y_ROOF_F"), S.hp("Y_ROOF_R"), S.hp("Y_RS_BASE")
Y_B, Y_C, Y_D = S.hp("Y_B"), S.hp("Y_C"), S.hp("Y_D")
RAKE_WS, RAKE_RS = S.hp("RAKE_WS"), S.hp("RAKE_RS")
RAKE_FRONT, RAKE_REAR = S.hp("RAKE_FRONT"), S.hp("RAKE_REAR")
TUMB_SHEET = S.hp("TUMBLEHOME", "tumblehome on the sheet (reference only)")
ARCH_R, ARCH_FLAT = S.hp("ARCH_R"), S.hp("ARCH_TOP_FLAT")
BE_Y = S.con("BONNET_EDGE_Y")
RSB_Z = S.con("RS_BASE_Z")
GLASS_BELT = S.con("GLASS_BELT_BAND")
BOW_BASE = S.rule("GH-01", "base", use="windscreen plan bow at the glass base (belt height)")
BOW_TOP = S.rule("GH-01", "top", use="windscreen plan bow at the roof round tangent")
REAR_BOW = S.con("REAR_SCREEN_BOW", "rear screen plan bow (constant)")
BELT_Y0 = S.con("BELT_ANCHOR_Y", "belt ledge anchor (H_BELT here)")
TUCK_R = S.con("TUCK_ROUND", "sill tuck edge round")
A_WIDTH = S.rule("GH-03", "width", use="A-pillar width along the side")
CROWN_X = S.rule("GH-04", idx=0, use="roof crown across")
CROWN_Y = S.rule("GH-04", idx=1, use="roof crown along")
R_RAIL = S.rule("GH-05", idx=0, use="roof rail round")
R_HEAD_F = S.rule("GH-06", idx=0, use="roof front round")
R_HEAD_R = S.rule("GH-06", idx=1, use="roof rear round")
PIL_B = S.rule("GH-09", "B", use="B pillar width")
PIL_C = S.rule("GH-09", "C", use="C pillar width")
PIL_D = S.rule("GH-09", "D", use="D pillar width")
BELT_RISE = S.rule("GH-10", "rise", use="belt rise")
BELT_OVER = S.rule("GH-10", "over", use="belt rise length")
HEADER = S.rule("GH-11", idx=0, use="glass header band")
RC_A = S.rule("GH-13", idx=0, use="greenhouse A-pillar plan corner")
RC_GR = S.rule("GH-14", idx=0, use="greenhouse rear plan corner")
R_BELT = S.rule("BS-02", "r", use="lower body wall-to-top round")
LEDGE = S.rule("BS-02", "ledge", use="belt ledge")
TUCK_H = S.rule("BS-03", idx=0, use="sill tuck height")
TUCK_A = S.rule("BS-03", idx=1, use="sill tuck angle")
CROWN_B = S.rule("FR-02", "crown", use="bonnet crown at the leading edge")
R_NOSE = S.rule("FR-03", "edge", use="bonnet leading edge round")
RC_LF = S.rule("FR-03", "corner", use="lower body front plan corner")
RC_LR = S.rule("RR-02", idx=1, use="lower body rear plan corner")
BF_SIDE = S.rule("FR-04", "side", use="front bumper side length")
BF_EDGE = S.rule("FR-04", "edge", use="bumper edge round")
BF_CORNER = S.rule("FR-04", "corner", use="bumper plan corner")
BR_SIDE = S.rule("RR-03", "side", use="rear bumper side length")
BR_EDGE = S.rule("RR-03", "edge", use="rear bumper edge round")
BR_CORNER = S.rule("RR-03", "corner", use="rear bumper plan corner")
MARGIN = S.rule("BS-05", "margin", use="arch margin (G0, for the record)")

XB = W_BODY / 2
XG0 = XB - R_BELT - LEDGE  # glass base: a flat ledge of LEDGE between the shoulder round's tangent and the glass (plan 7)
Y_HF, Y_HR = -WB / 2, WB / 2
Y_BUMP_F = -(WB / 2 + OH_F)
Y_BUMP_R = WB / 2 + OH_R
S.prov["bumper half width"] = "W_FLARE / 2 (the sheet's front view shows the bumper bar as wide as the flares)"


# ------------------------------------------------------------------ outline (half, x >= 0) of a lofted rounded rectangle
def quad_roots(a, b, c):
    a, b, c = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float), np.asarray(c, float))
    lin = np.abs(a) < 1e-12
    with np.errstate(invalid="ignore", divide="ignore"):
        disc = b * b - 4 * a * c
        sq = np.sqrt(np.where(disc >= 0, disc, np.nan))
        r1 = np.where(lin, -c / b, (-b + sq) / (2 * a))
        r2 = np.where(lin, np.nan, (-b - sq) / (2 * a))
    return r1, r2


class Outline:
    """Segments: 0 front edge (x 0 -> corner tangent; parabola for a plan bow), 1 front corner arc, 2 side,
    3 rear corner arc, 4 rear edge (corner tangent -> x 0). A station is (segment, parameter); on the side the
    parameter is a reference Y mapped per height (side_map) so that the middle of the side keeps constant Y."""

    def __init__(self, W, YF, YR, bowF, bowR, rcf, rcr):
        """YF / YR: the front / rear edge at the sides (x = W); bowF / bowR: plan sag of the middle, functions of z."""
        self.W, self.YF, self.YR, self.bowF, self.bowR, self.rcf, self.rcr = W, YF, YR, bowF, bowR, rcf, rcr
        self.smap = None

    def g(self, z):
        z = np.atleast_1d(np.asarray(z, float))
        W = self.W(z)
        bf, br = self.bowF(z), self.bowR(z)
        p2 = bf / W ** 2
        p2r = br / W ** 2
        p0f = self.YF(z) - bf
        x0 = W - self.rcf
        s = 2 * p2 * x0
        q = np.sqrt(1 + s * s)
        cfy = p0f + p2 * x0 ** 2 + self.rcf * q
        tfx = x0 + self.rcf * s / q
        tfy = cfy - self.rcf / q
        p0r = self.YR(z) + br
        x0r = W - self.rcr
        sr = -2 * p2r * x0r
        qr = np.sqrt(1 + sr * sr)
        cry = p0r - p2r * x0r ** 2 - self.rcr * qr
        trx = x0r - self.rcr * sr / qr
        tr_y = cry + self.rcr / qr
        return {"W": W, "p2": p2, "p2r": p2r, "p0f": p0f, "cfx": x0, "cfy": cfy, "tfx": tfx, "af": np.arctan2(tfy - cfy, tfx - x0),
                "p0r": p0r, "crx": x0r, "cry": cry, "trx": trx, "ar": np.arctan2(tr_y - cry, trx - x0r)}

    def side_map(self, z_ref, a_off, p0, p1):
        g = self.g(z_ref)
        self.smap = (float(g["cfy"][0]), float(g["cry"][0]), a_off, p0, p1)

    def side_y(self, yref, y0, y1):
        y0b, y1b, a, p0, p1 = self.smap
        if yref <= y0b + a:
            return y0 + (yref - y0b)
        if yref < p0:
            t = (yref - (y0b + a)) / (p0 - (y0b + a))
            return (y0 + a) + t * (p0 - (y0 + a))
        if yref <= p1:
            return np.full_like(y0, yref)
        t = (yref - p1) / (y1b - p1)
        return p1 + t * (y1 - p1)

    def point(self, st, z):
        seg, p = st
        G = self.g(z)
        if seg == 0:
            x = p * G["tfx"]
            y = G["p0f"] + G["p2"] * x * x
        elif seg == 1:
            a = G["af"] * (1 - p)
            x, y = G["cfx"] + self.rcf * np.cos(a), G["cfy"] + self.rcf * np.sin(a)
        elif seg == 2:
            x, y = G["W"], self.side_y(p, G["cfy"], G["cry"])
        elif seg == 3:
            a = G["ar"] * p
            x, y = G["crx"] + self.rcr * np.cos(a), G["cry"] + self.rcr * np.sin(a)
        else:
            x = (1 - p) * G["trx"]
            y = G["p0r"] - G["p2r"] * x * x
        return np.stack([x, y], -1)

    def normal(self, st, z):
        seg, p = st
        G = self.g(z)
        if seg == 0:
            x = p * G["tfx"]
            s = 2 * G["p2"] * x
            n = np.stack([s, -np.ones_like(s)], -1)
        elif seg == 1:
            a = G["af"] * (1 - p)
            n = np.stack([np.cos(a), np.sin(a)], -1)
        elif seg == 2:
            n = np.stack([np.ones_like(G["W"]), np.zeros_like(G["W"])], -1)
        elif seg == 3:
            a = G["ar"] * p
            n = np.stack([np.cos(a), np.sin(a)], -1)
        else:
            x = (1 - p) * G["trx"]
            n = np.stack([2 * G["p2r"] * x, np.ones_like(x)], -1)
        return n / np.linalg.norm(n, axis=-1, keepdims=True)

    def ray_hit(self, O, n, z):
        """Distance along the horizontal ray O + t n to the outline at each height z (outermost valid hit)."""
        G = self.g(z)
        Ox, Oy = O
        nx, ny = n
        best = np.full(len(np.atleast_1d(z)), np.nan)

        def take(t, ok):
            nonlocal best
            best = np.fmax(best, np.where(ok & (t > 0), t, np.nan))

        p2 = G["p2"]
        for t in quad_roots(p2 * nx * nx, 2 * p2 * Ox * nx - ny, p2 * Ox * Ox - Oy + G["p0f"]):
            take(t, np.abs(Ox + t * nx) <= G["tfx"] + 1e-9)
        for (cx, cy, r, sgn) in ((G["cfx"], G["cfy"], self.rcf, -1), (G["crx"], G["cry"], self.rcr, 1)):
            bq = nx * (Ox - cx) + ny * (Oy - cy)
            cq = (Ox - cx) ** 2 + (Oy - cy) ** 2 - r * r
            with np.errstate(invalid="ignore"):
                sq = np.sqrt(np.where(bq * bq - cq >= 0, bq * bq - cq, np.nan))
            for t in (-bq + sq, -bq - sq):
                dx, dy = Ox + t * nx - cx, Oy + t * ny - cy
                take(t, (dx >= -1e-9) & (sgn * dy >= -1e-9))
        if abs(nx) > 1e-12:
            t = (G["W"] - Ox) / nx
            y = Oy + t * ny
            take(t, (y >= G["cfy"] - 1e-9) & (y <= G["cry"] + 1e-9))
        p2 = G["p2r"]
        for t in quad_roots(p2 * nx * nx, 2 * p2 * Ox * nx + ny, p2 * Ox * Ox + Oy - G["p0r"]):
            take(t, np.abs(Ox + t * nx) <= G["trx"] + 1e-9)
        return best


def stations(outline, z_ref, extra_side=(), min_arc=10):
    """Stations ~STEP apart at z_ref: segment counts from lengths; side stations uniform in reference Y plus the
    given extra Y values (band edges, arch ends)."""
    G = outline.g(z_ref)
    out = []
    n0 = max(4, int(math.ceil(float(G["tfx"][0]) / STEP)))
    out += [(0, k / n0) for k in range(n0)]
    n1 = max(min_arc, int(math.ceil(abs(float(G["af"][0])) * outline.rcf / STEP)))
    out += [(1, k / n1) for k in range(n1)]
    y0, y1 = float(G["cfy"][0]), float(G["cry"][0])
    ys = list(np.linspace(y0, y1, int(math.ceil((y1 - y0) / STEP)) + 1))
    for e in extra_side:
        if y0 + 0.004 < e < y1 - 0.004:
            ys = [v for v in ys if abs(v - e) > 0.008] + [e]
    ys = sorted(ys)
    out += [(2, v) for v in ys[:-1]]
    n3 = max(min_arc, int(math.ceil(abs(float(G["ar"][0])) * outline.rcr / STEP)))
    out += [(3, k / n3) for k in range(n3)]
    n4 = max(4, int(math.ceil(float(G["trx"][0]) / STEP)))
    out += [(4, k / n4) for k in range(n4 + 1)]
    return out


# ------------------------------------------------------------------ lower body L (6a)
TUCK_ZC = H_SILL + TUCK_H
TUCK_T = TUCK_R * math.tan(rad(TUCK_A) / 2)        # tangent length of the tuck edge round
TUCK_Z1 = TUCK_ZC + TUCK_T                          # round meets the vertical side
TUCK_Z2 = TUCK_ZC - TUCK_T * math.cos(rad(TUCK_A))  # round meets the tucked strip


def L_W(z):
    z = np.asarray(z, float)
    w = XB - np.maximum(0.0, TUCK_ZC - z) * math.tan(rad(TUCK_A))
    inr = (z > TUCK_Z2) & (z < TUCK_Z1)
    wr = (XB - TUCK_R) + np.sqrt(np.maximum(TUCK_R ** 2 - (z - TUCK_Z1) ** 2, 0.0))
    return np.where(inr, wr, w)


def L_YF(z):
    return BE_Y + (z - H_BF) * math.tan(rad(RAKE_FRONT))  # RAKE_FRONT < 0: the top is forward


def L_YR(z):
    return Y_RSB - (z - RSB_Z) * math.tan(rad(RAKE_REAR))  # RAKE_REAR > 0: the top is forward


LO = Outline(L_W, L_YF, L_YR, lambda z: 0.0 * z, lambda z: 0.0 * z, RC_LF, RC_LR)


def zs_side(y):
    z_ab = ledge(Y_AB)  # the plate's side edge starts on the belt at the A-pillar foot
    return z_ab + (y - Y_AB) * (H_BF - z_ab) / (BE_Y - Y_AB)


def zs_centre(y):
    return H_COWL + (y - Y_COWL) * (H_BF + CROWN_B - H_COWL) / (BE_Y - Y_COWL)


def ledge(y):
    return H_BELT + BELT_RISE * (y - BELT_Y0) / BELT_OVER  # H_BELT at mid-doors (plan 7)


Y_PE = None  # set after G: start of the crown fade behind the A-pillar foot (G's front corner side tangent)
CROWN_FADE = 0.15  # construction length (not a design value): crown fades out under G behind its front corner


def z_top_L(x, y):
    """Bonnet plate ahead of the A-pillar foot; behind it the belt ledge, carrying the bonnet crown until G's
    front corner side tangent (inside G's footprint except a strip of the ledge)."""
    x = np.minimum(np.abs(np.asarray(x, float)), XB)
    y = np.asarray(y, float)
    cr = (zs_centre(y) - zs_side(y)) * (1 - (x / XB) ** 2)
    plate = zs_side(y) + cr
    # behind the A-pillar foot the crown rides on the ledge and fades out (smoothstep over CROWN_FADE) from G's front
    # corner side tangent rearward: inside G's footprint except the 3 cm ledge strip, which gets no step
    t = np.clip((y - Y_PE) / CROWN_FADE, 0.0, 1.0)
    fade = 1 - t * t * (3 - 2 * t)
    behind = ledge(y) + cr * fade
    return np.where(y <= Y_AB, plate, behind)


def arch_z(y):
    """Lower edge of L at Y on the sides: H_SILL, or the arch opening (ARCH_R about the hub, flat top)."""
    z = np.full_like(np.asarray(y, float), H_SILL)
    for yh in (Y_HF, Y_HR):
        d = np.abs(y - yh)
        inside = d < ARCH_R
        dd = np.maximum(d, ARCH_FLAT / 2)
        za = HUB_Z + np.sqrt(np.maximum(ARCH_R ** 2 - dd ** 2, 0.0))
        z = np.where(inside, np.maximum(z, za), z)
    return z


ARCH_END = math.sqrt(max(ARCH_R ** 2 - (H_SILL - HUB_Z) ** 2, 0.0))


# ------------------------------------------------------------------ round in a station plane (body_builder)
class PlaneStation(F.Station):
    """bt1_fields.Station with analytic wall and top sections instead of fitted fields."""

    def __init__(self, O, n, wr, wz, tr, tz, ztop_fn):
        self.s = 0.0
        self.O = (float(O[0]), float(O[1]))
        self.n = (float(n[0]), float(n[1]))
        self.wr, self.wz = wr, wz
        d = np.gradient(wr, wz)
        nrm = np.sqrt(1 + d ** 2)
        self.wn = np.stack([1 / nrm, -d / nrm], 1)
        self.tr, self.tz = tr, tz
        dt = np.gradient(tz, tr)
        nrm = np.sqrt(1 + dt ** 2)
        self.tn = np.stack([-dt / nrm, 1 / nrm], 1)
        f = wz - ztop_fn(self.O[0] + wr * self.n[0], self.O[1] + wr * self.n[1])
        sc = np.where((f[:-1] < 0) & (f[1:] >= 0))[0]
        if len(sc):
            i = sc[0]
            t = f[i] / (f[i] - f[i + 1])
            self.corner = (float(wr[i] + t * (wr[i + 1] - wr[i])), float(wz[i] + t * (wz[i + 1] - wz[i])))
        else:
            self.corner = None


def solve_round(outline, st, ztop_fn, R, z_guess, z_lo, z_hi=None):
    """Round of radius R at a station: section plane through the outline point at the wall tangent height (two
    passes), rolling-ball centre by offset intersection; returns the plane station and the chosen round."""
    rd = stn = None
    for _ in range(3):
        P0 = outline.point(st, z_guess)[0]
        n0 = outline.normal(st, z_guess)[0]
        O = P0 - D_ORG * n0
        zs = np.arange(z_lo, max(z_guess + 0.20, z_hi or 0.0), DZ)
        wr = outline.ray_hit(O, n0, zs)
        ok = np.isfinite(wr)
        zs, wr = zs[ok], wr[ok]
        tr = np.arange(D_ORG - 0.70, D_ORG + 0.10, DR)
        tz = ztop_fn(O[0] + tr * n0[0], O[1] + tr * n0[1])
        stn = PlaneStation(O, n0, wr, zs, tr, tz, ztop_fn)
        if stn.corner is None:
            return stn, None
        c = stn.round_halving(R)
        if not c:
            return stn, None
        rd = c[0]
        if abs(rd["zw_t"] - z_guess) < 2e-4:
            break
        z_guess = rd["zw_t"]
    return stn, rd


def r_blend(r0, r1, p):
    return r0 + (r1 - r0) * 0.5 * (1 - math.cos(math.pi * p))


# ------------------------------------------------------------------ greenhouse G (6b)
def roof_z(x, y):
    ym = 0.5 * (Y_RF + Y_RR)
    hl = 0.5 * (Y_RR - Y_RF)
    return H_ROOF - CROWN_X * (np.asarray(x) / (W_ROOF / 2)) ** 2 - CROWN_Y * ((np.asarray(y) - ym) / hl) ** 2


Y_MID_ROOF = 0.5 * (Y_RF + Y_RR)


def rail_tangent_x(theta):
    """Half-width at the rail round's wall tangent for a wall leaning theta from vertical (station at the roof's
    mid-length, where the roof crown along is zero)."""
    zs = np.arange(H_BELT, H_ROOF + 0.05, DZ)
    wr = D_ORG + XG0 - (zs - H_BELT) * math.tan(theta)
    O = (-D_ORG, Y_MID_ROOF)
    tr = np.arange(D_ORG, D_ORG + XG0 + 0.1, DR)
    fn = lambda x, y: roof_z(x, y)  # noqa: E731
    stn = PlaneStation(O, (1.0, 0.0), wr, zs, tr, fn(tr - D_ORG, np.full_like(tr, Y_MID_ROOF)), fn)
    c = stn.round(R_RAIL)
    return (c[0]["Pw"][0] - D_ORG, c[0]) if c else (None, None)


lo_t, hi_t = rad(1.0), rad(45.0)
for _ in range(50):
    mid = 0.5 * (lo_t + hi_t)
    xm, _rd = rail_tangent_x(mid)
    if xm > W_ROOF / 2:
        lo_t = mid
    else:
        hi_t = mid
THETA = 0.5 * (lo_t + hi_t)
X_RAIL_T, RAIL_RD = rail_tangent_x(THETA)
TUMB_DERIVED = math.degrees(THETA)
print(f"tumblehome derived {TUMB_DERIVED:.2f} deg (sheet {TUMB_SHEET}); rail tangent half width {X_RAIL_T:.4f} at z {RAIL_RD['zw_t']:.4f}")


def G_W(z):
    return XG0 - (z - H_BELT) * math.tan(THETA)


Z_B1 = float(RAIL_RD["zw_t"])  # height of BOW_TOP: the roof front round's wall tangent (iterated below)


def ws_bow(z):
    """Windscreen plan bow, linear from BOW_BASE at the belt (where G0 measured it) to BOW_TOP at the roof round tangent."""
    return BOW_BASE + (BOW_TOP - BOW_BASE) * (np.asarray(z, float) - H_BELT) / (Z_B1 - H_BELT)


def G_YF(z):  # windscreen side edge: the centre line passes through the cowl point at RAKE_WS; the sides sit the bow behind
    return Y_COWL + (np.asarray(z, float) - H_COWL) * math.tan(rad(RAKE_WS)) + ws_bow(z)


def G_YR(z):  # rear screen side value; the centre passes through the rear screen base point
    return (Y_RSB - REAR_BOW) - (z - RSB_Z) * math.tan(rad(RAKE_RS))


GO = Outline(G_W, G_YF, G_YR, ws_bow, lambda z: REAR_BOW + 0.0 * np.asarray(z, float), RC_A, RC_GR)
for _ in range(4):  # BOW_TOP sits at the roof front round's wall tangent: solve the front centre station's round
    _stn, _rd = solve_round(GO, (0, 0.0), roof_z, R_HEAD_F, Z_B1, H_BELT - 0.05)
    if abs(_rd["zw_t"] - Z_B1) < 1e-4:
        break
    Z_B1 = float(_rd["zw_t"])
print(f"windscreen bow top height (front round wall tangent) {Z_B1:.4f}")
Z_RAIL = float(RAIL_RD["zw_t"])
gb, gt = GO.g(H_BELT), GO.g(Z_RAIL)
y0t, y1t = float(gt["cfy"][0]), float(gt["cry"][0])
Y_D_EDGE = Y_D - PIL_D / 2
P0_G = y0t + A_WIDTH + 0.10
P1_G = min(y1t - 0.005, Y_D_EDGE + 0.005)
GO.side_map(H_BELT, A_WIDTH, P0_G, P1_G)
Y_PE = float(gb["cfy"][0])
g_extra = [Y_B - PIL_B / 2, Y_B + PIL_B / 2, Y_C - PIL_C / 2, Y_C + PIL_C / 2, Y_D_EDGE, float(gb["cfy"][0]) + A_WIDTH]
G_ST = stations(GO, H_BELT, g_extra)
lb, lt = LO.g(H_SILL), LO.g(H_BELT)
P0_L = max(float(lb["cfy"][0]), float(lt["cfy"][0])) + 0.05
P1_L = min(float(lb["cry"][0]), float(lt["cry"][0])) - 0.05
LO.side_map(H_BELT, 0.0, P0_L, P1_L)
l_extra = [Y_HF - ARCH_END, Y_HF + ARCH_END, Y_HR - ARCH_END, Y_HR + ARCH_END,
           Y_HF - ARCH_FLAT / 2, Y_HF + ARCH_FLAT / 2, Y_HR - ARCH_FLAT / 2, Y_HR + ARCH_FLAT / 2]
L_ST = stations(LO, H_BELT, l_extra)
print(f"stations: L {len(L_ST)}, G {len(G_ST)}; Y_PE {Y_PE:.3f}")


NOSE_BLEND_SIDE = 0.40   # construction lengths (not design values): the bonnet edge round fades to the belt round from
NOSE_BLEND_FRONT = 0.45  # this far before the front corner to this far along the side, so the round's top tangent
                         # line stays smooth; on the corner arc the radius stays below 0.9 x the plan corner radius
                         # (a larger round would turn its inner edge inside out round the corner)
_L_ARC = math.pi / 2 * RC_LF
_L_BL = NOSE_BLEND_FRONT + _L_ARC + NOSE_BLEND_SIDE
_X_TF = float(LO.g(H_BELT)["tfx"][0])


def R_L(st):
    seg, p = st
    if seg == 0:
        sv = p * _X_TF - (_X_TF - NOSE_BLEND_FRONT)
        return R_NOSE if sv <= 0 else r_blend(R_NOSE, R_BELT, sv / _L_BL)
    if seg == 1:
        return min(r_blend(R_NOSE, R_BELT, (NOSE_BLEND_FRONT + p * _L_ARC) / _L_BL), 0.9 * RC_LF)
    if seg == 2:
        d = st[1] - LO.smap[0]
        if d < NOSE_BLEND_SIDE:
            return r_blend(R_NOSE, R_BELT, (NOSE_BLEND_FRONT + _L_ARC + d) / _L_BL)
    return R_BELT


def R_G(st):
    seg, p = st
    if seg == 0:
        return R_HEAD_F
    if seg == 1:
        return r_blend(R_HEAD_F, R_RAIL, p)
    if seg == 2:
        return R_RAIL
    if seg == 3:
        return r_blend(R_RAIL, R_HEAD_R, p)
    return R_HEAD_R


# ------------------------------------------------------------------ rounds
def rounds(outline, sts, ztop_fn, Rfn, z_guess_fn, z_lo_fn, tag, z_hi=None):
    res = []
    for st in sts:
        stn, rd = solve_round(outline, st, ztop_fn, Rfn(st), z_guess_fn(st), z_lo_fn(st), z_hi)
        if rd is None:
            raise RuntimeError(f"{tag}: no round at station {st}")
        res.append((stn, rd))
    return res


L_RD = rounds(LO, L_ST, z_top_L, R_L, lambda st: H_BELT - 0.03, lambda st: H_SILL + 0.10, "L", H_BELT + 0.25)
G_RD = rounds(GO, G_ST, roof_z, R_G, lambda st: Z_RAIL, lambda st: H_BELT - 0.05, "G", H_ROOF + 0.10)
print(f"rounds solved ({time.time() - t0:.1f} s); halvings L {sum(r['halvings'] for _, r in L_RD)}, G {sum(r['halvings'] for _, r in G_RD)}")


# ------------------------------------------------------------------ offset paths for the top rows
class OffsetRect:
    """Inward offset paths of a rounded rectangle (no bow) with mitred collapse: point(station, depth)."""

    def __init__(self, W0, Yf0, Yr0, rcf, rcr, y0s, y1s):
        self.W0, self.Yf0, self.Yr0, self.rcf, self.rcr, self.y0s, self.y1s = W0, Yf0, Yr0, rcf, rcr, y0s, y1s

    def point(self, st, d, y_actual=None):
        seg, p = st
        d = np.asarray(d, float)
        Wd, Yf, Yr = self.W0 - d, self.Yf0 + d, self.Yr0 - d
        rf, rr = np.maximum(self.rcf - d, 0), np.maximum(self.rcr - d, 0)
        if seg == 0:
            return np.stack([p * (Wd - rf), Yf], -1)
        if seg == 1:
            a = -math.pi / 2 * (1 - p)
            return np.stack([Wd - rf + rf * math.cos(a), Yf + rf + rf * math.sin(a)], -1)
        if seg == 2:
            fs = (y_actual - self.y0s) / (self.y1s - self.y0s)
            a0, a1 = Yf + rf, Yr - rr
            return np.stack([Wd, a0 + fs * (a1 - a0)], -1)
        if seg == 3:
            a = math.pi / 2 * p
            return np.stack([Wd - rr + rr * math.cos(a), Yr - rr + rr * math.sin(a)], -1)
        return np.stack([(1 - p) * (Wd - rr), Yr], -1)


def pip(poly, P):
    """Points P (N, 2) inside the closed polygon poly (M, 2): even-odd rule."""
    x, y = P[:, 0][:, None], P[:, 1][:, None]
    x1, y1 = poly[:, 0][None], poly[:, 1][None]
    x2, y2 = np.roll(poly[:, 0], -1)[None], np.roll(poly[:, 1], -1)[None]
    with np.errstate(divide="ignore", invalid="ignore"):
        cond = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1)
    return (cond.sum(1) % 2) == 1


def top_rows(outline, sts, rds, off, n_rows, footprint, ztop_fn, z_ref, inner=None):
    """Rows from each round's top tangent Pt straight toward a target on the top's medial line: stations whose Pt
    lies ahead of the front mitre point aim at it, behind the rear mitre point at that, the rest straight inward
    (x -> 0). Rows sit at the same fraction for every station (no interleaving where paths converge). A row path
    ends where it enters the footprint; zero length where Pt is already inside it (BT2 rule). `off` and z_ref are
    unused (kept for the call signature)."""
    Pt = np.array([[stn.O[0] + rd["Pt"][0] * stn.n[0], stn.O[1] + rd["Pt"][0] * stn.n[1]] for stn, rd in rds])
    side = [k for k, st in enumerate(sts) if st[0] == 2]
    w_t = float(np.median(Pt[side, 0]))
    yf_m = float(Pt[0, 1]) + w_t
    yr_m = float(Pt[-1, 1]) - w_t
    out, ends = [], []
    tf = np.linspace(0, 1, 501)
    # bonnet: the stations ahead of G's front corner end on an inner boundary (centre line, then G's front base
    # line) matched by normalised arc length, so their rows cross the windscreen base instead of running along it
    tgt = {}
    if inner is not None:
        y_pe, F_front = inner
        # two pieces matched separately so the outer front corner maps to the windscreen base centre: front-edge
        # stations end on the centre line (cowl to nose), corner and side stations end on G's front base line
        jf = [k for k, st in enumerate(sts) if st[0] == 0]
        js = [k for k, st in enumerate(sts) if st[0] == 1 or (st[0] == 2 and Pt[k, 1] < y_pe)]
        D = np.array([0.0, F_front[0, 1]])
        for ks, inn, how in ((jf, np.vstack([Pt[0][None], D[None]]), "centre line"), (js, F_front, "footprint (bonnet)")):
            outer = Pt[ks]
            so = np.r_[0, np.cumsum(np.linalg.norm(np.diff(outer, axis=0), axis=1))]
            si = np.r_[0, np.cumsum(np.linalg.norm(np.diff(inn, axis=0), axis=1))]
            so = so / so[-1] if so[-1] > 0 else so
            if how == "centre line":  # the front edge's far end maps to just ahead of D (the corner takes D)
                so = so * (len(ks) - 1) / len(ks) if len(ks) > 1 else so
            si = si / si[-1]
            for k, sv in zip(ks, so):
                tgt[k] = (np.array([np.interp(sv, si, inn[:, 0]), np.interp(sv, si, inn[:, 1])]), how)
    for k, (st, (stn, rd)) in enumerate(zip(sts, rds)):
        p0 = Pt[k]
        if k in tgt:
            T, how = tgt[k]
            if float(np.dot(T - p0, -np.asarray(stn.n))) < 0.002:  # target not inboard of the tangent: no top row
                T, how = p0.copy(), "zero (tangent inside the footprint)"
            tk = np.arange(1, n_rows + 1) / n_rows
            pk = p0[None] + tk[:, None] * (T - p0)[None]
            out.append(np.c_[pk, ztop_fn(pk[:, 0], pk[:, 1])])
            ends.append(how)
            continue
        T = np.array([0.0, min(max(p0[1], yf_m), yr_m)])
        path = p0[None] + tf[:, None] * (T - p0)[None]
        t_end, how = 1.0, "medial"
        if footprint is not None:
            inside = pip(footprint, path)
            if inside[0]:
                t_end, how = 0.0, "zero (tangent inside the footprint)"
            elif inside.any():
                j = int(np.argmax(inside))
                t_end, how = float(tf[j - 1] + 0.5 * (tf[j] - tf[j - 1])), "footprint"
        tk = np.minimum(np.arange(1, n_rows + 1) / n_rows, t_end)
        pk = p0[None] + tk[:, None] * (T - p0)[None]
        z = ztop_fn(pk[:, 0], pk[:, 1])
        out.append(np.c_[pk, z])
        ends.append(how)
    return out, ends


# ------------------------------------------------------------------ assemble L and G grids
def wall_rows(outline, st, z0, z1, n, bands=None, levels=None):
    if levels is not None:
        # common heights below Z_SPLIT for every station (clamped to its span): rows stay level along the side, the
        # tuck round lies on rows, rows collapse onto the arch edge; above Z_SPLIT uniform rows up to this station's
        # wall tangent, so stations with different round sizes never collapse rows at the top
        lo = np.clip(levels[levels < Z_SPLIT], z0, Z_SPLIT)
        up = Z_SPLIT + (z1 - Z_SPLIT) * np.arange(1, N_UP + 1) / N_UP
        zs = np.r_[lo, up]
        zs[0] = z0
        xy = outline.point(st, zs)
        return np.c_[xy, zs]
    if bands:
        b0, b1 = bands
        zz = [z0] + list(np.linspace(z0 + b0, z1 - b1, n - 2)) + [z1]  # exactly n rows, band edges on rows
        zs = np.array(zz)
    else:
        zs = z0 + (z1 - z0) * np.arange(n) / (n - 1)
    xy = outline.point(st, zs)
    return np.c_[xy, zs]


def to3d(stn, pts2):
    return np.stack([stn.O[0] + pts2[:, 0] * stn.n[0], stn.O[1] + pts2[:, 0] * stn.n[1], pts2[:, 1]], 1)


def build_grid(outline, sts, rds, zlow, n_wall, tops, bands_fn=None, levels=None):
    rows = []
    for st, (stn, rd), zl, top in zip(sts, rds, zlow, tops):
        Pw = to3d(stn, rd["Pw"][None])[0]
        wall = wall_rows(outline, st, zl, rd["zw_t"], n_wall, bands_fn(st) if bands_fn else None, levels)
        wall[-1] = Pw
        arc, _ = stn.arc(rd, N_ARC)
        rows.append(np.vstack([wall, to3d(stn, arc), top]))
    return np.array(rows)


L_Z0 = [float(arch_z(np.array([float(LO.point(st, H_SILL)[0, 1])]))[0]) if st[0] == 2 else H_SILL for st in L_ST]
_zt_max = H_BELT + 0.12
_lv = [H_SILL] + list(np.linspace(TUCK_Z2, TUCK_Z1, 5)) + list(np.arange(TUCK_Z1 + STEP, _zt_max, STEP)) + [_zt_max]
L_LEVELS = np.array(_lv)
Z_SPLIT = min(rd["zw_t"] for _, rd in L_RD) - 0.02
N_UP = int(math.ceil((max(rd["zw_t"] for _, rd in L_RD) - Z_SPLIT) / STEP))
N_WALL_L = int((L_LEVELS < Z_SPLIT).sum()) + N_UP
N_TOP_L = int(math.ceil(XB / STEP))
N_TOP_G = int(math.ceil((W_ROOF / 2) / STEP))
L_off = OffsetRect(XB, float(L_YF(H_BELT)), float(L_YR(H_BELT)), RC_LF, RC_LR, float(lt["cfy"][0]), float(lt["cry"][0]))

# H: L's upper surface (rounds + top) rasterised, for G's base
HX0, HY0, HG = -0.01, -2.40, 0.003
HNX, HNY = int((XB + 0.05 - HX0) / HG), int((2.75 - HY0) / HG)


def raster_upper(grid, r0):
    H = np.full((HNY, HNX), np.nan)
    ns, nr = grid.shape[:2]
    for i in range(ns - 1):
        for r in range(r0, nr - 1):
            q = [grid[i, r], grid[i + 1, r], grid[i + 1, r + 1], grid[i, r + 1]]
            for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
                A, B, C = tri
                det = (B[0] - A[0]) * (C[1] - A[1]) - (C[0] - A[0]) * (B[1] - A[1])
                if abs(det) < 1e-12:
                    continue
                xs = [A[0], B[0], C[0]]
                ys = [A[1], B[1], C[1]]
                ix0, ix1 = int((min(xs) - HX0) / HG), int((max(xs) - HX0) / HG) + 1
                iy0, iy1 = int((min(ys) - HY0) / HG), int((max(ys) - HY0) / HG) + 1
                ix0, iy0 = max(ix0, 0), max(iy0, 0)
                ix1, iy1 = min(ix1, HNX - 1), min(iy1, HNY - 1)
                if ix1 < ix0 or iy1 < iy0:
                    continue
                gx, gy = np.meshgrid(HX0 + HG * np.arange(ix0, ix1 + 1), HY0 + HG * np.arange(iy0, iy1 + 1))
                l1 = ((B[1] - C[1]) * (gx - C[0]) + (C[0] - B[0]) * (gy - C[1])) / (
                    (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1]))
                l2 = ((C[1] - A[1]) * (gx - C[0]) + (A[0] - C[0]) * (gy - C[1])) / (
                    (B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1]))
                l3 = 1 - l1 - l2
                m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
                if not m.any():
                    continue
                zz = l1 * A[2] + l2 * B[2] + l3 * C[2]
                sub = H[iy0:iy1 + 1, ix0:ix1 + 1]
                sub[m] = np.fmax(sub[m], zz[m])
    return H


def H_at(H, x, y):
    fx = (np.asarray(x) - HX0) / HG
    fy = (np.asarray(y) - HY0) / HG
    ix = np.clip(np.floor(fx).astype(int), 0, HNX - 2)
    iy = np.clip(np.floor(fy).astype(int), 0, HNY - 2)
    tx, ty = fx - ix, fy - iy
    v = (H[iy, ix] * (1 - tx) * (1 - ty) + H[iy, ix + 1] * tx * (1 - ty) + H[iy + 1, ix] * (1 - tx) * ty
         + H[iy + 1, ix + 1] * tx * ty)
    out = (fx < 0) | (fy < 0) | (fx > HNX - 1) | (fy > HNY - 1)
    return np.where(out, np.nan, v)


def g_bases(H):
    zs = np.arange(H_BELT - 0.12, H_BELT + 0.20, 0.001)
    out = []
    for st in G_ST:
        P = GO.point(st, zs)
        h = H_at(H, P[:, 0], P[:, 1]) if H is not None else np.full(len(zs), np.nan)
        h = np.where(np.isfinite(h), h, z_top_L(P[:, 0], P[:, 1]))
        f = zs - h
        k = np.where((f[:-1] < 0) & (f[1:] >= 0))[0]
        if not len(k):
            raise RuntimeError(f"G base not found at station {st}")
        i = k[0]
        t = f[i] / (f[i] - f[i + 1])
        out.append(float(zs[i] + t * (zs[i + 1] - zs[i])))
    return np.array(out)


def footprint(zb):
    half = np.array([GO.point(st, z)[0] for st, z in zip(G_ST, zb)])
    return np.vstack([half, half[::-1] * np.array([-1, 1])])


def front_base(zb_):
    """G's base points in plan from the front centre round the A-pillar corner to the first side station."""
    k = [i for i, st in enumerate(G_ST) if st[0] in (0, 1)] + [next(i for i, st in enumerate(G_ST) if st[0] == 2)]
    return np.array([GO.point(G_ST[i], zb_[i])[0] for i in k])


zb0 = g_bases(None)
fp0 = footprint(zb0)
tops_L, ends_L = top_rows(LO, L_ST, L_RD, L_off, N_TOP_L, fp0, z_top_L, H_BELT, (Y_PE, front_base(zb0)))
grid_L = build_grid(LO, L_ST, L_RD, L_Z0, N_WALL_L, tops_L, levels=L_LEVELS)
H_L = raster_upper(grid_L, N_WALL_L - 1)
for _pass in range(2):  # G base on the built L surface, L top rows on that footprint (twice: converged)
    zb = g_bases(H_L)
    fp = footprint(zb)
    tops_L, ends_L = top_rows(LO, L_ST, L_RD, L_off, N_TOP_L, fp, z_top_L, H_BELT, (Y_PE, front_base(zb)))
    grid_L = build_grid(LO, L_ST, L_RD, L_Z0, N_WALL_L, tops_L, levels=L_LEVELS)
    if _pass == 0:
        zb_prev = zb.copy()
        H_L = raster_upper(grid_L, N_WALL_L - 1)
print(f"G base second pass change max {np.abs(zb - zb_prev).max() * 1000:.2f} mm")
print(f"G base: analytic top vs built L surface, max change {np.abs(zb - zb0).max() * 1000:.1f} mm; "
      f"L top ends {dict((k, ends_L.count(k)) for k in set(ends_L))} ({time.time() - t0:.1f} s)")

z_ref_roof = float(np.median([rd["zw_t"] for st, (stn, rd) in zip(G_ST, G_RD) if st[0] == 2]))
gr = GO.g(z_ref_roof)
# the offset rectangle shares the outline's corner centres (the plan bow only moves the screens' middles)
G_off = OffsetRect(float(gr["W"][0]), float(gr["cfy"][0]) - RC_A, float(gr["cry"][0]) + RC_GR, RC_A, RC_GR,
                   float(gr["cfy"][0]), float(gr["cry"][0]))
tops_G, ends_G = top_rows(GO, G_ST, G_RD, G_off, N_TOP_G, None, roof_z, z_ref_roof)
N_WALL_G = int(math.ceil((Z_RAIL - H_BELT) / STEP)) + 1


def g_bands(st):
    return (GLASS_BELT, HEADER)


grid_G = build_grid(GO, G_ST, G_RD, zb, N_WALL_G, tops_G, g_bands)
print(f"grids: L {grid_L.shape}, G {grid_G.shape}")


# ------------------------------------------------------------------ glass by rule (6d)
def glass_at(st, x, y, z, z_base, z_wt):
    """Glass test for a point on G's wall (station st)."""
    if z < z_base + GLASS_BELT - 1e-6 or z > z_wt - HEADER + 1e-6:
        return False
    seg = st[0]
    if seg in (0, 4):
        return True
    if seg in (1, 3):
        return False
    g = GO.g(z)
    if y < float(g["cfy"][0]) + A_WIDTH - 1e-6:
        return False
    if abs(y - Y_B) < PIL_B / 2 - 1e-6 or abs(y - Y_C) < PIL_C / 2 - 1e-6:
        return False
    if y > Y_D_EDGE + 1e-6:
        return False
    return True


nsG, nrG = grid_G.shape[:2]
glass_face = np.zeros((nsG - 1, nrG - 1), bool)
glass_vert = np.zeros((nsG, nrG))
for i in range(nsG):
    st = G_ST[i]
    zw_t = G_RD[i][1]["zw_t"]
    for r in range(N_WALL_G):
        x, y, z = grid_G[i, r]
        glass_vert[i, r] = 1.0 if glass_at(st, x, y, z, zb[i], zw_t) else 0.0
for i in range(nsG - 1):
    for r in range(N_WALL_G - 1):
        c = grid_G[i:i + 2, r:r + 2].reshape(-1, 3).mean(0)
        st = G_ST[i] if G_ST[i][0] == G_ST[i + 1][0] else G_ST[i + 1]
        zbm = 0.5 * (zb[i] + zb[i + 1])
        ztm = 0.5 * (G_RD[i][1]["zw_t"] + G_RD[i + 1][1]["zw_t"])
        both = glass_vert[i, r] + glass_vert[i + 1, r] + glass_vert[i, r + 1] + glass_vert[i + 1, r + 1]
        glass_face[i, r] = both >= 4 or (both >= 2 and glass_at(st, *c, zbm, ztm))


# ------------------------------------------------------------------ weld
def weld(P, flags):
    NS, NR, _ = P.shape
    v = P.reshape(-1, 3).copy()
    v[np.abs(v[:, 0]) < 1e-7, 0] = 0.0
    key = np.round(v / WELD).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    vw = v[first]
    vf = {k: np.zeros(len(vw), bool) for k in flags}
    for k, fl in flags.items():
        vf[k][inv[np.where(fl.ravel())[0]]] = True
    faces, fmap = [], []
    for i in range(NS - 1):
        for r in range(NR - 1):
            g = [inv[i * NR + r], inv[(i + 1) * NR + r], inv[(i + 1) * NR + r + 1], inv[i * NR + r + 1]]
            u = []
            for q in g:
                if q not in u:
                    u.append(int(q))
            if len(u) < 3:
                continue
            p = vw[u]
            area = 0.5 * np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])) if len(u) == 3 else 0.5 * np.linalg.norm(
                np.cross(p[2] - p[0], p[3] - p[1]))
            if area < 1e-10:
                continue
            faces.append(u + [-1] * (4 - len(u)))
            fmap.append((i, r))
    return vw, np.array(faces), vf, np.array(fmap), inv


nsL, nrL = grid_L.shape[:2]
fl_L = {"lower": np.zeros((nsL, nrL), bool), "junction": np.zeros((nsL, nrL), bool), "pole": np.zeros((nsL, nrL), bool)}
fl_L["lower"][:, 0] = True
for i, e in enumerate(ends_L):
    if e.startswith("footprint") or e.startswith("zero"):
        fl_L["junction"][i, -1] = True  # the row end on G's base (zero-length rows collapse onto it)
        if e.startswith("zero"):
            fl_L["junction"][i, N_WALL_L + N_ARC - 1:] = True
    elif e == "medial":
        fl_L["pole"][i, -1] = True
vL, fL, vfL, fmapL, _ = weld(grid_L, fl_L)
fl_G = {"base": np.zeros((nsG, nrG), bool), "pole": np.zeros((nsG, nrG), bool)}
fl_G["base"][:, 0] = True
fl_G["pole"][:, -1] = True
vG, fG, vfG, fmapG, invG = weld(grid_G, fl_G)
gglass = np.array([glass_face[i, r] if r < glass_face.shape[1] else False for i, r in fmapG])
gvert = np.zeros(len(vG))
for k, val in zip(invG, glass_vert.ravel()):
    gvert[k] = max(gvert[k], val)
print(f"L {len(vL)} v / {len(fL)} f; G {len(vG)} v / {len(fG)} f, glass faces {int(gglass.sum())}")


# ------------------------------------------------------------------ bumpers (6c) and wheels (6e)
def rounded_box(x_half, y0, y1, z0, z1, rc, re, front_sign):
    """Box from y0 to y1 (y0 = face), x in +-x_half, z in [z0, z1]; plan corners rc, edges re; closed mesh."""
    n_ring = 96
    zr = list(z0 + re - re * np.cos(np.linspace(0, math.pi / 2, 7)))
    zr = [z0] + zr[1:] + list(z1 - re + re * np.sin(np.linspace(0, math.pi / 2, 7)))[0:]
    zr = sorted(set(round(v, 9) for v in zr))

    def inset(z):
        d = min(z - z0, z1 - z)
        return re - math.sqrt(max(re * re - (re - d) ** 2, 0.0)) if d < re else 0.0

    def ring(z):
        e = inset(z)
        hx, ya, yb = x_half - e, min(y0, y1) + e, max(y0, y1) - e
        r = max(rc - e, 0.002)
        cs = [(hx - r, yb - r, 0.0), (-hx + r, yb - r, 90.0), (-hx + r, ya + r, 180.0), (hx - r, ya + r, 270.0)]
        pts = []
        for cx, cy, a0 in cs:
            for a in np.linspace(a0, a0 + 90, n_ring // 4, endpoint=False):
                pts.append((cx + r * math.cos(rad(a)), cy + r * math.sin(rad(a)), z))
        return pts

    V, Fc = [], []
    rings = [ring(z) for z in zr]
    for rg in rings:
        V += rg
    m = n_ring
    for k in range(len(rings) - 1):
        for j in range(m):
            a, b = k * m + j, k * m + (j + 1) % m
            Fc.append([a, b, b + m, a + m])
    cb = len(V)
    V.append((0.0, 0.5 * (y0 + y1), z0))
    ct = len(V)
    V.append((0.0, 0.5 * (y0 + y1), z1))
    for j in range(m):
        Fc.append([cb, (j + 1) % m, j, -1])
        top = (len(rings) - 1) * m
        Fc.append([ct, top + j, top + (j + 1) % m, -1])
    return np.array(V), np.array(Fc)


BF_V, BF_F = rounded_box(W_FLARE / 2, Y_BUMP_F, Y_BUMP_F + BF_SIDE, H_BB, H_BT, BF_CORNER, BF_EDGE, -1)
z_rb0 = S.con("REAR_BUMPER_B", "rear bumper bottom")
z_rb1 = S.con("REAR_BUMPER_T", "rear bumper top")
BR_V, BR_F = rounded_box(W_FLARE / 2, Y_BUMP_R, Y_BUMP_R - BR_SIDE, z_rb0, z_rb1, BR_CORNER, BR_EDGE, 1)


def wheel(xc, yc, zc, r, w, n=64):
    V, Fc = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        for dx in (-w / 2, w / 2):
            V.append((xc + dx, yc + r * math.cos(a), zc + r * math.sin(a)))
    for k in range(n):
        a0, a1 = 2 * k, 2 * ((k + 1) % n)
        Fc.append([a0, a1, a1 + 1, a0 + 1])
    Fc.append(list(range(0, 2 * n, 2))[::-1])
    Fc.append(list(range(1, 2 * n, 2)))
    return np.array(V), Fc


wheels = {}
for name, xc, yc, trk in (("FL", 1, Y_HF, TRACK_F), ("FR", -1, Y_HF, TRACK_F), ("RL", 1, Y_HR, TRACK_R), ("RR", -1, Y_HR, TRACK_R)):
    V, Fc = wheel(xc * trk / 2, yc, HUB_Z, TYRE_R, TYRE_W)
    wheels[name] = (V, Fc)
S.prov["wheel centre plane"] = "TRACK/2 (outer face at TRACK/2 + TYRE_W/2, plan 6e)"

# ------------------------------------------------------------------ outputs for Blender and checks
if os.environ.get("G1_NO_SAVE") != "1":
    os.makedirs(DBG, exist_ok=True)


def pad(Fc):
    m = max(len(f) for f in Fc)
    return np.array([list(f) + [-1] * (m - len(f)) for f in Fc])


SAVE = os.environ.get("G1_NO_SAVE") != "1"  # G2 imports this module as the master and must not rewrite G1's files
if SAVE:
  np.savez_compressed(os.path.join(OUT, "shell-mesh.npz"), L_v=vL, L_f=fL, L_lower=vfL["lower"], L_junction=vfL["junction"],
                    L_pole=vfL["pole"], G_v=vG, G_f=fG, G_base=vfG["base"], G_pole=vfG["pole"], G_glass=gglass, G_glass_v=gvert,
                    BF_v=BF_V, BF_f=pad(BF_F), BR_v=BR_V, BR_f=pad(BR_F),
                    **{f"W{k}_v": v for k, (v, _) in wheels.items()}, **{f"W{k}_f": pad(f) for k, (_, f) in wheels.items()},
                    grid_L=grid_L, grid_G=grid_G, zb=zb)
STATE = {"L_ST": L_ST, "G_ST": G_ST, "N_WALL_L": N_WALL_L, "N_WALL_G": N_WALL_G, "N_ARC": N_ARC, "THETA_deg": TUMB_DERIVED,
         "X_RAIL_T": X_RAIL_T, "Z_RAIL": Z_RAIL, "Y_PE": Y_PE, "ends_L": ends_L, "provenance": S.prov,
         "L_round_R": [float(r["R"]) for _, r in L_RD], "G_round_R": [float(r["R"]) for _, r in G_RD],
         "L_halvings": int(sum(r["halvings"] for _, r in L_RD)), "G_halvings": int(sum(r["halvings"] for _, r in G_RD)),
         "G_zw_t": [float(r["zw_t"]) for _, r in G_RD], "L_zw_t": [float(r["zw_t"]) for _, r in L_RD],
         "G_plane": [[stn.O, stn.n] for stn, _ in G_RD], "L_plane": [[stn.O, stn.n] for stn, _ in L_RD],
         "G_rd": [[list(map(float, r["C"])), list(map(float, r["Pw"])), list(map(float, r["Pt"]))] for _, r in G_RD]}
if SAVE:
    with open(os.path.join(OUT, "g1-state.json"), "w", encoding="utf-8") as f:
        json.dump(STATE, f, indent=0, default=float)
print(f"G1 shell built in {time.time() - t0:.1f} s")
