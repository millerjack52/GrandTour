"""MudRunner MR1 (docs/MUDRUNNER_LESSONS_PLAN.md MR1 item 4): the mud splat atlas, headless.

Sixteen irregular painterly blots of mud, each its own shape (no repeats), in the style-study language of the approved
churn (docs/MUD_WET_STUDY.md): irregular outlines from a few random harmonics and a light warp, lumpy domes, clustered
droplets, no lines, no swirls, no direction-free mosaics. Three kinds:
- blot (7): a lumpy core with two to four lobes and a few droplets beside it, clustered on one or two sides;
- splatter (5): a smaller core and a fan of flung droplets in two or three sectors, smaller and sparser further out,
  a few drawn out a little along their flight;
- smear (4): a drag - overlapping lumps along a gently bending path, thick at the head, thinning and breaking into
  separate beads at the tail.
Every blot lies inside its tile's inscribed circle at WINDOW (0.88) of the half size, so a blot drawn over a square of
half size H reaches at most 0.88 H from its centre, and tiles never bleed into each other.

Run headless (Blender 5.1, no add-ons):
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 \
      --python Art/Blender/build_mud_splats.py [-- norender]
Outputs, Art/Export/MudSplats/:
  T_MudSplat_Mask.png      2048 8-bit grey, 4 x 4 tiles of 512 (tile t at column t % 4, row t // 4, row 0 at the top):
                           the coverage, 1 = mud
  T_MudSplat_Height.png    2048 16-bit grey: the mud's thickness 0..1 over the whole atlas (one scale), 0 outside
  T_MudSplat_Normal.png    2048 8-bit RGB: a DirectX tangent normal (green = -Y, as the bog bakes) from the height
  T_MudSplat_Splatter.png  2048 8-bit RGB, tileable: a car-space splatter of droplets and short drips (for MR2); R the
                           coverage, G each droplet's rank 0..1 (MR2b: a drip carries its droplet's, a pixel two droplets
                           share the lower, the background a neighbouring droplet's, grown 24 px, else 1; uniform over the
                           droplets and loosely shared by a cluster), so a material shows a share D of whole droplets where
                           G < D; B 0
  MudSplats_Preview.png    a Cycles render of the sixteen blots as mud on a pale ground (1 m a tile, top down)
  manifest.json            per tile: kind, fill share, outermost radius, droplet count; the Standard bog's mean colour
And Source/GrandTour/Terrain/GTMudBlots.inl: the mask box-filtered to 32 x 32 a tile, as bytes, for
UGTTrackPaintSubsystem's carried-mud and splat brushes and its CPU grid (rebuild the C++ after a re-bake).
"""
import bpy, math, json, sys, zlib, struct, time
import numpy as np
from pathlib import Path

T0 = time.time()
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Export/MudSplats'
INL = ROOT / 'Source/GrandTour/Terrain/GTMudBlots.inl'
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RENDER = 'norender' not in ARGS

ATLAS = 2048
TILES = 4
T = ATLAS // TILES          # 512 px a tile
WINDOW = 0.88               # every blot inside this radius (tile half size = 1)
CPU = 32                    # the C++ brush's tile size
SEED = 7101
KINDS = ['blot', 'splatter', 'smear', 'blot', 'splatter', 'blot', 'smear', 'blot',
         'splatter', 'blot', 'smear', 'splatter', 'blot', 'smear', 'blot', 'splatter']
NORMAL_STRENGTH = 9.0       # height units per pixel to tangent slope (a 50 cm tile, about 1.5 cm of mud)


def say(msg):
    print('MUD_SPLATS %6.1f s  %s' % (time.time() - T0, msg), flush=True)


def smoothstep(a, b, x):
    v = np.clip((x - a) / (b - a), 0, 1)
    return v * v * (3 - 2 * v)


