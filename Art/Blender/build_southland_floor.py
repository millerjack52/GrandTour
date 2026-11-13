"""S1 Southland bush floor and river set (docs/SOUTHLAND_ASSET_PLAN.md) on the native plant kit's pipeline:
kiokio A/B, fallen log A/B, rotten stump, moss hummock A/B, river cobble cluster S/M/L, cobble bar,
bleached driftwood, log jam, river boulder A/B as deterministic Blender geometry, three authored LODs
each, FBX (cm) + GLB (m), manifest rows (set 'floor'), asset .blend and review renders.

Run: blender -b --factory-startup --python-exit-code 1 --python build_southland_floor.py [-- --only X,Y --no-render --no-assembly --assembly-only]
Each asset is designed once from its fixed seed (57000 + 97 k; all RNG is drawn in the design), then
emitted at LOD0/1/2 from that one design, so the RNG is consumed identically at every LOD.

Ground rule for every mesh: roots / buried parts stop 6 cm below the ground plane (the lowest vertex of
every LOD is clamped or shifted to z = -0.06), the pivot is the ground point under the middle of the object.
"""
import bpy, bmesh, sys, math, random, json, time
from pathlib import Path
from mathutils import Vector, Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_plant_lib as L
import build_native_bush as B
from native_plant_lib import Z, clamp, lerp, mix, scale_col, smoothstep, polar, rot, hnoise, vnoise

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ONLY = set(ARGS[ARGS.index('--only') + 1].split(',')) if '--only' in ARGS else None
NO_RENDER = '--no-render' in ARGS
NO_ASSEMBLY = '--no-assembly' in ARGS
ASM_ONLY = '--assembly-only' in ARGS
OUT = L.OUT
D2R = math.radians
FILL = B.FILL
ROOT_Z = -.06

# ---------------------------------------------------------------- colours (linear RGB)
# S1b: the S1 set rendered far too pale (near-white driftwood, pastel cobbles). Every value below is a dark,
# desaturated river/bush colour from photos 01, 05, 06, 07, 08; tints are luminance-only (0.85-1.15).
KIO = (.055, .14, .045); KIO_NEW = (.20, .11, .05); KIO_OLD = (.22, .16, .08); KIO_CROWN = (.06, .045, .03)
BARK = (.07, .055, .04); MOSS = (.11, .16, .06); LICHEN = (.22, .22, .19); ROT = (.16, .10, .05); WOOD_END = (.24, .17, .10)
HUM_MOSS = (.10, .15, .055); HUM_PALE = (.18, .23, .09); HUM_DARK = (.05, .04, .03)
COB_WARM = (.24, .20, .16); COB_DARK = (.13, .13, .12); COB_MOSS = (.10, .15, .06); COB_GREY_LUM = (.20, .28)
SAND = (.34, .30, .24)
GRAVEL = (.10, .085, .07); SHELL = (.10, .085, .07)
BLEACH = (.26, .23, .19); WEATHER = (.17, .16, .15); WDARK = (.10, .09, .08); JAM_MOSS = (.10, .15, .06)
BLEACH_END = (.31, .27, .21); BLEACH_ROOT_END = (.20, .16, .12); BLEACH_SPLINTER = (.33, .28, .22)
BOULDER = (.19, .20, .18); BOULDER_WET = (.12, .12, .11)
BAR_PACK = .66
COB_SIZE_MEDIAN = .12; COB_SIZE_SIGMA = .55; COB_SIZE_RANGE = (.04, .35)

# paint-coverage statistics for the report (LOD0 only): {layer: [vertices at mask > .5, vertices painted]}
PAINTSTAT = {}
CUR_LOD = [0]

ASSETS = [
    dict(asset='SM_NZ_Kiokio_A', family='Kiokio', variant='A', label='KIOKIO A', slots=[1], budget=(2500, 1000, 300), hulls=0),
    dict(asset='SM_NZ_Kiokio_B', family='Kiokio', variant='B', label='KIOKIO B', slots=[1], budget=(3500, 1000, 300), hulls=0),
    dict(asset='SM_NZ_Log_A', family='Log', variant='A', label='LOG A', slots=[0], budget=(4000, 1200, 300), hulls=2),
    dict(asset='SM_NZ_Log_B', family='Log', variant='B', label='LOG B', slots=[0], budget=(4000, 1200, 300), hulls=2),
    dict(asset='SM_NZ_Stump_A', family='Stump', variant='A', label='STUMP', slots=[0], budget=(2000, 600, 150), hulls=1),
    dict(asset='SM_NZ_MossHummock_A', family='MossHummock', variant='A', label='HUMMOCK A', slots=[1], budget=(800, 300, 80), hulls=0),
    dict(asset='SM_NZ_MossHummock_B', family='MossHummock', variant='B', label='HUMMOCK B', slots=[1], budget=(800, 300, 80), hulls=0),
    dict(asset='SM_NZ_Cobble_Cluster_S', family='CobbleCluster', variant='S', label='COBBLES S', slots=[0], budget=(600, 200, 60), hulls=0),
    dict(asset='SM_NZ_Cobble_Cluster_M', family='CobbleCluster', variant='M', label='COBBLES M', slots=[0], budget=(600, 200, 60), hulls=0),
    dict(asset='SM_NZ_Cobble_Cluster_L', family='CobbleCluster', variant='L', label='COBBLES L', slots=[0], budget=(600, 200, 60), hulls=0),
    dict(asset='SM_NZ_CobbleBar', family='CobbleBar', variant='', label='COBBLE BAR', slots=[0], budget=(3000, 900, 200), hulls=0),
    dict(asset='SM_NZ_Driftwood_A', family='Driftwood', variant='A', label='DRIFTWOOD', slots=[0], budget=(2000, 600, 150), hulls=1),
    dict(asset='SM_NZ_LogJam', family='LogJam', variant='', label='LOG JAM', slots=[0], budget=(6000, 1800, 500), hulls=2),
    dict(asset='SM_NZ_Boulder_A', family='Boulder', variant='A', label='BOULDER A', slots=[0], budget=(1200, 400, 100), hulls=1),
    dict(asset='SM_NZ_Boulder_B', family='Boulder', variant='B', label='BOULDER B', slots=[0], budget=(1200, 400, 100), hulls=1),
]
for _k, _a in enumerate(ASSETS):
    _a['k'] = _k


def seed_of(a):
    return 57000 + 97 * a['k']


# ================================================================ shared helpers

def tris(g):
    return sum(len(f) - 2 for f in g.f)


def ground(g, root=ROOT_Z):
    """Hold everything at or above the root depth, then make the lowest vertex sit exactly there."""
    for v in g.v:
        if v.z < root:
            v.z = root
    mn = min(v.z for v in g.v)
    if mn > root + .003:
        d = root - mn
        for v in g.v:
            v.z += d


def jit(rng, s):
    return Vector((rng.uniform(-s, s), rng.uniform(-s, s), rng.uniform(-s, s)))


def paint(g, idx, base, layers, jitter=.10, mottle=0.0, mscale=.15, stretch=None, tag=None):
    """Per-vertex colour: `base`, then for each layer irregular low-frequency blotches (the lib's domain-
    warped sine field + per-vertex noise + a finer edge noise) thresholded to the layer's coverage of the
    vertices it can reach (`weight(i)` > .5), then a fine mottle. Returns {layer name: {vertex: mix}}.
    `stretch` = (sx, sy, sz) squeezes the field's input so blotches elongate along an axis."""
    idx = list(idx)
    cols = {i: Vector(base) for i in idx}
    masks = {}
    for li, ly in enumerate(layers):
        k = ly.get('freq', 6.0); amp = ly.get('noise', .45); salt = ly.get('seed', 11 + li * 7)
        en = ly.get('edge_noise', .5); es = ly.get('edge_scale', .1); wfn = ly.get('weight')
        vals = []
        for i in idx:
            w = wfn(i) if wfn else 1.0
            if w <= 0:
                continue
            p = g.v[i]; r = g.r[i]
            sx = ly.get('stretch', stretch)
            q = Vector((p.x * sx[0], p.y * sx[1], p.z * sx[2])) if sx else p
            f = L._field(q, r, k, salt, inflate=ly.get('inflate', 0.0)) + amp * (hnoise(p, salt) - .5) * 2 + en * (2 * vnoise(q, es, salt + 3.0) - 1)
            vals.append((i, f, w))
        el = sorted(f for i, f, w in vals if w > .5)
        mk = {}
        if el:
            thr = el[min(len(el) - 1, int((1 - ly['coverage']) * len(el)))]
            pc = Vector(ly['colour'])
            for i, f, w in vals:
                soft = ly.get('soft', .06)
                m = smoothstep(thr - soft, thr + soft, f) * w * ly.get('strength', 1.0)
                if m > 0:
                    cols[i] = cols[i].lerp(pc, m); mk[i] = m
        masks[ly.get('name', str(li))] = mk
        if CUR_LOD[0] == 0:
            st = PAINTSTAT.setdefault(ly.get('name', str(li)) + '@' + str(tag or ''), [0, 0])
            st[0] += sum(1 for m in mk.values() if m > .5 * ly.get('strength', 1.0)); st[1] += len(idx)    # 'covered' = at least half the layer's own peak strength
    for i in idx:
        j = 1 - jitter + 2 * jitter * hnoise(g.v[i], 91.0)
        if mottle:
            j = 1 + mottle * ((2 * vnoise(g.v[i], mscale, 57.0) - 1) * .7 + (2 * hnoise(g.v[i], 23.0) - 1) * .3)
        g.c[i] = tuple(min(.95, x * j) for x in cols[i])
    return masks


def relief(g, mask, amount, skip=()):
    """Raise moss-coloured vertices out along their radial direction so moss reads as a mass, not a stain."""
    for i, m in mask.items():
        if m > .5 and i not in skip:
            g.v[i] = g.v[i] + g.r[i] * (amount * (.6 + .8 * hnoise(g.v[i], 5.0)) * m)


def orient(g, faces, verts, ref_fn):
    """Flip every face of a closed run together when most of them point away from ref_fn(centroid)."""
    score = 0
    for f in faces:
        a, b, c = verts[f[0]], verts[f[1]], verts[f[2]]
        cen = sum((verts[i] for i in f), Vector()) / len(f)
        score += 1 if (b - a).cross(c - a).dot(ref_fn(cen) - cen) >= 0 else -1
    return faces if score >= 0 else [tuple(reversed(f)) for f in faces]


def skin(g, A, Bv, colA, colB, ref_fn, mi=0):
    """Quad band between two rings (own vertices, so its shading edge is crisp)."""
    n = len(A)
    verts = [Vector(p) for p in A] + [Vector(p) for p in Bv]
    cols = [colA[k] if isinstance(colA, list) else colA for k in range(n)] + [colB[k] if isinstance(colB, list) else colB for k in range(n)]
    faces = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    faces = orient(g, faces, verts, ref_fn)
    g.add(verts, faces, cols, [(p.x, p.y) for p in verts], mi, [(p - sum(verts, Vector()) / len(verts)).normalized() for p in verts])


def fan(g, ring, centre, col_ring, col_centre, ref_fn, mi=0):
    n = len(ring)
    verts = [Vector(p) for p in ring] + [Vector(centre)]
    cols = [col_ring[k] if isinstance(col_ring, list) else col_ring for k in range(n)] + [col_centre]
    faces = [(k, (k + 1) % n, n) for k in range(n)]
    faces = orient(g, faces, verts, ref_fn)
    g.add(verts, faces, cols, [(p.x, p.y) for p in verts], mi, [(p - Vector(centre)).normalized() if (p - Vector(centre)).length > 1e-6 else Z for p in verts])


def ring_pts(g, start, i, sides):
    return [g.v[start + i * sides + j].copy() for j in range(sides)]


def band_noise(g, start, n, sides, pts, fr, total, amp, salt, ds=1.0, ang=.5, scale=.7):
    """Radius noise in irregular bands: a smooth 3D value noise of (arc length, radial direction)."""
    for i in range(n):
        s = fr[i] * total * ds
        for j in range(sides):
            vi = start + i * sides + j
            rv = g.r[vi]
            f = 1 + amp * (2 * vnoise(Vector((s, rv.x * ang, rv.y * ang + rv.z * ang)), scale, salt) - 1)
            g.v[vi] = pts[i] + (g.v[vi] - pts[i]) * f


def piece(g, ctrl, rfn, segs, sides, caps=(False, True), noise=0.0, phase=0.0, steps=8):
    """A tube through ctrl with radius rfn(arc fraction): returns (start vertex, rings, axis points, fractions)."""
    dense = L.curve(ctrl, steps)
    pts, fr = L.resample(dense, segs)
    radii = [rfn(f) for f in fr]
    start, n = L.tube(g, pts, radii, sides, (0, 0, 0), 0, caps, noise, phase=phase)
    return start, n, pts, fr


def tube_hull(name, dense, rfn, f0, f1, stations, coll, sides=8, pad=1.04):
    """One convex hull around the part of an axis polyline between arc fractions f0..f1: ring points at
    `stations` positions, convex hull through bmesh, hidden object named `name` (UCX_<mesh>_NN)."""
    pts = []
    for s in range(stations):
        f = lerp(f0, f1, s / (stations - 1))
        p, T = L.along(dense, f)
        u = L.perp(T); v = T.cross(u); r = rfn(f) * pad
        for j in range(sides):
            a = math.tau * (j + .5) / sides
            pts.append(p + (u * math.cos(a) + v * math.sin(a)) * r)
    return hull_from_points(name, pts, coll)


def hull_from_points(name, pts, coll):
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(tuple(p))
    res = bmesh.ops.convex_hull(bm, input=bm.verts[:])
    bmesh.ops.delete(bm, geom=res['geom_interior'], context='VERTS')
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    ob.hide_render = True; ob.hide_set(True)
    return ob



