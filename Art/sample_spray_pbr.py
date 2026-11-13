"""Wheel spray P2b / P2c (docs/WHEEL_SPRAY_PLAN.md): the spray's gates, from Art/Unreal/check_wheel_spray.py's captures. Every capture of a
scenario is one paused frame (the picture, the buffer dump, the hides), so the images line up pixel for pixel.
- P2b, base colour (HighResShot's BaseColor, CustomDepth and Roughness, uncompressed EXR, linear; Art/sample_gravel_pbr.py's method and
  reader): only the car's Niagara components were in custom depth; the visible masked sprites are the custom-depth pixels whose
  BaseColor differs from the same frame's dump with those components hidden (P2c: custom depth also holds sprites hidden behind the
  body). The GBuffer comes at the 87 % render resolution; the mask is resampled onto it. Spray_Mud_Close and
  Spray_Mud_Drive: the droplets' median luminance within the mud soil band 0.03-0.25; Spray_Gravel_Close: the grit's within 30 % of the
  gravel ground's p50, 0.197 (Art/Export/DeformableGravel/pbr-rows.json).
- P2c, droplets above the arch (Spray_Mud_Close): the share of the visible droplet pixels above the camera's rear wheel's arch-top line
  (its contact + twice the wheel radius + 10 cm, projected; check-report arch_line); asked at least 25 %.
- P2c, dust in shadow (Spray_Gravel_Close): the dust mask is where the picture and Spray_Gravel_Close_NoSprites (the same frame, the
  car's Niagara components hidden) differ by more than 0.01 in linear luminance, less the grit (the custom-depth mask, grown 2 px).
  A dust pixel is in shadow where the frame without sprites is under 0.4 x its sunlit ground (the 75th percentile of the lower half).
  Asked: the median final-image luminance of the dust in shadow at least 0.5 x that of the dust in sun. The same numbers for the
  same frame with the dust's lighting swept (Spray_Gravel_Close_Dust_L<lit>_F<floor>, MPC_GT_Spray) as dust_light_sweep.
Writes Art/Export/WheelSpray/spray-pbr.json.  python Art/sample_spray_pbr.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sample_mud_pbr import read_exr   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Art/Export/WheelSpray'
GRAVEL_P50 = 0.197
REPORT = json.loads((OUT / 'check-report.json').read_text())


def lum(d):
    return 0.2126 * d['R'] + 0.7152 * d['G'] + 0.0722 * d['B']


def resample(a, shape):
    """Nearest-neighbour onto shape: the same view, so a pixel maps by its fraction across the frame."""
    h, w = shape
    rows = np.minimum(((np.arange(h) + .5) * a.shape[0] / h).astype(int), a.shape[0] - 1)
    cols = np.minimum(((np.arange(w) + .5) * a.shape[1] / w).astype(int), a.shape[1] - 1)
    return a[rows][:, cols]


def sprite_mask(name):
    """The masked sprites' pixels at the output resolution (the CustomDepth dump's own)."""
    d = read_exr(str(OUT / (name + '_Gate')) + '_CustomDepth.exr')['R']
    vals, counts = np.unique(np.round(d, 4), return_counts=True)
    empty = vals[np.argmax(counts)]
    return np.abs(d - empty) > 1e-3, float(empty)


def visible(name):
    """The visible masked sprites at the GBuffer's resolution: in custom depth, and where the BaseColor differs from the same frame's
    dump without the car's Niagara components (a sprite hidden behind the body is in custom depth but shows the body)."""
    colour = read_exr(str(OUT / (name + '_Gate')) + '_BaseColor.exr')
    without = read_exr(str(OUT / (name + '_Gate_NoSprites')) + '_BaseColor.exr')
    mask, empty = sprite_mask(name)
    m = resample(mask, colour['R'].shape)
    changed = sum(np.abs(colour[k] - without[k]) for k in 'RGB') > 1e-3
    return colour, m & changed, int(m.sum()), empty


def base_colour(name):
    colour, m, in_custom_depth, empty = visible(name)
    L = lum(colour)
    v = L[m]
    row = dict(empty_custom_depth=empty, custom_depth_pixels=in_custom_depth, sprite_pixels=int(m.sum()))
    if v.size:
        row.update(luminance_median=round(float(np.median(v)), 4), luminance_p10_50_90=[round(float(x), 4) for x in np.percentile(v, [10, 50, 90])],
                   rgb_median=[round(float(np.median(colour[k][m])), 4) for k in 'RGB'])
    return row


def picture(name):
    """A capture's linear luminance."""
    px = np.asarray(Image.open(OUT / (name + '.png')).convert('RGB'), dtype=np.float64) / 255.
    lin = np.where(px <= .04045, px / 12.92, ((px + .055) / 1.055) ** 2.4)
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def pic(name):
    return next(p for p in REPORT['pictures'] if p['name'] == name)


def above_arch():
    _, mask, _, _ = visible('Spray_Mud_Close')
    p = pic('Spray_Mud_Close')
    line = p['arch_line']
    wheel = p['at_capture']['camera']['wheel']
    row = next((w for w in line['wheels'] if w['wheel'] == wheel and w['screen']), None) or next(w for w in line['wheels'] if w['screen'])
    vy = float(line['viewport'][1]) or mask.shape[0]
    y = row['screen'][1] * mask.shape[0] / vy
    ys = np.nonzero(mask)[0]
    share = float((ys < y).mean()) if ys.size else 0.0
    return dict(camera_wheel=wheel, arch_wheel=row['wheel'], wheel_radius_cm=row['radius_cm'], arch_line_y_px=round(y, 1), droplet_pixels=int(ys.size),
                above_pixels=int((ys < y).sum()), share_above=round(share, 3), gate='at least 0.25', **{'pass': bool(share >= .25)})