def band(n, feat_px, rng, width=.55):
    """Zero-mean, unit-std noise with features of about feat_px pixels, periodic over n."""
    F = np.fft.rfft2(rng.standard_normal((n, n)))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    k = np.hypot(fx, fy)
    k[0, 0] = 1e-9
    filt = np.exp(-.5 * (np.log(k * feat_px) / width) ** 2)
    filt[0, 0] = 0
    a = np.fft.irfft2(F * filt, s=(n, n))
    return (a - a.mean()) / (a.std() + 1e-12)


def gauss(a, sigma_px):
    n0, n1 = a.shape
    k = np.hypot(np.fft.fftfreq(n0)[:, None], np.fft.rfftfreq(n1)[None, :])
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (math.pi * sigma_px * k) ** 2), s=a.shape)


def write_png(path, arr, bits=8, grey=True):
    """arr (h, w) or (h, w, 3) floats 0..1, row 0 = the top."""
    a = np.clip(arr, 0, 1)
    h, w = a.shape[:2]
    data = (a * 65535 + .5).astype('>u2') if bits == 16 else (a * 255 + .5).astype(np.uint8)
    rows = data.reshape(h, -1).view(np.uint8)
    raw = np.hstack([np.zeros((h, 1), np.uint8), rows]).tobytes()

    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xFFFFFFFF)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, bits, 0 if grey else 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


