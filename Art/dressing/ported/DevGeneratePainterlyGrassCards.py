"""G1 of Docs/OWPainterlyGrassPlan.md: painterly grass/flower card textures.

Outputs 512x512 RGBA PNGs into GrassCards/ next to this script:
  T_OWGrassCard_01..06        blade clusters, GREYSCALE root->tip value ramp
                              (0.35 -> 1.0) - color comes from the material,
                              so one set serves every biome tint.
  T_OWFlowerCard_White/Yellow/Violet
                              same blades + colored head dabs in the top third.
  _ContactSheet.png           the G1 user gate.

Deterministic (fixed seed per card), rerunnable (overwrites). Painterly edge
comes from blurring the coverage and re-thresholding against value noise -
chunky dab silhouettes, no anti-aliased hair edges.

Plain Python (numpy + Pillow), no Unreal:  python DevGeneratePainterlyGrassCards.py
Import into UE (after the contact-sheet gate) with ClaudeImportGrassCards.py
(same folder).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RES = 512
OUT_DIR = Path(__file__).resolve().parent / "GrassCards"

GRASS_CARDS = [  # (name, seed, blade count, height fraction, lean px)
    ("T_OWGrassCard_01", 101, 5, 0.90, 20),
    ("T_OWGrassCard_02", 102, 7, 0.80, -35),
    ("T_OWGrassCard_03", 103, 4, 0.95, 55),
    ("T_OWGrassCard_04", 104, 6, 0.72, 0),
    ("T_OWGrassCard_05", 105, 3, 0.88, -60),
    ("T_OWGrassCard_06", 106, 7, 0.85, 30),
]
FLOWER_CARDS = [  # (name, seed, head RGB)
    ("T_OWFlowerCard_White", 201, (235, 235, 218)),
    ("T_OWFlowerCard_Yellow", 202, (242, 199, 56)),
    ("T_OWFlowerCard_Violet", 203, (148, 115, 217)),
]


def draw_blades(rng: np.random.Generator, count: int, height_frac: float,
                lean: float):
    """Stamp tapered bezier blades into value/coverage buffers.

    Returns (value 0..1, coverage 0..1, tip points)."""
    value = np.zeros((RES, RES))
    cover = np.zeros((RES, RES))
    yy, xx = np.mgrid[0:RES, 0:RES]
    tips = []
    # Each blade gets an evenly-spaced fan slot (+/- spread) so the cluster
    # fans out from a tight base instead of intertwining (round-1 kelp look).
    spread = 150.0
    for b in range(count):
        slot = -1.0 + 2.0 * (b + 0.5) / count      # -1..1 across the fan
        x0 = RES / 2 + rng.uniform(-22, 22)
        y0 = RES - 12
        tip_y = RES * (1.0 - height_frac) + rng.uniform(0, 50) \
            + abs(slot) * RES * 0.10               # outer blades shorter
        x2 = x0 + slot * spread + lean + rng.uniform(-18, 18)
        # single gentle arc: control point biased toward the base x
        x1 = x0 + (x2 - x0) * 0.25
        y1 = y0 + (tip_y - y0) * 0.55
        base_w = rng.uniform(14, 22)
        tip_w = rng.uniform(2, 4)
        droop = (0.6 + 0.4 * rng.random()) * slot  # tips bend over, outward
        v_base = rng.uniform(0.28, 0.42)           # per-blade depth variation
        v_tip = rng.uniform(0.88, 1.0)
        for t in np.linspace(0.0, 1.0, 130):
            bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * x1 + t * t * x2
            by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * y1 + t * t * tip_y
            if t > 0.75:                           # tip droop hook
                h = (t - 0.75) / 0.25
                bx += droop * 34.0 * h * h
                by += abs(droop) * 14.0 * h * h
            # dab-width jitter: chunky stroke, not a smooth taper
            r = max((base_w * (1 - t) ** 0.9 + tip_w * t) / 2, 1.2)
            r *= 1.0 + 0.22 * np.sin(t * 23.0 + b * 2.1)
            v = v_base + (v_tip - v_base) * t
            m = (xx - bx) ** 2 + (yy - by) ** 2 <= r * r
            value[m] = np.maximum(value[m], v)
            cover[m] = 1.0
        tips.append((float(bx), float(by)))
    return value, cover, tips


def painterly_alpha(rng: np.random.Generator, cover: np.ndarray) -> np.ndarray:
    """Blur coverage and re-threshold against noise -> chunky dab edges."""
    img = Image.fromarray((cover * 255).astype(np.uint8), "L")
    soft = np.asarray(img.filter(ImageFilter.GaussianBlur(3.5))) / 255.0
    noise = rng.random((RES // 16 + 1, RES // 16 + 1))
    noise = np.kron(noise, np.ones((16, 16)))[:RES, :RES]
    return (soft > 0.40 + 0.34 * (noise - 0.5)).astype(np.uint8) * 255


def make_card(name: str, seed: int, blades: int, height: float, lean: float,
              head_rgb=None) -> Image.Image:
    rng = np.random.default_rng(seed)
    value, cover, tips = draw_blades(rng, blades, height, lean)
    alpha = painterly_alpha(rng, cover)
    grey = (value * 255).astype(np.uint8)
    rgb = np.stack([grey, grey, grey], axis=-1)
    img = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
    if head_rgb is not None:
        d = ImageDraw.Draw(img)
        heads = rng.integers(5, 10)
        for i in range(int(heads)):
            # sit ON a blade tip (round-2 fix: a top-third clamp left heads
            # floating in air when their tip sat lower)
            tx, ty = tips[i % len(tips)]
            hx = tx + rng.uniform(-8, 8)
            hy = ty + rng.uniform(-10, 4)
            hr = rng.uniform(6, 10)
            for _ in range(3):  # overlapping dabs = painterly blob head
                ox, oy = rng.uniform(-4, 4), rng.uniform(-4, 4)
                jr = hr * rng.uniform(0.7, 1.0)
                jc = tuple(int(np.clip(c + rng.uniform(-18, 18), 0, 255))
                           for c in head_rgb)
                d.ellipse([hx + ox - jr, hy + oy - jr, hx + ox + jr, hy + oy + jr],
                          fill=jc + (255,))
    img.save(OUT_DIR / f"{name}.png")
    return img


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cards = []
    for name, seed, blades, height, lean in GRASS_CARDS:
        cards.append((name, make_card(name, seed, blades, height, lean)))
    for name, seed, rgb in FLOWER_CARDS:
        cards.append((name, make_card(name, seed, 5, 0.85, 0, head_rgb=rgb)))

    cell, pad = 300, 12
    cols = 3
    rows = (len(cards) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cell + pad) + pad,
                              rows * (cell + pad + 18) + pad), (46, 46, 52))
    d = ImageDraw.Draw(sheet)
    for i, (name, img) in enumerate(cards):
        cx = pad + (i % cols) * (cell + pad)
        cy = pad + (i // cols) * (cell + pad + 18)
        sheet.paste(img.resize((cell, cell)), (cx, cy), img.resize((cell, cell)))
        d.text((cx + 2, cy + cell + 3), name, fill=(210, 210, 210))
    sheet.save(OUT_DIR / "_ContactSheet.png")
    print(f"wrote {len(cards)} cards + contact sheet to {OUT_DIR}")


if __name__ == "__main__":
    main()
