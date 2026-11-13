"""GP1 grass clump set (docs/LIDAR_PLACE_PLAN.md GP1-GP3) on the native plant kit's pipeline: SM_NZ_PastureClump_S/M/L (grazed
ryegrass and clover, 25/40/60 cm across) and SM_NZ_RankClump_A/B (rank ungrazed grass with seed-head stalks, 50/70 cm across) as
deterministic Blender geometry, TWO authored LODs each, FBX (cm) + GLB (m), manifest rows (set 'grass'), the set .blend and review renders.

Run: blender -b --factory-startup --python-exit-code 1 --python build_southland_grass.py [-- --only X,Y --no-render --no-assembly --assembly-only]

LOD0 is the full clump (blades are narrow tapering strips; pasture clumps add clover petioles with a three-leaflet head, rank clumps add
seed-head stalks with 4-5 spikelet quads); LOD1 is a six-blade cross of wider strips at 60 degree steps that keeps the silhouette and
the colour mix (rank LOD1 keeps a few single-quad seed stalks so the straw-headed top survives). Every asset is designed once from its
fixed seed (60000 + 97 k) and the footprint is solved so the larger horizontal extent equals the stated across-size.

Vertex colour: linear FLOAT_COLOR `Color`. Its alpha is a wind weight (0 at the blade base, 1 at the tip; heads 1): L.to_object writes
the per-vertex list of this script's GG geometry buffer.

Ground rule: the lowest vertex of every LOD is 2 cm below the ground plane (not the kit's 6 cm: the clumps are 8-14 cm tall, so a 6 cm
root would spend half of every blade underground); the manifest rows declare min_z_band [-.03, -.01] for the validator.
"""
import bpy, sys, math, random, json, time
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_plant_lib as L
import build_native_bush as B
import build_southland_floor as F
from native_plant_lib import Z, clamp, lerp, mix, scale_col, smoothstep, polar, rot, hnoise, vnoise

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ONLY = set(ARGS[ARGS.index('--only') + 1].split(',')) if '--only' in ARGS else None
NO_RENDER = '--no-render' in ARGS
NO_ASSEMBLY = '--no-assembly' in ARGS
ASM_ONLY = '--assembly-only' in ARGS
OUT = L.OUT
D2R = math.radians
ROOT_Z = -.02
UN = 60                      # samples of the unit blade path (divisible by every segment count used: 2, 3, 4, 5)

# ---------------------------------------------------------------- colours (linear RGB; tint is luminance only, .9-1.1 per blade)
P_BASE = (.06, .12, .02); P_TIP = (.24, .33, .08); CLOVER = (.10, .20, .04); P_STRAW = (.40, .34, .16)
R_BASE = (.08, .15, .03); R_TIP = (.30, .32, .12); R_STRAW = (.42, .36, .16); R_HEAD = (.55, .50, .30)
R_STALK = (.30, .30, .115)

ASSETS = [
    dict(asset='SM_NZ_PastureClump_S', family='PastureClump', variant='S', label='PASTURE CLUMP', sub='S', kind='pasture', across=.25, n=12, H=(.08, .11),
         tufts=1, reach=.105, segs=4, budget=(120, 24), lod1=dict(segs=2, width=.012)),
    dict(asset='SM_NZ_PastureClump_M', family='PastureClump', variant='M', label='PASTURE CLUMP', sub='M', kind='pasture', across=.40, n=20, H=(.09, .13),
         tufts=3, reach=.115, segs=4, budget=(200, 36), lod1=dict(segs=3, width=.015)),
    dict(asset='SM_NZ_PastureClump_L', family='PastureClump', variant='L', label='PASTURE CLUMP', sub='L', kind='pasture', across=.60, n=30, H=(.10, .14),
         tufts=4, reach=.135, segs=4, budget=(300, 48), lod1=dict(segs=4, width=.019)),
    dict(asset='SM_NZ_RankClump_A', family='RankClump', variant='A', label='RANK CLUMP', sub='A', kind='rank', across=.50, n=24, H=(.30, .38),
         stalks=6, head_q=[4, 4, 4, 4, 4, 4], segs=5, budget=(300, 60), lod1=dict(segs=4, width=.026, stalks=4)),
    dict(asset='SM_NZ_RankClump_B', family='RankClump', variant='B', label='RANK CLUMP', sub='B', kind='rank', across=.70, n=32, H=(.40, .45),
         stalks=8, head_q=[4, 5, 4, 4, 5, 4, 4, 4], segs=5, budget=(400, 80), lod1=dict(segs=4, width=.030, stalks=8)),
]
for _k, _a in enumerate(ASSETS):
    _a['k'] = _k


def seed_of(a):
    return 60000 + 97 * a['k']


def rhu(x):
    return int(math.floor(x + .5))


# ---------------------------------------------------------------- geometry buffer with vertex alpha

