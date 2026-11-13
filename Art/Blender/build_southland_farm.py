"""S2a Southland farm hardware (docs/SOUTHLAND_ASSET_PLAN.md) on the native plant kit's pipeline: post-and-wire fence module, strainer
assembly, steel farm gate, cattle stop, culvert with headwall, concrete trough, power pole, road-name sign post, give-way sign, letterbox
and round hay bale (11 meshes) as deterministic Blender geometry, three authored LODs each, FBX (cm) + GLB (m), manifest rows (set 'farm'),
the set .blend and review renders.

Run: blender -b --factory-startup --python-exit-code 1 --python build_southland_farm.py [-- --only X,Y --no-render --no-assembly --assembly-only --lineup-only]
Each asset is designed once from its fixed seed (59000 + 97 k; every random draw is in the design), then emitted at LOD0/1/2 from that one
design, so the RNG is consumed identically at every LOD. These are hard-surface props: the LODs keep every structural member and step
down the sides, the rings along each member and the small fittings (welds, staples, clamps, letters).

Ground rule: the lowest vertex of every mesh sits 6 cm below the ground plane (post roots, the bale and trough bases), except the two
partly buried pieces: the cattle stop (pit and footings, lowest vertex -0.45 m) and the culvert (pipe centre .5 m below the road, headwall
footing -0.90 m); their rows carry `min_z_band` and the validator checks them against it. One material slot `Bark` serves wood, steel and
concrete (vertex colour carries the difference).
"""
import bpy, sys, math, random, json, time
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_plant_lib as L
import build_native_bush as B
import build_southland_floor as F
import build_southland_verge as V
from native_plant_lib import Z, clamp, lerp, mix, scale_col, smoothstep, hnoise, vnoise, perp

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ONLY = set(ARGS[ARGS.index('--only') + 1].split(',')) if '--only' in ARGS else None
NO_RENDER = '--no-render' in ARGS
NO_ASSEMBLY = '--no-assembly' in ARGS
ASM_ONLY = '--assembly-only' in ARGS
LINEUP_ONLY = '--lineup-only' in ARGS
OUT = L.OUT
D2R = math.radians
ROOT_Z = -.06
XV = Vector((1, 0, 0)); YV = Vector((0, 1, 0))

# ---------------------------------------------------------------- colours (linear RGB; dark and desaturated, tint is luminance only)
PINE = (.22, .19, .14); PINE_GREY = (.25, .235, .205); PINE_CCA = (.15, .17, .09); PINE_WET = (.09, .085, .06); PINE_KNOT = (.11, .085, .05)
GALV = (.38, .38, .36); RUST = (.25, .12, .06)
CONC = (.36, .35, .32); CONC_DAMP = (.19, .18, .155); ALGAE = (.09, .15, .055)
PIPE = (.045, .045, .044); PIPE_DUST = (.12, .10, .075)
WATER = (.06, .06, .05)
POLE = (.27, .25, .22); POLE_BASE = (.085, .075, .06); ARM = (.20, .17, .12); INSUL = (.17, .15, .13)
SIGN_GREEN = (.05, .22, .10); LETTER = (.72, .72, .68); SIGN_WHITE = (.80, .80, .78); SIGN_RED = (.55, .05, .04)
BOX_RED = (.30, .06, .05)
STRAW = (.42, .36, .20); STRAW_TOP = (.28, .24, .14)
PIT = (.03, .03, .025); EARTH = (.07, .055, .035)

ASSETS = [
    dict(asset='SM_NZ_Fence_4m', family='Fence', variant='4m', label='FENCE 4M', budget=(1200, 400, 120), hulls=1),
    dict(asset='SM_NZ_Strainer', family='Strainer', variant='', label='STRAINER', budget=(1500, 500, 150), hulls=2),
    dict(asset='SM_NZ_Gate_3m6', family='Gate', variant='3m6', label='GATE 3.6 M', budget=(2500, 800, 240), hulls=3),
    dict(asset='SM_NZ_CattleStop', family='CattleStop', variant='', label='CATTLE STOP', budget=(2000, 600, 200), hulls=3, min_z_band=(-.47, -.43)),
    dict(asset='SM_NZ_Culvert', family='Culvert', variant='', label='CULVERT', budget=(1500, 500, 150), hulls=1, min_z_band=(-.92, -.88)),
    dict(asset='SM_NZ_Trough', family='Trough', variant='', label='TROUGH', budget=(900, 300, 90), hulls=1),
    dict(asset='SM_NZ_PowerPole', family='PowerPole', variant='', label='POWER POLE', budget=(1200, 400, 120), hulls=1),
    dict(asset='SM_NZ_SignPost', family='SignPost', variant='', label='ROAD NAME SIGN', budget=(400, 150, 60), hulls=1),
    dict(asset='SM_NZ_GiveWay', family='GiveWay', variant='', label='GIVE WAY SIGN', budget=(400, 150, 60), hulls=1),
    dict(asset='SM_NZ_Letterbox', family='Letterbox', variant='', label='LETTERBOX', budget=(400, 150, 60), hulls=1),
    dict(asset='SM_NZ_HayBale', family='HayBale', variant='', label='HAY BALE', budget=(600, 200, 60), hulls=1),
]
for _k, _a in enumerate(ASSETS):
    _a['k'] = _k


def seed_of(a):
    return 59000 + 97 * a['k']


def tint(c, f):
    return tuple(min(.95, x * f) for x in c)


def lum(p, amt, scale, salt=0.0):
    """Fine irregular luminance mottle: smooth noise at `scale` metres plus a per-position share, +-amt."""
    return 1 + amt * ((2 * vnoise(p, scale, salt) - 1) * .7 + (2 * hnoise(p, salt + 5.0) - 1) * .3)


# ================================================================ colour functions: f(position, normal) -> linear colour

def pine_fn(tv, salt, wet=True, cca=True):
    """Treated pine: grey-brown (.22,.19,.14) with weathered grey patches, dark weathered blotches (a little elongated along the grain) and knots,
    a green CCA tint toward the base and a dark wet band at the ground line with an irregular upper edge."""
    def f(p, n):
        m = lum(p, .18, .16, salt)
        c = tint(PINE, tv * m)
        c = mix(c, tint(PINE_GREY, tv * m), smoothstep(.5, .72, vnoise(p, .30, salt + 2)) * .55)
        c = mix(c, tint(PINE_WET, 1.0), smoothstep(.64, .78, vnoise(Vector((p.x, p.y, p.z * .45)), .07, salt + 14)) * .6)
        c = mix(c, tint(PINE_KNOT, m), smoothstep(.76, .85, vnoise(p, .07, salt + 4)) * .8)
        if cca:
            top = .55 + .4 * (vnoise(p, .25, salt + 6) - .5)
            c = mix(c, tint(PINE_CCA, tv * m), (1 - smoothstep(.05, top, p.z)) * .75)
        if wet:
            edge = .13 + .24 * (vnoise(p, .12, salt + 8) - .5)
            c = mix(c, tint(PINE_WET, m), (1 - smoothstep(edge - .05, edge + .05, p.z)) * .9)
        return c
    return f


def steel_fn(tv, salt, welds=(), low=0.0, under=0.0):
    """Galvanised steel (.38,.38,.36) with dirt and oxidation patches and rust (.25,.12,.06) as irregular blotches: certain within `rad` of the
    weld points, likelier on the lower parts (`low`) and on downward-facing surfaces (`under`), a few specks elsewhere."""
    def f(p, n):
        m = lum(p, .16, .2, salt)
        c = tint(GALV, tv * m)
        c = mix(c, tint((.17, .17, .165), m), smoothstep(.42, .60, vnoise(p, .2, salt + 11)) * .85)
        nz = .6 * vnoise(p, .12, salt + 3) + .4 * vnoise(p, .035, salt + 4)
        w = 0.0
        for q, rad in welds:
            w = max(w, 1 - smoothstep(rad * .3, rad, (p - q).length))
        bias = max(w * .9, low * (1 - smoothstep(.05, .9, p.z)) * .7, under * smoothstep(-.1, -.7, n.z) * .6)
        score = nz * .75 + bias
        mm = smoothstep(.62, .76, score)
        rc = mix(tint(RUST, .65 + .7 * nz), (.13, .065, .04), smoothstep(.78, .95, score) * .6)
        return mix(c, rc, mm)
    return f


def rust_fn(salt):
    return lambda p, n: tint(RUST, .55 + .5 * vnoise(p, .02, salt) + .2 * hnoise(p, salt))


def concrete_fn(tv, salt, damp_z=0.0, damp_h=.25):
    """Concrete (.36,.35,.32): mottle, dirty brown-grey and pale weathering patches, a dark damp stain with a green tint rising from `damp_z`
    with an irregular top edge."""
    def f(p, n):
        m = lum(p, .22, .2, salt)
        c = tint(CONC, tv * m)
        c = mix(c, tint((.19, .17, .14), m), smoothstep(.42, .62, vnoise(p, .5, salt + 2)) * .8)
        c = mix(c, tint(CONC, tv * m * 1.2), smoothstep(.65, .8, vnoise(p, .18, salt + 5)) * .4)
        if n.z > .6:
            c = mix(c, tint((.11, .15, .07), m), smoothstep(.55, .72, vnoise(p, .12, salt + 9)) * .5)
        edge = damp_z + damp_h * (1 + .8 * (vnoise(p, .14, salt + 4) - .5))
        d = clamp(1 - smoothstep(damp_z - .03, edge, p.z))
        c = mix(c, tint(CONC_DAMP, m), d * .85)
        return mix(c, tint((.12, .15, .08), m), d * smoothstep(.5, .7, vnoise(p, .1, salt + 8)) * .4)
    return f


def pit_wrap(f):
    def g_(p, n):
        return tint(f(p, n), 1 - .8 * smoothstep(0.0, -.4, p.z))
    return g_


def paint_fn(base, salt, rust_amt=.5, floor_z=0.0):
    """Painted steel with rust blooming through at edges and low down."""
    def f(p, n):
        m = lum(p, .10, .09, salt)
        c = tint(base, m)
        nz = vnoise(p, .07, salt + 3)
        r = rust_amt * (.55 * nz + .45 * (1 - smoothstep(floor_z, floor_z + .12, p.z))) + .2 * (hnoise(p, salt + 9.0) - .5)
        c = mix(c, tint(BOX_RED, .55), smoothstep(.55, .7, vnoise(p, .05, salt + 6)) * .5)
        return mix(c, tint(RUST, .9 + .3 * nz), smoothstep(.40, .66, r))
    return f


# ================================================================ primitives

