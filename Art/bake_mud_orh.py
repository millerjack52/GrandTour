"""MudRunner MRP item 2 (docs/MUDRUNNER_LESSONS_PLAN.md MRP): the bog variants' packed ORH maps.

For each variant (Standard, Firm, Deep, Stony), from its bakes in Art/Export/MudStyleUE (Art/Blender/export_mud_wet.py):
- T_MS_Bog<V>AO.png: horizon-based ambient occlusion from T_MS_Bog<V>Height.png (16-bit, the 0-1 height over the variant's
  height_range_cm in bog-bakes-<V>.json, a true 3 m tile of 2048 px): per pixel, 16 directions, each marched to 6 cm
  (AO_RADIUS_CM) over 11 integer steps (wrapped: the tiles are tileable); a direction's occlusion is the largest sin of the
  horizon's elevation above the horizontal, attenuated by (1 - (r / R)^2) so nothing cuts off at the radius; the AO is one
  minus the mean over the directions (the sky's cosine-weighted visibility above level ground). 8-bit, linear.
- T_MS_Bog<V>ORH.png: R the AO, G the roughness remapped into the physically based bands, B the height (the bake's 0-1).
  The remap (linear, exactly invertible over the bakes' range 0.149-0.902): r' = 0.45 + (r - 0.14) x 0.5 / 0.77, clamped
  0.45-0.95, so the slurry (0.15-0.38) lands in the wet-mud band (0.46-0.61) and the lump tops (0.83-0.90) in the dry band
  (0.89-0.95). The materials' gt.Mud.PBR 0 path inverts it (r = 0.14 + (r' - 0.45) x 1.54) for the look before MRP.
MRP follow-up 3: ORH's B is the parallax's height with soft rims (soft_rims: the slope capped at SOFT_SLOPE 1.5 % of the range per
texel, then a SOFT_SIGMA 1.5 texel Gaussian); the AO is still from the sharp height and the shading normal stays the bake's. (Follow-up
2's OR and 8-bit height PNGs are no longer written.)
Writes Art/Export/MudStyleUE/bog-orh.json (per variant: the AO's mean and percentiles, the roughness before and after, the
colour's linear mean and luminance). numpy and Pillow (system Python).   python Art/bake_mud_orh.py
"""
import json
import math
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'Art/Export/MudStyleUE'
VARIANTS = ['Standard', 'Firm', 'Deep', 'Stony']
TILE_CM = 300.0
AO_RADIUS_CM = 6.0
DIRECTIONS = 16
STEPS_PX = [1, 2, 3, 5, 7, 10, 14, 19, 25, 32, 41]   # integer radii up to 6 cm (41 px of 0.146 cm)
ROUGH_BAKE = (0.14, 0.91)
ROUGH_PBR = (0.45, 0.95)


def remap_rough(r):
    lo, hi = ROUGH_BAKE
    a, b = ROUGH_PBR
    return np.clip(a + (r - lo) * (b - a) / (hi - lo), a, b)


def horizon_ao(h_cm, px_cm):
    radius_px = AO_RADIUS_CM / px_cm
    occ_sum = np.zeros_like(h_cm)
    for k in range(DIRECTIONS):
        a = 2.0 * math.pi * (k + 0.5) / DIRECTIONS
        best = np.zeros_like(h_cm)
        seen = set()
        for r in STEPS_PX:
            dx, dy = int(round(r * math.cos(a))), int(round(r * math.sin(a)))
            if (dx, dy) in seen or (dx == 0 and dy == 0):
                continue
            seen.add((dx, dy))
            d_px = math.hypot(dx, dy)
            if d_px > radius_px * 1.02:
                continue
            q = np.roll(h_cm, shift=(-dy, -dx), axis=(0, 1))
            rise = q - h_cm
            d_cm = d_px * px_cm
            sin_e = rise / np.sqrt(rise * rise + d_cm * d_cm)
            atten = 1.0 - (d_px / radius_px) ** 2
            np.maximum(best, sin_e * atten, out=best)
        occ_sum += best
    return np.clip(1.0 - occ_sum / DIRECTIONS, 0.0, 1.0)


# MRP follow-up 3: the parallax height's rims softened (the bakes' lump rims rise up to 8 % of the range in one texel: the parallax
# stretched those few texels of colour, normal and AO into bands down every steep flank). The slope is capped at SOFT_SLOPE of the
# range per texel by the mean of the height's two cone envelopes (the highest h(q) - s d(p, q) and the lowest h(q) + s d(p, q):
# both are s-Lipschitz, and both equal h wherever no rim is within reach, so tops and floors keep their levels), then a Gaussian
# of SOFT_SIGMA texels (it keeps the cap). Not volume-preserving. Wrapped: the tiles are tileable.
SOFT_SLOPE = 0.015
SOFT_SIGMA = 1.5


def soft_rims(h):
    s = SOFT_SLOPE
    steps = [((dy, dx), s * math.hypot(dx, dy)) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]
    up, lo = h.copy(), h.copy()
    for _ in range(int(1.0 / s) + 4):
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
    soft = 0.5 * (up + lo)
    r = int(math.ceil(3.0 * SOFT_SIGMA))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / SOFT_SIGMA) ** 2)
    k /= k.sum()
    for axis in (0, 1):
        soft = sum(w * np.roll(soft, i - r, axis=axis) for i, w in enumerate(k))
    return np.clip(soft, 0.0, 1.0).astype(np.float32)


