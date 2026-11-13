"""S2b Southland verge set (docs/SOUTHLAND_ASSET_PLAN.md) on the native plant kit's pipeline: gorse A/B, broom,
rush A/B, thistle, verge tussock A/B, radiata pine young/mature, macrocarpa and the ground-litter props
(twig litter A/B, root tangle, leaf litter) as deterministic Blender geometry, three authored LODs each, FBX (cm)
+ GLB (m), manifest rows (set 'verge'), the set .blend and review renders.

Run: blender -b --factory-startup --python-exit-code 1 --python build_southland_verge.py [-- --only X,Y --no-render --no-assembly --assembly-only]
Each asset is designed once from its fixed seed (58000 + 97 k; all RNG is drawn in the design), then emitted at
LOD0/1/2 from that one design, so the RNG is consumed identically at every LOD.

Every foliage or litter element is an `item`: a function fn(geo, lod) whose triangle cost per LOD is measured by
drawing it once into a scratch buffer. Structure (stems, trunks, branches, whips, roots) is kept at every LOD;
items are grouped, each group takes the largest even subset that fits its share of the 96 % ceiling, and LOD1/2
draw the items LOD0 kept, enlarged 1.0 / 1.3 / 1.55 (the kit's rule).

Ground rule: the lowest vertex of every LOD sits 6 cm below the ground plane (roots, stems, buried stones and the
rim leaves are what go down there); the pivot is the ground point under the middle of the object.
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
ASM_SEL = set(ARGS[ARGS.index('--asm') + 1].split(',')) if '--asm' in ARGS else None
OUT = L.OUT
D2R = math.radians
ENL = B.ENLARGE
ROOT_Z = -.06
LITTER_FACTOR = float(ARGS[ARGS.index('--litter-factor') + 1]) if '--litter-factor' in ARGS else 5.5
ASM_COUNTS = {}

# ---------------------------------------------------------------- colours (linear RGB; dark and desaturated, tint is luminance only)
GORSE_WOOD = (.16, .13, .10); GORSE_NEEDLE = (.07, .13, .05); GORSE_TIP = (.11, .17, .07); GORSE_FLOWER = (.80, .60, .06); GORSE_DEAD = (.18, .13, .08)
BROOM = (.14, .22, .08); BROOM_BASE = (.12, .15, .07); BROOM_LEAF = (.12, .21, .07)
RUSH = (.09, .14, .06); RUSH_DEAD = (.25, .18, .09)
THIS_LEAF = (.18, .24, .12); THIS_PURPLE = (.35, .12, .30); THIS_CUP = (.10, .17, .07); THIS_STALK = (.13, .19, .08)
TUSS = (.16, .24, .09); TUSS_STRAW = (.40, .36, .20); TUSS_SEED = (.55, .50, .30)
RAD_NEEDLE = (.06, .12, .05); RAD_BARK = (.095, .056, .038); RAD_PLATE = (.135, .10, .082); RAD_DEAD = (.15, .11, .075)
MAC_BARK = (.085, .066, .052); MAC_STRIP = (.135, .11, .088); MAC_LEAF = (.07, .12, .05); MASS_DARK = (.04, .075, .032)
TWIG = (.14, .10, .07); TWIG_PALE = (.26, .22, .17); SCRAP = (.12, .08, .04); STONE = (.13, .13, .12)
ROOT = (.075, .060, .045); MOSS = (.10, .15, .06)
LEAFB = (.13, .088, .040); LEAFD = (.065, .048, .024)

ASSETS = [
    dict(asset='SM_NZ_Gorse_A', family='Gorse', variant='A', label='GORSE A', slots=[1], budget=(9000, 3000, 800), hulls=0),
    dict(asset='SM_NZ_Gorse_B', family='Gorse', variant='B', label='GORSE B', slots=[1], budget=(9000, 3000, 800), hulls=0),
    dict(asset='SM_NZ_Broom_A', family='Broom', variant='A', label='BROOM', slots=[1], budget=(4000, 1200, 300), hulls=0),
    dict(asset='SM_NZ_Rush_A', family='Rush', variant='A', label='RUSH A', slots=[1], budget=(1500, 500, 120), hulls=0),
    dict(asset='SM_NZ_Rush_B', family='Rush', variant='B', label='RUSH B', slots=[1], budget=(1500, 500, 120), hulls=0),
    dict(asset='SM_NZ_Thistle_A', family='Thistle', variant='A', label='THISTLE', slots=[1], budget=(2000, 600, 150), hulls=0),
    dict(asset='SM_NZ_VergeTussock_A', family='VergeTussock', variant='A', label='VERGE TUSSOCK A', slots=[1], budget=(1200, 400, 100), hulls=0),
    dict(asset='SM_NZ_VergeTussock_B', family='VergeTussock', variant='B', label='VERGE TUSSOCK B', slots=[1], budget=(1200, 400, 100), hulls=0),
    dict(asset='SM_NZ_Radiata_Young', family='Radiata', variant='Young', label='RADIATA YOUNG', slots=[0, 1], budget=(10000, 3000, 800), hulls=1),
    dict(asset='SM_NZ_Radiata_Mature', family='Radiata', variant='Mature', label='RADIATA MATURE', slots=[0, 1], budget=(16000, 5000, 1200), hulls=2),
    dict(asset='SM_NZ_Macrocarpa', family='Macrocarpa', variant='', label='MACROCARPA', slots=[0, 1], budget=(16000, 5000, 1200), hulls=2),
    dict(asset='SM_NZ_TwigLitter_A', family='TwigLitter', variant='A', label='TWIG LITTER A', slots=[1], budget=(900, 300, 80), hulls=0),
    dict(asset='SM_NZ_TwigLitter_B', family='TwigLitter', variant='B', label='TWIG LITTER B', slots=[1], budget=(900, 300, 80), hulls=0),
    dict(asset='SM_NZ_RootTangle_A', family='RootTangle', variant='A', label='ROOT TANGLE', slots=[1], budget=(1200, 400, 100), hulls=0),
    dict(asset='SM_NZ_LeafLitter_A', family='LeafLitter', variant='A', label='LEAF LITTER', slots=[1], budget=(600, 200, 60), hulls=0),
]
for _k, _a in enumerate(ASSETS):
    _a['k'] = _k


def seed_of(a):
    return 58000 + 97 * a['k']


# ================================================================ shared machinery

def tris(g):
    return sum(len(f) - 2 for f in g.f)


def jit(rng, s):
    return Vector((rng.uniform(-s, s), rng.uniform(-s, s), rng.uniform(-s, s)))


def hflat(v, fallback=Vector((1, 0, 0))):
    h = Vector((v.x, v.y, 0))
    return h.normalized() if h.length > 1e-4 else fallback.copy()


def mot(c, p, amt=.12, salt=31.0):
    return scale_col(c, 1 + amt * (2 * hnoise(p, salt) - 1))


class VD(B.Design):
    """The kit's design container plus measured foliage/litter items and their group shares."""

    def __init__(self, budget):
        super().__init__()
        self.items = []; self.shares = []; self.note = {}; self.post = None; self.budget = budget


def item(D, fn, group):
    """A foliage or litter element. Its triangle cost at each LOD is measured by drawing it into a scratch buffer."""
    cost = []
    for lod in range(3):
        t = L.Geo(); fn(t, lod); cost.append(tris(t))
    D.items.append(dict(fn=fn, group=group, cost=cost))


def emit(D, lod, budget, base_kept=None):
    g, _ = B.emit(D, lod, budget)
    wood = tris(g)
    room = B.FILL * budget - wood
    assert room > 0, 'structure alone (%d) fills the LOD%d ceiling %d' % (wood, lod, budget)
    pool = list(range(len(D.items))) if base_kept is None else base_kept
    kept = []; avail = room
    for grp, share in D.shares:
        sub = [i for i in pool if D.items[i]['group'] == grp]
        cost = (lambda i: D.items[i]['cost'][lod])
        pick = B.fit_subset(sub, cost, min(avail, share * room))
        avail -= sum(cost(i) for i in pick)
        kept += pick
    for i in sorted(kept):
        D.items[i]['fn'](g, lod)
    if D.post:
        D.post(g, lod)
    for v in g.v:
        if v.z < ROOT_Z:
            v.z = ROOT_Z
    mn = min(v.z for v in g.v)
    if mn > ROOT_Z + .003:
        print('WARNING lowest vertex %.3f m: shifting the mesh down' % mn)
        for v in g.v:
            v.z += ROOT_Z - mn
    return g, sorted(kept), wood


def tube_cols(g, pts, radii, sides, ring_cols, mi=1, caps=(False, True), noise=0.0, phase=0.0):
    """A tube whose rings take their own colour (stems that go brown toward the tip)."""
    start, n = L.tube(g, pts, radii, sides, (0, 0, 0), mi, caps, noise, phase=phase)
    for i in range(n):
        for j in range(sides):
            g.c[start + i * sides + j] = ring_cols[i]
    return start, n


def ribbon_path(g, pts, w0, w1, roll, colour, mi=1, cols=None):
    """A flat tapering ribbon along a polyline ending in a point (3 triangles for a 3-point path)."""
    n = len(pts); sides = []; ups = []
    for i in range(n):
        T = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        s = rot(L.perp(T), T, roll)
        sides.append(s); ups.append(T.cross(s).normalized())
    hw = [lerp(w0, w1, i / (n - 1)) for i in range(n)]
    L.strip(g, pts, hw, hw, sides, ups, colour, mi, 0.0, tip=True, colours=cols)


def wood_layer(D, twigs, colour_fn, mi=1, shares=(.30, .22)):
    """Structural twigs: LOD0 tubes (5/4/3 sides by radius), LOD1 and LOD2 flat ribbons for as many levels as fit
    `shares` of those ceilings (the deepest levels drop first)."""
    per = [0] * 14
    for t in twigs:
        per[t['level']] += 1

    def depth(room):
        lev = 0
        while lev < 12 and sum(per[:lev + 2]) * 2 <= room:
            lev += 1
        return lev
    lods = (99, depth(shares[0] * D.budget[1]), depth(shares[1] * D.budget[2]))
    D.note['ribbon_levels'] = list(lods[1:])
    for t in twigs:
        t['ref'] = Vector((hnoise(t['a'], 1.0) - .5, hnoise(t['a'], 2.0) - .5, hnoise(t['a'], 3.0) - .5)) + Vector((.01, .02, .03))
        t['col'] = colour_fn(t)

    def fn(g, lod):
        for t in twigs:
            if lod == 0:
                sd = 5 if t['r0'] >= .02 else 4 if t['r0'] >= .009 else 3
                L.tube(g, [t['a'], t['b']], [max(t['r0'], .0016), max(t['r1'], .0012)], sd, t['col'], mi, (False, False), noise=0)
            elif t['level'] <= lods[lod]:
                L.ribbon(g, t['a'], t['b'], max(t['r0'], .0016) * ENL[lod], max(t['r1'], .0012) * ENL[lod], t['ref'], t['col'], mi)
    D.extra(fn)


# ================================================================ shrub envelope and twig growth (gorse)

class Mound:
    """Irregular superellipsoid mound standing on the ground: rho = 1 on the shell."""

    def __init__(s, R, H, rng, pw=2.6):
        s.R = R; s.H = H; s.pw = pw; s.ph = [rng.uniform(0, math.tau) for _ in range(4)]

    def Ra(s, az):
        return s.R * (1 + .16 * math.sin(2 * az + s.ph[0]) + .11 * math.sin(3 * az + s.ph[1]) + .07 * math.sin(5 * az + s.ph[2]))

    def Ha(s, az):
        return s.H * (1 + .13 * math.sin(3 * az + s.ph[3]) + .06 * math.sin(5 * az + s.ph[0]))

    def rho(s, q):
        az = math.atan2(q.y, q.x); r = math.hypot(q.x, q.y) / s.Ra(az); z = max(q.z, 0.0) / s.Ha(az)
        return (r ** s.pw + z ** s.pw) ** (1 / s.pw)

    def out(s, q):
        az = math.atan2(q.y, q.x); Ra = s.Ra(az); Ha = s.Ha(az)
        v = Vector((q.x / (Ra * Ra), q.y / (Ra * Ra), max(q.z, 0.0) / (Ha * Ha)))
        return v.normalized() if v.length > 1e-6 else Z.copy()


def grow_twigs(rng, M, c):
    """Monopodial growth inside the mound: a continuing child bending outward and up, plus 0-2 laterals; a twig
    that would leave the mound is clipped to the shell and ends there (the dead interior is what is left behind)."""
    twigs = []

    def rec(p, d, ln, r, lev):
        q = p + d * ln
        term = False
        if M.rho(q) > 1.0:
            lo, hi = 0.0, 1.0
            for _ in range(9):
                mid = (lo + hi) / 2
                if M.rho(p + d * ln * mid) > 1.0:
                    hi = mid
                else:
                    lo = mid
            if lo < .18:
                return None
            q = p + d * ln * lo; term = True
        t = dict(a=p.copy(), b=q.copy(), r0=r, r1=max(r * .8, .0013), level=lev, term=term, kids=0)
        twigs.append(t)
        if term or lev >= c['maxd']:
            t['term'] = True
            return t
        out = M.out(q)
        d1 = (d + out * rng.uniform(.25, .5) + Z * .08 + jit(rng, .22)).normalized()
        if rec(q, d1, ln * c['decay'] * rng.uniform(.85, 1.12), r * c['rdecay'], lev + 1):
            t['kids'] += 1
        fp = c['fork'][min(lev, len(c['fork']) - 1)]
        nlat = 1 if rng.random() < fp else 0
        if rng.random() < fp * .4:
            nlat += 1
        for _ in range(nlat):
            ax = rot(L.perp(d), d, rng.uniform(0, math.tau))
            sd = (rot(d, ax, D2R(rng.uniform(32, 62))) + out * .3).normalized()
            if rec(q, sd, ln * c['decay'] * rng.uniform(.6, .95), r * c['rdecay'] * .85, lev + 1):
                t['kids'] += 1
        if t['kids'] == 0:
            t['term'] = True
        return t
    for i in range(c['stems']):
        az = i * math.tau / c['stems'] + rng.uniform(-.3, .3)
        el = D2R(rng.uniform(70, 82)) if i % 3 == 0 else D2R(rng.uniform(*c['el']))
        d0 = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
        base = Vector((math.cos(az), math.sin(az), 0)) * rng.uniform(.02, .09) + Vector((0, 0, ROOT_Z))
        rec(base, d0, c['L0'] * rng.uniform(.8, 1.2), c['r0'] * rng.uniform(.85, 1.15), 0)
    return twigs


# ================================================================ gorse

