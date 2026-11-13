"""Benmore integration B2b (docs/BENMORE_INTEGRATION_PLAN.md, "B2 addendum", Pictures): the deform zones on L_Benmore_GaeaReview,
rendered (Art/benmore_b2.ps1 -Step capture: a -RenderOffScreen editor at a fixed 1/60 s step, Play In Editor in a 1440 x 900 window, the
Clear weather, dry). The sun behind every camera where the road allows. Writes Art/Export/BenmoreB2/capture.json and:
  B2_Bog_<n>.png     each bog before driving, on foot (1.7 m) 12 m off its outline, looking at its middle;
  B2_Road_Mud.png    on foot (1.7 m) on a MudRoad stretch, looking along it;
  B2_Edge.png        close (1.5 m up, 6 m off) across a live gravel tile's border: its patch against Codex's road gravel beyond the last
                     live tile (only the tile under the camera live: ZoneActivateCm 100 cm, the cap 1) and the verge's landscape;
  B2_Top.png         a MudRoad stretch and the gravel either side from 30 m up;
  B2_Road_Gravel.png the possessed car at about 30 km/h along a gravel run heading with the sun, the chase camera low behind it, the ruts
                     forming (and B2_Road_Gravel_NoDust.png the same frame with the car's Niagara hidden and gt.SurfaceEffects 0).
Each picture's row holds UGTMudSubsystem::DescribeZones at the capture (the live units, cells, cache bytes, coverage texels). Saves
nothing. No timing."""
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/BenmoreB2'
LEVEL = '/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
VIEW = (1440, 900)
PLAN = json.loads((OUT / 'plan.json').read_text())
ROADS = {r['name']: r for r in json.loads((ROOT / 'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']}
# GT_B2_ONLY: a comma list of the scenarios to take (bogs, mud, top, edge, gravel; all when empty), the report then written as
# capture_<list>.json (a retake of some keeps the full run's capture.json).
ONLY = [n for n in os.environ.get('GT_B2_ONLY', '').split(',') if n]
# GT_B2_ONLY triage (Benmore triage): the B2 cameras again and the Terrace loop join on foot, into Art/Export/BenmoreTriage.
TRIAGE = 'triage' in ONLY
PICS = ROOT / 'Art/Export/BenmoreTriage' if TRIAGE else OUT
TRIAGE_SOURCES = [('B2_Bog_1', 'capture_b2c.json'), ('B2_Bog_3', 'capture_b2c.json'), ('B2_Road_Mud', 'capture_b2c.json'), ('B2_Top', 'capture_b2c.json'),
                  ('B2_MudFar', 'capture_b2c.json'), ('B2_Edge', 'capture_b2c_edge.json'), ('B2_Road_Gravel', 'capture_edge_gravel.json')]
u.EditorPythonScripting.set_keep_python_script_alive(True)
report = dict(ok=False, level=LEVEL, timings_collected=False, pictures=[])
world = pc = car = move = mud = camera = None
L = Lh = None


def gs():
    return u.GameplayStatics.get_time_seconds(world)


def console(cmd):
    u.SystemLibrary.execute_console_command(world, cmd, pc)


def unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.
    return tuple(c / n for c in v)


def ground(x, y):
    res = u.GTSurfaceQueryLibrary.trace_landscape_surface(world, u.Vector(x, y, 60000.), u.Vector(x, y, -60000.))
    point = res[1] if isinstance(res, tuple) else None
    return point.z if point else 0.


def surface_z(x, y):
    """The ground plus the live mud field there (the mud's surface, cm)."""
    return ground(x, y) + mud.mud_height_cm_at(u.Vector2D(x, y))


def aim(eye, target, fov):
    pos = u.Vector(*eye)
    camera.set_actor_location(pos, False, False)
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos, u.Vector(*target)), False)
    camera.camera_component.set_field_of_view(fov)
    return dict(eye=[round(c) for c in eye], target=[round(c) for c in target], fov=fov,
                sun_angle_deg=round(math.degrees(math.acos(max(-1., min(1., sum(a * b for a, b in zip(unit(tuple(t - e for t, e in zip(target, eye))), L)))))), 1))


def wait(seconds):
    t0 = gs()
    while gs() - t0 < seconds:
        yield


