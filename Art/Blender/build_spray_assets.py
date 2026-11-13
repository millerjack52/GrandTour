"""Wheel spray P1 (docs/WHEEL_SPRAY_PLAN.md P1): the painterly spray assets, headless.

Run (Blender 5.1, no add-ons):
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 \
      --python Art/Blender/build_spray_assets.py [-- norender]

Outputs, Art/Export/WheelSpray/:
  SM_GT_SprayClump_0..7.fbx  P1b: eight thrown mud clumps from LM2c's clod recipe (Art/Blender/build_mud_clods.py: a
                             noise-displaced icosphere), droopy and torn: pulled-out lobes, sagging rims, three of the eight
                             strings 1.8-3x long tapering into a sagging tail; decimated to 46 triangles, one Catmull-Clark
                             level, fine noise along the normals, all smooth shaded (at most 300 triangles). Longest side
                             1.6-6 cm (mostly small), pivot at the bounds' centre. Slot 0 named M_GT_Clod. Metres in
                             Blender, centimetres in the FBX, -Z forward, Y up (the clods' settings).
  T_GT_SprayMud.png          1024 RGBA, 4 x 4 frames of 256 (frame f at column f % 4, row f // 4, row 0 at the top):
                             wet droplet clusters, 0-3 single drops, 4-7 small clusters, 8-11 ragged blobs with satellites,
                             12-15 ragged splats with many satellites. R a soft height (one scale over the atlas) for the
                             lighting normal, G and B 0, A the coverage with soft painted edges.
  T_GT_SprayGrit.png         1024 RGBA, 4 x 4 frames: tiny angular chips, 0-5 single, 6-11 two to four, 12-15 five to ten.
                             R the facet shade (flat facets), G a random number per chip (the material's palette pick),
                             B 0, A the mask (crisp edge, for alpha-masking).
  T_GT_SprayDust.png         1024 grey, 4 x 4 frames over the puff's life (frame 0 first): a tight clump of overlapping
                             flat-topped soft-edged dabs that spreads, grows and thins, dabs dropping out. Coverage only.
  Assets_Clumps.png          Cycles: the clumps on a ground plane, wet (Fresh 1: x0.8, roughness 0.5) in the Standard bog
                             bake's colour, tri-planar at one 25 cm tile (M_GT_SprayClump's ClodScaleCm), one row on
                             neutral grey, one on the Standard bog colour.
  Atlas_Sheets.png           the three atlases composited on grey (top row: mud on sRGB 0.5, grit and dust on 0.3) and on the ground's colour bakes (bottom row):
                             mud on the Standard bog, grit and dust on the gravel Loose bake.
  WheelSpray.blend, manifest.json
"""
import bpy, bmesh, math, json, sys, zlib, struct, time
import numpy as np
from pathlib import Path
from mathutils import Vector, noise

T0 = time.time()
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Export/WheelSpray'
OUT.mkdir(parents=True, exist_ok=True)
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RENDER = 'norender' not in ARGS
SEED = 8231
ATLAS, TILES = 1024, 4
T = ATLAS // TILES           # 256 px a frame
WINDOW = .90                 # everything inside this radius of the frame (half size = 1)
BOG_STANDARD = ROOT / 'Art/Export/MudStyleUE/T_MS_BogStandardColor.png'
GV_COLOR = ROOT / 'Art/Export/GravelDG1/T_GV_LooseColor.png'
GV_ORH = ROOT / 'Art/Export/GravelDG1/T_GV_LooseORH.png'
FBX = dict(axis_forward='-Z', axis_up='Y', global_scale=1.0, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
           bake_space_transform=False, use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=False,
           add_leaf_bones=False, bake_anim=False, path_mode='AUTO', embed_textures=False, use_custom_props=False,
           use_selection=True, object_types={'MESH'})


def say(msg):
    print('SPRAY_ASSETS %6.1f s  %s' % (time.time() - T0, msg), flush=True)


# ---------------------------------------------------------------- clumps (P1b)
# P1b (the main session's look at P1: "hard facets and flat shading read as small brown rocks, the 8 cm flake as a stone
# slab"): smooth shaded, no planar cuts; a coarse droopy, torn shape, one Catmull-Clark level, then fine noise along the
# normals. Longest side 1.6-6 cm by a power law (mostly small). A third are strings that taper into a sagging tail.
CLUMPS = [
    dict(size=1.6, family='blob', aspect=1.1, flat=.85, lobes=1),
    dict(size=1.9, family='string', aspect=2.4, flat=.75, lobes=0),
    dict(size=2.2, family='blob', aspect=1.25, flat=.75, lobes=2),
    dict(size=2.6, family='flake', aspect=1.3, flat=.45, lobes=1),
    dict(size=3.1, family='string', aspect=1.8, flat=.70, lobes=1),
    dict(size=3.8, family='blob', aspect=1.35, flat=.70, lobes=2),
    dict(size=4.7, family='string', aspect=3.0, flat=.60, lobes=0),
    dict(size=6.0, family='flake', aspect=1.45, flat=.42, lobes=2),
]
CLUMP_TILE_M = .25        # P2's M_GT_SprayClump ClodScaleCm: one bake tile per 25 cm, so a 2-6 cm clump shows the bake
BASE_TRIS = 46            # before the one subdivision level: x6 after Catmull-Clark and triangulation (<= 300)