class GG(L.Geo):
    """The kit's Geo plus a per-vertex alpha list `a` (wind weight), 1.0 unless set_alpha() overwrites it."""

    def __init__(self):
        super().__init__()
        self.a = []

    def add(self, verts, faces, colours, uvs, mi, radial=None):
        n0 = len(self.v)
        s = super().add(verts, faces, colours, uvs, mi, radial)
        self.a.extend([1.0] * (len(self.v) - n0))
        return s


def tris(g):
    return sum(len(f) - 2 for f in g.f)


# ---------------------------------------------------------------- blade shape

def unit_path(t0, arch, p=1.5, n=UN):
    """Unit-arclength polyline (h, z): the tilt from vertical goes t0 -> t0 + arch as s^p (the bend concentrates toward the tip)."""
    h = z = 0.0
    out = [(0.0, 0.0)]
    for i in range(n):
        s = (i + .5) / n
        t = t0 + arch * s ** p
        h += math.sin(t) / n; z += math.cos(t) / n
        out.append((h, z))
    return out


def reach_ratio(t0, arch, p):
    pts = unit_path(t0, arch, p)
    return pts[-1][0] / max(z for _, z in pts)


def solve_t0(rho, arch, p, tmax):
    lo = D2R(2); hi = max(D2R(3), min(D2R(82), tmax - arch))
    if reach_ratio(hi, arch, p) <= rho:
        return hi
    if reach_ratio(lo, arch, p) >= rho:
        return lo
    for _ in range(26):
        mid = (lo + hi) / 2
        if reach_ratio(mid, arch, p) < rho:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def shape_for(top, reach, arch, p=1.5, tmax=D2R(100)):
    """A blade whose highest point is `top` metres above ground and whose horizontal reach is `reach` (the path starts at ROOT_Z)."""
    rho = reach / (top - ROOT_Z)
    t0 = solve_t0(rho, arch, p, tmax)
    zmax = max(z for _, z in unit_path(t0, arch, p))
    return dict(t0=t0, arch=arch, p=p, sc=(top - ROOT_Z) / zmax)


def shape_flat(length, t0, arch, p=1.5):
    return dict(t0=t0, arch=arch, p=p, sc=length)


def path_points(base, out, sh, nseg):
    up = unit_path(sh['t0'], sh['arch'], sh['p'])
    k = UN // nseg
    return [base + out * (up[j * k][0] * sh['sc']) + Z * (up[j * k][1] * sh['sc']) for j in range(nseg + 1)]


def profile(t):
    """Half-width factor along a blade: a little narrow at the base, widest at about a quarter, tapering to the point."""
    return (.8 + .2 * smoothstep(0, .25, t)) * (1 - .55 * smoothstep(.45, 1, t))


def section_colours(kind, n, base_c, tip_c, straw_c, tint):
    cols = []
    for j in range(n):
        t = j / (n - 1)
        if kind == 'straw':
            c = mix(scale_col(straw_c, .55), straw_c, smoothstep(0, .4, t))
        else:
            c = mix(base_c, tip_c, t ** .8)
        cols.append(scale_col(c, tint))
    return cols


def draw_blade(g, pts, out, width, roll, twist, cols):
    n = len(pts)
    side0 = Z.cross(out).normalized()
    S = []; U = []; hw = []
    for j in range(n):
        T = (pts[min(j + 1, n - 1)] - pts[max(j - 1, 0)]).normalized()
        s = rot(side0, T, roll + twist * j / (n - 1))
        S.append(s); U.append(T.cross(s).normalized()); hw.append(width * .5 * profile(j / (n - 1)))
    n0 = len(g.v)
    L.strip(g, pts, hw, hw, S, U, cols[0], 1, 0.0, tip=True, colours=cols)
    al = []
    for j in range(n):
        al += [j / (n - 1)] * (2 if j < n - 1 else 1)
    assert len(al) == len(g.v) - n0, (len(al), len(g.v) - n0)
    g.a[n0:] = al
    g.counts['leaves'] += 1


def draw_ribbon(g, pts, hw, S, colour, alpha0=0.0):
    """A plain 2-vertex ribbon (no point at the end) with its alpha rising from alpha0 to 1: stalks and petioles."""
    n = len(pts)
    U = []
    for j in range(n):
        T = (pts[min(j + 1, n - 1)] - pts[max(j - 1, 0)]).normalized()
        U.append(T.cross(S[j]).normalized())
    n0 = len(g.v)
    L.strip(g, pts, hw, hw, S, U, colour, 1, 0.0, tip=False)
    al = []
    for j in range(n):
        al += [lerp(alpha0, 1.0, j / (n - 1))] * 2
    g.a[n0:] = al


