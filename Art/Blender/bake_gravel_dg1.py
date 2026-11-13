"""Deformable gravel DG1 item 1 (docs/DEFORMABLE_GRAVEL_PLAN.md DG1): revision 04's own surface shader baked into two
tileable 2 m sets at 2048, plus the look-gate renders.

The approved study (Art/Export/GravelRoadStudy/04, Art/Blender/gravel_road_material.py, docs/GRAVEL_ROAD_STUDY.md; read only,
never modified) paints the road with Blender procedurals: Voronoi stone faces (13 cells per metre) and embedded chips (34
per metre) on coordinates warped by a 16 per metre noise, a broad brush wash (noise 1.15 per metre, detail 1) and long
paint dabs (noise of the metres x (8, 48)). Those procedurals don't repeat, so, as LM5's bakes did
(Art/Blender/build_mud_wet_study.py: periodic numpy fields, no mirror), every procedural input is made here in numpy,
periodic over the 2 m tile, and fed to a node-for-node copy of the study's graph (study_shader below, every ramp, map
range, mix and bump number unchanged), which Cycles bakes:
- Voronoi: Blender's own F1 / distance-to-edge construction (one jittered point per cell, the 3x3 searches), with the
  cell grid wrapped (2 m x 13 = 26 and x 34 = 68 cells, both whole);
- Noise: periodic gradient noise whose values are then matched, quantile for quantile, to Blender 5.1's own Noise output
  at the study's settings (point-sampled by an EMIT bake here), so every ramp and map range sees the study's value
  distribution. The chipped-outline warp (16 per metre: 32 periods) is exact in period; the broad wash goes from 1.15 to
  1.0 per metre (2 periods; 1.15 has no whole period on 2 m);
- the paint dabs (brush=dabs, the default): the study's dabs are its noise at (8 x, 48 y): about 6:1 marks all along the
  road's direction. A world-UV tile must have no dominant direction (the plan: "no dominant direction"), so the dabs
  keep their size (sigma 3.0 x 0.55 cm) and value distribution and take a random orientation each (18 orientation
  bins). brush=road bakes the study's road-aligned dabs instead (periodic: 16 x 96 lattice periods).
The study's wheel wear is its vertex alpha (build_road_ford_style.surface: 1 - 0.68 x lane): Loose bakes alpha 1 (off the
path), Packed alpha 0.32 (the wheel path's centre), so Packed is the study's own wheel-path shading. Dry: the meadow and
wetness masks are 0 (their mixes are identities), the roughness is the study's dry 0.9 (ground_material_v2: 0.9 - 0.3 x
wetness), Specular IOR Level 0.12.

Bakes (Cycles CPU, 4 threads, 1 sample; EMIT for values, a tangent NORMAL bake with green NEG_Y = DirectX, as the mud's):
  T_GV_<Set>Color   RGB 8-bit sRGB
  T_GV_<Set>Normal  RGB 8-bit DirectX (the study's two chained bumps)
  T_GV_<Set>Rough   grey 8-bit linear: the decided roughness (Art/bake_gravel_orh.py roughness: 0.9 - 0.16 x
                    smoothstep(0.45, 0.9, h), Packed - 0.05, floor 0.55), the same values as ORH.G
  T_GV_<Set>Height  grey 16-bit: the parallax height (phase A3, parallax_heights; not baked): per broad stone a centre height
                    (Loose 0.35-1.0, Packed 0.25-0.7, uniform: 31 % at 0.35-0.55) and a tilted top (rise 0.15-0.45 across its width, random
                    azimuth) with 6 %/texel sides, chips raised 0.05-0.3 each on a 0-0.1 noisy matrix; 0-1 in units both
                    sets share, x the parallax depth (Loose 0.8 cm, Packed 0.5 cm). The colour and normal bakes don't use it.
  T_GV_<Set>AO, T_GV_<Set>ORH  Art/bake_gravel_orh.py (bake_mud_orh.py's method, DG1 item 1's decisions): R horizon AO at
                    the parallax depth (Loose 0.8 cm, Packed 0.5 cm), G the roughness, B the parallax height with soft
                    rims at 6 %/texel and a 1.0-texel Gaussian
Checks on the files as written (export_mud_wet.py's): the seam ratio and edge z-score per channel, the structure-tensor
coherence (whole tile, 10 cm mean) of the height and the colour, roughness percentiles, colour and luminance, the
study's coverage numbers per set, the stone-top B gates (the median per stone: each Loose stone's top mean B, each stone
once, >= 0.6; the maximum B >= 0.97) and mean(hL) (Loose ORH.B's mean, which the track blend centres
on). Writes Art/Export/GravelDG1/manifest.json.

Renders (study 04's world, sun, AgX Medium High Contrast, Cycles 32 samples denoised, 1440 x 900): a flat 6 m ground of
the tile 3 x 3, the eye 1.7 m up, 1.5 m behind the ground's edge, looking along x 18 deg down, 30 mm (the study's driver
lens): Loose_3x3.png, Packed_3x3.png, and Transition.png, where Packed runs through Loose as two 30 cm wheel paths by DG1
item 2's rule p = smoothstep(0.35, 0.7, T - 0.3 (hL - mean(hL))) (T a Gaussian path mask, sigma 18.5 cm, so p = 0.5 lies
15 cm out where hL = mean(hL); hL = Loose ORH.B), with the study's SM_GR_Stone1-4 placed by the study's own rule on the
Loose areas. Those three are normal-mapped only. Close.png and OnFoot.png: the transition ground continued to 40 x 40 m
(the tile and the paths repeat; the study's stones along the road band to x 40), truly displaced by
lerp(Loose B x 0.8 cm, Packed B x 0.5 cm, p) with Cycles adaptive subdivision (simple, 1 px dicing), shaded by the baked
normals in the flat ground's frame (an object-space normal map, as POM shades), so the geometry adds parallax, occlusion,
silhouettes and shadows only; the stones sit on the displaced surface. Close.png: 0.6 m up, 20 deg down, 60 mm, looking
across the y < 0 path (the view's centre on its inner p = 0.5 edge). OnFoot.png: the game's on-foot view, eye 1.7 m up,
looking along the paths 25 deg down, 90 deg horizontal FOV.

Run headless (Blender 5.1):
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 \
      --python Art/Blender/bake_gravel_dg1.py -- [stage=all|bake|render] [brush=dabs|road]
"""
import ast, bpy, json, math, random, struct, sys, time, zlib
import numpy as np
from pathlib import Path
from mathutils import Vector

T0 = time.time()
ROOT = Path(__file__).resolve().parents[2]
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def arg(name, default):
    return next((a.split('=', 1)[1] for a in ARGS if a.startswith(name + '=')), default)


STAGE = arg('stage', 'all')
BRUSH = arg('brush', 'dabs')
STUDY = ROOT / 'Art/Export/GravelRoadStudy/04'
OUT = ROOT / 'Art/Export/GravelDG1'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'Art'))
import bake_gravel_orh as orh

