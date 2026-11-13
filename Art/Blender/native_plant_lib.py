"""Shared primitives for the Grand Tour native plant kit (docs/NATIVE_PLANT_KIT_PLAN.md).

Blender 5.1.2, no add-ons. Ported from build_shrub_library.py (material, export, manifest,
review) and willow_reference_v5.py (Catmull-Rom curve, noisy tubes, hulls). Every primitive
writes into a Geo buffer. Nothing here draws from the caller's RNG: the only randomness is
cluster(), which runs its own random.Random(seed) on a seed the design drew once, so the LOD
rule (RNG consumed identically at every LOD) holds.
"""
import bpy, math, json, random
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Art/Export/NativePlants/v01'
KIT = 'Grand Tour Native Plants v01'
Z = Vector((0, 0, 1))
SLOT_NAMES = {0: 'Bark', 1: 'Foliage'}


# ---------------------------------------------------------------- small maths

def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smoothstep(a, b, x):
    t = clamp((x - a) / (b - a)) if b != a else (1.0 if x >= b else 0.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c0, c1, t):
    return tuple(lerp(a, b, t) for a, b in zip(c0, c1))


def scale_col(c, s):
    return tuple(min(.95, x * s) for x in c)


def hnoise(p, salt=0.0):
    """Deterministic per-position hash in [0,1). Uses no RNG and no Python hash()."""
    s = math.sin(p[0] * 12.9898 + p[1] * 78.233 + p[2] * 37.719 + salt * 3.7173) * 43758.5453
    return s - math.floor(s)


def rot(v, axis, angle):
    return Matrix.Rotation(angle, 3, Vector(axis).normalized()) @ Vector(v)


def perp(v):
    v = Vector(v).normalized()
    a = Vector((0, 0, 1)) if abs(v.z) < .9 else Vector((1, 0, 0))
    return v.cross(a).normalized()


def polar(theta_from_vertical, azimuth):
    s = math.sin(theta_from_vertical)
    return Vector((s * math.cos(azimuth), s * math.sin(azimuth), math.cos(theta_from_vertical)))


def curve(points, steps=4):
    """Catmull-Rom through the control points (willow_reference_v5.curve)."""
    p = [Vector(x) for x in points]
    if len(p) < 2:
        return p
    out = []
    for i in range(len(p) - 1):
        a, b, c, d = p[max(0, i - 1)], p[i], p[i + 1], p[min(len(p) - 1, i + 2)]
        for j in range(steps):
            t = j / steps
            out.append(.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t * t * t))
    return out + [p[-1]]


def resample(points, n):
    """n segments evenly spaced by arc length along a polyline; returns (points, fractions)."""
    p = [Vector(x) for x in points]
    acc = [0.0]
    for i in range(1, len(p)):
        acc.append(acc[-1] + (p[i] - p[i - 1]).length)
    total = acc[-1] or 1e-9
    out = []; fr = []; j = 0
    for k in range(n + 1):
        s = total * k / n
        while j < len(p) - 2 and acc[j + 1] < s:
            j += 1
        seg = (acc[j + 1] - acc[j]) or 1e-9
        out.append(p[j].lerp(p[j + 1], clamp((s - acc[j]) / seg)))
        fr.append(k / n)
    return out, fr


def along(points, t):
    """Point and tangent at arc fraction t of a polyline."""
    p = [Vector(x) for x in points]
    acc = [0.0]
    for i in range(1, len(p)):
        acc.append(acc[-1] + (p[i] - p[i - 1]).length)
    s = acc[-1] * clamp(t)
    j = 0
    while j < len(p) - 2 and acc[j + 1] < s:
        j += 1
    seg = (acc[j + 1] - acc[j]) or 1e-9
    return p[j].lerp(p[j + 1], clamp((s - acc[j]) / seg)), (p[j + 1] - p[j]).normalized()


def length(points):
    return sum((Vector(points[i + 1]) - Vector(points[i])).length for i in range(len(points) - 1))


def profile(prof, t):
    """Piecewise-linear [(t, value), ...]."""
    if t <= prof[0][0]:
        return prof[0][1]
    for (t0, v0), (t1, v1) in zip(prof, prof[1:]):
        if t <= t1:
            return lerp(v0, v1, (t - t0) / ((t1 - t0) or 1e-9))
    return prof[-1][1]


# ---------------------------------------------------------------- geometry buffer

class Geo:
    """Vertex positions, per-vertex linear colour, UV and a radial hint; faces with a semantic
    material index (0 Bark, 1 Foliage). Each element owns its vertices, so per-vertex colour is
    per-element colour where the element is flat-coloured."""

    def __init__(self):
        self.v = []; self.c = []; self.uv = []; self.r = []
        self.f = []; self.mi = []
        self.counts = dict(leaves=0, fronds=0, sprays=0, clusters=0, tubes=0)

    def add(self, verts, faces, colours, uvs, mi, radial=None):
        start = len(self.v)
        n = len(verts)
        self.v.extend(Vector(p) for p in verts)
        if colours and isinstance(colours[0], (tuple, list)) and len(colours) == n:
            self.c.extend(tuple(c) for c in colours)
        else:
            self.c.extend([tuple(colours)] * n)
        self.uv.extend(uvs if uvs else [(0, 0)] * n)
        self.r.extend(radial if radial else [Vector((0, 0, 0))] * n)
        for f in faces:
            self.f.append(tuple(start + i for i in f)); self.mi.append(mi)
        return start

    def oriented(self, verts, colours, uvs, mi, up):
        """Add one polygon whose normal is turned toward `up`."""
        a, b, c = Vector(verts[0]), Vector(verts[1]), Vector(verts[2])
        face = list(range(len(verts)))
        if (b - a).cross(c - a).dot(up) < 0:
            face.reverse()
        return self.add(verts, [face], colours, uvs, mi)


# ---------------------------------------------------------------- primitives

