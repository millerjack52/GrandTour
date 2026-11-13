"""NP2 margin and high-country set (docs/NATIVE_PLANT_KIT_PLAN.md): harakeke, coprosma
(mikimiki), matagouri, ti kouka and kanuka, A and B each, as deterministic Blender geometry with
three authored LODs, FBX (cm) + GLB (m), manifest rows tagged set: open (merged into the shared
manifest.json), the open asset .blend and review renders.

Run: blender -b --factory-startup --python-exit-code 1 --python build_native_open.py [-- --only X,Y --no-render]
Needs the bush set built first: Assembly_Edge appends the bush LOD0 meshes from
GrandTour_NativePlants.blend. Reuses the bush builder's design container, emitter and review
helpers (build_native_bush.main only runs when that file is the script).

Every asset is designed once from its fixed seed; all RNG is drawn in the design and LOD0/1/2 are
emitted from it. Structure (trunks, branches, leaders, lattice twigs) is kept at every LOD (fine
lattice twigs become flat ribbons at LOD1/LOD2, the finest drop at LOD2); foliage items (straps,
pods, leaves, spines, needle sprays) are kept as the largest even subset that fits 96 % of each
ceiling, enlarged 1.0 / 1.3 / 1.55 where a subset is dropped.
"""
import bpy, sys, math, random, time
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_plant_lib as L
import build_native_bush as B
from native_plant_lib import Z, clamp, lerp, mix, scale_col, smoothstep, polar, rot

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ONLY = set(ARGS[ARGS.index('--only') + 1].split(',')) if '--only' in ARGS else None
NO_RENDER = '--no-render' in ARGS
OUT = L.OUT
D2R = math.radians
ENLARGE = B.ENLARGE

FLAX_LEAF = (.07, .16, .075)
FLAX_EDGE = (.28, .10, .05)
FLAX_DEAD = (.40, .30, .15)
FLAX_DEAD_EDGE = (.30, .20, .10)
KORARI = (.20, .07, .04)
POD = (.08, .05, .03)
COP_TWIG = (.14, .12, .09)
COP_LEAF = (.09, .19, .055)
COP_LEAF_YG = (.16, .26, .07)
MAT_TWIG = (.17, .16, .14)
MAT_SPINE = (.22, .21, .19)
MAT_TRUNK = (.15, .13, .11)
MAT_LEAF = (.18, .22, .12)
TIK_BARK = (.30, .28, .25)
TIK_FISSURE = (.17, .16, .14)
TIK_LEAF = (.14, .24, .09)
TIK_DEAD = (.38, .30, .17)
KAN_BARK = (.17, .13, .09)
KAN_STRIP = (.30, .25, .18)
KAN_NEEDLE = (.10, .18, .06)
KAN_TIP = (.16, .24, .09)

ASSETS = [
    dict(asset='SM_NZ_Harakeke_A', family='Harakeke', variant='A', fam=4, var=0, label='HARAKEKE / A', slots=[1], budget=(5000, 1600, 400), hulls=0),
    dict(asset='SM_NZ_Harakeke_B', family='Harakeke', variant='B', fam=4, var=1, label='HARAKEKE / B', slots=[1], budget=(5000, 1600, 400), hulls=0),
    dict(asset='SM_NZ_Coprosma_A', family='Coprosma', variant='A', fam=5, var=0, label='COPROSMA / A', slots=[1], budget=(10000, 3000, 800), hulls=0),
    dict(asset='SM_NZ_Coprosma_B', family='Coprosma', variant='B', fam=5, var=1, label='COPROSMA / B', slots=[1], budget=(10000, 3000, 800), hulls=0),
    dict(asset='SM_NZ_Matagouri_A', family='Matagouri', variant='A', fam=6, var=0, label='MATAGOURI / A', slots=[1], budget=(10000, 3000, 800), hulls=0),
    dict(asset='SM_NZ_Matagouri_B', family='Matagouri', variant='B', fam=6, var=1, label='MATAGOURI / B', slots=[0, 1], budget=(10000, 3000, 800), hulls=1),
    dict(asset='SM_NZ_TiKouka_A', family='TiKouka', variant='A', fam=7, var=0, label='TI KOUKA / A', slots=[0, 1], budget=(9000, 3000, 800), hulls=2),
    dict(asset='SM_NZ_TiKouka_B', family='TiKouka', variant='B', fam=7, var=1, label='TI KOUKA / B', slots=[0, 1], budget=(12000, 3000, 800), hulls=2),
    dict(asset='SM_NZ_Kanuka_A', family='Kanuka', variant='A', fam=8, var=0, label='KANUKA / A', slots=[0, 1], budget=(16000, 5000, 1200), hulls=1),
    dict(asset='SM_NZ_Kanuka_B', family='Kanuka', variant='B', fam=8, var=1, label='KANUKA / B', slots=[0, 1], budget=(16000, 5000, 1200), hulls=2),
]


def jit(rng, s):
    return Vector((rng.uniform(-s, s), rng.uniform(-s, s), rng.uniform(-s, s)))


def hflat(v, fallback=Vector((1, 0, 0))):
    h = Vector((v.x, v.y, 0))
    return h.normalized() if h.length > 1e-4 else fallback.copy()


def design():
    D = B.Design()
    D.items = []
    return D


def item(D, cost, fn, tier=1):
    """A foliage element: cost = triangles at LOD0/1/2, fn(geo, lod) draws it. Tier 0 items are
    fitted first (the plant itself), tier 1 items fill what remains."""
    D.items.append(dict(cost=cost, fn=fn, tier=tier))


def mottle(c, p, amt=.15):
    return scale_col(c, 1 + amt * (2 * L.hnoise(p, 31.0) - 1))


# ================================================================ lattice twigs