# ---------------------------------------------------------------- one tile's shapes
class Tile:
    def __init__(self, index, kind):
        self.index, self.kind = index, kind
        self.rng = np.random.default_rng(SEED + 97 * index)
        c = (np.arange(T) + .5) / T * 2 - 1           # pixel centres, -1..1
        self.X, self.Y = np.meshgrid(c, c)             # Y down the image (row 0 at the top)
        # A light warp of the plane (features of a fifth of the tile, under 3 % of it): outlines wander, nothing flows.
        wx, wy = band(T, T * .2, self.rng), band(T, T * .2, self.rng)
        amp = self.rng.uniform(.015, .028)
        self.U, self.V = self.X + amp * wx, self.Y + amp * wy
        self.mask = np.zeros((T, T))
        self.height = np.zeros((T, T))
        self.droplets = 0
        self.soft = 2.2 / (T / 2)                      # the edge's width, tile units (2.2 px)

    def outline(self, kmin=2, kmax=7, amp=.16, decay=1.1):
        """A smooth periodic radius scale over the angle: a few random harmonics, the low ones strongest."""
        ks = np.arange(kmin, kmax + 1)
        a = amp * ks ** (-decay) * self.rng.uniform(.45, 1., len(ks))
        ph = self.rng.uniform(0, 2 * math.pi, len(ks))
        return lambda th: 1 + sum(ai * np.cos(k * th + p) for ai, k, p in zip(a, ks, ph))

    def blob(self, cx, cy, r, thick, aspect=1., turn=0., lumps=0, kmax=7, amp=.16):
        """An irregular domed blob: a lumpy outline round (cx, cy), radius r, drawn out by aspect along turn."""
        if r <= 0:
            return
        box = r * aspect * 1.45 + 4 * self.soft
        i0, i1 = [int(np.clip((v + 1) / 2 * T, 0, T)) for v in (cy - box, cy + box + 2 / T)]
        j0, j1 = [int(np.clip((v + 1) / 2 * T, 0, T)) for v in (cx - box, cx + box + 2 / T)]
        if i1 <= i0 or j1 <= j0:
            return
        du, dv = self.U[i0:i1, j0:j1] - cx, self.V[i0:i1, j0:j1] - cy
        ct, st = math.cos(turn), math.sin(turn)
        a, b = (du * ct + dv * st) / aspect, -du * st + dv * ct
        th = np.arctan2(b, a)
        q = np.hypot(a, b) / (r * self.outline(2, kmax, amp)(th))
        m = smoothstep(1 + self.soft / r * .5, 1 - self.soft / r * .5, q)
        h = thick * np.clip(1 - q * q, 0, 1) ** .7
        if lumps:
            for _ in range(lumps):
                ang, dist = self.rng.uniform(0, 2 * math.pi), r * math.sqrt(self.rng.uniform(0, .5))
                lx, ly = cx + dist * math.cos(ang), cy + dist * math.sin(ang)
                w = r * self.rng.uniform(.12, .28)
                h = h + thick * self.rng.uniform(.12, .32) * np.exp(-((self.U[i0:i1, j0:j1] - lx) ** 2 + (self.V[i0:i1, j0:j1] - ly) ** 2) / (2 * w * w)) * m
        self.mask[i0:i1, j0:j1] = np.maximum(self.mask[i0:i1, j0:j1], m)
        self.height[i0:i1, j0:j1] = np.maximum(self.height[i0:i1, j0:j1], h * m)

    def droplet_cloud(self, cx, cy, core_r, sectors, count, dmin, dmax, size, stretch=0.):
        """Droplets clustered in sectors (centre angle, spread rad): further out smaller and sparser, never in a row."""
        made = 0
        for _ in range(count * 3):
            if made >= count:
                break
            centre, spread = sectors[self.rng.integers(len(sectors))]
            ang = centre + self.rng.normal(0, spread)
            u = self.rng.uniform(0, 1) ** 1.15             # more near the core
            d = core_r * (dmin + (dmax - dmin) * u)
            x, y = cx + d * math.cos(ang), cy + d * math.sin(ang)
            rr = size * (dmin / (d / core_r)) ** 1.15 * self.rng.uniform(.5, 1.3)
            if math.hypot(x, y) + rr * (1 + stretch) > WINDOW - .03 or rr < 2.5 / (T / 2):
                continue
            asp = 1 + stretch * self.rng.uniform(0, 1) * (d / core_r - dmin) / max(dmax - dmin, 1e-3)
            small = rr < .05
            self.blob(x, y, rr, .35 + .4 * rr / size, aspect=asp, turn=ang, kmax=4 if small else 5, amp=.07 if small else .13)
            made += 1
        self.droplets += made

    def build(self):
        rng = self.rng
        if self.kind == 'blot':
            r = rng.uniform(.34, .48)
            cx, cy = rng.uniform(-.06, .06, 2)
            # a drawn-out, kidney or lobed core (strong low harmonics), never the same proportions twice
            self.blob(cx, cy, r, 1., aspect=rng.uniform(1., 1.45), turn=rng.uniform(0, math.pi), lumps=rng.integers(4, 9), amp=.3, kmax=6)
            for _ in range(rng.integers(3, 7)):
                ang = rng.uniform(0, 2 * math.pi)
                lr = r * rng.uniform(.25, .6)
                d = r * rng.uniform(.6, 1.05)
                if math.hypot(cx + d * math.cos(ang), cy + d * math.sin(ang)) + lr * 1.3 > WINDOW - .03:
                    continue
                self.blob(cx + d * math.cos(ang), cy + d * math.sin(ang), lr, .8, aspect=rng.uniform(1., 1.4), turn=ang, lumps=rng.integers(1, 4), amp=.26)
            side = rng.uniform(0, 2 * math.pi)
            sectors = [(side, .45)] + ([(side + rng.uniform(1.8, 3.6), .35)] if rng.uniform() < .6 else [])
            self.droplet_cloud(cx, cy, r, sectors, int(rng.integers(3, 10)), 1.08, 1.6, .065)
        elif self.kind == 'splatter':
            fling = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(.25, .36)
            cx, cy = -.16 * math.cos(fling), -.16 * math.sin(fling)
            self.blob(cx, cy, r, .9, lumps=rng.integers(3, 6), amp=.22)
            for _ in range(rng.integers(1, 3)):          # thick arms toward the fling
                ang = fling + rng.normal(0, .35)
                self.blob(cx + .85 * r * math.cos(ang), cy + .85 * r * math.sin(ang), r * rng.uniform(.38, .55), .7, aspect=1.25, turn=ang, lumps=2)
            sectors = [(fling + rng.normal(0, .3), rng.uniform(.18, .3)) for _ in range(rng.integers(2, 4))]
            self.droplet_cloud(cx, cy, r, sectors, int(rng.integers(22, 44)), 1.05, 2.7, .08, stretch=.7)
        else:   # smear: a drag along a gently bending path, thick at the head, breaking up at the tail
            heading = rng.uniform(0, 2 * math.pi)
            bend = rng.uniform(-.25, .25)                  # total turn along the smear, under 15 degrees each way
            n = int(rng.integers(5, 8))
            length = rng.uniform(1.15, 1.4)
            pts = []
            x, y = -.5 * length * math.cos(heading), -.5 * length * math.sin(heading)
            for k in range(n):
                f = k / (n - 1)
                a = heading + bend * (f - .5)
                pts.append((x, y, f, a))
                step = length / (n - 1) * rng.uniform(.8, 1.2)
                x, y = x + step * math.cos(a), y + step * math.sin(a)
            # the head is the last point; the tail beads are separated by small gaps
            for k, (px, py, f, a) in enumerate(pts):
                r = .07 + .2 * f ** 1.3
                if f < .35:
                    r *= rng.uniform(.6, .9)
                    px += rng.normal(0, .02)
                    py += rng.normal(0, .02)
                if math.hypot(px, py) + r * 1.3 > WINDOW - .02:
                    s = (WINDOW - .02 - r * 1.3) / max(math.hypot(px, py), 1e-6)
                    px, py = px * s, py * s
                self.blob(px, py, r, .55 + .45 * f, aspect=1.3, turn=a, lumps=int(1 + 3 * f), amp=.18)
            hx, hy, _, ha = pts[-1]
            self.droplet_cloud(hx, hy, .26, [(ha, .5), (ha + rng.choice([-1, 1]) * 1.4, .4)], int(rng.integers(3, 8)), 1.1, 1.7, .05)
        # Crumb grain in the mud: a fine lumpy texture on the dome (no direction).
        crumbs = band(T, 7, rng) * .05 + band(T, 18, rng) * .07
        self.height = np.clip(self.height + crumbs * self.mask * np.clip(self.height * 3, 0, 1), 0, None)
        # The window: nothing beyond WINDOW of the half size (the droplet placement keeps clear of it already).
        rad = np.hypot(self.X, self.Y)
        win = smoothstep(WINDOW, WINDOW - .02, rad)
        self.mask *= win
        self.height *= win
        return self


