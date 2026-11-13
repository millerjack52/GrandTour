"""Round-trip every FBX in the native plant manifest (docs/NATIVE_PLANT_KIT_PLAN.md) and write
validation-report.json (or validation-report-<set>.json with --set bush|open|floor|verge|farm|grass|patch). Only ok: true counts.
Per FBX: one render mesh, dimensions and triangles equal to the manifest, within budget, lowest vertex
5-7 cm below ground (or the row's own min_z_band for partly buried meshes), Color and UV present, slot count, origin at zero, UCX hull count and names as the
manifest says, GLB present; per asset: three LODs (two for the 'grass' set, GP1; three for the 'patch' set, GP4a) with strictly descending triangles; rows that declare
vertex_alpha must carry a vertex alpha spanning 0 at the base to 1 at the tip through the FBX round trip (the 'grass' and 'patch' sets must declare it).
Pattern: validate_shrub_library.py."""
import bpy, json, math, sys, traceback
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / 'Art/Export/NativePlants/v01'
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
SET = ARGS[ARGS.index('--set') + 1] if '--set' in ARGS else None
data = json.loads((OUT / 'manifest.json').read_text())
if SET:
    data['models'] = [r for r in data['models'] if r.get('set') == SET]
checks = []; failures = []
if SET and not data['models']:
    failures.append('set %s has no rows in the manifest' % SET)


def check(cond, row, what):
    if not cond:
        failures.append('%s: %s' % (row['name'], what))
    return cond


for row in data['models']:
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(OUT / (row['name'] + '.fbx')), use_custom_normals=True)
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        hulls = [o for o in meshes if o.name.startswith('UCX_')]
        render = [o for o in meshes if not o.name.startswith('UCX_')]
        check(len(render) == 1, row, 'expected one render mesh, got %s' % [o.name for o in render])
        ob = render[0]; mesh = ob.data; mesh.calc_loop_triangles()
        actual = list(ob.dimensions); expected = row['size_m']
        check(all(abs(a - b) < .001 for a, b in zip(sorted(actual), sorted(expected))), row, 'dimensions %s vs manifest %s' % (actual, expected))
        tris = len(mesh.loop_triangles)
        check(tris == row['triangles'], row, 'triangles %d vs manifest %d' % (tris, row['triangles']))
        check(tris <= row['budget'], row, 'triangles %d over budget %d' % (tris, row['budget']))
        has_colour = any(a.name == 'Color' for a in mesh.color_attributes)
        zmin = min((ob.matrix_world @ v.co).z for v in mesh.vertices)
        band = row.get('min_z_band', (-.075, -.045))     # partly buried meshes (cattle stop, culvert) declare their own band in the manifest
        check(band[0] <= zmin <= band[1], row, 'lowest vertex outside %s: min z %.3f m' % (band if 'min_z_band' in row else '5-7 cm below ground', zmin))
        check(has_colour, row, 'no Color attribute')
        alpha_span = None
        if row.get('set') in ('grass', 'patch'):     # GP1 / GP4a: the wind-weight alpha is part of these sets' contract
            check(bool(row.get('vertex_alpha')), row, 'row does not declare vertex_alpha')
        if row.get('vertex_alpha') and has_colour:   # GP1: the wind-weight alpha must survive the FBX round trip
            ca = next(a for a in mesh.color_attributes if a.name == 'Color'); n = len(ca.data)
            buf = [0.0] * (n * 4); ca.data.foreach_get('color', buf); al = buf[3::4]
            alpha_span = (round(min(al), 3), round(max(al), 3))
            check(alpha_span[0] < .01 and alpha_span[1] > .99, row, 'vertex alpha span %s, expected 0..1' % (alpha_span,))
        check(len(mesh.uv_layers) > 0, row, 'no UV layer')
        check(len(mesh.materials) == row['slots'], row, 'material slots %d vs manifest %d' % (len(mesh.materials), row['slots']))
        check(ob.location.length < 1e-4, row, 'origin not at zero: %s' % (tuple(ob.location),))
        check(all(math.isfinite(x) for v in mesh.vertices for x in v.co), row, 'non-finite coordinate')
        check(len(hulls) == row['hulls'], row, 'UCX hulls %d vs manifest %d' % (len(hulls), row['hulls']))
        check(all(h.name.startswith('UCX_' + row['name'] + '_') for h in hulls), row, 'hull names %s' % [h.name for h in hulls])
        glb = OUT / (row['name'] + '.glb')
        check(glb.exists() and glb.stat().st_size > 1000, row, 'GLB missing or too small')
        checks.append(dict(name=row['name'], triangles=tris, dimensions_m=[round(x, 4) for x in actual], vertex_colours=has_colour,
                           uv=len(mesh.uv_layers) > 0, slots=len(mesh.materials), hulls=len(hulls), ground_origin=ob.location.length < 1e-4,
                           glb_bytes=glb.stat().st_size if glb.exists() else 0, vertex_alpha_span=alpha_span))
    except Exception as e:
        failures.append('%s: exception %s' % (row['name'], e)); traceback.print_exc()

lods = {}
for asset in sorted({r['asset'] for r in data['models']}):
    rows = sorted([r for r in data['models'] if r['asset'] == asset], key=lambda r: r['lod'])
    counts = [r['triangles'] for r in rows]
    lods[asset] = counts
    want = 2 if rows[0].get('set') == 'grass' else 3    # GP1: the grass clumps have two LODs
    if not (len(rows) == want and all(counts[i] > counts[i + 1] for i in range(want - 1))):
        failures.append('%s: expected %d LODs with strictly descending triangles, got %s' % (asset, want, counts))

for asset in sorted({r['asset'] for r in data['models']}, key=lambda a: [r['asset'] for r in data['models']].index(a)):
    rows = sorted([r for r in data['models'] if r['asset'] == asset], key=lambda r: r['lod'])
    sz = rows[0]['size_m']
    print('SUMMARY %-22s LOD0/1/2 %6d /%5d /%5s tris   size %5.2f x %5.2f x %5.2f m   hulls %d   slots %d' % (
        asset, rows[0]['triangles'], rows[1]['triangles'], rows[2]['triangles'] if len(rows) > 2 else '-', sz[0], sz[1], sz[2], rows[0]['hulls'], rows[0]['slots']))

ok = not failures and len(checks) == len(data['models'])
(OUT / ('validation-report.json' if not SET else 'validation-report-%s.json' % SET)).write_text(json.dumps(dict(
    ok=ok, set=SET or 'all', fbx_roundtrips=checks, lod_triangles=lods, failures=failures, meshes=len(lods), files=len(checks)), indent=2))
for f in failures:
    print('VALIDATION_FAIL', f)
if not ok:
    sys.exit(1)
print('NATIVE_VALIDATION_OK', len(checks))