def shot(path):
    t = time.time()
    console('HighResShot %dx%d filename="%s"' % (VIEW[0], VIEW[1], path.as_posix()))
    t1 = time.monotonic()
    while not (path.exists() and path.stat().st_mtime >= t - 0.5 and time.monotonic() - t1 > 1.5):
        if time.monotonic() - t1 > 60.:
            raise RuntimeError('no capture written: ' + path.name)
        yield


def focus(x, y, z):
    mud.set_zone_focus_for_test(u.Vector(x, y, z), True)
    mud.stream_zones_now()


def capture(name, view, extra):
    yield from wait(1.5)   # the patch's first uploads and the coverage texture
    row = dict(name=name, image=str(PICS / (name + '.png')), view=view, zones=json.loads(mud.describe_zones()))
    row.update(extra)
    report['pictures'].append(row)
    yield from shot(PICS / (name + '.png'))
    row['written'] = True


def road_point(road, arc_m):
    """(x, y) cm and the unit heading at arc_m along a road (wrapping a closed one)."""
    r = ROADS[road]
    pts = r['points']
    a = arc_m % r['length_m'] if r['closed'] else min(max(arc_m, 0.), r['length_m'])
    i = next((k for k in range(1, len(pts)) if pts[k]['arc_m'] >= a), len(pts) - 1)
    p0, p1 = pts[i - 1], pts[i]
    t = (a - p0['arc_m']) / max(1e-6, p1['arc_m'] - p0['arc_m'])
    x = (p0['x_m'] + (p1['x_m'] - p0['x_m']) * t) * 100.
    y = (p0['y_m'] + (p1['y_m'] - p0['y_m']) * t) * 100.
    return (x, y), unit((p1['x_m'] - p0['x_m'], p1['y_m'] - p0['y_m']))


def zone_kind(road, arc_m):
    r = ROADS[road]
    a = arc_m % r['length_m'] if r['closed'] else arc_m
    for z in PLAN['zones']:
        if z['road'] == road and z['a0_m'] <= a < z['a1_m']:
            return z['kind']
    return None


def park_car_away():
    """The car (kept possessed: the controller would put the on-foot character in its place) parked on open ground 150 m or more from
    every zone, braked, its input off; the camera is the view target."""
    pts = [(p[0], p[1]) for z in PLAN['zones'] for p in z['line_cm'][::5]] + [(b['centre_m'][0] * 100., b['centre_m'][1] * 100.) for b in PLAN['bogs']]
    spot = None
    for gy in range(-8, 9):
        for gx in range(-8, 9):
            x, y = gx * 12000., gy * 12000.
            d = min(math.hypot(x - a, y - b) for a, b in pts)
            if d > 15000. and (spot is None or abs(x) + abs(y) < abs(spot[0]) + abs(spot[1])):
                spot = (x, y, d)
    x, y, d = spot
    report['car_parked_cm'] = [round(x), round(y), round(d)]
    car.reset_driving_inputs()
    move.set_throttle_input(0.)
    move.set_brake_input(1.)
    move.set_handbrake_input(True)
    car.set_actor_location_and_rotation(u.Vector(x, y, ground(x, y) + 150.), u.Rotator(0., 0., 0.), False, True)
    body = car.get_component_by_class(u.SkeletalMeshComponent)
    body.set_physics_linear_velocity(u.Vector())
    body.set_physics_angular_velocity_in_degrees(u.Vector())


def bog_views():
    for n, b in enumerate(PLAN['bogs']):
        cx, cy = b['centre_m'][0] * 100., b['centre_m'][1] * 100.
        rx = b['half_m'][0] * 100.
        # Stand on the sun's side, looking with the sun at the middle: 12 m beyond the outline along the long axis or across it,
        # whichever is nearer the sun's direction.
        back = (-Lh[0], -Lh[1])
        d = (rx * 1.16 + 1200.)
        ex, ey = cx + back[0] * d, cy + back[1] * d
        ez = ground(ex, ey) + 170.
        view = aim((ex, ey, ez), (cx, cy, ground(cx, cy)), 65.)
        focus(cx, cy, ez)
        yield from capture('B2_Bog_%d' % (n + 1), view, dict(bog=dict(label=b['label'], centre_m=b['centre_m'], half_m=b['half_m'], variant=b['variant'],
                                                                        nearest_camera=b['nearest_camera'])))


