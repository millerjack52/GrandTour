"""LM5 phase A item 2 and A2 (docs/LIVING_MUD_PLAN.md LM5, docs/MUD_WET_STUDY.md): bake study 04's wet churn into four 2048
maps of one 3 m tile, truly tileable (the study's fields are periodic; no mirror).

Run headless after Art/Blender/build_mud_wet_study.py:
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 \
      --python Art/Blender/export_mud_wet.py [-- variant=Standard|Firm|Deep|Stony]
With no variant: phase A2's study (04_wet) into T_MS_Churn* and churn-bakes.json. With one (LM5b): that variant's study
(05_variants/<V>) into T_MS_Bog<V>{Color,Normal,Rough,Height} and bog-bakes-<V>.json. The names below are A2's.

On export_mud_style.py's pattern (a plane carrying the study material, Cycles CPU bakes on four threads, EMIT for the
values, a tangent-space NORMAL bake with green NEG_Y = DirectX, as the clay's), but the plane is the 3 m tile itself (its
UV 0-1 is one period of the fields) and every map bakes into a float image and is written by this script:
  T_MS_ChurnColor   RGB 8-bit, sRGB         (EMIT of NG_MW_Churn's Color)
  T_MS_ChurnNormal  RGB 8-bit, DirectX      (NORMAL bake of the group's bump)
  T_MS_ChurnRough   grey 8-bit, linear      (EMIT of the roughness)
  T_MS_ChurnHeight  grey 16-bit, linear     (EMIT of the 0-1 height; the range in cm is in the JSON, for the cavity)
into Art/Export/MudStyleUE, beside the clay's bakes. Then it checks the files it wrote (read back from disk):
- the tile join, per channel: the mean step across the wrapped edges over the mean step between neighbouring pixels
  inside (LM4b's seam ratio; about 1 = no seam), and the edge step's z-score among the 2047 interior row (column)
  steps (a seam stands far above 3);
- direction: the structure tensor's coherence over the whole tile (0 = no dominant direction, 1 = stripes) and its mean
  over 10 cm neighbourhoods (how stroke-like it is locally), with the clay and worked bakes measured the same way;
- value against T_MS_ClayColor: mean CIE L*, HSV value, linear luminance and saturation;
- roughness by zone (the study's F_Zones / F_Shape: open slurry, wet gaps, the upper half of the clods, crumbs) and in
  the lowest 20 % / highest 10 % of the height; the luminance by zone;
and renders the four files on a 9 m plane (3x3 tiles) under study 03's sky and sun: Bake_Tile3x3.png, with the 30 cm
window landmark z-scores of the centre tile. Writes Art/Export/MudStyleUE/churn-bakes.json.
"""
import bpy, json, math, zlib, struct, time, sys
import numpy as np
from pathlib import Path

T0 = time.time()
ROOT = Path(__file__).resolve().parents[2]
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
VARIANT = next((a.split('=', 1)[1] for a in ARGS if a.startswith('variant=')), None)
if VARIANT:     # LM5b: a churned-bog variant's study (build_mud_wet_study.py -- variant=<V>) -> T_MS_Bog<V>*
    STUDY = ROOT / 'Art/Export/MudStyleStudy/05_variants' / VARIANT
    PRE = 'T_MS_Bog' + VARIANT
    REPORT = 'bog-bakes-%s.json' % VARIANT
else:           # phase A2's study -> T_MS_Churn*
    STUDY = ROOT / 'Art/Export/MudStyleStudy/04_wet'
    PRE = 'T_MS_Churn'
    REPORT = 'churn-bakes.json'
SRC = STUDY / 'MudWetStudy.blend'
OUT = ROOT / 'Art/Export/MudStyleUE'
SIZE = 2048
TILE_M = 3.0


def rel(path):
    return str(Path(path).relative_to(ROOT)).replace('\\', '/')


def say(msg):
    print('MUD_WET_BAKE %6.1f s  %s' % (time.time() - T0, msg), flush=True)


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
    """The wrapped edge's mean step as a z-score among the interior row (and column) steps: (rows, columns). A seam
    stands out (z far above 3); a tile that joins sits inside the spread of its own interior steps."""
    rows = np.abs(np.diff(img, axis=0)).mean(1)
    cols = np.abs(np.diff(img, axis=1)).mean(0)
    er = np.abs(img[0, :] - img[-1, :]).mean()
    ec = np.abs(img[:, 0] - img[:, -1]).mean()
    return round(float((er - rows.mean()) / rows.std()), 2), round(float((ec - cols.mean()) / cols.std()), 2)


def gauss(a, sigma_px):
    k = np.hypot(np.fft.fftfreq(a.shape[0])[:, None], np.fft.rfftfreq(a.shape[1])[None, :])
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * (math.pi * sigma_px * k) ** 2), s=a.shape)