def polar_strip(rings, N):
    """Faces of a polar grid: rings[0] = [centre], rings[1..K] staggered (odd rings at phase 0, even rings
    at phase half a sector), rings[K + 1] = a skirt at ring K's phase."""
    faces = [(rings[0][0], rings[1][j], rings[1][(j + 1) % N]) for j in range(N)]
    last = len(rings) - 2
    for k in range(1, len(rings) - 1):
        A_ = rings[k]; B_ = rings[k + 1]
        for j in range(N):
            j2 = (j + 1) % N
            if k == last:
                faces += [(A_[j], B_[j], B_[j2]), (A_[j], B_[j2], A_[j2])]
            elif k % 2 == 1:
                faces += [(A_[j], B_[j], A_[j2]), (A_[j2], B_[j], B_[j2])]
            else:
                faces += [(A_[j], B_[j], B_[j2]), (A_[j], B_[j2], A_[j2])]
    return faces

# ---------------------------------------------------------------- unit meshes (icospheres and domes)

_ICO = {}


def icosphere(sub):
    if sub in _ICO:
        return _ICO[sub]
    t = (1 + 5 ** .5) / 2
    vs = [Vector(v).normalized() for v in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
                                           (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    fs = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
          (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(sub):
        cache = {}

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                vs.append(((vs[a] + vs[b]) / 2).normalized()); cache[key] = len(vs) - 1
            return cache[key]
        nf = []
        for a, b, c in fs:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        fs = nf
    _ICO[sub] = (vs, fs)
    return _ICO[sub]


_DOME = {}


def dome(nseg, rings, theta_max=1.75):
    key = (nseg, rings)
    if key in _DOME:
        return _DOME[key]
    vs = [Vector((0, 0, 1))]; fs = []
    for j in range(1, rings + 1):
        th = theta_max * j / rings
        for k in range(nseg):
            ph = math.tau * k / nseg + (.5 * math.tau / nseg if j % 2 == 0 else 0.0)
            vs.append(Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))))
    for k in range(nseg):
        fs.append((0, 1 + k, 1 + (k + 1) % nseg))
    for j in range(1, rings):
        a0 = 1 + (j - 1) * nseg; b0 = 1 + j * nseg
        for k in range(nseg):
            k2 = (k + 1) % nseg
            fs.append((a0 + k, b0 + k, b0 + k2)); fs.append((a0 + k, b0 + k2, a0 + k2))
    _DOME[key] = (vs, fs)
    return _DOME[key]


LEVELS = {'p4': ('dome', 4, 1), 'd6': ('dome', 6, 2), 'd8': ('dome', 8, 3), 'ico0': ('ico', 0), 'ico1': ('ico', 1), 'ico2': ('ico', 2), 'ico3': ('ico', 3)}


def unit_mesh(level):
    k = LEVELS[level]
    return dome(k[1], k[2]) if k[0] == 'dome' else icosphere(k[1])


# ================================================================ KIOKIO (hound's-tongue fern)

# S1b: A 14 fronds (7 outer arching below the crown, 2 mid, 4 erect of which 1 new, 1 old = 10 % each), B 18 fronds
# (9 outer, 3 mid, 4 erect of which 2 new, 2 old). B's pairs drop 52 -> 44 so 18 fronds stay inside the 3500 ceiling
# (same pinna structure: pinnate pairs on a rachis, only fewer, slightly wider pinnae).
KIOKIO = {
    'A': dict(n=14, apex=.80, reach=.82, pinna=.15, outer=7, mid=2, erect=4, new=1, old=1, pairs=36, stub_r=.040),
    'B': dict(n=18, apex=1.20, reach=1.34, pinna=.18, outer=9, mid=3, erect=4, new=2, old=2, pairs=44, stub_r=.055),
}


def frond_unit(e0, droop, power):
    pts, *_ = L.frond_path(Vector((0, 0, 0)), polar(D2R(90 - e0), 0.0), 1.0, droop, 8, power, 0.0, 0.0, None)
    return max(p.z for p in pts), max(p.x for p in pts), pts[-1].z


def fit_outer(e0, power, reach):
    """Smallest droop whose tip hangs below the crown, with the frond's reach on target."""
    for dd in range(100, 262, 4):
        a, r_, tz = frond_unit(e0, D2R(dd), power)
        if tz < -.02 and r_ > .3:
            return reach / r_, D2R(dd)
    a, r_, tz = frond_unit(e0, D2R(250), power)
    return reach / r_, D2R(250)


def fit_apex(e0, droop, power, apex):
    a, r_, tz = frond_unit(e0, droop, power)
    return apex / a


def kiokio(a, rng):
    c = KIOKIO[a['variant']]; D = B.Design()
    big = a['variant'] == 'B'
    D.tube([(0, 0, ROOT_Z), (0, 0, .02), (0, 0, .11)], [(0, c['stub_r'] * 1.1), (.55, c['stub_r']), (1, c['stub_r'] * .8)], (2, 2, 1), (6, 5, 4), 'crown', (False, True), mi=1, noise=.08)
    D.paint['crown'] = (KIO_CROWN, [], 0.0)
    roles = ['outer'] * c['outer'] + ['mid'] * c['mid'] + ['erect'] * c['erect'] + ['old'] * c['old']
    new_ids = set(range(c['outer'] + c['mid'], c['outer'] + c['mid'] + c['new']))   # the first `new` erect fronds are bronze
    az0 = rng.uniform(0, math.tau)
    for i, role in enumerate(roles):
        az = az0 + i * 2.39996 + rng.uniform(-.25, .25)
        tint = rng.uniform(.85, 1.15)
        colour = scale_col(KIO, tint)
        if role == 'outer':
            e0 = rng.uniform(50, 62); power = rng.uniform(1.1, 1.5)
            ln, droop = fit_outer(e0, power, c['reach'] * rng.uniform(.9, 1.1))
        elif role == 'mid':
            e0 = rng.uniform(62, 70); power = 1.5; droop = D2R(rng.uniform(130, 160))
            a_, r_, tz = frond_unit(e0, droop, power)
            ln = c['reach'] * rng.uniform(.62, .72) / r_
        elif role == 'erect':
            e0 = rng.uniform(72, 80); power = 2.0; droop = D2R(rng.uniform(55, 80))
            ln = fit_apex(e0, droop, power, c['apex'] * rng.uniform(.82, 1.0))
            if i in new_ids:
                colour = scale_col(KIO_NEW, tint)
        else:
            e0 = rng.uniform(6, 12); power = 1.5; droop = D2R(rng.uniform(18, 28))
            ln = c['reach'] * rng.uniform(.62, .75) / frond_unit(e0, droop, power)[1]
            colour = scale_col(KIO_OLD, tint)
        stipe = .06
        pairs = c['pairs'] if role != 'old' else int(c['pairs'] * .75)
        pitch = ln * (1 - stipe) / (pairs + .25)
        width = min(.05, pitch * 1.3)
        h = Vector((math.cos(az), math.sin(az), 0))
        anchor = Vector((0, 0, .10 if role != 'old' else .09)) + h * rng.uniform(.015, .04)
        D.frond(fold=(True, True, True), kw=dict(
            anchor=anchor, direction=polar(D2R(90 - e0), az), length=ln, pairs=pairs, pinna_len=c['pinna'] * (rng.uniform(.9, 1.05) if role != 'old' else .85),
            pinna_width=width, droop=droop, colour=colour, power=power, stipe=stipe, forward=D2R(28), rise=D2R(12),
            roll=rng.uniform(-.2, .2), curl=rng.uniform(-.04, .04), rachis_w=(.0045, .0015), floor=.012, taper=(.55, .30)))
    D.note = dict(fronds_designed=len(roles), roles={r: roles.count(r) for r in sorted(set(roles))}, pinnae_per_side=c['pairs'])
    return D


# ================================================================ LOG, STUMP, DRIFTWOOD, LOG JAM (wood on the ground)

def log_stub(g, axis_pt, T, r_at, ang, length, r0, sides, segs, tilt=.45, sweep=.5):
    """A broken branch stub standing out of a log at radial angle `ang` about the axis (0 = straight up)."""
    up = Z - T * Z.dot(T)
    up = up.normalized() if up.length > 1e-4 else L.perp(T)
    rhat = rot(up, T, ang)
    d = (rhat * (1 - tilt * .3) + T * sweep + Z * tilt * .5).normalized()
    p0 = axis_pt + rhat * r_at * .72
    ctrl = [p0, p0 + d * length * .5 + Z * length * .04, p0 + d * length]
    start, n, pts, fr = piece(g, ctrl, lambda f: lerp(r0, r0 * .5, f), segs, sides, (False, True), .05)
    return start, n


def splinter(g, start, sides, cpt, out, peaks, valley, lod, pull=.5):
    """Raise the ring at `start` into irregular splinters: up to sides/2.5 peaks (at least two ring vertices
    apart) pulled in toward the axis, every other vertex a low jagged valley. Returns the height per vertex."""
    best = {}
    maxp = max(2, int(sides / 2.5))
    for f_, h_ in sorted(peaks, key=lambda t: -t[1]):
        j = int(round(f_ * sides)) % sides
        if len(best) < maxp and all(min((j - q) % sides, (q - j) % sides) >= 2 for q in best):
            best[j] = h_
    heights = []
    for j in range(sides):
        vi = start + j; v = g.v[vi]
        if j in best:
            h = best[j]; pl = pull
        else:
            h = valley[j % len(valley)] * (1.0 if lod == 0 else .8); pl = .06
        g.v[vi] = cpt + (v - cpt) * (1 - pl) + out * h
        heights.append(h)
    return heights


def roughen(g, start, n, sides, pts, fr, total, salt, bands=.06, grain=.04):
    """Irregular radius bands plus longer, finer grain (features stretched along the axis), both smooth noise."""
    band_noise(g, start, n, sides, pts, fr, total, bands, salt)
    band_noise(g, start, n, sides, pts, fr, total, grain, salt + 1.7, ds=.42, ang=1.5, scale=.30)


class LogDesign:
    """Fallen trunk lying on the ground (long axis along x, thick end at +x), one broken or hollow end."""

    def __init__(self, a, rng):
        self.a = a; self.rng = rng
        A = a['variant'] == 'A'
        self.length = 7.55 if A else 5.0
        r0, r1 = (.35, .225) if A else (.225, .19)
        self.r0, self.r1 = r0, r1
        self.ph = [rng.uniform(0, math.tau) for _ in range(4)]
        self.lat = (.30, .09) if A else (.18, .06)
        self.rfn = lambda f: lerp(r0, r1, f ** 1.1) * (1 + .09 * math.exp(-f * 14))
        m = 11
        half = self.length / 2
        ctrl = []
        for i in range(m):
            f = i / (m - 1); x = half - self.length * f
            y = self.lat[0] * math.sin(x * .42 + self.ph[0]) + self.lat[1] * math.sin(x * 1.15 + self.ph[1])
            z = self.rfn(f) * .62 + .035 * math.sin(x * 1.3 + self.ph[2])
            ctrl.append(Vector((x, y, z)))
        self.ctrl = ctrl
        self.dense = L.curve(self.ctrl, 8)
        self.total = L.length(self.dense)
        self.moss_cov = rng.uniform(.35, .50)
        self.salt = rng.uniform(1, 90)
        fs = sorted(rng.uniform(.18, .86) for _ in range(3))
        self.stubs = [dict(f=f, ang=rng.uniform(-1.0, 1.0) + (rng.choice((-1, 1)) * .5), length=rng.uniform(.3, .8), r0=rng.uniform(.045, .075)) for f in fs]
        if A:
            npk = rng.randint(5, 7)
            self.peaks = [((k + rng.uniform(.15, .85)) / npk, rng.uniform(.22, .62)) for k in range(npk)]
            self.valley = [rng.uniform(.02, .12) for _ in range(40)]
            self.hollow = None
        else:
            self.peaks = None
            self.hollow = dict(depth=.25, inner=.62)
            self.lip = [rng.uniform(.0, .03) for _ in range(40)]
        self.sides = (18, 10, 6) if A else (16, 9, 6)
        self.segs = (70, 34, 12) if A else (50, 24, 9)
        self.stub_sides = (7, 5, 4); self.stub_segs = (4, 2, 1)

    def emit(self, lod):
        g = L.Geo(); sides = self.sides[lod]; segs = self.segs[lod]
        pts, fr = L.resample(self.dense, segs)
        radii = [self.rfn(f) for f in fr]
        start, n = L.tube(g, pts, radii, sides, (0, 0, 0), 0, (False, False), 0.0, phase=self.salt % 7)
        roughen(g, start, n, sides, pts, fr, self.total, self.salt)
        for s in self.stubs:
            p, T = L.along(self.dense, s['f'])
            log_stub(g, p, T, self.rfn(s['f']), s['ang'], s['length'], s['r0'], self.stub_sides[lod], self.stub_segs[lod])
        out = (pts[0] - pts[1]).normalized()
        heights = []
        if self.peaks:
            heights = splinter(g, start, sides, pts[0], out, self.peaks, self.valley, lod)
        elif self.hollow:
            for j in range(sides):
                vi = start + j
                g.v[vi] = g.v[vi] + out * self.lip[j % 40]
        idx = list(range(len(g.v)))
        up = lambda i: smoothstep(-.15, .45, g.r[i].z)
        # S1b: moss is a fine, low-contrast mottle (field at ~8 cm, per-vertex noise dominant) over 35-50 % of the upper
        # half only; lichen is 5 % small flecks; the brightness mottle is at 8 cm too
        masks = paint(g, idx, BARK, [
            dict(name='moss', colour=MOSS, coverage=self.moss_cov, weight=up, freq=34.0, noise=.65, edge_noise=.6, edge_scale=.08, soft=.35, strength=.55, seed=int(self.salt) + 3),
            dict(name='lichen', colour=LICHEN, coverage=.10, weight=lambda i: smoothstep(-.4, .5, g.r[i].z), freq=46.0, noise=1.0, edge_noise=.6, edge_scale=.05, soft=.12, strength=.45, seed=int(self.salt) + 5)],
            jitter=.12, mottle=.16, mscale=.08, tag=self.a['asset'])
        ends = set(range(start, start + sides)) | set(range(start + (n - 1) * sides, start + n * sides))
        relief(g, masks['moss'], .02, skip=ends)
        if self.peaks and heights:
            for j in range(sides):
                t = clamp((heights[j] - .12) / .4)
                if t > 0:
                    g.c[start + j] = tuple(mix(g.c[start + j], WOOD_END, .75 * t))
        end_ring = ring_pts(g, start, n - 1, sides)
        o_end = (pts[-1] - pts[-2]).normalized()
        fan(g, end_ring, pts[-1] + o_end * .02, [scale_col(WOOD_END, .85 + .3 * hnoise(p, 2.0)) for p in end_ring], scale_col(WOOD_END, .8),
            lambda cen, o=o_end: cen + o * 5)
        if self.peaks:
            ring = ring_pts(g, start, 0, sides)
            hm = sum(heights) / len(heights)
            fan(g, ring, pts[0] + out * (hm * .6 + .05), [scale_col(WOOD_END, .8 + .4 * hnoise(p, 4.0)) for p in ring], scale_col(WOOD_END, .75),
                lambda cen, o=out: cen + o * 5)
        elif self.hollow:
            hd = self.hollow; ring = ring_pts(g, start, 0, sides)
            r_in = self.rfn(0.0) * hd['inner']
            inner = [pts[0] + (p - pts[0]).normalized() * r_in * (1 + .08 * (2 * hnoise(p, 6.0) - 1)) + out * .01 for p in ring]
            skin(g, ring, inner, [scale_col(ROT, .7 + .5 * hnoise(p, 7.0)) for p in ring], [scale_col(ROT, .55) for _ in ring], lambda cen, o=out: cen + o * 5)
            prev = inner; depth = hd['depth']
            nd = 3 if lod == 0 else 2 if lod == 1 else 1
            for d in range(1, nd + 1):
                t = d / nd
                cur = [pts[0] - out * depth * t + ((q - pts[0]) - out * (q - pts[0]).dot(out)) * (1 - .35 * t) for q in inner]
                skin(g, prev, cur, [scale_col(ROT, .55 * (1 - .25 * (t - 1.0 / nd))) for _ in prev], [scale_col(ROT, .5 * (1 - .4 * t)) for _ in cur], lambda cen, ax=pts[0]: ax)
                prev = cur
            fan(g, prev, pts[0] - out * depth, [scale_col(ROT, .35) for _ in prev], scale_col(ROT, .25), lambda cen, o=out: cen + o * 5)
        return g

    def make_hulls(self, name, coll):
        return [tube_hull('UCX_%s_%02d' % (name, h), self.dense, lambda f: self.rfn(f), h * .5, h * .5 + .5, 5, coll) for h in range(2)]


