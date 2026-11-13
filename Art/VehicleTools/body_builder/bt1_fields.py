"""BT1 (tub master), steps 4a-4f in numpy: envelope, station frame, wall field, top fields,
shoulder rounds, and the sampled half mesh. System Python (numpy + PIL for the debug picture).

Plan: docs/BODY_BUILDER_PLAN.md section 4. Inputs (read only) from impreza-scaffold-cage-v02.
Writes to impreza-builder-bt1-v01: tub-mesh.npz, bt1-fields.json, debug/tub-fields.png.
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scaffold_cage"))
import bspline as BS  # noqa: E402
import sc_common as C  # noqa: E402  (helpers only: bilinear, px/Y conversions, smoothing)
import sc3_lines as SL  # noqa: E402  (lower_line: z_arch / z_low by reference column)

import bt_paths as BP  # noqa: E402

IN_DIR = BP.IN_DIR
OUT_DIR = BP.OUT_DIR
DEBUG_DIR = BP.DEBUG_DIR
V2 = BP.V2

# 4a
MIRROR_UNKNOWN_X = (0.78, 1.20)
MIRROR_UNKNOWN_Z = (1.00, 1.26)
# 4b
Y_FAN_FRONT = -1.60
Y_FAN_REAR = 1.72
RHO0 = 0.90
S_MIN = Y_FAN_FRONT - RHO0 * math.pi / 2
S_MAX = Y_FAN_REAR + RHO0 * math.pi / 2
MARCH_START = 2.5
MARCH_STEP = 0.005
MARCH_TOL = 0.0005
# 4c
WALL_S_STEP = 0.02
WALL_Z = (0.10, 1.30)
WALL_Z_STEP = 0.02
Z_PROBE = 0.50
PX_CLAMP = (133, 1760)
SLOPE_MAX = 1.2
ZL_MARGIN = 0.02
ARCH_WEIGHT = 0.3
ARCH_WIDEN = 0.03
ARCH_Z_MARGIN = 0.04
Y_CAB0, Y_CAB1 = -0.82, 1.63
CAB_BELT_MARGIN = 0.03
WALL_KNOT_S = 0.20
WALL_KNOT_Z = 0.15
WALL_RMS_CM = 0.5
# 4d
COWL_X = (0.0, 0.80, 0.02)
COWL_START_Y = -1.30
COWL_SLOPE = 0.55
BL_START_Y = 2.00
BL_SLOPE = 0.40
RUN_CM = 5
CURVE_REJECT_K = 2.5  # one rejection pass: drop points more than 2.5 x RMS off the first fit
TOP_SLOPE_MAX = 1.0
COWL_MARGIN = 0.03
A_FRONT_Y = (-2.25, -0.55)
A_REAR_Y = (1.45, 2.35)
TOP_X = (0.0, 1.1)
TOP_KNOT = 0.20
TOP_RMS_CM = 0.4
U_BLEND = 0.10
SLOPE_RULE_MID = False  # BT2 v02 (plan 8.1): wall data valid only while the slope stays near the mid-wall slope
MID_SLOPE_TOL = 0.35
# 4e
R_RANGE = (0.02, 0.30)
R_STEP = 0.005
ENV_INSET = 0.4
ENV_ANGLES = np.radians(np.arange(15.0, 75.0 + 1e-9, 2.5))
R_MEDIAN_N = 5
R_KNOT = 0.50
R_SPLINE_LAM = 0.1
BELT_ROUND_R = 0.03
R_CAB_BLEND = 0.15
LEDGE_W = 0.05
END_CURVE_MARGIN = 0.02
PROFILE_STEP = 0.002
ROUND_TOL = 0.02  # rolling-ball validity tolerance (sampling of the polylines)
COARSE = 5  # coarse step (samples) for the polyline intersection
WALL_ZMAX = 1.30
# 4f
MESH_S_STEP = 0.03
N_WALL, N_ARC, N_TOP = 30, 6, 14
# v02 (plan section 6)
ROBUST_C_CM = 2.0
ROBUST_PASSES = 4
N_WALL_LOW, N_WALL_HIGH = 4, 27
R_CAB_BLEND_V2 = 0.60  # centred on each end of the cabin zone
ZL_SMOOTH = 0.10
ENV_WIN, ENV_SIGMA = 0.10, 0.05
ZL_FINE_STEP = 0.01
if V2:
    N_ARC = 16
    N_WALL = N_WALL_LOW + N_WALL_HIGH
    R_RANGE = (0.02, 0.40)
TOP_EXP = 1.3
WELD = 1e-6


def save_json(name, data):
    with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- 4a envelope
class Envelope:
    def __init__(self, maps):
        self.ys, self.zs, self.xs = maps["ys"], maps["zs"], maps["xs"]
        self.SIDE, self.TOP, self.FRONT, self.REAR = maps["SIDE"], maps["TOP"], maps["FRONT"], maps["REAR"]
        self.g = float(maps["grid"])

    def side(self, y, z):
        return C.bilinear(self.SIDE, self.ys[0], self.zs[0], self.g, y, z)

    def top(self, ax, y):
        return C.bilinear(self.TOP, self.xs[0], self.ys[0], self.g, ax, y)

    def front(self, ax, z):
        return C.bilinear(self.FRONT, self.xs[0], self.zs[0], self.g, ax, z)

    def rear(self, ax, z):
        return C.bilinear(self.REAR, self.xs[0], self.zs[0], self.g, ax, z)

    def inside(self, x, y, z):
        ax = np.abs(x)
        with np.errstate(invalid="ignore"):
            c1 = ax < self.side(y, z)
            c2 = z < self.top(ax, y)
            unknown = (ax >= MIRROR_UNKNOWN_X[0]) & (ax <= MIRROR_UNKNOWN_X[1]) & (z >= MIRROR_UNKNOWN_Z[0]) & (z <= MIRROR_UNKNOWN_Z[1])
            c3 = unknown | (y > self.front(ax, z))
            c4 = unknown | (y < self.rear(ax, z))
        return c1 & c2 & c3 & c4


# ---------------------------------------------------------------- 4b frame
def frame(s):
    s = np.atleast_1d(np.asarray(s, float))
    Ox = np.zeros_like(s)
    Oy = s.copy()
    nx = np.ones_like(s)
    ny = np.zeros_like(s)
    f = s < Y_FAN_FRONT
    a = (Y_FAN_FRONT - s[f]) / RHO0
    Oy[f] = Y_FAN_FRONT
    nx[f] = np.cos(a)
    ny[f] = -np.sin(a)
    r = s > Y_FAN_REAR
    a = (s[r] - Y_FAN_REAR) / RHO0
    Oy[r] = Y_FAN_REAR
    nx[r] = np.cos(a)
    ny[r] = np.sin(a)
    nx[np.abs(nx) < 1e-12] = 0.0
    return Ox, Oy, nx, ny


def march_rays(env, Ox, Oy, nx, ny, z, start=None):
    """Distance from O along n to the envelope (march inward from 2.5 m, 5 mm steps, bisect to 0.5 mm)."""
    n = len(Ox)
    res = np.full(n, np.nan)
    hi = np.full(n, np.nan)
    todo = np.ones(n, bool)
    rho = MARCH_START if start is None else start
    while rho >= -1e-9 and todo.any():
        idx = np.where(todo)[0]
        ins = env.inside(Ox[idx] + rho * nx[idx], Oy[idx] + rho * ny[idx], z[idx])
        hit = idx[ins]
        res[hit] = rho
        hi[hit] = rho + MARCH_STEP
        todo[hit] = False
        rho -= MARCH_STEP
    found = np.isfinite(res)
    lo = res.copy()
    idx = np.where(found)[0]
    while len(idx) and np.max(hi[idx] - lo[idx]) > MARCH_TOL:
        mid = 0.5 * (lo[idx] + hi[idx])
        ins = env.inside(Ox[idx] + mid * nx[idx], Oy[idx] + mid * ny[idx], z[idx])
        lo[idx] = np.where(ins, mid, lo[idx])
        hi[idx] = np.where(ins, hi[idx], mid)
    out = np.full(n, np.nan)
    out[found] = 0.5 * (lo[found] + hi[found])
    return out


def march_plane(env, Ox, Oy, nx, ny, P, d):
    """Rays in a station plane (rho, z) from points P inside, outward along d, to the envelope boundary."""
    n = len(P)
    t = np.zeros(n)
    res = np.full(n, np.nan)
    rho0 = P[:, 0]
    z0 = P[:, 1]
    inside0 = env.inside(Ox + rho0 * nx, Oy + rho0 * ny, z0)
    todo = inside0.copy()
    step = 0.005
    lo = np.zeros(n)
    for k in range(1, 400):
        tt = k * step
        idx = np.where(todo)[0]
        if not len(idx):
            break
        rr = rho0[idx] + tt * d[idx, 0]
        zz = z0[idx] + tt * d[idx, 1]
        ins = env.inside(Ox + rr * nx, Oy + rr * ny, zz)
        out = idx[~ins]
        res[out] = tt
        lo[out] = tt - step
        todo[out] = False
    idx = np.where(np.isfinite(res))[0]
    hi = res.copy()
    while len(idx) and np.max(hi[idx] - lo[idx]) > MARCH_TOL:
        mid = 0.5 * (lo[idx] + hi[idx])
        rr = rho0[idx] + mid * d[idx, 0]
        zz = z0[idx] + mid * d[idx, 1]
        ins = env.inside(Ox + rr * nx, Oy + rr * ny, zz)
        lo[idx] = np.where(ins, mid, lo[idx])
        hi[idx] = np.where(ins, hi[idx], mid)
    tfin = 0.5 * (lo + hi)
    pts = np.stack([rho0 + tfin * d[:, 0], z0 + tfin * d[:, 1]], 1)
    pts[~np.isfinite(res)] = np.nan
    return pts


# ---------------------------------------------------------------- reference lines helpers
class RefLines:
    def __init__(self, lines):
        self.lines = lines
        self.zL_px = SL.lower_line(lines)
        self.coef = lines["belt"]["coef_line"]

    def z_L_at_y(self, y):
        px = np.clip(C.Y_to_px(y), *PX_CLAMP)
        return self.zL_px(px)

    def z_B(self, y):
        return C.py_to_Z(np.polyval(self.coef, C.Y_to_px(y)))

    def in_arch(self, y, z):
        m = np.zeros(np.broadcast(y, z).shape, bool)
        for (lf, lr), a in zip(self.lines["legs_px"], self.lines["arch"]):
            Yf = C.px_to_Y(lf) - ARCH_WIDEN
            Yr = C.px_to_Y(lr) + ARCH_WIDEN
            px = np.arange(a["x0"], a["x0"] + len(a["py"]))
            za = C.py_to_Z(np.array(a["py"]))
            z_at = np.interp(C.Y_to_px(y), px, za)
            m |= (y >= Yf) & (y <= Yr) & (z < z_at + ARCH_Z_MARGIN)
        return m


def v01_penalties():
    with open(os.path.join(BP.V01_DIR, "report.json"), encoding="utf-8") as f:
        r = json.load(f)
    return {k: r["fits"][k]["penalty"] for k in ("wall", "A_front", "A_rear")}


def robust_fit(fit, u, v, val, w0, lam, cons):
    """Plan 6.1: first fit, then four reweighting passes with a biweight at ROBUST_C_CM on the residuals
    (each pass: weight = base weight x biweight of the current residual)."""
    c = ROBUST_C_CM / 100.0
    pred = fit.fit(u, v, val, w0, lam, cons)
    w = w0.copy()
    for _ in range(ROBUST_PASSES):
        r = pred - val
        bw = np.where(np.abs(r) < c, (1 - (r / c) ** 2) ** 2, 0.0)
        w = w0 * bw
        pred = fit.fit(u, v, val, w, lam, cons)
    r = pred - val
    m0 = w0 > 0
    rms0, p950 = BS.weighted_stats(r, w0)
    rmsr, p95r = BS.weighted_stats(r, w) if (w > 0).any() else (float("nan"), float("nan"))
    return pred, w, {"penalty": lam, "weighted_rms_cm": rms0 * 100, "p95_cm": p950 * 100,
                     "robust_weighted_rms_cm": rmsr * 100, "robust_p95_cm": p95r * 100,
                     "cells_zeroed_by_biweight": int(np.sum(m0 & (w == 0))),
                     "cells_downweighted_below_half": int(np.sum(m0 & (w < w0 * 0.5))), "cells": int(m0.sum())}


def mid_slope_valid(dr, z, z_lo, z_hi, lo_margin=0.0):
    """Plan 8.1: per row, slope_mid = median d rho/dz over the middle third of [z_lo, z_hi]; a cell is valid
    while |d rho/dz - slope_mid| <= MID_SLOPE_TOL; scanning up from the middle, the first cell that breaks
    it (or has no data) ends the wall. Below the middle each cell is checked on its own.
    Returns (valid mask, slope_mid per row, z where the wall ends per row)."""
    n = dr.shape[0]
    valid = np.zeros(dr.shape, bool)
    smid = np.full(n, np.nan)
    zend = np.full(n, np.nan)
    for i in range(n):
        lo, hi = z_lo[i], z_hi[i]
        if not (np.isfinite(lo) and np.isfinite(hi)) or hi - lo < 3 * (z[1] - z[0]):
            continue
        d = dr[i]
        fin = np.isfinite(d)
        third = fin & (z >= lo + (hi - lo) / 3) & (z <= lo + 2 * (hi - lo) / 3)
        if not third.any():
            continue
        sm = float(np.median(d[third]))
        smid[i] = sm
        ok = fin & (np.abs(np.where(fin, d, 1e9) - sm) <= MID_SLOPE_TOL) & (z >= lo - lo_margin) & (z <= hi)
        zm = 0.5 * (lo + hi)
        up = np.where(z >= zm)[0]
        for k in up:
            if not ok[k]:
                ok[k:] = False
                zend[i] = z[k]
                break
        valid[i] = ok
    return valid, smid, zend


# ---------------------------------------------------------------- 4c wall field
def wall_field(env, ref):
    s_grid = np.arange(S_MIN, S_MAX + 1e-9, WALL_S_STEP)
    if S_MAX - s_grid[-1] > 1e-6:
        s_grid = np.append(s_grid, S_MAX)
    z_grid = np.arange(WALL_Z[0], WALL_Z[1] + 1e-9, WALL_Z_STEP)
    S, Z = np.meshgrid(s_grid, z_grid, indexing="ij")
    Ox, Oy, nx, ny = frame(S.ravel())
    t = time.time()
    rho = march_rays(env, Ox, Oy, nx, ny, Z.ravel()).reshape(S.shape)
    print(f"  rho grid {S.shape} in {time.time() - t:.1f} s; finite {np.isfinite(rho).sum()}", flush=True)
    Ox1, Oy1, nx1, ny1 = frame(s_grid)
    rho_p = march_rays(env, Ox1, Oy1, nx1, ny1, np.full(len(s_grid), Z_PROBE))
    y_h = Oy1 + rho_p * ny1
    z_L = ref.z_L_at_y(y_h)
    # slope |d rho / dz| by central difference over +-2 cm (one-sided at the grid ends)
    drho = np.full(rho.shape, np.nan)
    drho[:, 1:-1] = (rho[:, 2:] - rho[:, :-2]) / (2 * WALL_Z_STEP)
    drho[:, 0] = (rho[:, 1] - rho[:, 0]) / WALL_Z_STEP
    drho[:, -1] = (rho[:, -1] - rho[:, -2]) / WALL_Z_STEP
    fin = np.isfinite(rho)
    cab = (y_h >= Y_CAB0) & (y_h <= Y_CAB1)
    zb = ref.z_B(y_h)
    mid_info = None
    if SLOPE_RULE_MID:
        # height range: z_L to the highest finite cell below any cabin cut
        cut = np.where(cab, zb - CAB_BELT_MARGIN, np.inf)
        zhi = np.array([z_grid[np.isfinite(rho[i]) & (z_grid <= cut[i])].max() if (np.isfinite(rho[i]) & (z_grid <= cut[i])).any() else np.nan
                        for i in range(len(s_grid))])
        slope_ok, smid, zend = mid_slope_valid(drho, z_grid, z_L, zhi, lo_margin=ZL_MARGIN)
        # arch-opening cells (inpainted, below z_L) keep their own test: slope near the mid-wall slope
        near = fin & (np.abs(np.nan_to_num(drho, nan=99.0) - np.nan_to_num(smid, nan=-99.0)[:, None]) <= MID_SLOPE_TOL)
        mid_info = {"slope_mid": smid, "z_end": zend, "z_hi": zhi}
    else:
        slope_ok = fin & (np.abs(np.nan_to_num(drho, nan=99.0)) <= SLOPE_MAX)
        near = slope_ok
    yhit = Oy.reshape(S.shape) + np.nan_to_num(rho) * ny.reshape(S.shape)
    arch = ref.in_arch(yhit, Z) & fin
    w = np.zeros(S.shape)
    w[slope_ok & (Z >= z_L[:, None] - ZL_MARGIN)] = 1.0
    w[arch & near] = ARCH_WEIGHT
    w[cab[:, None] & (Z > zb[:, None] - CAB_BELT_MARGIN)] = 0.0
    w[~fin] = 0.0
    # fit
    fit = BS.Fit2D(BS.Knots(S_MIN, S_MAX, WALL_KNOT_S), BS.Knots(WALL_Z[0], WALL_Z[1], WALL_KNOT_Z))
    cons = np.vstack([fit.du_constraint(S_MIN), fit.du_constraint(S_MAX)])
    m = w > 0
    if V2:
        lam = v01_penalties()["wall"] * BP.PENALTY_FACTOR
        _, wr_, rinfo = robust_fit(fit, S[m], Z[m], rho[m], w[m], lam, cons)
        rms, p95 = rinfo["weighted_rms_cm"] / 100, rinfo["p95_cm"] / 100
        li = {"reached": None, "floor": float("nan"), "budget": float("nan")}
        w_rob = np.zeros(w.shape)
        w_rob[m] = wr_
    else:
        lam, rms, p95, li = BS.choose_lambda(fit, S[m], Z[m], rho[m], w[m], WALL_RMS_CM / 100.0, cons)
        rinfo = {}
        w_rob = w
    reached = li["reached"]
    pred = fit(S, Z)
    info = {"penalty": lam, "weighted_rms_cm": rms * 100, "p95_cm": p95 * 100, "target_reached": reached,
            "rms_floor_cm": li["floor"] * 100, "rms_budget_cm": li["budget"] * 100, **rinfo,
            "coefficients": int(fit.ku.n * fit.kv.n), "knots": [fit.ku.n, fit.kv.n], "cells_w1": int((w == 1).sum()),
            "cells_w03": int((w == ARCH_WEIGHT).sum()), "cells_w0": int((w == 0).sum()), "cells_total": int(w.size),
            "end_slope_max": float(max(np.abs(fit.du(np.full(5, S_MIN), np.linspace(0.2, 1.2, 5))).max(),
                                       np.abs(fit.du(np.full(5, S_MAX), np.linspace(0.2, 1.2, 5))).max()))}
    print(f"  wall fit: lam {lam:.3g}, wRMS {rms * 100:.3f} cm, p95 {p95 * 100:.3f} cm, coefs {info['coefficients']}, reached {reached}", flush=True)
    return fit, {"s": s_grid, "z": z_grid, "rho": rho, "w": w, "w_robust": w_rob, "pred": pred, "y_h": y_h, "z_L": z_L, "cab": cab,
                 "mid": mid_info}, info


# ---------------------------------------------------------------- 4d top fields
def curve_scan(T, xs, ys, start_y, slope_thr, forward):
    pts = []
    skipped = []
    g = ys[1] - ys[0]
    for x in np.arange(COWL_X[0], COWL_X[1] + 1e-9, COWL_X[2]):
        ix = int(round((x - xs[0]) / g))
        col = T[ix]
        dz = np.full(len(col), np.nan)
        dz[1:-1] = (col[2:] - col[:-2]) / (2 * g)
        iy0 = int(round((start_y - ys[0]) / g))
        rng = range(iy0, len(col) - RUN_CM - 1) if not forward else range(iy0, RUN_CM, -1)
        for iy in rng:
            if not forward:
                seg = dz[iy:iy + RUN_CM + 1]
                ok = np.all(np.isfinite(seg)) and np.all(seg > slope_thr)
            else:
                seg = -dz[iy - RUN_CM:iy + 1]
                ok = np.all(np.isfinite(seg)) and np.all(seg > slope_thr)
            if ok:
                if iy != iy0:  # a hit at the start means no flat surface before the slope here: no detection
                    pts.append((x, ys[iy]))
                else:
                    skipped.append(float(x))
                break
    return np.array(pts), skipped


def fit_quadratic(pts):
    x, y = pts[:, 0], pts[:, 1]
    A = np.stack([np.ones_like(x), x ** 2], 1)
    co = np.linalg.lstsq(A, y, rcond=None)[0]
    r = y - A @ co
    rms = float(np.sqrt(np.mean(r ** 2)))
    keep = np.abs(r) <= CURVE_REJECT_K * rms
    co2 = np.linalg.lstsq(A[keep], y[keep], rcond=None)[0]
    r2 = y[keep] - A[keep] @ co2
    return co2, {"a": float(co2[0]), "b": float(co2[1]), "points": int(len(x)), "rejected": int((~keep).sum()),
                 "rms_cm": float(np.sqrt(np.mean(r2 ** 2)) * 100), "max_cm": float(np.abs(r2).max() * 100)}


def top_fields(maps):
    T = maps["TOP"]
    xs, ys = maps["xs"], maps["ys"]
    g = float(maps["grid"])
    cowl_pts, cowl_skip = curve_scan(T, xs, ys, COWL_START_Y, COWL_SLOPE, forward=False)
    bl_pts, bl_skip = curve_scan(T, xs, ys, BL_START_Y, BL_SLOPE, forward=True)
    cowl_co, cowl_info = fit_quadratic(cowl_pts)
    bl_co, bl_info = fit_quadratic(bl_pts)
    cowl_info["start_hits_discarded_x"] = cowl_skip
    bl_info["start_hits_discarded_x"] = bl_skip
    print(f"  cowl y = {cowl_co[0]:.4f} + {cowl_co[1]:.4f} x^2 ({cowl_info}); backlight y = {bl_co[0]:.4f} + {bl_co[1]:.4f} x^2 ({bl_info})", flush=True)
    # slope magnitude on the clean TOP (symmetric at x = 0)
    Tm = np.concatenate([T[1:2][::-1], T], 0)  # mirror row for x = -0.01
    gx = np.full(T.shape, np.nan)
    gx[:-1] = (Tm[2:] - Tm[:-2]) / (2 * g)
    gy = np.full(T.shape, np.nan)
    gy[:, 1:-1] = (T[:, 2:] - T[:, :-2]) / (2 * g)
    smag = np.sqrt(gx ** 2 + gy ** 2)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    out = {}
    infos = {}
    for name, yr, side in (("A_front", A_FRONT_Y, "front"), ("A_rear", A_REAR_Y, "rear")):
        dom = (X >= TOP_X[0] - 1e-9) & (X <= TOP_X[1] + 1e-9) & (Y >= yr[0] - 1e-9) & (Y <= yr[1] + 1e-9)
        if side == "front":
            sel = Y < (cowl_co[0] + cowl_co[1] * X ** 2) - COWL_MARGIN
        else:
            sel = Y > (bl_co[0] + bl_co[1] * X ** 2) + COWL_MARGIN
        m = dom & sel & np.isfinite(T) & np.isfinite(smag) & (smag < TOP_SLOPE_MAX)
        fit = BS.Fit2D(BS.Knots(TOP_X[0], TOP_X[1], TOP_KNOT), BS.Knots(yr[0], yr[1], TOP_KNOT))
        cons = fit.du_constraint(0.0)
        # inpainted cells (accessory boxes, wing-rejected cells) are not measured: weight 0.3, as the plan
        # does for the arch openings in the wall field (BT1 deviation)
        if V2:
            # plan 6.1: inpainted cells weight 0; robust passes at the v01 penalty x factor
            w = np.where(maps["TOP_excl"][m], 0.0, 1.0)
            lam = v01_penalties()[name] * BP.PENALTY_FACTOR
            _, wr_, rinfo = robust_fit(fit, X[m], Y[m], T[m], w, lam, cons)
            rms, p95 = rinfo["weighted_rms_cm"] / 100, rinfo["p95_cm"] / 100
            li = {"reached": None, "floor": float("nan"), "budget": float("nan")}
        else:
            w = np.where(maps["TOP_excl"][m], ARCH_WEIGHT, 1.0)
            lam, rms, p95, li = BS.choose_lambda(fit, X[m], Y[m], T[m], w, TOP_RMS_CM / 100.0, cons)
            rinfo = {}
        reached = li["reached"]
        infos[name] = {"penalty": lam, "weighted_rms_cm": rms * 100, "p95_cm": p95 * 100, "target_reached": reached,
                       "rms_floor_cm": li["floor"] * 100, "rms_budget_cm": li["budget"] * 100, **rinfo,
                       "coefficients": int(fit.ku.n * fit.kv.n), "cells": int(m.sum()),
                       "inpainted_cells_w03": int((w < 1).sum())}
        print(f"  {name}: lam {lam:.3g}, RMS {rms * 100:.3f} cm, p95 {p95 * 100:.3f} cm, cells {int(m.sum())}, reached {reached}", flush=True)
        out[name] = fit
        out[name + "_mask"] = m
    return out, cowl_co, bl_co, cowl_pts, bl_pts, {"cowl": cowl_info, "backlight": bl_info, **infos}


class TopU:
    def __init__(self, tops, ref):
        self.f, self.r, self.ref = tops["A_front"], tops["A_rear"], ref

    def __call__(self, x, y):
        x = np.clip(np.asarray(x, float), TOP_X[0], TOP_X[1])
        y = np.asarray(y, float)
        af = self.f(x, np.clip(y, A_FRONT_Y[0], A_FRONT_Y[1]))
        ar = self.r(x, np.clip(y, A_REAR_Y[0], A_REAR_Y[1]))
        zb = self.ref.z_B(y)
        wf = smoothstep((y - (Y_CAB0 - U_BLEND)) / U_BLEND)  # 0 at -0.92, 1 at -0.82
        wr = smoothstep((y - Y_CAB1) / U_BLEND)  # 0 at 1.63, 1 at 1.73
        u = np.where(y <= Y_CAB0, (1 - wf) * af + wf * zb, np.where(y < Y_CAB1, zb, (1 - wr) * zb + wr * ar))
        return u


# ---------------------------------------------------------------- 4e rounds
class Station:
    """Wall and top curves of one station in its plane (rho, z)."""

    def __init__(self, s, wall, U, ref, env, cowl_co, bl_co, zL, zenv=None):
        self.s = s
        self.zenv = float(zL) if zenv is None else float(zenv)
        Ox, Oy, nx, ny = frame(s)
        self.O = (float(Ox[0]), float(Oy[0]))
        self.n = (float(nx[0]), float(ny[0]))
        self.zL = float(zL)
        self.env = env
        self.cowl, self.bl = cowl_co, bl_co
        self.U = U
        zw = np.arange(self.zL, WALL_ZMAX + 1e-9, PROFILE_STEP)
        self.wz = zw
        self.wr = wall(np.full(len(zw), s), zw)
        d = wall.dv(np.full(len(zw), s), zw)
        nrm = np.sqrt(1 + d ** 2)
        self.wn = np.stack([1 / nrm, -d / nrm], 1)  # outward normal (rho, z)
        rr = np.arange(0.0, 1.30 + 1e-9, PROFILE_STEP)
        self.tr = rr
        self.tz = U(self.O[0] + rr * self.n[0], self.O[1] + rr * self.n[1])
        dt = np.gradient(self.tz, rr)
        nrm = np.sqrt(1 + dt ** 2)
        self.tn = np.stack([-dt / nrm, 1 / nrm], 1)  # upward normal
        # corner: lowest z where the wall point reaches the top surface
        f = self.wz - U(self.O[0] + self.wr * self.n[0], self.O[1] + self.wr * self.n[1])
        sc = np.where((f[:-1] < 0) & (f[1:] >= 0))[0]
        if len(sc):
            i = sc[0]
            t = f[i] / (f[i] - f[i + 1])
            self.corner = (float(self.wr[i] + t * (self.wr[i + 1] - self.wr[i])), float(self.wz[i] + t * (self.wz[i + 1] - self.wz[i])))
        else:
            self.corner = None

    def to3d(self, rho, z):
        return np.stack([self.O[0] + rho * self.n[0], self.O[1] + rho * self.n[1], z], -1)

    def round(self, R):
        """All valid centres of a round of radius R: intersections of the wall curve offset inward by R
        and the top curve offset downward by R (polyline-polyline, coarse 1 cm then 2 mm), kept when
        the circle does not cut the used parts of the curves and turns the short way."""
        wo = np.stack([self.wr, self.wz], 1) - R * self.wn
        to = np.stack([self.tr, self.tz], 1) - R * self.tn
        ref = np.array(self.corner) if self.corner is not None else np.array([self.wr[-1], self.wz[-1]])
        hits = seg_intersections(wo, to, COARSE)
        valid = []
        for (i, t, j, u) in hits:
            Cc = wo[i] + t * (wo[i + 1] - wo[i])
            Pw = np.array([self.wr[i] + t * (self.wr[i + 1] - self.wr[i]), self.wz[i] + t * (self.wz[i + 1] - self.wz[i])])
            Pt = np.array([self.tr[j] + u * (self.tr[j + 1] - self.tr[j]), self.tz[j] + u * (self.tz[j + 1] - self.tz[j])])
            zw_t = float(Pw[1])
            # a round of a convex corner touches the wall below the corner and the top inward of it
            if self.corner is not None and (zw_t > self.corner[1] + 1e-6 or Pt[0] > self.corner[0] + 1e-6):
                continue
            mw = self.wz <= zw_t + 1e-9
            mt = self.tr <= Pt[0] + 1e-9
            dw = np.min(np.hypot(self.wr[mw] - Cc[0], self.wz[mw] - Cc[1])) if mw.any() else R
            dt = np.min(np.hypot(self.tr[mt] - Cc[0], self.tz[mt] - Cc[1])) if mt.any() else R
            if dw < R * (1 - ROUND_TOL) or dt < R * (1 - ROUND_TOL):
                continue
            a0 = math.atan2(Pw[1] - Cc[1], Pw[0] - Cc[0])
            a1 = math.atan2(Pt[1] - Cc[1], Pt[0] - Cc[0])
            if (a1 - a0) % (2 * math.pi) > math.pi:
                continue
            valid.append({"C": Cc, "Pw": Pw, "Pt": Pt, "zw_t": zw_t, "R": R, "d_corner": float(np.linalg.norm(Cc - ref))})
        if not valid:
            return None
        valid.sort(key=lambda c: c["d_corner"])
        return valid

    def round_halving(self, R):
        """All valid rounds at R, halving R until there is at least one."""
        halv = 0
        rr = R
        while rr >= 1e-3:
            out = self.round(rr)
            if out is not None:
                for c in out:
                    c["halvings"] = halv
                return out
            rr *= 0.5
            halv += 1
        return None

    def env_rms(self, rd, E):
        d = poly_dist(E, self.built_polyline(rd))
        return float(np.sqrt(np.mean(d ** 2)))

    def arc(self, rd, n):
        Cc, Pw, Pt = rd["C"], rd["Pw"], rd["Pt"]
        a0 = math.atan2(Pw[1] - Cc[1], Pw[0] - Cc[0])
        a1 = math.atan2(Pt[1] - Cc[1], Pt[0] - Cc[0])
        while a1 < a0:
            a1 += 2 * math.pi
        R = float(np.linalg.norm(Pw - Cc))
        R2 = float(np.linalg.norm(Pt - Cc))
        fr = np.arange(1, n + 1) / n if n > 0 else np.array([])
        ang = a0 + fr * (a1 - a0)
        rad = R + fr * (R2 - R)
        return np.stack([Cc[0] + rad * np.cos(ang), Cc[1] + rad * np.sin(ang)], 1), math.degrees(a1 - a0)

    def end_rho(self, rho_t, zone):
        if zone == "cabin":
            return max(rho_t - LEDGE_W, 0.0), "ledge"
        rr = np.arange(rho_t, -1e-9, -PROFILE_STEP)
        p = self.to3d(rr, np.zeros_like(rr))
        x, y = np.abs(p[:, 0]), p[:, 1]
        if zone == "front":
            g = y - (self.cowl[0] + self.cowl[1] * x ** 2 - END_CURVE_MARGIN)
        else:
            g = (self.bl[0] + self.bl[1] * x ** 2 + END_CURVE_MARGIN) - y
        hit = np.where(g >= 0)[0]
        if len(hit):
            k = hit[0]
            if k == 0:
                return float(rho_t), "curve at tangent"
            t = g[k - 1] / (g[k - 1] - g[k])
            return float(rr[k - 1] + t * (rr[k] - rr[k - 1])), "cowl" if zone == "front" else "backlight"
        return 0.0, "centre"

    def profile(self, rd, zone, n_wall=N_WALL, n_arc=N_ARC, n_top=N_TOP):
        zt = rd["zw_t"]
        if V2:
            # plan 6.4: 4 rows from z_L up to z_env, 27 rows from z_env to the wall tangent point
            ze = self.zenv
            if ze > zt - 0.02:  # envelope at or above the tangent: even rows instead (BT1 v02 deviation)
                ze = self.zL + (zt - self.zL) * N_WALL_LOW / (n_wall - 1)
                self.env_fallback = True
            zw = np.concatenate([self.zL + (ze - self.zL) * np.arange(N_WALL_LOW) / N_WALL_LOW,
                                 ze + (zt - ze) * np.arange(N_WALL_HIGH) / (N_WALL_HIGH - 1)])
        else:
            zw = self.zL + (zt - self.zL) * np.arange(n_wall) / (n_wall - 1)
        wall = np.stack([np.interp(zw, self.wz, self.wr), zw], 1)
        wall[-1] = rd["Pw"]
        arc, sweep = self.arc(rd, n_arc)
        rho_t = float(rd["Pt"][0])
        rho_end, how = self.end_rho(rho_t, zone)
        k = np.arange(1, n_top + 1)
        rk = rho_t - (rho_t - rho_end) * (k / n_top) ** TOP_EXP
        top = np.stack([rk, self.U(self.O[0] + rk * self.n[0], self.O[1] + rk * self.n[1])], 1)
        return np.vstack([wall, arc, top]), {"rho_end": rho_end, "end": how, "sweep_deg": sweep}

    def built_polyline(self, rd):
        zt = rd["zw_t"]
        m = self.wz <= zt
        wall = np.stack([self.wr[m], self.wz[m]], 1)
        arc, _ = self.arc(rd, 24)
        mt = self.tr <= rd["Pt"][0]
        top = np.stack([self.tr[mt], self.tz[mt]], 1)[::-1]
        return np.vstack([wall, rd["Pw"][None], arc, top])

    def envelope_points(self):
        if self.corner is None:
            return None
        P0 = np.array([self.corner[0] - ENV_INSET, self.corner[1] - ENV_INSET])
        d = np.stack([np.cos(ENV_ANGLES), np.sin(ENV_ANGLES)], 1)
        P = np.repeat(P0[None], len(d), 0)
        pts = march_plane(self.env, self.O[0], self.O[1], self.n[0], self.n[1], P, d)
        return pts[np.isfinite(pts[:, 0])]


def _seg_hits(P, Q):
    """Intersections between consecutive segments of polylines P and Q: list of (i, t, j, u)."""
    p = P[:-1]
    r = P[1:] - P[:-1]
    q = Q[:-1]
    sv = Q[1:] - Q[:-1]
    qp = q[None, :, :] - p[:, None, :]
    den = r[:, None, 0] * sv[None, :, 1] - r[:, None, 1] * sv[None, :, 0]
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (qp[..., 0] * sv[None, :, 1] - qp[..., 1] * sv[None, :, 0]) / den
        u = (qp[..., 0] * r[:, None, 1] - qp[..., 1] * r[:, None, 0]) / den
    ok = (np.abs(den) > 1e-15) & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1)
    ii, jj = np.where(ok)
    return [(int(i), float(t[i, j]), int(j), float(u[i, j])) for i, j in zip(ii, jj)]


def seg_intersections(P, Q, k):
    """Coarse-to-fine polyline intersection: every k-th point first, then the fine segments inside each
    coarse hit. Returns (i, t, j, u) on the fine polylines."""
    ci = np.arange(0, len(P), k)
    if ci[-1] != len(P) - 1:
        ci = np.append(ci, len(P) - 1)
    cj = np.arange(0, len(Q), k)
    if cj[-1] != len(Q) - 1:
        cj = np.append(cj, len(Q) - 1)
    out = []
    seen = set()
    for (a, _, b, _) in _seg_hits(P[ci], Q[cj]):
        i0, i1 = ci[a], ci[a + 1]
        j0, j1 = cj[b], cj[b + 1]
        # widen by one coarse step so a crossing near a coarse vertex is not lost
        i0, i1 = max(0, i0 - k), min(len(P) - 1, i1 + k)
        j0, j1 = max(0, j0 - k), min(len(Q) - 1, j1 + k)
        for (i, t, j, u) in _seg_hits(P[i0:i1 + 1], Q[j0:j1 + 1]):
            key = (i + i0, j + j0)
            if key not in seen:
                seen.add(key)
                out.append((i + i0, t, j + j0, u))
    return out


def poly_dist(pts, poly):
    a = poly[:-1]
    b = poly[1:]
    ab = b - a
    L2 = np.maximum(np.sum(ab ** 2, 1), 1e-18)
    out = np.empty(len(pts))
    for i, p in enumerate(pts):
        t = np.clip(np.sum((p - a) * ab, 1) / L2, 0, 1)
        q = a + t[:, None] * ab
        out[i] = np.sqrt(np.min(np.sum((q - p) ** 2, 1)))
    return out


def zone_of(s):
    if s < Y_FAN_FRONT:
        return "nose"
    if s > Y_FAN_REAR:
        return "tail"
    if s < Y_CAB0:
        return "front side"
    if s > Y_CAB1:
        return "rear side"
    return "cabin"


def end_zone(s):
    z = zone_of(s)
    return "cabin" if z == "cabin" else ("front" if z in ("nose", "front side") else "rear")


def smooth_lower(env, ref, s_mesh):
    """Plan 6.4: z_L smoothed (Gaussian 0.10 m of s) outside the arch spans, legs sharp; z_env = running
    max of z_L over +-0.10 m, Gaussian 0.05 m, then max(z_env, z_L). Computed on a 1 cm s grid."""
    sf = np.arange(S_MIN, S_MAX + 1e-9, ZL_FINE_STEP)
    Ox, Oy, nx, ny = frame(sf)
    rp = march_rays(env, Ox, Oy, nx, ny, np.full(len(sf), Z_PROBE))
    yh = Oy + rp * ny
    zl = ref.z_L_at_y(yh)
    px = C.Y_to_px(yh)
    in_arch = np.zeros(len(sf), bool)
    for (lf, lr) in ref.lines["legs_px"]:
        in_arch |= (px > lf) & (px < lr)
    zs = zl.copy()
    sig = ZL_SMOOTH / ZL_FINE_STEP
    i = 0
    while i < len(sf):
        if in_arch[i]:
            i += 1
            continue
        j = i
        while j < len(sf) and not in_arch[j]:
            j += 1
        if j - i > 2:
            zs[i:j] = C.gauss1d(zl[i:j], sig)
        i = j
    h = int(round(ENV_WIN / ZL_FINE_STEP))
    run = np.array([zs[max(0, k - h): k + h + 1].max() for k in range(len(sf))])
    ze = np.maximum(C.gauss1d(run, ENV_SIGMA / ZL_FINE_STEP), zs)
    # stations take the nearest fine sample so the legs stay sharp
    k = np.clip(np.round((s_mesh - S_MIN) / ZL_FINE_STEP).astype(int), 0, len(sf) - 1)
    info = {"z_L_change_max_cm": float(np.max(np.abs(zs - zl)) * 100),
            "z_env_minus_z_L_max_cm": float(np.max(ze - zs) * 100)}
    return zs[k], ze[k], info


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    os.makedirs(DEBUG_DIR, exist_ok=True)
    maps = np.load(os.path.join(IN_DIR, "maps.npz"))
    with open(os.path.join(IN_DIR, "reference-lines.json"), encoding="utf-8") as f:
        lines = json.load(f)
    env = Envelope(maps)
    ref = RefLines(lines)

    print("4c wall field", flush=True)
    wall, wd, wall_info = wall_field(env, ref)
    print("4d top fields", flush=True)
    tops, cowl_co, bl_co, cowl_pts, bl_pts, top_info = top_fields(maps)
    U = TopU(tops, ref)

    print("4e rounds", flush=True)
    s_mesh = np.linspace(S_MIN, S_MAX, int(math.ceil((S_MAX - S_MIN) / MESH_S_STEP)) + 1)
    Ox, Oy, nx, ny = frame(s_mesh)
    rho_p = march_rays(env, Ox, Oy, nx, ny, np.full(len(s_mesh), Z_PROBE))
    zL = ref.z_L_at_y(Oy + rho_p * ny)
    zenv = zL.copy()
    zl_info = {}
    if V2:
        zL, zenv, zl_info = smooth_lower(env, ref, s_mesh)
    stations = [Station(s, wall, U, ref, env, cowl_co, bl_co, z, ze) for s, z, ze in zip(s_mesh, zL, zenv)]
    no_corner = [i for i, st in enumerate(stations) if st.corner is None]
    R_grid = np.arange(R_RANGE[0], R_RANGE[1] + 1e-9, R_STEP)
    R_star = np.full(len(s_mesh), np.nan)
    R_rms = np.full(len(s_mesh), np.nan)
    tt = time.time()
    for i, st in enumerate(stations):
        if zone_of(st.s) == "cabin" or st.corner is None:
            continue
        E = st.envelope_points()
        if E is None or len(E) < 5:
            continue
        best = None
        for R in R_grid:
            cands = st.round(R)
            if cands is None:
                continue
            for rd in cands:
                rms = st.env_rms(rd, E)
                if best is None or rms < best[0]:
                    best = (rms, R)
        if best is not None:
            R_star[i] = best[1]
            R_rms[i] = best[0]
    print(f"  R search {time.time() - tt:.1f} s; stations with R* {np.isfinite(R_star).sum()}", flush=True)
    # median of 5, P-spline along s, cabin R and blends
    R_med = np.full(len(s_mesh), np.nan)
    h = R_MEDIAN_N // 2
    for i in range(len(s_mesh)):
        seg = R_star[max(0, i - h): i + h + 1]
        seg = seg[np.isfinite(seg)]
        if len(seg) and np.isfinite(R_star[i]):
            R_med[i] = np.median(seg)
    rf = BS.Fit1D(BS.Knots(S_MIN, S_MAX, R_KNOT))
    wR = np.isfinite(R_med).astype(float)
    rf.fit(s_mesh, np.nan_to_num(R_med), wR, R_SPLINE_LAM)
    R_sp = np.clip(rf(s_mesh), *R_RANGE)
    if V2:
        hb = R_CAB_BLEND_V2 / 2
        w_c0 = smoothstep((s_mesh - (Y_CAB0 - hb)) / R_CAB_BLEND_V2)
        w_c1 = smoothstep(((Y_CAB1 + hb) - s_mesh) / R_CAB_BLEND_V2)
    else:
        w_c0 = smoothstep((s_mesh - (Y_CAB0 - R_CAB_BLEND)) / R_CAB_BLEND)
        w_c1 = smoothstep(((Y_CAB1 + R_CAB_BLEND) - s_mesh) / R_CAB_BLEND)
    w_cab = np.minimum(w_c0, w_c1)
    R_fin = (1 - w_cab) * R_sp + w_cab * BELT_ROUND_R

    # final profiles and mesh
    print("4f mesh", flush=True)
    NR = N_WALL + N_ARC + N_TOP
    P = np.zeros((len(s_mesh), NR, 3))
    meta = []
    halv = []
    prev_C = None
    n_multi = 0
    for i, st in enumerate(stations):
        cands = st.round_halving(R_fin[i])
        if cands is None:
            raise RuntimeError(f"no round at station {i} s={st.s:.3f}")
        if len(cands) > 1:
            n_multi += 1
        if prev_C is not None:
            # continuity: the candidate whose centre and both tangent points are nearest the previous
            # station's (planes rotate continuously; where a curve bends with about the round's radius the
            # centres nearly coincide but the tangent points do not)
            rd = min(cands, key=lambda c: np.linalg.norm(c["C"] - prev_C[0]) + np.linalg.norm(c["Pw"] - prev_C[1])
                     + np.linalg.norm(c["Pt"] - prev_C[2]))
        else:
            E = st.envelope_points()
            rd = min(cands, key=lambda c: st.env_rms(c, E)) if E is not None and len(E) >= 5 else cands[0]
        prev_C = (rd["C"], rd["Pw"], rd["Pt"])
        halv.append(rd["halvings"])
        prof, pm = st.profile(rd, end_zone(st.s))
        P[i] = st.to3d(prof[:, 0], prof[:, 1])
        meta.append({"s": float(st.s), "zone": zone_of(st.s), "R": float(rd["R"]), "R_target": float(R_fin[i]),
                     "halvings": int(rd["halvings"]), "z_L": st.zL, "z_wall_tangent": rd["zw_t"],
                     "rho_top_tangent": float(rd["Pt"][0]), "z_top_tangent": float(rd["Pt"][1]), "z_env": float(st.zenv),
                     "corner": st.corner, "rho_end": pm["rho_end"], "end": pm["end"], "arc_sweep_deg": pm["sweep_deg"]})
    P[np.abs(P[..., 0]) < 1e-9, 0] = 0.0
    verts = P.reshape(-1, 3)
    NS = len(s_mesh)

    def vid(i, r):
        return i * NR + r

    faces = []
    for i in range(NS - 1):
        for r in range(NR - 1):
            faces.append([vid(i, r), vid(i + 1, r), vid(i + 1, r + 1), vid(i, r + 1)])
    faces = np.array(faces)
    # weld coincident points
    key = np.round(verts / WELD).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    vw = verts[first]
    lower = np.zeros(len(vw), bool)
    lower[inv[[vid(i, 0) for i in range(NS)]]] = True
    out_faces = []
    dropped = 0
    tris = 0
    for f in faces:
        g = [int(inv[v]) for v in f]
        u = []
        for v in g:
            if v not in u:
                u.append(v)
        if len(u) < 3:
            dropped += 1
            continue
        pts = vw[u]
        if len(u) == 3:
            area = 0.5 * np.linalg.norm(np.cross(pts[1] - pts[0], pts[2] - pts[0]))
        else:
            area = 0.5 * np.linalg.norm(np.cross(pts[2] - pts[0], pts[3] - pts[1]))
        if area < 1e-10:
            dropped += 1
            continue
        if len(u) == 3:
            tris += 1
        out_faces.append(u + [-1] * (4 - len(u)))
    out_faces = np.array(out_faces)
    # pole: the welded point shared by the most stations' last rows
    last = inv[[vid(i, NR - 1) for i in range(NS)]]
    vals, cnt = np.unique(last, return_counts=True)
    pole = int(vals[np.argmax(cnt)]) if cnt.max() > 1 else -1
    # pole points: the welded vertex shared by the last rows of each fan (front, rear) if any
    pole_pts = []
    for fan in (s_mesh < Y_FAN_FRONT, s_mesh > Y_FAN_REAR):
        idxs = inv[[vid(i, NR - 1) for i in np.where(fan)[0]]]
        v, c = np.unique(idxs, return_counts=True)
        if c.max() > 1:
            pole_pts.append(vw[v[np.argmax(c)]])
    np.savez_compressed(os.path.join(OUT_DIR, "tub-mesh.npz"), verts=vw, faces=out_faces, lower=lower, pole=pole,
                        grid=P, s=s_mesh, pole_pts=np.array(pole_pts))
    print(f"  mesh: {NS} stations x {NR} rows, verts {len(vw)} (welded from {len(verts)}), faces {len(out_faces)} "
          f"(triangles {tris}, dropped {dropped}), pole {pole} shared by {int(cnt.max())} stations", flush=True)

    # numbers for the report
    zones = ["nose", "front side", "cabin", "rear side", "tail"]
    rz = {}
    for zname in zones:
        sel = [m for m in meta if m["zone"] == zname]
        Rs = np.array([m["R"] for m in sel])
        rz[zname] = {"stations": len(sel), "min": float(Rs.min()), "median": float(np.median(Rs)), "max": float(Rs.max()),
                     "halved": int(sum(1 for m in sel if m["halvings"] > 0))}
    shoulder = {}
    for Yq in (-1.27, 0.0, 1.27):
        st = Station(Yq, wall, U, ref, env, cowl_co, bl_co, ref.z_L_at_y(np.array([Yq]))[0])
        R = float(np.interp(Yq, s_mesh, R_fin))
        rd = st.round_halving(R)[0]
        shoulder[str(Yq)] = {"corner_z": st.corner[1] if st.corner else None, "corner_x": st.corner[0] if st.corner else None,
                             "top_tangent_z": float(rd["Pt"][1]), "wall_tangent_z": rd["zw_t"], "R": rd["R"]}
    ends = {}
    for m in meta:
        ends[m["end"]] = ends.get(m["end"], 0) + 1
    info = {
        "frame": {"S_MIN": S_MIN, "S_MAX": S_MAX, "mesh_stations": NS, "mesh_s_spacing": float(s_mesh[1] - s_mesh[0])},
        "wall": wall_info, "tops": top_info,
        "rounds": {"stations_with_several_valid_centres": n_multi,
                   "solved_at_first_R": int(sum(1 for hh in halv if hh == 0)), "needed_halving": int(sum(1 for hh in halv if hh > 0)),
                   "stations_without_corner": no_corner, "by_zone": rz, "R_spline_penalty": R_SPLINE_LAM,
                   "R_star_count": int(np.isfinite(R_star).sum()), "R_star_rms_median_cm": float(np.nanmedian(R_rms) * 100),
                   "arc_sweep_deg": {"min": float(min(m["arc_sweep_deg"] for m in meta)), "max": float(max(m["arc_sweep_deg"] for m in meta))}},
        "ends": ends, "shoulder": shoulder, "version": BP.VERSION, "variant": BP.VARIANT if V2 else None,
        "lower_line": zl_info, "env_row_fallback_stations": int(sum(1 for st in stations if getattr(st, "env_fallback", False))),
        "mesh": {"verts_half": int(len(vw)), "faces_half": int(len(out_faces)), "triangles": tris, "dropped": dropped,
                 "pole": pole, "pole_stations": int(cnt.max())},
        "cowl_curve": [float(cowl_co[0]), float(cowl_co[1])], "backlight_curve": [float(bl_co[0]), float(bl_co[1])],
        "stations": meta,
    }
    save_json("bt1-fields.json", info)
    np.savez_compressed(os.path.join(OUT_DIR, "bt1-fields-debug.npz"), s=wd["s"], z=wd["z"], rho=wd["rho"], w=wd["w"],
                        w_robust=wd["w_robust"], z_env=np.array([m["z_env"] for m in meta]),
                        pred=wd["pred"], y_h=wd["y_h"], z_L=wd["z_L"], s_mesh=s_mesh, R_star=R_star, R_med=R_med,
                        R_sp=R_sp, R_fin=R_fin, cowl_pts=cowl_pts, bl_pts=bl_pts,
                        A_front_mask=tops["A_front_mask"], A_rear_mask=tops["A_rear_mask"],
                        zw_t=np.array([m["z_wall_tangent"] for m in meta]), zt_t=np.array([m["z_top_tangent"] for m in meta]),
                        corner_z=np.array([m["corner"][1] if m["corner"] else np.nan for m in meta]))
    print(f"rounds by zone {rz}; ends {ends}; shoulder {shoulder}")
    print(f"done in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
