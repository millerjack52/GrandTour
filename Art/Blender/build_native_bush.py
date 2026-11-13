"""NP1 Waimeamea bush set (docs/NATIVE_PLANT_KIT_PLAN.md) with the NP1b look corrections:
silver beech (mature, pole, edge), dead spar, crown fern A/B/C and wheki tree fern A/B/Young as
deterministic Blender geometry, three authored LODs each, FBX (cm) + GLB (m), manifest, asset
.blend and review renders.

Run: blender -b --factory-startup --python-exit-code 1 --python build_native_bush.py [-- --only X,Y --no-render]
Each asset is designed once from its fixed seed (all RNG is drawn in the design), then emitted at
LOD0/1/2 from that one design, so the RNG is consumed identically for every LOD.

Beech foliage (NP5): flat domed tiers (3-4 on the mature, 2-3 on the pole, 3 on the edge). A secondary
climbs or sinks to the nearest tier surface and carries 6-10 near-horizontal branchlets; leaf clusters
(1.8 x the NP1c size; the edge 1.67 x) sit about a third of a cluster width apart along the whole
branchlet, the inner third at 40 % of the outer density so the crown has no hollow core. Foliage draws from its own RNG (Design.frng); the
skeleton (trunk, limbs, forks, terminals) draws the exact NP1c stream by burning the legacy plate code
into a scratch design, so those limbs and the silhouette do not move. LOD0 keeps the largest even
cluster subset that fills 96 % of the ceiling; LOD1 keeps every structural branch and secondary (the
2 cm branchlets go), the largest even subset of the LOD0 clusters that fits, enlarged 1.4; LOD2 drops
secondaries and branchlets and draws one folded quad per kept cluster, enlarged 1.8.
"""
import bpy, sys, math, random, json, time
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_plant_lib as L
from native_plant_lib import Z, clamp, lerp, mix, scale_col, smoothstep, polar, rot

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ONLY = set(ARGS[ARGS.index('--only') + 1].split(',')) if '--only' in ARGS else None
NO_RENDER = '--no-render' in ARGS
NO_ASSEMBLY = '--no-assembly' in ARGS
OUT = L.OUT
D2R = math.radians
ENLARGE = (1.0, 1.4, 1.8)
FILL = .96

BARK = (.062, .052, .042)
MOSS = (.10, .14, .055)
LICHEN = (.30, .31, .27)
LICHEN_GREY = (.26, .26, .23)
BLEACHED = (.42, .40, .36)
WEATHERED = (.24, .22, .20)
LEAF_DARK = (.035, .075, .028)
LEAF_LIGHT = (.08, .15, .045)
FERN = (.11, .24, .065)
FERN_NEW = (.20, .34, .09)
FERN_OLD = (.26, .17, .06)
FERTILE = (.10, .12, .05)
WHEKI_TRUNK = (.045, .038, .03)
WHEKI_MOSS = (.11, .14, .06)
WHEKI_FROND = (.07, .17, .05)
WHEKI_RACHIS = (.06, .045, .03)
WHEKI_MIDRIB = (.22, .14, .07)
WHEKI_DEAD = (.16, .10, .05)
MOTTLE = .18

ASSETS = [
    dict(asset='SM_NZ_Beech_Mature', family='Beech', variant='Mature', fam=0, var=0, label='SILVER BEECH / MATURE', slots=[0, 1], budget=(28000, 8000, 2000), hulls=3),
    dict(asset='SM_NZ_Beech_Pole', family='Beech', variant='Pole', fam=0, var=1, label='SILVER BEECH / POLE', slots=[0, 1], budget=(6000, 2000, 600), hulls=1),
    dict(asset='SM_NZ_Beech_Edge', family='Beech', variant='Edge', fam=0, var=2, label='SILVER BEECH / EDGE', slots=[0, 1], budget=(24000, 7000, 2000), hulls=3),
    dict(asset='SM_NZ_DeadSpar', family='DeadSpar', variant='', fam=1, var=0, label='DEAD SPAR', slots=[0, 1], budget=(1500, 600, 200), hulls=2),
    dict(asset='SM_NZ_CrownFern_A', family='CrownFern', variant='A', fam=2, var=0, label='CROWN FERN / A', slots=[1], budget=(2000, 900, 250), hulls=0),
    dict(asset='SM_NZ_CrownFern_B', family='CrownFern', variant='B', fam=2, var=1, label='CROWN FERN / B', slots=[1], budget=(3000, 900, 250), hulls=0),
    dict(asset='SM_NZ_CrownFern_C', family='CrownFern', variant='C', fam=2, var=2, label='CROWN FERN / C', slots=[1], budget=(3000, 900, 250), hulls=0),
    dict(asset='SM_NZ_TreeFern_A', family='TreeFern', variant='A', fam=3, var=0, label='TREE FERN / A', slots=[0, 1], budget=(9000, 3000, 800), hulls=1),
    dict(asset='SM_NZ_TreeFern_B', family='TreeFern', variant='B', fam=3, var=1, label='TREE FERN / B', slots=[0, 1], budget=(9000, 3000, 800), hulls=1),
    dict(asset='SM_NZ_TreeFern_Young', family='TreeFern', variant='Young', fam=3, var=2, label='TREE FERN / YOUNG', slots=[0, 1], budget=(4000, 1200, 400), hulls=0),
]


def seed_of(a):
    return 52710 + a['fam'] * 409 + a['var'] * 97


def jit(rng, s):
    return Vector((rng.uniform(-s, s), rng.uniform(-s, s), rng.uniform(-s, s)))


def hflat(v, fallback=Vector((1, 0, 0))):
    h = Vector((v.x, v.y, 0))
    return h.normalized() if h.length > 1e-4 else fallback.copy()


# ================================================================ design container

class Design:
    def __init__(self):
        self.tubes = []; self.clusters = []; self.fronds = []; self.extras = []; self.paint = {}
        self.trunk = None; self.hull_z = 0.0; self.hull_rfn = None; self.target_h = None
        self.frng = None; self.tiers = None   # NP5: foliage RNG and the tier surfaces (beech only)

    def tube(self, ctrl, rprof, segs, sides, group, caps=(False, True), keep=(1, 1, 1), rfn=None, tint=1.0, mi=0, noise=.04, jag=None):
        t = dict(ctrl=[Vector(c) for c in ctrl], rprof=rprof, segs=segs, sides=sides, group=group, caps=caps, keep=keep, rfn=rfn, tint=tint, mi=mi, noise=noise, jag=jag)
        self.tubes.append(t); return t

    def cluster(self, centre, up, nq, seed, exposure, tint, yaw, size=(.09, .13), scale=1.0):
        self.clusters.append(dict(centre=Vector(centre), up=Vector(up), nq=nq, seed=seed, ex=exposure, tint=tint, yaw=Vector(yaw), size=size, scale=scale))

    def extra(self, fn, keep=(1, 1, 1)):
        """Geometry emitted by fn(geo, lod); fn holds only values drawn at design time."""
        self.extras.append(dict(fn=fn, keep=keep))

    def frond(self, keep=(1, 1, 1), detail=(None, None, None), fold=(True, True, True), kw=None, wscale=(1.0, 1.0, 1.0)):
        self.fronds.append(dict(keep=keep, detail=detail, fold=fold, kw=kw, wscale=wscale))

    def zscale(self, f):
        sz = lambda c: Vector((c.x, c.y, c.z * f if c.z > 0 else c.z))
        for t in self.tubes:
            t['ctrl'] = [sz(c) for c in t['ctrl']]
        for c in self.clusters:
            c['centre'] = sz(c['centre'])
        if self.trunk:
            self.trunk = [sz(p) for p in self.trunk]
        self.hull_z *= f


class Env:
    """Irregular crown envelope: a lobed ellipsoid, taller above its centre (H) than below (Hd),
    optionally narrower on a windward side."""

    def __init__(self, c, R, H, rng, Hd=None, Rw=None, wind=Vector((-1, 0, 0))):
        self.c = Vector(c); self.R = R; self.H = H; self.Hd = Hd or H; self.Rw = Rw; self.wind = wind
        self.ph = [rng.uniform(0, math.tau) for _ in range(4)]

    def radius(self, az):
        R = self.R
        if self.Rw is not None:
            w = max(0.0, math.cos(az) * self.wind.x + math.sin(az) * self.wind.y)
            R = lerp(self.R, self.Rw, w)
        return R * (1 + .13 * math.sin(2 * az + self.ph[0]) + .08 * math.sin(3 * az + self.ph[1]) + .05 * math.sin(5 * az + self.ph[2]))

    def h(self, dz):
        return self.H if dz >= 0 else self.Hd

    def point(self, az, phi, k=1.0):
        R = self.radius(az) * k; cz = math.cos(phi)
        return self.c + Vector((R * math.sin(phi) * math.cos(az), R * math.sin(phi) * math.sin(az), self.h(cz) * k * cz))

    def rho(self, p):
        d = p - self.c; az = math.atan2(d.y, d.x); R = self.radius(az); H = self.h(d.z)
        return math.sqrt((d.x * d.x + d.y * d.y) / (R * R) + d.z * d.z / (H * H))

    def top(self, p):
        return (p.z - self.c.z) / self.H

    def normal(self, p):
        d = p - self.c; az = math.atan2(d.y, d.x); R = self.radius(az); H = self.h(d.z)
        n = Vector((d.x / (R * R), d.y / (R * R), d.z / (H * H)))
        return n.normalized() if n.length > 1e-9 else Z.copy()

    def phi_of(self, p):
        d = p.z - self.c.z
        return math.acos(clamp(d / self.h(d), -1, 1))

    def az_of(self, p):
        d = p - self.c; return math.atan2(d.y, d.x)