def coherence(a, cm_per_px):
    """(whole tile, mean over 10 cm neighbourhoods) of the structure tensor's coherence."""
    ax = (np.roll(a, -1, 1) - np.roll(a, 1, 1)) * .5
    ay = (np.roll(a, -1, 0) - np.roll(a, 1, 0)) * .5
    jxx, jyy, jxy = ax * ax, ay * ay, ax * ay
    whole = math.hypot(jxx.mean() - jyy.mean(), 2 * jxy.mean()) / max(jxx.mean() + jyy.mean(), 1e-12)
    s = 10.0 / cm_per_px / 2.0
    lxx, lyy, lxy = gauss(jxx, s), gauss(jyy, s), gauss(jxy, s)
    local = np.hypot(lxx - lyy, 2 * lxy) / np.maximum(lxx + lyy, 1e-12)
    return round(float(whole), 4), round(float(local.mean()), 4)


def colour_stats(srgb):
    lin = srgb_to_linear(srgb)
    lum = lin @ np.array([.2126, .7152, .0722])
    lstar = np.where(lum > .008856, 116 * np.cbrt(lum) - 16, 903.3 * lum)
    v = srgb.max(-1)
    sat = (srgb.max(-1) - srgb.min(-1)) / np.maximum(srgb.max(-1), 1e-6)
    return dict(lstar=float(lstar.mean()), value=float(v.mean()), lum=float(lum.mean()), sat=float(sat.mean()),
                mean_linear=[round(float(x), 4) for x in lin.reshape(-1, 3).mean(0)])