def mud_view():
    muds = [z for z in PLAN['zones'] if z['kind'] == 'mud']
    best = None
    for z in muds:
        mid = 0.5 * (z['a0_m'] + z['a1_m'])
        for d in (1., -1.):
            (_, _), h = road_point(z['road'], mid)
            h = (h[0] * d, h[1] * d)
            dev = math.degrees(math.acos(max(-1., min(1., h[0] * Lh[0] + h[1] * Lh[1]))))
            if best is None or dev < best[0]:
                best = (dev, z, d)
    dev, z, d = best
    start = z['a0_m'] + 2. if d > 0 else z['a1_m'] - 2.
    (ex, ey), h = road_point(z['road'], start)
    h = (h[0] * d, h[1] * d)
    (tx, ty), _ = road_point(z['road'], start + d * 14.)
    ez = ground(ex, ey) + 170.
    view = aim((ex, ey, ez), (tx, ty, ground(tx, ty)), 65.)
    focus(ex, ey, 0.)
    yield from capture('B2_Road_Mud', view, dict(zone=z['label'], sun_heading_deviation_deg=round(dev, 1)))
    report['mud_zone'] = z['label']


def top_view():
    z = next(z for z in PLAN['zones'] if z['label'] == report.get('mud_zone')) if report.get('mud_zone') else next(z for z in PLAN['zones'] if z['kind'] == 'mud')
    mid = 0.5 * (z['a0_m'] + z['a1_m'])
    (cx, cy), h = road_point(z['road'], mid)
    gz = ground(cx, cy)
    eye = (cx - Lh[0] * 1200., cy - Lh[1] * 1200., gz + 3000.)
    view = aim(eye, (cx, cy, gz), 70.)
    focus(cx, cy, 0.)
    yield from capture('B2_Top', view, dict(zone=z['label']))


def edge_view():
    """Only the tile under the camera live: the camera 6 m inside a gravel tile from its border on the road, looking across it."""
    mud.set_editor_property('zone_activate_cm', 100.)
    mud.set_editor_property('zone_release_cm', 150.)
    mud.set_editor_property('max_active_zone_tiles', 1)
    tile = 2400.
    for z in PLAN['zones']:
        if z['kind'] != 'gravel' or z['length_m'] < 60.:
            continue
        for a in range(int(z['a0_m']) + 10, int(z['a1_m']) - 10, 2):
            (x, y), h = road_point(z['road'], a)
            (x2, y2), _ = road_point(z['road'], a + 2.)
            # the road crosses a tile border between a and a + 2 m
            if math.floor(x / tile) == math.floor(x2 / tile) and math.floor(y / tile) == math.floor(y2 / tile):
                continue
            (ex, ey), _ = road_point(z['road'], a - 6.)
            # the eye 6 m back in the tile, 1.5 m up, off to the side by 1.2 m, looking at the border on the road and past it
            ex, ey = ex - h[1] * 120., ey + h[0] * 120.
            ez = ground(ex, ey) + 150.
            (tx, ty), _ = road_point(z['road'], a + 4.)
            view = aim((ex, ey, ez), (tx, ty, ground(tx, ty)), 60.)
            focus(ex, ey, 0.)
            yield from capture('B2_Edge', view, dict(zone=z['label'], border_arc_m=a + 1))
            mud.set_editor_property('zone_activate_cm', 4000.)
            mud.set_editor_property('zone_release_cm', 6000.)
            mud.set_editor_property('max_active_zone_tiles', 9)
            return
    raise RuntimeError('no tile border on a gravel stretch')


def gravel_drive():
    """The Terrace loop: a gravel run (no mud zone) heading with the sun, the straightest first; the car placed 70 m before the
    capture point; up to three runs (the scripted car can leave its path, as in B1b)."""
    road = 'Terrace loop'
    r = ROADS[road]
    cands = []
    for a in range(0, int(r['length_m']), 4):
        for d in (1., -1.):
            if any(zone_kind(road, a + d * k) != 'gravel' for k in range(-75, 31, 5)):
                continue
            hs = [road_point(road, a + d * k)[1] for k in range(-70, 31, 5)]
            dev = max(math.degrees(math.acos(max(-1., min(1., h[0] * d * Lh[0] + h[1] * d * Lh[1])))) for h in hs[-9:])
            bend = max(math.degrees(math.acos(max(-1., min(1., hs[i][0] * hs[i + 1][0] + hs[i][1] * hs[i + 1][1])))) for i in range(len(hs) - 1))
            cands.append((dev + 2. * bend, dev, bend, a, d))
    cands.sort()
    tries = []
    for score, dev, bend, a, d in cands:
        if len(tries) >= 3:
            break
        if any(abs(a - t) < 60 for t in tries):
            continue
        tries.append(a)
        try:
            yield from drive_once(road, a, d, dev, bend, len(tries))
            return
        except RuntimeError as e:
            report.setdefault('drive_failures', []).append(str(e))
            u.GameplayStatics.set_game_paused(world, False)
            move.set_throttle_input(0.)
            move.set_brake_input(1.)
    raise RuntimeError('gravel drive: every run left its path: %s' % report.get('drive_failures'))