def rod(geo, pts, radii, sides, colf, cap0=False, cap1=True, noise=0.0, phase=0.0, split=False, flip=False, mi=0):
    """Tube along a polyline (parallel-transport frames). Ring vertices are shared along the length unless `split` (each segment owns its
    rings, so a corrugation keeps its crisp facet shading); caps own their vertices (flat ends). flip reverses the faces (an inside liner)."""
    p = [Vector(q) for q in pts]; n = len(p)
    rad = [radii] * n if isinstance(radii, (int, float)) else list(radii)
    frames = []
    u = perp((p[1] - p[0]).normalized())
    for i in range(n):
        t = (p[min(i + 1, n - 1)] - p[max(0, i - 1)]).normalized()
        u = u - t * u.dot(t)
        if u.length < 1e-6:
            u = perp(t)
        u = u.normalized()
        frames.append((t, u, t.cross(u)))
    dist = [0.0]
    for i in range(1, n):
        dist.append(dist[-1] + (p[i] - p[i - 1]).length)

    def ring(i):
        t, u_, v_ = frames[i]
        out = []
        for j in range(sides):
            a = math.tau * j / sides
            rv = u_ * math.cos(a) + v_ * math.sin(a)
            out.append((p[i] + rv * rad[i] * (1 + noise * math.sin(j * 2.3 + i * 1.37 + phase)), rv))
        return out

    def faces_for(base):
        return [(base + j, base + (j + 1) % sides, base + sides + (j + 1) % sides, base + sides + j) for j in range(sides)]

    def fl(fs):
        return [tuple(reversed(f)) for f in fs] if flip else fs

    if not split:
        verts = []; cols = []; uvs = []; rvs = []
        for i in range(n):
            for j, (pos, rv) in enumerate(ring(i)):
                verts.append(pos); cols.append(colf(pos, rv)); uvs.append((j / sides, dist[i])); rvs.append(rv)
        faces = []
        for i in range(n - 1):
            faces += faces_for(i * sides)
        geo.add(verts, fl(faces), cols, uvs, mi, rvs)
    else:
        for i in range(n - 1):
            ra, rb = ring(i), ring(i + 1)
            verts = [x[0] for x in ra] + [x[0] for x in rb]; rvs = [x[1] for x in ra] + [x[1] for x in rb]
            cols = [colf(v, r) for v, r in zip(verts, rvs)]
            uvs = [(j / sides, dist[i]) for j in range(sides)] + [(j / sides, dist[i + 1]) for j in range(sides)]
            geo.add(verts, fl(faces_for(0)), cols, uvs, mi, rvs)
    for end, do in ((0, cap0), (n - 1, cap1)):
        if not do or sides < 3:
            continue
        rg = ring(end); t = frames[end][0]
        verts = [x[0] for x in rg]
        nrm = -t if end == 0 else t
        face = tuple(reversed(range(sides))) if end == 0 else tuple(range(sides))
        geo.add(verts, [face], [colf(v, nrm) for v in verts],
                [(.5 + .5 * math.cos(math.tau * j / sides), .5 + .5 * math.sin(math.tau * j / sides)) for j in range(sides)], mi, [nrm] * sides)
    geo.counts['tubes'] += 1


def box(geo, c, half, colf, axes=None, grid=(1, 1, 1), skip=(), mi=0):
    """Oriented box; every face owns its vertices (flat shading) and is a gb x gc grid so vertex colour can vary across it.
    axes = (ex, ey, ez) unit vectors, grid = subdivisions along each local axis, skip = face tags such as '-z', '+y'."""
    c = Vector(c)
    E = [Vector(e) for e in axes] if axes else [XV, YV, Z]
    H = list(half); G = list(grid); names = 'xyz'
    for a in range(3):
        b = (a + 1) % 3; cc = (a + 2) % 3
        for s in (1, -1):
            if ('+' if s > 0 else '-') + names[a] in skip:
                continue
            nrm = E[a] * s
            gb, gc = G[b], G[cc]
            verts = []; cols = []; uvs = []
            for j in range(gc + 1):
                for i in range(gb + 1):
                    sb = -1 + 2 * i / gb; sc = -1 + 2 * j / gc
                    pos = c + nrm * H[a] + E[b] * (H[b] * sb) + E[cc] * (H[cc] * sc)
                    verts.append(pos); cols.append(colf(pos, nrm)); uvs.append((H[b] * (sb + 1), H[cc] * (sc + 1)))
            faces = [(j * (gb + 1) + i, j * (gb + 1) + i + 1, (j + 1) * (gb + 1) + i + 1, (j + 1) * (gb + 1) + i) for j in range(gc) for i in range(gb)]
            p0, p1, p2 = verts[faces[0][0]], verts[faces[0][1]], verts[faces[0][2]]
            if (p1 - p0).cross(p2 - p0).dot(nrm) < 0:
                faces = [tuple(reversed(f)) for f in faces]
            geo.add(verts, faces, cols, uvs, mi, [nrm] * len(verts))


def quad(geo, vs, colf, nrm, mi=0):
    vs = [Vector(v) for v in vs]
    face = (0, 1, 2, 3) if (vs[1] - vs[0]).cross(vs[2] - vs[0]).dot(nrm) >= 0 else (3, 2, 1, 0)
    geo.add(vs, [face], [colf(v, nrm) for v in vs], [(0, 0), (1, 0), (1, 1), (0, 1)], mi, [Vector(nrm)] * 4)


def fan(geo, vs, colf, nrm, mi=0):
    """One convex polygon facing `nrm` (own vertices)."""
    vs = [Vector(v) for v in vs]
    geo.oriented(vs, [colf(v, nrm) for v in vs], [(v.x, v.z) for v in vs], mi, nrm)


def revolve(geo, prof, sides, colf, centre=(0, 0, 0), phase=0.0, mi=0):
    """Surface of revolution about the vertical axis through `centre`; prof = [(r, z), ...] walked so the material is on the right (outer wall
    up, rim inward, inner wall down gives outward normals); r = 0 is an apex/centre point (a triangle fan)."""
    c = Vector(centre); n = len(prof)
    verts = []; cols = []; uvs = []; rvs = []; start = []
    for i, (r, z) in enumerate(prof):
        a, b = prof[max(0, i - 1)], prof[min(n - 1, i + 1)]
        dr, dz = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dr, dz) or 1.0
        nr, nz_ = dz / ln, -dr / ln
        start.append(len(verts))
        if r <= 1e-6:
            pos = c + Vector((0, 0, z)); nrm = Vector((0, 0, 1 if nz_ >= 0 else -1))
            verts.append(pos); cols.append(colf(pos, nrm)); uvs.append((.5, .5)); rvs.append(nrm)
            continue
        for j in range(sides):
            a_ = math.tau * j / sides + phase
            rv = Vector((math.cos(a_), math.sin(a_), 0))
            pos = c + rv * r + Vector((0, 0, z)); nrm = rv * nr + Vector((0, 0, nz_))
            verts.append(pos); cols.append(colf(pos, nrm)); uvs.append((j / sides, z)); rvs.append(nrm)
    faces = []
    for i in range(n - 1):
        ri, rj = prof[i][0], prof[i + 1][0]
        a0, b0 = start[i], start[i + 1]
        for j in range(sides):
            j1 = (j + 1) % sides
            if ri <= 1e-6 and rj <= 1e-6:
                continue
            if rj <= 1e-6:
                faces.append((a0 + j, a0 + j1, b0))
            elif ri <= 1e-6:
                faces.append((b0 + j1, b0 + j, a0))
            else:
                faces.append((a0 + j, a0 + j1, b0 + j1, b0 + j))
    geo.add(verts, faces, cols, uvs, mi, rvs)
    geo.counts['tubes'] += 1


def extrude(geo, poly, ufn, d0, d1, colf, segs=1, caps=(True, True), mi=0):
    """Prism: polygon `poly` (u, v) mapped to the world by ufn(u, v, d) and extruded from depth d0 to d1 (segs sections). Side vertices are
    shared round the ring (smooth), caps own theirs. Normals follow the polygon's counter-clockwise order seen along +depth reversed."""
    m = len(poly); verts = []; cols = []; uvs = []
    dirn = (ufn(0, 0, 1) - ufn(0, 0, 0)).normalized()
    for s in range(segs + 1):
        d = lerp(d0, d1, s / segs)
        for k, (u, v) in enumerate(poly):
            pos = ufn(u, v, d); verts.append(pos); cols.append(colf(pos, Z)); uvs.append((k / m, d))
    faces = [(s * m + k, s * m + (k + 1) % m, (s + 1) * m + (k + 1) % m, (s + 1) * m + k) for s in range(segs) for k in range(m)]
    cen = sum(verts[:m], Vector()) / m
    p0, p1, p2 = verts[faces[0][0]], verts[faces[0][1]], verts[faces[0][2]]
    mid = (verts[0] + verts[1]) / 2
    if (p1 - p0).cross(p2 - p0).dot(mid - cen) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    geo.add(verts, faces, cols, uvs, mi)
    for end, do in ((0, caps[0]), (segs, caps[1])):
        if do:
            ring = [verts[end * m + k] for k in range(m)]
            fan(geo, ring, colf, -dirn if end == 0 else dirn, mi)


def post_rod(g, x, y, r, ztop, lod, colf, sides=(12, 8, 6), noise=(.03, .02, .0), phase=0.0, bevel=.06, z0=ROOT_Z, tilt=(0.0, 0.0)):
    """Round post from the root (z0) to ztop: shaft rings every ~16 cm at LOD0 (fewer after), a chamfered top, flat cap."""
    nseg = (7, 3, 1)[lod]
    if lod == 2:
        zs = [z0, ztop]; ks = [1.0, .85]
    else:
        zs = [z0 + (ztop - bevel - z0) * k / nseg for k in range(nseg + 1)] + [ztop]; ks = [1.0] * (nseg + 1) + [.68]
    pts = [Vector((x + tilt[0] * (z - z0) / (ztop - z0), y + tilt[1] * (z - z0) / (ztop - z0), z)) for z in zs]
    rod(g, pts, [r * k for k in ks], sides[lod], colf, cap0=False, cap1=True, noise=noise[lod], phase=phase)


# ---------------------------------------------------------------- hulls (UCX_<mesh>_NN convex prisms)

def _hull_obj(name, idx, verts, faces, coll):
    nm = 'UCX_%s_%02d' % (name, idx)
    me = bpy.data.meshes.new(nm); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    ob = bpy.data.objects.new(nm, me); coll.objects.link(ob)
    ob.hide_render = True; ob.hide_set(True)
    return ob


def hull_cyl(name, idx, a, b, r, sides, coll):
    a = Vector(a); b = Vector(b); ax = (b - a).normalized(); u = perp(ax); v = ax.cross(u)
    verts = [c + (u * math.cos(math.tau * j / sides) + v * math.sin(math.tau * j / sides)) * r for c in (a, b) for j in range(sides)]
    faces = [tuple(reversed(range(sides))), tuple(range(sides, 2 * sides))] + [(j, (j + 1) % sides, sides + (j + 1) % sides, sides + j) for j in range(sides)]
    return _hull_obj(name, idx, verts, faces, coll)