N = 2048
TILE_M = 2.0
TEXEL_CM = TILE_M * 100.0 / N
SEED = 290929                      # the study's
PRE = 'T_GV_'
SETS = [('Loose', 1.0), ('Packed', 0.32)]   # the study's vertex alpha: off the path, the wheel path's centre (1 - 0.68)
STONE_SCALE, GRIT_SCALE, DISTORT_SCALE = 13, 34, 16
PATCH_LATTICE = 2                  # the study's 1.15 per metre -> 1.0 (2 periods on 2 m)
DAB_SIGMA_CM = (3.0, 0.55)
DAB_BINS = 18
DRY_ROUGH = 0.9
PATH_SIGMA_M = 0.185
# Phase A3: the parallax height (Height PNG, ORH.B) per stone (parallax_heights). The colour and normal bakes don't use it.
TOP_RANGE = {'Loose': (0.35, 1.0), 'Packed': (0.25, 0.7)}   # a stone's centre height, the same draw u for both sets
TOP_SKEW = 1.0                      # centre = lo + (hi - lo) x u^skew; uniform already puts 31 % of Loose stones at 0.35-0.55
TILT_RISE = (0.15, 0.45)            # the tilted top's rise across the stone's width, of the range; random azimuth
F1_OUT, EDGE_IN = 0.56, 0.015       # a stone's footprint: F1 < 0.56 cells and 0.015 cells inside its Voronoi edges
TILT_WIDTH = 2 * F1_OUT             # the stone's width (cells) the rise is measured across
SIDE_SLOPE = 0.06                   # the sides: 6 % of the range per texel inward from the footprint (the cap itself)
CHIP_RAISE = (0.05, 0.3)            # each chip cell raised by this, on the matrix
MATRIX = (0.05, 0.025, 3.0)         # the matrix: 0.05 + 0.025 x unit noise (3 cm features), clamped to 0-0.1


def say(msg):
    print('GRAVEL_DG1 %6.1f s  %s' % (time.time() - T0, msg), flush=True)


def rel(p):
    return str(Path(p).relative_to(ROOT)).replace('\\', '/')


# ---------------------------------------------------------------- files and metrics (export_mud_wet.py's)
def write_png(path, arr, bits):
    """arr (h, w) grey or (h, w, 3), floats 0..1, row 0 = the bottom (Blender's pixels); written top row first."""
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


def read(path):
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


def linear_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= .0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - .055)


def seam_ratio(img):
    inner = .5 * (np.mean(np.abs(np.diff(img, axis=0))) + np.mean(np.abs(np.diff(img, axis=1))))
    edge = .5 * (np.mean(np.abs(img[0, :] - img[-1, :])) + np.mean(np.abs(img[:, 0] - img[:, -1])))
    return float(edge / max(inner, 1e-12))


def seam_z(img):
    rows = np.abs(np.diff(img, axis=0)).mean(1)
    cols = np.abs(np.diff(img, axis=1)).mean(0)
    er = np.abs(img[0, :] - img[-1, :]).mean()
    ec = np.abs(img[:, 0] - img[:, -1]).mean()
    return round(float((er - rows.mean()) / max(rows.std(), 1e-12)), 2), round(float((ec - cols.mean()) / max(cols.std(), 1e-12)), 2)


def gauss(a, sigma_px):
    k = np.hypot(np.fft.fftfreq(a.shape[0])[:, None], np.fft.rfftfreq(a.shape[1])[None, :])
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (math.pi * sigma_px * k) ** 2), s=a.shape)


def coherence(a, cm_per_px):
    """(whole tile, mean over 10 cm neighbourhoods) of the structure tensor's coherence: 0 no direction, 1 stripes."""
    ax = (np.roll(a, -1, 1) - np.roll(a, 1, 1)) * .5
    ay = (np.roll(a, -1, 0) - np.roll(a, 1, 0)) * .5
    jxx, jyy, jxy = ax * ax, ay * ay, ax * ay
    whole = math.hypot(jxx.mean() - jyy.mean(), 2 * jxy.mean()) / max(jxx.mean() + jyy.mean(), 1e-12)
    s = 10.0 / cm_per_px / 2.0
    lxx, lyy, lxy = gauss(jxx, s), gauss(jyy, s), gauss(jxy, s)
    local = np.hypot(lxx - lyy, 2 * lxy) / np.maximum(lxx + lyy, 1e-12)
    return round(float(whole), 4), round(float(local.mean()), 4)


def pct(a, ps):
    return [round(float(x), 3) for x in np.percentile(a, ps)]