def walk(p0, d0, length, n, rng, up_bend=0.0, wobble=.06, kinks=0, kink_deg=(20, 40)):
    pts = [Vector(p0)]; d = Vector(d0).normalized(); step = length / n
    kink_at = set(rng.sample(range(1, n), min(kinks, n - 1))) if kinks else set()
    for i in range(n):
        if i in kink_at:
            axis = L.perp(d); axis = rot(axis, d, rng.uniform(0, math.tau))
            d = rot(d, axis, D2R(rng.uniform(*kink_deg)))
        d = (d + Z * (up_bend / n) + jit(rng, wobble)).normalized()
        pts.append(pts[-1] + d * step)
    return pts, d


def aim(p0, target, rng, lift=.18, wobble=.10):
    p0 = Vector(p0); target = Vector(target); dist = (target - p0).length
    mid = p0.lerp(target, .5) + Z * lift * dist + jit(rng, wobble * dist)
    return [p0, p0.lerp(mid, .55) + jit(rng, wobble * .3 * dist), mid, target]


def trunk_at(dense, z):
    """Point on a (monotonic in z) trunk polyline at height z, and its arc fraction."""
    acc = [0.0]
    for i in range(1, len(dense)):
        acc.append(acc[-1] + (dense[i] - dense[i - 1]).length)
    for i in range(1, len(dense)):
        if dense[i].z >= z:
            f = (z - dense[i - 1].z) / ((dense[i].z - dense[i - 1].z) or 1e-9)
            return dense[i - 1].lerp(dense[i], f), (acc[i - 1] + f * (acc[i] - acc[i - 1])) / acc[-1]
    return dense[-1].copy(), 1.0


# ================================================================ beech

def plate_burn(D, root, heading, rng, env, P, keep_fn=None):
    """NP1c plate, kept verbatim as an RNG spacer (see plates_on): One foliage tier: a near-horizontal secondary carrying 6-10 near-horizontal branchlets
    (slight droop, lift at the tip) with clusters every 20-30 cm along their outer two thirds,
    alternating sides and sitting just above the branchlet."""
    d = hflat(heading)
    d = (d + Z * rng.uniform(-.04, .10)).normalized()
    ln = rng.uniform(*P['sec_len'])
    end = root + d * ln
    mid = root.lerp(end, .5) + Z * rng.uniform(-.03, .05) * ln + jit(rng, .03)
    ctrl = [root, mid, end]
    D.tube(ctrl, [(0, P['sec_r'][0]), (1, P['sec_r'][1])], (2, 1, 1), (4, 3, 3), 'twig', (False, False), (1, 1, 0))
    path = L.curve(ctrl, 4)
    nb = rng.randint(*P['br_n'])
    for j in range(nb):
        t = .12 + .88 * (j + rng.uniform(.15, .85)) / nb
        p, T = L.along(path, t)
        side = 1 if j % 2 == 0 else -1
        bd = rot(hflat(T, d), Z, side * D2R(rng.uniform(25, 80)))
        bl = rng.uniform(*P['br_len'])
        droop = rng.uniform(.05, .10) * bl; lift = rng.uniform(.04, .09) * bl
        e1 = p + bd * bl * .55 - Z * droop + jit(rng, .02 * bl)
        e2 = p + bd * bl + Z * (lift - droop * .5) + jit(rng, .03 * bl)
        bctrl = [p, e1, e2]
        D.tube(bctrl, [(0, .012), (1, .004)], (2, 1, 1), (3, 3, 3), 'twig', (False, False), (1, 1, 0), noise=0)
        bpath = L.curve(bctrl, 4); blen = L.length(bpath)
        # 70 % of the clusters on the outer half, the rest on the inner third-to-half, the
        # largest at the tip
        outer = []; s = blen * .5 + rng.uniform(0, .06)
        while s < blen - .12:
            outer.append(s); s += rng.uniform(.20, .30)
        outer.append(blen)
        inner = [rng.uniform(blen / 3, blen * .5) for _ in range(max(0, round(len(outer) * 3 / 7)))]
        for k, s in enumerate(sorted(inner) + outer):
            tip = s >= blen - 1e-6
            sc = 1.25 if tip else lerp(.85, 1.08, s / blen)
            q, Tb = L.along(bpath, min(1.0, s / blen))
            sd = Vector((-Tb.y, Tb.x, 0))
            sd = sd.normalized() if sd.length > 1e-4 else L.perp(Tb)
            c = q + sd * (1 if k % 2 == 0 else -1) * rng.uniform(.04, .10) + Z * rng.uniform(.02, .06)
            up = (Z + jit(rng, .12) + env.normal(c) * .08).normalized()
            nq = rng.randint(5, 7); seed = rng.randrange(1 << 30)
            ex = clamp(max(clamp((env.rho(c) - .55) / .45), clamp((env.top(c) - .25) / .6)) + rng.uniform(-.15, .15))
            tint = rng.uniform(.9, 1.1)
            keep = rng.random()
            if keep_fn is None or keep < keep_fn(c):
                D.cluster(c, up, nq, seed, ex, tint, bd, P['quad'], sc)


def plates_burn(D, path, fracs, rng, env, P, keep_fn=None, swing=(20, 55)):
    """NP1c plates_on, verbatim: plates along a branch path at the given arc fractions, headed outward from the crown axis
    and swung alternately left and right."""
    for j, f in enumerate(fracs):
        p, T = L.along(path, clamp(f + rng.uniform(-.05, .05), .05, .98))
        out = hflat(p - env.c, hflat(T))
        head = rot(out, Z, (1 if j % 2 == 0 else -1) * D2R(rng.uniform(*swing)))
        plate_burn(D, p, head, rng, env, P, keep_fn)


# NP1c plate parameters. The skeleton draws its RNG stream through plate_burn with these values, so the
# trunk, limbs, forks and terminals come out exactly as they did before NP5.
P_OLD = {
    'Mature': dict(sec_len=(.8, 1.4), sec_r=(.035, .012), br_n=(6, 8), br_len=(1.0, 2.0), quad=(.16, .24)),
    'Pole': dict(sec_len=(.2, .4), sec_r=(.02, .008), br_n=(6, 9), br_len=(.45, .85), quad=(.12, .16)),
    'Edge': dict(sec_len=(.6, 1.1), sec_r=(.03, .01), br_n=(6, 9), br_len=(1.0, 1.8), quad=(.16, .24)),
}


def tier_z(D, p):
    """Height of the tier surface (a shallow dome about the crown axis, edges drooping) nearest p."""
    T = D.tiers
    dx, dy = p.x - T['c'].x, p.y - T['c'].y
    r = math.hypot(dx, dy); az = math.atan2(dy, dx)
    dz = T['dome'] * (1 - min(1.6, (r / T['R']) ** 2)) + T['wob'] * (.6 * math.sin(2 * az + T['ph'][0]) + .4 * math.sin(3 * az + .8 * r + T['ph'][1]))
    return min((lz + dz for lz in T['levels']), key=lambda z: abs(z - p.z))


def plate(D, root, heading, env, P, keep_fn=None):
    """NP5 foliage tier, drawn from D.frng. A secondary (climbing or sinking to the nearest tier surface)
    carries 6-10 near-horizontal branchlets (straight 1-segment twigs); leaf clusters sit every
    P['step'] along the outer two thirds of each branchlet and, at 40 % of that density, along the
    inner third, so the crown has no hollow core. Clusters alternate sides and sit just above the twig."""
    rng = D.frng
    d = hflat(heading)
    d = (d + Z * rng.uniform(-.04, .10)).normalized()
    ln = rng.uniform(*P['sec_len'])
    end = root + d * ln
    mid = root.lerp(end, .5) + Z * rng.uniform(-.03, .05) * ln + jit(rng, .03)
    if D.tiers:
        rise = clamp((tier_z(D, end) - end.z) * rng.uniform(.7, 1.0), -.8 * ln, .8 * ln)
        end.z += rise; mid.z += rise * .8
    ctrl = [root, mid, end]
    D.tube(ctrl, [(0, P['sec_r'][0]), (1, P['sec_r'][1])], (2, 1, 1), (4, 3, 3), 'twig', (False, False), (1, 1, 0))
    path = L.curve(ctrl, 4)
    nb = rng.randint(*P['br_n'])
    k = P['k']; st = P['step']
    for j in range(nb):
        t = .12 + .88 * (j + rng.uniform(.15, .85)) / nb
        p, T = L.along(path, t)
        side = 1 if j % 2 == 0 else -1
        bd = rot(hflat(T, d), Z, side * D2R(rng.uniform(25, 80)))
        bd = (bd + Z * rng.uniform(*P['pitch'])).normalized()   # the sheet is flat-ish, never a plate
        bl = rng.uniform(*P['br_len'])
        droop = rng.uniform(.05, .10) * bl; lift = rng.uniform(.04, .09) * bl
        e1 = p + bd * bl * .55 - Z * droop + jit(rng, .02 * bl)
        e2 = p + bd * bl + Z * (lift - droop * .5) + jit(rng, .03 * bl)
        bctrl = [p, e1, e2]
        D.tube(bctrl, [(0, .012), (1, .004)], (1, 1, 1), (3, 3, 3), 'twig', (False, False), (1, 0, 0), noise=0)
        bpath = L.curve(bctrl, 4); blen = L.length(bpath)
        outer = []; s = blen / 3 + rng.uniform(0, st[0] * .5)
        while s < blen - st[0] * .5:
            outer.append(s); s += rng.uniform(*st)
        outer.append(blen)
        n_in = (blen / 3) / (.5 * (st[0] + st[1])) * .4
        inner = [rng.uniform(blen * .06, blen / 3) for _ in range(int(n_in + rng.random()))]
        for i, s in enumerate(sorted(inner) + outer):
            tip = s >= blen - 1e-6
            sc = 1.25 if tip else lerp(.85, 1.08, s / blen)
            q, Tb = L.along(bpath, min(1.0, s / blen))
            sd = Vector((-Tb.y, Tb.x, 0))
            sd = sd.normalized() if sd.length > 1e-4 else L.perp(Tb)
            c = q + sd * (1 if i % 2 == 0 else -1) * rng.uniform(.04, .10) * k + Z * rng.uniform(.02, .06) * k
            up = (Z + jit(rng, .12) + env.normal(c) * .08).normalized()
            nq = rng.randint(5, 7); seed = rng.randrange(1 << 30)
            ex = clamp(max(clamp((env.rho(c) - .55) / .45), clamp((env.top(c) - .25) / .6)) + rng.uniform(-.15, .15))
            tint = rng.uniform(.85, 1.15)
            keep = rng.random()
            if keep_fn is None or keep < keep_fn(c):
                D.cluster(c, up, nq, seed, ex, tint, bd, P['quad'], sc)


