"""LM4b item 3 (docs/LIVING_MUD_PLAN.md LM4b; LM4 item 4 before it): eight rounded, lumpy snow clumps, exported as FBX for
Art/Unreal/import_snow_chunks.py (the same names, so the import and AGTMudPatch's shards pick them up unchanged).

Run headless, no add-ons:
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python Art/Blender/build_snow_chunks.py

LM4's were Voronoi shards of a 4-8 cm slab, flat shaded (the owner's screenshot read them as ice cubes). LM4b's are snow
clumps, built with bmesh (no add-ons) from a smoothed fracture piece:
- an icosphere (three subdivisions, 320 triangles) scaled to the clump's own ellipsoid: across 5-18 cm, its width 0.70-0.90
  of that, its height 0.50-0.72;
- the fracture: two to four planes cut into it at random, each pulling what stands past it most of the way back onto it
  (a break face), so the piece is irregular, not an egg;
- the bevel: every vertex pulled toward its neighbours' mean (Laplacian smoothing), so the break faces' edges round over;
- the lumps: the vertices pushed along their normals by three octaves of noise (about 15, 7 and 3 % of the size), then one
  more light smoothing pass, so the surface is clumpy but soft;
- the bottom squashed flat over its lowest 12 % (AGTMudPatch sinks a clump by its height, read from its bounds), the pivot
  at the middle of the flat bottom, the whole scaled back to the across asked (the cuts and the rounding shrink it); smooth
  shaded.
Written to Art/Export/SnowChunks/SM_GT_SnowChunk_<n>.fbx the way build_mud_clods.py writes the clods (metres in Blender, the
FBX in centimetres, -Z forward, Y up), with manifest.json (across, thickness, triangles) and SnowChunks.blend beside them.
"""
import bpy
import bmesh
import json
import math
import random
from pathlib import Path
from mathutils import Vector, noise

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art' / 'Export' / 'SnowChunks'
OUT.mkdir(parents=True, exist_ok=True)
FBX = dict(axis_forward='-Z', axis_up='Y', global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
           bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=False,
           add_leaf_bones=False, bake_anim=False, path_mode='AUTO', embed_textures=False, use_custom_props=False,
           use_selection=True, object_types={'MESH'})
# (across cm, width share, height share, fracture planes): the eight, spread over 5-18 cm.
CLUMPS = [
    dict(across=5.0, width=0.86, height=0.68, cuts=2),
    dict(across=6.5, width=0.78, height=0.62, cuts=3),
    dict(across=8.0, width=0.90, height=0.72, cuts=2),
    dict(across=9.5, width=0.74, height=0.55, cuts=4),
    dict(across=11.5, width=0.84, height=0.60, cuts=3),
    dict(across=13.5, width=0.70, height=0.52, cuts=4),
    dict(across=15.5, width=0.82, height=0.58, cuts=3),
    dict(across=18.0, width=0.76, height=0.50, cuts=4),
]


def say(*a):
    print('SNOW_CHUNKS', *a, flush=True)


def smooth(bm, factor, passes):
    for _ in range(passes):
        bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=factor, use_axis_x=True, use_axis_y=True, use_axis_z=True)


