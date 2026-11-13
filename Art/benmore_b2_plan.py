"""Benmore integration B2b (docs/BENMORE_INTEGRATION_PLAN.md, "B2 addendum"): where the deform zones go on L_Benmore_GaeaReview, from
the road manifest and the Gaea data on disk. Plain Python (numpy, Pillow), no Unreal: writes Art/Export/BenmoreB2/plan.json, which
Art/Unreal/setup_benmore_b2.py places (and checks the bogs against the level's meshes by traces).

- Heights: ShoreRefinement/reloaded-native-height.r16 (the review landscape's own heights; 2017 x 2017 at 124 cm, z = (h - 32768) x 200 /
  128 cm; matches the road manifest's z within centimetres).
- The creek and channel: T_GC_ExtendedBedZones' alpha (the bed zones, as M_GC_Terrain's ChannelPilot reads them, its own UV).
- The lake: ground under 48 cm (M_GC_Terrain's lake test).
- Flow: T_Gaea_Flow is a flow-direction field (RG the downhill direction, A the slope's steepness: dark on the valley floor and in the
  gullies), not an accumulation, so its top 25 % is the steepest hillside. The low, wet lines come from a D8 flow accumulation of the
  heights at 5 m instead; the plan's "top 25 %" is taken over the road's own samples.
- Roads: every 2 m along each centreline. MudRoad where a sample is within 40 m of the bed, or under 3 deg near (40 m) the lake, or in
  the accumulation's top quarter; runs scored by wetness, the wettest taken until 35 % of the road length; MudRoad stretches 30-60 m
  (a mud zone is one patch over its box), gravel 30-120 m.
- Gravel profile per stretch: B1's physical material output (benmore_gt_ground MASKS_HLSL with Codex's TRACKS) across the road on a
  25 cm lateral grid - the dominant of GravelFirm (the wheel paths) and GravelLoose (crown and edges).
- Bogs: flat (< 4 deg), low and wet (40 m of the bed, or within 10 m of a drainage line - the accumulation's top 5 % of the land - or
  near the lake), off the road and the
  bed, within 30 m of a road; connected regions of at least 150 m^2; an irregular blob 15-40 m across inside each; the sparsest
  vegetation first (T_RL_Vegetation: the landscape grass grows from it and would stand in the mud), at most 6, 80 m apart; Standard or
  Deep near water, Firm or Stony elsewhere.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GAEA = ROOT / 'Art/Export/BenmoreGaea'
OUT = ROOT / 'Art/Export/BenmoreB2'
N = 2017
PX = 2500.0 / 2016.0   # m per height sample


def to_px(x, y):
    return (x + 1250.0) / 2500.0 * 2016.0, (y + 1250.0) / 2500.0 * 2016.0


def bilinear(img, x, y):
    c, r = to_px(x, y)
    c0 = int(np.clip(math.floor(c), 0, N - 2))
    r0 = int(np.clip(math.floor(r), 0, N - 2))
    tc, tr = c - c0, r - r0
    return (img[r0, c0] * (1 - tc) * (1 - tr) + img[r0, c0 + 1] * tc * (1 - tr) + img[r0 + 1, c0] * (1 - tc) * tr + img[r0 + 1, c0 + 1] * tc * tr)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h = np.fromfile(GAEA / 'ShoreRefinement/reloaded-native-height.r16', dtype='<u2').reshape(N, N).astype(np.float64)
    z = (h - 32768.0) * 200.0 / 128.0 / 100.0
    gy, gx = np.gradient(z, PX)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    # The bed (creek and channel) on the height grid.
    bed_img = np.asarray(Image.open(GAEA / 'ShoreRefinement/T_GC_ExtendedBedZones.png')).astype(np.float64)
    ys, xs = np.mgrid[0:N, 0:N]
    xm = xs / 2016.0 * 2500.0 - 1250.0
    ym = ys / 2016.0 * 2500.0 - 1250.0
    u = (xm + 1581.1011904762 + 0.6200396825) / 2832.3412698413
    v = (ym + 1250.0 + 0.62) / 2501.24
    bc = np.clip(np.round(u * bed_img.shape[1] - 0.5).astype(int), 0, bed_img.shape[1] - 1)
    br = np.clip(np.round(v * bed_img.shape[0] - 0.5).astype(int), 0, bed_img.shape[0] - 1)
    bed = np.where((u >= 0) & (u <= 1) & (v >= 0) & (v <= 1), bed_img[br, bc, 3] / 255.0, 0.0)
    lake = z < 0.48
    veg = np.asarray(Image.open(GAEA / 'Morphology/T_RL_Vegetation.png').convert('RGBA')).astype(np.float64)[..., :3] / 255.0
    eco = np.asarray(Image.open(GAEA / 'ShoreRefinement/T_RL_Ecology.png').convert('RGBA')).astype(np.float64) / 255.0
    # D8 flow accumulation at 5 m (4 x 4 height samples).
    k = 4
    zc = z[:N // k * k, :N // k * k].reshape(N // k, k, N // k, k).mean(axis=(1, 3))
    M = zc.shape[0]
    order = np.argsort(-zc, axis=None)
    acc = np.ones(M * M)
    flat = zc.ravel()
    offs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for idx in order:
        r, c = divmod(int(idx), M)
        best, bz = -1, flat[idx]
        for dr, dc in offs:
            rr, cc = r + dr, c + dc
            if 0 <= rr < M and 0 <= cc < M:
                d = (flat[idx] - flat[rr * M + cc]) / (1.4142 if dr and dc else 1.0)
                if d > 0 and flat[idx] - d > -1e9 and (best < 0 or d > bz):
                    best, bz = rr * M + cc, d
        if best >= 0:
            acc[best] += acc[idx]
    acc = acc.reshape(M, M)
    acc_full = np.kron(np.log1p(acc), np.ones((k, k)))
    acc_full = np.pad(acc_full, ((0, N - acc_full.shape[0]), (0, N - acc_full.shape[1])), mode='edge')
    # Points of the bed and the lake for distances.
    bed_pts = np.stack([xm[bed > 0.5], ym[bed > 0.5]], 1)[::3]
    lake_pts = np.stack([xm[lake], ym[lake]], 1)[::4]

    def nearest(pts, P):
        out = np.full(len(P), 1e9)
        for i in range(0, len(P), 256):
            d = np.sqrt(((P[i:i + 256, None, :] - pts[None, :, :]) ** 2).sum(-1)).min(1) if len(pts) else np.full(len(P[i:i + 256]), 1e9)
            out[i:i + 256] = d
        return out

    manifest = json.loads((ROOT / 'Art/Export/BenmoreRoads/road-manifest.json').read_text())
    inventory = json.loads((ROOT / 'Art/Export/BenmoreB1/inventory.json').read_text())
    cams = [(c['label'], c['loc'][0] / 100.0, c['loc'][1] / 100.0) for c in inventory['cameras']]

    def nearest_camera(x, y):
        best = min(cams, key=lambda c: (c[1] - x) ** 2 + (c[2] - y) ** 2)
        return best[0], round(math.hypot(best[1] - x, best[2] - y), 1)

    roads = []
    for ri, r in enumerate(manifest['routes']):
        pts = r['points']
        P = np.array([[p['x_m'], p['y_m']] for p in pts])
        A = np.array([p['arc_m'] for p in pts])
        L = r['length_m']
        # every 2 m (the manifest's own spacing)
        S = np.array([[bilinear(slope, x, y), bilinear(acc_full, x, y), bilinear(z, x, y)] for x, y in P])
        dbed = nearest(bed_pts, P)
        dlake = nearest(lake_pts, P)
        roads.append(dict(index=ri, name=r['name'], closed=r['closed'], width_m=r['width_m'], length_m=L, P=P, A=A, slope=S[:, 0], acc=S[:, 1],
                          z=S[:, 2], dbed=dbed, dlake=dlake))
    all_acc = np.concatenate([rd['acc'] for rd in roads])
    acc_q75 = float(np.percentile(all_acc, 75))
    land_acc_q95 = float(np.percentile(acc_full[~lake & (bed < 0.1)], 95))
    total_len = sum(rd['length_m'] for rd in roads)
    cap = 0.35 * total_len
    # Wetness per sample and its reasons.
    for rd in roads:
        creek = rd['dbed'] <= 40.0
        lakeflat = (rd['dlake'] <= 40.0) & (rd['slope'] < 3.0)
        flow = rd['acc'] >= acc_q75
        rd['wet'] = creek | lakeflat | flow
        rd['score'] = (np.clip(1.0 - rd['dbed'] / 40.0, 0, 1) * 3.0 + lakeflat * 2.0 + np.clip((rd['acc'] - acc_q75) / max(1e-6, all_acc.max() - acc_q75), 0, 1) * 1.0)
        rd['why'] = np.where(creek, 'creek', np.where(lakeflat, 'lake', np.where(flow, 'flow', '')))
    # Wet runs (contiguous wet samples, closed loops wrap), each 30 m at least (grown about its middle), scored by mean wetness.
    runs = []
    for rd in roads:
        wet = rd['wet']
        n = len(wet)
        i = 0
        while i < n:
            if not wet[i]:
                i += 1
                continue
            j = i
            while j + 1 < n and wet[j + 1]:
                j += 1
            a0, a1 = rd['A'][i], rd['A'][j] + 2.0
            if a1 - a0 < 30.0:
                mid = 0.5 * (a0 + a1)
                a0, a1 = max(0.0, mid - 15.0), min(rd['length_m'], mid + 15.0)
            sc = float(rd['score'][i:j + 1].mean())
            why = sorted(set(w for w in rd['why'][i:j + 1] if w))
            runs.append(dict(road=rd['index'], a0=float(a0), a1=float(a1), score=sc, why=why))
            i = j + 1
    runs.sort(key=lambda r: -r['score'])
    mud = []
    used = 0.0
    for r in runs:
        ln = r['a1'] - r['a0']
        if used + ln > cap:
            if cap - used >= 30.0:
                mid = 0.5 * (r['a0'] + r['a1'])
                ln = cap - used
                r = dict(r, a0=mid - 0.5 * ln, a1=mid + 0.5 * ln)
            else:
                continue
        if any(m['road'] == r['road'] and m['a0'] < r['a1'] + 30.0 and r['a0'] < m['a1'] + 30.0 for m in mud):
            continue   # keep 30 m of gravel between two mud runs (or they would join)
        mud.append(r)
        used += r['a1'] - r['a0']
    # Stretches per road: the mud runs cut into 30-60 m pieces, the gravel between into 30-120 m pieces.
    stretches = []
    for rd in roads:
        L = rd['length_m']
        cuts = sorted((m['a0'], m['a1'], m) for m in mud if m['road'] == rd['index'])
        spans = []
        pos = 0.0
        for a0, a1, m in cuts:
            if a0 > pos:
                spans.append(('gravel', pos, a0, None))
            spans.append(('mud', a0, a1, m))
            pos = a1
        if pos < L:
            spans.append(('gravel', pos, L, None))
        # a too-short gravel span folds into its neighbour mud span on a closed loop's seam or anywhere it is under 30 m
        merged = []
        for sp in spans:
            if sp[0] == 'gravel' and sp[2] - sp[1] < 30.0 and merged:
                k0, s0, e0, m0 = merged[-1]
                merged[-1] = (k0, s0, sp[2], m0)
                continue
            merged.append(sp)
        for kind, s0, e0, m in merged:
            ln = e0 - s0
            top = 60.0 if kind == 'mud' else 120.0
            pieces = max(1, math.ceil(ln / top))
            for p in range(pieces):
                stretches.append(dict(road=rd['index'], kind=kind, a0=round(s0 + ln * p / pieces, 2), a1=round(s0 + ln * (p + 1) / pieces, 2),
                                      why=m['why'] if m else []))
    # Gravel profile by B1's physical material across the road (benmore_reference_surface.TRACKS with the road's own lateral).
    def loose_share(rd, a0, a1):
        firm = loose = 0
        hw = rd['width_m'] * 0.5
        for a in np.arange(a0 + 1.0, a1, 4.0):
            i = int(np.clip(np.searchsorted(rd['A'], a), 1, len(rd['A']) - 1))
            px, py = rd['P'][i]
            dx, dy = rd['P'][i] - rd['P'][i - 1]
            nl = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / nl, dx / nl
            for lat in np.arange(-hw + 0.125, hw, 0.25):
                X, Y = px + nx * lat, py + ny * lat
                Pc = (X * 100.0, Y * 100.0)
                wander = .14 * math.sin(Pc[0] * .00071 + Pc[1] * .00113) + .10 * math.sin(Pc[1] * .0031) + .045 * math.sin(Pc[0] * .014 + Pc[1] * .009)
                lane = (1.05 + .88) * 0.5
                track = 1 - np.clip((abs(abs(lat - wander) - lane) - .18) / .32, 0, 1) ** 2 * (3 - 2 * np.clip((abs(abs(lat - wander) - lane) - .18) / .32, 0, 1))
                ct = np.clip((abs(lat) - .12) / .5, 0, 1)
                centre = 1 - ct * ct * (3 - 2 * ct)
                et = np.clip((abs(lat) - (hw - 1.1)) / .95, 0, 1)
                edge = et * et * (3 - 2 * et)
                lo = float(np.clip(.50 + .24 * centre + .38 * edge - .34 * track, .22, 1))
                if lo > 0.5:
                    loose += 1
                else:
                    firm += 1
        return loose / max(1, firm + loose)

    def line_for(rd, a0, a1, lead=15.0):
        """The road's own vertices from a0 - lead to a1 + lead (wrapping a closed loop), and the stretch's arcs on that line (m)."""
        A, P, L = rd['A'], rd['P'], rd['length_m']
        out = []
        for a in np.arange(a0 - lead, a1 + lead + 1e-6, 2.0):
            aa = a % L if rd['closed'] else min(max(a, 0.0), L)
            i = int(np.clip(np.searchsorted(A, aa), 1, len(A) - 1))
            t = (aa - A[i - 1]) / max(1e-6, A[i] - A[i - 1])
            q = P[i - 1] + (P[i] - P[i - 1]) * min(max(t, 0.0), 1.0)
            if not out or math.hypot(*(q - out[-1])) > 0.05:
                out.append(q)
        # the stretch's arc on its own line: the line starts lead m before a0 (unless clamped at an open road's start)
        start = (a0 - max(0.0, a0 - lead)) if not rd['closed'] else lead
        return [[round(p[0] * 100.0, 1), round(p[1] * 100.0, 1)] for p in out], start * 100.0, (start + (a1 - a0)) * 100.0

    zones = []
    zid = 1
    for st in stretches:
        rd = roads[st['road']]
        line, s0, s1 = line_for(rd, st['a0'], st['a1'])
        ls = loose_share(rd, st['a0'], st['a1']) if st['kind'] == 'gravel' else None
        key = lambda a: rd['index'] * 100000 + int(round((a % rd['length_m'] if rd['closed'] else a) * 10)) + 1
        mid_i = int(np.clip(np.searchsorted(rd['A'], 0.5 * (st['a0'] + st['a1'])), 0, len(rd['A']) - 1))
        mx, my = rd['P'][mid_i]
        zones.append(dict(id=zid, label='%s %.0f-%.0f m %s' % (rd['name'], st['a0'], st['a1'], 'MudRoad' if st['kind'] == 'mud' else 'gravel'),
                          shape='road', kind=st['kind'], road=rd['name'], a0_m=st['a0'], a1_m=st['a1'], length_m=round(st['a1'] - st['a0'], 2),
                          width_cm=rd['width_m'] * 100.0, line_cm=line, start_cm=round(s0, 1), end_cm=round(s1, 1),
                          start_key=0 if (not rd['closed'] and st['a0'] <= 0.01) else key(st['a0']),
                          end_key=0 if (not rd['closed'] and st['a1'] >= rd['length_m'] - 0.01) else key(st['a1']),
                          profile=None if ls is None else ('loose' if ls >= 0.5 else 'firm'), loose_share=None if ls is None else round(ls, 3),
                          why=st['why'], centre_m=[round(float(mx), 1), round(float(my), 1)], nearest_camera=nearest_camera(mx, my)))
        zid += 1
    # Bogs.
    near_road = np.zeros((N, N), bool)
    road_pts = np.concatenate([rd['P'] for rd in roads])
    for x, y in road_pts[::2]:
        c, r = to_px(x, y)
        r0, r1 = int(max(0, r - 25)), int(min(N, r + 26))
        c0, c1 = int(max(0, c - 25)), int(min(N, c + 26))
        near_road[r0:r1, c0:c1] = True
    # within 30 m of the road and off its band (+3 m)
    dist_road = np.full((N, N), 1e9)
    sub = np.argwhere(near_road)
    Pm = np.stack([xm[near_road], ym[near_road]], 1)
    dr = nearest(road_pts[::2], Pm)
    dist_road[near_road] = dr
    wl = {rd['name']: rd['width_m'] for rd in roads}
    off_band = dist_road > max(wl.values()) * 0.5 + 3.0
    dbed_grid = np.full((N, N), 1e9)
    dbed_grid[near_road] = nearest(bed_pts, Pm)
    dlake_grid = np.full((N, N), 1e9)
    dlake_grid[near_road] = nearest(lake_pts, Pm)
    vegsum = veg.sum(-1)
    # wet: near the bed or the lake, or within 10 m of a drainage line (the accumulation's top 5 % of the land: the lines are a cell or
    # two wide, so a bog is the flat ground beside one)
    lines = acc_full >= land_acc_q95
    wet_line = lines.copy()
    rad = int(10.0 / PX)
    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            if dx * dx + dy * dy > rad * rad or (dx == 0 and dy == 0):
                continue
            wet_line[max(0, dy):N + min(0, dy), max(0, dx):N + min(0, dx)] |= lines[max(0, -dy):N + min(0, -dy), max(0, -dx):N + min(0, -dx)]
    wet_cell = (dbed_grid <= 40.0) | wet_line | (dlake_grid <= 40.0)
    cand = near_road & (dist_road <= 30.0) & off_band & (slope < 4.0) & wet_cell & (bed < 0.1) & ~lake & (z > 0.6)
    # connected regions (4-neighbour flood fill)
    lab = np.zeros((N, N), int)
    regions = []
    for r, c in np.argwhere(cand):
        if lab[r, c]:
            continue
        stack = [(r, c)]
        lab[r, c] = len(regions) + 1
        cells = []
        while stack:
            a, b = stack.pop()
            cells.append((a, b))
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                aa, bb = a + da, b + db
                if 0 <= aa < N and 0 <= bb < N and cand[aa, bb] and not lab[aa, bb]:
                    lab[aa, bb] = lab[r, c]
                    stack.append((aa, bb))
        regions.append(np.array(cells))
    mud_mid = [(z_['centre_m'], z_['id']) for z_ in zones if z_['kind'] == 'mud']
    bogs = []
    for cells in regions:
        area = len(cells) * PX * PX
        if area < 150.0:
            continue
        X = xm[cells[:, 0], cells[:, 1]]
        Y = ym[cells[:, 0], cells[:, 1]]
        cx, cy = float(X.mean()), float(Y.mean())
        cov = np.cov(np.stack([X - cx, Y - cy]))
        w, vec = np.linalg.eigh(cov)
        major = vec[:, 1]
        yaw = math.degrees(math.atan2(major[1], major[0]))
        # the outline wobbles to 1.16 x its box (AGTDeformZone::BlobEdgeNoise 0.16): the box's half at most 17.2 m keeps a bog 40 m across
        rx = float(np.clip(2.0 * math.sqrt(max(w[1], 1e-6)), 7.5, 17.2))
        ry = float(np.clip(2.0 * math.sqrt(max(w[0], 1e-6)), 7.5, 17.2))
        # shrink until 90 % of the blob lies on candidate cells (an ellipse test on the height grid)
        for _ in range(12):
            ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
            c0, r0 = to_px(cx, cy)
            rr = int(max(rx, ry) / PX) + 2
            inside = ok = 0
            for dr_ in range(-rr, rr + 1):
                for dc_ in range(-rr, rr + 1):
                    a, b = int(round(r0)) + dr_, int(round(c0)) + dc_
                    if not (0 <= a < N and 0 <= b < N):
                        continue
                    lx = (xm[a, b] - cx) * ca + (ym[a, b] - cy) * sa
                    ly = -(xm[a, b] - cx) * sa + (ym[a, b] - cy) * ca
                    if (lx / rx) ** 2 + (ly / ry) ** 2 <= 1.0:
                        inside += 1
                        ok += 1 if cand[a, b] else 0
            if inside and ok / inside >= 0.9:
                break
            rx, ry = max(7.5, rx * 0.88), max(7.5, ry * 0.88)
        if not inside or ok / inside < 0.9 or math.pi * rx * ry < 150.0:
            continue
        c0, r0 = to_px(cx, cy)
        a, b = int(round(r0)), int(round(c0))
        win = (slice(max(0, a - int(ry / PX)), a + int(ry / PX) + 1), slice(max(0, b - int(rx / PX)), b + int(rx / PX) + 1))
        near_water = float(min(dbed_grid[a, b], dlake_grid[a, b]))
        mud_near = min((math.hypot(m[0][0] - cx, m[0][1] - cy) for m in mud_mid), default=1e9)
        bogs.append(dict(centre_m=[round(cx, 1), round(cy, 1)], z_m=round(float(z[a, b]), 2), yaw_deg=round(yaw, 1), half_m=[round(rx, 1), round(ry, 1)],
                         area_m2=round(math.pi * rx * ry, 1), region_m2=round(area, 1), slope_max_deg=round(float(slope[win].max()), 2),
                         slope_mean_deg=round(float(slope[win].mean()), 2), to_road_m=round(float(dist_road[a, b]), 1), to_water_m=round(near_water, 1),
                         to_mudroad_m=round(mud_near, 1), vegetation=round(float(vegsum[win].mean()), 3), flow_log=round(float(acc_full[a, b]), 2),
                         nearest_camera=nearest_camera(cx, cy)))
    # sparsest vegetation and MudRoad-adjacent first, then wetness; 80 m apart; at most 6
    bogs.sort(key=lambda b: (b['vegetation'] > 0.6, b['to_mudroad_m'] > 120.0, b['vegetation'], b['to_water_m']))
    chosen = []
    for b in bogs:
        if len(chosen) >= 6:
            break
        if any(math.hypot(b['centre_m'][0] - c['centre_m'][0], b['centre_m'][1] - c['centre_m'][1]) < 80.0 for c in chosen):
            continue
        chosen.append(b)
    for n, b in enumerate(chosen):
        if b['to_water_m'] <= 40.0:
            b['variant'] = 'Deep' if b['to_water_m'] <= 15.0 else 'Standard'
        else:
            b['variant'] = 'Stony' if n % 2 else 'Firm'
        b['id'] = zid
        b['label'] = 'Bog %d (%s)' % (n + 1, b['variant'])
        zid += 1
    # The landscape grass grows from T_RL_Vegetation and would stand up through a bog's mud: a copy with each bog's inner 70 % (B2c: the
    # tussocks encroach on the rim) painted out, feathered over 2 m, for setup_benmore_b2 to swap into M_GC_Terrain. And the coverage
    # texture's default (black, linear) for the material's parameter.
    vimg = np.asarray(Image.open(GAEA / 'Morphology/T_RL_Vegetation.png').convert('RGBA')).astype(np.float64)
    keep = np.ones((N, N))
    for b in chosen:
        ca, sa = math.cos(math.radians(b['yaw_deg'])), math.sin(math.radians(b['yaw_deg']))
        lx = (xm - b['centre_m'][0]) * ca + (ym - b['centre_m'][1]) * sa
        ly = -(xm - b['centre_m'][0]) * sa + (ym - b['centre_m'][1]) * ca
        rx, ry = b['half_m'][0] * 0.7, b['half_m'][1] * 0.7
        rho = np.sqrt((lx / rx) ** 2 + (ly / ry) ** 2)
        edge = np.clip((rho - 1.0) * min(rx, ry) / 2.0 + 0.5, 0.0, 1.0)
        keep = np.minimum(keep, edge * edge * (3 - 2 * edge))
    vout = vimg.copy()
    vout[..., :3] *= keep[..., None]
    Image.fromarray(np.clip(np.round(vout), 0, 255).astype(np.uint8), 'RGBA').save(OUT / 'T_RL_Vegetation_B2.png')
    Image.fromarray(np.zeros((4, 4, 4), np.uint8), 'RGBA').save(OUT / 'T_GT_DeformCoverageNone.png')
    mud_len = sum(z_['length_m'] for z_ in zones if z_['kind'] == 'mud')
    plan = dict(ok=True, note=__doc__.split('\n\n')[0], total_road_m=round(total_len, 1), mud_cap_m=round(cap, 1), mud_m=round(mud_len, 1),
                mud_share=round(mud_len / total_len, 4), accumulation_road_q75_log=round(acc_q75, 3), accumulation_land_q95_log=round(land_acc_q95, 3),
                flow_mask_fact='T_Gaea_Flow: RG a direction field, A the slope steepness (bed mean A 7.4 vs 29.9 elsewhere): not an accumulation',
                zones=zones, bogs=chosen, bog_candidates=len(bogs), regions=len(regions),
                gravel=dict(loose=sum(1 for z_ in zones if z_['profile'] == 'loose'), firm=sum(1 for z_ in zones if z_['profile'] == 'firm'),
                            loose_share_range=[min((z_['loose_share'] for z_ in zones if z_['loose_share'] is not None), default=None),
                                               max((z_['loose_share'] for z_ in zones if z_['loose_share'] is not None), default=None)]))
    (OUT / 'plan.json').write_text(json.dumps(plan, indent=1))
    print(json.dumps({k: v for k, v in plan.items() if k not in ('zones', 'bogs', 'note')}, indent=1))
    for z_ in zones:
        if z_['kind'] == 'mud':
            print('MUD', z_['id'], z_['label'], z_['why'], z_['nearest_camera'])
    for b in chosen:
        print('BOG', b)


if __name__ == '__main__':
    main()