GORSE = {
    'A': dict(H=1.48, R=.85, stems=9, el=(36, 66), L0=.44, r0=.012, maxd=6, decay=.85, rdecay=.70, fork=[.8, .7, .5, .4, .3, .2],
              flower=.20, dead_rho=.55, spray=(.09, .13), width=.12, nshell=760, zmin=.06, nmass=1000, mass=(.11, .17), mass_share=.26),
    'B': dict(H=2.02, R=1.15, stems=12, el=(42, 74), L0=.62, r0=.024, maxd=6, decay=.85, rdecay=.70, fork=[.8, .7, .5, .4, .3, .2],
              flower=.05, dead_rho=.68, spray=(.12, .18), width=.12, nshell=1000, zmin=.06, nmass=1300, mass=(.15, .23), mass_share=.28),
}


def nearest_on_twigs(twigs, p):
    """Closest point on any twig segment to p."""
    best = None; bd = 1e9
    for t in twigs:
        ab = t['b'] - t['a']; l2 = ab.dot(ab)
        u = clamp((p - t['a']).dot(ab) / l2) if l2 > 1e-9 else 0.0
        q = t['a'] + ab * u
        d = (p - q).length_squared
        if d < bd:
            bd = d; best = q
    return best, math.sqrt(bd)


def gorse(v, rng, a):
    """Dense spiny mound: a woody framework of grey-brown stems and twigs grown inside an irregular dome, dead brown
    twigs left in the interior, and dark green needle sprays with paler tips spread evenly over the outer shell (each
    on a short twiglet back to the framework), yellow flower clusters on a clumpy share of the sprays (20 % on A, 5 %
    on B)."""
    c = GORSE[v]; D = VD(a['budget']); M = Mound(c['R'], c['H'], rng)
    twigs = grow_twigs(rng, M, c)
    for t in twigs:
        rb = M.rho(t['b'])
        t['dead'] = rb < c['dead_rho'] or (v == 'B' and t['b'].z < .55 and rng.random() < .55)
    wood_layer(D, twigs, lambda t: mot(GORSE_DEAD if t['dead'] else GORSE_WOOD, t['a'], .16), 1, shares=(.30, .20))
    live = [t for t in twigs if not t['dead'] and t['level'] >= 1]
    sp = []
    N = c['nshell']
    for i in range(N):
        zz = (i + .5) / N; phi = i * 2.39996 + rng.uniform(-.25, .25)
        rr = math.sqrt(1 - zz * zz)
        dv = Vector((rr * math.cos(phi), rr * math.sin(phi), max(zz, .04) * c['H'] / c['R']))
        lo, hi = 0.0, 4.0
        for _ in range(14):
            mid = (lo + hi) / 2
            if M.rho(dv * mid) > 1.0:
                hi = mid
            else:
                lo = mid
        pos = dv * lo * rng.uniform(.80, 1.0)
        if pos.z < c['zmin'] or (v == 'B' and pos.z < .46):
            continue
        out = M.out(pos)
        dd = (out * .85 + jit(rng, .5) + Z * .12).normalized()
        up = rot(L.perp(dd), dd, rng.uniform(0, math.tau))
        ln = rng.uniform(*c['spray'])
        shade = .86 + .14 * clamp(pos.z / c['H'])
        col = scale_col(GORSE_NEEDLE, shade * rng.uniform(.9, 1.1)); tip = scale_col(GORSE_TIP, shade * rng.uniform(.9, 1.1))
        sp.append(dict(pos=pos, dd=dd, up=up, ln=ln, col=col, tip=tip, fl=None, att=None))
    nf = int(round(c['flower'] * len(sp)))
    order = sorted(range(len(sp)), key=lambda i: -vnoise(sp[i]['pos'], .42, 5.0))
    for i in order[:nf]:
        s_ = sp[i]
        s_['fl'] = [(s_['pos'] + s_['dd'] * s_['ln'] * rng.uniform(.5, 1.0) + jit(rng, .035), jit(rng, 1).normalized(), (Z + jit(rng, .8)).normalized(),
                     scale_col(GORSE_FLOWER, rng.uniform(.9, 1.1))) for _ in range(4)]
    for s_ in sp:
        def fn(g, lod, s=s_):
            e = ENL[lod]
            if lod < 2:
                L.needles(g, s['pos'], s['dd'], s['ln'] * e, s['col'], s['tip'], s['up'], fan=D2R(36), width=c['width'])
                if s['fl']:
                    for q, d_, n_, col in (s['fl'] if lod == 0 else s['fl'][:2]):
                        L.leaflet(g, q, d_, .034 * e, .028 * e, n_, col)
            else:
                col = mix(s['col'], s['tip'], .4)
                if s['fl']:
                    col = mix(col, GORSE_FLOWER, .5)
                L.leaflet(g, s['pos'] + s['dd'] * s['ln'] * e * .5, s['dd'], s['ln'] * e, s['ln'] * e * .5, s['up'], col)
        item(D, fn, 'spray')
    # the dense dark mass under the spiky sprays: big folded diamonds scattered over the inner shell, lying along it
    nm = 0
    for i in range(c['nmass']):
        zz = (i + .5) / c['nmass']; phi = i * 2.39996 + 1.1 + rng.uniform(-.3, .3)
        rr = math.sqrt(1 - zz * zz)
        dv = Vector((rr * math.cos(phi), rr * math.sin(phi), max(zz, .05) * c['H'] / c['R']))
        lo, hi = 0.0, 4.0
        for _ in range(14):
            mid = (lo + hi) / 2
            if M.rho(dv * mid) > 1.0:
                hi = mid
            else:
                lo = mid
        pos = dv * lo * rng.uniform(.70, .93)
        if pos.z < c['zmin'] + .04 or (v == 'B' and pos.z < .50):
            continue
        nrm = (M.out(pos) + jit(rng, .45)).normalized()
        dd = (rot(L.perp(nrm), nrm, rng.uniform(0, math.tau)) + Z * .25).normalized()
        size = rng.uniform(*c['mass'])
        shade = (.80 + .16 * clamp(pos.z / c['H'])) * rng.uniform(.9, 1.1)
        col = scale_col(GORSE_NEEDLE, shade * .82)
        nm += 1

        def mfn(g, lod, pos=pos, dd=dd, nrm=nrm, size=size, col=col):
            L.leaflet(g, pos, dd, size * ENL[lod], size * ENL[lod] * .38, nrm, col)
        item(D, mfn, 'mass')
    D.shares = [('mass', c['mass_share']), ('spray', 1.0)]
    D.note.update(twigs=len(twigs), sprays_designed=len(sp), mass_designed=nm, flowering=nf, dead_twigs=sum(1 for t in twigs if t['dead']))
    return D


# ================================================================ broom

def broom(v, rng, a):
    """Upright green whips (3-sided tubes) fanning from the base and arching outward at the top, a feathery mass of
    thin side shoots along their upper four fifths, sparse tiny leaves, 10 % of the shoot tips carrying yellow
    flower clusters."""
    D = VD(a['budget'])
    n = 38; whips = []
    for i in range(n):
        az = i * 2.39996 + rng.uniform(-.25, .25)
        tilt = D2R(rng.uniform(4, 22)); ln = rng.uniform(1.5, 2.1)
        out = Vector((math.cos(az), math.sin(az), 0))
        p = Vector((math.cos(az), math.sin(az), 0)) * rng.uniform(.01, .07) + Vector((0, 0, ROOT_Z))
        d = polar(tilt, az); pts = [p.copy()]; ns = 10
        for k in range(ns):
            tk = (k + .5) / ns
            d = (d + out * (.14 * tk) + jit(rng, .025)).normalized()
            pts.append(pts[-1] + d * (ln / ns))
        whips.append(dict(pts=pts, r=rng.uniform(.0065, .0090), tint=rng.uniform(.88, 1.12)))
    zmax = max(w['pts'][-1].z for w in whips)
    for w in whips:
        w['pts'] = [Vector((q.x, q.y, q.z * (1.95 / zmax) if q.z > 0 else q.z)) for q in w['pts']]
        w['dense'] = L.curve(w['pts'], 4)

    def wfn(g, lod):
        for k, w in enumerate(whips):
            segs = (6, 3, 2)[lod]
            pts, fr = L.resample(w['dense'], segs)
            if lod < 2:
                radii = [w['r'] * (1 - .6 * f) * (1 if lod == 0 else 1.15) for f in fr]
                cols = [scale_col(mix(BROOM_BASE, BROOM, smoothstep(0, .35, f)), w['tint']) for f in fr]
                tube_cols(g, pts, radii, 3, cols, 1, (False, True), 0.0)
            else:
                ribbon_path(g, pts, w['r'] * 1.6 * ENL[2], w['r'] * .6, k * .9, scale_col(BROOM, w['tint']))
    D.extra(wfn)
    shoots = []; leaves = []
    for k, w in enumerate(whips):
        t = .10; s = 0
        while t < .97:
            p, T = L.along(w['dense'], t)
            az = (k * 1.7 + s * 2.399) + rng.uniform(-.5, .5)
            e0 = rng.uniform(30, 52)
            sd = (T * math.cos(D2R(e0)) + rot(L.perp(T), T, az) * math.sin(D2R(e0))).normalized()
            sd = (sd + Z * .18).normalized()
            ln = rng.uniform(.17, .40) * (1.0 - .45 * t)
            e = p + sd * ln + jit(rng, .015)
            mid = p.lerp(e, .5) + jit(rng, .012) + Z * .02 * ln
            fl = rng.random() < .10
            shoots.append(dict(a=p, m=mid, b=e, fl=fl, tint=rng.uniform(.88, 1.12), roll=rng.uniform(0, 3)))
            for j in range(rng.randint(2, 3)):
                u = rng.uniform(.35, 1.0)
                q = p.lerp(mid, u * 2) if u < .5 else mid.lerp(e, (u - .5) * 2)
                leaves.append(dict(pos=q, d=(sd + jit(rng, .9)).normalized(), n=(Z + jit(rng, .9)).normalized(), tint=rng.uniform(.88, 1.12)))
            s += 1
            t += rng.uniform(.030, .046)
    for sh in shoots:
        def fn(g, lod, sh=sh):
            col = scale_col(BROOM, sh['tint'])
            if lod == 0:
                ribbon_path(g, [sh['a'], sh['m'], sh['b']], .0050, .0014, sh['roll'], col)
            else:
                L.ribbon(g, sh['a'], sh['b'], .0050 * ENL[lod], .0016 * ENL[lod], Z + Vector((.3, .2, 0)) * sh['roll'], col, 1)
            if sh['fl']:
                n_ = 3 if lod == 0 else 1 if lod == 1 else 0
                dd = (sh['b'] - sh['a']).normalized()
                for q in range(n_):
                    L.leaflet(g, sh['b'] - dd * .022 * q, dd, .034 * ENL[lod], .028 * ENL[lod],
                              (Z + Vector((.3 * q, -.2 * q, 0))).normalized(), scale_col(GORSE_FLOWER, 1.0 - .06 * q))
        item(D, fn, 'shoot')
    for lf in leaves:
        def lfn(g, lod, lf=lf):
            if lod < 2:
                L.leaflet(g, lf['pos'], lf['d'], .016 * ENL[lod], .008 * ENL[lod], lf['n'], scale_col(BROOM_LEAF, lf['tint']))
        item(D, lfn, 'leaf')
    D.shares = [('shoot', .86), ('leaf', 1.0)]
    D.note.update(whips=n, shoots_designed=len(shoots), leaves_designed=len(leaves), flowering_shoots=sum(1 for s_ in shoots if s_['fl']))
    return D


# ================================================================ rush

RUSHC = {'A': dict(n=80, Lmax=.68, segs=2, r=.0026, lying=4), 'B': dict(n=66, Lmax=1.0, segs=3, r=.0030, lying=4)}


def rush(v, rng, a):
    """Juncus clump: 60-90 stiff cylindrical 3-sided stems from a tight base flaring 15-25 degrees, dark green with
    brown dead tips on 30 %, and a few collapsed stems lying out and down."""
    c = RUSHC[v]; D = VD(a['budget'])
    for i in range(c['n']):
        az = i * 2.39996 + rng.uniform(-.4, .4)
        rb = rng.uniform(.004, .032)
        base = Vector((math.cos(az), math.sin(az), 0)) * rb + Vector((0, 0, ROOT_Z))
        th0 = D2R(rng.uniform(10, 25)); th1 = th0 + D2R(rng.uniform(6, 16))
        ln = c['Lmax'] * rng.uniform(.62, 1.0) * (1 - .22 * (th0 - D2R(10)) / D2R(15))
        pts = [base]
        for k in range(10):
            t = (k + .5) / 10
            pts.append(pts[-1] + polar(th0 + (th1 - th0) * t ** 1.4, az) * (ln / 10))
        dead = rng.random() < .30
        tdead = rng.uniform(.16, .40) if dead else 0.0
        tint = rng.uniform(.88, 1.12)
        item(D, _rush_stem(c, pts, dead, tdead, tint, rng.uniform(0, 3)), 'stem')
    for i in range(c['lying']):
        az = rng.uniform(0, math.tau); out = Vector((math.cos(az), math.sin(az), 0))
        base = out * rng.uniform(.01, .03) + Vector((0, 0, ROOT_Z))
        ln = c['Lmax'] * rng.uniform(.40, .62)
        pts = [base]; zrise = rng.uniform(.07, .12) * c['Lmax'] / .68
        side_ = Vector((-out.y, out.x, 0)) * rng.uniform(-.10, .10)
        for k in range(1, 11):
            t = k / 10
            pts.append(Vector((base.x + out.x * ln * t + side_.x * t * t, base.y + out.y * ln * t + side_.y * t * t, .012 + zrise * math.sin(math.pi * t) ** 1.25)))
        item(D, _rush_stem(c, pts, True, rng.uniform(.0, .5), rng.uniform(.9, 1.1), rng.uniform(0, 3), lying=True), 'lying')
    D.shares = [('lying', .16), ('stem', 1.0)]
    D.note.update(stems=c['n'], lying=c['lying'])
    return D


def _rush_stem(c, pts, dead, tdead, tint, roll, lying=False):
    dense = L.curve(pts, 2)

    def fn(g, lod):
        segs = (c['segs'] if not lying else 9, 2 if not lying else 3, 1 if not lying else 2)[lod]
        p, fr = L.resample(dense, segs)
        cols = [scale_col(RUSH_DEAD if (dead and f > 1 - tdead) else RUSH if not lying else mix(RUSH, RUSH_DEAD, .55), tint) for f in fr]
        if lod == 0:
            radii = [c['r'] * (1.1 if lying else 1.0) * (1 - .55 * f) for f in fr]
            tube_cols(g, p, radii, 3, cols, 1, (False, True), 0.0)
        else:
            w = c['r'] * 1.5 * ENL[lod] * (1.0 if lod == 1 else 1.8)
            ribbon_path(g, p, w, w * .4, roll, cols[0], 1, cols if lod == 1 and len(cols) == len(p) else None)
    return fn