class StumpDesign:
    """Rotten stump, 1.2 m tall, 4 buttress roots, jagged hollowed top."""

    def __init__(self, a, rng):
        self.a = a
        self.ph = [rng.uniform(0, math.tau) for _ in range(4)]
        self.salt = rng.uniform(1, 90)
        self.rfn = lambda f: lerp(.40, .33, smoothstep(0, .7, f)) * (1 + .125 * (1 - smoothstep(0, .28, f)))
        self.top_z = 1.0
        zs = [ROOT_Z, .12, .4, .7, self.top_z]
        self.ctrl = [Vector((.03 * math.sin(z * 2.1 + self.ph[0]), .03 * math.sin(z * 1.7 + self.ph[1]), z)) for z in zs]
        self.dense = L.curve(self.ctrl, 8)
        npk = 5
        self.peaks = [((k + rng.uniform(.1, .9)) / npk, rng.uniform(.14, .22)) for k in range(npk)]
        self.valley = [rng.uniform(-.03, .05) for _ in range(40)]
        a0 = rng.uniform(0, math.tau)
        self.roots = [dict(az=a0 + k * math.tau / 4 + rng.uniform(-.3, .3), reach=rng.uniform(.52, .64), r0=rng.uniform(.19, .24), zstart=rng.uniform(.42, .58)) for k in range(4)]
        self.sides = (20, 12, 6); self.segs = (16, 8, 3)
        self.root_sides = (10, 6, 4); self.root_segs = (8, 4, 2)

    def emit(self, lod):
        g = L.Geo(); sides = self.sides[lod]
        start, n, pts, fr = piece(g, self.ctrl, self.rfn, self.segs[lod], sides, (False, False), 0.0, phase=self.salt % 5)
        total = L.length(pts)
        roughen(g, start, n, sides, pts, fr, total, self.salt, bands=.07, grain=.05)
        for rt in self.roots:
            h = Vector((math.cos(rt['az']), math.sin(rt['az']), 0))
            rt0 = self.rfn(.3)
            p = [h * rt0 * .40 + Vector((0, 0, rt['zstart'])), h * (rt0 + .10) + Vector((0, 0, rt['zstart'] * .55)),
                 h * (rt0 + rt['reach'] * .45) + Vector((0, 0, .14)), h * (rt0 + rt['reach'] * .80) + Vector((0, 0, .02)), h * (self.rfn(0) + rt['reach']) + Vector((0, 0, ROOT_Z))]
            piece(g, p, lambda f, r0=rt['r0']: lerp(r0, r0 * .34, f ** .6), self.root_segs[lod], self.root_sides[lod], (True, True), .08)
        top_c = pts[-1]
        splinter(g, start + (n - 1) * sides, sides, top_c, Z, self.peaks, self.valley, lod, pull=.14)
        upper = lambda i: smoothstep(.40, .60, g.v[i].z)      # the stump's upper half (it stands 1.0-1.2 m)
        idx = list(range(len(g.v)))
        masks = paint(g, idx, BARK, [
            dict(name='moss', colour=MOSS, coverage=.48, weight=upper, freq=34.0, noise=.65, edge_noise=.6, edge_scale=.08, soft=.35, strength=.55, seed=int(self.salt) + 3),
            dict(name='lichen', colour=LICHEN, coverage=.05, freq=46.0, noise=1.0, edge_noise=.6, edge_scale=.05, soft=.12, strength=.45, seed=int(self.salt) + 5)],
            jitter=.12, mottle=.16, mscale=.08, tag=self.a['asset'])
        ends = set(range(start + (n - 1) * sides, start + n * sides))
        relief(g, masks['moss'], .02, skip=ends)
        ring = ring_pts(g, start, n - 1, sides)
        inner = []
        for k, p in enumerate(ring):
            q = top_c + (p - top_c) * .70
            q.z = p.z - (.07 + .10 * hnoise(p, 8.0)) if (p.z - top_c.z) > -.01 else p.z - .12
            inner.append(q)
        skin(g, ring, inner, [scale_col(ROT, .85 + .4 * hnoise(p, 9.0)) for p in ring], [scale_col(ROT, .65 + .35 * hnoise(p, 10.0)) for p in inner], lambda cen: cen + Z * 5)
        fan(g, inner, Vector((top_c.x, top_c.y, min(p.z for p in inner) - .06)), [scale_col(ROT, .55 + .35 * hnoise(p, 11.0)) for p in inner], scale_col(ROT, .45), lambda cen: cen + Z * 5)
        return g

    def make_hulls(self, name, coll):
        return [tube_hull('UCX_%s_00' % name, self.dense, self.rfn, 0.0, .96, 5, coll, sides=10)]


class DriftwoodDesign:
    """Bleached log with a root ball (6-9 broken root stubs) at f = 0, which is the +x end."""

    def __init__(self, a, rng):
        self.a = a
        self.length = 3.85
        self.ph = [rng.uniform(0, math.tau) for _ in range(3)]
        self.rfn = lambda f: lerp(.175, .135, f) * (1 + .50 * max(0.0, 1 - f / .11) ** 1.5)
        m = 9
        half = self.length / 2
        ctrl = []
        for i in range(m):
            f = i / (m - 1); x = half - self.length * f
            y = .16 * math.sin(x * .55 + self.ph[0]) + .05 * math.sin(x * 1.4 + self.ph[1])
            z = self.rfn(f) * .52 + .02 * math.sin(x * 1.6 + self.ph[2]) + .12 * max(0.0, 1 - f / .25) ** 2
            ctrl.append(Vector((x, y, z)))
        self.ctrl = ctrl
        self.dense = L.curve(ctrl, 8); self.total = L.length(self.dense)
        self.salt = rng.uniform(1, 90)
        nr = rng.randint(7, 9)
        self.roots = []
        for k in range(nr):
            th = D2R(rng.uniform(20, 86)); az = (k + rng.uniform(.1, .9)) / nr * math.tau
            self.roots.append(dict(th=th, az=az, length=rng.uniform(.34, .78), r0=rng.uniform(.065, .115), jit=jit(rng, .09), jit2=jit(rng, .07)))
        self.knots = [dict(f=rng.uniform(.35, .85), ang=rng.uniform(-1.2, 1.2), length=rng.uniform(.14, .28), r0=rng.uniform(.03, .045)) for _ in range(2)]
        self.sides = (14, 8, 5); self.segs = (40, 17, 7)
        self.root_sides = (6, 4, 3); self.root_segs = (3, 2, 1)

    def emit(self, lod):
        g = L.Geo(); sides = self.sides[lod]
        pts, fr = L.resample(self.dense, self.segs[lod])
        radii = [self.rfn(f) for f in fr]
        start, n = L.tube(g, pts, radii, sides, (0, 0, 0), 0, (False, False), 0.0, phase=self.salt % 5)
        roughen(g, start, n, sides, pts, fr, self.total, self.salt, bands=.05, grain=.045)
        T0 = (pts[0] - pts[1]).normalized()      # pointing out of the root end
        u = L.perp(T0); v = T0.cross(u)
        for rt in self.roots:
            ra = (u * math.cos(rt['az']) + v * math.sin(rt['az']))
            d = (T0 * math.cos(rt['th']) + ra * math.sin(rt['th']) + Z * .15).normalized()
            p0 = pts[0] + ra * self.rfn(0.0) * .55 - T0 * .04
            ctrl = [p0, p0 + d * rt['length'] * .5 + rt['jit'], p0 + d * rt['length'] + rt['jit2'] - Z * .06 * rt['length']]
            piece(g, ctrl, lambda f, r0=rt['r0']: lerp(r0, r0 * .4, f), self.root_segs[lod], self.root_sides[lod], (False, True), .08)
        for s in self.knots:
            p, T = L.along(self.dense, s['f'])
            log_stub(g, p, T, self.rfn(s['f']), s['ang'], s['length'], s['r0'], 5 if lod < 2 else 3, 2 if lod == 0 else 1)
        idx = list(range(len(g.v)))
        # S1b: grey-brown bleached wood, not white: base (.26,.23,.19), 35 % low-contrast grey weathering mottle,
        # 15 % near-black (dark cracks 5 % + the underside 10 %)
        under = lambda i: 1 - smoothstep(-.85, -.55, g.r[i].z)
        paint(g, idx, BLEACH, [dict(name='weather', colour=WEATHER, coverage=.35, freq=7.0, noise=.6, edge_noise=.7, edge_scale=.07, soft=.35, strength=.9, seed=int(self.salt) + 3),
                               dict(name='under', colour=WDARK, coverage=.40, weight=under, freq=5.0, noise=.4, edge_noise=.5, edge_scale=.10, soft=.2, seed=int(self.salt) + 4),
                               dict(name='cracks', colour=WDARK, coverage=.05, freq=16.0, noise=.9, edge_noise=.6, edge_scale=.05, soft=.12, stretch=(.22, 1.0, 1.0), seed=int(self.salt) + 6)],
              jitter=.09, mottle=.12, mscale=.10, stretch=(.45, 1.0, 1.0), tag=self.a['asset'])
        end = ring_pts(g, start, n - 1, sides)
        o = (pts[-1] - pts[-2]).normalized()
        fan(g, end, pts[-1] + o * .015, [scale_col(BLEACH_END, .85 + .3 * hnoise(p, 2.0)) for p in end], scale_col(BLEACH_END, .8), lambda cen: cen + o * 5)
        rend = ring_pts(g, start, 0, sides)
        fan(g, rend, pts[0] + T0 * .02, [scale_col(BLEACH_ROOT_END, .8 + .4 * hnoise(p, 3.0)) for p in rend], scale_col(BLEACH_ROOT_END, .8), lambda cen: cen + T0 * 5)
        return g

    def make_hulls(self, name, coll):
        return [tube_hull('UCX_%s_00' % name, self.dense, self.rfn, 0.0, 1.0, 6, coll)]


