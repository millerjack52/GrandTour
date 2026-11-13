"""MudRunner MRP item 4 (docs/MUDRUNNER_LESSONS_PLAN.md MRP): the PBR validation rows from the buffer-visualisation captures.

The checks (Art/Unreal/check_mud_variants.py on L_MudVariants, Art/Unreal/check_car_washed.py on L_MudDrive) take, besides
their look pictures, HighResShot captures that dump the GBuffer's BaseColor, Roughness and MaterialAO visualisations
(r.BufferVisualizationOverviewTargets; uncompressed EXR, so the values are the materials' own, linear), and list them in their
report under mrp.dumps with the camera. This reads them:
- calib: the strip's gravel (roughness 0.9 by construction, the landscape's groundtex): the dumps' encoding is checked against it
  (linear, or written through an sRGB decode, which is then undone for every capture);
- ground (one per variant on L_MudVariants, one on L_MudDrive): the middle of the picture (all mud ground: the camera looks down
  into the patch) - roughness 5th / 50th / 95th percentile, AO mean and 5th percentile, the base colour's linear mean and
  luminance. Pass: roughness p5 >= 0.40 (the translucent rut water is not in the GBuffer: what shows there is the mud under it);
- car: the sill band between the arches on the camera's side (world corners from the check, projected with the camera), its mud
  pixels (base colour luminance under 0.12; the paint is lighter): roughness median and p5, base colour mean. Pass: >= 0.45 when
  the mud is wet (MudWet >= 0.5), else reported;
- water (L_MudVariants): the rut water is translucent, so no GBuffer: the row is the material's own formula (live_mud_style.py
  MUDDY_HLSL, gt.Mud.PBR 1) over the pool's cells' turbidity as the check read it - a model, not a capture. Pass: median >= 0.12.
- carry (MRP follow-up, L_MudVariants under test wetness 1): carried mud on the gravel (brown pixels against grey) - its roughness
  against the wet gravel's. Pass: the mud's median 0.45 or more (the rain floor after MF_Weather). GR1c checks follow-up: the
  floor applies by the cover (MF_MudCover's FloorMask is the cover c) and not in MF_Weather's standing water (x (1 - Puddle)), so
  the mud pixels in the weather's puddles (roughness under 0.06: its 0.03) are left out and counted, the floor is read on the
  fully covered pixels - the upper quarter, p75 - and its threshold is one 8-bit GBuffer step under 0.45 (0.446: a floored pixel
  encodes as 114 or 115 of 255, 0.447 or 0.451); at least 5,000 unpuddled mud pixels. The median is still reported.
Base colour: the means against the soil range (linear albedo 0.05-0.25 dry; wet mud 0.65-0.8x of it, so 0.0325 at the least).
Writes <report dir>/pbr-rows.json and a greyscale view of each roughness and AO buffer (<capture>_Roughness_view.png).
numpy and Pillow (system Python).   python Art/sample_mud_pbr.py Art/Export/MudVariants/drive-report.json
"""
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SOIL_LO, SOIL_HI = 0.0325, 0.25
CAR_MUD_LUM = 0.12


def read_exr(path):
    """An uncompressed single-part scanline EXR (UE's writer with r.SaveEXR.CompressionQuality 0): {channel: HxW float32}."""
    data = Path(path).read_bytes()
    magic, version = struct.unpack_from('<ii', data, 0)
    assert magic == 20000630, 'not an EXR: %s' % path
    pos = 8
    attrs = {}
    while data[pos] != 0:
        end = data.index(b'\0', pos)
        name = data[pos:end].decode()
        pos = end + 1
        end = data.index(b'\0', pos)
        kind = data[pos:end].decode()
        pos = end + 1
        size = struct.unpack_from('<i', data, pos)[0]
        pos += 4
        attrs[name] = (kind, data[pos:pos + size])
        pos += size
    pos += 1
    assert attrs['compression'][1][0] == 0, '%s is compressed (set r.SaveEXR.CompressionQuality 0)' % path
    xmin, ymin, xmax, ymax = struct.unpack('<iiii', attrs['dataWindow'][1])
    width, height = xmax - xmin + 1, ymax - ymin + 1
    chans = []
    raw = attrs['channels'][1]
    q = 0
    while raw[q] != 0:
        end = raw.index(b'\0', q)
        cname = raw[q:end].decode()
        q = end + 1
        ptype = struct.unpack_from('<i', raw, q)[0]
        q += 16
        chans.append((cname, ptype))
    offsets = struct.unpack_from('<%dQ' % height, data, pos)
    sizes = {0: 4, 1: 2, 2: 4}
    dtypes = {0: '<u4', 1: '<f2', 2: '<f4'}
    out = {c: np.zeros((height, width), np.float32) for c, _t in chans}
    for off in offsets:
        y = struct.unpack_from('<i', data, off)[0] - ymin
        p = off + 8
        for cname, ptype in chans:
            n = width * sizes[ptype]
            out[cname][y] = np.frombuffer(data, dtypes[ptype], width, p).astype(np.float32)
            p += n
    return out


