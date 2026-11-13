"""LM5 phase A2 (docs/LIVING_MUD_PLAN.md "LM5 phase A2: no swirls", docs/MUD_WET_STUDY.md): wet churned mud, study 04.

Started from revision 03 (Art/Blender/build_mud_style_study.py, untouched): this opens 03's saved scene
(Art/Export/MudStyleStudy/03/MudStyleStudy.blend: the approved clay, ruts, clods, pools, grass, light and cameras) and adds
a wet churn on the ruts and banks; the clay stays everywhere else. Output: Art/Export/MudStyleStudy/04_wet/.
Phase A's swirled version (the owner: "like chocolate") is kept in 04_wet/BeforeRevision/rev9_swirls_phaseA.

Run headless (Blender 5.1, no add-ons):
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 \
      --python Art/Blender/build_mud_wet_study.py -- [variant=Standard|Firm|Deep|Stony] [coverage=mud|ruts] [out=<dir>]
      [renders=a2] [quick [close=x,y]]
LM5b: variant picks the parameter set (VARIANTS; Standard is phase A2's, number for number); coverage=mud (default) paints
the bog over the whole mud patch, ruts included, coverage=ruts only on the ruts as A2 did; out is the folder under
Art/Export/MudStyleStudy (default 05_variants/<variant>). The per-variant set: ChurnClose, Tile3x3, TileClose and Driver
with the far gloss fade. renders=a2 renders phase A2's set instead (A2 itself: variant=Standard coverage=ruts out=04_wet
renders=a2). 'quick' renders small: the 3x3 tile view, a 1.5 m close-up of the plane (at x,y metres) and the driver view
at half size with its far-view band numbers.

The churn is torn and lumpy, not flowing. Periodic fields on one 3 m tile, 2048 x 2048, made here with numpy (every noise
is band-passed white noise in the Fourier domain, every stamp wraps), so the tile repeats with no mirror:
- clods 3-15 cm across pressed into the wet mud: irregular polygons (6-10 corners, a third with one side torn flat,
  corners rounded), domed on the ray-normalised radius, in three families (rounded lumps, low pressed slabs, faceted
  chunks), a tilted top, a fillet of slurry at the foot; clustered by a 55 / 25 cm density field, so some patches are
  crowded and others open; emerging from the slurry's colour and gloss at the foot, matte and a little lighter on top;
- dark wet gaps where clods crowd (the ground between them a little lower);
- flat slurry between them: broad, low, smooth, glossy (roughness 0.22-0.38);
- crumbs 1-4 cm: angular polygons (5-7 corners), no lobes, mostly near the clods (torn bits);
- colour: per-clod flat umbers, chosen by two independent broad patch fields (three umbers), slurry in two dark umbers
  by a third; nothing long or thin (clods at most 1.35:1, crumbs 1.5:1), no direction.
The colour is scaled so its mean CIE L* is VALUE_TARGET x the clay bake's (T_MS_ClayColor).
Stored as two 16-bit PNGs (fields/F_Paint.png = linear colour; fields/F_Shape.png = height, roughness, crumbs) plus
fields/F_Zones.png (slurry, clods, gaps; for the export's numbers). NG_MW_Churn reads them; Art/Blender/export_mud_wet.py
bakes it into the four 2048 maps.
"""
import bpy, math, ast, json, sys, zlib, struct, time
import numpy as np
from pathlib import Path
from mathutils import Vector

T0 = time.time()
ROOT = Path(__file__).resolve().parents[2]
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
QUICK = 'quick' in ARGS


def arg(name, default):
    return next((a.split('=', 1)[1] for a in ARGS if a.startswith(name + '=')), default)


N = 2048            # field resolution (the bakes' size)
TILE = 300.0        # cm
PX = TILE / N       # cm per pixel
HEIGHT_BUMP = 1.0

# LM5b (docs/LIVING_MUD_PLAN.md "LM5b: four churned-bog variants"): one parameter set per variant. Standard is phase A2's
# churn, number for number (it reproduces A2's fields to the bit). Colours are linear, before the value scaling; value
# is the mean CIE L* over the clay bake's.
STANDARD = dict(
    seed=405, value=.60,
    umbers=[(.072, .041, .019), (.064, .040, .021), (.078, .040, .017)],   # clod umbers: warm, grey-brown, red
    side=.82, shade=(.5, .9),                                              # the clod's side shade, top-lightening ramp
    slurry=[(.037, .021, .0095), (.053, .031, .0145)], gap=(.019, .010, .0045), crumb_lift=1.10,
    slurry_rough=(.22, .38), gap_rough=.25, clod_rough=(.58, .86), crumb_rough=.86,
    clod_rough_ramp=((.45, .85), (.1, .45)),
    crowd=(-.2, .95), base=(.06, .3), clod_target=.36, accept=(.15, .85), size=(1.5, 6.0, 1.4),
    fam=(.5, .83), dome=((.30, .48), (2.5, 4.0), .3), slab=((.16, .26), (5.0, 8.0), .4), chunk=((.30, .45), (3.0, 5.0)),
    tilt=(.07, .12), fillet=(.12, 1.3), crumb_target=.04, crumb_accept=(.12, .88),
    gap_depth=.4, emerge=(.1, .7), crumb_emerge=(.05, .55), tone_jitter=(.96, 1.04), stones=None,
    prof_pow=.6, win=1.75)   # the clod's profile (1 - q^e)^prof_pow (.6: steep sides; 1+: it rises out of the mud), window
