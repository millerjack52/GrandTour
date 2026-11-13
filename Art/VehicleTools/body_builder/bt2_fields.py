"""BT2 (greenhouse master on the P4 tub), plan docs/BODY_BUILDER_PLAN.md section 7, steps 7a-7i in numpy.

7a: the P4 tub refitted with exact centre-plane symmetry (wall, tops and the R spline).
7b-7f: greenhouse frame, wall field Dg, roof field A_roof, header/rail rounds, base and footprint.
7g: tub top rows end on the footprint. 7h: both meshes as grids. 7i: glass tags.
System Python (numpy + PIL). Writes body-mesh.npz, bt2-fields.json, bt2-fields-debug.npz.
"""
import json
import math
import os
import sys
import time

os.environ.setdefault("BT_VERSION", "v02")
os.environ.setdefault("BT_VARIANT", "P4")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import bspline as BS  # noqa: E402
import bt1_fields as F  # noqa: E402

C = F.C
# BT2 run: BT2_VERSION v01 (section 7) or v02 (section 8); BT2_VARIANT R100 / R60 (v02 only)
BT2_VERSION = os.environ.get("BT2_VERSION", "v01")
BV2 = BT2_VERSION != "v01"
BT2_VARIANT = os.environ.get("BT2_VARIANT", "R100")
ROUND_SCALE = {"R100": 1.0, "R60": 0.6}[BT2_VARIANT] if BV2 else 1.0
R_FLOOR = 0.03
OUT_ROOT = os.path.join(C.ROOT, r"Art\Export\VehicleTools", "impreza-builder-bt2-" + BT2_VERSION)
OUT_DIR = os.path.join(OUT_ROOT, BT2_VARIANT) if BV2 else OUT_ROOT
DEBUG_DIR = os.path.join(OUT_DIR, "debug")
if BV2:
    F.SLOPE_RULE_MID = True  # plan 8.1
    F.U_BLEND = 0.30  # plan 8.2
SMOOTH = 4.0
# 7b
Y_GF, Y_GR, RHO0_G = 0.05, 0.85, 0.75
SG_MIN = Y_GF - RHO0_G * math.pi / 2
SG_MAX = Y_GR + RHO0_G * math.pi / 2
G_MARCH_START = 2.0
GZ = (0.95, 1.70)
G_STEP = 0.02
# 7c
G_SLOPE_MAX = 2.5
G_ABOVE_U = 0.03
G_KNOT_S, G_KNOT_Z = 0.10, 0.12
G_ROBUST_C_CM = 1.5
G_RMS_CM = 0.5  # floor-rule target, as the tub wall
# 7d
ROOF_ZMIN = 1.35
ROOF_SLOPE = 0.45
ROOF_X = (0.0, 0.85)
ROOF_Y = (-0.65, 1.55)
ROOF_KNOT = 0.20
ROOF_RMS_CM = 0.4  # floor-rule target, as the tub tops
# 7e
GR_RANGE = (0.03, 0.30)
GR_STEP = 0.005
# 7h
G_MESH_STEP = 0.03
G_N_WALL, G_N_ARC, G_N_ROOF = 24, 16, 12
ROOF_EXP = 1.3
# 7i
GLASS_ROWS = (150, 360)
GLASS_ABOVE_BASE = 0.06
GLASS_BELOW_TANGENT = 0.04
GLASS_INBOARD = 0.09
# zones for reporting
HEADER_ANGLE = math.radians(45.0)


def save_json(name, data):
    with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)


# ------------------------------------------------------------------ 7a exact symmetry
_orig_robust = F.robust_fit


def robust_exact(fit, u, v, val, w0, lam, cons):
    """BT1 robust fit with the symmetry rows imposed exactly (null-space) instead of as penalty rows."""
    fit.exact = cons
    return _orig_robust(fit, u, v, val, w0, lam, None)


F.robust_fit = robust_exact


def r_spline(s, R_med, s0, s1, lam):
    rf = BS.Fit1D(BS.Knots(s0, s1, F.R_KNOT))
    w = np.isfinite(R_med).astype(float)
    rf.fit(s, np.nan_to_num(R_med), w, lam, exact_ends=True)
    return rf


def median5(a):
    out = np.full(len(a), np.nan)
    h = F.R_MEDIAN_N // 2
    for i in range(len(a)):
        seg = a[max(0, i - h): i + h + 1]
        seg = seg[np.isfinite(seg)]
        if len(seg) and np.isfinite(a[i]):
            out[i] = np.median(seg)
    return out


# ------------------------------------------------------------------ greenhouse frame
def gframe(s):
    s = np.atleast_1d(np.asarray(s, float))
    Ox = np.zeros_like(s)
    Oy = s.copy()
    nx = np.ones_like(s)
    ny = np.zeros_like(s)
    f = s < Y_GF
    a = (Y_GF - s[f]) / RHO0_G
    Oy[f] = Y_GF
    nx[f], ny[f] = np.cos(a), -np.sin(a)
    r = s > Y_GR
    a = (s[r] - Y_GR) / RHO0_G
    Oy[r] = Y_GR
    nx[r], ny[r] = np.cos(a), np.sin(a)
    nx[np.abs(nx) < 1e-12] = 0.0
    return Ox, Oy, nx, ny


