"""SC2 part 2 (system Python): exclusions, inpaint, smoothing, maps.npz and debug images.

Plan: docs/SCAFFOLD_CAGE_PLAN.md section 3, steps 6-8. Reads maps-raw.npz (sc2_maps.py) and
reference-lines.json (sc1_side_fit.py). Writes maps.npz, debug/map-side.png, map-top.png,
map-front.png, map-rear.png.
"""
import json
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sc_common as C  # noqa: E402

MAP_SIGMA_CM = 2.0  # v01
MAP_SIGMA_CM_V2 = {"SIDE": 3.0, "TOP": 3.0, "FRONT": 5.0, "REAR": 5.0}  # plan 9a.2
INPAINT_TOL = 1e-4  # 0.1 mm
INPAINT_MAX_IT = 200000
ARCH_WIDEN = 0.03
ARCH_Z_MARGIN = 0.04

# Exclusion boxes in the car frame (u0, u1, v0, v1). Plan initial values; adjusted after looking at
# the raw maps (see BOX_NOTES in the output json).
SIDE_BOXES = {  # (Y, Z)
    "mirror": [-0.69, -0.44, 1.03, 1.24],
    "front_mudflap": [-0.97, -0.82, 0.0, 0.58],
    "rear_mudflap": [1.57, 1.71, 0.0, 0.56],
}
TOP_BOXES = {  # (X, Y)
    "bonnet_scoop": [0.0, 0.34, -1.53, -1.01],
    "roof_scoop": [0.0, 0.27, 0.01, 0.51],
    "wing_endplate_feet": [0.59, 0.76, 1.69, 2.15],
    "mirror": [0.78, 1.20, -0.70, -0.44],
}
FRONT_BOXES = {  # (X, Z)
    "lamp_pod": [0.0, 0.51, 0.63, 0.86],
}
if C.V2:
    # s2 is about 1.03 at the nose, so the pod sits about 2.5 cm higher: measured X 0..0.48, Z 0.66..0.86
    FRONT_BOXES = {"lamp_pod": [0.0, 0.51, 0.63, 0.89]}
REAR_BOXES = {}
BOXES_PLAN = {
    "SIDE": {"mirror": [-0.74, -0.49, 1.01, 1.21], "front_mudflap": [-0.95, -0.77, 0.0, 0.56],
             "rear_mudflap": [1.59, 1.78, 0.0, 0.56]},
    "TOP": {"bonnet_scoop": [0.0, 0.36, -1.50, -1.02], "roof_scoop": [0.0, 0.26, 0.02, 0.47],
            "wing_endplate_feet": [0.60, 0.95, 1.62, 2.30], "mirror": [0.80, 1.20, -0.74, -0.49]},
    "FRONT": {"lamp_pod": [0.0, 0.72, 0.60, 0.93]},
    "REAR": {},
}
BOX_NOTES = {
    "SIDE.mirror": "mirror measured Y -0.66..-0.47, Z 1.06..1.21 (bump > 1 cm); box = that + 3 cm",
    "SIDE.front_mudflap": "flap measured Y -0.94..-0.85, Z 0.12..0.55; Y1 tightened to -0.82, Z1 to 0.58",
    "SIDE.rear_mudflap": "flap measured Y 1.60..1.68, Z 0.13..0.50; box 1.57..1.71",
    "TOP.bonnet_scoop": "scoop measured X 0..0.31, Y -1.50..-1.04",
    "TOP.roof_scoop": "scoop incl. side wall measured X 0..0.24, Y 0.04..0.48",
    "TOP.wing_endplate_feet": "end-plate bumps left after step 5 at X 0.62..0.72, Y 1.72..2.12",
    "TOP.mirror": "mirror measured X 0.81..1.01, Y -0.67..-0.47",
    "FRONT.lamp_pod": "pod lamps measured X 0..0.48, Z 0.66..0.83 (FRONT Y ~ -2.06 against -1.90 for the headlamp "
                      "beside it); the bumper top at Z 0.56..0.62 stays measured",
}


def box_mask(u, v, box):
    U, V = np.meshgrid(u, v, indexing="ij")
    u0, u1, v0, v1 = box
    eps = 1e-9
    return (U >= u0 - eps) & (U <= u1 + eps) & (V >= v0 - eps) & (V <= v1 + eps)


def arch_mask(ys, zs, lines):
    """SIDE cells inside the arch openings: Y between the legs (widened 3 cm), Z < z_arch(Y) + 4 cm."""
    Yg, Zg = np.meshgrid(ys, zs, indexing="ij")
    m = np.zeros(Yg.shape, bool)
    for (lf, lr), a in zip(lines["legs_px"], lines["arch"]):
        Yf = C.px_to_Y(lf) - ARCH_WIDEN
        Yr = C.px_to_Y(lr) + ARCH_WIDEN
        px = np.arange(a["x0"], a["x0"] + len(a["py"]))
        za = C.py_to_Z(np.array(a["py"]))
        z_at = np.interp(C.Y_to_px(ys), px, za)  # constant beyond the legs
        inside = (Yg >= Yf) & (Yg <= Yr) & (Zg < z_at[:, None] + ARCH_Z_MARGIN)
        m |= inside
    return m


