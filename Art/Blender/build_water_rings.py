"""Mud and water MW1 item 3d (docs/MUD_WATER_SURFACE_PLAN.md): the painterly ring atlas for NS_GT_WaterRings.

Headless:  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --python Art/Blender/build_water_rings.py
Writes Art/Export/MudWater/T_GT_WaterRings.png (1024 x 1024, RGBA, linear) and its manifest: 2 x 2 cells, one soft painted ring
in each, none alike. Each ring is laid as soft elongated dabs along a wobbling circle (the radius 0.36-0.42 of the cell, wandering
+-5 % with two low harmonics), the dabs' width, strength and spacing jittered, a few left out (the ring breaks), so no ring is a
clean even line. R is the shade: over 0.5 the light crest (the sky caught on the ring's outer slope), under 0.5 the dark trough
just inside it; A is the coverage. Cells 1 and 3 carry a fainter second ring inside (the follow-on ripple). No downloads, numpy only.
"""
import json
import math
import struct
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Export/MudWater'
SIZE = 1024
CELL = SIZE // 2
SEED = 4127


def write_png(path, arr):
    """(h, w, 4) floats 0..1, row 0 = the top."""
    a = np.clip(arr, 0, 1)
    h, w = a.shape[:2]
    data = (a * 255 + .5).astype(np.uint8)
    raw = np.hstack([np.zeros((h, 1), np.uint8), data.reshape(h, -1)]).tobytes()

    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xFFFFFFFF)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def ring(rng, inner):
    """One cell: (shade, coverage), CELL x CELL, the ring centred."""
    y, x = (np.mgrid[0:CELL, 0:CELL] + 0.5) / CELL - 0.5
    shade = np.zeros((CELL, CELL))
    cover = np.zeros((CELL, CELL))
    rings = [(rng.uniform(0.36, 0.42), 1.0, rng.uniform(0.022, 0.03))]
    if inner:
        rings.append((rings[0][0] * rng.uniform(0.55, 0.68), rng.uniform(0.35, 0.55), rings[0][2] * 0.7))
    for radius, strength, width in rings:
        # The wobble: two low harmonics of random phase, +-5 % of the radius at most together.
        h2, h3 = rng.uniform(0, 2 * math.pi, 2)
        a2, a3 = rng.uniform(0.01, 0.03), rng.uniform(0.005, 0.02)
        n = int(rng.integers(34, 46))
        angles = np.sort(rng.uniform(0, 2 * math.pi, n) + np.linspace(0, 2 * math.pi, n, endpoint=False)) % (2 * math.pi)
        gaps = rng.random(n) < 0.12          # the ring breaks: about one dab in eight left out
        for k, t in enumerate(angles):
            if gaps[k]:
                continue
            r = radius * (1 + a2 * math.sin(2 * t + h2) + a3 * math.sin(3 * t + h3))
            cx, cy = r * math.cos(t), r * math.sin(t)
            along = np.array([-math.sin(t), math.cos(t)])   # the dab's long axis: along the ring
            across = np.array([math.cos(t), math.sin(t)])   # outward
            ln = rng.uniform(0.07, 0.12)
            wd = width * rng.uniform(0.7, 1.35)
            s = strength * rng.uniform(0.6, 1.0)
            du = (x - cx) * along[0] + (y - cy) * along[1]
            dv = (x - cx) * across[0] + (y - cy) * across[1]
            env = np.exp(-(du / ln) ** 2 * 2.0)
            crest = np.exp(-((dv - 0.35 * wd) / (0.55 * wd)) ** 2) * env * s     # the light crest, outward
            trough = np.exp(-((dv + 0.9 * wd) / (0.8 * wd)) ** 2) * env * s     # the dark trough, inside it
            shade += crest - 0.55 * trough
            cover = np.maximum(cover, np.maximum(crest, 0.8 * trough))
    # A faint grain on the coverage (no clean airbrush).
    grain = rng.random((CELL // 8, CELL // 8))
    grain = np.kron(grain, np.ones((8, 8)))
    cover *= 0.85 + 0.3 * grain
    return np.clip(0.5 + 0.5 * shade, 0, 1), np.clip(cover, 0, 1)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    atlas = np.zeros((SIZE, SIZE, 4))
    rows = []
    for k in range(4):
        cx, cy = k % 2, k // 2
        sh, cv = ring(rng, inner=k in (1, 3))
        cell = atlas[cy * CELL:(cy + 1) * CELL, cx * CELL:(cx + 1) * CELL]
        cell[..., 0] = sh
        cell[..., 1] = sh
        cell[..., 2] = sh
        cell[..., 3] = cv
        rows.append(dict(cell=k, column=cx, row=cy, inner_ring=k in (1, 3), coverage_mean=round(float(cv.mean()), 4),
                         coverage_max=round(float(cv.max()), 3), shade_range=[round(float(sh.min()), 3), round(float(sh.max()), 3)]))
    write_png(OUT / 'T_GT_WaterRings.png', atlas)
    (OUT / 'water-rings-manifest.json').write_text(json.dumps(dict(texture='T_GT_WaterRings.png', size=SIZE, cells='2 x 2 (row 0 at the top)',
                                                                   channels='R=G=B shade (0.5 neutral, over: crest, under: trough), A coverage',
                                                                   seed=SEED, cells_info=rows), indent=2))
    print('WATER_RINGS_ATLAS_OK', rows)


main()
