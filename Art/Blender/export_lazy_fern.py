"""Inspect/export the owned Lazy Forest Fern_02 without rendering or saving source.

Run with Blender --background --factory-startup --disable-autoexec --python this.py.
Licensed output stays local on D:, never in the source repository.
"""
import hashlib
import json
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path('D:/GrandTourAssets/FlippedNormals/Lazy_Forest_Gen_Addon')
OUT = Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/LazyFern')
NAME = 'Fern_02'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def nodes(tree, seen=None):
    seen = set() if seen is None else seen
    if not tree or tree.as_pointer() in seen:
        return []
    seen.add(tree.as_pointer())
    result = []
    for n in tree.nodes:
        row = {'name': n.name, 'type': n.bl_idname}
        row['inputs'] = []
        for i, socket in enumerate(n.inputs):
            if not hasattr(socket, 'default_value'):
                continue
            value = socket.default_value
            if not isinstance(value, (int, float, str, bool)):
                try:
                    value = list(value)
                except TypeError:
                    continue
            row['inputs'].append({'index': i, 'name': socket.name, 'value': value})
        for key in ('blend_type', 'data_type', 'operation', 'vector_type'):
            if hasattr(n, key):
                row[key] = getattr(n, key)
        if n.type == 'CURVE_RGB':
            row['curves'] = [[list(p.location) for p in c.points] for c in n.mapping.curves]
        if n.type == 'TEX_IMAGE' and n.image:
            im = n.image
            row['image'] = {'name': im.name, 'filepath': bpy.path.abspath(im.filepath, library=im.library),
                            'size': list(im.size), 'colorspace': im.colorspace_settings.name,
                            'packed': bool(im.packed_file)}
        if n.type == 'GROUP':
            row['group'] = nodes(n.node_tree, seen)
        result.append(row)
    return {'nodes': result, 'links': [[l.from_node.name, l.from_socket.name, l.to_node.name, l.to_socket.name] for l in tree.links]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sources = [ROOT/'Assets/Assets.blend', ROOT/'Data.blend']
    inventory = {}
    source = None
    for p in sources:
        with bpy.data.libraries.load(str(p), link=False) as (src, dst):
            inventory[str(p)] = [n for n in src.objects if 'fern' in n.lower()]
            if source is None and NAME in src.objects:
                dst.objects = [NAME]
                source = p
        if source:
            break
    assert source, inventory
    obj = bpy.data.objects.get(NAME)
    assert obj and obj.type == 'MESH', (NAME, obj)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.context.view_layer.update()
    obj.data.calc_loop_triangles()
    report = {'asset': NAME, 'source': str(source), 'source_sha256': sha(source),
              'blender': bpy.app.version_string, 'inventory': inventory,
              'vertices': len(obj.data.vertices), 'triangles': len(obj.data.loop_triangles),
              'dimensions_m': list(obj.dimensions), 'scale': list(obj.scale),
              'location': list(obj.location), 'rotation_euler': list(obj.rotation_euler),
              'uv_layers': [uv.name for uv in obj.data.uv_layers],
              'modifiers': [{'name': m.name, 'type': m.type} for m in obj.modifiers],
              'materials': [{'name': m.name, 'nodes': nodes(m.node_tree)} for m in obj.data.materials if m],
              'bounds_local': [[min(v.co[i] for v in obj.data.vertices), max(v.co[i] for v in obj.data.vertices)] for i in range(3)],
              'uv_bounds': [[min(d.uv[i] for d in obj.data.uv_layers[0].data), max(d.uv[i] for d in obj.data.uv_layers[0].data)] for i in range(2)],
              'rendered': False, 'unreal_tested': False}
    (OUT/'source-audit.json').write_text(json.dumps(report, indent=2))
    assert not obj.modifiers, 'Review source modifiers before exporting'
    # Preserve the complete authored material for later transfer/baking. FBX
    # alone does not reproduce Blender's curves, tint, bump and translucency.
    obj.location = (0, 0, 0)
    bounds = report['bounds_local']
    offset = Vector(((bounds[0][0]+bounds[0][1])/2, (bounds[1][0]+bounds[1][1])/2, bounds[2][0]))
    for vertex in obj.data.vertices:
        vertex.co -= offset
    report['root_offset_m'] = list(offset)
    for im in bpy.data.images:
        if im.source == 'FILE':
            im.filepath = bpy.path.abspath(im.filepath, library=im.library)
            assert Path(im.filepath).is_file(), im.filepath
    bpy.data.libraries.write(str(OUT/'Fern02-source.blend'), {obj}, path_remap='ABSOLUTE')
    bpy.ops.export_scene.fbx(filepath=str(OUT/'SM_LazyFern02.fbx'), use_selection=True,
                             object_types={'MESH'}, axis_forward='-Z', axis_up='Y',
                             apply_unit_scale=True, bake_anim=False, add_leaf_bones=False,
                             path_mode='ABSOLUTE', mesh_smooth_type='FACE')
    assert sha(source) == report['source_sha256']
    report['fbx_sha256'] = sha(OUT/'SM_LazyFern02.fbx')
    for existing in list(bpy.data.objects):
        bpy.data.objects.remove(existing, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=str(OUT/'SM_LazyFern02.fbx'), use_anim=False)
    imported = next(o for o in bpy.context.selected_objects if o.type == 'MESH')
    imported.data.calc_loop_triangles()
    bpy.context.view_layer.update()
    report['roundtrip'] = {'vertices': len(imported.data.vertices),
                           'triangles': len(imported.data.loop_triangles),
                           'dimensions_m': list(imported.dimensions),
                           'uv_layers': [uv.name for uv in imported.data.uv_layers]}
    assert report['roundtrip']['triangles'] == report['triangles']
    assert report['roundtrip']['vertices'] == report['vertices']
    assert report['roundtrip']['uv_layers'] == report['uv_layers']
    assert all(abs(a-b) < 1e-5 for a, b in zip(imported.dimensions, report['dimensions_m']))
    report['roundtrip']['passed'] = True
    (OUT/'source-audit.json').write_text(json.dumps(report, indent=2))
    print('LAZY_FERN_EXPORT', json.dumps({k: report[k] for k in ('asset', 'vertices', 'triangles', 'dimensions_m')}), flush=True)


if __name__ == '__main__':
    main()