def load_buffer(base, name):
    """(HxWx3 float32 linear, how) for <base>_<name>.exr, else .png (8-bit, taken as written)."""
    exr = Path(str(base) + '_' + name + '.exr')
    if exr.exists():
        ch = read_exr(exr)
        return np.stack([ch.get('R'), ch.get('G'), ch.get('B')], axis=-1), 'exr'
    png = Path(str(base) + '_' + name + '.png')
    if png.exists():
        return np.asarray(Image.open(png).convert('RGB'), np.float32) / 255.0, 'png'
    return None, 'missing'


def srgb_encode(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def project(cam, point, width, height):
    c = np.array(cam['location'], float)
    f = np.array(cam['target'], float) - c
    f /= np.linalg.norm(f)
    r = np.array([-f[1], f[0], 0.0])
    r /= np.linalg.norm(r)
    up = np.cross(f, r)
    focal = 0.5 * width / math.tan(math.radians(cam['fov']) * 0.5)
    v = np.array(point, float) - c
    depth = v @ f
    return 0.5 * width + focal * (v @ r) / depth, 0.5 * height - focal * (v @ up) / depth


def pct(a, ps):
    return [round(float(x), 3) for x in np.percentile(a, ps)] if a.size else None


def lum(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def save_view(arr, path, box=None):
    img = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), 'L').convert('RGB')
    if box is not None:
        ImageDraw.Draw(img).polygon(box, outline=(255, 0, 0))
    img.save(path)


