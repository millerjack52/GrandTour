"""BT1 (tub master) in headless Blender: build the mesh from tub-mesh.npz (4f), wheel proxies, the
decimated blueprint in a hidden collection, save Impreza_Tub_Master.blend; then the 4g checks that
need meshes (distance to the blueprint, fold detector, centre-line profile, dimensions) and the
Workbench renders. bt1_compose.py (system Python) composes the pictures and writes report.json.

Run: blender.exe -b --python-exit-code 1 --python bt1_blender.py
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scaffold_cage"))
import sc_common as C  # noqa: E402

import bt_paths as BP  # noqa: E402

IN_DIR = BP.IN_DIR
OUT_DIR = BP.OUT_DIR
RENDER_DIR = os.path.join(BP.DEBUG_DIR, "renders")
TUB_NAME = "GT_Impreza_TubMaster"
MIRROR_MERGE = 0.001
WHEEL_R, WHEEL_W, WHEEL_SEARCH_R = 0.3575, 0.25, 0.2
DECIMATE_RATIO = 0.05
REF_COLLECTION = "REF | Tripo scaffold (corrected)"
CLAY = (0.5, 0.5, 0.5, 1.0)
WHEEL_DARK = (0.06, 0.06, 0.06, 1.0)
GLOSS_COLOUR = (0.85, 0.85, 0.85)
MATCAPS = ["metal_carpaint.exr", "check_reflection_horizontal.exr"]
TILE = (800, 560)
GLOSS_RES = (1000, 700)
FOLD_DEG = 10.0
POLE_VALENCE = 10
ARCH_WIDEN, ARCH_Z_MARGIN = 0.03, 0.04
Y_FAN_FRONT = -1.60
DOOR_Y = (-0.6, 1.0)
CURVE_MARGIN = 0.02


def log(m):
    print(m, flush=True)


def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def make_material(name, rgba):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    return mat


def build_tub(npz):
    verts = npz["verts"]
    faces = [[int(v) for v in f if v >= 0] for f in npz["faces"]]
    me = bpy.data.meshes.new(TUB_NAME + "_half")
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update(calc_edges=True)
    ob = bpy.data.objects.new(TUB_NAME, me)
    bpy.context.scene.collection.objects.link(ob)
    # orientation: mean normal x on the side band must be outward
    n = len(me.polygons)
    nrm = np.empty(n * 3)
    cen = np.empty(n * 3)
    me.polygons.foreach_get("normal", nrm)
    me.polygons.foreach_get("center", cen)
    nrm, cen = nrm.reshape(-1, 3), cen.reshape(-1, 3)
    side = (np.abs(cen[:, 1]) < 1.0) & (cen[:, 2] > 0.4) & (cen[:, 2] < 0.8)
    flipped = False
    if nrm[side, 0].mean() < 0:
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
    full.name = TUB_NAME
    old = ob.data
    ob.modifiers.clear()
    ob.data = full
    bpy.data.meshes.remove(old)
    try:
        full.shade_smooth()
    except AttributeError:
        full.polygons.foreach_set("use_smooth", [True] * len(full.polygons))
    ob.color = CLAY
    ob.data.materials.append(make_material("GT_Clay", CLAY))
    return ob, flipped


def wheel_proxies(maps):
    SR = maps["SIDE_raw"]
    ys, zs = maps["ys"], maps["zs"]
    Yg, Zg = np.meshgrid(ys, zs, indexing="ij")
    mat = make_material("GT_WheelProxy_Dark", WHEEL_DARK)
    info = []
    for Yw in C.WHEEL_Y:
        sel = ((Yg - Yw) ** 2 + (Zg - C.WHEEL_Z) ** 2 <= WHEEL_SEARCH_R ** 2) & np.isfinite(SR)
        x_out = float(np.median(SR[sel]))
        info.append({"Y": Yw, "outer_face_X": x_out})
        for side in (1.0, -1.0):
            xc = side * (x_out - WHEEL_W / 2)
            vs, fs = [], []
            seg = 48
            for k in range(seg):
                a = 2 * math.pi * k / seg
                for dx in (-WHEEL_W / 2, WHEEL_W / 2):
                    vs.append((xc + dx, Yw + WHEEL_R * math.cos(a), C.WHEEL_Z + WHEEL_R * math.sin(a)))
            for k in range(seg):
                a0, a1 = 2 * k, 2 * ((k + 1) % seg)
                fs.append((a0, a1, a1 + 1, a0 + 1))
            fs.append(tuple(2 * k for k in range(seg))[::-1])
            fs.append(tuple(2 * k + 1 for k in range(seg)))
            me = bpy.data.meshes.new("wheel")
            me.from_pydata(vs, [], fs)
            me.update(calc_edges=True)
            ob = bpy.data.objects.new(f"GT_WheelProxy_{'F' if Yw < 0 else 'R'}{'L' if side > 0 else 'R'}", me)
            ob.data.materials.append(mat)
            ob.color = WHEEL_DARK
            bpy.context.scene.collection.objects.link(ob)
    return info


def load_blueprint(decimate):
    with bpy.data.libraries.load(os.path.join(IN_DIR, "scaffold-corrected.blend"), link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    ob = [o for o in dst.objects if o is not None and o.type == "MESH"][0]
    if decimate:
        col = bpy.data.collections.new(REF_COLLECTION)
        bpy.context.scene.collection.children.link(col)
        col.objects.link(ob)
        dec = ob.modifiers.new("Decimate", "DECIMATE")
        dec.decimate_type = "COLLAPSE"
        dec.ratio = DECIMATE_RATIO
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
        ob.name = "BT1_Blueprint_Full"
        ob.color = CLAY
    return ob


def mesh_co(me):
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def in_box2(u, v, b):
    return (u >= b[0]) & (u <= b[1]) & (v >= b[2]) & (v <= b[3])


def arch_mask(Y, Z, lines):
    m = np.zeros(Y.shape, bool)
    for (lf, lr), a in zip(lines["legs_px"], lines["arch"]):
        Yf = C.px_to_Y(lf) - ARCH_WIDEN
        Yr = C.px_to_Y(lr) + ARCH_WIDEN
        px = np.arange(a["x0"], a["x0"] + len(a["py"]))
        za = C.py_to_Z(np.array(a["py"]))
        m |= (Y >= Yf) & (Y <= Yr) & (Z < np.interp(C.Y_to_px(Y), px, za) + ARCH_Z_MARGIN)
    return m


def distances(co, blue, boxes, lines):
    X, Y, Z = co[:, 0], co[:, 1], co[:, 2]
    ax = np.abs(X)
    ex = np.zeros(len(co), bool)
    why = {}
    for name, b in boxes["SIDE"].items():
        m = in_box2(Y, Z, b)
        why["SIDE." + name] = int(m.sum())
        ex |= m
    for name, b in boxes["TOP"].items():
        m = in_box2(ax, Y, b)
        why["TOP." + name] = int(m.sum())
        ex |= m
    for name, b in boxes["FRONT"].items():
        m = in_box2(ax, Z, b) & (Y < Y_FAN_FRONT)
        why["FRONT." + name + " (front fascia)"] = int(m.sum())
        ex |= m
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


def folds(me, lower_keys, pole_keys):
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    poles = set(v.index for v in bm.verts if (round(abs(v.co.x), 5), round(v.co.y, 5), round(v.co.z, 5)) in pole_keys)
    low = set(v.index for v in bm.verts if (round(abs(v.co.x), 5), round(v.co.y, 5), round(v.co.z, 5)) in lower_keys)
    rows = []
    skipped = 0
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        fv = set(v.index for f in e.link_faces for v in f.verts)
        if fv & poles or fv & low:
            skipped += 1
            continue
        a = math.degrees(e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0))
        m = (e.verts[0].co + e.verts[1].co) / 2
        rows.append((a, m.x, m.y, m.z))
    bm.free()
    rows.sort(reverse=True)
    angs = np.array([r[0] for r in rows])
    return {"max_deg": float(angs.max()), "at": list(rows[0][1:]), "edges_over_10deg": int(np.sum(angs > FOLD_DEG)),
            "edges_measured": int(len(angs)), "edges_skipped_lower_or_pole": skipped, "poles": len(poles),
            "top": [{"deg": r[0], "at": [r[1], r[2], r[3]]} for r in rows[:15]]}, rows


def centre_profile(ob, masks, boxes_px, cowl, bl):
    """Bonnet and deck centre-line top (vertical ray at x = 0) against the reference silhouette top."""
    R = masks["R_filled"]
    dg = bpy.context.evaluated_depsgraph_get()
    rows = []
    for px in range(0, C.REF_W):
        Y = (px - C.PX_MID) / C.PX_PER_M
        bonnet = Y <= cowl[0] - CURVE_MARGIN
        deck = Y >= bl[0] + CURVE_MARGIN
        if not (bonnet or deck):
            continue
        hit, loc, _, _ = ob.ray_cast(Vector((0.0, Y, 3.0)), Vector((0, 0, -1)))
        if not hit:
            continue
        col = R[:735, px]
        if not col.any():
            continue
        r = int(np.argmax(col))
        z_ref = (C.PX_GROUND - (r - 0.5)) / C.PX_PER_M
        py_mesh = C.PX_GROUND - loc.z * C.PX_PER_M
        inbox = any(b[0] <= px <= b[1] and (b[2] <= r <= b[3] or b[2] <= py_mesh <= b[3]) for b in boxes_px.values())
        if inbox:
            continue
        rows.append((px, Y, loc.z, z_ref, "bonnet" if bonnet else "deck"))
    dev = np.array([abs(r[2] - r[3]) for r in rows]) * 100
    k = int(np.argmax(dev))
    out = {"columns": len(rows), "mean_cm": float(dev.mean()), "max_cm": float(dev.max()), "max_at_px": rows[k][0],
           "max_at_Y": rows[k][1], "max_part": rows[k][4], "signed_at_max_cm": float((rows[k][2] - rows[k][3]) * 100)}
    for part in ("bonnet", "deck"):
        d = np.array([abs(r[2] - r[3]) for r in rows if r[4] == part]) * 100
        if len(d):
            out[part] = {"columns": len(d), "mean_cm": float(d.mean()), "max_cm": float(d.max())}
    return out


def set_engine(scene):
    for eng in ("BLENDER_WORKBENCH", "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            return eng
        except TypeError:
            continue
    return scene.render.engine


def make_cam(name, loc, target, ortho_scale=None, lens=50.0):
    cd = bpy.data.cameras.new(name)
    if ortho_scale:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho_scale
    else:
        cd.lens = lens
    cd.clip_start, cd.clip_end = 0.05, 100.0
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


def render(scene, cam, res, path, visible):
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in visible
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    t0 = time.time()
    os.makedirs(RENDER_DIR, exist_ok=True)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    npz = np.load(os.path.join(OUT_DIR, "tub-mesh.npz"))
    maps = np.load(os.path.join(IN_DIR, "maps.npz"))
    lines = jload(os.path.join(IN_DIR, "reference-lines.json"))
    fields = jload(os.path.join(OUT_DIR, "bt1-fields.json"))
    boxes = json.loads(str(maps["boxes_json"]))
    tub, flipped = build_tub(npz)
    log(f"tub: {len(tub.data.vertices)} verts, {len(tub.data.polygons)} faces (half flipped: {flipped})")
    winfo = wheel_proxies(maps)
    load_blueprint(decimate=True)
    out_blend = os.path.join(OUT_DIR, "Impreza_Tub_Master.blend")
    if os.path.exists(out_blend):
        os.remove(out_blend)
    bpy.ops.wm.save_as_mainfile(filepath=out_blend, compress=True)
    log(f"saved {out_blend}")

    blue = load_blueprint(decimate=False)
    co = mesh_co(tub.data)
    dist, dvals = distances(co, blue, boxes, lines)
    log(f"distances {dist}")
    lower = npz["verts"][npz["lower"]]
    lower_keys = set((round(abs(x), 5), round(y, 5), round(z, 5)) for x, y, z in lower)
    pole_keys = set((round(abs(x), 5), round(y, 5), round(z, 5)) for x, y, z in npz["pole_pts"])
    fold, _ = folds(tub.data, lower_keys, pole_keys)
    log(f"folds max {fold['max_deg']:.1f} deg at {np.round(fold['at'], 3).tolist()}, over 10 deg {fold['edges_over_10deg']}, poles {fold['poles']}")
    masks = np.load(os.path.join(IN_DIR, "sc1-masks.npz"))
    sidefit = jload(os.path.join(IN_DIR, "side-fit.json"))
    prof = centre_profile(tub, masks, sidefit["boxes_px"], fields["cowl_curve"], fields["backlight_curve"])
    log(f"centre profile {prof}")
    X, Y, Z = co[:, 0], co[:, 1], co[:, 2]
    door = (Y >= DOOR_Y[0]) & (Y <= DOOR_Y[1])
    dims = {"width_doors_m": float(2 * np.abs(X[door]).max()), "length_m": float(Y.max() - Y.min()),
            "Y_range": [float(Y.min()), float(Y.max())], "height_m": float(Z.max()), "shoulder": fields["shoulder"]}
    log(f"dims {dims}")

    # renders
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
    wheels = [o.name for o in scene.objects if o.name.startswith("GT_WheelProxy")]
    cy = (C.REF_W / 2 - C.PX_MID) / C.PX_PER_M
    cz = (C.PX_GROUND - C.REF_H / 2) / C.PX_PER_M
    cams = {
        "side": make_cam("CAM_side", (10.0, cy, cz), (0.0, cy, cz), ortho_scale=C.REF_W / C.PX_PER_M),
        "front": make_cam("CAM_front", (0.0, -10.0, 0.82), (0.0, 0.0, 0.82), ortho_scale=2.9),
        "rear": make_cam("CAM_rear", (0.0, 10.0, 0.82), (0.0, 0.0, 0.82), ortho_scale=2.9),
        "front34": make_cam("CAM_front34", (4.9, -5.7, 2.2), (0.0, -0.15, 0.65), lens=50.0),
        "rear34": make_cam("CAM_rear34", (4.9, 5.7, 2.2), (0.0, 0.15, 0.65), lens=50.0),
    }
    files = {}
    p = os.path.join(RENDER_DIR, "side_tub_wheels.png")
    render(scene, cams["side"], (C.REF_W, C.REF_H), p, [tub.name] + wheels)
    files["side_tub_wheels"] = p
    p = os.path.join(RENDER_DIR, "side_tub_only.png")
    render(scene, cams["side"], (C.REF_W, C.REF_H), p, [tub.name])
    files["side_tub_only"] = p
    for v in ("front", "rear", "front34", "rear34"):
        for what, vis in (("blueprint", [blue.name]), ("tub", [tub.name])):
            p = os.path.join(RENDER_DIR, f"view_{v}_{what}.png")
            render(scene, cams[v], TILE, p, vis)
            files[f"view_{v}_{what}"] = p
    sh.light = "MATCAP"
    sh.color_type = "SINGLE"
    sh.single_color = GLOSS_COLOUR
    names = [s.name for s in bpy.context.preferences.studio_lights if s.type == "MATCAP"]
    used = []
    for mc in MATCAPS:
        if mc not in names:
            continue
        sh.studio_light = mc
        used.append(mc)
        for v in ("front34", "rear34"):
            p = os.path.join(RENDER_DIR, f"gloss_{mc.split('.')[0]}_{v}.png")
            render(scene, cams[v], GLOSS_RES, p, [tub.name])
            files[f"gloss_{mc.split('.')[0]}_{v}"] = p
    out = {"distance": dist, "folds": fold, "centre_profile": prof, "dimensions": dims, "wheel_proxies": winfo,
           "render_engine": eng, "matcaps": used, "renders": files, "half_mesh_flipped": flipped,
           "tub_verts": len(tub.data.vertices), "tub_faces": len(tub.data.polygons)}
    with open(os.path.join(OUT_DIR, "bt1-review.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    log(f"BT1 blender done in {time.time() - t0:.1f} s")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
