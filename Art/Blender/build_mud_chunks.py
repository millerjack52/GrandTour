"""MudRunner MR5 (docs/MUDRUNNER_LESSONS_PLAN.md MR5 execution block item 1): six breakable mud chunks, the firm crust,
exported as FBX for Art/Unreal/import_mud_chunks.py.

Run headless, no add-ons:
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 --python Art/Blender/build_mud_chunks.py

build_mud_clods.py's recipe and export conventions, larger and rougher. Six chunks by number (AGTMudPatch maps the number to
the family):
  0-1 rounded   lumpy bodies, 0.48-0.55 of across tall;
  2-3 slab      0.30-0.34 of across tall, an irregular outline (3 has a broken side);
  4   broken    two planar cuts with flat faces and hard edges;
  5   smear     aspect 2.1, thinning toward one end.
Each one: a cube-sphere (the finest whose finished chunk stays within the triangle range) displaced by three octaves of noise (stronger than the clods'), a few crack grooves (a wavy plane
through the body, the surface pushed in along it, tapered at its ends), shaped by its family, cut flat at the bottom and
capped, then scaled to 30 cm across (its longest horizontal side) and its family's height. Smooth shaded, cut faces flat;
triangulated, 600-1,000 triangles.

The embed line is 18 % of the height up from the bottom. One convex collision hull (UCX_<name>_00, at most 64 vertices: the
hull of the mesh above the line, its extreme points thinned by farthest-point sampling) covers the mesh above it; its bottom
face lies on the line. The pivot is the hull's bottom centre (the area centroid of that face), so a chunk resting on the
ground has its lowest 18 % under it (render only; the physics is the hull's).

Written to Art/Export/MudChunks/SM_GT_MudChunk_<n>.fbx (the render mesh and its UCX_ hull in one file) the way the other
Art/Blender export scripts write theirs (metres in Blender, the FBX in centimetres, -Z forward, Y up), with manifest.json
(family, triangles, size, the closed-mesh volume, the hull's volume, the volume above the line and the embed height, cm and
cm^3 at 30 cm across) and MudChunks.blend beside them.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector, noise

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art' / 'Export' / 'MudChunks'
OUT.mkdir(parents=True, exist_ok=True)
WIDTH_M = 0.30        # across at scale 1 (the longest horizontal side)
EMBED = 0.18          # the embed line, a share of the height up from the bottom
HULL_MAX_VERTS = 64
HULL_RING_VERTS = 16  # of them at most on the bottom face
TRIS = (600, 1000)
FBX = dict(axis_forward='-Z', axis_up='Y', global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
           bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=False,
           add_leaf_bones=False, bake_anim=False, path_mode='AUTO', embed_textures=False, use_custom_props=False,
           use_selection=True, object_types={'MESH'})
FAMILIES = ['rounded', 'slab', 'broken', 'smear']
# (family, height as a share of across, bottom cut as a share of the sphere's radius, crack grooves, extra numbers)
CHUNKS = [
    dict(family='rounded', height=0.55, cut=-0.48, cracks=3),
    dict(family='rounded', height=0.48, cut=-0.40, cracks=4),
    dict(family='slab', height=0.30, cut=-0.30, cracks=4),
    dict(family='slab', height=0.34, cut=-0.28, cracks=3, side_cut=((0.85, 0.30, 0.0), 0.52)),   # a slab with a broken side
    dict(family='broken', height=0.58, cut=-0.45, cracks=3, cuts=[((0.55, -0.35, 0.75), 0.40), ((-0.70, 0.62, 0.22), 0.50)]),
    dict(family='smear', height=0.26, cut=-0.28, cracks=2, aspect=2.1),
]


def say(*a):
    print('MUD_CHUNKS', *a, flush=True)


def cut_and_cap(bm, co, no, caps):
    """Everything on the far side of the plane (along no) goes; the hole is closed with one flat face."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
    boundary = [e for e in bm.edges if e.is_boundary]
    if boundary:
        filled = bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
        caps.update(filled['faces'])


def hashed(k, salt):
    """A repeatable number in 0..1 from two integers (no global random state)."""
    x = math.sin(12.9898 * (k + 1) + 78.233 * (salt + 1)) * 43758.5453
    return x - math.floor(x)