def clump_coarse(index, spec):
    """The coarse shape at radius ~1: LM2c's noise-displaced icosphere, torn lobes pulled out, strings tapered, a droop."""
    bm = bmesh.new()
    for sub in (2, 3, 4):
        bm.clear()
        bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
        if len(bm.faces) >= 240:
            break
    rng = np.random.default_rng(SEED + 31 * index)
    seed = Vector((23.1 * (index + 1), -7.3 * (index + 2), 4.9 * (index + 3)))
    fam, aspect = spec['family'], spec['aspect']
    lobes = []
    for _ in range(spec['lobes']):          # torn tongues: a direction mostly sideways, a reach
        th, ph = rng.uniform(0, 2 * math.pi), rng.uniform(-.5, .3)
        lobes.append((Vector((math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph), math.sin(ph))), rng.uniform(.35, .7)))
    droop = rng.uniform(.25, .45)
    for v in bm.verts:
        n = v.co.normalized()
        r = 1.0 + .30 * noise.noise(n * 1.5 + seed) + .12 * noise.noise(n * 3.4 + seed * 1.4)
        for d, reach in lobes:
            k = n.dot(d)
            if k > .55:
                r += reach * ((k - .55) / .45) ** 1.6
        p = n * r
        if fam == 'string':
            t = .5 * (n.x + 1.0)                                  # 0 head, 1 tail
            thin = max(1.1 - .95 * t ** 1.2, .08)
            p = Vector((p.x * aspect, p.y * thin, p.z * thin * spec['flat']))
            p.z -= droop * aspect * .35 * t * t                  # the tail sags
        else:
            p = Vector((p.x * aspect, p.y, p.z * spec['flat']))
            h2 = (p.x / aspect) ** 2 + p.y ** 2
            p.z -= droop * (.55 if fam == 'flake' else .30) * h2   # the rim droops, like a wet sheet in flight
        v.co = p
    bm.normal_update()
    return bm


def apply_modifier(ob, kind, **props):
    mod = ob.modifiers.new('m', kind)
    for k, v in props.items():
        setattr(mod, k, v)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=False, depsgraph=dg)
    ob.modifiers.remove(mod)
    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)


def build_clump(index, spec):
    name = 'SM_GT_SprayClump_%d' % index
    bm = clump_coarse(index, spec)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    apply_modifier(ob, 'DECIMATE', decimate_type='COLLAPSE', ratio=BASE_TRIS / len(me.polygons), use_collapse_triangulate=True)
    apply_modifier(ob, 'SUBSURF', subdivision_type='CATMULL_CLARK', levels=1, render_levels=1)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    seed = Vector((5.3 * (index + 1), 11.7 * (index + 2), -3.1 * (index + 3)))
    ext = max(max(abs(v.co[k]) for v in bm.verts) for k in range(3))
    moves = [(v, v.normal * ext * (.075 * noise.noise(v.co / ext * 5.0 + seed) + .03 * noise.noise(v.co / ext * 11.0 + seed * 1.7)))
             for v in bm.verts]
    for v, d in moves:
        v.co += d
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY')
    for fc in bm.faces:
        fc.smooth = True
    for e in bm.edges:
        e.smooth = True
    lo = Vector([min(v.co[k] for v in bm.verts) for k in range(3)])
    hi = Vector([max(v.co[k] for v in bm.verts) for k in range(3)])
    s = spec['size'] / 100.0 / max(hi - lo)
    mid = (lo + hi) * .5
    for v in bm.verts:
        v.co = (v.co - mid) * s
    bm.to_mesh(ob.data)
    bm.free()
    me = ob.data
    uv = me.uv_layers.new(name='UVMap')
    zs = [v.co.z for v in me.vertices]
    z0, zr = min(zs), max(zs) - min(zs)
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (math.atan2(co.y, co.x) / (2 * math.pi) + .5, (co.z - z0) / max(zr, 1e-6))
    mat = bpy.data.materials.get('M_GT_Clod') or bpy.data.materials.new('M_GT_Clod')
    me.materials.append(mat)
    return ob


# ---------------------------------------------------------------- painting helpers (MR1's build_mud_splats.py method)
def smoothstep(a, b, x):
    v = np.clip((x - a) / (b - a), 0, 1)
    return v * v * (3 - 2 * v)


def band(n, feat_px, rng, width=.55):
    """Zero-mean, unit-std noise with features of about feat_px pixels, periodic over n."""
    F = np.fft.rfft2(rng.standard_normal((n, n)))
    k = np.hypot(np.fft.rfftfreq(n)[None, :], np.fft.fftfreq(n)[:, None])
    k[0, 0] = 1e-9
    filt = np.exp(-.5 * (np.log(k * feat_px) / width) ** 2)
    filt[0, 0] = 0
    a = np.fft.irfft2(F * filt, s=(n, n))
    return (a - a.mean()) / (a.std() + 1e-12)