def dust_shadow(name='Spray_Gravel_Close'):
    a = picture(name)
    b = picture('Spray_Gravel_Close_NoSprites')
    grit, _ = sprite_mask('Spray_Gravel_Close')
    grit = resample(grit, a.shape)
    grown = grit.copy()
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            grown |= np.roll(np.roll(grit, dy, 0), dx, 1)
    dust = (np.abs(a - b) > .01) & ~grown
    lower = b[b.shape[0] // 2:]
    sunlit = float(np.percentile(lower, 75))
    shadow = b < .4 * sunlit
    ds, dn = a[dust & shadow], a[dust & ~shadow]
    out = dict(dust_pixels=int(dust.sum()), grit_pixels=int(grit.sum()), sunlit_ground_p75=round(sunlit, 4), shadow_threshold=round(.4 * sunlit, 4),
               dust_in_shadow_pixels=int(ds.size), dust_in_sun_pixels=int(dn.size))
    if ds.size and dn.size:
        ms, mn = float(np.median(ds)), float(np.median(dn))
        out.update(dust_in_shadow_median=round(ms, 4), dust_in_sun_median=round(mn, 4), ratio=round(ms / max(mn, 1e-6), 3), gate='at least 0.5',
                   **{'pass': bool(ms >= .5 * mn)})
    else:
        out['pass'] = False
    return out


def clumping(name):
    """P2d: the visible droplets' screen positions in 32 px cells of the 1440 x 900 output: the counts' coefficient of variation
    over all 1260 cells (higher = more clumped)."""
    _, m, _, _ = visible(name)
    mm = resample(m, (900, 1440))
    cells = mm[:896, :1440].reshape(28, 32, 45, 32).sum((1, 3)).astype(float)
    return dict(droplet_pixels=int(mm.sum()), occupied_cells=int((cells > 0).sum()), cells=int(cells.size),
                cv_32px_cells=round(float(cells.std() / max(cells.mean(), 1e-9)), 3))


def muddy_splash():
    """P2d: the CPU Water spray's pixels in Spray_Mud_Close - where it differs from Spray_Mud_Close_NoWater (the same paused frame, the
    Water ISM hidden) by over 0.01 in linear luminance. The spray is translucent and writes no BaseColor, so its colour is read in the
    final image: the median linear luminance in 0.03-0.3 and R > G > B (the medians)."""
    def rgb(n):
        px = np.asarray(Image.open(OUT / (n + '.png')).convert('RGB'), dtype=np.float64) / 255.
        return np.where(px <= .04045, px / 12.92, ((px + .055) / 1.055) ** 2.4)
    a, b = rgb('Spray_Mud_Close'), rgb('Spray_Mud_Close_NoWater')
    la = a @ np.array([.2126, .7152, .0722])
    lb = b @ np.array([.2126, .7152, .0722])
    m = np.abs(la - lb) > .01
    if not m.any():
        return dict(water_pixels=0, **{'pass': False})
    med = [float(np.median(a[..., c][m])) for c in range(3)]
    lm = float(np.median(la[m]))
    return dict(water_pixels=int(m.sum()), luminance_median=round(lm, 4), rgb_median=[round(x, 4) for x in med],
                gate='median luminance 0.03-0.3 and R > G > B (final image)', **{'pass': bool(.03 <= lm <= .3 and med[0] > med[1] > med[2])})


def main():
    rows = {}
    for name in ('Spray_Mud_Close', 'Spray_Mud_Drive'):
        r = base_colour(name)
        med = r.get('luminance_median')
        r['gate'] = 'median in 0.03-0.25'
        r['pass'] = bool(med is not None and 0.03 <= med <= 0.25)
        rows[name + ' base colour'] = r
    r = base_colour('Spray_Gravel_Close')
    med = r.get('luminance_median')
    r['gate'] = 'median within 30 %% of %.3f (%.3f-%.3f)' % (GRAVEL_P50, GRAVEL_P50 * .7, GRAVEL_P50 * 1.3)
    r['ratio_to_ground'] = round(med / GRAVEL_P50, 3) if med is not None else None
    r['pass'] = bool(med is not None and abs(med / GRAVEL_P50 - 1.) <= .3)
    rows['Spray_Gravel_Close base colour'] = r
    rows['Spray_Mud_Close droplets above the arch'] = above_arch()
    rows['Spray_Gravel_Close dust in shadow'] = dust_shadow()
    rows['Spray_Mud_Close muddy splash'] = muddy_splash()
    heights = pic('Spray_Mud_Drive').get('droplet_heights', {})
    p95 = heights.get('height_p95_m')
    rows['Spray_Mud_Drive droplet height'] = dict(heights, gate='p95 at most 2.5 m', **{'pass': bool(p95 is not None and p95 <= 2.5)})
    clump = clumping('Spray_Mud_Drive')
    clump['pass'] = True   # reported, not gated
    rows['Spray_Mud_Drive droplet clumping'] = clump
    # P2c: the same frame with the dust's lighting swept (MPC_GT_Spray DustLit, DustFloor); not gates, the evidence for the default.
    sweep = {}
    for p in sorted(OUT.glob('Spray_Gravel_Close_Dust_L*_F*.png')):
        r = dust_shadow(p.stem)
        sweep[p.stem.replace('Spray_Gravel_Close_Dust_', '')] = {k: r.get(k) for k in ('dust_in_shadow_median', 'dust_in_sun_median', 'ratio', 'pass')}
    out = dict(rows=rows, dust_light_sweep=sweep, ok=all(v['pass'] for v in rows.values()))
    (OUT / 'spray-pbr.json').write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


main()