def tube(geo, points, radii, sides, colour, mi=0, caps=(False, True), noise=.04, phase=0.0):
    """Tube along points with parallel-transport frames, 4 % radius noise, outward faces.
    radii: one value per point. Returns (first vertex, rings)."""
    p = [Vector(q) for q in points]
    n = len(p)
    start = len(geo.v)
    verts = []; uvs = []; radial = []
    t0 = (p[1] - p[0]).normalized()
    u = perp(t0)
    dist = 0.0
    for i, q in enumerate(p):
        t = (p[min(i + 1, n - 1)] - p[max(0, i - 1)]).normalized()
        u = (u - t * u.dot(t))
        if u.length < 1e-6:
            u = perp(t)
        u.normalize()
        v = t.cross(u)
        if i:
            dist += (p[i] - p[i - 1]).length
        for j in range(sides):
            a = math.tau * j / sides
            rv = u * math.cos(a) + v * math.sin(a)
            r = radii[i] * (1 + noise * math.sin(j * 2.3 + i * 1.37 + phase))
            verts.append(q + rv * r); uvs.append((j / sides, dist)); radial.append(rv)
    faces = []
    for i in range(n - 1):
        for j in range(sides):
            a = i * sides + j; b = i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    if caps[0]:
        faces.append(tuple(reversed(range(sides))))
    if caps[1]:
        faces.append(tuple((n - 1) * sides + j for j in range(sides)))
    geo.add(verts, faces, colour, uvs, mi, radial)
    geo.counts['tubes'] += 1
    return start, n


def leaf(geo, anchor, direction, size, colour, broad=.4, roll=0.0, mi=1):
    """Folded 4-triangle leaf: base, two edge points, tip around a raised midrib point."""
    d = Vector(direction).normalized(); side = d.cross(Vector((.13, .21, 1))).normalized(); n = side.cross(d).normalized()
    side = side * math.cos(roll) + n * math.sin(roll); n = side.cross(d).normalized()
    w = size * broad * .5
    a = Vector(anchor)
    vs = [a, a + d * size * .45 - side * w, a + d * size, a + d * size * .45 + side * w, a + d * size * .45 + n * size * .07]
    geo.add(vs, [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], colour, [(0, .5), (.45, 0), (1, .5), (.45, 1), (.45, .5)], mi)
    geo.counts['leaves'] += 1


def spray(geo, anchor, direction, size, colour, up=Z, quads=3, fan=math.radians(35), width=.72, fold=.20, mi=1):
    """Small-leaf cluster: `quads` folded diamonds fanned `fan` apart around `direction`
    in the plane normal to `up` (2 triangles each). The diamonds are broad (width .72 of the
    length, widest at 55 %) so neighbours just overlap into one fan instead of a star; the two
    side diamonds are rolled opposite ways and shaded darker, so a crown of sprays reads as
    broken small-leaf texture rather than flat leaves."""
    up = Vector(up).normalized(); d0 = Vector(direction)
    d0 = (d0 - up * d0.dot(up)).normalized() if (d0 - up * d0.dot(up)).length > 1e-4 else perp(up)
    a = Vector(anchor)
    offs = [0.0] if quads == 1 else [(k - (quads - 1) / 2) * fan for k in range(quads)]
    for k, off in enumerate(offs):
        d = rot(d0, up, off)
        centre = abs(off) < 1e-6
        s = size * (1.0 if centre else .86)
        side = up.cross(d).normalized()
        dd = (d - up * (.03 if centre else .10)).normalized()
        n = up if centre else rot(up, dd, .32 if off > 0 else -.32)
        side = n.cross(dd).normalized()
        w = s * width * .5
        mid = a + dd * s * .55 - n * fold * s
        vs = [a, mid - side * w, a + dd * s, mid + side * w]
        col = colour if centre else scale_col(colour, .86)
        geo.add(vs, [(0, 1, 2), (0, 2, 3)] if (vs[1] - vs[0]).cross(vs[2] - vs[0]).dot(n) > 0 else [(0, 2, 1), (0, 3, 2)],
                col, [(0, .5), (.55, 0), (1, .5), (.55, 1)], mi)
    geo.counts['sprays'] += 1