def cracks_for(index, spec):
    """The crack grooves: a centre direction, the plane's normal (the centre lies in the plane), its reach (cos), width, depth."""
    out = []
    for k in range(spec['cracks']):
        a = 2.0 * math.pi * hashed(index * 7 + k, 1)
        up = 0.25 + 0.7 * hashed(index * 7 + k, 2) if spec['family'] in ('slab', 'smear') else -0.3 + 1.1 * hashed(index * 7 + k, 2)
        c = Vector((math.cos(a), math.sin(a), up)).normalized()
        t = Vector((-math.sin(a), math.cos(a), 0.0))
        b = c.cross(t).normalized()
        turn = math.pi * hashed(index * 7 + k, 3)
        p = (t * math.cos(turn) + b * math.sin(turn)).normalized()   # perpendicular to c: the plane holds the centre
        out.append(dict(c=c, p=p, reach=math.cos(0.55 + 0.45 * hashed(index * 7 + k, 4)), width=0.10 + 0.04 * hashed(index * 7 + k, 5),
                        depth=0.08 + 0.05 * hashed(index * 7 + k, 6), seed=Vector((3.1 * k + index, -1.7 * k, 0.9 * index + k))))
    return out


def crack_factor(n, cracks):
    """How far in the cracks pull a point on the unit sphere (0: not at all), the deepest crack's."""
    pull = 0.0
    for cr in cracks:
        along = n.dot(cr['c'])
        if along <= cr['reach']:
            continue
        # A wavy line: the plane's distance bent by noise along the crack, so it is no straight cut.
        d = n.dot(cr['p']) + 0.05 * noise.noise(n * 5.0 + cr['seed'])
        if abs(d) >= cr['width']:
            continue
        taper = min(1.0, (along - cr['reach']) / max(1e-6, 0.35 * (1.0 - cr['reach'])))
        prof = (1.0 - (d / cr['width']) ** 2) ** 2
        pull = max(pull, cr['depth'] * prof * taper)
    return pull


def cube_sphere(bm, n):
    """A cube of n x n quads a face pushed onto the unit sphere (the even cube-to-sphere map): 12 n^2 triangles in all."""
    bmesh.ops.create_cube(bm, size=2.0)
    if n > 1:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=n - 1, use_grid_fill=True)
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector((x * math.sqrt(max(0.0, 1 - y * y / 2 - z * z / 2 + y * y * z * z / 3)),
                       y * math.sqrt(max(0.0, 1 - z * z / 2 - x * x / 2 + z * z * x * x / 3)),
                       z * math.sqrt(max(0.0, 1 - x * x / 2 - y * y / 2 + x * x * y * y / 3))))


def shaped(index, spec, n):
    """The chunk at cube-sphere resolution n: displaced, cracked, cut and capped, triangulated (unit size)."""
    bm = bmesh.new()
    cube_sphere(bm, n)
    family = spec['family']
    seed = Vector((11.3 * (index + 1), -7.9 * (index + 2), 5.3 * (index + 3)))
    aspect = spec.get('aspect', 1.0)
    cracks = cracks_for(index, spec)
    for v in bm.verts:
        n3 = v.co.normalized()
        crumbs = 0.07 * noise.noise(n3 * 7.5 + seed * 2.3)
        pull = 1.0 - crack_factor(n3, cracks)
        if family == 'rounded':
            # Three octaves, stronger than the clods' two: a lumpy body, knobs and crumbs on it.
            r = (1.0 + 0.38 * noise.noise(n3 * 1.5 + seed) + 0.16 * noise.noise(n3 * 3.6 + seed * 1.7) + crumbs) * pull
            v.co = n3 * r
        elif family == 'slab':
            # An irregular outline (the noise on the direction round Z), a lumpy top with crumbs.
            flat = Vector((n3.x, n3.y, 0.0))
            ring = 1.0 + 0.32 * noise.noise(flat * 1.3 + seed) + 0.12 * noise.noise(n3 * 3.4 + seed * 1.3)
            top = 1.0 + 0.35 * noise.noise(n3 * 2.5 + seed * 0.7) + crumbs
            v.co = Vector((n3.x * ring * pull, n3.y * ring * pull, n3.z * top * pull))
        elif family == 'broken':
            r = (1.0 + 0.26 * noise.noise(n3 * 1.7 + seed) + 0.12 * noise.noise(n3 * 4.2 + seed * 1.9) + crumbs) * pull
            v.co = n3 * r
        else:   # smear: long in X, thinning toward +X (the way it was dragged)
            r = (1.0 + 0.22 * noise.noise(n3 * 1.7 + seed) + 0.10 * noise.noise(n3 * 4.6 + seed * 1.5) + crumbs) * pull
            p = n3 * r
            t = 0.5 * (n3.x + 1.0)
            v.co = Vector((p.x * aspect, p.y, p.z * (1.15 - 0.55 * t)))
    bm.normal_update()
    caps = set()
    # The family's planar cuts (broken; the slab's broken side), each closed with a flat face, one after the other.
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
    return bm