def gzone(s):
    if s < Y_GF:
        return "windscreen header" if (Y_GF - s) / RHO0_G > HEADER_ANGLE else "front corner"
    if s > Y_GR:
        return "backlight header" if (s - Y_GR) / RHO0_G > HEADER_ANGLE else "rear corner"
    return "side rail"


class Roof:
    def __init__(self, fit):
        self.f = fit

    def __call__(self, x, y):
        return self.f(np.clip(np.abs(np.asarray(x, float)), *ROOF_X), np.clip(np.asarray(y, float), *ROOF_Y))


# ------------------------------------------------------------------ 7c, 7d fits
def greenhouse_wall(env, U):
    s_grid = np.arange(SG_MIN, SG_MAX + 1e-9, G_STEP)
    if SG_MAX - s_grid[-1] > 1e-6:
        s_grid = np.append(s_grid, SG_MAX)
    z_grid = np.arange(GZ[0], GZ[1] + 1e-9, G_STEP)
    S, Z = np.meshgrid(s_grid, z_grid, indexing="ij")
    Ox, Oy, nx, ny = gframe(S.ravel())
    rho = F.march_rays(env, Ox, Oy, nx, ny, Z.ravel(), start=G_MARCH_START).reshape(S.shape)
    fin = np.isfinite(rho)
    d = np.full(rho.shape, np.nan)
    d[:, 1:-1] = (rho[:, 2:] - rho[:, :-2]) / (2 * G_STEP)
    d[:, 0] = (rho[:, 1] - rho[:, 0]) / G_STEP
    d[:, -1] = (rho[:, -1] - rho[:, -2]) / G_STEP
    xh = Ox.reshape(S.shape) + np.nan_to_num(rho) * nx.reshape(S.shape)
    yh = Oy.reshape(S.shape) + np.nan_to_num(rho) * ny.reshape(S.shape)
    above = Z >= U(np.abs(xh), yh) + G_ABOVE_U
    if BV2:
        # plan 8.1: range from the base estimate (lowest finite cell at least 3 cm above U) to the highest finite cell
        zlo = np.array([z_grid[fin[i] & above[i]].min() if (fin[i] & above[i]).any() else np.nan for i in range(len(s_grid))])
        zhi = np.array([z_grid[fin[i]].max() if fin[i].any() else np.nan for i in range(len(s_grid))])
        ok, smid, zend = F.mid_slope_valid(d, z_grid, zlo, zhi)
        w = (ok & above).astype(float)
        mid = {"slope_mid": smid, "z_end": zend, "z_lo": zlo, "z_hi": zhi}
    else:
        w = (fin & (np.abs(np.nan_to_num(d, nan=99.0)) <= G_SLOPE_MAX) & above).astype(float)
        mid = None
    fit = BS.Fit2D(BS.Knots(SG_MIN, SG_MAX, G_KNOT_S), BS.Knots(GZ[0], GZ[1], G_KNOT_Z))
    fit.exact = np.vstack([fit.du_constraint(SG_MIN), fit.du_constraint(SG_MAX)])
    m = w > 0
    lam0, rms0, p950, li = BS.choose_lambda(fit, S[m], Z[m], rho[m], w[m], G_RMS_CM / 100.0)
    lam = lam0 * SMOOTH
    F.ROBUST_C_CM = G_ROBUST_C_CM
    _, wr_, rinfo = _orig_robust(fit, S[m], Z[m], rho[m], w[m], lam, None)
    F.ROBUST_C_CM = 2.0
    w_rob = np.zeros(w.shape)
    w_rob[m] = wr_
    info = {"floor_rule_penalty": lam0, "penalty": lam, "rms_floor_cm": li["floor"] * 100, "rms_budget_cm": li["budget"] * 100,
            **rinfo, "coefficients": int(fit.ku.n * fit.kv.n), "cells_w1": int(m.sum()), "cells_total": int(w.size),
            "cells_no_crossing": int((~fin).sum())}
    return fit, {"s": s_grid, "z": z_grid, "rho": rho, "w": w, "w_robust": w_rob, "pred": fit(S, Z), "slope": d, "mid": mid}, info


def roof_field(maps):
    T = maps["TOP"]
    xs, ys = maps["xs"], maps["ys"]
    g = float(maps["grid"])
    Tm = np.concatenate([T[1:2], T], 0)
    gx = np.full(T.shape, np.nan)
    gx[:-1] = (Tm[2:] - Tm[:-2]) / (2 * g)
    gy = np.full(T.shape, np.nan)
    gy[:, 1:-1] = (T[:, 2:] - T[:, :-2]) / (2 * g)
    smag = np.sqrt(gx ** 2 + gy ** 2)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    dom = (X <= ROOF_X[1] + 1e-9) & (Y >= ROOF_Y[0] - 1e-9) & (Y <= ROOF_Y[1] + 1e-9)
    m = dom & np.isfinite(T) & np.isfinite(smag) & (T > ROOF_ZMIN) & (smag < ROOF_SLOPE)
    w = np.where(maps["TOP_excl"][m], 0.0, 1.0)
    fit = BS.Fit2D(BS.Knots(ROOF_X[0], ROOF_X[1], ROOF_KNOT), BS.Knots(ROOF_Y[0], ROOF_Y[1], ROOF_KNOT))
    fit.exact = fit.du_constraint(0.0)
    lam0, _, _, li = BS.choose_lambda(fit, X[m], Y[m], T[m], w, ROOF_RMS_CM / 100.0)
    lam = lam0 * SMOOTH
    F.ROBUST_C_CM = G_ROBUST_C_CM
    _, wr_, rinfo = _orig_robust(fit, X[m], Y[m], T[m], w, lam, None)
    F.ROBUST_C_CM = 2.0
    info = {"floor_rule_penalty": lam0, "penalty": lam, "rms_floor_cm": li["floor"] * 100, "rms_budget_cm": li["budget"] * 100,
            **rinfo, "coefficients": int(fit.ku.n * fit.kv.n), "cells": int(m.sum()), "inpainted_cells_w0": int((w == 0).sum())}
    return fit, m, info


