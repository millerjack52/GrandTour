"""Paint two seamless woodland surface studies at metre scale from overlapping brush shapes."""

import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


def paint_surfaces(out):
    size = 512
    rng = np.random.default_rng(61123)

    def clouds(sigma):
        a = ndimage.gaussian_filter(rng.normal(size=(size, size)), sigma, mode="wrap")
        return np.clip(0.5 + (a - a.mean()) / max(a.std(), 1.0e-5) * 0.18, 0, 1)

    def rgba(planes):
        return Image.fromarray(np.clip(np.stack(planes, -1) * 255 + 0.5, 0, 255).astype("uint8"))

    def strokes(bg, count, lengths, widths, slant, strength, texture):
        im = Image.fromarray(np.clip(bg * 255, 0, 255).astype("uint8"))
        pen = ImageDraw.Draw(im)
        for _ in range(count):
            x, y = rng.integers(size, size=2)
            a = slant + (texture[y, x] - 0.5) * 1.3 + rng.normal(0, 0.16)
            length = rng.uniform(*lengths)
            width = rng.uniform(*widths)
            tone = int(np.clip(bg[y, x] + rng.uniform(-strength, strength), 0, 1) * 255)
            outline = [
                (-0.54, -0.06),
                (-0.34, -0.36),
                (-0.08, -0.45),
                (0.39, -0.29),
                (0.54, 0.04),
                (0.31, 0.24),
                (-0.19, 0.47),
                (-0.44, 0.27),
            ]
            points = [
                (
                    x + u * length * math.cos(a) - v * width * math.sin(a),
                    y + u * length * math.sin(a) + v * width * math.cos(a),
                )
                for u, v in outline
            ]
            for dx in (-size, 0, size):
                for dy in (-size, 0, size):
                    pen.polygon([(px + dx, py + dy) for px, py in points], fill=tone)
        return np.asarray(im, dtype="float32") / 255

    large = clouds(24)
    medium = clouds(8)
    small = clouds(3)
    sweep = strokes(0.28 + 0.46 * large, 280, (30, 110), (7, 24), -0.39, 0.19, medium)
    chisel = strokes(0.27 + 0.48 * medium, 480, (13, 44), (3, 10), -0.56, 0.19, large)
    # Connected cushions, with soft boundary transitions. Highlights occur along
    # the shoulders of lobes; there is no white point noise between them.
    bed = np.clip(0.66 * large + 0.29 * medium + 0.05 * small, 0, 1)
    low, high = np.gradient(bed)
    shoulder = np.clip(0.48 + 6.2 * low + 3.3 * high, 0, 1)
    moss = strokes(0.29 + 0.48 * bed, 520, (5, 17), (2, 6), -0.83, 0.11, large)
    rgba([sweep, chisel, bed, 0.48 * shoulder + 0.52 * moss]).save(out / "T_WoodlandPaint.png")