def drive_once(road, a, d, dev, bend, attempt):
    path = [road_point(road, a + d * k)[0] for k in range(-70, 32, 2)]
    mud.set_zone_focus_for_test(u.Vector(), False)
    x0, y0 = path[0]
    f = unit((path[1][0] - x0, path[1][1] - y0))
    car.reset_driving_inputs()
    move.set_throttle_input(0.)
    move.set_brake_input(1.)
    move.set_handbrake_input(True)
    car.set_actor_location_and_rotation(u.Vector(x0, y0, ground(x0, y0) + 120.), u.Rotator(yaw=math.degrees(math.atan2(f[1], f[0]))), False, True)
    body = car.get_component_by_class(u.SkeletalMeshComponent)
    body.set_physics_linear_velocity(u.Vector())
    body.set_physics_angular_velocity_in_degrees(u.Vector())

    def chase():
        loc, fv = car.get_actor_location(), car.get_actor_forward_vector()
        fh = unit((fv.x, fv.y))
        rv = (-fh[1], fh[0])
        gz = ground(loc.x, loc.y)
        ax, ay = loc.x - fh[0] * 115., loc.y - fh[1] * 115.
        eye = (ax - fh[0] * 650. + rv[0] * 160., ay - fh[1] * 650. + rv[1] * 160., gz + 210.)
        return aim(eye, (ax - fh[0] * 150., ay - fh[1] * 150., gz + 40.), 70.)
    t0 = gs()
    while gs() - t0 < 2.5:
        chase()
        yield
    car.get_drivetrain().set_low_range(False)
    car.get_drivetrain().set_diff_lock(False)
    car.reset_driving_inputs()
    move.set_handbrake_input(False)
    move.set_brake_input(0.)
    move.set_target_gear(1, True)
    t0 = gs()
    idx, track, next_s = 0, [], 0.
    target = 7.
    while True:
        p = car.get_actor_location()
        speed = car.get_velocity().length() / 100.
        idx = min(range(max(0, idx - 3), min(len(path) - 1, idx + 25)), key=lambda k: (path[k][0] - p.x) ** 2 + (path[k][1] - p.y) ** 2)
        pa, pb = path[idx], path[min(idx + 1, len(path) - 1)]
        tx, ty = unit((pb[0] - pa[0], pb[1] - pa[1]))
        cte = ((p.x - pa[0]) * -ty + (p.y - pa[1]) * tx) / 100.
        psi = (math.atan2(ty, tx) - math.radians(car.get_actor_rotation().yaw) + math.pi) % (2 * math.pi) - math.pi
        steer = max(-1., min(1., (psi - math.atan2(1.5 * cte, speed + 1.)) / math.radians(35)))
        car.set_raw_steer(steer)
        move.set_throttle_input(max(0., min(1., (target - speed) * .3 + .35)))
        move.set_brake_input(max(0., min(.6, (speed - target - .8) * .3)))
        view = chase()
        if gs() - t0 >= next_s:
            track.append([round(gs() - t0, 1), idx, round(cte, 2), round(math.degrees(psi), 1), round(steer, 2), round(speed, 1)])
            next_s += .5
        if abs(cte) > 10. or gs() - t0 > 60.:
            report.setdefault('failed_tracks', []).append(dict(attempt=attempt, start_arc_m=a - d * 70., direction=d, track=track))
            raise RuntimeError('attempt %d: left the path or stalled (%.1f m off, %.1f m/s)' % (attempt, cte, speed))
        if idx >= 35 and speed >= 6.:
            break
        yield
    u.GameplayStatics.set_game_paused(world, True)
    row = dict(name='B2_Road_Gravel', image=str(OUT / 'B2_Road_Gravel.png'), view=view, zones=json.loads(mud.describe_zones()),
               speed_mps=round(speed, 2), sun_heading_deviation_deg=round(dev, 1), largest_bend_deg=round(bend, 1), start_arc_m=a - d * 70.,
               direction=d, attempt=attempt, track=track, lowered_cm3=round(mud.total_lowered_cm3()),
               wheels=[dict(sinkage_cm=round(w.get_editor_property('Sinkage') * 100., 2), in_patch=bool(w.get_editor_property('bInMudPatch')),
                            profiled=bool(w.get_editor_property('bInProfiledPatch'))) for w in car.get_traction().wheels])
    report['pictures'].append(row)
    yield from shot(OUT / 'B2_Road_Gravel.png')
    row['written'] = True
    console('gt.SurfaceEffects 0')
    sprites = [c for c in car.get_components_by_class(u.NiagaraComponent) if c.is_visible()]
    for act in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):   # GPT's surface effects (PIE only; the map is not touched)
        if act.get_class().get_name().startswith('GTVehicleSurfaceEffects'):
            sprites += [c for c in act.get_components_by_class(u.NiagaraComponent) if c.is_visible()]
    for c in sprites:
        c.set_visibility(False)
    yield from shot(OUT / 'B2_Road_Gravel_NoDust.png')
    row['no_dust'] = dict(image=str(OUT / 'B2_Road_Gravel_NoDust.png'), niagara_hidden=len(sprites))
    u.GameplayStatics.set_game_paused(world, False)
    move.set_throttle_input(0.)
    move.set_brake_input(1.)