class LogJamDesign:
    """6 x 3 x 1.2 m tangle of 8 bleached logs and branches (plus a few twigs), resting on the ground at the
    water side (-y) and rising onto an implied bank along the +y long side."""

    def __init__(self, a, rng):
        self.a = a
        self.salt = rng.uniform(1, 90)
        specs = [  # layer, length, diameter
            (0, 5.6, .40), (0, 4.8, .34), (0, 5.2, .30), (1, 4.9, .36), (1, 5.4, .27), (2, 4.4, .30), (1, 2.6, .19), (2, 3.0, .16)]
        self.logs = []
        sign = 1
        for k, (layer, ln, dia) in enumerate(specs):
            phi = D2R(rng.uniform(6, 26)) * sign; sign = -sign
            if k == 6:
                phi = D2R(rng.uniform(26, 34)) * (1 if rng.random() < .5 else -1)
            ext_x = ln / 2 * math.cos(phi); ext_y = ln / 2 * abs(math.sin(phi)) + dia / 2
            cx = rng.uniform(-(3.0 - ext_x), (3.0 - ext_x)) * .85
            if k == 0:
                cx = 3.0 - ext_x - .05
            if k == 1:
                cx = -(3.0 - ext_x) + .05
            cy = {0: rng.uniform(-.7, .0), 1: rng.uniform(-.3, .5), 2: rng.uniform(.1, .7)}[layer]
            cy = clamp(cy, -1.5 + ext_y, 1.5 - ext_y)
            z0 = dia / 2 * .78 + layer * .24
            slope = rng.uniform(.20, .32) if layer else rng.uniform(.08, .16)
            self.logs.append(dict(len=ln, r=dia / 2, phi=phi, cx=cx, cy=cy, z0=z0, slope=slope, tint=rng.uniform(.85, 1.15), layer=layer, kind='log',
                                  salt=rng.uniform(1, 90), wob=rng.uniform(.05, .12), wph=rng.uniform(0, math.tau),
                                  stubs=[dict(f=rng.uniform(.2, .8), ang=rng.uniform(-1.3, 1.3), length=rng.uniform(.16, .30), r0=rng.uniform(.03, .045)) for _ in range(rng.randint(0, 2))],
                                  moss=.10 if layer == 0 else 0.0,
                                  broken=[((j + rng.uniform(.15, .85)) / 4, rng.uniform(.10, .34)) for j in range(4)] if k in (0, 3, 5) else None,
                                  valley=[rng.uniform(.01, .06) for _ in range(20)]))
        # branches 6 and 7 carry forks
        for k in (6, 7):
            self.logs[k]['forks'] = [dict(f=rng.uniform(.3, .7), ang=rng.uniform(-1.0, 1.0), length=rng.uniform(.32, .5), r0=rng.uniform(.045, .065)) for _ in range(2)]
        # a few thin twigs lying across the top
        for t in range(5):
            ln = rng.uniform(.9, 1.8); dia = rng.uniform(.05, .08)
            phi = D2R(rng.uniform(-40, 40))
            cx = rng.uniform(-2.2, 2.2); cy = rng.uniform(-.6, .8)
            self.logs.append(dict(len=ln, r=dia / 2, phi=phi, cx=cx, cy=cy, z0=.50 + rng.uniform(0, .18), slope=rng.uniform(.05, .15), tint=rng.uniform(.85, 1.15), layer=3, kind='twig',
                                  salt=rng.uniform(1, 90), wob=.03, wph=rng.uniform(0, math.tau), stubs=[], moss=0.0, broken=None, valley=[.02] * 20))
        self.sides = (12, 7, 4)
        self.seg_per_m = (5.0, 2.0, .8)
        for lg in self.logs:
            c, s = math.cos(lg['phi']), math.sin(lg['phi'])
            ctrl = []
            m = 7
            for i in range(m):
                t = i / (m - 1); d = (t - .5) * lg['len']
                x = lg['cx'] + d * c - s * lg['wob'] * math.sin(d * 1.3 + lg['wph']); y = lg['cy'] + d * s + c * lg['wob'] * math.sin(d * 1.3 + lg['wph'])
                z = lg['z0'] + lg['slope'] * (y + 1.5) + .03 * math.sin(d * 2.1 + lg['salt'])
                z = min(z, .80 - lg['r'])
                ctrl.append(Vector((x, y, z)))
            lg['ctrl'] = ctrl; lg['dense'] = L.curve(ctrl, 8); lg['rfn'] = lambda f, r=lg['r']: r * (1 - .22 * f) * (1 + .05 * math.sin(f * 13))

    def emit(self, lod):
        g = L.Geo(); sides = self.sides[lod]
        for k, lg in enumerate(self.logs):
            i0 = len(g.v)
            sd = sides if lg['kind'] == 'log' else (5, 4, 3)[lod]
            segs = max(3, int(round(lg['len'] * self.seg_per_m[lod] * (1 if lg['kind'] == 'log' else .6))))
            pts, fr = L.resample(lg['dense'], segs)
            start, n = L.tube(g, pts, [lg['rfn'](f) for f in fr], sd, (0, 0, 0), 0, (False, False), 0.0, phase=k * .7)
            tot = L.length(pts)
            if lg['kind'] == 'log':
                roughen(g, start, n, sd, pts, fr, tot, lg['salt'], bands=.07, grain=.04)
            for s in lg['stubs']:
                p, T = L.along(lg['dense'], s['f'])
                log_stub(g, p, T, lg['rfn'](s['f']), s['ang'], s['length'], s['r0'], 5 if lod < 2 else 3, 2 if lod == 0 else 1)
            for fk in lg.get('forks', []):
                p, T = L.along(lg['dense'], fk['f'])
                log_stub(g, p, T, lg['rfn'](fk['f']), fk['ang'], fk['length'], fk['r0'], 5 if lod < 2 else 3, 3 if lod == 0 else 2 if lod == 1 else 1, tilt=.6, sweep=.9)
            out0 = (pts[0] - pts[1]).normalized()
            heights = []
            if lg['broken']:
                heights = splinter(g, start, sd, pts[0], out0, lg['broken'], lg['valley'], lod)
            low = lambda i: 1 - smoothstep(.12, .5, g.v[i].z)
            under = lambda i: 1 - smoothstep(-.85, -.55, g.r[i].z)
            layers = [dict(name='weather', colour=WEATHER, coverage=.35, freq=7.0, noise=.6, edge_noise=.7, edge_scale=.07, soft=.35, strength=.9, seed=int(lg['salt']) + 3),
                      dict(name='under', colour=WDARK, coverage=.40, weight=under, freq=5.0, noise=.4, edge_noise=.5, edge_scale=.10, soft=.2, seed=int(lg['salt']) + 4),
                      dict(name='cracks', colour=WDARK, coverage=.05, freq=16.0, noise=.9, edge_noise=.6, edge_scale=.05, soft=.12, stretch=(.22, .5, 1.0), seed=int(lg['salt']) + 6)]
            if lg['moss']:
                # moss only on the lowest logs (layer 0), 10 % of their vertices, and only on the low upward-facing part
                layers.append(dict(name='moss', colour=JAM_MOSS, coverage=lg['moss'], weight=lambda i: low(i) * smoothstep(-.2, .5, g.r[i].z), freq=22.0, noise=.6, edge_noise=.7, edge_scale=.08, soft=.2, seed=int(lg['salt']) + 5))
            idx = list(range(i0, len(g.v)))
            masks = paint(g, idx, scale_col(BLEACH, lg['tint']), layers, jitter=.09, mottle=.12, mscale=.10, stretch=(.5, .5, 1.0), tag='LogJam')
            if 'moss' in masks:
                relief(g, masks['moss'], .02)
            if heights:
                for j in range(sd):
                    t = clamp((heights[j] - .08) / .25)
                    if t > 0:
                        g.c[start + j] = tuple(mix(g.c[start + j], scale_col(BLEACH_SPLINTER, lg['tint']), .7 * t))
            for end_i, sgn in ((0, -1), (n - 1, 1)):
                ring = ring_pts(g, start, end_i, sd)
                o = out0 if sgn < 0 else (pts[-1] - pts[-2]).normalized()
                hm = (sum(heights) / len(heights) * .6 + .02) if (sgn < 0 and heights) else .01
                cen = pts[end_i] + o * hm
                fan(g, ring, cen, [scale_col(BLEACH_END, lg['tint'] * (.85 + .3 * hnoise(p, 2.0))) for p in ring], scale_col(BLEACH_END, .8 * lg['tint']), lambda c_, o=o: c_ + o * 5)
        return g

    def make_hulls(self, name, coll):
        hs = []
        for h, (x0, x1) in enumerate(((-3.0, .05), (-.05, 3.0))):
            pts = []
            for x in (x0, x1):
                y0, y1, zf, zm, zb = (-1.35, 1.5, .36, .70, .90)
                pts += [Vector((x, y0, ROOT_Z)), Vector((x, y1, ROOT_Z)), Vector((x, y0 + .15, zf)), Vector((x, .1, zm)), Vector((x, y1 - .02, zb))]
            hs.append(hull_from_points('UCX_%s_%02d' % (name, h), pts, coll))
        return hs


# ================================================================ MOSS HUMMOCK

class HummockDesign:
    def __init__(self, a, rng):
        self.a = a
        A = a['variant'] == 'A'
        self.W, self.H = (.70, .22) if A else (1.20, .35)
        R = self.W / 2 * .91; self.R = R
        self.ph = [rng.uniform(0, math.tau) for _ in range(3)]
        self.salt = rng.uniform(1, 90)
        self.lobes = []
        nl = rng.randint(4, 6)
        a0 = rng.uniform(0, math.tau)
        for k in range(nl):
            az = a0 + (k + rng.uniform(-.2, .2)) * math.tau / nl
            self.lobes.append((math.cos(az) * rng.uniform(.46, .66) * R, math.sin(az) * rng.uniform(.46, .66) * R, rng.uniform(.17, .25) * R, rng.uniform(.75, 1.0)))
        self.lobes.append((rng.uniform(-.10, .10) * R, rng.uniform(-.10, .10) * R, rng.uniform(.20, .27) * R, rng.uniform(.8, 1.0)))
        self.N = (30, 18, 8); self.K = (11, 6, 3)
        mx = 0.0
        for i in range(40):
            for j in range(40):
                x = (i / 39 * 2 - 1) * R; y = (j / 39 * 2 - 1) * R
                rho = math.hypot(x, y) / R
                if rho < 1:
                    mx = max(mx, self.raw(x, y, rho))
        self.norm = 1 / mx

    def outline(self, az):
        return self.R * (1 + .10 * math.sin(2 * az + self.ph[0]) + .07 * math.sin(3 * az + self.ph[1]) + .04 * math.sin(5 * az + self.ph[2]))

    def lobe(self, x, y):
        """Probabilistic union of the lobes: 0 in the gaps between them, near 1 on a lobe."""
        q = 1.0
        for lx, ly, sg, amp in self.lobes:
            q *= 1 - amp * math.exp(-((x - lx) ** 2 + (y - ly) ** 2) / (2 * sg * sg))
        return 1 - q

    def raw(self, x, y, rho):
        env = max(0.0, 1 - rho * rho) ** .38
        return env * (.20 + .80 * self.lobe(x, y))

    def emit(self, lod):
        g = L.Geo(); N = self.N[lod]; K = self.K[lod]
        verts = []; cols = []; rings = []
        W = self.W

        def vcol(p, h01, lobe01, rho):
            t = lerp(.85, 1.15, vnoise(p, W * .22, self.salt))
            c = Vector(scale_col(HUM_MOSS, t))
            pale = smoothstep(.45, .95, h01 * .75 + lobe01 * .30 + .35 * (vnoise(p, W * .12, self.salt + 2) - .5))
            c = c.lerp(Vector(scale_col(HUM_PALE, t)), pale)
            dark = (1 - smoothstep(.30, .58, lobe01)) * smoothstep(.35, .75, rho) * smoothstep(.50, .70, vnoise(p, W * .16, self.salt + 5))
            c = c.lerp(Vector(HUM_DARK), clamp(dark * 1.1))
            return tuple(c)
        p0 = Vector((0, 0, self.H * self.raw(0, 0, 0) * self.norm))
        verts.append(p0); cols.append(vcol(p0, 1.0, 1.0, 0.0)); rings.append([0])
        amp_f = self.H * .10
        for k in range(1, K + 1):
            rho = k / K; ring = []
            for j in range(N):
                az = math.tau * (j + (.5 if k % 2 == 0 else 0)) / N
                Rr = self.outline(az) * rho * (1 + (.04 * (2 * hnoise((rho, az, 1.0), self.salt) - 1) if k < K else 0.0))
                x, y = Rr * math.cos(az), Rr * math.sin(az)
                rr = min(1.0, math.hypot(x, y) / max(self.outline(az), 1e-6))
                h = self.H * self.raw(x, y, rr) * self.norm
                if k < K:
                    h += amp_f * (2 * vnoise(Vector((x, y, 0)), W * .055, self.salt + 7) - 1) * (1 - rr * rr)
                else:
                    h = 0.0
                p = Vector((x, y, max(h, 0.0)))
                ring.append(len(verts)); verts.append(p)
                cols.append(vcol(p, p.z / self.H, self.lobe(x, y), rr))
            rings.append(ring)
        skirt = []
        for j in range(N):
            az = math.tau * (j + (.5 if K % 2 == 0 else 0)) / N
            Rr = self.outline(az) * 1.035
            p = Vector((Rr * math.cos(az), Rr * math.sin(az), ROOT_Z))
            skirt.append(len(verts)); verts.append(p); cols.append(tuple(scale_col(HUM_DARK, 1.2)))
        rings.append(skirt)
        faces = polar_strip(rings, N)
        faces = orient(g, faces, verts, lambda cen: cen + Vector((0, 0, 3)) if cen.z > 0 else cen + Vector((cen.x, cen.y, 0)) * 3)
        g.add(verts, faces, cols, [(p.x, p.y) for p in verts], 1, [(p - Vector((0, 0, -self.H * .2))).normalized() for p in verts])
        return g


# ================================================================ COBBLES (clusters and the bar)

class Cob:
    pass


def cobble_geom(cob, level, enlarge=1.0, zcut=-.02):
    """World-space vertices, triangles and radial hints of one cobble at a detail level: a displaced ellipsoid
    (icosphere or a low dome) half-sunk at the ground, parts below `zcut` dropped, the rest clamped to it."""
    uv, uf = unit_mesh(level)
    Rm = Matrix.Rotation(cob.yaw, 3, 'Z') @ Matrix.Rotation(cob.tilt[0], 3, 'X') @ Matrix.Rotation(cob.tilt[1], 3, 'Y')
    P = []; Rd = []; Zo = []
    for u in uv:
        f = 1 + .11 * (2 * vnoise(u * 1.0 + Vector((3.1, 1.7, 5.3)), .55, cob.salt) - 1) + .04 * (2 * vnoise(u * 2.3, .5, cob.salt + 2) - 1)
        q = Vector((u.x * cob.a * f, u.y * cob.b * f, u.z * cob.c * f)) * enlarge
        q = Rm @ q + Vector((cob.x, cob.y, cob.z + cob.z0 * enlarge))
        P.append(q); Zo.append(q.z); Rd.append((Rm @ u).normalized())
    keep = [f for f in uf if max(Zo[i] for i in f) > zcut]
    used = sorted({i for f in keep for i in f})
    remap = {o: n for n, o in enumerate(used)}
    verts = [Vector((P[o].x, P[o].y, max(P[o].z, zcut))) for o in used]
    rad = [Rd[o] for o in used]
    faces = [tuple(remap[i] for i in f) for f in keep]
    cen = Vector((cob.x, cob.y, cob.z))
    faces = [f if (verts[f[1]] - verts[f[0]]).cross(verts[f[2]] - verts[f[0]]).dot(sum((verts[i] for i in f), Vector()) / 3 - cen) >= 0 else tuple(reversed(f)) for f in faces]
    return verts, faces, rad