# ------------------------------------------------------------------ greenhouse stations
class GStation(F.Station):
    def __init__(self, s, wall, roof, U, env):
        self.s = float(s)
        Ox, Oy, nx, ny = gframe(s)
        self.O = (float(Ox[0]), float(Oy[0]))
        self.n = (float(nx[0]), float(ny[0]))
        self.env = env
        self.U = roof
        self.Utub = U
        zw = np.arange(GZ[0], GZ[1] + 1e-9, F.PROFILE_STEP)
        self.wz = zw
        self.wr = wall(np.full(len(zw), s), zw)
        dd = wall.dv(np.full(len(zw), s), zw)
        nrm = np.sqrt(1 + dd ** 2)
        self.wn = np.stack([1 / nrm, -dd / nrm], 1)
        rr = np.arange(0.0, 1.20 + 1e-9, F.PROFILE_STEP)
        self.tr = rr
        self.tz = roof(self.O[0] + rr * self.n[0], self.O[1] + rr * self.n[1])
        dt = np.gradient(self.tz, rr)
        nrm = np.sqrt(1 + dt ** 2)
        self.tn = np.stack([-dt / nrm, 1 / nrm], 1)
        f = self.wz - roof(self.O[0] + self.wr * self.n[0], self.O[1] + self.wr * self.n[1])
        sc = np.where((f[:-1] < 0) & (f[1:] >= 0))[0]
        self.corner = None
        if len(sc):
            i = sc[0]
            t = f[i] / (f[i] - f[i + 1])
            self.corner = (float(self.wr[i] + t * (self.wr[i + 1] - self.wr[i])), float(self.wz[i] + t * (self.wz[i + 1] - self.wz[i])))
        # 7f base: lowest z >= 0.95 where the wall point is on the tub top
        x, y = self.O[0] + self.wr * self.n[0], self.O[1] + self.wr * self.n[1]
        fb = self.wz - U(np.abs(x), y)
        sb = np.where((fb[:-1] < 0) & (fb[1:] >= 0))[0]
        if fb[0] >= 0:
            self.z_base, self.base_how = float(self.wz[0]), "wall above tub top at 0.95"
        elif len(sb):
            i = sb[0]
            t = fb[i] / (fb[i] - fb[i + 1])
            self.z_base, self.base_how = float(self.wz[i] + t * (self.wz[i + 1] - self.wz[i])), "crossing"
        else:
            self.z_base, self.base_how = float(self.wz[-1]), "no crossing"
        self.rho_base = float(np.interp(self.z_base, self.wz, self.wr))
        self.zL = self.z_base

    def gprofile(self, rd):
        zt = rd["zw_t"]
        zb = min(self.z_base, zt)
        zw = zb + (zt - zb) * np.arange(G_N_WALL) / (G_N_WALL - 1)
        wall = np.stack([np.interp(zw, self.wz, self.wr), zw], 1)
        wall[-1] = rd["Pw"]
        arc, sweep = self.arc(rd, G_N_ARC)
        rho_t = float(rd["Pt"][0])
        k = np.arange(1, G_N_ROOF + 1)
        rk = rho_t - rho_t * (k / G_N_ROOF) ** ROOF_EXP
        roof = np.stack([rk, self.U(self.O[0] + rk * self.n[0], self.O[1] + rk * self.n[1])], 1)
        return np.vstack([wall, arc, roof]), {"sweep_deg": sweep, "base_clamped": zt < self.z_base}


# ------------------------------------------------------------------ tub stations with the 7g end rule
class TubStation(F.Station):
    footprint = None  # (N, 2) polyline in plan, x >= 0

    def end_rho(self, rho_t, zone):
        """7g: from the tangent point inward to the footprint crossing, else to the centre. If the ray meets
        the footprint only outboard of the tangent point (the base sits outside the tub's top tangent),
        the top has zero length (BT2 deviation; the literal rule would run a lid across the cabin)."""
        rho_far = 1.6
        P0 = np.array([self.O[0] + rho_far * self.n[0], self.O[1] + rho_far * self.n[1]])
        P1 = np.array([self.O[0], self.O[1]])
        fp = self.footprint
        hits = []
        r = P1 - P0
        for k in range(len(fp) - 1):
            a, b = fp[k], fp[k + 1]
            sv = b - a
            den = r[0] * sv[1] - r[1] * sv[0]
            if abs(den) < 1e-15:
                continue
            qp = a - P0
            t = (qp[0] * sv[1] - qp[1] * sv[0]) / den
            u = (qp[0] * r[1] - qp[1] * r[0]) / den
            if 0 <= t <= 1 and 0 <= u <= 1:
                hits.append(rho_far * (1 - t))
        inside = [h for h in hits if h <= rho_t + 1e-9]
        if inside:
            return float(max(inside)), "footprint"
        if hits:
            return float(rho_t), "footprint outboard of tangent"
        return 0.0, "centre"


