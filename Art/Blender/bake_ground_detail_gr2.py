"""Ground relief GR2 phase A (docs/GROUND_RELIEF_PLAN.md GR2): the ground bakes and the scatter meshes, headless Blender, look-gated
by the main session before any Unreal work. Uncommitted until that look.

Bakes (numpy, every field periodic over the 2 m tile, 2048 px = 0.0977 cm a texel; no mirror, no Cycles bake needed): two sets,
  ScrubSoil      dry crumbly soil: small clods (power-law 0.6-6 cm, clustered, warped rims), short broken cracks (warped Voronoi
                 edges kept only where a crack-presence noise is high, so they never join into a mosaic), pebbles (0.4-2.2 cm, sparse),
                 fine dead-grass litter (1.5-5 cm strands at random orientations), all over a soft 6-40 cm undulation;
  SoilUnderGrass darker: root mats (random-walk fibres, dense in patches), more and darker litter, few clods, no cracks.
The palette is the strips' scrub layer (live_mud_style.GROUND_HLSL: linear lerp((.095,.08,.052), (.19,.145,.083), n)), painted
with randomly oriented dabs (bake_gravel_dg1.dab_field's construction, no dominant direction). Files per set (Art/Export/GroundDetailGR2):
  T_GD_<Set>Color   RGB 8-bit sRGB
  T_GD_<Set>Normal  RGB 8-bit DirectX (green NEG_Y), from the sharp height at the parallax depth
  T_GD_<Set>Height  grey 16-bit, the sharp height 0-1 (1 = PARALLAX_DEPTH_CM)
  T_GD_<Set>ORH     RGB 8-bit linear: R horizon AO (bake_gravel_orh.horizon_ao at the parallax depth, 6 cm reach), G roughness
                    (0.6-0.95), B the parallax height with soft rims (6 % of the range a texel, a 1-texel Gaussian, as gravel's)
Renders (Cycles CPU 32 samples denoised, AgX Medium High Contrast, study 04's world and sun, 1440 x 900):
  <Set>_3x3.png           a flat 6 m ground of the tile 3 x 3, the eye 1.7 m up (normal-mapped)
  <Set>_Displaced.png     the same view truly displaced by B x 1.5 cm (adaptive subdivision, 1 px dicing)
  Scatter_<Family>.png    each scatter family on the ScrubSoil ground, 0.9 m up
Scatter meshes (100-400 triangles each, the painterly palette, UVs by smart projection): 6 soil clods 3-12 cm, 4 pebbles 1-5 cm (the gravel
study's SM_GR_Stone1-4 re-tinted), 4 dead-grass litter tufts 10-25 cm (flat, bent), 3 twigs 15-40 cm, 3 tussock-base mounds 25-50 cm
across and 6-12 cm high (soil and root bumps); FBX each and GroundDetailScatter.blend. manifest.json holds every number.

Phase A2 (the plan's "Decisions after phase A"): the bakes, pebbles and twigs pass and are kept; the clods, litter and tussock
bases are redone (clod(), litter_mat(), tussock_base() say how) with a vertex colour 'Col'; the A1 renders of those families are
kept as Scatter_<Family>_A1.png; ScrubSoil_AntiTile.png previews phase B's two-sample macro blend over 20 m at 1.7 m (with
ScrubSoil_AntiTile_Single.png, the same view on one sample).

Run headless (Blender 5.1):
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 \
      --python Art/Blender/bake_ground_detail_gr2.py -- [stage=all|bake|mesh|render|a2|scatter|antitile] [families=Clods,Litter]
  bake = phase B item 0: A2's crack numbers measured, the two sets re-baked, both sets' anti-tile views rendered (A2's kept as *_A2.png).
  a2 = the meshes, then the redone families' renders and the anti-tile pair; scatter = only those family renders; antitile = only that.
"""
import bmesh
import bpy
import json
import math
import random
import shutil
import struct
import sys
import time
import zlib
from pathlib import Path

import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Art'))
import bake_gravel_orh as orh   # noqa: E402  (horizon_ao)

OUT = ROOT / 'Art/Export/GroundDetailGR2'
OUT.mkdir(parents=True, exist_ok=True)
STUDY = ROOT / 'Art/Export/GravelRoadStudy/04'
N = 2048
TILE_M = 2.0
TEXEL_CM = TILE_M * 100.0 / N
PARALLAX_DEPTH_CM = 1.5
PRE = 'T_GD_'
SETS = ['ScrubSoil', 'SoilUnderGrass']
SCRUB_DARK = np.array([.095, .08, .052])     # live_mud_style.GROUND_HLSL, linear
SCRUB_LIGHT = np.array([.19, .145, .083])
T0 = time.time()
ARGS = dict(a.split('=', 1) for a in sys.argv[sys.argv.index('--') + 1:] if '=' in a) if '--' in sys.argv else {}
STAGE = ARGS.get('stage', 'all')
A2_FAMILIES = ['Clods', 'Litter', 'TussockBases']     # redone in phase A2
# Phase B item 0 (docs/GROUND_RELIEF_PLAN.md GR2 phase B, 2026-10-10): the A2 anti-tile preview's faint diagonal rows of darker
# streaks are the crack network's dark paint. The cracks now read through height and normal: their colour darkening is 0.35 of
# A2's, 20 % of the tile keeps cracks (A2 36.5 %), the presence noise is finer (shorter runs) and no crack reaches within 1-2.5 cm of
# a Voronoi vertex (the runs no longer join at the cells' corners). The rng stream is A2's (same calls, same order), so the clods,
# pebbles, litter, colour wash and dabs are A2's exactly. CRACKS_A2 rebuilds A2's numbers for the report (stage=bake).
CRACKS_A2 = dict(darken=.35, presence_band_cm=(6, 30), presence_edges=(.55, .72), junction_gap_cm=None)
CRACKS = dict(darken=.35 * .35, presence_band_cm=(4, 18), presence_edges=(.74, .86), junction_gap_cm=(1.0, 2.5))


def say(msg):
    print('GROUND_GR2 %6.1f s  %s' % (time.time() - T0, msg), flush=True)


def rel(p):
    return str(Path(p).relative_to(ROOT)).replace('\\', '/')


def write_png(path, arr, bits):
    """bake_gravel_dg1.write_png: arr (h, w) or (h, w, 3), 0..1, row 0 = the bottom; written top row first."""
    a = np.clip(arr[::-1], 0, 1)
    h, w = a.shape[:2]
    kind = 2 if a.ndim == 3 else 0
    data = (a * 65535 + .5).astype('>u2') if bits == 16 else (a * 255 + .5).astype(np.uint8)
    rows = data.reshape(h, -1).view(np.uint8)
    raw = np.hstack([np.zeros((h, 1), np.uint8), rows]).tobytes()

    def chunk(k, payload):
        return struct.pack('>I', len(payload)) + k + payload + struct.pack('>I', zlib.crc32(k + payload) & 0xFFFFFFFF)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, bits, kind, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def linear_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= .0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - .055)


def gauss(a, sigma_px):
    k = np.hypot(np.fft.fftfreq(a.shape[0])[:, None], np.fft.rfftfreq(a.shape[1])[None, :])
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (math.pi * sigma_px * k) ** 2), s=a.shape)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def band_noise(rng, lo_cm, hi_cm):
    """Periodic noise: random phases on the frequencies whose wavelength lies in lo_cm..hi_cm, std 1."""
    fy = np.fft.fftfreq(N)[:, None]
    fx = np.fft.rfftfreq(N)[None, :]
    f = np.hypot(fx, fy) / TEXEL_CM     # cycles per cm
    lo_f, hi_f = 1.0 / hi_cm, 1.0 / lo_cm
    amp = np.where((f >= lo_f) & (f <= hi_f), 1.0 / np.maximum(f, 1e-6), 0.0)
    spec = amp * (rng.standard_normal(amp.shape) + 1j * rng.standard_normal(amp.shape))
    out = np.fft.irfft2(spec, s=(N, N))
    return (out - out.mean()) / max(out.std(), 1e-12)


def uniformise(a):
    """Rank-remap to about uniform 0..1."""
    r = np.empty(a.size)
    r[np.argsort(a, axis=None)] = np.linspace(0, 1, a.size)
    return r.reshape(a.shape)