VARIANTS = {
    'Standard': STANDARD,
    # Firm: lighter mid-brown, less slurry (matte lumps dominate), smaller lumps. The lumps rise out of the mud (soft
    # shoulders, a broad foot) in nearly its own tone, so crowded lumps make one torn surface, not a bed of pebbles.
    'Firm': dict(STANDARD, seed=406, value=.72,
                 umbers=[(.090, .060, .035), (.083, .058, .037), (.094, .059, .033)], side=.88,
                 slurry=[(.062, .042, .023), (.069, .046, .026)], gap=(.054, .037, .020), crumb_lift=1.06,
                 slurry_rough=(.58, .72), gap_rough=.55, clod_rough=(.76, .90), crumb_rough=.90,
                 clod_rough_ramp=((.35, .8), (.0, .3)),
                 crowd=(-.6, .9), base=(.05, .15), clod_target=.50, accept=(.40, .60), size=(1.5, 3.5, 1.5),
                 fam=(.35, .70), dome=((.26, .40), (2.0, 3.0), .35), slab=((.13, .20), (4.0, 6.0), .5),
                 chunk=((.26, .38), (2.5, 4.0)), fillet=(.22, 1.5), crumb_target=.06, crumb_accept=(.30, .70),
                 gap_depth=.12, emerge=(.0, .6), crumb_emerge=(.0, .5), prof_pow=1.0, win=2.0),
    # Deep: darker, wetter, large glossy slurry areas, fewer, softer lumps: low wet humps slumping into the slurry.
    'Deep': dict(STANDARD, seed=407, value=.50,
                 umbers=[(.050, .030, .0145), (.047, .030, .016), (.053, .030, .0135)], side=.9,
                 slurry=[(.038, .022, .0100), (.044, .026, .0120)], gap=(.034, .020, .009), crumb_lift=1.05,
                 slurry_rough=(.15, .28), gap_rough=.18, clod_rough=(.42, .64), crumb_rough=.66,
                 clod_rough_ramp=((.5, .95), (.2, .7)),
                 crowd=(.1, 1.0), base=(.10, .2), clod_target=.18, accept=(.03, .97), size=(2.5, 5.0, 1.2),
                 fam=(.70, .95), dome=((.12, .20), (1.8, 2.6), .1), slab=((.07, .12), (3.0, 5.0), .15),
                 chunk=((.16, .24), (2.5, 4.0)), tilt=(.04, .06), fillet=(.35, 1.8), crumb_target=.012,
                 gap_depth=.15, emerge=(.15, .9), crumb_emerge=(.15, .7), prof_pow=1.3, win=2.2),
    # Stony: the churn with gravel and small stones pressed in, the gravel-04 palette under an earth coating; the lumps
    # rise out of the mud as in Firm; the stones are sunk, clustered and coated, 1.2-6 cm.
    'Stony': dict(STANDARD, seed=408, value=.62,
                  umbers=[(.066, .042, .022), (.061, .041, .024), (.069, .041, .020)], side=.88,
                  slurry=[(.046, .029, .014), (.054, .034, .017)], gap=(.036, .022, .011),
                  clod_target=.24, size=(1.5, 5.0, 1.4), crumb_target=.03, emerge=(.0, .6),
                  dome=((.24, .38), (2.0, 3.0), .3), slab=((.13, .20), (4.0, 6.0), .4), chunk=((.24, .36), (2.5, 4.0)),
                  fillet=(.25, 1.55), gap_depth=.15, prof_pow=.95, win=2.0,
                  stones=dict(cover=.08, size=(.6, 2.4, 1.3), height=(.45, .65), embed=(.35, .60), accept=(.02, .98, .1, 1.2),
                              rmin=.65, round=(2, 5),
                              palette=[(.20, .235, .25), (.38, .375, .335), (.26, .275, .265), (.29, .315, .31)],
                              coat=(.70, .52, .36), mud_coat=(.60, .85), rough=(.45, .60))),
}
VARIANT = arg('variant', 'Standard')
assert VARIANT in VARIANTS, 'variant=%s: one of %s' % (VARIANT, ', '.join(VARIANTS))
V = VARIANTS[VARIANT]
SEED = V['seed']
VALUE_TARGET = V['value']
COVERAGE = arg('coverage', 'mud')     # 'mud': the bog over the whole mud patch (LM5b); 'ruts': phase A2's churn on the ruts
assert COVERAGE in ('mud', 'ruts')
OUT = ROOT / 'Art/Export/MudStyleStudy' / arg('out', '05_variants/' + VARIANT)
FIELDS = OUT / 'fields'
FIELDS.mkdir(parents=True, exist_ok=True)
# Phase A2's names, read by the node group and the export.
UMBERS, SIDE, SLURRY, GAP, CRUMB_LIFT = V['umbers'], V['side'], V['slurry'], V['gap'], V['crumb_lift']
SLURRY_ROUGH, GAP_ROUGH, CLOD_ROUGH, CRUMB_ROUGH = V['slurry_rough'], V['gap_rough'], V['clod_rough'], V['crumb_rough']


def say(msg):
    print('MUD_WET %6.1f s  %s' % (time.time() - T0, msg), flush=True)


# ---------------------------------------------------------------- periodic fields (numpy)
def band(n, feat_cm, seed, width=.6):
    """Zero-mean, unit-std noise with features of about feat_cm (wavelength), periodic over the tile."""
    rng = np.random.default_rng(SEED * 1000 + seed)
    F = np.fft.rfft2(rng.standard_normal((n, n)))
    fy = np.fft.fftfreq(n, d=TILE / n)[:, None]
    fx = np.fft.rfftfreq(n, d=TILE / n)[None, :]
    k = np.hypot(fx, fy)
    k[0, 0] = 1e-9
    filt = np.exp(-.5 * (np.log(k * feat_cm) / width) ** 2)
    filt[0, 0] = 0
    a = np.fft.irfft2(F * filt, s=(n, n))
    return (a - a.mean()) / a.std()


def gauss(a, sigma_cm):
    k = np.hypot(np.fft.fftfreq(N, d=PX)[:, None], np.fft.rfftfreq(N, d=PX)[None, :])
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (math.pi * sigma_cm * k) ** 2), s=a.shape)


def smoothstep(a, b, x):
    v = np.clip((x - a) / (b - a), 0, 1)
    return v * v * (3 - 2 * v)


def lerp(a, b, t):
    return a + (b - a) * t


def write_png(path, arr, bits=16):
    """arr (h, w, 3) floats 0..1, row 0 = the bottom (Blender's v = 0); written top row first."""
    a = np.clip(arr[::-1], 0, 1)
    h, w, _ = a.shape
    data = (a * 65535 + .5).astype('>u2') if bits == 16 else (a * 255 + .5).astype(np.uint8)
    rows = data.reshape(h, -1).view(np.uint8)
    raw = np.hstack([np.zeros((h, 1), np.uint8), rows]).tobytes()

    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xFFFFFFFF)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, bits, 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def read_png(path):
    """A PNG as Blender loads it, raw (Non-Color): (h, w, 4) floats, row 0 = the bottom."""
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = 'Non-Color'
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(a)
    out = a.reshape(im.size[1], im.size[0], 4).astype(np.float64)
    bpy.data.images.remove(im)
    return out


def srgb_to_linear(s):
    return np.where(s <= .04045, s / 12.92, ((s + .055) / 1.055) ** 2.4)


def lstar(lin_rgb):
    lum = lin_rgb @ np.array([.2126, .7152, .0722])
    return np.where(lum > .008856, 116 * np.cbrt(np.maximum(lum, 0)) - 16, 903.3 * lum)


def poly_sdf(X, Y, P):
    """Signed distance (positive inside) from the points (X, Y) to the polygon P (k, 2), in the same units."""
    d2 = np.full(X.shape, np.inf)
    inside = np.zeros(X.shape, bool)
    k = len(P)
    for i in range(k):
        ax, ay = P[i]
        bx, by = P[(i + 1) % k]
        ex, ey = bx - ax, by - ay
        wx, wy = X - ax, Y - ay
        t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1)
        dx, dy = wx - t * ex, wy - t * ey
        d2 = np.minimum(d2, dx * dx + dy * dy)
        if abs(ey) > 1e-12:
            inside ^= ((Y >= ay) != (Y >= by)) & (X < ax + (Y - ay) * ex / ey)
    d = np.sqrt(d2)
    return np.where(inside, d, -d)


def outline(rng, r, kmin, kmax, rmin, aspect_max, notch_p):
    """An irregular polygon about the origin, radius about r: k corners at jittered angles and radii, one side torn
    flat (a chord 0.55-0.8 r from the middle) with probability torn_p, stretched to at most aspect_max:1 along a random
    axis. (A2 revision 5: revision 4's torn bite, one corner pulled in to half, drew heart shapes.)"""
    k = int(rng.integers(kmin, kmax + 1))
    ang = (np.arange(k) + rng.uniform(-.35, .35, k)) * 2 * math.pi / k + rng.uniform(0, 2 * math.pi)
    rad = r * rng.uniform(rmin, 1.0, k)
    if rng.random() < notch_p:
        phi = rng.uniform(0, 2 * math.pi)
        off = np.angle(np.exp(1j * (ang - phi)))
        c = r * rng.uniform(.55, .8)
        near = np.abs(off) < math.radians(65)
        rad[near] = np.minimum(rad[near], c / np.cos(off[near]))
    a = math.sqrt(rng.uniform(1.0, aspect_max))
    th = rng.uniform(0, math.pi)
    x = rad * np.cos(ang) * a
    y = rad * np.sin(ang) / a
    c, s = math.cos(th), math.sin(th)
    return np.stack([x * c - y * s, x * s + y * c], -1)