def plates_on(D, path, fracs, rng, env, P, keep_fn=None, swing=(20, 55), inner=()):
    """Plates along a branch path at the given arc fractions (plus `inner`, extra fractions nearer the
    crown axis), headed outward from the crown axis and swung alternately left and right. `rng` is the
    skeleton stream: the NP1c code runs once into a scratch design (plates_burn) so it draws exactly what
    it drew before, and the foliage itself comes from D.frng."""
    plates_burn(Design(), path, fracs, rng, env, P_OLD[P['name']], keep_fn, swing)
    fr = D.frng
    for j, f in enumerate(list(fracs) + list(inner)):
        p, T = L.along(path, clamp(f + fr.uniform(-.05, .05), .05, .98))
        out = hflat(p - env.c, hflat(T))
        head = rot(out, Z, (1 if j % 2 == 0 else -1) * D2R(fr.uniform(*swing)))
        plate(D, p, head, env, P, keep_fn)


def dead_stub(D, dense, rng, z, length, r=.03, group='bleached', theta=(60, 85), trunk_r=None):
    p, f = trunk_at(dense, z)
    d = polar(D2R(rng.uniform(*theta)), rng.uniform(0, math.tau))
    tr = trunk_r(f) if trunk_r else 0
    end = p + d * (tr + length)
    D.tube([p, p.lerp(end, .5) + jit(rng, .02), end], [(0, r * 1.15), (1, r * .8)], (2, 1, 1), (5, 4, 3), group, (False, True))


def height_profile(ctrl, pairs):
    """Radius profile [(arc fraction, r)] from (height, r) pairs on a near-vertical trunk."""
    pts = L.curve(ctrl, 6)
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    out = []
    for z, r in pairs:
        _, f = trunk_at(pts, z)
        out.append((f, r))
    return out


def beech_paint(D, moss_cov, lichen_cov, side, moss_top=7.0, lichen=LICHEN, lichen_side=None):
    D.paint['bark'] = (BARK, [
        dict(colour=MOSS, coverage=moss_cov, band=(-1, moss_top), side=side, side_bias=.9, height_bias=.5, freq=12.0, noise=.35, inflate=0.0, seed=3, edge_noise=.6, edge_scale=.11),
        dict(colour=lichen, coverage=lichen_cov, band=(moss_top - .5, 40), side=lichen_side, side_bias=.6, freq=24.0, noise=.9, inflate=0.0, seed=5)], MOTTLE)
    D.paint['twig'] = (BARK, [], MOTTLE)
    D.paint['bleached'] = (BLEACHED, [dict(colour=WEATHERED, coverage=.2, freq=2.6, noise=.4, seed=9)], MOTTLE)


def beech_mature(rng, frng):
    D = Design(); D.target_h = 22.0; D.frng = frng
    # NP5: clusters 1.8 x the NP1c size (about .9-1.3 m across), four domed tiers through the 16.6 m crown centre
    P = dict(name='Mature', sec_len=(.8, 1.4), sec_r=(.035, .012), br_n=(6, 8), br_len=(1.0, 2.0), quad=(.29, .43), step=(.36, .54), k=1.8, pitch=(-.05, .20))
    ph = [rng.uniform(0, math.tau) for _ in range(6)]
    amp = rng.uniform(.35, .5)

    def off(z):
        zz = min(z, 10.0)
        x = .42 * (math.sin(zz * .52 + ph[0]) - math.sin(ph[0])) + .16 * (math.sin(zz * 1.31 + ph[1]) - math.sin(ph[1]))
        y = .38 * (math.sin(zz * .47 + ph[2]) - math.sin(ph[2])) + .14 * (math.sin(zz * 1.19 + ph[3]) - math.sin(ph[3]))
        return Vector((x, y, 0))
    zs = [-.06, .3, .6] + [1.0 + i for i in range(21)]
    m = max(off(z).length for z in zs) or 1
    ctrl = [off(z) * (amp / m) + Vector((.12 * math.sin(z * .7 + ph[4]), .12 * math.sin(z * .6 + ph[5]), 0)) * smoothstep(10, 14, z) + Vector((0, 0, z)) for z in zs]
    # columnar bole: .32 with a 1.3x flare over the lowest .6 m, .24 at 9 m, .16 at 15 m, .08 at the top
    rprof = height_profile(ctrl, [(-.06, .416), (.6, .32), (9, .24), (15, .16), (21, .08)])
    D.tube(ctrl, rprof, (70, 27, 10), (10, 8, 6), 'bark', (False, True))
    dense = L.curve(ctrl, 6); D.trunk = dense; D.hull_z = 9.0
    D.hull_rfn = lambda t: L.profile(rprof, t) * 1.05
    trunk_r = lambda f: L.profile(rprof, f)
    for z in sorted(rng.uniform(3, 8) for _ in range(rng.randint(2, 3))):
        dead_stub(D, dense, rng, z, rng.uniform(.4, .8), .03, trunk_r=trunk_r)
    top = dense[-1]
    env = Env((top.x, top.y, 16.6), 3.0, 4.4, rng, Hd=4.4)
    D.tiers = dict(c=env.c, R=4.2, dome=.5, wob=.3, ph=[frng.uniform(0, math.tau) for _ in range(2)], levels=[14.5, 16.4, 18.3, 20.1])
    a0 = rng.uniform(0, math.tau)
    n = rng.choice([6, 7])
    zl = [9.0, 9.7, 10.9, 12.0, 13.1, 14.2, 15.3]
    terminals = []
    for i in range(n):
        heavy = i < 2
        z = zl[i] + rng.uniform(-.2, .2)
        az = a0 + i * 2.4 + rng.uniform(-.35, .35)
        th = D2R(rng.uniform(45, 55) if heavy else rng.uniform(25, 40))
        Ll = rng.uniform(6, 7) if heavy else lerp(5.8, 3.6, (i - 2) / max(1, n - 3)) * rng.uniform(.9, 1.1)
        r0 = .16 if heavy else .10
        p0, f = trunk_at(dense, z)
        limb, d1 = walk(p0, polar(th, az), Ll * .45, 3, rng, up_bend=.10, wobble=.05)
        D.tube(limb, [(0, r0), (1, r0 * .7)], (6, 3, 2), (8, 6, 4), 'bark', (False, True))
        for c in (-1, 1):
            axis = rot(L.perp(d1), d1, az + c)
            dc = (rot(d1, axis, c * D2R(rng.uniform(18, 30))) + Z * .10).normalized()
            fork, d2 = walk(limb[-1], dc, Ll * .30 * rng.uniform(.85, 1.1), 3, rng, up_bend=.1, wobble=.05)
            D.tube(fork, [(0, r0 * .62), (1, r0 * .45)], (5, 2, 1), (6, 4, 4), 'bark', (False, True))
            F2 = fork[-1]; phiF = env.phi_of(F2); azF = env.az_of(F2)
            # one terminal to the upper dome, one to the lower flank, so tiers fill the whole crown
            for k, (lo, hi) in enumerate(((8, 50), (55, 100))):
                phi = D2R(rng.uniform(lo, hi))
                tgt = env.point(azF + c * rng.uniform(.15, .55) * (1 if k else -1), phi, rng.uniform(.9, 1.02))
                terminals.append((F2, tgt, i, k, r0))
    escape = {(0, 0), (2, 0)}
    tips = []
    for F2, tgt, i, k, r0 in terminals:
        esc = (i, k) in escape
        if esc:
            tgt = env.point(env.az_of(tgt), D2R(rng.uniform(5, 18)), 1.15)
        path = aim(F2, tgt, rng, lift=.12)
        D.tube(path, [(0, r0 * .4), (1, .015)], (5, 2, 1), (5, 4, 3), 'bark', (False, False))
        plates_on(D, L.curve(path, 3), [.6] if esc else [.55, .95], rng, env, P, inner=() if esc else (.28,))
        tips.append(path)
    # the leader carries tiers up the crown centre
    leader = [p for p in dense if p.z >= 15.5]
    plates_on(D, leader, [.1, .35, .6, .85], rng, env, P, swing=(0, 180), inner=(.22, .48, .72))
    for path in sorted(tips, key=lambda p: -p[-1].z)[:2]:
        p = L.along(L.curve(path, 3), .8)[0]
        ln = rng.uniform(1.0, 1.5)
        D.tube([p, p + (Z + jit(rng, .3)).normalized() * ln * .5, p + (Z + jit(rng, .35)).normalized() * ln], [(0, .025), (1, .006)], (3, 1, 1), (4, 3, 3), 'bleached', (False, False))
    beech_paint(D, rng.uniform(.35, .45), rng.uniform(.10, .15), (math.cos(a0 + 1), math.sin(a0 + 1)))
    return D


