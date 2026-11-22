"""Bake disconnected erosion faces along a dry bank. All input coordinates are metres."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

from bake_riverbank_relief import smooth


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


class Ground:
    def __init__(self, args):
        meta = read(args.grid)
        self.origin = np.asarray(meta["origin_m"])
        self.cell = meta["cell_m"]
        wet = np.asarray(Image.open(args.wet).convert("L")) > 0
        protected = np.asarray(Image.open(args.protected).convert("L")) > 0
        if (wet.shape != protected.shape or not wet.any() or self.cell <= 0 or meta["unit_m"] <= 0
                or not np.isfinite([*self.origin, self.cell, meta["unit_m"], meta["zero_m"]]).all()):
            raise ValueError("Supply matching wet and protection masks and a positive grid size")
        raw = np.fromfile(args.terrain, "<u2").reshape(wet.shape)
        self.height = raw * meta["unit_m"] + meta["zero_m"]
        self.shore = distance_transform_edt(~wet) * self.cell
        self.excluded = wet | protected
        self.rise_y, self.rise_x = np.gradient(self.height, self.cell)

    def sample(self, field, xy):
        # Match the native diagonal in each landscape quad.
        f = (np.asarray(xy) - self.origin) / self.cell
        ix, iy = np.floor(f).astype(int).T
        if np.any(ix < 0) or np.any(iy < 0) or np.any(ix >= field.shape[1]-1) or np.any(iy >= field.shape[0]-1):
            raise ValueError("Sample outside landscape")
        a, b = (f - np.floor(f)).T
        z00, z10 = field[iy, ix], field[iy, ix+1]
        z01, z11 = field[iy+1, ix], field[iy+1, ix+1]
        return np.where(a >= b, z00 + a*(z10-z00) + b*(z11-z10), z00 + a*(z11-z01) + b*(z01-z00))


def candidates(ground, course, limits, trunks, seed):
    lengths = np.linalg.norm(np.diff(course[:, :2], axis=0), axis=1)
    stations = np.r_[0, np.cumsum(lengths)]
    if np.any(lengths <= 0) or not 0 <= limits[0] < limits[1] <= stations[-1]:
        raise ValueError("Supply a non-degenerate course and a reach within its length")
    # Dense centreline samples also support sparsely surveyed bends.
    chain = np.linspace(0, stations[-1], int(np.ceil(stations[-1])) + 1)
    guide = np.column_stack([np.interp(chain, stations, c) for c in course.T])
    rows, cols = np.nonzero((ground.shore > 2.2) & (ground.shore < 11) & (~ground.excluded))
    coords = ground.origin + np.column_stack((cols, rows)) * ground.cell
    _, nearest = cKDTree(guide[:, :2]).query(coords)
    options = []
    for i in np.flatnonzero((chain[nearest] >= limits[0]) & (chain[nearest] <= limits[1])):
        site, row, col, k = coords[i], rows[i], cols[i], nearest[i]
        rise = np.array([ground.rise_x[row, col], ground.rise_y[row, col]])
        slope = np.linalg.norm(rise)
        if not .22 < slope < 1.12 or not .45 < ground.height[row, col] - guide[k, 2] < 5.7:
            continue
        land = rise / slope
        radial = site - guide[k, :2]
        if np.dot(land, radial) < .66 * np.linalg.norm(radial):
            continue
        if trunks is not None and trunks.query(site)[0] < 1.25:
            continue
        along = np.array([land[1], -land[0]])
        random = np.random.default_rng([seed, row, col])
        span, depth = random.uniform([9.5, 2.35], [16., 3.6])
        rank = .54 * random.random() + .22 * min(.85, slope) - .23 * ground.shore[row, col]
        for scale in (1., .78, .57):
            width, deep = span * scale, depth * scale**.5
            # Pad the enclosing rectangle for all cross-section bends. The
            # probes below also cover the spaces between adjacent lines.
            s, d = np.meshgrid(np.linspace(-width/2, width/2, int(np.ceil(width/.55))+1),
                               np.arange(-deep, 1.5*deep+.51, .5))
            footprint = site + s.flatten()[:, None]*along + d.flatten()[:, None]*land
            fractional = (footprint - ground.origin) / ground.cell
            if np.any(fractional < 0) or np.any(fractional >= np.array(ground.height.shape[::-1])-1):
                continue
            # Every landscape quad in the footprint must be dry and unprotected.
            # Include a quarter-metre margin for the space between probe lines.
            grid_xy = (np.vstack([footprint+[dx,dy] for dx in (-.27,.27)
                                   for dy in (-.27,.27)]) - ground.origin) / ground.cell
            cells = np.floor(grid_xy).astype(int)
            if (cells.min() < 0 or np.any(cells.max(axis=0)+1 >= ground.excluded.shape[::-1])
                    or any(ground.excluded[cells[:,1]+dy, cells[:,0]+dx].any()
                           for dx in (0,1) for dy in (0,1))):
                continue
            options.append((rank + .24*scale, row, col, site, along, land, width, deep, chain[k]))
            break
    # Resolve spacing once over the managed reach, before splitting into render tiles.
    placed = []
    neighbours = defaultdict(list)
    cell_size = max((item[6] for item in options), default=0.) * 1.02 + 1.4
    for item in sorted(options, key=lambda x: (-x[0], x[1], x[2])):
        x, y = np.floor(item[3] / cell_size).astype(int)
        nearby = (p for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  for p in neighbours.get((x+dx, y+dy), ()))
        if all(np.linalg.norm(item[3]-p[3]) > .51*(item[6]+p[6]) + 1.4 for p in nearby):
            placed.append(item)
            neighbours[x, y].append(item)
    return sorted(placed, key=lambda x: x[-1])


# Offset into the slope, fraction of the local cut filled, and linear pigment.
# The undercut doubles back beneath a slightly protruding, darker organic layer.
PROFILE = (
    (-.82, -.2, (.072,.058,.042)), (-.45, .01, (.093,.073,.047)),
    (-.23, .13, (.082,.061,.042)), (-.12, .29, (.086,.068,.049)),
    (-.09, .47, (.080,.054,.039)), (-.10, .57, (.106,.076,.051)),
    (-.07, .74, (.087,.072,.049)), (-.045, .85, (.065,.046,.034)),
    (-.075, .93, (.056,.045,.033)), (-.06, 1., (.066,.062,.040)),
    (.08, 1., (.072,.065,.042)), (.52, 1., (.079,.073,.042)),
    (.91, .73, (.072,.068,.040)), (1.22, -.24, (.075,.069,.042)),
)


def build_face(item, ground, trunks, seed):
    _, row, col, site, along, land, width, depth, station = item
    rng = np.random.default_rng([seed, row, col, 19])
    phases = rng.uniform(0, 2*np.pi, 4)
    center_z = float(ground.sample(ground.height, site))
    vertices, colours, uv, triangles = [], [], [], []
    slices = int(np.ceil(width/.43)) + 1
    for i, t in enumerate(np.linspace(0, 1, slices)):
        side = (t-.5) * width
        ends = float(smooth(0, .19, min(t, 1-t)))
        bow = .13*np.sin(6.2*t+phases[0]) + .08*np.sin(15*t+phases[1]) + .065*np.sin(27*t+phases[3])
        shoulder = .89 + .18*np.sin(8*t+phases[2]) + .09*np.sin(19*t+phases[3])
        base_xy = site + along * side
        # Carry the uphill elevation forward over falling ground. The back of
        # the shelf rejoins the original hillside rather than forming a mound.
        top = float(ground.sample(ground.height, base_xy + land*depth*shoulder)) + .09
        for j, (offset, fraction, pigment) in enumerate(PROFILE):
            d = depth*(offset + bow) + .06*np.sin(i*1.1+j*.62+phases[0])
            xy = base_xy + land*d
            floor = float(ground.sample(ground.height, xy))
            rise = min(1.48, max(0., top-floor))
            clearance = float(smooth(.48, 1.35, trunks.query(xy)[0])) if trunks is not None else 1.
            slump = .48 + .48*smooth(-.72,.5,np.sin(side*1.05+phases[2]) + .5*np.sin(side*2.2+phases[3]))
            taper = ends*clearance*slump
            dz = fraction*rise*taper - .24*(1.-taper)
            if j in (0,len(PROFILE)-1):
                dz = -.24
            colour = np.array(pigment) * (.91 + .12*np.sin(side*.91+phases[0]) + .07*rng.random())
            vertices.append([*map(float, xy-site), floor + dz - center_z])
            colours.append(colour.tolist())
            uv.append([side/2.1, (d+dz)/2.1])
        if i:
            for j in range(len(PROFILE)-1):
                a = (i-1)*len(PROFILE)+j
                b = a+len(PROFILE)
                triangles.extend([[a,a+1,b], [a+1,b+1,b]])
    add_gravel(vertices, colours, uv, triangles, site, along, land, width, depth, center_z, ground, trunks, rng)
    return dict(station=station, origin=[*site,center_z], width=width, v=vertices, c=colours, uv=uv, t=triangles)


def add_gravel(vertices, colours, uv, triangles, site, along, land, width, depth, center_z, ground, trunks, rng):
    # Loose gravel collects where the bank has slumped. Rocks intersect the
    # local terrain on all sides and share the cut's material and draw batch.
    pocket = rng.uniform(-.21, .21) * width
    for _ in range(round(width * 1.6)):
        s = np.clip(pocket+rng.normal(0, width*.22), -width*.43, width*.43)
        d = -depth*rng.uniform(.30,.63)
        xy = site + along*s + land*d
        radius = min(width*.055, depth*.18, rng.uniform(.14,.56))
        if trunks is not None and trunks.query(xy)[0] < radius+.48:
            continue
        aspect = rng.uniform(.55,.91)
        orientation = rng.uniform(0.,2*np.pi)
        base = float(ground.sample(ground.height,xy))
        crown = radius*rng.uniform(.46,.9)
        rock_colour = np.array([.093,.096,.085])*rng.uniform(.70,1.08)
        rings = []
        count = 7
        shape = rng.uniform(.85,1.12,count)
        for scale, height in ((1.,-.32),(.97,.18),(.64,.81)):
            ring = []
            for k in range(count):
                angle = 2*np.pi*k/count+orientation
                delta = radius*shape[k]*(along*np.cos(angle)+land*np.sin(angle)*aspect)
                at = xy+scale*delta
                ground_z = float(ground.sample(ground.height,at))
                z = ground_z-.24 if height<0 else .5*(base+ground_z)+crown*height
                ring.append(len(vertices))
                vertices.append([*map(float,at-site), z-center_z])
                colours.append((rock_colour*(.90+.11*height+.10*rng.random())).tolist())
                uv.append([float(at[0]-site[0])/1.1,float(at[1]-site[1])/1.1])
            rings.append(ring)
        top = len(vertices)
        vertices.append([*map(float,xy-site),base+crown-center_z])
        colours.append(rock_colour.tolist())
        uv.append([float(xy[0]-site[0])/1.1,float(xy[1]-site[1])/1.1])
        for k in range(count):
            nxt = (k+1)%count
            for lo,hi in zip(rings,rings[1:]):
                triangles.extend([[lo[k],hi[k],lo[nxt]],[lo[nxt],hi[k],hi[nxt]]])
            triangles.append([rings[-1][nxt],rings[-1][k],top])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("terrain","grid","wet","protected","course","output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--trunks", type=Path, help="XY trunk positions in metres, over the whole reach")
    parser.add_argument("--reach", type=float, nargs=2, required=True, metavar=("START","END"))
    parser.add_argument("--seed", type=int, default=7126)
    args = parser.parse_args()
    ground = Ground(args)
    course = np.asarray(read(args.course), dtype=float)
    if course.ndim != 2 or course.shape[1] != 3 or len(course) < 2 or not np.isfinite(course).all():
        raise ValueError("Supply a finite ordered XYZ river course in metres")
    points = np.asarray(read(args.trunks) if args.trunks else [], dtype=float)
    if points.size and (points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all()):
        raise ValueError("Supply finite XY trunk positions in metres")
    trunks = cKDTree(points) if points.size else None
    sections = [build_face(item, ground, trunks, args.seed)
                for item in candidates(ground, course, args.reach, trunks, args.seed)]
    with NamedTemporaryFile(dir=args.output.parent, delete=False, suffix=".tmp") as handle:
        temporary = Path(handle.name)
    try:
        temporary.write_text(json.dumps(dict(reach=args.reach, sections=sections), separators=(",",":")))
        temporary.replace(args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(len(sections), "faces,", sum(len(s["t"]) for s in sections), "triangles")


if __name__ == "__main__":
    main()