# ---- Benmore B2c (docs/BENMORE_INTEGRATION_PLAN.md B2c item 6): the retakes with B2's own cameras, the edge's colour strips, B2_MudFar ----
def recorded(name, source):
    """A B2 picture's camera (eye, target, fov) from its capture report."""
    r = json.loads((OUT / source).read_text())
    row = next(x for x in r['pictures'] if x['name'] == name)
    return row['view'], row


def screen(x, y, z):
    """A world point in the picture's pixels: the projection is in the game viewport's (the PIE window's client, about 1120 x 700 in the
    first B2c run), the picture HighResShot's VIEW, so the viewport's size scales it."""
    res = u.GameplayStatics.project_world_to_screen(pc, u.Vector(x, y, z), False)
    v = res[1] if isinstance(res, tuple) else res
    vp = u.WidgetLayoutLibrary.get_viewport_size(world)
    sx = VIEW[0] / vp.x if vp and vp.x > 1 else 1.
    sy = VIEW[1] / vp.y if vp and vp.y > 1 else 1.
    report['viewport_px'] = [round(vp.x), round(vp.y)] if vp else None
    return [round(v.x * sx, 1), round(v.y * sy, 1)] if v is not None else None


def relief(cx, cy, half=300.):
    """The live field's heights over a 6 m square at a bog's middle: what its patch displaces by."""
    h = list(mud.mud_cell_heights_cm(u.Vector2D(cx - half, cy - half), u.Vector2D(cx + half, cy + half)))
    if not h:
        return None
    m = sum(h) / len(h)
    sd = (sum((v - m) ** 2 for v in h) / len(h)) ** 0.5
    return dict(cells=len(h), min_cm=round(min(h), 2), max_cm=round(max(h), 2), mean_cm=round(m, 2), sd_cm=round(sd, 2))


def b2c_bogs():
    for n in (1, 3):
        view, _ = recorded('B2_Bog_%d' % n, 'capture_bogs.json')
        b = PLAN['bogs'][n - 1]
        cx, cy = b['centre_m'][0] * 100., b['centre_m'][1] * 100.
        aim(tuple(view['eye']), tuple(view['target']), view['fov'])
        focus(cx, cy, 0.)
        yield from capture('B2_Bog_%d' % n, dict(view, sun_angle_deg=view.get('sun_angle_deg')), dict(bog=dict(label=b['label'], centre_m=b['centre_m'])))
        report['pictures'][-1]['relief'] = relief(cx, cy)


def b2c_fixed(name, source):
    view, row = recorded(name, source)
    aim(tuple(view['eye']), tuple(view['target']), view['fov'])
    tx, ty = view['target'][0], view['target'][1]
    focus(tx, ty, 0.) if name != 'B2_Edge' else None
    return view, row


def b2c_mud():
    view, row = b2c_fixed('B2_Road_Mud', 'capture.json')
    yield from capture('B2_Road_Mud', view, dict(zone=row.get('zone')))


def b2c_top():
    view, row = b2c_fixed('B2_Top', 'capture.json')
    yield from capture('B2_Top', view, dict(zone=row.get('zone')))