def dab_field(rng, sigma_cm=(3.0, .55), bins=18, density=6):
    """bake_gravel_dg1.dab_field: paint dabs with no dominant direction (impulses convolved with turned anisotropic Gaussians)."""
    sl, sw = sigma_cm[0] / TEXEL_CM, sigma_cm[1] / TEXEL_CM
    count = int(density * (TILE_M * 100) ** 2 / (2 * math.pi * sigma_cm[0] * sigma_cm[1]))
    fy = np.fft.fftfreq(N)[:, None]
    fx = np.fft.rfftfreq(N)[None, :]
    acc = np.zeros((N, N // 2 + 1), complex)
    for b in range(bins):
        th = math.pi * (b + rng.random()) / bins
        k = count // bins
        imp = np.zeros((N, N))
        np.add.at(imp, (rng.integers(0, N, k), rng.integers(0, N, k)), rng.standard_normal(k))
        kl = fx * math.cos(th) + fy * math.sin(th)
        kw = -fx * math.sin(th) + fy * math.cos(th)
        acc += np.fft.rfft2(imp) * np.exp(-2 * math.pi ** 2 * (sl * sl * kl * kl + sw * sw * kw * kw))
    out = np.fft.irfft2(acc, s=(N, N))
    return out / max(out.std(), 1e-12)


def stamp(field, cx, cy, half_px, fn, mode='max'):
    """Apply fn(dx_cm, dy_cm) (offsets of the texel centres from (cx, cy) px) over a wrapped window into field (max or add)."""
    r = int(math.ceil(half_px))
    ix0, iy0 = int(math.floor(cx)), int(math.floor(cy))
    offs = np.arange(-r, r + 1)
    xs, ys = (ix0 + offs) % N, (iy0 + offs) % N
    dx = ((ix0 + offs) + .5 - cx) * TEXEL_CM
    dy = ((iy0 + offs) + .5 - cy) * TEXEL_CM
    val = fn(dx[None, :], dy[:, None])
    val = np.broadcast_to(val, (len(ys), len(xs)))
    sub = field[np.ix_(ys, xs)]
    field[np.ix_(ys, xs)] = np.maximum(sub, val) if mode == 'max' else sub + val
    return val


def blob_fn(rng, radius_cm, height, warp=.25, crest=.25, power=2.0):
    """An irregular soft dome: rim warped by three angular harmonics, crest off centre; (1 - u^2)^power."""
    k = [2 + rng.integers(0, 2), 3 + rng.integers(0, 3), 5 + rng.integers(0, 3)]
    ph = rng.random(3) * 2 * math.pi
    ca = rng.random() * 2 * math.pi
    co = crest * rng.random() * radius_cm
    ox, oy = co * math.cos(ca), co * math.sin(ca)

    def fn(dx, dy):
        qx, qy = dx - ox, dy - oy
        th = np.arctan2(qy, qx)
        w = (np.sin(k[0] * th + ph[0]) + .5 * np.sin(k[1] * th + ph[1]) + .25 * np.sin(k[2] * th + ph[2])) / 1.75
        rim = radius_cm * (1 + warp * w)
        u = np.hypot(qx, qy) / np.maximum(rim, 1e-3)
        return np.where(u < 1, height * np.clip(1 - u * u, 0, 1) ** power, 0.0)
    return fn


def scatter_points(rng, count, cluster, strength):
    """count points, accepted against a 0..1 cluster field raised to strength (clustered, irregular)."""
    pts = []
    while len(pts) < count:
        x, y = rng.random(2) * N
        if rng.random() < cluster[int(y) % N, int(x) % N] ** strength:
            pts.append((x, y))
    return pts


def strands(rng, field_h, colour_mask, count, len_cm, width_cm, height, cluster=None, strength=1.0, curl=.35):
    """Thin curved strands (litter or fibres) at random orientations: raised by height, painted into colour_mask."""
    pts = scatter_points(rng, count, cluster, strength) if cluster is not None else [tuple(rng.random(2) * N) for _ in range(count)]
    for x, y in pts:
        length = rng.uniform(*len_cm)
        segs = max(2, int(length / 1.2))
        th = rng.random() * 2 * math.pi
        px, py = x, y
        for _ in range(segs):
            th += rng.normal(0, curl)
            step = length / segs / TEXEL_CM
            nx, ny = px + step * math.cos(th), py + step * math.sin(th)
            w = rng.uniform(*width_cm)
            ax, ay = px, py
            bx, by = nx, ny
            cx, cy = .5 * (ax + bx), .5 * (ay + by)
            half = .5 * math.hypot(bx - ax, by - ay) + w / TEXEL_CM + 2

            def fn(dx, dy, ax=ax - cx, ay=ay - cy, bx=bx - cx, by=by - cy, w=w):
                # distance (cm) to the segment, the window's origin at the segment's middle
                ex, ey = (bx - ax) * TEXEL_CM, (by - ay) * TEXEL_CM
                l2 = max(ex * ex + ey * ey, 1e-9)
                t = np.clip(((dx - ax * TEXEL_CM) * ex + (dy - ay * TEXEL_CM) * ey) / l2, 0, 1)
                d = np.hypot(dx - ax * TEXEL_CM - t * ex, dy - ay * TEXEL_CM - t * ey)
                return np.clip(1 - d / w, 0, 1)
            cov = stamp(colour_mask, cx, cy, half, fn, 'max')
            stamp(field_h, cx, cy, half, lambda dx, dy, c=cov: c * height, 'max')
            px, py = nx, ny
    return len(pts)


def crack_runs(mask):
    """Phase B item 0: the crack mask's connected runs (8-connected, periodic): how many, and their extents (the longer side of each
    run's box, cm) - shorter and less connected than A2's."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    ys, xs = np.nonzero(mask)
    extents, sizes = [], []
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        seen[y0, x0] = True
        stack = [(y0, x0, y0, x0)]
        ymin = ymax = y0
        xmin = xmax = x0
        n = 0
        while stack:
            y, x, uy, ux = stack.pop()     # uy, ux: unwrapped
            n += 1
            ymin, ymax, xmin, xmax = min(ymin, uy), max(ymax, uy), min(xmin, ux), max(xmax, ux)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = (y + dy) % h, (x + dx) % w
                    if mask[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        stack.append((yy, xx, uy + dy, ux + dx))
        sizes.append(n)
        extents.append(max(ymax - ymin, xmax - xmin) + 1)
    if not extents:
        return dict(count=0)
    e = np.array(extents) * TEXEL_CM
    big = np.array(sizes) >= 20
    return dict(count=len(extents), count_20px=int(big.sum()), extent_cm_p50_p95_max=pct(e[big] if big.any() else e, [50, 95, 100]),
                pixels=int(sum(sizes)), largest_px=int(max(sizes)))


def voronoi_edges(rng, cell_cm, warp_cm, with_f3=False):
    """Periodic distance to the nearest Voronoi edge (F2 - F1, cm) on coordinates warped by a noise; with_f3, also F3 - F1 (small
    near a vertex, where three cells meet)."""
    cells = max(2, int(round(TILE_M * 100 / cell_cm)))
    size = TILE_M * 100 / cells
    jit = rng.random((cells, cells, 2))
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64) * TEXEL_CM
    wx = xx + warp_cm * band_noise(rng, cell_cm * .4, cell_cm * 1.5)
    wy = yy + warp_cm * band_noise(rng, cell_cm * .4, cell_cm * 1.5)
    gx, gy = np.floor(wx / size).astype(int), np.floor(wy / size).astype(int)
    f1 = np.full((N, N), 1e9)
    f2 = np.full((N, N), 1e9)
    f3 = np.full((N, N), 1e9)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            cx, cy = gx + ox, gy + oy
            j = jit[cy % cells, cx % cells]
            px, py = (cx + j[..., 0]) * size, (cy + j[..., 1]) * size
            d = np.hypot(wx - px, wy - py)
            f3 = np.where(d < f2, f2, np.minimum(f3, d))
            f2 = np.where(d < f1, f1, np.minimum(f2, d))
            f1 = np.minimum(f1, d)
    return (f2 - f1, f3 - f1) if with_f3 else f2 - f1


def soft_rims(h, slope=.06, sigma=1.0):
    """bake_gravel_orh.soft_rims with its own numbers (the slope capped by the mean of the two cone envelopes, then a Gaussian)."""
    steps = [((dy, dx), slope * math.hypot(dx, dy)) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]
    up, lo = h.copy(), h.copy()
    for _ in range(int(1.0 / slope) + 4):
        changed = False
        for (dy, dx), c in steps:
            nu = np.roll(up, shift=(dy, dx), axis=(0, 1)) - c
            nl = np.roll(lo, shift=(dy, dx), axis=(0, 1)) + c
            if (nu > up).any() or (nl < lo).any():
                changed = True
            np.maximum(up, nu, out=up)
            np.minimum(lo, nl, out=lo)
        if not changed:
            break
    return np.clip(gauss(.5 * (up + lo), sigma), 0, 1)


def coherence(a):
    """bake_gravel_dg1.coherence: (whole tile, mean over 10 cm) of the structure tensor's coherence; 0 no direction, 1 stripes."""
    ax = (np.roll(a, -1, 1) - np.roll(a, 1, 1)) * .5
    ay = (np.roll(a, -1, 0) - np.roll(a, 1, 0)) * .5
    jxx, jyy, jxy = ax * ax, ay * ay, ax * ay
    whole = math.hypot(jxx.mean() - jyy.mean(), 2 * jxy.mean()) / max(jxx.mean() + jyy.mean(), 1e-12)
    s = 10.0 / TEXEL_CM / 2.0
    lxx, lyy, lxy = gauss(jxx, s), gauss(jyy, s), gauss(jxy, s)
    local = np.hypot(lxx - lyy, 2 * lxy) / np.maximum(lxx + lyy, 1e-12)
    return round(float(whole), 4), round(float(local.mean()), 4)


def seam_ratio(img):
    inner = .5 * (np.mean(np.abs(np.diff(img, axis=0))) + np.mean(np.abs(np.diff(img, axis=1))))
    edge = .5 * (np.mean(np.abs(img[0, :] - img[-1, :])) + np.mean(np.abs(img[:, 0] - img[:, -1])))
    return round(float(edge / max(inner, 1e-12)), 3)


def pct(a, ps):
    return [round(float(x), 3) for x in np.percentile(a, ps)]


# ---------------------------------------------------------------- the two sets
def build_set(name, seed, cracks=CRACKS, write=True):
    rng = np.random.default_rng(seed)
    under = name == 'SoilUnderGrass'
    h = np.zeros((N, N))                         # cm, the sharp relief
    facts = {}
    # A soft undulation (6-40 cm), a few mm.
    h += .07 * band_noise(rng, 6, 40) + .04 * band_noise(rng, 2, 6)
    cluster = uniformise(band_noise(rng, 15, 60))
    # Clods: power-law radii, clustered, warped domes, combined by max (each crumb its own).
    clod_h = np.zeros((N, N))
    n_clods = 6000 if under else 22000
    rmin, rmax, alpha = .25, 3.0, 2.0
    for (x, y) in scatter_points(rng, n_clods, cluster, 1.2):
        r = rmin / (1 - rng.random() * (1 - (rmin / rmax) ** alpha)) ** (1 / alpha)
        height = r * rng.uniform(.35, .7) * (.6 if under else 1.0)
        stamp(clod_h, x, y, r * 1.3 / TEXEL_CM + 2, blob_fn(rng, r, height, warp=.22, crest=.3, power=1.3))
    h += clod_h
    facts['clods'] = dict(count=n_clods, radius_cm=[rmin, rmax], power=alpha, height_per_radius=[.35, .7])
    # Pebbles: few, harder domes (they get their own colour).
    peb = np.zeros((N, N))
    n_peb = 70 if under else 260
    for (x, y) in scatter_points(rng, n_peb, 1 - cluster, 1.0):
        r = rng.uniform(.2, 1.1)
        stamp(peb, x, y, r * 1.3 / TEXEL_CM + 2, blob_fn(rng, r, r * rng.uniform(.5, .8), warp=.08, crest=.15, power=.8))
    h = np.where(peb > 0, np.maximum(h, gauss(h, 2) + peb), h)
    facts['pebbles'] = dict(count=n_peb, diameter_cm=[.4, 2.2])
    # Cracks: warped Voronoi edges (cells 10-22 cm), kept only where a presence noise is high, so they break off irregularly.
    crack_mask = np.zeros((N, N))
    if not under:
        e, e3 = voronoi_edges(rng, 16.0, 4.0, with_f3=True)
        presence = smoothstep(*cracks['presence_edges'], uniformise(band_noise(rng, *cracks['presence_band_cm'])))
        width = .1 + .15 * uniformise(band_noise(rng, 3, 12))
        crack_mask = (1 - smoothstep(0, width, e)) * presence
        if cracks['junction_gap_cm']:
            crack_mask = crack_mask * smoothstep(*cracks['junction_gap_cm'], e3)
        h -= .45 * crack_mask * (.6 + .4 * uniformise(band_noise(rng, 2, 10)))
        facts['cracks'] = dict(cell_cm=16, warp_cm=4, kept_share=round(float((presence > .5).mean()), 3), depth_cm=.45,
                               colour_darken=round(cracks['darken'], 4), presence_band_cm=list(cracks['presence_band_cm']),
                               presence_edges=list(cracks['presence_edges']), junction_gap_cm=cracks['junction_gap_cm'],
                               runs=crack_runs(crack_mask > .3))
    # Litter (dead grass) and, under grass, root mats.
    litter = np.zeros((N, N))
    lit_h = np.zeros((N, N))
    n_lit = strands(rng, lit_h, litter, 4200 if under else 1300, (1.5, 4.5), (.08, .16), .18, curl=.12)
    h = h + lit_h
    facts['litter'] = dict(strands=n_lit, length_cm=[1.5, 4.5], width_cm=[.08, .16])
    roots = np.zeros((N, N))
    if under:
        root_h = np.zeros((N, N))
        n_roots = strands(rng, root_h, roots, 2400, (5.0, 15.0), (.05, .1), .12, cluster=cluster, strength=2.5, curl=.6)
        h = h + root_h
        facts['roots'] = dict(fibres=n_roots, length_cm=[5.0, 15.0], clustered=True)
    # The sharp height 0-1 over the parallax depth, and the soft-rimmed B.
    hs = h - np.percentile(h, .5)
    h01 = np.clip(hs / PARALLAX_DEPTH_CM, 0, 1)
    b = soft_rims(h01)
    # Colour: the scrub palette painted (a broad wash, dabs), clod tops lighter, cracks and hollows darker, pebbles greyer, litter straw.
    wash = uniformise(.7 * band_noise(rng, 20, 80) + .3 * band_noise(rng, 5, 20))
    dabs = dab_field(rng)
    clod01 = smoothstep(0, .6, clod_h / PARALLAX_DEPTH_CM)
    t = np.clip(.12 + .6 * wash + .14 * dabs + .35 * (clod01 - .35), 0, 1)
    col = SCRUB_DARK[None, None, :] + (SCRUB_LIGHT - SCRUB_DARK)[None, None, :] * t[..., None]
    if under:
        col *= .62
    col *= (1 - cracks['darken'] * crack_mask)[..., None]
    pebble_c = np.array([.17, .148, .112]) * (.85 + .3 * uniformise(band_noise(rng, 1, 4)))[..., None]
    col = np.where((peb > .05)[..., None], pebble_c, col)
    straw = np.array([.32, .25, .13]) * (.55 if under else 1.0)
    col = col * (1 - litter[..., None]) + straw * (.8 + .4 * dabs[..., None] * .2) * litter[..., None]
    if under:
        root_c = np.array([.07, .05, .032])
        col = col * (1 - roots[..., None]) + root_c * roots[..., None]
    # Roughness 0.6-0.95: soil 0.9-0.95, pebbles ~0.72, litter ~0.8, under grass lower (damper).
    rough = .92 + .03 * uniformise(band_noise(rng, 2, 20)) - .2 * (peb > .05) - .12 * litter
    if under:
        rough = rough - .12 - .08 * roots
    rough = np.clip(rough, .6, .95)
    # Normal (DirectX: green = dh / drow, row 0 the bottom) from the sharp height in cm; AO from it at the parallax depth.
    hc = h01 * PARALLAX_DEPTH_CM
    dx = (np.roll(hc, -1, 1) - np.roll(hc, 1, 1)) / (2 * TEXEL_CM)
    dy = (np.roll(hc, -1, 0) - np.roll(hc, 1, 0)) / (2 * TEXEL_CM)
    n = np.stack([-dx, dy, np.ones_like(dx)], -1)     # x: -dh/du; DirectX green: +dh/drow (= -(-dh/dv))
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    ao = orh.horizon_ao(hc, TEXEL_CM)
    col = col * (.7 + .3 * ao)[..., None]      # the cavities a little darker in the albedo (the painterly bakes' habit)
    lum = .2126 * col[..., 0] + .7152 * col[..., 1] + .0722 * col[..., 2]
    # Phase B item 0's numbers: how much darker the crack pixels are than the rest (and the AO term's part of it), what survives
    # minification (the 4 cm blur's contrast, the mid-distance read); under grass, the root fibres' darkness.
    cr, away = crack_mask > .3, crack_mask < .02
    aot = .7 + .3 * ao
    blur = gauss(lum, 4.0 / TEXEL_CM)
    facts['darkening'] = dict(crack_lum_ratio=round(float(lum[cr].mean() / lum[away].mean()), 4) if cr.any() else None,
                              crack_ao_only_ratio=round(float(aot[cr].mean() / aot[away].mean()), 4) if cr.any() else None,
                              blur4cm_contrast=round(float(blur.std() / blur.mean()), 4),
                              root_lum_ratio=round(float(lum[roots > .3].mean() / lum[roots < .02].mean()), 4) if (roots > .3).any() else None)
    if not write:
        return facts
    files = {}
    write_png(OUT / (PRE + name + 'Color.png'), linear_to_srgb(col), 8)
    write_png(OUT / (PRE + name + 'Normal.png'), .5 + .5 * n, 8)
    write_png(OUT / (PRE + name + 'Height.png'), h01, 16)
    write_png(OUT / (PRE + name + 'ORH.png'), np.stack([ao, rough, b], -1), 8)
    for k in ('Color', 'Normal', 'Height', 'ORH'):
        files[k] = rel(OUT / (PRE + name + k + '.png'))
    facts.update(files=files, size=N, texel_cm=round(TEXEL_CM, 4), parallax_depth_cm=PARALLAX_DEPTH_CM,
                 seams=dict(colour=seam_ratio(lum), height=seam_ratio(h01), b=seam_ratio(b)),
                 coherence=dict(height=coherence(h01), colour=coherence(lum)),
                 roughness_p5_50_95=pct(rough, [5, 50, 95]), ao_mean=round(float(ao.mean()), 3), ao_p5=pct(ao, [5])[0],
                 b_p5_50_95_max=pct(b, [5, 50, 95, 100]), height_p50_95=pct(h01, [50, 95]),
                 colour_mean_linear=[round(float(col[..., i].mean()), 4) for i in range(3)], luminance_mean=round(float(lum.mean()), 4),
                 litter_cover=round(float((litter > .3).mean()), 4), crack_cover=round(float((crack_mask > .3).mean()), 4),
                 pebble_cover=round(float((peb > .05).mean()), 4), root_cover=round(float((roots > .3).mean()), 4))
    say('baked %s: %s' % (name, json.dumps(facts['coherence'])))
    return facts


# ---------------------------------------------------------------- scatter meshes
def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def finish_mesh(bm, name, size_note):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.02)
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as e:   # noqa: BLE001
        say('smart project failed on %s: %s' % (name, e))
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:    # noqa: BLE001
            pass
    return ob


def a1_rng_for_twigs():
    """Phase A drew its clods and litter tufts from one stream before the twigs. A2 redoes those families from their own streams;
    replaying A1's draws here (same calls, same order) keeps the twigs, which pass, identical."""
    rng = np.random.default_rng(20261010)
    for _ in range(6):           # A1 clod(): noise3's 9 phases, the 3 axis scales, a normal per icosphere vertex (162)
        rng.random(9)
        rng.uniform(.8, 1.2), rng.uniform(.7, 1.0), rng.uniform(.45, .7)
        for _ in range(162):
            rng.normal()
    for _ in range(4):           # A1 litter_tuft(): the blade count, then 5 draws a blade
        for _ in range(int(rng.integers(8, 13))):
            rng.uniform(.55, 1.0), rng.uniform(.003, .006), rng.random(), rng.uniform(.005, .02), rng.normal(0, .5)
    return rng


def hull_piece(bm, pts):
    """A convex hull of the points (n, 3) as one closed piece; returns [(point index, vert)] of the hull's verts and its faces."""
    vs = [bm.verts.new(Vector([float(c) for c in p])) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    faces = [g for g in res['geom'] if isinstance(g, bmesh.types.BMFace)]
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    loose = [v for v in vs if not v.link_faces]
    used = [(i, v) for i, v in enumerate(vs) if v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    return used, faces


def paint(faces, cl, rgb):
    for f in faces:
        for lp in f.loops:
            lp[cl] = (float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0)


def crumb(bm, cl, rng, x, y, size_m, sink):
    """A small broken crumb: a hull of 7 points, flattened, sunk by `sink` of its height. About 10 triangles."""
    h = size_m * rng.uniform(.5, .8)
    d = rng.normal(size=(7, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    pts = d * np.array([size_m / 2, size_m / 2 * rng.uniform(.6, 1.0), h / 2]) * rng.uniform(.7, 1.0, (7, 1))
    pts += np.array([x, y, h * (.5 - sink)])
    _, faces = hull_piece(bm, pts)
    paint(faces, cl, [rng.uniform(.82, 1.08)] * 3)
    return faces


def clod(rng, name, size_cm):
    """A2 clod (plan: torn and crumbly, broken facets, crumb satellites, height 0.4-0.7 of the width, sunk 25-40 %).
    An aggregate, not one lump: a small core (the convex hull of 22 + size_cm points at 0.75-1.0 of an ellipsoid, y 0.6-0.95 of x,
    its verts then dented in or out by 10 %) with 8 + size_cm crumbs stuck into it (each the hull of 8 points, 22-42 % of the
    core's radius, centred at 0.6-0.95 of its radius, mostly on the upper half), so the surface is a cluster of small lumps with
    concave seams between them. 2-3 fracture planes cut the whole aggregate (every piece's points past a plane are pressed onto
    it), so flat broken faces run across core and crumbs alike, mostly steep or tilted, a little darker in the vertex colour; a
    crumb more than half cut away is dropped (no slivers). Then 2-5 loose crumbs (8-20 % of the width) lie round the base, sunk 30-50 %. Every piece
    gets its own tone (0.9-1.08). Edges sharper than 55 degrees are hard. No subdivision (it rounds them back into potatoes).
    The material bumps the ScrubSoil height bake, box-projected (crumb texture)."""
    bm = bmesh.new()
    cl = bm.loops.layers.float_color.new('Col')
    ratio, sink = rng.uniform(.4, .7), rng.uniform(.25, .4)
    core_r = np.array([1.0, rng.uniform(.6, .95), 1.0])
    pieces = [('core', np.zeros(3), core_r, int(22 + size_cm), (.75, 1.0))]
    for _ in range(int(8 + size_cm)):
        d = rng.normal(size=3)
        d[2] = abs(d[2]) * .8 if rng.random() < .75 else -abs(d[2]) * .5
        d /= np.linalg.norm(d)
        r = rng.uniform(.22, .42)
        pieces.append(('crumb', d * core_r * rng.uniform(.6, .95), np.array([r, r * rng.uniform(.65, 1.0), r * rng.uniform(.6, .95)]), 8, (.7, 1.0)))
    planes = []
    for _ in range(int(rng.integers(2, 4))):
        th = rng.uniform(0, 2 * math.pi)
        nrm = np.array([math.cos(th), math.sin(th), rng.uniform(-.15, .9)])
        nrm /= np.linalg.norm(nrm)
        planes.append((nrm, (np.linalg.norm(core_r * nrm) + .25) * rng.uniform(.5, .8)))
    body, stuck = [], 0
    for kind, centre, radii, n, rf in pieces:
        d = rng.normal(size=(n, 3))
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        pts = centre + d * radii * rng.uniform(rf[0], rf[1], (n, 1))
        cut = np.zeros(n, bool)
        for nrm, reach in planes:
            over = pts @ nrm - reach
            m = over > 0
            pts[m] -= over[m, None] * nrm
            cut |= m
        if kind == 'crumb' and cut.sum() > n // 2:
            continue                                   # mostly cut away: it would be a thin sliver
        pts += rng.normal(0, .004, pts.shape)
        try:
            used, faces = hull_piece(bm, pts)
        except Exception as e:   # noqa: BLE001
            say('hull failed on a piece of %s: %s' % (name, e))
            continue
        on_cut = {v: bool(cut[i]) for i, v in used}
        stuck += kind == 'crumb'
        if kind == 'core':
            for i, v in used:
                if not cut[i]:
                    v.co = Vector(centre) + (v.co - Vector(centre)) * float(np.clip(1 + rng.normal(0, .1), .78, 1.1))
        tone = rng.uniform(.9, 1.08)
        for f in faces:
            facet = all(on_cut.get(v, False) for v in f.verts)
            paint([f], cl, (tone * .88, tone * .86, tone * .87) if facet else (tone, tone, tone))
        body += [v for _, v in used]
    # Fit: the widest plan extent = size_cm, the height = ratio x that, the bottom `sink` of the height below the ground.
    xs, ys, zs = ([v.co[k] for v in body] for k in range(3))
    w = size_cm / 100
    sxy = w / max(max(xs) - min(xs), max(ys) - min(ys))
    sz = ratio * w / (max(zs) - min(zs))
    cx, cy, z0 = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, min(zs)
    for v in body:
        v.co = Vector(((v.co.x - cx) * sxy, (v.co.y - cy) * sxy, (v.co.z - z0) * sz - sink * ratio * w))
    ex = (max(xs) - min(xs)) * sxy / 2
    ey = (max(ys) - min(ys)) * sxy / 2
    crumbs = int(rng.integers(2, 6))
    for _ in range(crumbs):
        a = rng.uniform(0, 2 * math.pi)
        s = max(.004, w * rng.uniform(.08, .2))
        rr = rng.uniform(.85, 1.3)
        crumb(bm, cl, rng, math.cos(a) * (ex * rr + s * .3), math.sin(a) * (ey * rr + s * .3), s, rng.uniform(.3, .5))
    ob = finish_mesh(bm, name, size_cm)
    try:
        ob.data.set_sharp_from_angle(angle=math.radians(55))
    except Exception as e:   # noqa: BLE001
        say('set_sharp_from_angle failed on %s: %s' % (name, e))
    ob['gd_recipe'] = json.dumps(dict(height_ratio=round(float(ratio), 3), sunk=round(float(sink), 3), stuck_crumbs=stuck,
                                      fracture_planes=len(planes), loose_crumbs=crumbs))
    return ob


def litter_mat(rng, name, length_cm):
    """A2 litter (plan: flattened mats of bent blades lying mostly one way per mat, irregular outline, 2-6 cm high, no radial
    symmetry). The mat lies along +x, its widest plan extent fitted to length_cm, 0.45-0.7 as wide. Blade roots lie along 2-4
    root bands (strips along x over the back 60 % of the mat, each at its own y, never a centre point, so blades overlap side by
    side instead of fanning); each blade heads +x within about 9 degrees of its band's lean (10 % strays up to about 45
    degrees), 0.4-0.9 of the mat long, curving in plan, a third of them kinked (folded) 15-40 degrees partway. Each rises from
    its root: 75 % lie flat almost at once (a 2-6 mm lift at 12-25 % of the length), 25 % hump over in a low arch (a smoothstep
    rise, so no steep stub at the root) peaking at 40-60 % of the length (35-100 % of the mat height, 2-6 cm, capped so the
    steepest part stays under ~34 degrees; the tallest at least 2 cm) and come down over the next 25-40 %; each then lies at its own 1.5-7 mm layer. Blades
    are 3-6 mm wide, 12-28 a mat. Standing parts roll up to 14 degrees about the blade. 2-4 short
    broken stalk pieces lie across at any angle. Vertex colour: per blade straw, bleached grey or dark old, darker at the root."""
    bm = bmesh.new()
    cl = bm.loops.layers.float_color.new('Col')
    L = length_cm / 100 * .75        # blades reach past the root clumps by up to ~1.4 L; the mat is fitted to length_cm at the end
    W = L * rng.uniform(.45, .7)
    Hm = rng.uniform(.02, .06)
    # Root bands: 2-4 strips along x across the back 60 % of the mat, each at its own y with its own lean; a blade's root lies
    # anywhere along its band, so the blades overlap side by side instead of fanning from a point.
    clumps = [(rng.uniform(-.55, -.35) * L, rng.uniform(-.35, .35) * W, rng.uniform(.25, .45) * L, rng.normal(0, .15))
              for _ in range(int(rng.integers(2, 5)))]
    nb = int(np.clip(round(length_cm * .9) + rng.integers(2, 6), 12, 28))
    segs = 6
    ts = [(i / segs) ** 1.35 for i in range(segs + 1)]
    up = Vector((0, 0, 1))

    def blade_tone():
        r = rng.random()
        v = rng.uniform(.85, 1.2)
        if r < .65:
            return (v, v, v)                                    # straw
        if r < .85:
            return (v * .95, v * 1.02, v * 1.35)                # bleached, greyer
        v = rng.uniform(.55, .7)
        return (v, v * .96, v * .95)                            # dark old blade

    def ribbon(points, widths, rolls, tone, dark_root):
        prev = None
        for i, (p, w, roll) in enumerate(zip(points, widths, rolls)):
            fwd = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)])
            fwd.z = 0
            fwd = fwd.normalized() if fwd.length > 1e-9 else Vector((1, 0, 0))
            perp = Vector((-fwd.y, fwd.x, 0))
            side = (perp * math.cos(roll) + up * math.sin(roll)) * w
            pair = (bm.verts.new(p + side), bm.verts.new(p - side))
            if prev:
                f = bm.faces.new((prev[0], prev[1], pair[1], pair[0]))
                t = i / (len(points) - 1)
                k = (.6 + .4 * min(1.0, t / .35)) if dark_root else 1.0
                paint([f], cl, [c * k for c in tone])
            prev = pair

    for b in range(nb):
        cx, cy, sp, bias = clumps[int(rng.integers(len(clumps)))]
        pos = Vector((cx + rng.uniform(0, sp), cy + rng.normal(0, .1 * W), 0))
        ang = bias + rng.normal(0, .15) + (rng.normal(0, .8) if rng.random() < .1 else 0)
        blen = L * (.9 if b == 0 else rng.uniform(.4, .9))
        curv = rng.normal(0, .55)
        kink_t = rng.uniform(.3, .7) if rng.random() < .35 else 2.0
        kink = float(rng.choice([-1, 1])) * rng.uniform(.25, .7)
        bowed = b == 0 or rng.random() < .25                 # a quarter hump over in a low arch; the rest lie flat from the root
        tp = rng.uniform(.4, .6) if bowed else rng.uniform(.12, .25)
        peak = (Hm if b == 0 else Hm * rng.uniform(.35, 1.0)) if bowed else rng.uniform(.002, .006)
        peak = min(peak, .45 * tp * blen)                    # the hump's steepest part stays under ~34 degrees: bent over, not a stalk
        if b == 0:
            peak = max(peak, .024)                           # the mat is at least 2 cm high (the samples fall either side of the peak)
        fall = rng.uniform(.25, .4) if bowed else .2
        lie = rng.uniform(.0015, .007)
        w0 = rng.uniform(.003, .006)
        roll0 = rng.uniform(-.25, .25)
        pts, wid, rol = [], [], []
        tprev = 0.0
        for i, t in enumerate(ts):
            if i:
                ang += curv * (t - tprev) + rng.normal(0, .05)
                if tprev < kink_t <= t:
                    ang += kink
                pos = pos + Vector((math.cos(ang), math.sin(ang), 0)) * (blen * (t - tprev))
            if t <= tp:
                r_ = t / tp
                z, stand = -.003 + (peak + .003) * (r_ * r_ * (3 - 2 * r_) if bowed else math.sin(.5 * math.pi * r_)), 1.0
            else:
                f = min(1.0, (t - tp) / fall)
                f = f * f * (3 - 2 * f)
                z, stand = peak + (lie - peak) * f, 1 - f
            pts.append(Vector((pos.x, pos.y, z)))
            wid.append(w0 * (1 - .72 * t))
            rol.append(roll0 * stand)
            tprev = t
        ribbon(pts, wid, rol, blade_tone(), True)
    for _ in range(int(rng.integers(2, 5))):                    # broken stalk pieces, any direction
        a = rng.uniform(0, 2 * math.pi)
        ln = L * rng.uniform(.1, .28)
        p0 = Vector((rng.uniform(-.45, .45) * L, rng.uniform(-.4, .4) * W, 0))
        z = rng.uniform(.002, .008)
        bend = rng.normal(0, .25)
        pts = [p0 + Vector((math.cos(a + bend * k / 3), math.sin(a + bend * k / 3), 0)) * (ln * k / 3) + Vector((0, 0, z)) for k in range(4)]
        ribbon(pts, [rng.uniform(.002, .0035)] * 4, [0] * 4, blade_tone(), False)
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    off = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, 0))
    fit = length_cm / 100 / max(max(xs) - min(xs), max(ys) - min(ys))      # the widest plan extent = length_cm
    for v in bm.verts:
        v.co = Vector(((v.co.x - off.x) * fit, (v.co.y - off.y) * fit, v.co.z))
    ob = finish_mesh(bm, name, length_cm)
    ob['gd_recipe'] = json.dumps(dict(blades=nb, mat_height_cm=round(max(v.co.z for v in ob.data.vertices) * 100, 2), root_bands=len(clumps)))
    return ob