def kite(g, a, d, ln, wd, side, colours, normal_hint):
    """One four-vertex leaflet or spikelet: base point a, widest at 55 % of the length along d, a point at the end (2 triangles)."""
    mid = a + d * ln * .55
    vs = [a, mid - side * wd * .5, a + d * ln, mid + side * wd * .5]
    g.oriented(vs, colours, [(0, .5), (.55, 0), (1, .5), (.55, 1)], 1, normal_hint)


# ---------------------------------------------------------------- designs (every random draw is unconditional and in a fixed order)

def design_pasture(a, fit, rot0=0.0):
    rng = random.Random(seed_of(a))
    n = a['n']; T = a['tufts']; R = a['across'] / 2; Hlo, Hhi = a['H']; Rb = a['reach']
    n_clover = rhu(.15 * n); n_straw = max(1, rhu(.05 * n)); n_flat = max(1, rhu(.10 * n))
    kinds = ['clover'] * n_clover + ['straw'] * n_straw + ['grass'] * (n - n_clover - n_straw)
    rng.shuffle(kinds)
    phase = rng.uniform(0, math.tau)
    tufts = []
    for k in range(T):
        ang = phase + k * 2.39996 + rng.uniform(-.25, .25) + rot0
        rad = clamp(math.sqrt((k + .5) / T) + rng.uniform(-.08, .08), 0, 1) if T > 1 else 0.0
        tufts.append(dict(ang=ang, rad=rad, ph=rng.uniform(0, math.tau), count=0))
    perm = list(range(n)); rng.shuffle(perm)
    els = []
    for i, kind in enumerate(kinds):
        tf = tufts[i % T]; idx = tf['count']; tf['count'] += 1
        az = tf['ph'] + idx * 2.39996 + rng.uniform(-.35, .35) + rot0
        rb = rng.uniform(.002, .010)
        H = lerp(Hlo, Hhi, (perm[i] + rng.random() * .9) / n)
        rr = rng.uniform(.5, 1.0)
        arch = D2R(rng.uniform(30, 60)); width = rng.uniform(.004, .006)
        roll = rng.uniform(-.6, .6); twist = rng.uniform(-.5, .5); tint = rng.uniform(.9, 1.1)
        fl = rng.random(); fj = rng.uniform(-.6, .6); ft0 = D2R(rng.uniform(70, 82)); farch = D2R(rng.uniform(6, 14)); flen = rng.uniform(.9, 1.4)
        ctilt = D2R(rng.uniform(8, 30)); clen = rng.uniform(.03, .06); caz = rng.uniform(0, math.tau) + rot0; cj = [rng.uniform(-.4, .4) for _ in range(3)]
        cel = [D2R(rng.uniform(-5, 22)) for _ in range(3)]
        els.append(dict(kind=kind, tuft=i % T, az=az, rb=rb, H=H, rr=rr, arch=arch, width=width, roll=roll, twist=twist, tint=tint, fl=fl, fj=fj, ft0=ft0,
                        farch=farch, flen=flen, ctilt=ctilt, clen=clen, caz=caz, cj=cj, cel=cel))
    grass_idx = sorted([i for i, e in enumerate(els) if e['kind'] == 'grass'], key=lambda i: els[i]['fl'])[:n_flat]
    for i in grass_idx:
        els[i]['kind'] = 'flat'
    l1 = dict(phase=rng.uniform(0, math.tau), tint=[rng.uniform(.93, 1.07) for _ in range(6)], u=[rng.random() for _ in range(6)], v=[rng.random() for _ in range(6)])
    blades = []
    for e in els:
        tf = tufts[e['tuft']]
        centre = Vector((math.cos(tf['ang']), math.sin(tf['ang']), 0)) * (tf['rad'] * R * fit)
        if e['kind'] == 'flat':
            az = tf['ang'] + e['fj']
        else:
            az = e['az']
        out = Vector((math.cos(az), math.sin(az), 0))
        base = centre + out * e['rb'] + Vector((0, 0, ROOT_Z))
        b = dict(e); b.update(base=base, out=out, az=az)
        if e['kind'] == 'flat':
            b['shape'] = shape_flat(Rb * e['flen'] * fit, e['ft0'], e['farch'])
        elif e['kind'] != 'clover':
            b['shape'] = shape_for(e['H'], Rb * e['rr'] * fit, e['arch'])
        blades.append(b)
    return dict(blades=blades, tufts=tufts, l1=l1, counts=dict(clover=n_clover, straw=n_straw, flat=n_flat, grass=n - n_clover - n_straw - n_flat))


