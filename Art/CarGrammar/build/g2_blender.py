"""G2 9e in headless Blender: LandCruiser80_Panels.blend (each panel its own object, bumpers and wheels from G1 v02)
and the renders: clay quarters (a grey per panel, glass dark), the same opened about the LAY-12 hinges, the side view
at the G0 registration, and car-paint gloss. Render helpers adapted from g1_blender.py."""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = r"C:\GrandTour"
OUT = os.path.join(ROOT, r"Art\Export\VehicleTools\landcruiser-grammar-g2-v01")
G1 = os.path.join(ROOT, r"Art\Export\VehicleTools\landcruiser-grammar-g1-v02")
RDIR = os.path.join(OUT, "debug", "renders")
GLASS = (0.10, 0.11, 0.12, 1.0)
DARK = (0.06, 0.06, 0.06, 1.0)
GREYS = {"FrontPanel": 0.52, "Bonnet": 0.60, "Cowl": 0.44, "Fender": 0.56, "Rocker": 0.40, "FrontDoor": 0.64, "RearDoor": 0.58,
         "Quarter": 0.50, "Valance": 0.42, "LowerTailgate": 0.62, "UpperHatch": 0.56, "CabinFrame": 0.48, "Bumper": 0.36}
OPEN = {"FrontDoor_L": 50.0, "FrontDoor_R": 50.0, "Bonnet": 35.0, "LowerTailgate": 80.0, "UpperHatch": 60.0}  # plan 9e


def log(m):
    print(m, flush=True)


def make(name, V, Fs, rgba):
    fl = [[int(k) for k in f if k >= 0] for f in Fs]
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in V], [], fl)
    me.update(calc_edges=True)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.color = rgba
    try:
        me.shade_smooth()
    except AttributeError:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    return ob