def twig(rng, name, length_cm):
    bm = bmesh.new()

    def branch(start, direction, L, r0, segs, sides=5):
        rings = []
        d = direction.normalized()
        pos = start.copy()
        for i in range(segs + 1):
            t = i / segs
            if i:
                d = (d + Vector((rng.normal(0, .25), rng.normal(0, .25), rng.normal(0, .08)))).normalized()
                d.z = max(-.05, min(.05, d.z))
                pos = pos + d * (L / segs)
            r = r0 * (1 - .7 * t)
            up = Vector((0, 0, 1))
            side = d.cross(up).normalized()
            up2 = side.cross(d).normalized()
            ring = [bm.verts.new(pos + (side * math.cos(2 * math.pi * k / sides) + up2 * math.sin(2 * math.pi * k / sides)) * r) for k in range(sides)]
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for k in range(sides):
                bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]))
        return rings
    L = length_cm / 100
    r0 = rng.uniform(.004, .008) * (L / .3) ** .5
    main = branch(Vector((0, 0, r0)), Vector((1, 0, 0)), L, r0, 7)
    mid = main[int(len(main) * rng.uniform(.3, .6))]
    c = sum((v.co for v in mid), Vector()) / len(mid)
    branch(c, Vector((rng.uniform(.3, .8), rng.choice([-1, 1]) * rng.uniform(.5, 1), 0)), L * rng.uniform(.25, .45), r0 * .55, 4)
    return finish_mesh(bm, name, length_cm)


