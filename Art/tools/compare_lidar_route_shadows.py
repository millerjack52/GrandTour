"""Pair native chase-camera frames by route section and simulation time."""

import argparse
import json
import math
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw

from compare_lidar_shadow_drive import LUMA_WEIGHTS, font, read


NAMES = {
    "paddock_mid": "Fine-grass paddock",
    "access": "Forest access",
    "river": "River margin",
    "bog_entry": "Deep-bog approach",
    "bog552": "Deep-bog checkpoint",
}


def review(stock, trial, output):
    output.mkdir(parents=True, exist_ok=True)
    takes = [read(folder / "shadow-results.json") for folder in (stock, trial)]
    plans = [read(folder / "shadow-schedule.json") for folder in (stock, trial)]
    assert plans[0]["stage"] == plans[1]["stage"]
    boundary = plans[0]["stage"] == "boundaryfilm"
    names = {key: NAMES[key] for key in ("paddock_mid", "access")} if boundary else NAMES
    count, rate = (60, 2) if boundary else (48, 8)
    prefix = "boundary" if boundary else "route"
    labels = font(21)
    board = Image.new("RGB", (1280, 394 * len(names)), "#18211e")
    painter = ImageDraw.Draw(board)
    results = {}
    movie = imageio_ffmpeg.write_frames(
        str(output / f"lidar-{prefix}-shadows.mp4"),
        (1600, 496),
        fps=rate,
        codec="libx264",
        quality=None,
        macro_block_size=1,
        output_params=[
            "-crf",
            "17",
            "-preset",
            "veryfast",
            "-threads",
            "2",
            "-movflags",
            "+faststart",
        ],
    )
    movie.send(None)
    try:
        for station, (name, title) in enumerate(names.items()):
            before, after = (take[station] for take in takes)
            assert before["name"] == after["name"] == name
            assert len(before["pawn_cm"]) == len(after["pawn_cm"]) and len(before["pawn_cm"]) > 1
            separation = max(math.dist(a, b) for a, b in zip(before["pawn_cm"], after["pawn_cm"]))
            deltas = []
            worst = -1
            for index in range(count):
                frame = Image.new("RGB", (1600, 496), "#18211e")
                overlay = ImageDraw.Draw(frame)
                luma = []
                for side, (folder, label) in enumerate(
                    ((stock, "Original"), (trial, "Shadow fix"))
                ):
                    with Image.open(folder / f"r{station}{index:02}.png") as capture:
                        assert capture.size == (1600, 900)
                        rgb = capture.convert("RGB")
                    frame.paste(rgb.resize((800, 450), Image.Resampling.LANCZOS), (800 * side, 46))
                    overlay.text(
                        (800 * side + 14, 7), f"{label}   |   {title}", fill="white", font=labels
                    )
                    pixels = np.asarray(rgb, dtype=np.float32) @ LUMA_WEIGHTS
                    luma.append(pixels)
                movie.send(frame.tobytes())
                delta = np.abs(luma[0] - luma[1])
                scene = delta[195:875, 80:1520]
                skyline = delta[45:410, 495:1487]
                # Largest local error in a 96x96 patch helps catch coherent shadow loss.
                tiles = scene[:672, :1440].reshape(7, 96, 15, 96).mean(axis=(1, 3))
                deltas.append(
                    (
                        float(scene.mean()),
                        float((scene > 8).mean() * 100),
                        float(skyline.mean()),
                        float(tiles.max()),
                    )
                )
                if deltas[-1][3] > worst:
                    worst = deltas[-1][3]
                    image = frame.crop((0, 46, 1600, 496)).resize(
                        (1280, 360), Image.Resampling.LANCZOS
                    )
                    board.paste(image, (0, station * 394 + 34))
                    worst_index = index
            painter.text(
                (12, station * 394 + 3),
                f"{title}   |   Original (left) and shadow fix (right)   |   {worst_index / rate:.2f} s",
                fill="white",
                font=labels,
            )
            data = np.array(deltas)
            results[name] = {
                "travel_m": [before["travel_m"], after["travel_m"]],
                "pose_samples": len(before["pawn_cm"]),
                "max_separation_cm": round(separation, 3),
                "samples": len(deltas),
                "mean_luma_delta_255": round(float(data[:, 0].mean()), 3),
                "max_pct_over_8": round(float(data[:, 1].max()), 3),
                "mean_upper_scene_delta_255": round(float(data[:, 2].mean()), 3),
                "worst_96px_patch_mean_delta_255": round(worst, 3),
                "worst_local_frame": worst_index,
            }
    finally:
        movie.close()
    board.save(output / f"{prefix}-pairs.jpg", quality=93)
    (output / f"{prefix}-visual.json").write_text(json.dumps(results, indent=2))
    return results


