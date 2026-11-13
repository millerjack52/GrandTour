"""G1 6f/6h in headless Blender: LandCruiser80_Shell.blend (L, G, two bumpers, four wheels as separate objects; L and G
mirrored about X) and the renders for the pictures. Render setup adapted from body_builder/bt2_blender.py (that
script runs on import). Reads shell-mesh.npz and g1-report.json (cameras) from the G1 output folder."""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = r"C:\GrandTour"
OUT = os.path.join(ROOT, r"Art\Export\VehicleTools\landcruiser-grammar-g1-v02")
RDIR = os.path.join(OUT, "debug", "renders")
CLAY = (0.5, 0.5, 0.5, 1.0)
GLASS = (0.12, 0.12, 0.13, 1.0)
DARK = (0.06, 0.06, 0.06, 1.0)
GLOSS = (0.85, 0.85, 0.85)
MATCAPS = ["metal_carpaint.exr", "check_reflection_horizontal.exr"]


def log(m):
    print(m, flush=True)


def mat(name, rgba):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    return m


def vcol(me, rgba):
    a = me.color_attributes.new("GT_Tint", "FLOAT_COLOR", "POINT")
    a.data.foreach_set("color", np.asarray(rgba, float).reshape(-1))
    me.color_attributes.active_color = a
    try:
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    except AttributeError:
        pass


def make(name, V, Fc, colours, mirror=False, out_test=None, face_mat=None):
    fl = [[int(k) for k in f if k >= 0] for f in Fc]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in V], [], fl)
    me.update(calc_edges=True)
    if face_mat is not None:
        me.polygons.foreach_set("material_index", [int(m) for m in face_mat])
    vcol(me, colours)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if out_test is not None:
        n = len(me.polygons)
        nrm, cen = np.empty(n * 3), np.empty(n * 3)
        me.polygons.foreach_get("normal", nrm)
        me.polygons.foreach_get("center", cen)
        nrm, cen = nrm.reshape(-1, 3), cen.reshape(-1, 3)
        sel, axis, sign = out_test(cen)
        if sel.any() and np.sign(nrm[sel, axis].mean()) != sign:
            bm = bmesh.new()
            bm.from_mesh(me)
            for f in bm.faces:
                f.normal_flip()
            bm.to_mesh(me)
            bm.free()
            log(f"{name}: normals flipped outward")
    if mirror:
        m = ob.modifiers.new("Mirror", "MIRROR")
        m.use_axis = (True, False, False)
        m.use_mirror_merge = True
        m.merge_threshold = 0.0005
        dg = bpy.context.evaluated_depsgraph_get()
        full = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        full.name = name
        old = ob.data
        ob.modifiers.clear()
        ob.data = full
        bpy.data.meshes.remove(old)
        if "GT_Tint" in full.color_attributes:
            full.color_attributes.active_color = full.color_attributes["GT_Tint"]
    try:
        ob.data.shade_smooth()
    except AttributeError:
        ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
    return ob


def cam(name, loc, direction, ortho=None, lens=50.0, roll_top=False):
    c = bpy.data.cameras.new(name)
    if ortho:
        c.type = "ORTHO"
        c.ortho_scale = ortho
    else:
        c.lens = lens
    c.clip_start, c.clip_end = 0.05, 100.0
    ob = bpy.data.objects.new(name, c)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    if roll_top:
        ob.rotation_euler = (0.0, 0.0, math.pi / 2)  # looking down, image right = +Y (front at the left)
    else:
        ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return ob