def beech_pole(rng, frng):
    D = Design(); D.target_h = 12.0; D.frng = frng
    # NP5: clusters 1.8 x the NP1c size (about .5-.7 m across), three whorl tiers on the leader
    P = dict(name='Pole', sec_len=(.2, .4), sec_r=(.02, .008), br_n=(6, 9), br_len=(.45, .85), quad=(.216, .288), step=(.22, .34), k=1.8, pitch=(-.25, .55))
    azb = rng.uniform(0, math.tau); bend = rng.uniform(.3, .45); ph = rng.uniform(0, math.tau)
    hb = Vector((math.cos(azb), math.sin(azb), 0)); hp = Vector((-hb.y, hb.x, 0))
    zs = [-.06, .3, .6] + [1.0 + i * 1.0 for i in range(11)] + [11.9]
    ctrl = [hb * bend * math.sin(math.pi * max(0, z) / 12) + hp * .05 * math.sin(z * .9 + ph) + Vector((0, 0, z)) for z in zs]
    rprof = height_profile(ctrl, [(-.06, .13), (.6, .10), (7, .06), (10, .04), (11.9, .015)])
    D.tube(ctrl, rprof, (30, 14, 6), (8, 6, 5), 'bark', (False, False))
    dense = L.curve(ctrl, 6); D.trunk = dense; D.hull_z = 7.0
    D.hull_rfn = lambda t: L.profile(rprof, t) * 1.05
    trunk_r = lambda f: L.profile(rprof, f)
    for z in sorted(rng.uniform(2.5, 6.8) for _ in range(2)):
        dead_stub(D, dense, rng, z, rng.uniform(.25, .5), .02, trunk_r=trunk_r)
    cz, _ = trunk_at(dense, 10.0)
    env = Env((cz.x, cz.y, 10.0), .75, 2.0, rng, Hd=2.0)
    D.tiers = dict(c=env.c, R=1.5, dome=.25, wob=.2, ph=[frng.uniform(0, math.tau) for _ in range(2)], levels=[8.9, 10.3, 11.6])
    a0 = rng.uniform(0, math.tau)
    for i in range(3):
        z = 8.0 + i * .7 + rng.uniform(-.2, .2)
        p0, f = trunk_at(dense, z)
        az = a0 + i * 2.2 + rng.uniform(-.3, .3)
        limb, d = walk(p0, polar(D2R(rng.uniform(20, 35)), az), rng.uniform(1.2, 1.8), 3, rng, up_bend=.15, wobble=.06)
        D.tube(limb, [(0, .035), (1, .01)], (4, 2, 1), (5, 4, 3), 'bark', (False, False))
        plates_on(D, L.curve(limb, 3), [.5, .95], rng, env, P, inner=(.22,))
    leader = [p for p in dense if p.z >= 8.0]
    nl = 14
    for j in range(nl):
        # skeleton stream only (the NP1c leader plates); the NP5 whorls below draw from D.frng
        p, T = L.along(leader, clamp((j + rng.uniform(.2, .8)) / nl, .02, .97))
        plate_burn(Design(), p, Vector((math.cos(a0 + j * 2.39996), math.sin(a0 + j * 2.39996), 0)), rng, env, P_OLD['Pole'])
    fr = D.frng
    for k, lz in enumerate(D.tiers['levels']):
        for m in range(6):
            j = k * 6 + m
            p = trunk_at(dense, lz + .1 + fr.uniform(-.32, .32))[0]
            plate(D, p, Vector((math.cos(a0 + j * 2.39996), math.sin(a0 + j * 2.39996), 0)), env, P)
    beech_paint(D, .20, rng.uniform(.10, .15), (math.cos(a0), math.sin(a0)), moss_top=6.5)
    return D


def beech_edge(rng, frng):
    D = Design(); D.target_h = 16.0; D.frng = frng
    # NP5: clusters 1.67 x the NP1c size (about .8-1.2 m across), three domed tiers
    P = dict(name='Edge', sec_len=(.6, 1.1), sec_r=(.03, .01), br_n=(6, 9), br_len=(1.0, 1.8), quad=(.27, .40), step=(.34, .50), k=1.67, pitch=(-.05, .22))
    ph = [rng.uniform(0, math.tau) for _ in range(2)]

    def off(z):
        x = 1.5 * (max(0, z) / 6) ** 1.1 if z <= 6 else 1.5 + .2 * (z - 6)
        return Vector((x + .12 * math.sin(z * .8 + ph[0]), .25 * math.sin(z * .55 + ph[1]) - .25 * math.sin(ph[1]), 0))
    zs = [-.06, .3, .6] + [1.0 + i * 1.0 for i in range(10)] + [10.6]
    ctrl = [off(z) + Vector((0, 0, z)) for z in zs]
    ctrl[0] = Vector((0, 0, -.06)); ctrl[1] = Vector((off(.3).x * .3, 0, .3))
    rprof = height_profile(ctrl, [(-.06, .364), (.6, .28), (5, .22), (10.6, .13)])
    D.tube(ctrl, rprof, (36, 14, 7), (10, 8, 6), 'bark', (False, True))
    dense = L.curve(ctrl, 6); D.trunk = dense; D.hull_z = 7.5
    D.hull_rfn = lambda t: L.profile(rprof, t) * 1.05
    env = Env((2.3, 0, 10.2), 3.0, 4.6, rng, Hd=4.6, Rw=1.6, wind=Vector((-1, 0, 0)))
    D.tiers = dict(c=env.c, R=4.0, dome=.5, wob=.3, ph=[frng.uniform(0, math.tau) for _ in range(2)], levels=[8.3, 10.7, 13.1])
    trunk_x = lambda z: trunk_at(dense, z)[0].x
    keep_fn = lambda q: lerp(.42, 1.0, smoothstep(-1.5, 1.5, q.x - trunk_x(clamp(q.z, 0, 10.5)) - .3))
    n = 8
    for i in range(n):
        z = 3.0 + i * .95 + rng.uniform(-.25, .25)
        windward = i in (1, 4)
        az = math.pi + rng.uniform(-.6, .6) if windward else rng.gauss(0, .85)
        th = D2R(lerp(72, 38, i / (n - 1)) + rng.uniform(-6, 6))
        Ll = rng.uniform(1.6, 2.4) if windward else lerp(4.6, 3.0, i / (n - 1)) * rng.uniform(.85, 1.1)
        p0, f = trunk_at(dense, z)
        limb, d1 = walk(p0, polar(th, az), Ll, 5, rng, up_bend=.18, wobble=.05, kinks=rng.randint(2, 3), kink_deg=(20, 40))
        r0 = .07 if windward else .12
        D.tube(limb, [(0, r0), (1, r0 * .55)], (8, 4, 2), (7, 5, 4), 'bark', (False, True))
        plates_on(D, L.curve(limb, 3), [.75], rng, env, P, keep_fn, inner=(.45,))
        if windward:
            continue
        F = limb[-1]; phiF = env.phi_of(F); azF = env.az_of(F)
        for k, (lo, hi) in enumerate(((-35, -8), (0, 22))):
            phi = clamp(phiF + D2R(rng.uniform(lo, hi)), D2R(5), D2R(125))
            tgt = env.point(azF + rng.uniform(-.5, .5), phi, rng.uniform(.88, 1.0))
            ctrl2, _ = walk(F, (tgt - F).normalized(), max(.8, (tgt - F).length), 3, rng, up_bend=.05, wobble=.06, kinks=1, kink_deg=(20, 35))
            D.tube(ctrl2, [(0, r0 * .5), (1, .012)], (6, 3, 1), (5, 4, 3), 'bark', (False, False))
            plates_on(D, L.curve(ctrl2, 3), [.3, .55, .8, .97], rng, env, P, keep_fn)
    top = dense[-1]
    lead, _ = walk(top, (Z + Vector((.25, 0, 0))).normalized(), 4.2, 4, rng, wobble=.08, kinks=2, kink_deg=(20, 30))
    D.tube(lead, [(0, .12), (1, .02)], (6, 3, 2), (6, 5, 4), 'bark', (False, False))
    plates_on(D, L.curve(lead, 3), [.3, .65, .95], rng, env, P, keep_fn, swing=(0, 180))
    for j in range(rng.randint(2, 3)):
        z = rng.uniform(7.5, 10.4)
        p0, _ = trunk_at(dense, z)
        az = (math.pi if j == 0 else 0) + rng.uniform(-.9, .9)
        dl, _ = walk(p0, polar(D2R(rng.uniform(25, 50)), az), rng.uniform(5.0, 7.0), 4, rng, up_bend=.1, wobble=.05, kinks=rng.randint(1, 2), kink_deg=(20, 35))
        D.tube(dl, [(0, .07), (1, .012)], (5, 3, 1), (5, 4, 3), 'bleached', (False, False))
    # plan: lichen-grey patches 25 % (as NP1b flecks, windward), moss 35-45 % of the lower 7 m
    beech_paint(D, rng.uniform(.35, .45), .25, (.3, 1), lichen=LICHEN_GREY, lichen_side=(-1, 0))
    return D