def cluster(geo, centre, up, nquads, seed, dark, light, exposure, tint=1.0, enlarge=1.0, size=(.09, .13), spread=.06, dome=.045, mi=1):
    """Beech foliage cluster: `nquads` small square quads (9-13 cm, 2 triangles each), a near
    horizontal centre quad and the rest jittered round it (offsets up to about `spread` per
    axis, tilts 10-35 degrees, random yaw) in a slightly domed irregular blob ~30-40 cm across.
    Lower quads take `dark`, upper quads `light`, shifted by the cluster's crown `exposure`;
    per-quad tint .8-1.2. Runs its own RNG from `seed`, so every LOD draws the same quads."""
    r = random.Random(seed)
    up = Vector(up).normalized(); a = perp(up); b = up.cross(a)
    c0 = Vector(centre)
    for k in range(nquads):
        if k == 0:
            off = Vector((0, 0, 0)); tilt = math.radians(r.uniform(0, 8))
        else:
            off = a * r.uniform(-spread, spread) + b * r.uniform(-spread, spread)
            tilt = math.radians(r.uniform(10, 35))
        rr = off.length / (spread * 1.5)
        h = dome * max(0.0, 1 - rr * rr) + r.uniform(-.012, .012)
        pos = c0 + (off + up * h) * enlarge
        yaw = r.uniform(0, math.tau)
        axis = rot(a, up, r.uniform(0, math.tau))
        n = rot(up, axis, tilt)
        u = rot(rot(a, up, yaw), axis, tilt); u = (u - n * u.dot(n)).normalized(); v = n.cross(u)
        s = r.uniform(*size) * enlarge * .5
        corners = [pos + (u * cx + v * cy) * s * (1 + r.uniform(-.16, .16)) for cx, cy in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
        t = clamp(.55 * exposure + .45 * (h / dome) + r.uniform(-.15, .15))
        col = scale_col(mix(dark, light, t), r.uniform(.8, 1.2) * tint)
        geo.oriented(corners, col, [(1, 1), (0, 1), (0, 0), (1, 0)], mi, n)
    geo.counts['clusters'] += 1


def strip(geo, centre, half_l, half_r, side, up, colour, mi=1, rise=0.0, tip=True, colours=None):
    """Ribbon through centre points. side/up: per-section vectors. half_l/half_r: half widths.
    rise > 0 lifts the edges along up (a V fold, 3 vertices per section, 4 triangles per
    segment); rise == 0 gives a flat 2-vertex ribbon. With tip=True the last section is one
    point (no zero-area quad)."""
    n = len(centre)
    folded = abs(rise) > 1e-6
    verts = []; uvs = []; cols = []; faces = []
    rows = []
    for j in range(n):
        c = Vector(centre[j]); s = Vector(side[j]); u = Vector(up[j]); col = colours[j] if colours else colour
        last = tip and j == n - 1
        if last:
            rows.append([len(verts)]); verts.append(c); uvs.append((.5, j / (n - 1))); cols.append(col)
            continue
        l = c + s * half_l[j] + u * half_l[j] * rise
        r = c - s * half_r[j] + u * half_r[j] * rise
        if folded:
            rows.append([len(verts), len(verts) + 1, len(verts) + 2]); verts += [l, c, r]; uvs += [(0, j / (n - 1)), (.5, j / (n - 1)), (1, j / (n - 1))]; cols += [col] * 3
        else:
            rows.append([len(verts), len(verts) + 1]); verts += [l, r]; uvs += [(0, j / (n - 1)), (1, j / (n - 1))]; cols += [col] * 2
    for j in range(n - 1):
        A = rows[j]; B = rows[j + 1]
        if len(B) == 1:
            for k in range(len(A) - 1):
                faces.append((A[k], A[k + 1], B[0]))
        else:
            for k in range(len(A) - 1):
                faces.append((A[k], A[k + 1], B[k + 1], B[k]))
    # orient toward up of the first section
    if faces:
        f0 = faces[0]
        a, b, c = verts[f0[0]], verts[f0[1]], verts[f0[2]]
        if (b - a).cross(c - a).dot(Vector(up[0])) < 0:
            faces = [tuple(reversed(f)) for f in faces]
    geo.add(verts, faces, cols, uvs, mi)


def pinna_taper(u, base=.5, tip=.25):
    """Pinna length along the lamina: `base` at the base, 100 % at 40 %, `tip` at the tip
    (plan default 50 % / 25 %)."""
    return base + (1 - base) * u / .4 if u < .4 else 1 - (1 - tip) * (u - .4) / .6


def frond_path(anchor, direction, length, droop, segs=8, power=2.0, curl=0.0, roll=0.0, floor=None):
    """Rachis that rises along `direction` and arches by `droop` (radians of elevation lost by
    the tip). Returns points, tangents, side and up vectors per section."""
    d = Vector(direction).normalized()
    h = Vector((d.x, d.y, 0))
    h = h.normalized() if h.length > 1e-5 else Vector((1, 0, 0))
    side0 = Vector((-h.y, h.x, 0))
    e0 = math.asin(clamp(d.z, -1, 1))
    sub = 6
    pts = [Vector(anchor)]; tans = []; p = Vector(anchor)
    total = segs * sub
    for i in range(total):
        t = (i + .5) / total
        e = e0 - droop * t ** power
        step = (h * math.cos(e) + Z * math.sin(e)) * (length / total)
        step += side0 * (curl * 2 * t * length / total)
        p = p + step
        if floor is not None and p.z < floor:
            p.z = floor
        if (i + 1) % sub == 0:
            pts.append(p.copy())
    for j in range(len(pts)):
        tans.append((pts[min(j + 1, len(pts) - 1)] - pts[max(0, j - 1)]).normalized())
    sides = []; ups = []
    for j, t in enumerate(tans):
        s = side0 - t * side0.dot(t)
        s = rot(s.normalized(), t, roll * j / segs)
        sides.append(s); ups.append(t.cross(s).normalized())
    return pts, tans, sides, ups


def frond(geo, anchor, direction, length, pairs, pinna_len, pinna_width, droop, colour, lod=0, *,
          detail=None, power=2.0, stipe=.04, forward=math.radians(24), rise=math.radians(10), roll=0.0,
          curl=0.0, rachis_w=(.004, .0015), rachis_colour=None, pinna_segs=6, pinna_droop=0.0,
          serration=.4, width_scale=1.0, floor=None, taper=(.5, .25), fold_strip=True, mi=1):
    """Pinnate fern frond. detail: 'bipinnate' (each pinna a serrated strip), 'pinnate' (each
    pinna a single quad), 'serrated' (whole frond one zigzag strip), 'plain' (one tapered strip).
    Default by lod: pinnate / serrated / plain. Rachis is an 8-segment ribbon (16 triangles)
    in the pinnate levels."""
    if detail is None:
        detail = ('pinnate', 'serrated', 'plain')[lod]
    pts, tans, sides, ups = frond_path(anchor, direction, length, droop, 8, power, curl, roll, floor)
    rc = rachis_colour or scale_col(colour, .72)
    grad = lambda t: scale_col(colour, .86 + .2 * t)

    def lamina_u(t):
        return clamp((t - stipe) / (1 - stipe))

    if detail in ('pinnate', 'bipinnate'):
        # rachis ribbon, 8 segments, flat in the frond plane
        hw = [lerp(rachis_w[0], rachis_w[1], j / 8) for j in range(9)]
        strip(geo, pts, hw, hw, sides, ups, rc, mi, 0.0, tip=False)
        npin = 2 * pairs
        for i in range(npin):
            sgn = 1 if i % 2 == 0 else -1
            t = stipe + (1 - stipe) * (i + .5 + (.25 if sgn < 0 else 0)) / (npin + .5)
            t = min(t, .985)
            a, T = along(pts, t)
            k = min(7, int(t * 8)); f = t * 8 - k
            S = sides[k].lerp(sides[k + 1], f).normalized(); U = ups[k].lerp(ups[k + 1], f).normalized()
            u = lamina_u(t)
            L = pinna_len * pinna_taper(u, *taper)
            dp = (S * sgn * math.cos(forward) + T * math.sin(forward)).normalized()
            dp = (dp + U * math.tan(rise)).normalized()
            col = grad(t)
            if detail == 'pinnate':
                wb = pinna_width * .5 * width_scale; wt = wb * .38
                vs = [a - T * wb, a + dp * L - T * wt, a + dp * L + T * wt, a + T * wb]
                geo.oriented(vs, col, [(0, 0), (1, 0), (1, 1), (0, 1)], mi, U)
            else:
                m = pinna_segs
                cen = []; hl = []; hr = []; sv = []; uv_ = []
                pside = (T - dp * T.dot(dp)).normalized()
                pup = dp.cross(pside).normalized()
                if pup.dot(U) < 0:
                    pup = -pup
                for j in range(m + 1):
                    s = j / m
                    q = a + dp * L * s - Z * pinna_droop * L * s * s
                    env = pinna_width * .5 * width_scale * (1 - .82 * s)
                    cen.append(q); sv.append(pside); uv_.append(pup)
                    hl.append(env * (1.0 if j % 2 == 0 else serration))
                    hr.append(env * (serration if j % 2 == 0 else 1.0))
                strip(geo, cen, hl, hr, sv, uv_, col, mi, 0.0, tip=True)
            geo.counts['leaves'] += 1
    else:
        # one strip for the whole frond: envelope = the pinnate outline
        env = []
        for j, t in enumerate([j / 8 for j in range(9)]):
            u = lamina_u(t)
            w = pinna_len * pinna_taper(u, *taper) * math.cos(forward) * width_scale
            if t < stipe:
                w *= .3
            env.append(w)
        cols = [grad(j / 8) for j in range(9)]
        if detail == 'serrated':
            hl = [e * (1.0 if j % 2 == 0 else serration + .05) for j, e in enumerate(env)]
            hr = [e * (serration + .05 if j % 2 == 0 else 1.0) for j, e in enumerate(env)]
            strip(geo, pts, hl, hr, sides, ups, colour, mi, math.tan(rise) if fold_strip else 0.0, tip=True, colours=cols)
        else:
            idx = [0, 2, 4, 6, 8]
            strip(geo, [pts[i] for i in idx], [env[i] * .85 for i in idx], [env[i] * .85 for i in idx],
                  [sides[i] for i in idx], [ups[i] for i in idx], colour, mi, 0.0, tip=True, colours=[cols[i] for i in idx])
    geo.counts['fronds'] += 1
    return pts


def strap(geo, anchor, direction, length, width, arch, colour, edge_colour, *, arch_dir=None, side=None, across=5, segs=7,
          fold=math.radians(12), roll=0.0, keel_colour=None, arch_start=2 / 3, arch_power=1.5, base_w=.55, mi=1):
    """Keeled leaf for flax and cabbage tree. Rises along `direction`, then arches by `arch`
    (radians) after `arch_start` of its length toward the horizontal `arch_dir`, tapering to a
    point. Cross-section: across=7 gives thin `edge_colour` margins and a thin keel line,
    across=5 gives a thin `edge_colour` line on each margin and a keel
    (two quads each side, the halves folded up by `fold` - a 12 degree keel), across=3 the plain
    keel fold (two quads across), across=2 a flat strip. `side` is the initial width direction."""
    d0 = Vector(direction).normalized()
    h = Vector((d0.x, d0.y, 0))
    h = h.normalized() if h.length > 1e-4 else perp(Z)
    ad = Vector(arch_dir) if arch_dir is not None else h
    ad = Vector((ad.x, ad.y, 0)).normalized() if Vector((ad.x, ad.y, 0)).length > 1e-4 else h
    axis = Z.cross(ad).normalized()
    s0 = Vector(side) if side is not None else Z.cross(h)
    n = segs
    sub = 4
    pts = [Vector(anchor)]; tans = []
    p = Vector(anchor)
    for i in range(n * sub):
        t = (i + .5) / (n * sub)
        f = 0.0 if t < arch_start else ((t - arch_start) / (1 - arch_start)) ** arch_power
        T = rot(d0, axis, arch * f)
        p = p + T * (length / (n * sub))
        if (i + 1) % sub == 0:
            pts.append(p.copy())
    for j in range(len(pts)):
        tans.append((pts[min(j + 1, len(pts) - 1)] - pts[max(0, j - 1)]).normalized())
    kc = keel_colour or colour
    if across == 7:
        us = [-1, -.84, -.12, 0, .12, .84, 1]; cols = [edge_colour, colour, colour, kc, colour, colour, edge_colour]
    elif across == 5:
        us = [-1, -.8, 0, .8, 1]; cols = [edge_colour, colour, kc, colour, edge_colour]
    elif across == 3:
        us = [-1, 0, 1]; ec = mix(colour, edge_colour, .3); cols = [ec, kc, ec]
    else:
        us = [-1, 1]; cols = [colour, colour]
    verts = []; vcol = []; uvs = []; rows = []; up0 = None
    for j, c in enumerate(pts):
        t = j / n
        T = tans[j]
        S = s0 - T * s0.dot(T)
        S = S.normalized() if S.length > 1e-5 else perp(T)
        S = rot(S, T, roll * t)
        N = T.cross(S)
        if up0 is None:
            up0 = N
        if j == n:
            rows.append([len(verts)]); verts.append(c); vcol.append(cols[len(cols) // 2]); uvs.append((.5, 1))
            continue
        w = width * .5 * (base_w + (1 - base_w) * smoothstep(0, .25, t)) * (1 - .9 * smoothstep(.55, 1.0, t))
        row = []
        for u, col in zip(us, cols):
            off = S * (u * w * math.cos(fold)) + N * (abs(u) * w * math.sin(fold)) if across > 2 else S * (u * w)
            row.append(len(verts)); verts.append(c + off); vcol.append(col); uvs.append(((u + 1) * .5, t))
        rows.append(row)
    faces = []
    for j in range(n):
        A = rows[j]; B = rows[j + 1]
        for k in range(len(A) - 1):
            faces.append((A[k], A[k + 1], B[0]) if len(B) == 1 else (A[k], A[k + 1], B[k + 1], B[k]))
    a, b, c = verts[faces[0][0]], verts[faces[0][1]], verts[faces[0][2]]
    if (b - a).cross(c - a).dot(up0) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    geo.add(verts, faces, vcol, uvs, mi)
    geo.counts['leaves'] += 1
    return pts


def strap_tris(across, segs):
    return (segs - 1) * (across - 1) * 2 + (across - 1)


def needles(geo, anchor, direction, length, colour, tip_colour, up=Z, fan=math.radians(28), width=.14, mi=1):
    """Kanuka needle spray: a fan of three thin quads (6 triangles), base dark, tips paler."""
    up = Vector(up).normalized(); d0 = Vector(direction).normalized()
    side0 = d0.cross(up)
    side0 = side0.normalized() if side0.length > 1e-4 else perp(d0)
    n = side0.cross(d0).normalized()
    a = Vector(anchor)
    for k in (-1, 0, 1):
        d = rot(d0, n, k * fan)
        s = n.cross(d).normalized()
        ln = length * (1.0 if k == 0 else .85)
        w = ln * width * .5
        vs = [a, a + d * ln * .5 - s * w, a + d * ln, a + d * ln * .5 + s * w]
        geo.add(vs, [(0, 1, 2), (0, 2, 3)], [colour, colour, tip_colour, colour], [(0, .5), (.5, 0), (1, .5), (.5, 1)], mi)
    geo.counts['sprays'] += 1


def ribbon(geo, a, b, w0, w1, ref, colour, mi=1):
    """Flat twig ribbon (2 triangles), the cheap twig used at LOD1/LOD2."""
    a = Vector(a); b = Vector(b); d = (b - a).normalized()
    s = d.cross(Vector(ref))
    s = s.normalized() if s.length > 1e-4 else perp(d)
    geo.add([a - s * w0, a + s * w0, b + s * w1, b - s * w1], [(0, 1, 2, 3)], colour, [(0, 0), (1, 0), (1, 1), (0, 1)], mi)


def spine(geo, base, direction, length, radius, colour, mi=0):
    """Thorn: a four-triangle cone (open square pyramid)."""
    d = Vector(direction).normalized(); u = perp(d); v = d.cross(u)
    b = Vector(base); tip = b + d * length
    ring = [b + (u * math.cos(k * math.pi / 2) + v * math.sin(k * math.pi / 2)) * radius for k in range(4)]
    geo.add(ring + [tip], [(k, (k + 1) % 4, 4) for k in range(4)], colour, [(0, 0), (1, 0), (1, 1), (0, 1), (.5, .5)], mi)


def leaflet(geo, centre, direction, length, width, normal, colour, mi=1):
    """Tiny single-quad leaf (2 triangles)."""
    d = Vector(direction).normalized(); n = Vector(normal).normalized()
    s = n.cross(d); s = s.normalized() if s.length > 1e-4 else perp(d)
    c = Vector(centre)
    vs = [c - d * length * .5, c - s * width * .5, c + d * length * .5, c + s * width * .5]
    geo.oriented(vs, colour, [(0, .5), (.5, 0), (1, .5), (.5, 1)], mi, n)
    geo.counts['leaves'] += 1


def lattice(base, direction, radius, levels, angle, step, rng, inside=None, leader_steps=0, leader_step=None,
            leader_zig=(30, 45), plane=None, stop=0.0):
    """Divaricating twig lattice, drawn at design time from the caller's RNG. Returns twigs as
    dicts (a, b, r0, r1, level). Each twig of length `step` ends in two children diverging by
    `angle` (degrees, a range) in planes that alternate by 90 degrees, radius halving per level,
    `levels` deep. With leader_steps > 0 the level-0 twig is a zigzag leader (consecutive
    segments `leader_zig` either side of `direction`) and the second child at every leader node
    starts a side lattice, so the lattice fills a whole mound. `inside(p)` prunes twigs that
    would leave the silhouette; `stop` is the chance a fine twig ends early."""
    twigs = []
    d0 = Vector(direction).normalized()
    pl = Vector(plane) if plane is not None else perp(d0)

    def grow(p, d, r, lev, pa):
        if lev >= levels:
            return
        ln = rng.uniform(*step)
        q = p + d * ln
        ok = inside is None or inside(q)
        end = rng.random()
        a1 = math.radians(rng.uniform(*angle)) * .5; a2 = math.radians(rng.uniform(*angle)) * .5
        jit_ = rng.uniform(-.25, .25)
        if not ok:
            return
        twigs.append(dict(a=p, b=q, r0=r, r1=r * .75, level=lev))
        if lev > 1 and end < stop:
            return
        pa2 = rot(pa, d, math.pi / 2 + jit_)
        ax = (pa2 - d * pa2.dot(d)).normalized()
        grow(q, rot(d, ax, a1), r * .5, lev + 1, pa2)
        grow(q, rot(d, ax, -a2), r * .5, lev + 1, pa2)

    if leader_steps:
        p = Vector(base); r = radius; pa = pl
        for k in range(leader_steps):
            sgn = 1 if k % 2 == 0 else -1
            pa = rot(pa, d0, math.pi / 2 + rng.uniform(-.3, .3))
            ax = (pa - d0 * pa.dot(d0)).normalized()
            zig = math.radians(rng.uniform(*leader_zig))
            d = rot(d0, ax, sgn * zig)
            ln = rng.uniform(*(leader_step or step))
            q = p + d * ln
            if inside is not None and not inside(q):
                # try the other side of the zigzag once before the leader stops
                sgn = -sgn; d = rot(d0, ax, sgn * zig); q = p + d * ln
                if not inside(q):
                    break
            r1 = r * .9
            twigs.append(dict(a=p, b=q, r0=r, r1=r1, level=0))
            side = rot(d0, ax, -sgn * math.radians(rng.uniform(*angle)) * .5)
            grow(q, side, r1 * .5, 1, pa)
            p = q; r = r1
    else:
        grow(Vector(base), d0, radius, 0, pl)
    return twigs


# ---------------------------------------------------------------- bark colour

_DIRS = [Vector(d).normalized() for d in [(.62, .31, .72), (-.45, .79, .41), (.27, -.58, -.77), (.83, .12, -.55)]]


def vnoise(p, scale, salt=0.0):
    """Smooth 3D value noise in [0,1) at the given feature scale (metres)."""
    x, y, z = p[0] / scale, p[1] / scale, p[2] / scale
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)

    def h(a, b, c):
        return hnoise((ix + a, iy + b, iz + c), salt)
    x00 = lerp(h(0, 0, 0), h(1, 0, 0), fx); x10 = lerp(h(0, 1, 0), h(1, 1, 0), fx)
    x01 = lerp(h(0, 0, 1), h(1, 0, 1), fx); x11 = lerp(h(0, 1, 1), h(1, 1, 1), fx)
    return lerp(lerp(x00, x10, fy), lerp(x01, x11, fy), fz)


def _field(p, r, k, salt, warp=1.4, inflate=1.3):
    q = p + r * inflate
    ph = [hnoise((salt, 1, 2)) * math.tau, hnoise((salt, 3, 4)) * math.tau, hnoise((salt, 5, 6)) * math.tau, hnoise((salt, 7, 8)) * math.tau]
    w = math.sin(q.dot(_DIRS[3]) * k * .61 + ph[3])
    return (math.sin(q.dot(_DIRS[0]) * k + ph[0] + warp * w)
            + .75 * math.sin(q.dot(_DIRS[1]) * k * 1.618 + ph[1])
            + .55 * math.sin(q.dot(_DIRS[2]) * k * 2.414 + ph[2] + .9 * w))


def bark_paint(geo, indices, base, patches, jitter=.12, mottle=0.0, mottle_scale=.15):
    """Per-vertex bark colour: base, then for each patch irregular low-frequency blotches
    (three incommensurate, domain-warped sines of the position plus per-vertex noise,
    thresholded to the requested coverage of the vertices inside the height band), biased to
    one side and toward one end of the band. Never stripes or rings: the field mixes oblique
    directions and the circumferential position."""
    idx = list(indices)
    cols = {i: Vector(base) for i in idx}
    for pi, pt in enumerate(patches):
        z0, z1 = pt.get('band', (-1e9, 1e9)); soft = pt.get('soft', .8)
        k = pt.get('freq', 2.4); amp = pt.get('noise', .35); salt = pt.get('seed', 11 + pi * 7); infl = pt.get('inflate', 1.3)
        en = pt.get('edge_noise', 0.0); es = pt.get('edge_scale', .11); zs = pt.get('zstretch', 1.0)
        side = Vector((pt['side'][0], pt['side'][1], 0)).normalized() if pt.get('side') is not None else None
        sb = pt.get('side_bias', .8); hb = pt.get('height_bias', 0.0)
        vals = []
        for i in idx:
            p = geo.v[i]; r = geo.r[i]
            bw = smoothstep(z0 - soft, z0, p.z) * (1 - smoothstep(z1, z1 + soft, p.z))
            if bw <= 0:
                continue
            q = Vector((p.x, p.y, p.z * zs)) if zs != 1.0 else p
            f = _field(q, r, k, salt, inflate=infl) + amp * (hnoise(p, salt) - .5) * 2
            if en:
                # a finer noise breaks the blotch edges up
                f += en * (2 * vnoise(p, es, salt + 3.0) - 1)
            if side is not None:
                rh = Vector((r.x, r.y, 0))
                f += sb * (rh.dot(side) if rh.length > 1e-6 else 0)
            if hb and z1 > z0:
                f += hb * (1 - clamp((p.z - z0) / (z1 - z0)))
            vals.append((i, f, bw))
        inside = sorted(f for i, f, bw in vals if bw > .5)
        if not inside:
            continue
        thr = inside[min(len(inside) - 1, int((1 - pt['coverage']) * len(inside)))]
        pc = Vector(pt['colour'])
        for i, f, bw in vals:
            m = smoothstep(thr - .06, thr + .06, f) * bw
            if m > 0:
                cols[i] = cols[i].lerp(pc, m)
    for i in idx:
        # fine mottle: value noise at ~15 cm plus a per-vertex share, +-mottle in brightness
        j = 1 - jitter + 2 * jitter * hnoise(geo.v[i], 91.0)
        if mottle:
            j = 1 + mottle * ((2 * vnoise(geo.v[i], mottle_scale, 57.0) - 1) * .7 + (2 * hnoise(geo.v[i], 23.0) - 1) * .3)
        geo.c[i] = tuple(min(.95, x * j) for x in cols[i])


# ---------------------------------------------------------------- mesh object

def material(name, colour, vertex=True):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*colour, 1); m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*colour, 1)
    p.inputs['Roughness'].default_value = .87; p.inputs['Specular IOR Level'].default_value = .19
    if vertex and not any(n.type == 'VERTEX_COLOR' for n in m.node_tree.nodes):
        v = m.node_tree.nodes.new('ShaderNodeVertexColor'); v.layer_name = 'Color'
        m.node_tree.links.new(v.outputs['Color'], p.inputs['Base Color'])
    m.use_backface_culling = False
    return m