def b2c_edge():
    """B2's edge camera; only the tile under the camera live; the 1 m strips either side of the tile's border across the road's middle
    three quarters projected to the screen (Art/benmore_b2_gate.py reads the picture there)."""
    view, row = recorded('B2_Edge', 'capture_edge_gravel.json')
    z = next(x for x in PLAN['zones'] if x['label'] == row['zone'])
    a = row['border_arc_m'] - 1
    (x0, y0), h = road_point(z['road'], a)
    (x1, y1), _ = road_point(z['road'], a + 2.)
    tile = 2400.
    if math.floor(x0 / tile) != math.floor(x1 / tile):
        bx = (math.floor(max(x0, x1) / tile)) * tile
        t = (bx - x0) / (x1 - x0)
        cx, cy = bx, y0 + (y1 - y0) * t
        b, nrm = (0., 1.), (1. if view['eye'][0] > bx else -1., 0.)
    else:
        by = (math.floor(max(y0, y1) / tile)) * tile
        t = (by - y0) / (y1 - y0)
        cx, cy = x0 + (x1 - x0) * t, by
        b, nrm = (1., 0.), (0., 1. if view['eye'][1] > by else -1.)
    hw = ROADS[z['road']]['width_m'] * 50.
    cross = abs(b[0] * h[1] - b[1] * h[0]) or 1.
    half = 0.75 * hw / cross
    mud.set_editor_property('zone_activate_cm', 100.)
    mud.set_editor_property('zone_release_cm', 150.)
    mud.set_editor_property('max_active_zone_tiles', 1)
    aim(tuple(view['eye']), tuple(view['target']), view['fov'])
    focus(view['eye'][0], view['eye'][1], 0.)
    yield from wait(1.5)
    strips = {}
    for side, sg in (('inside', 1.), ('outside', -1.)):
        quad = []
        for along, off in ((-half, 5.), (half, 5.), (half, 100.), (-half, 100.)):
            x = cx + b[0] * along + nrm[0] * off * sg
            y = cy + b[1] * along + nrm[1] * off * sg
            quad.append(screen(x, y, ground(x, y)))
        strips[side] = quad
    yield from capture('B2_Edge', view, dict(zone=row['zone'], border_cm=[round(cx), round(cy)], border_dir=b, inside_normal=nrm, strips_px=strips))
    # The same frame with no patch: the live patches hidden and the landscape's coverage window off (the landscape alone), the gate's
    # reference for the same pixels.
    hidden = list(u.GameplayStatics.get_all_actors_of_class(world, u.GTMudPatch))
    for a in hidden:
        a.set_actor_hidden_in_game(True)
    lands = u.GameplayStatics.get_all_actors_of_class(world, u.LandscapeProxy)
    for land in lands:
        land.set_landscape_material_vector_parameter_value('GTDeformWindow', u.LinearColor(0.0, 0.0, 1.0, 0.0))
    yield from wait(1.5)
    yield from shot(OUT / 'B2_Edge_NoPatch.png')
    report['pictures'][-1]['no_patch'] = dict(image=str(OUT / 'B2_Edge_NoPatch.png'), patches_hidden=len(hidden), landscapes=len(lands))
    for a in hidden:
        a.set_actor_hidden_in_game(False)
    zd = json.loads(mud.describe_zones())
    for land in lands:
        land.set_landscape_material_vector_parameter_value('GTDeformWindow', u.LinearColor(zd['coverage_origin'][0], zd['coverage_origin'][1],
                                                                                           zd['coverage_size'] * zd['coverage_texel_cm'], 1.0))
    mud.set_editor_property('zone_activate_cm', 4000.)
    mud.set_editor_property('zone_release_cm', 6000.)
    mud.set_editor_property('max_active_zone_tiles', 9)


