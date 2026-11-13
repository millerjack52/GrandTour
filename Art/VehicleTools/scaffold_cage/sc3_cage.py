"""SC3 part 2 (Blender, headless): build the half cage from cage-targets.npz, Mirror + Subdivision
Surface, fit the limit surface to the samples (4e), review extras (4f), save the blend.

Plan: docs/SCAFFOLD_CAGE_PLAN.md section 4e-4f. Reads cage-targets.npz (sc3_lines.py, built from
maps.npz and the two json files) and maps.npz (raw SIDE for the wheel proxies).
Run: blender.exe -b --python-exit-code 1 --python sc3_cage.py
Writes Impreza_Scaffold_Cage.blend and sc3-fit.json.
"""
import math
import os
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sc_common as C  # noqa: E402

CAGE_NAME = "GT_Impreza_BodyCage"
MIRROR_MERGE = 0.001
SUBSURF_LEVELS = 2
FIT_PASSES = 3 if C.V2 else 8  # plan 9b.6
FIT_DAMPING_RETRY = 0.7
VERIFY_MAX_DIST = 0.10
WHEEL_R = 0.3575
WHEEL_W = 0.25
WHEEL_SEARCH_R = 0.2
DECIMATE_RATIO = 0.05
REF_COLLECTION = "REF | Tripo scaffold (corrected)"
CAGE_GREY = (0.5, 0.5, 0.5, 1.0)
WHEEL_DARK = (0.06, 0.06, 0.06, 1.0)


def log(msg):
    print(msg, flush=True)


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)


def make_material(name, rgba):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.6
    return mat


def build_cage(verts, faces):
    me = bpy.data.meshes.new(CAGE_NAME)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(int(i) for i in f) for f in faces])
    me.update(calc_edges=True)
    try:
        me.shade_smooth()
    except AttributeError:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    obj = bpy.data.objects.new(CAGE_NAME, me)
    bpy.context.scene.collection.objects.link(obj)
    mir = obj.modifiers.new("Mirror", "MIRROR")
    mir.use_axis = (True, False, False)
    mir.use_clip = True
    mir.use_mirror_merge = True
    mir.merge_threshold = MIRROR_MERGE
    sub = obj.modifiers.new("Subdivision", "SUBSURF")
    sub.subdivision_type = "CATMULL_CLARK"
    sub.levels = SUBSURF_LEVELS
    sub.render_levels = SUBSURF_LEVELS
    sub.use_limit_surface = True
    obj.color = CAGE_GREY
    obj.data.materials.append(make_material("GT_Clay", CAGE_GREY))
    return obj


def orientation_check(obj):
    me = obj.data
    n = len(me.polygons)
    nrm = np.empty(n * 3)
    cen = np.empty(n * 3)
    me.polygons.foreach_get("normal", nrm)
    me.polygons.foreach_get("center", cen)
    nrm = nrm.reshape(-1, 3)
    cen = cen.reshape(-1, 3)
    top = cen[:, 2] > 1.3
    side = (cen[:, 0] > 0.75) & (cen[:, 2] > 0.4) & (cen[:, 2] < 0.9)
    return float(nrm[top, 2].mean()), float(nrm[side, 0].mean())


def evaluated_coords(obj, n):
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    m = len(me.vertices)
    co = np.empty(m * 3)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    co = co.reshape(-1, 3)
    return co[:n], m


def set_cage(obj, cage):
    obj.data.vertices.foreach_set("co", cage.ravel())
    obj.data.update()


def fit(obj, t, centre, damping):
    n = len(t)
    cage = t.copy()
    set_cage(obj, cage)
    hist = []
    verify = None
    for p in range(FIT_PASSES):
        ev, m = evaluated_coords(obj, n)
        if verify is None:
            d = np.linalg.norm(ev - cage, axis=1)
            verify = {"evaluated_verts": int(m), "max_dist_first_N_to_cage": float(d.max()),
                      "median_dist": float(np.median(d))}
        r = t - ev
        hist.append(float(np.linalg.norm(r, axis=1).max()))
        cage = cage + damping * r
        cage[centre, 0] = 0.0
        set_cage(obj, cage)
        log(f"  pass {p + 1}: max residual before update {hist[-1] * 1000:.2f} mm")
    ev, _ = evaluated_coords(obj, n)
    final = np.linalg.norm(t - ev, axis=1)
    return cage, hist, final, verify


def wheel_proxies(maps, mat):
    SR = maps["SIDE_raw"]
    ys, zs = maps["ys"], maps["zs"]
    Yg, Zg = np.meshgrid(ys, zs, indexing="ij")
    objs = []
    info = []
    for Yw in C.WHEEL_Y:
        sel = ((Yg - Yw) ** 2 + (Zg - C.WHEEL_Z) ** 2 <= WHEEL_SEARCH_R ** 2) & np.isfinite(SR)
        x_out = float(np.median(SR[sel]))
        info.append({"Y": Yw, "outer_face_X": x_out, "cells": int(sel.sum())})
        for side in (1.0, -1.0):
            xc = side * (x_out - WHEEL_W / 2)
            me = bpy.data.meshes.new("wheel")
            # cylinder along X
            seg = 48
            vs, fs = [], []
            for k in range(seg):
                a = 2 * math.pi * k / seg
                for dx in (-WHEEL_W / 2, WHEEL_W / 2):
                    vs.append((xc + dx, Yw + WHEEL_R * math.cos(a), C.WHEEL_Z + WHEEL_R * math.sin(a)))
            for k in range(seg):
                a0, a1 = 2 * k, 2 * ((k + 1) % seg)
                fs.append((a0, a1, a1 + 1, a0 + 1))
            fs.append(tuple(2 * k for k in range(seg))[::-1])
            fs.append(tuple(2 * k + 1 for k in range(seg)))
            me.from_pydata(vs, [], fs)
            me.update(calc_edges=True)
            name = f"GT_WheelProxy_{'F' if Yw < 0 else 'R'}{'L' if side > 0 else 'R'}"
            ob = bpy.data.objects.new(name, me)
            ob.data.materials.append(mat)
            ob.color = WHEEL_DARK
            bpy.context.scene.collection.objects.link(ob)
            objs.append(ob)
    return objs, info


