"""bake_snow_detail.py - the snow-clump detail height map T_GT_SnowDetail for M_GT_Snow (living mud LM4b items 4-6,
docs/LIVING_MUD_PLAN.md LM4b; docs/LIVE_SNOW_DRIVE.md).

Generated from procedural noise only: nothing is downloaded or painted. numpy (and the standard library's zlib for the PNG),
so it runs in any Python with numpy (the system one, or Blender's: blender -b --factory-startup --python this file):
  python Art/tools/bake_snow_detail.py

A tileable 1024 x 1024 map of a 100 cm square (10.24 px a cm), 16 bits a channel, linear (not colour):
- R, crumbs: 1-4 cm clumps (radius 0.5-2.0 cm, more small than large), 0.5 x their radius high;
- G, clods: 6-15 cm clumps (radius 3-7.5 cm), 0.4 x their radius high;
- B, the two together by their heights in cm (crumbs 0.8, clods 2.0: M_GT_Snow's SnowDetailCm defaults), for the parallax's
  one-tap height.
Each layer is a soft clumped field: lumpy, rounded blobs ((1 - d^2)^1.5, so a rounded top and a foot that meets the floor at
no slope), each outline wobbled by its own 2nd-4th harmonics, placed where a periodic low-frequency density field puts them
(so they clump and leave gaps), joined by a smooth maximum (k log sum exp) so where two meet there is a soft crevice, never
a crisp cell edge, plus a faint periodic grain. Every field is periodic over the tile (the placement wraps; the noise is
FFT-filtered white noise), so the map tiles without a seam.

Writes Art/Textures/Snow/T_GT_SnowDetail.png (16-bit RGB), T_GT_SnowDetail_preview.png (8-bit: the three channels, a lit
view of each layer and of the two together, and the combined map tiled 2 x 2) and T_GT_SnowDetail.json (the numbers and
the measures below). Measures, printed with the prefix SNOWDETAIL: each layer's coverage (the share of the tile a blob
stands on), its height range in cm, the blobs placed, and the seam ratio (the mean step across the tile's wrapped edges over
the mean step between neighbouring texels inside: about 1 for a map that tiles).
"""
import json
import math
import os
import struct
import sys
import time
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, 'Art', 'Textures', 'Snow')
NAME = 'T_GT_SnowDetail'
SIZE = 1024
TILE_CM = 100.0
PX_CM = SIZE / TILE_CM
SEED = 0x5E0D4B

# The layers: radius range (cm), the radius law's power (r = min + (max - min) u^power: more small than large), height per
# radius, coverage asked (the Poisson rate is set from it), the smooth maximum's softness (cm), the density field's
# wavelength (cm) and its contrast (0 uniform, 1 strongly clumped), and the faint grain's sd (cm) and wavelength (cm).
LAYERS = {
    'crumbs': dict(r_min=0.5, r_max=2.0, power=1.5, h_per_r=0.5, coverage=0.93, soft_cm=0.12, density_cm=7.0, contrast=1.1,
                   grain_cm=0.025, grain_wave_cm=0.6),
    'clods': dict(r_min=3.0, r_max=7.5, power=1.3, h_per_r=0.4, coverage=0.88, soft_cm=0.35, density_cm=30.0, contrast=0.9,
                  grain_cm=0.06, grain_wave_cm=2.0),
}
# M_GT_Snow's SnowDetailCm defaults (the layers' height in cm at a channel value of 1): the B channel's weights.
COMBINE_CM = (0.8, 2.0)


def say(msg):
    print('SNOWDETAIL ' + msg)
    sys.stdout.flush()


def periodic_noise(rng, wave_cm):
    """Tileable smooth noise, zero mean, unit sd: white noise low-passed in the Fourier domain (a Gaussian at wave_cm)."""
    white = rng.standard_normal((SIZE, SIZE))
    k = np.fft.fftfreq(SIZE) * SIZE / TILE_CM          # cycles per cm
    kk = k[:, None] ** 2 + k[None, :] ** 2
    sigma = 1.0 / max(wave_cm, 1e-3)
    field = np.real(np.fft.ifft2(np.fft.fft2(white) * np.exp(-0.5 * kk / (sigma * sigma))))
    field -= field.mean()
    sd = field.std()
    return field / sd if sd > 0 else field


