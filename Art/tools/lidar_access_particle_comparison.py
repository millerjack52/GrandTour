"""Compare moving forest-access pairs with ordinary and hidden tyre particles."""

import argparse
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageDraw

from compare_lidar_shadow_drive import LUMA_WEIGHTS, font


def luma(path):
    with Image.open(path) as source:
        if source.size != (1600, 900):
            raise ValueError(f"Unexpected capture dimensions at {path}")
        return np.asarray(source.convert("RGB"), dtype=np.float32) @ LUMA_WEIGHTS


def box_mean(image, rect):
    x, y, right, bottom = rect
    return round(float(image[y:bottom, x:right].mean()), 3)


def compare(folders, output):
    positions = []
    for i, folder in enumerate(folders):
        windows = json.loads((folder / "shadow-results.json").read_text())[:2]
        if [window["name"] for window in windows] != ["paddock_mid", "access"]:
            raise ValueError(f"Unexpected checkpoints at {folder}")
        positions.append([window["pawn_cm"] for window in windows])
        if i >= 2:
            log = (folder / "drive.log").read_text(errors="replace")
            if not re.search(r'\[899\]r\.Shadow\.Virtual\.Cache = "1"', log) or not re.search(
                r'\[900\]ShowFlag\.Particles = "0"', log
            ):
                raise ValueError(f"Missing access readback at {folder}")
    if not all(points == positions[0] for points in positions) or sum(map(len, positions[0])) != 26:
        raise ValueError("The four moving cameras require the same 26 pickup positions")
    x, y = np.meshgrid(np.arange(16, 1505, 32), np.arange(8, 805, 32))
    visible = (x >= 436) | (y >= 151)
    x, y = x[visible], y[visible]
    rows = []
    dust = (16, 680, 112, 776)
    light = (864, 40, 960, 136)
    for frame in range(48):
        name = f"r1{frame:02d}.png"
        original, trial, off_original, off_trial = [luma(path / name) for path in folders]
        normal = np.abs(original - trial)
        isolated = np.abs(off_original - off_trial)
        tiles = isolated[:896].reshape(112, 8, 200, 8).mean(axis=(1, 3))
        sums = np.pad(tiles, ((1, 0), (1, 0))).cumsum(0, dtype=np.float64).cumsum(1)
        u, v = x // 8, y // 8
        total = sums[v + 12, u + 12] - sums[v, u + 12] - sums[v + 12, u] + sums[v, u]
        ix = total.argmax()
        rect = (int(x[ix]), int(y[ix]), int(x[ix]) + 96, int(y[ix]) + 96)
        rows.append(dict(frame=name, dust_on=box_mean(normal, dust), dust_off=box_mean(isolated, dust),
                         sunlight_on=box_mean(normal, light), sunlight_off=box_mean(isolated, light),
                         max_without_particles=box_mean(isolated, rect), rect=rect))
    output.mkdir(exist_ok=True, parents=True)
    (output / "forest-access-particles.json").write_text(json.dumps(rows, indent=2) + "\n")
    worst = max(rows, key=lambda row: row["max_without_particles"])
    board = Image.new("RGB", (1072, 595), "#18211e")
    draw = ImageDraw.Draw(board)
    for i, title in enumerate(("Original", "Candidate", "Original, particles hidden", "Candidate, particles hidden")):
        draw.text((i * 268 + 5, 5), title, font=font(17), fill="white")
    for i, (frame, rect, title) in enumerate(((25, dust, "Tyre dust"), (40, light, "Sunlit gap"),
                                               (int(worst["frame"][2:4]), worst["rect"], "Largest difference with particles hidden"))):
        name = f"r1{frame:02d}.png"
        top = 34 + i * 187
        draw.text((6, top), f"{title}   {name}", font=font(16), fill="#d6e5d1")
        for col, folder in enumerate(folders):
            with Image.open(folder / name) as image:
                crop = image.convert("RGB").crop(rect).resize((152, 152), Image.Resampling.NEAREST)
            board.paste(crop, (col * 268 + 52, top + 25))
    board.save(output / "forest-access-particles.jpg", quality=94)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("trial", type=Path)
    parser.add_argument("original_hidden", type=Path)
    parser.add_argument("trial_hidden", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    compare((args.original, args.trial, args.original_hidden, args.trial_hidden), args.output)