def set_engine(scene):
    for e in ("BLENDER_WORKBENCH", "BLENDER_WORKBENCH_NEXT"):
        try:
            scene.render.engine = e
            return e
        except TypeError:
            continue
    return scene.render.engine


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
    os.makedirs(RDIR, exist_ok=True)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    z = np.load(os.path.join(OUT, "shell-mesh.npz"))
    rep = json.load(open(os.path.join(OUT, "g1-report.json"), encoding="utf-8"))
    clay, glass, dark = mat("GT_Clay", CLAY), mat("GT_GlassTint", GLASS), mat("GT_Wheel", DARK)
    L = make("GT_LC80_L", z["L_v"], z["L_f"], np.tile(CLAY, (len(z["L_v"]), 1)), mirror=True,
             out_test=lambda c: ((np.abs(c[:, 1]) < 0.5) & (c[:, 2] > 0.6) & (c[:, 2] < 1.0), 0, 1.0))
    L.data.materials.append(clay)
    gv = np.clip(z["G_glass_v"], 0, 1)[:, None]
    G = make("GT_LC80_G", z["G_v"], z["G_f"], (1 - gv) * np.array(CLAY) + gv * np.array(GLASS), mirror=True,
             out_test=lambda c: ((np.abs(c[:, 1] - 1.0) < 0.6) & (c[:, 2] > 1.25) & (c[:, 2] < 1.55), 0, 1.0),
             face_mat=z["G_glass"].astype(int))
    G.data.materials.append(clay)
    G.data.materials.append(glass)
    BF = make("GT_LC80_BumperFront", z["BF_v"], z["BF_f"], np.tile(CLAY, (len(z["BF_v"]), 1)),
              out_test=lambda c: (c[:, 1] < c[:, 1].min() + 0.01, 1, -1.0))
    BF.data.materials.append(clay)
    BR = make("GT_LC80_BumperRear", z["BR_v"], z["BR_f"], np.tile(CLAY, (len(z["BR_v"]), 1)),
              out_test=lambda c: (c[:, 1] > c[:, 1].max() - 0.01, 1, 1.0))
    BR.data.materials.append(clay)
    wheels = []
    for k in ("FL", "FR", "RL", "RR"):
        V = z[f"W{k}_v"]
        xc = V[:, 0].mean()
        w = make(f"GT_LC80_Wheel_{k}", V, z[f"W{k}_f"], np.tile(DARK, (len(V), 1)),
                 out_test=lambda c: (c[:, 2] > c[:, 2].max() - 0.02, 2, 1.0))
        w.data.materials.append(dark)
        wheels.append(w.name)
    log(f"L {len(L.data.vertices)} v / {len(L.data.polygons)} f; G {len(G.data.vertices)} v / {len(G.data.polygons)} f")
    out = os.path.join(OUT, "LandCruiser80_Shell.blend")
    if os.path.exists(out):
        os.remove(out)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    log(f"saved {out}")

    scene = bpy.context.scene
    eng = set_engine(scene)
    sh = scene.display.shading
    sh.light = "STUDIO"
    sh.show_cavity = True
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    try:
        sh.color_type = "VERTEX"
    except TypeError:
        sh.color_type = "MATERIAL"
    body = [L.name, G.name, BF.name, BR.name]
    files = {}
    C = rep["cameras"]
    for k, c in C.items():
        cm = cam(f"CAM_{k}", c["loc"], c["dir"], ortho=c["ortho"], roll_top=(k == "top"))
        p = os.path.join(RDIR, f"view_{k}.png")
        render(scene, cm, tuple(c["res"]), p, body + wheels)
        files[f"view_{k}"] = p
    q = {"front34": ((5.6, -6.6, 2.7), (0.0, -0.2, 0.85)), "rear34": ((5.6, 6.6, 2.7), (0.0, 0.25, 0.85))}
    for k, (loc, tgt) in q.items():
        cm = cam(f"CAM_{k}", loc, tuple(Vector(tgt) - Vector(loc)), lens=50.0)
        p = os.path.join(RDIR, f"quarter_{k}.png")
        render(scene, cm, (1600, 1100), p, body + wheels)
        files[f"quarter_{k}"] = p
    sh.light = "MATCAP"
    sh.color_type = "SINGLE"
    sh.single_color = GLOSS
    names = [s.name for s in bpy.context.preferences.studio_lights if s.type == "MATCAP"]
    for mc in MATCAPS:
        if mc in names:
            sh.studio_light = mc
            for k, (loc, tgt) in q.items():
                cm = bpy.data.objects[f"CAM_{k}"]
                p = os.path.join(RDIR, f"gloss_{mc.split('.')[0]}_{k}.png")
                render(scene, cm, (1000, 700), p, body)
                files[f"gloss_{mc.split('.')[0]}_{k}"] = p
    with open(os.path.join(OUT, "g1-renders.json"), "w", encoding="utf-8") as f:
        json.dump({"engine": eng, "files": files}, f, indent=1)
    log("G1 blender done")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