def stats(t):
    rad = np.hypot(t.X, t.Y)
    on = t.mask > .02
    return dict(index=t.index, kind=t.kind, fill_share=round(float(t.mask.mean()), 4),
                outermost_radius=round(float(rad[on].max()) if on.any() else 0., 4), droplets=t.droplets,
                height_max=round(float(t.height.max()), 4))


# ---------------------------------------------------------------- the car-space splatter (MR2), tileable
def splatter(n=2048, seed=SEED + 5000):
    rng = np.random.default_rng(seed)
    rr = np.random.default_rng(seed + 1)                # MR2b: the ranks' own stream, so the coverage is the MR2 bake's exactly
    out = np.zeros((n, n))
    rank = np.full((n, n), 2.0)                         # 2 = no droplet yet
    px_cm = n / 100.0                                   # the tile is a metre of body side
    # clustered: cluster centres from a coarse density field (crowded in places, open in others)
    dens = band(64, 14, rng)
    cand = np.argwhere(dens > .25)
    clusters = cand[rng.choice(len(cand), size=min(70, len(cand)), replace=False)] * (n / 64) + rng.uniform(0, n / 64, (min(70, len(cand)), 2))
    drops = []
    keys = []                                           # MR2b: a droplet's rank key, 0.6 its cluster's and 0.4 its own
    for cy, cx in clusters:
        fling = rng.uniform(0, 2 * math.pi)
        big = rng.uniform(.6, 1.6)
        cluster_key = rr.uniform()
        for _ in range(int(rng.integers(8, 34))):
            ang = fling + rng.normal(0, .55)
            d = px_cm * rng.uniform(0, 9) ** 1.3
            r = px_cm * big * rng.uniform(.25, 1.5) * (1.0 / (1 + d / (px_cm * 6)))
            drops.append((cx + d * math.cos(ang), cy + d * math.sin(ang), max(r, 2.5), ang))
            keys.append(.6 * cluster_key + .4 * rr.uniform())
    for _ in range(900):                                # loose specks everywhere, sparse
        drops.append((rng.uniform(0, n), rng.uniform(0, n), max(2.5, px_cm * rng.uniform(.12, .45)), rng.uniform(0, 2 * math.pi)))
        keys.append(rr.uniform())
    # The keys made uniform over the droplets: a share D of them has a rank under D.
    order = np.argsort(np.argsort(np.array(keys)))
    ranks = (order + .5) / len(keys)

    def stamp(x, y, r, asp, turn, value=1., rk=None):
        box = int(r * asp * 1.5 + 4)
        ii = (np.arange(int(y) - box, int(y) + box + 1)) % n
        jj = (np.arange(int(x) - box, int(x) + box + 1)) % n
        yy, xx = np.meshgrid(np.arange(int(y) - box, int(y) + box + 1) + .5 - y, np.arange(int(x) - box, int(x) + box + 1) + .5 - x, indexing='ij')
        ct, st = math.cos(turn), math.sin(turn)
        a, b = (xx * ct + yy * st) / asp, -xx * st + yy * ct
        th = np.arctan2(b, a)
        ks = np.arange(2, 6)
        amp = .14 * ks ** -1.1 * rng.uniform(.4, 1, len(ks))
        ph = rng.uniform(0, 2 * math.pi, len(ks))
        scale = 1 + sum(ai * np.cos(k * th + p) for ai, k, p in zip(amp, ks, ph))
        q = np.hypot(a, b) / (r * scale)
        m = smoothstep(1 + 1.1 / r, 1 - 1.1 / r, q) * value
        out[np.ix_(ii, jj)] = np.maximum(out[np.ix_(ii, jj)], m)
        if rk is not None:
            block = rank[np.ix_(ii, jj)]
            rank[np.ix_(ii, jj)] = np.where(m > .02, np.minimum(block, rk), block)

    drips = 0
    for (x, y, r, ang), rk in zip(drops, ranks):
        asp = 1 + .5 * rng.uniform() if r < px_cm * .6 else 1.
        stamp(x, y, r, asp, ang, rk=rk)
        if r > px_cm * .55 and rng.uniform() < .22:     # a short drip running down (image down = car-space down)
            length = r * rng.uniform(2, 7)
            steps = int(length / max(r * .35, 2)) + 2
            wob = rng.uniform(-.25, .25)
            for s in range(1, steps + 1):
                f = s / steps
                w = r * (.55 - .3 * f) * rng.uniform(.85, 1.1)
                stamp(x + r * wob * math.sin(f * 2.4) , y + f * length, max(w, 2.), 1., 0., rk=rk)
            stamp(x + r * wob * math.sin(2.4), y + length, max(r * .42, 2.5), 1., 0., rk=rk)   # the bead at its foot
            drips += 1
    # MR2b: the background takes the nearest droplet's rank (24 px, tileable), so filtering and mips keep each droplet's own.
    for _ in range(24):
        free = rank > 1.5
        if not free.any():
            break
        near = np.minimum.reduce([np.roll(rank, 1, 0), np.roll(rank, -1, 0), np.roll(rank, 1, 1), np.roll(rank, -1, 1)])
        rank = np.where(free & (near < 1.5), near, rank)
    rank = np.where(rank > 1.5, 1., rank)
    return np.stack([out, rank, np.zeros_like(out)], -1), len(drops), drips


