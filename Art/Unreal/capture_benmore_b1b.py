"""Benmore integration B1b / B1c (docs/BENMORE_INTEGRATION_PLAN.md): the wheel spray on Benmore's surface physical materials, rendered
(Art/benmore_b1b.ps1 -Stage <stage>: a -RenderOffScreen editor at a fixed 1/60 s step, Play In Editor in a 1440 x 900 window on
L_Benmore_GaeaReview, the possessed car driven by script; the Clear weather, dry). Three pictures, <stage>_... (GT_BENMORE_STAGE, default
B1c), the sun behind every camera:
  _Gravel_Chase  a chase view at about 40 km/h (11.1 m/s) on the Terrace loop's gravel, on a stretch heading with the sun;
  _Gravel_Close  a low side view of a rear wheel in a full-throttle launch, captured at the first frame from 1.2 s (by 2.2 s) with that
                 wheel on GravelLoose; its line from 0.5 m behind to 2 m ahead loose at the start, on a stretch across the sun; also at
                 MPC_GT_Spray DustFloorDisplay 1.5 and 4 (_Floor<v>, the same frame);
  _Verge         a chase view at about 30 km/h on the verge (FirmGround; no gravel spray expected), a path free of collision.
Each capture is of one paused frame, and again without the car's Niagara components (<name>_NoSprites.png). The report holds the live
particles per Niagara emitter, the CPU kinds, the clumps drawn, the speed, each wheel's physical material (the Chaos wheel state: what
the spray reads), surface tag, rates and flags, the physical materials the wheels touched over the drive, and the camera's sun angle.
Writes Art/Export/Benmore<stage>/capture.json and the PNGs. Saves nothing. No timing."""
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
STAGE = os.environ.get('GT_BENMORE_STAGE', 'B1c')   # the pictures' prefix and folder (B1b's were taken as B1b)
OUT = ROOT / ('Art/Export/Benmore' + STAGE)
# GT_BENMORE_ONLY: a comma list of the pictures to take (Gravel_Chase, Gravel_Close, Verge; all when empty), the report written as
# capture_<list>.json (a game open can make a run slow enough to need a second one for the rest).
ONLY = [n for n in os.environ.get('GT_BENMORE_ONLY', '').split(',') if n]
OUT.mkdir(parents=True, exist_ok=True)
LEVEL = '/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
VIEW = (1440, 900)
ROAD = json.loads((ROOT / 'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes'][0]
assert ROAD['name'] == 'Terrace loop'
PTS = [(p['x_m'] * 100., p['y_m'] * 100.) for p in ROAD['points']]   # about 2 m apart, closed
N = len(PTS)
HW = ROAD['width_m'] * 50.                                             # half width, cm
GRAVEL = {'PM_Benmore_GravelFirm', 'PM_Benmore_GravelLoose'}
FIRM = 'PM_Benmore_FirmGround'
CHASE = dict(back=450., up=130., lat=150., fov=70.)
u.EditorPythonScripting.set_keep_python_script_alive(True)
report = dict(ok=False, level=LEVEL, timings_collected=False, pictures=[])
world = pc = car = move = spray = weather = camera = None
L = Lh = None


def P(i):
    return PTS[i % N]


def heading(i, d):
    a, b = P(i - 2), P(i + 2)
    x, y = (b[0] - a[0]) * d, (b[1] - a[1]) * d
    n = math.hypot(x, y) or 1.
    return (x / n, y / n)


def ang2(a, b):
    return math.degrees(math.acos(max(-1., min(1., a[0] * b[0] + a[1] * b[1]))))


def unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.
    return tuple(c / n for c in v)


def gs():
    return u.GameplayStatics.get_time_seconds(world)


def console(cmd):
    u.SystemLibrary.execute_console_command(world, cmd, pc)


def surface(x, y):
    res = u.GTSurfaceQueryLibrary.trace_landscape_surface(world, u.Vector(x, y, 60000.), u.Vector(x, y, -60000.))
    pm, point = (res[0], res[1]) if isinstance(res, tuple) else (res, None)
    return (pm.get_name() if pm else None), (point.z if point else None)


def obstacle(x, y, z):
    """The first non-landscape collision on a vertical line 3 m over the ground to 20 cm under it (the name), or None."""
    hit = u.SystemLibrary.line_trace_single(world, u.Vector(x, y, z + 300.), u.Vector(x, y, z - 20.), u.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                            True, [car], u.DrawDebugTrace.NONE, True)
    if not hit:
        return None
    actor = next((v for v in hit.to_tuple() if isinstance(v, u.Actor)), None)
    return None if actor is None or isinstance(actor, u.LandscapeProxy) else actor.get_actor_label()


def tag_name(tag):
    for fn in (lambda: tag.get_editor_property('tag_name'), lambda: u.BlueprintGameplayTagLibrary.get_debug_string_from_gameplay_tag(tag)):
        try:
            return str(fn())
        except Exception:  # noqa: BLE001
            pass
    return str(tag)


def wheel_pm(i):
    st = u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))
    pm = next((v for v in st if isinstance(v, u.PhysicalMaterial)), None)
    return pm.get_name() if pm else None


