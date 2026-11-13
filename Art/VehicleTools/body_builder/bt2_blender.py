"""BT2 in headless Blender: tub and greenhouse objects from body-mesh.npz (7h), glass material (7i), wheel
proxies, hidden decimated blueprint; save Impreza_Body_Master.blend; the 7j checks that need meshes and
the Workbench renders. bt2_compose.py writes the pictures and report.json.

Run: blender.exe -b --python-exit-code 1 --python bt2_blender.py
"""
import json
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scaffold_cage"))
import sc_common as C  # noqa: E402

IN_DIR = os.path.join(C.ROOT, r"Art\Export\VehicleTools\impreza-scaffold-cage-v02")
BT2_VERSION = os.environ.get("BT2_VERSION", "v01")
BT2_VARIANT = os.environ.get("BT2_VARIANT", "R100")
OUT_ROOT = os.path.join(C.ROOT, r"Art\Export\VehicleTools", "impreza-builder-bt2-" + BT2_VERSION)
OUT_DIR = os.path.join(OUT_ROOT, BT2_VARIANT) if BT2_VERSION != "v01" else OUT_ROOT
RENDER_DIR = os.path.join(OUT_DIR, "debug", "renders")
CLAY = (0.5, 0.5, 0.5, 1.0)
GLASS = (0.12, 0.12, 0.13, 1.0)
WHEEL_DARK = (0.06, 0.06, 0.06, 1.0)
GLOSS_COLOUR = (0.85, 0.85, 0.85)
MATCAPS = ["metal_carpaint.exr", "check_reflection_horizontal.exr"]
TILE = (800, 560)
GLOSS_RES = (1000, 700)
MIRROR_MERGE = 0.001
WHEEL_R, WHEEL_W, WHEEL_SEARCH_R = 0.3575, 0.25, 0.2
DECIMATE_RATIO = 0.05
REF_COLLECTION = "REF | Tripo scaffold (corrected)"
FOLD_DEG = 10.0
ARCH_WIDEN, ARCH_Z_MARGIN = 0.03, 0.04
Y_FAN_FRONT = -1.60
DOOR_Y = (-0.6, 1.0)
CURVE_MARGIN = 0.02


def log(m):
    print(m, flush=True)


