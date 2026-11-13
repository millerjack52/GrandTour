"""SC1 (plan revision 2): side warp of the Tripo scaffold onto the approved side reference, and
reference lines (arch legs, arch profile, lower boundary, belt) measured from the reference image.

System Python (numpy + PIL). Plan: docs/SCAFFOLD_CAGE_PLAN.md section 2.
Writes side-fit.json, reference-lines.json, debug/side-fit-overlay.png, debug/side-fit-diff.png,
debug/side-fit-nose.png, debug/reference-lines.png.
"""
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sc_common as C  # noqa: E402

CTRL = [51, 135, 221, 386, 551, 720, 893, 1066, 1235, 1400, 1565, 1680, 1791]
E_ROW_MAX = 735  # rows y < 735
# Boxes in reference px: x0, x1, y0, y1 (inclusive). Revision 2 = the run-1 widened boxes.
BOXES = {
    "lamp_pod": [0, 150, 385, 540],
    "front_tow_hook": [0, 95, 540, 640],
    "bonnet_scoop": [286, 480, 280, 345],
    "roof_scoop": [900, 1092, 60, 135],
    "wing": [1575, 1881, 150, 315],
    "exhaust": [1690, 1881, 575, 640],
    "front_mudflap": [520, 585, 530, 735],
    "rear_mudflap": [1535, 1600, 530, 735],
}
WHEEL_DISC_R = 175
REF_BG_THRESH = 0.10
# Nose term (revision 2): blue masks compared over columns 0..230, rows 385..735
NOSE_COLS = (0, 230)
NOSE_ROWS = (385, 735)
NOSE_WEIGHT = 0.5
PEN_D = 1e-5
PEN_S = 2.0
# Descent start: the converged run-1 solution (coordinator instruction, revision 2)
D_START = [-4.0, -3.0, -2.0, -2.0, -2.0, 0.0, 1.0, 3.0, 6.0, 10.0, 9.0, 4.0, -2.0]
S_START = [0.9325, 0.93, 0.935, 0.93, 0.925, 0.935, 0.93, 0.9275, 0.92, 0.90, 0.9025, 0.92, 0.9275]
STEPS_D = [8, 4, 2, 1]
STEPS_S = [0.02, 0.01, 0.005, 0.0025]
SMOOTH_SIGMA_PX = 25.0
WIDTH_COLS = (386, 1400)
ACC_IOU = 0.955
ACC_S = (0.86, 1.00)
ACC_D = 80
BUMPER_ROWS = (545, 605)
ACC_BUMPER_PX = 6

# 2b
BLUE_HUE = (200, 240)
BLUE_SAT = 0.45
RED_HUE_LO = 15
RED_HUE_HI = 345
RED_SAT = 0.6
COLOUR_VAL_MIN = 0.2  # revision 2 brightness floor for blue and red
DARK_VAL = 0.5
DARK_SAT = 0.45
LEG_ROWS = (609, 619)
ARCH_ROW_LIMIT = 464  # 150 px above the wheel-centre row
ARCH_MEDIAN = 9
LOW_SEG_START = 133
LOW_SEG_END = 1760
RED_DILATE = 6
RED_COL_COUNT = 10
LOW_MEDIAN = 15
BELT_ROWS = (150, 360)
BELT_FIT_COLS = (695, 1300)
BELT_REJECT_PX = 4
BELT_EVAL_COLS = (607, 1560)
BELT_RAW_COLS = (560, 1560)  # raw glass bottoms recorded for the picture
DLO_SPAN = [607, 1300]
BLUE_GAP_CLOSE_PX = 4  # revision 3: close vertical gaps up to 4 px before arch profile / lower boundary


def hsv_arrays(rgb_u8):
    hsv = np.asarray(Image.fromarray(rgb_u8).convert("HSV")).astype(float)
    return hsv[..., 0] / 255.0 * 360.0, hsv[..., 1] / 255.0, hsv[..., 2] / 255.0


def colour_masks(rgb_u8):
    Hd, Sa, V = hsv_arrays(rgb_u8)
    blue = (Hd >= BLUE_HUE[0]) & (Hd <= BLUE_HUE[1]) & (Sa > BLUE_SAT) & (V > COLOUR_VAL_MIN)
    red = ((Hd < RED_HUE_LO) | (Hd > RED_HUE_HI)) & (Sa > RED_SAT) & (V > COLOUR_VAL_MIN)
    dark = (V < DARK_VAL) & (Sa < DARK_SAT)
    return blue, red, dark


