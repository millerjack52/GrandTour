"""SC4 part 1 (Blender, headless): checks and renders.

Plan: docs/SCAFFOLD_CAGE_PLAN.md section 5. Opens Impreza_Scaffold_Cage.blend, appends the full
corrected scaffold, computes the report numbers, renders the clay / matcap views (Workbench, film
transparent) into debug/renders/, and writes the projected control-cage edges for cage-wire.png.
sc4_compose.py (system Python) composes the four pictures and writes report.json.
Run: blender.exe -b --python-exit-code 1 --python sc4_review.py
"""
import json
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sc_common as C  # noqa: E402

CAGE_NAME = "GT_Impreza_BodyCage"
RENDER_DIR = os.path.join(C.DEBUG_DIR, "renders")
CLAY = (0.5, 0.5, 0.5, 1.0)
GLOSS_COLOUR = (0.85, 0.85, 0.85)
MATCAPS = ["metal_carpaint.exr", "check_reflection_horizontal.exr"]
TILE = (800, 560)
WIRE_RES = (1200, 800)
GLOSS_RES = (1000, 700)
WIRE_SAMPLES = 8
WIRE_TOL = 0.03
DOOR_Y = (-0.6, 1.0)
ARCH_WIDEN = 0.03
UPPER_COLS_V2 = (150, 1700)  # plan 9c
DIHEDRAL_TOP = 12
ARCH_Z_MARGIN = 0.04
GPT_AXIS = ("GPT's rebuild_impreza_orthographic.py lays the car's length along Y with forward = -Y "
            "(front=-1.97, back=2.0925), the same convention as this cage.")


def log(m):
    print(m, flush=True)