def state(view):
    wheels = car.get_traction().wheels
    eye, tgt = view['eye'], view['target']
    v = unit((tgt[0] - eye[0], tgt[1] - eye[1], tgt[2] - eye[2]))
    return dict(
        niagara_live={'MudDroplets': spray.get_fine_live_count(0), 'GravelGrit': spray.get_fine_live_count(1),
                      'GravelDust': spray.get_fine_live_count(2)},
        cpu_live={k: spray.get_live_count(getattr(u.GTSprayKind, k.upper())) for k in ('Mud', 'Dust', 'Snow', 'Water')},
        clumps_drawn=spray.get_clumps_drawn(),
        speed_mps=round(car.get_velocity().length() / 100., 2),
        car_cm=[round(c) for c in car.get_actor_location().to_tuple()],
        camera=dict(eye=[round(c) for c in eye], target=[round(c) for c in tgt],
                    sun_angle_deg=round(math.degrees(math.acos(max(-1., min(1., sum(a * b for a, b in zip(v, L)))))), 1)),
        wheels=[dict(wheel=i, contact=bool(w.get_editor_property('bInContact')), phys_material=wheel_pm(i),
                     surface_tag=tag_name(w.get_editor_property('SurfaceTag')), gravel_patch=bool(w.get_editor_property('bInGravelPatch')),
                     slipping=bool(w.get_editor_property('bSlipping')),
                     rates_mud_grit_dust=[round(spray.get_fine_rate(i, e), 2) for e in range(3)]) for i, w in enumerate(wheels)],
        art=u.SystemLibrary.get_console_variable_int_value('gt.Spray.Art'),
        fine=u.SystemLibrary.get_console_variable_int_value('gt.Spray.Fine'),
        wetness=round(weather.get_wetness(), 3))


def aim(eye, target, fov):
    pos = u.Vector(*eye)
    camera.set_actor_location(pos, False, False)
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos, u.Vector(*target)), False)
    camera.camera_component.set_field_of_view(fov)
    return dict(eye=eye, target=target)


def chase_view():
    """Low behind the car (the P2b height): the eye CHASE back from the rear axle and out to the side, CHASE up from the rear contacts,
    looking at the ground 1.5 m behind the axle (the spray against the road ahead and the skyline, the car above it)."""
    loc, f = car.get_actor_location(), car.get_actor_forward_vector()
    fh = unit((f.x, f.y))
    r = (-fh[1], fh[0])
    zs = [w.contact_point.z for w in car.get_traction().wheels if abs(w.contact_point.z - loc.z) < 300.]
    gz = min(zs) if zs else loc.z - 50.
    ax, ay = loc.x - fh[0] * 115., loc.y - fh[1] * 115.
    eye = (ax - fh[0] * CHASE['back'] + r[0] * CHASE['lat'], ay - fh[1] * CHASE['back'] + r[1] * CHASE['lat'], gz + CHASE['up'])
    return aim(eye, (ax - fh[0] * 150., ay - fh[1] * 150., gz + 50.), CHASE['fov'])