def gauss(a, sigma_px):
    k = np.hypot(np.fft.fftfreq(a.shape[0])[:, None], np.fft.rfftfreq(a.shape[1])[None, :])
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (math.pi * sigma_px * k) ** 2), s=a.shape)


def write_png(path, arr, bits=8):
    """arr (h, w) grey, (h, w, 3) RGB or (h, w, 4) RGBA floats 0..1, row 0 = the top."""
    a = np.clip(arr, 0, 1)
    h, w = a.shape[:2]
    ctype = {2: 0, 3: 2, 4: 6}[a.ndim if a.ndim == 2 else a.shape[2]]
    data = (a * 65535 + .5).astype('>u2') if bits == 16 else (a * 255 + .5).astype(np.uint8)
    raw = np.hstack([np.zeros((h, 1), np.uint8), data.reshape(h, -1).view(np.uint8)]).tobytes()

    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xFFFFFFFF)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, bits, ctype, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def load_png(path):
    """(h, w, 4) floats as stored (sRGB values left as they are), row 0 = the top."""
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = 'Non-Color'
    px = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(px)
    a = px.reshape(im.size[1], im.size[0], 4)[::-1].astype(np.float64)
    bpy.data.images.remove(im)
    return a


def to_lin(c):
    return np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= .0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - .055)


class Frame:
    """One 256 px frame: coordinates -1..1, a light warp and an edge-breakup field, so outlines are painted, not drawn."""

    def __init__(self, seed, edge_amp=.05):
        self.rng = np.random.default_rng(seed)
        c = (np.arange(T) + .5) / T * 2 - 1
        self.X, self.Y = np.meshgrid(c, c)
        amp = self.rng.uniform(.012, .022)
        self.U = self.X + amp * band(T, T * .2, self.rng)
        self.V = self.Y + amp * band(T, T * .2, self.rng)
        self.E = edge_amp * band(T, T * .035, self.rng)       # the brush's ragged edge (features ~9 px)
        self.mask = np.zeros((T, T))
        self.height = np.zeros((T, T))
        self.soft = 3.2 / (T / 2)                           # the painted edge's width, frame units (3.2 px)

    def outline(self, kmax=7, amp=.16, decay=1.1):
        ks = np.arange(2, kmax + 1)
        a = amp * ks ** (-decay) * self.rng.uniform(.45, 1., len(ks))
        ph = self.rng.uniform(0, 2 * math.pi, len(ks))
        return lambda th: 1 + sum(ai * np.cos(k * th + p) for ai, k, p in zip(a, ks, ph))

    def blob(self, cx, cy, r, thick, aspect=1., turn=0., lumps=0, kmax=7, amp=.16):
        box = r * aspect * 1.5 + 5 * self.soft
        i0, i1 = [int(np.clip((v + 1) / 2 * T, 0, T)) for v in (cy - box, cy + box + 2 / T)]
        j0, j1 = [int(np.clip((v + 1) / 2 * T, 0, T)) for v in (cx - box, cx + box + 2 / T)]
        if i1 <= i0 or j1 <= j0:
            return
        U, V = self.U[i0:i1, j0:j1], self.V[i0:i1, j0:j1]
        du, dv = U - cx, V - cy
        ct, st = math.cos(turn), math.sin(turn)
        a, b = (du * ct + dv * st) / aspect, -du * st + dv * ct
        q = np.hypot(a, b) / (r * self.outline(kmax, amp)(np.arctan2(b, a)))
        s = self.soft / r
        m = smoothstep(1 + s, 1 - s, q + self.E[i0:i1, j0:j1] * min(1., .08 / r))
        h = thick * np.clip(1 - q * q, 0, 1) ** .7
        for _ in range(lumps):
            ang, dist = self.rng.uniform(0, 2 * math.pi), r * math.sqrt(self.rng.uniform(0, .5))
            w = r * self.rng.uniform(.12, .28)
            h = h + thick * self.rng.uniform(.12, .32) * np.exp(-((U - cx - dist * math.cos(ang)) ** 2 + (V - cy - dist * math.sin(ang)) ** 2) / (2 * w * w))
        self.mask[i0:i1, j0:j1] = np.maximum(self.mask[i0:i1, j0:j1], m)
        self.height[i0:i1, j0:j1] = np.maximum(self.height[i0:i1, j0:j1], h * m)

    def satellites(self, cx, cy, core_r, sectors, count, dmin, dmax, size, stretch=0.):
        """Droplets clustered in sectors: further out smaller and sparser, never in a row (MR1's droplet cloud)."""
        made = 0
        for _ in range(count * 4):
            if made >= count:
                break
            centre, spread = sectors[self.rng.integers(len(sectors))]
            ang = centre + self.rng.normal(0, spread)
            d = core_r * (dmin + (dmax - dmin) * self.rng.uniform(0, 1) ** 1.15)
            x, y = cx + d * math.cos(ang), cy + d * math.sin(ang)
            rr = size * (dmin / (d / core_r)) ** 1.15 * self.rng.uniform(.5, 1.3)
            asp = 1 + stretch * self.rng.uniform(0, 1)
            if math.hypot(x, y) + rr * asp > WINDOW - .03 or rr < 3.0 / (T / 2):
                continue
            self.blob(x, y, rr, .35 + .4 * min(rr / size, 1.), aspect=asp, turn=ang, kmax=4 if rr < .06 else 5, amp=.07 if rr < .06 else .13)
            made += 1
        return made


