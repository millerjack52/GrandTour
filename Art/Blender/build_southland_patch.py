"""GP4a / GS2 grass patch set (docs/LIDAR_PLACE_PLAN.md GP4 and "Owner verdict 2026-10-19", stage GS2) on the native plant kit's pipeline: SM_NZ_GrassPatch_A/B/C, three seeds of ONE
design of a dense 70 x 70 cm grass patch that is instanced edge to edge (about 55 cm apart, so neighbours overlap and interleave) to give full-coverage grass geometry on the LiDAR
map (references Art/References/Grass/01-03; GS2 follows 01, the Breath of the Wild meadow: tall sweeping blades in clumps with flowers). Deterministic Blender geometry, THREE authored
LODs each, FBX (cm) + GLB (m), manifest rows (set 'patch'), the set .blend and review renders.

Run: blender -b --factory-startup --python-exit-code 1 --python build_southland_patch.py [-- --no-render --no-assembly --assembly-only]
Flags: --width-scale X multiplies every blade width (default 2.2: the 5-8 mm draw becomes 11-17.6 mm; 1.0 gives the original sparse 5-8 mm look), --tag _name suffixes the two assembly renders.

LOD0 (GS2): 5-7 TUFTS per patch (A 6, B 5, C 7; centres by best-candidate sampling in the 70 cm footprint, 12-16 cm tuft radius) plus short FILLER blades in the gaps between them.
  Tuft blades (about 61 percent of the 110 blades): the base lies in a crown of radius .5 R about the tuft centre, the blade fans outward from the centre (azimuth = the base's angle
  about the centre, +-30 degrees), inner blades stand up (20 degrees) and outer blades arch over (to 40 degrees), the length is lognormal with median 48 cm (range 40-65 cm) so the tips
  stand around 35-45 cm; each blade is a 3-triangle two-segment strip (base pair, mid pair, a point; segment tilts .65 b and 1.35 b) rising from 2 cm below ground.
  Filler blades (25 percent of the grass blades, base placed where it is farthest from every tuft): median 22 cm (15-32 cm), 25-50 degree lean, one tapered quad (2 triangles).
  Blades are 11-17.6 mm wide (the 5-8 mm draw times WIDTH_SCALE 2.2) with a slight twist; blades whose base (or tuft) is near an edge lean outward so adjacent patches interleave.
  8 percent of the blades are FLOWER stalks 35-50 cm tall (a straight 2-triangle stalk rising from inside a tuft, 6-18 degrees outward) carrying a 2.5 cm head of four quads: 50 percent white
  (.80,.80,.74), 30 percent purple (.48,.30,.55), 20 percent yellow (.85,.70,.15), the colours dealt from a shuffled ten-card list per patch. 10 percent are CLOVER (a 4-6 cm stalk with a
  2 cm trefoil of three round quads) placed in the gaps. LOD1 (<= 130 tris): every third grass blade kept and widened 1.6x (one segment, the longest upgraded to two while the ceiling holds), every
  flower stalk kept with a two-quad head, clover dropped. LOD2 (<= 24 tris): a six-card cross of wide strips 70 cm across at the new mean height carrying the gradient.

Vertex colour: linear FLOAT_COLOR `Color`, a vertical gradient per blade from the dark base to the bright tip, a per-blade luminance tint .85-1.15, a per-tuft tint .90-1.10 (fillers .92 darker) and a
per-patch region tint .95-1.05 in 20 cm cells. Its alpha is a wind weight, 0 at the blade base and 1 at the tip (the very short clover is damped to
.2, a 5 cm sprig must not flap like a 48 cm blade); L.to_object writes the per-vertex list of this script's GG geometry buffer.

Ground rule: the lowest vertex of every LOD is 2 cm below the ground plane; the manifest rows declare min_z_band [-.03, -.01] for the validator.
Every random draw is unconditional and in a fixed order from the seed 61000 + 97 k (k = 0, 1, 2), so the build is rerunnable and byte-stable.
"""
import bpy, sys, math, random, json, time
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_plant_lib as L
import build_native_bush as B
import build_southland_floor as F
import build_southland_grass as G
from native_plant_lib import Z, clamp, lerp, mix, scale_col, smoothstep, polar, rot

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
NO_RENDER = '--no-render' in ARGS
NO_ASSEMBLY = '--no-assembly' in ARGS
ASM_ONLY = '--assembly-only' in ARGS
WIDTH_SCALE = float(ARGS[ARGS.index('--width-scale') + 1]) if '--width-scale' in ARGS else 2.2     # blade width multiplier on the 5-8 mm draw: 2.2 (11-17.6 mm) is the GS2 width (GP4a shipped 2.0)
TAG = ARGS[ARGS.index('--tag') + 1] if '--tag' in ARGS else ''                                         # experiments only: suffix for the render file names
OUT = L.OUT
D2R = math.radians
TAU = math.tau
ROOT_Z = -.02
HALF = .35                   # footprint half-extent: 70 x 70 cm
EDGE_BAND = .10              # blades whose base is this close to an edge lean outward
TUFT_EDGE_BAND = .16         # tufts whose centre is this close to an edge lean outward (every blade of the tuft)
BUDGET = (420, 130, 24)      # triangles LOD0 / LOD1 / LOD2: hard ceilings
LOD0_TARGET = 414            # the design fills the LOD0 budget with two-segment tuft blades up to this (6 under the ceiling)
LOD1_TARGET = 126            # LOD1 upgrades its longest kept tuft blades to two segments while the total stays at or under this (4 under the ceiling)
N_BLADES = 110               # blades per patch: grass + clover + flower stalks
TUFTS = (6, 5, 7)            # tufts per patch A / B / C (the plan says 5-7)
TUFT_R = (.12, .16)          # tuft radius range, m
CROWN = .50                  # blade bases lie within CROWN * R of the tuft centre
LEN_MEDIAN = .48; LEN_RANGE = (.40, .65)        # tuft blade length, m (lognormal)
FILL_MEDIAN = .22; FILL_RANGE = (.15, .32)      # filler blade length, m
BEND_RANGE = (20, 50)        # degrees from vertical
FLOWER_LEN = (.35, .50)      # flower stalk length, m
FLOWER_FRAC = .08; CLOVER_FRAC = .10; FILLER_FRAC = .25