def compare_held(folder, output, sections=None):
    """Measure treatment changes against repeated original frames at the same time and pose."""
    output.mkdir(parents=True, exist_ok=True)
    results = []
    sections = list(NAMES) if sections is None else sections
    board = Image.new("RGB", (1280, 394 * len(sections)), "#18211e")
    painter = ImageDraw.Draw(board)
    for row, name in enumerate(sections):
        title = NAMES[name]
        station = list(NAMES).index(name)
        highest = -1
        for n in range(2):
            sample = 2 * station + n
            a, b = (read(folder / f"record_{sample}_{key}.json") for key in ("a", "b"))
            assert abs(a["game_time"] - b["game_time"]) < 0.001
            for key in ("pawn", "camera", "rotation"):
                assert math.dist(a[key], b[key]) < 0.01, (sample, key)
            luma = {}
            for key in ("a0", "a1", "b0", "b1", "c1"):
                with Image.open(folder / f"h{sample}{key}.png") as im:
                    luma[key] = np.asarray(im.convert("RGB"), dtype=np.float32) @ LUMA_WEIGHTS
            stats = {}
            for label, p, q in (
                ("shadow_change", "a1", "b1"),
                ("stock_repeat", "a0", "a1"),
                ("trial_repeat", "b0", "b1"),
                ("stock_restored", "a1", "c1"),
            ):
                delta = np.abs(luma[p] - luma[q])
                scene = delta[195:875, 80:1520]
                upper = delta[45:410, 495:1487]
                tiles = scene[:672, :1440].reshape(7, 96, 15, 96).mean(axis=(1, 3))
                stats[label] = {
                    "mean_scene_255": round(float(scene.mean()), 3),
                    "pct_scene_over_8": round(float((scene > 8).mean() * 100), 3),
                    "mean_upper_255": round(float(upper.mean()), 3),
                    "worst_96px_mean_255": round(float(tiles.max()), 3),
                }
            results.append({"section": name, "sample": sample, "pose": a, "luma": stats})
            severity = stats["shadow_change"]["worst_96px_mean_255"]
            if severity > highest:
                highest = severity
                for col, key in enumerate(("a1", "b1")):
                    with Image.open(folder / f"h{sample}{key}.png") as im:
                        board.paste(
                            im.convert("RGB").resize((640, 360), Image.Resampling.LANCZOS),
                            (col * 640, row * 394 + 34),
                        )
        painter.text(
            (12, row * 394 + 3),
            f"{title}   |   Original (left) and shadow fix (right), same game time",
            fill="white",
            font=font(21),
        )
    board.save(output / "held-pairs.jpg", quality=94)
    (output / "held-visual.json").write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for field in ("stock", "trial", "output"):
        parser.add_argument(field, type=Path)
    parser.add_argument("--held", type=Path, help="Also assess the routehold drive")
    parser.add_argument(
        "--held-sections",
        nargs="+",
        choices=NAMES,
        help="Completed checkpoints in the held capture",
    )
    args = parser.parse_args()
    print(json.dumps(review(args.stock, args.trial, args.output), indent=2))
    if args.held:
        compare_held(args.held, args.output, args.held_sections)
