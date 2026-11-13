"""Benmore integration B1c (docs/BENMORE_INTEGRATION_PLAN.md): the spray's two gates from Art/benmore_b1b.ps1's pictures (each paused frame
taken again without the car's Niagara components, <name>_NoSprites).
- Visibility (<stage>_Gravel_Chase): the sprite pixels, where the picture and its NoSprites differ by more than 8 of 255 in the
  difference's luminance (the method B1b's 83,054 was counted by). Asked: at least 1.5 x 83,054.
- Dust in shadow (<stage>_Gravel_Close, WHEEL_SPRAY_PLAN P2c's method, Art/sample_spray_pbr.py dust_shadow, the NoSprites difference as
  the mask; no custom-depth grit mask here, so the grit's chips are in it): a sprite pixel is in shadow where the frame without
  sprites is under 0.4 x its sunlit ground (the 75th percentile of the lower half). Asked: the median final-image linear luminance of
  the sprites in shadow at least 0.5 x that of those in sun. The same for the floor sweep's pictures (<name>_Floor<v>).
python Art/sample_benmore_spray.py [stage]   -> Art/Export/Benmore<stage>/gates.json"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
STAGE = sys.argv[1] if len(sys.argv) > 1 else 'B1c'
OUT = ROOT / ('Art/Export/Benmore' + STAGE)
B1B_SPRITE_PIXELS = 83054


def lum(path):
    px = np.asarray(Image.open(path).convert('RGB'), dtype=np.float64) / 255.
    lin = np.where(px <= .04045, px / 12.92, ((px + .055) / 1.055) ** 2.4)
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def sprite_pixels(name):
    d = ImageChops.difference(Image.open(OUT / (name + '.png')).convert('RGB'), Image.open(OUT / (name + '_NoSprites.png')).convert('RGB'))
    return int((np.asarray(d.convert('L')) > 8).sum())


def dust_shadow(picture, without):
    a, b = lum(picture), lum(without)
    dust = np.abs(a - b) > .01
    sunlit = float(np.percentile(b[b.shape[0] // 2:], 75))
    shadow = b < .4 * sunlit
    ds, dn = a[dust & shadow], a[dust & ~shadow]
    out = dict(sprite_pixels=int(dust.sum()), in_shadow=int(ds.size), in_sun=int(dn.size), sunlit_ground_p75=round(sunlit, 4))
    if ds.size and dn.size:
        ms, mn = float(np.median(ds)), float(np.median(dn))
        out.update(shadow_median=round(ms, 4), sun_median=round(mn, 4), ratio=round(ms / max(mn, 1e-6), 3), **{'pass': bool(ms >= .5 * mn)})
    else:
        out['pass'] = False
    return out


gates = {}
chase = STAGE + '_Gravel_Chase'
if (OUT / (chase + '_NoSprites.png')).exists():
    n = sprite_pixels(chase)
    gates['visibility'] = dict(picture=chase, sprite_pixels=n, b1b=B1B_SPRITE_PIXELS, ratio=round(n / B1B_SPRITE_PIXELS, 3), asked='at least 1.5',
                               **{'pass': n >= 1.5 * B1B_SPRITE_PIXELS})
close = STAGE + '_Gravel_Close'
if (OUT / (close + '_NoSprites.png')).exists():
    gates['dust_in_shadow'] = dict(picture=close, asked='at least 0.5', **dust_shadow(OUT / (close + '.png'), OUT / (close + '_NoSprites.png')))
    gates['dust_in_shadow_sweep'] = {p.stem.split('_Floor')[1]: dust_shadow(p, OUT / (close + '_NoSprites.png'))
                                     for p in sorted(OUT.glob(close + '_Floor*.png'))}
(OUT / 'gates.json').write_text(json.dumps(gates, indent=2))
print(json.dumps(gates, indent=1))