def eval_region():
    H, W = C.REF_H, C.REF_W
    E = np.zeros((H, W), bool)
    E[:E_ROW_MAX, :] = True
    for x0, x1, y0, y1 in BOXES.values():
        E[max(0, y0):min(H, y1 + 1), max(0, x0):min(W, x1 + 1)] = False
    yy, xx = np.mgrid[0:H, 0:W]
    for cx, cy in C.WHEEL_PX:
        E[(xx - cx) ** 2 + (yy - cy) ** 2 <= WHEEL_DISC_R ** 2] = False
    return E


def flood_from(bg, seeds):
    reach = seeds & bg
    while True:
        n = reach.copy()
        n[1:] |= reach[:-1]
        n[:-1] |= reach[1:]
        n[:, 1:] |= reach[:, :-1]
        n[:, :-1] |= reach[:, 1:]
        n &= bg
        if np.array_equal(n, reach):
            return reach
        reach = n


def fill_holes(R, E):
    """Holes of R = background not reachable by a 4-connected flood fill from the image border.
    The ground contact shadow is part of R (it differs from the background colour) and closes the
    gap under the car between the tyres, so a fill seeded only at the image border would turn that
    gap into body. The fill is therefore also seeded from every pixel outside E (boxes, wheel discs,
    rows >= 735), i.e. holes are counted inside the evaluation region only."""
    bg = ~R
    border = np.zeros_like(R)
    border[0, :] = border[-1, :] = True
    border[:, 0] = border[:, -1] = True
    literal = ~flood_from(bg, border) & bg
    holes = ~flood_from(bg, border | ~E) & bg
    return R | holes, int(holes.sum()), int(literal.sum())


def load_inputs():
    ref_u8 = np.asarray(Image.open(C.REF_SIDE).convert("RGB"))
    ref = ref_u8.astype(float) / 255.0
    bg = ref[5, 5]
    R_raw = np.max(np.abs(ref - bg), axis=2) > REF_BG_THRESH
    tri = np.asarray(Image.open(C.TRIPO_SIDE_REGISTERED).convert("RGBA"))
    T_full = tri[:, :, 3] > 127
    tblue, _, _ = colour_masks(np.ascontiguousarray(tri[:, :, :3]))
    tblue &= T_full
    rblue, rred, rdark = colour_masks(ref_u8)
    return ref_u8, R_raw, T_full, tblue, rblue, tri


class Warper:
    """Per-column counts: silhouette IoU over E and blue IoU over the nose window N."""

    def __init__(self, R, T_full, E, tblue, rblue):
        self.R = R[:E_ROW_MAX]
        self.E = E[:E_ROW_MAX]
        self.T = T_full
        self.TB = tblue
        self.rows_E = np.arange(E_ROW_MAX, dtype=float)
        self.rows_N = np.arange(NOSE_ROWS[0], NOSE_ROWS[1] + 1, dtype=float)
        self.RB_N = rblue[NOSE_ROWS[0]:NOSE_ROWS[1] + 1, NOSE_COLS[0]:NOSE_COLS[1] + 1]

    @staticmethod
    def warp(src, xs, dcol, scol, rows):
        src_c = np.floor(xs + dcol + 0.5).astype(int) + C.TRIPO_PAD
        src_r = np.floor(C.PX_GROUND - (C.PX_GROUND - rows[:, None]) / scol[None, :] + 0.5).astype(int)
        ok = (src_r >= 0) & (src_r < src.shape[0]) & ((src_c >= 0) & (src_c < src.shape[1]))[None, :]
        rr = np.clip(src_r, 0, src.shape[0] - 1)
        cc = np.broadcast_to(np.clip(src_c, 0, src.shape[1] - 1)[None, :], rr.shape)
        out = np.zeros(rr.shape, bool)
        out[ok] = src[rr, cc][ok]
        return out

    def counts_E(self, xs, dcol, scol):
        Tw = self.warp(self.T, xs, dcol, scol, self.rows_E)
        e = self.E[:, xs]
        r = self.R[:, xs]
        return np.sum(Tw & r & e, axis=0), np.sum((Tw | r) & e, axis=0)

    def counts_N(self, xs, dcol, scol):
        """xs must lie inside NOSE_COLS."""
        Bw = self.warp(self.TB, xs, dcol, scol, self.rows_N)
        rb = self.RB_N[:, xs - NOSE_COLS[0]]
        return np.sum(Bw & rb, axis=0), np.sum(Bw | rb, axis=0)

    def full(self, src, dcol, scol):
        xs = np.arange(C.REF_W)
        return self.warp(src, xs, dcol, scol, np.arange(C.REF_H, dtype=float))


