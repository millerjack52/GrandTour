"""Compare native driving-image crops known to expose mismatched tree shading and shapes."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from compare_lidar_shadow_drive import LUMA_WEIGHTS, font


REGIONS = (
    ("Paddock skyline", "paddock_mid", "r047.png", (1056, 81, 1376, 291)),
    ("Forest access sunlight", "access", "r140.png", (864, 40, 960, 136)),
    ("Bog approach bark", "bog_entry", "r319.png", (1424, 483, 1520, 579)),
    ("Deep bog grass", "bog552", "r410.png", (272, 771, 368, 867)),
)


def difference(original, trial):
    delta = np.asarray(trial, dtype=float) - np.asarray(original, dtype=float)
    return {
        "mean_absolute_brightness_255": round(float(np.abs(delta @ LUMA_WEIGHTS).mean()), 3),
        "mean_signed_rgb_255": np.round(delta.mean(axis=(0, 1)), 3).tolist(),
    }


def compare(original, repeat, trial, output):
    output.mkdir(exist_ok=True, parents=True)
    folders = (original, repeat, trial)
    poses = []
    for folder in folders:
        schedule = json.loads((folder / "shadow-schedule.json").read_text())
        if schedule["stage"] != "routefilm":
            raise ValueError(f"A full fixed-camera route film is required: {folder}")
        measured = json.loads((folder / "shadow-results.json").read_text())
        poses.append({section["name"]: section["pawn_cm"] for section in measured})
    if not poses[0] == poses[1] == poses[2] or len(poses[0]) != 5:
        raise ValueError("Route positions do not match across all three films")
    board = Image.new("RGB", (990, 34 + 230 * len(REGIONS)), "#18211e")
    draw = ImageDraw.Draw(board)
    for col, title in enumerate(("Original", "Original repeat", "Candidate")):
        draw.text((col * 330 + 10, 4), title, font=font(20), fill="white")
    results = []
    for row, (title, section, filename, rect) in enumerate(REGIONS):
        top = 34 + 230 * row
        draw.text((10, top), title, font=font(18), fill="#d3e2ce")
        crops = []
        for col, folder in enumerate(folders):
            with Image.open(folder / filename) as image:
                if image.size != (1600, 900):
                    raise ValueError(f"Expected 1600 x 900 at {folder / filename}")
                crop = image.convert("RGB").crop(rect)
            crops.append(crop)
            shown = ImageOps.contain(crop, (320, 190), Image.Resampling.NEAREST)
            board.paste(shown, (col * 330 + (330 - shown.width) // 2, top + 28))
        results.append(
            {
                "section": section,
                "frame": filename,
                "rect": rect,
                "repeat": difference(crops[0], crops[1]),
                "candidate": difference(crops[0], crops[2]),
            }
        )
    board.save(output / "driving-tree-crops.png")
    (output / "driving-tree-crops.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "repeat", "trial", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    compare(args.original, args.repeat, args.trial, args.output)