def build(index, spec):
    # The finest cube-sphere whose finished chunk stays within TRIS (the cuts and caps take a family-dependent share).
    bm = None
    for n in range(14, 5, -1):
        if bm:
            bm.free()
        bm = shaped(index, spec, n)
        if len(bm.faces) <= TRIS[1]:
            break
    assert TRIS[0] <= len(bm.faces) <= TRIS[1], (index, len(bm.faces))
    res = n
    # Scale to WIDTH_M across (the longest horizontal side) and the family's height, the bottom at z = 0, centred in XY.
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
    height = spec['height'] * WIDTH_M
    embed = EMBED * height
    hull_pts, ring = hull_points(bm, embed)
    # The pivot: the hull's bottom centre (the area centroid of its face on the line), the line at z = 0.
    px, py = polygon_centroid(ring)
    shift = Vector((px, py, embed))
    for v in bm.verts:
        v.co -= shift
    bm.normal_update()
    volume = bm.calc_volume(signed=False)
    above = volume_above(bm, 0.0)
    me = bpy.data.meshes.new('SM_GT_MudChunk_%d' % index)
    bm.to_mesh(me)
    bm.free()
    # A UV set (the material is tri-planar in world space; Unreal still wants one): around Z, up the height.
    uv = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (math.atan2(co.y, co.x) / (2 * math.pi) + 0.5, (co.z + embed) / height)
    ob = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.get('M_GT_MudChunk') or bpy.data.materials.new('M_GT_MudChunk')
    me.materials.append(mat)
    hull_ob, hull_volume, hull_verts, hull_tris, hull_bottom = build_hull(index, [p - shift for p in hull_pts])
    return ob, hull_ob, dict(resolution=res, height_m=height, embed_m=embed, volume_m3=volume, above_m3=above, hull_m3=hull_volume, hull_verts=hull_verts,
                            hull_tris=hull_tris, hull_bottom_m=hull_bottom, pivot_shift_m=[px, py, embed])


def hull_points(bm, ze):
    """The mesh's points above the line z = ze and where its edges cross it (the hull's bottom ring), as Vectors."""
    pts = [v.co.copy() for v in bm.verts if v.co.z >= ze]
    ring = []
    for e in bm.edges:
        a, b = e.verts[0].co, e.verts[1].co
        if (a.z - ze) * (b.z - ze) < 0.0:
            t = (ze - a.z) / (b.z - a.z)
            p = a.lerp(b, t)
            p.z = ze
            ring.append(p)
    ring += [p for p in pts if abs(p.z - ze) < 1e-9]
    pts += ring
    return pts, convex_ring(ring)


def convex_ring(points):
    """The 2D convex hull (XY) of the points, counter-clockwise (monotone chain)."""
    p = sorted({(round(q.x, 9), round(q.y, 9)) for q in points})
    if len(p) < 3:
        return p

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for q in p:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], q) <= 0:
            lower.pop()
        lower.append(q)
    for q in reversed(p):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], q) <= 0:
            upper.pop()
        upper.append(q)
    return lower[:-1] + upper[:-1]


def polygon_centroid(ring):
    a = cx = cy = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        k = x0 * y1 - x1 * y0
        a += k
        cx += (x0 + x1) * k
        cy += (y0 + y1) * k
    a *= 0.5
    return (cx / (6.0 * a), cy / (6.0 * a)) if abs(a) > 1e-12 else (0.0, 0.0)


def volume_above(bm_src, z):
    """The closed volume of the mesh above z (a copy cut there and capped)."""
    bm = bm_src.copy()
    cut_and_cap(bm, (0.0, 0.0, z), (0.0, 0.0, -1.0), set())
    v = bm.calc_volume(signed=False)
    bm.free()
    return v


def farthest(points, count, start, metric):
    """Farthest-point sampling: count of the points, from start, each the farthest from those taken."""
    if len(points) <= count:
        return list(points)
    taken = [start]
    dist = [metric(p, start) for p in points]
    while len(taken) < count:
        i = max(range(len(points)), key=lambda k: dist[k])
        taken.append(points[i])
        dist = [min(dist[k], metric(points[k], points[i])) for k in range(len(points))]
    return taken


def convex_hull_bm(points):
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(bm, input=verts)
    gone = list({g for g in res['geom_interior'] + res['geom_unused'] if isinstance(g, bmesh.types.BMVert) and g.is_valid})
    if gone:
        bmesh.ops.delete(bm, geom=gone, context='VERTS')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    return bm


