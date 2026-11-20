"""Compare native driving-image crops known to expose mismatched tree shading and shapes."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

from compare_lidar_shadow_drive import LUMA_WEIGHTS, font


REGIONS = (
    ("Paddock sunlit crowns", "paddock_mid", "r019.png", (1424, 72, 1520, 168)),
    ("Paddock crown shadow", "paddock_mid", "r027.png", (720, 232, 816, 328)),
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


def compare(original, repeat, trial, output, paddock_only=False):
    output.mkdir(exist_ok=True, parents=True)
    folders = (original, repeat, trial)
    poses = []
    for folder in folders:
        schedule = json.loads((folder / "shadow-schedule.json").read_text())
        if schedule["stage"] != "routefilm":
            raise ValueError(f"A full fixed-camera route film is required: {folder}")
        measured = json.loads((folder / "shadow-results.json").read_text())
        if paddock_only:
            if not measured or measured[0]["name"] != "paddock_mid" or len(measured[0]["pawn_cm"]) != 13:
                raise ValueError(f"Missing the 13 opening paddock positions in {folder}")
            measured = measured[:1]
        poses.append({section["name"]: section["pawn_cm"] for section in measured})
    if not poses[0] == poses[1] == poses[2] or len(poses[0]) != (1 if paddock_only else 5):
        raise ValueError("Route positions do not match across all three films")
    regions = [r for r in REGIONS if not paddock_only or r[1] == "paddock_mid"]
    board = Image.new("RGB", (990, 34 + 230 * len(regions)), "#18211e")
    draw = ImageDraw.Draw(board)
    for col, title in enumerate(("Original", "Original repeat", "Candidate")):
        draw.text((col * 330 + 10, 4), title, font=font(20), fill="white")
    results = []
    for row, (title, section, filename, rect) in enumerate(regions):
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
    prefix = "paddock-crops" if paddock_only else "driving-tree-crops"
    board.save(output / f"{prefix}.png")
    (output / f"{prefix}.json").write_text(json.dumps(results, indent=2) + "\n")


def scan_route(original, repeat, trial, output):
    folders = (original, repeat, trial)
    names = ("paddock_mid", "access", "river", "bog_entry", "bog552")
    measurements = [json.loads((folder / "shadow-results.json").read_text()) for folder in folders]
    positions = [[row["pawn_cm"] for row in run] for run in measurements]
    if any(tuple(row["name"] for row in run) != names for run in measurements):
        raise ValueError("Expected the five driving checkpoints in order")
    if positions[0] != positions[1] or positions[0] != positions[2] or sum(map(len, positions[0])) != 65:
        raise ValueError("The film requires 65 matching pickup positions")

    # Native 96-pixel squares on a 32-pixel grid, omitting tiles touching the HUD.
    x, y = np.meshgrid(np.arange(16, 1505, 32), np.arange(8, 805, 32))
    outside_hud = (x >= 436) | (y >= 151)
    x, y = x[outside_hud], y[outside_hud]
    u, v = x // 8, y // 8

    def tiles(delta):
        cells = np.abs(delta[:896]).reshape(112, 8, 200, 8).mean(axis=(1, 3))
        table = np.pad(cells, ((1, 0), (1, 0))).cumsum(axis=0, dtype=np.float64).cumsum(axis=1)
        return (table[v + 12, u + 12] - table[v, u + 12] - table[v + 12, u] + table[v, u]) / 144

    board = Image.new("RGB", (960, 1040), "#18211e")
    draw = ImageDraw.Draw(board)
    for col, title in enumerate(("Original", "Original repeat", "Candidate")):
        draw.text((col * 320 + 8, 5), title, font=font(19), fill="white")
    results = {}
    for section, name in enumerate(names):
        rows = []
        for frame in range(48):
            filename = f"r{section}{frame:02d}.png"
            values = []
            for folder in folders:
                with Image.open(folder / filename) as shot:
                    if shot.size != (1600, 900):
                        raise ValueError(f"Unexpected image dimensions at {folder / filename}")
                    values.append(np.asarray(shot.convert("RGB"), dtype=np.float32) @ LUMA_WEIGHTS)
            baseline, candidate = (tiles(value - values[0]) for value in values[1:])
            excess = candidate - baseline
            index = int(excess.argmax())
            box = [int(x[index]), int(y[index]), int(x[index] + 96), int(y[index] + 96)]
            rows.append(dict(frame=filename, box=box, repeat=round(float(baseline[index]), 3),
                             candidate=round(float(candidate[index]), 3), excess=round(float(excess[index]), 3)))
        results[name] = rows
        peak = max(rows, key=lambda item: item["excess"])
        top = 35 + section * 200
        draw.text((6, top), f"{name.replace('_', ' ')}   {peak['frame']}   "
                  f"candidate {peak['candidate']:.2f}, repeat {peak['repeat']:.2f}", font=font(17), fill="white")
        for col, folder in enumerate(folders):
            with Image.open(folder / peak["frame"]) as shot:
                crop = shot.convert("RGB").crop(peak["box"]).resize((166, 166), Image.Resampling.NEAREST)
            board.paste(crop, (col * 320 + 77, top + 25))
    board.save(output / "route-tile-peaks.jpg", quality=94)
    (output / "route-tiles.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "repeat", "trial", "output"):
        parser.add_argument(name, type=Path)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--scan-route", action="store_true", help="Check every moving frame against the original repeat")
    scope.add_argument("--paddock-only", action="store_true", help="Compare the 13 matching positions in the opening drive")
    args = parser.parse_args()
    compare(args.original, args.repeat, args.trial, args.output, args.paddock_only)
    if args.scan_route:
        scan_route(args.original, args.repeat, args.trial, args.output)
