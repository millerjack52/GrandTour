"""LP4 (docs/LIDAR_PLACE_PLAN.md): the three paddocks and the Southland farm hardware for prepare_lidar_place.py.

Everything here works in world METRES, the map's own frame: x east, y SOUTH (so the map seen from above has y pointing down). In that frame
- the true right of a travel direction d=(dx,dy) is (-dy,dx), the true left (dy,-dx);
- a polygon with positive shoelace area (shapely orient(p,1)) has its interior on the true RIGHT of its traversal;
- an Unreal yaw theta turns +X toward +Y: local +X=(cos,sin), local +Y (the kit's Blender -Y side, the wire / sign-face / letterbox-door side)=(-sin,cos),
  i.e. the true right of local +X. The kit FBX import keeps Blender X and Z and flips Y (checked against the farm import report's bounds).
Kit facing, from Art/Blender/build_southland_farm.py: fence module = post at x=0 and wires to +x on the +Y side; strainer = post at 0, stay and wire tails to +x,
second post at x=-2.5; gate = hinge post at 0, latch post at 3.96, straps and brace on +Y; cattle stop travel along +X; culvert axis along X with the headwall at
the -X end (flow runs toward +X); power pole stay cable toward +X; sign, give way and letterbox faces on +Y.
"""
import json, math
import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, binary_closing, binary_opening, median_filter, uniform_filter, label, maximum_filter, map_coordinates, distance_transform_edt
import shapely
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, polylabel, nearest_points
from rasterio.features import shapes, rasterize
from affine import Affine

MESH = dict(fence='SM_NZ_Fence_4m', strainer='SM_NZ_Strainer', gate='SM_NZ_Gate_3m6', stop='SM_NZ_CattleStop', culvert='SM_NZ_Culvert', trough='SM_NZ_Trough',
            pole='SM_NZ_PowerPole', sign='SM_NZ_SignPost', giveway='SM_NZ_GiveWay', letterbox='SM_NZ_Letterbox', bale='SM_NZ_HayBale')
FENCE_SPAN = 4.0     # post to post of one SM_NZ_Fence_4m module
GATE_SPAN = 3.96     # hinge post to latch post of SM_NZ_Gate_3m6 (3.6 m clear opening)
ROAD_HALF = 1.9      # private road bed 3.8 m wide (install width_cm 380)
# Pasture in the registered aerial: green over red and blue, bright, smooth (texture = luminance std over 9 px). Thresholds from the three fields' own pixels
# (field 94/115/76 with texture 1-4, bush 55/75/50 with texture 10-20).
PASTURE = dict(g_over_r=6., g_over_b=25., v_min=85., texture_max=5.5, median_px=9, open_iterations=3)
# One straight fence digitised from the aerial: the west fence of the square paddock, pixel columns 420..428 of the 1200 x 2080 aerial, cut through the whole height so the
# square paddock does not merge with the west paddock (the fence is a 1 px line in the aerial, invisible to the colour test).
SPLIT_U = [(420, 429)]
TOUCH_M = 12.        # a field "touches" a private road when its nearest pixel is within this (road bed 1.9 m + shoulder + the field's own edge)
NEAR_M = 150.        # fallback when fewer than three fields touch
DILATE_M = 2.        # the green edge is inside the real fence line (rank grass at the foot); push it out
SIMPLIFY_M = 8.      # Douglas-Peucker tolerance: the real fences are straight runs
SMOOTH_PX = 8        # closing then opening, in aerial pixels (0.625 m): 5 m
MIN_VERTEX_M = 8.    # polygon vertices at least this far apart
ROAD_CLEAR_M = 3.    # a fence never closer than this to a private road centre line
GATE_FROM_VERTEX_M = 4.


def ang(d):
    return math.degrees(math.atan2(d[1], d[0]))


def unit(v):
    v = np.asarray(v, float)
    n = float(np.hypot(*v))
    return v / (n if n > 1e-9 else 1.)


def right(d):
    return np.array([-d[1], d[0]], float)


def left(d):
    return np.array([d[1], -d[0]], float)


def enforce_spacing(coords, min_len):
    """Drop the vertex of the shortest edge whose removal changes the area least, until every edge is at least min_len."""
    pts = [np.array(c, float) for c in coords[:-1]]
    while len(pts) > 3:
        n = len(pts)
        lens = [float(np.hypot(*(pts[(i + 1) % n] - pts[i]))) for i in range(n)]
        i = int(np.argmin(lens))
        if lens[i] >= min_len:
            break

        def tri(k):
            a, b, c = pts[(k - 1) % n], pts[k], pts[(k + 1) % n]
            return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
        k = i if tri(i) <= tri((i + 1) % n) else (i + 1) % n
        del pts[k]
    return pts