def design_rank(a, fit, rot0=0.0):
    rng = random.Random(seed_of(a))
    n = a['n']; R = a['across'] / 2; Hlo, Hhi = a['H']
    n_straw = rhu(.25 * n)
    kinds = ['straw'] * n_straw + ['grass'] * (n - n_straw)
    rng.shuffle(kinds)
    perm = list(range(n)); rng.shuffle(perm)
    blades = []
    for i, kind in enumerate(kinds):
        az = i * 2.39996 + rng.uniform(-.3, .3)
        rb = rng.uniform(.004, .03)
        H = lerp(Hlo, Hhi, (perm[i] + rng.random() * .9) / n)
        rr = rng.uniform(.5, 1.0); arch = D2R(rng.uniform(40, 85)); width = rng.uniform(.006, .009)
        roll = rng.uniform(-.6, .6); twist = rng.uniform(-.5, .5); tint = rng.uniform(.9, 1.1)
        out = Vector((math.cos(az), math.sin(az), 0))
        base = out * (rb * fit) + Vector((0, 0, ROOT_Z))
        blades.append(dict(kind=kind, az=az, out=out, base=base, H=H, width=width, roll=roll, twist=twist, tint=tint,
                           shape=shape_for(H, rr * R * fit, arch)))
    stalks = []
    for i in range(a['stalks']):
        az = i * 2.39996 + rng.uniform(-.5, .5) + 1.1
        rb = rng.uniform(.004, .03)
        ztop = Hhi + rng.uniform(.07, .11)
        lean = D2R(rng.uniform(10, 26)); tint = rng.uniform(.9, 1.1); hq = a['head_q'][i]
        ph = rng.uniform(0, math.tau); tilt = rng.uniform(.9, 1.1)
        out = Vector((math.cos(az), math.sin(az), 0))
        base = out * (rb * fit) + Vector((0, 0, ROOT_Z))
        sh = dict(t0=D2R(2), arch=lean - D2R(2), p=1.6)
        zm = max(z for _, z in unit_path(sh['t0'], sh['arch'], sh['p']))
        sh['sc'] = (ztop - .035 - ROOT_Z) / zm
        stalks.append(dict(az=az, out=out, base=base, ztop=ztop, shape=sh, tint=tint, q=hq, ph=ph, tilt=tilt))
    l1 = dict(phase=rng.uniform(0, math.tau), tint=[rng.uniform(.93, 1.07) for _ in range(6)], u=[rng.random() for _ in range(6)], v=[rng.random() for _ in range(6)])
    return dict(blades=blades, stalks=stalks, l1=l1, counts=dict(straw=n_straw, grass=n - n_straw, stalks=a['stalks']))


def design(a, fit, rot0=0.0):
    return design_pasture(a, fit, rot0) if a['kind'] == 'pasture' else design_rank(a, fit, rot0)


# ---------------------------------------------------------------- LOD0

def draw_clover(g, b):
    az = b['caz']
    pts = [b['base'], None, None]
    d1 = polar(b['ctilt'] * .6, az); d2 = polar(b['ctilt'] * 1.5, az)
    pts[1] = pts[0] + d1 * b['clen'] * .5
    pts[2] = pts[1] + d2 * b['clen'] * .5
    out = Vector((math.cos(az), math.sin(az), 0))
    side = Z.cross(out).normalized()
    col = scale_col(CLOVER, b['tint'])
    draw_ribbon(g, pts, [.0008, .0008, .0007], [side] * 3, col)
    c = pts[2] + d2 * .002
    for k in range(3):
        a_k = az + k * math.tau / 3 + b['cj'][k]; el = b['cel'][k]
        d = Vector((math.cos(el) * math.cos(a_k), math.cos(el) * math.sin(a_k), math.sin(el)))
        sd = Z.cross(d); sd = sd.normalized() if sd.length > 1e-4 else Vector((1, 0, 0))
        ln = .0078
        kite(g, c, d, ln, ln * .95, sd, scale_col(CLOVER, b['tint'] * (.94 + .06 * k)), Z)
    g.counts['leaves'] += 1


def draw_seed_stalk(g, st, lod, n_head=None):
    sh = st['shape']
    nseg = 2 if lod == 0 else 1
    pts = path_points(st['base'], st['out'], sh, nseg)
    side0 = Z.cross(st['out']).normalized()
    col = scale_col(R_STALK, st['tint'])
    d = (pts[-1] - pts[-2]).normalized()
    if lod == 0:
        draw_ribbon(g, pts, [.0013, .0011, .0009], [side0] * 3, col)
    else:
        draw_ribbon(g, pts, [.0028, .0016], [side0] * 2, col)
    top = pts[-1]
    r0 = L.perp(d)
    head = scale_col(R_HEAD, st['tint'])
    if lod == 0:
        q = st['q']; span = .030
        for i in range(q):
            f = (i + .5) / q
            pos = top - d * span * (1 - f)
            rad = rot(r0, d, st['ph'] + i * 2.39996)
            tilt = D2R(40 - 34 * f)
            dd = (d * math.cos(tilt) + rad * math.sin(tilt)).normalized()
            ln = .024 * (.85 + .25 * f) * st['tilt']; wd = .0095
            side = rad.cross(dd).normalized()
            kite(g, pos, dd, ln, wd, side, [scale_col(head, .7), scale_col(head, .95), scale_col(head, 1.03), scale_col(head, .95)], rad)
        g.counts['sprays'] += 1
    else:
        ln = .05; wd = .016
        side = r0
        kite(g, top - d * .008, d, ln, wd, side, [scale_col(head, .75), scale_col(head, .97), scale_col(head, 1.03), scale_col(head, .97)], rot(r0, d, 1.0))
        g.counts['sprays'] += 1


