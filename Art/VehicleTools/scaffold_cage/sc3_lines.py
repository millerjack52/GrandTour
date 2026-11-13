"""SC3 part 1 (numpy): lines along the car, stations, ring and cap targets, repairs.

Plan: docs/SCAFFOLD_CAGE_PLAN.md section 4a-4d. Reads maps.npz, side-fit.json and
reference-lines.json only. Writes cage-targets.npz, cage-lines.json and (system Python only)
debug/lines-side.png, debug/lines-top.png. sc3_cage.py (Blender) builds the mesh from
cage-targets.npz and does 4e-4f.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sc_common as C  # noqa: E402

T_X_START = 0.25
T_SLOPE = 1.0
T_SLOPE_HALF = 2  # central difference over +-2 cm (grid cells)
T_STAY = 2  # stays >= 1.0 for 2 cm
T_MEDIAN_CM = 7
T_SIGMA_CM = 3.0
B_OFFSET = 0.05
# v02 (plan section 9b)
SHOULDER_DROP = 0.12
END_BLEND = 0.30
END_T_FRACTION = 0.80
ENV_WINDOW_CM = 10
ENV_SIGMA_CM = 5.0
G_INTERIOR = [0.22, 0.45, 0.68, 0.87]
FAIR_WEIGHT = 0.5
if C.V2:
    B_OFFSET = SHOULDER_DROP
B_SIGMA_CM = 3.0
Y_FRONT = -1.90
Y_REAR_SEARCH = (1.95, 2.20)
Y_REAR_FALLBACK = 2.10
LEG_HALF = 0.0125
ARCH_FRACTIONS = [0.08, 0.20, 0.35, 0.50, 0.65, 0.80, 0.92]
COWL_SEARCH = (-0.95, -0.60)
BACKLIGHT_SEARCH = (1.50, 1.80)
KINK_HOLD = 0.05
MAX_STATION_GAP = 0.13
MERGE_DIST = 0.02
F_TOP = [0.0, 0.30, 0.58, 0.82, 1.0]
G_SIDE = [0.22, 0.45, 0.68, 0.87, 1.0]
J11_LOOKUP_UP = 0.015
CAP_CLAMP = 0.01
NJ = 12


class Maps:
    def __init__(self, path):
        m = np.load(path)
        self.ys, self.zs, self.xs = m["ys"], m["zs"], m["xs"]
        self.g = float(m["grid"])
        self.SIDE, self.TOP, self.FRONT, self.REAR = m["SIDE"], m["TOP"], m["FRONT"], m["REAR"]
        self.SIDE_raw = m["SIDE_raw"]
        self.boxes = json.loads(str(m["boxes_json"]))

    def side(self, Y, Z):
        return C.bilinear(self.SIDE, self.ys[0], self.zs[0], self.g, Y, Z)

    def top(self, X, Y):
        return C.bilinear(self.TOP, self.xs[0], self.ys[0], self.g, X, Y)

    def front(self, X, Z):
        return C.bilinear(self.FRONT, self.xs[0], self.zs[0], self.g, X, Z)

    def rear(self, X, Z):
        return C.bilinear(self.REAR, self.xs[0], self.zs[0], self.g, X, Z)


def nan_median_filter(a, w):
    return C.median1d(a, w)


def line_T(M):
    """x_T, z_T per 1 cm of Y (raw and filtered)."""
    ny = len(M.ys)
    x_raw = np.full(ny, np.nan)
    how = np.full(ny, "", dtype=object)
    i0 = int(round((T_X_START - M.xs[0]) / M.g))
    for iy in range(ny):
        row = M.TOP[:, iy]
        if not np.isfinite(row[i0]):
            continue
        # contiguous valid run from X = 0.25 outward
        last = i0
        while last + 1 < len(row) and np.isfinite(row[last + 1]):
            last += 1
        found = None
        for ix in range(i0, last - T_SLOPE_HALF - T_STAY + 1):
            ok = True
            for k in range(T_STAY + 1):
                a = ix + k
                if a - T_SLOPE_HALF < 0 or a + T_SLOPE_HALF > last:
                    ok = False
                    break
                slope = -(row[a + T_SLOPE_HALF] - row[a - T_SLOPE_HALF]) / (2 * T_SLOPE_HALF * M.g)
                if slope < T_SLOPE:
                    ok = False
                    break
            if ok:
                found = ix
                break
        if found is not None:
            x_raw[iy] = M.xs[found]
            how[iy] = "slope"
        else:
            x_raw[iy] = M.xs[last] - 0.01
            how[iy] = "map end"
    z_raw = M.top(x_raw, M.ys)
    xf = C.gauss1d_nan(nan_median_filter(x_raw, T_MEDIAN_CM), T_SIGMA_CM)
    zf = C.gauss1d_nan(nan_median_filter(z_raw, T_MEDIAN_CM), T_SIGMA_CM)
    return x_raw, z_raw, xf, zf, how


def smoothstep(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def blend_T_ends(M, xT, y_front, y_rear):
    """Plan 9b.2: within END_BLEND of each end, blend x_T towards 0.80 * W(Y), W = largest clean SIDE
    value at that Y; weight 1 at the end station, 0 at END_BLEND from it."""
    W = np.nanmax(np.where(np.isfinite(M.SIDE), M.SIDE, -np.inf), axis=1)
    W[~np.isfinite(W)] = np.nan
    ys = M.ys
    w_f = smoothstep(1.0 - (ys - y_front) / END_BLEND)
    w_r = smoothstep(1.0 - (y_rear - ys) / END_BLEND)
    w = np.maximum(w_f, w_r)
    target = END_T_FRACTION * W
    x = np.where(np.isfinite(target) & (w > 0), (1 - w) * xT + w * target, xT)
    return x, w, W


def lower_envelope(zL_grid):
    """Plan 9b.3: running maximum of z_L over +-10 cm, Gaussian sigma 5 cm, then max(z_env, z_L)."""
    n = len(zL_grid)
    h = ENV_WINDOW_CM
    run = np.array([np.nanmax(zL_grid[max(0, i - h): min(n, i + h + 1)]) for i in range(n)])
    env = C.gauss1d(run, ENV_SIGMA_CM)
    return np.maximum(env, zL_grid)


def fair_rows(Lk, stations, Ys):
    """Plan 9b.5: one Jacobi pass per row on the measured coordinate, interior stations only; kink,
    holding and end stations untouched, and j = 11 untouched at leg stations."""
    NS = Lk.shape[0]
    out = Lk.copy()
    skip_all = set([0, NS - 1])
    for i, st in enumerate(stations):
        k = st["kind"]
        if k.startswith("cowl") or k.startswith("backlight base"):
            skip_all.add(i)
    legs = set(i for i, st in enumerate(stations) if "leg" in st["kind"])
    changes = []
    for j in range(Lk.shape[1]):
        for i in range(1, NS - 1):
            if i in skip_all or (j == 11 and i in legs):
                continue
            wp = 1.0 / (Ys[i] - Ys[i - 1])
            wn = 1.0 / (Ys[i + 1] - Ys[i])
            m = (wp * Lk[i - 1, j] + wn * Lk[i + 1, j]) / (wp + wn)
            out[i, j] = Lk[i, j] + FAIR_WEIGHT * (m - Lk[i, j])
            changes.append(abs(out[i, j] - Lk[i, j]))
    ch = np.array(changes)
    return out, {"modified": int(len(ch)), "max_change_m": float(ch.max()) if len(ch) else 0.0,
                 "median_change_m": float(np.median(ch)) if len(ch) else 0.0,
                 "over_1cm": int(np.sum(ch > 0.01)), "over_3cm": int(np.sum(ch > 0.03))}


def lower_line(lines):
    """z_L as a function of reference px: z_arch strictly between legs, z_low elsewhere."""
    legs = lines["legs_px"]
    arch = lines["arch"]
    low = lines["low"]

    def zL_px(px):
        px = np.atleast_1d(np.asarray(px, float))
        out = np.full(px.shape, np.nan)
        for i, p in enumerate(px):
            done = False
            for (lf, lr), a in zip(legs, arch):
                if lf < p < lr:
                    xx = np.arange(a["x0"], a["x0"] + len(a["py"]))
                    out[i] = C.py_to_Z(np.interp(p, xx, a["py"]))
                    done = True
                    break
            if done:
                continue
            # segment containing p, else nearest segment end
            best = None
            for s in low:
                if s["x0"] <= p <= s["x1"]:
                    best = s
                    break
            if best is None:
                dists = [min(abs(p - s["x0"]), abs(p - s["x1"])) for s in low]
                best = low[int(np.argmin(dists))]
            xx = np.arange(best["x0"], best["x0"] + len(best["py"]))
            out[i] = C.py_to_Z(np.interp(p, xx, best["py"]))
        return out
    return zL_px


def belt_Z(lines, px):
    co = lines["belt"]["coef_line"]
    return C.py_to_Z(np.polyval(co, px))


def line_B(M, lines, zT_f):
    """Revision 4: z_B = min(belt line, z_T - 0.05) at every column; the belt line is the straight
    line of SC1 extended over the whole car; Gaussian sigma 3 cm."""
    px = C.Y_to_px(M.ys)
    zbelt = belt_Z(lines, px)
    zb = np.minimum(zbelt, zT_f - B_OFFSET)
    belt_wins = zbelt < zT_f - B_OFFSET
    return C.gauss1d_nan(zb, B_SIGMA_CM), belt_wins


def centre_profile(M):
    return M.TOP[0, :]


def find_kink(M, prof, rng):
    h = T_SLOPE_HALF
    best, best_y, d2s = -np.inf, None, []
    for iy in range(h, len(M.ys) - h):
        Y = M.ys[iy]
        if Y < rng[0] - 1e-9 or Y > rng[1] + 1e-9:
            continue
        d2 = (prof[iy + h] - 2 * prof[iy] + prof[iy - h]) / (h * M.g) ** 2
        if np.isfinite(d2) and d2 > best:
            best, best_y = d2, float(Y)
    return best_y, float(best)


def find_y_rear(M, prof):
    h = T_SLOPE_HALF
    for iy in range(h, len(M.ys) - h):
        Y = M.ys[iy]
        if Y < Y_REAR_SEARCH[0] - 1e-9 or Y > Y_REAR_SEARCH[1] + 1e-9:
            continue
        s = -(prof[iy + h] - prof[iy - h]) / (2 * h * M.g)
        if np.isfinite(s) and s >= 1.0:
            return float(Y), False
    return Y_REAR_FALLBACK, True


def build_stations(M, lines, prof):
    st = []  # dicts: Y, kind, priority, leg_pair id
    y_rear, fb = find_y_rear(M, prof)
    st.append({"Y": Y_FRONT, "kind": "front end", "prio": 3})
    st.append({"Y": y_rear, "kind": "rear end", "prio": 3})
    for ai, (lf, lr) in enumerate(lines["legs_px"]):
        Yf, Yr = float(C.px_to_Y(lf)), float(C.px_to_Y(lr))
        st.append({"Y": Yf - LEG_HALF, "kind": f"arch{ai} front leg outer", "prio": 5, "leg": True})
        st.append({"Y": Yf + LEG_HALF, "kind": f"arch{ai} front leg inner", "prio": 5, "leg": True})
        st.append({"Y": Yr - LEG_HALF, "kind": f"arch{ai} rear leg inner", "prio": 5, "leg": True})
        st.append({"Y": Yr + LEG_HALF, "kind": f"arch{ai} rear leg outer", "prio": 5, "leg": True})
        for f in ARCH_FRACTIONS:
            st.append({"Y": Yf + f * (Yr - Yf), "kind": f"arch{ai} {f:.2f}", "prio": 2})
    cowl, cowl_d2 = find_kink(M, prof, COWL_SEARCH)
    bl, bl_d2 = find_kink(M, prof, BACKLIGHT_SEARCH)
    for name, y in (("cowl", cowl), ("backlight base", bl)):
        st.append({"Y": y, "kind": name, "prio": 4})
        st.append({"Y": y - KINK_HOLD, "kind": name + " hold -", "prio": 1})
        st.append({"Y": y + KINK_HOLD, "kind": name + " hold +", "prio": 1})
    st = [s for s in st if Y_FRONT - 1e-9 <= s["Y"] <= y_rear + 1e-9]
    st.sort(key=lambda s: s["Y"])
    # merge stations closer than 2 cm (never two legs of a pair): keep the higher priority one
    merged_log = []
    changed = True
    while changed:
        changed = False
        for i in range(len(st) - 1):
            a, b = st[i], st[i + 1]
            if b["Y"] - a["Y"] < MERGE_DIST - 1e-12:
                if a.get("leg") and b.get("leg"):
                    continue
                drop = a if a["prio"] < b["prio"] else b
                if a["prio"] == b["prio"]:
                    keep = a
                    keep["Y"] = 0.5 * (a["Y"] + b["Y"])
                    drop = b
                merged_log.append({"dropped": drop["kind"], "Y": drop["Y"]})
                st.remove(drop)
                changed = True
                break
    # fill gaps
    out = []
    n_fill = 0
    for i in range(len(st)):
        out.append(st[i])
        if i + 1 < len(st):
            gap = st[i + 1]["Y"] - st[i]["Y"]
            if gap > MAX_STATION_GAP + 1e-12:
                n = int(np.ceil(gap / MAX_STATION_GAP)) - 1
                for k in range(1, n + 1):
                    out.append({"Y": st[i]["Y"] + gap * k / (n + 1), "kind": "fill", "prio": 0})
                    n_fill += 1
    info = {"Y_REAR": y_rear, "Y_REAR_fallback": fb, "cowl": cowl, "cowl_d2": cowl_d2,
            "backlight_base": bl, "backlight_d2": bl_d2, "merged": merged_log, "n_fill": n_fill}
    return out, info


def at_Y(arr, ys, Y):
    return np.interp(Y, ys, arr)


def repair_rows(V, lookup_col):
    """V: (NS, NJ) looked-up coordinate per station/vertex. Revision 4: NaN lookups are filled by
    interpolation along the row (same j, neighbouring stations); no outlier replacement."""
    NS, NJ_ = V.shape
    n_nan = 0
    details = []
    idx = np.arange(NS)
    for j in range(NJ_):
        if not lookup_col[j]:
            continue
        col = V[:, j]
        bad = ~np.isfinite(col)
        if bad.any():
            n_nan += int(bad.sum())
            good = ~bad
            if good.sum() >= 1:
                col[bad] = np.interp(idx[bad], idx[good], col[good])
            for i in np.where(bad)[0]:
                details.append({"kind": "nan", "station": int(i), "j": int(j)})
        V[:, j] = col
    return V, n_nan, 0, details


def build(M, lines, verbose=True):
    x_raw, z_raw, xT, zT, how = line_T(M)
    zL_px = lower_line(lines)
    prof = centre_profile(M)
    stations, sinfo = build_stations(M, lines, prof)
    Ys = np.array([s["Y"] for s in stations])
    NS = len(Ys)
    v2 = {}
    xT_measured, zT_measured = xT.copy(), zT.copy()
    if C.V2:
        xT, w_end, W = blend_T_ends(M, xT, Ys[0], Ys[-1])
        zT = C.gauss1d_nan(nan_median_filter(M.top(xT, M.ys), T_MEDIAN_CM), T_SIGMA_CM)
        v2["T_end_weight"] = w_end
        v2["W"] = W
    zB, b_inside = line_B(M, lines, zT)
    zL_grid = zL_px(C.Y_to_px(M.ys))
    z_env = lower_envelope(zL_grid) if C.V2 else zL_grid
    xT_s = at_Y(xT, M.ys, Ys)
    zT_s = at_Y(zT, M.ys, Ys)
    zB_s = at_Y(zB, M.ys, Ys)
    zL_s = zL_px(C.Y_to_px(Ys))
    zE_s = at_Y(z_env, M.ys, Ys) if C.V2 else zL_s
    if C.V2:
        v2["zB_minus_zenv_min_at_stations"] = float(np.min(zB_s - zE_s))

    # 4c ring targets: X, Z per (station, j); the looked-up coordinate is Z for j<=4, X for j>=5
    Xr = np.zeros((NS, NJ))
    Zr = np.zeros((NS, NJ))
    Lk = np.zeros((NS, NJ))
    for j in range(5):
        Xr[:, j] = F_TOP[j] * xT_s
        Lk[:, j] = M.top(Xr[:, j], Ys)
    Zr[:, 5] = zB_s + 0.5 * (zT_s - zB_s)
    Zr[:, 6] = zB_s
    if C.V2:
        for k, g in enumerate(G_INTERIOR):
            Zr[:, 7 + k] = zB_s - g * (zB_s - zE_s)
        Zr[:, 11] = zL_s
    else:
        for k, g in enumerate(G_SIDE):
            Zr[:, 7 + k] = zB_s - g * (zB_s - zL_s)
    for j in range(5, NJ):
        zl = Zr[:, j] + (J11_LOOKUP_UP if j == 11 else 0.0)
        Lk[:, j] = M.side(Ys, zl)
    n_lookups_ring = NS * NJ
    Lk, n_nan, n_out, rep = repair_rows(Lk, [True] * NJ)
    if C.V2:
        Lk, fair_info = fair_rows(Lk, stations, Ys)
        v2["fairing"] = fair_info
    for j in range(5):
        Zr[:, j] = Lk[:, j]
    for j in range(5, NJ):
        Xr[:, j] = Lk[:, j]
    Xr[:, 0] = 0.0
    ring = np.stack([Xr, np.repeat(Ys[:, None], NJ, 1), Zr], axis=-1)  # (NS, NJ, 3)

    # 4d caps
    caps = {}
    cap_rep = {"nan": 0, "lookups": 0}
    for which, si, fn, clamp in (("front", 0, M.front, lambda y, Y0: np.minimum(y, Y0 - CAP_CLAMP)),
                                 ("rear", NS - 1, M.rear, lambda y, Y0: np.maximum(y, Y0 + CAP_CLAMP))):
        Y0 = Ys[si]
        x_side = Xr[si, 4:12]
        z_side = Zr[si, 4:12]
        z0 = Zr[si, 0]
        z7 = zL_s[si]
        frac = (z_side[0] - z_side) / (z_side[0] - z_side[7])
        z_ctr = z0 - frac * (z0 - z7)
        P = np.zeros((4, 8, 3))
        nan_ct = 0
        raw_y = np.zeros((4, 8))
        for c in range(4):
            for r in range(1, 8):
                X = F_TOP[c] * x_side[r]
                Z = z_ctr[r] + F_TOP[c] ** 2 * (z_side[r] - z_ctr[r])
                y = float(fn(X, Z))
                raw_y[c, r] = y
                if not np.isfinite(y):
                    nan_ct += 1
                P[c, r] = [X, y, Z]
        # NaN repair along the cap row (neighbouring columns), then clamp
        for r in range(1, 8):
            col = P[:, r, 1]
            bad = ~np.isfinite(col)
            if bad.any():
                good = ~bad
                if good.any():
                    col[bad] = np.interp(np.where(bad)[0], np.where(good)[0], col[good])
                else:
                    col[bad] = Y0
            P[:, r, 1] = clamp(col, Y0)
        n_clamped = int(np.sum(np.abs(P[:, 1:, 1] - np.where(np.isfinite(raw_y[:, 1:]), raw_y[:, 1:], np.inf)) > 1e-9))
        caps[which] = {"P": P, "z_ctr": z_ctr, "frac": frac, "nan": nan_ct, "clamped": n_clamped, "Y0": Y0}
        cap_rep["nan"] += nan_ct
        cap_rep["lookups"] += 28

    total_lookups = n_lookups_ring + cap_rep["lookups"]
    total_repairs = n_nan + cap_rep["nan"]
    res = {
        "lines": {"ys": M.ys, "x_T_raw": x_raw, "z_T_raw": z_raw, "x_T": xT, "z_T": zT, "z_B": zB, "z_env": z_env,
                  "T_how": how, "B_belt_wins": b_inside},
        "stations": stations, "station_info": sinfo, "Ys": Ys,
        "xT_s": xT_s, "zT_s": zT_s, "zB_s": zB_s, "zL_s": zL_s,
        "ring": ring, "caps": caps, "v2": v2, "z_env": z_env, "zE_s": zE_s,
        "xT_measured": xT_measured, "zT_measured": zT_measured,
        "crease_verts": [i * NJ + 11 for i, st in enumerate(stations) if "leg outer" in st["kind"]],
        "repairs": {"ring_lookups": n_lookups_ring, "ring_nan_filled": n_nan, 
                    "cap_lookups": cap_rep["lookups"], "cap_nan_filled": cap_rep["nan"],
                    "cap_clamped_front": caps["front"]["clamped"], "cap_clamped_rear": caps["rear"]["clamped"],
                    "total_lookups": total_lookups, "total_repaired": total_repairs,
                    "fraction": total_repairs / total_lookups, "details": rep},
    }
    return res


def mesh_from(res):
    """Vertex array and quad faces of the half cage. Ring vertex (i, j) -> i*12 + j; then front cap
    interior (c 0..3, r 1..7), then rear cap interior."""
    ring = res["ring"]
    NS = ring.shape[0]
    verts = [tuple(v) for v in ring.reshape(-1, 3)]
    faces = []

    def rv(i, j):
        return i * NJ + j

    for i in range(NS - 1):
        for j in range(NJ - 1):
            faces.append((rv(i, j), rv(i, j + 1), rv(i + 1, j + 1), rv(i + 1, j)))
    cap_index = {}
    for which, si in (("front", 0), ("rear", NS - 1)):
        P = res["caps"][which]["P"]
        idx = {}
        for c in range(5):
            idx[(c, 0)] = rv(si, c)
        for r in range(8):
            idx[(4, r)] = rv(si, 4 + r)
        for c in range(4):
            for r in range(1, 8):
                idx[(c, r)] = len(verts)
                verts.append(tuple(P[c, r]))
        for c in range(4):
            for r in range(7):
                a, b, cc, d = idx[(c, r)], idx[(c + 1, r)], idx[(c + 1, r + 1)], idx[(c, r + 1)]
                if which == "front":
                    faces.append((a, d, cc, b))
                else:
                    faces.append((a, b, cc, d))
        cap_index[which] = {f"{k[0]},{k[1]}": v for k, v in idx.items()}
    return np.array(verts), faces, cap_index


def main():
    M = Maps(os.path.join(C.OUT_DIR, "maps.npz"))
    lines = C.load_json("reference-lines.json")
    res = build(M, lines)
    verts, faces, cap_index = mesh_from(res)
    NS = len(res["Ys"])
    centre = np.zeros(len(verts), bool)
    centre[[i * NJ for i in range(NS)]] = True
    for which in ("front", "rear"):
        for k, v in cap_index[which].items():
            if k.startswith("0,"):
                centre[v] = True
    np.savez_compressed(os.path.join(C.OUT_DIR, "cage-targets.npz"), verts=verts, faces=np.array(faces),
                        centre=centre, NS=NS, NJ=NJ, crease_verts=np.array(res["crease_verts"], int))
    L = res["lines"]
    ys = L["ys"]
    sel = (ys >= C_FRONT_LIMIT(res)) & (ys <= res["station_info"]["Y_REAR"])
    dx = np.abs(np.diff(L["x_T"][sel]))
    dz = np.abs(np.diff(L["z_T"][sel]))
    cont = {"max_step_x_T_per_cm": float(np.nanmax(dx)), "max_step_z_T_per_cm": float(np.nanmax(dz)),
            "nan_x_T_in_station_range": int(np.sum(~np.isfinite(L["x_T"][sel]))),
            "T_by_map_end_in_range": int(np.sum(L["T_how"][sel] == "map end"))}
    out = {
        "station_info": res["station_info"],
        "stations": [{"Y": float(s["Y"]), "kind": s["kind"]} for s in res["stations"]],
        "n_stations": NS, "n_verts": int(len(verts)), "n_faces": len(faces),
        "repairs": {k: v for k, v in res["repairs"].items()},
        "T_continuity": cont,
        "v2": {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in res["v2"].items() if k not in ("T_end_weight", "W")},
        "crease_verts": res["crease_verts"],
        "caps": {w: {"z_ctr": res["caps"][w]["z_ctr"].tolist(), "nan": res["caps"][w]["nan"],
                     "clamped": res["caps"][w]["clamped"], "Y0": float(res["caps"][w]["Y0"])} for w in ("front", "rear")},
        "lines": {"ys": ys.tolist(), "x_T": L["x_T"].tolist(), "z_T": L["z_T"].tolist(), "z_B": L["z_B"].tolist(),
                  "x_T_raw": L["x_T_raw"].tolist(), "z_T_raw": L["z_T_raw"].tolist(),
                  "T_how": [str(h) for h in L["T_how"]]},
        "station_lines": {"Y": res["Ys"].tolist(), "x_T": res["xT_s"].tolist(), "z_T": res["zT_s"].tolist(),
                          "z_B": res["zB_s"].tolist(), "z_L": res["zL_s"].tolist(), "z_env": res["zE_s"].tolist()},
    }
    C.save_json("cage-lines.json", out)
    print("stations", NS, "verts", len(verts), "faces", len(faces))
    print("station info", {k: v for k, v in res["station_info"].items() if k != "merged"}, "merged", len(res["station_info"]["merged"]))
    r = res["repairs"]
    print("repairs: ring lookups", r["ring_lookups"], "nan", r["ring_nan_filled"],
          "| cap lookups", r["cap_lookups"], "nan", r["cap_nan_filled"], "clamped", r["cap_clamped_front"], r["cap_clamped_rear"],
          f"| fraction {r['fraction']:.4f}")
    for d in r["details"][:40]:
        print("   ", d)
    print("T continuity", cont)
    print("v2", out["v2"], "crease verts", res["crease_verts"])
    draw(M, lines, res)


def C_FRONT_LIMIT(res):
    return Y_FRONT


def draw(M, lines, res):
    from PIL import Image, ImageDraw
    L = res["lines"]
    ys = L["ys"]
    img = Image.open(C.REF_SIDE).convert("RGB")
    dr = ImageDraw.Draw(img)
    px = C.Y_to_px(ys)
    yr = res["station_info"]["Y_REAR"]
    sel = (ys >= Y_FRONT - 0.1) & (ys <= yr + 0.1)

    def poly(z, col, w=2):
        pts = [(float(a), float(C.Z_to_py(b))) for a, b, s in zip(px, z, sel) if s and np.isfinite(b)]
        dr.line(pts, fill=col, width=w)

    poly(L["z_T"], (255, 0, 0))
    poly(L["z_B"], (0, 200, 0))
    zl = lower_line(lines)(px)
    poly(np.where((ys >= Y_FRONT) & (ys <= yr), zl, np.nan), (255, 0, 255))
    if C.V2:
        poly(np.where((ys >= Y_FRONT) & (ys <= yr), L["z_env"], np.nan), (0, 220, 255))
    for s, Y in zip(res["stations"], res["Ys"]):
        x = float(C.Y_to_px(Y))
        col = (0, 120, 255) if s["kind"] == "fill" else (255, 140, 0) if "leg" in s["kind"] else (0, 0, 0)
        dr.line([x, 20, x, 60], fill=col, width=2)
        dr.line([x, 770, x, 800], fill=col, width=2)
    dr.text((10, 806), "red z_T, green z_B, magenta z_L" + (", cyan z_env" if C.V2 else "") +
            "; ticks = stations (orange legs, blue fill, black others)", fill=(0, 0, 0))
    img.save(os.path.join(C.DEBUG_DIR, "lines-side.png"))

    # top: x_T over the clean TOP map (horizontal Y, vertical X with centre line at the bottom)
    T = M.TOP
    lo, hi = 0.2, 1.75
    g = np.clip((T - lo) / (hi - lo), 0, 1)
    im = np.where(np.isfinite(T), 40 + 200 * g, 255).astype(np.uint8)  # [ix, iy]
    im = im[::-1, :]  # X up
    sc = 3
    pic = Image.fromarray(im).convert("RGB").resize((im.shape[1] * sc, im.shape[0] * sc), Image.NEAREST)
    d2 = ImageDraw.Draw(pic)
    nx = len(M.xs)

    def P(Y, X):
        return ((Y - ys[0]) / M.g * sc + sc / 2, (nx - 1 - (X - M.xs[0]) / M.g) * sc + sc / 2)

    pts = [P(Y, X) for Y, X, s in zip(ys, L["x_T_raw"], sel) if s and np.isfinite(X)]
    for p in pts:
        d2.point(p, fill=(255, 200, 0))
    if C.V2:
        pts = [P(Y, X) for Y, X, s in zip(ys, res["xT_measured"], sel) if s and np.isfinite(X)]
        d2.line(pts, fill=(255, 150, 200), width=1)
    pts = [P(Y, X) for Y, X, s in zip(ys, L["x_T"], sel) if s and np.isfinite(X)]
    d2.line(pts, fill=(255, 0, 0), width=2)
    for s, Y, X in zip(res["stations"], res["Ys"], res["xT_s"]):
        p = P(Y, X)
        d2.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], outline=(0, 0, 255))
    d2.text((6, 6), "x_T over clean TOP (horizontal Y -2.30..2.40, vertical X 0 bottom .. 1.20 top); yellow raw, red filtered" + (" + end blend, pink before blend" if C.V2 else "") + ", blue stations", fill=(0, 0, 255))
    pic.save(os.path.join(C.DEBUG_DIR, "lines-top.png"))


if __name__ == "__main__":
    main()