def landmarks(path):
    """The centre tile of a 3x3 render: 30 cm window mean luminance and contrast, their largest |z| and the share over 3."""
    a = read(path)[..., :3]
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


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 1
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    with bpy.data.libraries.load(str(SRC)) as (src, dst):
        dst.materials = ['M_MW_ChurnFlat']
        dst.worlds = ['Soft cool daylight']
        dst.objects = ['Directional daylight']
    mat = dst.materials[0]
    study = json.loads((STUDY / 'manifest.json').read_text())
    # The plane is one tile: 3 m, its UVMap 0-1 one period of the fields.
    me = bpy.data.meshes.new('Churn tile')
    h = TILE_M / 2
    me.from_pydata([(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name='UVMap')
    for loop in me.loops:
        v = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = ((v.x + h) / TILE_M, (v.y + h) / TILE_M)
    me.materials.append(mat)
    plane = bpy.data.objects.new('Churn tile', me)
    scene.collection.objects.link(plane)
    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    ns, ls = mat.node_tree.nodes, mat.node_tree.links
    p = next(n for n in ns if n.type == 'BSDF_PRINCIPLED')
    out = next(n for n in ns if n.type == 'OUTPUT_MATERIAL')
    group = next(n for n in ns if n.type == 'GROUP')
    em = ns.new('ShaderNodeEmission')
    target = ns.new('ShaderNodeTexImage')
    scene.render.bake.margin = 8
    scene.render.bake.normal_space = 'TANGENT'
    scene.render.bake.normal_g = 'NEG_Y'
    baked = {}
    for name, socket, kind in [(PRE + 'Color', 'Color', 'EMIT'), (PRE + 'Rough', 'Roughness', 'EMIT'),
                               (PRE + 'Height', 'Height', 'EMIT'), (PRE + 'Normal', None, 'NORMAL')]:
        im = bpy.data.images.new(name, SIZE, SIZE, alpha=False, float_buffer=True)
        im.colorspace_settings.name = 'Non-Color'
        target.image = im
        ns.active = target
        for link in list(out.inputs['Surface'].links):
            ls.remove(link)
        if kind == 'EMIT':
            for link in list(em.inputs['Color'].links):
                ls.remove(link)
            ls.new(group.outputs[socket], em.inputs['Color'])
            ls.new(em.outputs[0], out.inputs['Surface'])
        else:
            ls.new(p.outputs[0], out.inputs['Surface'])
        bpy.ops.object.bake(type=kind)
        a = np.empty(SIZE * SIZE * 4, np.float32)
        im.pixels.foreach_get(a)
        baked[name] = a.reshape(SIZE, SIZE, 4)[..., :3].astype(np.float64)
        say('baked ' + name)
    files = {}
    for name, arr, bits in [(PRE + 'Color', linear_to_srgb(baked[PRE + 'Color']), 8),
                            (PRE + 'Normal', baked[PRE + 'Normal'], 8),
                            (PRE + 'Rough', baked[PRE + 'Rough'][..., 0], 8),
                            (PRE + 'Height', baked[PRE + 'Height'][..., 0], 16)]:
        path = OUT / (name + '.png')
        write_png(path, arr, bits)
        files[name] = path
        say('wrote %s (%d-bit, %.2f MB)' % (path.name, bits, path.stat().st_size / 1048576.0))
    # Checks, on the files as written.
    back = {name: read(path) for name, path in files.items()}
    cm_px = TILE_M * 100 / SIZE
    report = dict(source='%s (Art/Blender/build_mud_wet_study.py), baked by Art/Blender/export_mud_wet.py' % rel(STUDY), variant=VARIANT or 'A2',
                  tile_m=TILE_M, size=SIZE, mirror=False, normal='DirectX tangent (green = -Y), from the bump of the height',
                  height_range_cm=study['fields']['height_range_cm'], fields=study['fields'], maps={})
    for name, a in back.items():
        chans = 'RGB' if name in (PRE + 'Color', PRE + 'Normal') else 'R'
        seams = {c: round(seam_ratio(a[..., i]), 3) for i, c in enumerate(chans)}
        zs = {c: seam_z(a[..., i]) for i, c in enumerate(chans)}
        row = dict(file=str(files[name].relative_to(ROOT)).replace('\\', '/'), bits=16 if name == PRE + 'Height' else 8,
                   channels=len(chans), colour='sRGB' if name == PRE + 'Color' else 'linear', seam_ratio=seams,
                   seam_z_rows_cols=zs, bytes=files[name].stat().st_size)
        if name != PRE + 'Normal':
            row['min'], row['mean'], row['max'] = [round(float(f(a[..., 0])), 4) for f in (np.min, np.mean, np.max)]
        report['maps'][name] = row
        say('%s seam ratio %s, edge z (rows, cols) %s' % (name, seams, zs))
    col = back[PRE + 'Color'][..., :3]
    height = back[PRE + 'Height'][..., 0]
    rough = back[PRE + 'Rough'][..., 0]
    clay = read(OUT / 'T_MS_ClayColor.png')[..., :3]
    worked = read(OUT / 'T_MS_WorkedColor.png')[..., :3]
    lum = lambda s: srgb_to_linear(s) @ np.array([.2126, .7152, .0722])
    churn_c, clay_c, worked_c = colour_stats(col), colour_stats(clay), colour_stats(worked)
    report['value'] = dict(churn=churn_c, clay=clay_c, worked=worked_c,
                           ratio_to_clay=dict(lstar=round(churn_c['lstar'] / clay_c['lstar'], 3),
                                              value=round(churn_c['value'] / clay_c['value'], 3),
                                              linear_luminance=round(churn_c['lum'] / clay_c['lum'], 3),
                                              saturation=round(churn_c['sat'] / clay_c['sat'], 3)))
    report['direction'] = dict(note='structure-tensor coherence: (whole tile, mean over 10 cm); 0 = no direction, 1 = stripes',
                               churn_colour=coherence(lum(col), cm_px), churn_height=coherence(height, cm_px),
                               clay_colour=coherence(lum(clay), 600.0 / clay.shape[0]),
                               worked_colour=coherence(lum(worked), 600.0 / worked.shape[0]))
    # Phase A2's zones (the study's F_Zones: R open slurry, G clods, B wet gaps; F_Shape B crumbs).
    zones = read(STUDY / 'fields/F_Zones.png')
    shape = read(STUDY / 'fields/F_Shape.png')
    lo, hi = np.percentile(height, [20, 90])
    clod = zones[..., 1] > .9
    clod_h = height[clod]
    top = clod & (height >= np.percentile(clod_h, 50))
    report['roughness'] = dict(slurry=[round(float(np.percentile(rough[zones[..., 0] > .9], q)), 3) for q in (5, 50, 95)],
                               wet_gaps=round(float(rough[zones[..., 2] > .5].mean()), 3) if (zones[..., 2] > .5).any() else None,
                               clod_tops_upper_half=round(float(rough[top].mean()), 3),
                               crumbs=round(float(rough[shape[..., 2] > .9].mean()), 3),
                               lowest_20pc_height=round(float(rough[height <= lo].mean()), 3),
                               highest_10pc_height=round(float(rough[height >= hi].mean()), 3),
                               glossy_share_under_04=round(float((rough < .4).mean() * 100), 1),
                               matte_share_over_08=round(float((rough > .8).mean() * 100), 1),
                               note='slurry as its 5th / 50th / 95th percentiles')
    lin = srgb_to_linear(col) @ np.array([.2126, .7152, .0722])
    report['value_by_zone_linear_luminance'] = dict(slurry=round(float(lin[zones[..., 0] > .9].mean()), 4),
                                                    clod_tops=round(float(lin[top].mean()), 4),
                                                    wet_gaps=round(float(lin[zones[..., 2] > .5].mean()), 4) if (zones[..., 2] > .5).any() else None)
    if (STUDY / 'fields/F_Stones.png').exists():
        stones = read(STUDY / 'fields/F_Stones.png')
        top = (stones[..., 2] > .9) & (stones[..., 1] > .5)
        report['roughness']['stone_tops'] = round(float(rough[top].mean()), 3)
        report['value_by_zone_linear_luminance']['stone_tops'] = round(float(lin[top].mean()), 4)
        report['stone_visible_share'] = round(float((stones[..., 2] > .5).mean() * 100), 2)
    say('value %s' % json.dumps(report['value']['ratio_to_clay']))
    say('direction %s' % json.dumps(report['direction']))
    say('roughness %s' % json.dumps(report['roughness']))
    say('luminance by zone %s' % json.dumps(report['value_by_zone_linear_luminance']))
    # The four files on a 9 m plane, 3x3, under 03's sky and sun.
    scene.world = dst.worlds[0]
    sun = dst.objects[0]
    scene.collection.objects.link(sun)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.cycles.samples = 40
    scene.render.resolution_x = scene.render.resolution_y = 1800
    plane.hide_render = True
    m = bpy.data.materials.new('M_MW_ChurnBakes')
    m.use_nodes = True
    mn, ml = m.node_tree.nodes, m.node_tree.links
    bsdf = next(n for n in mn if n.type == 'BSDF_PRINCIPLED')
    uvn = mn.new('ShaderNodeUVMap')
    uvn.uv_map = 'UVMap'
    tex = {}
    for name in files:
        t = mn.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(str(files[name]), check_existing=False)
        t.image.colorspace_settings.name = 'sRGB' if name == PRE + 'Color' else 'Non-Color'
        t.extension = 'REPEAT'
        t.interpolation = 'Linear'
        ml.new(uvn.outputs[0], t.inputs['Vector'])
        tex[name] = t
    ml.new(tex[PRE + 'Color'].outputs['Color'], bsdf.inputs['Base Color'])
    ml.new(tex[PRE + 'Rough'].outputs['Color'], bsdf.inputs['Roughness'])
    sep = mn.new('ShaderNodeSeparateColor')
    ml.new(tex[PRE + 'Normal'].outputs['Color'], sep.inputs[0])
    inv = mn.new('ShaderNodeMath')
    inv.operation = 'SUBTRACT'
    inv.inputs[0].default_value = 1.0
    ml.new(sep.outputs[1], inv.inputs[1])            # DirectX -> Blender's OpenGL green
    comb = mn.new('ShaderNodeCombineColor')
    ml.new(sep.outputs[0], comb.inputs[0])
    ml.new(inv.outputs[0], comb.inputs[1])
    ml.new(sep.outputs[2], comb.inputs[2])
    nm = mn.new('ShaderNodeNormalMap')
    nm.space = 'TANGENT'
    nm.uv_map = 'UVMap'
    ml.new(comb.outputs[0], nm.inputs['Color'])
    ml.new(nm.outputs[0], bsdf.inputs['Normal'])
    bsdf.inputs['Specular IOR Level'].default_value = .5
    big = bpy.data.meshes.new('Churn bakes 3x3')
    big.from_pydata([(-4.5, -4.5, 0), (4.5, -4.5, 0), (4.5, 4.5, 0), (-4.5, 4.5, 0)], [], [(0, 1, 2, 3)])
    buv = big.uv_layers.new(name='UVMap')
    for loop in big.loops:
        v = big.vertices[loop.vertex_index].co
        buv.data[loop.index].uv = ((v.x + 4.5) / 3, (v.y + 4.5) / 3)
    big.materials.append(m)
    scene.collection.objects.link(bpy.data.objects.new('Churn bakes 3x3', big))
    cd = bpy.data.cameras.new('Bake3x3')
    cd.type = 'ORTHO'
    cd.ortho_scale = 9.0
    cam = bpy.data.objects.new('Bake3x3', cd)
    cam.location = (0, 0, 10)
    scene.collection.objects.link(cam)
    scene.camera = cam
    scene.render.filepath = str(STUDY / 'Bake_Tile3x3.png')
    bpy.ops.render.render(write_still=True)
    say('rendered Bake_Tile3x3')
    report['bake_tile3x3'] = dict(file=rel(STUDY / 'Bake_Tile3x3.png'), landmarks_30cm=landmarks(STUDY / 'Bake_Tile3x3.png'))
    if (STUDY / 'Tile3x3.png').exists():
        report['study_tile3x3'] = dict(file=rel(STUDY / 'Tile3x3.png'), landmarks_30cm=landmarks(STUDY / 'Tile3x3.png'))
    (OUT / REPORT).write_text(json.dumps(report, indent=2))
    say('landmarks %s' % json.dumps({k: v['landmarks_30cm'] for k, v in report.items() if k.endswith('tile3x3')}))
    print('MUD_WET_BAKE_OK', flush=True)


main()