# ================================================================ dead spar

def dead_spar(rng):
    D = Design()
    ph = [rng.uniform(0, math.tau) for _ in range(4)]
    zs = [-.06, .4] + [1.0 + i * 1.1 for i in range(11)] + [13.25]
    ctrl = [Vector((.18 * (math.sin(z * .45 + ph[0]) - math.sin(ph[0])), .15 * (math.sin(z * .38 + ph[1]) - math.sin(ph[1])), z)) for z in zs]
    rprof = [(0, .30), (.03, .26), (.08, .25), (.6, .19), (1, .13)]
    peaks = [(rng.uniform(0, .5), 14.0 - 13.25), (rng.uniform(2.0, 2.6), rng.uniform(.35, .55)), (rng.uniform(3.9, 4.6), rng.uniform(.15, .3))]
    D.tube(ctrl, rprof, (24, 10, 5), (10, 7, 5), 'bleached', (False, False), jag=peaks)
    dense = L.curve(ctrl, 6); D.trunk = dense; D.hull_z = 8.0
    D.hull_rfn = lambda t: L.profile(rprof, t) * 1.05
    trunk_r = lambda f: L.profile(rprof, f)
    for z in sorted(rng.uniform(5, 12.5) for _ in range(5)):
        p, f = trunk_at(dense, z)
        d = polar(D2R(rng.uniform(45, 80)), rng.uniform(0, math.tau))
        ln = rng.uniform(.5, 2.0)
        end = p + d * (trunk_r(f) + ln)
        D.tube([p, p.lerp(end, .5) + jit(rng, .04), end], [(0, .085), (1, .03 if ln < 1.2 else .022)], (3, 1, 1), (6, 4, 3), 'bleached', (False, True))
    z = rng.uniform(8, 10)
    p, f = trunk_at(dense, z)
    limb, d = walk(p, polar(D2R(rng.uniform(40, 55)), rng.uniform(0, math.tau)), 4.0, 5, rng, up_bend=.1, wobble=.05, kinks=1, kink_deg=(20, 30))
    D.tube(limb, [(0, .11), (1, .02)], (6, 3, 1), (6, 5, 3), 'bleached', (False, True))
    D.paint['bleached'] = (BLEACHED, [dict(colour=WEATHERED, coverage=.2, band=(-1, 20), side=(math.cos(ph[2]), math.sin(ph[2])), side_bias=.5, freq=2.2, noise=.4, seed=9)], MOTTLE)
    return D


# ================================================================ ferns

CROWN = {
    # pairs held by the ceilings (A 2k, B/C 3k): 84 / 92 / 84-triangle fronds
    'A': dict(n=20, L=.56, pairs=17, new=3, fertile=3, fert_pairs=16, old=0, lod1_fold=True),
    'B': dict(n=26, L=.80, pairs=19, new=4, fertile=4, fert_pairs=16, old=3, lod1_fold=True),
    'C': dict(n=30, L=1.0, pairs=17, new=4, fertile=3, fert_pairs=16, old=3, lod1_fold=False),
}


def crown_fern(variant, rng):
    """Dense shuttlecock: the older outer fronds leave the 8 cm crown low (30-45 degrees), the rest
    rise steeply (60-75 degrees) and droop over their outer third, the newest stand erect in the
    centre. Pinnae touch along the rachis so each frond reads as one solid ladder blade."""
    c = CROWN[variant]; D = Design()
    D.tube([(0, 0, -.06), (0, 0, .0), (0, 0, .05)], [(0, .032), (.6, .03), (1, .022)], (2, 2, 1), (5, 4, 4), 'crown', (False, True), mi=1, noise=.08)
    D.paint['crown'] = ((.06, .045, .03), [], 0.0)
    n = c['n']; fold = (True, c['lod1_fold'], True)
    for i in range(n):
        az = i * 2.39996 + rng.uniform(-.25, .25)
        h = Vector((math.cos(az), math.sin(az), 0))
        rank = i / (n - 1)
        tint = rng.uniform(.8, 1.15)
        colour = scale_col(FERN, tint)
        if rank < .3:
            e0 = rng.uniform(30, 45); end = rng.uniform(-35, -22); power = 1.6; ln = c['L'] * rng.uniform(.95, 1.05)
        else:
            u = (rank - .3) / .7
            e0 = clamp(lerp(60, 75, u) + rng.uniform(-3, 3), 60, 75); end = lerp(-22, -6, u) + rng.uniform(-5, 5)
            power = 2.6; ln = c['L'] * lerp(1.22, 1.08, u) * rng.uniform(.92, 1.05)
        if i >= n - c['new']:
            e0 = rng.uniform(76, 84); end = rng.uniform(15, 30); ln *= rng.uniform(.70, .80); colour = scale_col(FERN_NEW, tint)
        pitch = ln * .95 / c['pairs']
        anchor = Vector((0, 0, lerp(.035, .08, rank))) + h * rng.uniform(.02, .045)
        D.frond(fold=fold, kw=dict(anchor=anchor, direction=polar(D2R(90 - e0), az), length=ln, pairs=c['pairs'], pinna_len=.08,
                                   pinna_width=min(.05, pitch * 1.04), droop=D2R(e0 - end), colour=colour, power=power, stipe=.05,
                                   forward=D2R(20), rise=D2R(10), roll=rng.uniform(-.25, .25), curl=rng.uniform(-.05, .05),
                                   rachis_w=(.0035, .0012), floor=.012, taper=(.5, .3125)))
    for i in range(c['old']):
        az = rng.uniform(0, math.tau); e0 = rng.uniform(4, 10); ln = c['L'] * rng.uniform(.72, .85)
        D.frond(fold=fold, kw=dict(anchor=Vector((0, 0, .04)) + Vector((math.cos(az), math.sin(az), 0)) * .03, direction=polar(D2R(90 - e0), az),
                                   length=ln, pairs=12, pinna_len=.07, pinna_width=min(.05, ln * .95 / 12 * .8), droop=D2R(rng.uniform(20, 30)),
                                   colour=scale_col(FERN_OLD, rng.uniform(.8, 1.15)), power=1.5, stipe=.05, forward=D2R(26), rise=D2R(-5),
                                   roll=rng.uniform(-.4, .4), curl=rng.uniform(-.08, .08), rachis_w=(.0035, .0012), floor=.012, taper=(.5, .3125)))
    for i in range(c['fertile']):
        az = rng.uniform(0, math.tau)
        D.frond(keep=(1, 0, 0), kw=dict(anchor=Vector((0, 0, .09)) + Vector((math.cos(az), math.sin(az), 0)) * .01,
                                         direction=polar(D2R(90 - rng.uniform(78, 86)), az), length=c['L'] * .6 * rng.uniform(.9, 1.05),
                                         pairs=c['fert_pairs'], pinna_len=.045, pinna_width=.004, droop=D2R(rng.uniform(5, 15)),
                                         colour=scale_col(FERTILE, rng.uniform(.8, 1.15)), power=2.0, stipe=.08, forward=D2R(30), rise=D2R(25),
                                         roll=rng.uniform(-.2, .2), rachis_w=(.0025, .001)))
    return D


WHEKI = {
    'A': dict(h=3.5, r=.12, lean=0, n=16, L=2.2, skirt=True, segs=(24, 12, 6), sides=(8, 6, 5), pinna=1.0),
    'B': dict(h=5.0, r=.14, lean=15, n=18, L=2.6, skirt=True, segs=(33, 16, 7), sides=(8, 6, 5), pinna=1.0),
    # Young: crown stub only; pinnae scaled with its 1.5 m fronds
    'Young': dict(h=.3, r=.08, lean=0, n=9, L=1.5, skirt=False, segs=(3, 2, 1), sides=(7, 5, 4), pinna=.68),
}