def reachable(dom, known):
    """Domain cells connected (4-neighbour, through the domain) to a known cell."""
    seed = dom & (shift_any(known))
    reach = seed.copy()
    while True:
        n = reach | (shift_any(reach) & dom)
        if np.array_equal(n, reach):
            return reach
        reach = n


def shift_any(m):
    out = np.zeros_like(m)
    out[1:] |= m[:-1]
    out[:-1] |= m[1:]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    return out


def neighbour_sum(val, w):
    s = np.zeros_like(val)
    c = np.zeros_like(val)
    for sl_dst, sl_src in (((slice(1, None), slice(None)), (slice(None, -1), slice(None))),
                           ((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
                           ((slice(None), slice(1, None)), (slice(None), slice(None, -1))),
                           ((slice(None), slice(None, -1)), (slice(None), slice(1, None)))):
        s[sl_dst] += np.where(w[sl_src], val[sl_src], 0.0)
        c[sl_dst] += w[sl_src]
    return s, c


def inpaint(raw, dom_in):
    """Laplace (4-neighbour Jacobi) inpaint of the domain cells from the valid cells around them.
    NaN cells outside the domain are not neighbours."""
    val = raw.copy()
    dom = dom_in.copy()
    val[dom] = np.nan
    known = np.isfinite(val) & ~dom
    reach = reachable(dom, known)
    unreached = int((dom & ~reach).sum())
    # initial values: onion peel, mean of known/filled neighbours
    filled = known.copy()
    v = np.where(known, val, 0.0)
    todo = reach.copy()
    while todo.any():
        s, c = neighbour_sum(v, filled.astype(float))
        ready = todo & (c > 0)
        if not ready.any():
            break
        v[ready] = s[ready] / c[ready]
        filled |= ready
        todo &= ~ready
    w = (known | reach).astype(float)
    it = 0
    change = np.inf
    while it < INPAINT_MAX_IT:
        s, c = neighbour_sum(v, w > 0)
        new = np.where(reach & (c > 0), s / np.maximum(c, 1), v)
        change = float(np.max(np.abs(new - v)[reach])) if reach.any() else 0.0
        v = new
        it += 1
        if change < INPAINT_TOL:
            break
    out = np.where(known, val, np.nan)
    out[reach] = v[reach]
    return out, {"domain": int(dom.sum()), "inpainted": int(reach.sum()), "unreached_left_nan": unreached,
                 "iterations": it, "last_change_m": change}


def gray(a, lo, hi):
    g = np.clip((a - lo) / (hi - lo), 0, 1)
    im = np.where(np.isfinite(a), 30 + 210 * g, 0)
    rgb = np.stack([im, im, im], -1).astype(np.uint8)
    rgb[~np.isfinite(a)] = [255, 235, 235]
    return rgb


def bumps(a):
    sm = C.gauss2d_nan(a, 5.0)
    d = a - sm
    g = np.clip(0.5 + d / 0.06, 0, 1)
    im = np.where(np.isfinite(a), 255 * g, 255)
    rgb = np.stack([im, im, im], -1).astype(np.uint8)
    rgb[~np.isfinite(a)] = [255, 235, 235]
    return rgb


def panel(rgb_uv, u, v, boxes, extra_mask, title, scale, v_up=True, flip_u=False):
    """rgb_uv indexed [iu, iv]; drawn with u horizontal, v vertical (up if v_up)."""
    img = np.transpose(rgb_uv, (1, 0, 2))
    if v_up:
        img = img[::-1]
    if flip_u:
        img = img[:, ::-1]
    im = Image.fromarray(np.ascontiguousarray(img)).resize((img.shape[1] * scale, img.shape[0] * scale), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    nu, nv = len(u), len(v)

    def P(uu, vv):
        iu = (uu - u[0]) / C_GRID
        iv = (vv - v[0]) / C_GRID
        if flip_u:
            iu = nu - 1 - iu
        if v_up:
            iv = nv - 1 - iv
        return (iu + 0.5) * scale, (iv + 0.5) * scale

    for name, (u0, u1, v0, v1) in boxes.items():
        p0 = P(u0, v0)
        p1 = P(u1, v1)
        dr.rectangle([min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1])], outline=(255, 0, 0), width=2)
        dr.text((min(p0[0], p1[0]) + 2, min(p0[1], p1[1]) + 2), name, fill=(255, 0, 0))
    if extra_mask is not None:
        em = np.transpose(extra_mask, (1, 0))
        if v_up:
            em = em[::-1]
        if flip_u:
            em = em[:, ::-1]
        edge = em & ~(np.roll(em, 1, 0) & np.roll(em, -1, 0) & np.roll(em, 1, 1) & np.roll(em, -1, 1))
        ys_, xs_ = np.where(edge)
        for y_, x_ in zip(ys_, xs_):
            dr.rectangle([x_ * scale, y_ * scale, x_ * scale + scale - 1, y_ * scale + scale - 1], fill=(255, 0, 255))
    dr.text((4, 4), title, fill=(0, 90, 255))
    return im


C_GRID = 0.01


def save_map_image(name, clean, raw, u, v, boxes, extra, lo, hi, scale, v_up=True, flip_u=False, labels=("", "")):
    p1 = panel(gray(clean, lo, hi), u, v, boxes, extra, f"{name} clean ({labels[0]})", scale, v_up, flip_u)
    p2 = panel(gray(raw, lo, hi), u, v, boxes, extra, f"{name} raw (symmetrised)", scale, v_up, flip_u)
    p3 = panel(bumps(raw), u, v, boxes, extra, f"{name} raw minus 5 cm blur (+-3 cm)", scale, v_up, flip_u)
    gap = 8
    W = p1.width
    H = p1.height
    vertical = W > H
    if vertical:
        out = Image.new("RGB", (W, 3 * H + 2 * gap + 20), (255, 255, 255))
        for i, p in enumerate((p1, p2, p3)):
            out.paste(p, (0, i * (H + gap)))
    else:
        out = Image.new("RGB", (3 * W + 2 * gap, H + 20), (255, 255, 255))
        for i, p in enumerate((p1, p2, p3)):
            out.paste(p, (i * (W + gap), 0))
    ImageDraw.Draw(out).text((4, out.height - 16), labels[1], fill=(0, 0, 0))
    out.save(os.path.join(C.DEBUG_DIR, name))


def draw_s2():
    """debug/s2.png: reference top, mesh top (before s2) and the s2 curve."""
    chk = C.load_json("sc2-check.json")["s2"]
    cols = np.array(chk["cols"])
    ref = np.array(chk["ref_top_row"], float)
    mesh = np.array(chk["mesh_top_row"], float)
    used = np.array(chk["used"], bool)
    s2 = np.array(chk["s2"])
    img = Image.open(C.REF_SIDE).convert("RGB")
    d = ImageDraw.Draw(img)
    for x, r, mm, u in zip(cols, ref, mesh, used):
        if np.isfinite(mm):
            d.point((int(x), float(mm)), fill=(255, 0, 255) if u else (255, 180, 255))
        if np.isfinite(r):
            d.point((int(x), float(r)), fill=(0, 160, 0) if u else (160, 220, 160))
    # s2 curve: 1.00 at y 790, 100 px per 0.05
    base = 790
    d.line([0, base, C.REF_W, base], fill=(150, 150, 150))
    for v in (0.95, 1.05):
        y = base - (v - 1.0) * 2000
        d.line([0, y, C.REF_W, y], fill=(210, 210, 210))
    pts = [(x, base - (s2[x] - 1.0) * 2000) for x in range(C.REF_W)]
    d.line(pts, fill=(255, 0, 0), width=2)
    d.text((8, 806), f"s2 (red, 1.00 at y {base}, +-0.05 lines): min {chk['s2_min']:.4f} max {chk['s2_max']:.4f}; "
                     "green = reference top, magenta = mesh top before s2 (pale = excluded)", fill=(0, 0, 0))
    img.save(os.path.join(C.DEBUG_DIR, "s2.png"))


def main():
    t0 = time.time()
    m = np.load(os.path.join(C.OUT_DIR, "maps-raw.npz"))
    lines = C.load_json("reference-lines.json")
    ys, zs, xs = m["ys"], m["zs"], m["xs"]
    raw = {"SIDE": m["SIDE"], "TOP": m["TOP"], "FRONT": m["FRONT"], "REAR": m["REAR"]}
    axes = {"SIDE": (ys, zs), "TOP": (xs, ys), "FRONT": (xs, zs), "REAR": (xs, zs)}
    boxes = {"SIDE": SIDE_BOXES, "TOP": TOP_BOXES, "FRONT": FRONT_BOXES, "REAR": REAR_BOXES}
    arch = arch_mask(ys, zs, lines)
    # Body half-width per Y from the raw SIDE map with the SIDE boxes (mirror) removed; TOP cells
    # beyond it are not body (mirror head, end-plate overhang) and are left NaN rather than inpainted.
    side_nb = raw["SIDE"].copy()
    for b in SIDE_BOXES.values():
        side_nb[box_mask(ys, zs, b)] = np.nan
    half_width = np.nanmax(np.where(np.isfinite(side_nb), side_nb, -np.inf), axis=1)
    half_width[~np.isfinite(half_width)] = -1.0
    beyond_top = xs[:, None] > half_width[None, :] + 1e-9
    clean, stats, excl = {}, {}, {}
    for k in raw:
        u, v = axes[k]
        dom = np.zeros(raw[k].shape, bool)
        for b in boxes[k].values():
            dom |= box_mask(u, v, b)
        if k == "SIDE":
            dom |= arch
        # Only cells that were body in the raw map are inpainted; NaN cells outside the body stay out
        # (revision-3 latitude: the plan's "NaN cells outside the body are not neighbours").
        dom &= np.isfinite(raw[k])
        if k == "TOP":
            dom |= m["wing_reject"]
            n_beyond = int((dom & beyond_top).sum())
            dom_beyond = dom & beyond_top
            dom &= ~beyond_top
            raw_k = raw[k].copy()
            raw_k[dom_beyond] = np.nan
        else:
            n_beyond = 0
            raw_k = raw[k]
        excl[k] = dom
        filled, st = inpaint(raw_k, dom)
        st["excluded_cells_beyond_body_half_width_set_nan"] = n_beyond
        sig = MAP_SIGMA_CM_V2[k] if C.V2 else MAP_SIGMA_CM
        clean[k] = C.gauss2d_nan(filled, sig)
        st["sigma_cm"] = sig
        st["valid_after"] = int(np.isfinite(clean[k]).sum())
        stats[k] = st
        print(k, st, flush=True)

    np.savez_compressed(
        os.path.join(C.OUT_DIR, "maps.npz"),
        SIDE_raw=raw["SIDE"], TOP_raw=raw["TOP"], FRONT_raw=raw["FRONT"], REAR_raw=raw["REAR"],
        SIDE=clean["SIDE"], TOP=clean["TOP"], FRONT=clean["FRONT"], REAR=clean["REAR"],
        SIDE_excl=excl["SIDE"], TOP_excl=excl["TOP"], FRONT_excl=excl["FRONT"], REAR_excl=excl["REAR"],
        side_pos=m["side_pos"], side_neg=m["side_neg"],
        ys=ys, zs=zs, xs=xs, grid=C_GRID,
        origin_SIDE=np.array([ys[0], zs[0]]), origin_TOP=np.array([xs[0], ys[0]]),
        origin_FRONT=np.array([xs[0], zs[0]]), origin_REAR=np.array([xs[0], zs[0]]),
        boxes_json=json.dumps({"SIDE": SIDE_BOXES, "TOP": TOP_BOXES, "FRONT": FRONT_BOXES, "REAR": REAR_BOXES}))
    C.save_json("sc2-clean.json", {"inpaint": stats, "boxes": {"SIDE": SIDE_BOXES, "TOP": TOP_BOXES,
                                                               "FRONT": FRONT_BOXES, "REAR": REAR_BOXES},
                                   "boxes_plan": BOXES_PLAN, "box_notes": BOX_NOTES,
                                   "arch_openings": {"widen_m": ARCH_WIDEN, "z_margin_m": ARCH_Z_MARGIN},
                                   "MAP_SIGMA_CM": MAP_SIGMA_CM_V2 if C.V2 else MAP_SIGMA_CM})
    if C.V2:
        draw_s2()

    lab = "front = left; "
    save_map_image("map-side.png", clean["SIDE"], raw["SIDE"], ys, zs, SIDE_BOXES, arch, 0.0, 1.05, 2,
                   labels=("X depth, light = wide", lab + "horizontal Y -2.30..2.40, vertical Z 0..1.80 up; magenta = arch openings"))
    save_map_image("map-top.png", clean["TOP"], raw["TOP"], xs, ys, TOP_BOXES, m["wing_reject"], 0.2, 1.75, 2,
                   v_up=False, labels=("Z height, light = high", "horizontal X 0..1.20 (centre line left), vertical Y -2.30 (top) .. 2.40; magenta = wing-rejected cells"))
    save_map_image("map-front.png", clean["FRONT"], raw["FRONT"], xs, zs, FRONT_BOXES, None, -2.35, -1.3, 3,
                   labels=("Y, light = further back", "horizontal X 0..1.20 (centre line left), vertical Z 0..1.80 up"))
    save_map_image("map-rear.png", clean["REAR"], raw["REAR"], xs, zs, REAR_BOXES, None, 2.35, 1.3, 3,
                   labels=("Y, light = further forward", "horizontal X 0..1.20 (centre line left), vertical Z 0..1.80 up"))
    print(f"done in {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