def hull_box(name, idx, c, half, coll):
    c = Vector(c); hx, hy, hz = half
    verts = [c + Vector((sx * hx, sy * hy, sz * hz)) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    return _hull_obj(name, idx, verts, faces, coll)


def make_hulls(name, specs, coll):
    out = []
    for i, sp in enumerate(specs):
        if sp[0] == 'cyl':
            out.append(hull_cyl(name, i, sp[1], sp[2], sp[3], sp[4], coll))
        else:
            out.append(hull_box(name, i, sp[1], sp[2], coll))
    return out


# ================================================================ 1. Fence module

WIRE_Z = [.12, .26, .42, .60, .78, .96, 1.14]


def design_fence(rng, a):
    return dict(r=.07 * rng.uniform(.97, 1.04), tint=rng.uniform(.93, 1.07), salt=rng.uniform(1, 90),
                sag=[.015 * rng.uniform(.88, 1.12) for _ in WIRE_Z], wt=[rng.uniform(.9, 1.1) for _ in WIRE_Z],
                wsalt=[rng.uniform(1, 90) for _ in WIRE_Z],
                bx=[k + 1 + rng.uniform(-.04, .04) for k in range(3)], bt=[rng.uniform(.92, 1.08) for _ in range(3)],
                bsalt=[rng.uniform(1, 90) for _ in range(3)], lean=(rng.uniform(-.012, .012), rng.uniform(-.012, .012)))


def emit_fence(D, lod):
    g = L.Geo(); r = D['r']
    post_rod(g, 0, 0, r, 1.2, lod, pine_fn(D['tint'], D['salt']), phase=D['salt'], tilt=D['lean'])
    y = -(r + .003)
    nseg = (16, 4, 1)[lod]
    for k, z0 in enumerate(WIRE_Z):
        pts = [Vector((4.0 * i / nseg, y, z0 - D['sag'][k] * 4 * (i / nseg) * (1 - i / nseg))) for i in range(nseg + 1)]
        rod(g, pts, .002, 3, steel_fn(D['wt'][k], D['wsalt'][k], low=.03), cap0=False, cap1=True)
    grid = ((1, 1, 3), (1, 1, 1), (1, 1, 1))[lod]
    for k in range(3):
        box(g, (D['bx'][k], y + .014, .03 + .55), (.025, .015, .55), pine_fn(D['bt'][k], D['bsalt'][k], wet=False), grid=grid)
    return g


def hulls_fence(D):
    return [('cyl', (0, 0, ROOT_Z), (0, 0, 1.2), D['r'] * 1.06, 8)]


# ================================================================ 2. Strainer assembly

def design_strainer(rng, a):
    return dict(tint=[rng.uniform(.92, 1.08) for _ in range(5)], salt=[rng.uniform(1, 90) for _ in range(6)],
                lean=(rng.uniform(-.01, .01), rng.uniform(-.01, .01)), wt=[rng.uniform(.9, 1.1) for _ in WIRE_Z],
                wrap0=[rng.uniform(-110, -70) for _ in WIRE_Z])


def emit_strainer(D, lod):
    g = L.Geo(); T = D['tint']; S = D['salt']
    rs, rp = .12, .09
    post_rod(g, 0, 0, rs, 1.3, lod, pine_fn(T[0], S[0]), sides=(12, 8, 6), phase=S[0], tilt=D['lean'])
    post_rod(g, -2.5, 0, rp, 1.2, lod, pine_fn(T[1], S[1]), sides=(10, 6, 6), phase=S[1])
    # diagonal stay post from the strainer's top to a foot block on the ground 2 m along the fence line
    a0 = Vector((.03, -.15, 1.13)); a1 = Vector((2.0, -.15, .12))
    n_st = (3, 2, 2)[lod]
    rod(g, [a0.lerp(a1, i / (n_st - 1)) for i in range(n_st)], .05, (8, 6, 4)[lod], pine_fn(T[2], S[2], wet=False), cap0=True, cap1=True)
    box(g, (2.04, -.15, .03), (.2, .14, .09), pine_fn(T[3], S[3]), grid=((2, 1, 1), (1, 1, 1), (1, 1, 1))[lod], skip=('-z',))
    # horizontal rail .5 m up to the second post
    n_r = (3, 2, 2)[lod]
    rod(g, [Vector((-.1 + (-2.41 + .1) * i / (n_r - 1), 0, .5)) for i in range(n_r)], .05, (8, 6, 4)[lod], pine_fn(T[4], S[4], wet=False), cap0=False, cap1=True)
    # wires tied off: a wrap round the post and a tail toward the fence
    ar = .124
    for k, z0 in enumerate(WIRE_Z):
        wc = steel_fn(D['wt'][k], S[5] + k, low=.03)
        if lod < 2:
            n_w = (9, 5)[lod]; a_0 = D2R(D['wrap0'][k]); a_1 = a_0 + D2R(300)
            rod(g, [Vector((ar * math.cos(lerp(a_0, a_1, i / (n_w - 1))), ar * math.sin(lerp(a_0, a_1, i / (n_w - 1))), z0 + .03 * i / (n_w - 1)))
                    for i in range(n_w)], .0028, 3, wc, cap0=False, cap1=True)
        n_t = (3, 1, 1)[lod]
        rod(g, [Vector((.10 + .45 * i / n_t, -.0725, z0)) for i in range(n_t + 1)], .002, 3, wc, cap0=False, cap1=True)
    return g


def hulls_strainer(D):
    return [('cyl', (0, 0, ROOT_Z), (0, 0, 1.3), .12 * 1.06, 8), ('cyl', (-2.5, 0, ROOT_Z), (-2.5, 0, 1.2), .09 * 1.06, 8)]


# ================================================================ 3. Farm gate

BAR_Z = [.14, .30, .48, .69, .94, 1.24]
GX0, GX1, GXL = .22, 3.82, 3.96


def design_gate(rng, a):
    return dict(ht=rng.uniform(.93, 1.07), lt=rng.uniform(.93, 1.07), salt=rng.uniform(1, 90),
                bt=[rng.uniform(.9, 1.1) for _ in BAR_Z], st=[rng.uniform(.9, 1.1) for _ in range(2)], dt=rng.uniform(.9, 1.1),
                lean=(rng.uniform(-.01, .01), rng.uniform(-.01, .01)), lean2=(rng.uniform(-.01, .01), rng.uniform(-.01, .01)))


def emit_gate(D, lod):
    g = L.Geo(); S = D['salt']
    post_rod(g, 0, 0, .12, 1.3, lod, pine_fn(D['ht'], S), sides=(12, 8, 6), phase=S, tilt=D['lean'])
    post_rod(g, GXL, 0, .09, 1.2, lod, pine_fn(D['lt'], S + 11), sides=(10, 6, 6), phase=S + 11, tilt=D['lean2'])
    xs0, xs1 = GX0 + .0185, GX1 - .0185
    welds = [(Vector((x, 0, z)), .13) for x in (xs0, xs1) for z in BAR_Z]
    fr = ([0, .04, .12, .5, .88, .96, 1], [0, .06, .5, .94, 1], [0, 1])[lod]
    sd = (8, 6, 4)[lod]
    for k, z in enumerate(BAR_Z):
        rod(g, [Vector((GX0 + (GX1 - GX0) * t, 0, z)) for t in fr], .0165, sd, steel_fn(D['bt'][k], S + 3 * k, welds, low=.24 if z < .5 else .06, under=.12),
            cap0=True, cap1=True)
    zr = (BAR_Z, [BAR_Z[0], BAR_Z[3], BAR_Z[5]], [BAR_Z[0], BAR_Z[5]])[lod]
    for e, x in enumerate((xs0, xs1)):
        rod(g, [Vector((x, 0, z)) for z in zr], .0185, sd, steel_fn(D['st'][e], S + 40 + e, welds, low=.5), cap0=True, cap1=True)
    nd = (5, 3, 2)[lod]
    rod(g, [Vector((xs0, -.032, BAR_Z[0])).lerp(Vector((xs1, -.032, BAR_Z[5])), i / (nd - 1)) for i in range(nd)], .014, sd,
        steel_fn(D['dt'], S + 60, welds, low=.4, under=.2), cap0=True, cap1=True)
    if lod == 0:
        for z in BAR_Z:
            for x in (GX0 + .045, GX1 - .045):
                rod(g, [Vector((x - .015, 0, z)), Vector((x + .015, 0, z))], .024, 6, rust_fn(S + z * 13 + x), cap0=True, cap1=True)
    # hinge straps, hinge eyes, latch tongue and keeper
    sc = steel_fn(1.0, S + 70, low=.5)
    if lod < 2:
        for z in (.30, .94):
            box(g, (.33, -.025, z), (.27, .003, .028), sc, grid=(1, 1, 1))
        if lod == 0:
            for z in (.30, .94):
                rod(g, [Vector((.145, -.02, z - .045)), Vector((.145, -.02, z + .045))], .013, 6, sc, cap0=True, cap1=True)
        box(g, (GX1 + .035, -.02, .94), (.045, .01, .012), sc)
        box(g, (GXL - .095, -.02, .94), (.014, .025, .03), sc)
    return g


def hulls_gate(D):
    return [('box', (2.02, 0, .69), (1.8, .04, .56)), ('cyl', (0, 0, ROOT_Z), (0, 0, 1.3), .12 * 1.06, 8),
            ('cyl', (GXL, 0, ROOT_Z), (GXL, 0, 1.2), .09 * 1.06, 8)]


# ================================================================ 4. Cattle stop (travel along +X, width along Y)

def design_cattle(rng, a):
    return dict(salt=rng.uniform(1, 90), ct=[rng.uniform(.93, 1.07) for _ in range(6)], bt=[rng.uniform(.9, 1.1) for _ in range(12)],
                bs=[rng.uniform(1, 90) for _ in range(12)])


def emit_cattle(D, lod):
    g = L.Geo(); S = D['salt']
    cc = lambda k, dz=0.0, dh=.12: pit_wrap(concrete_fn(D['ct'][k], S + 7 * k, damp_z=dz, damp_h=dh))
    gk = ((10, 2, 4), (2, 1, 1), (1, 1, 1))[lod]
    for sy, k in ((1, 0), (-1, 1)):
        box(g, (0, sy * 1.65, -.135), (1.2, .15, .315), cc(k), grid=gk, skip=('-z',))
    gb = ((3, 2, 2), (1, 1, 1), (1, 1, 1))[lod]
    for sx in (1, -1):
        for sy in (1, -1):
            box(g, (sx * .9, sy * 1.65, .28), (.3, .15, .10), cc(2), grid=gb, skip=('-z',))
    gbm = ((1, 6, 3), (1, 2, 1), (1, 1, 1))[lod]
    for sx, k in ((1, 3), (-1, 4)):
        box(g, (sx * 1.05, 0, -.225), (.15, 1.5, .225), cc(k), grid=gbm, skip=('+y', '-y', '-z'))
    floor = lambda p, n: tint(PIT, lum(p, .25, .3, S + 90))
    box(g, (0, 0, -.42), (.9, 1.5, .02), floor, grid=((3, 6, 1), (1, 1, 1), (1, 1, 1))[lod], skip=('-z', '+x', '-x', '+y', '-y'))
    fr = ([0, .05, .5, .95, 1], [0, .5, 1], [0, 1])[lod]
    sd = (8, 6, 3)[lod]
    for k in range(12):
        x = -.825 + .15 * k
        welds = [(Vector((x, 1.5, -.035)), .12), (Vector((x, -1.5, -.035)), .12)]
        rod(g, [Vector((x, -1.52 + 3.04 * t, -.035)) for t in fr], .035, sd, steel_fn(D['bt'][k], D['bs'][k], welds, low=.18, under=.45), cap0=True, cap1=True)
    return g


def hulls_cattle(D):
    return [('box', (0, 1.65, -.135), (1.2, .15, .315)), ('box', (0, -1.65, -.135), (1.2, .15, .315)), ('box', (0, 0, -.035), (.9, 1.5, .035))]


# ================================================================ 5. Culvert with headwall (axis along X, pipe centre .5 m below the road)

PZ = -.5; PR = .30; PV = .272; HX0, HX1 = -1.25, -1.0; HW = .8; HZ0, HZ1 = -.9, .1


def design_culvert(rng, a):
    return dict(salt=rng.uniform(1, 90), ct=[rng.uniform(.93, 1.07) for _ in range(5)], pt=rng.uniform(.9, 1.1))


def emit_culvert(D, lod):
    g = L.Geo(); S = D['salt']
    pc = lambda p, n: mix(tint(PIPE, D['pt'] * lum(p, .18, .12, S)), tint(PIPE_DUST, lum(p, .2, .08, S + 4)),
                          smoothstep(.64, .80, vnoise(p, .28, S + 2)) * .55 * (.4 + .6 * smoothstep(-1.0, -1.45, p.x) + .6 * smoothstep(.9, 1.3, p.x)))
    sides = (12, 8, 6)[lod]
    nseg = (40, 20, 2)[lod]
    if lod < 2:
        pts = [Vector((-1.5 + 3.0 * i / nseg, 0, PZ)) for i in range(nseg + 1)]
        rod(g, pts, [PR if i % 2 == 0 else PV for i in range(nseg + 1)], sides, pc, cap0=False, cap1=False, split=True)
        liner = lambda p, n: tint((.016, .016, .015), lum(p, .3, .1, S + 8))
        rod(g, [Vector((-1.5, 0, PZ)), Vector((1.5, 0, PZ))], PV - .004, sides, liner, cap0=False, cap1=False, flip=True)
        for x, sg in ((-1.5, -1), (1.5, 1)):     # the pipe's wall seen end-on: crest ring to liner ring
            for j in range(sides):
                a0 = math.tau * j / sides; a1 = math.tau * (j + 1) / sides
                vs = [Vector((x, PR * math.cos(a), PZ + PR * math.sin(a))) for a in (a0, a1)] + \
                     [Vector((x, (PV - .004) * math.cos(a), PZ + (PV - .004) * math.sin(a))) for a in (a1, a0)]
                quad(g, vs, pc, Vector((sg, 0, 0)))
    else:
        rod(g, [Vector((-1.5 + 1.5 * i, 0, PZ)) for i in range(3)], .286, sides, pc, cap0=True, cap1=True)
    # headwall: a slab with the pipe through it
    hc = lambda k, dz=-.9, dh=.55: concrete_fn(D['ct'][k], S + 5 * k, damp_z=dz, damp_h=dh)
    ctr = Vector((0, PZ))
    if lod < 2:
        ncp = 12 if lod == 0 else 8
        if ncp == 12:
            top = [(.8, .6), (.267, .6), (-.267, .6), (-.8, .6), (-.8, .267), (-.8, -.067), (-.8, -.4), (-.267, -.4), (.267, -.4), (.8, -.4), (.8, -.067), (.8, .267)]
        else:
            top = [(.8, .6), (0, .6), (-.8, .6), (-.8, .1), (-.8, -.4), (0, -.4), (.8, -.4), (.8, .1)]
        outer = [Vector((HX0, c[0], PZ + c[1])) for c in top]
        inner = []
        for c in top:
            an = math.atan2(c[1], c[0])
            inner.append(Vector((HX0, (PR + .005) * math.cos(an), PZ + (PR + .005) * math.sin(an))))
        mids = [o.lerp(i, .5) for o, i in zip(outer, inner)]
        f0 = hc(0)
        thirds = [o.lerp(i, 2 / 3) for o, i in zip(outer, inner)]
        rings = [inner, mids, thirds[::1], outer] if False else ([inner, [o.lerp(i, .67) for o, i in zip(outer, inner)], [o.lerp(i, .33) for o, i in zip(outer, inner)], outer] if lod == 0 else [inner, outer])
        for ra, rb in zip(rings[:-1], rings[1:]):
            for k in range(ncp):
                quad(g, [ra[k], ra[(k + 1) % ncp], rb[(k + 1) % ncp], rb[k]], f0, Vector((-1, 0, 0)))
        if lod == 0:
            fb = hc(1)
            ob_ = [Vector((HX1, v.y, v.z)) for v in outer]; ib_ = [Vector((HX1, v.y, v.z)) for v in inner]
            for k in range(ncp):
                quad(g, [ib_[k], ib_[(k + 1) % ncp], ob_[(k + 1) % ncp], ob_[k]], fb, Vector((1, 0, 0)))
        gs = ((1, 4, 4), (1, 1, 2), (1, 1, 1))[lod]
        box(g, ((HX0 + HX1) / 2, 0, (HZ0 + HZ1) / 2), ((HX1 - HX0) / 2, HW, (HZ1 - HZ0) / 2), hc(2), grid=gs, skip=('+x', '-x', '-z'))
        # wing walls, apron
        for sy in (1, -1):
            box(g, (-.7, sy * (HW - .075), -.5), (.3, .075, .4), hc(3 + (sy > 0), -.9, .5), grid=((2, 1, 2), (1, 1, 1), (1, 1, 1))[lod], skip=('-z', '-x'))
        box(g, (-1.6, 0, -.86), (.35, .6, .04), hc(4, -.9, .1), grid=((2, 3, 1), (1, 1, 1), (1, 1, 1))[lod], skip=('-z', '+x'))
    else:
        box(g, ((HX0 + HX1) / 2, 0, (HZ0 + HZ1) / 2), ((HX1 - HX0) / 2, HW, (HZ1 - HZ0) / 2), hc(2), skip=('-z', '+x'))
        for sy in (1, -1):
            box(g, (-.7, sy * (HW - .075), -.5), (.3, .075, .4), hc(3), skip=('-z', '-x', '+y', '-y'))
        box(g, (-1.6, 0, -.86), (.35, .6, .04), hc(4), skip=('-z', '+x', '+y', '-y'))
    return g


def hulls_culvert(D):
    return [('box', ((HX0 + HX1) / 2, 0, (HZ0 + HZ1) / 2), ((HX1 - HX0) / 2, HW, (HZ1 - HZ0) / 2))]


# ================================================================ 6. Concrete trough

def design_trough(rng, a):
    return dict(salt=rng.uniform(1, 90), tint=rng.uniform(.94, 1.06), lump_az=rng.uniform(-.45, -.1) * math.pi, phase=rng.uniform(0, 6))


def emit_trough(D, lod):
    g = L.Geo(); S = D['salt']
    base = concrete_fn(D['tint'], S, damp_z=-.06, damp_h=.2)

    def tc(p, n):
        c = base(p, n)
        inward = (n.x * p.x + n.y * p.y) < -.05 * math.hypot(p.x, p.y)
        if inward or n.z > .6:
            dz = .475 - p.z
            nz = vnoise(p, .12, S + 11)
            w = smoothstep(-.03, .015, dz) * (1 - smoothstep(.04, .075 + .09 * nz, dz)) * (.6 + .5 * nz)
            below = smoothstep(.01, .04, dz)
            c = mix(c, tint(ALGAE, .8 + .5 * vnoise(p, .05, S + 12)), clamp(w * 1.3) * .85)
            c = mix(c, tint((.05, .07, .04), lum(p, .2, .1, S + 13)), below * .5)
        return c
    if lod == 0:
        sides = 28
        prof = [(.605, -.06), (.600, .04), (.595, .22), (.597, .40), (.600, .47), (.592, .50), (.555, .505), (.525, .50),
                (.520, .47), (.515, .42), (.510, .34), (.500, .20), (.490, .10), (0, .08)]
    elif lod == 1:
        sides = 16
        prof = [(.605, -.06), (.597, .25), (.600, .47), (.59, .50), (.525, .50), (.520, .45), (.50, .12), (0, .08)]
    else:
        sides = 8
        prof = [(.605, -.06), (.600, .50), (.52, .50), (.51, .10), (0, .08)]
    revolve(g, prof, sides, tc, phase=D['phase'])
    water = lambda p, n: tint(WATER, lum(p, .25, .2, S + 14))
    wz = .45
    wr = .518
    fan(g, [Vector((wr * math.cos(math.tau * j / sides + D['phase']), wr * math.sin(math.tau * j / sides + D['phase']), wz)) for j in range(sides)], water, Z)
    # ballcock cover: a concrete lid on the rim with a lifting block, and the black poly inlet pipe running down the outside
    az = D['lump_az']
    ex = Vector((math.cos(az), math.sin(az), 0)); ey = Vector((-math.sin(az), math.cos(az), 0))
    lid = concrete_fn(D['tint'], S + 21, damp_z=.4, damp_h=.01)
    cen = ex * .555
    box(g, (cen.x, cen.y, .54), (.13, .09, .04), lid, axes=(ex, ey, Z), grid=((2, 2, 1), (1, 1, 1), (1, 1, 1))[lod], skip=('-z',))
    if lod == 0:
        box(g, (cen.x - ex.x * .02, cen.y - ex.y * .02, .605), (.05, .045, .025), lid, axes=(ex, ey, Z), skip=('-z',))
        pipe = lambda p, n: tint((.035, .035, .034), lum(p, .25, .08, S + 23))
        rod(g, [ex * .60 + Vector((0, 0, .53)), ex * .632 + Vector((0, 0, .50)), ex * .632 + Vector((0, 0, .26)), ex * .632 + Vector((0, 0, ROOT_Z + .02))],
            .014, 5, pipe, cap0=True, cap1=True)
    return g


def hulls_trough(D):
    return [('cyl', (0, 0, ROOT_Z), (0, 0, .5), .605 * 1.05, 12)]


# ================================================================ 7. Rural power pole

def design_pole(rng, a):
    return dict(salt=rng.uniform(1, 90), tint=rng.uniform(.93, 1.07), bend=(rng.uniform(.025, .04), rng.uniform(.025, .04), rng.uniform(0, 6), rng.uniform(0, 6)),
                at=rng.uniform(.93, 1.07), ct=rng.uniform(.9, 1.1))


def pole_axis(D, z):
    b = D['bend']
    return Vector((b[0] * math.sin(z * .62 + b[2]) * min(1, z / 2), b[1] * math.sin(z * .47 + b[3]) * min(1, z / 2), z))


def pole_r(z):
    return (.175 if z < .35 else .165) - .040 * clamp(z / 10.0)


def emit_pole(D, lod):
    g = L.Geo(); S = D['salt']; zt = 10.0

    def pc(p, n):
        m = lum(p, .10, .2, S)
        c = tint(POLE, D['tint'] * m)
        c = mix(c, tint(POLE, D['tint'] * m * 1.25), smoothstep(.55, .75, vnoise(Vector((p.x, p.y, p.z * .5)), .3, S + 2)) * .5)
        c = mix(c, tint(POLE, D['tint'] * m * .45), smoothstep(.5, .68, vnoise(Vector((p.x, p.y, p.z * .5)), .17, S + 3)) * .7)
        top = 1.15 + 1.1 * vnoise(Vector((p.x, p.y, 0)), .2, S + 5) + .5 * (hnoise(p, S) - .5)
        return mix(c, tint(POLE_BASE, m), (1 - smoothstep(top - .35, top, p.z)) * .92)
    nr = (34, 12, 3)[lod]
    zs = [ROOT_Z + (zt - ROOT_Z) * (i / (nr - 1)) for i in range(nr)]
    pts = [pole_axis(D, z) for z in zs]
    rod(g, pts, [pole_r(z) * (1 if lod < 2 else .95) for z in zs], (10, 8, 5)[lod], pc, cap0=False, cap1=True, noise=(.03, .02, 0)[lod], phase=S)
    zc = 9.4; c0 = pole_axis(D, zc)
    # cross-arm, braces, three insulators
    armc = lambda p, n: tint(ARM, D['ct'] * lum(p, .14, .15, S + 6))
    box(g, (c0.x, c0.y, zc), (.045, .9, .06), armc, grid=((1, 6, 1), (1, 1, 1), (1, 1, 1))[lod], skip=() if lod < 2 else ('-z',))
    stl = steel_fn(D['at'], S + 7, low=.0)
    if lod == 0:
        for sy in (1, -1):
            rod(g, [Vector((c0.x, c0.y + sy * .12, zc - .45)), Vector((c0.x, c0.y + sy * .62, zc - .06))], .012, 5, stl, cap0=True, cap1=True)
    ins = lambda p, n: tint(INSUL, lum(p, .2, .03, S + 8))
    ip = [(.014, .0), (.05, .03), (.056, .05), (.034, .075), (.05, .10), (.03, .13), (.012, .16)]
    ip = ip if lod == 0 else ([(.014, 0), (.05, .04), (.034, .09), (.012, .16)] if lod == 1 else [(.03, 0), (.012, .16)])
    for yo in (-.75, 0.0, .75):
        revolve(g, ip, (8, 6, 3)[lod], ins, centre=(c0.x, c0.y + yo, zc + .06))
    # steel stay cable to a ground anchor 3 m out
    zs_ = 8.7; att = pole_axis(D, zs_) + Vector((.14, 0, 0)); anc = Vector((3.0, 0, .12))
    ns = (5, 2, 2)[lod]
    rod(g, [att.lerp(anc, i / (ns - 1)) for i in range(ns)], .008, 3, steel_fn(D['at'], S + 9, low=.55), cap0=True, cap1=True)
    box(g, (3.0, 0, .03), (.17, .17, .09), concrete_fn(D['tint'], S + 10, damp_z=-.06, damp_h=.1), grid=((2, 2, 1), (1, 1, 1), (1, 1, 1))[lod], skip=('-z',))
    if lod == 0:
        box(g, (att.x - .02, att.y, att.z), (.03, .018, .035), stl)
    return g


def hulls_pole(D):
    return [('cyl', (0, 0, ROOT_Z), (0, 0, 10.0), .175 * 1.06, 8)]


# ================================================================ 8. Sign posts

def design_sign(rng, a):
    return dict(salt=rng.uniform(1, 90), pt=rng.uniform(.92, 1.08), bt=rng.uniform(.92, 1.08),
                lw=[w * rng.uniform(.95, 1.05) for w in (.075, .075, .045, .08, .07, .07, .045, .075)], lean=(rng.uniform(-.008, .008), rng.uniform(-.008, .008)))


def sign_post(g, lod, D, ztop=2.2):
    pc = steel_fn(D['pt'], D['salt'], low=.3)
    zs = ([ROOT_Z, 1.0, ztop], [ROOT_Z, ztop], [ROOT_Z, ztop])[lod]
    rod(g, [Vector((D['lean'][0] * (z - ROOT_Z) / 2.3, D['lean'][1] * (z - ROOT_Z) / 2.3, z)) for z in zs], .03, (10, 6, 4)[lod], pc, cap0=False, cap1=True)


def emit_sign(D, lod):
    g = L.Geo(); S = D['salt']
    sign_post(g, lod, D)
    zc = 2.015; yb = -.036

    def bc(p, n):
        if n.y > .5:
            return tint(GALV, D['bt'] * lum(p, .08, .1, S + 2))
        if n.y < -.5:
            dust = smoothstep(.04, -.005, p.z - (zc - .125)) * .5
            c = tint(SIGN_GREEN, D['bt'] * lum(p, .14, .14, S + 3))
            return mix(c, tint((.10, .14, .08), lum(p, .2, .05, S + 4)), dust)
        return tint(GALV, .7)
    box(g, (0, yb, zc), (.45, .006, .125), bc, grid=((6, 1, 2), (1, 1, 1), (1, 1, 1))[lod])
    pale = lambda p, n: tint(LETTER, lum(p, .12, .06, S + 5))
    yl = yb - .006 - .0022
    if lod == 0:
        w = D['lw']; gap = .02; wg = .05
        total = sum(w) + 6 * gap + wg
        x = -total / 2
        for k, wi in enumerate(w):
            box(g, (x + wi / 2, yl, zc), (wi / 2, .0022, .055), pale, skip=('+y',))
            x += wi + (wg if k == 4 else gap)
        for (cx, cz, hx, hz) in ((0, zc + .107, .41, .0055), (0, zc - .107, .41, .0055), (-.415, zc, .0055, .102), (.415, zc, .0055, .102)):
            box(g, (cx, yb - .006 - .0015, cz), (hx, .0015, hz), pale, skip=('+y',))
        for z in (1.93, 2.10):
            box(g, (0, 0, z), (.036, .036, .01), steel_fn(1.0, S + 9, low=.2))
    elif lod == 1:
        for cx, hw in ((-.2, .17), (.28, .1)):
            box(g, (cx, yl, zc), (hw, .0022, .055), pale, skip=('+y',))
        box(g, (0, 0, 2.0), (.036, .036, .01), steel_fn(1.0, S + 9, low=.2))
    else:
        box(g, (0, yl, zc), (.34, .0022, .055), pale, skip=('+y',))
    return g


def hulls_sign(D):
    return [('cyl', (0, 0, ROOT_Z), (0, 0, 2.2), .03 * 1.06, 8)]


def rtri(inr, rc, arcn):
    """Rounded equilateral triangle, apex down, centroid at the origin, as CCW (x, z) points. arcn points per corner (1 = sharp)."""
    R = 2 * inr
    out = []
    for ang in (-90, 30, 150):
        th = D2R(ang); d = (math.cos(th), math.sin(th))
        if arcn == 1:
            out.append((R * d[0], R * d[1])); continue
        cx, cz = d[0] * (R - 2 * rc), d[1] * (R - 2 * rc)
        for i in range(arcn):
            a = th + D2R(-60 + 120 * i / (arcn - 1))
            out.append((cx + rc * math.cos(a), cz + rc * math.sin(a)))
    return out


def design_giveway(rng, a):
    return dict(salt=rng.uniform(1, 90), pt=rng.uniform(.92, 1.08), wt=rng.uniform(.95, 1.05), rt=rng.uniform(.92, 1.08),
                lean=(rng.uniform(-.008, .008), rng.uniform(-.008, .008)))


def emit_giveway(D, lod):
    g = L.Geo(); S = D['salt']
    sign_post(g, lod, D)
    inr = .75 / (2 * math.sqrt(3)); ztop = 2.12; zc = ztop - inr
    arcn = (4, 2, 1)[lod]
    yf, yr = -.040, -.032

    def wc(p, n):
        if n.y < -.5:
            grime = smoothstep(zc - .02, zc - .22, p.z) * .5 * (.5 + vnoise(p, .08, S + 3))
            return mix(tint(SIGN_WHITE, D['wt'] * lum(p, .06, .1, S + 2)), tint((.50, .50, .46), lum(p, .2, .06, S + 4)), grime)
        return tint(GALV, D['pt'] * lum(p, .08, .1, S + 2))
    rim = lambda p, n: tint(SIGN_RED, D['rt'] * lum(p, .10, .06, S + 5))
    plate = rtri(inr, .045, arcn)
    P = lambda pts, y: [Vector((x, y, zc + z)) for x, z in pts]
    pf = P(plate, yf); pb = P(plate, yr)
    fan(g, pf, wc, Vector((0, -1, 0))); fan(g, pb, wc, Vector((0, 1, 0)))
    m = len(plate)
    for k in range(m):
        k1 = (k + 1) % m
        edge = Vector((0, 1, 0)).cross(pf[k1] - pf[k])
        quad(g, [pf[k], pf[k1], pb[k1], pb[k]], wc, edge.normalized() if edge.length > 1e-6 else Vector((1, 0, 0)))
    yrim = yf - .006
    ro = P(rtri(inr - .008, max(.045 - .008, .004), arcn), yf); ri = P(rtri(inr - .068, .01, arcn), yf)
    roh = P(rtri(inr - .008, max(.045 - .008, .004), arcn), yrim); rih = P(rtri(inr - .068, .01, arcn), yrim)
    for k in range(m):
        k1 = (k + 1) % m
        quad(g, [roh[k], roh[k1], rih[k1], rih[k]], rim, Vector((0, -1, 0)))
        if lod < 2:
            quad(g, [ro[k], ro[k1], roh[k1], roh[k]], rim, Vector((0, 1, 0)).cross(ro[k1] - ro[k]))
        if lod == 0:
            quad(g, [ri[k], ri[k1], rih[k1], rih[k]], rim, (ri[k1] - ri[k]).cross(Vector((0, 1, 0))))
    if lod == 0:
        for z in (1.78, 2.02):
            box(g, (0, 0, z), (.036, .036, .01), steel_fn(1.0, S + 9, low=.2))
    elif lod == 1:
        box(g, (0, 0, 1.95), (.036, .036, .01), steel_fn(1.0, S + 9, low=.2))
    return g


# ================================================================ 9. Letterbox

def design_letterbox(rng, a):
    return dict(salt=rng.uniform(1, 90), tint=rng.uniform(.93, 1.07), pt=rng.uniform(.93, 1.07), lean=(rng.uniform(-.01, .01), rng.uniform(-.01, .01)))


def emit_letterbox(D, lod):
    g = L.Geo(); S = D['salt']
    pc = pine_fn(D['pt'], S)
    px = lambda p, n: pc(p, n)
    box(g, (0, 0, .52), (.05, .05, .58), px, grid=((1, 1, 4), (1, 1, 1), (1, 1, 1))[lod], skip=('-z',))
    z0 = 1.112
    red = paint_fn(BOX_RED, S + 2, .8, floor_z=z0)
    if lod < 2:
        box(g, (0, 0, 1.106), (.11, .09, .006), steel_fn(1.0, S + 3, low=.3), skip=('-z',))
        prof = [(-.125, 0), (.125, 0), (.125, .10), (.108, .175), (.0625, .23), (0, .25), (-.0625, .23), (-.108, .175), (-.125, .10)]
        extrude(g, prof, lambda u, v, d: Vector((u, d, z0 + v)), -.175, .175, red, segs=(3, 1)[lod], caps=(True, True))
        if lod == 0:
            fl = [(u * .93, .006 + v * .93) for u, v in prof]
            extrude(g, fl, lambda u, v, d: Vector((u, d, z0 + v)), -.187, -.175, paint_fn(BOX_RED, S + 4, .75, floor_z=z0), caps=(True, True))
            box(g, (0, -.195, z0 + .09), (.04, .008, .008), steel_fn(1.0, S + 5, low=.2))
            plate = lambda p, n: tint(SIGN_WHITE, lum(p, .08, .08, S + 6))
            dark = lambda p, n: tint((.04, .04, .04), lum(p, .2, .05, S + 7))
            box(g, (0, -.052, .85), (.09, .002, .05), plate, skip=('+y',))
            for dx, hz in ((-.04, .026), (0, .03), (.04, .022)):
                box(g, (dx, -.0545, .85), (.012, .001, hz), dark, skip=('+y',))
    else:
        box(g, (0, 0, z0 + .125), (.125, .175, .125), red, skip=('-z',))
    return g


def hulls_letterbox(D):
    return [('box', (0, 0, .52), (.052, .052, .58))]


# ================================================================ 10. Round hay bale (axis along X, lying on its curved side)

BR = .75; BHL = .6


def design_bale(rng, a):
    return dict(salt=rng.uniform(1, 90), tint=rng.uniform(.94, 1.06), ph=[rng.uniform(0, 6.28) for _ in range(3)], pitch=rng.uniform(.5, .6))


def emit_bale(D, lod):
    g = L.Geo(); S = D['salt']; ph = D['ph']
    sides = (28, 16, 12)[lod]
    xs = ([-BHL + 2 * BHL * i / 6 for i in range(7)], [-BHL, 0, BHL], [-BHL, BHL])[lod]
    cz = BR - .06

    def rad(a, x):
        bar = 1 - .016 * (x / BHL) ** 2 * (1 if lod == 0 else 0)
        return BR * bar * (1 + .018 * math.sin(3 * a + x * 4.1 + ph[0]) + .012 * math.sin(5 * a - x * 3.0 + ph[1]) + .006 * math.sin(7 * a + x * 6.3 + ph[2]))

    def col(p, n):
        if abs(n.x) > .6:     # the cut end: hay laid in a spiral, darker toward the middle
            rr = math.hypot(p.y, p.z - cz)
            sp = math.sin(rr * 21 + math.atan2(p.z - cz, p.y) * 1.0 + 3 * vnoise(p, .3, S + 7) + ph[1])
            c = mix(STRAW, STRAW_TOP, .35 + .3 * (1 - rr / BR))
            return tint(c, D['tint'] * (1 + .13 * sp) * lum(p, .22, .1, S + 8))
        a = math.atan2(p.z - cz, p.y)
        s = a * BR
        P_ = D['pitch'] * (1 + .25 * (vnoise(p, .5, S) - .5))
        dia = math.cos(math.tau * (s + p.x) / P_) * math.cos(math.tau * (s - p.x) / P_)
        topw = smoothstep(-.1, .85, n.z) * (.7 + .5 * (vnoise(p, .3, S + 2) - .3))
        c = mix(STRAW, STRAW_TOP, clamp(topw))
        return tint(c, D['tint'] * (1 + .20 * dia) * lum(p, .26, .12, S + 3))

    def pos(a, x, r=None):
        rr = rad(a, x) if r is None else r
        return Vector((x, rr * math.cos(a), cz + rr * math.sin(a)))
    verts = []; cols = []; uvs = []; nrms = []
    for i, x in enumerate(xs):
        for j in range(sides):
            a = math.tau * j / sides + math.pi / sides
            p = pos(a, x); n_ = Vector((0, math.cos(a), math.sin(a)))
            verts.append(p); cols.append(col(p, n_)); uvs.append((j / sides, x)); nrms.append(n_)
    faces = [(i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j) for i in range(len(xs) - 1) for j in range(sides)]
    # orient: normal should point out radially
    f0 = faces[0]
    nn = (verts[f0[1]] - verts[f0[0]]).cross(verts[f0[2]] - verts[f0[0]])
    if nn.dot(nrms[f0[0]]) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    g.add(verts, faces, cols, uvs, 0, nrms)
    # dished ends: edge ring, a recessed ring, centre
    for sg in (1, -1):
        x_e = sg * BHL
        e0 = [pos(math.tau * j / sides + math.pi / sides, x_e) for j in range(sides)]
        if lod == 0:
            e1 = [pos(math.tau * j / sides + math.pi / sides, x_e - sg * .04, BR * .62) for j in range(sides)]
            ctr = Vector((x_e - sg * .075, 0, cz))
            nrm = Vector((sg, 0, 0))
            for j in range(sides):
                j1 = (j + 1) % sides
                quad(g, [e0[j], e0[j1], e1[j1], e1[j]], col, nrm)
                geo_v = [e1[j], e1[j1], ctr]
                g.oriented(geo_v, [col(v, nrm) for v in geo_v], [(v.y, v.z) for v in geo_v], 0, nrm)
        elif lod == 1:
            ctr = Vector((x_e - sg * .05, 0, cz)); nrm = Vector((sg, 0, 0))
            for j in range(sides):
                j1 = (j + 1) % sides
                geo_v = [e0[j], e0[j1], ctr]
                g.oriented(geo_v, [col(v, nrm) for v in geo_v], [(v.y, v.z) for v in geo_v], 0, nrm)
        else:
            fan(g, e0, col, Vector((sg, 0, 0)))
    return g


def hulls_bale(D):
    return [('cyl', (-BHL, 0, BR - .06), (BHL, 0, BR - .06), BR * 1.05, 12)]


DESIGNS = {'Fence': (design_fence, emit_fence, hulls_fence), 'Strainer': (design_strainer, emit_strainer, hulls_strainer),
           'Gate': (design_gate, emit_gate, hulls_gate), 'CattleStop': (design_cattle, emit_cattle, hulls_cattle),
           'Culvert': (design_culvert, emit_culvert, hulls_culvert), 'Trough': (design_trough, emit_trough, hulls_trough),
           'PowerPole': (design_pole, emit_pole, hulls_pole), 'SignPost': (design_sign, emit_sign, hulls_sign),
           'GiveWay': (design_giveway, emit_giveway, hulls_sign), 'Letterbox': (design_letterbox, emit_letterbox, hulls_letterbox),
           'HayBale': (design_bale, emit_bale, hulls_bale)}


# ================================================================ build

def tris(g):
    return sum(len(f) - 2 for f in g.f)


def build_asset(a, mats, coll):
    seed = seed_of(a)
    rng = random.Random(seed)
    design, emit, hullf = DESIGNS[a['family']]
    D = design(rng, a)
    band = a.get('min_z_band')
    obs = []; rows = []; hull_obs = []
    for lod in range(3):
        g = emit(D, lod)
        mn = min(v.z for v in g.v)
        if band is None and abs(mn - ROOT_Z) > .004:
            print('NOTE %s LOD%d lowest vertex %.3f m: shifting the mesh to the 6 cm root rule' % (a['asset'], lod, mn))
            for v in g.v:
                v.z += ROOT_Z - mn
        name = '%s_LOD%d' % (a['asset'], lod)
        ob, dropped = L.to_object(g, name, mats, [0], coll)
        n = len(ob.data.loop_triangles)
        print('LOD', name, n, 'of', a['budget'][lod], 'size', [round(x, 2) for x in ob.dimensions], 'minz %.3f' % min(v.co.z for v in ob.data.vertices), 'dropped', dropped)
        assert n <= a['budget'][lod], '%s: %d triangles over the LOD%d ceiling %d' % (name, n, lod, a['budget'][lod])
        if band is not None:
            mz = min(v.co.z for v in ob.data.vertices)
            assert band[0] <= mz <= band[1], '%s: lowest vertex %.3f outside its band %s' % (name, mz, band)
        ob['kit'] = L.KIT; ob['lod'] = lod; ob['seed'] = seed
        ob['placement'] = 'Ground pivot at the origin; roots/footings below ground.' + (' Convex UCX hulls in the LOD0 FBX.' if a['hulls'] else ' No collision.')
        hs = []
        if lod == 0:
            hs = make_hulls(name, hullf(D), coll)
            assert len(hs) == a['hulls'], (a['asset'], len(hs), a['hulls'])
            hull_obs = hs
        L.export(ob, hs)
        extra = dict(farm_part_triangles=tris(g))
        if band is not None:
            extra['min_z_band'] = list(band)
        rows.append(L.manifest_row(ob, a['asset'], a['family'], a['variant'], lod, [0], seed, g.counts, len(hs), a['budget'][lod], extra))
        obs.append(ob)
    for i in range(2):
        assert rows[i]['triangles'] > rows[i + 1]['triangles'], (a['asset'], [r['triangles'] for r in rows])
    print('BUILT', a['asset'], [r['triangles'] for r in rows], rows[0]['size_m'], 'minz', [r['min_z_m'] for r in rows], 'hulls', len(hull_obs))
    return obs, rows, hull_obs


# ================================================================ review helpers

def rect_floor(scene, name, rects, mat, z):
    verts = []; faces = []
    for (x0, x1, y0, y1) in rects:
        b = len(verts)
        verts += [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]; faces.append((b, b + 1, b + 2, b + 3))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    return ob


def floor_holes(scene, mat, holes=(), size=600.0, z=-.07, centre=(0.0, 0.0)):
    """The review floor with rectangular holes (x0, x1, y0, y1) cut out, so a buried part (the pit, the culvert) can be seen."""
    h = size / 2
    rects = [(centre[0] - h, centre[0] + h, centre[1] - h, centre[1] + h)]
    for hx0, hx1, hy0, hy1 in holes:
        new = []
        for (x0, x1, y0, y1) in rects:
            if hx1 <= x0 or hx0 >= x1 or hy1 <= y0 or hy0 >= y1:
                new.append((x0, x1, y0, y1)); continue
            if hx0 > x0:
                new.append((x0, hx0, y0, y1))
            if hx1 < x1:
                new.append((hx1, x1, y0, y1))
            ax0, ax1 = max(x0, hx0), min(x1, hx1)
            if hy0 > y0:
                new.append((ax0, ax1, y0, hy0))
            if hy1 < y1:
                new.append((ax0, ax1, hy1, y1))
        rects = new
    return rect_floor(scene, scene.name + ' Floor', rects, mat, z)


def culvert_bank(scene, x, y):
    """Review-only: the road embankment the culvert is buried in, cut in half along the pipe so the pipe shows (an earth block behind y), and
    the ditch it drains into (a bed .95 m down with a sloped near bank and walls, so nothing shows through the hole in the floor)."""
    earth = L.flat_material('Review | Embankment', (.06, .045, .028), roughness=.95)
    ditch = L.flat_material('Review | Ditch', (.05, .04, .026), roughness=.95)
    x0, x1, y0, y1, z0, z1 = x - 1.0, x + 1.2, y, y + 2.4, -.95, 0.0
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new('Review embankment'); me.from_pydata(v, [], f); me.materials.append(earth)
    ob = bpy.data.objects.new(me.name, me); scene.collection.objects.link(ob)
    a0, a1, ye, ys, yf, zb, zt = x - 2.4, x + 1.9, y - 3.4, y - 1.3, y + 2.6, -.95, -.07
    tv = [(a0, ys, zb), (a1, ys, zb), (a1, yf, zb), (a0, yf, zb), (a0, ye, zt), (a1, ye, zt), (a1, yf, zt), (a0, yf, zt)]
    tf = [(0, 1, 2, 3), (4, 5, 1, 0), (3, 2, 6, 7), (4, 0, 3, 7), (5, 6, 2, 1)]
    me2 = bpy.data.meshes.new('Review ditch'); me2.from_pydata(tv, [], tf); me2.materials.append(ditch)
    ob2 = bpy.data.objects.new(me2.name, me2); scene.collection.objects.link(ob2)


def detail_view(ob, name, path, fig_mat, fig_at=None, k=None, el=None, holes=(), bank=None, az=-45):
    """Three-quarter close view in its own scene (floor with holes where something is buried), framed like the kit's detail renders."""
    scene = L.review_scene('Farm Detail ' + name)
    chalk = L.flat_material('Review | Chalk', (.19, .225, .21))
    floor_holes(scene, chalk, holes)
    if bank:
        culvert_bank(scene, *bank)
    L.display_copy(scene, ob, 'Detail_' + name)
    lo, hi = B.bbox(ob)
    small = hi.z < 1.5
    if fig_at is not None:
        fx, fy = fig_at
        L.figure(scene, (fx, fy, 0), mat=fig_mat)
        lo = Vector((min(lo.x, fx - .3), lo.y, lo.z)); hi = Vector((hi.x, hi.y, max(hi.z, 1.8)))
    centre = (lo + hi) / 2
    rad = (hi - lo).length / 2
    el = D2R(el if el is not None else (30 if small else 16))
    az = D2R(az)
    back = Vector((math.sin(-az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    right = Z.cross(back).normalized(); up = back.cross(right).normalized()
    th = 36 / 2 / 50; tv = (36 * 1200 / 1400) / 2 / 50
    d = 0.0
    for cx in (lo.x, hi.x):
        for cy in (lo.y, hi.y):
            for cz in (lo.z, hi.z):
                q = Vector((cx, cy, cz)) - centre
                d = max(d, q.dot(back) + abs(q.dot(right)) / th, q.dot(back) + abs(q.dot(up)) / tv)
    L.camera(scene, centre + back * d * (k if k is not None else .9), centre, lens=50)
    L.studio_lights(scene, Vector((centre.x, centre.y, 0)), max(.35, rad / 6))
    L.render(scene, path, 1400, 1200)
    return path


ROW_A = ['SM_NZ_PowerPole', 'SM_NZ_Strainer', 'SM_NZ_Gate_3m6', 'SM_NZ_Fence_4m']
ROW_B = ['SM_NZ_CattleStop', 'SM_NZ_Culvert', 'SM_NZ_Trough', 'SM_NZ_SignPost', 'SM_NZ_GiveWay', 'SM_NZ_Letterbox', 'SM_NZ_HayBale']
LINE_LABELS = {'SM_NZ_PowerPole': ('POWER POLE', ''), 'SM_NZ_Strainer': ('STRAINER', 'ASSEMBLY'), 'SM_NZ_Gate_3m6': ('FARM GATE', '3.6 M'),
               'SM_NZ_Fence_4m': ('FENCE', '4 M MODULE'), 'SM_NZ_CattleStop': ('CATTLE STOP', ''), 'SM_NZ_Culvert': ('CULVERT', 'HALF SUNK'),
               'SM_NZ_Trough': ('TROUGH', ''), 'SM_NZ_SignPost': ('ROAD NAME', 'SIGN'), 'SM_NZ_GiveWay': ('GIVE WAY', 'SIGN'),
               'SM_NZ_Letterbox': ('LETTERBOX', ''), 'SM_NZ_HayBale': ('HAY BALE', '')}


LINE_YAW = {'SM_NZ_HayBale': -50.0}


def farm_lineup(lod0):
    scene = L.review_scene('Farm Lineup')
    ink = L.flat_material('Review | Ink', (.70, .78, .70), .8); muted = L.flat_material('Review | Secondary', (.44, .53, .47), .8)
    chalk = L.flat_material('Review | Chalk', (.19, .225, .21)); fig = L.flat_material('Review | Figure', (.55, .36, .16))
    tilt = D2R(14)
    rot_txt = (math.pi / 2 - tilt, 0, 0)
    holes = []; bank = None
    width = 0.0
    for names, y0, wmin in ((ROW_A, 0.0, 3.4), (ROW_B, -17.0, 1.4)):
        x = 0.0
        L.figure(scene, (x, y0, 0), mat=fig); x += 1.9
        for name in [n for n in names if n in lod0]:
            ob = lod0[name]; lo, hi = B.bbox(ob)
            w = max(hi.x - lo.x, wmin)
            lx = x + (w - (hi.x - lo.x)) / 2 - lo.x
            L.display_copy(scene, ob, name.replace('SM_NZ_', 'Lineup_'), (lx, y0, 0), D2R(LINE_YAW.get(name, 0.0)))
            mid = x + w / 2
            if name == 'SM_NZ_CattleStop':
                holes.append((lx - .9, lx + .9, y0 - 1.5, y0 + 1.5))
            if name == 'SM_NZ_Culvert':
                holes.append((lx - 2.4, lx + 1.9, y0 - 3.4, y0 + 2.6)); bank = (lx, y0)
            a1, a2 = LINE_LABELS[name]
            d = (3.2, 5.0, 6.8) if y0 == 0 else ((5.0, 6.8, 8.6) if name == 'SM_NZ_Culvert' else (3.6, 5.4, 7.2))
            L.text_obj(scene, a1, (mid, y0 - d[0], 0), .5, ink, rot_txt)
            if a2:
                L.text_obj(scene, a2, (mid, y0 - d[1], 0), .38, ink, rot_txt)
            if name == 'SM_NZ_CattleStop':
                val = '3.6 x 2.4 m  pit .4 deep'
            elif name == 'SM_NZ_Culvert':
                val = '600 mm  3 m  headwall 1.6 x 1.0'
            elif name == 'SM_NZ_Fence_4m':
                val = '1.2 m posts  7 wires'
            else:
                val = '%.2f m' % hi.z
            L.text_obj(scene, val, (mid, y0 - d[2], 0), .3, muted, rot_txt)
            x += w + 1.5
        L.figure(scene, (x + .1, y0, 0), mat=fig)
        width = max(width, x + 1.2)
    floor_holes(scene, chalk, holes, size=900, centre=(width / 2, -6))
    if bank:
        culvert_bank(scene, *bank)
    top = 11.4
    L.text_obj(scene, 'GRAND TOUR / NATIVE PLANTS / SOUTHLAND FARM HARDWARE', (.4, 6.0, top), .7, ink, rot_txt, 'LEFT')
    L.text_obj(scene, 'S2a   11 MESHES   TRUE SCALE   MODELLED GEOMETRY   THREE LODS   POSTS 1.8 M   HEIGHTS ABOVE GROUND', (.4, 6.0, top - 1.2), .42, muted, rot_txt, 'LEFT')
    L.studio_lights(scene, Vector((width / 2, -6, 0)), 6.0)
    vtop = top * math.cos(tilt) + 1.2; vbot = -(17 + 9.2) * math.sin(tilt) - .8
    ortho = width + 1.5
    target = Vector((width / 2, ((vtop + vbot) / 2) / math.sin(tilt), 0))
    L.camera(scene, target + Vector((0, -math.cos(tilt), math.sin(tilt))) * 200, target, ortho=ortho)
    return scene, int(2000 * (vtop - vbot) / ortho) + 8


# ================================================================ assembly: a paddock gateway off a gravel track

def assembly_gateway(lod0):
    """A paddock gateway off a gravel farm track, seen from the track at 30 m (35 mm, eye 1.6 m, overcast, exposure 1.8). The fence line runs
    across the track: Strainer at the west end, 2 + 8 Fence_4m modules, the closed gate (hinge post at x -6), the cattle stop in the track
    (turned to run along it), a strainer at the far east end; the letterbox and road-name sign at the track mouth, the power pole with its
    stay, a trough 15 m into the paddock with 3 hay bales; the kit's Beech_Edge x3 and DeadSpar x1 form the bush wall behind (with a Beech
    stand closing it and a crown-fern margin), VergeTussock and Gorse along the fence foot."""
    bush = V.append_from('GrandTour_NativePlants.blend', ['SM_NZ_Beech_Edge_LOD0', 'SM_NZ_Beech_Pole_LOD0', 'SM_NZ_Beech_Mature_LOD0', 'SM_NZ_DeadSpar_LOD0',
                                                          'SM_NZ_CrownFern_B_LOD0', 'SM_NZ_CrownFern_C_LOD0', 'SM_NZ_TreeFern_A_LOD0', 'SM_NZ_TreeFern_Young_LOD0'])
    verge = V.append_from('GrandTour_NativePlants_Verge.blend', ['SM_NZ_VergeTussock_A_LOD0', 'SM_NZ_VergeTussock_B_LOD0', 'SM_NZ_Gorse_A_LOD0', 'SM_NZ_Gorse_B_LOD0'])
    have = dict(lod0); have.update(bush); have.update(verge)
    scene = L.review_scene('Gateway Assembly')
    F.overcast_world(scene, 'NZ Gateway Overcast', 1.8)
    rng = random.Random(59000 + 9001)
    st = V.Stage(scene, have, rng, 'Gw_')
    grass = L.material('Assembly | Grazed grass', (.068, .15, .028))
    grass.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .95
    try:
        # fine grain (a luminance multiply) and a little bump from one noise, so the pasture and the gravel are not a smooth painted sheet
        nt = grass.node_tree
        vc = next(n for n in nt.nodes if n.type == 'VERTEX_COLOR'); bsdf = nt.nodes['Principled BSDF']
        tc = nt.nodes.new('ShaderNodeTexCoord'); tex = nt.nodes.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 70.0; tex.inputs['Detail'].default_value = 10.0; tex.inputs['Roughness'].default_value = .7
        nt.links.new(tc.outputs['Object'], tex.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = .30; mr.inputs['From Max'].default_value = .70; mr.inputs['To Min'].default_value = .55; mr.inputs['To Max'].default_value = 1.4
        nt.links.new(tex.outputs['Fac'], mr.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
        mx.inputs[0].default_value = 1.0
        ia = next(i for i in mx.inputs if i.identifier == 'A_Color'); ib = next(i for i in mx.inputs if i.identifier == 'B_Color')
        nt.links.new(vc.outputs['Color'], ia); nt.links.new(mr.outputs['Result'], ib)
        nt.links.new(next(o for o in mx.outputs if o.identifier == 'Result_Color'), bsdf.inputs['Base Color'])
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = .6; bp.inputs['Distance'].default_value = .04
        nt.links.new(tex.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
    except Exception as e:
        print('NOTE terrain grain nodes skipped:', e)
    cx = -.1
    tx = lambda y: cx + .7 * math.sin(y / 17.0) * smoothstep(6, 22, abs(y))
    pit = (cx - 1.55, cx + 1.55, -.95, .95)
    fine_x = [cx - 2.25 + .25 * i for i in range(19)]
    fine_y = [-1.5 + .25 * i for i in range(13)]
    fine_tx = [cx - 4.5 + .25 * i for i in range(37)]
    fine_ty = [-40.0 + .5 * i for i in range(101)]
    xs = sorted(set(V.grid_axes([-250, -150, -90, -60, 50, 80, 120, 200, 300], None, -40, 46, 1.0)) | set(fine_x) | set(fine_tx))
    ys = sorted(set(V.grid_axes([-90, -70, -55, 70, 90, 120, 160, 220, 300], None, -45, 56, 1.0)) | set(fine_y) | set(fine_ty))

    def zfn(x, y):
        z = (.05 * math.sin(x * .09 + y * .05) + .03 * math.sin(x * .31 - y * .17)) * smoothstep(1.2, 6.0, abs(y)) * smoothstep(2.4, 5.0, abs(x - tx(y)))
        z -= .02 * (1 - smoothstep(2.4, 5.0, abs(x - tx(y))))
        if pit[0] < x < pit[1] and pit[2] < y < pit[3]:
            z = -.5
        return z, 0, 0

    def cfn(x, y, z, tag, u):
        lum_ = 1 + .14 * (2 * vnoise(Vector((x, y, 0)), 2.2, 4.0) - 1) + .07 * (2 * hnoise(Vector((x, y, 0)), 6.0) - 1)
        c = scale_col((.068, .15, .028), lum_)
        edge = smoothstep(2.5, 4.5, abs(x - tx(y)))
        c = mix(scale_col((.10, .12, .05), lum_), c, edge)
        # the gravel track: speckled grey, darker wheel lines, an irregular edge, a grassy crown away from the gateway
        d = abs(x - tx(y)); nz = vnoise(Vector((x, y, 0)), .7, 11.0)
        mask = 1 - smoothstep(1.7 + .25 * nz, 2.2 + .35 * nz, d)
        ruts = (1 - smoothstep(.15, .4, abs(d - 1.0))) * (.5 + .5 * nz)
        crown = (1 - smoothstep(.2, .55, d)) * smoothstep(8, 20, abs(y))
        grav = scale_col((.30, .28, .24), (.72 + .5 * hnoise(Vector((x * 4, y * 4, 0)), 3.0) + .25 * (nz - .5)) * (1 - .45 * ruts))
        c = mix(c, grav, mask)
        c = mix(c, scale_col((.09, .13, .05), lum_), crown * .75 * mask)
        c = mix(c, scale_col((.11, .12, .05), lum_), smoothstep(36, 42, y) * .8)          # rank dry grass in front of the bush
        return mix(c, scale_col((.035, .03, .02), lum_), smoothstep(43, 49, y))            # the bush floor under the wall
    F.terrain_grid(scene, 'Gateway paddock', xs, ys, zfn, cfn, grass)
    # a far dark bush mass closes the horizon behind the trunk stand
    dark = L.flat_material('Assembly | Distant bush', (.03, .045, .025), roughness=1.0)
    bm = bpy.data.meshes.new('Distant bush'); bm.from_pydata([(-700, 250, -1), (700, 250, -1), (700, 250, 45), (-700, 250, 45)], [], [(0, 1, 2, 3)]); bm.materials.append(dark)
    scene.collection.objects.link(bpy.data.objects.new('Distant bush', bm))
    # the fence line
    st.put('SM_NZ_Strainer', -14.0, 0.0, 0.0, 1.0, record=False)
    for i, x in enumerate([-14.0, -10.0] + [1.9 + 4 * k for k in range(8)]):
        st.put('SM_NZ_Fence_4m', x + rng.uniform(-.02, .02), rng.uniform(-.02, .02), rng.uniform(-.012, .012), 1.0, record=False)
    st.put('SM_NZ_Strainer', 33.9, 0.0, math.pi, 1.0, record=False)
    st.put('SM_NZ_Gate_3m6', -6.0, 0.0, 0.0, 1.0, record=False)
    st.put('SM_NZ_CattleStop', cx, 0.0, math.pi / 2, 1.0, record=False)
    st.put('SM_NZ_Letterbox', cx + 2.8, -7.5, rng.uniform(-.08, .08), 1.0, record=False)
    st.put('SM_NZ_SignPost', cx + 3.1, -13.0, rng.uniform(-.08, .08), 1.0, record=False)
    st.put('SM_NZ_PowerPole', cx + 7.5, -5.0, 0.0, 1.0, record=False)
    st.put('SM_NZ_Trough', -9.5, 15.0, rng.uniform(0, 6.28), 1.0, record=False)
    for x, y in ((-6.7, 17.2), (-12.6, 13.4), (-6.2, 12.0)):
        st.put('SM_NZ_HayBale', x, y, rng.uniform(0, math.pi), 1.0, record=False)
    # fence-foot vegetation: rank tussock all along it, gorse at the strainer and out east
    st.scatter(['SM_NZ_VergeTussock_A', 'SM_NZ_VergeTussock_B'], [.5, .5], 60, (-15.5, 34.5, -.7, .7), .45, (.9, 1.3), tries=9000, overlap=.35,
               avoid=lambda x, y: (-6.5 < x < 2.4))
    for nm, x, y in (('SM_NZ_Gorse_B', -15.4, .9), ('SM_NZ_Gorse_A', -11.0, -.9), ('SM_NZ_Gorse_B', 14.5, .9), ('SM_NZ_Gorse_A', 24.0, -.8), ('SM_NZ_Gorse_B', 31.5, .8)):
        st.put(nm, x, y, None, rng.uniform(.95, 1.08), 1.3)
    # rank tussock along both edges of the track and out in the paddock around the trough and bales
    st.scatter(['SM_NZ_VergeTussock_A', 'SM_NZ_VergeTussock_B'], [.5, .5], 44, (cx - 4.2, cx + 4.2, -40, 30), .5, (.9, 1.25), tries=9000, overlap=.3,
               avoid=lambda x, y: abs(x - tx(y)) < 2.5 or abs(y) < 2.0)
    st.scatter(['SM_NZ_VergeTussock_A', 'SM_NZ_VergeTussock_B'], [.5, .5], 40, (-24, 22, 4, 44), .5, (.9, 1.3), tries=7000, overlap=.3,
               avoid=lambda x, y: math.hypot(x + 9.5, y - 15) < 4.0 or abs(x - tx(y)) < 2.8)
    # the bush wall behind: the front trees, the margin ferns and rank grass, the stand that closes it
    for nm, x, yy in (('SM_NZ_Beech_Edge', -24.0, 47.0), ('SM_NZ_Beech_Edge', 2.0, 50.0), ('SM_NZ_Beech_Edge', 26.0, 47.5), ('SM_NZ_DeadSpar', 13.0, 49.0)):
        yaw = -math.pi / 2 + rng.uniform(-.4, .4) if nm == 'SM_NZ_Beech_Edge' else rng.uniform(0, math.tau)
        st.put(nm, x, yy, yaw, rng.uniform(.95, 1.05), record=False)
    for i in range(int(130 / 1.3)):
        x = -65 + 1.3 * i + rng.uniform(-.4, .4)
        for j in range(4):
            st.put('SM_NZ_CrownFern_B' if rng.random() < .6 else 'SM_NZ_CrownFern_C', x, 44.5 + 1.4 * j + rng.uniform(-.5, .5), None, rng.uniform(.95, 1.3), record=False)
    for k in range(9):
        st.put(('SM_NZ_TreeFern_A', 'SM_NZ_TreeFern_Young')[k % 2], -50 + k * 12 + rng.uniform(-3, 3), rng.uniform(44, 50), None, rng.uniform(.9, 1.15), record=False)
    st.scatter(['SM_NZ_VergeTussock_A', 'SM_NZ_VergeTussock_B'], [.5, .5], 70, (-50, 50, 41, 46), .5, (1.0, 1.4), tries=9000, overlap=.35)
    V.beech_wall(st, rng, -90, 90, 52.0, 84.0, 2.5)
    V.beech_wall(st, rng, -130, 130, 88.0, 150.0, 4.2)
    V.beech_wall(st, rng, -250, 250, 156.0, 230.0, 8.0)
    L.studio_lights(scene, (0, 25, 0), 8.0, energy=.5)
    eye = Vector((cx - 1.0, -30.0, 1.6))
    tgt = Vector((cx - 1.0, 0.0, 1.6)) + Vector((0, 0, 30 * math.tan(D2R(3))))
    L.camera(scene, eye, tgt, lens=35)
    print('GATEWAY ASSEMBLY', st.counts)
    return scene, st.counts


# ================================================================ renders and main

FIG_SKIP = set()


def render_all(lod0, assets, only, no_assembly, t0):
    renders = []
    if only is None and not ASM_ONLY:
        s1, h = farm_lineup(lod0)
        renders.append(L.render(s1, OUT / 'Lineup_Farm.png', 2000, h))
        print('RENDERED Lineup', '%.1fs' % (time.time() - t0))
    fig = L.flat_material('Review | Figure', (.55, .36, .16))
    for a in ([] if (ASM_ONLY or LINEUP_ONLY) else assets):
        nm = a['asset'].replace('SM_NZ_', '')
        ob = lod0[a['asset']]
        lo, hi = B.bbox(ob)
        kw = dict(fig_at=(lo.x - .7, (lo.y + hi.y) / 2))
        if a['asset'] == 'SM_NZ_CattleStop':
            kw.update(holes=[(-.9, .9, -1.5, 1.5)], el=38, k=.95)
        if a['asset'] == 'SM_NZ_Culvert':
            kw.update(holes=[(-2.4, 1.9, -3.4, 2.6)], bank=(0.0, 0.0), el=26, k=.95, az=42, fig_at=(lo.x - .9, -3.9))
        if a['asset'] in ('SM_NZ_Fence_4m', 'SM_NZ_Gate_3m6', 'SM_NZ_Strainer'):
            kw.update(k=.92, el=14)
        if a['asset'] == 'SM_NZ_PowerPole':
            kw.update(k=.98)
        renders.append(detail_view(ob, nm, OUT / ('Detail_%s.png' % nm), fig, **kw))
        print('RENDERED Detail', nm, '%.1fs' % (time.time() - t0))
    if only is None and not no_assembly and not LINEUP_ONLY:
        sc_, counts = assembly_gateway(lod0)
        renders.append(L.render(sc_, OUT / 'Assembly_Gateway.png', 2000, 1333))
        print('RENDERED Assembly_Gateway.png', '%.1fs' % (time.time() - t0))
    return renders


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene; scene.name = 'Native Farm Assets - metres'
    mats = L.plant_materials()
    coll = scene.collection
    lod0 = {}; rows = []
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
        L.mark_asset(obs[0], a['label'] + ' / vertex-colour hard-surface geometry / 3 LODs', ['Native', 'NZ', a['family'], 'Southland', 'Farm', 'Grand Tour'])
        lod0[a['asset']] = obs[0]
    if ONLY is None:
        L.write_manifest(rows, set_name='farm', extra=dict(farm_stage='S2a', farm_seeds={a['asset']: seed_of(a) for a in assets},
                         farm_lod_rule='one design per asset from seed 59000 + 97 k. Every structural member is kept at every LOD; the sides of round members (posts 12/8/6, bars 8/6/4, wires 3), the rings along them, the grid of each concrete face (vertex colour), the corrugation (pipe pitch 7.5 cm / 15 cm / smooth), the sign lettering (8 blocks / 2 / 1) and the small fittings (weld collars, wire wraps, clamps, hinge eyes) step down. Hulls: UCX convex prisms in the LOD0 FBX. Rows with min_z_band (cattle stop, culvert) are partly buried and are validated against that band instead of the 6 cm root rule'))
        print('MANIFEST', len(rows), 'rows', '%.1fs' % (time.time() - t0))
    else:
        print('PARTIAL RUN (--only): manifest.json left alone')
    renders = []
    if not NO_RENDER:
        renders += render_all(lod0, assets, ONLY, NO_ASSEMBLY, t0)
    try:
        bpy.context.window.scene = bpy.data.scenes['Native Farm Assets - metres']
    except Exception:
        pass
    if ONLY is None:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'GrandTour_NativePlants_Farm.blend'))
    for b in OUT.glob('*.blend1'):
        b.unlink()
    for p in renders:
        print('RENDER', p)
    print('NATIVE_FARM_BUILD_OK', len(assets), 'meshes', len(rows), 'lods', '%.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
