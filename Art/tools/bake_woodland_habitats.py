"""Bake terrain-scale forest communities and a seamless painted litter tile."""

import argparse
import json
import math
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from woodland_paint import paint_surfaces


def smooth(low, high, x):
    t = np.clip((x - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def litter_tile(folder, rng):
    # 2.4 m of floor. Each ellipse of deposition shares a grain direction and
    # has a ragged end; a folded leaf has two different planes and a central rib.
    size = 512
    grain = ndimage.gaussian_filter(rng.normal(size=(size, size)), 3, mode="wrap") * 23
    grain += rng.normal(0, 4, (size, size))
    earth = np.clip(np.array([72, 59, 42]) + grain[:, :, None], 0, 255).astype("uint8")
    tile = Image.fromarray(earth).convert("RGBA")
    tile.putalpha(25)
    draw = ImageDraw.Draw(tile)
    for _ in range(30):
        cx, cy = rng.uniform(0, size, 2)
        heading = rng.uniform(0, math.tau)
        for _ in range(rng.integers(24, 68)):
            p, q = rng.normal(0, [54, 19])
            x = (cx + p * math.cos(heading) - q * math.sin(heading)) % size
            y = (cy + p * math.sin(heading) + q * math.cos(heading)) % size
            a = heading + rng.normal(0, 0.87)
            length = rng.uniform(4, 16)
            width = length * rng.uniform(0.19, 0.43)
            tint = rng.uniform(0.72, 1.20)
            col = np.array([136, 104, 66]) * tint
            for ox in [-size, 0, size]:
                for oy in [-size, 0, size]:
                    bx, by = x + ox, y + oy
                    if not (-20 < bx < size + 20 and -20 < by < size + 20):
                        continue

                    def pt(l, w):
                        return (
                            bx + math.cos(a) * l * length - math.sin(a) * w * width,
                            by + math.sin(a) * l * length + math.cos(a) * w * width,
                        )

                    for sign, light, height in [(1, 1.04, 170), (-1, 0.76, 110)]:
                        draw.polygon(
                            [
                                pt(-1, 0),
                                pt(-0.46, sign * 0.79),
                                pt(0.14, sign),
                                pt(0.70, sign * 0.43),
                                pt(1, 0),
                                pt(-0.08, 0.10),
                            ],
                            fill=tuple((col * light).astype(int)) + (height,),
                        )
                    draw.line(
                        [pt(-1.18, 0), pt(-0.08, 0.10), pt(0.81, 0)],
                        fill=tuple((col * 1.1).astype(int)) + (205,),
                        width=1,
                    )
    tile.save(folder / "T_WoodlandLitter.png")


def bake(place, out, trees):
    rng = np.random.default_rng(91648)
    out.mkdir(parents=True, exist_ok=True)
    source = json.loads((place.parent / "authoring.json").read_text())
    origin = np.asarray(source["origin"])
    span = source["size"]
    style = np.asarray(Image.open(place / "style.png"), dtype="float32") / 255
    n = len(style)
    cell = span / n
    metres = cell / 100

    def index(xy):
        return np.clip(np.floor((xy - origin) / cell).astype("int32"), 0, n - 1)

    canopy = np.zeros((n, n), dtype="float32")
    tree_xy = np.fromfile(trees, "<f4").reshape(-1, 2)
    ij = index(tree_xy)
    np.add.at(canopy, (ij[:, 1], ij[:, 0]), 1.0)
    canopy = ndimage.gaussian_filter(canopy, 7 / metres)
    forest = (
        np.asarray(
            Image.open(place.parent / "Reference/forest-mask.png").convert("L"), dtype="float32"
        )
        / 255
    )
    woods = smooth(0.12, 0.72, forest) * (1 - smooth(0.52, 0.85, style[:, :, 1]))
    sample = canopy[(woods > 0.7) & (canopy > 0.002)]
    shelter = smooth(0, max(0.02, np.quantile(sample, 0.78)), canopy)
    raw = np.fromfile(place / "authoring-height.r16", "<u2")
    r = math.isqrt(len(raw))
    assert r * r == len(raw)
    z = (
        np.asarray(
            Image.fromarray(raw.reshape(r, r).astype("float32")).resize(
                (n, n), Image.Resampling.BILINEAR
            )
        )
        * source["height_span_cm"]
        / (65535 * 100)
    )
    gy, gx = np.gradient(ndimage.gaussian_filter(z, 1.3), metres)
    slope = np.hypot(gx, gy)
    hollow = ndimage.gaussian_filter(z, 7 / metres) - z

    def noise(spacing):
        m = max(4, math.ceil(n * metres / spacing))
        grid = rng.uniform(0, 1, (m, m)).astype("float32")
        return np.asarray(Image.fromarray(grid).resize((n, n), Image.Resampling.BICUBIC))

    broad = noise(29) * 0.59 + noise(11) * 0.31 + noise(4.6) * 0.10
    mid = noise(16) * 0.75 + noise(6) * 0.25
    roads = Image.new("L", (n, n))
    draw = ImageDraw.Draw(roads)
    for road in json.loads((place / "roads.json").read_text()):
        draw.line([tuple(p) for p in index(np.asarray(road["points"])[:, :2])], fill=255, width=1)
    road_dist = ndimage.distance_transform_edt(np.asarray(roads) == 0) * metres
    wet = np.zeros((n, n), bool)
    for file in place.glob("*-domain.bin"):
        data = file.read_bytes()
        magic, nx, ny, _, _, x, y, step = struct.unpack_from("<5i3f", data)
        assert magic == 0x47545744
        cells = np.frombuffer(data, "<f4", count=nx * ny * 4, offset=32).reshape(ny, nx, 4)
        j, i = np.nonzero(cells[:, :, 1] > 0)
        ij = index(np.column_stack((x + (i + 0.5) * step, y + (j + 0.5) * step)))
        wet[ij[:, 1], ij[:, 0]] = True
    shore = ndimage.distance_transform_edt(~wet) * metres
    # Coherent ribbons follow local contours. Domain warp and two wavelengths
    # interrupt the ribbons before they become parallel stripes across hills.
    strata = 0.5 + 0.5 * np.sin(z * 0.53 + 6.7 * mid + 3.0 * broad)
    shelves = smooth(0.27, 0.76, slope + 0.15 * (mid - 0.5)) * smooth(0.27, 0.70, strata)
    bank = (1 - smooth(5, 26, shore)) * smooth(0.15, 0.59, strata + mid * 0.15)
    stone = np.clip(np.maximum(shelves, bank) * 1.18, 0, 1)
    moss = smooth(
        0.36, 0.68, 0.51 * broad + 0.21 * mid + 0.27 * shelter + 0.13 * np.clip(hollow, -1, 1)
    ) * (1 - stone * 0.79)
    opening = smooth(0.45, 0.70, 0.69 * mid + 0.20 * (1 - shelter) + 0.20 * broad) * (
        1 - stone * 0.92
    )
    margin = smooth(3.8, 6.0, road_dist) * smooth(1.9, 4.2, shore)
    weight = woods * margin
    # R coverage / G moss and fern / B exposed rock / A grass opening.
    fields = np.clip(np.stack((weight, moss, stone, opening), -1) * 255 + 0.5, 0, 255).astype(
        "uint8"
    )
    Image.fromarray(fields).save(out / "T_WoodlandHabitat.png")
    # Retain occasional grasses in the fern beds and let gaps interrupt the road verge.
    woodland_grass = 0.13 + 0.87 * opening**1.5
    verge = (1 - smooth(4, 13, road_dist)) * smooth(0.30, 0.69, broad)
    woodland_grass = np.maximum(woodland_grass, verge * 0.66)
    grass = 1 - woods * (1 - woodland_grass)
    grass = np.clip(grass * 255 + 0.5, 0, 255).astype("uint8")
    moss_stamps = np.clip(weight * smooth(0.46, 0.76, moss) * (1 - opening) * 255, 0, 255).astype(
        "uint8"
    )
    for name, array in [("grass-density", grass), ("moss-density", moss_stamps)]:
        (out / (name + ".bin")).write_bytes(struct.pack("<I", n) + array.tobytes())
    (out / "habitat.rgba").write_bytes(fields.tobytes())
    litter_tile(out, rng)
    paint_surfaces(out)
    eligible = weight > 0.5
    report = dict(
        origin=origin.tolist(),
        span=span,
        size=n,
        canopy_instances=len(tree_xy),
        woodland_km2=round(float(eligible.sum() * metres**2 / 1e6), 3),
        grass_open_fraction=round(float((opening[eligible] > 0.5).mean()), 3),
        mineral_fraction=round(float((stone[eligible] > 0.5).mean()), 3),
        moss_fraction=round(float((moss[eligible] > 0.5).mean()), 3),
    )
    (out / "field.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("place", "out", "trees"):
        p.add_argument("--" + key, type=Path, required=True)
    a = p.parse_args()
    bake(a.place, a.out, a.trees)
