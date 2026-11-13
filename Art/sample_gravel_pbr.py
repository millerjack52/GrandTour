"""Deformable gravel DG1 item 6 (docs/DEFORMABLE_GRAVEL_PLAN.md): the PBR sampler rows from Art/Unreal/check_deformable_gravel.py's
buffer captures (HighResShot's dump of BaseColor, Roughness and MaterialAO, uncompressed EXR; linear, as MRP's calibration found:
Art/Export/MudVariants/pbr-rows.json encoding.verdict). PBR_Gravel_Dry and PBR_Gravel_Wet look down 50 deg from 2.2 m at the Loose
section's -Y rut and the loose ground beside it (the stones in the picture); the middle 60 % of the picture is read:
- dry: the base colour's linear luminance p5 / p50 / p95 inside 0.05-0.35 (dry stone), roughness p5 at least 0.5;
- wet (the weather's wetness 1): roughness p5 at least 0.4; the base colour's luminance against the dry (asked x0.75);
- stones (DG1b, PBR_Gravel_Stones, the ground hidden): the stones' median base-colour luminance within 25 % of the dry ground's p50,
  and no stone pixel under 0.08.
Writes Art/Export/DeformableGravel/pbr-rows.json. numpy (system Python), Art/sample_mud_pbr.py's EXR reader.
    python Art/sample_gravel_pbr.py
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sample_mud_pbr import read_exr   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'Art/Export/DeformableGravel'


def middle(a):
    h, w = a.shape
    return a[int(.2 * h):int(.8 * h), int(.2 * w):int(.8 * w)]


def pct(a, ps):
    return [round(float(x), 4) for x in np.percentile(a, ps)]


def channel(d, name):
    for key in (name + '.R', 'R', name):
        if key in d:
            return d[key]
    return d[sorted(d)[0]]


def capture(name):
    base = OUT / name
    colour = read_exr(str(base) + '_BaseColor.exr')
    rough = middle(channel(read_exr(str(base) + '_Roughness.exr'), 'Roughness'))
    ao = middle(channel(read_exr(str(base) + '_MaterialAO.exr'), 'MaterialAO'))
    r, g, b = (middle(colour[k]) for k in ('R', 'G', 'B'))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return dict(roughness_p5_50_95=pct(rough, [5, 50, 95]), luminance_p5_50_95=pct(lum, [5, 50, 95]), luminance_mean=round(float(lum.mean()), 4),
                ao_mean_p5=[round(float(ao.mean()), 4), round(float(np.percentile(ao, 5)), 4)], pixels=int(lum.size))


def stones(ground_p50):
    """DG1b: the loose stones alone (PBR_Gravel_Stones: the ground hidden): their pixels are where the roughness buffer is set (the
    stones' 0.75-0.85; the empty background reads 0), the whole picture. Pass: the median base-colour luminance within 25 % of the
    ground's p50 and no stone pixel under 0.08."""
    base = OUT / 'PBR_Gravel_Stones'
    colour = read_exr(str(base) + '_BaseColor.exr')
    rough = channel(read_exr(str(base) + '_Roughness.exr'), 'Roughness')
    lum = 0.2126 * colour['R'] + 0.7152 * colour['G'] + 0.0722 * colour['B']
    mask = rough > 0.5
    v = lum[mask]
    med = float(np.median(v)) if v.size else 0.0
    return dict(pixels=int(v.size), luminance_median=round(med, 4), luminance_min=round(float(v.min()) if v.size else 0.0, 4),
                luminance_p1_5_95=pct(v, [1, 5, 95]) if v.size else [], roughness_p5_50_95=pct(rough[mask], [5, 50, 95]) if v.size else [],
                ground_p50=ground_p50, ratio_to_ground=round(med / max(ground_p50, 1e-6), 3),
                passes=dict(median_within_25_pct=bool(v.size and abs(med / max(ground_p50, 1e-6) - 1.0) <= 0.25),
                            none_under_0_08=bool(v.size and float(v.min()) >= 0.08)))


def main():
    dry, wet = capture('PBR_Gravel_Dry'), capture('PBR_Gravel_Wet')
    rows = dict(
        dry=dict(dry, passes=dict(luminance_in_0_05_0_35=bool(dry['luminance_p5_50_95'][0] >= 0.05 and dry['luminance_p5_50_95'][2] <= 0.35),
                                  roughness_p5_at_least_0_5=bool(dry['roughness_p5_50_95'][0] >= 0.5))),
        wet=dict(wet, luminance_vs_dry=round(wet['luminance_mean'] / max(dry['luminance_mean'], 1e-6), 3),
                 passes=dict(roughness_p5_at_least_0_4=bool(wet['roughness_p5_50_95'][0] >= 0.4))),
        note='linear buffers (MRP calibration); the middle 60 % of each capture (the stones: the whole picture, the ground hidden)')
    if (OUT / 'PBR_Gravel_Stones_BaseColor.exr').exists():
        rows['stones'] = stones(dry['luminance_p5_50_95'][1])
    rows['ok'] = all(v for k in ('dry', 'wet', 'stones') if k in rows for v in rows[k]['passes'].values())
    (OUT / 'pbr-rows.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=1))
    print('GRAVEL_PBR_ROWS_%s' % ('OK' if rows['ok'] else 'FAIL'))


if __name__ == '__main__':
    main()