# ================================================================ thistle

def thistle(v, rng, a):
    """Spiny basal rosette of 12 lobed grey-green leaves (alternating half-widths, spines at the lobe tips), three
    ribbed stalks with bracts and purple heads on spiny green cups."""
    D = VD(a['budget'])
    nl = 14; a0 = rng.uniform(0, math.tau)
    for i in range(nl):
        az = a0 + i * 2.39996 + rng.uniform(-.2, .2)
        e0 = D2R(rng.uniform(12, 38)); ln = rng.uniform(.38, .60); dp = D2R(rng.uniform(25, 55))
        anchor = Vector((math.cos(az), math.sin(az), 0)) * .02 + Vector((0, 0, .03 + .004 * i))
        tint = rng.uniform(.80, 1.0); wmax = ln * rng.uniform(.16, .21)
        pts, tans, sides, ups = L.frond_path(anchor, polar(D2R(90) - e0, az), ln, dp, 9, 1.6, 0.0, rng.uniform(-.15, .15), .015)
        item(D, _thistle_leaf(pts, sides, ups, ln, wmax, tint), 'rosette')
    heights = [1.05, .90, .78]; az0 = rng.uniform(0, math.tau)
    for k, h in enumerate(heights):
        az = az0 + k * 2.1
        lean = D2R(rng.uniform(3, 10)) * (1 if k else .5)
        base = Vector((math.cos(az), math.sin(az), 0)) * .03 + Vector((0, 0, ROOT_Z))
        pts = [base]; d = polar(lean, az + rng.uniform(-.5, .5))
        for s in range(10):
            d = (d + jit(rng, .03)).normalized(); pts.append(pts[-1] + d * (h + .06) / 10)
        sc = h / (pts[-1].z or 1)
        pts = [Vector((q.x, q.y, q.z * sc if q.z > 0 else q.z)) for q in pts]
        dense = L.curve(pts, 3)
        item(D, _thistle_stalk(dense, rng.uniform(.9, 1.1)), 'stalk')
        for j in range(5):
            t = .18 + .13 * j + rng.uniform(-.02, .02)
            p, T = L.along(dense, t)
            ba = az + j * 2.4 + rng.uniform(-.3, .3)
            sd = (T * .55 + Vector((math.cos(ba), math.sin(ba), 0)) * .8).normalized()
            item(D, _thistle_bract(p, sd, .10 * (1.15 - t), rng.uniform(.88, 1.12)), 'stalk')
        top = pts[-1]; T_end = (pts[-1] - pts[-2]).normalized()
        item(D, _thistle_head(top, T_end, 1.4, rng.uniform(.9, 1.1)), 'head')
        for j in range(2 if k == 0 else 1):
            p, T = L.along(dense, .78 - .08 * j)
            ba = az + (j * 3.1) + rng.uniform(-.3, .3)
            sd = (T * .7 + Vector((math.cos(ba), math.sin(ba), 0)) * .55).normalized()
            ln = rng.uniform(.10, .17)
            e = p + sd * ln
            item(D, _thistle_pedicel(p, e, T), 'stalk')
            item(D, _thistle_head(e, sd, 1.1, rng.uniform(.9, 1.1)), 'head')
    D.shares = [('stalk', .34), ('head', .36), ('rosette', 1.0)]
    D.note.update(leaves=nl)
    return D


def _thistle_leaf(pts, sides, ups, ln, wmax, tint):
    def fn(g, lod):
        idx = list(range(10)) if lod == 0 else [0, 2, 4, 6, 8, 9] if lod == 1 else [0, 5, 9]
        cen = [pts[i] for i in idx]; sd = [sides[i] for i in idx]; up = [ups[i] for i in idx]
        hl = []; hr = []
        for jj, i in enumerate(idx):
            t = i / 9
            env = wmax * (.25 + .75 * math.sin(math.pi * min(1, (t + .12) / 1.12)) ** .8) * (1 - .7 * smoothstep(.7, 1, t))
            if lod == 0:
                hl.append(env * (1.0 if i % 2 == 0 else .5)); hr.append(env * (.5 if i % 2 == 0 else 1.0))
            else:
                hl.append(env * .85 * ENL[lod] ** .5); hr.append(env * .85 * ENL[lod] ** .5)
        cols = [scale_col(THIS_LEAF, tint * (.86 + .22 * (i / 9))) for i in idx]
        L.strip(g, cen, hl, hr, sd, up, cols[0], 1, math.tan(D2R(14)) if lod == 0 else 0.0, tip=True, colours=cols)
        if lod == 0:
            for i in (3, 4, 5, 6, 7):
                tdir = (pts[i + 1] - pts[i - 1]).normalized()
                env = wmax * (.25 + .75 * math.sin(math.pi * min(1, (i / 9 + .12) / 1.12)) ** .8) * (1 - .7 * smoothstep(.7, 1, i / 9))
                s_ = sides[i] * (1 if i % 2 == 0 else -1)
                base = pts[i] + s_ * env
                L.spine(g, base, (s_ * .8 + tdir * .55 + ups[i] * .25).normalized(), .022, .0025, scale_col(THIS_LEAF, 1.25), 1)
    return fn


def _thistle_stalk(dense, tint):
    def fn(g, lod):
        pts, fr = L.resample(dense, (8, 4, 2)[lod])
        radii = [lerp(.0105, .0055, f) for f in fr]
        if lod == 0:
            L.tube(g, pts, radii, 6, scale_col(THIS_STALK, tint), 1, (False, True), noise=.22)
        elif lod == 1:
            L.tube(g, pts, [r * 1.2 for r in radii], 4, scale_col(THIS_STALK, tint), 1, (False, True), noise=0)
        else:
            ribbon_path(g, pts, .011, .005, 0.4, scale_col(THIS_STALK, tint))
    return fn


def _thistle_pedicel(p, e, T):
    def fn(g, lod):
        if lod == 0:
            L.tube(g, [p, e], [.0035, .0030], 4, scale_col(THIS_STALK, 1.0), 1, (False, False), 0)
        elif lod == 1:
            L.ribbon(g, p, e, .005, .004, Z + Vector((.3, .1, 0)), THIS_STALK, 1)
    return fn


def _thistle_bract(p, sd, ln, tint):
    def fn(g, lod):
        if lod == 0:
            side = L.perp(sd); up = sd.cross(side)
            pts = [p + sd * ln * (k / 4) + Z * (.014 * math.sin(k / 4 * math.pi)) - Z * .01 * (k / 4) ** 2 for k in range(5)]
            hl = [ln * .16 * (1.0 if k % 2 == 0 else .55) * (1 - k / 5) for k in range(5)]
            hr = [ln * .16 * (.55 if k % 2 == 0 else 1.0) * (1 - k / 5) for k in range(5)]
            L.strip(g, pts, hl, hr, [side] * 5, [up] * 5, scale_col(THIS_LEAF, tint * .95), 1, 0.0, tip=True)
        elif lod == 1:
            L.leaflet(g, p + sd * ln * .5, sd, ln, ln * .3, Z, scale_col(THIS_LEAF, tint), 1)
    return fn


def _thistle_head(base, axis, sc, tint):
    def fn(g, lod):
        ax = Vector(axis).normalized(); u = L.perp(ax); v = ax.cross(u)
        r = .021 * sc; h = .026 * sc
        top = base + ax * h
        ring = [top + (u * math.cos(k * math.tau / 8) + v * math.sin(k * math.tau / 8)) * r for k in range(8)]
        cup = scale_col(THIS_CUP, tint)
        g.add([base] + ring, [(0, 1 + (k + 1) % 8, 1 + k) for k in range(8)], cup, [(0, 0)] * 9, 1)
        if lod == 0:
            for k in range(8):
                rd = (ring[k] - top).normalized()
                L.spine(g, ring[k] - ax * .006 * sc, (rd * .75 + ax * .65).normalized(), .017 * sc, .0016, scale_col(THIS_CUP, tint * 1.3), 1)
        nflor = 8 if lod == 0 else 4 if lod == 1 else 1
        for k in range(nflor):
            a_ = k * math.tau / nflor + (.3 if k % 2 else 0)
            rd = u * math.cos(a_) + v * math.sin(a_)
            d = (ax * .85 + rd * (.35 if lod == 0 else .3)).normalized()
            ln = .036 * sc * (1.0 if lod == 0 else 1.35 * ENL[lod] / 1.3)
            wd = .010 * sc * (1.0 if lod == 0 else 1.6)
            L.leaflet(g, top + rd * r * .45 + d * ln * .5, d, ln, wd, rd, scale_col(THIS_PURPLE, tint * (.92 + .12 * (k % 3) / 2)), 1)
    return fn


# ================================================================ verge tussock

TUS = {'A': dict(nb=96, nst=18, H=.5, Lb=(.26, .42), segs=4, stalk=(.34, .44)),
       'B': dict(nb=128, nst=20, H=.8, Lb=(.42, .66), segs=3, stalk=(.58, .70))}


def verge_tussock(v, rng, a):
    """Rank grass tuft: narrow blades arching outward (green, 30 % straw), seed-head stalks rising above with pale
    heads."""
    c = TUS[v]; D = VD(a['budget'])
    for i in range(c['nb']):
        az = i * 2.39996 + rng.uniform(-.3, .3)
        rb = rng.uniform(.004, .05)
        anchor = Vector((math.cos(az), math.sin(az), 0)) * rb + Vector((0, 0, ROOT_Z))
        el = D2R(rng.uniform(52, 82)) if rng.random() < .55 else D2R(rng.uniform(30, 55))
        ln = rng.uniform(*c['Lb']); arch = D2R(rng.uniform(40, 95)); wd = rng.uniform(.0085, .014)
        straw = rng.random() < .30
        tint = rng.uniform(.88, 1.12)
        col = scale_col(TUSS_STRAW if straw else TUSS, tint)
        out = Vector((math.cos(az), math.sin(az), 0))
        # start low so the base is buried: the blade rises from 6 cm down
        d = polar(D2R(90) - el, az)
        kw = dict(anchor=anchor, direction=d, length=ln + .06, width=wd, arch=arch, colour=col, edge_colour=col, arch_dir=out,
                  arch_start=rng.uniform(.38, .55), arch_power=1.4, base_w=.7, roll=rng.uniform(-.3, .3))
        item(D, _blade(kw, c['segs']), 'blade')
    for i in range(c['nst']):
        az = rng.uniform(0, math.tau); out = Vector((math.cos(az), math.sin(az), 0))
        base = out * rng.uniform(.005, .03) + Vector((0, 0, ROOT_Z))
        h = rng.uniform(*c['stalk'])
        lean = D2R(rng.uniform(6, 26))
        pts = [base]; d = polar(lean, az)
        for k in range(6):
            d = (d + out * .04 + jit(rng, .03)).normalized(); pts.append(pts[-1] + d * ((h + .06) / 6))
        sc = h / pts[-1].z
        pts = [Vector((q.x, q.y, q.z * sc if q.z > 0 else q.z)) for q in pts]
        item(D, _seed_stalk(L.curve(pts, 3), rng.uniform(.88, 1.12), rng.uniform(.055, .085)), 'stalk')
    D.shares = [('stalk', .38), ('blade', 1.0)]
    D.note.update(blades=c['nb'], stalks=c['nst'])
    return D


def _blade(kw, segs0):
    def fn(g, lod):
        k2 = dict(kw)
        k2['width'] = kw['width'] * (ENL[lod] if lod < 2 else 2.2)
        L.strap(g, across=2, segs=(segs0, 2, 1)[lod], **k2)
    return fn


def _seed_stalk(dense, tint, hl):
    def fn(g, lod):
        pts, fr = L.resample(dense, (3, 2, 1)[lod])
        col = scale_col(mix(TUSS_STRAW, TUSS, .5), tint)
        if lod == 0:
            L.tube(g, pts, [.0013 * (1 - .4 * f) for f in fr], 3, col, 1, (False, False), 0)
        else:
            ribbon_path(g, pts, .002 * ENL[lod], .0012, .5, col)
        top = pts[-1]; d = (pts[-1] - pts[-2]).normalized()
        e = ENL[lod]; ln = hl * e
        head = scale_col(TUSS_SEED, tint)
        side = L.perp(d)
        if lod == 0:
            for k in range(2):
                n = rot(side, d, k * math.pi / 2)
                L.leaflet(g, top - d * .004 + d * ln * .5, d, ln, ln * .17, n, head, 1)
        else:
            L.leaflet(g, top + d * ln * .4, d, ln, ln * .30, side, head, 1)
    return fn


# ================================================================ trees

RAD_TIP = (.10, .17, .07)


def prof_from(ctrl, rz):
    """Radius profile [(arc fraction, r)] for a tube through ctrl whose radius is a function of height."""
    dense = L.curve(ctrl, 6)
    out = []
    for f in (0, .02, .06, .12, .2, .3, .45, .6, .8, 1.0):
        p, _ = L.along(dense, f)
        out.append((f, rz(p.z)))
    return out


def needle_tuft(D, c0, dirv, size, shade, rng, n, wd, group='pad'):
    """A dense tuft at a branch end: `n` needle sprays fanned about the heading (the last one pointing up), 6 triangles
    each; LOD1 two sprays enlarged, LOD2 one wide quad."""
    h = hflat(dirv, Vector((1, 0, 0)))
    tint = rng.uniform(.9, 1.1)
    col = scale_col(RAD_NEEDLE, shade * tint); tip = scale_col(RAD_TIP, shade * tint)
    rolls = [rng.uniform(-.5, .5) for _ in range(n)]

    def fn(g, lod):
        e = (1.0, 1.7, 2.3)[lod]
        if lod == 0:
            for k in range(n):
                if k == n - 1 and n >= 4:
                    d = (h * .45 + Z * .9).normalized(); up = h
                else:
                    off = (k - (min(n, 3) - 1) / 2) * D2R(46)
                    d = (rot(h, Z, off) * .9 + Vector((0, 0, .18 + .1 * rolls[k]))).normalized()
                    up = rot(Z, d, rolls[k] * .8)
                L.needles(g, c0, d, size, col, tip, up, fan=D2R(30), width=wd)
        elif lod == 1:
            d = (h * .9 + Vector((0, 0, .2))).normalized()
            L.needles(g, c0, d, size * e, col, tip, rot(Z, d, rolls[0] * .8), fan=D2R(34), width=wd)
        else:
            L.leaflet(g, c0 + h * size * e * .5, h, size * e, size * e * .55, Z, mix(col, tip, .35))
    item(D, fn, group)


