"""
Split a multi-view car blueprint into PNG crops without changing scale, and
work out where to place each crop in Blender so the views line up.

Cropping never resamples pixels, so every crop keeps the source image's
pixels-per-millimetre. Scale is preserved as long as you never resize a crop.

Usage:
    python split_blueprint.py <blueprint image> <config.json>

Config JSON (see the *.json files next to this script):
    ref_px, ref_mm   a measured dimension line in pixels and its real length
    views: { name: { box, anchor, kind } }
        box     (left, top, right, bottom) crop in source pixels
        anchor  (x, y) source pixel that lands on the origin lines:
                car centreline horizontally, ground line vertically
                (top view: wheelbase centre x, car centreline y)
        kind    one of front, rear, side_left, side_right, top

Blender convention: car nose points to -Y, Z up, ground at Z=0.
    Numpad 1 front, Ctrl+Numpad 1 rear, Numpad 3 left side, Ctrl+Numpad 3 right side, Numpad 7 top.
"""
import json
import sys
from pathlib import Path

from PIL import Image

# kind -> (XYZ Euler degrees, push away from origin, location rule)
# location rule maps (dx, dy) = anchor offset from crop centre in px (image y down)
# to the empty's world location so the anchor sits on the origin lines.
KINDS = {
    "front":      dict(rot=(90, 0, 0),    push=(0, -3.0, 0),  loc=lambda dx, dy, m: (-dx * m, 0.0, dy * m)),
    "rear":       dict(rot=(90, 0, 180),  push=(0, 3.0, 0),   loc=lambda dx, dy, m: (dx * m, 0.0, dy * m)),
    "side_left":  dict(rot=(90, 0, 90),   push=(1.5, 0, 0),   loc=lambda dx, dy, m: (0.0, -dx * m, dy * m)),
    "side_right": dict(rot=(90, 0, -90),  push=(-1.5, 0, 0),  loc=lambda dx, dy, m: (0.0, dx * m, dy * m)),
    "top":        dict(rot=(0, 0, 90),    push=(0, 0, -1.2),  loc=lambda dx, dy, m: (-dy * m, -dx * m, 0.0)),
}


def main(src: str, cfg_path: str) -> None:
    src_path = Path(src)
    cfg = json.loads(Path(cfg_path).read_text())
    img = Image.open(src_path)
    out_dir = src_path.parent / (src_path.stem + "_views")
    out_dir.mkdir(exist_ok=True)

    m_per_px = (cfg["ref_mm"] / cfg["ref_px"]) / 1000.0
    data = {"name": cfg.get("name", src_path.stem), "m_per_px": m_per_px, "views": {}}

    for name, v in cfg["views"].items():
        kind = KINDS[v["kind"]]
        l, t, r, b = v["box"]
        crop = img.crop((l, t, r, b))
        out = out_dir / f"{name}.png"
        crop.save(out)                                  # PNG = lossless, no resampling
        w, h = crop.size
        size_m = max(w, h) * m_per_px                   # Blender: larger side == Size
        dx, dy = v["anchor"][0] - (l + w / 2.0), v["anchor"][1] - (t + h / 2.0)
        loc = kind["loc"](dx, dy, m_per_px)
        loc = tuple(round(a + p, 5) for a, p in zip(loc, kind["push"]))
        data["views"][name] = {
            "file": str(out.resolve()), "px": [w, h],
            "size_m": round(size_m, 5), "rotation_deg": kind["rot"], "location": loc,
        }
        print(f"{name:10s} {w:4d}x{h:<4d} px  Size={size_m:.4f} m  loc={loc}")

    (out_dir / "blender_sizes.json").write_text(json.dumps(data, indent=2))
    print(f"\nScale: {1000 * m_per_px:.3f} mm per pixel")
    print(f"Wrote crops + blender_sizes.json to {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("usage: python split_blueprint.py <blueprint image> <config.json>")
    main(sys.argv[1], sys.argv[2])