def tussock_base(rng, name, across_cm, height_cm):
    """A2 tussock base (plan: low, broad, lumpy root mound, height 0.12-0.2 of the width, a flattened crown where the tussock sits,
    an irregular outline, crumb and root texture, no peak). The outline is a circle warped by harmonics 2-5 (random amplitudes and
    phases, 5-15 % x 2/k) plus 1-3 bulging lobes. The profile is flat over the crown (the inner 25-35 % of the way to the rim, a slight tilt and
    dish, never a point), then falls by a smoothstep to the rim. 5-8 Gaussian lumps (10-22 % of the radius, 15-35 % of the height,
    a quarter of them dips) sit on the shoulder. The polar grid is staggered and jittered (no spokes), every vertex gets a crumb jitter, and
    a skirt goes 1.5 cm into the soil. 3-5 roots (low rounded ridges, radius 0.7-1.3 cm x sqrt(R / 19 cm) tapering 12 % a segment, the top 0.8 radius over the
    surface, both ends sunk into the soil, 4 segments) leave the crown edge at random
    angles, wander, and run 45-95 % of the radius, some over the rim into the ground. 2-4 crumbs lie round the rim. 6-10 small
    lumps and hollows (6-12 % of the radius) add crumb, the rim radius jitters 4 % and the rim sits 4 mm under the ground, so the
    ground cuts the mound along an irregular contact line instead of meeting it at a tangent. The mound's outline is fitted to across_cm wide and
    height_cm high before the roots go on. Vertex colour: crown darker (organic), roots a little browner. The material bumps the
    ScrubSoil height bake, box-projected (crumb texture)."""
    bm = bmesh.new()
    cl = bm.loops.layers.float_color.new('Col')
    R, H = across_cm / 200, height_cm / 100
    harm = [(k, rng.uniform(.05, .15) * 2 / k, rng.uniform(0, 2 * math.pi)) for k in (2, 3, 4, 5)]
    lobes = [(rng.uniform(0, 2 * math.pi), rng.uniform(.12, .3), rng.uniform(.25, .5)) for _ in range(int(rng.integers(1, 4)))]

    def angd(a, b):
        return (a - b + math.pi) % (2 * math.pi) - math.pi

    def rim(a):
        return R * (1 + sum(m * math.sin(k * a + p) for k, m, p in harm) + sum(h * math.exp(-(angd(a, c) / w) ** 2) for c, h, w in lobes))

    def sstep(t):
        t = min(1.0, max(0.0, t))
        return t * t * (3 - 2 * t)
    # The outline (lobes and harmonics included), not the base circle, is fitted to across_cm.
    aa = np.linspace(0, 2 * math.pi, 360, endpoint=False)
    R = 1.0
    ow = [rim(a) * math.cos(a) for a in aa]
    oh = [rim(a) * math.sin(a) for a in aa]
    R = across_cm / 100 / max(max(ow) - min(ow), max(oh) - min(oh))
    uc = rng.uniform(.25, .35)
    tilt = (rng.normal(0, .06), rng.normal(0, .06))
    bumps = []
    for _ in range(int(rng.integers(5, 9))):
        a, u = rng.uniform(0, 2 * math.pi), rng.uniform(.35, .9)
        bumps.append((math.cos(a) * u * rim(a), math.sin(a) * u * rim(a), R * rng.uniform(.1, .22),
                      rng.uniform(.15, .35) * (-.5 if rng.random() < .25 else 1.0)))
    for _ in range(int(rng.integers(6, 11))):            # small crumbly lumps and hollows
        a, u = rng.uniform(0, 2 * math.pi), rng.uniform(.1, .95)
        bumps.append((math.cos(a) * u * rim(a), math.sin(a) * u * rim(a), R * rng.uniform(.06, .12),
                      rng.uniform(.08, .2) * (-.7 if rng.random() < .35 else 1.0)))

    def raw_height(x, y):
        a = math.atan2(y, x)
        u = math.hypot(x, y) / rim(a)
        if u >= 1:
            return 0.0, u
        crown = 1 - sstep((u - uc) / (1 - uc))
        dish = -.05 * (1 - min(1.0, u / uc)) ** 2 + (tilt[0] * x + tilt[1] * y) / R * min(1.0, 1.5 * (1 - u))
        lumps = sum(h * math.exp(-((x - bx) ** 2 + (y - by) ** 2) / br ** 2) for bx, by, br, h in bumps)
        return max(0.0, .92 * crown + dish + lumps * (1 - sstep((u - .8) / .2))), u

    S, us = 18, [.17, .34, .52, .68, .83, 1.0]
    probe = [raw_height(u * rim(a) * math.cos(a), u * rim(a) * math.sin(a))[0] for u in np.linspace(0, .99, 40) for a in np.linspace(0, 2 * math.pi, 72)]
    fit = H / max(probe)

    def height(x, y):
        z, u = raw_height(x, y)
        return z * fit, u
    centre = bm.verts.new((0, 0, height(0, 0)[0]))
    shade = {centre: .82}
    rings = []
    for j, u0 in enumerate(us):
        ring = []
        for k in range(S):
            a = 2 * math.pi * (k + .5 * (j % 2) + rng.uniform(-.22, .22)) / S
            u = u0 * rng.uniform(.96, 1.04) if j == len(us) - 1 else u0 + rng.uniform(-.03, .03)
            x, y = u * rim(a) * math.cos(a), u * rim(a) * math.sin(a)
            z = height(x, y)[0] + (rng.normal(0, .09) * H * (1 - u) if j < len(us) - 1 else -.004)
            v = bm.verts.new((x, y, z))
            shade[v] = (.82 + .18 * sstep((u - uc * .6) / (.6 - uc * .6 + 1e-6))) * rng.uniform(.93, 1.05)
            ring.append(v)
        rings.append(ring)
    skirt = [bm.verts.new((v.co.x * 1.05, v.co.y * 1.05, -.015)) for v in rings[-1]]
    for v in skirt:
        shade[v] = 1.0
    mound = [bm.faces.new((centre, rings[0][k], rings[0][(k + 1) % S])) for k in range(S)]
    for a_, b_ in zip(rings, rings[1:] + [skirt]):
        mound += [bm.faces.new((a_[k], b_[k], b_[(k + 1) % S], a_[(k + 1) % S])) for k in range(S)]
    for f in mound:
        for lp in f.loops:
            s = shade[lp.vert]
            lp[cl] = (s, s, s, 1.0)
    # Roots: inverted-V ridges on the surface, half sunk.
    nroots = int(rng.integers(3, 6))
    for a0 in sorted(rng.uniform(0, 2 * math.pi, nroots)):
        r0 = rng.uniform(.007, .013) * (R / .19) ** .5
        length = R * rng.uniform(.45, .95)
        u0 = uc * rng.uniform(.7, 1.1)
        p = Vector((u0 * rim(a0) * math.cos(a0), u0 * rim(a0) * math.sin(a0), 0))
        heading = a0 + rng.normal(0, .6)
        cs = []
        for i in range(5):
            if i:
                heading += rng.normal(0, .3)
                p = p + Vector((math.cos(heading), math.sin(heading), 0)) * (length / 4)
            rr = r0 * (1 - .12 * i)
            z, u = height(p.x, p.y)
            sunk = 1.4 * rr if i == 0 or (i == 4 and u >= .97) else 0.0      # both ends go into the soil (no open ends)
            cs.append((Vector((p.x, p.y, z - sunk)), rr))
        ridge = []
        for i, (c, rr) in enumerate(cs):
            fwd = cs[min(i + 1, 4)][0] - cs[max(i - 1, 0)][0]
            fwd.z = 0
            fwd.normalize()
            left = Vector((-fwd.y, fwd.x, 0))
            # a low rounded ridge: two buried feet and two shoulders, the top 0.8 rr over the surface
            prof = [(1.25, -.5), (.5, .8), (-.5, .8), (-1.25, -.5)]
            ridge.append(([bm.verts.new(c + left * (rr * a_) + Vector((0, 0, rr * z_))) for a_, z_ in prof], left))
        rf = []
        for (r0_, left), (r1_, _) in zip(ridge, ridge[1:]):
            for k in range(3):
                f = bm.faces.new((r0_[k], r1_[k], r1_[k + 1], r0_[k + 1]))
                f.normal_update()
                want = Vector((0, 0, 1)) + left * (.8 - .8 * k)
                if f.normal.dot(want) < 0:
                    f.normal_flip()
                rf.append(f)
        paint(rf, cl, [c * rng.uniform(.95, 1.05) for c in (.9, .82, .73)])
    for _ in range(int(rng.integers(2, 5))):
        a = rng.uniform(0, 2 * math.pi)
        rr = rim(a) * rng.uniform(.85, 1.15)
        crumb(bm, cl, rng, rr * math.cos(a), rr * math.sin(a), rng.uniform(.01, .025), rng.uniform(.3, .5))
    ob = finish_mesh(bm, name, across_cm)
    ob['gd_recipe'] = json.dumps(dict(height_ratio=round(height_cm / across_cm, 3), crown_fraction=round(float(uc), 3), lumps=len(bumps),
                                      roots=nroots, lobes=len(lobes)))
    return ob