# ---------------------------------------------------------------- bakes
def plane(name, size_m, uv_scale=1.0):
    me = bpy.data.meshes.new(name)
    h = size_m / 2
    me.from_pydata([(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        v = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((v.x + h) / size_m * uv_scale, (v.y + h) / size_m * uv_scale)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def bake(ob, mat, kind, socket, size, name):
    """EMIT of socket, or the NORMAL of the material's Principled BSDF, into a float image: (size, size, 3), row 0 bottom."""
    ns, ls = mat.node_tree.nodes, mat.node_tree.links
    out = next(n for n in ns if n.type == 'OUTPUT_MATERIAL')
    p = next(n for n in ns if n.type == 'BSDF_PRINCIPLED')
    im = bpy.data.images.new(name, size, size, alpha=False, float_buffer=True)
    im.colorspace_settings.name = 'Non-Color'
    tgt = ns.get('GT bake target') or ns.new('ShaderNodeTexImage')
    tgt.name = 'GT bake target'
    tgt.image = im
    for n in ns:
        n.select = False
    tgt.select = True
    ns.active = tgt
    for link in list(out.inputs['Surface'].links):
        ls.remove(link)
    if kind == 'EMIT':
        em = ns.get('GT bake emission') or ns.new('ShaderNodeEmission')
        em.name = 'GT bake emission'
        for link in list(em.inputs['Color'].links):
            ls.remove(link)
        ls.new(socket, em.inputs['Color'])
        ls.new(em.outputs[0], out.inputs['Surface'])
    else:
        ls.new(p.outputs[0], out.inputs['Surface'])
    if not ob.data.materials or ob.data.materials[0] != mat:
        ob.data.materials.clear()
        ob.data.materials.append(mat)
    for o in bpy.context.scene.objects:
        o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type=kind)
    a = np.empty(size * size * 4, np.float32)
    im.pixels.foreach_get(a)
    arr = a.reshape(size, size, 4)[..., :3].astype(np.float64)
    bpy.data.images.remove(im)
    return arr


def noise_quantiles():
    """Blender 5.1's own Noise texture values at the study's settings (3D fBm, normalised, roughness 0.5, lacunarity 2,
    z = 0): detail 0 Fac and Color R/G/B, detail 1 Fac, point-sampled over 256 x 256 lattice cells by EMIT bakes."""
    ob = plane('Noise sampler', 1.0)
    mat = bpy.data.materials.new('Noise sampler')
    mat.use_nodes = True
    ns, ls = mat.node_tree.nodes, mat.node_tree.links
    uv = ns.new('ShaderNodeUVMap')
    uv.uv_map = 'UVMap'
    sc = ns.new('ShaderNodeVectorMath')
    sc.operation = 'SCALE'
    sc.inputs['Scale'].default_value = 256.0
    ls.new(uv.outputs[0], sc.inputs[0])
    n0, n1 = ns.new('ShaderNodeTexNoise'), ns.new('ShaderNodeTexNoise')
    for n, d in ((n0, 0.0), (n1, 1.0)):
        n.inputs['Scale'].default_value = 1.0
        n.inputs['Detail'].default_value = d
        ls.new(sc.outputs[0], n.inputs['Vector'])
    comb = ns.new('ShaderNodeCombineColor')
    ls.new(n0.outputs['Fac'], comb.inputs[0])
    ls.new(n1.outputs['Fac'], comb.inputs[1])
    col = bake(ob, mat, 'EMIT', n0.outputs['Color'], 1024, 'noise color d0')
    fac = bake(ob, mat, 'EMIT', comb.outputs[0], 1024, 'noise fac d0 d1')
    bpy.data.objects.remove(ob)
    qs = np.linspace(0, 1, 2001)
    return dict(fac0=np.quantile(fac[..., 0], qs), fac1=np.quantile(fac[..., 1], qs),
                col_r=np.quantile(col[..., 0], qs), col_g=np.quantile(col[..., 1], qs), col_b=np.quantile(col[..., 2], qs))


# ---------------------------------------------------------------- periodic fields (numpy), row 0 = v = 0 (Blender's)
def match(a, q):
    """a's values replaced, rank for rank, by the distribution whose quantiles (at linspace(0, 1)) are q."""
    order = np.argsort(a, axis=None)
    u = np.empty(a.size)
    u[order] = (np.arange(a.size) + .5) / a.size
    return np.interp(u, np.linspace(0, 1, len(q)), q).reshape(a.shape)


def perlin(px, py, rng):
    """Gradient noise periodic over the tile with px x py lattice periods (quintic fade)."""
    ang = rng.uniform(0, 2 * math.pi, (py, px))
    gx, gy = np.cos(ang), np.sin(ang)
    u = (np.arange(N) + .5) / N * px
    v = (np.arange(N) + .5) / N * py
    i0 = np.floor(u).astype(np.int64)
    j0 = np.floor(v).astype(np.int64)
    fu, fv = (u - i0)[None, :], (v - j0)[:, None]
    i0 %= px
    j0 %= py
    i1, j1 = (i0 + 1) % px, (j0 + 1) % py

    def fade(t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def d(jj, ii, ox, oy):
        return gx[jj][:, ii] * (fu - ox) + gy[jj][:, ii] * (fv - oy)
    su, sv = fade(fu), fade(fv)
    a = d(j0, i0, 0, 0) * (1 - su) + d(j0, i1, 1, 0) * su
    b = d(j1, i0, 0, 1) * (1 - su) + d(j1, i1, 1, 1) * su
    return a * (1 - sv) + b * sv


def voronoi(wx, wy, scale, rng):
    """Blender's 2D Voronoi (randomness 1, Euclidean) on a cell grid wrapped over the tile: F1 distance, the closest
    cell's colour (3 uniform values) and the distance to the edge, with Blender's 3x3 searches."""
    cells = int(round(scale * TILE_M))
    jit = rng.random((cells, cells, 2))
    colour = rng.random((cells, cells, 3))
    px, py = wx * scale, wy * scale
    cx, cy = np.floor(px), np.floor(py)
    fx, fy = px - cx, py - cy
    cx, cy = cx.astype(np.int64), cy.astype(np.int64)
    best = np.full(px.shape, 8.0)
    vcx, vcy = np.zeros(px.shape), np.zeros(px.shape)
    bx, by = np.zeros(px.shape, np.int64), np.zeros(px.shape, np.int64)
    offs = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    for dx, dy in offs:
        ix, iy = (cx + dx) % cells, (cy + dy) % cells
        vx = dx + jit[iy, ix, 0] - fx
        vy = dy + jit[iy, ix, 1] - fy
        dd = vx * vx + vy * vy
        m = dd < best
        best[m], vcx[m], vcy[m], bx[m], by[m] = dd[m], vx[m], vy[m], ix[m], iy[m]
    edge = np.full(px.shape, 8.0)
    for dx, dy in offs:
        ix, iy = (cx + dx) % cells, (cy + dy) % cells
        vx = dx + jit[iy, ix, 0] - fx
        vy = dy + jit[iy, ix, 1] - fy
        ex, ey = vx - vcx, vy - vcy
        l2 = ex * ex + ey * ey
        ok = l2 > .0001
        inv = np.where(ok, 1 / np.sqrt(np.maximum(l2, 1e-12)), 0)
        de = ((vcx + vx) * .5 * ex + (vcy + vy) * .5 * ey) * inv
        np.minimum(edge, np.where(ok, de, 8.0), out=edge)
    return np.sqrt(best), colour[by, bx], edge, dict(cells=cells, id=by * cells + bx, dx=-vcx, dy=-vcy)


def dab_field(rng):
    """Paint dabs with no dominant direction: impulses (normal amplitudes) at random texels, each orientation bin's set
    convolved (periodic, in the Fourier domain) with an anisotropic Gaussian of DAB_SIGMA_CM turned to that bin."""
    sl, sw = DAB_SIGMA_CM[0] / TEXEL_CM, DAB_SIGMA_CM[1] / TEXEL_CM
    count = int(6 * (TILE_M * 100) ** 2 / (2 * math.pi * DAB_SIGMA_CM[0] * DAB_SIGMA_CM[1]))
    fy = np.fft.fftfreq(N)[:, None]
    fx = np.fft.rfftfreq(N)[None, :]
    acc = np.zeros((N, N // 2 + 1), complex)
    for b in range(DAB_BINS):
        th = math.pi * (b + rng.random()) / DAB_BINS
        k = count // DAB_BINS
        imp = np.zeros((N, N))
        np.add.at(imp, (rng.integers(0, N, k), rng.integers(0, N, k)), rng.standard_normal(k))
        kl = fx * math.cos(th) + fy * math.sin(th)
        kw = -fx * math.sin(th) + fy * math.cos(th)
        acc += np.fft.rfft2(imp) * np.exp(-2 * math.pi ** 2 * (sl * sl * kl * kl + sw * sw * kw * kw))
    return np.fft.irfft2(acc, s=(N, N)), count


def build_fields(q):
    rng = np.random.default_rng(SEED)
    c = (np.arange(N) + .5) / N * TILE_M
    X, Y = np.meshgrid(c, c)
    lat = int(DISTORT_SCALE * TILE_M)
    cr = match(perlin(lat, lat, rng), q['col_r'])
    cg = match(perlin(lat, lat, rng), q['col_g'])
    wx, wy = X + (cr - .5) * .026, Y + (cg - .5) * .026          # the study's 'Chipped outlines' warp
    s_f1, s_col, s_edge, s_ext = voronoi(wx, wy, STONE_SCALE, rng)
    say('stone Voronoi (%d cells)' % int(STONE_SCALE * TILE_M) ** 2)
    g_f1, g_col, g_edge, g_ext = voronoi(wx, wy, GRIT_SCALE, rng)
    say('chip Voronoi (%d cells)' % int(GRIT_SCALE * TILE_M) ** 2)
    patch = match(perlin(PATCH_LATTICE, PATCH_LATTICE, rng) + .5 * perlin(2 * PATCH_LATTICE, 2 * PATCH_LATTICE, rng), q['fac1'])
    if BRUSH == 'road':
        brush, dabs = match(perlin(int(8 * TILE_M), int(48 * TILE_M), rng), q['fac0']), None
    else:
        raw, dabs = dab_field(rng)
        brush = match(raw, q['fac0'])
    say('noise fields')
    return dict(A=np.stack([s_f1, s_edge, g_f1], -1), B=np.stack([g_edge, patch, brush], -1),
                C=np.stack([s_col[..., 0], s_col[..., 2], g_col[..., 0]], -1), dabs=dabs,
                geo=dict(s_f1=s_f1, s_edge=s_edge, s_b=s_col[..., 2], s=s_ext, g_f1=g_f1, g_edge=g_edge, g=g_ext))


def smootherstep01(x, a, b):
    """Blender's Map Range SMOOTHERSTEP (clamped) from a..b onto 0..1."""
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * t * (t * (t * 6 - 15) + 10)


def parallax_heights(geo):
    """Phase A3: the parallax height per set (0-1 in units both sets share), from the study's own stone and chip cells.
    - The matrix: 0.05 + 0.025 x periodic unit noise of 3 cm features, clamped to 0-0.1.
    - Chips: the study's chip shape (bevel x size, as its fine bump) raised by a random 0.05-0.3 per chip cell, on the matrix.
    - Broad stones, keyed by their wrapped cell id: a top that is a tilted plane, centre(id) + rise(id) x (p - point) . dir(id)
      / width, the centre 0.35-1.0 (Packed 0.25-0.7, the same draw, so the same stone pressed in) uniform, the rise
      0.15-0.45 of the range across the stone width (2 x 0.56 cells), a random azimuth; the sides fall at 6 % of the range per
      texel to the footprint (F1 0.56, 0.015 cells inside the Voronoi edges); scaled by the study's 'present'. A stone whose top
      would pass 1 is shifted down so its highest texel is 1.
    - The height is the higher of the stones and the chips-on-matrix.
    Returns per set: h, the facet mask (the stone tops: a fully present stone's tilted top, where it is the surface), the
    stone id per texel (-1 where no stone is the surface) and the per-stone numbers."""
    rng = np.random.default_rng(SEED + 3)
    sc, gc = geo['s']['cells'], geo['g']['cells']
    u = rng.random(sc * sc) ** TOP_SKEW
    rise = rng.uniform(TILT_RISE[0], TILT_RISE[1], sc * sc)
    az = rng.uniform(0, 2 * math.pi, sc * sc)
    chip_raise = rng.uniform(CHIP_RAISE[0], CHIP_RAISE[1], gc * gc)
    noise = gauss(rng.standard_normal((N, N)), MATRIX[2] / 4.0 / TEXEL_CM)
    matrix = np.clip(MATRIX[0] + MATRIX[1] * noise / noise.std(), 0, .1)
    chips = smootherstep01(geo['g_edge'], .025, .13) * (1 - smootherstep01(geo['g_f1'], .28, .61))
    fine = matrix + chips * chip_raise[geo['g']['id']]
    present = np.clip((geo['s_b'] - .26) / .13, 0, 1)
    texels_per_cell = N / (STONE_SCALE * TILE_M)
    side = SIDE_SLOPE * np.maximum(np.minimum(geo['s_edge'] - EDGE_IN, F1_OUT - geo['s_f1']), 0) * texels_per_cell
    sid = geo['s']['id']
    along = (geo['s']['dx'] * np.cos(az)[sid] + geo['s']['dy'] * np.sin(az)[sid]) / TILT_WIDTH
    out = {}
    for set_name, _ in SETS:
        lo, hi = TOP_RANGE[set_name]
        centre = lo + (hi - lo) * u
        plane = centre[sid] + rise[sid] * along
        stone = present * np.minimum(plane, side)
        top = np.zeros(sc * sc)
        np.maximum.at(top, sid.ravel(), stone.ravel())
        shift = np.maximum(top - 1.0, 0)
        plane = plane - shift[sid]
        stone = np.maximum(present * np.minimum(plane, side), 0)
        h = np.clip(np.maximum(fine, stone), 0, 1)
        surface = (stone >= fine) & (stone > 0)
        facet = surface & (present > .99) & (plane <= side)
        live = np.unique(sid[surface])
        c = centre - shift
        out[set_name] = dict(h=h, facet=facet, stone_id=np.where(surface, sid, -1), numbers=dict(
            stones_present=int(live.size), centre_range=[lo, hi], centre_p5_50_95=pct(c[live], [5, 50, 95]),
            centre_share_0_35_0_55=round(float(((c[live] >= .35) & (c[live] <= .55)).mean()), 3),
            rise_p5_50_95=pct(rise[live], [5, 50, 95]), shifted_down=int((shift[live] > 0).sum()),
            facet_share=round(float(facet.mean()), 4), stone_surface_share=round(float(surface.mean()), 4),
            matrix_min_max=[round(float(matrix.min()), 3), round(float(matrix.max()), 3)],
            chip_top_p50_95=pct((fine)[chips > .9], [50, 95])))
    return out


def field_image(name, rgb):
    im = bpy.data.images.new(name, N, N, alpha=True, float_buffer=True)
    im.colorspace_settings.name = 'Non-Color'
    a = np.ones((N, N, 4), np.float32)
    a[..., :3] = rgb
    im.pixels.foreach_set(a.ravel())
    im.update()
    return im


# ---------------------------------------------------------------- the study's graph (gravel_road_material.build), its
# procedurals replaced by the periodic field images; every other node and number as the study's.
def study_shader(name, images, alpha):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    ns, ls = mat.node_tree.nodes, mat.node_tree.links
    p = next(n for n in ns if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Roughness'].default_value = DRY_ROUGH

    def node(kind, label):
        n = ns.new(kind)
        n.label = label
        return n

    def wire(value, socket):
        if isinstance(value, (int, float, tuple, list)):
            socket.default_value = value
        else:
            ls.new(value, socket)

    def math_(op, a, b=0):
        n = node('ShaderNodeMath', op)
        n.operation = op
        wire(a, n.inputs[0])
        wire(b, n.inputs[1])
        return n.outputs[0]

    def mix(a, b, f):
        n = node('ShaderNodeMixRGB', 'Paint blend')
        wire(f, n.inputs[0])
        wire(a, n.inputs[1])
        wire(b, n.inputs[2])
        return n.outputs[0]

    def ramp(value, entries, interpolation='LINEAR'):
        n = node('ShaderNodeValToRGB', 'Restricted painted palette')
        n.color_ramp.interpolation = interpolation
        for i, (pos, col) in enumerate(entries):
            e = n.color_ramp.elements[i] if i < 2 else n.color_ramp.elements.new(pos)
            e.position = pos
            e.color = (*col, 1)
        wire(value, n.inputs[0])
        return n.outputs[0]

    def map_range(value, f0, f1, t0, t1, interp, label):
        n = node('ShaderNodeMapRange', label)
        n.interpolation_type = interp
        n.clamp = True
        wire(value, n.inputs['Value'])
        n.inputs['From Min'].default_value, n.inputs['From Max'].default_value = f0, f1
        n.inputs['To Min'].default_value, n.inputs['To Max'].default_value = t0, t1
        return n.outputs[0]

    uv = node('ShaderNodeUVMap', 'Tile coordinates (one period)')
    uv.uv_map = 'UVMap'

    def field(key, closest):
        t = node('ShaderNodeTexImage', key)
        t.image = images[key]
        t.interpolation = 'Closest' if closest else 'Linear'
        t.extension = 'REPEAT'
        wire(uv.outputs[0], t.inputs['Vector'])
        s = node('ShaderNodeSeparateColor', key)
        wire(t.outputs['Color'], s.inputs[0])
        return s.outputs
    A, B, C = field('A', False), field('B', False), field('C', True)
    s_f1, s_edge, g_f1 = A[0], A[1], A[2]
    g_edge, patch, brush = B[0], B[1], B[2]
    s_r, s_b, g_r = C[0], C[1], C[2]
    va = node('ShaderNodeValue', 'Wheel wear (the study vertex alpha)')
    va.outputs[0].default_value = alpha
    wear = math_('MULTIPLY', math_('SUBTRACT', 1, va.outputs[0]), math_('ADD', .55, math_('MULTIPLY', patch, .6)))
    loose = math_('SUBTRACT', 1, math_('MULTIPLY', wear, 1.1))
    stone_color = ramp(s_r, [(0, (.20, .235, .25)), (.24, (.29, .315, .31)), (.49, (.38, .375, .335)), (.75, (.26, .275, .265)),
                             (.91, (.43, .415, .355))], 'CONSTANT')
    bevel = map_range(s_edge, .015, .115, 0, 1, 'SMOOTHERSTEP', 'Broad stone crown')
    chip = map_range(s_f1, .25, .64, 1, 0, 'SMOOTHERSTEP', 'Broken gravel chip size')
    present = map_range(s_b, .26, .39, 0, 1, 'LINEAR', 'Sparse painted chips')
    chip_height = math_('MULTIPLY', math_('MULTIPLY', bevel, chip), present)
    coverage = math_('MULTIPLY', chip_height, math_('ADD', .28, math_('MULTIPLY', loose, .72)))
    base = ramp(patch, [(.23, (.19, .205, .195)), (.75, (.285, .29, .26))])
    grit_color = ramp(g_r, [(0, (.15, .177, .18)), (.30, (.245, .255, .24)), (.65, (.325, .31, .267)), (.88, (.21, .23, .23))], 'CONSTANT')
    grit_bevel = map_range(g_edge, .025, .13, 0, 1, 'SMOOTHERSTEP', 'Small chip flat face')
    grit_size = map_range(g_f1, .28, .61, 1, 0, 'SMOOTHERSTEP', 'Small chip coverage')
    grit_height = math_('MULTIPLY', grit_bevel, grit_size)
    grit_opacity = math_('MULTIPLY', grit_height, math_('ADD', .52, math_('MULTIPLY', loose, .22)))
    base = mix(base, grit_color, grit_opacity)
    road = mix(base, stone_color, coverage)
    wash = ramp(brush, [(.30, (.89, .91, .93)), (.70, (1.02, 1.01, .98))])
    multiply = node('ShaderNodeMixRGB', 'Subtle surface brushwork')
    multiply.blend_type = 'MULTIPLY'
    multiply.inputs[0].default_value = .6
    wire(road, multiply.inputs[1])
    wire(wash, multiply.inputs[2])
    road = multiply.outputs[0]
    wire(road, p.inputs['Base Color'])
    bump = node('ShaderNodeBump', 'Stone bevel relief')
    bump.inputs['Distance'].default_value = .006
    bump.inputs['Strength'].default_value = .42
    fine_bump = node('ShaderNodeBump', 'Embedded grit relief')
    fine_bump.inputs['Distance'].default_value = .002
    fine_bump.inputs['Strength'].default_value = .3
    h_fine = math_('MULTIPLY', grit_height, math_('SUBTRACT', 1, coverage))
    h_broad = math_('MULTIPLY', chip_height, math_('ADD', .35, math_('MULTIPLY', loose, .65)))
    wire(h_fine, fine_bump.inputs['Height'])
    wire(fine_bump.outputs['Normal'], bump.inputs['Normal'])
    wire(h_broad, bump.inputs['Height'])
    wire(bump.outputs['Normal'], p.inputs['Normal'])
    p.inputs['Specular IOR Level'].default_value = .12
    # For the bakes: the bumps' effective height in cm (strength x distance x height) and the study's coverage numbers.
    height_cm = math_('MULTIPLY', math_('ADD', math_('MULTIPLY', h_broad, .42 * .006), math_('MULTIPLY', h_fine, .3 * .002)), 100)
    derive = node('ShaderNodeCombineColor', 'coverage, chip opacity, broad bump height')
    wire(coverage, derive.inputs[0])
    wire(grit_opacity, derive.inputs[1])
    wire(h_broad, derive.inputs[2])
    return mat, dict(color=road, height=height_cm, derive=derive.outputs[0], probe=A[0])


def stage_bake():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 1
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.render.bake.margin = 8
    scene.render.bake.normal_space = 'TANGENT'
    scene.render.bake.normal_g = 'NEG_Y'
    q = noise_quantiles()
    say('Blender noise quantiles: fac0 p1/50/99 %s, fac1 %s' % (np.round(q['fac0'][[20, 1000, 1980]], 3), np.round(q['fac1'][[20, 1000, 1980]], 3)))
    F = build_fields(q)
    images = {k: field_image('GV field ' + k, F[k]) for k in 'ABC'}
    tile = plane('Gravel tile', TILE_M)
    raw = {}
    for set_name, alpha in SETS:
        mat, out = study_shader('M_GV_Study_' + set_name, images, alpha)
        if set_name == 'Loose':
            probe = bake(tile, mat, 'EMIT', out['probe'], N, 'probe')[..., 0]
            probe_err = float(np.abs(probe - F['A'][..., 0]).max())
            say('field read-back max error %.2e' % probe_err)
        raw[set_name] = dict(color=bake(tile, mat, 'EMIT', out['color'], N, set_name + ' color'),
                             derive=bake(tile, mat, 'EMIT', out['derive'], N, set_name + ' derive'),
                             normal=bake(tile, mat, 'NORMAL', None, N, set_name + ' normal'))
        say('baked ' + set_name)
    H = parallax_heights(F['geo'])
    say('parallax heights: %s' % json.dumps({k: v['numbers'] for k, v in H.items()}))
    manifest = dict(
        source='%s (revision 04, Art/Blender/gravel_road_material.py), baked by Art/Blender/bake_gravel_dg1.py' % rel(STUDY),
        plan='docs/DEFORMABLE_GRAVEL_PLAN.md DG1 item 1', tile_m=TILE_M, size=N, texel_cm=round(TEXEL_CM, 4), mirror=False,
        normal='DirectX tangent (green = -Y), Cycles NORMAL bake of the study\'s two chained bumps',
        periodic_inputs=dict(
            stones='Voronoi F1 / distance to edge, 13 per metre: %d x %d cells wrapped' % (STONE_SCALE * TILE_M, STONE_SCALE * TILE_M),
            chips='Voronoi, 34 per metre: %d x %d cells wrapped' % (GRIT_SCALE * TILE_M, GRIT_SCALE * TILE_M),
            warp='noise 16 per metre (32 periods), Color R/G matched to Blender 5.1 Noise detail 0 Color R/G',
            wash='noise detail 1 at %.2f per metre (study 1.15; %d periods), matched to Blender 5.1 Noise detail 1 Fac' % (PATCH_LATTICE / TILE_M, PATCH_LATTICE),
            dabs=('study road-aligned (8 x, 48 y): 16 x 96 periods, matched to detail 0 Fac' if BRUSH == 'road' else
                  '%d dabs, sigma %.1f x %.2f cm, random orientation (%d bins), matched to Blender 5.1 Noise detail 0 Fac (study: 6:1 along the road)'
                  % (F['dabs'], DAB_SIGMA_CM[0], DAB_SIGMA_CM[1], DAB_BINS)),
            field_readback_max_error=probe_err),
        height=dict(definition='phase A3: per-stone parallax height (bake_gravel_dg1.parallax_heights), 0-1 in units both sets share; '
                               'Height PNG = the sharp height, ORH.B = its soft rims; the colour and normal bakes are from the study shader, unchanged',
                    stones=dict(centre_skew='lo + (hi - lo) x u^%.2f' % TOP_SKEW, centre_range=TOP_RANGE, tilt_rise=TILT_RISE, tilt_width_cells=TILT_WIDTH,
                                footprint='F1 < %.2f cells, %.3f cells inside the Voronoi edges' % (F1_OUT, EDGE_IN), side_slope_per_texel=SIDE_SLOPE),
                    chips=dict(raise_range=CHIP_RAISE, shape='the study chip shape (bevel 0.025-0.13 x size 0.28-0.61)'),
                    matrix='0.05 + 0.025 x unit noise (3 cm features), clamped 0-0.1'),
        roughness_note=('the study dry roughness is one constant, 0.9 (ground_material_v2: 0.9 - 0.3 x wetness; dry wetness 0); '
                        'DG1 item 1 decision: 0.9 - 0.16 x smoothstep(0.45, 0.9, h) on the sharp height, Packed - 0.05, floor 0.55 '
                        '(Rough PNG = ORH.G)'),
        parallax_depth_cm=dict(orh.PARALLAX_DEPTH_CM, note='ORH.B 0-1 (units both sets share) x depth; Packed B reaches %.3f, so %.2f cm'
                               % (H['Packed']['h'].max(), H['Packed']['h'].max() * orh.PARALLAX_DEPTH_CM['Packed'])),
        sets={})
    for set_name, alpha in SETS:
        r = raw[set_name]
        h01 = H[set_name]['h']
        files = {}
        for suffix, arr, bits in [('Color', linear_to_srgb(r['color']), 8), ('Normal', r['normal'], 8), ('Height', h01, 16)]:
            path = OUT / ('%s%s%s.png' % (PRE, set_name, suffix))
            write_png(path, arr, bits)
            files[suffix] = path
        back = {k: read(p) for k, p in files.items()}
        h_back = back['Height'][..., 0]
        files['Rough'] = OUT / ('%s%sRough.png' % (PRE, set_name))
        write_png(files['Rough'], orh.roughness(h_back, set_name), 8)
        back['Rough'] = read(files['Rough'])
        rough_back = back['Rough'][..., 0]
        ao, g, b, ostats = orh.pack(h_back, set_name, TEXEL_CM, top_mask=H[set_name]['facet'], stone_id=H[set_name]['stone_id'],
                                    top_definition='the tilted tops of fully present stones where they are the surface')
        write_png(OUT / ('%s%sAO.png' % (PRE, set_name)), ao, 8)
        write_png(OUT / ('%s%sORH.png' % (PRE, set_name)), np.stack([ao, g, b], -1), 8)
        files['AO'] = OUT / ('%s%sAO.png' % (PRE, set_name))
        files['ORH'] = OUT / ('%s%sORH.png' % (PRE, set_name))
        back['ORH'] = read(files['ORH'])
        seams = {}
        for k, chans in [('Color', 'RGB'), ('Normal', 'RGB'), ('Rough', 'R'), ('Height', 'R'), ('ORH', 'RGB')]:
            a = back[k]
            seams[k] = {c: dict(ratio=round(seam_ratio(a[..., i]), 3), edge_z_rows_cols=seam_z(a[..., i])) for i, c in enumerate(chans)}
        lin = srgb_to_linear(back['Color'][..., :3])
        lum = lin @ np.array([.2126, .7152, .0722])
        lstar = np.where(lum > .008856, 116 * np.cbrt(lum) - 16, 903.3 * lum)
        d = r['derive']
        hcm = h_back * orh.PARALLAX_DEPTH_CM[set_name]
        manifest['sets'][set_name] = dict(
            study_vertex_alpha=alpha, files={k: rel(p) for k, p in files.items()},
            height_range_cm=[round(float(hcm.min()), 4), round(float(hcm.max()), 4)], height_cm_p50_95_99=pct(hcm, [50, 95, 99]),
            parallax_stones=H[set_name]['numbers'],
            roughness_p5_50_95=dict(rough_png=pct(rough_back, [5, 50, 95]), orh_g=pct(back['ORH'][..., 1], [5, 50, 95])),
            colour=dict(linear_mean=[round(float(x), 4) for x in lin.reshape(-1, 3).mean(0)], luminance_mean=round(float(lum.mean()), 4),
                        luminance_p5_50_95=[round(float(x), 4) for x in np.percentile(lum, [5, 50, 95])], lstar_mean=round(float(lstar.mean()), 2)),
            study_numbers=dict(broad_stone_coverage_mean=round(float(d[..., 0].mean()), 4), stone_face_share_coverage_over_0_5=round(float((d[..., 0] > .5).mean()), 4),
                               chip_opacity_mean=round(float(d[..., 1].mean()), 4), broad_bump_height_mean=round(float(d[..., 2].mean()), 4),
                               broad_bump_height_p95=round(float(np.percentile(d[..., 2], 95)), 4)),
            seams=seams,
            direction=dict(note='structure-tensor coherence (whole tile, mean over 10 cm): 0 no direction, 1 stripes',
                           height=coherence(h_back, TEXEL_CM), parallax_height=coherence(back['ORH'][..., 2], TEXEL_CM),
                           colour_luminance=coherence(lum, TEXEL_CM)),
            orh=ostats)
        say('%s: %s' % (set_name, json.dumps(dict(lum=manifest['sets'][set_name]['colour']['luminance_mean'],
                                                   cov=manifest['sets'][set_name]['study_numbers'], dir=manifest['sets'][set_name]['direction']))))
    L, P = manifest['sets']['Loose'], manifest['sets']['Packed']
    manifest['packed_vs_loose'] = dict(
        luminance=round(P['colour']['luminance_mean'] / L['colour']['luminance_mean'], 3),
        lstar=round(P['colour']['lstar_mean'] / L['colour']['lstar_mean'], 3),
        broad_stone_coverage=round(P['study_numbers']['broad_stone_coverage_mean'] / L['study_numbers']['broad_stone_coverage_mean'], 3),
        stone_face_share=round(P['study_numbers']['stone_face_share_coverage_over_0_5'] / max(L['study_numbers']['stone_face_share_coverage_over_0_5'], 1e-9), 3),
        chip_opacity=round(P['study_numbers']['chip_opacity_mean'] / L['study_numbers']['chip_opacity_mean'], 3),
        broad_bump_height=round(P['study_numbers']['broad_bump_height_mean'] / L['study_numbers']['broad_bump_height_mean'], 3),
        height_p95=round(P['height_cm_p50_95_99'][1] / max(L['height_cm_p50_95_99'][1], 1e-9), 3))
    tops = L['orh']['parallax_height']['stone_tops']
    manifest['gates'] = dict(loose_max_b=tops['max_b'], loose_texel_median_b_for_reference=tops.get('median_b'), **tops['gates'])
    manifest['track_blend'] = dict(rule='p = smoothstep(0.35, 0.7, T - 0.3 x (hL - mean(hL))), hL = Loose ORH.B',
                                   mean_hL=L['orh']['parallax_height']['mean_b'])
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    say('packed vs loose %s' % json.dumps(manifest['packed_vs_loose']))
    say('gates %s; mean(hL) %.4f' % (json.dumps(manifest['gates']), manifest['track_blend']['mean_hL']))
    say('wrote manifest.json')


# ---------------------------------------------------------------- renders
def study_functions():
    """build_road_ford_style.py's smooth / noise / edge, taken the way the study's build script takes them."""
    tree = ast.parse((ROOT / 'Art/Blender/build_road_ford_style.py').read_text())
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ['smooth', 'noise', 'edge']]
    env = {'math': math}
    exec(compile(ast.Module(body=fns, type_ignores=[]), 'existing-road-functions', 'exec'), env)
    return env['smooth'], env['noise'], env['edge']


def path_mask(s, t):
    c = .12 * math.sin(.29 * s)
    return max(math.exp(-((t - .784 - c) / PATH_SIGMA_M) ** 2), math.exp(-((t + .784 - c) / PATH_SIGMA_M) ** 2))


def render_material(kind, mean_hl):
    mat = bpy.data.materials.new('M_GV_Render_' + kind)
    mat.use_nodes = True
    ns, ls = mat.node_tree.nodes, mat.node_tree.links
    p = next(n for n in ns if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Specular IOR Level'].default_value = .5          # the plan's PBR: default specular (F0 0.04)
    uv = ns.new('ShaderNodeUVMap')
    uv.uv_map = 'UVMap'

    def tex(set_name, suffix, srgb=False):
        t = ns.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(str(OUT / ('%s%s%s.png' % (PRE, set_name, suffix))), check_existing=True)
        t.image.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
        t.extension = 'REPEAT'
        t.interpolation = 'Linear'
        ls.new(uv.outputs[0], t.inputs['Vector'])
        return t.outputs['Color']

    def sep(sock):
        s = ns.new('ShaderNodeSeparateColor')
        ls.new(sock, s.inputs[0])
        return s.outputs

    def m(op, a, b=0.0):
        n = ns.new('ShaderNodeMath')
        n.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                ls.new(v, n.inputs[i])
        return n.outputs[0]

    def mixc(f, a, b):
        n = ns.new('ShaderNodeMixRGB')
        ls.new(f, n.inputs[0])
        ls.new(a, n.inputs[1])
        ls.new(b, n.inputs[2])
        return n.outputs[0]
    disp = None
    if kind in ('Loose', 'Packed'):
        color, normal, rough = tex(kind, 'Color', True), tex(kind, 'Normal'), sep(tex(kind, 'ORH'))[1]
    else:
        lc, ln, lorh = tex('Loose', 'Color', True), tex('Loose', 'Normal'), sep(tex('Loose', 'ORH'))
        pc, pn, porh = tex('Packed', 'Color', True), tex('Packed', 'Normal'), sep(tex('Packed', 'ORH'))
        tc = ns.new('ShaderNodeTexCoord')
        xyz = ns.new('ShaderNodeSeparateXYZ')
        ls.new(tc.outputs['Object'], xyz.inputs[0])
        s, t = xyz.outputs[0], xyz.outputs[1]
        wob = m('MULTIPLY', m('SINE', m('MULTIPLY', s, .29)), .12)
        lanes = []
        for off in (.784, -.784):
            dd = m('DIVIDE', m('SUBTRACT', m('SUBTRACT', t, off), wob), PATH_SIGMA_M)
            lanes.append(m('EXPONENT', m('MULTIPLY', m('MULTIPLY', dd, dd), -1.0)))
        T = m('MAXIMUM', lanes[0], lanes[1])
        q = m('SUBTRACT', T, m('MULTIPLY', m('SUBTRACT', lorh[2], mean_hl), .3))     # T - 0.3 (hL - mean(hL))
        mr = ns.new('ShaderNodeMapRange')
        mr.interpolation_type = 'SMOOTHSTEP'
        mr.clamp = True
        ls.new(q, mr.inputs['Value'])
        mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = .35, .7
        pmask = mr.outputs[0]
        color, normal = mixc(pmask, lc, pc), mixc(pmask, ln, pn)
        rough = m('ADD', lorh[1], m('MULTIPLY', m('SUBTRACT', porh[1], lorh[1]), pmask))
        if kind == 'Close':        # lerp(Loose B x 1.0 cm, Packed B x 0.5 cm, p), in metres
            hl = m('MULTIPLY', lorh[2], orh.PARALLAX_DEPTH_CM['Loose'] / 100.0)
            hp = m('MULTIPLY', porh[2], orh.PARALLAX_DEPTH_CM['Packed'] / 100.0)
            disp = ns.new('ShaderNodeDisplacement')
            disp.inputs['Midlevel'].default_value = 0.0
            disp.inputs['Scale'].default_value = 1.0
            ls.new(m('ADD', hl, m('MULTIPLY', m('SUBTRACT', hp, hl), pmask)), disp.inputs['Height'])
            out = next(n for n in ns if n.type == 'OUTPUT_MATERIAL')
            ls.new(disp.outputs[0], out.inputs['Displacement'])
            try:
                mat.displacement_method = 'DISPLACEMENT'
            except AttributeError:
                mat.cycles.displacement_method = 'DISPLACEMENT'
    ls.new(color, p.inputs['Base Color'])
    ls.new(rough, p.inputs['Roughness'])
    n = sep(normal)
    comb = ns.new('ShaderNodeCombineColor')
    ls.new(n[0], comb.inputs[0])
    ls.new(m('SUBTRACT', 1.0, n[1]), comb.inputs[1])           # DirectX -> Blender's OpenGL green
    ls.new(n[2], comb.inputs[2])
    nm = ns.new('ShaderNodeNormalMap')
    nm.space = 'OBJECT'           # the ground lies in the object's xy with u along x, v along y: the same as tangent space
                                  # on the flat ground; on the displaced patch it shades in the flat frame, as POM does
    ls.new(comb.outputs[0], nm.inputs['Color'])
    ls.new(nm.outputs[0], p.inputs['Normal'])
    return mat


def stage_render():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    with bpy.data.libraries.load(str(STUDY / 'GravelRoadStudy.blend')) as (src, dst):
        dst.worlds = ['Soft cool daylight']
        dst.objects = ['Directional daylight', 'SM_GR_Stone1', 'SM_GR_Stone2', 'SM_GR_Stone3', 'SM_GR_Stone4']
    scene.world = dst.worlds[0]
    sun = dst.objects[0]
    scene.collection.objects.link(sun)
    prototypes = dst.objects[1:]
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1440, 900, 100
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = 0
    scene.render.image_settings.file_format = 'PNG'
    # The ground: 6 m, x 0-6 along the paths, y -3..3, the tile 3 x 3 (UV = metres / 2).
    me = bpy.data.meshes.new('Gravel ground 3x3')
    me.from_pydata([(0, -3, 0), (6, -3, 0), (6, 3, 0), (0, 3, 0)], [], [(0, 1, 2, 3)])
    uvl = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        v = me.vertices[loop.vertex_index].co
        uvl.data[loop.index].uv = (v.x / TILE_M, (v.y + 3) / TILE_M)
    ground = bpy.data.objects.new('Gravel ground 3x3', me)
    scene.collection.objects.link(ground)
    bpy.ops.object.camera_add(location=(-1.5, 0, 1.7))
    cam = bpy.context.object
    pitch = math.radians(18)
    cam.rotation_euler = Vector((math.cos(pitch), 0, -math.sin(pitch))).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 30
    scene.camera = cam
    # The study's loose stones on the Loose areas of the transition, by the study's own rule (build_gravel_road_study.py).
    smooth, noise, edge = study_functions()
    R = random.Random(SEED)
    attempts = int(round(78000 / (71.8 * 6.5) * 5.8 * 5.8))
    stones = []
    for _ in range(attempts):
        s, t = R.uniform(.1, 5.9), R.uniform(-2.9, 2.9)
        lane = max(math.exp(-((t - .784 - .12 * math.sin(s * .29)) / .33) ** 2), math.exp(-((t + .784 - .12 * math.sin(s * .29)) / .35) ** 2))
        shoulder = smooth(1.1, 2.6, abs(t))
        middle = math.exp(-(t / .45) ** 2)
        patch = .5 + .5 * noise(s, t, 1.1)
        chance = (.075 + .42 * shoulder + .42 * middle) * (.35 + 1.0 * patch) * (1 - .86 * lane)
        if R.random() > chance or abs(t) > edge(s, t) + .48:
            continue
        width = R.uniform(.032, .087)
        if R.random() < .09 and shoulder > .5:
            width = R.uniform(.09, .13)
        kind = R.randrange(4)
        yaw = R.uniform(-math.pi, math.pi)
        rot = [math.radians(R.uniform(-8, 8)), math.radians(R.uniform(-8, 8)), yaw]
        scale = (width * R.uniform(.9, 1.35), width, width * R.uniform(.7, 1.1))
        if path_mask(s, t) > .35:          # Loose areas only: none where the path blend starts
            continue
        ob = bpy.data.objects.new('Loose gravel', prototypes[kind].data)
        ob.location, ob.rotation_euler, ob.scale = (s, t, .001), rot, scale
        ob.hide_render = True
        scene.collection.objects.link(ob)
        stones.append(ob)
    man_path = OUT / 'manifest.json'
    man = json.loads(man_path.read_text())
    mean_hl = man['track_blend']['mean_hL']
    n6 = len(stones)
    renders = {}
    for kind, name in [('Loose', 'Loose_3x3.png'), ('Packed', 'Packed_3x3.png'), ('Transition', 'Transition.png')]:
        ground.data.materials.clear()
        ground.data.materials.append(render_material(kind, mean_hl))
        for ob in stones:
            ob.hide_render = kind != 'Transition'
        scene.render.filepath = str(OUT / name)
        bpy.ops.render.render(write_still=True)
        renders[name] = rel(OUT / name)
        say('rendered ' + name)
    # Close.png and OnFoot.png: the transition ground continued to 40 x 40 m (the tile and the paths repeat), truly displaced
    # at the parallax depths with Cycles adaptive subdivision (simple, 1 px dicing); the stones sit on the displaced height.
    gm = bpy.data.meshes.new('Gravel displaced ground')
    step, gx0, gx1, gy0, gy1 = .5, 0.0, 40.0, -20.0, 20.0
    nx, ny = int((gx1 - gx0) / step), int((gy1 - gy0) / step)
    gm.from_pydata([(gx0 + i * step, gy0 + j * step, 0) for j in range(ny + 1) for i in range(nx + 1)], [],
                   [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(ny) for i in range(nx)])
    guv = gm.uv_layers.new(name='UVMap')
    for loop in gm.loops:
        v = gm.vertices[loop.vertex_index].co
        guv.data[loop.index].uv = (v.x / TILE_M, (v.y + 3) / TILE_M)
    disp_ob = bpy.data.objects.new('Gravel displaced ground', gm)
    scene.collection.objects.link(disp_ob)
    sub = disp_ob.modifiers.new('Dice', 'SUBSURF')
    sub.subdivision_type = 'SIMPLE'
    sub.use_adaptive_subdivision = True
    sub.adaptive_space = 'PIXEL'
    sub.adaptive_pixel_size = 1.0
    gm.materials.append(render_material('Close', mean_hl))
    ground.hide_render = True
    # More of the study's stones for the continued road (x 6-40), by the same rule, from their own stream.
    R2 = random.Random(SEED + 5)
    for _ in range(int(round(78000 / (71.8 * 6.5) * 33.9 * 6.5))):
        s, t = R2.uniform(6.0, 39.9), R2.uniform(-3.25, 3.25)
        lane = max(math.exp(-((t - .784 - .12 * math.sin(s * .29)) / .33) ** 2), math.exp(-((t + .784 - .12 * math.sin(s * .29)) / .35) ** 2))
        shoulder = smooth(1.1, 2.6, abs(t))
        middle = math.exp(-(t / .45) ** 2)
        patch = .5 + .5 * noise(s, t, 1.1)
        chance = (.075 + .42 * shoulder + .42 * middle) * (.35 + 1.0 * patch) * (1 - .86 * lane)
        if R2.random() > chance or abs(t) > edge(s, t) + .48:
            continue
        width = R2.uniform(.032, .087)
        if R2.random() < .09 and shoulder > .5:
            width = R2.uniform(.09, .13)
        kind = R2.randrange(4)
        yaw = R2.uniform(-math.pi, math.pi)
        rot = [math.radians(R2.uniform(-8, 8)), math.radians(R2.uniform(-8, 8)), yaw]
        scale = (width * R2.uniform(.9, 1.35), width, width * R2.uniform(.7, 1.1))
        if path_mask(s, t) > .35:
            continue
        ob = bpy.data.objects.new('Loose gravel', prototypes[kind].data)
        ob.location, ob.rotation_euler, ob.scale = (s, t, .001), rot, scale
        scene.collection.objects.link(ob)
        stones.append(ob)
    orh_l, orh_p = read(OUT / (PRE + 'LooseORH.png')), read(OUT / (PRE + 'PackedORH.png'))

    def texel(a, x, y):
        return a[int(((y + 3) / TILE_M % 1.0) * N) % N, int((x / TILE_M % 1.0) * N) % N, 2]
    for ob in stones:
        x, y = ob.location.x, ob.location.y
        hl = texel(orh_l, x, y)
        q = path_mask(x, y) - .3 * (hl - mean_hl)
        pp = min(1.0, max(0.0, (q - .35) / .35))
        pp = pp * pp * (3 - 2 * pp)
        hgt = (hl * orh.PARALLAX_DEPTH_CM['Loose'] * (1 - pp) + texel(orh_p, x, y) * orh.PARALLAX_DEPTH_CM['Packed'] * pp) / 100.0
        ob.location.z = hgt + .001
        ob.hide_render = False
    close_y = -.784 + .12 * math.sin(.29 * 3.0) + .15     # the y < 0 path's inner p = 0.5 edge at x = 3 (hL = mean)
    down = math.radians(20)
    cam.location = (3.0, close_y + .6 / math.tan(down), .6)
    cam.rotation_euler = Vector((0, -math.cos(down), -math.sin(down))).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 60
    scene.render.filepath = str(OUT / 'Close.png')
    bpy.ops.render.render(write_still=True)
    renders['Close.png'] = rel(OUT / 'Close.png')
    close_cam = 'location (3.0, %.3f, 0.6), looking along -y across the y < 0 path, 20 deg down, 60 mm' % cam.location.y
    say('rendered Close.png')
    down = math.radians(25)
    cam.location = (0.5, 0.0, 1.7)
    cam.rotation_euler = Vector((math.cos(down), 0, -math.sin(down))).to_track_quat('-Z', 'Y').to_euler()
    cam.data.sensor_fit = 'HORIZONTAL'
    cam.data.angle = math.radians(90)
    scene.render.filepath = str(OUT / 'OnFoot.png')
    bpy.ops.render.render(write_still=True)
    renders['OnFoot.png'] = rel(OUT / 'OnFoot.png')
    say('rendered OnFoot.png')
    man['renders'] = dict(files=renders, ground='Loose_3x3, Packed_3x3, Transition: flat 6 m, the tile 3 x 3, normal maps (object space = the flat ground tangent space), Specular IOR Level 0.5, roughness ORH.G',
                          camera='3x3 and Transition: eye 1.7 m up, 1.5 m behind the ground edge, looking along x (the paths), 18 deg down, 30 mm',
                          lighting='study 04: world Soft cool daylight, sun Directional daylight; AgX Medium High Contrast; Cycles 32 samples, denoised; 1440 x 900',
                          transition=dict(rule='p = smoothstep(0.35, 0.7, T - 0.3 (hL - mean(hL))), hL = Loose ORH.B, mean(hL) = %.4f' % mean_hl,
                                          T='max of two Gaussians, sigma %.3f m, centres +-0.784 + 0.12 sin(0.29 x) (the study lanes)' % PATH_SIGMA_M,
                                          stones=n6, stones_per_m2=round(n6 / 36.0, 1),
                                          stone_rule='the study placement (78000 tries per 466.7 m2, scaled to 5.8 x 5.8 m), none where T > 0.35'),
                          displaced=dict(ground='the transition ground continued to 40 x 40 m (x 0-40 along the paths, y -20..20; the tile and the paths repeat); '
                                                'the study stones on its road band to x 40 (%d in all)' % len(stones),
                                         displacement='true displacement, Cycles adaptive subdivision (simple, 1 px dicing) of a 0.5 m grid, by lerp(Loose B x %.1f cm, Packed B x %.1f cm, p); '
                                                      'shading normal = the baked normal maps in the flat frame (as POM shades); stones on the displaced height'
                                                      % (orh.PARALLAX_DEPTH_CM['Loose'], orh.PARALLAX_DEPTH_CM['Packed']),
                                         close=close_cam + '; the view centre on the inner p = 0.5 edge of that path',
                                         on_foot='location (0.5, 0, 1.7), looking along x (the paths), 25 deg down, 90 deg horizontal FOV'))
    man_path.write_text(json.dumps(man, indent=2))
    say('stones %d; manifest renders block written' % len(stones))


if STAGE in ('all', 'bake'):
    stage_bake()
if STAGE in ('all', 'render'):
    stage_render()
print('GRAVEL_DG1_OK', flush=True)
