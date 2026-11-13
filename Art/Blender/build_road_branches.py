"""Mud roads MRD1 item 3 (docs/MUD_ROADS_PLAN.md): two fallen branches for the mud roads' debris, headless Blender, on GR2's twig
recipe (Art/Blender/bake_ground_detail_gr2.py twig(): a tapering 5-sided tube that wanders a little in plan and hardly at all in
height, with side shoots). A branch is the same tube, 6-sided and longer (12 segments), with 2-4 side shoots of 25-45 % of its
length, some with a shoot of their own, all lying within +-5 % slope of the ground plane (the pieces lie flat). Sizes 60 and 105 cm
(AGTMudPatch::InitRoadDebris scales them into 40-120 cm). The origin is the plan's centre at the lowest point of the main stem, so
the piece sits on the ground and the patch sinks it RoadDebrisSinkMin-Max of its thickness.

Run headless (Blender 5.1):
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python Art/Blender/build_road_branches.py
Writes Art/Export/MudRoads/SM_MRD_Branch<n>.fbx and manifest.json (Art/Unreal/mud_roads.py imports them).
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Export/MudRoads'
OUT.mkdir(parents=True, exist_ok=True)
SIZES_CM = [60, 105]
SEED = 20261012


def branch_mesh(rng, name, length_cm):
    bm = bmesh.new()

    def tube(start, direction, L, r0, segs, sides):
        rings = []
        d = direction.normalized()
        pos = start.copy()
        for i in range(segs + 1):
            t = i / segs
            if i:
                d = (d + Vector((rng.normal(0, .18), rng.normal(0, .18), rng.normal(0, .05)))).normalized()
                d.z = max(-.05, min(.05, d.z))
                pos = pos + d * (L / segs)
            r = r0 * (1 - .7 * t)
            up = Vector((0, 0, 1))
            side = d.cross(up).normalized()
            up2 = side.cross(d).normalized()
            rings.append([bm.verts.new(pos + (side * math.cos(2 * math.pi * k / sides) + up2 * math.sin(2 * math.pi * k / sides)) * r) for k in range(sides)])
        for a, b in zip(rings, rings[1:]):
            for k in range(sides):
                bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
        # The far end capped (a broken stub).
        bm.faces.new(list(reversed(rings[-1])))
        return rings

    L = length_cm / 100
    r0 = rng.uniform(.006, .009) * (L / .3) ** .5
    main = tube(Vector((0, 0, r0)), Vector((1, 0, 0)), L, r0, 12, 6)
    bm.faces.new(main[0])   # the butt capped
    shoots = int(rng.integers(2, 5))
    for s in range(shoots):
        ring = main[int(len(main) * rng.uniform(.2, .75))]
        c = sum((v.co for v in ring), Vector()) / len(ring)
        side = rng.choice([-1, 1])
        d = Vector((rng.uniform(.3, .9), side * rng.uniform(.4, 1.0), 0))
        lr = r0 * rng.uniform(.4, .6)
        sub = tube(c, d, L * rng.uniform(.25, .45), lr, 5, 5)
        if rng.random() < .5:
            ring2 = sub[int(len(sub) * rng.uniform(.3, .7))]
            c2 = sum((v.co for v in ring2), Vector()) / len(ring2)
            tube(c2, Vector((rng.uniform(.4, .9), -side * rng.uniform(.3, .8), 0)), L * rng.uniform(.1, .2), lr * .55, 3, 4)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    # The plan's centre to the origin, the lowest point on the ground.
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    zs = [v.co.z for v in me.vertices]
    off = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, min(zs)))
    for v in me.vertices:
        v.co -= off
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.02)
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as e:   # noqa: BLE001
        print('smart project failed on %s: %s' % (name, e))
        bpy.ops.object.mode_set(mode='OBJECT')
    return ob


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = np.random.default_rng(SEED)
    mat = bpy.data.materials.new('M_GD_Twig')   # Unreal puts MI_GD_Twig on them (Art/Unreal/mud_roads.py)
    rows = []
    for i, size in enumerate(SIZES_CM):
        ob = branch_mesh(rng, 'SM_MRD_Branch%d' % i, size)
        ob.data.materials.append(mat)
        for o in bpy.context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        path = OUT / (ob.name + '.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, apply_unit_scale=True, bake_space_transform=False, mesh_smooth_type='FACE')
        d = ob.dimensions
        rows.append(dict(name=ob.name, length_cm=size, size_m=[round(d.x, 4), round(d.y, 4), round(d.z, 4)],
                         triangles=sum(len(p.vertices) - 2 for p in ob.data.polygons), fbx=str(path.relative_to(ROOT).as_posix())))
        print('ROAD_BRANCH', json.dumps(rows[-1]), flush=True)
    (OUT / 'manifest.json').write_text(json.dumps(dict(recipe='GR2 twig() as a 6-sided 12-segment tube with 2-4 shoots (build_road_branches.py)', seed=SEED, branches=rows), indent=2))


main()
