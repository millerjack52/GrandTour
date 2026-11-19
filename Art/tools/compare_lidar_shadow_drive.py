"""Compare normal gameplay frames and same-pose shadow captures on the logging track."""

import argparse
import json
import math
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
import numpy as np

SCENE_BOUNDS = (80, 195, 1520, 875)
LUMA_WEIGHTS = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def font(size):
    return ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)


def make_movie(before, after, dest):
    paths = [sorted(d.glob("film_*.png")) for d in (before, after)]
    assert all(len(p) == 96 for p in paths)
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        exe,
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        "1920x590",
        "-r",
        "12",
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-threads",
        "2",
        "-preset",
        "veryfast",
        "-crf",
        "17",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    label_font = font(23)
    frame_deltas = []
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as encoder:
        for idx, pair in enumerate(zip(*paths)):
            frame = Image.new("RGB", (1920, 590), "#1c2421")
            draw = ImageDraw.Draw(frame)
            scene_luma = []
            for side, (f, label) in enumerate(zip(pair, ("Current shadows", "Candidate shadows"))):
                with Image.open(f) as image:
                    assert image.size == (1600, 900)
                    crop = image.crop(SCENE_BOUNDS).convert("RGB")
                    scene_luma.append(np.asarray(crop, dtype=np.float32) @ LUMA_WEIGHTS)
                    frame.paste(
                        image.convert("RGB").resize((960, 540), Image.Resampling.LANCZOS),
                        (960 * side, 50),
                    )
                draw.text((960 * side + 18, 8), label, fill="white", font=label_font)
            draw.text((1740, 8), f"{idx / 12:.2f} s", fill="#cfdbd0", font=label_font)
            encoder.stdin.write(frame.tobytes())
            delta = np.abs(scene_luma[0] - scene_luma[1])
            frame_deltas.append((float(delta.mean()), float((delta > 8).mean() * 100)))
        encoder.stdin.close()
        if encoder.wait():
            raise RuntimeError("Comparison encode failed")
    drives = [read(folder / "shadow-results.json")[0] for folder in (before, after)]
    positions = [drive["pawn_cm"] for drive in drives]
    assert len(positions[0]) == len(positions[1]) and positions[0]
    mean_delta, changed_percent = np.array(frame_deltas).T
    motion = {
        "frames": len(frame_deltas),
        "seconds": len(frame_deltas) / 12,
        "crop_xyxy": SCENE_BOUNDS,
        "positions": len(positions[0]),
        "max_pawn_separation_cm": max(math.dist(a, b) for a, b in zip(*positions)),
        "travel_m": [drive["travel_m"] for drive in drives],
        "mean_luma_delta_255_per_frame": {
            "mean": round(float(mean_delta.mean()), 3),
            "max": round(float(mean_delta.max()), 3),
        },
        "pct_scene_luma_delta_over_8_per_frame": {
            "mean": round(float(changed_percent.mean()), 3),
            "max": round(float(changed_percent.max()), 3),
        },
        "highest_difference_frame": int(changed_percent.argmax()),
    }
    (dest.parent / "motion-comparison.json").write_text(json.dumps(motion, indent=2))


def image_delta(a, b):
    diff = np.abs(a - b)
    return {
        "mae_255": round(float(diff.mean()), 3),
        "pct_over_8": round(float((diff > 8).mean() * 100), 3),
        "p99_255": round(float(np.quantile(diff, 0.99)), 3),
    }


def exact_pairs(after, out):
    values = []
    # Mask the HUD and screen edges. These scene-space regions are also reported separately.
    rects = {
        "scene": SCENE_BOUNDS,
        "left_verge": (100, 335, 490, 700),
        "truck_ground": (540, 430, 1085, 860),
        "right_trees": (1130, 195, 1510, 570),
        "upper_canopy": (490, 42, 1500, 283),
        "distant_path": (650, 220, 1040, 420),
    }
    for n in range(4):
        pa, pb = [read(after / f"record_{n}_{c}.json") for c in ("a", "b")]
        assert abs(pa["game_time"] - pb["game_time"]) < 0.001
        assert math.dist(pa["pawn"], pb["pawn"]) < 0.01
        assert (
            math.dist(pa["camera"], pb["camera"]) < 0.01
            and math.dist(pa["rotation"], pb["rotation"]) < 0.001
        )
        imgs = {}
        for key in ("a0", "a1", "b0", "b1", "a2"):
            with Image.open(after / f"pair_{n}_{key}.png") as img:
                rgb = np.array(img.convert("RGB"), dtype=np.float32)
            imgs[key] = rgb @ LUMA_WEIGHTS
        regions = {}
        for name, (x, y, right, bottom) in rects.items():
            sub = {k: v[y:bottom, x:right] for k, v in imgs.items()}
            regions[name] = {
                title: image_delta(sub[a], sub[b])
                for title, a, b in [
                    ("before_repeat", "a0", "a1"),
                    ("after_repeat", "b0", "b1"),
                    ("before_after", "a1", "b1"),
                    ("baseline_restored", "a1", "a2"),
                ]
            }
        values.append(dict(sample=n, pose=pa, regions=regions))
    (out / "same-pose.json").write_text(json.dumps(values, indent=2))
    # Show the full matched views at the station with the largest measured change.
    worst = max(values, key=lambda v: v["regions"]["scene"]["before_after"]["mae_255"])["sample"]
    board = Image.new("RGB", (1600, 497), "#1c2421")
    draw = ImageDraw.Draw(board)
    for i, (key, label) in enumerate([("a1", "Current shadows"), ("b1", "Candidate shadows")]):
        with Image.open(after / f"pair_{worst}_{key}.png") as img:
            board.paste(img.convert("RGB").resize((800, 450), Image.Resampling.LANCZOS), (i * 800, 47))
        draw.text((i * 800 + 13, 7), label, fill="white", font=font(22))
    board.save(out / "matched-track.jpg", quality=94)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("before", "after", "out"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    make_movie(args.before, args.after, args.out / "wooded-mud-drive.mp4")
    exact_pairs(args.after, args.out)
