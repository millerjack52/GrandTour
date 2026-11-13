"""LM2b + LM2c (docs/LIVING_MUD_PLAN.md): ten procedural mud clods in four families, exported as FBX for
Art/Unreal/import_mud_clods.py.

Run headless, no add-ons:
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python Art/Blender/build_mud_clods.py

LM2c (the owner, 2026-10-05: "They are very uniform"): LM2b's five clods were all one recipe. Now ten, by number (the
patch maps the number to the family, AGTMudPatch::InitClods):
  0-1 rounded blobs        LM2b's recipe with stronger noise, 0.55-0.62 of across tall;
  2-4 pancakes and slabs   0.25-0.35 of across tall, an irregular outline (4 has a broken side);
  5-7 broken chunks        one or two planar cuts with flat faces and hard edges;
  8-9 elongated smears     aspect 1.8-2.5, thinning toward one end.
Each one: an icosphere displaced by noise (a seed per clod), shaped by its family, cut flat at the bottom and capped, then
scaled to 10 cm across (its longest horizontal side) and its family's height, its pivot at the middle of the flat face
(AGTMudPatch reads the height from the mesh's bounds and sinks a clod by it). Smooth shaded, cut faces flat;
triangulated, 150-400 triangles. Written to Art/Export/MudClods/SM_GT_Clod_<n>.fbx the way the other Art/Blender export
scripts write theirs (metres in Blender, the FBX in centimetres, -Z forward, Y up), with manifest.json (family,
triangles, size) and MudClods.blend beside them.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector, noise

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art' / 'Export' / 'MudClods'
OUT.mkdir(parents=True, exist_ok=True)
WIDTH_M = 0.10        # across at scale 1 (the longest horizontal side)
FBX = dict(axis_forward='-Z', axis_up='Y', global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
           bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=False,
           add_leaf_bones=False, bake_anim=False, path_mode='AUTO', embed_textures=False, use_custom_props=False,
           use_selection=True, object_types={'MESH'})
FAMILIES = ['blob', 'pancake', 'chunk', 'smear']
# (family, height as a share of across, cut height as a share of the sphere's radius, extra numbers)
CLODS = [
    dict(family='blob', height=0.62, cut=-0.55),
    dict(family='blob', height=0.55, cut=-0.45),
    dict(family='pancake', height=0.25, cut=-0.30),
    dict(family='pancake', height=0.30, cut=-0.25),
    dict(family='pancake', height=0.35, cut=-0.30, side_cut=((0.85, 0.30, 0.0), 0.55)),   # a slab with a broken side
    dict(family='chunk', height=0.62, cut=-0.50, cuts=[((0.55, -0.35, 0.75), 0.42)]),
    dict(family='chunk', height=0.70, cut=-0.45, cuts=[((-0.80, 0.25, 0.35), 0.50), ((0.30, 0.85, 0.45), 0.55)]),
    dict(family='chunk', height=0.55, cut=-0.55, cuts=[((0.20, 0.10, 1.00), 0.35), ((-0.65, -0.70, 0.10), 0.52)]),
    dict(family='smear', height=0.24, cut=-0.30, aspect=1.9),
    dict(family='smear', height=0.28, cut=-0.25, aspect=2.25),
]


def say(*a):
    print('MUD_CLODS', *a, flush=True)


def cut_and_cap(bm, co, no, caps):
    """Everything on the far side of the plane (along no) goes; the hole is closed with one flat face."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
    boundary = [e for e in bm.edges if e.is_boundary]
    if boundary:
        filled = bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
        caps.update(filled['faces'])