def ctrl_to_cols(d, s):
    x = np.arange(C.REF_W, dtype=float)
    return np.interp(x, CTRL, d), np.interp(x, CTRL, s)


def objective(cE, cN, d, s):
    iouE = cE[0].sum() / max(1, cE[1].sum())
    iouN = cN[0].sum() / max(1, cN[1].sum())
    pen = PEN_D * np.sum(np.diff(d) ** 2) + PEN_S * np.sum(np.diff(s) ** 2)
    return iouE + NOSE_WEIGHT * iouN - pen, iouE, iouN


def all_counts(W, dcol, scol):
    xs = np.arange(C.REF_W)
    cE = W.counts_E(xs, dcol, scol)
    xn = np.arange(NOSE_COLS[0], NOSE_COLS[1] + 1)
    cN = W.counts_N(xn, dcol[xn], scol[xn])
    return [cE[0].copy(), cE[1].copy()], [cN[0].copy(), cN[1].copy()]


def descend(W, d, s):
    K = len(CTRL)
    d = np.array(d, float)
    s = np.array(s, float)
    dcol, scol = ctrl_to_cols(d, s)
    cE, cN = all_counts(W, dcol, scol)
    obj, iouE, iouN = objective(cE, cN, d, s)
    start = (float(obj), float(iouE), float(iouN))
    log = []
    n_eval = 0
    for sd, ss in zip(STEPS_D, STEPS_S):
        sweeps = 0
        while True:
            changed = False
            sweeps += 1
            for k in range(K):
                lo = CTRL[k - 1] if k > 0 else 0
                hi = CTRL[k + 1] if k < K - 1 else C.REF_W - 1
                xs = np.arange(lo, hi + 1)
                xn = xs[(xs >= NOSE_COLS[0]) & (xs <= NOSE_COLS[1])]
                for which, step in (("d", sd), ("s", ss)):
                    for sign in (1.0, -1.0):
                        d2 = d.copy()
                        s2 = s.copy()
                        if which == "d":
                            d2[k] += sign * step
                        else:
                            s2[k] += sign * step
                        dc = np.interp(xs, CTRL, d2)
                        scl = np.interp(xs, CTRL, s2)
                        iE, uE = W.counts_E(xs, dc, scl)
                        cE2 = [cE[0].copy(), cE[1].copy()]
                        cE2[0][xs] = iE
                        cE2[1][xs] = uE
                        cN2 = [cN[0].copy(), cN[1].copy()]
                        if len(xn):
                            iN, uN = W.counts_N(xn, np.interp(xn, CTRL, d2), np.interp(xn, CTRL, s2))
                            cN2[0][xn - NOSE_COLS[0]] = iN
                            cN2[1][xn - NOSE_COLS[0]] = uN
                        n_eval += 1
                        obj2, iouE2, iouN2 = objective(cE2, cN2, d2, s2)
                        if obj2 > obj + 1e-12:
                            d, s, cE, cN = d2, s2, cE2, cN2
                            obj, iouE, iouN = obj2, iouE2, iouN2
                            changed = True
                            break
            if not changed:
                break
        log.append({"step_d": sd, "step_s": ss, "sweeps": sweeps, "objective": float(obj),
                    "iou_E": float(iouE), "iou_N_blue": float(iouN)})
        print(f"  level d={sd} s={ss}: sweeps {sweeps}, obj {obj:.5f}, IoU_E {iouE:.5f}, blue IoU_N {iouN:.5f}", flush=True)
    return d, s, start, (float(obj), float(iouE), float(iouN)), log, n_eval


def bumper_offset(Bw_full, rblue):
    rows = range(BUMPER_ROWS[0], BUMPER_ROWS[1] + 1)
    offs = []
    per_row = []
    for y in rows:
        sc = np.where(Bw_full[y, NOSE_COLS[0]:NOSE_COLS[1] + 1])[0]
        rc = np.where(rblue[y, NOSE_COLS[0]:NOSE_COLS[1] + 1])[0]
        if len(sc) and len(rc):
            offs.append(int(sc.min()) - int(rc.min()))
            per_row.append([y, int(sc.min()) + NOSE_COLS[0], int(rc.min()) + NOSE_COLS[0]])
    return float(np.median(offs)) if offs else float("nan"), per_row