def flat_pad(D, c0, dirv, size, shade, rng, up_n):
    """Macrocarpa scale-spray pad: two flat fans (spray, 6 triangles each) a little apart; LOD1 one fan of two diamonds,
    LOD2 one diamond."""
    h = hflat(dirv, Vector((1, 0, 0)))
    tint = rng.uniform(.9, 1.1)
    col = scale_col(MAC_LEAF, shade * tint)
    yaw = rng.uniform(.5, 1.0) * (1 if rng.random() < .5 else -1)
    off2 = rng.uniform(.18, .3) * size

    def fn(g, lod):
        e = ENL[lod]
        if lod == 0:
            L.spray(g, c0, h, size, col, up_n)
            L.spray(g, c0 + rot(h, Z, yaw) * off2, rot(h, Z, yaw), size * .92, scale_col(col, .94), up_n)
        elif lod == 1:
            L.spray(g, c0, h, size * 1.4, col, up_n, quads=2)
        else:
            L.spray(g, c0, h, size * 1.9, col, up_n, quads=1)
    item(D, fn, 'pad')


def trunk_ctrl(zs, off):
    return [Vector((off(z)[0], off(z)[1], z)) for z in zs]


def crown_mass(D, rng, samples, size, shade_fn, kind='needle', group='mass'):
    """The dark volume under the tufts: big sprays lying along the crown shell with scattered facing so the shell catches the
    light in flecks, darker the deeper they sit; samples are (pos, normal, depth 0 inner .. 1 outer). kind 'needle': a fan of
    three needle quads (conifer); 'scale': a flat fan of three folded diamonds (macrocarpa)."""
    for pos, nrm, depth in samples:
        nr2 = (nrm + jit(rng, .85)).normalized()
        dd = (rot(L.perp(nr2), nr2, rng.uniform(0, math.tau)) + Z * .1).normalized()
        sz = rng.uniform(*size)
        sh = shade_fn(pos) * (.55 + .55 * depth) * rng.uniform(.9, 1.1)
        col = scale_col(MASS_DARK, sh); tip = scale_col((.075, .125, .05), sh)

        def fn(g, lod, pos=pos, dd=dd, nrm=nr2, sz=sz, col=col, tip=tip):
            e = (1.0, 1.35, 2.0)[lod]
            if lod == 2:
                L.leaflet(g, pos + dd * sz * e * .5, dd, sz * e, sz * e * .5, nrm, col)
            elif kind == 'needle':
                L.needles(g, pos, dd, sz * e, col, tip, nrm, fan=D2R(44), width=.22)
            else:
                L.spray(g, pos, dd, sz * e, col, nrm, quads=3 if lod == 0 else 2)
        item(D, fn, group)


def ellipsoid_samples(rng, n, centre, a_, c_, rho=(.78, .97), cut=None, zmin=None, zmax=None):
    out = []
    for i in range(n):
        zz = -1 + 2 * (i + .5) / n; ph = i * 2.39996 + rng.uniform(-.2, .2); r = math.sqrt(max(0.0, 1 - zz * zz))
        dv = Vector((r * math.cos(ph), r * math.sin(ph), zz))
        k = rng.uniform(*rho)
        base = Vector((dv.x * a_, dv.y * a_, dv.z * c_))
        lump = 1 + .20 * (2 * vnoise(base, 2.4, 3.0) - 1)
        pos = centre + base * (k * lump)
        nrm = Vector((dv.x / a_, dv.y / a_, dv.z / c_)).normalized()
        depth = clamp((k * lump - rho[0]) / (rho[1] - rho[0]))
        if zmin is not None and pos.z < zmin:
            continue
        if zmax is not None and pos.z > zmax:
            continue
        if cut is not None and pos.x < cut + .1:
            pos.x = cut + .1 + rng.uniform(0, .25); nrm = (Vector((-1, 0, 0)) * .8 + nrm * .4).normalized(); depth = max(depth, .7)
        out.append((pos, nrm, depth))
    return out


RADC = {
    'Young': dict(H=7.9, r0=.12, z_live=1.25, whorl=(.55, .70), nb=(4, 5), lean=(.22, .10), sway=.08, size=.30, n=4, wd=.34, e0=(26, 8), droop=14,
                  Lmax=2.0, rb=(.030, .013), dead=3, shade=(.82, 1.12)),
    'Mature': dict(H=21.7, r0=.45, z_live=7.4, whorl=(.95, 1.15), nb=(4, 6), lean=(.9, .15), sway=.14, size=.60, n=3, wd=.36, e0=(40, -4), droop=20,
                   Lmax=4.7, rb=(.085, .040), dead=14, shade=(.78, 1.12), cut=-2.3),
}


def radiata(v, rng, a):
    """Radiata pine: a straight plated red-brown trunk (grey plates as a fine mottle), whorls of 4-6 branches rising
    then levelling, dense needle-spray tufts at the branch ends and along the outer branches, dead lower branches on
    the mature tree, whose crown the wind has pruned flat on its windward (-x) side."""
    c = RADC[v]; D = VD(a['budget']); H = c['H']; r0 = c['r0']; z0 = c['z_live']
    ph = [rng.uniform(0, math.tau) for _ in range(4)]
    rz = lambda z: L.profile([(-.06, r0 * 1.22), (.5, r0 * 1.05), (z0, r0 * .70), (.62 * H, r0 * .38), (H - .4, .035), (H, .02)], z)
    lean = c['lean']
    off = lambda z: (lean[0] * (max(z, 0) / H) ** 1.6 + c['sway'] * math.sin(z * .43 + ph[0]), lean[1] * (max(z, 0) / H) ** 1.6 + c['sway'] * math.sin(z * .37 + ph[1]))
    top = H - .12
    if v == 'Mature':
        za = [-.06, .5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.6]; zb = [7.6] + [7.6 + (top - 7.6) * i / 7 for i in range(1, 8)]
        ca = trunk_ctrl(za, off); cb = trunk_ctrl(zb, off)
        D.tube(ca, prof_from(ca, rz), (22, 8, 3), (12, 8, 6), 'bark', (False, False))
        D.tube(cb, prof_from(cb, rz), (14, 6, 3), (8, 6, 4), 'bark', (False, True))
        trunk = ca[:-1] + cb
    else:
        zs = [-.06, .5] + [.5 + (top - .5) * i / 9 for i in range(1, 10)]
        trunk = trunk_ctrl(zs, off)
        D.tube(trunk, prof_from(trunk, rz), (14, 6, 3), (10, 6, 4), 'bark', (False, True))
    dense = L.curve(trunk, 6)
    D.trunk = dense; D.hull_z = 3.0 if v == 'Young' else 6.0
    D.hull_rfn = lambda t: rz(max(0.0, t * H)) * 1.05
    D.paint['bark'] = (RAD_BARK, [dict(colour=RAD_PLATE, coverage=.30, freq=26.0, noise=.7, inflate=0.0, zstretch=.35, edge_noise=.7, edge_scale=.06, seed=21)], .18)
    D.paint['branch'] = (scale_col(RAD_BARK, .78), [], .16)
    D.paint['dead'] = (RAD_DEAD, [], .16)
    # dead lower branches / stubs
    for i in range(c['dead']):
        zd = (lerp(2.6, 6.8, (i + rng.uniform(.1, .9)) / c['dead']) if v == 'Mature' else rng.uniform(.5, 1.1))
        tp, _ = B.trunk_at(dense, zd)
        az = rng.uniform(0, math.tau); ln = rng.uniform(.5, 2.4) if v == 'Mature' else rng.uniform(.25, .5)
        e0 = D2R(rng.uniform(-14, 10)); out = Vector((math.cos(az), math.sin(az), 0))
        p = tp + out * rz(zd) * .85; pts = [p]
        for k in range(3):
            t = (k + .5) / 3
            e = e0 - D2R(26) * t
            pts.append(pts[-1] + Vector((math.cos(e) * out.x, math.cos(e) * out.y, math.sin(e))) * (ln / 3) + jit(rng, .02))
        rb = .042 if v == 'Mature' else .018
        D.tube(pts, [(0, rb), (1, rb * .3)], (3, 2, 1), (4, 3, 3), 'dead', (False, True), (1, 1, 0))
    # whorls
    z = z0; nbr = 0; cut = c.get('cut')
    while z < H - 1.1:
        nb = rng.randint(*c['nb']); a0 = rng.uniform(0, math.tau)
        u = clamp((z - z0) / (H - 1.1 - z0))
        if v == 'Mature':
            zc = z0 + (H - z0) * .46; Hc = (H - z0) * .56
            Lz = c['Lmax'] * math.sqrt(max(.06, 1 - ((z - zc) / Hc) ** 2))
            e0 = lerp(-4, 8, smoothstep(0, .35, u)) + lerp(0, 34, smoothstep(.55, 1, u))
        else:
            Lz = c['Lmax'] * (1 - u) ** .85 + .30
            e0 = lerp(c['e0'][1], c['e0'][0], u)
        tp, _ = B.trunk_at(dense, z)
        for k in range(nb):
            az = a0 + k * math.tau / nb + rng.uniform(-.3, .3)
            out = Vector((math.cos(az), math.sin(az), 0))
            Lb = Lz * rng.uniform(.78, 1.08) * (1.22 if (v == 'Mature' and out.x > .3) else 1.0)
            e_0 = D2R(e0 + rng.uniform(-6, 6))
            p0 = tp + out * rz(z) * .85 + Z * rng.uniform(-.12, .12)
            pts = [p0]; ca_ = az
            for s_ in range(3):
                t = (s_ + .5) / 3
                e = e_0 - D2R(c['droop']) * smoothstep(0, .9, t)
                ca_ += rng.uniform(-.10, .10)
                q = pts[-1] + Vector((math.cos(e) * math.cos(ca_), math.cos(e) * math.sin(ca_), math.sin(e))) * (Lb / 3)
                if cut is not None and q.x < cut:
                    pp = pts[-1]
                    if pp.x - cut > .3:
                        f = (pp.x - cut) / (pp.x - q.x)
                        pts.append(pp + (q - pp) * f)
                    break
                pts.append(q)
            if len(pts) < 2 or (pts[-1] - pts[0]).length < .5:
                continue
            rb0 = lerp(c['rb'][0], c['rb'][1], u)
            D.tube(pts, [(0, rb0), (1, rb0 * .35)], (3, 1, 1), (4, 3, 3), 'branch', (False, True))
            nbr += 1
            bp = L.curve(pts, 4)
            shade_at = lambda q: lerp(c['shade'][0], c['shade'][1], clamp((q.z - z0) / (H - z0)))
            fr = (.50, .70, .90, 1.0) if v == 'Mature' else (.38, .58, .76, .92, 1.0)
            for f in fr:
                q, T = L.along(bp, f)
                cp = q + Z * c['size'] * .25
                if cut is not None and cp.x < cut + .05:
                    cp.x = cut + .05
                needle_tuft(D, cp, (T + jit(rng, .25)).normalized(), c['size'] * rng.uniform(.9, 1.15), shade_at(q), rng, c['n'], c['wd'])
            nsec = rng.randint(2, 3) if v == 'Mature' else rng.randint(1, 2)
            for j in range(nsec):
                tt = .34 + .24 * j + rng.uniform(-.04, .04)
                q, T = L.along(bp, tt)
                sgn = 1 if (j + k) % 2 == 0 else -1
                sd = (rot(hflat(T, out), Z, sgn * D2R(rng.uniform(42, 74))) + Z * .16).normalized()
                ls = Lb * rng.uniform(.26, .40) * (1 - .4 * tt)
                e = q + sd * ls
                if cut is not None and e.x < cut:
                    f2 = (q.x - cut) / max(1e-6, q.x - e.x)
                    if f2 < .3:
                        continue
                    e = q + (e - q) * min(1.0, f2)
                mid = q.lerp(e, .5) + jit(rng, .03)
                D.tube([q, mid, e], [(0, rb0 * .42), (1, rb0 * .14)], (1, 1, 1), (3, 3, 3), 'branch', (False, True), (1, 0, 0), noise=0)
                for f in ((.62, 1.0) if v == 'Mature' else (1.0,)):
                    cp = q.lerp(e, f) + Z * c['size'] * .2
                    if cut is not None and cp.x < cut + .05:
                        cp.x = cut + .05
                    needle_tuft(D, cp, (sd + Z * .2).normalized(), c['size'] * rng.uniform(.85, 1.1), shade_at(cp), rng, c['n'], c['wd'])
        z += rng.uniform(*c['whorl'])
    # dark crown mass under the tufts
    if v == 'Mature':
        zc = z0 + (H - z0) * .46
        smp = ellipsoid_samples(rng, 1000, Vector((.9 + .3, 0, zc)), 5.6, (H - z0) * .56, (.62, 1.0), cut=cut, zmin=z0 + .4, zmax=H - .5)
        crown_mass(D, rng, smp, (1.0, 1.5), lambda q: lerp(.62, 1.0, clamp((q.z - z0) / (H - z0))))
    else:
        smp = []
        for i in range(260):
            t = (i + .5) / 260; zq = z0 + .5 + t * (H - 1.4 - z0); phi_ = i * 2.39996 + rng.uniform(-.3, .3)
            rr = (c['Lmax'] * (1 - clamp((zq - z0) / (H - 1.1 - z0))) ** .85 + .3) * rng.uniform(.75, .95)
            ox = off(zq)
            pos = Vector((ox[0] + rr * math.cos(phi_), ox[1] + rr * math.sin(phi_), zq))
            smp.append((pos, Vector((math.cos(phi_), math.sin(phi_), .4)).normalized(), rng.uniform(.3, 1.0)))
        crown_mass(D, rng, smp, (.55, .85), lambda q: lerp(.62, 1.0, clamp((q.z - z0) / (H - z0))))
    # leader tufts
    tp = dense[-1]
    for k in range(3):
        az = k * 2.1 + rng.uniform(0, 1)
        needle_tuft(D, tp + Vector((math.cos(az), math.sin(az), 0)) * .06 + Z * (-.08 + .06 * k), (Vector((math.cos(az), math.sin(az), 0)) * .5 + Z).normalized(),
                    c['size'] * 1.15, c['shade'][1], rng, c['n'], c['wd'])
    D.shares = [('mass', .36), ('pad', 1.0)]
    D.note.update(whorl_branches=nbr, pads_designed=len(D.items), windward_cut=bool(cut is not None))
    return D


MACC = dict(r0=.55, fork=2.5, size=.88, H=14.0)