# ---------------------------------------------------------------- colours (linear RGB)
BASE_C = (.05, .11, .02); TIP_C = (.30, .40, .10)
CLOVER_C = (.09, .19, .04)
STALK_TIP_C = (.20, .30, .07)
FLOWER_COLS = ((.80, .80, .74), (.48, .30, .55), (.85, .70, .15))       # white, purple, yellow
FLOWER_NAMES = ('white', 'purple', 'yellow')
GROUND_C = TIP_C                                          # the ground the patches sit on in the assembly renders

ASSETS = [dict(asset='SM_NZ_GrassPatch_%s' % v, family='GrassPatch', variant=v, label='GRASS PATCH', sub=v, k=k) for k, v in enumerate('ABC')]


def seed_of(a):
    return 61000 + 97 * a['k']


def rhu(x):
    return int(math.floor(x + .5))


COST = dict(grass1=2, grass2=3, clover=7, flower=10)      # triangles per element at LOD0 (clover: 1-triangle stalk + three quads; flower: 2-triangle stalk + four quads)
FLOWER_LOD1 = 6                                           # a flower at LOD1: 2-triangle stalk + two quads


# ---------------------------------------------------------------- design

def edge_lean(x, y, az, bend, out_jit, tx=None, ty=None):
    """The lean direction and bend: random (az), except that blades near an edge (or in a tuft near an edge) lean outward so neighbouring patches interleave."""
    wx = clamp(1 - (HALF - abs(x)) / EDGE_BAND); wy = clamp(1 - (HALF - abs(y)) / EDGE_BAND)
    sx, sy = x, y
    if tx is not None:
        wx = max(wx, .85 * clamp(1 - (HALF - abs(tx)) / TUFT_EDGE_BAND)); wy = max(wy, .85 * clamp(1 - (HALF - abs(ty)) / TUFT_EDGE_BAND))
        sx, sy = tx, ty
    ow = max(wx, wy)
    rv = Vector((math.cos(az), math.sin(az), 0))
    outv = Vector((math.copysign(wx, sx), math.copysign(wy, sy), 0))
    if outv.length > 1e-6:
        outv = rot(outv.normalized(), Z, out_jit)
        d = rv * (1 - ow) + outv * ow
        d = d.normalized() if d.length > 1e-6 else outv
        bend = lerp(bend, D2R(40), .6 * ow)
    else:
        d = rv
    return d, bend, ow


def blade_rolls(rng):
    """The per-blade draws every blade takes (unconditional, fixed order)."""
    return dict(width=rng.uniform(.005, .008), roll=rng.uniform(-1.1, 1.1), twist=rng.uniform(-.45, .45), tint=rng.uniform(.85, 1.15), out_jit=rng.uniform(-.5, .5))


def best_candidate(rng, k, score):
    """Mitchell's best candidate: k random points in the footprint (all k draws taken), the one with the highest score(x, y)."""
    best = None
    for _ in range(k):
        x = rng.uniform(-HALF, HALF); y = rng.uniform(-HALF, HALF)
        sc = score(x, y)
        if best is None or sc > best[0]:
            best = (sc, x, y)
    return best[1], best[2]


def tip_z(length, bend, segs):
    """Height of the blade tip above the ground plane."""
    if segs == 1:
        return ROOT_Z + length * math.cos(bend)
    return ROOT_Z + length / 2 * (math.cos(.65 * bend) + math.cos(1.35 * bend))