def place(x, y, f):
    _, z = surface(x, y)
    car.reset_driving_inputs()
    move.set_throttle_input(0.)
    move.set_brake_input(1.)
    move.set_handbrake_input(True)
    car.set_actor_location_and_rotation(u.Vector(x, y, z + 150.), u.Rotator(yaw=math.degrees(math.atan2(f[1], f[0]))), False, True)
    body = car.get_component_by_class(u.SkeletalMeshComponent)
    body.set_physics_linear_velocity(u.Vector())
    body.set_physics_angular_velocity_in_degrees(u.Vector())


def settle(view_fn, seconds=2.):
    t0 = gs()
    while gs() - t0 < seconds:
        view_fn()
        yield


def release(high, diff_lock):
    car.get_drivetrain().set_low_range(not high)
    car.get_drivetrain().set_diff_lock(diff_lock)
    car.reset_driving_inputs()
    move.set_handbrake_input(False)
    move.set_brake_input(0.)
    move.set_target_gear(1, True)


def stop():
    move.set_throttle_input(0.)
    move.set_brake_input(1.)
    car.set_raw_steer(0.)


def shot(path):
    """One HighResShot of the paused frame to path; done when its file is fresh (and 1.5 s on)."""
    t = time.time()
    console('HighResShot %dx%d filename="%s"' % (VIEW[0], VIEW[1], path.as_posix()))
    t1 = time.monotonic()
    while not (path.exists() and path.stat().st_mtime >= t - 0.5 and time.monotonic() - t1 > 1.5):
        if time.monotonic() - t1 > 60.:
            raise RuntimeError('no capture written: ' + path.name)
        yield


def capture(name, view, extra, sweep=()):
    """The paused frame: the picture; again without the car's Niagara components (<name>_NoSprites, the sprites' mask); then, for each
    sweep value, the picture at MPC_GT_Spray DustFloorDisplay = value (<name>_Floor<value>), the default put back."""
    u.GameplayStatics.set_game_paused(world, True)
    row = dict(name=name, image=str(OUT / (name + '.png')), at_capture=state(view))
    row.update(extra)
    report['pictures'].append(row)
    yield from shot(OUT / (name + '.png'))
    row['written'] = True
    sprites = [c for c in car.get_components_by_class(u.NiagaraComponent) if c.is_visible()]
    for c in sprites:
        c.set_visibility(False)
    yield from shot(OUT / (name + '_NoSprites.png'))
    for c in sprites:
        c.set_visibility(True)
    row['no_sprites'] = dict(image=str(OUT / (name + '_NoSprites.png')), hidden=len(sprites))
    if sweep:
        mpc = u.load_asset('/Game/GrandTour/FX/MPC_GT_Spray')
        default = u.MaterialLibrary.get_scalar_parameter_value(world, mpc, 'DustFloorDisplay')
        row['floor_sweep'] = dict(default=default)
        for v in sweep:
            u.MaterialLibrary.set_scalar_parameter_value(world, mpc, 'DustFloorDisplay', v)
            f = OUT / ('%s_Floor%g.png' % (name, v))
            yield from shot(f)
            row['floor_sweep'][str(v)] = str(f)
        u.MaterialLibrary.set_scalar_parameter_value(world, mpc, 'DustFloorDisplay', default)
    u.GameplayStatics.set_game_paused(world, False)
    stop()