def macrocarpa(v, rng, a):
    """Macrocarpa: a massive short buttressed trunk forking at 2.5 m into five spreading limbs, each forking again into
    two or three branches carrying flat layered secondaries, dense dark scale-spray pads layered into a broad dome."""
    c = MACC; D = VD(a['budget'])
    ph = [rng.uniform(0, math.tau) for _ in range(2)]
    rz = lambda z: L.profile([(-.06, .80), (.35, .64), (1.2, .56), (2.5, .50)], z)
    zs = [-.06, .4, 1.0, 1.7, 2.5]
    ctrl = [Vector((.04 * math.sin(z * 1.3 + ph[0]), .04 * math.sin(z * 1.1 + ph[1]), z)) for z in zs]
    D.tube(ctrl, prof_from(ctrl, rz), (8, 4, 2), (16, 8, 5), 'bark', (False, False))
    dense = L.curve(ctrl, 6); D.trunk = dense; D.hull_z = 2.4; D.hull_rfn = lambda t: rz(2.5 * t) * 1.04
    D.paint['bark'] = (MAC_BARK, [dict(colour=MAC_STRIP, coverage=.28, freq=16.0, noise=.5, inflate=0.0, zstretch=.25, edge_noise=.6, edge_scale=.08, seed=17)], .15)
    D.paint['branch'] = (scale_col(MAC_BARK, .85), [dict(colour=MAC_STRIP, coverage=.18, freq=20.0, noise=.5, inflate=0.0, zstretch=.3, edge_noise=.6, edge_scale=.08, seed=19)], .15)
    fork = ctrl[-1]
    a0 = rng.uniform(0, math.tau); nl = 5
    npads = 0
    shade_at = lambda q: lerp(.66, .98, clamp((q.z - 3.0) / 10.5))
    for i in range(nl):
        az = a0 + i * math.tau / nl + rng.uniform(-.25, .25)
        out = Vector((math.cos(az), math.sin(az), 0))
        th = D2R(rng.uniform(18, 30)); Ll = rng.uniform(6.4, 7.6)
        d = polar(th, az); pts = [fork + out * .22]
        for s_ in range(4):
            d = (d + out * .14 + jit(rng, .05)).normalized()
            pts.append(pts[-1] + d * (Ll / 4))
        D.tube(pts, [(0, .31), (1, .16)], (6, 3, 1), (8, 5, 3), 'bark', (False, True))
        lp = L.curve(pts, 4)
        nb = rng.choice((2, 3))
        for j in range(nb):
            t = .50 + .20 * j + rng.uniform(-.04, .04)
            p, T = L.along(lp, min(t, .93))
            baz = az + (j - (nb - 1) / 2) * D2R(rng.uniform(42, 62)) + rng.uniform(-.15, .15)
            elev = D2R(rng.uniform(36, 56))
            d = (Vector((math.cos(baz), math.sin(baz), 0)) * math.cos(elev) + Z * math.sin(elev))
            Lb = rng.uniform(4.0, 5.3); bpts = [p]
            for s_ in range(4):
                d = (d + Vector((math.cos(baz), math.sin(baz), 0)) * .20 - Z * .03 + jit(rng, .05)).normalized()
                bpts.append(bpts[-1] + d * (Lb / 4))
            D.tube(bpts, [(0, .15), (1, .06)], (4, 2, 1), (6, 4, 3), 'branch', (False, True))
            bp = L.curve(bpts, 4)
            nsec = rng.randint(8, 10)
            for k in range(nsec):
                tt = .16 + .84 * (k + rng.uniform(.1, .9)) / nsec
                q, Tb = L.along(bp, min(tt, .98))
                sgn = 1 if k % 2 == 0 else -1
                sd = (rot(hflat(Tb, Vector((1, 0, 0))), Z, sgn * D2R(rng.uniform(50, 85))) + Tb * .5 + Z * rng.uniform(.1, .45)).normalized()
                ls = rng.uniform(1.2, 2.3) * (1 - .42 * tt)
                e = q + sd * ls; mid = q.lerp(e, .5) + jit(rng, .05) + Z * .06
                D.tube([q, mid, e], [(0, .048), (1, .016)], (1, 1, 1), (3, 3, 3), 'branch', (False, True), (1, 1, 0), noise=0)
                nsp = 6 if tt > .5 else 5
                for f in [.30 + .70 * m / (nsp - 1) for m in range(nsp)]:
                    cp = q.lerp(e, f) + Z * .22
                    flat_pad(D, cp, (sd + jit(rng, .3)).normalized(), c['size'] * rng.uniform(.85, 1.2), shade_at(cp), rng, (Z + jit(rng, .22) + hflat(sd) * .1).normalized())
                    npads += 1
            for f in (.55, .72, .88, 1.0):
                q, Tb = L.along(bp, f)
                cp = q + Z * .25
                flat_pad(D, cp, (Tb + jit(rng, .3)).normalized(), c['size'] * rng.uniform(.95, 1.25), shade_at(cp), rng, (Z + jit(rng, .2)).normalized())
                npads += 1
        for f in (.7, .85, 1.0):
            q, Tb = L.along(lp, f)
            flat_pad(D, q + Z * .3, (Tb + jit(rng, .3)).normalized(), c['size'] * 1.2, shade_at(q), rng, (Z + jit(rng, .2)).normalized())
            npads += 1
    smp = ellipsoid_samples(rng, 800, Vector((0, 0, 8.4)), 7.8, 5.2, (.62, 1.0), zmin=3.9)
    crown_mass(D, rng, smp, (.85, 1.3), lambda q: lerp(.62, .95, clamp((q.z - 3.5) / 10.0)), kind='scale')
    D.shares = [('mass', .34), ('pad', 1.0)]
    D.note.update(limbs=nl, pads_designed=npads)
    return D


# ================================================================ ground litter

_ICO_V = [Vector(p).normalized() for p in [(-1, 1.618, 0), (1, 1.618, 0), (-1, -1.618, 0), (1, -1.618, 0), (0, -1, 1.618), (0, 1, 1.618),
                                           (0, -1, -1.618), (0, 1, -1.618), (1.618, 0, -1), (1.618, 0, 1), (-1.618, 0, -1), (-1.618, 0, 1)]]
_ICO_F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2),
          (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]


def stone_item(D, c0, rx, ry, rzz, yaw, tint, seed):
    """A half-buried stone: 20-triangle icosahedron, LOD1 an octahedron, LOD2 a tetrahedron, its base 6 cm down."""
    r = random.Random(seed)
    jv = [Vector((1 + r.uniform(-.22, .22), 1 + r.uniform(-.22, .22), 1 + r.uniform(-.2, .2))) for _ in range(12)]

    def fn(g, lod):
        if lod == 0:
            vs = [Vector((v.x * j.x * rx, v.y * j.y * ry, v.z * j.z * rzz)) for v, j in zip(_ICO_V, jv)]; fs = _ICO_F
        elif lod == 1:
            vs = [Vector((rx, 0, 0)), Vector((-rx, 0, 0)), Vector((0, ry, 0)), Vector((0, -ry, 0)), Vector((0, 0, rzz * .85)), Vector((0, 0, -rzz * .85))]
            fs = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
        else:
            vs = [Vector((rx, 0, -rzz * .7)), Vector((-rx * .6, ry * .9, -rzz * .7)), Vector((-rx * .6, -ry * .9, -rzz * .7)), Vector((0, 0, rzz * .85))]
            fs = [(0, 1, 3), (1, 2, 3), (2, 0, 3), (0, 2, 1)]
        vs = [Vector((q.x * math.cos(yaw) - q.y * math.sin(yaw), q.x * math.sin(yaw) + q.y * math.cos(yaw), q.z)) + c0 for q in vs]
        dz = ROOT_Z - min(q.z for q in vs)
        vs = [q + Vector((0, 0, dz)) for q in vs]
        cols = [scale_col(STONE, tint * (.78 + .34 * clamp((q.z - ROOT_Z) / (rzz * 1.7)))) for q in vs]
        g.add(vs, [tuple(f) for f in fs], cols, [(q.x, q.y) for q in vs], 1, [(q - c0 - Vector((0, 0, dz))).normalized() for q in vs])
    item(D, fn, 'stone')


def litter_twig(D, rng, p, yaw, ln, r, lift, col, group='twig', bend=.10):
    d = Vector((math.cos(yaw), math.sin(yaw), 0)); sd = Vector((-d.y, d.x, 0))
    bnd = rng.uniform(-bend, bend) * ln
    a_ = p - d * ln * .5; m_ = p + sd * bnd; b_ = p + d * ln * .5 + sd * bnd * .3
    z0 = r * .6 - .012 + lift
    pts = [Vector((q.x, q.y, z0 + rng.uniform(-.004, .006) + (.01 if k == 1 else 0))) for k, q in enumerate((a_, m_, b_))]
    rr = [r * .95, r, r * .55]
    ref = Vector((.0, .0, 1.0))

    def fn(g, lod):
        if lod == 0:
            L.tube(g, pts, rr, 3, col, 1, (False, True), 0.0)
        elif lod == 1:
            L.ribbon(g, pts[0], pts[1], r * 1.4 * ENL[1], r * 1.3 * ENL[1], ref, col, 1); L.ribbon(g, pts[1], pts[2], r * 1.3 * ENL[1], r * .8 * ENL[1], ref, col, 1)
        else:
            L.ribbon(g, pts[0], pts[2], r * 1.6 * ENL[2], r * ENL[2] * .9, ref, col, 1)
    item(D, fn, group)


def litter_scrap(D, rng, p, col, lift=0.0):
    yaw = rng.uniform(0, math.tau); d = Vector((math.cos(yaw), math.sin(yaw), 0))
    ln = rng.uniform(.040, .080); wd = ln * rng.uniform(.45, .65)
    c0 = Vector((p.x, p.y, .004 + rng.uniform(0, .012) + lift))
    nrm = (Z + jit(rng, .3)).normalized()

    def fn(g, lod):
        L.leaflet(g, c0, d, ln * ENL[lod], wd * ENL[lod], nrm, col, 1)
    item(D, fn, 'leaf')


def twig_litter(v, rng, a):
    """A 1.5 x 1.0 m flat patch of 30-50 twigs 10-60 cm (3-sided tubes, 1-3 cm thick, a fifth of them weathered pale),
    20-30 dark leaf scraps and three half-buried stones, lying on the ground and on each other, nothing above 12 cm."""
    D = VD(a['budget'])
    nt = 46 if v == 'A' else 40; ns = 26 if v == 'A' else 29
    base_yaw = rng.uniform(0, math.pi); placed = []
    stones = [(rng.uniform(-.55, .55), rng.uniform(-.34, .34)) for _ in range(3)]
    for (sx, sy) in stones:
        rx = rng.uniform(.034, .052); ry = rng.uniform(.030, .046); rzz = rng.uniform(.044, .056)
        stone_item(D, Vector((sx, sy, -.018)), rx, ry, rzz, rng.uniform(0, math.tau), rng.uniform(.86, 1.14), rng.randrange(1 << 30))
    forks = 2 if v == 'B' else 0
    n_main = nt - forks * 3
    for i in range(n_main):
        u = rng.random()
        ln = .10 + .50 * u ** 1.8
        r = rng.uniform(.0045, .0085) + .006 * u ** 2
        for _ in range(30):
            p = Vector((rng.uniform(-.70, .70), rng.uniform(-.46, .46), 0))
            if (p.x / .72) ** 2 + (p.y / .48) ** 2 < 1.05:
                break
        yaw = base_yaw + rng.gauss(0, .75) if rng.random() < .7 else rng.uniform(0, math.pi)
        lift = .0
        for (q, yq, lq, rq) in placed:
            if (q - p).length < (lq + ln) * .32 and abs(math.sin(yq - yaw)) > .35 and rng.random() < .5:
                lift = max(lift, rq * 1.6)
        pale = rng.random() < .20
        col = scale_col(TWIG_PALE if pale else TWIG, rng.uniform(.86, 1.14))
        litter_twig(D, rng, p, yaw, ln, r, lift, col)
        placed.append((p, yaw, ln, r))
    for fk in range(forks):
        p = Vector((rng.uniform(-.35, .35), rng.uniform(-.25, .25), 0)); yaw = rng.uniform(0, math.pi)
        col = scale_col(TWIG, rng.uniform(.9, 1.1)); d = Vector((math.cos(yaw), math.sin(yaw), 0))
        litter_twig(D, rng, p, yaw, .58, .010, 0, col, bend=.06)
        for j, f in enumerate((-.12, .08, .26)):
            q = p + d * .58 * f
            litter_twig(D, rng, q + Vector((-d.y, d.x, 0)) * (.07 * (1 if j % 2 else -1)), yaw + (1 if j % 2 else -1) * rng.uniform(.5, .9), rng.uniform(.18, .32), .005, .006, col, bend=.1)
    for i in range(ns):
        p = Vector((rng.uniform(-.72, .72), rng.uniform(-.48, .48), 0))
        litter_scrap(D, rng, p, scale_col(SCRAP, rng.uniform(.85, 1.15)), lift=(.01 if rng.random() < .3 else 0.0))
    D.shares = [('stone', .22), ('twig', .80), ('leaf', 1.0)]
    D.note.update(twigs=nt, scraps=ns, stones=3, patch_m='1.5 x 1.0')
    return D


def moss_dapple(coverage=.30, scale=.055, strength=.65, salt=77.0):
    """Fine low-contrast moss mottle over a whole mesh: value noise at `scale` metres, the upward-facing vertices favoured,
    thresholded to `coverage` of the vertices."""
    def post(g, lod):
        f = [vnoise(g.v[i], scale, salt) * .6 + hnoise(g.v[i], salt + 1) * .4 + .22 * clamp(g.r[i].z) for i in range(len(g.v))]
        srt = sorted(f); thr = srt[min(len(srt) - 1, int((1 - coverage) * len(srt)))]
        for i in range(len(g.v)):
            w = smoothstep(thr - .07, thr + .07, f[i]) * strength
            if w > 0:
                g.c[i] = tuple(lerp(a_, b_, w) for a_, b_ in zip(g.c[i], MOSS))
    return post


