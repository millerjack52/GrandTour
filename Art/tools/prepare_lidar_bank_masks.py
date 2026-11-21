"""Make river and keep-out masks for bake_riverbank_relief from a LiDAR Place bake."""

import argparse
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def prepare(place, survey, output, grid):
    size = 2017
    cell = grid["cell_m"]
    origin = np.array(grid["origin_m"])
    wet = np.zeros((size, size), dtype=bool)
    keep = Image.new("L", (size, size))
    draw = ImageDraw.Draw(keep)

    def pixel(xy):
        return tuple(np.rint((np.array(xy) - origin) / cell).astype(int))

    def box(bounds):
        draw.rectangle([pixel(bounds[:2]), pixel(bounds[2:])], fill=255)

    for x, y, span in survey["tiles"]:
        box([x, y, x + span, y + span])
    for bounds in survey["fitted"] + survey["water"]:
        box(bounds)
    # Include the attached gravel point and the whole projected road corridor.
    settings = Path(__file__).resolve().parents[1] / "LidarAuthoring/river_banks.json"
    for bank in json.loads(settings.read_text())["banks"]:
        draw.polygon([pixel(v) for v in bank["attachment_polygon_m"]], fill=255)
    for road in json.loads((place / "roads.json").read_text()):
        widths = road.get("widths_cm", [])
        width = max([8.] + [v / 100 for v in widths]) + 4.
        draw.line([pixel(np.array(p[:2]) / 100) for p in road["points"]],
                  fill=255, width=int(np.ceil(width / cell)) + 1)
    # Mark all vertices neighbouring a wet domain sample. Combined with the
    # triangle guard in the bake, this also protects quads crossed by the shore.
    data = (place / "River-domain.bin").read_bytes()
    magic, nx, ny, _, _, x, y, step = struct.unpack_from("<5i3f", data)
    if magic != 0x47545744 or len(data) != 33 + nx * ny * 16:
        raise ValueError("Invalid LiDAR water domain")
    grid_data = np.frombuffer(data, "<f4", count=nx * ny * 4, offset=32).reshape(ny, nx, 4)
    j, i = np.nonzero(grid_data[:, :, 1] > 0)
    for offset_x in [0., 1.]:
        for offset_y in [0., 1.]:
            col = ((x + (i + offset_x) * step) / 100 - origin[0]) / cell
            row = ((y + (j + offset_y) * step) / 100 - origin[1]) / cell
            for xx, yy in [(np.floor(col), np.floor(row)), (np.ceil(col), np.ceil(row)),
                           (np.ceil(col), np.floor(row)), (np.floor(col), np.ceil(row))]:
                inside = (xx >= 0) & (yy >= 0) & (xx < size) & (yy < size)
                wet[yy[inside].astype(int), xx[inside].astype(int)] = True
    guide = json.loads((place / "authoring-reference.json").read_text())["river_points_cm"]
    output.mkdir(parents=True, exist_ok=True)
    Image.fromarray(wet).save(output / "river-wet.png")
    keep.save(output / "protected.png")
    (output / "course.json").write_text(json.dumps((np.array(guide) / 100).tolist()))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("place", type=Path)
    p.add_argument("survey", type=Path, help="Map survey with tile, fitted-bank and pond bounds in metres")
    p.add_argument("grid", type=Path, help="Surveyed cell_m and origin_m")
    p.add_argument("output", type=Path)
    args = p.parse_args()
    prepare(args.place, json.loads(args.survey.read_text()), args.output, json.loads(args.grid.read_text()))