def b2c_far():
    """B2_MudFar: the B2_Road_Mud stretch from about 110 m back along the road, 3 m up: no live patch there, the far maps' mud."""
    _, row = recorded('B2_Road_Mud', 'capture.json')
    z = next(x for x in PLAN['zones'] if x['label'] == row['zone'])
    mid = 0.5 * (z['a0_m'] + z['a1_m'])
    (mx, my), _ = road_point(z['road'], mid)
    best = None
    for d in (1., -1.):
        for k in range(30, 200, 2):
            (x, y), _ = road_point(z['road'], mid - d * k)
            dist = math.hypot(x - mx, y - my) / 100.
            if 100. <= dist <= 130.:
                back = (Lh[0] * (mx - x) + Lh[1] * (my - y)) / max(1., math.hypot(mx - x, my - y) )
                if best is None or back > best[0]:
                    best = (back, x, y, dist)
                break
    back, ex, ey, dist = best
    ez = ground(ex, ey) + 300.
    view = aim((ex, ey, ez), (mx, my, ground(mx, my)), 50.)
    focus(ex, ey, 0.)
    yield from capture('B2_MudFar', view, dict(zone=z['label'], distance_m=round(dist, 1)))
    report['pictures'][-1]['mud_zone_live'] = any(lv['label'] == z['label'] for lv in report['pictures'][-1]['zones']['live_units'])


def triage_surfaces():
    """The landscape's physical material across both roads (B1 check's table, three offsets): the surface types after the triage."""
    table = {}
    for r in ROADS.values():
        hw = r['width_m'] * 0.5
        for label, off in [('centre', 0.), ('edge-0.3m', hw - 0.3), ('grass+8m', hw + 8.)]:
            counts = {}
            for pt in r['points'][::12]:
                yaw = math.radians(pt['yaw'])
                for side in (1., -1.):
                    x = (pt['x_m'] - math.sin(yaw) * off * side) * 100.
                    y = (pt['y_m'] + math.cos(yaw) * off * side) * 100.
                    res = u.GTSurfaceQueryLibrary.trace_landscape_surface(world, u.Vector(x, y, 60000.), u.Vector(x, y, -60000.))
                    pm = res[0] if isinstance(res, tuple) else res
                    k = pm.get_name() if pm else 'none'
                    counts[k] = counts.get(k, 0) + 1
            table.setdefault(r['name'], {})[label] = counts
    report['surfaces'] = table


def triage_views():
    """Benmore triage: the B2 pictures' cameras (B2c's set, B2_Edge from its own retake, B2_Road_Gravel's chase camera as a still, the car
    parked away), then on foot (1.7 m, 1.2 m off the centreline) 9 m before the old join of the Terrace loop 222-252 m MudRoad zone and
    the gravel zone after it (251.9 m), looking 9 m past it, from the side with the sun behind."""
    triage_surfaces()
    for name, source in TRIAGE_SOURCES:
        view, _ = recorded(name, source)
        aim(tuple(view['eye']), tuple(view['target']), view['fov'])
        yield from capture('Triage_' + name, view, dict(camera_from=source))
    join = next(z for z in PLAN['zones'] if z['label'] == 'Terrace loop 222-252 m MudRoad')['a1_m']
    best = None
    for d in (1., -1.):
        (ex, ey), h = road_point('Terrace loop', join - 9. * d)
        (tx, ty), _ = road_point('Terrace loop', join + 9. * d)
        ex, ey = ex - h[1] * 120., ey + h[0] * 120.
        eye, target = (ex, ey, ground(ex, ey) + 170.), (tx, ty, ground(tx, ty))
        v = aim(eye, target, 65.)
        if best is None or v['sun_angle_deg'] < best[0]['sun_angle_deg']:
            best = (v, eye, target)
    view = aim(best[1], best[2], 65.)
    yield from capture('Triage_Join_OnFoot', view, dict(join_arc_m=join, zones_joined=['Terrace loop 222-252 m MudRoad', 'Terrace loop 252-307 m gravel']))