def weld(P, flags):
    """Quads of a station x row grid P (NS, NR, 3), welded. flags: dict name -> bool array (NS, NR) of points.
    Returns verts, faces (padded -1), per-vertex flags, face map to grid quads (i, r)."""
    NS, NR, _ = P.shape
    verts = P.reshape(-1, 3).copy()
    verts[np.abs(verts[:, 0]) < 1e-9, 0] = 0.0
    key = np.round(verts / F.WELD).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    vw = verts[first]
    vflags = {k: np.zeros(len(vw), bool) for k in flags}
    for k, fl in flags.items():
        vflags[k][inv[np.where(fl.ravel())[0]]] = True
    faces, fmap = [], []
    dropped = 0
    for i in range(NS - 1):
        for r in range(NR - 1):
            g = [inv[i * NR + r], inv[(i + 1) * NR + r], inv[(i + 1) * NR + r + 1], inv[i * NR + r + 1]]
            u = []
            for v in g:
                if v not in u:
                    u.append(int(v))
            if len(u) < 3:
                dropped += 1
                continue
            p = vw[u]
            area = 0.5 * np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])) if len(u) == 3 else 0.5 * np.linalg.norm(np.cross(p[2] - p[0], p[3] - p[1]))
            if area < 1e-10:
                dropped += 1
                continue
            faces.append(u + [-1] * (4 - len(u)))
            fmap.append((i, r))
    return vw, np.array(faces), vflags, np.array(fmap), dropped