# ---------------------------------------------------------------- the three atlases
def mud_frame(f):
    fr = Frame(SEED + 1000 + 97 * f)
    rng = fr.rng
    ang0 = rng.uniform(0, 2 * math.pi)
    drops = 0
    if f < 4:            # a single drop, the last two with one or two tiny satellites
        r = rng.uniform(.30, .50)
        fr.blob(rng.uniform(-.08, .08), rng.uniform(-.08, .08), r, 1., aspect=rng.uniform(1.0, 1.5), turn=ang0, lumps=rng.integers(0, 2), kmax=5, amp=.10)
        if f >= 2:
            drops = fr.satellites(0, 0, r, [(ang0, .35)], int(f - 1), 1.35, 1.7, .10)
    elif f < 8:          # two to four drops in a cluster, one bigger, sizes falling off by a power law
        n = int(rng.integers(2, 5))
        cx, cy = rng.uniform(-.1, .1), rng.uniform(-.1, .1)
        for k in range(n):
            r = .34 * (k + 1) ** -.9 * rng.uniform(.8, 1.15)
            a, d = ang0 + rng.normal(0, .7), (0 if k == 0 else rng.uniform(.35, .55))
            x, y = cx + d * math.cos(a), cy + d * math.sin(a)
            if math.hypot(x, y) + r * 1.3 < WINDOW:
                fr.blob(x, y, r, .8 + .2 * (k == 0), aspect=rng.uniform(1., 1.6), turn=a, lumps=int(k == 0), kmax=5, amp=.12)
                drops += 1
    elif f < 12:         # a ragged blob with a few satellites on one or two sides
        r = rng.uniform(.30, .42)
        cx, cy = .25 * math.cos(ang0 + math.pi) * rng.uniform(.3, 1), .25 * math.sin(ang0 + math.pi) * rng.uniform(.3, 1)
        fr.blob(cx, cy, r, 1., aspect=rng.uniform(1.0, 1.4), turn=ang0, lumps=int(rng.integers(2, 4)), kmax=7, amp=.20)
        sectors = [(ang0, .4)] + ([(ang0 + rng.uniform(1.2, 2.2), .35)] if rng.uniform() < .6 else [])
        drops = fr.satellites(cx, cy, r, sectors, int(rng.integers(4, 9)), 1.25, 2.1, .12, stretch=.5)
    else:                # a ragged splat: lobed core and many flung satellites in two or three sectors
        r = rng.uniform(.26, .36)
        cx, cy = .2 * math.cos(ang0 + math.pi), .2 * math.sin(ang0 + math.pi)
        fr.blob(cx, cy, r, 1., aspect=rng.uniform(1.0, 1.3), turn=ang0, lumps=3, kmax=7, amp=.26)
        for _ in range(int(rng.integers(1, 3))):          # one or two lobes torn off the core
            a = ang0 + rng.normal(0, .8)
            fr.blob(cx + r * .95 * math.cos(a), cy + r * .95 * math.sin(a), r * rng.uniform(.35, .55), .8, aspect=rng.uniform(1.2, 1.8), turn=a, kmax=5, amp=.15)
        sectors = [(ang0 + rng.normal(0, .3), rng.uniform(.25, .45)) for _ in range(int(rng.integers(2, 4)))]
        drops = fr.satellites(cx, cy, r, sectors, int(rng.integers(10, 21)), 1.3, 2.6, .10, stretch=.9)
    return fr, drops


