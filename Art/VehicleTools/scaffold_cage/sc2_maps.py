"""SC2 part 1 (Blender, headless): corrected scaffold and raw depth maps.

Plan: docs/SCAFFOLD_CAGE_PLAN.md section 3, steps 1-5. Steps 6-8 (exclusions, inpaint, smoothing,
debug images) are in sc2_clean.py (system Python), which reads maps-raw.npz written here.

Run: blender.exe -b --python-exit-code 1 --python sc2_maps.py
Writes scaffold-corrected.blend, maps-raw.npz, sc2-check.json.
"""
import json
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sc_common as C  # noqa: E402

OBJ_NAME = "GT_Impreza_TripoScaffold_Corrected"
GRID = 0.01
SIDE_Y = (-2.30, 2.40)
SIDE_Z = (0.0, 1.80)
TOP_X = (0.0, 1.20)
SIDE_RAY_X = 3.0
TOP_RAY_Z = 3.0
FRONT_RAY_Y = -4.0
REAR_RAY_Y = 4.0
WING_Y = (1.62, 2.30)
WING_REJECT_BELOW_MEDIAN = 0.15
SYM_TOL = 0.015
IOU_TOL = 0.01
CENTRE_ACC_FRACTION = 0.95  # revision 3: share of SIDE cells within SYM_TOL after centring
# v02 (plan section 9a.1): outline correction s2
S2_COLS = (150, 1575)
S2_CLIP = (0.95, 1.08)
S2_SIGMA_PX = 30.0
S2_REPORT_COLS = [200, 250, 700, 1200, 1500]
S2_SCAN_ROW_MAX = 735
FAR = 100.0


def axis(lo, hi, step=GRID):
    n = int(round((hi - lo) / step)) + 1
    return lo + step * np.arange(n)


def log(msg):
    print(msg, flush=True)


def import_scaffold():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    t = time.time()
    bpy.ops.import_scene.gltf(filepath=C.TRIPO_GLB)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    log(f"import {time.time() - t:.1f} s; objects {[(o.name, o.type) for o in bpy.data.objects]}")
    if len(meshes) != 1:
        raise RuntimeError(f"expected one mesh, got {len(meshes)}")
    obj = meshes[0]
    me = obj.data
    mw = obj.matrix_world.copy()
    obj.parent = None
    me.transform(mw)
    obj.matrix_world.identity()
    for o in list(bpy.data.objects):
        if o is not obj:
            bpy.data.objects.remove(o, do_unlink=True)
    me.materials.clear()
    for img in list(bpy.data.images):
        bpy.data.images.remove(img)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)
    obj.name = OBJ_NAME
    me.name = OBJ_NAME
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    log(f"verts {n}, tris {sum(len(p.vertices) - 2 for p in me.polygons)}; native bbox "
        f"x {co[:, 0].min():.4f}..{co[:, 0].max():.4f} y {co[:, 1].min():.4f}..{co[:, 1].max():.4f} "
        f"z {co[:, 2].min():.4f}..{co[:, 2].max():.4f}")
    return obj, co


def warp_vertices(co, fit):
    d_px = np.array(fit["d_px"])
    s_px = np.array(fit["s_px"])
    xs = np.arange(len(d_px), dtype=float)
    h = xs + d_px
    # extend h beyond the table with constant d (d is constant beyond the ends)
    h_ext = np.concatenate([[-2000.0 + d_px[0]], h, [4000.0 + d_px[-1]]])
    x_ext = np.concatenate([[-2000.0], xs, [4000.0]])
    X = co[:, 0] * C.S
    Y = (co[:, 1] + C.GLB_Y_OFFSET) * C.S
    Z = co[:, 2] * C.S
    px_s = C.PX_MID + C.PX_PER_M * Y
    px_r = np.interp(px_s, h_ext, x_ext)  # g = inverse of h
    s_at = np.interp(px_r, xs, s_px)
    out = np.empty_like(co)
    out[:, 0] = X * fit["WIDTH_SCALE"]
    out[:, 1] = (px_r - C.PX_MID) / C.PX_PER_M
    out[:, 2] = Z * s_at
    return out, px_s, px_r


def cast(obj, origins, direction, max_dist=FAR):
    """First-hit ray casts. origins (N,3). Returns hit locations (N,3) NaN for misses, normals."""
    d = Vector(direction)
    loc = np.full((len(origins), 3), np.nan)
    nrm = np.full((len(origins), 3), np.nan)
    rc = obj.ray_cast
    for i, o in enumerate(origins):
        hit, p, n, _ = rc(Vector(o), d, distance=max_dist)
        if hit:
            loc[i] = p
            nrm[i] = n
    return loc, nrm