def root_tangle(v, rng, a):
    """A 1.2 m spread of 7-9 surface roots from a 30 cm centre, radius 2-6 cm, wavering over the ground and diving under
    at the ends; dark bark with a fine low-contrast moss mottle over 30 % of it."""
    D = VD(a['budget'])
    D.paint['bark'] = (ROOT, [], .14)
    nr = 8; a0 = rng.uniform(0, math.tau)
    for i in range(nr):
        az = a0 + i * math.tau / nr + rng.uniform(-.34, .34)
        Lr = rng.uniform(.32, .52); amp = rng.uniform(.06, .12); phs = rng.uniform(0, math.tau); fq = rng.uniform(.8, 1.4)
        out = Vector((math.cos(az), math.sin(az), 0)); sd = Vector((-out.y, out.x, 0))
        rb = rng.uniform(.048, .064)
        pts = []
        for k in range(11):
            t = k / 10
            rr_ = .10 + (.07 + Lr) * t
            w = amp * (math.sin(math.tau * (t * fq) + phs) + .45 * math.sin(math.tau * (t * fq * 2.3) + phs * 1.7)) * t ** .8
            rad_t = rb * (1 - .74 * t ** .7) + .010
            zz = max(rad_t * .55, .011) + .014 * (1 - t) ** 2 + .005 * math.sin(math.tau * t * 1.7 + phs)
            if t > .76:
                zz = lerp(zz, -.09, smoothstep(.76, 1.0, t))
            pts.append(out * rr_ + sd * w + Vector((0, 0, zz)))
        D.tube(pts, [(0, rb), (.30, rb * .60), (1, .012)], (9, 4, 1), (5, 4, 3), 'bark', (True, True), mi=1)
        # every root forks once, a thinner root diverging 30-55 degrees that dives under at its end
        t0 = rng.uniform(.38, .55)
        p0, T = L.along(L.curve(pts, 3), t0)
        fd = rot(hflat(T, out), Z, (1 if i % 2 == 0 else -1) * D2R(rng.uniform(30, 55)))
        fpts = [p0 + Vector((0, 0, .004))]
        fsd = Vector((-fd.y, fd.x, 0)) * rng.uniform(-.05, .05)
        for k in range(1, 5):
            t = k / 4
            fpts.append(p0 + fd * rng.uniform(.22, .30) * t + fsd * t * t + Vector((0, 0, .008 - .03 * t - (.07 if t > .8 else 0))))
        fpts[-1].z = -.08
        D.tube(fpts, [(0, rb * .45), (1, .010)], (3, 2, 1), (4, 3, 3), 'bark', (False, True), (1, 0, 0), mi=1)

    def boss(g, lod):
        ns = (8, 6, 4)[lod]
        rings = [(.23, -.01), (.18, .030), (.11, .052)]
        verts = []; faces = []
        for (r_, z_) in rings:
            for k in range(ns):
                an = math.tau * k / ns + .2
                verts.append(Vector((r_ * math.cos(an), r_ * math.sin(an), z_)))
        top = len(verts); verts.append(Vector((.0, .0, .058)))
        nr_ = len(rings)
        for j in range(nr_ - 1):
            for k in range(ns):
                k2 = (k + 1) % ns
                faces.append((j * ns + k, j * ns + k2, (j + 1) * ns + k2, (j + 1) * ns + k))
        for k in range(ns):
            faces.append(((nr_ - 1) * ns + k, (nr_ - 1) * ns + (k + 1) % ns, top))
        if lod == 2:
            faces = faces[ns:]
        cols = [mot(ROOT, q, .14, 17.0) for q in verts]
        g.add(verts, [tuple(f) for f in faces], cols, [(q.x, q.y) for q in verts], 1, [Vector((q.x, q.y, .3)).normalized() for q in verts])
    D.extra(boss)
    D.post = moss_dapple(.30, .055, .35)
    D.note.update(roots=nr, forks=nr, spread_m=1.2)
    return D


def leaf_litter(v, rng, a):
    """A 1.0 m soft mound .12 m high of overlapping brown leaf quads (15 % darker, moss on one side), the rim leaves tucked
    into the ground."""
    D = VD(a['budget'])
    R = .5; hf = lambda r: .12 * max(0.0, 1 - (r / R) ** 2) ** 1.1
    n = 180

    def base_dome(g, lod):
        ns = (10, 7, 5)[lod]; rings = [(R * .97, -.02), (R * .74, h_at(.74) * .6 + .004), (R * .44, h_at(.44) * .72 + .004), (R * .16, h_at(.16) * .8 + .004)]
        if lod == 2:
            rings = [rings[0], rings[2]]
        verts = []
        for (r_, z_) in rings:
            for k in range(ns):
                an = math.tau * k / ns + .3
                verts.append(Vector((r_ * math.cos(an), r_ * math.sin(an), z_)))
        top = len(verts); verts.append(Vector((0, 0, h_at(0) * .85)))
        faces = []
        for j in range(len(rings) - 1):
            for k in range(ns):
                k2 = (k + 1) % ns
                faces.append((j * ns + k, j * ns + k2, (j + 1) * ns + k2, (j + 1) * ns + k))
        for k in range(ns):
            faces.append(((len(rings) - 1) * ns + k, (len(rings) - 1) * ns + (k + 1) % ns, top))
        cols = [scale_col(LEAFD, .85 * (.9 + .2 * hnoise(q, 5.0))) for q in verts]
        g.add(verts, [tuple(f) for f in faces], cols, [(q.x, q.y) for q in verts], 1, [Vector((q.x, q.y, .5)).normalized() for q in verts])
    h_at = lambda f: hf(R * f)
    D.extra(base_dome)
    for k in range(8):
        an = k * math.tau / 8 + rng.uniform(-.2, .2)
        r = R * rng.uniform(.88, .98)
        d = Vector((math.cos(an), math.sin(an), 0))
        tilt = D2R(rng.uniform(55, 68)); ln = rng.uniform(.085, .105)
        c0 = d * r + Vector((0, 0, -.012))
        dr = (d * math.cos(tilt) - Z * math.sin(tilt)).normalized()
        col = scale_col(LEAFD if k % 3 == 0 else LEAFB, rng.uniform(.9, 1.1))

        sd_ = Z.cross(dr).normalized(); nr_ = dr.cross(sd_).normalized()

        def rfn(g, lod, c0=c0, dr=dr, ln=ln, col=col, nr_=nr_):
            L.leaflet(g, c0 + dr * ln * .5, dr, ln * ENL[lod], ln * .5 * ENL[lod], nr_, col, 1)
        item(D, rfn, 'rim')
    for i in range(n):
        r = R * math.sqrt(rng.random()) * .96
        an = rng.uniform(0, math.tau)
        x = r * math.cos(an); y = r * math.sin(an)
        h = hf(r)
        eps = .01
        sx = (hf(math.hypot(x + eps, y)) - hf(math.hypot(x - eps, y))) / (2 * eps)
        sy = (hf(math.hypot(x, y + eps)) - hf(math.hypot(x, y - eps))) / (2 * eps)
        nrm = (Vector((-sx, -sy, 1)).normalized() + jit(rng, .09)).normalized()
        z = h * rng.uniform(.45, 1.0) + .006
        yaw = rng.uniform(0, math.tau)
        d = rot(L.perp(nrm), nrm, yaw)
        ln = rng.uniform(.095, .135); wd = ln * rng.uniform(.50, .64)
        mossy = rng.random() < clamp(.62 * smoothstep(-.05, .6, x / R + .45 * (vnoise(Vector((x, y, 0)), .12, 9.0) - .5)))
        base = scale_col(MOSS, .78) if mossy else (LEAFD if rng.random() < .15 else LEAFB)
        col = scale_col(base, rng.uniform(.86, 1.14))
        c0 = Vector((x, y, z))
        folded = rng.random() < .40
        roll = rng.uniform(-.5, .5)

        def fn(g, lod, c0=c0, d=d, nrm=nrm, ln=ln, wd=wd, col=col, folded=folded, roll=roll):
            e = ENL[lod]
            if lod == 0 and folded:
                L.leaf(g, c0 - d * ln * .5, d, ln, col, broad=wd / ln, roll=roll)
            else:
                L.leaflet(g, c0, d, ln * e, wd * e, nrm, col, 1)
        item(D, fn, 'leaf')
    D.shares = [('rim', .25), ('leaf', 1.0)]
    D.note.update(leaves=n, rim=8, height_m=.12)
    return D


# ================================================================ build

DESIGNS = {'Gorse': gorse, 'Broom': broom, 'Rush': rush, 'Thistle': thistle, 'VergeTussock': verge_tussock, 'Radiata': radiata, 'Macrocarpa': macrocarpa,
           'TwigLitter': twig_litter, 'RootTangle': root_tangle, 'LeafLitter': leaf_litter}


def build_asset(a, mats, coll):
    seed = seed_of(a)
    rng = random.Random(seed)
    D = DESIGNS[a['family']](a['variant'], rng, a)
    obs = []; rows = []; hull_obs = []; base_kept = None
    for lod in range(3):
        g, kept, wood = emit(D, lod, a['budget'][lod], base_kept)
        if lod == 0:
            base_kept = kept
        name = '%s_LOD%d' % (a['asset'], lod)
        ob, dropped = L.to_object(g, name, mats, a['slots'], coll)
        n = len(ob.data.loop_triangles)
        print('LOD', name, n, 'of', a['budget'][lod], 'wood', wood, 'items', len(kept), 'of', len(D.items), 'size', [round(x, 2) for x in ob.dimensions], 'dropped', dropped)
        assert n <= a['budget'][lod], '%s: %d triangles over the LOD%d ceiling %d' % (name, n, lod, a['budget'][lod])
        ob['kit'] = L.KIT; ob['lod'] = lod; ob['seed'] = seed
        ob['placement'] = 'Ground pivot at the origin; buried parts stop 6 cm below ground.' + (' Convex UCX hulls in the LOD0 FBX.' if a['hulls'] else ' No collision.')
        hs = []
        if lod == 0 and a['hulls']:
            hs = L.hulls(name, D.trunk, D.hull_rfn, a['hulls'], D.hull_z, coll)
            assert len(hs) == a['hulls'], (a['asset'], len(hs))
            hull_obs = hs
        L.export(ob, hs)
        extra = dict(items_designed=len(D.items), items_kept=len(kept), dropped_degenerate_faces=dropped)
        extra.update(D.note)
        rows.append(L.manifest_row(ob, a['asset'], a['family'], a['variant'], lod, a['slots'], seed, g.counts, len(hs), a['budget'][lod], extra))
        obs.append(ob)
    for i in range(2):
        assert rows[i]['triangles'] > rows[i + 1]['triangles'], (a['asset'], [r['triangles'] for r in rows])
    print('BUILT', a['asset'], [r['triangles'] for r in rows], rows[0]['size_m'], 'minz', [r['min_z_m'] for r in rows], 'hulls', len(hull_obs))
    return obs, rows, hull_obs


# ================================================================ review renders

ROW_BIG = ['SM_NZ_Macrocarpa', 'SM_NZ_Radiata_Mature', 'SM_NZ_Radiata_Young', 'SM_NZ_Gorse_B', 'SM_NZ_Gorse_A', 'SM_NZ_Broom_A']
ROW_SMALL = ['SM_NZ_Thistle_A', 'SM_NZ_Rush_B', 'SM_NZ_Rush_A', 'SM_NZ_VergeTussock_B', 'SM_NZ_VergeTussock_A', 'SM_NZ_TwigLitter_A', 'SM_NZ_TwigLitter_B',
             'SM_NZ_RootTangle_A', 'SM_NZ_LeafLitter_A']
LINE_LABELS = {'SM_NZ_Macrocarpa': ('MACROCARPA', ''), 'SM_NZ_Radiata_Mature': ('RADIATA', 'MATURE'), 'SM_NZ_Radiata_Young': ('RADIATA', 'YOUNG'),
               'SM_NZ_Gorse_B': ('GORSE', 'B'), 'SM_NZ_Gorse_A': ('GORSE', 'A'), 'SM_NZ_Broom_A': ('BROOM', ''), 'SM_NZ_Thistle_A': ('THISTLE', ''),
               'SM_NZ_Rush_B': ('RUSH', 'B'), 'SM_NZ_Rush_A': ('RUSH', 'A'), 'SM_NZ_VergeTussock_B': ('TUSSOCK', 'B'), 'SM_NZ_VergeTussock_A': ('TUSSOCK', 'A'),
               'SM_NZ_TwigLitter_A': ('TWIG LITTER', 'A'), 'SM_NZ_TwigLitter_B': ('TWIG LITTER', 'B'), 'SM_NZ_RootTangle_A': ('ROOT TANGLE', ''),
               'SM_NZ_LeafLitter_A': ('LEAF LITTER', '')}

FIGURE_FOR = {'SM_NZ_Macrocarpa', 'SM_NZ_Radiata_Mature', 'SM_NZ_Radiata_Young', 'SM_NZ_Gorse_A', 'SM_NZ_Gorse_B', 'SM_NZ_Broom_A', 'SM_NZ_Thistle_A',
              'SM_NZ_Rush_B', 'SM_NZ_VergeTussock_B'}


def verge_lineup(lod0, labels):
    """All meshes at true scale in two rows (trees and big shrubs behind, the small plants and the litter in front), labels with
    heights, 1.8 m figure posts at each row's ends. Orthographic from the front, 14 degrees down."""
    scene = L.review_scene('Verge Lineup')
    ink = L.flat_material('Review | Ink', (.70, .78, .70), .8); muted = L.flat_material('Review | Secondary', (.44, .53, .47), .8)
    chalk = L.flat_material('Review | Chalk', (.19, .225, .21)); fig = L.flat_material('Review | Figure', (.55, .36, .16))
    L.floor(scene, chalk, 900, location=(30, -12))
    tilt = D2R(14)
    rot_txt = (math.pi / 2 - tilt, 0, 0)
    width = 0.0
    for names, y0, wmin, big in ((ROW_BIG, 0.0, 6.0, True), (ROW_SMALL, -20.0, 3.9, False)):
        x = 0.0
        L.figure(scene, (x, y0, 0), mat=fig); x += 1.9
        for name in [n for n in names if n in lod0]:
            ob = lod0[name]; lo, hi = B.bbox(ob)
            w = max(hi.x - lo.x, hi.y - lo.y, wmin)
            mid = x + w / 2
            L.display_copy(scene, ob, name.replace('SM_NZ_', 'Lineup_'), (mid - (lo.x + hi.x) / 2, y0 - (lo.y + hi.y) / 2, 0))
            a1, a2 = LINE_LABELS[name]
            d = (3.0, 7.0, 9.8) if big else (2.4, 5.2, 7.2)
            sz = (.85, .6, .5) if big else (.5, .4, .34)
            L.text_obj(scene, a1, (mid, y0 - d[0], 0), sz[0], ink, rot_txt)
            if a2:
                L.text_obj(scene, a2, (mid, y0 - d[1], 0), sz[1], ink, rot_txt)
            L.text_obj(scene, '%.2f m' % hi.z, (mid, y0 - d[2], 0), sz[2], muted, rot_txt)
            x += w + 1.4
        L.figure(scene, (x + .1, y0, 0), mat=fig)
        width = max(width, x + 1.2)
    top = 25.0
    L.text_obj(scene, 'GRAND TOUR / NATIVE PLANTS / SOUTHLAND VERGE, SHELTERBELT AND LITTER', (.4, 4.0, top), 1.2, ink, rot_txt, 'LEFT')
    L.text_obj(scene, 'S2b   15 MESHES   TRUE SCALE   MODELLED GEOMETRY   THREE LODS   POSTS 1.8 M   HEIGHTS ABOVE GROUND', (.4, 4.0, top - 1.8), .7, muted, rot_txt, 'LEFT')
    L.studio_lights(scene, Vector((width / 2, -9, 0)), 7.0)
    vtop = top * math.cos(tilt) + 1.5; vbot = -(20 + 7.4) * math.sin(tilt) - .8
    ortho = width + 1.5
    target = Vector((width / 2, ((vtop + vbot) / 2) / math.sin(tilt), 0))
    L.camera(scene, target + Vector((0, -math.cos(tilt), math.sin(tilt))) * 200, target, ortho=ortho)
    return scene, int(2000 * (vtop - vbot) / ortho) + 8