def draw_lod0(g, a, D):
    for b in D['blades']:
        if b['kind'] == 'clover':
            draw_clover(g, b)
            continue
        nseg = a['segs']
        pts = path_points(b['base'], b['out'], b['shape'], nseg)
        if a['kind'] == 'pasture':
            cols = section_colours(b['kind'], nseg + 1, P_BASE, P_TIP, P_STRAW, b['tint'])
        else:
            cols = section_colours(b['kind'], nseg + 1, R_BASE, R_TIP, R_STRAW, b['tint'])
        draw_blade(g, pts, b['out'], b['width'], b['roll'], b['twist'], cols)
    for st in D.get('stalks', []):
        draw_seed_stalk(g, st, 0)


# ---------------------------------------------------------------- LOD1: six blades at 60 degree steps, wider strips

def draw_lod1(g, a, D, g0):
    l1 = D['l1']; c1 = a['lod1']; nseg = c1['segs']
    R0 = a['across'] / 2
    Hlo, Hhi = a['H']
    if a['kind'] == 'pasture':
        gb = [b['H'] for b in D['blades'] if b['kind'] in ('grass', 'straw')]
        reach1 = R0 * .90; H1 = lerp(sum(gb) / len(gb), Hhi, .5)
        base_c = scale_col(P_BASE, .96); tip_c = tuple(.80 * x + .15 * y + .05 * z for x, y, z in zip(P_TIP, CLOVER, P_STRAW))
        arch = D2R(48)
    else:
        reach1 = R0 * .95; H1 = Hhi * .94
        base_c = tuple(.75 * x + .25 * y * .55 for x, y in zip(R_BASE, R_STRAW)); tip_c = tuple(.75 * x + .25 * y for x, y in zip(R_TIP, R_STRAW))
        arch = D2R(62)
    for k in range(6):
        az = l1['phase'] + k * math.pi / 3
        out = Vector((math.cos(az), math.sin(az), 0))
        base = out * .004 + Vector((0, 0, ROOT_Z))
        H = H1 * (.88 + .24 * l1['u'][k]); reach = reach1 * (.84 + .16 * l1['v'][k])
        sh = shape_for(H, reach, arch)
        pts = path_points(base, out, sh, nseg)
        cols = section_colours('grass', nseg + 1, base_c, tip_c, None, l1['tint'][k])
        draw_blade(g, pts, out, c1['width'], (-.25, .25)[k % 2], .3, cols)
    if a['kind'] == 'rank':
        ns = len(D['stalks']); m = c1['stalks']
        pick = sorted({int(round(i * (ns - 1) / max(1, m - 1))) for i in range(m)})
        assert len(pick) == m, (a['asset'], pick, m)
        for i in pick:
            draw_seed_stalk(g, D['stalks'][i], 1)


# ---------------------------------------------------------------- footprint

def extents(a, fit, rot0):
    g = GG(); draw_lod0(g, a, design(a, fit, rot0))
    xs = [v.x for v in g.v]; ys = [v.y for v in g.v]
    return max(xs) - min(xs), max(ys) - min(ys)


def solve_fit(a):
    """The footprint scale `fit` at which the larger horizontal extent equals the across-size, for the layout rotation (pasture clumps
    only: 8 steps of 15 degrees) that makes the other extent closest to it. Returns (fit, rotation, other extent / larger extent)."""
    best = None
    for rot0 in ([0.0] if a['kind'] == 'rank' else [D2R(15 * i) for i in range(8)]):
        big = lambda f: max(extents(a, f, rot0))
        lo, hi = .05, 3.0
        if big(hi) < a['across']:
            print('WARNING', a['asset'], 'cannot reach the across-size even at fit', hi); fit = hi
        elif big(lo) > a['across']:
            print('WARNING', a['asset'], 'is wider than the across-size even at fit', lo); fit = lo
        else:
            for _ in range(16):
                mid = (lo + hi) / 2
                if big(mid) < a['across']:
                    lo = mid
                else:
                    hi = mid
            fit = (lo + hi) / 2
        ex, ey = extents(a, fit, rot0)
        iso = min(ex, ey) / max(ex, ey)
        if best is None or iso > best[2] + 1e-9:
            best = (fit, rot0, iso)
    return best