def cam(name, loc, direction, ortho=None, lens=50.0):
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
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
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
    os.makedirs(RDIR, exist_ok=True)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    z = np.load(os.path.join(OUT, "panels.npz"))
    info = json.load(open(os.path.join(OUT, "g2-build.json"), encoding="utf-8"))
    rep1 = json.load(open(os.path.join(G1, "g1-report.json"), encoding="utf-8"))
    names = sorted({k.split("__")[0] for k in z.files})
    objs = {}
    for n in names:
        base = n.split("_")[0] if not n.startswith("Glass") else "Glass"
        if n.startswith("Glass"):
            col = GLASS
        else:
            g = GREYS.get(base, 0.5)
            col = (g, g, g, 1.0)
        objs[n] = make(n, z[n + "__v"], z[n + "__f"], col)
    s1 = np.load(os.path.join(G1, "shell-mesh.npz"))
    for k, nm in (("BF", "BumperFront"), ("BR", "BumperRear")):
        g = GREYS["Bumper"]
        objs[nm] = make(nm, s1[k + "_v"], s1[k + "_f"], (g, g, g, 1.0))
    for k in ("FL", "FR", "RL", "RR"):
        objs["Wheel_" + k] = make("Wheel_" + k, s1[f"W{k}_v"], s1[f"W{k}_f"], DARK)
    # rendering aid (not a panel): a dark inner skin 25 mm inside the G1 v02 shell, so gaps read dark instead of
    # showing the background through the open shell
    for k in ("L", "G"):
        V = s1[k + "_v"]
        Fh = [[int(q) for q in f if q >= 0] for f in s1[k + "_f"]]
        Vm = V * np.array([-1, 1, 1])
        Vall = np.vstack([V, Vm])
        Fall = Fh + [[q + len(V) for q in f[::-1]] for f in Fh]
        me = bpy.data.meshes.new("Backing_" + k)
        me.from_pydata([tuple(map(float, v)) for v in Vall], [], Fall)
        me.update(calc_edges=True)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        for vv in bm.verts:
            vv.co -= 0.025 * vv.normal
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new("Backing_" + k, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.color = (0.07, 0.07, 0.07, 1.0)
        objs["Backing_" + k] = ob
    log(f"objects {len(objs)}")
    out = os.path.join(OUT, "LandCruiser80_Panels.blend")
    if os.path.exists(out):
        os.remove(out)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    log(f"saved {out}")

    scene = bpy.context.scene
    for e in ("BLENDER_WORKBENCH", "BLENDER_WORKBENCH_NEXT"):
        try:
            scene.render.engine = e
            break
        except TypeError:
            continue
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
    allv = list(objs)
    body = [n for n in objs if not n.startswith("Wheel")]
    q = {"front34": ((5.6, -6.6, 2.7), (0.0, -0.2, 0.85)), "rear34": ((5.6, 6.6, 2.7), (0.0, 0.25, 0.85))}
    cams = {k: cam("CAM_" + k, loc, tuple(Vector(tgt) - Vector(loc))) for k, (loc, tgt) in q.items()}
    files = {}
    for k, cm in cams.items():
        p = os.path.join(RDIR, f"quarter_{k}.png")
        render(scene, cm, (1600, 1100), p, allv)
        files[f"quarter_{k}"] = p
    closeups = {"cu_front_corner": ((2.0, -3.6, 1.6), (0.75, -1.95, 1.0)), "cu_apillar": ((2.4, -1.6, 1.7), (0.85, -0.6, 1.1)),
                "cu_rear_door": ((2.6, 0.6, 1.0), (0.9, 1.15, 0.7)), "cu_tail": ((2.0, 4.3, 1.5), (0.4, 2.55, 0.95)),
                "cu_rocker": ((2.4, -0.2, 0.6), (0.9, 0.0, 0.45))}
    for k, (loc, tgt) in closeups.items():
        cm = cam("CAM_" + k, loc, tuple(Vector(tgt) - Vector(loc)), lens=50.0)
        p = os.path.join(RDIR, f"{k}.png")
        render(scene, cm, (1000, 750), p, allv)
    c = rep1["cameras"]["side"]
    cs = cam("CAM_side", c["loc"], c["dir"], ortho=c["ortho"])
    p = os.path.join(RDIR, "view_side.png")
    render(scene, cs, tuple(c["res"]), p, allv)
    files["view_side"] = p
    # opened about the LAY-12 hinges (followers move with their panel)
    saved = {n: ob.matrix_world.copy() for n, ob in objs.items()}
    for n, ang in OPEN.items():
        h = info["hinges"][n]
        o = Vector(h["origin"])
        ax = Vector(h["axis"])
        R = Matrix.Translation(o) @ Matrix.Rotation(math.radians(h["deg"] if abs(h["deg"]) == ang else math.copysign(ang, h["deg"])), 4, ax) @ Matrix.Translation(-o)
        objs[n].matrix_world = R @ objs[n].matrix_world
        for f, lead in info["follow"].items():
            if lead == n and f in objs:
                objs[f].matrix_world = R @ objs[f].matrix_world
    for k, cm in cams.items():
        p = os.path.join(RDIR, f"open_{k}.png")
        render(scene, cm, (1600, 1100), p, allv)
        files[f"open_{k}"] = p
    for n, mw in saved.items():
        objs[n].matrix_world = mw
    sh.light = "MATCAP"
    sh.color_type = "OBJECT"  # the matcap tinted per object: panels and bumpers light, glass and the backing dark
    for n, ob in objs.items():
        if not (n.startswith("Glass") or n.startswith("Backing") or n.startswith("Wheel")):
            ob.color = (0.85, 0.85, 0.85, 1.0)
    names_mc = [s.name for s in bpy.context.preferences.studio_lights if s.type == "MATCAP"]
    if "metal_carpaint.exr" in names_mc:
        sh.studio_light = "metal_carpaint.exr"
    for k, cm in cams.items():
        p = os.path.join(RDIR, f"gloss_{k}.png")
        render(scene, cm, (1400, 960), p, body)
        files[f"gloss_{k}"] = p
    with open(os.path.join(OUT, "g2-renders.json"), "w", encoding="utf-8") as f:
        json.dump(files, f, indent=1)
    log("G2 blender done")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