def run():
    global world, pc, car, move, mud, camera, L, Lh
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
    t = time.monotonic()
    while time.monotonic() - t < 10.:
        yield
    lib = getattr(u, 'GTPlayWindowLibrary', None)
    if not (lib and lib.request_play_in_new_window(*VIEW)):
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
    t = time.monotonic()
    while u.EditorLevelLibrary.get_game_world() is None:
        if time.monotonic() - t > 300.:
            raise RuntimeError('Play In Editor did not start')
        yield
    world = u.EditorLevelLibrary.get_game_world()
    t = time.monotonic()
    while time.monotonic() - t < 10.:
        yield
    pc = u.GameplayStatics.get_player_controller(world, 0)
    pawn = u.GameplayStatics.get_player_pawn(world, 0)
    cars = sorted(u.GameplayStatics.get_all_actors_of_class(world, u.GTCarPawn), key=lambda c: c.get_path_name())
    car = pawn if isinstance(pawn, u.GTCarPawn) else cars[0]
    pc.possess(car)
    car.disable_input(pc)
    move = car.get_chaos_movement()
    mud = next(o for o in u.ObjectIterator(u.GTMudSubsystem) if o.get_outer() == world)
    weather = next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer() == world)
    clear = weather.find_state('Clear')
    if clear:
        weather.set_state(clear, True)
    weather.set_wetness_for_test(0.)
    camera = u.GTVehicleSetupLibrary.spawn_actor_of_class(world, u.CameraActor, u.Transform(), 'B2Cam')
    camera.camera_component.set_constraint_aspect_ratio(False)
    for cmd in ('showhud',):
        console(cmd)

    def intensity(a):
        try:
            return a.get_component_by_class(u.DirectionalLightComponent).get_editor_property('intensity')
        except Exception:  # noqa: BLE001
            return 0.
    sun = max(u.GameplayStatics.get_all_actors_of_class(world, u.DirectionalLight), key=intensity)
    fv = sun.get_component_by_class(u.DirectionalLightComponent).get_forward_vector()
    L = unit((fv.x, fv.y, fv.z))
    Lh = unit((fv.x, fv.y))
    report.update(car=car.get_path_name(), sun=dict(actor=sun.get_actor_label(), direction=[round(c, 3) for c in L]),
                  zones_at_start=json.loads(mud.describe_zones()), zone_count=mud.get_zone_count(), unit_count=mud.get_zone_unit_count())
    park_car_away()
    pc.set_view_target_with_blend(camera, 0.)
    yield from wait(3.)
    scenarios = (('bogs', bog_views), ('mud', mud_view), ('top', top_view), ('edge', edge_view), ('gravel', gravel_drive))
    if 'b2c' in ONLY:
        scenarios = (('bogs', b2c_bogs), ('mud', b2c_mud), ('top', b2c_top), ('edge', b2c_edge), ('far', b2c_far))
    if TRIAGE:
        scenarios = (('triage', triage_views),)
    for name, fn in scenarios:
        if ONLY and ('b2c' not in ONLY or len(ONLY) > 1) and name not in ONLY:
            continue   # GT_B2_ONLY b2c: the B2c set; b2c,edge: of it the edge alone
        try:
            yield from fn()
        except Exception:  # noqa: BLE001
            report.setdefault('errors', {})[name] = traceback.format_exc()
            u.GameplayStatics.set_game_paused(world, False)
        yield from wait(0.5)
    report['zones_at_end'] = json.loads(mud.describe_zones())
    names = dict(bogs=['B2_Bog_%d' % (n + 1) for n in range(len(PLAN['bogs']))], mud=['B2_Road_Mud'], top=['B2_Top'], edge=['B2_Edge'],
                 gravel=['B2_Road_Gravel'])
    want = [w for k, v in names.items() if not ONLY or k in ONLY for w in v]
    if 'b2c' in ONLY:
        b2c = dict(bogs=['B2_Bog_1', 'B2_Bog_3'], mud=['B2_Road_Mud'], top=['B2_Top'], edge=['B2_Edge'], far=['B2_MudFar'])
        want = [w for k, v in b2c.items() if len(ONLY) == 1 or k in ONLY for w in v]
    if TRIAGE:
        want = ['Triage_' + n for n, _ in TRIAGE_SOURCES] + ['Triage_Join_OnFoot']
    got = [p['name'] for p in report['pictures'] if p.get('written')]
    report['ok'] = all(w in got for w in want)


def finish(error=None):
    if error:
        report['error'] = error
    elif not report['ok']:
        report['error'] = 'pictures missing: %s' % sorted(report.get('errors', {}))
    (PICS / 'capture.json' if TRIAGE else OUT / (('capture_%s.json' % '_'.join(ONLY)) if ONLY else 'capture.json')).write_text(json.dumps(report, indent=2))
    u.unregister_slate_post_tick_callback(handle)
    try:
        u.EditorLevelLibrary.editor_end_play()
    except Exception:  # noqa: BLE001
        pass
    u.SystemLibrary.quit_editor()


gen = run()
started = time.monotonic()
busy = False


def tick(dt):
    global busy
    if busy or gen is None:
        return
    busy = True
    try:
        if time.monotonic() - started > 3600.:
            raise RuntimeError('B2 capture timed out')
        next(gen)
    except StopIteration:
        finish()
    except Exception:  # noqa: BLE001
        finish(traceback.format_exc())
    finally:
        busy = False


handle = u.register_slate_post_tick_callback(tick)