def drive(path, capture_at, target, min_speed, name, view_fn, extra):
    """A Stanley path follower along path (cm points in travel order, the car placed at its start): steer = the path's heading error
    + atan(1.5 x the cross-track error / (speed + 1)), over a nominal 35 deg lock. The capture once past capture_at at min_speed. A
    sample of the tracking every 0.5 s goes in the report."""
    release(True, False)
    t0 = gs()
    idx, touched, track, next_s = 0, {}, [], 0.
    while True:
        p = car.get_actor_location()
        speed = car.get_velocity().length() / 100.
        idx = min(range(max(0, idx - 3), min(len(path) - 1, idx + 25)), key=lambda k: (path[k][0] - p.x) ** 2 + (path[k][1] - p.y) ** 2)
        a, b = path[idx], path[idx + 1]
        tx, ty = unit((b[0] - a[0], b[1] - a[1]))
        cte = ((p.x - a[0]) * -ty + (p.y - a[1]) * tx) / 100.        # metres, positive: the car right of the path
        psi = (math.atan2(ty, tx) - math.radians(car.get_actor_rotation().yaw) + math.pi) % (2 * math.pi) - math.pi
        steer = max(-1., min(1., (psi - math.atan2(1.5 * cte, speed + 1.)) / math.radians(35)))
        car.set_raw_steer(steer)
        move.set_throttle_input(max(0., min(1., (target - speed) * .3 + .35)))
        move.set_brake_input(max(0., min(.6, (speed - target - .8) * .3)))
        if gs() - t0 >= next_s:
            track.append([round(gs() - t0, 1), idx, round(cte, 2), round(math.degrees(psi), 1), round(steer, 2), round(speed, 1)])
            next_s += .5
        if abs(cte) > 8. or abs(car.get_actor_rotation().roll) > 40.:
            report.setdefault('failed_tracks', {}).setdefault(name, []).append(track)
            raise RuntimeError('%s: left the path (%.1f m off, roll %.0f)' % (name, cte, car.get_actor_rotation().roll))
        if idx >= len(path) - 6 or gs() - t0 > 90.:
            report.setdefault('failed_tracks', {}).setdefault(name, []).append(track)
            raise RuntimeError('%s: path exhausted or stalled at %.1f m/s' % (name, speed))
        view = view_fn()
        if idx >= capture_at - 20:
            for i in range(4):
                pm = wheel_pm(i)
                touched[pm] = touched.get(pm, 0) + 1
        if idx >= capture_at and (speed >= min_speed or idx >= capture_at + 15):
            extra = dict(extra, wheel_ticks_by_material_last_40m=touched, drive_s=round(gs() - t0, 1), track=track)
            yield from capture(name, view, extra)
            return
        yield


def wheel_geometry():
    """The wheels' contacts in the car's frame (forward, right), cm, after a settle."""
    loc, f = car.get_actor_location(), car.get_actor_forward_vector()
    fh = unit((f.x, f.y))
    r = (-fh[1], fh[0])
    out = []
    for w in car.get_traction().wheels:
        c = w.contact_point
        dx, dy = c.x - loc.x, c.y - loc.y
        out.append((dx * fh[0] + dy * fh[1], dx * r[0] + dy * r[1]))
    return out


def candidates(window, runup, want_deg):
    """(score, i, d): the stretch at i in direction d whose headings over window (points before/after) are nearest want_deg from the
    sun's heading; the run-up within 60 deg of it."""
    out = []
    for d in (1, -1):
        for i in range(N):
            hs = [ang2(heading(i + d * k, d), Lh) for k in range(-window[0], window[1] + 1)]
            if runup and max(ang2(heading(i - d * k, d), Lh) for k in range(0, runup, 5)) > 60.:
                continue
            out.append((max(abs(h - want_deg) for h in hs), i, d))
    out.sort()
    return out


def scenario_chase():
    RUN, PAST = 60, 25
    tries = 0
    for score, i, d in candidates((15, PAST), RUN, 0.)[:80]:
        if score > 35. or tries >= 3:
            break
        if not all(surface(*P(i + d * k))[0] in GRAVEL for k in range(-RUN, PAST + 1, 2)):
            continue
        tries += 1
        path = [P(i + d * k) for k in range(-RUN, PAST + 10)]
        place(path[0][0], path[0][1], heading(i - d * RUN, d))
        yield from settle(chase_view)
        report['wheel_geometry_cm'] = [[round(a), round(b)] for a, b in wheel_geometry()]
        try:
            yield from drive(path, RUN, 11.1, 10.3, STAGE + '_Gravel_Chase', chase_view,
                             dict(stretch=dict(index=i, direction=d, sun_heading_deviation_deg=round(score, 1), attempt=tries)))
            return
        except RuntimeError:
            stop()
            if tries >= 3:
                raise
    raise RuntimeError('no gravel stretch heading with the sun (or every drive left it)')