def tree_fern(variant, rng):
    """Wheki: a near-black fibrous trunk, an arching umbrella of overlapping bipinnate fronds (each
    leaves the crown at +20-30 degrees and ends 30-40 degrees below horizontal), three half-length
    erect young fronds, and a dense brown collar of dead midribs and collapsed fronds hugging the
    top 1.2-1.6 m of the trunk."""
    c = WHEKI[variant]; D = Design()
    azl = rng.uniform(0, math.tau); lean = math.tan(D2R(c['lean']))
    hl = Vector((math.cos(azl), math.sin(azl), 0))
    ph = [rng.uniform(0, math.tau) for _ in range(4)]
    h = c['h']
    n_ctrl = max(2, int(h / .5) + 1)
    zs = [-.06] + [h * (i + 1) / n_ctrl for i in range(n_ctrl)]
    ctrl = [hl * lean * max(0, z) * (1 - .15 * z / h) + Vector((.025 * math.sin(z * 1.7 + ph[0]), .025 * math.sin(z * 1.3 + ph[1]), z)) for z in zs]
    r = c['r']

    def band(p, t):
        z = p.z
        b = .65 * math.sin(z * 7.7 + ph[2] + .8 * math.sin(z * 2.3 + ph[3])) + .35 * math.sin(z * 17.3 + ph[0])
        flare = 1 + .35 * (1 - smoothstep(0, .35, z))
        return (1 + .15 * clamp(b, -1, 1)) * flare
    D.tube(ctrl, [(0, r), (1, r * .92)], c['segs'], c['sides'], 'trunk', (False, True), rfn=band, noise=0)
    dense = L.curve(ctrl, 6); D.trunk = dense; D.hull_z = h
    D.hull_rfn = lambda t: r * 1.15 * (1 + .35 * (1 - smoothstep(0, .35, t * h)))
    D.paint['trunk'] = (WHEKI_TRUNK, [dict(colour=WHEKI_MOSS, coverage=.10, band=(-1, h + 1), side=(math.cos(ph[1]), math.sin(ph[1])), side_bias=.8, freq=12.0, noise=.5, inflate=0.0, seed=7, edge_noise=.6, edge_scale=.11)], MOTTLE)
    crown = dense[-1]
    ps = c['pinna']
    LOD1_WIDE = (1.0, 1.3, 1.0)   # NP4: the LOD1 pinnae 1.3x wider so the crown stays solid at 40 m

    def big_frond(i, rng, keep=(1, 1, 1)):
        az = i * 2.39996 + rng.uniform(-.3, .3)
        hdir = Vector((math.cos(az), math.sin(az), 0))
        e0 = rng.uniform(20, 30); end = -rng.uniform(30, 40)
        tint = rng.uniform(.85, 1.15)
        ln = c['L'] * rng.uniform(.92, 1.05)
        stipe = .20 / ln
        pitch = ln * (1 - stipe) / 24
        D.frond(keep=keep, detail=('bipinnate', 'pinnate', 'serrated'), fold=(True, True, False), kw=dict(
            anchor=crown + hdir * r * .7 + Z * .02, direction=polar(D2R(90 - e0), az), length=ln, pairs=24,
            pinna_len=.45 * ps, pinna_width=pitch * 1.08, droop=D2R(e0 - end), colour=scale_col(WHEKI_FROND, tint),
            rachis_colour=scale_col(WHEKI_RACHIS, tint), power=1.3, stipe=stipe, forward=D2R(25), rise=D2R(-15),
            roll=rng.uniform(-.15, .15), curl=rng.uniform(-.03, .03), rachis_w=(.012, .003), pinna_segs=4, pinna_droop=.05,
            taper=(.25 / .45, .15 / .45)), wscale=LOD1_WIDE)

    for i in range(c['n']):
        big_frond(i, rng)
    for i in range(3):
        az = rng.uniform(0, math.tau)
        hdir = Vector((math.cos(az), math.sin(az), 0))
        ln = c['L'] * .5 * rng.uniform(.9, 1.05)
        D.frond(detail=('bipinnate', 'serrated', 'plain'), fold=(True, True, False), kw=dict(
            anchor=crown + hdir * r * .3 + Z * .03, direction=polar(D2R(90 - rng.uniform(68, 80)), az), length=ln, pairs=10,
            pinna_len=.22 * ps, pinna_width=ln * .85 / 10 * 1.05, droop=D2R(rng.uniform(25, 40)),
            colour=scale_col(WHEKI_FROND, rng.uniform(1.0, 1.15)), rachis_colour=WHEKI_RACHIS, power=1.6, stipe=.15,
            forward=D2R(30), rise=D2R(-5), roll=rng.uniform(-.2, .2), rachis_w=(.008, .002), pinna_segs=4, pinna_droop=.03,
            taper=(.4, .3)), wscale=LOD1_WIDE)
    if c['skirt']:
        D.paint['skirt'] = (WHEKI_MIDRIB, [], MOTTLE)
        nk = rng.randint(14, 18)
        for i in range(nk):
            az = math.tau * i / nk + rng.uniform(-.2, .2)
            hd = Vector((math.cos(az), math.sin(az), 0))
            drop = rng.uniform(1.2, 1.6)
            top = Vector((crown.x, crown.y, crown.z - rng.uniform(0, .12)))
            axis_at = lambda dz: trunk_at(dense, max(.05, top.z - dz))[0]
            base = top + hd * r * .85
            elbow = axis_at(.10) + hd * (r + rng.uniform(.05, .10)) + Z * 0
            midp = axis_at(drop * .5) + hd * (r + rng.uniform(.06, .14)) + jit(rng, .02)
            endp = axis_at(drop) + hd * (r + rng.uniform(.08, .20)) + jit(rng, .03)
            D.tube([base, elbow, midp, endp], [(0, .013), (1, .006)], (4, 2, 1), (3, 3, 3), 'skirt', (False, False), tint=rng.uniform(.8, 1.2), noise=0)
        ns = rng.randint(24, 30)
        for i in range(ns):
            az = math.tau * (i + rng.uniform(.15, .85)) / ns
            ln = rng.uniform(.8, 1.6); hw = rng.uniform(.025, .035)
            z0 = crown.z - rng.uniform(.0, .14); ro = r + (.02 if i % 2 else .05)
            curl = rng.uniform(.06, .14); sway = rng.uniform(-.04, .04)
            col = scale_col(WHEKI_DEAD, rng.uniform(.7, 1.2))
            D.extra(collar_strip(dense, az, z0, ro, ln, hw, curl, sway, col))
    if c['skirt']:
        # NP4: two more crown fronds at LOD0 only, continuing the golden-angle sequence into the gaps;
        # LOD1/LOD2 keep the original count so the 3k / 800 ceilings hold
        xr = random.Random(rng.randrange(1 << 30))
        for i in range(c['n'], c['n'] + 2):
            big_frond(i, xr, keep=(1, 0, 0))
    return D


def collar_strip(dense, az, z0, ro, ln, hw, curl, sway, col):
    """One dead frond hanging down the trunk: a narrow strip (5-7 cm) following the trunk, curling
    slightly outward at the bottom, tapering to a point."""
    def fn(g, lod):
        n = (6, 6, 3)[lod]
        hd = Vector((math.cos(az), math.sin(az), 0)); tg = Vector((-hd.y, hd.x, 0))
        cen = []; hl = []; sv = []; uv = []
        for j in range(n + 1):
            t = j / n
            axis = trunk_at(dense, max(.05, z0 - ln * t))[0]
            cen.append(axis + hd * (ro + curl * t * t) + tg * sway * t)
            hl.append(hw * (1 - .35 * t)); sv.append(tg); uv.append(hd)
        L.strip(g, cen, hl, hl, sv, uv, col, 1, 0.0, tip=True)
    return fn


# ================================================================ emission

def jag_top(g, start, n, sides, peaks, centre):
    """Broken spar top: raise ring vertices near three peak angles into jagged points and close
    the stump with a fan to a slightly sunken centre."""
    ring = [start + (n - 1) * sides + j for j in range(sides)]
    for ang, hgt in peaks:
        j = int(round(ang / math.tau * sides)) % sides
        for dj, f in ((0, 1.0), (-1, .35), (1, .3)):
            k = ring[(j + dj) % sides]
            v = g.v[k]; rad = v - centre
            rad.z = 0
            g.v[k] = Vector((centre.x + rad.x * (1 - .45 * f), centre.y + rad.y * (1 - .45 * f), v.z + hgt * f))
    c = len(g.v)
    g.add([centre + Vector((0, 0, .04))], [], (0, 0, 0), [(.5, .5)], 0)
    for j in range(sides):
        g.f.append((ring[j], ring[(j + 1) % sides], c)); g.mi.append(0)
    return [c]


def even_pick(items, k):
    n = len(items)
    if k >= n:
        return list(items)
    return [items[int(i * n / k)] for i in range(k)]


def fit_subset(items, cost, room):
    """Largest even subset of `items` whose summed cost fits `room`."""
    lo, hi = 0, len(items)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if sum(cost(i) for i in even_pick(items, mid)) <= room:
            lo = mid
        else:
            hi = mid - 1
    return even_pick(items, lo)