def find_paddocks(base, priv_lines):
    """The three big grazed paddocks along the private roads, from the registered priority aerial (reference only, never shipped).
    Why not the forest and scrub masks: they are OSM land cover polygons, coarse and misregistered against the aerial (the NE paddock is 81% 'scrub', and every open
    region joins into one 596k-cell field), so the three largest open regions on the 2048 grid are not the three fields. The aerial's own pasture pixels give them directly."""
    ext = json.loads((base / 'Reference/priority-extent.json').read_text())
    e = ext['extent']
    px = (e['xmax'] - e['xmin']) / ext['width']
    py = (e['ymax'] - e['ymin']) / ext['height']
    assert abs(px - py) < 1e-6, (px, py)
    x0 = e['xmin'] - 1197144.5            # NZTM -> map metres (centre E1197144.5 N4865011.5), x east
    y0 = -(e['ymax'] - 4865011.5)         # south positive, image row 0 is the north edge
    A = Affine(px, 0, x0, 0, px, y0)
    a = np.asarray(Image.open(base / 'Reference/priority-aerial.jpg').convert('RGB')).astype(float)
    assert a.shape[1] == ext['width'] and a.shape[0] == ext['height'], (a.shape, ext['width'], ext['height'])
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    lum = a.mean(-1)
    m1 = uniform_filter(lum, 9)
    tex = np.sqrt(np.maximum(uniform_filter(lum * lum, 9) - m1 * m1, 0))
    P = PASTURE
    mask = (G > R + P['g_over_r']) & (G > B + P['g_over_b']) & (a.max(-1) > P['v_min']) & (tex < P['texture_max'])
    mask = median_filter(mask.astype(np.uint8), size=P['median_px']).astype(bool)
    mask = binary_opening(mask, iterations=P['open_iterations'])
    cut = mask.copy()
    for u0, u1 in SPLIT_U:
        cut[:, u0:u1] = False
    cut = binary_opening(cut, iterations=4)
    lab, n = label(cut)
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    roadpx = rasterize([(l, 1) for l in priv_lines], out_shape=mask.shape, transform=A, all_touched=True, dtype='uint8') > 0
    dmap = distance_transform_edt(~roadpx) * px
    cands = []
    for i in np.argsort(-sizes):
        if sizes[i] * px * px < 2000.:
            break
        mm = lab == i
        ys, xs = np.nonzero(mm)
        cands.append(dict(label=int(i), area_m2=float(sizes[i] * px * px), centroid_m=[float(x0 + (xs.mean() + .5) * px), float(y0 + (ys.mean() + .5) * px)], dist_to_private_road_m=float(dmap[mm].min())))
    big = [c for c in cands if c['area_m2'] >= 5000.]
    touching = [c for c in big if c['dist_to_private_road_m'] <= TOUCH_M]
    pick = sorted(touching, key=lambda c: -c['area_m2'])[:3]
    rule = 'three largest fields touching a private road (<= %.0f m)' % TOUCH_M
    if len(pick) < 3:
        extra = [c for c in sorted(big, key=lambda c: -c['area_m2']) if c not in pick and c['dist_to_private_road_m'] <= NEAR_M]
        pick = (pick + extra)[:3]
        rule += ' topped up from fields within %.0f m' % NEAR_M
    assert len(pick) == 3, ('three paddocks not found', cands)
    polys = []
    for c in pick:
        m = binary_fill_holes(lab == c['label'])
        m = binary_fill_holes(binary_closing(m, iterations=SMOOTH_PX))     # fill notches under ~6 m (a tree at the edge, a wet hollow) ...
        m = binary_opening(m, iterations=SMOOTH_PX)                          # ... and shave spurs under ~6 m: a fence line is straight
        cand = [shapely.geometry.shape(g) for g, v in shapes(m.astype('uint8'), mask=m, transform=A) if v == 1]
        poly = max(cand, key=lambda p: p.area)
        poly = orient(Polygon(poly.exterior).buffer(DILATE_M, join_style=2).simplify(SIMPLIFY_M), 1.)
        pts = enforce_spacing(list(poly.exterior.coords), MIN_VERTEX_M)
        poly = orient(Polygon(pts), 1.)
        if not poly.is_valid:
            poly = orient(poly.buffer(0), 1.)
        clear = unary_union(priv_lines).buffer(ROAD_CLEAR_M)
        if poly.intersects(clear):   # keep every fence off the road bed and its shoulder
            poly = poly.difference(clear)
            poly = max(poly.geoms, key=lambda p: p.area) if poly.geom_type == 'MultiPolygon' else poly
            pts = enforce_spacing(list(orient(poly, 1.).exterior.coords), MIN_VERTEX_M)
            poly = orient(Polygon(pts), 1.)
        c['polygon'] = poly
        c['chosen'] = True
        c['vertices'] = len(poly.exterior.coords) - 1
        c['area_polygon_m2'] = float(poly.area)
        c['perimeter_m'] = float(poly.length)
        c['min_edge_m'] = float(min(np.hypot(*(np.array(q) - np.array(p))) for p, q in zip(poly.exterior.coords[:-1], poly.exterior.coords[1:])))
        polys.append(c)
    return dict(paddocks=polys, candidates=cands, rule=rule, aerial_px_m=px, aerial_origin_m=[x0, y0], split_u=SPLIT_U)