# ================================================================ build

def build_asset(a, mats, coll):
    seed = seed_of(a)
    fit, rot0, iso = solve_fit(a)
    D = design(a, fit, rot0)
    g0 = GG(); draw_lod0(g0, a, D)
    g1 = GG(); draw_lod1(g1, a, D, g0)
    obs = []; rows = []
    for lod, g in enumerate((g0, g1)):
        name = '%s_LOD%d' % (a['asset'], lod)
        ob, dropped = L.to_object(g, name, mats, [1], coll)
        n = len(ob.data.loop_triangles)
        print('LOD', name, n, 'of', a['budget'][lod], 'verts', len(g.v), 'size', [round(x, 3) for x in ob.dimensions], 'dropped', dropped)
        assert n <= a['budget'][lod], '%s: %d triangles over the LOD%d ceiling %d' % (name, n, lod, a['budget'][lod])
        ob['kit'] = L.KIT; ob['lod'] = lod; ob['seed'] = seed
        ob['placement'] = 'Ground pivot at the origin; bases stop 2 cm below ground. Vertex alpha = wind weight (0 base, 1 tip). No collision.'
        L.export(ob, [])
        extra = dict(min_z_band=[-.03, -.01], vertex_alpha='wind weight: 0 at the blade base, 1 at the tip and on seed heads', across_m=a['across'],
                     fit=round(fit, 4), layout_rotation_deg=round(math.degrees(rot0)), roundness=round(iso, 3), dropped_degenerate_faces=dropped)
        extra.update(D['counts'])
        rows.append(L.manifest_row(ob, a['asset'], a['family'], a['variant'], lod, [1], seed, g.counts, 0, a['budget'][lod], extra))
        obs.append(ob)
    assert rows[0]['triangles'] > rows[1]['triangles'], (a['asset'], [r['triangles'] for r in rows])
    amin = min(g0.a); amax = max(g0.a)
    assert amin < .001 and amax > .999, (a['asset'], 'alpha range', amin, amax)
    print('BUILT', a['asset'], [r['triangles'] for r in rows], 'size', rows[0]['size_m'], 'minz', [r['min_z_m'] for r in rows], 'fit %.3f rot %d roundness %.2f' % (fit, round(math.degrees(rot0)), iso), D['counts'])
    return obs, rows


# ================================================================ review renders

def append_from(blend, names):
    src = OUT / blend
    assert src.exists(), blend + ' is missing (build that set first)'
    with bpy.data.libraries.load(str(src), link=False) as (dfrom, dto):
        dto.objects = [n for n in names if n in dfrom.objects]
    return {o.name.split('_LOD0')[0]: o for o in dto.objects if o is not None}


def box(scene, name, x0, x1, y0, y1, z0, z1, mat):
    vs = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    fs = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs); me.update(); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); scene.collection.objects.link(ob)
    return ob