def star_q(P, X, Y, round_deg):
    """For a polygon P (star-shaped about the origin): q = distance / the boundary's distance along the same ray, the
    boundary first smoothed over +-round_deg (rounded corners). q < 1 inside. A dome on q has no creases from the
    polygon's medial axis (the polygon SDF's profile read as cut stones), only the outline's corners."""
    n = 720
    th = np.linspace(0, 2 * math.pi, n, endpoint=False)
    dx, dy = np.cos(th), np.sin(th)
    R = np.full(n, np.inf)
    k = len(P)
    for i in range(k):
        ax, ay = P[i]
        ex, ey = P[(i + 1) % k][0] - ax, P[(i + 1) % k][1] - ay
        det = -dx * ey + dy * ex
        ok = np.abs(det) > 1e-12
        det = np.where(ok, det, 1)
        t = (-ax * ey + ay * ex) / det
        u = (dx * ay - dy * ax) / det
        hit = ok & (t > 0) & (u >= 0) & (u <= 1)
        R = np.where(hit, np.minimum(R, t), R)
    R = np.where(np.isfinite(R), R, np.nanmax(np.where(np.isfinite(R), R, np.nan)))
    w = max(1, int(round(round_deg * n / 360)))
    R = np.convolve(np.concatenate([R[-w:], R, R[:w]]), np.ones(2 * w + 1) / (2 * w + 1), 'valid')
    ang = np.mod(np.arctan2(Y, X), 2 * math.pi)
    return np.hypot(X, Y) / np.interp(ang, th, R, period=2 * math.pi)


def window(cx, cy, extent_px):
    span = int(extent_px) + 3
    ix = np.arange(int(cx) - span, int(cx) + span + 1)
    iy = np.arange(int(cy) - span, int(cy) + span + 1)
    X = np.broadcast_to(ix[None, :] - cx, (len(iy), len(ix)))
    Y = np.broadcast_to(iy[:, None] - cy, (len(iy), len(ix)))
    return np.ix_(iy % N, ix % N), X, Y


def stamp(arrays, sub, z, a, kid, h):
    """Add one shape: Z keeps the highest surface; the owner, its top fraction and the coverage follow it."""
    Z, OWN, TF, COV = arrays
    cur = Z[sub]
    m = (a > .02) & (z >= cur)
    Z[sub] = np.maximum(cur, z)
    own = OWN[sub]
    own[m] = kid
    OWN[sub] = own
    tf = TF[sub]
    tf[m] = (z / max(h, 1e-6))[m]
    TF[sub] = tf
    COV[sub] = np.maximum(COV[sub], a)


def coherence(a):
    ax = (np.roll(a, -1, 1) - np.roll(a, 1, 1)) * .5
    ay = (np.roll(a, -1, 0) - np.roll(a, 1, 0)) * .5
    jxx, jyy, jxy = (ax * ax).mean(), (ay * ay).mean(), (ax * ay).mean()
    return float(math.hypot(jxx - jyy, 2 * jxy) / max(jxx + jyy, 1e-12))


def build_stones(S, COV, pa, pb):
    """Stony: gravel and small stones pressed into the churn - angular-rounded, 1-6 cm (most 1-3), mostly sunk (only the
    top 40-65 % shows), clustered into gravel patches, never stacked or standing on a clod, in the gravel-04 palette under
    the 03 earth coat (x 0.70 / 0.52 / 0.36) and then part-covered by the mud's own umber. Its own random stream, so the
    churn under it is the same draw as without stones."""
    rng = np.random.default_rng(SEED * 7 + 1)
    acc = S.get('accept', (.25, .75, -.4, .8))
    dens = smoothstep(acc[2], acc[3], band(N, 40, 11))
    arrays = (np.zeros((N, N)), np.full((N, N), -1, np.int64), np.zeros((N, N)), np.zeros((N, N)))
    tones, sizes = [], []
    for _ in range(40000):
        if len(sizes) % 100 == 0 and len(sizes) and arrays[3].mean() >= S['cover']:
            break
        cx, cy = rng.uniform(0, N, 2)
        ic, jc = int(cy) % N, int(cx) % N
        if rng.random() > acc[0] + acc[1] * dens[ic, jc] or COV[ic, jc] > .3:
            continue
        r = S['size'][0] + S['size'][1] * rng.random() ** S['size'][2]
        rp = r / PX
        sub, X, Y = window(cx, cy, rp * 1.6)
        if arrays[3][ic, jc] > .3:                          # no stone on top of another (they may touch)
            continue
        P = outline(rng, rp, 5, 8, S.get('rmin', .7), 1.5, .25)
        q = star_q(P, X, Y, rng.uniform(*S.get('round', (3, 8))))
        h = r * rng.uniform(*S['height'])
        prof = (1 - np.clip(q, 0, 1) ** rng.uniform(2.5, 4.5)) ** .6
        z = h * prof
        phi = rng.uniform(0, 2 * math.pi)
        for f in range(int(rng.random() < .6) + int(rng.random() < .3)):     # flat broken faces
            ph = phi + f * rng.uniform(1.6, 2.6)
            proj = (X * math.cos(ph) + Y * math.sin(ph)) * PX
            z = np.minimum(z, np.maximum(h * .92 - rng.uniform(.3, .7) * h / r * (proj - rng.uniform(.2, .5) * r), .4 * h * prof))
        embed = h * rng.uniform(*S['embed'])
        z = np.maximum(z - embed, 0)
        exposed = max(h - embed, 1e-6)
        stone = np.array(S['palette'][int(rng.integers(len(S['palette'])))]) * np.array(S['coat']) * rng.uniform(.9, 1.1)
        u = UMBERS[2] if pa[ic, jc] > .35 else (UMBERS[0] if pb[ic, jc] > 0 else UMBERS[1])
        tones.append(lerp(stone, np.array(u) * 1.1, rng.uniform(*S['mud_coat'])))
        stamp(arrays, sub, z, smoothstep(0, .12 * exposed, z), len(tones) - 1, exposed)
        sizes.append(2 * r)
    Z, OWN, TF, SCOV = arrays
    sizes = np.array(sizes)
    say('%d stones, cover %.3f' % (len(sizes), SCOV.mean()))
    return dict(Z=Z, OWN=OWN, TF=TF, COV=SCOV, tones=np.array(tones), count=len(sizes),
                across=[round(float(sizes.min()), 2), round(float(np.median(sizes)), 2), round(float(sizes.max()), 2)])