def all_hits(obj, origin, direction, max_hits=8):
    d = Vector(direction)
    o = Vector(origin)
    hits = []
    for _ in range(max_hits):
        hit, p, n, _ = obj.ray_cast(o, d, distance=FAR)
        if not hit:
            break
        hits.append((tuple(p), tuple(n)))
        o = p + d * 1e-4
    return hits


def mesh_top_rows(obj, cols):
    """Top of the mesh's side silhouette per reference column (fractional row), by ray casts along -X:
    1 px scan from row 0, then bisection to 0.02 px. NaN where the column is empty."""
    d = Vector((-1.0, 0.0, 0.0))
    out = np.full(len(cols), np.nan)
    for k, px in enumerate(cols):
        Y = (px - C.PX_MID) / C.PX_PER_M

        def hit(py):
            return obj.ray_cast(Vector((SIDE_RAY_X, Y, (C.PX_GROUND - py) / C.PX_PER_M)), d, distance=FAR)[0]

        prev = None
        for py in range(0, S2_SCAN_ROW_MAX):
            if hit(py):
                if prev is None:
                    out[k] = float(py)
                    break
                lo, hi = float(prev), float(py)
                while hi - lo > 0.02:
                    mid = 0.5 * (lo + hi)
                    if hit(mid):
                        hi = mid
                    else:
                        lo = mid
                out[k] = 0.5 * (lo + hi)
                break
            prev = py
    return out


def outline_s2(obj, masks, fit):
    """Plan 9a.1: per-column ratio z_ref_top / z_mesh_top over columns 150..1575 outside the SC1 boxes,
    clipped, interpolated across excluded spans, ends held, Gaussian sigma 30 px."""
    cols = np.arange(S2_COLS[0], S2_COLS[1] + 1)
    R = masks["R_filled"]
    ref_top = np.array([np.argmax(R[:735, x]) if R[:735, x].any() else np.nan for x in cols], float)
    mesh_top = mesh_top_rows(obj, cols)
    boxes = list(fit["boxes_px"].values())

    def in_box(x, y):
        return any(b[0] <= x <= b[1] and b[2] <= y <= b[3] for b in boxes)

    # ref pixel row r covers [r - 0.5, r + 0.5]; its top edge is the silhouette boundary
    z_ref = (C.PX_GROUND - (ref_top - 0.5)) / C.PX_PER_M
    z_mesh = (C.PX_GROUND - mesh_top) / C.PX_PER_M
    ok = np.isfinite(ref_top) & np.isfinite(mesh_top)
    for i, x in enumerate(cols):
        if ok[i] and (in_box(x, ref_top[i]) or in_box(x, mesh_top[i])):
            ok[i] = False
    ratio_raw = np.where(ok, z_ref / z_mesh, np.nan)
    ratio = np.clip(ratio_raw, *S2_CLIP)
    n_clipped = int(np.sum(ok & (np.abs(ratio - ratio_raw) > 1e-12)))
    ratio = np.interp(cols, cols[ok], ratio[ok])
    full = np.interp(np.arange(C.REF_W), cols, ratio)  # ends held constant
    s2 = C.gauss1d(full, S2_SIGMA_PX)
    info = {"columns_used": int(ok.sum()), "columns_excluded": int((~ok).sum()), "clipped": n_clipped,
            "raw_ratio_min": float(np.nanmin(ratio_raw)), "raw_ratio_max": float(np.nanmax(ratio_raw)),
            "s2_min": float(s2.min()), "s2_max": float(s2.max()),
            "s2_at": {str(c): float(s2[c]) for c in S2_REPORT_COLS},
            "cols": cols.tolist(), "ref_top_row": ref_top.tolist(), "mesh_top_row": mesh_top.tolist(),
            "used": ok.tolist(), "ratio_raw": [None if not np.isfinite(r) else float(r) for r in ratio_raw],
            "s2": s2.tolist()}
    return s2, info


