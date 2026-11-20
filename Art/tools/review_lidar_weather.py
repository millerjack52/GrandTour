"""Compare native LiDAR weather probes and track ordinary repeat-to-repeat image variation."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from compare_lidar_shadow_drive import LUMA_WEIGHTS


def samples(directory):
    rows = (directory / "weather.jsonl").read_text(encoding="utf-8").splitlines()
    return {data["frame_state"]: data for data in map(json.loads, rows)}


def brightness(path):
    with Image.open(path) as image:
        assert image.size == (1600, 900)
        pixels = np.asarray(image.convert("RGB"), dtype=np.float32)
    return pixels[170:890, 40:1510] @ LUMA_WEIGHTS


def compare(reference, candidate, repeat):
    controls, trial, repeated = map(samples, (reference, candidate, repeat))
    stages = {"dry1", "dry2", "onset", "raining", "drying", "dry3", "dry4", "snowing", "melting"}
    assert controls.keys() == trial.keys() == repeated.keys() == stages
    assert all(row["gate"] == 0 for row in (*controls.values(), *repeated.values()))
    assert all(row["gate"] == 1 for row in trial.values())
    assert trial["dry1"]["captures"] == trial["dry2"]["captures"]
    assert trial["dry3"]["captures"] == trial["dry4"]["captures"]
    assert trial["onset"]["captures"] > trial["dry2"]["captures"]
    assert trial["raining"]["captures"] < trial["drying"]["captures"]
    assert trial["snowing"]["captures"] > trial["dry4"]["captures"]
    depths = {}
    for stage in sorted(stages):
        row, old = trial[stage], controls[stage]
        assert (row["wetness"], row["snow"], row["drops"]) == (
            old["wetness"],
            old["snow"],
            old["drops"],
        )
        dry = row["state"] == "Clear" and row["wetness"] == 0 and row["snow"] == 0
        assert row["enabled"] == float(not dry)
        if not dry:
            assert row["centre"] == old["centre"]
            depths[stage] = max(
                abs(x - y) for x, y in zip(row["depth_cm"], old["depth_cm"], strict=True)
            )
    views = {}
    for name in ("dry", "rain", "drying", "snow"):
        original = brightness(reference / f"{name}.png")
        views[name] = {}
        for key, folder in (("change", candidate), ("original_repeat", repeat)):
            delta = np.abs(brightness(folder / f"{name}.png") - original)
            views[name][key] = {
                "mean_luma_255": round(float(delta.mean()), 3),
                "scene_pct_over_8": round(float((delta > 8).mean() * 100), 3),
            }
    return {
        "reference": controls,
        "candidate": trial,
        "repeat": repeated,
        "depth_max_difference_cm": depths,
        "views": views,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "candidate", "repeat", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(compare(args.reference, args.candidate, args.repeat), indent=2) + "\n",
        encoding="utf-8",
    )
