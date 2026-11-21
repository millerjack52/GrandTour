"""Bake tileable, driving-scale variation into an existing sRGB ground colour tile."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def periodic_field(rng, size, cells):
    """Bicubic reconstruction with wrapped neighbours at every tile edge."""
    width, height = size
    samples = rng.uniform(-1, 1, (cells, cells)).astype(np.float32)
    padded = Image.fromarray(np.pad(samples, 2, mode="wrap"))
    return np.asarray(padded.resize(
        (width, height), Image.Resampling.BICUBIC,
        box=(2, 2, cells + 2, cells + 2),
    ))


def bake(source, target, seed):
    if source.resolve() == target.resolve():
        raise ValueError("Choose a separate output for the candidate")
    with Image.open(source) as original:
        if original.mode not in ("RGB", "RGBA"):
            raise ValueError("Expected an RGB or RGBA sRGB colour tile")
        pixels = np.asarray(original).copy()
        rgb = pixels[:, :, :3].astype(np.float32)
        value = rgb @ np.array([0.213, 0.715, 0.072], dtype=np.float32)
        rng = np.random.default_rng(seed)
        # Preserve the position of painted stones, so their normal map still fits.
        offset = 0.52 * (value - np.median(value))
        for cells, amplitude in ((4, 24), (11, 12), (27, 5)):
            offset += amplitude * periodic_field(rng, original.size, cells)
        offset -= offset.mean()
        pixels[:, :, :3] = np.clip(np.rint(rgb + offset[:, :, None]), 0, 255)
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--seed", type=int, default=711)
    args = parser.parse_args()
    bake(args.source, args.target, args.seed)