def max_slope(h):
    return float(max(np.abs(h - np.roll(h, 1, axis=0)).max(), np.abs(h - np.roll(h, 1, axis=1)).max()))


def pct(a, ps):
    return [round(float(x), 3) for x in np.percentile(a, ps)]


def main():
    report = dict(note=__doc__.split('\n\n')[0], ao=dict(radius_cm=AO_RADIUS_CM, directions=DIRECTIONS, steps_px=STEPS_PX),
                  rough_remap=dict(bake=ROUGH_BAKE, pbr=ROUGH_PBR, formula="r' = 0.45 + (r - 0.14) x 0.5 / 0.77, clamped 0.45-0.95",
                                   inverse='r = 0.14 + (r\' - 0.45) x 1.54'), variants={})
    for v in VARIANTS:
        t0 = time.time()
        meta = json.loads((SRC / ('bog-bakes-%s.json' % v)).read_text())
        lo, hi = meta['height_range_cm']
        himg = Image.open(SRC / ('T_MS_Bog%sHeight.png' % v))
        h01 = np.asarray(himg, dtype=np.float32) / 65535.0
        if h01.ndim == 3:
            h01 = h01[..., 0]
        size = h01.shape[0]
        px_cm = TILE_CM / size
        h_cm = (lo + h01 * (hi - lo)).astype(np.float32)
        ao = horizon_ao(h_cm, px_cm)
        r8 = np.asarray(Image.open(SRC / ('T_MS_Bog%sRough.png' % v)).convert('L'), dtype=np.float32) / 255.0
        rp = remap_rough(r8)
        ao8 = (ao * 255.0 + 0.5).astype(np.uint8)
        Image.fromarray(ao8, 'L').save(SRC / ('T_MS_Bog%sAO.png' % v))
        # MRP follow-up 3: B is the parallax's height with soft rims (soft_rims); the AO above and the shading normal keep the sharp bake.
        hs = soft_rims(h01)
        slope_before, slope_after = max_slope(h01), max_slope(hs)
        orh = np.stack([ao8, (rp * 255.0 + 0.5).astype(np.uint8), (np.clip(hs, 0, 1) * 255.0 + 0.5).astype(np.uint8)], axis=-1)
        Image.fromarray(orh, 'RGB').save(SRC / ('T_MS_Bog%sORH.png' % v))

        c = np.asarray(Image.open(SRC / ('T_MS_Bog%sColor.png' % v)).convert('RGB'), dtype=np.float32) / 255.0
        lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        lum = 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
        # The cavity tint the ground applies (MudCavityTint 0.15): the colour's mean after it.
        lum_cav = lum * (1.0 - 0.15 * (1.0 - ao))
        report['variants'][v] = dict(
            height_range_cm=[lo, hi], size=size, px_cm=round(px_cm, 4),
            ao=dict(mean=round(float(ao.mean()), 3), p1_5_50_95=pct(ao, [1, 5, 50, 95]), under_0_7=round(float((ao < 0.7).mean()), 4)),
            rough_bake=dict(min_max=[round(float(r8.min()), 3), round(float(r8.max()), 3)], p5_50_95=pct(r8, [5, 50, 95])),
            rough_pbr=dict(min_max=[round(float(rp.min()), 3), round(float(rp.max()), 3)], p5_50_95=pct(rp, [5, 50, 95]),
                           roundtrip_max_err=round(float(np.abs(0.14 + (rp - 0.45) * 0.77 / 0.5 - r8).max()), 4)),
            colour_linear_mean=[round(float(x), 4) for x in lin.reshape(-1, 3).mean(0)],
            luminance_mean=round(float(lum.mean()), 4), luminance_p5_95=pct(lum, [5, 95]),
            luminance_mean_with_cavity=round(float(lum_cav.mean()), 4),
            parallax_height=dict(max_slope_per_texel_pct_before=round(100.0 * slope_before, 2), max_slope_per_texel_pct_after=round(100.0 * slope_after, 2),
                                 cap_pct=100.0 * SOFT_SLOPE, sigma_texels=SOFT_SIGMA,
                                 mean_abs_change=round(float(np.abs(hs - h01).mean()), 4), p99_abs_change=round(float(np.percentile(np.abs(hs - h01), 99)), 4)),
            files=dict(ao='Art/Export/MudStyleUE/T_MS_Bog%sAO.png' % v, orh='Art/Export/MudStyleUE/T_MS_Bog%sORH.png' % v),
            seconds=round(time.time() - t0, 1))
        r = report['variants'][v]
        print('%s: AO mean %.3f p5 %.3f; rough %s -> %s (p5/50/95); luminance %.4f (with cavity %.4f); parallax height max slope %.2f -> %.2f %% of the range per texel (mean change %.4f); %.1f s' % (
            v, r['ao']['mean'], r['ao']['p1_5_50_95'][1], r['rough_bake']['p5_50_95'], r['rough_pbr']['p5_50_95'], r['luminance_mean'],
            r['luminance_mean_with_cavity'], r['parallax_height']['max_slope_per_texel_pct_before'], r['parallax_height']['max_slope_per_texel_pct_after'],
            r['parallax_height']['mean_abs_change'], r['seconds']))
    (SRC / 'bog-orh.json').write_text(json.dumps(report, indent=2))
    print('MUD_ORH_BAKE_OK')


if __name__ == '__main__':
    main()
