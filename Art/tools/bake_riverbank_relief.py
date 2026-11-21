"""Bake dry-bank shelves and scour into an existing metre-referenced R16 heightfield."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree


def smooth(low, high, x):
    t = np.clip((x - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def along_bank(station, spacing, rng, length):
    """Smoothly varying values indexed along the whole course, stable across crops."""
    knots = rng.uniform(-1, 1, int(np.ceil(length / spacing)) + 2)
    index = np.floor(station / spacing).astype(int)
    blend = smooth(0, 1, station / spacing - index)
    return knots[index] * (1 - blend) + knots[index + 1] * blend


def bank_delta(encoded, wet, protected, course, origin, cell, unit, zero, seed, reach=None):
    """Return signed metres at existing vertices. Masks share the heightfield grid.

    course is ordered XYZ in metres, Z being water elevation. wet includes the
    vertices of every quad intersecting this watercourse. protected covers
    roads, fitted meshes and other exclusions.
    """
    if encoded.ndim != 2 or wet.shape != encoded.shape or protected.shape != encoded.shape:
        raise ValueError("Height, water and protection rasters must share one grid")
    if not wet.any() or cell <= 0 or unit <= 0 or not np.isfinite([*origin, cell, unit, zero]).all():
        raise ValueError("Supply a wet river mask and a valid metric grid transform")
    if course.ndim != 2 or course.shape[1] != 3 or len(course) < 2 or not np.isfinite(course).all():
        raise ValueError("Supply an ordered XYZ watercourse in metres")
    lengths = np.linalg.norm(np.diff(course[:, :2], axis=0), axis=1)
    if np.any(lengths == 0):
        raise ValueError("Watercourse has consecutive coincident XY points")
    chain = np.r_[0., np.cumsum(lengths)]
    if reach is not None and not 0 <= reach[0] < reach[1] <= chain[-1]:
        raise ValueError("Reach must lie inside the supplied course")
    # Short segments keep the nearest-station lookup accurate on sparse source splines.
    samples = np.linspace(0, chain[-1], int(np.ceil(chain[-1] / min(cell, 1.))) + 1)
    guide = np.column_stack([np.interp(samples, chain, column) for column in course.T])
    tangents = np.gradient(guide[:, :2], axis=0)
    shore = distance_transform_edt(~wet) * cell
    # The wet mask already covers every vertex of a wet quad. Give the other
    # exclusions an extra cell diagonal, then feather the first editable row.
    pad = np.sqrt(2.) * cell
    clearance = distance_transform_edt(~protected) * cell if protected.any() else np.full(encoded.shape, np.inf)
    rows, cols = np.nonzero((shore > 0) & (shore < 26) & (clearance > pad))
    xy = np.column_stack([origin[0] + cols * cell, origin[1] + rows * cell])
    _, idx = cKDTree(guide[:, :2]).query(xy)
    s = samples[idx]
    vector = xy - guide[idx, :2]
    side = tangents[idx, 0] * vector[:, 1] - tangents[idx, 1] * vector[:, 0]
    above = encoded[rows, cols].astype(float) * unit + zero - guide[idx, 2]
    d = shore[rows, cols]
    # Flatten short pieces of the actual cross slope. Adding the same bump to
    # a steep face merely lifts it, leaving almost the original profile.
    bank_y, bank_x = np.gradient(gaussian_filter(shore.astype(np.float32), 1), cell)
    rise_y, rise_x = np.gradient(encoded.astype(np.float32) * unit, cell)
    inward_x, inward_y = bank_x[rows, cols], bank_y[rows, cols]
    slope = ((inward_x * rise_x[rows, cols] + inward_y * rise_y[rows, cols])
             / np.maximum(.1, np.hypot(inward_x, inward_y)))
    slope = np.clip(slope, 0., 1.2)
    weight = smooth(pad, pad + 2.5, clearance[rows, cols]) * smooth(0, 2.5, d)
    weight *= (1 - smooth(17, 26, d)) * smooth(.16, .85, above) * (1 - smooth(7, 12, above))
    if reach is not None:
        weight *= smooth(reach[0], reach[0] + 8, s) * (1 - smooth(reach[1] - 8, reach[1], s))
    # Each side has its own irregular, interrupted shelf. A shallow scoop lies
    # below its lip and a broader shoulder grades back into the original terrain.
    delta = np.zeros(encoded.shape, dtype=np.float32)
    for direction, sequence in enumerate(np.random.SeedSequence(seed).spawn(2)):
        use = (side >= 0) == bool(direction)
        rng = np.random.default_rng(sequence)
        station, inland = s[use], d[use]
        def noise(spacing):
            return along_bank(station, spacing, rng, chain[-1])
        crest = 4.8 + 2.1 * noise(17) + 1.2 * noise(7.5)
        width = 3.7 + 1.1 * noise(14)
        shelf = np.exp(-((inland - crest) / width) ** 4)
        cut = np.exp(-((inland - crest + width + 1.5) / 2.9) ** 2)
        shoulder = np.exp(-((inland - crest - 7.) / 4.8) ** 2)
        bench = np.clip((crest - inland) * slope[use], -1.05, 1.05)
        height = shelf * (.48 + .34 * noise(11) + bench) - cut * .46
        height *= .42 + .58 * smooth(-.68, .32, noise(18))
        upper_bench = np.clip((crest + 7. - inland) * slope[use], -.65, .65)
        height += shoulder * (.14 + .50 * noise(13) + upper_bench)
        # A cut on a low dry bank must stay above the local water surface.
        delta[rows[use], cols[use]] = np.maximum(height * weight[use], np.minimum(0, .16 - above[use]))
    return delta


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path, help="Original little-endian unsigned R16")
    p.add_argument("course", type=Path, help="JSON array of ordered water-surface XYZ in metres")
    p.add_argument("wet", type=Path, help="River occupancy mask, white = wet")
    p.add_argument("protected", type=Path, help="Do-not-edit mask, white = protected")
    p.add_argument("output", type=Path)
    p.add_argument("--origin", type=float, nargs=2, required=True, help="World XY of vertex [0,0], metres")
    p.add_argument("--cell", type=float, required=True, help="Square vertex spacing, metres")
    p.add_argument("--unit", type=float, required=True, help="Metres per encoded height step")
    p.add_argument("--zero", type=float, default=0., help="World elevation of code zero, metres")
    p.add_argument("--reach", type=float, nargs=2, help="Optional pilot station interval in metres")
    p.add_argument("--seed", type=int, default=711)
    args = p.parse_args()
    inputs = [args.source, args.wet, args.protected, args.course]
    if args.output.resolve() in {path.resolve() for path in inputs}:
        p.error("Choose a separate destination to preserve the source")
    wet, protected = [np.array(Image.open(path).convert("L")) > 0 for path in (args.wet, args.protected)]
    source = np.fromfile(args.source, "<u2").reshape(wet.shape)
    delta = bank_delta(source, wet, protected, np.array(json.loads(args.course.read_text())),
                       args.origin, args.cell, args.unit, args.zero, args.seed, args.reach)
    result = source.astype(np.int32) + np.rint(delta / args.unit).astype(np.int32)
    if result.min() < 0 or result.max() > 65535:
        raise ValueError("Relief would exceed the source height encoding")
    result.astype("<u2").tofile(args.output)
    print(json.dumps(dict(changed_vertices=int((result != source).sum()),
                          low_m=float(delta.min()), high_m=float(delta.max()))))


if __name__ == "__main__":
    main()