def build_hull(index, points):
    """UCX_<name>_00: the convex hull of the points (the mesh above the line, the line at z = 0), thinned to HULL_MAX_VERTS."""
    bm = convex_hull_bm(points)
    if len(bm.verts) > HULL_MAX_VERTS:
        extreme = [v.co.copy() for v in bm.verts]
        bm.free()
        bottom = [p for p in extreme if abs(p.z) < 1e-6]
        upper = [p for p in extreme if abs(p.z) >= 1e-6]
        d2 = lambda a, b: (a - b).length_squared
        xy2 = lambda a, b: (a.x - b.x) ** 2 + (a.y - b.y) ** 2
        ring = farthest(bottom, HULL_RING_VERTS, max(bottom, key=lambda p: p.x), xy2) if bottom else []
        top = farthest(upper, HULL_MAX_VERTS - len(ring), max(upper, key=lambda p: p.z), d2)
        bm = convex_hull_bm(ring + top)
    for v in bm.verts:
        if abs(v.co.z) < 1e-6:
            v.co.z = 0.0
    volume = bm.calc_volume(signed=False)
    nverts, ntris = len(bm.verts), len(bm.faces)
    bottom = min(v.co.z for v in bm.verts)
    me = bpy.data.meshes.new('UCX_SM_GT_MudChunk_%d_00' % index)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(me.name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, volume, nverts, ntris, bottom


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    rows = []
    for index, spec in enumerate(CHUNKS):
        ob, hull, facts = build(index, spec)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        hull.select_set(True)
        bpy.context.view_layer.objects.active = ob
        path = OUT / (ob.name + '.fbx')
        bpy.context.view_layer.update()
        bpy.ops.export_scene.fbx(filepath=str(path), **FBX)
        me = ob.data
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        dims = [round(d * 100.0, 2) for d in ob.dimensions]
        cm3 = 1.0e6
        row = dict(name=ob.name, family=spec['family'], family_index=FAMILIES.index(spec['family']), height_ratio=spec['height'],
                   fbx=str(path.relative_to(ROOT)).replace('\\', '/'), triangles=tris, vertices=len(me.vertices), size_cm=dims,
                   across_cm=round(WIDTH_M * 100.0, 3), height_cm=round(facts['height_m'] * 100.0, 3), embed_cm=round(facts['embed_m'] * 100.0, 3),
                   embed_share=EMBED, volume_cm3=round(facts['volume_m3'] * cm3, 2), volume_above_embed_cm3=round(facts['above_m3'] * cm3, 2),
                   hull_volume_cm3=round(facts['hull_m3'] * cm3, 2), hull=hull.name, hull_vertices=facts['hull_verts'], hull_triangles=facts['hull_tris'],
                   hull_bottom_cm=round(facts['hull_bottom_m'] * 100.0, 4), mesh_bottom_cm=round(min(v.co.z for v in me.vertices) * 100.0, 3),
                   cracks=spec['cracks'], cube_sphere_n=facts['resolution'], pivot_shift_cm=[round(x * 100.0, 3) for x in facts['pivot_shift_m']])
        rows.append(row)
        say(ob.name, spec['family'], 'triangles', tris, 'size cm', dims, 'volume cm3', row['volume_cm3'], 'above the line', row['volume_above_embed_cm3'],
            'hull cm3', row['hull_volume_cm3'], 'hull verts', row['hull_vertices'], 'embed cm', row['embed_cm'], '->', path)
        assert TRIS[0] <= tris <= TRIS[1], (ob.name, tris)
        assert row['hull_vertices'] <= HULL_MAX_VERTS, (ob.name, row['hull_vertices'])
        assert abs(row['hull_bottom_cm']) < 1e-3, (ob.name, row['hull_bottom_cm'])
    # Side by side in the .blend, for a look.
    for k, row in enumerate(rows):
        for name in (row['name'], row['hull']):
            bpy.data.objects[name].location = (0.4 * (k % 3), 0.4 * (k // 3), 0.0)
        bpy.data.objects[row['hull']].display_type = 'WIRE'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'MudChunks.blend'))
    manifest = dict(blender=bpy.app.version_string, units='Blender metres; FBX centimetres (apply_unit_scale), -Z forward, Y up',
                    across_cm=WIDTH_M * 100.0, embed_share=EMBED, hull_max_vertices=HULL_MAX_VERTS,
                    families='0-1 rounded, 2-3 slab, 4 broken, 5 smear (AGTMudPatch maps the number)',
                    pivot='the hull\'s bottom centre: the area centroid of its face on the embed line (z = 0); the render mesh goes on below it by embed_cm',
                    volumes='cm^3 at 30 cm across: volume_cm3 the closed render mesh (what a break deposits, x scale^3), hull_volume_cm3 the UCX_ hull, volume_above_embed_cm3 the mesh above the line',
                    chunks=rows)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    say('OK', len(rows), 'chunks ->', OUT)


main()