def main():
    t0 = time.time()
    os.makedirs(DEBUG_DIR, exist_ok=True)
    maps = np.load(os.path.join(F.IN_DIR, "maps.npz"))
    lines = json.load(open(os.path.join(F.IN_DIR, "reference-lines.json"), encoding="utf-8"))
    env = F.Envelope(maps)
    ref = F.RefLines(lines)

    print("7a tub fields (P4, exact symmetry)", flush=True)
    wall, wd, wall_info = F.wall_field(env, ref)
    tops, cowl_co, bl_co, cowl_pts, bl_pts, top_info = F.top_fields(maps)
    U = F.TopU(tops, ref)
    print(f"  wall lam {wall_info['penalty']:.3g} RMS {wall_info['weighted_rms_cm']:.2f}/{wall_info['robust_weighted_rms_cm']:.2f} cm; "
          f"end slope max {np.abs(np.concatenate([wall.du(np.full(7, F.S_MIN), np.linspace(0.1, 1.3, 7)), wall.du(np.full(7, F.S_MAX), np.linspace(0.1, 1.3, 7))])).max():.2e}", flush=True)

    print("7b-7d greenhouse fields", flush=True)
    gwall, gd, g_info = greenhouse_wall(env, U)
    print(f"  Dg: floor-rule lam {g_info['floor_rule_penalty']:.3g} x {SMOOTH} = {g_info['penalty']:.3g}; RMS {g_info['weighted_rms_cm']:.2f} cm "
          f"(robust {g_info['robust_weighted_rms_cm']:.2f}), p95 {g_info['p95_cm']:.2f}; cells w1 {g_info['cells_w1']}, no crossing {g_info['cells_no_crossing']}", flush=True)
    roof_fit, roof_mask, roof_info = roof_field(maps)
    roof = Roof(roof_fit)
    print(f"  A_roof: floor-rule lam {roof_info['floor_rule_penalty']:.3g} x {SMOOTH}; RMS {roof_info['weighted_rms_cm']:.2f} cm "
          f"(robust {roof_info['robust_weighted_rms_cm']:.2f}), p95 {roof_info['p95_cm']:.2f}; cells {roof_info['cells']}", flush=True)

    # 7e greenhouse stations and rounds
    print("7e greenhouse rounds", flush=True)
    sg = np.linspace(SG_MIN, SG_MAX, int(math.ceil((SG_MAX - SG_MIN) / G_MESH_STEP)) + 1)
    gst = [GStation(s, gwall, roof, U, env) for s, in zip(sg)]
    R_grid = np.arange(GR_RANGE[0], GR_RANGE[1] + 1e-9, GR_STEP)
    Rs = np.full(len(sg), np.nan)
    for i, st in enumerate(gst):
        if st.corner is None:
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
                e = st.env_rms(rd, E)
                if best is None or e < best[0]:
                    best = (e, R)
        if best:
            Rs[i] = best[1]
    Rmed = median5(Rs)
    rfg = r_spline(sg, Rmed, SG_MIN, SG_MAX, F.R_SPLINE_LAM)
    Rg_meas = np.clip(rfg(sg), *GR_RANGE)
    Rg = np.maximum(Rg_meas * ROUND_SCALE, R_FLOOR)  # plan 8.3
    # greenhouse profiles (continuity selection as the tub)
    NRg = G_N_WALL + G_N_ARC + G_N_ROOF
    Pg = np.zeros((len(sg), NRg, 3))
    gmeta = []
    prev = None
    for i, st in enumerate(gst):
        cands = st.round_halving(Rg[i])
        if cands is None:
            raise RuntimeError(f"greenhouse station {i} s={st.s:.3f}: no round")
        if prev is not None:
            rd = min(cands, key=lambda c: np.linalg.norm(c["C"] - prev[0]) + np.linalg.norm(c["Pw"] - prev[1]) + np.linalg.norm(c["Pt"] - prev[2]))
        else:
            E = st.envelope_points()
            rd = min(cands, key=lambda c: st.env_rms(c, E)) if E is not None and len(E) >= 5 else cands[0]
        prev = (rd["C"], rd["Pw"], rd["Pt"])
        prof, pm = st.gprofile(rd)
        Pg[i] = st.to3d(prof[:, 0], prof[:, 1])
        gmeta.append({"s": float(st.s), "zone": gzone(st.s), "R": float(rd["R"]), "R_target": float(Rg[i]), "halvings": int(rd["halvings"]),
                      "R_measured": float(Rg_meas[i]), "rd": rd, "plane": (st.O, st.n), "profile2d": prof,
                      "z_base": st.z_base, "base_how": st.base_how, "x_base": float(Pg[i, 0, 0]), "y_base": float(Pg[i, 0, 1]),
                      "z_wall_tangent": rd["zw_t"], "z_top_tangent": float(rd["Pt"][1]), "corner": st.corner,
                      "arc_sweep_deg": pm["sweep_deg"], "base_clamped": bool(pm["base_clamped"])})
    footprint = np.array([[m["x_base"], m["y_base"]] for m in gmeta])
    print(f"  greenhouse: {len(sg)} stations; R* found {np.isfinite(Rs).sum()}; base how {dict((k, sum(1 for m in gmeta if m['base_how'] == k)) for k in set(m['base_how'] for m in gmeta))}", flush=True)

    # NaN cells inside the wall's valid range (below the corner) per station
    nan_valid = 0
    valid_cells = 0
    nan_heights = []
    for k, s in enumerate(gd["s"]):
        j = int(np.argmin(np.abs(sg - s)))
        zc = gst[j].corner[1] if gst[j].corner else GZ[1]
        zb = gst[j].z_base
        sel = (gd["z"] >= zb) & (gd["z"] <= zc)
        valid_cells += int(sel.sum())
        bad = sel & ~np.isfinite(gd["rho"][k])
        nan_valid += int(bad.sum())
        nan_heights += list(gd["z"][bad])

    # 7g tub stations ending on the footprint
    print("7g/7h tub stations", flush=True)
    TubStation.footprint = footprint
    s_mesh = np.linspace(F.S_MIN, F.S_MAX, int(math.ceil((F.S_MAX - F.S_MIN) / F.MESH_S_STEP)) + 1)
    zL, zenv, zl_info = F.smooth_lower(env, ref, s_mesh)
    tst = [TubStation(s, wall, U, ref, env, cowl_co, bl_co, z, ze) for s, z, ze in zip(s_mesh, zL, zenv)]
    R_grid_t = np.arange(F.R_RANGE[0], F.R_RANGE[1] + 1e-9, F.R_STEP)
    Rt = np.full(len(s_mesh), np.nan)
    for i, st in enumerate(tst):
        if F.zone_of(st.s) == "cabin" or st.corner is None:
            continue
        E = st.envelope_points()
        if E is None or len(E) < 5:
            continue
        best = None
        for R in R_grid_t:
            cands = st.round(R)
            if cands is None:
                continue
            for rd in cands:
                e = st.env_rms(rd, E)
                if best is None or e < best[0]:
                    best = (e, R)
        if best:
            Rt[i] = best[1]
    Rtm = median5(Rt)
    rft = r_spline(s_mesh, Rtm, F.S_MIN, F.S_MAX, F.R_SPLINE_LAM)
    R_meas = np.clip(rft(s_mesh), *F.R_RANGE)
    R_sp = np.maximum(R_meas * ROUND_SCALE, R_FLOOR)  # plan 8.3
    hb = F.R_CAB_BLEND_V2 / 2
    w_cab = np.minimum(F.smoothstep((s_mesh - (F.Y_CAB0 - hb)) / F.R_CAB_BLEND_V2), F.smoothstep(((F.Y_CAB1 + hb) - s_mesh) / F.R_CAB_BLEND_V2))
    R_fin = (1 - w_cab) * R_sp + w_cab * F.BELT_ROUND_R
    NRt = F.N_WALL + F.N_ARC + F.N_TOP
    Pt = np.zeros((len(s_mesh), NRt, 3))
    tmeta = []
    prev = None
    for i, st in enumerate(tst):
        cands = st.round_halving(R_fin[i])
        if cands is None:
            raise RuntimeError(f"tub station {i}: no round")
        if prev is not None:
            rd = min(cands, key=lambda c: np.linalg.norm(c["C"] - prev[0]) + np.linalg.norm(c["Pw"] - prev[1]) + np.linalg.norm(c["Pt"] - prev[2]))
        else:
            E = st.envelope_points()
            rd = min(cands, key=lambda c: st.env_rms(c, E)) if E is not None and len(E) >= 5 else cands[0]
        prev = (rd["C"], rd["Pw"], rd["Pt"])
        prof, pm = st.profile(rd, F.end_zone(st.s))
        Pt[i] = st.to3d(prof[:, 0], prof[:, 1])
        tmeta.append({"s": float(st.s), "zone": F.zone_of(st.s), "R": float(rd["R"]), "z_L": st.zL, "end": pm["end"],
                      "R_measured": float(R_meas[i]) if F.zone_of(st.s) != "cabin" else float(R_fin[i]), "plane": (st.O, st.n), "profile2d": prof,
                      "rho_end": pm["rho_end"], "z_wall_tangent": rd["zw_t"], "z_top_tangent": float(rd["Pt"][1]),
                      "arc_sweep_deg": pm["sweep_deg"]})

    # 7i glass tags on greenhouse wall quads
    ref_u8 = np.asarray(Image.open(C.REF_SIDE).convert("RGB"))
    hsv = np.asarray(Image.fromarray(ref_u8).convert("HSV")).astype(float)
    dark = (hsv[..., 2] / 255 < 0.5) & (hsv[..., 1] / 255 < 0.45)
    zgrid = np.arange(GZ[0], GZ[1] + 1e-9, 0.01)
    widest = np.array([np.nanmax(gwall(sg[(sg >= Y_GF) & (sg <= Y_GR)], np.full(int(((sg >= Y_GF) & (sg <= Y_GR)).sum()), z))) for z in zgrid])
    NSg = len(sg)
    glass = np.zeros((NSg - 1, NRg - 1), bool)
    for i in range(NSg - 1):
        for r in range(G_N_WALL - 1):
            q = np.array([Pg[i, r], Pg[i + 1, r], Pg[i + 1, r + 1], Pg[i, r + 1]])
            c = q.mean(0)
            nrm = np.cross(q[2] - q[0], q[3] - q[1])
            if np.linalg.norm(nrm) < 1e-12:
                continue
            nrm /= np.linalg.norm(nrm)
            if abs(nrm[0]) >= abs(nrm[1]):
                px = int(round(C.Y_to_px(c[1])))
                py = int(round(C.Z_to_py(c[2])))
                if GLASS_ROWS[0] <= py <= GLASS_ROWS[1] and 0 <= px < C.REF_W and dark[py, px]:
                    glass[i, r] = True
            else:
                zb = 0.5 * (gmeta[i]["z_base"] + gmeta[i + 1]["z_base"])
                zt = 0.5 * (gmeta[i]["z_wall_tangent"] + gmeta[i + 1]["z_wall_tangent"])
                wz = np.interp(c[2], zgrid, widest)
                if c[2] > zb + GLASS_ABOVE_BASE and c[2] < zt - GLASS_BELOW_TANGENT and abs(c[0]) < wz - GLASS_INBOARD:
                    glass[i, r] = True

    # plan 8.4: the same rules per grid vertex (vertex normal from the grid), for interpolated vertex colours
    glass_v = np.zeros((NSg, NRg))
    for i in range(NSg):
        for r in range(G_N_WALL):
            c = Pg[i, r]
            ta = Pg[min(i + 1, NSg - 1), r] - Pg[max(i - 1, 0), r]
            tb = Pg[i, min(r + 1, NRg - 1)] - Pg[i, max(r - 1, 0)]
            nrm = np.cross(ta, tb)
            if np.linalg.norm(nrm) < 1e-12:
                continue
            nrm /= np.linalg.norm(nrm)
            if abs(nrm[0]) >= abs(nrm[1]):
                px = int(round(C.Y_to_px(c[1])))
                py = int(round(C.Z_to_py(c[2])))
                if GLASS_ROWS[0] <= py <= GLASS_ROWS[1] and 0 <= px < C.REF_W and dark[py, px]:
                    glass_v[i, r] = 1.0
            else:
                wz = np.interp(c[2], zgrid, widest)
                if c[2] > gmeta[i]["z_base"] + GLASS_ABOVE_BASE and c[2] < gmeta[i]["z_wall_tangent"] - GLASS_BELOW_TANGENT and abs(c[0]) < wz - GLASS_INBOARD:
                    glass_v[i, r] = 1.0

    # corner miss (plan 8.6): blueprint (envelope) to master along the 45 degree ray of each station plane
    def corner_miss(meta, stations):
        out = []
        for m, st in zip(meta, stations):
            if st.corner is None:
                out.append(np.nan)
                continue
            P0 = np.array([st.corner[0] - F.ENV_INSET, st.corner[1] - F.ENV_INSET])
            dvec = np.array([[math.sqrt(0.5), math.sqrt(0.5)]])
            e = F.march_plane(env, st.O[0], st.O[1], st.n[0], st.n[1], P0[None], dvec)[0]
            prof = m["profile2d"]
            best = None
            for k in range(len(prof) - 1):
                a, b = prof[k], prof[k + 1]
                r_ = dvec[0]
                sv = b - a
                den = r_[0] * sv[1] - r_[1] * sv[0]
                if abs(den) < 1e-15:
                    continue
                qp = a - P0
                t = (qp[0] * sv[1] - qp[1] * sv[0]) / den
                u = (qp[0] * r_[1] - qp[1] * r_[0]) / den
                if t >= 0 and 0 <= u <= 1 and (best is None or t < best):
                    best = t
            if best is None or not np.isfinite(e[0]):
                out.append(np.nan)
                continue
            te = float(np.dot(e - P0, dvec[0]))
            out.append(best - te)  # + = master outside the blueprint along the ray
        return np.array(out)
    miss_t = corner_miss(tmeta, tst)
    miss_g = corner_miss(gmeta, gst)

    def miss_by_zone(meta, miss):
        res = {}
        for z in dict.fromkeys(m["zone"] for m in meta):
            v = np.array([mm for m, mm in zip(meta, miss) if m["zone"] == z and np.isfinite(mm)])
            if len(v):
                res[z] = {"stations": int(len(v)), "median_cm": float(np.median(np.abs(v)) * 100),
                          "p95_cm": float(np.percentile(np.abs(v), 95) * 100), "signed_median_cm": float(np.median(v) * 100)}
        return res

    # meshes
    NSt = len(s_mesh)
    tflags = {"lower": np.zeros((NSt, NRt), bool), "junction": np.zeros((NSt, NRt), bool), "pole": np.zeros((NSt, NRt), bool)}
    tflags["lower"][:, 0] = True
    for i, m in enumerate(tmeta):
        if m["end"].startswith("footprint"):
            tflags["junction"][i, -1] = True
    for fan in (s_mesh < F.Y_FAN_FRONT, s_mesh > F.Y_FAN_REAR):
        idx = np.where(fan)[0]
        if len(idx) and all(tmeta[i]["end"] == "centre" for i in idx):
            tflags["pole"][idx, -1] = True
    tv, tf, tvf, _, tdrop = weld(Pt, tflags)
    gflags = {"base": np.zeros((NSg, NRg), bool), "pole": np.zeros((NSg, NRg), bool)}
    gflags["base"][:, 0] = True
    gflags["pole"][sg < Y_GF, -1] = True
    gflags["pole"][sg > Y_GR, -1] = True
    gv, gf, gvf, gfmap, gdrop = weld(Pg, gflags)
    gglass = np.array([glass[i, r] if r < glass.shape[1] else False for i, r in gfmap])
    # per welded vertex glass value (max over the grid points that merged into it)
    gpts = Pg.reshape(-1, 3).copy()
    gpts[np.abs(gpts[:, 0]) < 1e-9, 0] = 0.0  # same keys as weld() (only x is snapped)
    gkey = np.round(gpts / F.WELD).astype(np.int64)
    gmiss = 0
    vkey = {tuple(k): j for j, k in enumerate(np.round(gv / F.WELD).astype(np.int64))}
    gglass_v = np.zeros(len(gv))
    for k, val in zip(gkey, glass_v.ravel()):
        j = vkey.get(tuple(k))
        if j is not None:
            gglass_v[j] = max(gglass_v[j], val)
        else:
            gmiss += 1
    print(f"  glass vertex values: {int((gglass_v > 0.5).sum())} of {len(gv)} welded vertices; grid points without a welded key {gmiss}", flush=True)
    np.savez_compressed(os.path.join(OUT_DIR, "body-mesh.npz"), tub_verts=tv, tub_faces=tf, tub_lower=tvf["lower"],
                        tub_junction=tvf["junction"], tub_pole=tvf["pole"], gh_verts=gv, gh_faces=gf, gh_base=gvf["base"],
                        gh_pole=gvf["pole"], gh_glass=gglass, gh_glass_v=gglass_v, footprint=footprint, tub_grid=Pt, gh_grid=Pg, s_tub=s_mesh, s_gh=sg)
    print(f"  tub mesh {len(tv)} verts {len(tf)} faces (dropped {tdrop}); greenhouse {len(gv)} verts {len(gf)} faces (dropped {gdrop}); glass faces {int(gglass.sum())}", flush=True)

    # report numbers
    def rz(meta, zones, key="R"):
        out = {}
        for z in zones:
            Rv = np.array([m.get(key, m["R"]) for m in meta if m["zone"] == z])
            if len(Rv):
                out[z] = {"stations": int(len(Rv)), "min": float(Rv.min()), "median": float(np.median(Rv)), "max": float(Rv.max()),
                          "halved": int(sum(1 for m in meta if m["zone"] == z and m.get("halvings", 0) > 0))}
        return out
    base_at = {}
    for sq in (-1.0, -0.6, -0.2, 0.05, 0.45, 0.85, 1.3, 1.8):
        j = int(np.argmin(np.abs(sg - sq)))
        base_at[f"{sg[j]:.3f} ({gzone(sg[j])})"] = {"z_base": gmeta[j]["z_base"], "x_base": gmeta[j]["x_base"], "y_base": gmeta[j]["y_base"]}
    ends = {}
    for m in tmeta:
        ends[m["end"]] = ends.get(m["end"], 0) + 1
    info = {
        "tub": {"wall": wall_info, "tops": top_info, "R_by_zone": rz(tmeta, ["nose", "front side", "cabin", "rear side", "tail"]),
                "ends": ends, "lower_line": zl_info, "R_spline_exact_ends": True,
                "wall_end_slope_max": float(np.abs(np.concatenate([wall.du(np.full(7, F.S_MIN), np.linspace(0.1, 1.3, 7)), wall.du(np.full(7, F.S_MAX), np.linspace(0.1, 1.3, 7))])).max()),
                "R_end_slope": [float(v) for v in rft.du([F.S_MIN, F.S_MAX])]},
        "greenhouse": {"Dg": g_info, "A_roof": roof_info, "R_by_zone": rz(gmeta, ["windscreen header", "front corner", "side rail", "rear corner", "backlight header"]),
                       "R_star_count": int(np.isfinite(Rs).sum()), "stations": len(sg), "base_how": {k: sum(1 for m in gmeta if m["base_how"] == k) for k in set(m["base_how"] for m in gmeta)},
                       "base_clamped_to_tangent": int(sum(1 for m in gmeta if m["base_clamped"])),
                       "no_crossing_cells_in_valid_wall_range": nan_valid, "valid_wall_cells": valid_cells,
                       "no_crossing_heights": [float(np.min(nan_heights)), float(np.max(nan_heights))] if nan_heights else None,
                       "no_crossing_cells_total": g_info["cells_no_crossing"], "base_at": base_at,
                       "Dg_end_slope_max": float(np.abs(np.concatenate([gwall.du(np.full(7, SG_MIN), np.linspace(1.0, 1.65, 7)), gwall.du(np.full(7, SG_MAX), np.linspace(1.0, 1.65, 7))])).max()),
                       "arc_sweep_deg": [float(min(m["arc_sweep_deg"] for m in gmeta)), float(max(m["arc_sweep_deg"] for m in gmeta))],
                       "glass_faces_half": int(gglass.sum())},
        "frames": {"tub": [F.S_MIN, F.S_MAX], "greenhouse": [SG_MIN, SG_MAX], "Y_GF": Y_GF, "Y_GR": Y_GR, "RHO0_G": RHO0_G},
        "R_measured_by_zone": {"tub": rz(tmeta, ["nose", "front side", "cabin", "rear side", "tail"], "R_measured"),
                               "greenhouse": rz(gmeta, ["windscreen header", "front corner", "side rail", "rear corner", "backlight header"], "R_measured")},
        "corner_miss_by_zone": {"tub": miss_by_zone(tmeta, miss_t), "greenhouse": miss_by_zone(gmeta, miss_g)},
        "variant": BT2_VARIANT if BV2 else None, "round_scale": ROUND_SCALE,
        "wall_mid_rule": None if wd.get("mid") is None else {
            "tub_slope_mid_range": [float(np.nanmin(wd["mid"]["slope_mid"])), float(np.nanmax(wd["mid"]["slope_mid"]))],
            "gh_slope_mid_range": [float(np.nanmin(gd["mid"]["slope_mid"])), float(np.nanmax(gd["mid"]["slope_mid"]))],
            "tub_cells_w_gt0": int((wd["w"] > 0).sum()), "gh_cells_w_gt0": int((gd["w"] > 0).sum())},
        "gh_stations": [{k: v for k, v in m.items() if k not in ("rd", "plane", "profile2d")} for m in gmeta],
        "tub_stations": [{k: v for k, v in m.items() if k not in ("plane", "profile2d")} for m in tmeta], "cowl_curve": [float(cowl_co[0]), float(cowl_co[1])],
        "backlight_curve": [float(bl_co[0]), float(bl_co[1])], "shoulder_unused": None,
    }
    save_json("bt2-fields.json", info)
    # profiles for the debug picture: one greenhouse side-rail station, one tub front-side and one tub tail station
    prof_dbg = {}
    for tag, meta, sts, sq in (("gh_side_rail", gmeta, gst, 0.45), ("tub_front_side", tmeta, tst, -1.30), ("tub_tail", tmeta, tst, 2.60),
                               ("gh_windscreen_header", gmeta, gst, SG_MIN)):
        j = int(np.argmin([abs(m["s"] - sq) for m in meta]))
        stj = sts[j]
        E = stj.envelope_points()
        prof_dbg[tag + "_s"] = np.array([meta[j]["s"]])
        prof_dbg[tag + "_E"] = E if E is not None else np.zeros((0, 2))
        prof_dbg[tag + "_wall"] = np.stack([stj.wr, stj.wz], 1)
        prof_dbg[tag + "_top"] = np.stack([stj.tr, stj.tz], 1)
        prof_dbg[tag + "_prof"] = meta[j]["profile2d"]
        prof_dbg[tag + "_corner"] = np.array(stj.corner if stj.corner else (np.nan, np.nan))
        prof_dbg[tag + "_R"] = np.array([meta[j]["R"], meta[j].get("R_measured", meta[j]["R"])])
    np.savez_compressed(os.path.join(OUT_DIR, "bt2-profiles-debug.npz"), **prof_dbg)
    np.savez_compressed(os.path.join(OUT_DIR, "bt2-fields-debug.npz"), gs=gd["s"], gz=gd["z"], grho=gd["rho"], gw=gd["w"],
                        gw_rob=gd["w_robust"], gpred=gd["pred"], sg=sg, Rs=Rs, Rmed=Rmed, Rg=Rg, roof_mask=roof_mask,
                        footprint=footprint, zbase=np.array([m["z_base"] for m in gmeta]),
                        zwt=np.array([m["z_wall_tangent"] for m in gmeta]), zcorner=np.array([m["corner"][1] if m["corner"] else np.nan for m in gmeta]))
    print(f"greenhouse R by zone {info['greenhouse']['R_by_zone']}")
    print(f"no-crossing cells in the valid wall range: {nan_valid} of {valid_cells}; heights {info['greenhouse']['no_crossing_heights']}")
    print(f"tub ends {ends}; base at {base_at}")
    print(f"done in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