def fit_levels(cobs, ladder, budget, fixed, enlarge):
    """Round-robin the largest cobbles up the detail ladder until 96 % of the ceiling is spent; drop the
    smallest cobbles when even the lowest rung does not fit."""
    cache = {}

    def cost(i, lv):
        key = (i, lv)
        if key not in cache:
            cache[key] = len(cobble_geom(cobs[i], ladder[lv], enlarge)[1])
        return cache[key]
    room = FILL * budget
    kept = list(range(len(cobs))); levels = [0] * len(cobs)
    total = fixed + sum(cost(i, 0) for i in kept)
    while total > room and kept:
        i = kept.pop(); total -= cost(i, 0)
    changed = True
    while changed:
        changed = False
        for i in kept:
            if levels[i] + 1 < len(ladder):
                add = cost(i, levels[i] + 1) - cost(i, levels[i])
                if total + add <= room:
                    levels[i] += 1; total += add; changed = True
    return levels, kept, total


def lognormal_d(rng, lo=COB_SIZE_RANGE[0], hi=COB_SIZE_RANGE[1]):
    """One cobble diameter (m): lognormal, median 12 cm, truncated to [lo, hi] by redrawing."""
    for _ in range(60):
        d = math.exp(rng.gauss(math.log(COB_SIZE_MEDIAN), COB_SIZE_SIGMA))
        if lo <= d <= hi:
            return d
    return clamp(d, lo, hi)


def pack_cobbles(rng, ds, sample, overlap=.80, tries=80, spread_first=16, min_gap=-.25, inside=None):
    """Place cobbles (diameters `ds`, largest first) so they touch. A candidate's gap is min over the placed
    cobbles of dist - overlap * (d + d_o) / 2 (>= 0: no overlap beyond the allowed 1 - overlap). The first
    `spread_first` (the biggest) take the most open of their `tries` random candidates (a spread skeleton). Every
    later one picks among `tries` candidates, half random and half CONTACT candidates (touching a randomly chosen
    placed cobble at a random angle), and takes the accepted one with the SMALLEST gap, i.e. snuggled into the pile;
    when none is accepted the least overlapping one is used unless it would bury the cobble (gap < min_gap * d),
    then the cobble is skipped. `inside(x, y, d)` (optional) keeps contact candidates in the region. Returns
    (x, y, d) for the cobbles placed."""
    out = []
    for k, d in enumerate(ds):
        best = None; fallback = None; open_ = None
        for t in range(tries):
            if k >= spread_first and out and t % 2:
                o = out[rng.randrange(len(out))]
                ang = rng.uniform(0, math.tau); r = overlap * (d + o[2]) / 2 * 1.0005
                x, y = o[0] + r * math.cos(ang), o[1] + r * math.sin(ang)
                if inside is not None and not inside(x, y, d):
                    continue
            else:
                xy = sample(d)
                if xy is None:
                    continue
                x, y = xy
            gap = min([math.hypot(x - o[0], y - o[1]) - overlap * (d + o[2]) / 2 for o in out] or [9.0])
            if open_ is None or gap > open_[0]:
                open_ = (gap, x, y)
            if gap >= 0:
                if best is None or gap < best[0]:
                    best = (gap, x, y)
            elif fallback is None or gap > fallback[0]:
                fallback = (gap, x, y)
        pick = open_ if k < spread_first else (best or (fallback if fallback and fallback[0] >= min_gap * d else None))
        if pick is None:
            continue
        out.append((pick[1], pick[2], d))
    return out


def make_cob(rng, diameter, x, y, z=0.0, moss_p=0.0):
    """One cobble. Colour family: 60 % neutral grey (luminance .20-.28), 25 % warm (.24,.20,.16), 15 % dark
    (.13,.13,.12); warm and dark take a luminance-only tint of .85-1.15 (the grey family's own luminance spread is
    the variation). `moss_p` is the chance this cobble carries moss (callers pass it for bar-edge cobbles only)."""
    c = Cob()
    c.a = diameter / 2 * rng.uniform(.95, 1.05); c.b = c.a * rng.uniform(.70, .92); c.c = c.b * rng.uniform(.68, .95)
    c.yaw = rng.uniform(0, math.tau); c.tilt = (rng.uniform(-.1, .1), rng.uniform(-.1, .1))
    c.x = x; c.y = y; c.z = z; c.z0 = -c.c * .04
    r = rng.random()
    if r < .60:
        lum = rng.uniform(*COB_GREY_LUM); c.base = (lum, lum, lum); c.tint = 1.0
    elif r < .85:
        c.base = COB_WARM; c.tint = rng.uniform(.85, 1.15)
    else:
        c.base = COB_DARK; c.tint = rng.uniform(.85, 1.15)
    mr = rng.random()
    c.moss = rng.uniform(.4, .85) if mr < moss_p else 0.0
    c.salt = rng.uniform(1, 90)
    c.size = diameter
    return c


def paint_cob(g, cob, idx):
    idx = list(idx)
    ly = []
    if cob.moss:
        ly.append(dict(name='moss', colour=COB_MOSS, coverage=cob.moss, weight=lambda i: smoothstep(.35, .75, g.r[i].z), freq=22.0, noise=.5, edge_noise=.5, edge_scale=.03, soft=.12, seed=int(cob.salt)))
    paint(g, idx, scale_col(cob.base, cob.tint), ly, jitter=.07, mottle=.10, mscale=.07, tag='cobble')
    # wet: the lower third of every cobble is 40 % darker (soft edge between 27 % and 40 % of its height)
    top = max(g.v[i].z for i in idx); lo = cob.z
    span = max(top - lo, 1e-4)
    for i in idx:
        t = (g.v[i].z - lo) / span
        w = 1 - smoothstep(.27, .40, t)
        if w > 0:
            g.c[i] = tuple(x * (1 - .40 * w) for x in g.c[i])


def emit_cobbles(g, cobs, levels, kept, ladder, enlarge):
    for i in kept:
        verts, faces, rad = cobble_geom(cobs[i], ladder[levels[i]], enlarge)
        i0 = g.add(verts, faces, (0, 0, 0), [(p.x, p.y) for p in verts], 0, rad)
        paint_cob(g, cobs[i], range(i0, i0 + len(verts)))


class ClusterDesign:
    """A loose scatter of cobbles (lognormal sizes, median 12 cm, at most the cluster's own upper size) spread
    over a dark gravel dish; best-candidate spacing keeps them apart, the dish is dark so gaps never read pale."""

    def __init__(self, a, rng):
        self.a = a
        v = a['variant']
        n, Rc, dhi = {'S': (5, .205, .20), 'M': (8, .41, .30), 'L': (12, .745, COB_SIZE_RANGE[1])}[v]
        self.n = n; self.Rc = Rc
        ds = sorted((lognormal_d(rng, COB_SIZE_RANGE[0], dhi) for _ in range(n)), reverse=True)
        self.cobs = []
        for d in ds:
            best = None
            for _ in range(40):
                ang = rng.uniform(0, math.tau); rad = Rc * math.sqrt(rng.uniform(0, 1))
                rad = min(rad, max(0.0, Rc - d / 2 * 1.02))
                x, y = rad * math.cos(ang), rad * math.sin(ang)
                gap = min([math.hypot(x - o.x, y - o.y) - (d + o.size) / 2 * .92 for o in self.cobs] or [9.0])
                if best is None or gap > best[0]:
                    best = (gap, x, y)
            self.cobs.append(make_cob(rng, d, best[1], best[2]))
        self.ladders = (['ico0', 'ico1', 'ico2'], ['p4', 'ico0', 'ico1'], ['p4', 'ico0'])
        self.enl = (1.0, 1.05, 1.12)
        self.apron = (10, 8, 6)

    def emit(self, lod):
        g = L.Geo()
        n_ap = self.apron[lod]
        levels, kept, total = fit_levels(self.cobs, self.ladders[lod], self.a['budget'][lod], n_ap, self.enl[lod])
        self.last = (levels, kept)
        emit_cobbles(g, self.cobs, levels, kept, self.ladders[lod], self.enl[lod])
        # a shallow gravel dish under the cobbles: its edge is the 6 cm root, its middle just below the ground plane
        ring = [Vector((self.Rc * .94 * math.cos(math.tau * k / n_ap), self.Rc * .94 * math.sin(math.tau * k / n_ap), ROOT_Z)) for k in range(n_ap)]
        fan(g, ring, Vector((0, 0, -.012)), scale_col(GRAVEL, .95), scale_col(GRAVEL, 1.05), lambda cen: cen + Z * 5)
        return g


class BarDesign:
    """3 x 2 m low shell (a lens of dark gravel with a few pale sand patches at its rim) carrying ~120 cobbles of
    lognormal size (median 12 cm, 4-35 cm), packed so the gaps between them are dark."""

    def __init__(self, a, rng):
        self.a = a
        self.ph = [rng.uniform(0, math.tau) for _ in range(3)]
        self.salt = rng.uniform(1, 90)
        self.RX, self.RY = 1.5, 1.0
        self.peak = .035
        ds = sorted((lognormal_d(rng) for _ in range(124)), reverse=True)

        PACK = BAR_PACK            # the packed pile fills this fraction of the shell's outline; bare dark gravel and a few sand patches edge it

        def inside(x, y, d):
            rho = math.hypot(x / self.RX, y / self.RY) / max(self.outline(math.atan2(y / self.RY, x / self.RX)), 1e-6)
            return rho <= PACK - d / (2 * self.RY) * .3

        def sample(d):
            for _ in range(8):
                ang = rng.uniform(0, math.tau); rr = math.sqrt(rng.uniform(0, 1)) * PACK
                x = self.RX * self.outline(ang) * rr * math.cos(ang); y = self.RY * self.outline(ang) * rr * math.sin(ang)
                if inside(x, y, d):
                    return x, y
            return None
        placed = pack_cobbles(rng, ds, sample, overlap=.68, tries=120, spread_first=10, inside=inside)
        self.cobs = []
        for k, (x, y, d) in enumerate(placed):
            rho = math.hypot(x / self.RX, y / self.RY) / max(self.outline(math.atan2(y / self.RY, x / self.RX)), 1e-6)
            # a cobble that overlaps earlier (larger) ones in plan rests up on them, not through them
            lift = 0.0
            for (ox, oy, od) in placed[:k]:
                depth = .8 * (d + od) / 2 - math.hypot(x - ox, y - oy)
                if depth > 0:
                    lift = max(lift, min(depth * .6, .35 * d))
            self.cobs.append(make_cob(rng, d, x, y, self.height(x, y) + lift, moss_p=.10 if rho > .55 else 0.0))
        self.designed = len(ds)
        self.ladders = (['ico0', 'ico1'], ['p4'], ['p4'])
        self.enl = (1.0, 1.12, 1.55)
        self.NK = ((24, 6), (14, 3), (8, 2))

    def outline(self, az):
        return 1 + .07 * math.sin(3 * az + self.ph[0]) + .05 * math.sin(5 * az + self.ph[1])

    def height(self, x, y):
        rho = math.hypot(x / self.RX, y / self.RY) / max(self.outline(math.atan2(y / self.RY, x / self.RX)), 1e-6)
        if rho >= 1:
            return 0.0
        return self.peak * (1 - rho * rho) ** .8 + .010 * math.sin(x * 4.1 + self.ph[2]) * math.sin(y * 3.3 + self.ph[0]) * (1 - rho)

    def shell(self, g, lod):
        N, K = self.NK[lod]
        verts = [Vector((0, 0, self.height(0, 0)))]; rings = [[0]]
        for k in range(1, K + 1):
            rho = k / K; ring = []
            for j in range(N):
                az = math.tau * (j + (.5 if k % 2 == 0 else 0)) / N
                ol = self.outline(az)
                x, y = self.RX * ol * rho * math.cos(az), self.RY * ol * rho * math.sin(az)
                z = self.height(x, y) if k < K else 0.0
                ring.append(len(verts)); verts.append(Vector((x, y, z)))
            rings.append(ring)
        sk = []
        for j in range(N):
            az = math.tau * (j + (.5 if K % 2 == 0 else 0)) / N
            ol = self.outline(az) * 1.04
            sk.append(len(verts)); verts.append(Vector((self.RX * ol * math.cos(az), self.RY * ol * math.sin(az), ROOT_Z)))
        rings.append(sk)
        faces = polar_strip(rings, N)
        faces = orient(g, faces, verts, lambda cen: cen + (Z * 3 if cen.z > ROOT_Z + .01 else Vector((cen.x, cen.y, 0)) * 3))
        i0 = g.add(verts, faces, GRAVEL, [(p.x, p.y) for p in verts], 0, [Z] * len(verts))
        # S1b: the surface under the cobbles is dark (.10,.085,.07); pale sand (.34,.30,.24) only in a few small patches
        # on the outermost rim (<= 15 % of the shell, never in the middle where the cobbles are packed)
        def rho_i(i):
            p = g.v[i]
            return math.hypot(p.x / self.RX, p.y / self.RY) / max(self.outline(math.atan2(p.y / self.RY, p.x / self.RX)), 1e-6)
        rim = lambda i: smoothstep(.88, .97, rho_i(i)) * (1.0 if g.v[i].z > ROOT_Z + .01 else 0.0)
        paint(g, range(i0, i0 + len(verts)), SHELL, [dict(name='sand', colour=SAND, coverage=.40, weight=rim, freq=16.0, noise=.6, edge_noise=.6, edge_scale=.10, soft=.15, seed=int(self.salt) + 1)],
              jitter=.08, mottle=.12, mscale=.2, tag='CobbleBar')
        return len(faces)

    def emit(self, lod):
        g = L.Geo()
        nshell = self.shell(g, lod)
        levels, kept, total = fit_levels(self.cobs, self.ladders[lod], self.a['budget'][lod], nshell, self.enl[lod])
        self.last = (levels, kept)
        emit_cobbles(g, self.cobs, levels, kept, self.ladders[lod], self.enl[lod])
        return g


# ================================================================ BOULDER