def append_from(blend, names):
    """LOD0 meshes appended (not rebuilt) from another set's .blend."""
    src = OUT / blend
    assert src.exists(), blend + ' is missing (build that set first)'
    with bpy.data.libraries.load(str(src), link=False) as (dfrom, dto):
        dto.objects = [n for n in names if n in dfrom.objects]
    return {o.name.split('_LOD0')[0]: o for o in dto.objects if o is not None}


class Stage:
    """Instance placement for an assembly: records counts and the footprints already used."""

    def __init__(self, scene, have, rng, prefix):
        self.scene = scene; self.have = have; self.rng = rng; self.prefix = prefix; self.counts = {}; self.used = []

    def put(self, name, x, y, yaw=None, sc=1.0, r=0.0, tilt=(0.0, 0.0), z=0.0, record=True):
        if name not in self.have:
            return None
        yaw = self.rng.uniform(0, math.tau) if yaw is None else yaw
        o = L.display_copy(self.scene, self.have[name], name.replace('SM_NZ_', self.prefix) + '_%03d' % self.counts.get(name, 0), (x, y, z), yaw, sc)
        o.rotation_euler = (tilt[0], tilt[1], yaw)
        self.counts[name] = self.counts.get(name, 0) + 1
        if record and r > 0:
            self.used.append((x, y, r))
        return o

    def free(self, x, y, r, overlap=.0):
        return all((x - a) ** 2 + (y - b) ** 2 >= ((r + rr) * (1 - overlap)) ** 2 for a, b, rr in self.used)

    def scatter(self, names, weights, n, region, r, scale=(.9, 1.1), overlap=.0, tries=4000, dens=None, tilt=0.0, avoid=None, keep=True):
        """Dart-throw n instances of the named meshes into region (x0, x1, y0, y1) with footprint radius r (scaled),
        refusing overlaps beyond `overlap`; `dens(x, y)` in 0..1 thins the field, `avoid(x, y)` forbids places."""
        done = 0; t = 0
        while done < n and t < tries:
            t += 1
            x = self.rng.uniform(region[0], region[1]); y = self.rng.uniform(region[2], region[3])
            sc = self.rng.uniform(*scale)
            if avoid and avoid(x, y):
                continue
            if dens and self.rng.random() > dens(x, y):
                continue
            rr = r * sc
            if not self.free(x, y, rr, overlap):
                continue
            pick = self.rng.random() * sum(weights); acc = 0.0; nm = names[-1]
            for w, n_ in zip(weights, names):
                acc += w
                if pick <= acc:
                    nm = n_; break
            tl = D2R(self.rng.uniform(0, tilt)); ta = self.rng.uniform(0, math.tau)
            self.put(nm, x, y, None, sc, rr if keep else 0.0, (tl * math.cos(ta), tl * math.sin(ta)))
            done += 1
        return done


def flat_disc(scene, name, cx, cy, rx, ry, ang, z, mat, n=28):
    ring = [(cx + rx * math.cos(t) * math.cos(ang) - ry * math.sin(t) * math.sin(ang), cy + rx * math.cos(t) * math.sin(ang) + ry * math.sin(t) * math.cos(ang), z)
            for t in [math.tau * i / n for i in range(n)]]
    me = bpy.data.meshes.new(name); me.from_pydata(ring, [], [tuple(range(n))]); me.materials.append(mat)
    for pl in me.polygons:
        pl.use_smooth = True
    ob = bpy.data.objects.new(me.name, me); scene.collection.objects.link(ob)
    return ob


def strip_mesh(scene, name, xs_fn, y0, y1, width, mat, z=.002, step=1.0, wob=.12):
    verts = []; faces = []
    ys = [y0 + i * step for i in range(int((y1 - y0) / step) + 1)]
    for i, y in enumerate(ys):
        c = xs_fn(y)
        verts += [(c - width / 2 + wob * math.sin(y * .31), y, z), (c + width / 2 + wob * .85 * math.sin(y * .27 + 1), y, z)]
        if i:
            a_ = 2 * (i - 1); faces.append((a_, a_ + 1, a_ + 3, a_ + 2))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.materials.append(mat)
    ob = bpy.data.objects.new(me.name, me); scene.collection.objects.link(ob)
    return ob


def grid_axes(coarse, fine, f0, f1, fstep):
    xs = sorted(set([c for c in coarse if c < f0 or c > f1] + [f0 + i * fstep for i in range(int(round((f1 - f0) / fstep)) + 1)]))
    return xs


def beech_wall(st, rng, x0, x1, y0, y1, step, front_y=None):
    """The kit's beech stand to close a wall or horizon: poles with a few matures on a jittered grid."""
    for i in range(int((x1 - x0) / step) + 1):
        for j in range(int((y1 - y0) / step) + 1):
            x = x0 + step * i + rng.uniform(-.6, .6); y = y0 + step * j + rng.uniform(-.6, .6)
            pk = rng.random()
            st.put('SM_NZ_Beech_Pole' if pk < .72 else 'SM_NZ_Beech_Mature', x, y, rng.uniform(0, math.tau), rng.uniform(.9, 1.1), record=False)


def assembly_edge2(lod0):
    """The paddock edge from 20 m out (photos 09, 10), 35 mm at 1.6 m, overcast, exposure 1.8: the kit's Beech_Edge x2, Beech_Pole x6
    and DeadSpar x1 as the front of a dark bush wall (a stand of Beech_Pole and Beech_Mature behind it closes the wall), a 5 m
    band in front of it of Gorse A/B x5, Broom x3, Coprosma A/B x4 (appended from the open set), VergeTussock x30, Thistle x4 and a
    wet dip with Rush x8, on grazed green pasture (.16, .26, .08)."""
    bush = append_from('GrandTour_NativePlants.blend', ['SM_NZ_Beech_Edge_LOD0', 'SM_NZ_Beech_Pole_LOD0', 'SM_NZ_Beech_Mature_LOD0', 'SM_NZ_DeadSpar_LOD0',
                                                        'SM_NZ_CrownFern_B_LOD0', 'SM_NZ_CrownFern_C_LOD0', 'SM_NZ_TreeFern_A_LOD0', 'SM_NZ_TreeFern_B_LOD0', 'SM_NZ_TreeFern_Young_LOD0'])
    opn = append_from('GrandTour_NativePlants_Open.blend', ['SM_NZ_Coprosma_A_LOD0', 'SM_NZ_Coprosma_B_LOD0'])
    have = dict(lod0); have.update(bush); have.update(opn)
    scene = L.review_scene('Edge2 Assembly')
    F.overcast_world(scene, 'NZ Edge2 Overcast', 1.8)
    rng = random.Random(58000 + 9001)
    st = Stage(scene, have, rng, 'Edge2_')
    grass = L.material('Assembly | Grazed grass', (.16, .26, .08))
    grass.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .95
    dip = Vector((3.9, 9.6)); dip_r = 3.0
    xs = grid_axes([-70, -45, -30, -20, -14, 14, 20, 30, 45, 70], None, -14, 14, .5)
    ys = grid_axes([-6, -3, 0, 24, 30, 40, 60, 90, 140], None, 0, 24, .5)

    def zfn(x, y):
        d = math.hypot(x - dip.x, (y - dip.y) * 1.25)
        z = .06 * math.sin(x * .21 + y * .13) + .05 * math.sin(x * .47 - y * .31) - .20 * math.exp(-(d / dip_r) ** 2)
        return z, d, 0

    def cfn(x, y, z, d, u):
        lum = 1 + .13 * (2 * vnoise(Vector((x, y, 0)), 1.6, 3.0) - 1) + .07 * (2 * hnoise(Vector((x, y, 0)), 5.0) - 1)
        c = scale_col((.068, .15, .028), lum)
        band = smoothstep(13.0, 17.0, y) * (1 - smoothstep(20.5, 24, y))
        c = mix(c, scale_col((.10, .14, .04), lum), band * .8)
        wet = math.exp(-(d / (dip_r * 1.0)) ** 2)
        c = mix(c, scale_col((.028, .04, .018), lum), clamp(wet * 1.5))
        return c
    terrain = F.terrain_grid(scene, 'Edge2 pasture', xs, ys, zfn, cfn, grass)
    # bush wall: front of the wall at y 21-24 (the edge trees lean out toward the paddock), the stand behind it
    front = [('SM_NZ_Beech_Edge', -10.0), ('SM_NZ_Beech_Pole', -15.5), ('SM_NZ_Beech_Pole', -6.5), ('SM_NZ_Beech_Pole', -2.5), ('SM_NZ_DeadSpar', 2.0),
             ('SM_NZ_Beech_Pole', 5.5), ('SM_NZ_Beech_Pole', 9.0), ('SM_NZ_Beech_Edge', 13.0), ('SM_NZ_Beech_Pole', 17.0)]
    for nm, x in front:
        yaw = -math.pi / 2 + rng.uniform(-.4, .4) if nm == 'SM_NZ_Beech_Edge' else rng.uniform(0, math.tau)
        st.put(nm, x + rng.uniform(-.6, .6), rng.uniform(22.0, 24.0), yaw, rng.uniform(.94, 1.06), record=False)
    beech_wall(st, rng, -48, 48, 26.0, 110.0, 2.5)
    beech_wall(st, rng, -140, 140, 112.0, 170.0, 4.0)
    # the margin understory the wall stands in: crown ferns massed to the front of the wall, tree ferns scattered along it
    for i in range(int(56 / 1.25) + 1):
        for j in range(int(11 / 1.25) + 1):
            x = -28 + 1.25 * i + rng.uniform(-.4, .4); y = 21.0 + 1.25 * j + rng.uniform(-.4, .4)
            st.put('SM_NZ_CrownFern_B' if rng.random() < .6 else 'SM_NZ_CrownFern_C', x, y, None, rng.uniform(.85, 1.15), record=False)
    for k in range(9):
        st.put(('SM_NZ_TreeFern_A', 'SM_NZ_TreeFern_B', 'SM_NZ_TreeFern_Young')[k % 3], -22 + k * 5.4 + rng.uniform(-1.5, 1.5), rng.uniform(20.5, 27), None, rng.uniform(.9, 1.1), record=False)
    # the 5 m verge band y 15-20: scrub first, then the rank grass between and in front of it
    gor = [('SM_NZ_Gorse_B', -7.2, 19.0), ('SM_NZ_Gorse_A', -3.4, 17.6), ('SM_NZ_Gorse_B', 2.0, 19.4), ('SM_NZ_Gorse_A', 6.3, 17.8), ('SM_NZ_Gorse_A', 11.2, 18.4)]
    for nm, x, y in gor:
        st.put(nm, x, y, None, rng.uniform(.95, 1.08), 1.4)
    for x, y in ((-10.5, 17.8), (4.2, 19.6), (13.8, 19.0)):
        st.put('SM_NZ_Broom_A', x, y, None, rng.uniform(.95, 1.08), 1.0)
    for nm, x, y in (('SM_NZ_Coprosma_B', -5.2, 20.1), ('SM_NZ_Coprosma_A', -.4, 19.2), ('SM_NZ_Coprosma_B', 8.6, 20.0), ('SM_NZ_Coprosma_A', 15.2, 18.6)):
        st.put(nm, x, y, None, rng.uniform(.95, 1.1), 1.2)
    st.scatter(['SM_NZ_Thistle_A'], [1], 4, (-9, 12, 12.5, 17.0), .5, (.95, 1.15), tries=900, avoid=lambda x, y: math.hypot(x - dip.x, y - dip.y) < dip_r + .3)
    st.scatter(['SM_NZ_VergeTussock_A', 'SM_NZ_VergeTussock_B'], [.5, .5], 70, (-16, 17, 13.5, 20.6), .5, (.9, 1.25), tries=9000, overlap=.3,
               avoid=lambda x, y: math.hypot(x - dip.x, y - dip.y) < dip_r + .2)
    st.scatter(['SM_NZ_Rush_A', 'SM_NZ_Rush_B'], [.5, .5], 8, (dip.x - 2.3, dip.x + 2.3, dip.y - 1.8, dip.y + 1.8), .45, (.95, 1.15), tries=4000,
               avoid=lambda x, y: math.hypot(x - dip.x, (y - dip.y) * 1.25) > dip_r * .85)
    # beyond the band: a few rank-grass tufts out in the paddock and along the foot of the wall
    st.scatter(['SM_NZ_VergeTussock_A', 'SM_NZ_VergeTussock_B'], [.6, .4], 10, (-16, 18, 20.2, 22.0), .6, (.9, 1.2), tries=2000)
    puddle = L.flat_material('Assembly | Dip water', (.035, .04, .03), roughness=.05)
    flat_disc(scene, 'Dip water', dip.x, dip.y, 1.9, 1.2, .3, -.17, puddle)
    L.studio_lights(scene, (0, 20, 0), 3.2, energy=.5)
    eye = Vector((0, 0, 1.6))
    L.camera(scene, eye, eye + Vector((0, 10, 10 * math.tan(D2R(9)))), lens=35)
    print('EDGE2 ASSEMBLY', st.counts)
    return scene, st.counts


