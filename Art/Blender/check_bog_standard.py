"""LM5b phase A (docs/LIVING_MUD_PLAN.md "LM5b: four churned-bog variants", docs/MUD_WET_STUDY.md): does the Standard
variant reproduce phase A2? Compares, pixel for pixel, as Blender reads the files (raw, 0-1):
- the fields: 05_variants/Standard/fields/F_{Paint,Shape,Zones}.png against 04_wet/fields/ (and their bytes);
- the bakes: T_MS_BogStandard{Color,Normal,Rough,Height}.png against A2's T_MS_Churn* (Art/Export/MudStyleUE);
- the renders: 05_variants/Standard_A2check (Standard painted on the ruts only, as A2 was:
  build_mud_wet_study.py -- variant=Standard coverage=ruts out=05_variants/Standard_A2check) against 04_wet's
  ChurnClose, Tile3x3, TileClose, Driver_ChurnMask and Driver_FarGlossFade (the check's Driver.png carries the same fade).

Run headless after both studies and the Standard export:
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --factory-startup --python-exit-code 1 \
      --python Art/Blender/check_bog_standard.py
Writes Art/Export/MudStyleUE/bog-standard-vs-a2.json: per pair the largest and mean absolute difference, in 8-bit
levels (x 255), and whether the bytes are identical.
"""
import bpy, json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S = ROOT / 'Art/Export/MudStyleStudy'
UE = ROOT / 'Art/Export/MudStyleUE'


def read(path):
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = 'Non-Color'
    a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
    im.pixels.foreach_get(a)
    out = a.reshape(im.size[1], im.size[0], 4)[..., :3].astype(np.float64)
    bpy.data.images.remove(im)
    return out


pairs = [('field ' + f, S / '05_variants/Standard/fields' / (f + '.png'), S / '04_wet/fields' / (f + '.png')) for f in ('F_Paint', 'F_Shape', 'F_Zones')]
pairs += [('bake ' + c, UE / ('T_MS_BogStandard%s.png' % c), UE / ('T_MS_Churn%s.png' % c)) for c in ('Color', 'Normal', 'Rough', 'Height')]
pairs += [('render ' + a, S / '05_variants/Standard_A2check' / a, S / '04_wet' / b) for a, b in
          [('ChurnClose.png', 'ChurnClose.png'), ('Tile3x3.png', 'Tile3x3.png'), ('TileClose.png', 'TileClose.png'),
           ('Driver_ChurnMask.png', 'Driver_ChurnMask.png'), ('Driver.png', 'Driver_FarGlossFade.png')]]
report = {}
for name, a, b in pairs:
    x, y = read(a), read(b)
    d = np.abs(x - y) * 255 if x.shape == y.shape else None
    report[name] = dict(new=str(a.relative_to(ROOT)).replace('\\', '/'), a2=str(b.relative_to(ROOT)).replace('\\', '/'),
                        bytes_identical=a.read_bytes() == b.read_bytes(),
                        max_abs_8bit=round(float(d.max()), 4) if d is not None else 'shape differs',
                        mean_abs_8bit=round(float(d.mean()), 6) if d is not None else None,
                        share_pixels_differing=round(float((d.max(-1) > 0).mean() * 100), 4) if d is not None else None)
    print('BOG_STANDARD_VS_A2 %-28s max %s  mean %s  differing %s %%  bytes identical %s' % (
        name, report[name]['max_abs_8bit'], report[name]['mean_abs_8bit'], report[name]['share_pixels_differing'],
        report[name]['bytes_identical']), flush=True)
(UE / 'bog-standard-vs-a2.json').write_text(json.dumps(report, indent=2))
print('BOG_STANDARD_CHECK_OK', flush=True)
