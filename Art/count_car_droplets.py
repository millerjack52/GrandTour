"""MudRunner MR2b item 3 (docs/MUDRUNNER_LESSONS_PLAN.md MR2b): the droplet-density row from Car_Muddy_Side.png.

The dark-spot count in two boxes on the car's right side, the same height band on the door (92-114 cm above the wheel
bottoms): behind the right rear arch and mid-door. check_mud_variants.py writes the boxes' world corners and the camera into
drive-report.json (mr2.droplet_boxes); this projects them into the picture (the camera's horizontal FOV over the picture's
width, the principal point at its centre: the letterbox bars are symmetric) and counts, inside each box, the connected dark
spots (8-connected, 3-1500 px, not touching the box's border: a droplet cut by the border, or the coat's edge, is not
counted) darker than DarkShare x the box's own 95th-percentile luminance (its paint). The fans must hold at least 3x the
spots of mid-door per area. Functional only. Writes Car_Muddy_Side_Boxes.png beside the picture (the boxes and the counted
spots marked).

  python Art/count_car_droplets.py Art/Export/MudVariants/drive-report.json Art/Export/MudVariants/Car_Muddy_Side.png
Needs numpy and Pillow (system Python).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

DARK_SHARE = 0.6
MIN_PX, MAX_PX = 3, 1500


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


def spots(dark):
    """Connected dark components (8-connected) not touching the border, as lists of (y, x)."""
    h, w = dark.shape
    seen = np.zeros_like(dark, bool)
    found = []
    for y0 in range(h):
        for x0 in range(w):
            if not dark[y0, x0] or seen[y0, x0]:
                continue
            stack = [(y0, x0)]
            seen[y0, x0] = True
            pixels = []
            edge = False
            while stack:
                y, x = stack.pop()
                pixels.append((y, x))
                edge |= y == 0 or x == 0 or y == h - 1 or x == w - 1
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and dark[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            if not edge and MIN_PX <= len(pixels) <= MAX_PX:
                found.append(pixels)
    return found


def main():
    report = json.loads(Path(sys.argv[1]).read_text())
    picture = Path(sys.argv[2])
    boxes = report['mr2']['droplet_boxes']
    image = Image.open(picture).convert('RGB')
    width, height = image.size
    rgb = np.asarray(image).astype(float)
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    marked = image.copy()
    draw = ImageDraw.Draw(marked)
    rows = {}
    for name, box in boxes['boxes'].items():
        pts = [project(boxes['camera'], p, width, height) for p in box['world_corners']]
        xs = sorted(p[0] for p in pts)
        ys = sorted(p[1] for p in pts)
        x0, x1 = int(math.ceil(xs[1])), int(math.floor(xs[2]))   # the inner rectangle of the projected quad
        y0, y1 = int(math.ceil(ys[1])), int(math.floor(ys[2]))
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, width - 1), min(y1, height - 1)
        if x1 - x0 < 10 or y1 - y0 < 10:
            rows[name] = dict(error='box off the picture or too small', px=[x0, y0, x1, y1])
            continue
        crop = lum[y0:y1 + 1, x0:x1 + 1]
        paint = float(np.percentile(crop, 95))
        dark = crop < DARK_SHARE * paint
        found = spots(dark)
        cm = box['car_x_cm']
        area_cm2 = (cm[1] - cm[0]) * (boxes['z_band_cm'][1] - boxes['z_band_cm'][0])
        rows[name] = dict(px=[x0, y0, x1, y1], spots=len(found), per_100cm2=round(100.0 * len(found) / area_cm2, 2),
                          dark_share=round(float(dark.mean()), 3), paint_lum_p95=round(paint, 1),
                          spot_px_median=int(np.median([len(f) for f in found])) if found else 0)
        draw.rectangle([x0, y0, x1, y1], outline=(0, 255, 255), width=2)
        for f in found:
            ys_, xs_ = zip(*f)
            draw.rectangle([x0 + min(xs_) - 1, y0 + min(ys_) - 1, x0 + max(xs_) + 1, y0 + max(ys_) + 1], outline=(255, 0, 255))
    out = picture.with_name(picture.stem + '_Boxes.png')
    marked.save(out)
    fan = rows.get('behind_rear_arch', {})
    door = rows.get('mid_door', {})
    ratio = None
    if 'spots' in fan and 'spots' in door:
        ratio = (fan['per_100cm2'] / door['per_100cm2']) if door['per_100cm2'] > 0 else float('inf') if fan['per_100cm2'] > 0 else None
    for name, row in rows.items():
        print('MR2b droplet box %s: %s' % (name, ', '.join('%s %s' % kv for kv in row.items())))
    verdict = 'PASS' if ratio is not None and ratio >= 3.0 else 'FAIL'
    print('MR2b droplet density: behind the rear arch %s spots, mid-door %s spots; per area %s x (asked at least 3): %s; marked %s'
          % (fan.get('spots'), door.get('spots'), 'n/a' if ratio is None else ('inf' if ratio == float('inf') else '%.2f' % ratio), verdict, out))


if __name__ == '__main__':
    main()