def load_study_stones():
    with bpy.data.libraries.load(str(STUDY / 'GravelRoadStudy.blend')) as (src, dst):
        dst.objects = ['SM_GR_Stone1', 'SM_GR_Stone2', 'SM_GR_Stone3', 'SM_GR_Stone4']
    return dst.objects


def soil_material(name, colour_png, tint, rough, box=True, vcol=False, bump_png=None, bump_m=PARALLAX_DEPTH_CM / 100):
    """vcol: the A2 meshes carry a float colour attribute 'Col' (linear, exported to FBX as sRGB vertex colour) that multiplies
    the colour."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    ns, ls = mat.node_tree.nodes, mat.node_tree.links
    p = next(n for n in ns if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Roughness'].default_value = rough
    if colour_png:
        tc = ns.new('ShaderNodeTexCoord')
        mp = ns.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (1 / TILE_M, 1 / TILE_M, 1 / TILE_M)
        ls.new(tc.outputs['Object'], mp.inputs['Vector'])
        t = ns.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(str(colour_png), check_existing=True)
        t.projection = 'BOX' if box else 'FLAT'
        t.projection_blend = .3
        ls.new(mp.outputs[0], t.inputs['Vector'])
        mul = ns.new('ShaderNodeMixRGB')
        mul.blend_type = 'MULTIPLY'
        mul.inputs[0].default_value = 1.0
        ls.new(t.outputs['Color'], mul.inputs[1])
        mul.inputs[2].default_value = (*tint, 1)
        out = mul.outputs[0]
        if bump_png:
            th = ns.new('ShaderNodeTexImage')
            th.image = bpy.data.images.load(str(bump_png), check_existing=True)
            th.image.colorspace_settings.name = 'Non-Color'
            th.projection = 'BOX' if box else 'FLAT'
            th.projection_blend = .3
            ls.new(mp.outputs[0], th.inputs['Vector'])
            bump = ns.new('ShaderNodeBump')
            bump.inputs['Distance'].default_value = bump_m
            ls.new(th.outputs['Color'], bump.inputs['Height'])
            ls.new(bump.outputs['Normal'], p.inputs['Normal'])
    else:
        rgb = ns.new('ShaderNodeRGB')
        rgb.outputs[0].default_value = (*tint, 1)
        out = rgb.outputs[0]
    if vcol:
        vc = ns.new('ShaderNodeVertexColor')
        vc.layer_name = 'Col'
        m2 = ns.new('ShaderNodeMixRGB')
        m2.blend_type = 'MULTIPLY'
        m2.inputs[0].default_value = 1.0
        ls.new(out, m2.inputs[1])
        ls.new(vc.outputs['Color'], m2.inputs[2])
        out = m2.outputs[0]
    ls.new(out, p.inputs['Base Color'])
    return mat


def stage_mesh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = a1_rng_for_twigs()                     # the twigs (kept from A1) draw from A1's stream
    rng_clod, rng_lit, rng_base = (np.random.default_rng(s) for s in (20261011, 20261012, 20261013))
    made = []
    scrub = OUT / (PRE + 'ScrubSoilColor.png')
    scrub_h = OUT / (PRE + 'ScrubSoilHeight.png')
    m_clod = soil_material('M_GD_Clod', scrub, (1.2, 1.14, 1.06), .93, vcol=True, bump_png=scrub_h)
    m_peb = soil_material('M_GD_Pebble', None, (.16, .145, .12), .72)
    m_lit = soil_material('M_GD_Litter', None, (.32, .25, .13), .8, vcol=True)
    m_twig = soil_material('M_GD_Twig', None, (.1, .08, .06), .85)
    m_base = soil_material('M_GD_TussockBase', scrub, (.86, .8, .7), .92, vcol=True, bump_png=scrub_h)
    for i, size in enumerate([3, 4.5, 6, 8, 10, 12]):
        ob = clod(rng_clod, 'SM_GD_Clod%d' % i, size)
        ob.data.materials.append(m_clod)
        made.append(('Clods', ob, dict(size_cm=size)))
    stones = load_study_stones()
    for i, (src, size) in enumerate(zip(stones, [1.2, 2.2, 3.5, 5.0])):
        me = src.data.copy()
        me.name = 'SM_GD_Pebble%d' % i
        ob = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(ob)
        xs_ = [v.co.x for v in me.vertices]
        ys_ = [v.co.y for v in me.vertices]
        ext = max(max(xs_) - min(xs_), max(ys_) - min(ys_), 1e-6)
        s = size / 100 / ext
        me.transform(Matrix.Diagonal((s, s, s, 1)))
        if tris(me) < 100:
            # The study's stones are 33-38 triangles: one Catmull-Clark level (x6 on triangles) brings them into 100-400, rounded.
            mod = ob.modifiers.new('Subdiv', 'SUBSURF')
            mod.levels = 1
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.triangulate(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        if tris(me) > 400:
            mod = ob.modifiers.new('Decimate', 'DECIMATE')
            mod.ratio = 380 / tris(me)
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.modifier_apply(modifier=mod.name)
        me.materials.clear()
        me.materials.append(m_peb)
        made.append(('Pebbles', ob, dict(size_cm=size, source='GravelRoadStudy 04 ' + src.name)))
    for i, size in enumerate([12, 16, 21, 26]):
        ob = litter_mat(rng_lit, 'SM_GD_Litter%d' % i, size)
        ob.data.materials.append(m_lit)
        made.append(('Litter', ob, dict(size_cm=size)))
    for i, size in enumerate([15, 26, 40]):
        ob = twig(rng, 'SM_GD_Twig%d' % i, size)
        ob.data.materials.append(m_twig)
        made.append(('Twigs', ob, dict(size_cm=size)))
    for i, (across, high) in enumerate([(26, 3.6), (38, 5.2), (50, 7.2)]):     # height 0.138, 0.137, 0.144 of the width
        ob = tussock_base(rng_base, 'SM_GD_TussockBase%d' % i, across, high)
        ob.data.materials.append(m_base)
        made.append(('TussockBases', ob, dict(across_cm=across, height_cm=high)))
    rows = []
    for fam, ob, extra in made:
        dims = ob.dimensions
        row = dict(family=fam, name=ob.name, triangles=tris(ob.data), size_m=[round(dims.x, 4), round(dims.y, 4), round(dims.z, 4)], **extra)
        if 'gd_recipe' in ob:
            row['recipe'] = json.loads(ob['gd_recipe'])
            row['phase'] = 'A2'
            row['z_range_m'] = [round(min(v.co.z for v in ob.data.vertices), 4), round(max(v.co.z for v in ob.data.vertices), 4)]
        for o in bpy.context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        path = OUT / (ob.name + '.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, apply_unit_scale=True, bake_space_transform=False,
                                 mesh_smooth_type='EDGE' if fam == 'Clods' else 'FACE')    # the clods' hard facet edges
        row['fbx'] = rel(path)
        rows.append(row)
    for st in stones:
        bpy.data.objects.remove(st)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'GroundDetailScatter.blend'))
    say('meshes: ' + ', '.join('%s %d' % (r['name'], r['triangles']) for r in rows))
    return rows


# ---------------------------------------------------------------- renders
def render_setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    with bpy.data.libraries.load(str(STUDY / 'GravelRoadStudy.blend')) as (src, dst):
        dst.worlds = ['Soft cool daylight']
        dst.objects = ['Directional daylight']
    scene.world = dst.worlds[0]
    scene.collection.objects.link(dst.objects[0])
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 6
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1440, 900, 100
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.render.image_settings.file_format = 'PNG'
    return scene


def ground_material(name, displaced):
    mat = bpy.data.materials.new('M_GD_Render_' + name + ('_Disp' if displaced else ''))
    mat.use_nodes = True
    ns, ls = mat.node_tree.nodes, mat.node_tree.links
    p = next(n for n in ns if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Specular IOR Level'].default_value = .5
    uv = ns.new('ShaderNodeUVMap')
    uv.uv_map = 'UVMap'

    def tex(suffix, srgb=False):
        t = ns.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(str(OUT / (PRE + name + suffix + '.png')), check_existing=True)
        t.image.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
        t.extension = 'REPEAT'
        ls.new(uv.outputs[0], t.inputs['Vector'])
        return t.outputs['Color']
    sep = ns.new('ShaderNodeSeparateColor')
    ls.new(tex('ORH'), sep.inputs[0])
    ls.new(tex('Color', True), p.inputs['Base Color'])
    ls.new(sep.outputs[1], p.inputs['Roughness'])
    nsep = ns.new('ShaderNodeSeparateColor')
    ls.new(tex('Normal'), nsep.inputs[0])
    inv = ns.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    ls.new(nsep.outputs[1], inv.inputs[1])
    comb = ns.new('ShaderNodeCombineColor')
    ls.new(nsep.outputs[0], comb.inputs[0])
    ls.new(inv.outputs[0], comb.inputs[1])        # DirectX -> Blender's OpenGL green
    ls.new(nsep.outputs[2], comb.inputs[2])
    nm = ns.new('ShaderNodeNormalMap')
    nm.space = 'OBJECT'
    ls.new(comb.outputs[0], nm.inputs['Color'])
    ls.new(nm.outputs[0], p.inputs['Normal'])
    if displaced:
        mul = ns.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        ls.new(sep.outputs[2], mul.inputs[0])
        mul.inputs[1].default_value = PARALLAX_DEPTH_CM / 100.0
        disp = ns.new('ShaderNodeDisplacement')
        disp.inputs['Midlevel'].default_value = 0.0
        disp.inputs['Scale'].default_value = 1.0
        ls.new(mul.outputs[0], disp.inputs['Height'])
        out = next(n for n in ns if n.type == 'OUTPUT_MATERIAL')
        ls.new(disp.outputs[0], out.inputs['Displacement'])
        try:
            mat.displacement_method = 'DISPLACEMENT'
        except AttributeError:
            mat.cycles.displacement_method = 'DISPLACEMENT'
    return mat


def ground_mesh(name, x0, x1, y0, y1, step):
    nx, ny = int(round((x1 - x0) / step)), int(round((y1 - y0) / step))
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x0 + i * step, y0 + j * step, 0) for j in range(ny + 1) for i in range(nx + 1)], [],
                   [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(ny) for i in range(nx)])
    uvl = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        v = me.vertices[loop.vertex_index].co
        uvl.data[loop.index].uv = (v.x / TILE_M, v.y / TILE_M)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def camera(scene, loc, pitch_deg, yaw_deg=0.0, lens=30):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    p, y = math.radians(pitch_deg), math.radians(yaw_deg)
    cam.rotation_euler = Vector((math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), -math.sin(p))).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = lens
    scene.camera = cam
    return cam


# The A2 anti-tile preview (plan GR2 phase A2): what phase B's landscape material is to do against the 2 m tile's chevrons.
AT_B_TILE_M = 2.7              # sample B's tile (scale 2.0 / 2.7 of sample A's UVs)
AT_B_ROT_DEG = 37.0            # sample B's UVs turned by this (its normals turned back to match)
AT_B_OFFSET = (.37, .61)       # sample B's UV offset
AT_MASK_M = 7.0                # the blend mask: 2D fBm noise, 7 m lattice, detail 2, roughness 0.5
AT_MASK_EDGES = (.45, .55)     # mask = smoothstep of the noise between these (0 = sample A, 1 = sample B)
AT_TINT_M = 13.0               # the macro tint: 2D fBm noise, 13 m lattice, detail 3, roughness 0.5
AT_TINT_EDGES = (.38, .62)     # linear ramp of that noise between these, clamped
AT_TINT_DAMP = (.82, .80, .82)     # colour multiplier at 0: darker, a little cooler (damp)
AT_TINT_DRY = (1.12, 1.07, .96)    # colour multiplier at 1: lighter, warmer (dry)


def antitile_material(name):
    """The bake sampled twice (A as baked; B at AT_B_TILE_M, turned AT_B_ROT_DEG, offset), A/B chosen by the 7 m mask; colour,
    roughness and normal all blended; the colour then multiplied by the macro tint. Normal-mapped like <Set>_3x3 (no displacement)."""
    mat = bpy.data.materials.new('M_GD_Render_' + name + '_AntiTile')
    mat.use_nodes = True
    ns, ls = mat.node_tree.nodes, mat.node_tree.links
    p = next(n for n in ns if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Specular IOR Level'].default_value = .5
    uv = ns.new('ShaderNodeUVMap')
    uv.uv_map = 'UVMap'
    mp = ns.new('ShaderNodeMapping')
    mp.vector_type = 'POINT'
    sc = TILE_M / AT_B_TILE_M
    mp.inputs['Scale'].default_value = (sc, sc, 1.0)
    mp.inputs['Rotation'].default_value = (0.0, 0.0, math.radians(AT_B_ROT_DEG))
    mp.inputs['Location'].default_value = (AT_B_OFFSET[0], AT_B_OFFSET[1], 0.0)
    ls.new(uv.outputs[0], mp.inputs['Vector'])
    pos = ns.new('ShaderNodeTexCoord').outputs['Object']

    def tex(suffix, vec, srgb=False):
        t = ns.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(str(OUT / (PRE + name + suffix + '.png')), check_existing=True)
        t.image.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
        t.extension = 'REPEAT'
        ls.new(vec, t.inputs['Vector'])
        return t.outputs['Color']

    def math_node(op, a, b=None, c=None):
        m = ns.new('ShaderNodeMath')
        m.operation = op
        for k, x in enumerate((a, b, c)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                m.inputs[k].default_value = float(x)
            else:
                ls.new(x, m.inputs[k])
        return m.outputs[0]

    def mix(a, b, fac, blend='MIX'):
        m = ns.new('ShaderNodeMixRGB')
        m.blend_type = blend
        for k, x in ((0, fac), (1, a), (2, b)):
            if isinstance(x, (int, float)):
                m.inputs[k].default_value = float(x)
            elif isinstance(x, tuple):
                m.inputs[k].default_value = (*x, 1.0)
            else:
                ls.new(x, m.inputs[k])
        return m.outputs[0]

    def noise(lattice_m, detail):
        n = ns.new('ShaderNodeTexNoise')
        n.noise_dimensions = '2D'
        n.inputs['Scale'].default_value = 1.0 / lattice_m
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = .5
        ls.new(pos, n.inputs['Vector'])
        return n.outputs['Fac']

    def ramp(x, lo, hi, smooth):
        m = ns.new('ShaderNodeMapRange')
        m.interpolation_type = 'SMOOTHSTEP' if smooth else 'LINEAR'
        m.clamp = True
        m.inputs['From Min'].default_value, m.inputs['From Max'].default_value = lo, hi
        m.inputs['To Min'].default_value, m.inputs['To Max'].default_value = 0.0, 1.0
        ls.new(x, m.inputs['Value'])
        return m.outputs['Result']

    def normal_gl(col, turn_deg):
        """DirectX tangent normal -> OpenGL, its xy turned by -turn_deg (B's UVs are turned by +turn_deg), re-encoded 0..1."""
        sep = ns.new('ShaderNodeSeparateColor')
        ls.new(col, sep.inputs[0])
        x = math_node('MULTIPLY_ADD', sep.outputs[0], 2.0, -1.0)
        y = math_node('MULTIPLY_ADD', sep.outputs[1], -2.0, 1.0)
        if turn_deg:
            c, s_ = math.cos(math.radians(turn_deg)), math.sin(math.radians(turn_deg))
            x, y = (math_node('MULTIPLY_ADD', x, c, math_node('MULTIPLY', y, s_)),
                    math_node('MULTIPLY_ADD', x, -s_, math_node('MULTIPLY', y, c)))
        comb = ns.new('ShaderNodeCombineColor')
        ls.new(math_node('MULTIPLY_ADD', x, .5, .5), comb.inputs[0])
        ls.new(math_node('MULTIPLY_ADD', y, .5, .5), comb.inputs[1])
        ls.new(sep.outputs[2], comb.inputs[2])
        return comb.outputs[0]

    a_vec, b_vec = uv.outputs[0], mp.outputs[0]
    mask = ramp(noise(AT_MASK_M, 2.0), AT_MASK_EDGES[0], AT_MASK_EDGES[1], True)
    tint = mix(AT_TINT_DAMP, AT_TINT_DRY, ramp(noise(AT_TINT_M, 3.0), AT_TINT_EDGES[0], AT_TINT_EDGES[1], False))
    colour = mix(tex('Color', a_vec, True), tex('Color', b_vec, True), mask)
    ls.new(mix(colour, tint, 1.0, 'MULTIPLY'), p.inputs['Base Color'])
    orh = ns.new('ShaderNodeSeparateColor')
    ls.new(mix(tex('ORH', a_vec), tex('ORH', b_vec), mask), orh.inputs[0])
    ls.new(orh.outputs[1], p.inputs['Roughness'])
    nm = ns.new('ShaderNodeNormalMap')
    nm.space = 'OBJECT'
    ls.new(mix(normal_gl(tex('Normal', a_vec), 0.0), normal_gl(tex('Normal', b_vec), AT_B_ROT_DEG), mask), nm.inputs['Color'])
    ls.new(nm.outputs[0], p.inputs['Normal'])
    return mat


def render_antitile(sets=('ScrubSoil',)):
    """A set over 20 m ahead of a 1.7 m eye: with the two-sample blend and tint (AntiTile), and ScrubSoil's single sample (reference).
    Phase B item 0: SoilUnderGrass too (its blended view), to judge whether its root fibres darken in rows."""
    renders = {}
    jobs = [(s + '_AntiTile', s, True) for s in sets] + [('ScrubSoil_AntiTile_Single', 'ScrubSoil', False)]
    for tag, name, blended in jobs:
        scene = render_setup()
        g = ground_mesh('Ground 20 m', -1, 20, -14, 14, 1.0)
        g.data.materials.append(antitile_material(name) if blended else ground_material(name, False))
        camera(scene, (-.5, 0, 1.7), 20, 0, 30)      # the frame's top edge just over the horizon: ground from 2 m to the far edge at 20 m
        scene.render.filepath = str(OUT / (tag + '.png'))
        bpy.ops.render.render(write_still=True)
        renders[tag] = rel(OUT / (tag + '.png'))
        say('rendered ' + tag)
    return renders


def keep_a1_renders(families):
    """Phase A's renders of the redone families stay as Scatter_<Family>_A1.png (copied once, never overwritten)."""
    kept = {}
    for fam in families:
        src, dst = OUT / ('Scatter_%s.png' % fam), OUT / ('Scatter_%s_A1.png' % fam)
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
        if dst.exists():
            kept['Scatter_%s_A1' % fam] = rel(dst)
    return kept


def stage_render(mesh_rows, soil=True, only_families=None, antitile=True):
    renders = {}
    for name in (SETS if soil else []):
        scene = render_setup()
        flat = ground_mesh('Ground 3x3 ' + name, 0, 6, -3, 3, 6.0)
        flat.data.materials.append(ground_material(name, False))
        camera(scene, (-1.5, 0, 1.7), 18)
        scene.render.filepath = str(OUT / (name + '_3x3.png'))
        bpy.ops.render.render(write_still=True)
        renders[name + '_3x3'] = rel(OUT / (name + '_3x3.png'))
        say('rendered %s_3x3' % name)
        flat.hide_render = True
        disp = ground_mesh('Ground displaced ' + name, -2, 30, -16, 16, .5)
        sub = disp.modifiers.new('Dice', 'SUBSURF')
        sub.subdivision_type = 'SIMPLE'
        sub.use_adaptive_subdivision = True
        sub.adaptive_space = 'PIXEL'
        sub.adaptive_pixel_size = 1.0
        disp.data.materials.append(ground_material(name, True))
        scene.render.filepath = str(OUT / (name + '_Displaced.png'))
        bpy.ops.render.render(write_still=True)
        renders[name + '_Displaced'] = rel(OUT / (name + '_Displaced.png'))
        say('rendered %s_Displaced' % name)
    # The scatter families on the ScrubSoil ground (normal-mapped), each instanced over 2 x 1.4 m in clusters.
    families = {}
    for row in mesh_rows:
        families.setdefault(row['family'], []).append(row['name'])
    counts = dict(Clods=70, Pebbles=60, Litter=40, Twigs=9, TussockBases=4)
    for fam, names in families.items():
        if only_families is not None and fam not in only_families:
            continue
        scene = render_setup()
        with bpy.data.libraries.load(str(OUT / 'GroundDetailScatter.blend')) as (src, dst):
            dst.objects = names
        protos = dst.objects
        flat = ground_mesh('Ground ' + fam, -1, 5, -3, 3, 6.0)
        flat.data.materials.append(ground_material('ScrubSoil', False))
        R = random.Random(sum(ord(c) for c in fam))
        centres = [(R.uniform(.4, 2.4), R.uniform(-.7, .7)) for _ in range(4)]
        for k in range(counts.get(fam, 20)):
            cx, cy = R.choice(centres)
            spread = .5 if fam in ('Twigs', 'TussockBases') else .28
            x, y = cx + R.gauss(0, spread), cy + R.gauss(0, spread)
            if fam == 'TussockBases':
                x, y = .6 + 1.0 * k, (-.35 if k % 2 else .35)
            proto = R.choice(protos)
            ob = bpy.data.objects.new(fam, proto.data)
            ob.location = (x, y, 0)
            ob.rotation_euler = (math.radians(R.uniform(-6, 6)), math.radians(R.uniform(-6, 6)), R.uniform(0, 2 * math.pi))
            s = R.uniform(.8, 1.2)
            ob.scale = (s, s, s)
            scene.collection.objects.link(ob)
        camera(scene, (-.6, 0, .9), 32, 0, 35)
        scene.render.filepath = str(OUT / ('Scatter_%s.png' % fam))
        bpy.ops.render.render(write_still=True)
        renders['Scatter_' + fam] = rel(OUT / ('Scatter_%s.png' % fam))
        say('rendered Scatter_%s' % fam)
    if antitile:
        renders.update(render_antitile())
    return renders


def main():
    man_path = OUT / 'manifest.json'
    man = json.loads(man_path.read_text()) if man_path.exists() else {}
    man.update(source='Art/Blender/bake_ground_detail_gr2.py', plan='docs/GROUND_RELIEF_PLAN.md GR2 phase A + A2', tile_m=TILE_M, size=N,
               texel_cm=round(TEXEL_CM, 4), parallax_depth_cm=PARALLAX_DEPTH_CM, normal='DirectX (green NEG_Y), tangent = the tile\'s u, v',
               palette=dict(scrub_dark_linear=SCRUB_DARK.tolist(), scrub_light_linear=SCRUB_LIGHT.tolist(), source='live_mud_style.GROUND_HLSL',
                            under_grass_scale=.62, straw_linear=[.32, .25, .13], pebble_linear=[.16, .145, .12], root_linear=[.07, .05, .032]),
               orh='R horizon AO (bake_gravel_orh.horizon_ao, 6 cm, 16 directions) at the parallax depth; G roughness 0.6-0.95; B soft rims (6 %/texel, 1-texel Gaussian)')
    man['a2'] = dict(
        redone=A2_FAMILIES, kept='the soil bakes, the pebbles, the twigs (twigs from A1\'s replayed random stream, so identical)',
        vertex_colour="the redone meshes carry a float colour attribute 'Col' (linear; FBX sRGB vertex colour) multiplying the colour",
        clod_edges='hard above 55 degrees (FBX smoothing by edge)',
        render_materials='clods and tussock bases: the ScrubSoil colour box-projected (object space, 2 m), times a tint, times Col, '
                         'bumped by the ScrubSoil height bake box-projected (distance 1.5 cm = the parallax depth); '
                         'phase B needs the equivalent (world-aligned)',
        antitile=dict(sample_b_tile_m=AT_B_TILE_M, sample_b_uv_scale=round(TILE_M / AT_B_TILE_M, 4), sample_b_rotation_deg=AT_B_ROT_DEG,
                      sample_b_uv_offset=list(AT_B_OFFSET), mask_noise='2D fBm, lattice %g m, detail 2, roughness 0.5' % AT_MASK_M,
                      mask_smoothstep=list(AT_MASK_EDGES), tint_noise='2D fBm, lattice %g m, detail 3, roughness 0.5' % AT_TINT_M,
                      tint_ramp=list(AT_TINT_EDGES), tint_damp=list(AT_TINT_DAMP), tint_dry=list(AT_TINT_DRY),
                      blended='colour, roughness (ORH G), normal (B turned back by its rotation)',
                      view='ground x -1..20 m, y -14..14 m; eye (-0.5, 0, 1.7) m, pitch 20 deg, 30 mm lens, 1440 x 900; normal-mapped only'))
    if STAGE in ('all', 'bake'):
        # Phase B item 0: A2's crack numbers first (measured, nothing written), then the bake; A2's anti-tile renders kept once.
        a2 = build_set('ScrubSoil', 7001, CRACKS_A2, write=False)
        man['sets'] = {name: build_set(name, 7001 + i) for i, name in enumerate(SETS)}
        man['phase_b_item0'] = dict(a2=dict(cracks=a2['cracks'], darkening=a2['darkening']),
                                    now=dict(cracks=man['sets']['ScrubSoil']['cracks'], darkening=man['sets']['ScrubSoil']['darkening']),
                                    soil_under_grass=man['sets']['SoilUnderGrass']['darkening'])
        for tag in ('ScrubSoil_AntiTile', 'ScrubSoil_AntiTile_Single'):
            if (OUT / (tag + '.png')).exists() and not (OUT / (tag + '_A2.png')).exists():
                shutil.copy2(OUT / (tag + '.png'), OUT / (tag + '_A2.png'))
        man_path.write_text(json.dumps(man, indent=2))
    if STAGE in ('all', 'mesh', 'a2'):
        man['scatter'] = stage_mesh()
        man_path.write_text(json.dumps(man, indent=2))
    if STAGE in ('all', 'render'):
        man['renders'] = stage_render(man.get('scatter', []))
        man_path.write_text(json.dumps(man, indent=2))
    if STAGE == 'bake':
        renders = man.get('renders', {})
        renders.update(render_antitile(('ScrubSoil', 'SoilUnderGrass')))
        renders.update({t + '_A2': rel(OUT / (t + '_A2.png')) for t in ('ScrubSoil_AntiTile', 'ScrubSoil_AntiTile_Single') if (OUT / (t + '_A2.png')).exists()})
        man['renders'] = renders
        man_path.write_text(json.dumps(man, indent=2))
    if STAGE in ('a2', 'scatter', 'antitile'):
        renders = man.get('renders', {})
        renders.update(keep_a1_renders(A2_FAMILIES))
        fams = [] if STAGE == 'antitile' else [f for f in ARGS.get('families', ','.join(A2_FAMILIES)).split(',') if f]
        renders.update(stage_render(man.get('scatter', []), soil=False, only_families=fams, antitile=STAGE != 'scatter'))
        man['renders'] = renders
        man_path.write_text(json.dumps(man, indent=2))
    say('done')


main()