def soft_mask(polys_m, N, step_m, o_m, ss=4):
    """Coverage fraction (0..1) of the polygons on the N x N map grid (cell step_m, origin o_m on both axes)."""
    out = np.zeros((N, N), np.float32)
    for p in polys_m:
        x0, y0, x1, y1 = p.bounds
        i0 = max(0, int((x0 - o_m) / step_m) - 1)
        i1 = min(N, int((x1 - o_m) / step_m) + 2)
        j0 = max(0, int((y0 - o_m) / step_m) - 1)
        j1 = min(N, int((y1 - o_m) / step_m) + 2)
        A = Affine(step_m / ss, 0, o_m + i0 * step_m, 0, step_m / ss, o_m + j0 * step_m)
        m = rasterize([(p, 1)], out_shape=((j1 - j0) * ss, (i1 - i0) * ss), transform=A, dtype='uint8').astype(np.float32)
        out[j0:j1, i0:i1] = np.maximum(out[j0:j1, i0:i1], m.reshape(j1 - j0, ss, i1 - i0, ss).mean((1, 3)))
    return out


def along(pts, s):
    """Point and unit tangent at arc length s of the polyline pts (metres)."""
    cum = np.concatenate([[0.], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
    s = float(min(max(s, 0.), cum[-1]))
    k = int(min(max(np.searchsorted(cum, s, side='right'), 1), len(pts) - 1))
    f = (s - cum[k - 1]) / max(cum[k] - cum[k - 1], 1e-9)
    p = pts[k - 1] + (pts[k] - pts[k - 1]) * f
    a = pts[min(k + 1, len(pts) - 1)] if k + 1 < len(pts) else pts[-1]
    b = pts[max(k - 2, 0)]
    t = unit(pts[k] - pts[k - 1]) if (cum[k] - cum[k - 1]) > 1e-6 else unit(a - b)
    return p, t


def build(ctx):
    """ctx: polys (oriented, metres), priv {name: (n,2) metres}, bush_flag(s_m)->bool for Riverside access, forest(x_m,y_m)->0..1, water_dist(x_m,y_m)->metres,
    acc / filled (the 2 m drainage grids), height_cm(x_cm,y_cm)->cm, rng."""
    polys = ctx['polys']
    priv = ctx['priv']
    ra = priv['Riverside access']
    rng = ctx['rng']
    items = []
    clear = []          # (x_m, y_m, radius_m) circles cleared of trees and understory
    wings = []          # fence lines outside the paddock polygons (entrance wings), metres
    info = dict(gates=[], culverts=[], poles=dict(placed=0, skipped=[]), entrance={}, troughs=[], bales=[])
    pad_union = unary_union(polys)

    def add(key, x, y, yaw, **kw):
        z = float(ctx['height_cm'](x * 100., y * 100.))
        items.append(dict(mesh=MESH[key], p=[round(x * 100., 1), round(y * 100., 1), round(z, 1)], yaw=round(float(yaw), 2), **kw))

    # ---------------------------------------------------------------- 1. paddock fences, strainers at corners, a gate at each paddock's gateway
    road_all = unary_union([LineString(p) for p in priv.values()])
    for k, poly in enumerate(polys):
        ring = list(poly.exterior.coords)[:-1]
        n = len(ring)
        V = [np.array(c, float) for c in ring]
        segs = []
        for i in range(n):
            d = V[(i + 1) % n] - V[i]
            segs.append((float(np.hypot(*d)), unit(d)))
        # gateways: where a private road crosses this boundary (a 3.6 m gap and a gate across the road); where none does, the boundary segment nearest a private road
        gates = []
        fits = [i for i in range(n) if segs[i][0] >= 2 * GATE_FROM_VERTEX_M + GATE_SPAN]
        assert fits, ('no boundary segment long enough for a gate', k)
        for rn, pts in priv.items():
            for pt in (lambda g: list(g.geoms) if hasattr(g, 'geoms') else ([g] if not g.is_empty else []))(poly.exterior.intersection(LineString(pts))):
                if pt.geom_type != 'Point':
                    continue
                best = min(fits, key=lambda i: LineString([V[i], V[(i + 1) % n]]).distance(pt))
                gates.append(dict(seg=best, along=float(np.dot(np.array([pt.x, pt.y]) - V[best], segs[best][1])), road=rn, kind='crossing', road_dist_m=0.))
        if not gates:
            cand = []
            for i in fits:
                for rn, pts in priv.items():
                    ls = LineString([V[i], V[(i + 1) % n]])
                    pr, pb = nearest_points(LineString(pts), ls)
                    cand.append((pr.distance(pb), i, rn, float(np.dot(np.array([pb.x, pb.y]) - V[i], segs[i][1]))))
            dist, i, rn, al = min(cand)
            gates.append(dict(seg=i, along=al, road=rn, kind='gateway at the nearest approach (the road runs alongside, it does not cross)', road_dist_m=float(dist)))
        for g in gates:   # the gate (3.96 m post to post) must keep a module's length of fence to each vertex
            L = segs[g['seg']][0]
            g['along'] = float(min(max(g['along'], GATE_FROM_VERTEX_M + GATE_SPAN / 2), L - GATE_FROM_VERTEX_M - GATE_SPAN / 2))
        by_seg = {g['seg']: g for g in gates}
        for i in range(n):
            L, d = segs[i]
            if i in by_seg:
                g = by_seg[i]
                g0, g1 = g['along'] - GATE_SPAN / 2, g['along'] + GATE_SPAN / 2
                runs = [(0., g0), (g1, L)]
                c = V[i] + d * g['along']
                a_in = right(d)                           # the road is outside the fence; the approach runs inward
                assert np.allclose(left(a_in), d, atol=1e-6), (left(a_in), d)   # the traveller's left hand is the later end of the segment
                hinge = c + d * (GATE_SPAN / 2)           # hinge post on the road's left side
                add('gate', hinge[0], hinge[1], ang(-d), len_cm=round(GATE_SPAN * 100., 1), tag='paddock %d gate' % (k + 1))
                g.update(paddock=k, centre_m=[float(c[0]), float(c[1])], approach=[float(a_in[0]), float(a_in[1])], hinge_m=[float(hinge[0]), float(hinge[1])], yaw=ang(-d), segment_m=float(L))
                info['gates'].append(g)
                clear += [(hinge[0], hinge[1], 1.4), (c[0] - d[0] * GATE_SPAN / 2, c[1] - d[1] * GATE_SPAN / 2, 1.4)]
            else:
                runs = [(0., L)]
            for s0, s1 in runs:
                m = max(1, int(round((s1 - s0) / FENCE_SPAN)))
                sp = (s1 - s0) / m
                for j in range(m):
                    q = V[i] + d * (s0 + j * sp)
                    add('fence', q[0], q[1], ang(d), len_cm=round(sp * 100., 1), tag='paddock %d fence' % (k + 1))
        for i in range(n):   # corner strainers: the assembly's stay and wire tails run along the outgoing fence
            add('strainer', V[i][0], V[i][1], ang(segs[i][1]), tag='paddock %d corner' % (k + 1))
            clear.append((V[i][0], V[i][1], 1.4))
    n_fence_runs = sum(1 for it in items if it['mesh'] == MESH['fence'])

    # ---------------------------------------------------------------- 2. main entrance off Waimeamea Road: cattle stop, fence wings, name sign, letterbox, give way
    J, t = along(ra, 0.)
    SC = 20.
    c0, t = along(ra, SC)
    t = unit(t)
    lt = left(t)
    add('stop', c0[0], c0[1], ang(t), tag='entrance cattle stop')
    clear.append((c0[0], c0[1], 3.6))
    d = lt                                          # fence line along the left of the track, wire side +Y = the true right of d = +t = the farm side
    for lo, hi, yaw_lo, yaw_hi in [(-16.5, -4.5, d, -d), (4.5, 16.5, d, -d)]:
        a0, a1 = c0 + d * lo, c0 + d * hi
        add('strainer', a0[0], a0[1], ang(yaw_lo), tag='entrance wing end')
        add('strainer', a1[0], a1[1], ang(yaw_hi), tag='entrance wing end')
        for j in range(3):
            q = a0 + d * (FENCE_SPAN * j)
            add('fence', q[0], q[1], ang(d), len_cm=FENCE_SPAN * 100., tag='entrance wing')
        wings.append(LineString([a0, a1]))
        clear += [(a0[0], a0[1], 1.4), (a1[0], a1[1], 1.4)]
    sp1 = c0 + lt * 3. - t * 1.5
    add('letterbox', sp1[0], sp1[1], ang(t), tag='entrance letterbox')       # door on +Y = the true right of +x = toward the track
    sp2 = c0 + lt * 3. - t * 4.5
    add('sign', sp2[0], sp2[1], math.degrees(math.atan2(t[0], -t[1])), tag='entrance road-name sign')   # face toward the traffic coming in (-t)
    jt = along(ra, 2.)
    gp = jt[0] + right(t) * 3.2
    add('giveway', gp[0], gp[1], math.degrees(math.atan2(-t[0], t[1])), tag='entrance give way')       # face toward the traffic leaving the farm (+t)
    clear += [(sp1[0], sp1[1], 1.2), (sp2[0], sp2[1], 1.2), (gp[0], gp[1], 1.2)]
    info['entrance'] = dict(junction_m=[float(J[0]), float(J[1])], stop_m=[float(c0[0]), float(c0[1])], track_tangent=[float(t[0]), float(t[1])], stop_station_m=SC,
                            letterbox_m=[float(sp1[0]), float(sp1[1])], sign_m=[float(sp2[0]), float(sp2[1])], giveway_m=[float(gp[0]), float(gp[1])])

    # ---------------------------------------------------------------- 3. culverts where Riverside access crosses a drainage channel
    acc, filled = ctx['acc'], ctx['filled']
    accm = maximum_filter(acc, size=5)
    Ltot = float(np.hypot(*np.diff(ra, axis=0).T).sum())
    ss = np.arange(0., Ltot, 1.)
    q = np.array([along(ra, s)[0] for s in ss])
    arow, acol = (q[:, 1] + 1849.5) / 2, (q[:, 0] + 1817.5) / 2
    aval = map_coordinates(accm, [arow, acol], order=0, mode='nearest')
    wd = np.array([ctx['water_dist'](x, y) for x, y in q])
    MAIN_STEM = 60000   # cells: the river itself and its big tributary, which the road fords (water patches), are not culvert sites
    trials = {}
    for T in (300, 500, 800, 1000, 1200, 1500, 2000, 3000, 4000, 6000):
        run = aval >= T
        e = np.diff(np.concatenate([[0], run.astype(int), [0]]))
        st, en = np.flatnonzero(e == 1), np.flatnonzero(e == -1)
        runs = []
        for s0, e0 in zip(st, en):
            if runs and s0 - runs[-1][1] < 12:
                runs[-1][1] = e0
            else:
                runs.append([s0, e0])
        good = []
        for s0, e0 in runs:
            seg = aval[s0:e0]
            if e0 - s0 > 40 or seg.max() >= MAIN_STEM or s0 < 40 or e0 > Ltot - 60 or wd[s0:e0].min() < 12.:
                continue
            good.append(int(s0 + seg.argmax()))
        sel = []
        for s in sorted(good):
            if not sel or s - sel[-1] >= 30:
                sel.append(s)
        trials[T] = sel
    MIN_CHANNEL = 1000   # cells (4,000 m2 upstream): below this the 'channel' is a seep that does not need a pipe under a farm track
    T_used = None
    for T in sorted(trials):
        if T >= MIN_CHANNEL and 3 <= len(trials[T]) <= 8:
            T_used = T
            break
    assert T_used is not None, {t_: len(v) for t_, v in trials.items()}
    info['culvert_threshold_cells'] = T_used
    info['culvert_trials'] = {int(t_): len(v) for t_, v in trials.items()}
    info['culvert_rule'] = ('5x5 max of the 2 m flow accumulation under the track >= T cells, one crossing = a run <= 40 m (gaps < 12 m merged) below %d cells (the river), '
                            '>= 12 m from the river and pond footprints, >= 30 m apart; smallest T >= 1000 of the trial list giving 3..8' % MAIN_STEM)
    for s in trials[T_used]:
        c, tg = along(ra, float(s))
        nl = left(tg)
        hu = float(map_coordinates(filled, [[(c[1] + nl[1] * 6 + 1849.5) / 2], [(c[0] + nl[0] * 6 + 1817.5) / 2]], order=1, mode='nearest')[0])
        hd = float(map_coordinates(filled, [[(c[1] - nl[1] * 6 + 1849.5) / 2], [(c[0] - nl[0] * 6 + 1817.5) / 2]], order=1, mode='nearest')[0])
        up = nl if hu > hd else -nl            # the uphill side of the road: the headwall goes there
        flow = -up                              # local +X runs downhill, across the road
        o = c + up * 1.175                      # headwall slab centre (local x = -1.125) 2.3 m from the road centre, just outside the 1.9 m bed
        add('culvert', o[0], o[1], ang(flow), tag='culvert station %d m' % s)
        clear.append((o[0], o[1], 2.4))
        info['culverts'].append(dict(station_m=int(s), acc_cells=int(aval[s]), uphill_rise_12m=float(abs(hu - hd)), centre_m=[float(c[0]), float(c[1])], origin_m=[float(o[0]), float(o[1])], yaw=ang(flow)))

    # ---------------------------------------------------------------- 4. power poles every 60 m from the junction, 3 m off the track's right edge, open stretches only
    fence_zone = pad_union.buffer(2.5)
    blocked_by = lambda x, y: ('forest' if ctx['forest'](x, y) > .5 else 'water' if ctx['water_dist'](x, y) < 3. else 'paddock fence' if fence_zone.contains(Point(x, y)) else None)
    stop_zone = Point(*c0).buffer(8.)
    for s in np.arange(60., Ltot - 20., 60.):
        c, tg = along(ra, float(s))
        r = right(tg)
        why = 'bush stretch' if ctx['bush_flag'](float(s)) else None
        placed = None
        if why is None:
            for off in (ROAD_HALF + 3., ROAD_HALF + 5., ROAD_HALF + 7.):
                p = c + r * off
                b = blocked_by(p[0], p[1]) or ('entrance' if stop_zone.contains(Point(*p)) else None)
                if b is None:
                    placed = p
                    break
                why = b
        if placed is None:
            info['poles']['skipped'].append(dict(station_m=float(s), why=why))
            continue
        add('pole', placed[0], placed[1], ang(r), tag='power pole station %d m' % s)    # stay cable (+X) points away from the track
        clear.append((placed[0], placed[1], 1.5))
        info['poles']['placed'] += 1

    # ---------------------------------------------------------------- 5. one trough per paddock near its centre, three bales by the first trough
    for k, poly in enumerate(polys):
        pt = polylabel(poly, tolerance=1.0)
        yaw = float(rng.uniform(0, 360))
        add('trough', pt.x, pt.y, yaw, tag='paddock %d trough' % (k + 1))
        clear.append((pt.x, pt.y, 1.6))
        info['troughs'].append(dict(paddock=k, centre_m=[float(pt.x), float(pt.y)], edge_clearance_m=float(poly.exterior.distance(pt)), yaw=yaw))
        if k == 0:
            base_a = float(rng.uniform(0, 360))
            for j in range(3):
                a = math.radians(base_a + j * 120. + float(rng.uniform(-15, 15)))
                r_ = float(rng.uniform(4.5, 6.5))
                bx, by = pt.x + math.cos(a) * r_, pt.y + math.sin(a) * r_
                assert poly.contains(Point(bx, by))
                yb = float(rng.uniform(0, 360))
                add('bale', bx, by, yb, tag='bale by trough 1')
                clear.append((bx, by, 1.6))
                info['bales'].append(dict(centre_m=[float(bx), float(by)], yaw=yb))
    info['fence_modules'] = n_fence_runs
    return dict(items=items, clear=clear, wings=wings, info=info)