def twig_layer(D, twigs, colour, mi, budgets, shares=(.70, .55), sides3=False):
    """Lattice twigs: LOD0 tubes (4 sides at 3 mm and over, 3 below), LOD1 and LOD2 flat ribbons
    for the leaders and as many lattice levels as fit 70 % / 55 % of those ceilings."""
    per = [sum(1 for t in twigs if t['level'] == k) for k in range(8)]

    def depth(room):
        lev = 0
        while lev < 7 and sum(per[:lev + 2]) * 2 <= room:
            lev += 1
        return lev
    lods = (99, depth(shares[0] * budgets[1]), depth(shares[1] * budgets[2]))
    D.note = dict(getattr(D, 'note', {}) or {}, ribbon_levels=list(lods[1:]))
    for t in twigs:
        t['ref'] = Vector((L.hnoise(t['a'], 1.0) - .5, L.hnoise(t['a'], 2.0) - .5, L.hnoise(t['a'], 3.0) - .5)) + Vector((.01, .02, .03))

    def fn(g, lod):
        for t in twigs:
            col = mottle(colour, t['a'])
            if lod == 0:
                L.tube(g, [t['a'], t['b']], [max(t['r0'], .0018), max(t['r1'], .0015)], 3 if sides3 or t['r0'] < .003 else 4, col, mi, (False, False), noise=0)
            elif t['level'] <= lods[lod]:
                w = max(t['r0'], .0015) * ENLARGE[lod]
                L.ribbon(g, t['a'], t['b'], w, max(t['r1'], .0012) * ENLARGE[lod], t['ref'], col, mi)
    D.extra(fn)


# ================================================================ harakeke

FLAX = {'A': dict(leaves=36, fans=5, Lmax=1.78, korari=0),
        'B': dict(leaves=50, fans=6, Lmax=2.35, korari=3)}