def scenario_close():
    """The camera 2.8 m out from the camera-side rear wheel, over the road: that wheel on the crown or the far half (2.8 m from the near
    edge), the far wheels on the road, the wheel's line from 0.5 m behind to 2 m ahead on GravelLoose (where the launch takes it)."""
    geo = report.get('wheel_geometry_cm') or [[130, -80], [130, 80], [-130, -80], [-130, 80]]
    rear = sorted(geo, key=lambda g: g[0])[:2]
    track = abs(rear[0][1] - rear[1][1])
    side = (-Lh[0], -Lh[1])                               # the camera's side of the car: looking back along the sun
    found = None
    for score, i, d in candidates((5, 5), 0, 90.)[:300]:
        if score > 15.:
            break
        f = heading(i, d)
        r = (-f[1], f[0])
        sc = 1. if r[0] * side[0] + r[1] * side[1] > 0 else -1.
        wf, wl = next(g for g in rear if g[1] * sc > 0)
        for oc in range(int(-HW + 30 + track), int(HW - 300) + 1, 15):   # the wheel's offset toward the camera side
            o = oc * sc
            cx, cy = P(i)[0] + r[0] * (o - wl), P(i)[1] + r[1] * (o - wl)
            wx, wy = cx + f[0] * wf + r[0] * wl, cy + f[1] * wf + r[1] * wl
            if all(surface(wx + f[0] * b, wy + f[1] * b)[0] == 'PM_Benmore_GravelLoose' for b in (0., 100., 200., -50.)):
                za, zb = surface(*P(i - 5 * d))[1], surface(*P(i + 5 * d))[1]
                if za is not None and zb is not None and abs(zb - za) < 0.06 * 2000.:
                    found = (score, i, d, f, cx, cy, o, wl)
                    break
        if found:
            break
    if not found:
        raise RuntimeError('no loose gravel spot across the sun')
    score, i, d, f, cx, cy, o, wl = found
    sgn = 1. if wl > 0 else -1.
    st = {}

    def side_view():
        loc, fv, rv = car.get_actor_location(), car.get_actor_forward_vector(), car.get_actor_right_vector()
        rel = [((w.contact_point.x - loc.x) * fv.x + (w.contact_point.y - loc.y) * fv.y,
                (w.contact_point.x - loc.x) * rv.x + (w.contact_point.y - loc.y) * rv.y, k, w) for k, w in enumerate(car.get_traction().wheels)]
        _, _, k, w = min((x for x in rel if x[1] * sgn > 0), key=lambda x: x[0])
        st['wheel'] = k
        c = w.contact_point
        if (c.x - loc.x) ** 2 + (c.y - loc.y) ** 2 > 400. ** 2:
            c = u.Vector(loc.x - fv.x * 115. + rv.x * sgn * 78., loc.y - fv.y * 115. + rv.y * sgn * 78., loc.z - 40.)
        eye = (c.x + rv.x * sgn * 280. - fv.x * 60., c.y + rv.y * sgn * 280. - fv.y * 60., c.z + 50.)
        return aim(eye, (c.x - fv.x * 80., c.y - fv.y * 80., c.z + 40.), 60.)
    place(cx, cy, f)
    yield from settle(side_view)
    release(True, True)
    t0 = gs()
    while True:
        move.set_throttle_input(1.)
        car.set_raw_steer(0.)
        view = side_view()
        t = gs() - t0
        if t >= 2.2 or (t >= 1.2 and wheel_pm(st['wheel']) == 'PM_Benmore_GravelLoose'):
            break
        yield
    yield from capture(STAGE + '_Gravel_Close', view, dict(stretch=dict(index=i, direction=d, across_sun_deviation_deg=round(score, 1),
                                                                    wheel_offset_from_centre_cm=round(o), wheel_side='right' if sgn > 0 else 'left'),
                                                      camera_wheel=st['wheel'], launch_s=round(gs() - t0, 2)), sweep=(1.5, 4.0))


def verge_path(i, d, sv, run, past, off):
    """The verge path (cm points in travel order) beside stretch (i, d) on side sv, or None at the first fault: a surface not
    FirmGround, a cross slope over 40 cm across 2 m or a step over 80 cm in 4 m, a collision within 1.3 m of the line."""
    path = []
    for k in range(-run, past + 10):
        f = heading(i + d * k, d)
        path.append((P(i + d * k)[0] - f[1] * sv * off, P(i + d * k)[1] + f[0] * sv * off))
    for k in range(0, len(path) - 8, 2):
        x, y = path[k]
        f = heading(i + d * (k - run), d)
        pm, z = surface(x, y)
        if pm != FIRM or z is None:
            return None
        zl, zr, zn = surface(x + f[1] * 100., y - f[0] * 100.)[1], surface(x - f[1] * 100., y + f[0] * 100.)[1], surface(*path[k + 2])[1]
        if None in (zl, zr, zn) or abs(zl - zr) > 40. or abs(zn - z) > 80.:
            return None
        if any(obstacle(x - f[1] * lx, y + f[0] * lx, z) for lx in (-130., -65., 0., 65., 130.)):
            return None
    return path