class BoulderDesign:
    def __init__(self, a, rng):
        self.a = a
        A = a['variant'] == 'A'
        self.ax, self.ay, self.az = (.76, .62, .64) if A else (.41, .34, .33)
        self.z0 = self.az * .22
        self.yaw = rng.uniform(0, math.tau); self.salt = rng.uniform(1, 90)
        n1 = Vector((rng.uniform(-.25, .25), rng.uniform(-.25, .25), 1.0)).normalized()
        n2 = Vector((math.cos(rng.uniform(0, math.tau)), math.sin(rng.uniform(0, math.tau)), rng.uniform(.0, .25))).normalized()
        self.planes = [(n1, .80), (n2, .86)]
        self.sub = (3, 2, 1)
        self.top = max(p.z for p in self.verts(2)[0])
        self.moss_cov = rng.uniform(.72, .90)

    def verts(self, lod):
        uv, uf = icosphere(self.sub[lod] if lod < 3 else 2)
        out = []
        for u in uv:
            f = 1 + .12 * (2 * vnoise(u * 1.0 + Vector((1.3, 4.1, 2.9)), .7, self.salt) - 1) + .06 * (2 * vnoise(u * 2.6, .55, self.salt + 3) - 1)
            p = Vector((u.x * self.ax * f, u.y * self.ay * f, u.z * self.az * f))
            for n, frac in self.planes:
                rn = math.sqrt((n.x * self.ax) ** 2 + (n.y * self.ay) ** 2 + (n.z * self.az) ** 2)
                d = frac * rn; s = p.dot(n)
                if s > d:
                    p = p - n * (s - d)
            p = Matrix.Rotation(self.yaw, 3, 'Z') @ p + Vector((0, 0, self.z0))
            out.append(p)
        return out, uf

    def emit(self, lod):
        g = L.Geo()
        P, uf = self.verts(lod)
        keep = [f for f in uf if max(P[i].z for i in f) > ROOT_Z]
        used = sorted({i for f in keep for i in f}); remap = {o: n for n, o in enumerate(used)}
        verts = [Vector((P[o].x, P[o].y, max(P[o].z, ROOT_Z))) for o in used]
        faces = [tuple(remap[i] for i in f) for f in keep]
        cen = Vector((0, 0, self.top * .35))
        faces = [f if (verts[f[1]] - verts[f[0]]).cross(verts[f[2]] - verts[f[0]]).dot(sum((verts[i] for i in f), Vector()) / 3 - cen) >= 0 else tuple(reversed(f)) for f in faces]
        rad = [(p - cen).normalized() for p in verts]
        i0 = g.add(verts, faces, (0, 0, 0), [(p.x, p.y) for p in verts], 0, rad)
        H = self.top
        # S1b: moss cap on the top third as a fine mottle, wet dark lower quarter, base (.19,.20,.18)
        moss_w = lambda i: smoothstep(.60 * H, .72 * H, g.v[i].z) * smoothstep(-.1, .35, g.r[i].z)
        wet_w = lambda i: 1 - smoothstep(.20 * H, .30 * H, g.v[i].z)
        masks = paint(g, range(i0, i0 + len(verts)), BOULDER, [
            dict(name='moss', colour=COB_MOSS, coverage=self.moss_cov, weight=moss_w, freq=20.0, noise=.35, edge_noise=.40, edge_scale=.06, soft=.35, strength=.95, seed=int(self.salt) + 2),
            dict(name='wet', colour=BOULDER_WET, coverage=.97, weight=wet_w, freq=3.0, noise=.3, edge_noise=.3, edge_scale=.2, soft=.25, seed=int(self.salt) + 4)],
            jitter=.07, mottle=.12, mscale=.12, tag=self.a['asset'])
        relief(g, masks['moss'], .012)
        return g

    def make_hulls(self, name, coll):
        P, uf = self.verts(1)
        pts = [Vector((p.x, p.y, max(p.z, ROOT_Z))) for p in P if p.z > ROOT_Z - .5]
        return [hull_from_points('UCX_%s_00' % name, pts, coll)]


# ================================================================ asset dispatch

class KiokioWrap:
    def __init__(self, a, rng):
        self.D = kiokio(a, rng); self.a = a; self.note = self.D.note

    def emit(self, lod):
        g, _ = B.emit(self.D, lod, self.a['budget'][lod])
        return g


DESIGNS = {'Kiokio': KiokioWrap, 'Log': LogDesign, 'Stump': StumpDesign, 'MossHummock': HummockDesign, 'CobbleCluster': ClusterDesign,
           'CobbleBar': BarDesign, 'Driftwood': DriftwoodDesign, 'LogJam': LogJamDesign, 'Boulder': BoulderDesign}


def build_asset(a, mats, coll):
    seed = seed_of(a)
    rng = random.Random(seed)
    D = DESIGNS[a['family']](a, rng)
    obs = []; rows = []; hs = []
    PAINTSTAT.clear()
    for lod in range(3):
        CUR_LOD[0] = lod
        g = D.emit(lod)
        ground(g)
        name = '%s_LOD%d' % (a['asset'], lod)
        ob, dropped = L.to_object(g, name, mats, a['slots'], coll)
        n = len(ob.data.loop_triangles)
        print('LOD', name, n, 'of', a['budget'][lod], 'size', [round(x, 2) for x in ob.dimensions], 'dropped', dropped)
        assert n <= a['budget'][lod], '%s: %d triangles over the LOD%d ceiling %d' % (name, n, lod, a['budget'][lod])
        ob['kit'] = L.KIT; ob['lod'] = lod; ob['seed'] = seed
        ob['placement'] = 'Ground pivot at the origin; buried parts stop 6 cm below ground.' + (' Convex UCX hulls in the LOD0 FBX.' if a['hulls'] else ' No collision.')
        hh = []
        if lod == 0 and a['hulls']:
            hh = D.make_hulls(name, coll)
            assert len(hh) == a['hulls'], (a['asset'], len(hh))
            hs = hh
        L.export(ob, hh)
        extra = dict(dropped_degenerate_faces=dropped)
        extra.update(getattr(D, 'note', {}) or {})
        if hasattr(D, 'cobs') and getattr(D, 'last', None):
            extra.update(cobbles_designed=len(D.cobs), cobbles_kept=len(D.last[1]))
        rows.append(L.manifest_row(ob, a['asset'], a['family'], a['variant'], lod, a['slots'], seed, g.counts, len(hh), a['budget'][lod], extra))
        obs.append(ob)
    for i in range(2):
        assert rows[i]['triangles'] > rows[i + 1]['triangles'], (a['asset'], [r['triangles'] for r in rows])
    print('BUILT', a['asset'], [r['triangles'] for r in rows], rows[0]['size_m'], 'hulls', len(hs), 'minz', [r['min_z_m'] for r in rows])
    if PAINTSTAT:
        print('PAINTSTAT', a['asset'], ' '.join('%s=%.1f%%' % (k.split('@')[0], 100.0 * v[0] / max(1, v[1])) for k, v in sorted(PAINTSTAT.items())))
    return obs, rows, hs


# ================================================================ review renders

ROW1 = ['SM_NZ_Log_A', 'SM_NZ_Log_B', 'SM_NZ_Driftwood_A', 'SM_NZ_LogJam', 'SM_NZ_Stump_A', 'SM_NZ_Kiokio_B']
ROW2 = ['SM_NZ_Kiokio_A', 'SM_NZ_MossHummock_A', 'SM_NZ_MossHummock_B', 'SM_NZ_Cobble_Cluster_S', 'SM_NZ_Cobble_Cluster_M', 'SM_NZ_Cobble_Cluster_L',
        'SM_NZ_CobbleBar', 'SM_NZ_Boulder_A', 'SM_NZ_Boulder_B']
FIGURE_FOR = {'SM_NZ_Log_A', 'SM_NZ_Log_B', 'SM_NZ_Stump_A', 'SM_NZ_Driftwood_A', 'SM_NZ_LogJam', 'SM_NZ_Boulder_A', 'SM_NZ_Kiokio_A', 'SM_NZ_Kiokio_B'}


def floor_lineup(lod0, labels):
    """All meshes at true scale in two rows (large wood and the big fern; then the small things), labels,
    1.8 m figure posts at each row's ends. Orthographic from the front, 14 degrees down."""
    scene = L.review_scene('Floor Lineup')
    ink = L.flat_material('Review | Ink', (.70, .78, .70), .8); muted = L.flat_material('Review | Secondary', (.44, .53, .47), .8)
    chalk = L.flat_material('Review | Chalk', (.19, .225, .21)); fig = L.flat_material('Review | Figure', (.55, .36, .16))
    L.floor(scene, chalk, 600, location=(0, -12))
    tilt = D2R(14)
    rot_txt = (math.pi / 2 - tilt, 0, 0)
    width = 0.0
    for names, y0 in ((ROW1, 0.0), (ROW2, -22.0)):
        x = 0.0
        L.figure(scene, (x, y0, 0), mat=fig); x += 1.7
        for name in [n for n in names if n in lod0]:
            ob = lod0[name]; lo, hi = B.bbox(ob)
            w = max(hi.x - lo.x, 3.6)
            mid = x + w / 2
            L.display_copy(scene, ob, name.replace('SM_NZ_', 'Lineup_'), (mid - (lo.x + hi.x) / 2, y0 - (lo.y + hi.y) / 2, 0))
            L.text_obj(scene, labels[name], (mid, y0 - 2.6, 0), .52, ink, rot_txt)
            L.text_obj(scene, '%.2f x %.2f x %.2f m' % (hi.x - lo.x, hi.y - lo.y, hi.z), (mid, y0 - 4.5, 0), .36, muted, rot_txt)
            x += w + .8
        L.figure(scene, (x + .1, y0, 0), mat=fig)
        width = max(width, x + 1.2)
    L.text_obj(scene, 'GRAND TOUR / NATIVE PLANTS / SOUTHLAND BUSH FLOOR AND RIVER', (.4, 7.0, 4.0), 1.0, ink, rot_txt, 'LEFT')
    L.text_obj(scene, 'S1   15 MESHES   TRUE SCALE   MODELLED GEOMETRY   THREE LODS   POSTS 1.8 M   HEIGHTS ABOVE GROUND', (.4, 7.0, 2.8), .55, muted, rot_txt, 'LEFT')
    L.studio_lights(scene, Vector((width / 2, -11, 0)), 3.6)
    target = Vector((width / 2, -2.0, 0))
    L.camera(scene, target + Vector((0, -math.cos(tilt), math.sin(tilt))) * 120, target, ortho=width + 1.5)
    return scene, width


def append_bush(names):
    """Bush-kit LOD0 meshes appended (not rebuilt) from GrandTour_NativePlants.blend."""
    src = OUT / 'GrandTour_NativePlants.blend'
    assert src.exists(), 'GrandTour_NativePlants.blend (bush set) is missing'
    with bpy.data.libraries.load(str(src), link=False) as (dfrom, dto):
        dto.objects = [n for n in names if n in dfrom.objects]
    return {o.name.split('_LOD0')[0]: o for o in dto.objects if o is not None}


def overcast_world(scene, name, exposure=1.8):
    w = bpy.data.worlds.new(name); w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (.75, .80, .85, 1); bg.inputs[1].default_value = 1.0
    scene.world = w
    scene.view_settings.exposure = exposure


def terrain_grid(scene, name, xs, ys, zfn, cfn, mat):
    """A heightfield on the (non-uniform) grid xs x ys: zfn(x, y) -> (z, tag, u), cfn(x, y, z, tag, u) -> linear
    colour (point attribute `Color`, read by the vertex-colour material). Smooth shaded."""
    verts = []; cols = []
    for y in ys:
        for x in xs:
            z, tag, u = zfn(x, y)
            verts.append((x, y, z)); cols.append(cfn(x, y, z, tag, u))
    nx = len(xs); ny = len(ys)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    ca = me.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='POINT')
    flat = []
    for c in cols:
        flat.extend((c[0], c[1], c[2], 1.0))
    ca.data.foreach_set('color', flat)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    return ob