def build_fields():
    rng = np.random.default_rng(SEED)
    crowd = smoothstep(V['crowd'][0], V['crowd'][1], .8 * band(N, 55, 1) + .35 * band(N, 25, 2))   # 0 open .. 1 crowded
    base = V['base'][0] * band(N, 90, 3) - V['base'][1] * crowd                    # the slurry surface, cm (flat)
    pa, pb, pc, pd = band(N, 70, 4), band(N, 45, 5), band(N, 55, 6), band(N, 50, 7)
    # Clods.
    clods = (np.zeros((N, N)), np.full((N, N), -1, np.int64), np.zeros((N, N)), np.zeros((N, N)))
    tones, hs, sizes = [], [], []
    target = V['clod_target']
    attempts = 0
    while attempts < 20000:
        attempts += 1
        if len(sizes) % 50 == 0 and len(sizes) and clods[3].mean() >= target:
            break
        cx, cy = rng.uniform(0, N, 2)
        ic, jc = int(cy) % N, int(cx) % N
        if rng.random() > V['accept'][0] + V['accept'][1] * crowd[ic, jc] or clods[3][ic, jc] > .4:
            continue
        # (A2 revision 2: the first clods read as chiselled stones - hard bevels, flat tops, dark rims. Now rounder,
        # domed, a soft foot in the slurry, lower, a broken facet on a third.)
        r = V['size'][0] + V['size'][1] * rng.random() ** V['size'][2]   # cm (Standard: 3-15 across, median about 7.5)
        P = outline(rng, r / PX, 6, 10, .8, 1.35, .3)
        rp = r / PX
        sub, X, Y = window(cx, cy, rp * V['win'])
        # (A2 revision 3: revision 2's polygon-distance profile still creased into cut-stone facets; the dome is now on
        # the ray-normalised radius of a corner-rounded outline.)
        q = star_q(P, X, Y, rng.uniform(6, 14))
        # (A2 revision 6: revision 5's lumps were all domes and read as pebbles. Three families: half rounded lumps,
        # a third pressed slabs - low, flat-topped, tilted - and the rest broken chunks with two facets.)
        fam = rng.random()
        dome, slab, chunk = V['dome'], V['slab'], V['chunk']
        if fam < V['fam'][0]:
            h, expo, facets = r * rng.uniform(*dome[0]), rng.uniform(*dome[1]), int(rng.random() < dome[2])
        elif fam < V['fam'][1]:
            h, expo, facets = r * rng.uniform(*slab[0]), rng.uniform(*slab[1]), int(rng.random() < slab[2])
        else:
            h, expo, facets = r * rng.uniform(*chunk[0]), rng.uniform(*chunk[1]), 2
        prof = (1 - np.clip(q, 0, 1) ** expo) ** V['prof_pow']
        z = np.maximum(h * prof, V['fillet'][0] * h * smoothstep(V['fillet'][1], .95, q))   # (revision 4) a fillet: slurry squeezed up its foot
        tx, ty = rng.normal(0, V['tilt'][0] if fam < V['fam'][0] else V['tilt'][1], 2)     # a tilted top, cm per cm
        z = z + prof * (tx * X + ty * Y) * PX
        phi = rng.uniform(0, 2 * math.pi)
        for f in range(facets):                                         # broken facets
            ph = phi + f * rng.uniform(1.6, 2.6)
            proj = (X * math.cos(ph) + Y * math.sin(ph)) * PX
            cut = h * .9 - rng.uniform(.4, .8) * h / r * (proj - rng.uniform(.25, .55) * r)
            z = np.minimum(z, np.maximum(cut, .3 * h * prof))
        z = np.maximum(z, 0)
        u = UMBERS[2] if pa[ic, jc] > .35 else (UMBERS[0] if pb[ic, jc] > 0 else UMBERS[1])
        tones.append(np.array(u) * rng.uniform(*V['tone_jitter']) * (1 + .08 * np.clip(pc[ic, jc], -1.5, 1.5)))
        stamp(clods, sub, z, smoothstep(1.03, .95, q), len(tones) - 1, h)
        hs.append(h)
        sizes.append(2 * r)
    Zc, OWN, TF, COV = clods
    say('%d clods, cover %.3f, %d attempts' % (len(sizes), COV.mean(), attempts))
    # Crumbs: torn bits, mostly near the clods.
    near = smoothstep(.05, .4, gauss(COV, 4.0))
    crumbs = (np.zeros((N, N)), np.full((N, N), -1, np.int64), np.zeros((N, N)), np.zeros((N, N)))
    ctones, csizes = [], []
    for _ in range(9000):
        if len(csizes) % 100 == 0 and len(csizes) and crumbs[3].mean() >= V['crumb_target']:
            break
        cx, cy = rng.uniform(0, N, 2)
        ic, jc = int(cy) % N, int(cx) % N
        if rng.random() > V['crumb_accept'][0] + V['crumb_accept'][1] * near[ic, jc] or COV[ic, jc] > .2 or crumbs[3][ic, jc] > .2:
            continue
        r = .5 + 1.5 * rng.random() ** 1.6                          # cm: 1-4 across
        rp = r / PX
        P = outline(rng, rp, 5, 7, .65, 1.5, 0)
        sub, X, Y = window(cx, cy, rp * 1.3)
        q = star_q(P, X, Y, rng.uniform(4, 10))
        h = r * rng.uniform(.3, .5)
        z = h * (1 - np.clip(q, 0, 1) ** rng.uniform(2.0, 3.0)) ** .6
        u = UMBERS[2] if pa[ic, jc] > .35 else (UMBERS[0] if pb[ic, jc] > 0 else UMBERS[1])
        ctones.append(np.array(u) * CRUMB_LIFT * rng.uniform(.92, 1.08))
        stamp(crumbs, sub, z, smoothstep(1.06, .92, q), len(ctones) - 1, h)
        csizes.append(2 * r)
    Zk, OWNK, TFK, CCOV = crumbs
    say('%d crumbs, cover %.3f' % (len(csizes), CCOV.mean()))
    stones = build_stones(V['stones'], COV, pa, pb) if V['stones'] else None
    # Wet gaps where clods crowd.
    gap = (1 - COV) * (1 - CCOV) * smoothstep(.3, .7, gauss(COV, 1.0))
    H = base - V['gap_depth'] * gap + np.maximum(Zc, Zk)
    if stones:
        H = np.maximum(H, base - V['gap_depth'] * gap + stones['Z'])
    # Colour.
    col = np.empty((N, N, 3))
    col[:] = SLURRY[0]
    col = lerp(col, np.array(SLURRY[1]), smoothstep(-.3, .3, pc)[..., None])
    col = lerp(col, np.array(GAP), gap[..., None])
    T = np.array(tones)
    # (A2 revision 4: revision 3's lumps sat on the slurry like pebbles. Now each emerges from it: the slurry's colour and
    # gloss at its foot, its own umber from a third of the way up, matte and a little lighter on top.)
    slurry_col = col.copy()
    shade = SIDE + (1 - SIDE) * smoothstep(V['shade'][0], V['shade'][1], TF)
    emerge = smoothstep(V['emerge'][0], V['emerge'][1], TF)[..., None]
    clod_col = lerp(slurry_col, T[np.clip(OWN, 0, None)] * shade[..., None], emerge)
    col = lerp(col, clod_col, (COV * (OWN >= 0))[..., None])
    CT = np.array(ctones)
    cshade = SIDE + (1 - SIDE) * smoothstep(.4, .85, TFK)
    crumb_col = lerp(slurry_col, CT[np.clip(OWNK, 0, None)] * cshade[..., None],
                     smoothstep(V['crumb_emerge'][0], V['crumb_emerge'][1], TFK)[..., None])
    crumb_w = CCOV * (OWNK >= 0) * (Zk >= Zc)
    col = lerp(col, crumb_col, crumb_w[..., None])
    if stones:
        # Stones emerge from the mud at their foot; their tops show the coated gravel.
        st = stones['tones'][np.clip(stones['OWN'], 0, None)] * (.88 + .12 * smoothstep(.4, .9, stones['TF']))[..., None]
        stone_col = lerp(slurry_col, st, smoothstep(.0, .45, stones['TF'])[..., None])
        stone_w = stones['COV'] * (stones['OWN'] >= 0) * (stones['Z'] >= np.maximum(Zc, Zk))
        col = lerp(col, stone_col, stone_w[..., None])
    # The value: scaled so the mean L* is VALUE_TARGET x the clay bake's.
    clay = read_png(ROOT / 'Art/Export/MudStyleUE/T_MS_ClayColor.png')[..., :3]
    clay_l = float(lstar(srgb_to_linear(clay)).mean())
    lo, hi = .3, 3.0
    for _ in range(30):
        s = (lo + hi) / 2
        if lstar(np.clip(col * s, 0, 1)).mean() < VALUE_TARGET * clay_l:
            lo = s
        else:
            hi = s
    scale = (lo + hi) / 2
    col = np.clip(col * scale, 0, 1)
    # Roughness.
    rough = lerp(SLURRY_ROUGH[0], SLURRY_ROUGH[1], smoothstep(-.6, .6, pd))
    rough = lerp(rough, GAP_ROUGH, gap)
    cr = V['clod_rough_ramp']
    clod_rough = lerp(rough, lerp(CLOD_ROUGH[0], CLOD_ROUGH[1], smoothstep(cr[0][0], cr[0][1], TF)), smoothstep(cr[1][0], cr[1][1], TF))
    rough = lerp(rough, clod_rough, COV * (OWN >= 0))
    rough = lerp(rough, lerp(rough, CRUMB_ROUGH, smoothstep(.05, .45, TFK)), crumb_w)
    if stones:
        sr = V['stones']['rough']
        rough = lerp(rough, lerp(rough, lerp(sr[0], sr[1], smoothstep(.3, .9, stones['TF'])), smoothstep(.05, .4, stones['TF'])), stone_w)
    hmin, hmax = float(H.min()), float(H.max())
    H01 = (H - hmin) / (hmax - hmin)
    slurry = (1 - COV) * (1 - CCOV) * (1 - gap)
    write_png(FIELDS / 'F_Paint.png', col)
    write_png(FIELDS / 'F_Shape.png', np.stack([H01, rough, CCOV], -1))
    write_png(FIELDS / 'F_Zones.png', np.stack([slurry, COV, gap], -1))
    if stones:
        write_png(FIELDS / 'F_Stones.png', np.stack([stones['COV'] * (stones['OWN'] >= 0), stones['TF'], stone_w], -1))
    half = lambda a: a[::2, ::2]
    lum = col @ np.array([.2126, .7152, .0722])
    prev = np.concatenate([np.clip(half(col) / max(float(np.percentile(lum, 99.5)), 1e-6) * .8, 0, 1),
                           np.repeat(half(H01)[..., None], 3, -1),
                           np.stack([half(COV) * .8 + half(CCOV), half(COV) * .45 + half(CCOV) * .6, half(gap)], -1)], 1)
    write_png(FIELDS / 'fields_preview.png', prev, bits=8)
    sizes, csizes, hs = np.array(sizes), np.array(csizes), np.array(hs)
    stats = dict(tile_cm=TILE, size=N, clods=len(sizes), clod_across_cm=[round(float(sizes.min()), 2), round(float(np.median(sizes)), 2), round(float(sizes.max()), 2)],
                 clod_height_cm=[round(float(hs.min()), 2), round(float(hs.max()), 2)], clod_cover=round(float(COV.mean()), 4),
                 crumbs=len(csizes), crumb_across_cm=[round(float(csizes.min()), 2), round(float(csizes.max()), 2)],
                 crumb_cover=round(float(CCOV.mean()), 4), gap_cover=round(float(gap.mean()), 4),
                 slurry_cover=round(float(slurry.mean()), 4), height_range_cm=[round(hmin, 3), round(hmax, 3)],
                 value_scale=round(scale, 4), clay_lstar=round(clay_l, 3), churn_lstar=round(float(lstar(col).mean()), 3),
                 coherence_colour=round(coherence(lum), 4), coherence_height=round(coherence(H01), 4))
    if stones:
        stats.update(stones=stones['count'], stone_across_cm=stones['across'], stone_cover_visible=round(float(stone_w.mean()), 4))
    stats.update(variant=VARIANT)
    say('fields: %s' % json.dumps(stats))
    return stats