def design(a):
    """One patch design from the asset's seed. Every random draw is unconditional and in a fixed order; the LODs are derived from it."""
    rng = random.Random(seed_of(a))
    n = N_BLADES
    n_flower = rhu(FLOWER_FRAC * n); n_clover = rhu(CLOVER_FRAC * n); n_grass = n - n_flower - n_clover
    n_fill = rhu(FILLER_FRAC * n_grass); n_tuft_bl = n_grass - n_fill
    cell_tint = [[rng.uniform(.95, 1.05) for _ in range(4)] for _ in range(4)]             # per-patch region tint, 20 cm cells (4 x 4 over 70 cm)
    T = TUFTS[a['k']]
    # tuft centres: Mitchell's best candidate, 16 candidates each, at least .05 m inside the footprint
    lim = HALF - .05
    tufts = []
    for t in range(T):
        best = None
        for _ in range(16):
            cx = rng.uniform(-lim, lim); cy = rng.uniform(-lim, lim)
            d = min([math.hypot(cx - u['x'], cy - u['y']) for u in tufts], default=9.0)
            if best is None or d > best[0]:
                best = (d, cx, cy)
        tufts.append(dict(x=best[1], y=best[2], R=rng.uniform(*TUFT_R), H=rng.uniform(.90, 1.14), tint=rng.uniform(.90, 1.10), w=rng.uniform(.8, 1.2), n=0))
    wsum = sum(u['w'] for u in tufts)
    raw = [n_tuft_bl * u['w'] / wsum for u in tufts]
    cnt = [int(math.floor(r)) for r in raw]
    for i in sorted(range(T), key=lambda i: -(raw[i] - cnt[i]))[:n_tuft_bl - sum(cnt)]:
        cnt[i] += 1
    for u, c in zip(tufts, cnt):
        u['n'] = c

    def region_tint(x, y):
        return cell_tint[min(3, int((y + HALF) / .2))][min(3, int((x + HALF) / .2))]

    blades = []
    # --- tuft blades: a crown, fanning outward, inner blades upright and outer blades arched over
    for ti, u in enumerate(tufts):
        for _ in range(u['n']):
            phi = rng.uniform(0, TAU); rr = math.sqrt(rng.random()); jit = rng.uniform(-.5, .5)
            bnoise = rng.uniform(-4, 4); lnoise = rng.gauss(0, .11); rolls = blade_rolls(rng)
            f = rr                                                  # radial fraction in the crown, 0 centre .. 1 rim
            x = u['x'] + math.cos(phi) * rr * CROWN * u['R']; y = u['y'] + math.sin(phi) * rr * CROWN * u['R']
            bend = D2R(clamp(lerp(20, 40, f ** 1.1) + bnoise, *BEND_RANGE))
            length = clamp(LEN_MEDIAN * u['H'] * math.exp(lnoise) * (1.04 - .10 * f), *LEN_RANGE)
            d, bend, ow = edge_lean(x, y, phi + jit, bend, rolls['out_jit'], u['x'], u['y'])
            bend = clamp(bend, D2R(BEND_RANGE[0]), D2R(BEND_RANGE[1]))
            blades.append(dict(kind='grass', role='tuft', tuft=ti, x=x, y=y, length=length, bend=bend, dir=d, width=rolls['width'], roll=rolls['roll'], twist=rolls['twist'],
                               tint=rolls['tint'] * u['tint'] * region_tint(x, y), edge=ow, segs=1))
    # --- filler blades in the gaps: the point farthest from every tuft (in tuft radii) and from the other fillers
    fillers = []
    for _ in range(n_fill):
        def score(x, y):
            s = min(math.hypot(x - u['x'], y - u['y']) / u['R'] for u in tufts)
            for q in fillers:
                s = min(s, math.hypot(x - q['x'], y - q['y']) / .12)
            return s
        x, y = best_candidate(rng, 8, score)
        az = rng.uniform(0, TAU); bnoise = rng.uniform(25, 50); lnoise = rng.gauss(0, .18); rolls = blade_rolls(rng)
        length = clamp(FILL_MEDIAN * math.exp(lnoise), *FILL_RANGE)
        d, bend, ow = edge_lean(x, y, az, D2R(bnoise), rolls['out_jit'])
        bend = clamp(bend, D2R(BEND_RANGE[0]), D2R(BEND_RANGE[1]))
        b = dict(kind='grass', role='filler', tuft=-1, x=x, y=y, length=length, bend=bend, dir=d, width=rolls['width'], roll=rolls['roll'], twist=rolls['twist'],
                 tint=rolls['tint'] * .92 * region_tint(x, y), edge=ow, segs=1)
        fillers.append(b); blades.append(b)
    # --- clover in the gaps (farthest from the tufts, the fillers and the other clover)
    clovers = []
    for _ in range(n_clover):
        def score(x, y):
            s = min(math.hypot(x - u['x'], y - u['y']) / u['R'] for u in tufts)
            for q in fillers:
                s = min(s, math.hypot(x - q['x'], y - q['y']) / .12)
            for q in clovers:
                s = min(s, math.hypot(x - q['x'], y - q['y']) / .15)
            return s
        x, y = best_candidate(rng, 8, score)
        c_tilt = D2R(rng.uniform(8, 30)); c_len = rng.uniform(.04, .06); c_az = rng.uniform(0, TAU)
        c_jit = [rng.uniform(-.4, .4) for _ in range(3)]; c_el = [D2R(rng.uniform(-5, 22)) for _ in range(3)]
        tint = rng.uniform(.85, 1.15) * region_tint(x, y)
        b = dict(kind='clover', role='clover', tuft=-1, x=x, y=y, tint=tint, c_tilt=c_tilt, c_len=c_len, c_az=c_az, c_jit=c_jit, c_el=c_el, segs=1)
        clovers.append(b); blades.append(b)
    # --- flower stalks rising from inside the tufts, leaning outward; colours dealt from a shuffled ten-card list (5 white, 3 purple, 2 yellow)
    deck = [0] * 5 + [1] * 3 + [2] * 2
    rng.shuffle(deck)
    for i in range(n_flower):
        r = rng.random() * wsum; acc = 0.0; ti = T - 1
        for q, u in enumerate(tufts):
            acc += u['w']
            if r <= acc:
                ti = q
                break
        u = tufts[ti]
        psi = rng.uniform(0, TAU); rad = rng.uniform(.30, .75) * u['R']
        f_len = rng.uniform(*FLOWER_LEN); f_tilt = D2R(rng.uniform(6, 18)); f_az = psi + rng.uniform(-.5, .5)
        f_jit = [rng.uniform(-.4, .4) for _ in range(4)]; f_el = [D2R(rng.uniform(15, 45)) for _ in range(4)]
        tint = rng.uniform(.9, 1.1)
        blades.append(dict(kind='flower', role='flower', tuft=ti, x=u['x'] + math.cos(psi) * rad, y=u['y'] + math.sin(psi) * rad, tint=tint, f_len=f_len, f_tilt=f_tilt, f_az=f_az,
                           f_col=deck[i], f_jit=f_jit, f_el=f_el, segs=1))
    # LOD2: six cards through the centre at 30 degree steps
    l2 = dict(phase=rng.uniform(0, math.pi / 6), height=[rng.uniform(.88, 1.12) for _ in range(6)], tint=[rng.uniform(.93, 1.07) for _ in range(6)],
              lean=[(rng.uniform(-.05, .05), rng.uniform(-.05, .05)) for _ in range(6)])
    grass = [b for b in blades if b['kind'] == 'grass']
    tuft_bl = [b for b in grass if b['role'] == 'tuft']
    # fill the LOD0 triangle budget with two-segment blades: the longest tuft blades curve most visibly; fillers stay one tapered quad
    fixed = n_clover * COST['clover'] + n_flower * COST['flower'] + len(grass) * COST['grass1']
    upgrades = max(0, min(len(tuft_bl), LOD0_TARGET - fixed))
    for b in sorted(tuft_bl, key=lambda b: -b['length'])[:upgrades]:
        b['segs'] = 2
    # LOD1: every third grass blade (tuft-major order), widened 1.6x; all flower stalks; clover dropped
    gi = [i for i, b in enumerate(blades) if b['kind'] == 'grass']
    keep = [gi[j] for j in range(0, len(gi), 3)]
    fl = [i for i, b in enumerate(blades) if b['kind'] == 'flower']
    base1 = 2 * len(keep) + FLOWER_LOD1 * len(fl)
    up1 = max(0, LOD1_TARGET - base1)
    cand = sorted([i for i in keep if blades[i]['role'] == 'tuft'], key=lambda i: -blades[i]['length'])[:up1]
    for i in cand:
        blades[i]['segs1'] = 2
    l1 = sorted(keep + fl)
    tips = [tip_z(b['length'], b['bend'], b['segs']) for b in grass]
    tuft_tips = [tip_z(b['length'], b['bend'], b['segs']) for b in tuft_bl]
    fill_tips = [tip_z(b['length'], b['bend'], b['segs']) for b in grass if b['role'] == 'filler']
    flower_tips = [ROOT_Z + b['f_len'] * math.cos(b['f_tilt']) for b in blades if b['kind'] == 'flower']
    lens = sorted(b['length'] for b in tuft_bl)
    fcols = [0, 0, 0]
    for b in blades:
        if b['kind'] == 'flower':
            fcols[b['f_col']] += 1
    mean_all = sum(tips) / len(tips)
    return dict(blades=blades, l1=l1, l2=l2, mean_height=mean_all, tufts=tufts,
                stats=dict(tuft_blade_length_median_m=round(lens[len(lens) // 2], 3), tuft_blade_length_min_m=round(lens[0], 3), tuft_blade_length_max_m=round(lens[-1], 3),
                           tuft_tip_height_mean_m=round(sum(tuft_tips) / len(tuft_tips), 3), filler_tip_height_mean_m=round(sum(fill_tips) / max(1, len(fill_tips)), 3),
                           flower_tip_height_mean_m=round(sum(flower_tips) / max(1, len(flower_tips)), 3),
                           tuft_bend_deg_range=[round(math.degrees(min(b['bend'] for b in tuft_bl)), 1), round(math.degrees(max(b['bend'] for b in tuft_bl)), 1)]),
                counts=dict(blades=n, grass=len(grass), clover=n_clover, flowers=n_flower, tufts=T, tuft_blades=len(tuft_bl), filler_blades=len(fillers), two_segment=upgrades,
                            lod1_blades=len(l1), lod1_two_segment=len(cand), flowers_white=fcols[0], flowers_purple=fcols[1], flowers_yellow=fcols[2],
                            tuft_radii_cm=[round(u['R'] * 100, 1) for u in tufts], tuft_blade_counts=[u['n'] for u in tufts]))


# ---------------------------------------------------------------- drawing

def blade_colours(nsec, tint):
    return [scale_col(mix(BASE_C, TIP_C, j / (nsec - 1)), tint) for j in range(nsec)]


def set_alpha(g, n0, per_section, tip):
    """Wind weight per vertex of one L.strip: per_section[j] on both vertices of section j (the single tip vertex of a pointed strip included)."""
    al = []
    last = len(per_section) - 1
    for j, v in enumerate(per_section):
        al += [v] * (1 if (tip and j == last) else 2)
    assert len(al) == len(g.v) - n0, (len(al), len(g.v) - n0)
    g.a[n0:] = al


def draw_grass(g, b, wscale=1.0, segs=None):
    base = Vector((b['x'], b['y'], ROOT_Z))
    d = b['dir']; nseg = b['segs'] if segs is None else segs
    tilts = [b['bend']] if nseg == 1 else [.65 * b['bend'], 1.35 * b['bend']]
    seg = b['length'] / nseg
    pts = [base]
    for t in tilts:
        pts.append(pts[-1] + (d * math.sin(t) + Z * math.cos(t)) * seg)
    n = len(pts)
    side0 = Z.cross(d).normalized()
    S = []; U = []
    for j in range(n):
        T = (pts[min(j + 1, n - 1)] - pts[max(j - 1, 0)]).normalized()
        s = rot(side0, T, b['roll'] + b['twist'] * j / (n - 1))
        S.append(s); U.append(T.cross(s).normalized())
    w = b['width'] * wscale * WIDTH_SCALE
    if nseg == 1:
        hw = [w * .5, w * .5 * .18]; tip = False                  # a tapered quad: 2 triangles
    else:
        hw = [w * .5, w * .5 * .85, 0.0]; tip = True              # base pair, mid pair, a point: 3 triangles
    n0 = len(g.v)
    L.strip(g, pts, hw, hw, S, U, BASE_C, 1, 0.0, tip=tip, colours=blade_colours(n, b['tint']))
    set_alpha(g, n0, [j / (n - 1) for j in range(n)], tip)
    g.counts['leaves'] += 1


def draw_clover(g, b):
    base = Vector((b['x'], b['y'], ROOT_Z))
    az = b['c_az']
    d = polar(b['c_tilt'], az)
    top = base + d * b['c_len']
    out = Vector((math.cos(az), math.sin(az), 0))
    side = Z.cross(out).normalized()
    col = scale_col(CLOVER_C, b['tint'])
    U = [d.cross(side).normalized()] * 2
    n0 = len(g.v)
    L.strip(g, [base, top], [.0013, 0.0], [.0013, 0.0], [side, side], U, col, 1, 0.0, tip=True)        # a one-triangle stalk
    set_alpha(g, n0, [0.0, .2], True)
    ln = .0105
    for k in range(3):
        a_k = az + k * TAU / 3 + b['c_jit'][k]; el = b['c_el'][k]
        dk = Vector((math.cos(el) * math.cos(a_k), math.cos(el) * math.sin(a_k), math.sin(el)))
        sd = Z.cross(dk); sd = sd.normalized() if sd.length > 1e-4 else Vector((1, 0, 0))
        n1 = len(g.v)
        G.kite(g, top + d * .002, dk, ln, ln * .95, sd, scale_col(CLOVER_C, b['tint'] * (.94 + .06 * k)), Z)
        g.a[n1:] = [.2] * (len(g.v) - n1)
    g.counts['leaves'] += 1


def draw_flower(g, b, petals=4):
    """A straight 2-triangle stalk (1.5 mm half-width at the base tapering to 1 mm) and a 2.5 cm head of `petals` quads (4 at LOD0, 2 at LOD1) in the flower's colour."""
    base = Vector((b['x'], b['y'], ROOT_Z))
    az = b['f_az']
    d = polar(b['f_tilt'], az)
    top = base + d * b['f_len']
    out = Vector((math.cos(az), math.sin(az), 0))
    side = Z.cross(out).normalized()
    U = [d.cross(side).normalized()] * 2
    sc = b['tint']
    n0 = len(g.v)
    L.strip(g, [base, top], [.0015, .0010], [.0015, .0010], [side, side], U, BASE_C, 1, 0.0, tip=False, colours=[scale_col(BASE_C, sc), scale_col(STALK_TIP_C, sc)])
    set_alpha(g, n0, [0.0, 1.0], False)
    head = FLOWER_COLS[b['f_col']]
    ln = .0125
    for k in range(petals):
        a_k = b['f_az'] + k * TAU / 4 + b['f_jit'][k]; el = b['f_el'][k]
        dk = Vector((math.cos(el) * math.cos(a_k), math.cos(el) * math.sin(a_k), math.sin(el)))
        sd = Z.cross(dk); sd = sd.normalized() if sd.length > 1e-4 else Vector((1, 0, 0))
        n1 = len(g.v)
        G.kite(g, top + d * .001, dk, ln, ln * .95, sd, scale_col(head, .97 + .03 * k), Z)
        g.a[n1:] = [1.0] * (len(g.v) - n1)
    g.counts['sprays'] += 1


def draw_lod0(g, D):
    for b in D['blades']:
        if b['kind'] == 'grass':
            draw_grass(g, b)
        elif b['kind'] == 'clover':
            draw_clover(g, b)
        else:
            draw_flower(g, b)


def draw_lod1(g, D):
    for i in D['l1']:
        b = D['blades'][i]
        if b['kind'] == 'grass':
            draw_grass(g, b, 1.6, segs=b.get('segs1', 1))
        else:
            draw_flower(g, b, petals=2)


def draw_lod2(g, D):
    """Six cards through the centre at 30 degree steps, each 70 cm across: base, shoulder and a slightly narrower top (4 triangles), carrying the gradient."""
    l2 = D['l2']; H0 = D['mean_height'] * .95
    for k in range(6):
        ang = l2['phase'] + k * math.pi / 6
        d = Vector((math.cos(ang), math.sin(ang), 0)); nrm = Z.cross(d)
        H = H0 * l2['height'][k]
        lx, ly = l2['lean'][k]
        centre = [Vector((0, 0, ROOT_Z)), Vector((lx * .4, ly * .4, ROOT_Z + (H - ROOT_Z) * .55)), Vector((lx, ly, H))]
        hw = [HALF, HALF * .96, HALF * .62]
        t = l2['tint'][k]
        cols = [scale_col(BASE_C, t), scale_col(mix(BASE_C, TIP_C, .55), t), scale_col(TIP_C, t)]
        n0 = len(g.v)
        L.strip(g, centre, hw, hw, [d] * 3, [nrm] * 3, BASE_C, 1, 0.0, tip=False, colours=cols)
        set_alpha(g, n0, [0.0, .5, 1.0], False)
        g.counts['leaves'] += 1


# ================================================================ build

def build_asset(a, mats, coll):
    seed = seed_of(a)
    D = design(a)
    gs = []
    for draw in (draw_lod0, draw_lod1, draw_lod2):
        g = G.GG(); draw(g, D); gs.append(g)
    obs = []; rows = []
    for lod, g in enumerate(gs):
        name = '%s_LOD%d' % (a['asset'], lod)
        ob, dropped = L.to_object(g, name, mats, [1], coll)
        n = len(ob.data.loop_triangles)
        print('LOD', name, n, 'of', BUDGET[lod], 'verts', len(g.v), 'size', [round(x, 3) for x in ob.dimensions], 'dropped', dropped)
        assert n <= BUDGET[lod], '%s: %d triangles over the LOD%d ceiling %d' % (name, n, lod, BUDGET[lod])
        ob['kit'] = L.KIT; ob['lod'] = lod; ob['seed'] = seed
        ob['placement'] = 'Ground pivot at the patch centre; bases stop 2 cm below ground. Vertex alpha = wind weight (0 base, 1 tip). No collision.'
        L.export(ob, [])
        extra = dict(min_z_band=[-.03, -.01], vertex_alpha='wind weight: 0 at the blade base, 1 at the tip (clover damped to .2)', footprint_m=[2 * HALF, 2 * HALF],
                     dropped_degenerate_faces=dropped, blade_width_scale=WIDTH_SCALE, blade_width_mm=[round(5 * WIDTH_SCALE, 1), round(8 * WIDTH_SCALE, 1)], mean_blade_height_m=round(D['mean_height'], 3))
        extra.update(D['counts']); extra.update(D['stats'])
        rows.append(L.manifest_row(ob, a['asset'], a['family'], a['variant'], lod, [1], seed, g.counts, 0, BUDGET[lod], extra))
        obs.append(ob)
    tr = [r['triangles'] for r in rows]
    assert tr[0] > tr[1] > tr[2], (a['asset'], tr)
    c = D['counts']
    assert 100 <= c['blades'] <= 160 and 5 <= c['tufts'] <= 7 and c['flowers'] == rhu(FLOWER_FRAC * c['blades']) and c['clover'] == rhu(CLOVER_FRAC * c['blades']), (a['asset'], c)
    for lod in range(3):
        amin = min(gs[lod].a); amax = max(gs[lod].a)
        assert amin < .001 and amax > .999, (a['asset'], lod, 'alpha range', amin, amax)
    print('BUILT', a['asset'], tr, 'size', rows[0]['size_m'], 'minz', [r['min_z_m'] for r in rows], 'mean height %.3f' % D['mean_height'], D['counts'])
    return obs, rows, D


# ================================================================ review renders

def lineup(lod0, tri_rows, D_rows):
    scene = L.review_scene('Patch Lineup')
    ink = L.flat_material('Review | Ink', (.70, .78, .70), .8); muted = L.flat_material('Review | Secondary', (.44, .53, .47), .8)
    chalk = L.flat_material('Review | Chalk', (.19, .225, .21))
    bar_a = L.flat_material('Review | Bar A', (.80, .55, .12)); bar_b = L.flat_material('Review | Bar B', (.75, .75, .70))
    L.floor(scene, chalk, 60, z=-.012, location=(2, 0))
    tilt = D2R(30)
    rot_txt = (math.pi / 2 - tilt, 0, 0)
    x = 0.0
    for a in ASSETS:
        ob = lod0[a['asset']]; lo, hi = B.bbox(ob)
        w = max(hi.x - lo.x, hi.y - lo.y)
        mid = x + w / 2
        L.display_copy(scene, ob, a['asset'].replace('SM_NZ_', 'Lineup_'), (mid - (lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, 0))
        tr = tri_rows[a['asset']]; dc = D_rows[a['asset']]
        y0 = -.66
        L.text_obj(scene, '%s %s' % (a['label'], a['sub']), (mid, y0, 0), .05, ink, rot_txt)
        L.text_obj(scene, '%d x %d x %d cm   %d blades  %d tufts  %d flowers' % (round((hi.x - lo.x) * 100), round((hi.y - lo.y) * 100), round(hi.z * 100), dc['blades'], dc['tufts'], dc['flowers']), (mid, y0 - .10, 0), .034, muted, rot_txt)
        L.text_obj(scene, 'LOD0 %d / LOD1 %d / LOD2 %d tris' % tuple(tr), (mid, y0 - .18, 0), .034, muted, rot_txt)
        x += w + .30
    width = x - .30
    for i in range(3):
        G.box(scene, 'Scale bar %d' % i, -.55 + .10 * i - .35, -.45 + .10 * i - .35, -.30, -.26, 0, .012, bar_a if i % 2 == 0 else bar_b)
    L.text_obj(scene, '30 CM', (-.55 - .35 + .15, -.40, 0), .04, ink, rot_txt)
    top = .72
    L.text_obj(scene, 'GRAND TOUR / NATIVE PLANTS / GRASS PATCHES', (-.9, .0, top), .075, ink, rot_txt, 'LEFT')
    L.text_obj(scene, 'GS2   3 MESHES   TRUE SCALE   THREE LODS   SCALE BAR 30 CM   70 X 70 CM FOOTPRINT   5-7 TUFTS   FLOWERS', (-.9, .0, top - .09), .04, muted, rot_txt, 'LEFT')
    cx = (width - .9) / 2
    L.studio_lights(scene, Vector((cx, 0, 0)), 1.3)
    target = Vector((cx, 0, .22))
    ortho = width + 1.4
    L.camera(scene, target + Vector((0, -math.cos(tilt), math.sin(tilt))) * 40, target, ortho=ortho)
    return scene, int(2000 * 1.46 / ortho) + 8


def assembly_meadow(objs, tag):
    """A 14 x 10 m slope from 1.2 m, 35 mm, overcast, exposure 1.8: the patches on a 55 cm jittered grid (about 460; random A/B/C, yaw and scale .8-1.25 each),
    the ground a plane coloured to the patch tip colour (.30, .40, .10) so the far edge fades, three of the kit's Beech_Edge behind."""
    bush = G.append_from('GrandTour_NativePlants.blend', ['SM_NZ_Beech_Edge_LOD0'])
    scene = L.review_scene('Meadow Assembly ' + tag)
    F.overcast_world(scene, 'NZ Meadow Overcast ' + tag, 1.8)
    rng = random.Random(61000 + 9001)
    ground = L.material('Assembly | Meadow ground', GROUND_C)
    ground.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .95

    def zfn_(x, y):
        return .105 * y + .035 * math.sin(x * .33 + y * .21) + .025 * math.sin(x * .81 - y * .57) + .012 * math.sin(y * 1.7 + x * 1.1)

    def zfn(x, y):
        return zfn_(x, y), 0, 0

    def cfn(x, y, z, tag_, u):
        return GROUND_C
    xs = sorted(set([-90, -50, -30, -16, 16, 30, 50, 90] + [-8 + i * .5 for i in range(33)]))
    ys = sorted(set([-14, -8, 18, 26, 44, 80] + [-4 + i * .5 for i in range(45)]))
    F.terrain_grid(scene, 'Meadow slope ' + tag, xs, ys, zfn, cfn, ground)
    counts = {}
    names = [a['asset'] for a in ASSETS]
    sp = .55
    nx = int(14 / sp); ny = int(10 / sp)
    for j in range(ny):
        for i in range(nx):
            x = -7 + sp * (i + .5) + rng.uniform(-.17, .17); y = sp * (j + .5) + rng.uniform(-.17, .17)
            nm = names[rng.randrange(3)]
            yaw = rng.uniform(0, TAU); sc = rng.uniform(.8, 1.25)
            o = L.display_copy(scene, objs[nm], nm.replace('SM_NZ_', 'Asm_') + '_%03d' % counts.get(nm, 0), (x, y, zfn_(x, y) - .004), yaw, sc)
            counts[nm] = counts.get(nm, 0) + 1
    for x, y in ((-5.0, 15.2), (.6, 16.4), (5.6, 15.0)):
        L.display_copy(scene, bush['SM_NZ_Beech_Edge'], 'Asm_Beech_Edge', (x, y, zfn_(x, y)), -math.pi / 2 + rng.uniform(-.4, .4), rng.uniform(.96, 1.04))
    L.studio_lights(scene, (0, 4, 0), 3.0, energy=.5)
    eye = Vector((0, -2.0, zfn_(0, -2.0) + 1.2))
    L.camera(scene, eye, Vector((0, 9.0, zfn_(0, 9.0) + .45)), lens=35)
    total = sum(counts.values())
    print('MEADOW ASSEMBLY', tag, counts, 'patches', total)
    return scene, dict(counts, patches=total)


def render_all(lod0, lod1, tri_rows, D_rows, t0):
    renders = []
    if not ASM_ONLY:
        s1, h = lineup(lod0, tri_rows, D_rows)
        renders.append(L.render(s1, OUT / 'Lineup_Patch.png', 2000, h))
        print('RENDERED Lineup', '%.1fs' % (time.time() - t0))
        s2 = G.detail_scene()
        fig = L.flat_material('Review | Figure', (.55, .36, .16))
        renders.append(B.render_detail(s2, lod0['SM_NZ_GrassPatch_A'], 'SM_NZ_GrassPatch_A', OUT / 'Detail_GrassPatch_A.png', fig))
        print('RENDERED Detail', '%.1fs' % (time.time() - t0))
    if not NO_ASSEMBLY:
        for fname, objs, tag in ((('Assembly_Meadow%s.png' % TAG), lod0, 'LOD0'), (('Assembly_Meadow_LOD1%s.png' % TAG), lod1, 'LOD1')):
            sc_, counts = assembly_meadow(objs, tag)
            renders.append(L.render(sc_, OUT / fname, 2000, 1333))
            print('RENDERED', fname, '%.1fs' % (time.time() - t0))
    return renders


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene; scene.name = 'Native Grass Patches - metres'
    mats = L.plant_materials()
    coll = scene.collection
    lod0 = {}; lod1 = {}; rows = []; tri_rows = {}; D_rows = {}
    x = 0.0
    for a in ASSETS:
        obs, r, D = build_asset(a, mats, coll)
        rows += r
        tri_rows[a['asset']] = [q['triangles'] for q in r]
        D_rows[a['asset']] = D['counts']
        lo, hi = B.bbox(obs[0])
        x += -lo.x + .3
        obs[0].location = (x, 0, 0)
        x += hi.x + .6
        for o in obs[1:]:
            o.hide_set(True); o.hide_render = True
        L.mark_asset(obs[0], a['label'] + ' ' + a['sub'] + ' / opaque vertex-colour blades / 3 LODs', ['Native', 'NZ', a['family'], 'Southland', 'Grass', 'Grand Tour'])
        lod0[a['asset']] = obs[0]; lod1[a['asset']] = obs[1]
    L.write_manifest(rows, set_name='patch', extra=dict(patch_stage='GP4a+GS2', patch_seeds={a['asset']: seed_of(a) for a in ASSETS},
                     patch_lod_rule='three LODs per asset from one design (seed 61000 + 97 k). GS2 LOD0: 110 blades 11-17.6 mm wide in 5-7 tufts (12-16 cm radius, blades fanning outward, 20-50 degree lean, lognormal length median 48 cm range 40-65 cm, '
                                    'three triangles each: base pair, mid pair, point) with short filler blades (median 22 cm, one tapered quad) in the gaps, 8 percent flower stalks 35-50 cm with a 2.5 cm head of four quads '
                                    '(50 white / 30 purple / 20 yellow), 10 percent clover (stalk plus three-quad trefoil); edge tufts lean outward. LOD1: every third grass blade widened 1.6x, every flower stalk with a two-quad head, clover dropped; '
                                    'LOD2: a six-card cross of 70 cm wide strips at the mean blade height carrying the gradient. Bases stop 2 cm below ground (rows declare min_z_band). Vertex alpha is a wind weight, 0 at the blade base and 1 at the tip (clover damped to .2). No collision'))
    print('MANIFEST', len(rows), 'rows', '%.1fs' % (time.time() - t0))
    renders = []
    if not NO_RENDER:
        renders += render_all(lod0, lod1, tri_rows, D_rows, t0)
    try:
        bpy.context.window.scene = bpy.data.scenes['Native Grass Patches - metres']
    except Exception:
        pass
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'GrandTour_NativePlants_Patch.blend'))
    for b in OUT.glob('*.blend1'):
        b.unlink()
    for p in renders:
        print('RENDER', p)
    print('NATIVE_PATCH_BUILD_OK', len(ASSETS), 'meshes', len(rows), 'lods', '%.1fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