def main():
    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    out_dir = report_path.parent
    mrp = report.get('mrp') or {}
    dumps = mrp.get('dumps') or []
    rows = dict(report=str(report_path), encoding=None, captures=[], water=None, passes={})
    fix = None
    # The encoding, from the calibration capture (the gravel's 0.9).
    for d in dumps:
        if d['kind'] != 'calib':
            continue
        rough, how = load_buffer(d['base'], 'Roughness')
        if rough is None:
            continue
        h, w = rough.shape[:2]
        med = float(np.median(rough[int(h * 0.55):int(h * 0.95), int(w * 0.3):int(w * 0.7), 0]))
        if abs(med - 0.9) < 0.03:
            fix = 'linear'
        elif abs(med - 0.787) < 0.03:
            fix = 'srgb-decoded'
        else:
            fix = 'unknown'
        rows['encoding'] = dict(file_type=how, gravel_roughness_median=round(med, 3), expected=0.9, verdict=fix)
    for d in dumps:
        if d['kind'] == 'calib':
            continue
        base = d['base']
        rough, how = load_buffer(base, 'Roughness')
        colour, _h = load_buffer(base, 'BaseColor')
        ao, _a = load_buffer(base, 'MaterialAO')
        row = dict(name=d['name'], kind=d['kind'], variant=d.get('variant'), file_type=how)
        if rough is None or colour is None:
            row['missing'] = [n for n, a in (('Roughness', rough), ('BaseColor', colour), ('MaterialAO', ao)) if a is None]
            rows['captures'].append(row)
            continue
        if fix == 'srgb-decoded':
            rough, colour = srgb_encode(rough), srgb_encode(colour)
            ao = srgb_encode(ao) if ao is not None else None
        h, w = rough.shape[:2]
        if d['kind'] == 'ground':
            sel = (slice(int(h * 0.25), int(h * 0.95)), slice(int(w * 0.15), int(w * 0.85)))
            r = rough[sel][..., 0].ravel()
            c = colour[sel].reshape(-1, 3)
            row.update(pixels=int(r.size), rough_p5_50_95=pct(r, [5, 50, 95]), rough_under_040=round(float((r < 0.40).mean()), 4),
                       base_colour_mean=[round(float(x), 4) for x in c.mean(0)], base_luminance_mean=round(float(lum(c).mean()), 4))
            if ao is not None:
                a = ao[sel][..., 0].ravel()
                row.update(ao_mean=round(float(a.mean()), 3), ao_p5=round(float(np.percentile(a, 5)), 3))
            row['pass_rough_p5'] = bool(row['rough_p5_50_95'][0] >= 0.40)
            row['pass_soil_range'] = bool(SOIL_LO <= row['base_luminance_mean'] <= SOIL_HI)
            box = [(int(w * 0.15), int(h * 0.25)), (int(w * 0.85), int(h * 0.25)), (int(w * 0.85), int(h * 0.95)), (int(w * 0.15), int(h * 0.95))]
        elif d['kind'] == 'carry':
            # MRP follow-up: carried mud on the gravel under test wetness 1 - the mud (brown, (r - b) / (r + g + b) over 0.3, and dark,
            # luminance under 0.08: the gravel is grey, the tussocks' straw light) against the gravel, the middle of the picture.
            sel = (slice(int(h * 0.15), int(h * 0.95)), slice(int(w * 0.1), int(w * 0.9)))
            c = colour[sel].reshape(-1, 3)
            r = rough[sel][..., 0].ravel()
            chroma = (c[:, 0] - c[:, 2]) / np.maximum(c.sum(1), 1e-4)
            mud = (chroma > 0.3) & (lum(c) < 0.08)   # brown and dark: not the tussocks' straw
            grey = chroma < 0.15
            row.update(wetness=d.get('wetness'), mud_pixels=int(mud.sum()), gravel_pixels=int(grey.sum()),
                       mud_rough_p5_50_95=pct(r[mud], [5, 50, 95]), gravel_rough_p5_50_95=pct(r[grey], [5, 50, 95]),
                       mud_under_045=round(float((r[mud] < 0.45).mean()), 4) if mud.any() else None)
            # GR1c checks follow-up: MF_Weather's standing water (its roughness 0.03, the floor off there by design) left out; the
            # floor read on the fully covered mud (p75; the partly covered edges sit between the weather's and the floor by design).
            water = mud & (r < 0.06)
            dry = mud & (r >= 0.06)
            rd = r[dry]
            row.update(mud_in_puddle_share=round(float(water.sum() / max(1, mud.sum())), 4), mud_unpuddled_pixels=int(dry.sum()),
                       mud_unpuddled_rough_p5_25_50_75_95=pct(rd, [5, 25, 50, 75, 95]),
                       mud_unpuddled_floor_share=round(float((rd >= 0.446).mean()), 4) if rd.size else None,
                       gravel_in_puddle_share=round(float((r[grey] < 0.06).mean()), 4) if grey.any() else None,
                       floor_gate='p75 of the unpuddled mud >= 0.446 (0.45 less one 8-bit step), at least 5000 of them')
            row['pass_floor'] = bool(rd.size >= 5000 and row['mud_unpuddled_rough_p5_25_50_75_95'][3] >= 0.446)
            box = [(int(w * 0.1), int(h * 0.15)), (int(w * 0.9), int(h * 0.15)), (int(w * 0.9), int(h * 0.95)), (int(w * 0.1), int(h * 0.95))]
        else:
            pts = [project(d['camera'], p, w, h) for p in d['box_world']]
            box = [(int(x), int(y)) for x, y in pts]
            mask_img = Image.new('L', (w, h), 0)
            ImageDraw.Draw(mask_img).polygon(box, fill=1)
            inside = np.asarray(mask_img, bool)
            l = lum(colour)
            mud = inside & (l < CAR_MUD_LUM) & (l > 0.002)
            paint = inside & (l >= CAR_MUD_LUM)
            r = rough[..., 0][mud]
            row.update(box_pixels=int(inside.sum()), mud_pixels=int(mud.sum()), paint_pixels=int(paint.sum()), mud_wet=d.get('mud_wet'),
                       mud_rough_p5_50_95=pct(r, [5, 50, 95]), paint_rough_median=round(float(np.median(rough[..., 0][paint])), 3) if paint.any() else None,
                       mud_base_colour_mean=[round(float(x), 4) for x in colour[mud].mean(0)] if mud.any() else None,
                       mud_base_luminance_mean=round(float(l[mud].mean()), 4) if mud.any() else None)
            if ao is not None and mud.any():
                row['mud_ao_mean'] = round(float(ao[..., 0][mud].mean()), 3)
            wet = (d.get('mud_wet') or 0) >= 0.5
            row['wet'] = wet
            if r.size:
                row['pass_rough'] = bool(row['mud_rough_p5_50_95'][1] >= (0.45 if wet else 0.85 - 0.4 * (d.get('mud_wet') or 0) - 0.03))
        save_view(rough[..., 0], out_dir / (d['name'] + '_Roughness_view.png'), box)
        if ao is not None:
            save_view(ao[..., 0], out_dir / (d['name'] + '_AO_view.png'), box)
        rows['captures'].append(row)
    if mrp.get('water_model'):
        wm = mrp['water_model']
        turb = np.array(wm['turbidity'], float)
        r = wm['settled_rough'] + (wm['turbid_rough'] - wm['settled_rough']) * turb
        rows['water'] = dict(model=wm['note'], cells=int(turb.size), turbidity_mean=round(float(turb.mean()), 3),
                             rough_median=round(float(np.median(r)), 3) if r.size else None, rough_min=round(float(r.min()), 3) if r.size else None,
                             pass_median=bool(r.size and np.median(r) >= 0.12))
    rows['passes'] = dict(ground=[c.get('pass_rough_p5') for c in rows['captures'] if c['kind'] == 'ground'],
                          soil=[c.get('pass_soil_range') for c in rows['captures'] if c['kind'] == 'ground'],
                          car=[c.get('pass_rough') for c in rows['captures'] if c['kind'] == 'car'],
                          carry_wet=[c.get('pass_floor') for c in rows['captures'] if c['kind'] == 'carry'],
                          water=rows['water'] and rows['water']['pass_median'])
    (out_dir / 'pbr-rows.json').write_text(json.dumps(rows, indent=2))
    if rows['encoding']:
        e = rows['encoding']
        print('PBR encoding: %s dumps, the gravel reads %.3f (0.9 by construction): %s' % (e['file_type'], e['gravel_roughness_median'], e['verdict']))
    for c in rows['captures']:
        if c.get('missing'):
            print('PBR %s: missing %s' % (c['name'], ', '.join(c['missing'])))
        elif c['kind'] == 'carry':
            print('PBR %s (test wetness %s): carried mud %d px, roughness p5/50/95 %s (under 0.45 %s); in the weather puddles %s; unpuddled %d px, p5/25/50/75/95 %s, at the floor %s; the wet gravel %d px, %s (puddled %s) -> %s' % (
                c['name'], c['wetness'], c['mud_pixels'], c['mud_rough_p5_50_95'], c['mud_under_045'], c.get('mud_in_puddle_share'), c.get('mud_unpuddled_pixels', 0),
                c.get('mud_unpuddled_rough_p5_25_50_75_95'), c.get('mud_unpuddled_floor_share'), c['gravel_pixels'], c['gravel_rough_p5_50_95'], c.get('gravel_in_puddle_share'),
                'PASS' if c['pass_floor'] else 'FAIL'))
        elif c['kind'] == 'ground':
            print('PBR %s (%s): roughness p5/50/95 %s, under 0.40 %.2f %%, AO mean %s p5 %s, base colour mean %s (luminance %.4f) -> rough %s, soil %s' % (
                c['name'], c['variant'], c['rough_p5_50_95'], 100 * c['rough_under_040'], c.get('ao_mean'), c.get('ao_p5'), c['base_colour_mean'],
                c['base_luminance_mean'], 'PASS' if c['pass_rough_p5'] else 'FAIL', 'PASS' if c['pass_soil_range'] else 'OUT'))
        else:
            print('PBR %s: MudWet %s, %d mud px of %d in the sill box, mud roughness p5/50/95 %s (paint %s), mud base colour %s (luminance %s), AO %s -> %s' % (
                c['name'], c['mud_wet'], c['mud_pixels'], c['box_pixels'], c['mud_rough_p5_50_95'], c['paint_rough_median'], c['mud_base_colour_mean'],
                c['mud_base_luminance_mean'], c.get('mud_ao_mean'), 'PASS' if c.get('pass_rough') else ('FAIL' if 'pass_rough' in c else 'no mud')))
    if rows['water']:
        wr = rows['water']
        print('PBR rut water (model, translucent: no GBuffer): %d cells, turbidity mean %.3f, roughness median %s min %s -> %s' % (
            wr['cells'], wr['turbidity_mean'], wr['rough_median'], wr['rough_min'], 'PASS' if wr['pass_median'] else 'FAIL'))
    print('MUD_PBR_ROWS_OK')


if __name__ == '__main__':
    main()