# ---------------------------------------------------------------- checks on renders
def landmarks(path):
    """The centre tile of a 3x3 render: 30 cm window mean luminance and contrast, their largest |z| and the share over 3."""
    a = read_png(path)[..., :3]
    lum = a @ np.array([.2126, .7152, .0722])
    t = lum.shape[1] // 3
    tile = lum[t:2 * t, t:2 * t]
    k = int(round(t * .1))

    def box(x):
        p = np.pad(x, ((0, k), (0, k)), mode='wrap')
        s = np.pad(np.cumsum(np.cumsum(p, 0), 1), ((1, 0), (1, 0)))
        n = x.shape[0]
        return (s[k:k + n, k:k + n] - s[:n, k:k + n] - s[k:k + n, :n] + s[:n, :n]) / k / k
    m = box(tile)
    sd = np.sqrt(np.maximum(box(tile ** 2) - m * m, 0))
    out = {}
    for name, f in [('mean', m), ('contrast', sd)]:
        z = (f - f.mean()) / f.std()
        out[name] = dict(max_abs_z=round(float(np.abs(z).max()), 2), share_over_3=round(float((np.abs(z) > 3).mean() * 100), 2))
    return out


def band_metrics(img_path, mask_path):
    """Crosswise banding in the driver view: over the churn's pixels and, for reference, the approved clay's at the same
    distances, the energy of the vertical gradient over the horizontal one (crosswise bands push it up; plain
    foreshortening does too, which is why the clay is the reference). Rows from the top of a 1440 x 900 frame, scaled."""
    a = read_png(img_path)[::-1, :, :3]
    m = read_png(mask_path)[::-1]
    lum = a @ np.array([.2126, .7152, .0722])
    gxv = np.zeros_like(lum)
    gyv = np.zeros_like(lum)
    gxv[:, 1:-1] = (lum[:, 2:] - lum[:, :-2]) * .5
    gyv[1:-1, :] = (lum[2:, :] - lum[:-2, :]) * .5
    churn = m[..., 0] > .9
    clay = (m[..., 1] > .5) & (m[..., 0] < .02)
    for _ in range(3):
        for sel in (churn, clay):
            sel &= np.roll(sel, 1, 0) & np.roll(sel, -1, 0) & np.roll(sel, 1, 1) & np.roll(sel, -1, 1)
    hgt = lum.shape[0] / 900.0
    out = {}
    for zone, (r0, r1) in [('far_445_520', (445, 520)), ('mid_520_620', (520, 620)), ('near_620_900', (620, 900))]:
        rows = np.zeros(lum.shape, bool)
        rows[int(r0 * hgt):int(r1 * hgt)] = True
        row = {}
        for name, sel in [('churn', churn & rows), ('clay', clay & rows)]:
            ex, ey = float((gxv[sel] ** 2).sum()), float((gyv[sel] ** 2).sum())
            row[name] = dict(pixels=int(sel.sum()), vertical_over_horizontal=round(ey / max(ex, 1e-12), 3),
                             contrast=round(float(lum[sel].std()) if sel.any() else 0.0, 4))
        row['churn_over_clay'] = round(row['churn']['vertical_over_horizontal'] / max(row['clay']['vertical_over_horizontal'], 1e-9), 3)
        # Crosswise bands directly: per rut (left / right half of the frame) and per image row, the mean luminance of
        # the churn's pixels on that row, less its running mean over 13 rows; the residual's spread over the zone's
        # mean luminance. Lines across the rut make rows differ; scattered lumps average out along a row.
        def row_index(sel):
            vals = []
            for half in (slice(0, lum.shape[1] // 2), slice(lum.shape[1] // 2, lum.shape[1])):
                ss = sel[:, half]
                ll = lum[:, half]
                n = ss.sum(1)
                ok = n >= 8
                means = np.where(ok, (ll * ss).sum(1) / np.maximum(n, 1), np.nan)
                idx = np.where(ok)[0]
                if len(idx) < 15:
                    continue
                m = means[idx]
                k = 6
                pad = np.concatenate([m[:k][::-1], m, m[-k:][::-1]])
                run = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), 'valid')
                vals.append(float(np.std(m - run) / max(np.mean(m), 1e-9)))
            return round(float(np.mean(vals)), 4) if vals else None
        row['churn']['row_band_index'] = row_index(churn & rows)
        row['clay']['row_band_index'] = row_index(clay & rows)
        out[zone] = row
    return out