def jload(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def mat(name, rgba):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m


def vcol(me, rgba):
    """Plan 8.4: per-vertex colour (FLOAT_COLOR, point domain, linear like the material colours), set active."""
    a = me.color_attributes.new("GT_Tint", "FLOAT_COLOR", "POINT")
    a.data.foreach_set("color", np.asarray(rgba, float).reshape(-1))
    me.color_attributes.active_color = a
    try:
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    except AttributeError:
        pass


def build(name, verts, faces, glass=None, side_test=None, colours=None):
    fl = [[int(v) for v in f if v >= 0] for f in faces]
    me = bpy.data.meshes.new(name + "_half")
    me.from_pydata([tuple(v) for v in verts], [], fl)
    me.update(calc_edges=True)
    if glass is not None:
        me.polygons.foreach_set("material_index", [1 if g else 0 for g in glass])
    if colours is not None:
        vcol(me, colours)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    n = len(me.polygons)
    nrm = np.empty(n * 3)
    cen = np.empty(n * 3)
    me.polygons.foreach_get("normal", nrm)
    me.polygons.foreach_get("center", cen)
    nrm, cen = nrm.reshape(-1, 3), cen.reshape(-1, 3)
    sel = side_test(cen)
    flipped = False
    if sel.any() and nrm[sel, 0].mean() < 0:
        bm = bmesh.new()
        bm.from_mesh(me)
        for f in bm.faces:
            f.normal_flip()
        bm.to_mesh(me)
        bm.free()
        flipped = True
    mir = ob.modifiers.new("Mirror", "MIRROR")
    mir.use_axis = (True, False, False)
    mir.use_mirror_merge = True
    mir.merge_threshold = MIRROR_MERGE
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    full = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    full.name = name
    old = ob.data
    ob.modifiers.clear()
    ob.data = full
    bpy.data.meshes.remove(old)
    try:
        full.shade_smooth()
    except AttributeError:
        full.polygons.foreach_set("use_smooth", [True] * len(full.polygons))
    if colours is not None and "GT_Tint" in full.color_attributes:
        full.color_attributes.active_color = full.color_attributes["GT_Tint"]
    ob.color = CLAY
    return ob, flipped


def wheel_proxies(maps):
    SR = maps["SIDE_raw"]
    ys, zs = maps["ys"], maps["zs"]
    Yg, Zg = np.meshgrid(ys, zs, indexing="ij")
    m = mat("GT_WheelProxy_Dark", WHEEL_DARK)
    names = []
    for Yw in C.WHEEL_Y:
        sel = ((Yg - Yw) ** 2 + (Zg - C.WHEEL_Z) ** 2 <= WHEEL_SEARCH_R ** 2) & np.isfinite(SR)
        x_out = float(np.median(SR[sel]))
        for side in (1.0, -1.0):
            xc = side * (x_out - WHEEL_W / 2)
            vs, fs = [], []
            for k in range(48):
                a = 2 * math.pi * k / 48
                for dx in (-WHEEL_W / 2, WHEEL_W / 2):
                    vs.append((xc + dx, Yw + WHEEL_R * math.cos(a), C.WHEEL_Z + WHEEL_R * math.sin(a)))
            for k in range(48):
                a0, a1 = 2 * k, 2 * ((k + 1) % 48)
                fs.append((a0, a1, a1 + 1, a0 + 1))
            fs.append(tuple(2 * k for k in range(48))[::-1])
            fs.append(tuple(2 * k + 1 for k in range(48)))
            me = bpy.data.meshes.new("wheel")
            me.from_pydata(vs, [], fs)
            me.update(calc_edges=True)
            vcol(me, np.tile(WHEEL_DARK, (len(vs), 1)))
            ob = bpy.data.objects.new(f"GT_WheelProxy_{'F' if Yw < 0 else 'R'}{'L' if side > 0 else 'R'}", me)
            ob.data.materials.append(m)
            ob.color = WHEEL_DARK
            bpy.context.scene.collection.objects.link(ob)
            names.append(ob.name)
    return names


def blueprint(decimate):
    with bpy.data.libraries.load(os.path.join(IN_DIR, "scaffold-corrected.blend"), link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    ob = [o for o in dst.objects if o is not None and o.type == "MESH"][0]
    if decimate:
        col = bpy.data.collections.new(REF_COLLECTION)
        bpy.context.scene.collection.children.link(col)
        col.objects.link(ob)
        d = ob.modifiers.new("Decimate", "DECIMATE")
        d.decimate_type = "COLLAPSE"
        d.ratio = DECIMATE_RATIO
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
        nm = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        old = ob.data
        ob.modifiers.clear()
        ob.data = nm
        bpy.data.meshes.remove(old)
        ob.name = "REF_TripoScaffold_Corrected_Decimated"
        col.hide_viewport = True
        col.hide_render = True
        lc = bpy.context.view_layer.layer_collection.children.get(REF_COLLECTION)
        if lc is not None:
            lc.hide_viewport = True
    else:
        bpy.context.scene.collection.objects.link(ob)
        ob.name = "BT2_Blueprint_Full"
        ob.color = CLAY
    return ob


def co_of(me):
    a = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


def in_box2(u, v, b):
    return (u >= b[0]) & (u <= b[1]) & (v >= b[2]) & (v <= b[3])


def arch_mask(Y, Z, lines):
    m = np.zeros(Y.shape, bool)
    for (lf, lr), a in zip(lines["legs_px"], lines["arch"]):
        px = np.arange(a["x0"], a["x0"] + len(a["py"]))
        za = C.py_to_Z(np.array(a["py"]))
        m |= (Y >= C.px_to_Y(lf) - ARCH_WIDEN) & (Y <= C.px_to_Y(lr) + ARCH_WIDEN) & (Z < np.interp(C.Y_to_px(Y), px, za) + ARCH_Z_MARGIN)
    return m


def distances(co, blue, boxes, lines):
    X, Y, Z = co[:, 0], co[:, 1], co[:, 2]
    ax = np.abs(X)
    ex = np.zeros(len(co), bool)
    why = {}
    for k, b in boxes["SIDE"].items():
        mm = in_box2(Y, Z, b)
        why["SIDE." + k] = int(mm.sum())
        ex |= mm
    for k, b in boxes["TOP"].items():
        mm = in_box2(ax, Y, b)
        why["TOP." + k] = int(mm.sum())
        ex |= mm
    for k, b in boxes["FRONT"].items():
        mm = in_box2(ax, Z, b) & (Y < Y_FAN_FRONT)
        why["FRONT." + k + " (front fascia)"] = int(mm.sum())
        ex |= mm
    am = arch_mask(Y, Z, lines)
    why["arch openings"] = int(am.sum())
    ex |= am
    d = np.full(len(co), np.nan)
    for i in np.where(~ex)[0]:
        ok, p, _, _ = blue.closest_point_on_mesh(Vector(co[i]))
        if ok:
            d[i] = (Vector(co[i]) - p).length
    v = np.isfinite(d)
    k = int(np.nanargmax(d))
    return {"verts": int(len(co)), "excluded": int(ex.sum()), "excluded_by": why, "measured": int(v.sum()),
            "median_cm": float(np.median(d[v]) * 100), "p95_cm": float(np.percentile(d[v], 95) * 100),
            "max_cm": float(d[k] * 100), "max_at": [float(c) for c in co[k]]}, d


def folds(me, skip_keys, label):
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    skip = set(v.index for v in bm.verts if (round(abs(v.co.x), 5), round(v.co.y, 5), round(v.co.z, 5)) in skip_keys)
    rows = []
    skipped = 0
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        fv = set(v.index for f in e.link_faces for v in f.verts)
        if fv & skip:
            skipped += 1
            continue
        a = math.degrees(e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0))
        m = (e.verts[0].co + e.verts[1].co) / 2
        rows.append((a, m.x, m.y, m.z, label))
    bm.free()
    return rows, skipped


def keys(arr):
    return set((round(abs(x), 5), round(y, 5), round(z, 5)) for x, y, z in arr)


def centre_profile(tub, masks, boxes_px, cowl_y0, bl_y0):
    R = masks["R_filled"]
    rows = []
    for px in range(C.REF_W):
        Y = (px - C.PX_MID) / C.PX_PER_M
        bonnet = Y <= cowl_y0
        deck = Y >= bl_y0
        if not (bonnet or deck):
            continue
        hit, loc, _, _ = tub.ray_cast(Vector((0.0, Y, 3.0)), Vector((0, 0, -1)))
        col = R[:735, px]
        if not hit or not col.any():
            continue
        r = int(np.argmax(col))
        z_ref = (C.PX_GROUND - (r - 0.5)) / C.PX_PER_M
        pym = C.PX_GROUND - loc.z * C.PX_PER_M
        if any(b[0] <= px <= b[1] and (b[2] <= r <= b[3] or b[2] <= pym <= b[3]) for b in boxes_px.values()):
            continue
        rows.append((px, Y, loc.z, z_ref, "bonnet" if bonnet else "deck"))
    if not rows:
        return {"columns": 0}
    dev = np.array([abs(a[2] - a[3]) for a in rows]) * 100
    k = int(np.argmax(dev))
    return {"columns": len(rows), "mean_cm": float(dev.mean()), "max_cm": float(dev.max()), "max_at_px": rows[k][0],
            "max_at_Y": rows[k][1], "max_part": rows[k][4], "signed_at_max_cm": float((rows[k][2] - rows[k][3]) * 100),
            "parts": {p: int(sum(1 for a in rows if a[4] == p)) for p in ("bonnet", "deck")}}


def upper_outline(objs, masks, boxes_px):
    vs, ps = [], []
    off = 0
    for ob in objs:
        co = co_of(ob.data)
        vs.extend([tuple(c) for c in co])
        ps.extend([tuple(i + off for i in p.vertices) for p in ob.data.polygons])
        off += len(co)
    bvh = BVHTree.FromPolygons(vs, ps)
    R = masks["R_filled"]
    d = Vector((-1.0, 0.0, 0.0))
    top_m = np.full(C.REF_W, -1)
    for px in range(C.REF_W):
        Y = (px - C.PX_MID) / C.PX_PER_M
        for py in range(0, 735):
            if bvh.ray_cast(Vector((3.0, Y, (C.PX_GROUND - py) / C.PX_PER_M)), d, 10.0)[0] is not None:
                top_m[px] = py
                break
    dev, cols = [], []
    for px in range(C.REF_W):
        col = R[:735, px]
        if top_m[px] < 0 or not col.any():
            continue
        r = int(np.argmax(col))
        if any(b[0] <= px <= b[1] and (b[2] <= r <= b[3] or b[2] <= top_m[px] <= b[3]) for b in boxes_px.values()):
            continue
        dev.append((top_m[px] - r) / 4.0)
        cols.append(px)
    dev = np.array(dev)
    k = int(np.argmax(np.abs(dev)))
    big = [int(c) for c, v in zip(cols, dev) if abs(v) > 3.5]
    return {"columns": len(cols), "mean_cm": float(np.abs(dev).mean()), "max_cm": float(np.abs(dev).max()),
            "max_at_px": int(cols[k]), "max_at_Y": float(C.px_to_Y(cols[k])), "signed_at_max_cm": float(dev[k]),
            "columns_over_3p5cm": len(big), "over_3p5_px_range": [min(big), max(big)] if big else None}, top_m


def set_engine(scene):
    for e in ("BLENDER_WORKBENCH", "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = e
            return e
        except TypeError:
            continue
    return scene.render.engine


def cam(name, loc, target, ortho=None, lens=50.0):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_start, cd.clip_end = 0.05, 100.0
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def render(scene, cm, res, path, visible):
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in visible
    scene.camera = cm
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    t0 = time.time()
    os.makedirs(RENDER_DIR, exist_ok=True)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    npz = np.load(os.path.join(OUT_DIR, "body-mesh.npz"))
    maps = np.load(os.path.join(IN_DIR, "maps.npz"))
    lines = jload(os.path.join(IN_DIR, "reference-lines.json"))
    fields = jload(os.path.join(OUT_DIR, "bt2-fields.json"))
    boxes = json.loads(str(maps["boxes_json"]))
    tub, tflip = build("GT_Impreza_Tub", npz["tub_verts"], npz["tub_faces"], colours=np.tile(CLAY, (len(npz["tub_verts"]), 1)),
                       side_test=lambda c: (np.abs(c[:, 1]) < 1.0) & (c[:, 2] > 0.4) & (c[:, 2] < 0.8))
    tub.data.materials.append(mat("GT_Clay", CLAY))
    gcol = None
    if "gh_glass_v" in npz.files:
        gv_ = np.clip(npz["gh_glass_v"], 0, 1)[:, None]
        assert len(gv_) == len(npz["gh_verts"]), (len(gv_), len(npz["gh_verts"]))
        gcol = (1 - gv_) * np.array(CLAY) + gv_ * np.array(GLASS)
        log(f"greenhouse vertex glass {int((gv_ > 0.5).sum())} of {len(gv_)} vertices")
    gh, gflip = build("GT_Impreza_Greenhouse", npz["gh_verts"], npz["gh_faces"], glass=npz["gh_glass"], colours=gcol,
                      side_test=lambda c: (np.abs(c[:, 1] - 0.45) < 0.35) & (c[:, 2] > 1.15) & (c[:, 2] < 1.35))
    gh.data.materials.append(bpy.data.materials["GT_Clay"])
    gh.data.materials.append(mat("GT_GlassTint", GLASS))
    log(f"tub {len(tub.data.vertices)} v / {len(tub.data.polygons)} f (flipped {tflip}); greenhouse {len(gh.data.vertices)} v / "
        f"{len(gh.data.polygons)} f (flipped {gflip})")
    wheels = wheel_proxies(maps)
    blueprint(True)
    out = os.path.join(OUT_DIR, "Impreza_Body_Master.blend")
    if os.path.exists(out):
        os.remove(out)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    log(f"saved {out}")

    blue = blueprint(False)
    co = np.vstack([co_of(tub.data), co_of(gh.data)])
    dist, _ = distances(co, blue, boxes, lines)
    log(f"distances {dist}")
    tskip = keys(npz["tub_verts"][npz["tub_lower"] | npz["tub_junction"] | npz["tub_pole"]])
    gskip = keys(npz["gh_verts"][npz["gh_base"] | npz["gh_pole"]])
    rt, st_ = folds(tub.data, tskip, "tub")
    rg, sg_ = folds(gh.data, gskip, "greenhouse")
    rows = sorted(rt + rg, reverse=True)
    angs = np.array([r[0] for r in rows])
    fold = {"max_deg": float(angs.max()), "at": list(rows[0][1:4]), "object": rows[0][4],
            "edges_over_10deg": int(np.sum(angs > FOLD_DEG)), "tub_over_10": int(sum(1 for r in rt if r[0] > FOLD_DEG)),
            "greenhouse_over_10": int(sum(1 for r in rg if r[0] > FOLD_DEG)), "edges_measured": len(rows),
            "edges_skipped": st_ + sg_, "top": [{"deg": r[0], "at": list(r[1:4]), "object": r[4]} for r in rows[:16]]}
    log(f"folds max {fold['max_deg']:.1f} at {np.round(fold['at'], 3).tolist()} ({fold['object']}), over 10: {fold['edges_over_10deg']}")
    masks = np.load(os.path.join(IN_DIR, "sc1-masks.npz"))
    sidefit = jload(os.path.join(IN_DIR, "side-fit.json"))
    fp = npz["footprint"]
    cowl_y0 = float(fp[0, 1]) - CURVE_MARGIN
    bl_y0 = float(fp[-1, 1]) + CURVE_MARGIN
    prof = centre_profile(tub, masks, sidefit["boxes_px"], cowl_y0, bl_y0)
    log(f"centre profile {prof}")
    outl, top_m = upper_outline([tub, gh], masks, sidefit["boxes_px"])
    log(f"upper outline {outl}")
    X, Y, Z = co[:, 0], co[:, 1], co[:, 2]
    door = (Y >= DOOR_Y[0]) & (Y <= DOOR_Y[1])
    dims = {"width_doors_m": float(2 * np.abs(X[door]).max()), "length_m": float(Y.max() - Y.min()),
            "Y_range": [float(Y.min()), float(Y.max())], "height_m": float(Z.max())}

    scene = bpy.context.scene
    eng = set_engine(scene)
    sh = scene.display.shading
    sh.light = "STUDIO"
    sh.color_type = "OBJECT"
    sh.show_cavity = True
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    cy = (C.REF_W / 2 - C.PX_MID) / C.PX_PER_M
    cz = (C.PX_GROUND - C.REF_H / 2) / C.PX_PER_M
    cams = {
        "side": cam("CAM_side", (10.0, cy, cz), (0.0, cy, cz), ortho=C.REF_W / C.PX_PER_M),
        "front": cam("CAM_front", (0.0, -10.0, 0.85), (0.0, 0.0, 0.85), ortho=2.9),
        "rear": cam("CAM_rear", (0.0, 10.0, 0.85), (0.0, 0.0, 0.85), ortho=2.9),
        "front34": cam("CAM_front34", (4.9, -5.7, 2.4), (0.0, -0.15, 0.75), lens=50.0),
        "rear34": cam("CAM_rear34", (4.9, 5.7, 2.4), (0.0, 0.15, 0.75), lens=50.0),
    }
    body = [tub.name, gh.name]
    files = {}

    def r(key, cm, res, vis):
        p = os.path.join(RENDER_DIR, key + ".png")
        render(scene, cm, res, p, vis)
        files[key] = p

    r("side_master_wheels", cams["side"], (C.REF_W, C.REF_H), body + wheels)
    r("side_master_only", cams["side"], (C.REF_W, C.REF_H), body)
    for v in ("front", "rear", "front34", "rear34"):
        r(f"view_{v}_blueprint", cams[v], TILE, [blue.name])
        r(f"view_{v}_master", cams[v], TILE, body)
    zone_ct = "MATERIAL"
    if "gh_glass_v" in npz.files:
        try:
            sh.color_type = "VERTEX"  # plan 8.4: interpolated vertex colours (Workbench "Attribute")
            zone_ct = "VERTEX"
        except TypeError as e:
            log(f"VERTEX colour type refused: {e}")
            sh.color_type = "MATERIAL"
    else:
        sh.color_type = "MATERIAL"
    log(f"zones colour type {sh.color_type}")
    for v in ("front34", "rear34", "side", "front"):
        res = (C.REF_W, C.REF_H) if v == "side" else TILE
        r(f"zones_{v}", cams[v], res, body + wheels)
    sh.light = "MATCAP"
    sh.color_type = "SINGLE"
    sh.single_color = GLOSS_COLOUR
    names = [s.name for s in bpy.context.preferences.studio_lights if s.type == "MATCAP"]
    for mc in MATCAPS:
        if mc in names:
            sh.studio_light = mc
            for v in ("front34", "rear34"):
                r(f"gloss_{mc.split('.')[0]}_{v}", cams[v], GLOSS_RES, body)
    res = {"distance": dist, "folds": fold, "centre_profile": prof, "upper_outline": outl, "dimensions": dims,
           "render_engine": eng, "renders": files, "zones_color_type": zone_ct, "flipped": {"tub": tflip, "greenhouse": gflip},
           "objects": {"tub": [len(tub.data.vertices), len(tub.data.polygons)], "greenhouse": [len(gh.data.vertices), len(gh.data.polygons)]},
           "outline_top_row_px": top_m.tolist()}
    with open(os.path.join(OUT_DIR, "bt2-review.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    log(f"BT2 blender done in {time.time() - t0:.1f} s")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