def scenario_verge():
    RUN, PAST = 35, 20
    off = HW + 320.
    tries = 0
    for score, i, d in candidates((15, PAST), RUN, 0.)[:150]:
        if score > 40. or tries >= 3:
            break
        for sv in (1., -1.):
            path = verge_path(i, d, sv, RUN, PAST, off)
            if not path:
                continue
            tries += 1
            place(path[0][0], path[0][1], heading(i - d * RUN, d))
            yield from settle(chase_view)
            try:
                yield from drive(path, RUN, 8.3, 7.5, STAGE + '_Verge', chase_view,
                                 dict(stretch=dict(index=i, direction=d, side='right' if sv > 0 else 'left', offset_from_centre_cm=round(off),
                                                   sun_heading_deviation_deg=round(score, 1), attempt=tries)))
                return
            except RuntimeError:
                stop()
                if tries >= 3:
                    raise
            break
    raise RuntimeError('no clear firm verge path heading with the sun (or every drive left it)')


def run():
    global world, pc, car, move, spray, weather, camera, L, Lh
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
    move, spray = car.get_chaos_movement(), car.get_spray()
    weather = next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer() == world)
    clear = weather.find_state('Clear')
    if clear:
        weather.set_state(clear, True)
    weather.set_wetness_for_test(0.)
    camera = u.GTVehicleSetupLibrary.spawn_actor_of_class(world, u.CameraActor, u.Transform(), 'B1bCam')
    camera.camera_component.set_constraint_aspect_ratio(False)
    pc.set_view_target_with_blend(camera, 0.)
    # gt.SurfaceEffects 0: a placed AGTVehicleSurfaceEffects (another session's DustLab / MudFlickLab, saved into the review map
    # 2026-10-12) otherwise replaces the spray's dust and mud with its own; these pictures are of the spray.
    for cmd in ('showhud', 'gt.Spray.Art 1', 'gt.Spray.Fine 1', 'gt.Spray.FineScale 1', 'gt.SurfaceEffects 0'):
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
                  surface_effects_actors=[a.get_actor_label() for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
                                          if a.get_class().get_name().startswith('GTVehicleSurfaceEffects')])
    t0 = gs()
    while gs() - t0 < 6.:
        yield
    for name, fn in ((STAGE + '_Gravel_Chase', scenario_chase), (STAGE + '_Gravel_Close', scenario_close), (STAGE + '_Verge', scenario_verge)):
        if ONLY and name[len(STAGE) + 1:] not in ONLY:
            continue
        try:
            yield from fn()
        except Exception:  # noqa: BLE001
            report.setdefault('errors', {})[name] = traceback.format_exc()
            u.GameplayStatics.set_game_paused(world, False)
            stop()
        t0 = gs()
        while gs() - t0 < 1.:
            yield
    names = [p['name'] for p in report['pictures'] if p.get('written')]
    report['ok'] = names == [STAGE + '_' + n for n in ('Gravel_Chase', 'Gravel_Close', 'Verge') if not ONLY or n in ONLY]


def finish(error=None):
    if error:
        report['error'] = error
    elif not report['ok']:
        report['error'] = 'pictures missing: %s' % sorted(report.get('errors', {}))
    (OUT / ('capture_%s.json' % '_'.join(ONLY) if ONLY else 'capture.json')).write_text(json.dumps(report, indent=2))
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
        if time.monotonic() - started > 5400.:
            raise RuntimeError(STAGE + ' capture timed out')
        next(gen)
    except StopIteration:
        finish()
    except Exception:  # noqa: BLE001
        finish(traceback.format_exc())
    finally:
        busy = False


handle = u.register_slate_post_tick_callback(tick)
