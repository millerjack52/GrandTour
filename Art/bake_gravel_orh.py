"""Deformable gravel DG1 item 1 (docs/DEFORMABLE_GRAVEL_PLAN.md DG1): the gravel sets' packed ORH maps.

A gravel copy of Art/bake_mud_orh.py's method (MRP item 2 and follow-up 3) for the 2 m tiles of 2048 px that
Art/Blender/bake_gravel_dg1.py bakes into Art/Export/GravelDG1 (sets Loose and Packed), with DG1 item 1's "Decisions after
the phase A bakes":
- R: horizon-based ambient occlusion from the sharp height (T_GV_<Set>Height.png, 16-bit, 0-1 in units both sets
  share; since phase A3 the per-stone parallax height of bake_gravel_dg1.parallax_heights) at the set's parallax depth
  (PARALLAX_DEPTH_CM: the 0-1 height is DEPTH cm, Loose 0.8 (phase A2: 1.0), Packed 0.5): per pixel, 16
  directions, each marched to 6 cm (AO_RADIUS_CM, as the mud's) over integer steps (wrapped: the tiles are tileable); a
  direction's occlusion is the largest sin of the horizon's elevation, attenuated by (1 - (r / R)^2); the AO is one minus
  the mean over the directions. The mud's steps reach 41 px of 0.146 cm; the gravel's texel is 0.0977 cm, so 61 px.
- G: the roughness (the study's is one constant, 0.9, so the bake adds structure): 0.9 - 0.16 x smoothstep(0.45, 0.9, h)
  on the sharp height h (stone tops near 0.74, the matrix 0.9); Packed takes 0.05 off everything (tyre-polished), with a
  floor of 0.55. T_GV_<Set>Rough.png holds the same values.
- B: the parallax height with soft rims (MRP follow-up 3's construction: the slope capped by the mean of the two cone
  envelopes, then a Gaussian), scaled for gravel: SOFT_SLOPE 6 % of the range per texel and a SOFT_SIGMA 1.0 texel
  Gaussian (the mud's 1.5 % / 1.5 texels turned 7.7 cm stones into domes). Gates (phase A3, accepted 2026-10-09): the
  stone-top median is PER STONE: each fully present Loose stone's tilted top (where it is the surface) gives its mean B,
  each stone counted once, and the median over the stones is >= 0.6; the maximum B is >= 0.97. (The texel-weighted median,
  kept as median_b for reference, leans to the low stones, whose tops are larger: 0.588 at A3. Standalone, without the
  stone ids, the gate falls back to the texel median of sharp h > 0.9.) The AO stays from the sharp height.
The functions are plain numpy, so the Blender bake calls them in-process. Standalone (system Python, numpy + Pillow) it
repacks from the Height PNGs already in Art/Export/GravelDG1 and refreshes manifest.json's orh blocks:
  python Art/bake_gravel_orh.py
"""
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Art/Export/GravelDG1'
SETS = ['Loose', 'Packed']
AO_RADIUS_CM = 6.0
DIRECTIONS = 16
STEPS_PX = [1, 2, 3, 5, 7, 10, 14, 19, 25, 32, 41, 51, 61]   # integer radii up to 6 cm (61 px of 0.0977 cm)
ROUGH_BAND = (0.55, 0.90)
PARALLAX_DEPTH_CM = {'Loose': 0.8, 'Packed': 0.5}   # phase A3: Loose 0.8 (A2 1.0)
SOFT_SLOPE = 0.06
SOFT_SIGMA = 1.0
TOP_H = 0.9                         # standalone fallback for a stone top: sharp height above 0.9
GATES = dict(top_median_b=0.6, top_max_b=0.97)    # phase A3 (A2: 0.85 / 0.97); the median is per stone (pack)


def horizon_ao(h_cm, px_cm):
    """bake_mud_orh.horizon_ao, with the gravel's steps."""
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


def soft_rims(h):
    """bake_mud_orh.soft_rims, unchanged (MRP follow-up 3)."""
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


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def roughness(h01, set_name):
    """DG1 item 1 decision: 0.9 - 0.16 x smoothstep(0.45, 0.9, h) on the sharp height; Packed 0.05 lower, floor 0.55."""
    r = 0.9 - 0.16 * smoothstep(0.45, 0.9, h01)
    if set_name == 'Packed':
        r = r - 0.05
    return np.clip(r, ROUGH_BAND[0], ROUGH_BAND[1]).astype(np.float32)


def pct(a, ps):
    return [round(float(x), 3) for x in np.percentile(a, ps)]