def blob_layer(rng, spec):
    """The layer's height in cm: lumpy rounded blobs joined by a smooth maximum over the floor (0), placed by a density field."""
    r_min, r_max, power = spec['r_min'], spec['r_max'], spec['power']
    # The mean blob's area (a lobed outline's area is about its mean radius's circle) and the rate for the coverage asked.
    us = rng.random(20000)
    radii = r_min + (r_max - r_min) * us ** power
    mean_area = float(np.mean(math.pi * radii ** 2))
    rate = -math.log(1.0 - spec['coverage']) / mean_area          # blobs per cm^2 on average
    count = int(round(rate * TILE_CM * TILE_CM))
    # The density field (periodic): the blobs are thinned by it, so they clump where it is high and gap where it is low.
    density = periodic_noise(rng, spec['density_cm'])
    weight = np.clip(1.0 + spec['contrast'] * density, 0.0, None)
    weight /= weight.max()
    k = spec['soft_cm']
    acc = np.ones((SIZE, SIZE), dtype=np.float64)                    # sum over blobs of exp(h / k) - 1, plus exp(0 / k) for the floor
    placed = 0
    tries = 0
    target = count
    yy_cache = {}
    while placed < target and tries < target * 20:
        tries += 1
        cx, cy = rng.random() * SIZE, rng.random() * SIZE
        if rng.random() > weight[int(cy) % SIZE, int(cx) % SIZE]:
            continue                                                   # thinned by the density: the blobs clump
        u = rng.random()
        r = r_min + (r_max - r_min) * u ** power                       # cm
        height = spec['h_per_r'] * r * (0.75 + 0.5 * rng.random())     # cm
        # The outline: the radius wobbled by its own 2nd, 3rd and 4th harmonics (a lumpy clump, not a disc), and a mild oval.
        amps = [0.22 * rng.random(), 0.12 * rng.random(), 0.08 * rng.random()]   # the 2nd: an oval up to 1.5:1
        phases = [2.0 * math.pi * rng.random() for _ in range(3)]
        reach = int(math.ceil(r * 1.3 * PX_CM)) + 1
        if reach not in yy_cache:
            off = np.arange(-reach, reach + 1)
            yy_cache[reach] = off
        off = yy_cache[reach]
        ix = (int(cx) + off) % SIZE
        iy = (int(cy) + off) % SIZE
        dx = (off[None, :] + int(cx) - cx) / PX_CM
        dy = (off[:, None] + int(cy) - cy) / PX_CM
        dist = np.sqrt(dx * dx + dy * dy)
        theta = np.arctan2(dy, dx)
        wobble = 1.0 + amps[0] * np.cos(2.0 * theta + phases[0]) + amps[1] * np.cos(3.0 * theta + phases[1]) + amps[2] * np.cos(4.0 * theta + phases[2])
        d = dist / (r * wobble)
        inside = d < 1.0
        if not inside.any():
            continue
        h = np.where(inside, height * np.clip(1.0 - d * d, 0.0, 1.0) ** 1.5, 0.0)
        acc[np.ix_(iy, ix)] += np.expm1(h / k)
        placed += 1
    layer = k * np.log(acc)
    grain = periodic_noise(rng, spec['grain_wave_cm']) * spec['grain_cm']
    layer = layer + grain
    covered = float(np.mean(layer > 0.1 * float(np.percentile(layer, 99.5))))
    return layer, dict(blobs=placed, rate_per_m2=round(rate * 1e4, 1), mean_area_cm2=round(mean_area, 2), coverage_asked=spec['coverage'],
                       covered_share=round(covered, 3), height_cm_p50=round(float(np.percentile(layer, 50)), 3),
                       height_cm_p995=round(float(np.percentile(layer, 99.5)), 3), height_cm_max=round(float(layer.max()), 3))


def to_unit(layer):
    lo = float(np.percentile(layer, 0.2))
    hi = float(np.percentile(layer, 99.8))
    return np.clip((layer - lo) / max(hi - lo, 1e-6), 0.0, 1.0), lo, hi


def seam_ratio(img):
    inner = 0.5 * (np.mean(np.abs(np.diff(img, axis=0))) + np.mean(np.abs(np.diff(img, axis=1))))
    edge = 0.5 * (np.mean(np.abs(img[0, :] - img[-1, :])) + np.mean(np.abs(img[:, 0] - img[:, -1])))
    return float(edge / max(inner, 1e-12))


def png_chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path, rgb, bits):
    h, w, _ = rgb.shape
    dtype = '>u2' if bits == 16 else 'u1'
    rows = rgb.astype(dtype)
    raw = b''.join(b'\x00' + rows[y].tobytes() for y in range(h))
    data = b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, bits, 2, 0, 0, 0))
    data += png_chunk(b'IDAT', zlib.compress(raw, 9)) + png_chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(data)


