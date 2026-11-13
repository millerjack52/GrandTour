"""Export isolated fourth-LOD candidates; never rewrite the approved library.

blender --background --python this_file.py -- --out <fresh directory>
Writes four FBXs, a geometry review blend/PNG and a manifest. No Unreal launch.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--out', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = Path(args.out).resolve()
out.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[2]
source_file = root / 'Art/Export/TussockStyleStudy/07/TussockStyleStudy.blend'
source_hash = hashlib.sha256(source_file.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source_file))
scene = bpy.context.scene
keep = []
models = []


def make_blades(src, per_blade, starts, pairs, width, name):
    vc = {loop.vertex_index: tuple(src.color_attributes['Color'].data[loop.index].color)
          for loop in src.loops}
    verts, faces, colours = [], [], []
    for first in starts:
        offset = len(verts)
        for pair_index in pairs:
            pair = first + pair_index * 2
            mid = (src.vertices[pair].co + src.vertices[pair + 1].co) * .5
            for side in (0, 1):
                verts.append(tuple(mid + (src.vertices[pair + side].co - mid) * width))
                colours.append(vc[pair + side])
        for j in range(len(pairs) - 1):
            a = offset + j * 2
            faces.extend([(a, a + 3, a + 1), (a, a + 2, a + 3)])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    colour = mesh.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    uv = mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        for li in polygon.loop_indices:
            vi = mesh.loops[li].vertex_index
            colour.data[li].color = colours[vi]
            uv.data[li].uv = mesh.vertices[vi].co.xy
    mesh.normals_split_custom_set_from_vertices(
        [Vector((v[0] * .48, v[1] * .48, .8)).normalized() for v in verts])
    mesh.materials.append(src.materials[0])
    mesh.calc_loop_triangles()
    assert all(math.isfinite(v) for xyz in verts for v in xyz)
    assert all(tri.area > 1e-12 for tri in mesh.loop_triangles), 'Degenerate blade triangle'
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    keep.append(obj)
    return obj


for kind, (label, source_name) in enumerate(zip(
        ['Straw', 'Rust', 'Weathered', 'Fine'],
        ['Arching', 'Wind-combed', 'Upright', 'Fine undergrass'])):
    src = bpy.data.objects[source_name].data
    per_blade = 16 if kind < 3 else 10
    assert len(src.vertices) % per_blade == 0
    starts = list(range(0, len(src.vertices), per_blade * 8))
    baseline = make_blades(src, per_blade, starts, range(per_blade // 2), 2.15, label + '_LOD2_review')
    # Deterministic subset of complete blades from the existing far LOD.
    # Fewer longitudinal segments and wider blades retain distant colour coverage.
    count = 8 if kind < 3 else 4
    chosen = [starts[(i * len(starts)) // count] for i in range(count)]
    pairs = [0, 2, 5, 7] if kind < 3 else [0, 1, 3, 4]
    width = 2.15 * len(starts) / count
    candidate = make_blades(src, per_blade, chosen, pairs, width, 'SM_TS_' + label + '_LOD3')
    expected = 48 if kind < 3 else 24
    assert len(candidate.data.loop_triangles) == expected
    assert len(baseline.data.loop_triangles) == (336 if kind < 3 else 80)
    bounds = [[min(v.co[i] for v in candidate.data.vertices),
               max(v.co[i] for v in candidate.data.vertices)] for i in range(3)]
    bpy.ops.object.select_all(action='DESELECT')
    candidate.select_set(True)
    bpy.context.view_layer.objects.active = candidate
    # Match the approved library's FBX centimetre export convention.
    for v in candidate.data.vertices:
        v.co *= 100
    scene.unit_settings.scale_length = .01
    fbx = out / (candidate.name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
        axis_forward='-Z', axis_up='Y', global_scale=1, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE', mesh_smooth_type='FACE',
        colors_type='LINEAR', bake_anim=False)
    for v in candidate.data.vertices:
        v.co /= 100
    scene.unit_settings.scale_length = 1
    models.append({'variant': label, 'fbx': str(fbx), 'lod': 3,
        'triangles': expected, 'source_lod2_triangles': len(baseline.data.loop_triangles),
        'blade_width_scale': width,
        'surface_area_ratio_to_lod2': sum(t.area for t in candidate.data.loop_triangles) /
            sum(t.area for t in baseline.data.loop_triangles),
        'bounds_m': bounds, 'fbx_sha256': hashlib.sha256(fbx.read_bytes()).hexdigest()})
    baseline.location = (kind * 3.1 - 4.65, 1.5, 0)
    candidate.location = (kind * 3.1 - 4.65, -1.5, 0)

for obj in list(scene.objects):
    if obj not in keep:
        bpy.data.objects.remove(obj, do_unlink=True)

# CPU-only geometry review, not an Unreal appearance or motion acceptance test.
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 12
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.render.resolution_x = 1200
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new('GeometryReviewWorld')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.22, .24, .27, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .7
bpy.ops.object.camera_add(location=(0, -10, 12))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 14
scene.camera = camera
bpy.ops.object.light_add(type='AREA', location=(0, -2, 7))
bpy.context.object.data.energy = 1500
bpy.context.object.data.shape = 'DISK'
bpy.context.object.data.size = 9
for obj in keep:
    bpy.ops.object.text_add(location=obj.location + Vector((0, -.9, 0)))
    text = bpy.context.object
    text.data.body = obj.name.replace('_review', '').replace('SM_TS_', '') + ' / ' + str(len(obj.data.loop_triangles)) + ' tris'
    text.data.align_x = 'CENTER'
    text.data.size = .16
    text.rotation_euler = camera.rotation_euler
scene.render.filepath = str(out / 'geometry-review.png')
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'far-tussock-review.blend'))
bpy.ops.render.render(write_still=True)
assert hashlib.sha256(source_file.read_bytes()).hexdigest() == source_hash
(out / 'manifest.json').write_text(json.dumps({
    'source': str(source_file), 'source_sha256': source_hash, 'models': models,
    'installed_in_unreal': False, 'runtime_performance_measured': False,
    'review_limit': 'Geometry only. Silhouette, coverage, popping and shimmer require Unreal moving-camera review.'}, indent=2))
print('FAR_TUSSOCK_EXPORT_OK ' + str(out))