def dilate(mask, r):
    out = mask.copy()
    H, W = mask.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r:
                continue
            sh = np.zeros_like(mask)
            ys0, ys1 = max(0, dy), min(H, H + dy)
            xs0, xs1 = max(0, dx), min(W, W + dx)
            sh[ys0:ys1, xs0:xs1] = mask[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
            out |= sh
    return out


def runs(col):
    """List of (start, end_inclusive) of True runs in a 1-D bool array."""
    c = np.concatenate([[False], col, [False]]).astype(int)
    dd = np.diff(c)
    st = np.where(dd == 1)[0]
    en = np.where(dd == -1)[0] - 1
    return list(zip(st, en))


def close_vertical_gaps(mask, max_gap):
    """Fill vertical runs of False of length <= max_gap that have True above and below."""
    out = mask.copy()
    n = 0
    for x in range(mask.shape[1]):
        col = mask[:, x]
        for a, b in runs(~col):
            if a > 0 and b < len(col) - 1 and (b - a + 1) <= max_gap:
                out[a:b + 1, x] = True
                n += int(b - a + 1)
    return out, n


def reference_lines(blue, red, dark):
    bodyish = blue | red
    blue_closed, n_closed = close_vertical_gaps(blue, BLUE_GAP_CLOSE_PX)
    out = {}
    legs = []
    leg_rows = []
    for cx, cy in C.WHEEL_PX:
        fwd, rwd = [], []
        for y in range(LEG_ROWS[0], LEG_ROWS[1] + 1):
            row = bodyish[y]
            fwd.append(next((x for x in range(cx, -1, -1) if row[x]), None))
            rwd.append(next((x for x in range(cx, C.REF_W) if row[x]), None))
        legs.append((float(np.median(fwd)), float(np.median(rwd))))
        leg_rows.append({"fwd": fwd, "rwd": rwd})
    out["legs_px"] = [list(l) for l in legs]
    out["legs_per_row"] = leg_rows

    arches = []
    for (lf, lr) in legs:
        x0 = int(np.floor(lf)) + 1
        x1 = int(np.ceil(lr)) - 1
        xs = np.arange(x0, x1 + 1)
        raw = []
        for x in xs:
            rs = [r for r in runs(blue_closed[:, x]) if r[0] < ARCH_ROW_LIMIT]
            raw.append(rs[-1][1] if rs else np.nan)
        raw = np.array(raw, float)
        med = C.median1d(raw, ARCH_MEDIAN)
        arches.append({"x0": int(x0), "x1": int(x1), "py_raw": raw.tolist(), "py": med.tolist(),
                       "n_nan": int(np.sum(~np.isfinite(raw)))})
    out["arch"] = arches
    out["blue_gap_close"] = {"max_gap_px": BLUE_GAP_CLOSE_PX, "pixels_filled": n_closed}

    red_d = dilate(red, RED_DILATE)
    red_cols = red_d.sum(axis=0) > RED_COL_COUNT
    segs = [(LOW_SEG_START, legs[0][0]), (legs[0][1], legs[1][0]), (legs[1][1], LOW_SEG_END)]
    low = []
    for (a, b) in segs:
        xa = int(np.ceil(a))
        xb = int(np.floor(b))
        xs = np.arange(xa, xb + 1)
        vals = np.array([(np.where(blue_closed[:, x])[0].max() if blue_closed[:, x].any() else np.nan) for x in xs], float)
        filled = vals.copy()
        filled[red_cols[xs]] = np.nan
        good = np.isfinite(filled)
        n_interp = int(np.sum(~good))
        if good.sum() >= 2:
            filled[~good] = np.interp(xs[~good], xs[good], filled[good])
        med = C.median1d(filled, LOW_MEDIAN)
        low.append({"x0": xa, "x1": xb, "py_raw": vals.tolist(), "py": med.tolist(),
                    "red_cols_interpolated": n_interp})
    out["low"] = low

    # Belt (revision 2): straight line through the measured glass bottom, cols 695..1300
    xs = np.arange(BELT_RAW_COLS[0], BELT_RAW_COLS[1] + 1)
    bottoms = np.full(len(xs), np.nan)
    for i, x in enumerate(xs):
        rs = runs(dark[BELT_ROWS[0]:BELT_ROWS[1] + 1, x])
        if rs:
            r = max(rs, key=lambda t: t[1] - t[0])
            bottoms[i] = BELT_ROWS[0] + r[1]
    use = (xs >= BELT_FIT_COLS[0]) & (xs <= BELT_FIT_COLS[1]) & np.isfinite(bottoms)
    co = np.polyfit(xs[use], bottoms[use], 1)
    resid = bottoms[use] - np.polyval(co, xs[use])
    keep = np.abs(resid) <= BELT_REJECT_PX
    co2 = np.polyfit(xs[use][keep], bottoms[use][keep], 1)
    resid2 = bottoms[use][keep] - np.polyval(co2, xs[use][keep])
    ev = np.arange(BELT_EVAL_COLS[0], BELT_EVAL_COLS[1] + 1)
    out["belt"] = {"coef_line": co2.tolist(), "eval_cols": [int(ev[0]), int(ev[-1])],
                   "py": np.polyval(co2, ev).tolist(),
                   "raw_cols": [int(xs[0]), int(xs[-1])], "py_raw": bottoms.tolist(),
                   "n_used": int(use.sum()), "n_rejected": int((~keep).sum()),
                   "rms_px": float(np.sqrt(np.mean(resid2 ** 2))), "max_abs_px": float(np.max(np.abs(resid2)))}
    out["DLO_SPAN"] = DLO_SPAN
    return out


def outline(mask):
    e = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
    return dilate(e, 1)


def main():
    os.makedirs(C.DEBUG_DIR, exist_ok=True)
    t0 = time.time()
    if "--lines-only" in sys.argv:
        ref_u8 = np.asarray(Image.open(C.REF_SIDE).convert("RGB"))
        write_lines(ref_u8)
        print(f"lines only (SC1a warp untouched), done in {time.time() - t0:.1f} s")
        return
    ref_u8, R_raw, T_full, tblue, rblue, tri = load_inputs()
    E = eval_region()
    R, n_filled, n_literal = fill_holes(R_raw, E)
    print(f"R holes filled inside E: {n_filled} px (border-only fill would add {n_literal} px)")
    W = Warper(R, T_full, E, tblue, rblue)

    z = np.zeros(C.REF_W)
    cE0, cN0 = all_counts(W, z, np.ones(C.REF_W))
    iou_identity = float(cE0[0].sum() / cE0[1].sum())
    iouN_identity = float(cN0[0].sum() / cN0[1].sum())
    print(f"identity: IoU_E {iou_identity:.5f}, blue IoU_N {iouN_identity:.5f}")

    d, s, start, end, log, n_eval = descend(W, D_START, S_START)
    print(f"start (run-1 solution): obj {start[0]:.5f} IoU_E {start[1]:.5f} blue IoU_N {start[2]:.5f}; "
          f"converged obj {end[0]:.5f} IoU_E {end[1]:.5f} blue IoU_N {end[2]:.5f}; {n_eval} evaluations")

    dcol, scol = ctrl_to_cols(d, s)
    d_px = C.gauss1d(dcol, SMOOTH_SIGMA_PX)
    s_px = C.gauss1d(scol, SMOOTH_SIGMA_PX)
    xs = np.arange(C.REF_W)
    cE1, cN1 = all_counts(W, d_px, s_px)
    iou_smooth = float(cE1[0].sum() / cE1[1].sum())
    iouN_smooth = float(cN1[0].sum() / cN1[1].sum())
    h = xs + d_px
    h_monotone = bool(np.all(np.diff(h) > 0))
    width_scale = float(np.mean(s_px[WIDTH_COLS[0]:WIDTH_COLS[1] + 1]))
    Bw = W.full(tblue, d_px, s_px)
    bump, bump_rows = bumper_offset(Bw, rblue)
    # same measure at the run-1 solution for the record
    dc1, sc1 = ctrl_to_cols(np.array(D_START), np.array(S_START))
    bump_run1, _ = bumper_offset(W.full(tblue, C.gauss1d(dc1, SMOOTH_SIGMA_PX), C.gauss1d(sc1, SMOOTH_SIGMA_PX)), rblue)
    print(f"smoothed warp: IoU_E {iou_smooth:.5f}, blue IoU_N {iouN_smooth:.5f}; h monotone {h_monotone} "
          f"(min dh {np.diff(h).min():.4f}); WIDTH_SCALE {width_scale:.5f}")
    print(f"bumper-face offset (median, scaffold - reference, px): {bump:+.1f} (run-1 solution {bump_run1:+.1f})")
    print("d_k", np.round(d, 2).tolist())
    print("s_k", np.round(s, 4).tolist())

    acc = {
        "iou_E": iou_smooth, "iou_E_limit": ACC_IOU, "iou_ok": iou_smooth >= ACC_IOU,
        "s_range": [float(s.min()), float(s.max())], "s_ok": bool(s.min() >= ACC_S[0] and s.max() <= ACC_S[1]),
        "d_abs_max": float(np.abs(d).max()), "d_ok": bool(np.abs(d).max() <= ACC_D),
        "h_monotone": h_monotone,
        "bumper_offset_px": bump, "bumper_limit_px": ACC_BUMPER_PX, "bumper_ok": bool(abs(bump) <= ACC_BUMPER_PX),
    }
    acc["pass"] = bool(acc["iou_ok"] and acc["s_ok"] and acc["d_ok"] and h_monotone and acc["bumper_ok"])
    print("SC1a acceptance", acc)

    fit = {
        "plan_revision": 2,
        "CTRL": CTRL, "d_k": d.tolist(), "s_k": s.tolist(), "d_start": D_START, "s_start": S_START,
        "d_px": d_px.tolist(), "s_px": s_px.tolist(), "h_px": h.tolist(),
        "note_tables": "per reference column x = 0..1880; h(x) = x + d(x) is the scaffold column (reference frame); "
                       "beyond the ends d and s are constant (end values); g = inverse of h",
        "iou_identity": iou_identity, "iou_start_run1_solution": start[1], "iou_ctrl_converged": end[1],
        "iou_smoothed": iou_smooth, "blue_iou_N_identity": iouN_identity, "blue_iou_N_start": start[2],
        "blue_iou_N_converged": end[2], "blue_iou_N_smoothed": iouN_smooth,
        "objective": end[0], "descent_log": log, "n_eval": n_eval,
        "bumper_offset_px": bump, "bumper_offset_run1_px": bump_run1, "bumper_rows": bump_rows,
        "R_holes_filled_px": n_filled, "R_holes_border_only_fill_px": n_literal,
        "WIDTH_SCALE": width_scale, "boxes_px": BOXES, "wheel_disc_r": WHEEL_DISC_R,
        "E_rows_lt": E_ROW_MAX, "nose_window": {"cols": NOSE_COLS, "rows": NOSE_ROWS, "weight": NOSE_WEIGHT},
        "acceptance": acc,
    }
    C.save_json("side-fit.json", fit)
    # Masks for SC2/SC4 checks (Blender's Python has no PIL)
    np.savez_compressed(os.path.join(C.OUT_DIR, "sc1-masks.npz"), R_filled=R, R_raw=R_raw, E=E, ref_blue=rblue)

    # Overlay picture
    Tw = W.full(T_full, d_px, s_px)
    arr = ref_u8.copy()
    arr[outline(Tw)] = [255, 0, 255]
    img = Image.fromarray(arr)
    dr = ImageDraw.Draw(img)
    for name, (x0, x1, y0, y1) in BOXES.items():
        dr.rectangle([x0, y0, x1, y1], outline=(0, 160, 0), width=2)
        dr.text((x0 + 3, y0 + 2), name, fill=(0, 110, 0))
    for cx, cy in C.WHEEL_PX:
        dr.ellipse([cx - WHEEL_DISC_R, cy - WHEEL_DISC_R, cx + WHEEL_DISC_R, cy + WHEEL_DISC_R], outline=(0, 160, 0), width=2)
    dr.line([0, E_ROW_MAX, C.REF_W, E_ROW_MAX], fill=(0, 160, 0), width=1)
    dr.rectangle([NOSE_COLS[0], NOSE_ROWS[0], NOSE_COLS[1], NOSE_ROWS[1]], outline=(0, 120, 255), width=1)
    for x in CTRL:
        dr.line([x, 0, x, 20], fill=(0, 0, 0), width=2)
    dr.text((10, 800), f"IoU over E: identity {iou_identity:.4f}  run-1 start {start[1]:.4f}  fitted {iou_smooth:.4f}   "
                       f"bumper offset {bump:+.1f} px (run-1 {bump_run1:+.1f})", fill=(0, 0, 0))
    img.save(os.path.join(C.DEBUG_DIR, "side-fit-overlay.png"))

    diff = np.full((C.REF_H, C.REF_W, 3), 255, np.uint8)
    diff[R & Tw] = [150, 150, 150]
    diff[R & ~Tw] = [0, 170, 220]
    diff[Tw & ~R] = [230, 0, 200]
    diff[~E] = (diff[~E] * 0.5 + 60).astype(np.uint8)
    Image.fromarray(diff).save(os.path.join(C.DEBUG_DIR, "side-fit-diff.png"))

    # Nose picture: blue masks in N (grey both, cyan reference only, magenta scaffold only), 3x
    x0, x1 = NOSE_COLS
    y0, y1 = NOSE_ROWS
    rb = rblue[y0:y1 + 1, x0:x1 + 1]
    sb = Bw[y0:y1 + 1, x0:x1 + 1]
    base = ref_u8[y0:y1 + 1, x0:x1 + 1].astype(float) * 0.4 + 150
    base[rb & sb] = [110, 110, 110]
    base[rb & ~sb] = [0, 190, 240]
    base[sb & ~rb] = [240, 0, 210]
    nimg = Image.fromarray(base.astype(np.uint8)).resize(((x1 - x0 + 1) * 3, (y1 - y0 + 1) * 3), Image.NEAREST)
    nd = ImageDraw.Draw(nimg)
    for y, sc_, rc_ in bump_rows:
        nd.point([((sc_ - x0) * 3 + 1, (y - y0) * 3 + 1)], fill=(0, 0, 0))
    for yy in BUMPER_ROWS:
        nd.line([0, (yy - y0) * 3, 30, (yy - y0) * 3], fill=(0, 0, 0), width=1)
    nd.text((4, 4), f"blue masks N: grey both, cyan ref only, magenta scaffold only; offset {bump:+.1f} px", fill=(0, 0, 0))
    nimg.save(os.path.join(C.DEBUG_DIR, "side-fit-nose.png"))

    write_lines(ref_u8)
    print(f"done in {time.time() - t0:.1f} s")


def write_lines(ref_u8):
    blue, red, dark = colour_masks(ref_u8)
    lines = reference_lines(blue, red, dark)
    C.save_json("reference-lines.json", lines)
    print("legs px", lines["legs_px"], "blue gap pixels closed", lines["blue_gap_close"]["pixels_filled"])
    for a in lines["arch"]:
        print("arch cols", a["x0"], a["x1"], "nan cols", a["n_nan"])
    for l in lines["low"]:
        print("low seg", l["x0"], l["x1"], "red cols interpolated", l["red_cols_interpolated"])
    b = lines["belt"]
    print("belt line", b["coef_line"], "used", b["n_used"], "rejected", b["n_rejected"],
          "rms", round(b["rms_px"], 2), "max", round(b["max_abs_px"], 2))

    img = Image.fromarray(ref_u8.copy())
    dr = ImageDraw.Draw(img)
    for a in lines["arch"]:
        dr.line([(a["x0"] + i, v) for i, v in enumerate(a["py"]) if np.isfinite(v)], fill=(255, 0, 255), width=2)
    for l in lines["low"]:
        dr.line([(l["x0"] + i, v) for i, v in enumerate(l["py"]) if np.isfinite(v)], fill=(0, 220, 0), width=2)
    for lf, lr in lines["legs_px"]:
        for x in (lf, lr):
            dr.line([x, 590, x, 640], fill=(255, 140, 0), width=3)
    ev = np.arange(b["eval_cols"][0], b["eval_cols"][1] + 1)
    dr.line(list(zip(ev.tolist(), b["py"])), fill=(255, 0, 0), width=2)
    for x, v in zip(range(b["raw_cols"][0], b["raw_cols"][1] + 1), b["py_raw"]):
        if np.isfinite(v):
            dr.point((x, v), fill=(255, 255, 0))
    for x in DLO_SPAN:
        dr.line([x, 140, x, 380], fill=(0, 200, 255), width=2)
    for x in BELT_FIT_COLS:
        dr.line([x, 360, x, 380], fill=(255, 0, 0), width=2)
    dr.text((10, 800), "magenta arch profile, green lower boundary, orange legs, red belt line (fit cols 695..1300, "
                       "ticks), yellow raw glass bottom, cyan DLO_SPAN", fill=(0, 0, 0))
    img.save(os.path.join(C.DEBUG_DIR, "reference-lines.png"))


if __name__ == "__main__":
    main()