# ---------------------------------------------------------------- the node group and materials
def nodes_for(tree):
    ns, ls = tree.nodes, tree.links

    def node(kind, label=''):
        n = ns.new(kind)
        n.label = label
        return n

    def wire(value, socket):
        if isinstance(value, (int, float, tuple, list)):
            socket.default_value = value
        else:
            ls.new(value, socket)

    def mathop(op, a, b=0):
        n = node('ShaderNodeMath', op)
        n.operation = op
        wire(a, n.inputs[0])
        wire(b, n.inputs[1])
        return n.outputs[0]

    def mix(a, b, f, blend='MIX'):
        n = node('ShaderNodeMixRGB', 'Paint blend')
        n.blend_type = blend
        wire(f, n.inputs[0])
        wire(a, n.inputs[1])
        wire(b, n.inputs[2])
        return n.outputs[0]

    def smooth(value, a, b, lo=0.0, hi=1.0):
        n = node('ShaderNodeMapRange', 'Smoothstep')
        n.interpolation_type = 'SMOOTHSTEP'
        wire(value, n.inputs['Value'])
        wire(a, n.inputs['From Min'])
        wire(b, n.inputs['From Max'])
        wire(lo, n.inputs['To Min'])
        wire(hi, n.inputs['To Max'])
        return n.outputs[0]
    return node, wire, mathop, mix, smooth


def build_group(stats, paint, shape):
    ng = bpy.data.node_groups.new('NG_MW_Churn', 'ShaderNodeTree')
    ng.interface.new_socket('Vector', in_out='INPUT', socket_type='NodeSocketVector')
    for name, typ in [('Color', 'NodeSocketColor'), ('Roughness', 'NodeSocketFloat'), ('Height', 'NodeSocketFloat'),
                      ('Normal', 'NodeSocketVector'), ('Crumbs', 'NodeSocketFloat')]:
        ng.interface.new_socket(name, in_out='OUTPUT', socket_type=typ)
    node, wire, mathop, mix, smooth = nodes_for(ng)
    gi = node('NodeGroupInput')
    go = node('NodeGroupOutput')
    tex = {}
    for im, label in [(paint, 'Painted colour, linear (3 m tile)'), (shape, 'Height / roughness / crumbs (3 m tile)')]:
        t = node('ShaderNodeTexImage', label)
        t.image = im
        t.interpolation = 'Linear'
        t.extension = 'REPEAT'
        wire(gi.outputs['Vector'], t.inputs['Vector'])
        tex[label] = t
    sep = node('ShaderNodeSeparateColor')
    wire(tex['Height / roughness / crumbs (3 m tile)'].outputs['Color'], sep.inputs[0])
    height, rough, crumbs = sep.outputs[:3]
    bump = node('ShaderNodeBump', 'Churn relief (height map)')
    bump.inputs['Strength'].default_value = HEIGHT_BUMP
    bump.inputs['Distance'].default_value = (stats['height_range_cm'][1] - stats['height_range_cm'][0]) / 100.0
    wire(height, bump.inputs['Height'])
    wire(tex['Painted colour, linear (3 m tile)'].outputs['Color'], go.inputs['Color'])
    wire(rough, go.inputs['Roughness'])
    wire(height, go.inputs['Height'])
    wire(bump.outputs[0], go.inputs['Normal'])
    wire(crumbs, go.inputs['Crumbs'])
    return ng