def harakeke(v, rng):
    """Clump of 4-6 fans rising from a 30 cm base; stiff keeled blades with a dark red-brown edge
    and keel line; outer leaves lean 50-60 degrees; the outermost 15 % are dead tan leaves hanging
    outward; B carries three korari leaning apart."""
    c = FLAX[v]; D = design()
    nf = c['fans']
    per = [c['leaves'] // nf + (1 if i < c['leaves'] % nf else 0) for i in range(nf)]
    leaves = []
    for f in range(nf):
        az = f * math.tau / nf + rng.uniform(-.4, .4)
        base = Vector((math.cos(az), math.sin(az), 0)) * rng.uniform(.04, .11) + Vector((0, 0, -.06))
        th = rng.uniform(0, math.pi)
        af = Vector((math.cos(th), math.sin(th), 0)); nfv = Vector((-af.y, af.x, 0))
        m = per[f]
        for k in range(m):
            rel = (k - (m - 1) / 2) / max(1, (m - 1) / 2)
            lean = rel * D2R(rng.uniform(50, 60)) + D2R(rng.uniform(-4, 4))
            tilt = D2R(rng.uniform(-8, 8))
            d = rot(Z * math.cos(lean) + af * math.sin(lean), af, tilt)
            side = rot(-Z * math.sin(lean) + af * math.cos(lean), af, tilt)
            ln = c['Lmax'] * (1 - .28 * abs(rel)) * rng.uniform(.88, 1.04)
            arch = D2R(rng.uniform(20, 30))
            ad = af * (1 if rel > 0 else -1) if abs(rel) > .15 else nfv * (1 if rng.random() < .5 else -1)
            anchor = base + af * rel * .05 + nfv * rng.uniform(-.02, .02)
            leaves.append(dict(anchor=anchor, d=d, side=side, ln=ln, arch=arch, ad=ad, roll=rng.uniform(-.5, .5),
                               rel=abs(rel), tint=rng.uniform(.8, 1.2), dead_arch=D2R(rng.uniform(95, 130)), order=len(leaves)))
    ndead = round(.15 * c['leaves'])
    dead = set(l['order'] for l in sorted(leaves, key=lambda l: (-l['rel'], l['order']))[:ndead])
    for l in leaves:
        isdead = l['order'] in dead
        colour = scale_col(FLAX_DEAD if isdead else FLAX_LEAF, l['tint'])
        edge = FLAX_DEAD_EDGE if isdead else FLAX_EDGE
        out = hflat(l['anchor'] + l['d'] * .5, l['ad'])
        kw = dict(anchor=l['anchor'], direction=l['d'], length=l['ln'] * (.9 if isdead else 1), width=.08,
                  arch=l['dead_arch'] if isdead else l['arch'], colour=colour, edge_colour=edge, keel_colour=edge,
                  arch_dir=out if isdead else l['ad'], side=l['side'], roll=l['roll'], arch_start=.3 if isdead else 2 / 3)

        def fn(g, lod, kw=kw):
            L.strap(g, across=(7, 3, 2)[lod], segs=(6, 4, 3)[lod], **kw)
        item(D, (L.strap_tris(7, 6), L.strap_tris(3, 4), L.strap_tris(2, 3)), fn, tier=0)
    if c['korari']:
        D.paint['korari'] = (KORARI, [], .12)
        a0 = rng.uniform(0, math.tau)
        for s in range(c['korari']):
            az = a0 + s * math.tau / 3 + rng.uniform(-.3, .3)
            d = polar(D2R(rng.uniform(10, 20)), az)
            base = Vector((math.cos(az), math.sin(az), 0)) * .04 + Vector((0, 0, -.06))
            ctrl = [base, base + d * 1.2 + jit(rng, .04), base + d * 2.4 + jit(rng, .06), base + d * 3.46]
            D.tube(ctrl, [(0, .02), (1, .012)], (10, 6, 3), (6, 5, 4), 'korari', (False, True), mi=1)
            stalk = L.curve(ctrl, 4)
            nb = rng.randint(10, 14)
            for j in range(nb):
                t = lerp(.55, .97, (j + rng.uniform(.2, .8)) / nb)
                p, T = L.along(stalk, t)
                baz = az + (1 if j % 2 else -1) * D2R(rng.uniform(60, 120))
                outv = Vector((math.cos(baz), math.sin(baz), 0))
                bd = (T * math.cos(D2R(rng.uniform(25, 40))) + outv * math.sin(D2R(rng.uniform(25, 40)))).normalized()
                bl = rng.uniform(.12, .25)
                D.tube([p, p + bd * bl], [(0, .007), (1, .004)], (1, 1, 1), (4, 3, 3), 'korari', (False, False), (1, 1, 0), mi=1, noise=0)
                for k in range(rng.randint(6, 8)):
                    u = rng.uniform(.25, 1.0)
                    cpos = p + bd * bl * u + jit(rng, .015)
                    pd = (bd * .6 + Z * .8 + jit(rng, .25)).normalized()
                    pl = rng.uniform(.05, .07)
                    nrm = (outv + jit(rng, .3)).normalized()
                    col = scale_col(POD, rng.uniform(.8, 1.2))

                    def pfn(g, lod, cpos=cpos, pd=pd, pl=pl, nrm=nrm, col=col):
                        e = ENLARGE[lod]
                        L.leaflet(g, cpos + pd * pl * .5, pd, pl * e, .012 * e, nrm, col)
                    item(D, (2, 2, 2), pfn, tier=1)
    return D


# ================================================================ coprosma

COP = {'A': dict(W=1.5, H=1.25, stems=(6, 7), lsteps=(5, 7), lstep=(.12, .18), r0=.010, leaves=3800, target=150),
       'B': dict(W=2.3, H=2.1, stems=(6, 7), lsteps=(6, 8), lstep=(.17, .25), r0=.013, leaves=4100, target=180)}


def coprosma(v, rng):
    """Margin coprosma: a dense dark-green mound. The mound is a lobed ellipsoid (A 1.5 x 1.25 m,
    B 2.3 x 2.1 m, top flattened to .85, cut by the ground); 5 x 3 cm leaves (10 % yellow-green)
    are scattered through its outer shell (0-25 cm inward), tangential with up to 40 degrees of tilt,
    1.2x near the top. A sparse 4-level lattice of dark twigs grows inside and reaches out to the
    shell, so it shows only in the gaps."""
    c = COP[v]; D = design()
    ph = [rng.uniform(0, math.tau) for _ in range(2)]
    R0 = c['W'] / 2; z0 = .45 * c['H']; Hu = c['H'] - z0; Hd = Hu / .85

    def Rof(az):
        return R0 * (1 + .08 * math.sin(2 * az + ph[0]) + .05 * math.sin(3 * az + ph[1]))

    def rho(q):
        az = math.atan2(q.y, q.x); R = Rof(az); h = Hu if q.z >= z0 else Hd
        return math.sqrt((q.x * q.x + q.y * q.y) / (R * R) + ((q.z - z0) / h) ** 2)

    def inside(q):
        if q.z < .02 and (q.z < -.07 or q.x * q.x + q.y * q.y > .15 ** 2):
            return False
        return rho(q) <= .92

    def gen(r, stop):
        tw = []
        ns = r.randint(*c['stems'])
        for i in range(ns):
            az = i * math.tau / ns + r.uniform(-.3, .3)
            el = D2R(r.uniform(30, 85))
            g = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
            base = Vector((math.cos(az), math.sin(az), 0)) * r.uniform(.02, .07) + Vector((0, 0, -.06))
            tw += L.lattice(base, g, c['r0'], 4, (60, 90), (.08, .12), r, inside, leader_steps=r.randint(*c['lsteps']),
                            leader_step=c['lstep'], leader_zig=(35, 50), stop=stop)
        return tw
    # one seed, the lightest pruning that keeps the twigs under the target
    sub = rng.randrange(1 << 30)
    for stop in (.1, .2, .3, .4, .5, .6, .7, .8, .9):
        twigs = gen(random.Random(sub), stop)
        if len(twigs) <= c['target']:
            break
    twig_layer(D, twigs, COP_TWIG, 1, (10000, 3000, 800), shares=(.25, .2), sides3=True)
    n = 0
    while n < c['leaves']:
        zs = rng.uniform(-1, 1); a = rng.uniform(0, math.tau); jin = rng.uniform(0, .25)
        tilt = rng.uniform(0, D2R(40)); tax = rng.uniform(0, math.tau); roll = rng.uniform(0, math.tau)
        yg = rng.random() < .10; tint = rng.uniform(.8, 1.2); irr = rng.uniform(-.12, .12)
        sq = math.sqrt(max(0.0, 1 - zs * zs)); R = Rof(a); h = Hu if zs >= 0 else Hd
        p = Vector((R * sq * math.cos(a), R * sq * math.sin(a), z0 + h * zs))
        nrm = Vector((p.x / (R * R), p.y / (R * R), (p.z - z0) / (h * h)))
        nrm = nrm.normalized() if nrm.length > 1e-9 else Z.copy()
        p = p - nrm * jin
        if p.z < .04:
            continue
        axis = rot(L.perp(nrm), nrm, tax)
        n2 = rot(nrm, axis, tilt)
        d = rot(L.perp(n2), n2, roll)
        sz = 1.2 if p.z > z0 + .5 * Hu else 1.0
        col = scale_col(COP_LEAF_YG if yg else COP_LEAF, tint)

        def fn(g, lod, p=p, d=d, n2=n2, sz=sz, col=col, irr=irr):
            e = (1.0, 1.3, 2.0)[lod] * sz
            ln = .05 * e * .5; w = .03 * e * .5
            sv = n2.cross(d).normalized()
            vs = [p - d * ln - sv * w * (.84 + irr), p + d * ln - sv * w, p + d * ln + sv * w, p - d * ln + sv * w * (.84 - irr)]
            g.oriented(vs, col, [(0, 0), (1, 0), (1, 1), (0, 1)], 1, n2)
            g.counts['leaves'] += 1
        item(D, (2, 2, 2), fn)
        n += 1
    # LOD1: 30 % of the shell leaves at 1.3x; LOD2: 300 at 2.0x so the mound silhouette survives
    D.quota = {1: .30, 2: 300}
    D.note = dict(D.note, twigs=len(twigs), leaves_designed=n, prune=stop)
    return D


# ================================================================ matagouri

MAT = {'A': dict(h=1.1, R=.85, stems=(10, 12), lsteps=(6, 8), lstep=(.12, .18), r0=.012, leaves=180, mi=1),
       'B': dict(h=2.6, R=1.4, stems=(7, 8), lsteps=(9, 12), lstep=(.20, .28), r0=.022, leaves=220, mi=0)}


def matagouri(v, rng):
    """Rigid grey lattice with 90 degree zigzags, a 2-4 cm spine at every node and very sparse tiny
    leaves. A: knee-high cushion; B: flat-topped small tree on a .6 m trunk."""
    c = MAT[v]; D = design()
    ph = [rng.uniform(0, math.tau) for _ in range(2)]
    twigs = []
    if v == 'A':
        def inside(q):
            if q.z < .02 and (q.z < -.07 or q.x * q.x + q.y * q.y > .15 ** 2):
                return False
            az = math.atan2(q.y, q.x)
            R = c['R'] * (1 + .1 * math.sin(2 * az + ph[0]) + .07 * math.sin(3 * az + ph[1]))
            return (q.x * q.x + q.y * q.y) / (R * R) + (max(0.0, q.z) / c['h']) ** 3 <= 1
        ns = rng.randint(*c['stems'])
        for i in range(ns):
            az = i * math.tau / ns + rng.uniform(-.3, .3)
            el = D2R(rng.uniform(25, 60))
            g = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
            base = Vector((math.cos(az), math.sin(az), 0)) * rng.uniform(.02, .06) + Vector((0, 0, -.06))
            twigs += L.lattice(base, g, c['r0'], 5, (85, 95), (.08, .12), rng, inside, leader_steps=rng.randint(*c['lsteps']),
                               leader_step=c['lstep'], leader_zig=(40, 50), stop=.05)
    else:
        top = Vector((.03 * math.cos(ph[0]), .03 * math.sin(ph[0]), .62))
        D.tube([(0, 0, -.06), (0, 0, .3), top], [(0, .075), (.15, .06), (1, .05)], (4, 2, 1), (8, 6, 5), 'bark', (False, True))
        D.paint['bark'] = (MAT_TRUNK, [], .15)
        D.trunk = L.curve([Vector((0, 0, -.06)), Vector((0, 0, .3)), top], 6); D.hull_z = .6
        D.hull_rfn = lambda t: .08

        def inside(q):
            if q.z < .45:
                return False
            az = math.atan2(q.y, q.x)
            R = c['R'] * (1 + .1 * math.sin(2 * az + ph[0]) + .07 * math.sin(3 * az + ph[1]))
            return (q.x * q.x + q.y * q.y) / (R * R) + abs((q.z - 1.5) / 1.1) ** 6 <= 1
        ns = rng.randint(*c['stems'])
        for i in range(ns):
            az = i * math.tau / ns + rng.uniform(-.3, .3)
            el = D2R(rng.uniform(20, 60))
            g = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
            twigs += L.lattice(top, g, c['r0'], 5, (85, 95), (.09, .13), rng, inside, leader_steps=rng.randint(*c['lsteps']),
                               leader_step=c['lstep'], leader_zig=(40, 50), stop=.05)
    twig_layer(D, twigs, MAT_TWIG, c['mi'], (10000, 3000, 800))
    spine_col = MAT_SPINE
    for t in twigs:
        d = (t['b'] - t['a']).normalized()
        sd = (rot(L.perp(d), d, rng.uniform(0, math.tau)) + d * .3).normalized()
        sl = rng.uniform(.02, .04)

        def fn(g, lod, b=t['b'], sd=sd, sl=sl):
            if lod < 2:
                L.spine(g, b, sd, sl * (1 if lod == 0 else 1.3), .0025, spine_col, c['mi'])
        item(D, (4, 4, 0), fn)
    nodes = [t['b'] for t in twigs if t['level'] >= 2]
    for k in range(c['leaves']):
        p = nodes[int(rng.random() * len(nodes))] if nodes else Vector((0, 0, .5))
        ld = jit(rng, 1).normalized(); nrm = (Z + jit(rng, .7)).normalized()
        col = scale_col(MAT_LEAF, rng.uniform(.8, 1.2))

        def lfn(g, lod, p=p, ld=ld, nrm=nrm, col=col):
            e = ENLARGE[lod]
            L.leaflet(g, p + ld * .005 * e, ld, .008 * e, .004 * e, nrm, col)
        item(D, (2, 2, 2), lfn)
    D.note = dict(D.note, twigs=len(twigs), spines=len(twigs), leaves_designed=c['leaves'])
    return D


# ================================================================ ti kouka

TIK = {'A': dict(r=.22, fork=3.0, segs0=6, leaves=(70, 90), skirt=(20, 30)),
       'B': dict(r=.30, fork=2.5, segs0=4, leaves=(70, 90), skirt=(20, 30))}


def ti_kouka(v, rng):
    """Cabbage tree: corky grey trunk with fissure blotches; A forks at 3 m into three heads, B at
    2.5 m and again into seven. Each head a dense ball of 70-90 keeled straps from a 10 cm tuft,
    erect above and drooping below, with a straight-down skirt of 20-30 dead tan straps."""
    c = TIK[v]; D = design()
    ph = [rng.uniform(0, math.tau) for _ in range(3)]
    fork = c['fork']
    zs = [-.06, .3, .8, 1.5, 2.2, fork]
    ctrl = [Vector((.05 * math.sin(z * 1.1 + ph[0]), .05 * math.sin(z * .9 + ph[1]), z)) for z in zs]
    r = c['r']
    D.tube(ctrl, [(0, r * 1.25), (.06, r), (1, r * .8)], (14, 7, 3), (10, 8, 6), 'bark', (False, True))
    dense = L.curve(ctrl, 6); D.trunk = dense; D.hull_z = fork
    D.hull_rfn = lambda t: r * (1.25 if t < .06 else 1.05)
    D.paint['bark'] = (TIK_BARK, [dict(colour=TIK_FISSURE, coverage=.30, freq=9.0, noise=.4, inflate=0.0, zstretch=.3, edge_noise=.5, edge_scale=.08, seed=13)], .15)
    top = dense[-1]
    heads = []
    a0 = rng.uniform(0, math.tau)
    for i in range(3):
        az = a0 + i * math.tau / 3 + rng.uniform(-.3, .3)
        if v == 'A':
            br, d = B.walk(top, polar(D2R(rng.uniform(28, 42)), az), rng.uniform(1.25, 1.6), 3, rng, up_bend=.25, wobble=.04)
            D.tube(br, [(0, r * .55), (1, r * .38)], (5, 3, 1), (7, 6, 4), 'bark', (False, True))
            heads.append(br[-1])
        else:
            br, d = B.walk(top, polar(D2R(rng.uniform(25, 40)), az), rng.uniform(1.8, 2.3), 3, rng, up_bend=.2, wobble=.04)
            D.tube(br, [(0, r * .5), (1, r * .4)], (5, 3, 1), (8, 6, 4), 'bark', (False, True))
            for k in range((2, 2, 3)[i]):
                az2 = az + (k - ((2, 2, 3)[i] - 1) / 2) * D2R(rng.uniform(55, 75))
                br2, _ = B.walk(br[-1], polar(D2R(rng.uniform(15, 30)), az2), rng.uniform(2.0, 2.6), 3, rng, up_bend=.2, wobble=.04)
                D.tube(br2, [(0, r * .32), (1, r * .25)], (5, 3, 1), (7, 5, 4), 'bark', (False, True))
                heads.append(br2[-1])
    for hpt in heads:
        n = rng.randint(*c['leaves'])
        for k in range(n):
            e = lerp(-55, 85, rng.random() ** .7)
            az = rng.uniform(0, math.tau)
            d = polar(D2R(90 - e), az)
            if e > 45:
                arch = D2R(rng.uniform(5, 15)); st = .55
            elif e > 0:
                arch = D2R(rng.uniform(15, 35)); st = .4
            else:
                arch = D2R(rng.uniform(30, 60)); st = .2
            ln = rng.uniform(.7, .9) if e > 0 else rng.uniform(.6, .85)
            anchor = hpt + jit(rng, .05) + Z * .03
            colour = scale_col(TIK_LEAF, rng.uniform(.8, 1.2))
            kw = dict(anchor=anchor, direction=d, length=ln, arch=arch, colour=colour, edge_colour=scale_col(colour, 1.18),
                      arch_dir=hflat(d, Vector((math.cos(az), math.sin(az), 0))), roll=rng.uniform(-.4, .4), arch_start=st, base_w=.6)

            def fn(g, lod, kw=kw):
                L.strap(g, width=.05 * ENLARGE[lod], across=(3, 3, 2)[lod], segs=(c['segs0'], 3, 2)[lod], **kw)
            item(D, (L.strap_tris(3, c['segs0']), L.strap_tris(3, 3), L.strap_tris(2, 2)), fn)
        for k in range(rng.randint(*c['skirt'])):
            az = rng.uniform(0, math.tau)
            outv = Vector((math.cos(az), math.sin(az), 0))
            anchor = hpt - Z * rng.uniform(.05, .15) + outv * rng.uniform(.03, .08)
            colour = scale_col(TIK_DEAD, rng.uniform(.8, 1.2))
            kw = dict(anchor=anchor, direction=polar(D2R(rng.uniform(170, 178)), az), length=rng.uniform(.5, .9), arch=D2R(rng.uniform(-8, 0)),
                      colour=colour, edge_colour=scale_col(colour, .8), arch_dir=outv, roll=rng.uniform(-.3, .3), arch_start=.5, base_w=.7)

            def sfn(g, lod, kw=kw):
                L.strap(g, width=.05 * ENLARGE[lod], across=(3, 3, 2)[lod], segs=(c['segs0'], 3, 2)[lod], **kw)
            item(D, (L.strap_tris(3, c['segs0']), L.strap_tris(3, 3), L.strap_tris(2, 2)), sfn)
    return D


# ================================================================ kanuka

KAN = {'A': dict(h=6.0, r=.10, bole=.8, branches=(32, 38), blen=(.6, 1.3), brl=(.2, .45), nbl=(4, 7), segs=(24, 10, 5)),
       'B': dict(h=10.0, r=.18, bole=3.0, branches=(28, 34), blen=(1.4, 3.0), brl=(.35, .8), nbl=(5, 8), segs=(40, 16, 7))}


def kanuka(v, rng):
    """Slender, upright, airy: many fine branches ascending 30-45 degrees from vertical, fine
    branchlets with feathery needle sprays (fans of three thin 6 cm quads, paler tips); stringy
    bark with broken irregular pale strips along the grain."""
    c = KAN[v]; D = design()
    ph = [rng.uniform(0, math.tau) for _ in range(4)]
    h = c['h']; r = c['r']
    lean = Vector((math.cos(ph[0]), math.sin(ph[0]), 0)) * rng.uniform(.1, .3)
    zs = [-.06, .3] + [h * .92 * (i + 1) / 10 for i in range(10)]
    ctrl = [lean * (max(0, z) / h) + Vector((.04 * math.sin(z * 1.3 + ph[1]), .04 * math.sin(z * 1.1 + ph[2]), z)) for z in zs]
    rprof = B.height_profile(ctrl, [(-.06, r * 1.25), (.4, r), (h * .45, r * .65), (h * .92, .02)])
    D.tube(ctrl, rprof, c['segs'], (10, 8, 6), 'bark', (False, False))
    dense = L.curve(ctrl, 6); D.trunk = dense; D.hull_z = 2.0 if v == 'A' else 3.0
    D.hull_rfn = lambda t: L.profile(rprof, t) * 1.05
    D.paint['bark'] = (KAN_BARK, [dict(colour=KAN_STRIP, coverage=.25, freq=14.0, noise=.5, inflate=0.0, zstretch=.2, edge_noise=.6, edge_scale=.08, seed=17)], .15)
    D.paint['twig'] = (KAN_BARK, [], .15)
    crown_w = 2.0 if v == 'A' else 5.0
    nb = rng.randint(*c['branches'])
    a0 = rng.uniform(0, math.tau)
    sprays = []
    for i in range(nb):
        z = lerp(c['bole'], h * .9, (i + rng.uniform(.1, .9)) / nb)
        p0, f = B.trunk_at(dense, z)
        az = a0 + i * 2.39996 + rng.uniform(-.3, .3)
        u = (z - c['bole']) / (h - c['bole'])
        bl = lerp(c['blen'][1], c['blen'][0], u) * rng.uniform(.85, 1.1)
        br, d = B.walk(p0, polar(D2R(rng.uniform(30, 45)), az), bl, 4, rng, up_bend=.08, wobble=.05)
        rb = lerp(.045, .02, u) * (r / .18)
        D.tube(br, [(0, rb), (1, .006)], (4, 2, 1), (5, 4, 3), 'bark', (False, False))
        bpath = L.curve(br, 3)
        twigs = [bpath[int(len(bpath) * .55):]]
        nbl = rng.randint(*c['nbl'])
        for k in range(nbl):
            t = lerp(.3, .92, (k + rng.uniform(.2, .8)) / nbl)
            p, T = L.along(bpath, t)
            sd = (T * math.cos(D2R(rng.uniform(15, 35))) + rot(hflat(T), Z, (1 if k % 2 else -1) * D2R(rng.uniform(50, 100))) * math.sin(D2R(rng.uniform(15, 35)))).normalized()
            sd = (sd + Z * .25).normalized()
            ln = rng.uniform(*c['brl'])
            e2 = p + sd * ln + jit(rng, .03)
            D.tube([p, p.lerp(e2, .5) + jit(rng, .02), e2], [(0, .008), (1, .003)], (2, 1, 1), (3, 3, 3), 'twig', (False, False), (1, 1, 0), noise=0)
            twigs.append(L.curve([p, p.lerp(e2, .5), e2], 3))
        for tw in twigs:
            tl = L.length(tw)
            s = tl * .3 + rng.uniform(0, .03); k = 0
            while s < tl:
                q, T = L.along(tw, s / tl)
                side = hflat(T.cross(Z), L.perp(T)) * (1 if k % 2 else -1)
                nd = (T * .6 + side * rng.uniform(.4, .8) + Z * rng.uniform(.2, .5)).normalized()
                ln = (.13 if v == 'A' else .16) * rng.uniform(.85, 1.25)
                tint = rng.uniform(.8, 1.2)
                sprays.append((q.copy(), nd, ln, tint, (T.cross(nd) + jit(rng, .2)).normalized()))
                s += rng.uniform(.06, .09); k += 1
    for q, nd, ln, tint, up in sprays:
        col = scale_col(KAN_NEEDLE, tint); tip = scale_col(KAN_TIP, tint)

        def fn(g, lod, q=q, nd=nd, ln=ln, col=col, tip=tip, up=up):
            e = ENLARGE[lod]
            if lod < 2:
                L.needles(g, q, nd, ln * e, col, tip, up, width=.24)
            else:
                L.leaflet(g, q + nd * ln * e * .5, nd, ln * e, ln * e * .5, up, mix(col, tip, .4))
        item(D, (6, 6, 2), fn)
    D.note = dict(branches=nb, sprays_designed=len(sprays), crown_w=crown_w)
    return D


# ================================================================ emission and build

def emit(D, lod, budget, base_kept=None):
    g, _ = B.emit(D, lod, budget)
    wood = sum(len(f) - 2 for f in g.f)
    room = B.FILL * budget - wood
    pool = list(range(len(D.items))) if base_kept is None else base_kept
    kept = []
    quota = getattr(D, 'quota', {}).get(lod)
    for tier in (0, 1):
        sub = [i for i in pool if D.items[i]['tier'] == tier]
        if tier == 1 and quota is not None:
            sub = B.even_pick(sub, int(round(quota * len(sub))) if quota < 1 else int(quota))
        pick = B.fit_subset(sub, lambda i: D.items[i]['cost'][lod], room)
        room -= sum(D.items[i]['cost'][lod] for i in pick)
        kept += pick
    for i in sorted(kept):
        D.items[i]['fn'](g, lod)
    # roots stop 6 cm down: leaf bases and ribbons that dip further are held at the root depth
    for v in g.v:
        if v.z < -.06:
            v.z = -.06
    return g, sorted(kept)


DESIGNS = {'Harakeke': harakeke, 'Coprosma': coprosma, 'Matagouri': matagouri, 'TiKouka': ti_kouka, 'Kanuka': kanuka}


def build_asset(a, mats, coll):
    seed = B.seed_of(a)
    rng = random.Random(seed)
    D = DESIGNS[a['family']](a['variant'], rng)
    obs = []; rows = []; hull_obs = []; base_kept = None
    for lod in range(3):
        g, kept = emit(D, lod, a['budget'][lod], base_kept)
        if lod == 0:
            base_kept = kept
        name = '%s_LOD%d' % (a['asset'], lod)
        ob, dropped = L.to_object(g, name, mats, a['slots'], coll)
        tris = len(ob.data.loop_triangles)
        print('LOD', name, tris, 'items', len(kept), 'of', len(D.items), 'counts', g.counts, 'size', [round(x, 2) for x in ob.dimensions])
        assert tris <= a['budget'][lod], '%s: %d triangles over the LOD%d ceiling %d' % (name, tris, lod, a['budget'][lod])
        ob['kit'] = L.KIT; ob['lod'] = lod; ob['seed'] = seed
        ob['placement'] = 'Ground pivot at the origin; roots 6 cm below ground.' + (' Trunk collision UCX hulls in the LOD0 FBX.' if a['hulls'] else ' No collision.')
        hs = []
        if lod == 0 and a['hulls']:
            hs = L.hulls(name, D.trunk, D.hull_rfn, a['hulls'], D.hull_z, coll)
            hull_obs = hs
        L.export(ob, hs)
        extra = dict(items_designed=len(D.items), items_kept=len(kept), dropped_degenerate_faces=dropped)
        extra.update(getattr(D, 'note', {}) or {})
        rows.append(L.manifest_row(ob, a['asset'], a['family'], a['variant'], lod, a['slots'], seed, g.counts, len(hs), a['budget'][lod], extra))
        obs.append(ob)
    for i in range(2):
        assert rows[i]['triangles'] > rows[i + 1]['triangles'], (a['asset'], [r['triangles'] for r in rows])
    print('BUILT', a['asset'], [r['triangles'] for r in rows], rows[0]['size_m'], 'items', [r['items_kept'] for r in rows], 'hulls', len(hull_obs))
    return obs, rows, hull_obs


# ================================================================ review

LINEUP_ORDER = ['SM_NZ_TiKouka_B', 'SM_NZ_TiKouka_A', 'SM_NZ_Kanuka_B', 'SM_NZ_Kanuka_A', 'SM_NZ_Harakeke_B', 'SM_NZ_Harakeke_A',
                'SM_NZ_Coprosma_B', 'SM_NZ_Coprosma_A', 'SM_NZ_Matagouri_B', 'SM_NZ_Matagouri_A']


def append_bush():
    """Bush LOD0 meshes appended from GrandTour_NativePlants.blend (not rebuilt)."""
    names = ['SM_NZ_Beech_Edge_LOD0', 'SM_NZ_Beech_Pole_LOD0', 'SM_NZ_Beech_Mature_LOD0', 'SM_NZ_DeadSpar_LOD0',
             'SM_NZ_TreeFern_A_LOD0', 'SM_NZ_TreeFern_B_LOD0', 'SM_NZ_TreeFern_Young_LOD0', 'SM_NZ_CrownFern_B_LOD0', 'SM_NZ_CrownFern_C_LOD0']
    src = OUT / 'GrandTour_NativePlants.blend'
    assert src.exists(), 'build the bush set first (GrandTour_NativePlants.blend missing)'
    with bpy.data.libraries.load(str(src), link=False) as (dfrom, dto):
        dto.objects = [n for n in names if n in dfrom.objects]
    return {o.name.split('_LOD0')[0]: o for o in dto.objects if o is not None}


def assembly_edge(lod0):
    """The bush wall from 25 m out in the paddock (photos 09/10): a 40 m front of bush trees with a
    tree fern at the margin and the stand behind it, a 6 m scrub band of coprosma with two harakeke
    in front, kanuka B at one end, matagouri B and a ti kouka out in the paddock."""
    bush = append_bush()
    have = dict(lod0); have.update(bush)
    scene = L.review_scene('Edge Assembly')
    w = bpy.data.worlds.new('NZ Paddock Overcast'); w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (.75, .80, .85, 1); bg.inputs[1].default_value = 1.0
    scene.world = w
    rng = random.Random(52710 + 1999)
    pasture = L.flat_material('Assembly | Pasture', (.18, .30, .09), roughness=.95)
    L.floor(scene, pasture, 600, z=-.004, location=(0, 60))
    counts = {}

    def put(name, x, y, yaw, sc=1.0):
        if name not in have:
            return
        o = L.display_copy(scene, have[name], name.replace('SM_NZ_', 'Edge_') + '_%03d' % counts.get(name, 0), (x, y, 0), yaw, sc)
        counts[name] = counts.get(name, 0) + 1
    # front of the wall, y 26-29; the edge trees lean out toward the paddock (model +x -> world -y)
    front = [('SM_NZ_Beech_Edge', -13.0), ('SM_NZ_Beech_Pole', -17.5), ('SM_NZ_Beech_Pole', -8.5), ('SM_NZ_DeadSpar', -4.5),
             ('SM_NZ_Beech_Pole', -1.0), ('SM_NZ_Beech_Mature', 3.5), ('SM_NZ_Beech_Pole', 8.0), ('SM_NZ_Beech_Edge', 12.0),
             ('SM_NZ_Beech_Pole', 15.5), ('SM_NZ_Beech_Pole', 18.5)]
    for name, x in front:
        yaw = -math.pi / 2 + rng.uniform(-.4, .4) if name == 'SM_NZ_Beech_Edge' else rng.uniform(0, math.tau)
        put(name, x + rng.uniform(-.8, .8), rng.uniform(26.5, 28.5), yaw, rng.uniform(.92, 1.06))
    put('SM_NZ_TreeFern_B', -6.5, 25.2, rng.uniform(0, math.tau))
    # the stand behind the front closes the canopy wall
    step = 2.6
    for i in range(int(76 / step) + 1):
        for j in range(int(52 / step) + 1):
            x = -38 + step * i + rng.uniform(-.6, .6); y = 30.5 + step * j + rng.uniform(-.6, .6)
            pick = rng.random(); yaw = rng.uniform(0, math.tau); sc = rng.uniform(.9, 1.1)
            if j < 2 and pick < .3:
                put('SM_NZ_Beech_Edge', x, y, -math.pi / 2 + rng.uniform(-.5, .5), sc)
            else:
                put('SM_NZ_Beech_Pole' if pick < .72 else 'SM_NZ_Beech_Mature', x, y, yaw, sc)
    # margin understory: tree ferns and crown ferns in the first metres of the stand
    for k in range(9):
        put(('SM_NZ_TreeFern_A', 'SM_NZ_TreeFern_B', 'SM_NZ_TreeFern_Young')[k % 3], -24 + k * 6 + rng.uniform(-1.5, 1.5), rng.uniform(25.5, 31), rng.uniform(0, math.tau), rng.uniform(.9, 1.1))
    fs = 1.1
    for i in range(int(54 / fs) + 1):
        for j in range(int(12 / fs) + 1):
            x = -27 + fs * i + rng.uniform(-.35, .35); y = 25.0 + fs * j + rng.uniform(-.35, .35)
            pick = rng.random(); yaw = rng.uniform(0, math.tau); sc = rng.uniform(.85, 1.15)
            put('SM_NZ_CrownFern_B' if pick < .6 else 'SM_NZ_CrownFern_C', x, y, yaw, sc)
    # 6 m scrub band of coprosma in front of the wall
    cs = 1.05
    for i in range(int(46 / cs) + 1):
        for j in range(int(6 / cs) + 1):
            x = -23 + cs * i + rng.uniform(-.4, .4); y = 19.5 + cs * j + rng.uniform(-.4, .4)
            pick = rng.random(); yaw = rng.uniform(0, math.tau); sc = rng.uniform(.85, 1.15)
            put('SM_NZ_Coprosma_A' if pick < .55 else 'SM_NZ_Coprosma_B', x, y, yaw, sc)
    put('SM_NZ_Harakeke_B', -5.0, 17.4, rng.uniform(0, math.tau))
    put('SM_NZ_Harakeke_A', 7.5, 18.0, rng.uniform(0, math.tau))
    # kept inside the 35 mm frame: kanuka B at the right end of the wall, ti kouka and matagouri out in the paddock to the left
    put('SM_NZ_Kanuka_B', 11.0, 23.6, rng.uniform(0, math.tau))
    put('SM_NZ_TiKouka_B', -7.6, 16.0, rng.uniform(0, math.tau))
    put('SM_NZ_Matagouri_B', -3.6, 9.0, rng.uniform(0, math.tau))
    L.studio_lights(scene, (0, 25, 0), 3.0, energy=.5)
    eye = Vector((0, 0, 1.4))
    L.camera(scene, eye, eye + Vector((0, 10, 10 * math.tan(D2R(10)))), lens=35)
    print('EDGE ASSEMBLY', counts)
    return scene


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene; scene.name = 'Native Open Assets - metres'
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
        L.mark_asset(obs[0], a['label'] + ' / opaque vertex-colour geometry / 3 LODs', ['Native', 'NZ', a['family'], 'Grand Tour'])
        lod0[a['asset']] = obs[0]
        fam = {'Harakeke': 'HARAKEKE', 'Coprosma': 'COPROSMA', 'Matagouri': 'MATAGOURI', 'TiKouka': 'TI KOUKA', 'Kanuka': 'KANUKA'}[a['family']]
        labels[a['asset']] = (fam, a['variant'])
    L.write_manifest(rows, set_name='open', extra=dict(open_stage='NP2', open_seeds={a['asset']: B.seed_of(a) for a in assets},
                                      open_lod_rule='one design per asset; trunks, branches, leaders and lattice twigs kept at every LOD (lattice twigs flat ribbons at LOD1/2, finest lattice levels dropped at LOD2, korari side branches dropped at LOD2); foliage items (straps, pods, leaves, spines, needle sprays) the largest even subset fitting 96 % of each ceiling, enlarged 1.0/1.3/1.55; flax leaves all kept (7 / 3 / 2 across)'))
    print('MANIFEST', len(rows), 'rows', '%.1fs' % (time.time() - t0))
    renders = []
    if not NO_RENDER:
        s1 = B.lineup(lod0, labels, order=LINEUP_ORDER, title='GRAND TOUR / NATIVE PLANTS / MARGIN AND HIGH COUNTRY',
                      subtitle='NP2   10 MESHES   TRUE SCALE   MODELLED FOLIAGE   THREE LODS   POSTS 1.8 M', name='Open Lineup', top=12.0)
        renders.append(L.render(s1, OUT / 'Lineup_Open.png', 2000, 800))
        print('RENDERED Lineup', '%.1fs' % (time.time() - t0))
        s2 = B.detail_scene(); s2.name = 'Open Detail'
        fig = L.flat_material('Review | Figure', (.55, .36, .16))
        for a in assets:
            nm = a['asset'].replace('SM_NZ_', '')
            lo, hi = B.bbox(lod0[a['asset']])
            renders.append(B.render_detail(s2, lod0[a['asset']], a['asset'], OUT / ('Detail_%s.png' % nm), fig, inset=False,
                                           fig_at=(lo.x - .5, (lo.y + hi.y) / 2)))
            print('RENDERED Detail', nm, '%.1fs' % (time.time() - t0))
        if ONLY is None:
            s3 = assembly_edge(lod0)
            renders.append(L.render(s3, OUT / 'Assembly_Edge.png', 2000, 1333))
            print('RENDERED Assembly', '%.1fs' % (time.time() - t0))
    try:
        bpy.context.window.scene = bpy.data.scenes['Native Open Assets - metres']
    except Exception:
        pass
    blend = OUT / 'GrandTour_NativePlants_Open.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    for b in OUT.glob('*.blend1'):
        b.unlink()
    for p in renders:
        print('RENDER', p)
    print('NATIVE_OPEN_BUILD_OK', len(assets), 'meshes', len(rows), 'lods', '%.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