def plant_materials():
    return {0: material('M_NZ_Bark', (.10, .085, .07)), 1: material('M_NZ_Foliage', (.12, .26, .07))}


def to_object(geo, name, mats, slots, collection=None):
    """Write the Geo into a mesh object: per-face material index mapped onto `slots`
    (list of semantic indices, e.g. [0, 1] or [1]), UVMap and linear FLOAT_COLOR corner
    attribute `Color`. Faces whose triangulation is zero-area are dropped (counted)."""
    verts = [tuple(v) for v in geo.v]
    faces = list(geo.f); mis = list(geo.mi)
    dropped = 0
    for attempt in range(3):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(verts, [], faces)
        mesh.update(); mesh.calc_loop_triangles()
        co = [v.co.copy() for v in mesh.vertices]
        bad = set()
        for t in mesh.loop_triangles:
            a, b, c = (co[i] for i in t.vertices)
            if (b - a).cross(c - a).length < 2e-10:
                bad.add(t.polygon_index)
        if not bad:
            break
        assert attempt < 2, (name, 'degenerate faces persist')
        dropped += len(bad)
        faces = [f for i, f in enumerate(faces) if i not in bad]; mis = [m for i, m in enumerate(mis) if i not in bad]
        bpy.data.meshes.remove(mesh)
    for s in slots:
        mesh.materials.append(mats[s])
    slot_of = {s: k for k, s in enumerate(slots)}
    assert all(m in slot_of for m in mis), (name, 'face material not in slots', set(mis), slots)
    mesh.polygons.foreach_set('material_index', [slot_of[m] for m in mis])
    mesh.polygons.foreach_set('use_smooth', [m == 0 for m in mis])
    vi = [0] * len(mesh.loops); mesh.loops.foreach_get('vertex_index', vi)
    uvl = mesh.uv_layers.new(name='UVMap')
    flat = []
    for i in vi:
        flat.extend(geo.uv[i])
    uvl.data.foreach_set('uv', flat)
    col = mesh.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='CORNER')
    alpha = getattr(geo, 'a', None)    # GP1: an optional per-vertex alpha list parallel to geo.v (grass wind weight); plain Geo writes 1.0 as before
    assert alpha is None or len(alpha) == len(geo.v), (name, 'alpha list does not match the vertices')
    flat = []
    for i in vi:
        c = geo.c[i]; flat.extend((c[0], c[1], c[2], 1.0 if alpha is None else alpha[i]))
    col.data.foreach_set('color', flat)
    mesh.color_attributes.active_color = col
    mesh.update(); mesh.calc_loop_triangles()
    ob = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(ob)
    assert all(math.isfinite(x) for v in mesh.vertices for x in v.co), name
    return ob, dropped