def emit(D, lod, budget, base_kept=None):
    g = L.Geo()
    groups = {}
    tints = []
    for k, t in enumerate(D.tubes):
        if not t['keep'][lod]:
            continue
        dense = L.curve(t['ctrl'], 6)
        pts, fr = L.resample(dense, t['segs'][lod])
        radii = [L.profile(t['rprof'], f) * (t['rfn'](p, f) if t['rfn'] else 1.0) for p, f in zip(pts, fr)]
        sides = t['sides'][lod]
        start, n = L.tube(g, pts, radii, sides, (0, 0, 0), t['mi'], t['caps'], t['noise'], phase=k * .731)
        idx = list(range(start, start + n * sides))
        if pts[0].z < 0:
            # level the buried base ring so roots sit 6 cm down whatever the trunk's lean
            for i in range(start, start + sides):
                g.v[i].z = pts[0].z
        if t['jag']:
            idx += jag_top(g, start, n, sides, t['jag'], pts[-1])
        groups.setdefault(t['group'], []).extend(idx)
        if t['tint'] != 1.0:
            tints.append((idx, t['tint']))
    for grp, idx in groups.items():
        base, patches, mottle = D.paint[grp]
        L.bark_paint(g, idx, base, patches, mottle=mottle)
    for idx, tn in tints:
        for i in idx:
            g.c[i] = scale_col(g.c[i], tn)
    for f in D.fronds:
        if not f['keep'][lod]:
            continue
        kw = dict(f['kw'])
        kw['width_scale'] = kw.get('width_scale', 1.0) * f['wscale'][lod]
        L.frond(g, lod=lod, detail=f['detail'][lod], fold_strip=f['fold'][lod], **kw)
    for e in D.extras:
        if e['keep'][lod]:
            e['fn'](g, lod)
    wood = sum(len(f) - 2 for f in g.f)
    kept = []
    if D.clusters:
        pool = list(range(len(D.clusters))) if base_kept is None else base_kept
        cost = (lambda i: 2 * D.clusters[i]['nq']) if lod < 2 else (lambda i: 2)
        kept = fit_subset(pool, cost, FILL * budget - wood)
        for i in kept:
            c = D.clusters[i]
            qs = (c['size'][0] + c['size'][1]) * .5
            if lod < 2:
                L.cluster(g, c['centre'], c['up'], c['nq'], c['seed'], LEAF_DARK, LEAF_LIGHT, c['ex'], c['tint'], ENLARGE[lod] * c['scale'],
                          size=c['size'], spread=qs * .5, dome=qs * .35)
            else:
                size = qs * 2.4 * c['scale'] * ENLARGE[lod]
                col = scale_col(mix(LEAF_DARK, LEAF_LIGHT, clamp(.55 * c['ex'] + .2)), c['tint'])
                L.spray(g, c['centre'] - c['yaw'] * size * .5, c['yaw'], size, col, c['up'], quads=1)
                g.counts['sprays'] -= 1; g.counts['clusters'] += 1
    return g, kept


# ================================================================ build

def design_for(a, rng):
    if a['family'] == 'Beech':
        return {'Mature': beech_mature, 'Pole': beech_pole, 'Edge': beech_edge}[a['variant']](rng, random.Random(seed_of(a) * 31 + 5))
    if a['family'] == 'DeadSpar':
        return dead_spar(rng)
    if a['family'] == 'CrownFern':
        return crown_fern(a['variant'], rng)
    return tree_fern(a['variant'], rng)


def build_asset(a, mats, coll):
    seed = seed_of(a)
    rng = random.Random(seed)
    D = design_for(a, rng)
    if D.target_h:
        g0, _ = emit(D, 0, a['budget'][0])
        top = max(v.z for v in g0.v)
        D.zscale(D.target_h / top)
    obs = []; rows = []; hull_obs = []; base_kept = None
    for lod in range(3):
        g, kept = emit(D, lod, a['budget'][lod], base_kept)
        if lod == 0:
            base_kept = kept
        name = '%s_LOD%d' % (a['asset'], lod)
        ob, dropped = L.to_object(g, name, mats, a['slots'], coll)
        tris = len(ob.data.loop_triangles)
        print('LOD', name, tris, 'clusters', len(kept), 'of', len(D.clusters), 'tubes', g.counts['tubes'], 'fronds', g.counts['fronds'], 'size', [round(x, 2) for x in ob.dimensions])
        assert tris <= a['budget'][lod], '%s: %d triangles over the LOD%d ceiling %d' % (name, tris, lod, a['budget'][lod])
        ob['kit'] = L.KIT; ob['lod'] = lod; ob['seed'] = seed
        ob['placement'] = 'Ground pivot at the origin; roots 6 cm below ground.' + (' Trunk collision UCX hulls in the LOD0 FBX; canopy never blocks.' if a['hulls'] else ' No collision.')
        hs = []
        if lod == 0 and a['hulls']:
            hs = L.hulls(name, D.trunk, D.hull_rfn, a['hulls'], D.hull_z, coll)
            hull_obs = hs
        L.export(ob, hs)
        rows.append(L.manifest_row(ob, a['asset'], a['family'], a['variant'], lod, a['slots'], seed, g.counts, len(hs), a['budget'][lod],
                                   dict(clusters_designed=len(D.clusters) or None, dropped_degenerate_faces=dropped)))
        if dropped:
            print('NOTE', name, 'dropped', dropped, 'degenerate faces')
        obs.append(ob)
    for i in range(2):
        assert rows[i]['triangles'] > rows[i + 1]['triangles'], (a['asset'], [r['triangles'] for r in rows])
    print('BUILT', a['asset'], [r['triangles'] for r in rows], rows[0]['size_m'], 'clusters', [r['clusters'] for r in rows], 'hulls', len(hull_obs))
    return obs, rows, hull_obs


# ================================================================ review

LINEUP_ORDER = ['SM_NZ_Beech_Mature', 'SM_NZ_Beech_Edge', 'SM_NZ_Beech_Pole', 'SM_NZ_DeadSpar', 'SM_NZ_TreeFern_B', 'SM_NZ_TreeFern_A',
                'SM_NZ_TreeFern_Young', 'SM_NZ_CrownFern_C', 'SM_NZ_CrownFern_B', 'SM_NZ_CrownFern_A']


def bbox(ob):
    vs = [v.co for v in ob.data.vertices]
    return Vector([min(v[i] for v in vs) for i in range(3)]), Vector([max(v[i] for v in vs) for i in range(3)])