def shade(height_cm, px_cm):
    """A lit view of a height field (cm): a low sun from the upper left, the light's cosine on the field's normal."""
    gy, gx = np.gradient(height_cm, 1.0 / px_cm)
    n = np.stack([-gx, -gy, np.ones_like(gx)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    sun = np.array([-0.55, -0.45, 0.70])
    sun /= np.linalg.norm(sun)
    return np.clip(0.15 + 0.85 * (n @ sun), 0.0, 1.0)


def down(img, factor):
    h, w = img.shape
    return img.reshape(h // factor, factor, w // factor, factor).mean(axis=(1, 3))


def main():
    start = time.time()
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(SEED)
    layers = {}
    report = dict(size=SIZE, tile_cm=TILE_CM, px_per_cm=PX_CM, seed=SEED, layers={}, combine_cm=COMBINE_CM)
    for name, spec in LAYERS.items():
        layer, stats = blob_layer(rng, spec)
        layers[name] = layer
        report['layers'][name] = dict(spec, **stats)
        say('%s: %d blobs (%.1f a m^2), radius %.1f-%.1f cm u^%.1f, %.2f x radius high; covered %.3f (asked %.2f); height cm p50 %.3f, p99.5 %.3f, max %.3f'
            % (name, stats['blobs'], stats['rate_per_m2'], spec['r_min'], spec['r_max'], spec['power'], spec['h_per_r'], stats['covered_share'],
               spec['coverage'], stats['height_cm_p50'], stats['height_cm_p995'], stats['height_cm_max']))
    r, r_lo, r_hi = to_unit(layers['crumbs'])
    g, g_lo, g_hi = to_unit(layers['clods'])
    combined_cm = COMBINE_CM[0] * r + COMBINE_CM[1] * g
    b, b_lo, b_hi = to_unit(combined_cm)
    report['channels'] = dict(R=dict(layer='crumbs', cm_at_0=round(r_lo, 4), cm_at_1=round(r_hi, 4)), G=dict(layer='clods', cm_at_0=round(g_lo, 4), cm_at_1=round(g_hi, 4)),
                              B=dict(layer='crumbs x %.1f cm + clods x %.1f cm' % COMBINE_CM, at_0=round(b_lo, 4), at_1=round(b_hi, 4)))
    seams = dict(R=round(seam_ratio(r), 3), G=round(seam_ratio(g), 3), B=round(seam_ratio(b), 3))
    report['seam_ratio'] = seams
    for ch, img in (('R', r), ('G', g), ('B', b)):
        report.setdefault('channel_stats', {})[ch] = dict(mean=round(float(img.mean()), 4), sd=round(float(img.std()), 4),
                                                         share_under_0_1=round(float(np.mean(img < 0.1)), 3), share_over_0_6=round(float(np.mean(img > 0.6)), 3))
    say('seam ratio R %.3f, G %.3f, B %.3f (about 1: the map tiles)' % (seams['R'], seams['G'], seams['B']))
    for ch in ('R', 'G', 'B'):
        st = report['channel_stats'][ch]
        say('%s: mean %.3f, sd %.3f, %.1f %% under 0.1 (the floor and the crevices), %.1f %% over 0.6 (the tops)' % (ch, st['mean'], st['sd'], 100 * st['share_under_0_1'], 100 * st['share_over_0_6']))
    rgb16 = np.stack([r, g, b], axis=-1)
    rgb16 = np.round(rgb16 * 65535.0).astype(np.uint16)
    path = os.path.join(OUT, NAME + '.png')
    write_png(path, rgb16, 16)
    # The preview: the top row the three channels (grey), the bottom row a lit view of the crumbs, of the clods, and of the
    # two together; a third row the combined lit view tiled 2 x 2 at half scale (the seams would show as lines).
    tile = 256
    f = SIZE // tile
    lit_r = shade(COMBINE_CM[0] * r, PX_CM)
    lit_g = shade(COMBINE_CM[1] * g, PX_CM)
    lit_b = shade(combined_cm, PX_CM)
    row1 = np.concatenate([down(r, f), down(g, f), down(b, f)], axis=1)
    row2 = np.concatenate([down(lit_r, f), down(lit_g, f), down(lit_b, f)], axis=1)
    half = down(lit_b, 2 * f)
    tiled = np.tile(half, (2, 2))
    row3 = np.concatenate([tiled, np.full((tile, 3 * tile - tiled.shape[1]), 0.5)], axis=1)
    preview = np.concatenate([row1, row2, row3], axis=0)
    preview8 = np.round(np.clip(preview, 0.0, 1.0) * 255.0).astype(np.uint8)
    preview_path = os.path.join(OUT, NAME + '_preview.png')
    write_png(preview_path, np.stack([preview8] * 3, axis=-1), 8)
    report.update(file=os.path.relpath(path, ROOT).replace('\\', '/'), preview=os.path.relpath(preview_path, ROOT).replace('\\', '/'),
                  bytes=os.path.getsize(path), seconds=round(time.time() - start, 1),
                  how='lumpy rounded blobs ((1 - d^2)^1.5, outlines wobbled by 2nd-4th harmonics) thinned by a periodic density field, joined by a smooth maximum, plus a faint periodic grain; periodic over the tile')
    with open(os.path.join(OUT, NAME + '.json'), 'w') as fjson:
        json.dump(report, fjson, indent=2)
    say('wrote %s (%d x %d, 16-bit RGB, %.2f MB), %s; %.1f s' % (report['file'], SIZE, SIZE, report['bytes'] / 1048576.0, report['preview'], report['seconds']))
    say('OK')


if __name__ == '__main__':
    main()