def hulls(name, trunk_points, radius_at, count, z_max, collection=None, sides=8):
    """`count` convex 8-sided prisms over the trunk below z_max, hidden, named
    UCX_<name>_NN (the render mesh object name inside the FBX)."""
    pts = [Vector(p) for p in trunk_points]
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + (pts[i] - pts[i - 1]).length)
    # arc length where z first reaches z_max
    s_max = acc[-1]
    for i in range(1, len(pts)):
        if pts[i].z >= z_max:
            f = (z_max - pts[i - 1].z) / ((pts[i].z - pts[i - 1].z) or 1e-9)
            s_max = acc[i - 1] + f * (acc[i] - acc[i - 1]); break
    total = acc[-1]
    obs = []
    for h in range(count):
        t0 = s_max * h / count / total; t1 = s_max * (h + 1) / count / total
        a, _ = along(pts, t0); b, _ = along(pts, t1)
        axis = (b - a).normalized()
        # radius covers the trunk plus the centre-line's departure from the straight prism
        r = 0.0
        for k in range(9):
            t = lerp(t0, t1, k / 8); p, _ = along(pts, t)
            off = (p - a) - axis * (p - a).dot(axis)
            r = max(r, radius_at(t) + off.length)
        r *= 1.03
        u = perp(axis); v = axis.cross(u)
        verts = [c + r * (u * math.cos(math.tau * j / sides) + v * math.sin(math.tau * j / sides)) for c in (a, b) for j in range(sides)]
        faces = [tuple(reversed(range(sides))), tuple(range(sides, 2 * sides))] + [(j, (j + 1) % sides, sides + (j + 1) % sides, sides + j) for j in range(sides)]
        me = bpy.data.meshes.new('UCX_%s_%02d' % (name, h)); me.from_pydata([tuple(x) for x in verts], [], faces); me.update()
        ob = bpy.data.objects.new('UCX_%s_%02d' % (name, h), me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        ob.hide_render = True; ob.hide_set(True)
        obs.append(ob)
    return obs


# ---------------------------------------------------------------- export and manifest

def export(ob, hull_obs=(), out=OUT):
    """GLB in metres (render mesh only), then FBX in centimetres exactly as
    build_shrub_library.export, with the UCX hulls selected alongside the mesh."""
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    bpy.ops.object.select_all(action='DESELECT'); ob.hide_set(False); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    scene.unit_settings.scale_length = 1
    bpy.ops.export_scene.gltf(filepath=str(out / (ob.name + '.glb')), export_format='GLB', use_selection=True, export_materials='EXPORT')
    for h in hull_obs:
        h.hide_set(False); h.select_set(True)
    group = [ob] + list(hull_obs)
    for o in group:
        for v in o.data.vertices:
            v.co *= 100
    scene.unit_settings.scale_length = .01
    bpy.ops.export_scene.fbx(filepath=str(out / (ob.name + '.fbx')), use_selection=True, object_types={'MESH'}, axis_forward='-Z', axis_up='Y',
                             global_scale=1, apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', mesh_smooth_type='FACE',
                             colors_type='LINEAR', bake_anim=False)
    for o in group:
        for v in o.data.vertices:
            v.co /= 100
    scene.unit_settings.scale_length = 1
    for h in hull_obs:
        h.select_set(False); h.hide_set(True)


def manifest_row(ob, asset, family, variant, lod, slots, seed, counts, hull_count, budget, extra=None):
    me = ob.data; me.calc_loop_triangles()
    xs = [v.co for v in me.vertices]
    size = [round(max(v[i] for v in xs) - min(v[i] for v in xs), 4) for i in range(3)]
    row = dict(name=ob.name, asset=asset, family=family, variant=variant, lod=lod, triangles=len(me.loop_triangles),
               budget=budget, slots=len(slots), slot_names=[SLOT_NAMES[s] for s in slots], leaves=counts['leaves'],
               fronds=counts['fronds'], sprays=counts['sprays'], clusters=counts['clusters'], tubes=counts['tubes'], size_m=size,
               min_z_m=round(min(v.z for v in xs), 4), hulls=hull_count, seed=seed, ground_pivot=True)
    if extra:
        row.update(extra)
    return row


def write_manifest(rows, out=OUT, extra=None, set_name=None):
    """Write manifest.json. With set_name, rows of other sets already in the manifest are kept
    (the bush and open sets share one manifest) and this set's rows are replaced."""
    keep = {}
    if set_name:
        for r in rows:
            r['set'] = set_name
        path = out / 'manifest.json'
        if path.exists():
            try:
                old = json.loads(path.read_text())
                rows = [r for r in old.get('models', []) if r.get('set') not in (None, set_name)] + rows
                keep = {k: v for k, v in old.items() if k != 'models'}
            except Exception:
                pass
    data = dict(version=1, kit=KIT, units='metres; FBX centimetres (vertices x100, unit scale .01, -Z forward, Y up)',
                collision='trees: UCX_<mesh>_NN convex hulls in the LOD0 FBX; ferns none',
                textures='none; linear vertex Color, UVMap local surface coordinates',
                unreal_destination='/Game/GrandTour/Environment/NativePlants/v01', models=rows)
    data = {**keep, **data}
    if extra:
        data.update(extra)
    order = ['version', 'kit', 'units', 'collision', 'textures', 'unreal_destination']
    data = {**{k: data[k] for k in order if k in data}, **{k: v for k, v in data.items() if k not in order and k != 'models'}, 'models': data['models']}
    (out / 'manifest.json').write_text(json.dumps(data, indent=2))
    return data


def mark_asset(ob, description, tags):
    ob.asset_mark(); ob.asset_data.description = description
    for t in tags:
        ob.asset_data.tags.new(t)


# ---------------------------------------------------------------- review helpers

def review_scene(name, samples=24):
    scene = bpy.data.scenes.new(name)
    scene.render.engine = 'CYCLES'; scene.cycles.samples = samples; scene.cycles.use_denoising = True
    w = bpy.data.worlds.get('NZ Review World') or bpy.data.worlds.new('NZ Review World')
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = (.32, .38, .44, 1); bg.inputs[1].default_value = .5
    scene.world = w
    scene.view_settings.view_transform = 'AgX'
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    return scene


def link(scene, ob):
    scene.collection.objects.link(ob)
    return ob


def display_copy(scene, ob, name, location=(0, 0, 0), rotation=0.0, scale=1.0):
    c = bpy.data.objects.new(name, ob.data)
    scene.collection.objects.link(c)
    c.location = location; c.rotation_euler = (0, 0, rotation); c.scale = (scale, scale, scale)
    return c


def studio_lights(scene, centre=(0, 0, 0), scale=1.0, energy=1.0):
    """The overcast studio's two disk area lights (shrub review rig), scaled about a centre."""
    c = Vector(centre)
    out = []
    for i, (loc, e, size) in enumerate([((-5, -5, 11), 1900, 8), ((7, 3, 9), 1400, 7)]):
        ld = bpy.data.lights.new('%s Light %d' % (scene.name, i), 'AREA')
        ld.energy = e * scale * scale * energy; ld.shape = 'DISK'; ld.size = size * scale
        lo = bpy.data.objects.new(ld.name, ld); scene.collection.objects.link(lo)
        lo.location = c + Vector(loc) * scale
        lo.rotation_euler = (c - lo.location).to_track_quat('-Z', 'Y').to_euler()
        out.append(lo)
    return out


def floor(scene, mat, size=400, z=-.07, location=(0, 0)):
    me = bpy.data.meshes.new(scene.name + ' Floor')
    h = size / 2
    me.from_pydata([(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0)], [], [(0, 1, 2, 3)]); me.materials.append(mat)
    ob = bpy.data.objects.new(me.name, me); scene.collection.objects.link(ob)
    ob.location = (location[0], location[1], z)
    return ob


def flat_material(name, colour, emission=0.0, roughness=.87):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value = (*colour, 1); p.inputs['Roughness'].default_value = roughness
    p.inputs['Specular IOR Level'].default_value = .19
    if emission:
        p.inputs['Emission Color'].default_value = (*colour, 1); p.inputs['Emission Strength'].default_value = emission
    return m


def text_obj(scene, body, location, size, mat, rotation=(math.pi / 4, 0, 0), align='CENTER'):
    c = bpy.data.curves.new(body, 'FONT'); c.body = body; c.size = size; c.align_x = align; c.extrude = 0
    c.materials.append(mat)
    o = bpy.data.objects.new(body, c); scene.collection.objects.link(o)
    o.location = location; o.rotation_euler = rotation
    return o


def figure(scene, location=(0, 0, 0), height=1.8, radius=.2, mat=None):
    """The 1.8 m scale capsule."""
    g = Geo()
    zs = []
    for k in range(7):
        a = -math.pi / 2 + (math.pi / 2) * k / 6
        zs.append((radius + radius * math.sin(a), radius * math.cos(a) if k else .002))
    zs.append((height - radius, radius))
    for k in range(1, 7):
        a = (math.pi / 2) * k / 6
        zs.append((height - radius + radius * math.sin(a), max(.002, radius * math.cos(a))))
    pts = [Vector((0, 0, z)) for z, r in zs]
    tube(g, pts, [r for z, r in zs], 16, (.6, .42, .2), 0, caps=(True, True), noise=0)
    me = bpy.data.meshes.new('Scale figure 1.8 m')
    me.from_pydata([tuple(v) for v in g.v], [], g.f)
    if mat:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new('Scale figure 1.8 m', me); scene.collection.objects.link(ob)
    ob.location = location
    return ob


def camera(scene, location, target, lens=50, ortho=None, name=None):
    cd = bpy.data.cameras.new(name or scene.name + ' Camera')
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_end = 2000
    co = bpy.data.objects.new(cd.name, cd); scene.collection.objects.link(co)
    co.location = location
    co.rotation_euler = (Vector(target) - Vector(location)).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = co
    return co


def render(scene, path, x, y):
    scene.render.resolution_x = x; scene.render.resolution_y = y
    scene.render.filepath = str(path)
    try:
        bpy.context.window.scene = scene
    except Exception:
        pass
    bpy.ops.render.render(write_still=True, scene=scene.name)
    return path


def compose_inset(main, inset, out):
    """Place the `inset` render at the top right beside the `main` render (raw PNG bytes kept)."""
    import numpy as np
    A = bpy.data.images.load(str(main), check_existing=False); B = bpy.data.images.load(str(inset), check_existing=False)
    wa, ha = A.size; wb, hb = B.size
    a = np.empty(wa * ha * 4, dtype=np.float32); A.pixels.foreach_get(a); a = a.reshape(ha, wa, 4)
    b = np.empty(wb * hb * 4, dtype=np.float32); B.pixels.foreach_get(b); b = b.reshape(hb, wb, 4)
    W, H = wa + wb, max(ha, hb)
    c = np.empty((H, W, 4), dtype=np.float32); c[:] = a[:, -1:, :].mean(axis=0)
    c[:ha, :wa] = a
    c[H - hb:, wa:] = b
    img = bpy.data.images.new('NZ inset compose', W, H, alpha=False)
    img.pixels.foreach_set(c.ravel())
    img.filepath_raw = str(out); img.file_format = 'PNG'; img.save()
    for im in (A, B, img):
        bpy.data.images.remove(im)
    return out