def assembly_river(lod0):
    """River reach, x 4..50, along +x. Water level z = -0.45; the NEAR bank (y < near lip, ~3 m) is 0.45 m above
    the water with a cut earth face and a moss top; the FAR bank (y > far lip, ~9.8 m) is 0.30 m above it. A
    low sand-and-cobble spit leaves the near bank at x ~ 9-17. Seen from the near bank at eye height 1.6 m, 35 mm,
    overcast, exposure 1.8 (the kit's). Crown ferns, tree ferns, the backdrop poles and the two beech are the bush
    kit's LOD0 meshes appended from GrandTour_NativePlants.blend (not rebuilt); the rest is this set's."""
    bush = append_bush(['SM_NZ_CrownFern_A_LOD0', 'SM_NZ_CrownFern_B_LOD0', 'SM_NZ_CrownFern_C_LOD0', 'SM_NZ_TreeFern_A_LOD0', 'SM_NZ_TreeFern_B_LOD0',
                        'SM_NZ_Beech_Pole_LOD0', 'SM_NZ_Beech_Edge_LOD0', 'SM_NZ_Beech_Mature_LOD0'])
    have = dict(lod0); have.update(bush)
    scene = L.review_scene('River Assembly')
    overcast_world(scene, 'NZ River Overcast', 1.8)
    rng = random.Random(57000 + 9001)
    earth = L.material('Assembly | Bank earth', (.05, .045, .025))
    earth.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .95
    water = L.flat_material('Assembly | Tannin water', (.045, .028, .012), roughness=.05)
    water.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = .6
    try:
        # fine grain (luminance only: a grey multiply) and a little bump from one noise, so the bank is not a smooth painted sheet
        nt = earth.node_tree
        vc = next(n for n in nt.nodes if n.type == 'VERTEX_COLOR'); bsdf = nt.nodes['Principled BSDF']
        tc = nt.nodes.new('ShaderNodeTexCoord'); tex = nt.nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 26.0; tex.inputs['Detail'].default_value = 9.0; tex.inputs['Roughness'].default_value = .65
        nt.links.new(tc.outputs['Object'], tex.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = .28; mr.inputs['From Max'].default_value = .72; mr.inputs['To Min'].default_value = .62; mr.inputs['To Max'].default_value = 1.38
        nt.links.new(tex.outputs['Fac'], mr.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs[0].default_value = 1.0
        ia = next(i for i in mx.inputs if i.identifier == 'A_Color'); ib = next(i for i in mx.inputs if i.identifier == 'B_Color')
        nt.links.new(vc.outputs['Color'], ia); nt.links.new(mr.outputs['Result'], ib)
        nt.links.new(next(o for o in mx.outputs if o.identifier == 'Result_Color'), bsdf.inputs['Base Color'])
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .5; bp.inputs['Distance'].default_value = .03
        nt.links.new(tex.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    except Exception as e:
        print('NOTE terrain grain nodes skipped:', e)

    ZW = -.45; ZBED = ZW - .30; ZS = ZW + .15          # water level, hidden bed, spit top
    RN, RF = .34, .30                                  # horizontal run of the near / far cut faces
    nl = lambda x: 3.0 + .9 * math.sin(.29 * x + .6) + .45 * math.sin(.77 * x + 2.0)      # near lip (y)
    fl = lambda x: 9.8 + .8 * math.sin(.23 * x + 1.7) + .40 * math.sin(.71 * x + .4)      # far lip (y)
    SX, SHX, SHY = 11.8, 5.4, 2.3                      # spit: centre x, half length, half width
    sy = lambda: nl(SX) + 1.1
    P3 = lambda x, y: Vector((x, y, 0))

    def fn(x, y, scale, salt):
        """Two value-noise octaves on rotated domains: no visible lattice (a plain vnoise shows rectangles)."""
        a_, b_ = x * .8 + y * .6, -x * .6 + y * .8
        return .6 * vnoise(Vector((a_, b_, 0)), scale, salt) + .4 * vnoise(Vector((b_ + 3.1, -a_ + 1.7, 0)), scale * .53, salt + 5.0)

    def zfn(x, y):
        a, b = nl(x), fl(x)
        n = vnoise(P3(x, y), .9, 2.0) * 2 - 1
        if y < a:                                      # near bank top
            z = .03 * n + .02 * math.sin(x * .8) * math.sin(y * .6) + .09 * (vnoise(P3(x, y), 2.6, 5.0) * 2 - 1) + .04 * (vnoise(P3(x, y), .9, 6.0) * 2 - 1)
            tag, u = 'top_n', 0.0
        elif y < a + RN:                               # near cut face (rounded lip and toe)
            u = (y - a) / RN
            z = lerp(.03 * n, ZBED, smoothstep(0, 1, u)); tag = 'face_n'
        elif y < b - RF:                               # channel (under the water plane)
            z = ZBED + .04 * n; tag, u = 'bed', 0.0
        elif y < b:                                    # far cut face
            u = (b - y) / RF
            z = lerp(ZW + .30 + .03 * n, ZBED, smoothstep(0, 1, u)); tag = 'face_f'
        else:                                          # far bank top, then the forest floor rising gently
            z = ZW + .30 + .03 * n + .035 * (y - b) + .5 * smoothstep(13, 30, y) + .09 * (vnoise(P3(x, y), 2.6, 5.0) * 2 - 1) + .04 * (vnoise(P3(x, y), .9, 6.0) * 2 - 1)
            tag, u = 'top_f', 0.0
        rho = math.hypot((x - SX) / SHX, (y - sy()) / SHY)
        m = 1 - smoothstep(.62, 1.0, rho)
        zsp = lerp(ZBED, ZS, m) + (.006 * n if m > .99 else 0.0)
        if m > .02 and zsp > z:
            z = zsp; tag = 'spit'
        return z, tag, u

    SPITSTAT = [0, 0]

    def cfn(x, y, z, tag, u):
        n1 = fn(x, y, .45, 3.0); n2 = fn(x, y, .13, 7.0); n3 = fn(x, y, 1.4, 11.0)
        lum = .85 + .30 * (n1 * .6 + n2 * .4)          # luminance only, .85-1.15
        if tag in ('top_n', 'top_f'):
            mw = smoothstep(.34, .52, n3 * .5 + n1 * .5)
            c = mix((.034, .026, .018), (.050, .078, .030), .15 + .85 * mw)      # moss over earth and litter
            return tuple(v * lum for v in c)
        if tag in ('face_n', 'face_f'):
            c = (.09, .07, .05)
            c = mix(c, (.050, .078, .030), .65 * (1 - smoothstep(0, .20, u)))     # moss drapes over the lip
            if z < ZW + .08:
                c = tuple(v * .6 for v in c)                                      # wet at the waterline
            return tuple(v * lum for v in c)
        if tag == 'spit':
            sand = smoothstep(.67, .73, fn(x, y, .8, 21.0))
            SPITSTAT[0] += 1 if sand > .5 else 0; SPITSTAT[1] += 1
            c = mix((.055, .047, .040), SAND, .9 * sand)
            if z < ZW + .07:
                c = tuple(v * .65 for v in c)
            return tuple(v * lum for v in c)
        return tuple(v * lum for v in (.035, .03, .022))
    xs = [4.0 + .2 * i for i in range(int(round((50.0 - 4.0) / .2)) + 1)]
    ys = [-12 + .8 * i for i in range(9)] + [-5.4 + .2 * i for i in range(27)] + [.1 * i for i in range(1, 116)] + [11.5 + .6 * i for i in range(1, 38)]
    terrain_grid(scene, 'Banks', xs, ys, zfn, cfn, earth)
    print('SPIT sand patches: %.1f %% of the spit terrain vertices' % (100.0 * SPITSTAT[0] / max(1, SPITSTAT[1])))
    me = bpy.data.meshes.new('Water'); me.from_pydata([(0, -2, ZW), (54, -2, ZW), (54, 14, ZW), (0, 14, ZW)], [], [(0, 1, 2, 3)]); me.materials.append(water)
    scene.collection.objects.link(bpy.data.objects.new('Water', me))
    counts = {}

    def H(x, y):
        return zfn(x, y)[0]

    def put(name, x, y, yaw=None, sc=1.0, z=None, lean=None):
        """lean = (dx, dy, angle): tip the object about its ground point toward (dx, dy)."""
        if name not in have:
            return None
        yaw = rng.uniform(0, math.tau) if yaw is None else yaw
        zz = H(x, y) if z is None else z
        o = L.display_copy(scene, have[name], name.replace('SM_NZ_', 'River_') + '_%03d' % counts.get(name, 0), (x, y, zz), yaw, sc)
        if lean:
            d = Vector((lean[0], lean[1], 0)).normalized()
            R = Matrix.Rotation(lean[2], 3, Vector((-d.y, d.x, 0))) @ Matrix.Rotation(yaw, 3, 'Z')
            o.rotation_euler = R.to_euler('XYZ')
        counts[name] = counts.get(name, 0) + 1
        return o
    # the spit: two cobble bars and three clusters on the sand-and-cobble plateau
    zsp = ZS
    put('SM_NZ_CobbleBar', 9.9, sy() - .1, .25, 1.0, zsp); put('SM_NZ_CobbleBar', 13.7, sy() + .2, -.2, 1.0, zsp)
    put('SM_NZ_Cobble_Cluster_L', 11.9, sy() - 1.1, None, 1.0, zsp); put('SM_NZ_Cobble_Cluster_M', 16.0, sy() - .1, None, 1.0, zsp); put('SM_NZ_Cobble_Cluster_S', 7.9, sy() + .3, None, 1.0, zsp)
    # boulders A and B stand in the water off the near bank
    put('SM_NZ_Boulder_A', 9.0, 5.7, None, 1.0, ZW - .10); put('SM_NZ_Boulder_B', 16.9, 5.2, None, 1.0, ZW - .10)
    # the far water line: the log jam lodged across the lip, the driftwood on the toe
    put('SM_NZ_LogJam', 15.6, fl(15.6) - .15, 0.0, 1.0, ZW + .16)
    put('SM_NZ_Driftwood_A', 22.6, fl(22.6) - .45, -.35, 1.0, ZW + .12)
    # kiokio x8, four on each bank top, leaning over the edge
    for k, x in enumerate((6.6, 8.6, 19.4, 22.4)):
        x += rng.uniform(-.2, .2)
        put('SM_NZ_Kiokio_B' if k % 2 else 'SM_NZ_Kiokio_A', x, nl(x) - .30, None, rng.uniform(1.0, 1.15), lean=(0, 1, D2R(rng.uniform(14, 20))))
    for k, x in enumerate((12.4, 17.2, 19.9, 24.0)):
        x += rng.uniform(-.3, .3)
        put('SM_NZ_Kiokio_A' if k % 2 else 'SM_NZ_Kiokio_B', x, fl(x) + .30, None, rng.uniform(1.0, 1.15), lean=(0, -1, D2R(rng.uniform(14, 20))))
    # crown ferns x25: the far bank top (16) and the near bank top (9)
    n = 0
    while n < 16:
        x = rng.uniform(10.5, 31.0); y = fl(x) + rng.uniform(.9, 3.6)
        put(('SM_NZ_CrownFern_A', 'SM_NZ_CrownFern_B', 'SM_NZ_CrownFern_C')[n % 3], x, y, None, rng.uniform(.95, 1.3)); n += 1
    n = 0
    while n < 9:
        x = rng.uniform(15.0, 28.0) if n % 3 else rng.uniform(5.6, 7.0); y = nl(x) - rng.uniform(.9, 2.6)
        put(('SM_NZ_CrownFern_B', 'SM_NZ_CrownFern_C', 'SM_NZ_CrownFern_A')[n % 3], x, y, None, rng.uniform(.9, 1.2)); n += 1
    # tree ferns x2 at the far bank
    put('SM_NZ_TreeFern_A', 20.8, fl(20.8) + 2.3, rng.uniform(0, math.tau), 1.05)
    put('SM_NZ_TreeFern_B', 12.6, fl(12.6) + 3.4, rng.uniform(0, math.tau), .95)
    # two beech whose limbs overhang the water (local +x is the long limb side of Beech_Edge)
    put('SM_NZ_Beech_Edge', 11.6, fl(11.6) + 1.6, D2R(-100), .85)
    put('SM_NZ_Beech_Edge', 28.5, nl(28.5) - 1.2, D2R(95), .95)
    # moss hummocks along both lips (the near bank top is the foreground: more of them)
    for k in range(16):
        if k < 10:
            x = rng.uniform(16.5, 27.0) if k % 5 else rng.uniform(5.5, 6.6)
            put('SM_NZ_MossHummock_B' if k % 2 else 'SM_NZ_MossHummock_A', x, nl(x) - rng.uniform(.5, 2.2), None, rng.uniform(.9, 1.3))
        else:
            x = rng.uniform(10.0, 28.0)
            put('SM_NZ_MossHummock_A' if k % 2 else 'SM_NZ_MossHummock_B', x, fl(x) + rng.uniform(.5, 1.6), None, rng.uniform(.9, 1.3))
    # the stand: Beech_Mature canopy trees on a jittered 5.5 m grid on both banks, set back 4 m from the lips, so the
    # corridor closes overhead like the kit's own stand (open overcast sky at exposure 1.8 washes everything out);
    # bush-kit poles fill between them behind the far bank
    nmat = 0
    keep = [(15.6, fl(15.6), 3.2), (22.6, fl(22.6), 2.4), (20.8, fl(20.8) + 2.3, 2.5), (12.6, fl(12.6) + 3.4, 2.8), (11.6, fl(11.6) + 1.6, 2.2)]
    for i in range(14):
        xb = -6 + i * 5.5
        for dy, off in ((2.2, 0.0), (8.0, 2.7), (14.0, 0.0), (20.5, 2.7)):                        # far bank rows (the first stands at the lip)
            x = xb + off + rng.uniform(-1.2, 1.2); y = fl(x) + dy + rng.uniform(-.8, .8)
            if any(math.hypot(x - kx, y - ky) < kr + .9 for kx, ky, kr in keep):
                continue
            put('SM_NZ_Beech_Mature', x, y, None, rng.uniform(.9, 1.08)); nmat += 1
        for dy in (1.0, 7.5, 13.0):                                                                # near bank rows
            x = xb + rng.uniform(-1.2, 1.2)
            if dy < 5 and 1.0 < x < 17.0:
                continue                                                                           # keep the view across the spit clear
            put('SM_NZ_Beech_Mature', x, nl(x) - dy - rng.uniform(0, .9), None, rng.uniform(.9, 1.08)); nmat += 1
    for row, (y0, y1) in enumerate(((14.5, 17.0), (18.5, 22.0), (23.5, 28.0), (30.0, 40.0))):
        for i in range(int(40 / (1.8 + row * .9))):
            put('SM_NZ_Beech_Pole', 6 + i * (1.8 + row * .9) + rng.uniform(-.6, .6), rng.uniform(y0, y1), None, rng.uniform(.95, 1.1))
    L.studio_lights(scene, (18, 6, 0), 2.6, energy=.5)
    eye = Vector((5.0, -1.2, 1.6))
    L.camera(scene, eye, Vector((14.5, 6.2, 1.0)), lens=35)
    print('RIVER ASSEMBLY', counts)
    return scene


def assembly_floor(lod0):
    """20 x 20 m bush floor along a 1.6 m dark peat track (x -10..10, y 0..20), 35 mm at 1.6 m looking along
    the track, overcast. The wood, stump and hummocks are this set's; crown ferns and Beech_Pole are the bush
    kit's LOD0 meshes (appended, not rebuilt); the poles beyond the square are backdrop only."""
    bush = append_bush(['SM_NZ_CrownFern_A_LOD0', 'SM_NZ_CrownFern_B_LOD0', 'SM_NZ_CrownFern_C_LOD0', 'SM_NZ_Beech_Pole_LOD0', 'SM_NZ_Beech_Mature_LOD0'])
    have = dict(lod0); have.update(bush)
    scene = L.review_scene('Floor Assembly')
    overcast_world(scene, 'NZ Floor Overcast', 1.8)
    rng = random.Random(57000 + 9002)
    peat = L.flat_material('Assembly | Peat', (.040, .031, .022), roughness=.92)
    track = L.flat_material('Assembly | Wet peat track', (.018, .014, .010), roughness=.62)
    L.floor(scene, peat, 600, z=-.004, location=(0, 30))
    xt = lambda y: 1.6 * (math.sin(y / 5.5 + .7) - math.sin(.7)) + .35 * (math.sin(y / 2.3 + 2.1) - math.sin(2.1))
    verts = []; faces = []
    ys = [-3 + i * .5 for i in range(62)]
    for i, y in enumerate(ys):
        c = xt(y); verts += [(c - .8 + .08 * math.sin(y * 1.7), y, 0), (c + .8 + .07 * math.sin(y * 1.3 + 1), y, 0)]
        if i:
            a = 2 * (i - 1); faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new('Peat track 1.6 m'); me.from_pydata(verts, [], faces); me.materials.append(track)
    scene.collection.objects.link(bpy.data.objects.new(me.name, me))
    counts = {}
    placed = []

    def put(name, x, y, yaw=None, sc=1.0, r=0.0, tilt=(0, 0)):
        if name not in have:
            return
        yaw = rng.uniform(0, math.tau) if yaw is None else yaw
        o = L.display_copy(scene, have[name], name.replace('SM_NZ_', 'Floor_') + '_%03d' % counts.get(name, 0), (x, y, 0), yaw, sc)
        o.rotation_euler = (tilt[0], tilt[1], yaw)
        counts[name] = counts.get(name, 0) + 1
        placed.append((x, y, r))
    # the wood and the stump on the stand's floor, off the track and in front of the camera
    put('SM_NZ_Log_A', -2.7 + xt(10.5), 10.5, -.30, 1.0, 3.9)
    put('SM_NZ_Log_B', 2.5 + xt(7.2), 7.2, .45, 1.0, 2.4)
    put('SM_NZ_Stump_A', 2.7 + xt(12.8), 12.8, None, 1.0, 1.1)
    for (dx, y) in ((-1.9, 4.0), (1.8, 9.6), (-1.6, 7.6), (3.2, 15.0), (-1.9, 14.2), (1.7, 3.2)):
        put('SM_NZ_MossHummock_A' if y < 10 else 'SM_NZ_MossHummock_B', dx + xt(y), y, None, rng.uniform(.95, 1.15), .9)
    for (dx, y) in ((-5.0, 11.0), (5.0, 13.5), (-3.0, 18.5)):
        put('SM_NZ_Beech_Pole', dx + xt(y), y, None, rng.uniform(.95, 1.08), .25)
    # 40 crown ferns as one continuous understory with clumps and gaps: accepted by a smooth density field over the
    # whole floor (not massed on two flanks), the track kept clear, thinning gently toward the far sides
    def dens(x, y):
        q = .6 * vnoise(Vector((x * .8 + y * .6, -x * .6 + y * .8, 0)), 3.0, 41.0) + .4 * vnoise(Vector((y * .9 - x * .4 + 7, x * .9 + y * .4, 0)), 1.5, 43.0)
        return smoothstep(.40, .60, q)
    nf = 0; tries = 0
    while nf < 40 and tries < 60000:
        tries += 1
        y = rng.uniform(.8, 19.0); x = rng.uniform(-9.0, 9.0)
        dx = abs(x - xt(y))
        if dx < .95 or any((x - a) ** 2 + (y - b) ** 2 < (r_ + .5) ** 2 for a, b, r_ in placed):
            continue
        if rng.random() > dens(x, y) * (1 - .55 * smoothstep(3.0, 9.0, dx)):
            continue
        pick = rng.random()
        put('SM_NZ_CrownFern_A' if pick < .25 else 'SM_NZ_CrownFern_B' if pick < .65 else 'SM_NZ_CrownFern_C', x, y, None, rng.uniform(1.0, 1.35), .6,
            tilt=(D2R(rng.uniform(0, 7)) * math.cos(y), D2R(rng.uniform(0, 7)) * math.sin(x)))
        nf += 1
    # 30 small twig sticks (3-sided tubes, 2-4 cm across), most of them on or across the track
    twig = L.flat_material('Assembly | Twig', (.12, .09, .06), roughness=.9)
    for k in range(30):
        ln = rng.uniform(.25, .75); r = rng.uniform(.01, .02)
        y = rng.uniform(1.2, 17.0)
        x = xt(y) + (rng.uniform(-.7, .7) if k < 19 else rng.choice((-1, 1)) * rng.uniform(.9, 2.6))
        g = L.Geo()
        pts = [Vector((-ln / 2, 0, r)), Vector((0, rng.uniform(-.04, .04), r * 1.1)), Vector((ln / 2, rng.uniform(-.05, .05), r))]
        L.tube(g, pts, [r, r * .9, r * .55], 3, (0, 0, 0), 0, (False, True), 0.0)
        me = bpy.data.meshes.new('Twig'); me.from_pydata([tuple(v) for v in g.v], [], g.f); me.materials.append(twig)
        for pl in me.polygons:
            pl.use_smooth = False
        ob = bpy.data.objects.new('Floor_Twig_%02d' % k, me); scene.collection.objects.link(ob)
        ob.location = (x, y, 0); ob.rotation_euler = (0, 0, rng.uniform(0, math.tau))
    # three dark puddle discs on the track
    puddle = L.flat_material('Assembly | Puddle', (.04, .04, .035), roughness=.04)
    for k, y in enumerate((4.6, 8.9, 13.4)):
        rx, ry = rng.uniform(.55, .75), rng.uniform(.30, .45)
        cx = xt(y) + rng.uniform(-.2, .2); an = math.atan2(xt(y + 1) - xt(y), 1.0) * 0 + rng.uniform(-.3, .3)
        ring = [(cx + rx * math.cos(t) * math.cos(an) - ry * math.sin(t) * math.sin(an), y + rx * math.cos(t) * math.sin(an) + ry * math.sin(t) * math.cos(an), .006)
                for t in [math.tau * i / 28 for i in range(28)]]
        me = bpy.data.meshes.new('Puddle %d' % k); me.from_pydata(ring, [], [tuple(range(28))]); me.materials.append(puddle)
        for pl in me.polygons:
            pl.use_smooth = True
        scene.collection.objects.link(bpy.data.objects.new(me.name, me))
    # the stand: poles and a few Beech_Mature on a jittered 2.7 m grid over the whole square (not on the track or the
    # wood), as in the kit's own stand, so the floor is shaded like it (open sky at exposure 1.8 makes the peat grey)
    trunks = []
    for i in range(9):
        for j in range(8):
            x = -10.8 + 2.4 * (i + .5) + rng.uniform(-.5, .5); y = 1.6 + 2.4 * (j + .5) + rng.uniform(-.5, .5)
            r = rng.random()
            if abs(x - xt(y)) < 1.35 or any((x - a) ** 2 + (y - b) ** 2 < (r_ + .7) ** 2 for a, b, r_ in placed):
                continue
            put('SM_NZ_Beech_Mature' if r < .35 else 'SM_NZ_Beech_Pole', x, y, None, rng.uniform(.92, 1.08), .35)
            trunks.append((x, y))
    # backdrop poles outside the square: a stand to the horizon
    for row in range(14):
        y0 = 21.0 + row * 3.4
        for i in range(24):
            put('SM_NZ_Beech_Mature' if rng.random() < .28 else 'SM_NZ_Beech_Pole', -34 + i * 3.0 + rng.uniform(-.9, .9), y0 + rng.uniform(-1.0, 1.0), None, rng.uniform(.95, 1.1), 0)
    for i in range(14):
        for side in (-1, 1):
            put('SM_NZ_Beech_Pole', side * (11.5 + rng.uniform(0, 5)), 1.5 + i * 1.6 + rng.uniform(-.5, .5), None, rng.uniform(.95, 1.1), 0)
    L.studio_lights(scene, (0, 10, 0), 2.6, energy=.5)
    y0 = .7
    eye = Vector((xt(y0), y0, 1.6)); ahead = Vector((xt(y0 + 8) - xt(y0), 8, 0)).normalized()
    L.camera(scene, eye, eye + ahead * 10 + Z * 10 * math.tan(D2R(9)), lens=35)
    print('FLOOR ASSEMBLY', counts)
    return scene


def render_detail(scene, ob, name, path, fig_mat, fig_at=None, k=None):
    """Three-quarter close view, framed like build_native_bush.render_detail but with a distance factor `k`
    that keeps the ends of long objects (logs, driftwood, the log jam) inside the frame."""
    for o in list(scene.collection.objects):
        if o.get('detail_item') or o.type in {'CAMERA', 'LIGHT'}:
            bpy.data.objects.remove(o, do_unlink=True)
    c = L.display_copy(scene, ob, 'Detail_' + name.replace('SM_NZ_', '')); c['detail_item'] = True
    lo, hi = B.bbox(ob)
    small = hi.z < 1.5
    if fig_at is not None:
        fx, fy = fig_at
        f = L.figure(scene, (fx, fy, 0), mat=fig_mat); f['detail_item'] = True
        lo = Vector((min(lo.x, fx - .3), lo.y, lo.z)); hi = Vector((hi.x, hi.y, max(hi.z, 1.8)))
    centre = (lo + hi) / 2
    rad = (hi - lo).length / 2
    el = D2R(30 if small else 16)
    az = D2R(-45)
    back = Vector((math.sin(-az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    right = Z.cross(back).normalized(); up = back.cross(right).normalized()
    th = 36 / 2 / 50; tv = (36 * 1200 / 1400) / 2 / 50
    d = 0.0
    for cx in (lo.x, hi.x):
        for cy in (lo.y, hi.y):
            for cz in (lo.z, hi.z):
                q = Vector((cx, cy, cz)) - centre
                d = max(d, q.dot(back) + abs(q.dot(right)) / th, q.dot(back) + abs(q.dot(up)) / tv)
    longest = max(hi.x - lo.x, hi.y - lo.y)
    k = k if k is not None else (1.0 if longest > 3.0 else .86)
    L.camera(scene, centre + back * d * k, centre, lens=50)
    L.studio_lights(scene, Vector((centre.x, centre.y, 0)), max(.35, rad / 6))
    L.render(scene, path, 1400, 1200)
    return path


def render_all(lod0, labels, assets, only, no_assembly, t0):
    renders = []
    if only is None and not ASM_ONLY:
        s1, width = floor_lineup(lod0, labels)
        renders.append(L.render(s1, OUT / 'Lineup_Floor.png', 2000, int(2000 * 15.0 / (width + 1.5)) + 40))
        print('RENDERED Lineup', '%.1fs' % (time.time() - t0))
    s2 = B.detail_scene(); s2.name = 'Floor Detail'
    fig = L.flat_material('Review | Figure', (.55, .36, .16))
    for a in ([] if ASM_ONLY else assets):
        nm = a['asset'].replace('SM_NZ_', '')
        lo, hi = B.bbox(lod0[a['asset']])
        renders.append(render_detail(s2, lod0[a['asset']], a['asset'], OUT / ('Detail_%s.png' % nm), fig,
                                     fig_at=((lo.x - .6, (lo.y + hi.y) / 2) if a['asset'] in FIGURE_FOR else None)))
        print('RENDERED Detail', nm, '%.1fs' % (time.time() - t0))
    if only is None and not no_assembly:
        s3 = assembly_river(lod0)
        renders.append(L.render(s3, OUT / 'Assembly_River.png', 2000, 1333))
        print('RENDERED Assembly_River', '%.1fs' % (time.time() - t0))
        s4 = assembly_floor(lod0)
        renders.append(L.render(s4, OUT / 'Assembly_Floor.png', 2000, 1333))
        print('RENDERED Assembly_Floor', '%.1fs' % (time.time() - t0))
    return renders


# ================================================================ main

def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene; scene.name = 'Native Floor Assets - metres'
    mats = L.plant_materials()
    coll = scene.collection
    lod0 = {}; labels = {}; rows = []
    assets = [a for a in ASSETS if ONLY is None or a['asset'].replace('SM_NZ_', '') in ONLY]
    x = 0.0
    for a in assets:
        obs, r, hs = build_asset(a, mats, coll)
        rows += r
        lo, hi = B.bbox(obs[0])
        x += -lo.x + .5
        obs[0].location = (x, 0, 0)
        for h in hs:
            h.parent = obs[0]
        x += hi.x + 1.5
        for o in obs[1:]:
            o.hide_set(True); o.hide_render = True
        L.mark_asset(obs[0], a['label'] + ' / opaque vertex-colour geometry / 3 LODs', ['Native', 'NZ', a['family'], 'Southland', 'Grand Tour'])
        lod0[a['asset']] = obs[0]
        labels[a['asset']] = a['label']
    if ONLY is None:
        L.write_manifest(rows, set_name='floor', extra=dict(floor_stage='S1', floor_seeds={a['asset']: seed_of(a) for a in assets},
                         floor_lod_rule='one design per asset from seed 57000 + 97 k. Wood (logs, stump, driftwood, log jam): tubes keep every ring column at fewer sides and segments (18/10/6), broken ends and stubs kept at every LOD (stubs with fewer sides), moss colour kept, moss relief shared; hulls UCX convex rings in the LOD0 FBX. Hummocks: one displaced dome at 30/18/8 sectors. Cobbles: clusters keep every cobble and step each one down a detail ladder (icosphere 2/1, dome 8x3/6x2, 4-sided pyramid) with the largest cobbles keeping the finest rung; the bar keeps its shell and drops the smallest cobbles at LOD2 (enlarged 1.55). Boulders: one displaced icosphere at subdivision 3/2/1 clipped at -6 cm. Kiokio: pinnate fronds -> serrated strip -> plain strip'))
        print('MANIFEST', len(rows), 'rows', '%.1fs' % (time.time() - t0))
    else:
        print('PARTIAL RUN (--only): manifest.json left alone')
    renders = []
    if not NO_RENDER:
        renders += render_all(lod0, labels, assets, ONLY, NO_ASSEMBLY, t0)
    try:
        bpy.context.window.scene = bpy.data.scenes['Native Floor Assets - metres']
    except Exception:
        pass
    if ONLY is None:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'GrandTour_NativePlants_Floor.blend'))
    for b in OUT.glob('*.blend1'):
        b.unlink()
    for p in renders:
        print('RENDER', p)
    print('NATIVE_FLOOR_BUILD_OK', len(assets), 'meshes', len(rows), 'lods', '%.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