def set_engine(scene):
    for eng in ("BLENDER_WORKBENCH", "BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            return eng
        except TypeError:
            continue
    return scene.render.engine


def mesh_arrays(me):
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def evaluated_mesh(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    return me


def topology(cage, NS, NJ):
    me = cage.data
    n_faces = len(me.polygons)
    all_quads = all(len(p.vertices) == 4 for p in me.polygons)
    nv = len(me.vertices)
    lower = set(i * NJ + 11 for i in range(NS))
    base = NS * NJ
    for cap in range(2):
        for c in range(4):
            lower.add(base + cap * 28 + c * 7 + 6)
    co = mesh_arrays(me)
    bm = bmesh.new()
    bm.from_mesh(me)
    over, bnd_lower, bnd_centre, bnd_other = 0, 0, 0, []
    for e in bm.edges:
        k = len(e.link_faces)
        if k > 2:
            over += 1
        elif k == 1:
            a, b = e.verts[0].index, e.verts[1].index
            if a in lower and b in lower:
                bnd_lower += 1
            elif abs(co[a, 0]) < 1e-6 and abs(co[b, 0]) < 1e-6:
                bnd_centre += 1
            else:
                bnd_other.append([a, b])
    nm_verts = sum(1 for v in bm.verts if not v.is_manifold and v.index not in lower and abs(co[v.index, 0]) > 1e-6)
    bm.free()
    # mirrored control cage (Mirror only)
    sub = cage.modifiers["Subdivision"]
    sub.show_viewport = False
    mme = evaluated_mesh(cage)
    sub.show_viewport = True
    bm = bmesh.new()
    bm.from_mesh(mme)
    m_over = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    m_bnd = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    m_faces = len(bm.faces)
    m_quads = all(len(f.verts) == 4 for f in bm.faces)
    bm.free()
    return {
        "half_cage_faces": n_faces, "half_cage_verts": nv, "all_quads": all_quads,
        "half_edges_more_than_2_faces": over, "half_boundary_lower": bnd_lower,
        "half_boundary_centre_line": bnd_centre, "half_boundary_other": len(bnd_other),
        "half_nonmanifold_verts_other": nm_verts,
        "mirrored_faces": m_faces, "mirrored_all_quads": m_quads, "mirrored_edges_more_than_2_faces": m_over,
        "mirrored_boundary_edges": m_bnd, "mirrored_boundary_expected_lower": 2 * bnd_lower,
        "nonmanifold_other_than_lower_boundary": over + len(bnd_other) + m_over + (m_bnd - 2 * bnd_lower),
    }, mme


def in_box2(u, v, b):
    return (u >= b[0]) & (u <= b[1]) & (v >= b[2]) & (v <= b[3])


def arch_mask_points(Y, Z, lines):
    m = np.zeros(Y.shape, bool)
    for (lf, lr), a in zip(lines["legs_px"], lines["arch"]):
        Yf = C.px_to_Y(lf) - ARCH_WIDEN
        Yr = C.px_to_Y(lr) + ARCH_WIDEN
        px = np.arange(a["x0"], a["x0"] + len(a["py"]))
        za = C.py_to_Z(np.array(a["py"]))
        z_at = np.interp(C.Y_to_px(Y), px, za)
        m |= (Y >= Yf) & (Y <= Yr) & (Z < z_at + ARCH_Z_MARGIN)
    return m


def distances(ev_co, scaffold, boxes, lines, y_front):
    X, Y, Z = ev_co[:, 0], ev_co[:, 1], ev_co[:, 2]
    ax = np.abs(X)
    ex = np.zeros(len(ev_co), bool)
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
        m = in_box2(ax, Z, b) & (Y <= y_front + 1e-6)
        why["FRONT." + name + " (front cap)"] = int(m.sum())
        ex |= m
    am = arch_mask_points(Y, Z, lines)
    why["arch openings"] = int(am.sum())
    ex |= am
    d = np.full(len(ev_co), np.nan)
    for i in np.where(~ex)[0]:
        ok, p, n, _ = scaffold.closest_point_on_mesh(Vector(ev_co[i]))
        if ok:
            d[i] = (Vector(ev_co[i]) - p).length
    v = np.isfinite(d)
    imax = int(np.nanargmax(d))
    return {
        "evaluated_verts": int(len(ev_co)), "excluded": int(ex.sum()), "excluded_by": why, "measured": int(v.sum()),
        "median_cm": float(np.median(d[v]) * 100), "p95_cm": float(np.percentile(d[v], 95) * 100),
        "max_cm": float(d[imax] * 100), "max_at": [float(c) for c in ev_co[imax]],
    }, d


def silhouette(ev_me):
    co = mesh_arrays(ev_me)
    polys = [tuple(p.vertices) for p in ev_me.polygons]
    bvh = BVHTree.FromPolygons([tuple(c) for c in co], polys)
    H, W = 760, C.REF_W
    sil = np.zeros((C.REF_H, W), bool)
    d = Vector((-1.0, 0.0, 0.0))
    for py in range(H):
        Z = (C.PX_GROUND - py) / C.PX_PER_M
        for px in range(W):
            Y = (px - C.PX_MID) / C.PX_PER_M
            hit = bvh.ray_cast(Vector((3.0, Y, Z)), d, 10.0)
            if hit[0] is not None:
                sil[py, px] = True
    return sil


def contour_checks(sil, R, boxes_px, lines):
    W = C.REF_W
    top_c = np.full(W, -1)
    top_r = np.full(W, -1)
    for x in range(W):
        a = np.where(sil[:, x])[0]
        b = np.where(R[:735, x])[0]
        if len(a):
            top_c[x] = a[0]
        if len(b):
            top_r[x] = b[0]

    def in_any_box(x, y):
        for (x0, x1, y0, y1) in boxes_px.values():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return True
        return False

    dev, cols = [], []
    for x in range(W):
        if top_c[x] < 0 or top_r[x] < 0:
            continue
        if C.V2 and not (UPPER_COLS_V2[0] <= x <= UPPER_COLS_V2[1]):
            continue
        if in_any_box(x, top_c[x]) or in_any_box(x, top_r[x]):
            continue
        dev.append(abs(int(top_c[x]) - int(top_r[x])) / 4.0)  # 1 px = 0.25 cm
        cols.append(x)
    dev = np.array(dev)
    k = int(np.argmax(dev))
    upper = {"columns": len(cols), "mean_cm": float(dev.mean()), "max_cm": float(dev.max()),
             "max_at_px": int(cols[k]), "max_at_Y": float(C.px_to_Y(cols[k])),
             "p95_cm": float(np.percentile(dev, 95)),
             "cage_cols": [int(np.min(np.where(top_c >= 0)[0])), int(np.max(np.where(top_c >= 0)[0]))],
             "ref_cols": [int(np.min(np.where(top_r >= 0)[0])), int(np.max(np.where(top_r >= 0)[0]))]}
    # arch edge: lowest cage silhouette row between the legs vs z_arch
    adev, apx, signed = [], [], []
    for (lf, lr), a in zip(lines["legs_px"], lines["arch"]):
        for i, py in enumerate(a["py"]):
            x = a["x0"] + i
            rows = np.where(sil[:, x])[0]
            if not len(rows):
                adev.append(np.inf)
                apx.append(x)
                signed.append(np.nan)
                continue
            low = rows.max()
            adev.append(abs(low - py) / 4.0)
            signed.append((low - py) / 4.0)
            apx.append(x)
    adev = np.array(adev)
    k = int(np.argmax(adev))
    arch = {"columns": len(adev), "max_cm": float(adev[k]), "max_at_px": int(apx[k]), "max_at_Y": float(C.px_to_Y(apx[k])),
            "mean_cm": float(np.mean(adev[np.isfinite(adev)])), "p95_cm": float(np.percentile(adev[np.isfinite(adev)], 95)),
            "cols_over_1p5cm": int(np.sum(adev > 1.5))}
    return upper, arch, top_c


def dihedral(ev_me, stations):
    """Largest angle between the normals of adjacent faces of the evaluated mesh (fold detector)."""
    bm = bmesh.new()
    bm.from_mesh(ev_me)
    bm.normal_update()
    rows = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        a = e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0)
        mid = (e.verts[0].co + e.verts[1].co) / 2
        rows.append((math.degrees(a), mid.x, mid.y, mid.z))
    bm.free()
    rows.sort(reverse=True)
    sy = np.array([st["Y"] for st in stations])

    def near(y):
        i = int(np.argmin(np.abs(sy - y)))
        return f"{stations[i]['kind']} (Y {sy[i]:.3f})"

    top = [{"deg": r[0], "at": [r[1], r[2], r[3]], "nearest_station": near(r[2])} for r in rows[:DIHEDRAL_TOP]]
    angs = np.array([r[0] for r in rows])
    return {"max_deg": float(angs.max()), "at": top[0]["at"], "nearest_station": top[0]["nearest_station"],
            "p99_deg": float(np.percentile(angs, 99)), "edges_over_20deg": int(np.sum(angs > 20)),
            "edges_over_30deg": int(np.sum(angs > 30)), "top": top}


def make_cam(name, loc, target, ortho_scale=None, lens=50.0):
    cd = bpy.data.cameras.new(name)
    if ortho_scale:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho_scale
    else:
        cd.lens = lens
    cd.clip_start = 0.05
    cd.clip_end = 100.0
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    direction = Vector(target) - Vector(loc)
    ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
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


def wire_projection(scene, cam, res, ctrl_me, surf_bvh):
    co = mesh_arrays(ctrl_me)
    scene.render.resolution_x, scene.render.resolution_y = res
    W, H = res
    cam_loc = cam.matrix_world.translation
    view_dir = (cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
    ortho = cam.data.type == "ORTHO"
    segs = []
    for e in ctrl_me.edges:
        a, b = co[e.vertices[0]], co[e.vertices[1]]
        pts = []
        for k in range(WIRE_SAMPLES + 1):
            p = Vector(a + (b - a) * k / WIRE_SAMPLES)
            if ortho:
                origin = p - view_dir * 20.0
                dirv = view_dir
                dist = 20.0
            else:
                dirv = (p - cam_loc)
                dist = dirv.length
                dirv = dirv.normalized()
                origin = cam_loc
            hit = surf_bvh.ray_cast(origin, dirv, dist + 1.0)
            vis = hit[0] is None or hit[3] >= dist - WIRE_TOL
            s = world_to_camera_view(scene, cam, p)
            pts.append((float(s.x * W), float((1 - s.y) * H), bool(vis)))
        segs.append(pts)
    return segs


def main():
    t0 = time.time()
    os.makedirs(RENDER_DIR, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(C.OUT_DIR, "Impreza_Scaffold_Cage.blend"))
    scene = bpy.context.scene
    cage = bpy.data.objects[CAGE_NAME]
    tg = np.load(os.path.join(C.OUT_DIR, "cage-targets.npz"))
    NS, NJ = int(tg["NS"]), int(tg["NJ"])
    lines = C.load_json("reference-lines.json")
    fitj = C.load_json("sc3-fit.json")
    clean = C.load_json("sc2-clean.json")
    sidefit = C.load_json("side-fit.json")
    cl = C.load_json("cage-lines.json")
    y_front = cl["stations"][0]["Y"]
    masks = np.load(os.path.join(C.OUT_DIR, "sc1-masks.npz"))

    # full corrected scaffold
    with bpy.data.libraries.load(os.path.join(C.OUT_DIR, "scaffold-corrected.blend"), link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    scaffold = [o for o in dst.objects if o is not None and o.type == "MESH"][0]
    scene.collection.objects.link(scaffold)
    scaffold.name = "SC4_TripoScaffold_Corrected"
    scaffold.color = CLAY

    # 1 topology
    topo, ctrl_me = topology(cage, NS, NJ)
    log(f"topology {topo}")
    # 2 fit residual (re-evaluated)
    ev_me = evaluated_mesh(cage)
    ev_co = mesh_arrays(ev_me)
    t = tg["verts"]
    res = np.linalg.norm(ev_co[:len(t)] - t, axis=1)
    fit_res = {"max_mm": float(res.max() * 1000), "median_mm": float(np.median(res) * 1000),
               "max_at": [float(c) for c in t[int(np.argmax(res))]], "history_mm": [h * 1000 for h in fitj["attempts"][-1]["history_m"]],
               "attempts": len(fitj["attempts"])}
    over = np.where(res > 0.002)[0]
    where = []
    for i in over:
        if i < NS * NJ:
            where.append({"vertex": int(i), "station": int(i // NJ), "j": int(i % NJ), "Y": float(t[i, 1]), "mm": float(res[i] * 1000)})
        else:
            k = int(i - NS * NJ)
            cap = "front" if k < 28 else "rear"
            k %= 28
            where.append({"vertex": int(i), "cap": cap, "c": k // 7, "r": k % 7 + 1, "mm": float(res[i] * 1000)})
    fit_res["verts_over_2mm"] = len(over)
    fit_res["over_2mm"] = where
    log(f"fit residual {fit_res}")
    # 3 distances
    dist, dvals = distances(ev_co, scaffold, clean["boxes"], lines, y_front)
    log(f"distances {dist}")
    np.save(os.path.join(C.OUT_DIR, "sc4-distances.npy"), np.c_[ev_co, dvals])
    # 4 silhouette
    tt = time.time()
    sil = silhouette(ev_me)
    np.save(os.path.join(C.OUT_DIR, "sc4-silhouette.npy"), sil)
    upper, arch, top_c = contour_checks(sil, masks["R_filled"], sidefit["boxes_px"], lines)
    log(f"silhouette {time.time() - tt:.1f} s; upper {upper}; arch {arch}")
    dih = dihedral(ev_me, cl["stations"])
    log(f"dihedral max {dih['max_deg']:.1f} deg at {np.round(dih['at'], 3).tolist()} near {dih['nearest_station']}; "
        f"edges > 20 deg {dih['edges_over_20deg']}, > 30 deg {dih['edges_over_30deg']}")
    # 5 dimensions
    X, Y, Z = ev_co[:, 0], ev_co[:, 1], ev_co[:, 2]
    door = (Y >= DOOR_Y[0]) & (Y <= DOOR_Y[1])
    sl = np.abs(Y) < 0.02
    dims = {"width_doors_max_m": float(2 * np.abs(X[door]).max()), "width_at_Y0_m": float(2 * np.abs(X[sl]).max()),
            "length_m": float(Y.max() - Y.min()), "Y_range": [float(Y.min()), float(Y.max())],
            "height_m": float(Z.max()), "Z_min": float(Z.min())}
    log(f"dims {dims}")

    # renders
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
    cage.color = CLAY
    wheels = [o.name for o in scene.objects if o.name.startswith("GT_WheelProxy")]
    log(f"engine {eng}, wheels {wheels}")
    cams = {
        "side": make_cam("CAM_side", (10.0, (C.REF_W / 2 - C.PX_MID) / C.PX_PER_M, (C.PX_GROUND - C.REF_H / 2) / C.PX_PER_M),
                         (0.0, (C.REF_W / 2 - C.PX_MID) / C.PX_PER_M, (C.PX_GROUND - C.REF_H / 2) / C.PX_PER_M),
                         ortho_scale=C.REF_W / C.PX_PER_M),
        "front": make_cam("CAM_front", (0.0, -10.0, 0.82), (0.0, 0.0, 0.82), ortho_scale=2.9),
        "rear": make_cam("CAM_rear", (0.0, 10.0, 0.82), (0.0, 0.0, 0.82), ortho_scale=2.9),
        "front34": make_cam("CAM_front34", (4.9, -5.7, 2.2), (0.0, -0.15, 0.65), lens=50.0),
        "rear34": make_cam("CAM_rear34", (4.9, 5.7, 2.2), (0.0, 0.15, 0.65), lens=50.0),
    }
    files = {}
    p = os.path.join(RENDER_DIR, "side_cage.png")
    render(scene, cams["side"], (C.REF_W, C.REF_H), p, [cage.name] + wheels)
    files["side_cage"] = p
    for v in ("front", "rear", "front34", "rear34"):
        for what, vis in (("scaffold", [scaffold.name]), ("cage", [cage.name])):
            p = os.path.join(RENDER_DIR, f"view_{v}_{what}.png")
            render(scene, cams[v], TILE, p, vis)
            files[f"view_{v}_{what}"] = p
    for v in ("front34", "side"):
        p = os.path.join(RENDER_DIR, f"wire_{v}.png")
        res_v = WIRE_RES if v == "front34" else (C.REF_W, C.REF_H)
        render(scene, cams[v], res_v, p, [cage.name])
        files[f"wire_{v}"] = p
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
            render(scene, cams[v], GLOSS_RES, p, [cage.name])
            files[f"gloss_{mc.split('.')[0]}_{v}"] = p

    # control cage edge projection (mirrored control cage) with visibility against the limit surface
    surf_bvh = BVHTree.FromPolygons([tuple(c) for c in ev_co], [tuple(pp.vertices) for pp in ev_me.polygons])
    wire = {}
    for v, res_v in (("front34", WIRE_RES), ("side", (C.REF_W, C.REF_H))):
        wire[v] = {"res": list(res_v), "segments": wire_projection(scene, cams[v], res_v, ctrl_me, surf_bvh)}

    out = {
        "topology": topo, "fit_residual": fit_res, "distance_to_scaffold": dist,
        "side_silhouette": {"upper_contour": upper, "arch_edge": arch}, "dimensions": dims,
        "dihedral": dih, "gpt_axis": GPT_AXIS, "render_engine": eng, "matcaps": used, "renders": files,
        "cage_top_row_px": top_c.tolist(),
    }
    with open(os.path.join(C.OUT_DIR, "sc4-review.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(C.OUT_DIR, "sc4-wire.json"), "w", encoding="utf-8") as f:
        json.dump(wire, f)
    log(f"SC4 review done in {time.time() - t0:.1f} s")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
