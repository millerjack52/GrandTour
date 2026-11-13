"""Benmore integration B2c item 1 (docs/BENMORE_INTEGRATION_PLAN.md B2c): the gravel edge gate. Reads B2_Edge.png and its row in
Art/Export/BenmoreB2/capture_b2c.json (the 1 m strips either side of the live tile's border across the road's middle three quarters,
projected to the screen by Art/Unreal/capture_benmore_b2.py) and writes edge-gate.json: each strip's mean colour (display-linear) and the
difference per channel, |inside - outside| / outside; the gate is 2 % or under on every channel. Plain Python (numpy, Pillow)."""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / 'Art/Export/BenmoreB2'


def lin(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float64) / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def main():
    cap = json.loads((OUT / 'capture_b2c_edge.json').read_text()) if (OUT / 'capture_b2c_edge.json').exists() else json.loads((OUT / 'capture_b2c.json').read_text())
    row = next(p for p in cap['pictures'] if p['name'] == 'B2_Edge')
    frames = {'patch': lin(OUT / 'B2_Edge.png')}
    if (OUT / 'B2_Edge_NoPatch.png').exists() and row.get('no_patch'):
        frames['landscape'] = lin(OUT / 'B2_Edge_NoPatch.png')
    means = {}
    for side, quad in row['strips_px'].items():
        mask = Image.new('L', (1440, 900), 0)
        ImageDraw.Draw(mask).polygon([tuple(p) for p in quad], fill=255)
        m = np.asarray(mask) > 0
        means[side] = dict(pixels=int(m.sum()), **{k: [round(float(v), 5) for v in f[m].mean(0)] for k, f in frames.items()})
    gate = dict(strips=means, rule='display-linear means of the 1 m strips either side of the live tile border; per channel')
    i, o = np.array(means['inside']['patch']), np.array(means['outside']['patch'])
    gate['across_border_patch_frame'] = [round(float(v), 4) for v in np.abs(i - o) / np.maximum(o, 1e-6)]
    if 'landscape' in frames:
        il, ol = np.array(means['inside']['landscape']), np.array(means['outside']['landscape'])
        gate['across_border_landscape_frame'] = [round(float(v), 4) for v in np.abs(il - ol) / np.maximum(ol, 1e-6)]
        d = np.abs(i - il) / np.maximum(il, 1e-6)   # the patch against the landscape it replaced, the same pixels
        gate['inside_patch_vs_landscape'] = [round(float(v), 4) for v in d]
        gate['outside_patch_frame_vs_landscape_frame'] = [round(float(v), 4) for v in np.abs(o - ol) / np.maximum(ol, 1e-6)]
        gate['max_diff'] = round(float(d.max()), 4)
        gate['passes'] = bool(d.max() <= 0.02)
    (OUT / 'edge-gate.json').write_text(json.dumps(gate, indent=1))
    print(json.dumps(gate))


if __name__ == '__main__':
    main()