def assembly_shelterbelt(lod0):
    """A shelterbelt along a gravel track seen from the track at 30 m (35 mm, eye 1.6 m, tilted up 12 degrees, yawed to the row):
    Radiata_Mature x6 and Macrocarpa x2 in a row beside the track with their wind-pruned flat sides toward it, VergeTussock x20 along
    the track edge, a distant stand of the kit's beech for the horizon."""
    bush = append_from('GrandTour_NativePlants.blend', ['SM_NZ_Beech_Pole_LOD0', 'SM_NZ_Beech_Mature_LOD0'])
    have = dict(lod0); have.update(bush)
    scene = L.review_scene('Shelterbelt Assembly')
    F.overcast_world(scene, 'NZ Shelterbelt Overcast', 1.8)
    rng = random.Random(58000 + 9002)
    st = Stage(scene, have, rng, 'Belt_')
    grass = L.material('Assembly | Pasture', (.16, .26, .08))
    grass.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .95
    gravel = L.flat_material('Assembly | Gravel', (.33, .31, .27), roughness=.93)
    xs = grid_axes([-200, -120, -60, -30, 30, 60, 120, 200], None, -30, 30, 1.0)
    ys = grid_axes([-10, 0, 60, 100, 180, 260], None, 0, 60, 1.0)

    tx = lambda y: .55 * math.sin(y / 17.0)

    def zfn(x, y):
        z = .10 * math.sin(x * .09 + y * .05) + .06 * math.sin(x * .31 - y * .17) + .03 * math.sin(y * .7 + x * .5)
        return z * smoothstep(2.4, 5.0, abs(x - tx(y))) - .02 * (1 - smoothstep(2.4, 5.0, abs(x - tx(y)))), 0, 0

    def cfn(x, y, z, tag, u):
        lum = 1 + .14 * (2 * vnoise(Vector((x, y, 0)), 2.2, 4.0) - 1) + .06 * (2 * hnoise(Vector((x, y, 0)), 6.0) - 1)
        return scale_col((.068, .15, .028), lum)
    F.terrain_grid(scene, 'Shelterbelt pasture', xs, ys, zfn, cfn, grass)
    strip_mesh(scene, 'Gravel track', tx, -10, 200, 4.4, gravel, z=.0, step=1.0, wob=.08)
    # darker wheel lines and a grass crown down the middle read as a used farm track
    wheel = L.flat_material('Assembly | Wheel ruts', (.20, .185, .16), roughness=.95)
    for off in (-1.0, 1.0):
        strip_mesh(scene, 'Wheel line', lambda y, o=off: tx(y) + o, -10, 200, .55, wheel, z=.01, step=1.0, wob=.02)
    kinds = ['SM_NZ_Macrocarpa', 'SM_NZ_Radiata_Mature', 'SM_NZ_Radiata_Mature', 'SM_NZ_Radiata_Mature', 'SM_NZ_Macrocarpa', 'SM_NZ_Radiata_Mature', 'SM_NZ_Radiata_Mature', 'SM_NZ_Radiata_Mature']
    for k, nm in enumerate(kinds):
        y = 30.0 + 8.7 * k + rng.uniform(-.8, .8)
        x = (9.6 if nm == 'SM_NZ_Macrocarpa' else 6.9) + rng.uniform(-.5, .5)
        st.put(nm, x, y, rng.uniform(-.12, .12), rng.uniform(.95, 1.06), record=False)
    # rank grass at the track edge, both sides, and a few clumps out in the paddock
    st.scatter(['SM_NZ_VergeTussock_A', 'SM_NZ_VergeTussock_B'], [.5, .5], 20, (-6.0, 6.0, 4, 46), .5, (.95, 1.25), tries=6000,
               avoid=lambda x, y: abs(x - tx(y)) < 2.35, overlap=.2)
    st.scatter(['SM_NZ_Rush_B', 'SM_NZ_Rush_A'], [.5, .5], 6, (-9, -2.6, 14, 60), .5, (.95, 1.2), tries=2000, avoid=lambda x, y: abs(x - tx(y)) < 2.5)
    # horizon: the kit's beech stand in the far distance, and a second, distant belt
    beech_wall(st, rng, -150, 150, 150.0, 190.0, 5.0)
    L.studio_lights(scene, (0, 60, 0), 8.0, energy=.5)
    eye = Vector((0, 0, 1.6))
    tgt = eye + Vector((math.sin(D2R(8)), math.cos(D2R(8)), 0)) * 60 + Vector((0, 0, 60 * math.tan(D2R(12))))
    L.camera(scene, eye, tgt, lens=35)
    print('SHELTERBELT ASSEMBLY', st.counts)
    return scene, st.counts


def assembly_litter(lod0, factor):
    """A 10 x 10 m bush floor from 1.2 m at 4 m (photos 01, 08), 35 mm, overcast, exposure 1.8: dark peat, TwigLitter, RootTangle and
    LeafLitter, the kit's crown ferns (appended), S1's MossHummock x4 and Log_B x1 (appended from the floor .blend), three dark puddle discs
    and a shading stand of the kit's beech behind. `factor` multiplies the instance counts so no bare flat peat shows between them."""
    bush = append_from('GrandTour_NativePlants.blend', ['SM_NZ_CrownFern_A_LOD0', 'SM_NZ_CrownFern_B_LOD0', 'SM_NZ_CrownFern_C_LOD0', 'SM_NZ_Beech_Pole_LOD0',
                                                        'SM_NZ_Beech_Mature_LOD0', 'SM_NZ_TreeFern_Young_LOD0'])
    flo = append_from('GrandTour_NativePlants_Floor.blend', ['SM_NZ_MossHummock_A_LOD0', 'SM_NZ_MossHummock_B_LOD0', 'SM_NZ_Log_B_LOD0'])
    have = dict(lod0); have.update(bush); have.update(flo)
    scene = L.review_scene('Litter Assembly')
    F.overcast_world(scene, 'NZ Litter Overcast', 1.8)
    rng = random.Random(58000 + 9003)
    st = Stage(scene, have, rng, 'Lit_')
    peat = L.material('Assembly | Peat', (.05, .04, .03))
    peat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .93
    xs = [-40 + i * 2 for i in range(5)] + [-22 + i * .3 for i in range(int(44 / .3) + 1)] + [24 + i * 2 for i in range(9)]
    ys = [-14 + i * 2 for i in range(5)] + [-4.5 + i * .3 for i in range(int(25 / .3) + 1)] + [22 + i * 3 for i in range(15)]

    def zfn(x, y):
        z = .012 * math.sin(x * 1.3 + y * .9) + .008 * math.sin(x * 3.1 - y * 2.3) + .006 * (2 * hnoise(Vector((round(x, 1), round(y, 1), 0)), 8.0) - 1)
        return z, 0, 0

    def cfn(x, y, z, tag, u):
        lum = .62 + .95 * vnoise(Vector((x, y, 0)), .45, 6.0) + .55 * (vnoise(Vector((x, y, 0)), 1.7, 7.0) - .5) + .25 * (vnoise(Vector((x, y, 0)), 5.0, 8.0) - .5)
        return scale_col((.05, .04, .03), max(.35, lum))
    F.terrain_grid(scene, 'Litter peat', xs, ys, zfn, cfn, peat)
    # puddles, then the big things, then the litter, then the ferns last
    puddle = L.flat_material('Assembly | Puddle', (.04, .04, .035), roughness=.04)
    pud = [(-1.8, 4.6, 1.5, .8, .3), (2.8, 7.6, 1.9, 1.0, -.4), (-3.6, 10.5, 1.4, .7, .2)]
    for k, (cx, cy, rx, ry, an) in enumerate(pud):
        flat_disc(scene, 'Puddle %d' % k, cx, cy, rx, ry, an, .03, puddle)
        st.used.append((cx, cy, max(rx, ry) * .9))
    region = (-7.5, 7.5, -1.6, 15.0)
    f = factor
    near = (-5.5, 5.5, -1.6, 9.0)
    st.scatter(['SM_NZ_Log_B'], [1], max(1, int(round(.5 * f + .5))), (-5, 5, 3.0, 11.0), 1.6, (.95, 1.05), tries=800, overlap=.15)
    st.scatter(['SM_NZ_MossHummock_A', 'SM_NZ_MossHummock_B'], [.5, .5], int(round(4 * f)), region, .7, (.95, 1.25), tries=6000, overlap=.35)
    st.scatter(['SM_NZ_RootTangle_A'], [1], int(round(3 * f)), region, .65, (.95, 1.25), tries=6000, overlap=.35)
    st.scatter(['SM_NZ_LeafLitter_A'], [1], int(round(5 * f)), region, .5, (.95, 1.3), tries=6000, overlap=.35)
    st.scatter(['SM_NZ_TwigLitter_A', 'SM_NZ_TwigLitter_B'], [.5, .5], int(round(6 * f)), region, .75, (.95, 1.3), tries=8000, overlap=.4)
    # the near field, where the camera is looking down into the litter, gets a second, denser pass of the small things
    st.scatter(['SM_NZ_TwigLitter_A', 'SM_NZ_TwigLitter_B'], [.5, .5], int(round(4.4 * f)), near, .75, (1.0, 1.5), tries=12000, overlap=.62)
    st.scatter(['SM_NZ_LeafLitter_A'], [1], int(round(2.4 * f)), near, .5, (1.0, 1.6), tries=12000, overlap=.55)
    st.scatter(['SM_NZ_RootTangle_A'], [1], int(round(.9 * f)), near, .65, (1.0, 1.4), tries=8000, overlap=.5)
    st.scatter(['SM_NZ_MossHummock_A', 'SM_NZ_MossHummock_B'], [.5, .5], int(round(.8 * f)), near, .7, (1.0, 1.4), tries=8000, overlap=.5)
    nferns = int(round(15 * f))
    dens = lambda x, y: .35 + .65 * smoothstep(1.5, 9.0, y) * (.5 + .5 * vnoise(Vector((x, y, 0)), 3.0, 41.0))
    st.scatter(['SM_NZ_CrownFern_A', 'SM_NZ_CrownFern_B', 'SM_NZ_CrownFern_C'], [.3, .4, .3], nferns, region, .8, (.85, 1.2), tries=20000, overlap=.62, dens=dens, tilt=7)
    st.scatter(['SM_NZ_TreeFern_Young'], [1], 3, (-8, 8, 4.0, 15.0), .8, (.9, 1.1), tries=800, overlap=.2)
    # the shading stand: poles and matures on a jittered 2.5 m grid over the whole floor and behind it, so the canopy closes overhead
    # (open sky at exposure 1.8 turns the peat grey); only the camera's own spot is left clear
    for i in range(-7, 8):
        for j in range(-3, 13):
            x = 2.5 * i + rng.uniform(-.65, .65); y = 2.5 * j + rng.uniform(-.65, .65)
            if math.hypot(x, y + 4.0) < 1.8 or abs(x) > 17:
                continue
            if y < 7.5 and abs(x) < .55 * (y + 4.0) + 1.3:
                continue    # the camera's view cone over the near floor stays free of trunks (the canopy beyond shades it)
            if any((x - cx) ** 2 + (y - cy) ** 2 < (max(rx, ry) + .3) ** 2 for cx, cy, rx, ry, an in pud):
                continue
            st.put('SM_NZ_Beech_Mature' if rng.random() < .30 else 'SM_NZ_Beech_Pole', x, y, None, rng.uniform(.92, 1.08), record=False)
    for i in range(18):
        for j in range(3):
            st.put('SM_NZ_Beech_Mature' if rng.random() < .3 else 'SM_NZ_Beech_Pole', -17 + 2.0 * i + rng.uniform(-.5, .5), 32 + 3.0 * j + rng.uniform(-.7, .7), None, rng.uniform(.92, 1.08), record=False)
    L.studio_lights(scene, (0, 6, 0), 2.8, energy=.5)
    eye = Vector((0, -4.0, 1.2))
    L.camera(scene, eye, Vector((0, 5.0, .55)), lens=35)
    print('LITTER ASSEMBLY factor', factor, st.counts)
    return scene, st.counts


def render_all(lod0, labels, assets, only, no_assembly, t0):
    renders = []
    if only is None and not ASM_ONLY:
        s1, h = verge_lineup(lod0, labels)
        renders.append(L.render(s1, OUT / 'Lineup_Verge.png', 2000, h))
        print('RENDERED Lineup', '%.1fs' % (time.time() - t0))
    s2 = B.detail_scene(); s2.name = 'Verge Detail'
    fig = L.flat_material('Review | Figure', (.55, .36, .16))
    for a in ([] if ASM_ONLY else assets):
        nm = a['asset'].replace('SM_NZ_', '')
        lo, hi = B.bbox(lod0[a['asset']])
        renders.append(F.render_detail(s2, lod0[a['asset']], a['asset'], OUT / ('Detail_%s.png' % nm), fig,
                                       fig_at=((lo.x - .6, (lo.y + hi.y) / 2) if a['asset'] in FIGURE_FOR else None)))
        print('RENDERED Detail', nm, '%.1fs' % (time.time() - t0))
    if only is None and not no_assembly:
        for fname, builder in (('Assembly_Edge2.png', lambda: assembly_edge2(lod0)), ('Assembly_Shelterbelt.png', lambda: assembly_shelterbelt(lod0)),
                               ('Assembly_Litter.png', lambda: assembly_litter(lod0, LITTER_FACTOR))):
            if ASM_SEL and fname.replace('Assembly_', '').replace('.png', '') not in ASM_SEL:
                continue
            sc_, counts = builder()
            renders.append(L.render(sc_, OUT / fname, 2000, 1333))
            ASM_COUNTS[fname] = counts
            print('RENDERED', fname, '%.1fs' % (time.time() - t0))
    return renders


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene; scene.name = 'Native Verge Assets - metres'
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
        L.write_manifest(rows, set_name='verge', extra=dict(verge_stage='S2b', verge_seeds={a['asset']: seed_of(a) for a in assets},
                         verge_lod_rule='one design per asset from seed 58000 + 97 k. Structure (stems, whips, trunks, branches, roots) kept at every LOD (twigs and whips become flat ribbons at LOD1/2, the finest twig levels drop first); foliage and litter elements (sprays, flowers, blades, seed stalks, leaves, litter twigs, stones, pads) are the largest even subset fitting 96 % of each ceiling, enlarged 1.0 / 1.3 / 1.55 and drawn with fewer triangles per element at LOD1/2; hulls UCX convex prisms on the lower trunk in the LOD0 FBX'))
        print('MANIFEST', len(rows), 'rows', '%.1fs' % (time.time() - t0))
    else:
        print('PARTIAL RUN (--only): manifest.json left alone')
    renders = []
    if not NO_RENDER:
        renders += render_all(lod0, labels, assets, ONLY, NO_ASSEMBLY, t0)
    try:
        bpy.context.window.scene = bpy.data.scenes['Native Verge Assets - metres']
    except Exception:
        pass
    if ONLY is None:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'GrandTour_NativePlants_Verge.blend'))
    for b in OUT.glob('*.blend1'):
        b.unlink()
    for p in renders:
        print('RENDER', p)
    print('NATIVE_VERGE_BUILD_OK', len(assets), 'meshes', len(rows), 'lods', '%.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