def decimated_reference():
    path = os.path.join(C.OUT_DIR, "scaffold-corrected.blend")
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    col = bpy.data.collections.new(REF_COLLECTION)
    bpy.context.scene.collection.children.link(col)
    out = []
    for ob in dst.objects:
        if ob is None or ob.type != "MESH":
            continue
        col.objects.link(ob)
        dec = ob.modifiers.new("Decimate", "DECIMATE")
        dec.decimate_type = "COLLAPSE"
        dec.ratio = DECIMATE_RATIO
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
        ev = ob.evaluated_get(dg)
        new_me = bpy.data.meshes.new_from_object(ev)
        old = ob.data
        ob.modifiers.clear()
        ob.data = new_me
        bpy.data.meshes.remove(old)
        ob.name = "REF_TripoScaffold_Corrected_Decimated"
        out.append((ob.name, len(new_me.polygons)))
    col.hide_viewport = True
    col.hide_render = True
    lc = bpy.context.view_layer.layer_collection.children.get(REF_COLLECTION)
    if lc is not None:
        lc.hide_viewport = True
    return out


def main():
    t0 = time.time()
    clear_scene()
    tg = np.load(os.path.join(C.OUT_DIR, "cage-targets.npz"))
    maps = np.load(os.path.join(C.OUT_DIR, "maps.npz"))
    t = tg["verts"].astype(float)
    faces = tg["faces"]
    centre = tg["centre"].astype(bool)
    obj = build_cage(t, faces)
    crease = tg["crease_verts"].astype(int) if (C.V2 and "crease_verts" in tg.files) else np.array([], int)
    if len(crease):
        att = obj.data.attributes.get("crease_vert") or obj.data.attributes.new("crease_vert", "FLOAT", "POINT")
        vals = np.zeros(len(obj.data.vertices))
        vals[crease] = 1.0
        att.data.foreach_set("value", vals)
        obj.data.update()
        log(f"crease_vert = 1.0 on vertices {crease.tolist()}")
    nz_top, nx_side = orientation_check(obj)
    log(f"cage: {len(t)} verts, {len(faces)} faces; mean normal z on roof {nz_top:+.2f}, mean normal x on doors {nx_side:+.2f}")
    if nz_top < 0 or nx_side < 0:
        raise RuntimeError("cage normals point inward")

    log("fit, damping 1.0")
    cage, hist, final, verify = fit(obj, t, centre, 1.0)
    attempts = [{"damping": 1.0, "history_m": hist, "final_max_m": float(final.max())}]
    log(f"  verify first-N correspondence: {verify}")
    if not hist[2] < hist[0]:
        log("max residual not falling by pass 3: retry with damping 0.7")
        cage, hist, final, verify2 = fit(obj, t, centre, FIT_DAMPING_RETRY)
        attempts.append({"damping": FIT_DAMPING_RETRY, "history_m": hist, "final_max_m": float(final.max())})
        if not hist[-1] < hist[0]:
            log("STOP: fit residual still grows")
    after = hist[1:] + [float(final.max())]
    log("max residual after each pass (mm): " + ", ".join(f"{a * 1000:.2f}" for a in after))
    crease_check = None
    if len(crease):
        ev, _ = evaluated_coords(obj, len(t))
        dc = np.linalg.norm(ev[crease] - cage[crease], axis=1)
        crease_check = {"verts": crease.tolist(), "max_eval_minus_control_mm": float(dc.max() * 1000),
                        "per_vertex_mm": (dc * 1000).tolist()}
        log(f"crease check: evaluated - control at crease verts, max {dc.max() * 1000:.4f} mm")
    worst = int(np.argmax(final))
    log(f"final residual after {FIT_PASSES} passes: max {final.max() * 1000:.3f} mm at vertex {worst} "
        f"{np.round(t[worst], 3).tolist()}, median {np.median(final) * 1000:.3f} mm")

    wheel_mat = make_material("GT_WheelProxy_Dark", WHEEL_DARK)
    _, winfo = wheel_proxies(maps, wheel_mat)
    log(f"wheel proxies: {winfo}")
    dec = decimated_reference()
    log(f"decimated reference: {dec}")
    out = os.path.join(C.OUT_DIR, "Impreza_Scaffold_Cage.blend")
    if os.path.exists(out):
        os.remove(out)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    C.save_json("sc3-fit.json", {
        "attempts": attempts, "final_residual_max_m": float(final.max()),
        "residual_after_each_pass_m": after, "initial_residual_m": hist[0], "crease_check": crease_check,
        "final_residual_median_m": float(np.median(final)), "worst_vertex": worst,
        "worst_vertex_target": t[worst].tolist(), "verify": verify,
        "cage_verts": int(len(t)), "cage_faces": int(len(faces)), "wheel_proxies": winfo,
        "decimated_reference": dec, "fitted_cage": cage.tolist(),
    })
    log(f"SC3 cage done in {time.time() - t0:.1f} s")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