def pack(h01, set_name, px_cm, top_mask=None, stone_id=None, top_definition=None):
    """h01: the sharp 0-1 height (float; row order irrelevant: everything wraps or is per texel).
    top_mask: the stone-top texels (default: h > TOP_H); stone_id: per texel the broad stone forming the surface (-1 none),
    for the per-stone maximum B. Returns (ao, g, b) as 0-1 float arrays and the stats for the manifest."""
    depth = PARALLAX_DEPTH_CM[set_name]
    h01 = h01.astype(np.float32)
    ao = horizon_ao((h01 * depth).astype(np.float32), px_cm)
    g = roughness(h01, set_name)
    b = soft_rims(h01)
    top = (h01 > TOP_H) if top_mask is None else top_mask
    b8 = np.round(b * 255.0) / 255.0                # as ORH.B stores it
    tops = dict(definition=top_definition or 'sharp h > %.2f' % TOP_H, share=round(float(top.mean()), 4))
    if top.any():
        tops.update(median_b=round(float(np.median(b8[top])), 3), p5_b=round(float(np.percentile(b8[top], 5)), 3))
    tops['max_b'] = round(float(b8.max()), 3)
    if stone_id is not None:
        sel = stone_id >= 0
        per = np.full(int(stone_id.max()) + 1, -1.0)
        np.maximum.at(per, stone_id[sel], b8[sel])
        per = per[per >= 0]
        tops['per_stone_max_b'] = dict(stones=int(per.size), p5_25_50_75_95=pct(per, [5, 25, 50, 75, 95]))
        ft = sel & top
        cnt = np.bincount(stone_id[ft], minlength=int(stone_id.max()) + 1)
        tot = np.bincount(stone_id[ft], weights=b8[ft], minlength=int(stone_id.max()) + 1)
        means = tot[cnt > 0] / cnt[cnt > 0]
        tops['per_stone_top_mean_b'] = dict(note='each stone weighted once (the gate median weights texels)', stones=int(means.size),
                                            p5_25_50_75_95=pct(means, [5, 25, 50, 75, 95]))
    if set_name == 'Loose':
        # The gate's median is per stone (each stone's top mean B, each stone once) when the stone ids are given.
        per_stone = 'per_stone_top_mean_b' in tops
        med = tops['per_stone_top_mean_b']['p5_25_50_75_95'][2] if per_stone else tops.get('median_b', 0)
        tops['gates'] = dict(median_measure='per stone: median over the stones of each top mean B' if per_stone else 'texel median (no stone ids)',
                             stone_top_median_b=med, median_b_min=GATES['top_median_b'], max_b_min=GATES['top_max_b'],
                             median_pass=bool(med >= GATES['top_median_b']), max_pass=bool(tops['max_b'] >= GATES['top_max_b']))
    stats = dict(
        parallax_depth_cm=depth,
        ao=dict(radius_cm=AO_RADIUS_CM, directions=DIRECTIONS, steps_px=STEPS_PX, height_cm='sharp h x %.1f' % depth,
                mean=round(float(ao.mean()), 3), p1_5_50_95=pct(ao, [1, 5, 50, 95]), under_0_7=round(float((ao < 0.7).mean()), 4)),
        rough_orh_g=dict(formula='0.9 - 0.16 x smoothstep(0.45, 0.9, h)' + (' - 0.05, floor 0.55' if set_name == 'Packed' else ''),
                         min_max=[round(float(g.min()), 3), round(float(g.max()), 3)], p5_50_95=pct(g, [5, 50, 95])),
        parallax_height=dict(cap_pct_of_range_per_texel=100.0 * SOFT_SLOPE, sigma_texels=SOFT_SIGMA,
                             max_slope_per_texel_pct_before=round(100.0 * max_slope(h01), 2),
                             max_slope_per_texel_pct_after=round(100.0 * max_slope(b), 2),
                             texels_for_a_full_range_rise=int(math.ceil(1.0 / SOFT_SLOPE)),
                             cm_for_a_full_range_rise=round(px_cm / SOFT_SLOPE, 2),
                             mean_abs_change=round(float(np.abs(b - h01).mean()), 4),
                             p99_abs_change=round(float(np.percentile(np.abs(b - h01), 99)), 4),
                             mean_b=round(float(b8.mean()), 4), stone_tops=tops))
    return ao, g, b, stats


def main():
    from PIL import Image
    manifest_path = OUT / 'manifest.json'
    man = json.loads(manifest_path.read_text())
    px_cm = man['texel_cm']
    q = lambda x: (np.clip(x, 0, 1) * 255.0 + 0.5).astype(np.uint8)
    for s in SETS:
        h = np.asarray(Image.open(OUT / ('T_GV_%sHeight.png' % s)), dtype=np.float32) / 65535.0
        h = h[..., 0] if h.ndim == 3 else h
        ao, g, b, stats = pack(h, s, px_cm)
        Image.fromarray(q(g), 'L').save(OUT / ('T_GV_%sRough.png' % s))
        Image.fromarray(q(ao), 'L').save(OUT / ('T_GV_%sAO.png' % s))
        Image.fromarray(np.stack([q(ao), q(g), q(b)], -1), 'RGB').save(OUT / ('T_GV_%sORH.png' % s))
        man['sets'][s]['orh'] = stats
        print('%s: AO mean %.3f; G %s; B mean %.3f, stone tops %s' % (
            s, stats['ao']['mean'], stats['rough_orh_g']['p5_50_95'], stats['parallax_height']['mean_b'],
            stats['parallax_height']['stone_tops']))
    man['track_blend']['mean_hL'] = man['sets']['Loose']['orh']['parallax_height']['mean_b']
    manifest_path.write_text(json.dumps(man, indent=2))
    print('GRAVEL_ORH_OK')


if __name__ == '__main__':
    main()