def lineup(lod0, assets, tri_rows):
    scene = L.review_scene('Grass Lineup')
    ink = L.flat_material('Review | Ink', (.70, .78, .70), .8); muted = L.flat_material('Review | Secondary', (.44, .53, .47), .8)
    chalk = L.flat_material('Review | Chalk', (.19, .225, .21))
    bar_a = L.flat_material('Review | Bar A', (.80, .55, .12)); bar_b = L.flat_material('Review | Bar B', (.75, .75, .70))
    L.floor(scene, chalk, 60, z=-.012, location=(2, 0))
    tilt = D2R(30)
    rot_txt = (math.pi / 2 - tilt, 0, 0)
    x = 0.0
    for a in assets:
        ob = lod0[a['asset']]; lo, hi = B.bbox(ob)
        w = max(hi.x - lo.x, hi.y - lo.y)
        mid = x + w / 2
        L.display_copy(scene, ob, a['asset'].replace('SM_NZ_', 'Lineup_'), (mid - (lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, 0))
        tr = tri_rows[a['asset']]
        L.text_obj(scene, '%s %s' % (a['label'], a['sub']), (mid, -.44, 0), .042, ink, rot_txt)
        L.text_obj(scene, '%d x %d x %d cm' % (round(a['across'] * 100), round((hi.y - lo.y) * 100), round(hi.z * 100)), (mid, -.53, 0), .030, muted, rot_txt)
        L.text_obj(scene, 'LOD0 %d / LOD1 %d tris' % tuple(tr), (mid, -.61, 0), .030, muted, rot_txt)
        x += w + .22
    width = x - .22
    for i in range(3):
        box(scene, 'Scale bar %d' % i, -.55 + .10 * i - .35, -.45 + .10 * i - .35, -.14, -.10, 0, .012, bar_a if i % 2 == 0 else bar_b)
    L.text_obj(scene, '30 CM', (-.55 - .35 + .15, -.24, 0), .036, ink, rot_txt)
    top = .62
    L.text_obj(scene, 'GRAND TOUR / NATIVE PLANTS / GRASS CLUMPS', (-.9, .0, top), .075, ink, rot_txt, 'LEFT')
    L.text_obj(scene, 'GP1   5 MESHES   TRUE SCALE   TWO LODS   SCALE BAR 30 CM   HEIGHTS ABOVE GROUND', (-.9, .0, top - .09), .04, muted, rot_txt, 'LEFT')
    cx = (width - .9) / 2
    L.studio_lights(scene, Vector((cx, 0, 0)), 1.1)
    target = Vector((cx, 0, .24))
    ortho = width + 1.2
    L.camera(scene, target + Vector((0, -math.cos(tilt), math.sin(tilt))) * 40, target, ortho=ortho)
    return scene, int(2000 * 1.12 / ortho) + 8


def detail_scene():
    scene = L.review_scene('Grass Detail')
    chalk = L.flat_material('Review | Chalk', (.19, .225, .21))
    L.floor(scene, chalk, 60, z=-.012)
    return scene


def append_ground_clumps():
    return None


def assembly_pasture(lod_objs, tag, lod_label):
    """A 12 x 8 m grazed slope from 1.2 m (photo 09), 35 mm, overcast, exposure 1.8: pasture clumps S/M/L on a 65 cm jittered grid (yaw and
    scale .85-1.15 each), a 3 m band of rank clumps A/B at the far edge in front of three of the kit's Beech_Edge, ground (.11, .19, .035)."""
    bush = append_from('GrandTour_NativePlants.blend', ['SM_NZ_Beech_Edge_LOD0'])
    scene = L.review_scene('Pasture Assembly ' + tag)
    F.overcast_world(scene, 'NZ Pasture Overcast ' + tag, 1.8)
    rng = random.Random(60000 + 9001)
    ground = L.material('Assembly | Pasture ground', (.11, .19, .035))
    ground.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .95

    def zfn_(x, y):
        return .105 * y + .035 * math.sin(x * .33 + y * .21) + .025 * math.sin(x * .81 - y * .57) + .012 * math.sin(y * 1.7 + x * 1.1)

    def zfn(x, y):
        return zfn_(x, y), 0, 0

    def cfn(x, y, z, tag_, u):
        lum = 1 + .08 * (2 * vnoise(Vector((x, y, 0)), 1.7, 3.0) - 1) + .05 * (2 * hnoise(Vector((x, y, 0)), 5.0) - 1)
        return scale_col((.11, .19, .035), lum)
    xs = sorted(set([-90, -50, -30, -16, 16, 30, 50, 90] + [-7 + i * .5 for i in range(29)]))
    ys = sorted(set([-14, -8, 14, 22, 40, 80] + [-4 + i * .5 for i in range(37)]))
    F.terrain_grid(scene, 'Pasture slope ' + tag, xs, ys, zfn, cfn, ground)
    counts = {}

    def put(nm, x, y, yaw, sc, zoff=-.004):
        o = L.display_copy(scene, lod_objs[nm], nm.replace('SM_NZ_', 'Asm_') + '_%03d' % counts.get(nm, 0), (x, y, zfn_(x, y) + zoff), yaw, sc)
        counts[nm] = counts.get(nm, 0) + 1
        return o
    sp = .65
    nx = int(12 / sp) + 1; ny = int(8 / sp) + 1
    for j in range(ny):
        for i in range(nx):
            x = -6 + sp * (i + .5) + rng.uniform(-.2, .2); y = sp * (j + .5) + rng.uniform(-.2, .2)
            u = .6 * rng.random() + .4 * vnoise(Vector((x, y, 0)), 3.0, 21.0)
            nm = 'SM_NZ_PastureClump_L' if u > .66 else 'SM_NZ_PastureClump_M' if u > .36 else 'SM_NZ_PastureClump_S'
            yaw = rng.uniform(0, math.tau); sc = rng.uniform(.85, 1.15)
            if abs(x) > 6.2 or y > 8.1:
                continue
            put(nm, x, y, yaw, sc)
    # the rank band, the far 3 m: y 5-8, denser toward the bush wall
    rs = .62
    for j in range(int(3.0 / rs) + 1):
        for i in range(int(12.4 / rs) + 1):
            x = -6.2 + rs * (i + .5) + rng.uniform(-.2, .2); y = 5.0 + rs * (j + .5) + rng.uniform(-.2, .2)
            keep = rng.random() < .55 + .45 * smoothstep(5.0, 7.2, y)
            nm = 'SM_NZ_RankClump_A' if rng.random() < .45 else 'SM_NZ_RankClump_B'
            yaw = rng.uniform(0, math.tau); sc = rng.uniform(.85, 1.15)
            if keep and abs(x) <= 6.3 and y <= 8.2:
                put(nm, x, y, yaw, sc)
    for x, y in ((-4.4, 9.5), (.6, 10.4), (4.9, 9.3)):
        o = L.display_copy(scene, bush['SM_NZ_Beech_Edge'], 'Asm_Beech_Edge', (x, y, zfn_(x, y)), -math.pi / 2 + rng.uniform(-.4, .4), rng.uniform(.96, 1.04))
    L.studio_lights(scene, (0, 4, 0), 3.0, energy=.5)
    eye = Vector((0, -2.0, zfn_(0, -2.0) + 1.2))
    L.camera(scene, eye, Vector((0, 9.0, zfn_(0, 9.0) + 1.3)), lens=35)
    pc = sum(v for k, v in counts.items() if 'Pasture' in k); rc = sum(v for k, v in counts.items() if 'Rank' in k)
    print('PASTURE ASSEMBLY', lod_label, counts, 'pasture clumps', pc, 'rank clumps', rc)
    return scene, dict(counts, pasture=pc, rank=rc)


def render_all(lod0, lod1, assets, tri_rows, only, no_assembly, t0):
    renders = []
    if only is None and not ASM_ONLY:
        s1, h = lineup(lod0, assets, tri_rows)
        renders.append(L.render(s1, OUT / 'Lineup_Grass.png', 2000, h))
        print('RENDERED Lineup', '%.1fs' % (time.time() - t0))
    s2 = detail_scene()
    fig = L.flat_material('Review | Figure', (.55, .36, .16))
    for a in ([] if ASM_ONLY else assets):
        nm = a['asset'].replace('SM_NZ_', '')
        renders.append(B.render_detail(s2, lod0[a['asset']], a['asset'], OUT / ('Detail_%s.png' % nm), fig))
        print('RENDERED Detail', nm, '%.1fs' % (time.time() - t0))
    if only is None and not no_assembly:
        for fname, objs, tag in (('Assembly_Pasture.png', lod0, 'LOD0'), ('Assembly_Pasture_LOD1.png', lod1, 'LOD1')):
            sc_, counts = assembly_pasture(objs, tag, tag)
            renders.append(L.render(sc_, OUT / fname, 2000, 1333))
            print('RENDERED', fname, '%.1fs' % (time.time() - t0))
    return renders


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene; scene.name = 'Native Grass Assets - metres'
    mats = L.plant_materials()
    coll = scene.collection
    lod0 = {}; lod1 = {}; rows = []; tri_rows = {}
    assets = [a for a in ASSETS if ONLY is None or a['asset'].replace('SM_NZ_', '') in ONLY]
    x = 0.0
    for a in assets:
        obs, r = build_asset(a, mats, coll)
        rows += r
        tri_rows[a['asset']] = [q['triangles'] for q in r]
        lo, hi = B.bbox(obs[0])
        x += -lo.x + .3
        obs[0].location = (x, 0, 0)
        x += hi.x + .6
        for o in obs[1:]:
            o.hide_set(True); o.hide_render = True
        L.mark_asset(obs[0], a['label'] + ' ' + a['sub'] + ' / opaque vertex-colour blades / 2 LODs', ['Native', 'NZ', a['family'], 'Southland', 'Grass', 'Grand Tour'])
        lod0[a['asset']] = obs[0]; lod1[a['asset']] = obs[1]
    if ONLY is None:
        L.write_manifest(rows, set_name='grass', extra=dict(grass_stage='GP1', grass_seeds={a['asset']: seed_of(a) for a in assets},
                         grass_lod_rule='two LODs per asset from one design (seed 60000 + 97 k). LOD0: every blade a narrow tapering strip (4 segments pasture, 5 rank), pasture clover petioles with a three-leaflet head, rank seed-head stalks with 4-5 spikelet quads; LOD1: a six-blade cross of wider strips at 60 degree steps keeping the silhouette and the colour mix (rank LOD1 keeps 4 / 8 single-quad seed stalks). Bases stop 2 cm below ground (rows declare min_z_band). Vertex alpha is a wind weight, 0 at the blade base and 1 at the tip. No collision'))
        print('MANIFEST', len(rows), 'rows', '%.1fs' % (time.time() - t0))
    else:
        print('PARTIAL RUN (--only): manifest.json left alone')
    renders = []
    if not NO_RENDER:
        renders += render_all(lod0, lod1, assets, tri_rows, ONLY, NO_ASSEMBLY, t0)
    try:
        bpy.context.window.scene = bpy.data.scenes['Native Grass Assets - metres']
    except Exception:
        pass
    if ONLY is None:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'GrandTour_NativePlants_Grass.blend'))
    for b in OUT.glob('*.blend1'):
        b.unlink()
    for p in renders:
        print('RENDER', p)
    print('NATIVE_GRASS_BUILD_OK', len(assets), 'meshes', len(rows), 'lods', '%.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