def churn_material(name, ng, coords):
    """A principled material painted by the group; coords 'uv' (UVMap in 3 m units) or 'world' (position / 3 m)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    node, wire, mathop, mix, smooth = nodes_for(m.node_tree)
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    g = node('ShaderNodeGroup', 'Wet churn')
    g.node_tree = ng
    if coords == 'uv':
        uv = node('ShaderNodeUVMap')
        uv.uv_map = 'UVMap'
        wire(uv.outputs[0], g.inputs['Vector'])
    else:
        geo = node('ShaderNodeNewGeometry')
        sc = node('ShaderNodeVectorMath')
        sc.operation = 'SCALE'
        wire(geo.outputs['Position'], sc.inputs[0])
        sc.inputs['Scale'].default_value = 1 / 3.0
        wire(sc.outputs[0], g.inputs['Vector'])
    wire(g.outputs['Color'], p.inputs['Base Color'])
    wire(g.outputs['Roughness'], p.inputs['Roughness'])
    wire(g.outputs['Normal'], p.inputs['Normal'])
    p.inputs['Specular IOR Level'].default_value = .5
    return m


def load_field(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = 'Non-Color'
    im.alpha_mode = 'CHANNEL_PACKED'
    return im


def tile_scene(scene, mat, res, samples):
    """A flat 9 m plane of the churn alone, top-down orthographic, the study's sun and sky: the 3x3 repeat check."""
    sc = bpy.data.scenes.new('ChurnTile3x3')
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 4
    sc.world = scene.world
    sc.view_settings.view_transform = scene.view_settings.view_transform
    sc.view_settings.look = scene.view_settings.look
    sc.view_settings.exposure = scene.view_settings.exposure
    sc.render.resolution_x = sc.render.resolution_y = res
    me = bpy.data.meshes.new('Churn 3x3 plane')
    me.from_pydata([(-4.5, -4.5, 0), (4.5, -4.5, 0), (4.5, 4.5, 0), (-4.5, 4.5, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        v = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((v.x + 4.5) / 3, (v.y + 4.5) / 3)
    me.materials.append(mat)
    ob = bpy.data.objects.new('Churn 3x3 plane', me)
    sc.collection.objects.link(ob)
    sun = bpy.data.objects['Directional daylight'].copy()
    sc.collection.objects.link(sun)
    cd = bpy.data.cameras.new('Tile3x3')
    cd.type = 'ORTHO'
    cd.ortho_scale = 9.0
    cam = bpy.data.objects.new('Tile3x3', cd)
    cam.location = (0, 0, 10)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return sc


def tile_close(sc, res, samples):
    """The same plane from 1.5 m wide (a close look at the clods, crumbs and slurry)."""
    at = next((tuple(float(v) for v in a[6:].split(',')) for a in ARGS if a.startswith('close=')), (.6, -.4))
    sc.camera.data.ortho_scale = 1.5
    sc.camera.location = (at[0], at[1], 10)
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.cycles.samples = samples


def render_mask(scene, path, res_pct):
    """The driver view with every surface replaced by an emission: R the churn mask, G the mud coverage (the ground only),
    for band_metrics. Restores the scene afterwards."""
    mm = bpy.data.materials.new('MW_MaskOverride')
    mm.use_nodes = True
    nt = mm.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    a1 = nt.nodes.new('ShaderNodeAttribute')
    a1.attribute_name = 'ChurnMask'
    a2 = nt.nodes.new('ShaderNodeAttribute')
    a2.attribute_name = 'MudMasks'
    s1 = nt.nodes.new('ShaderNodeSeparateColor')
    s2 = nt.nodes.new('ShaderNodeSeparateColor')
    cc = nt.nodes.new('ShaderNodeCombineColor')
    em = nt.nodes.new('ShaderNodeEmission')
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(a1.outputs['Color'], s1.inputs[0])
    nt.links.new(a2.outputs['Color'], s2.inputs[0])
    nt.links.new(s1.outputs[0], cc.inputs[0])
    nt.links.new(s2.outputs[0], cc.inputs[1])
    nt.links.new(cc.outputs[0], em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    vl = bpy.context.view_layer
    saved = (scene.view_settings.view_transform, scene.view_settings.look, scene.cycles.samples, scene.render.film_transparent,
             scene.render.resolution_percentage, scene.cycles.use_denoising)
    vl.material_override = mm
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.cycles.samples = 4
    scene.cycles.use_denoising = False
    scene.render.film_transparent = True
    scene.render.resolution_percentage = res_pct
    scene.camera = bpy.data.objects['Driver']
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True, scene=scene.name)
    vl.material_override = None
    (scene.view_settings.view_transform, scene.view_settings.look, scene.cycles.samples, scene.render.film_transparent,
     scene.render.resolution_percentage, scene.cycles.use_denoising) = saved


def far_gloss_variant(scene, name='Driver_FarGlossFade.png'):
    """The far gloss fade (not in the bakes; a live-material switch in LM5b phase B): the churn's gloss fades to 0.65
    between 6 and 12 m from the camera (the far ruts' crosswise sheen bands are the sky in glossy slurry over the rut's
    undulations; see docs/MUD_WET_STUDY.md). Renders the driver view with it and returns its band numbers."""
    mat = bpy.data.materials['M_MW_ClayAndChurn']
    node, wire, mathop, mix, smooth_n = nodes_for(mat.node_tree)
    g = next(n for n in mat.node_tree.nodes if n.type == 'GROUP' and n.node_tree and n.node_tree.name == 'NG_MW_Churn')
    link = next(l for l in mat.node_tree.links if l.from_node == g and l.from_socket.name == 'Roughness')
    target = link.to_socket
    mat.node_tree.links.remove(link)
    cam = node('ShaderNodeCameraData', 'View distance')
    fade = smooth_n(cam.outputs['View Distance'], 6.0, 12.0)
    wire(mix(g.outputs['Roughness'], (.65, .65, .65, 1), mathop('MULTIPLY', fade, mathop('LESS_THAN', g.outputs['Roughness'], .65))), target)
    scene.camera = bpy.data.objects['Driver']
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True, scene=scene.name)
    say('rendered %s (with the far gloss fade)' % name)
    return band_metrics(OUT / name, OUT / 'Driver_ChurnMask.png')


def main():
    stats = build_fields()
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Art/Export/MudStyleStudy/03/MudStyleStudy.blend'))
    scene = bpy.context.scene
    # 03's terrain functions, read from the generators (never edited), for the churn mask and the close camera.
    for path, names in [('Art/Blender/build_road_ford_style.py', ['center', 'channel', 'smooth', 'noise', 'edge', 'h']),
                        ('Art/Blender/build_gravel_road_study.py', ['gravel_relief']),
                        ('Art/Blender/build_mud_style_study.py', ['lanes', 'masks', 'delta', 'height'])]:
        tree = ast.parse((ROOT / path).read_text())
        exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[]), path, 'exec'), globals())

    def churn(s, t):
        """Churn presence: 1 in the ruts, decaying over the banks (as the field's capsule and band will write it)."""
        mud = masks(s, t)[0]
        return mud * max(smooth(.68, .30, abs(t - lane) + .07 * noise(s, t, .9)) for lane in lanes(s))

    def cover(s, t):
        """Where the churn / bog is painted: A2's ruts, or (LM5b) the whole mud patch, ruts and all."""
        return churn(s, t) if COVERAGE == 'ruts' else masks(s, t)[0]
    paint = load_field(FIELDS / 'F_Paint.png')
    shape = load_field(FIELDS / 'F_Shape.png')
    ng = build_group(stats, paint, shape)
    # The ground: 03's painted clay, with the churn over it by ChurnMask x a 30-80 cm breakup (a ragged edge, not a line).
    mat = bpy.data.materials['M_MS_PaintedMud'].copy()
    mat.name = 'M_MW_ClayAndChurn'
    node, wire, mathop, mix, smooth_n = nodes_for(mat.node_tree)
    p = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    old_color = p.inputs['Base Color'].links[0].from_socket
    old_rough = p.inputs['Roughness'].links[0].from_socket
    old_normal = p.inputs['Normal'].links[0].from_socket
    uvn = node('ShaderNodeUVMap', 'Churn tile (UVMap = 3 m)')
    uvn.uv_map = 'UVMap'
    g = node('ShaderNodeGroup', 'Wet churn')
    g.node_tree = ng
    wire(uvn.outputs[0], g.inputs['Vector'])
    attr = node('ShaderNodeVertexColor', 'Churn presence')
    attr.layer_name = 'ChurnMask' if COVERAGE == 'ruts' else 'BogMask'
    sep = node('ShaderNodeSeparateColor')
    wire(attr.outputs['Color'], sep.inputs[0])
    metres = node('ShaderNodeVectorMath')
    metres.operation = 'SCALE'
    wire(uvn.outputs[0], metres.inputs[0])
    metres.inputs['Scale'].default_value = 3
    brk = node('ShaderNodeTexNoise', 'Churn edge breakup (30-80 cm)')
    brk.inputs['Scale'].default_value = 1.8
    brk.inputs['Detail'].default_value = 2
    wire(metres.outputs[0], brk.inputs['Vector'])
    b = smooth_n(brk.outputs['Fac'], .3, .7)
    centre = mathop('ADD', .15, mathop('MULTIPLY', b, .55))
    M = smooth_n(sep.outputs[0], mathop('SUBTRACT', centre, .12), mathop('ADD', centre, .12))
    wire(mix(old_color, g.outputs['Color'], M), p.inputs['Base Color'])
    wire(mix(old_rough, g.outputs['Roughness'], M), p.inputs['Roughness'])
    wire(mix(old_normal, g.outputs['Normal'], M), p.inputs['Normal'])
    churn_cover = []
    for ob in scene.objects:
        if ob.type != 'MESH' or not ob.name.startswith(('SM_RF_DryRoad', 'SM_RF_GravelVerge', 'SM_RF_Bank')):
            continue
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        ca = ob.data.color_attributes.new(name='ChurnMask', type='FLOAT_COLOR', domain='CORNER')
        per_vertex = [churn(v.co.x, v.co.y - center(v.co.x)) for v in ob.data.vertices]
        for loop in ob.data.loops:
            c = per_vertex[loop.vertex_index]
            ca.data[loop.index].color = (c, c, c, 1)
        churn_cover.append(sum(1 for c in per_vertex if c > .5))
        if COVERAGE == 'mud':
            bm = ob.data.color_attributes.new(name='BogMask', type='FLOAT_COLOR', domain='CORNER')
            per_vertex = [cover(v.co.x, v.co.y - center(v.co.x)) for v in ob.data.vertices]
            for loop in ob.data.loops:
                c = per_vertex[loop.vertex_index]
                bm.data[loop.index].color = (c, c, c, 1)
    # Clods on churned ground take the churn (as a thrown clod will); the rest keep 03's clay.
    clod_mat = churn_material('M_MW_ChurnClod', ng, 'world')
    churned_clods = clay_clods = buried = 0
    for ob in list(scene.objects):
        if ob.name.startswith('Displaced mud clod'):
            s = ob.location.x
            t = ob.location.y - center(s)
            if cover(s, t) > .5:
                ob.material_slots[0].link = 'OBJECT'
                ob.material_slots[0].material = clod_mat
                churned_clods += 1
            else:
                clay_clods += 1
        elif ob.name.startswith('Loose gravel') and not ob.hide_render:
            s = ob.location.x
            t = ob.location.y - center(s)
            if cover(s, t) > .55:
                ob.hide_render = True
                buried += 1
    # A close camera over lane 1: the centre strip's clay at the bottom right, the inner bank, the rut, the outer bank.
    s0 = 14.8
    t1 = lanes(s0)[1]
    target = Vector((s0 + .3, center(s0 + .3) + t1, height(s0 + .3, t1)))
    cd = bpy.data.cameras.new('ChurnClose')
    cd.lens = 30
    cam = bpy.data.objects.new('ChurnClose', cd)
    cam.location = Vector((s0 - .75, center(s0 - .75) + .05, height(s0 - .75, .05) + 1.0))
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(cam)
    flat = churn_material('M_MW_ChurnFlat', ng, 'uv')
    tile = tile_scene(scene, flat, 1800, 40)
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 40
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    for im in (paint, shape):
        im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'MudWetStudy.blend'))
    (OUT / 'source').mkdir(exist_ok=True)
    (OUT / 'source' / Path(__file__).name).write_text(Path(__file__).read_text())
    prefix = 'Quick_' if QUICK else ''
    checks = {}
    if QUICK:
        tile.cycles.samples = 16
        tile.render.resolution_x = tile.render.resolution_y = 1080
        tile.render.filepath = str(OUT / 'Quick_Tile3x3.png')
        bpy.ops.render.render(write_still=True, scene=tile.name)
        tile_close(tile, 900, 24)
        tile.render.filepath = str(OUT / 'Quick_TileClose.png')
        bpy.ops.render.render(write_still=True, scene=tile.name)
        scene.cycles.samples = 24
        scene.render.resolution_percentage = 50
        scene.camera = bpy.data.objects['Driver']
        scene.render.filepath = str(OUT / 'Quick_Driver.png')
        bpy.ops.render.render(write_still=True, scene=scene.name)
        render_mask(scene, OUT / 'Quick_Driver_ChurnMask.png', 50)
        checks['tile3x3_landmarks_30cm'] = landmarks(OUT / 'Quick_Tile3x3.png')
        checks['driver_bands'] = band_metrics(OUT / 'Quick_Driver.png', OUT / 'Quick_Driver_ChurnMask.png')
        say('checks %s' % json.dumps(checks))
        print('MUD_WET_QUICK_OK', flush=True)
        return
    say('scene saved; rendering')
    a2 = arg('renders', 'variant') == 'a2'          # phase A2's set (04_wet); otherwise LM5b's per-variant set
    for name in ['ChurnClose', 'Driver', 'SurfaceDetail'] if a2 else ['ChurnClose']:
        scene.camera = bpy.data.objects[name]
        scene.render.filepath = str(OUT / (name + '.png'))
        bpy.ops.render.render(write_still=True, scene=scene.name)
        say('rendered ' + name)
    render_mask(scene, OUT / 'Driver_ChurnMask.png', 100)
    tile.render.filepath = str(OUT / 'Tile3x3.png')
    bpy.ops.render.render(write_still=True, scene=tile.name)
    say('rendered Tile3x3')
    tile_close(tile, 1200, 40)
    tile.render.filepath = str(OUT / 'TileClose.png')
    bpy.ops.render.render(write_still=True, scene=tile.name)
    say('rendered TileClose')
    checks['tile3x3_landmarks_30cm'] = landmarks(OUT / 'Tile3x3.png')
    if a2:
        checks['driver_bands'] = band_metrics(OUT / 'Driver.png', OUT / 'Driver_ChurnMask.png')
        checks['driver_far_gloss_fade_candidate_bands'] = far_gloss_variant(scene)
        renders = ['Driver.png', 'SurfaceDetail.png', 'ChurnClose.png', 'Tile3x3.png', 'TileClose.png', 'Driver_ChurnMask.png', 'Driver_FarGlossFade.png (candidate)']
    else:
        checks['driver_bands_with_far_gloss_fade'] = far_gloss_variant(scene, 'Driver.png')
        renders = ['Driver.png (with the far gloss fade)', 'ChurnClose.png', 'Tile3x3.png', 'TileClose.png', 'Driver_ChurnMask.png']
    say('checks %s' % json.dumps(checks))
    manifest = dict(status='Static Blender art study (LM5 phase A2 / LM5b phase A); no Unreal, no field or physics change',
                    variant=VARIANT, coverage=COVERAGE, parameters={k: v for k, v in V.items()},
                    source='MudStyleStudy/03 scene and clay; churn fields generated here', fields=stats, checks=checks,
                    umbers_linear_before_scale=UMBERS, slurry_linear_before_scale=SLURRY, gap_linear_before_scale=GAP,
                    roughness=dict(slurry=SLURRY_ROUGH, gap=GAP_ROUGH, clod_sides_tops=CLOD_ROUGH, crumbs=CRUMB_ROUGH),
                    ground_vertices_churned=churn_cover, clods_churned=churned_clods, clods_clay=clay_clods,
                    stones_buried_in_churn=buried, renders=renders)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print('MUD_WET_STUDY_OK', flush=True)


if __name__ == '__main__':
    main()