def build(index, spec):
    bm = bmesh.new()
    # bmesh's subdivision count differs from the operator's between versions: the one whose sphere has 240-400 faces.
    for sub in (2, 3, 4):
        bm.clear()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        faces = len(bm.faces)
        if faces >= 240:
            break
    assert 240 <= faces <= 400, faces
    family = spec['family']
    seed = Vector((17.3 * (index + 1), -5.1 * (index + 2), 3.7 * (index + 3)))
    aspect = spec.get('aspect', 1.0)
    for v in bm.verts:
        n = v.co.normalized()
        if family == 'blob':
            # LM2b's two octaves, stronger: a lumpy body and crumbs on it.
            r = 1.0 + 0.32 * noise.noise(n * 1.6 + seed) + 0.12 * noise.noise(n * 4.3 + seed * 1.7)
            v.co = n * r
        elif family == 'pancake':
            # An irregular outline (the noise on the direction round Z), a gently lumpy top.
            flat = Vector((n.x, n.y, 0.0))
            ring = 1.0 + 0.30 * noise.noise(flat * 1.4 + seed) + 0.10 * noise.noise(n * 3.8 + seed * 1.3)
            v.co = Vector((n.x * ring, n.y * ring, n.z * (1.0 + 0.25 * noise.noise(n * 2.7 + seed * 0.7))))
        elif family == 'chunk':
            r = 1.0 + 0.22 * noise.noise(n * 1.8 + seed) + 0.08 * noise.noise(n * 5.1 + seed * 1.9)
            v.co = n * r
        else:   # smear: long in X, thinning toward +X (the way it was dragged)
            r = 1.0 + 0.18 * noise.noise(n * 1.7 + seed) + 0.07 * noise.noise(n * 4.6 + seed * 1.5)
            p = n * r
            t = 0.5 * (n.x + 1.0)
            v.co = Vector((p.x * aspect, p.y, p.z * (1.15 - 0.55 * t)))
    bm.normal_update()
    caps = set()
    # The family's planar cuts (chunks; the slab's broken side), each closed with a flat face, one after the other.
    for no, d in spec.get('cuts', []):
        nv = Vector(no).normalized()
        cut_and_cap(bm, tuple(nv * d), tuple(nv), caps)
    if 'side_cut' in spec:
        no, d = spec['side_cut']
        nv = Vector(no).normalized()
        cut_and_cap(bm, tuple(nv * d), tuple(nv), caps)
    # The bottom cut flat, its face down.
    cut_and_cap(bm, (0.0, 0.0, spec['cut']), (0.0, 0.0, -1.0), caps)
    caps = {f for f in caps if f.is_valid}
    for f in bm.faces:
        f.smooth = f not in caps
    for f in caps:
        for e in f.edges:
            e.smooth = False
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    # Scale to WIDTH_M across (the longest horizontal side) and the family's height, the flat face at z = 0, centred in XY.
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    cx, cy = 0.5 * (min(xs) + max(xs)), 0.5 * (min(ys) + max(ys))
    across = max(max(xs) - min(xs), max(ys) - min(ys))
    tall = max(zs) - min(zs)
    sxy = WIDTH_M / across
    sz = spec['height'] * WIDTH_M / tall
    z0 = min(zs)
    for v in bm.verts:
        v.co = Vector(((v.co.x - cx) * sxy, (v.co.y - cy) * sxy, (v.co.z - z0) * sz))
    bm.normal_update()
    me = bpy.data.meshes.new('SM_GT_Clod_%d' % index)
    bm.to_mesh(me)
    bm.free()
    # A UV set (the material is tri-planar in world space; Unreal still wants one): around Z, up the height.
    uv = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (math.atan2(co.y, co.x) / (2 * math.pi) + 0.5, co.z / (spec['height'] * WIDTH_M))
    ob = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.get('M_GT_Clod') or bpy.data.materials.new('M_GT_Clod')
    me.materials.append(mat)
    return ob


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    rows = []
    for index, spec in enumerate(CLODS):
        ob = build(index, spec)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        path = OUT / (ob.name + '.fbx')
        bpy.context.view_layer.update()
        bpy.ops.export_scene.fbx(filepath=str(path), **FBX)
        me = ob.data
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        dims = [round(d * 100.0, 2) for d in ob.dimensions]
        rows.append(dict(name=ob.name, family=spec['family'], family_index=FAMILIES.index(spec['family']), height_ratio=spec['height'],
                         fbx=str(path.relative_to(ROOT)).replace('\\', '/'), triangles=tris, vertices=len(me.vertices), size_cm=dims))
        say(ob.name, spec['family'], 'triangles', tris, 'size cm', dims, '->', path)
        assert 150 <= tris <= 400, (ob.name, tris)
    # Side by side in the .blend, for a look.
    for k, row in enumerate(rows):
        bpy.data.objects[row['name']].location = (0.15 * (k % 5), 0.15 * (k // 5), 0.0)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'MudClods.blend'))
    manifest = dict(blender=bpy.app.version_string, units='Blender metres; FBX centimetres (apply_unit_scale), -Z forward, Y up',
                    width_cm=WIDTH_M * 100.0, families='0-1 blob, 2-4 pancake/slab, 5-7 chunk, 8-9 smear (AGTMudPatch maps the number)',
                    pivot='the middle of the flat face (z = 0)', clods=rows)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    say('OK', len(rows), 'clods ->', OUT)


main()