def lineup(lod0, labels, order=None, title='GRAND TOUR / NATIVE PLANTS / WAIMEAMEA BUSH',
           subtitle='NP1   10 MESHES   TRUE SCALE   MODELLED FOLIAGE   THREE LODS   POSTS 1.8 M', name='Bush Lineup', top=25.7):
    scene = L.review_scene(name)
    ink = L.flat_material('Review | Ink', (.70, .78, .70), .8); muted = L.flat_material('Review | Secondary', (.44, .53, .47), .8)
    chalk = L.flat_material('Review | Chalk', (.19, .225, .21)); fig = L.flat_material('Review | Figure', (.55, .36, .16))
    L.floor(scene, chalk, 600)
    tilt = D2R(14)
    rot_txt = (math.pi / 2 - tilt, 0, 0)
    x = 0.0
    order = [n for n in (order or LINEUP_ORDER) if n in lod0]
    L.figure(scene, (x, 0, 0), mat=fig); x += 2.0
    for name in order:
        ob = lod0[name]; lo, hi = bbox(ob)
        w = max(hi.x - lo.x, 4.6)
        mid = x + w / 2
        L.display_copy(scene, ob, name.replace('SM_NZ_', 'Lineup_'), (mid - (lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, 0))
        fam, var = labels[name]
        L.text_obj(scene, fam, (mid, -6.5, 0), .62, ink, rot_txt)
        L.text_obj(scene, (var + '   ' if var else '') + '%.1f m' % hi.z, (mid, -10.5, 0), .5, muted, rot_txt)
        x += w + 1.2
    L.figure(scene, (x + .4, 0, 0), mat=fig)
    x += 1.2
    width = x
    L.text_obj(scene, title, (.5, 9.0, top), 1.25, ink, rot_txt, 'LEFT')
    L.text_obj(scene, subtitle, (.5, 9.0, top - 1.6), .7, muted, rot_txt, 'LEFT')
    L.studio_lights(scene, Vector((width / 2, 0, 0)), 3.2)
    target = Vector((width / 2, 0, 11.5 * (top / 25.7)))
    L.camera(scene, target + Vector((0, -math.cos(tilt), math.sin(tilt))) * 120, target, ortho=width + 3)
    return scene


def detail_scene():
    scene = L.review_scene('Bush Detail')
    chalk = L.flat_material('Review | Chalk', (.19, .225, .21))
    L.floor(scene, chalk, 600)
    return scene


def render_detail(scene, ob, name, path, fig_mat, inset=None, fig_at=None):
    for o in list(scene.collection.objects):
        if o.get('detail_item') or o.type in {'CAMERA', 'LIGHT'}:
            bpy.data.objects.remove(o, do_unlink=True)
    c = L.display_copy(scene, ob, 'Detail_' + name.replace('SM_NZ_', '')); c['detail_item'] = True
    lo, hi = bbox(ob)
    small = hi.z < 1.5
    inset = small if inset is None else inset
    plant_lo, plant_hi = lo.copy(), hi.copy()
    if not small or fig_at is not None:
        fx, fy = fig_at if fig_at is not None else (-1.3, -.4)
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
    loc = centre + back * d * (.84 if small else 1.04)
    L.camera(scene, loc, centre, lens=50)
    L.studio_lights(scene, Vector((centre.x, centre.y, 0)), max(.35, rad / 6))
    L.render(scene, path, 1400, 1200)
    if inset:
        # crown ferns: top-down inset (ortho, straight down, 1.2 x the plant width) beside the view
        span = max(plant_hi.x - plant_lo.x, plant_hi.y - plant_lo.y) * 1.2
        mid = (plant_lo + plant_hi) / 2
        cam = L.camera(scene, (mid.x, mid.y, plant_hi.z + 4), (mid.x, mid.y, 0), ortho=span, name='Detail Top Camera')
        cam.rotation_euler = (0, 0, 0)
        tmp = OUT / ('_top_%s.png' % name)
        L.render(scene, tmp, 600, 600)
        L.compose_inset(path, tmp, path)
        tmp.unlink()
        cam.data.type = 'PERSP'
    return path


def assembly(lod0):
    """Closed stand at photo density: 40 x 40 m, trunks on a jittered 2.4 m grid, crown ferns at
    one per .6 m2 off a 1.6 m meandering peat track, bright overcast sky, 28 mm at eye height."""
    scene = L.review_scene('Bush Assembly')
    w = bpy.data.worlds.new('NZ Assembly Overcast'); w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (.75, .80, .85, 1); bg.inputs[1].default_value = 1.0
    scene.world = w
    rng = random.Random(52710 + 999)
    peat = L.flat_material('Assembly | Peat', (.040, .031, .022), roughness=.92)
    track = L.flat_material('Assembly | Wet peat track', (.018, .014, .010), roughness=.62)
    L.floor(scene, peat, 400, z=-.004, location=(0, 20))
    xt = lambda y: 2.8 * (math.sin(y / 8.5 + .7) - math.sin(.7)) + .5 * (math.sin(y / 3.1 + 2.1) - math.sin(2.1))
    verts = []; faces = []
    ys = [-3 + i * .5 for i in range(93)]
    for i, y in enumerate(ys):
        c = xt(y); verts += [(c - .8 + .08 * math.sin(y * 1.7), y, 0), (c + .8 + .07 * math.sin(y * 1.3 + 1), y, 0)]
        if i:
            a = 2 * (i - 1); faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new('Peat track 1.6 m'); me.from_pydata(verts, [], faces); me.materials.append(track)
    scene.collection.objects.link(bpy.data.objects.new(me.name, me))
    have = lambda n: n in lod0
    counts = {}

    def put(name, x, y, yaw, sc, tilt=(0, 0)):
        if not have(name):
            return
        o = L.display_copy(scene, lod0[name], name.replace('SM_NZ_', 'Bush_') + '_%04d' % counts.get(name, 0), (x, y, 0), yaw, sc)
        o.rotation_euler = (tilt[0], tilt[1], yaw)
        counts[name] = counts.get(name, 0) + 1
    trunks = []
    cell = 2.4; nc = int(40 / cell)
    for i in range(nc + 1):
        for j in range(nc + 1):
            x = -20 + cell * (i + .5) + rng.uniform(-.45, .45); y = cell * (j + .5) + rng.uniform(-.45, .45)
            r = rng.random(); yaw = rng.uniform(0, math.tau); sc = rng.uniform(.9, 1.1)
            if abs(x) > 20 or y > 40 or abs(x - xt(y)) < 1.25:
                continue
            name = 'SM_NZ_Beech_Pole' if r < .70 else 'SM_NZ_Beech_Mature' if r < .90 else 'SM_NZ_Beech_Edge' if r < .97 else 'SM_NZ_DeadSpar'
            put(name, x, y, yaw, sc); trunks.append((x, y))
    ferns = ['SM_NZ_TreeFern_A', 'SM_NZ_TreeFern_B', 'SM_NZ_TreeFern_Young']
    tf = 0; tries = 0
    while tf < 12 and tries < 5000:
        tries += 1
        if tf < 3:
            y = rng.uniform(7, 10); x = xt(y) + rng.choice((-1, 1)) * rng.uniform(1.3, 2.4)
        else:
            x = rng.uniform(-19, 19); y = rng.uniform(1, 39)
        if abs(x - xt(y)) < 1.25 or any((x - a) ** 2 + (y - b) ** 2 < 1.0 for a, b in trunks):
            continue
        put(ferns[tf % 3], x, y, rng.uniform(0, math.tau), rng.uniform(.9, 1.1)); trunks.append((x, y)); tf += 1
    crowns = ['SM_NZ_CrownFern_A', 'SM_NZ_CrownFern_B', 'SM_NZ_CrownFern_C']
    fc = 0; step = math.sqrt(.6); m = int(40 / step)
    for i in range(m):
        for j in range(m):
            x = -20 + step * (i + .5) + rng.uniform(-.35, .35) * step; y = step * (j + .5) + rng.uniform(-.35, .35) * step
            pick = rng.random(); yaw = rng.uniform(0, math.tau); sc = rng.uniform(.8, 1.2)
            tl = D2R(rng.uniform(0, 10)); ta = rng.uniform(0, math.tau)
            if abs(x - xt(y)) < .85 or any((x - a) ** 2 + (y - b) ** 2 < .35 ** 2 for a, b in trunks):
                continue
            name = crowns[0 if pick < .30 else 1 if pick < .75 else 2]
            put(name, x, y, yaw, sc, (tl * math.cos(ta), tl * math.sin(ta))); fc += 1
    # a sparser ring of poles and matures out to ~70 m closes the horizon at eye level
    ring = 0; rs = 3.0
    for i in range(int(110 / rs) + 1):
        for j in range(int(106 / rs) + 1):
            x = -55 + rs * i + rng.uniform(-.6, .6); y = -6 + rs * j + rng.uniform(-.6, .6)
            pick = rng.random(); yaw = rng.uniform(0, math.tau); sc = rng.uniform(.9, 1.1)
            if -20.5 < x < 20.5 and -.5 < y < 40.5:
                continue
            put('SM_NZ_Beech_Pole' if pick < .75 else 'SM_NZ_Beech_Mature', x, y, yaw, sc); ring += 1
    L.studio_lights(scene, (0, 20, 0), 2.6, energy=.5)
    y0 = 1.0; y1 = 9.0
    eye = Vector((xt(y0), y0, 1.6)); ahead = hflat(Vector((xt(y1) - xt(y0), y1 - y0, 0)))
    L.camera(scene, eye, eye + ahead * 10 + Z * 10 * math.tan(D2R(8)), lens=28)
    scene.view_settings.exposure = 1.8
    print('ASSEMBLY', 'trees', len(trunks) - tf, 'tree ferns', tf, 'crown ferns', fc, 'ring trees', ring, counts)
    return scene


# ================================================================ main

def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene; scene.name = 'Native Bush Assets - metres'
    mats = L.plant_materials()
    coll = scene.collection
    lod0 = {}; labels = {}; rows = []
    assets = [a for a in ASSETS if ONLY is None or a['asset'].replace('SM_NZ_', '') in ONLY]
    x = 0.0
    for a in assets:
        obs, r, hs = build_asset(a, mats, coll)
        rows += r
        lo, hi = bbox(obs[0])
        x += -lo.x + .5
        obs[0].location = (x, 0, 0)
        for h in hs:
            h.parent = obs[0]
        x += hi.x + 1.5
        for o in obs[1:]:
            o.hide_set(True); o.hide_render = True
        L.mark_asset(obs[0], a['label'] + ' / opaque vertex-colour geometry / 3 LODs', ['Native', 'NZ', a['family'], 'Grand Tour'])
        lod0[a['asset']] = obs[0]
        fam = {'Beech': 'SILVER BEECH', 'DeadSpar': 'DEAD SPAR', 'CrownFern': 'CROWN FERN', 'TreeFern': 'TREE FERN'}[a['family']]
        labels[a['asset']] = (fam, a['variant'].upper())
    L.write_manifest(rows, set_name='bush', extra=dict(stage='NP5', seeds={a['asset']: seed_of(a) for a in assets},
                                      lod_rule='one design per asset. Beech (NP5): LOD0 keeps the largest even cluster subset filling 96 % of the ceiling; LOD1 keeps every structural branch and secondary (the 2 cm branchlets go) and the largest even subset of the LOD0 clusters that fits, enlarged 1.4; LOD2 drops secondaries and branchlets, one folded quad per kept cluster enlarged 1.8. Ferns keep every frond: crown fern pinnate -> serrated strip -> plain strip; tree fern bipinnate -> pinnate -> flat serrated strip'))
    print('MANIFEST', len(rows), 'rows', '%.1fs' % (time.time() - t0))
    blend = OUT / 'GrandTour_NativePlants.blend'
    renders = []
    if not NO_RENDER:
        s1 = lineup(lod0, labels)
        renders.append(L.render(s1, OUT / 'Lineup_Bush.png', 2000, 1000))
        print('RENDERED Lineup', '%.1fs' % (time.time() - t0))
        s2 = detail_scene(); fig = L.flat_material('Review | Figure', (.55, .36, .16))
        for a in assets:
            nm = a['asset'].replace('SM_NZ_', '')
            renders.append(render_detail(s2, lod0[a['asset']], a['asset'], OUT / ('Detail_%s.png' % nm), fig))
            print('RENDERED Detail', nm, '%.1fs' % (time.time() - t0))
        if not NO_ASSEMBLY:
            s3 = assembly(lod0)
            renders.append(L.render(s3, OUT / 'Assembly_Bush.png', 2000, 1333))
            print('RENDERED Assembly', '%.1fs' % (time.time() - t0))
    try:
        bpy.context.window.scene = bpy.data.scenes['Native Bush Assets - metres']
    except Exception:
        pass
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    for b in OUT.glob('*.blend1'):
        b.unlink()
    for p in renders:
        print('RENDER', p)
    print('NATIVE_BUSH_BUILD_OK', len(assets), 'meshes', len(rows), 'lods', '%.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