def build(index, spec, rng):
    across = spec['across'] / 100.0
    rx = 0.5 * across
    ry = 0.5 * across * spec['width']
    rz = 0.5 * across * spec['height']
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    yaw = rng.uniform(0.0, 2.0 * math.pi)
    cy, sy = math.cos(yaw), math.sin(yaw)
    for v in bm.verts:
        x, y, z = v.co.x * rx, v.co.y * ry, v.co.z * rz
        v.co = Vector((x * cy - y * sy, x * sy + y * cy, z))
    # The fracture: each plane, at 0.45-0.75 of the way out along a random direction (mostly sideways and up), pulls what
    # stands past it 80 % of the way back onto it.
    for _ in range(spec['cuts']):
        ang = rng.uniform(0.0, 2.0 * math.pi)
        tilt = rng.uniform(-0.35, 0.9)
        d = Vector((math.cos(ang), math.sin(ang), tilt)).normalized()
        reach = max(abs(v.co.dot(d)) for v in bm.verts)
        plane = reach * rng.uniform(0.45, 0.75)
        for v in bm.verts:
            over = v.co.dot(d) - plane
            if over > 0.0:
                v.co -= d * (0.8 * over)
    # The bevel: the break faces' edges round over.
    smooth(bm, 0.5, 4)
    bm.normal_update()
    # The lumps: two octaves of noise along the normals, then a light smoothing.
    seed = Vector((13.1 * (index + 1), -7.7 * (index + 3), 4.3 * (index + 5)))
    size = across
    for v in bm.verts:
        p = v.co * (1.0 / size)
        dn = 0.15 * size * noise.noise(p * 3.0 + seed) + 0.07 * size * noise.noise(p * 6.5 + seed * 1.9) + 0.03 * size * noise.noise(p * 13.0 + seed * 2.7)
        v.co += v.normal * dn
    smooth(bm, 0.3, 1)
    # The bottom: the lowest 12 % of the height squashed flat (a clump sits in the snow), then the pivot at its middle.
    zs = [v.co.z for v in bm.verts]
    z0, z1 = min(zs), max(zs)
    base = z0 + 0.12 * (z1 - z0)
    for v in bm.verts:
        if v.co.z < base:
            v.co.z = base - 0.15 * (base - v.co.z)
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    cx, cyy, zmin = 0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys)), min(zs)
    # The cuts and the rounding shrink it: scaled back up, its proportions kept, so its across is the one asked.
    grow = across / max(max(xs) - min(xs), max(ys) - min(ys), 1e-6)
    for v in bm.verts:
        v.co = Vector(((v.co.x - cx) * grow, (v.co.y - cyy) * grow, (v.co.z - zmin) * grow))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new('SM_GT_SnowChunk_%d' % index)
    bm.to_mesh(me)
    bm.free()
    # A UV set (M_GT_Clod_Snow is tri-planar in world space; Unreal still wants one): top-down.
    uv = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (co.x / across + 0.5, co.y / across + 0.5)
    ob = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.get('M_GT_Clod_Snow') or bpy.data.materials.new('M_GT_Clod_Snow')
    me.materials.append(mat)
    return ob


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    rng = random.Random(0x5A0C4B)
    rows = []
    for index, spec in enumerate(CLUMPS):
        ob = build(index, spec, rng)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.context.view_layer.update()
        path = OUT / (ob.name + '.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path), **FBX)
        me = ob.data
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        dims = [round(d * 100.0, 2) for d in ob.dimensions]
        across = max(dims[0], dims[1])
        rows.append(dict(name=ob.name, fbx=str(path.relative_to(ROOT)).replace('\\', '/'), triangles=tris, vertices=len(me.vertices), size_cm=dims,
                         across_cm=across, thickness_cm=dims[2], asked_across_cm=spec['across'], asked_height_share=spec['height']))
        say(ob.name, 'triangles', tris, 'size cm', dims, '->', path.name)
        assert 150 <= tris <= 700, (ob.name, tris)
        assert 4.0 <= across <= 20.0, (ob.name, across)
    for k, row in enumerate(rows):
        bpy.data.objects[row['name']].location = (0.25 * (k % 4), 0.25 * (k // 4), 0.0)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'SnowChunks.blend'))
    manifest = dict(blender=bpy.app.version_string, units='Blender metres; FBX centimetres (apply_unit_scale), -Z forward, Y up',
                    how='LM4b: an icosphere ellipsoid, 2-4 fracture planes pulled in, Laplacian rounding, three octaves of normal noise, a flat bottom, smooth shaded',
                    pivot='the middle of the flat bottom (z = 0)', chunks=rows)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    say('OK', len(rows), 'clumps ->', OUT)


main()
