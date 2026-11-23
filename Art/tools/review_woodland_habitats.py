"""Compare the same in-engine camera path and independent woodland views."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Unreal/ForestAccessBend"))
from compare_reveal import panel, sheet


def review(before, after, out, encoder):
    def read(run, name):
        return json.loads((run / (name + ".json")).read_text())

    log = (after / "standalone.log").read_text(encoding="utf-8", errors="replace")
    fallback = [
        line
        for line in log.splitlines()
        if ("/WoodlandHabitats/" in line or "/M_BendMossLedges." in line)
        and ("Failed to compile Material" in line or "Default Material will be used" in line)
    ]
    if fallback:
        raise ValueError("Game used a fallback material: " + fallback[0])
    assert read(before, "drive")["source_sha256"] == read(after, "drive")["source_sha256"]
    poses = read(before, "camera-poses")
    assert poses == read(after, "camera-poses") and len(poses) > 30
    motion = read(before, "motion")
    assert motion == read(after, "motion")
    out.mkdir(parents=True, exist_ok=True)

    def pair(name, caption, width):
        return panel(
            [p / (name + ".png") for p in (before, after)],
            caption,
            width,
            ("Previous woodland", "Habitat rules"),
        )

    def shot(station):
        i, s = min(motion, key=lambda row: abs(station - row[1]))
        return f"motion-{i:03}", f"Forest access | {s:.0f} m"

    fixed = [Image.open(p / "bush-interior.png").convert("RGB") for p in (before, after)]
    assert all(img.size == (1600, 900) for img in fixed)
    details = []
    font = ImageFont.truetype("segoeui.ttf", 19)
    for box, caption in [
        ((0, 495, 810, 900), "Shaded litter, moss and fronds"),
        ((790, 312, 1600, 717), "Stone ledges and undergrowth"),
    ]:
        row = Image.new("RGB", (1440, 398), "#212723")
        draw = ImageDraw.Draw(row)
        for i, (im, version) in enumerate(zip(fixed, ["Before", "After"])):
            row.paste(im.crop(box).resize((720, 360), Image.Resampling.LANCZOS), (i * 720, 38))
            draw.text((i * 720 + 11, 5), version + "   /   " + caption, fill="white", font=font)
        details.append(row)
    sheet(details, out / "forest-floor-detail.jpg")
    sheet([pair("bush-interior", "Riverside access", 800)], out / "forest-floor-wide.jpg")

    sheet(
        [
            pair(*shot(30), 580),
            pair("water", "Opposite riverbank", 580),
            pair("bush-interior", "Riverside access | inland forest floor", 580),
        ],
        out / "comparison.jpg",
    )
    sheet(
        [
            pair(name, label, 800)
            for name, label in [
                ("early", "Wooded approach"),
                ("verge", "River approach | near shoulder"),
                ("bush-entry", "Riverside access | looking downhill"),
                ("bush-downhill", "Riverside access | looking back"),
            ]
        ],
        out / "fixed-views.jpg",
    )
    video = out / "woodland-drive.mp4"
    w = 768
    fps = 24
    with subprocess.Popen(
        [
            str(encoder),
            "-y",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{2 * w}x472",
            "-r",
            str(fps),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(video),
        ],
        stdin=subprocess.PIPE,
    ) as writer:
        for i, s in motion:
            image = pair(f"motion-{i:03}", f"Driver-height replay | {s:.0f} m", w).tobytes()
            for _ in range(7):
                writer.stdin.write(image)
        for name, caption in [
            ("water", "Opposite riverbank"),
            ("bush-entry", "Riverside access"),
            ("bush-interior", "Inland forest floor"),
        ]:
            image = pair(name, caption, w).tobytes()
            for _ in range(36):
                writer.stdin.write(image)
        writer.stdin.close()
        if writer.wait():
            raise RuntimeError("Video encoding failed")
    (out / "comparison.json").write_text(
        json.dumps(
            dict(
                before=before.name,
                after=after.name,
                matched_route_positions=len(motion),
                other_route_views=3,
                pose_checks=True,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    for key in ("before", "after", "out", "encoder"):
        args.add_argument("--" + key, type=Path, required=True)
    r = args.parse_args()
    review(r.before, r.after, r.out, r.encoder)
