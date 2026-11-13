"""Round-trip exported trial FBXs in a fresh background Blender process."""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy

manifest = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
data = json.loads(manifest.read_text())
checks = []
for row in data['models']:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.scale_length = 1
    path = Path(row['fbx'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == row['fbx_sha256']
    bpy.ops.import_scene.fbx(filepath=str(path))
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert len(objects) == 1
    obj = objects[0]
    mesh = obj.data
    mesh.calc_loop_triangles()
    assert len(mesh.loop_triangles) == row['triangles']
    assert mesh.color_attributes and mesh.uv_layers
    points = [obj.matrix_world @ v.co for v in mesh.vertices]
    bounds = [[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)]
    max_error = max(abs(a - b) for actual, expected in zip(bounds, row['bounds_m'])
                    for a, b in zip(actual, expected))
    assert max_error < 1e-4, (row['variant'], bounds, row['bounds_m'])
    assert all(math.isfinite(c) for p in points for c in p)
    checks.append({'variant': row['variant'], 'triangles': len(mesh.loop_triangles),
                   'bounds_error_m': max_error, 'colours_and_uvs_present': True})
assert hashlib.sha256(Path(data['source']).read_bytes()).hexdigest() == data['source_sha256']
(manifest.parent / 'roundtrip-verification.json').write_text(json.dumps({
    'ok': True, 'checks': checks, 'source_unchanged': True,
    'unreal_validation_pending': True}, indent=2))
print('FAR_TUSSOCK_ROUNDTRIP_OK')