def main():
    t0 = time.time()
    fit = C.load_json("side-fit.json")
    masks = np.load(os.path.join(C.OUT_DIR, "sc1-masks.npz"))
    obj, co = import_scaffold()

    # 1. car frame + warp
    new, px_s, px_r = warp_vertices(co, fit)
    obj.data.vertices.foreach_set("co", new.ravel())
    obj.data.update()

    # 4 (revision 3): centre first. X0 = median half side-to-side difference of the raw SIDE maps.
    ys = axis(*SIDE_Y)
    zs = axis(*SIDE_Z)
    YY, ZZ = np.meshgrid(ys, zs, indexing="ij")

    def side_maps():
        o = np.stack([np.full(YY.size, SIDE_RAY_X), YY.ravel(), ZZ.ravel()], 1)
        sp = cast(obj, o, (-1, 0, 0))[0][:, 0].reshape(YY.shape)
        o[:, 0] = -SIDE_RAY_X
        sn = -cast(obj, o, (1, 0, 0))[0][:, 0].reshape(YY.shape)
        return sp, sn

    sp0, sn0 = side_maps()
    both0 = np.isfinite(sp0) & np.isfinite(sn0)
    X0 = float(np.median((sp0 - sn0)[both0] / 2.0))
    frac0 = float(np.mean(np.abs(sp0 - sn0)[both0] < SYM_TOL))
    new[:, 0] -= X0
    obj.data.vertices.foreach_set("co", new.ravel())
    obj.data.update()
    log(f"centring: X0 = {X0 * 1000:.2f} mm (cells within {SYM_TOL} m before: {frac0:.3f})")
    s2_info = None
    if C.V2:
        tt = time.time()
        s2, s2_info = outline_s2(obj, masks, fit)
        px = C.PX_MID + C.PX_PER_M * new[:, 1]
        new[:, 2] *= np.interp(px, np.arange(C.REF_W), s2)
        obj.data.vertices.foreach_set("co", new.ravel())
        obj.data.update()
        log(f"s2 ({time.time() - tt:.1f} s): used {s2_info['columns_used']} cols, clipped {s2_info['clipped']}, "
            f"raw ratio {s2_info['raw_ratio_min']:.4f}..{s2_info['raw_ratio_max']:.4f}, s2 {s2_info['s2_min']:.4f}.."
            f"{s2_info['s2_max']:.4f}, at {s2_info['s2_at']}")
    log(f"corrected bbox X {new[:, 0].min():.4f}..{new[:, 0].max():.4f} Y {new[:, 1].min():.4f}..{new[:, 1].max():.4f} "
        f"Z {new[:, 2].min():.4f}..{new[:, 2].max():.4f}")
    blend = os.path.join(C.OUT_DIR, "scaffold-corrected.blend")
    if os.path.exists(blend):
        os.remove(blend)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    log(f"saved scaffold-corrected.blend ({time.time() - t0:.1f} s)")

    # 2. silhouette check, half resolution on the reference grid
    t = time.time()
    pxs = np.arange(0, C.REF_W, 2)
    pys = np.arange(0, 735, 2)
    PX, PY = np.meshgrid(pxs, pys)
    Ys = (PX.ravel() - C.PX_MID) / C.PX_PER_M
    Zs = (C.PX_GROUND - PY.ravel()) / C.PX_PER_M
    orig = np.stack([np.full_like(Ys, SIDE_RAY_X), Ys, Zs], axis=1)
    loc, _ = cast(obj, orig, (-1.0, 0.0, 0.0))
    sil = np.isfinite(loc[:, 0]).reshape(PY.shape)
    R = masks["R_filled"][PY, PX]
    E = masks["E"][PY, PX]
    inter = np.sum(sil & R & E)
    union = np.sum((sil | R) & E)
    iou = float(inter / union)
    log(f"silhouette check {time.time() - t:.1f} s: IoU over E (half res) {iou:.5f} vs SC1 {fit['iou_smoothed']:.5f} "
        f"(diff {iou - fit['iou_smoothed']:+.5f}, limit {IOU_TOL})")
    np.save(os.path.join(C.OUT_DIR, "sc2-silhouette-halfres.npy"), sil)

    # 3. depth maps (recomputed on the centred mesh)
    xs = axis(*TOP_X)
    t = time.time()
    side_pos, side_neg = side_maps()
    both1 = np.isfinite(side_pos) & np.isfinite(side_neg)
    frac1 = float(np.mean(np.abs(side_pos - side_neg)[both1] < SYM_TOL))
    resid_X0 = float(np.median((side_pos - side_neg)[both1] / 2.0))
    log(f"SIDE maps {time.time() - t:.1f} s; after centring {frac1:.3f} of SIDE cells within {SYM_TOL} m "
        f"(limit {CENTRE_ACC_FRACTION}); residual half-difference {resid_X0 * 1000:.2f} mm")

    # 5 (wing): centre-plane profile, ceiling between boot top and blade underside
    wing_rows = []
    for Y in ys[(ys >= WING_Y[0] - 1e-9) & (ys <= WING_Y[1] + 1e-9)]:
        hits = all_hits(obj, (0.0, float(Y), TOP_RAY_Z), (0, 0, -1))
        wing_rows.append({"Y": float(Y), "z": [h[0][2] for h in hits], "nz": [h[1][2] for h in hits]})
    # The shell is closed, so a vertical ray gives blade top, blade underside, boot top, floor (4 hits)
    # where the blade is overhead, boot top + floor (2 hits, far apart) elsewhere, or blade only
    # (2 hits, thin) behind the tail.
    # Blade candidates: a thin first pair (top up, underside down) with a gap to the next surface.
    # Thin lips behind the tail also match, so keep only candidates whose underside lies within
    # 0.10 m of the median candidate underside (the blade is one continuous surface).
    cand = []
    for r in wing_rows:
        z, nz = r["z"], r["nz"]
        r["kind"] = "none" if not z else "body"
        if len(z) >= 3 and z[0] - z[1] < 0.2 and nz[0] > 0 > nz[1] and z[1] - z[2] > 0.05:
            cand.append(r)
    med_under = float(np.median([r["z"][1] for r in cand])) if cand else float("nan")
    blade_under, boot_under_blade, boot_all = [], [], []
    for r in wing_rows:
        z = r["z"]
        if r in cand and abs(z[1] - med_under) <= 0.10:
            r["kind"] = "blade over body"
            blade_under.append(z[1])
            boot_under_blade.append(z[2])
            boot_all.append(z[2])
        elif z:
            boot_all.append(z[0])
    if not blade_under:
        raise RuntimeError("no blade found on the centre plane")
    gap_lo = max(boot_under_blade)
    gap_hi = min(blade_under)
    ceiling = 0.5 * (gap_lo + gap_hi)
    log(f"wing centre plane: rows with blade {len(blade_under)}/{len(wing_rows)}; boot top max {gap_lo:.4f}, "
        f"blade underside min {gap_hi:.4f}, ceiling {ceiling:.4f}; body top max over wing range {max(boot_all):.4f}")
    if gap_hi <= gap_lo or max(boot_all) >= ceiling:
        log("WARNING: no single ceiling clears the body under the whole wing range")

    t = time.time()
    XX, YT = np.meshgrid(xs, ys, indexing="ij")
    in_wing = (YT >= WING_Y[0] - 1e-9) & (YT <= WING_Y[1] + 1e-9)
    start_z = np.where(in_wing, ceiling, TOP_RAY_Z)
    top = {}
    top_nz = {}
    for sgn, key in ((1.0, "pos"), (-1.0, "neg")):
        o = np.stack([sgn * XX.ravel(), YT.ravel(), start_z.ravel()], 1)
        loc, nrm = cast(obj, o, (0, 0, -1))
        top[key] = loc[:, 2].reshape(XX.shape)
        top_nz[key] = nrm[:, 2].reshape(XX.shape)
    log(f"TOP maps {time.time() - t:.1f} s")
    # wing rejection per side. The plan's operational test (hit more than 15 cm below the row median)
    # is kept for the record, but the classifier applied is the one the plan describes: a ray that
    # starts inside the end-plate solid returns a back-facing first hit (normal along the ray).
    # Revision-3 latitude (classifier fix): the 15 cm test rejected ~730 front-facing hits on the
    # rear shoulders per side and kept ~180 back-facing hits inside the end plates.
    top_unrejected = {k: v.copy() for k, v in top.items()}
    reject = {}
    reject_15cm = {}
    for key in ("pos", "neg"):
        rj15 = np.zeros(XX.shape, bool)
        for yi in np.where(in_wing[0])[0]:
            col = top[key][:, yi]
            v = np.isfinite(col)
            if v.sum() == 0:
                continue
            med = np.median(col[v])
            rj15[v & (col < med - WING_REJECT_BELOW_MEDIAN), yi] = True
        rj = in_wing & np.isfinite(top[key]) & (top_nz[key] < 0)
        log(f"TOP {key}: wing cells back-facing (rejected) {int(rj.sum())}; 15 cm test would reject {int(rj15.sum())}, "
            f"of which front-facing {int((rj15 & ~rj).sum())}")
        top[key] = np.where(rj, np.nan, top[key])
        reject[key] = rj
        reject_15cm[key] = rj15

    t = time.time()
    XF, ZF = np.meshgrid(xs, zs, indexing="ij")
    front, rear = {}, {}
    for sgn, key in ((1.0, "pos"), (-1.0, "neg")):
        o = np.stack([sgn * XF.ravel(), np.full(XF.size, FRONT_RAY_Y), ZF.ravel()], 1)
        front[key] = cast(obj, o, (0, 1, 0))[0][:, 1].reshape(XF.shape)
        o[:, 1] = REAR_RAY_Y
        rear[key] = cast(obj, o, (0, -1, 0))[0][:, 1].reshape(XF.shape)
    log(f"FRONT/REAR maps {time.time() - t:.1f} s")

    # 4. symmetrise
    def sym(a, b, less):
        """less(a, b) -> bool array, True where a is the less protruding value."""
        out = np.full(a.shape, np.nan)
        va, vb = np.isfinite(a), np.isfinite(b)
        both = va & vb
        close = both & (np.abs(a - b) < SYM_TOL)
        far = both & ~close
        out[close] = 0.5 * (a[close] + b[close])
        pick_a = far & less(a, b)
        out[pick_a] = a[pick_a]
        out[far & ~pick_a] = b[far & ~pick_a]
        # Cells valid on one side only are one-sided parts by definition (exhaust tip, hook): NaN.
        # (Revision-3 latitude deviation; the plan leaves this case open.)
        stats = {"both_close": int(close.sum()), "both_far": int(far.sum()),
                 "one_side_only": int(((va ^ vb)).sum()), "valid": int(np.isfinite(out).sum())}
        return out, stats

    SIDE, st_side = sym(side_pos, side_neg, lambda a, b: a < b)
    TOP, st_top = sym(top["pos"], top["neg"], lambda a, b: a < b)
    FRONT, st_front = sym(front["pos"], front["neg"], lambda a, b: a > b)
    REAR, st_rear = sym(rear["pos"], rear["neg"], lambda a, b: a < b)
    wing_rej = (reject["pos"] | reject["neg"]) & ~np.isfinite(TOP)
    log(f"symmetrise SIDE {st_side}\n  TOP {st_top}\n  FRONT {st_front}\n  REAR {st_rear}")
    log(f"wing-rejected TOP cells left NaN after symmetrise: {int(wing_rej.sum())}")

    np.savez_compressed(
        os.path.join(C.OUT_DIR, "maps-raw.npz"),
        side_pos=side_pos, side_neg=side_neg, X0=X0, top_pos=top["pos"], top_neg=top["neg"],
        front_pos=front["pos"], front_neg=front["neg"], rear_pos=rear["pos"], rear_neg=rear["neg"],
        SIDE=SIDE, TOP=TOP, FRONT=FRONT, REAR=REAR, wing_reject=wing_rej,
        top_pos_unrejected=top_unrejected["pos"], top_neg_unrejected=top_unrejected["neg"],
        top_nz_pos=top_nz["pos"], top_nz_neg=top_nz["neg"], wing_reject_pos=reject["pos"], wing_reject_neg=reject["neg"],
        ys=ys, zs=zs, xs=xs, grid=GRID, wing_ceiling=ceiling)
    check = {
        "s2": s2_info,
        "centring": {"X0_m": X0, "within_tol_before": frac0, "within_tol_after": frac1,
                     "residual_half_diff_m": resid_X0, "limit": CENTRE_ACC_FRACTION,
                     "ok": frac1 >= CENTRE_ACC_FRACTION},
        "verts": int(len(co)), "corrected_bbox": {
            "X": [float(new[:, 0].min()), float(new[:, 0].max())],
            "Y": [float(new[:, 1].min()), float(new[:, 1].max())],
            "Z": [float(new[:, 2].min()), float(new[:, 2].max())]},
        "silhouette_iou_E_halfres": iou, "sc1_iou_E": fit["iou_smoothed"],
        "silhouette_ok": abs(iou - fit["iou_smoothed"]) <= IOU_TOL,
        "wing": {"ceiling": ceiling, "boot_top_max_under_blade": gap_lo, "blade_underside_min": gap_hi,
                 "rows_with_blade": len(blade_under), "rows": len(wing_rows), "profile": wing_rows,
                 "rejected_pos": int(reject["pos"].sum()), "rejected_neg": int(reject["neg"].sum()),
                 "rule": "back-facing first hit (classifier fix); 15 cm test counts below",
                 "rejected_15cm_pos": int(reject_15cm["pos"].sum()), "rejected_15cm_neg": int(reject_15cm["neg"].sum()),
                 "front_facing_in_15cm_pos": int((reject_15cm["pos"] & ~reject["pos"]).sum()),
                 "front_facing_in_15cm_neg": int((reject_15cm["neg"] & ~reject["neg"]).sum()),
                 "rejected_left_nan": int(wing_rej.sum())},
        "symmetrise": {"SIDE": st_side, "TOP": st_top, "FRONT": st_front, "REAR": st_rear},
    }
    C.save_json("sc2-check.json", check)
    log(f"SC2 part 1 done in {time.time() - t0:.1f} s")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