def grit_frame(f):
    fr = Frame(SEED + 2000 + 89 * f, edge_amp=0.)
    rng = fr.rng
    shade = np.zeros((T, T))
    chip_id = np.zeros((T, T))
    if f < 6:
        n = 1
    elif f < 12:
        n = int(rng.integers(2, 5))
    else:
        n = int(rng.integers(5, 11))
    base_r = [.0, .55, .40, .32, .28, .22, .20, .18, .16, .15, .14][min(n, 10)]
    ang0 = rng.uniform(0, 2 * math.pi)
    made = 0
    for k in range(n * 4):
        if made >= n:
            break
        r = base_r * (made + 1) ** -.55 * rng.uniform(.65, 1.2) if n > 1 else rng.uniform(.30, .62) * (1.0 if f % 2 else .7)
        if made == 0:
            cx, cy = rng.uniform(-.12, .12), rng.uniform(-.12, .12)
        else:
            a = ang0 + rng.normal(0, 1.0)
            d = rng.uniform(.25, .75) ** .8 * (WINDOW - r)
            cx, cy = d * math.cos(a), d * math.sin(a)
        # A convex angular chip: 4-7 corners round the circle (jittered, never bunched to a sliver), uneven radii,
        # drawn out by up to 2 (area kept).
        asp, turn = rng.uniform(1.0, 2.0), rng.uniform(0, math.pi)
        if math.hypot(cx, cy) + r * math.sqrt(asp) > WINDOW:
            continue
        nv = int(rng.integers(4, 8))
        th = (np.arange(nv) + rng.uniform(-.3, .3, nv)) * 2 * math.pi / nv + rng.uniform(0, 2 * math.pi)
        rad = rng.uniform(.6, 1.0, nv)
        px = rad * np.cos(th) * math.sqrt(asp)
        py = rad * np.sin(th) / math.sqrt(asp)
        ct, st = math.cos(turn), math.sin(turn)
        pts = np.stack([cx + r * (px * ct - py * st), cy + r * (px * st + py * ct)], 1)
        # Convex hull (gift wrap is enough for <= 7 points), then the signed distance to the polygon (max of half-planes).
        hull = convex_hull(pts)
        if len(hull) < 3:
            continue
        dist = np.full((T, T), -1e9)
        for i in range(len(hull)):
            p0, p1 = hull[i], hull[(i + 1) % len(hull)]
            e = p1 - p0
            nrm = np.array([e[1], -e[0]]) / (np.hypot(*e) + 1e-12)
            dist = np.maximum(dist, (fr.X - p0[0]) * nrm[0] + (fr.Y - p0[1]) * nrm[1])
        m = smoothstep(.9 / (T / 2), -.9 / (T / 2), dist)    # crisp: under a pixel each side
        if m.max() < .5:
            continue
        # Flat facets: the nearest of 2-4 seeds inside the chip, each its own shade.
        nf = int(rng.integers(2, 5))
        seeds = np.array([cx, cy]) + r * .45 * rng.uniform(-1, 1, (nf, 2))
        dd = np.stack([np.hypot(fr.X - sx, fr.Y - sy) for sx, sy in seeds])
        facet = np.argmin(dd, 0)
        shades = rng.uniform(.35, 1.0, nf)
        sh = shades[facet]
        put = m > fr.mask
        shade[put] = sh[put]
        chip_id[put] = rng.uniform(0, 1)
        fr.mask = np.maximum(fr.mask, m)
        made += 1
    return fr, shade, chip_id, made


def convex_hull(pts):
    pts = sorted(map(tuple, pts))
    if len(pts) < 3:
        return np.array(pts)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.array(lower[:-1] + upper[:-1])


def dust_frames():
    """One puff, sixteen moments: the same dabs (so the flipbook is continuous), spreading, growing, thinning, dropping out."""
    rng = np.random.default_rng(SEED + 3000)
    n = 22
    c = (np.arange(T) + .5) / T * 2 - 1
    X, Y = np.meshgrid(c, c)
    E = .06 * band(T, T * .04, rng)                         # the painted edge, shared by all frames
    ang = rng.uniform(0, 2 * math.pi, n)
    p0 = np.stack([np.cos(ang), np.sin(ang)], 1) * (.13 * rng.uniform(0, 1, n) ** .7)[:, None]
    p0[:, 1] -= .05                                         # the clump starts a little low, near the wheel
    vel = np.stack([np.cos(ang + rng.normal(0, .5, n)), np.sin(ang + rng.normal(0, .5, n))], 1) * rng.uniform(.18, .42, n)[:, None]
    vel[:, 1] -= .10                                        # and lifts (image up = -Y)
    s0 = .10 + .16 * rng.uniform(0, 1, n) ** 2.2            # dab radii by a power law: mostly small
    asp = rng.uniform(1.0, 1.7, n)
    turn = rng.uniform(0, math.pi, n)
    o0 = rng.uniform(.55, .9, n)
    die = rng.uniform(.45, 1.05, n)                         # each dab's own end (some outlive the puff)
    harm = [(rng.uniform(.04, .10, 3), rng.uniform(0, 2 * math.pi, 3)) for _ in range(n)]
    frames = []
    for f in range(16):
        t = f / 15
        grow = 1 + 1.5 * t ** .7
        travel = 1 - (1 - t) ** 2.2                         # fast out, settling
        cover = np.zeros((T, T))
        for i in range(n):
            life = np.clip(1 - t / die[i], 0, 1)
            o = o0[i] * life ** .8 * (1 - .35 * t)
            if o < .02:
                continue
            p = p0[i] + vel[i] * travel
            s = s0[i] * grow
            reach = math.hypot(*p) + s * asp[i] * 1.12
            if reach > WINDOW:                              # keep inside the frame: pull the dab in, never clip it
                k = WINDOW / reach
                p, s = p * k, s * k
            du, dv = X - p[0], Y - p[1]
            ct, st = math.cos(turn[i]), math.sin(turn[i])
            a, b = (du * ct + dv * st) / asp[i], -du * st + dv * ct
            th = np.arctan2(b, a)
            amp, ph = harm[i]
            rr = s * (1 + sum(amp[k] * np.cos((k + 2) * th + ph[k]) for k in range(3)))
            q = np.hypot(a, b) / rr + E
            dab = smoothstep(1.0, .62, q) * o                # flat-topped, soft-edged: a dab, not a smoke gaussian
            cover = 1 - (1 - cover) * (1 - dab)
        frames.append(cover)
    return frames