def bog_mean_colour():
    """The Standard bog bake's mean colour, linear (for the decal and grass tints)."""
    path = ROOT / 'Art/Export/MudStyleUE/T_MS_BogStandardColor.png'
    if not path.exists():
        return None
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = 'Non-Color'
    px = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(px)
    rgb = px.reshape(-1, 4)[:, :3].astype(np.float64)
    lin = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
    bpy.data.images.remove(im)
    return [round(float(v), 4) for v in lin.mean(0)]


def preview(mask_path, height_path, normal_path, mud_rgb):
    """The sixteen tiles as mud on a pale gravel-grey ground, 1 m a tile, top down, the sun low from the upper left."""
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 48
    sc.render.resolution_x = sc.render.resolution_y = 1024
    sc.view_settings.view_transform = 'Standard' if 'Standard' in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items] else sc.view_settings.view_transform
    world = bpy.data.worlds.new('Splat sky')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.55, .62, .75, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .6
    sc.world = world
    me = bpy.data.meshes.new('Atlas plane')
    me.from_pydata([(-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        v = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((v.x + 2) / 4, (v.y + 2) / 4)
    mat = bpy.data.materials.new('Splat preview')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')

    def img(path, colour=False):
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = bpy.data.images.load(str(path), check_existing=False)
        n.image.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
        n.interpolation = 'Cubic'
        return n
    m, h, nm = img(mask_path), img(height_path), img(normal_path)
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'

    def sock(sockets, ident):
        return next(s for s in sockets if s.identifier == ident)
    sock(mix.inputs, 'A_Color').default_value = (.36, .33, .28, 1)          # the pale ground
    mud = mud_rgb or (.05, .035, .022)
    sock(mix.inputs, 'B_Color').default_value = (mud[0] * .85, mud[1] * .85, mud[2] * .85, 1)
    nt.links.new(m.outputs['Color'], sock(mix.inputs, 'Factor_Float'))
    nt.links.new(sock(mix.outputs, 'Result_Color'), bsdf.inputs['Base Color'])
    rmix = nt.nodes.new('ShaderNodeMapRange')
    rmix.inputs['To Min'].default_value = .85
    rmix.inputs['To Max'].default_value = .32
    nt.links.new(m.outputs['Color'], rmix.inputs['Value'])
    nt.links.new(rmix.outputs['Result'], bsdf.inputs['Roughness'])
    # DirectX green (= -Y) to Blender's +Y: flip green before the normal map node.
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    inv = nt.nodes.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.
    comb = nt.nodes.new('ShaderNodeCombineColor')
    nt.links.new(nm.outputs['Color'], sep.inputs[0])
    nt.links.new(sep.outputs[0], comb.inputs[0])
    nt.links.new(sep.outputs[1], inv.inputs[1])
    nt.links.new(inv.outputs[0], comb.inputs[1])
    nt.links.new(sep.outputs[2], comb.inputs[2])
    nmap = nt.nodes.new('ShaderNodeNormalMap')
    nmap.inputs['Strength'].default_value = 1.
    nt.links.new(comb.outputs[0], nmap.inputs['Color'])
    nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
    me.materials.append(mat)
    ob = bpy.data.objects.new('Atlas plane', me)
    sc.collection.objects.link(ob)
    sun_d = bpy.data.lights.new('Sun', 'SUN')
    sun_d.energy = 3.2
    sun_d.angle = math.radians(2)
    sun = bpy.data.objects.new('Sun', sun_d)
    sun.rotation_euler = (math.radians(58), 0, math.radians(-135))
    sc.collection.objects.link(sun)
    cd = bpy.data.cameras.new('Top')
    cd.type = 'ORTHO'
    cd.ortho_scale = 4.0
    cam = bpy.data.objects.new('Top', cd)
    cam.location = (0, 0, 5)
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.filepath = str(OUT / 'MudSplats_Preview.png')
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mask = np.zeros((ATLAS, ATLAS))
    height = np.zeros((ATLAS, ATLAS))
    tiles = []
    for index, kind in enumerate(KINDS):
        t = Tile(index, kind).build()
        r, c = divmod(index, TILES)
        mask[r * T:(r + 1) * T, c * T:(c + 1) * T] = t.mask
        height[r * T:(r + 1) * T, c * T:(c + 1) * T] = t.height
        tiles.append(stats(t))
        say('tile %2d %-8s fill %.3f outermost %.3f droplets %d' % (index, kind, tiles[-1]['fill_share'], tiles[-1]['outermost_radius'], t.droplets))
    height /= max(height.max(), 1e-9)
    # The normal from a lightly smoothed height (DirectX: x right, y down the image, green = -Y = the image-down slope).
    hs = gauss(height, 1.2)
    gy, gx = np.gradient(hs)
    nx, ny = -gx * NORMAL_STRENGTH, -gy * NORMAL_STRENGTH
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack([nx / ln, ny / ln, nz / ln], -1) * .5 + .5
    write_png(OUT / 'T_MudSplat_Mask.png', mask, 8)
    write_png(OUT / 'T_MudSplat_Height.png', height, 16)
    write_png(OUT / 'T_MudSplat_Normal.png', normal, 8, grey=False)
    say('atlas written')
    sp_rgb, drops, drips = splatter()
    write_png(OUT / 'T_MudSplat_Splatter.png', sp_rgb, 8, grey=False)
    sp = sp_rgb[..., 0]
    covered = sp > .5
    say('splatter written: %d droplets, %d drips, coverage %.3f; rank (G) over the covered pixels mean %.3f, under 0.1 %.3f of them'
        % (drops, drips, float(covered.mean()), float(sp_rgb[..., 1][covered].mean()), float((sp_rgb[..., 1][covered] < .1).mean())))
    # The C++ brushes: each tile box-filtered to 32 x 32 (16 x 16 px blocks), row 0 = the PNG's top row.
    f = T // CPU
    small = mask.reshape(ATLAS // f, f, ATLAS // f, f).mean((1, 3))
    lines = ['// Generated by Art/Blender/build_mud_splats.py (MudRunner MR1) - do not edit; re-bake, then rebuild.',
             '// The splat atlas mask (T_MudSplat_Mask.png), box-filtered to %d x %d a tile, 0..255; row 0 = the PNG\'s top row.' % (CPU, CPU),
             '// Tile t is the atlas tile at column t %% 4, row t / 4; every blot lies within %.2f of its tile\'s half size.' % WINDOW,
             '#pragma once', '', 'namespace GTMudBlots', '{',
             '\tconstexpr int32 Count = %d;' % len(KINDS), '\tconstexpr int32 Size = %d;' % CPU,
             '\tconstexpr float Window = %.2ff;' % WINDOW,
             '\t/** 0 blot, 1 splatter, 2 smear. */',
             '\tstatic const uint8 Kinds[Count] = { %s };' % ', '.join(str({'blot': 0, 'splatter': 1, 'smear': 2}[k]) for k in KINDS),
             '\tstatic const uint8 Masks[Count * Size * Size] = {']
    for index in range(len(KINDS)):
        r, c = divmod(index, TILES)
        tile = (np.clip(small[r * CPU:(r + 1) * CPU, c * CPU:(c + 1) * CPU], 0, 1) * 255 + .5).astype(np.uint8)
        lines.append('\t\t// tile %d (%s)' % (index, KINDS[index]))
        for row in tile:
            lines.append('\t\t' + ','.join(str(int(v)) for v in row) + ',')
    lines += ['\t};', '}', '']
    INL.write_text('\n'.join(lines))
    say('wrote %s' % INL)
    mud = bog_mean_colour()
    manifest = dict(atlas=ATLAS, tiles=TILES, tile_px=T, window=WINDOW, cpu_tile=CPU, seed=SEED, normal='DirectX tangent (green = -Y), from the height',
                    height_scale='one scale over the atlas, max 1', tiles_info=tiles, splatter=dict(size=2048, droplets=drops, drips=drips,
                    coverage=round(float((sp > .5).mean()), 4), tileable=True, metre_per_tile=1.0,
                    channels='R coverage, G droplet rank 0..1 (MR2b), B 0',
                    rank_mean_covered=round(float(sp_rgb[..., 1][covered].mean()), 4)),
                    standard_bog_mean_linear=mud, cpu_header=str(INL.relative_to(ROOT)).replace('\\', '/'))
    if RENDER:
        preview(OUT / 'T_MudSplat_Mask.png', OUT / 'T_MudSplat_Height.png', OUT / 'T_MudSplat_Normal.png', mud)
        manifest['preview'] = 'MudSplats_Preview.png'
        say('preview rendered')
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    say('DONE')


main()