def tiles_to_atlas(tiles, channels=None):
    shape = (ATLAS, ATLAS) if channels is None else (ATLAS, ATLAS, channels)
    out = np.zeros(shape)
    for f, tile in enumerate(tiles):
        r, c = f // TILES, f % TILES
        out[r * T:(r + 1) * T, c * T:(c + 1) * T] = tile
    return out


# ---------------------------------------------------------------- the ground's palette
def palettes():
    bog = to_lin(load_png(BOG_STANDARD)[..., :3])
    col = to_lin(load_png(GV_COLOR)[..., :3])
    orh = load_png(GV_ORH)
    # mip-3-ish (DG1b samples mip 3): an 8 x 8 box over the 2048 bakes
    k = 8
    colm = col.reshape(col.shape[0] // k, k, col.shape[1] // k, k, 3).mean((1, 3))
    hb = orh[..., 2].reshape(orh.shape[0] // k, k, orh.shape[1] // k, k).mean((1, 3))
    stone = colm[hb > .45] * .82                      # DG1b: a stone face of the Loose bake x the ground's 0.82
    matrix = colm[hb < .20].mean(0) * .82 * 1.15      # the matrix between the stones, lightened x1.15 (dust)
    rng = np.random.default_rng(SEED + 4000)
    pick = stone[rng.integers(0, len(stone), 64)] * rng.uniform(.92, 1.06, (64, 1))
    lum = pick @ np.array([.2126, .7152, .0722])
    order = np.argsort(lum)
    tint_a = pick[order[:16]].mean(0)                # the darker quarter of the stone faces
    tint_b = pick[order[-16:]].mean(0)               # the lighter quarter
    variants = {}
    for v in ('Standard', 'Firm', 'Deep', 'Stony'):  # EGTMudVariant order; the slice means for MudTint (x0.8 wet in C++)
        variants[v] = to_lin(load_png(BOG_STANDARD.parent / ('T_MS_Bog%sColor.png' % v))[..., :3]).reshape(-1, 3).mean(0)
    return dict(bog=bog, bog_mean=bog.reshape(-1, 3).mean(0), gravel=col * .82, stone=pick, matrix=matrix,
                tint_a=tint_a, tint_b=tint_b, variants=variants)


def sheets(mud_rgba, grit_rgba, dust, pal):
    """The three atlases on grey (top) and on the ground's own colour bakes (bottom), lit simply, in sRGB."""
    grey = np.full((ATLAS, ATLAS, 3), to_lin(np.array(.5)))
    bog = pal['bog'][:ATLAS, :ATLAS]                  # one 1024 corner of the 2048 Standard bog bake (75 cm of ground)
    grav = pal['gravel'][:ATLAS, :ATLAS]
    L = np.array([-.45, -.55, .70])
    L /= np.linalg.norm(L)

    def lit(height, strength):
        gy, gx = np.gradient(height * strength)
        n = np.stack([-gx, gy, np.ones_like(gx)], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        return np.clip((n * L).sum(-1), 0, 1)

    wet = pal['bog_mean'] * .8                        # Fresh 1: FreshDarken 0.2
    mud_col = wet[None, None, :] * (.45 + .75 * lit(gauss(mud_rgba[..., 0], 1.0), 40.))[..., None]
    chip_col = pal['stone'][np.clip((grit_rgba[..., 1] * 63).astype(int), 0, 63)] * (.45 + .75 * grit_rgba[..., 0])[..., None]
    dust_col = np.broadcast_to(pal['matrix'], (ATLAS, ATLAS, 3))

    def over(bg, fg, a):
        return bg * (1 - a[..., None]) + fg * a[..., None]
    dark = np.full((ATLAS, ATLAS, 3), to_lin(np.array(.3)))   # the pale chips and dust (about sRGB 0.5) need a darker grey
    top = np.hstack([over(grey, mud_col, mud_rgba[..., 3]), over(dark, chip_col, grit_rgba[..., 3]), over(dark, dust_col, dust * .85)])
    bot = np.hstack([over(bog, mud_col, mud_rgba[..., 3]), over(grav, chip_col, grit_rgba[..., 3]), over(grav, dust_col, dust * .85)])
    img = to_srgb(np.vstack([top, bot]))
    # Frame grid lines (1 px, dark) so the frames read apart.
    for i in range(0, img.shape[0], T):
        img[i, :] = .15
    for j in range(0, img.shape[1], T):
        img[:, j] = .15
    return img


# ---------------------------------------------------------------- the clumps' render
def clump_render(objs, pal):
    scene = bpy.context.scene
    try:
        scene.render.engine = 'CYCLES'
    except TypeError as e:
        say('engine: %s' % e)
    scene.cycles.samples = 64
    try:
        scene.cycles.use_denoising = True
    except Exception:
        pass
    scene.render.resolution_x, scene.render.resolution_y = 1600, 760
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('W')
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (.55, .62, .75, 1)
    bg.inputs[1].default_value = .55
    scene.world = world
    sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
    sun.data.energy = 3.2
    sun.data.angle = math.radians(3)
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    scene.collection.objects.link(sun)

    def principled(name, rough):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        p.inputs['Roughness'].default_value = rough
        return m, p

    def bog_texture(m, p, darken, tile_m):
        nt = m.node_tree
        img = nt.nodes.new('ShaderNodeTexImage')
        img.image = bpy.data.images.load(str(BOG_STANDARD), check_existing=True)
        img.projection = 'BOX'
        img.projection_blend = .25
        tc = nt.nodes.new('ShaderNodeTexCoord')
        mp = nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (1 / tile_m, 1 / tile_m, 1 / tile_m)
        mul = nt.nodes.new('ShaderNodeMix')
        mul.data_type = 'RGBA'
        mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        mul.inputs[7].default_value = (darken, darken, darken, 1)
        nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
        nt.links.new(mp.outputs['Vector'], img.inputs['Vector'])
        nt.links.new(img.outputs['Color'], mul.inputs[6])
        nt.links.new(mul.outputs[2], p.inputs['Base Color'])

    wet, wp = principled('ClumpWet', .50)                  # Fresh 1: darker by FreshDarken 0.2, FreshRough 0.5
    bog_texture(wet, wp, .8, CLUMP_TILE_M)
    grey, gp = principled('GroundGrey', .85)
    gp.inputs['Base Color'].default_value = (.18, .18, .18, 1)
    ground, bgp = principled('GroundBog', .85)
    bog_texture(ground, bgp, 1.0, 1.5)         # the ground: ClodScaleCm 150, the bog's own tile
    for mat, y in ((grey, .07), (ground, -.07)):
        me = bpy.data.meshes.new('Ground')
        me.from_pydata([(-.10, -.07, 0), (.70, -.07, 0), (.70, .07, 0), (-.10, .07, 0)], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new('Ground', me)
        ob.location.y = y
        me.materials.append(mat)
        scene.collection.objects.link(ob)
    # Each clump twice, resting on the ground (lowest point at z = 0), a random yaw; the originals hidden.
    rng = np.random.default_rng(SEED + 5000)
    x = 0.0
    for ob in objs:
        w = max(ob.dimensions)
        x += w * .5 + .02
        for y in (.07, -.07):
            dup = bpy.data.objects.new(ob.name + '_r', ob.data.copy())
            dup.data.materials.clear()
            dup.data.materials.append(wet)
            dup.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
            scene.collection.objects.link(dup)
            bpy.context.view_layer.update()
            zmin = min((dup.matrix_world @ v.co).z for v in dup.data.vertices)
            dup.location = (x, y, -zmin)
        x += w * .5
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    cam.data.type = 'ORTHO'                                  # both rows the same scale, every clump in frame
    span = x
    cam.data.ortho_scale = span + .06
    cam.location = (span * .5, -.40, .40)                    # 45 degrees down onto the two rows' middle
    cam.rotation_euler = (math.radians(45), 0, 0)
    scene.collection.objects.link(cam)
    scene.camera = cam
    for ob in objs:
        ob.hide_render = True
    scene.render.filepath = str(OUT / 'Assets_Clumps.png')
    bpy.ops.render.render(write_still=True)
    for ob in objs:
        ob.hide_render = False


# ---------------------------------------------------------------- main
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    manifest = dict(plan='docs/WHEEL_SPRAY_PLAN.md P1', blender=bpy.app.version_string, seed=SEED)

    # 1. Clumps.
    rows, objs = [], []
    for i, spec in enumerate(CLUMPS):
        ob = build_clump(i, spec)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.context.view_layer.update()
        path = OUT / (ob.name + '.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path), **FBX)
        tris = len(ob.data.polygons)
        dims = [round(d * 100, 2) for d in ob.dimensions]
        rows.append(dict(name=ob.name, family=spec['family'], elongation=spec['aspect'], torn_lobes=spec['lobes'],
                         triangles=tris, vertices=len(ob.data.vertices), size_cm=dims,
                         fbx=str(path.relative_to(ROOT)).replace('\\', '/')))
        say('%s %s tris %d size cm %s' % (ob.name, spec['family'], tris, dims))
        assert tris <= 300, (ob.name, tris)
        objs.append(ob)
    manifest['clumps'] = dict(units='Blender metres; FBX centimetres (apply_unit_scale), -Z forward, Y up',
                              pivot='the bounds centre', material_slot='M_GT_Clod', rows=rows)

    # 2-4. Atlases.
    mud_tiles, mud_info = [], []
    for f in range(16):
        fr, drops = mud_frame(f)
        mud_tiles.append(fr)
        mud_info.append(dict(frame=f, coverage=round(float(fr.mask.mean()), 4), drops=drops))
    hmax = max(float(fr.height.max()) for fr in mud_tiles)
    mud = tiles_to_atlas([np.dstack([gauss(fr.height, 1.2) / hmax, np.zeros((T, T)), np.zeros((T, T)), fr.mask]) for fr in mud_tiles], 4)
    write_png(OUT / 'T_GT_SprayMud.png', mud)
    say('mud atlas written')
    grit_tiles, grit_info = [], []
    for f in range(16):
        fr, shade, cid, made = grit_frame(f)
        grit_tiles.append(np.dstack([shade * (fr.mask > .01), cid * (fr.mask > .01), np.zeros((T, T)), fr.mask]))
        grit_info.append(dict(frame=f, chips=made, coverage=round(float(fr.mask.mean()), 4)))
    grit = tiles_to_atlas(grit_tiles, 4)
    write_png(OUT / 'T_GT_SprayGrit.png', grit)
    say('grit atlas written')
    dframes = dust_frames()
    dust = tiles_to_atlas(dframes)
    write_png(OUT / 'T_GT_SprayDust.png', dust)
    say('dust flipbook written')
    layout = 'frame f at column f % 4, row f // 4, row 0 at the top; 256 px frames; everything inside 0.90 of the half frame'
    manifest['atlases'] = {
        'T_GT_SprayMud': dict(png='Art/Export/WheelSpray/T_GT_SprayMud.png', size=ATLAS, frames='4 x 4', layout=layout, format='RGBA 8-bit',
                              channels='R soft height (one scale over the atlas), G 0, B 0, A coverage (soft painted edge ~3 px)',
                              order='0-3 single drops (2-3 with satellites), 4-7 clusters of 2-4, 8-11 ragged blobs with satellites, 12-15 ragged splats',
                              frames_info=mud_info),
        'T_GT_SprayGrit': dict(png='Art/Export/WheelSpray/T_GT_SprayGrit.png', size=ATLAS, frames='4 x 4', layout=layout, format='RGBA 8-bit',
                               channels='R facet shade 0.35-1 (flat facets), G a random number per chip (palette pick), B 0, A mask (crisp)',
                               order='0-5 single chips, 6-11 two to four, 12-15 five to ten', frames_info=grit_info),
        'T_GT_SprayDust': dict(png='Art/Export/WheelSpray/T_GT_SprayDust.png', size=ATLAS, frames='4 x 4', layout=layout, format='grey 8-bit',
                               channels='coverage only', order='the puff over its life, frame 0 first (22 dabs: spread, grow, thin, drop out)',
                               coverage=[round(float(d.mean()), 4) for d in dframes]),
    }

    # 5. Palette and renders.
    pal = palettes()
    manifest['palette_linear'] = dict(mud_wet='Standard bog mean x0.8 (Fresh 1)', mud_wet_rgb=[round(float(v), 4) for v in pal['bog_mean'] * .8],
                                      gravel_stone='DG1b: Loose bake stone faces (ORH B > 0.45, 8 x 8 box) x0.82 x0.92-1.06, 64 picks',
                                      gravel_stone_mean=[round(float(v), 4) for v in pal['stone'].mean(0)],
                                      dust='Loose bake matrix (ORH B < 0.20) x0.82 x1.15', dust_rgb=[round(float(v), 4) for v in pal['matrix']],
                                      grit_tint_a=[round(float(v), 4) for v in pal['tint_a']], grit_tint_b=[round(float(v), 4) for v in pal['tint_b']],
                                      grit_tints='the darker and the lighter quarter of the 64 stone picks (GritTintA, GritTintB)',
                                      mud_variant_means={k: [round(float(c), 4) for c in v] for k, v in pal['variants'].items()},
                                      mud_variant_note='each bog slice bake mean, linear, dry (MudTint = x0.8 for wet)')
    write_png(OUT / 'Atlas_Sheets.png', sheets(mud, grit, dust, pal))
    say('Atlas_Sheets.png written')
    renders = dict(Atlas_Sheets='Art/Export/WheelSpray/Atlas_Sheets.png')
    if RENDER:
        clump_render(objs, pal)
        renders['Assets_Clumps'] = 'Art/Export/WheelSpray/Assets_Clumps.png'
        say('Assets_Clumps.png rendered')
    manifest['renders'] = renders
    bpy.context.preferences.filepaths.save_version = 0      # no .blend1 beside it
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'WheelSpray.blend'))
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    say('SPRAY_ASSETS_BUILT -> %s' % OUT)


main()
