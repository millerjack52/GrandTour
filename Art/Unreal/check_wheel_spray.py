"""Wheel spray P2 item 7 and P2b (docs/WHEEL_SPRAY_PLAN.md): the spray's pictures, mid-action, rendered (Art/check_wheel_spray.ps1: a
full editor with -RenderOffScreen, Play In Editor in a 1440 x 900 window, the possessed car driven by script).

P2b camera rule, every picture: a 3/4 rear view of a rear wheel, the eye 1.15 m above its contact, 4.0 m back and 2.5 m out to the
side (4.7 m from the wheel; the close pictures 2.4 m back and 1.8 m out, 3.0 m), looking at the ground 1.2 m behind the wheel (the
wheel and the 0-3 m behind it in frame). Of the two rear wheels the one whose view puts the level's sun (its DirectionalLight)
nearest behind the camera; the angle between the view and the light's direction is in the report and must be at most 60 deg.
L_MudVariants (low range, diff lock; the Clear weather, dry):
  Spray_Mud_Spin            the car put down in Deep, left 2 s to settle, the throttle held full for 3 s;
  Spray_Mud_Spin_Greybox    the same at gt.Spray.Art 0;
  Spray_Mud_Close           the same spin, the close camera; the gate dump (below); P2c: the rear arch-top line projected, and
                            Spray_Mud_Close_NoWater, the same paused frame with the CPU Water spray's ISM hidden;
  Spray_Mud_Drive           about 25 km/h (6.9 m/s) in Standard; a dump too (the white blots' diagnosis).
L_GravelDeform (high range, diff lock):
  the Kill On Collision check (before the drives): a still NS_GT_WheelSpray 60 cm above the flat road, a 0.06 s burst of MudDroplets
  and GravelGrit falling from rest, the live counts every frame for 1.7 s (report kill_check);
  Spray_Gravel_Drive        about 40 km/h (11.1 m/s) on Loose; P2c: Spray_Gravel_Drive_NoGreyDust, the same frame without the CPU
                            Dust kind's ISM (the dark streak's diagnosis);
  Spray_Gravel_Launch       a full-throttle launch from a standstill on Loose, 1.2 s in;
  Spray_Gravel_Wet          the drive again at the weather's wetness 1 (no dust);
  Spray_Gravel_Close        about 30 km/h (8.3 m/s) on Loose, the close camera; the gate dump; P2c: Spray_Gravel_Close_NoSprites,
                            the same frame without the car's Niagara components (the dust mask is the difference).
Every capture of a scenario is of one frame: the game is paused from the first to the last.
The gate dumps: HighResShot's buffer dump (BaseColor, CustomDepth, Roughness; uncompressed EXR) with the car's Niagara components in
custom depth, so the sprites' pixels are the custom-depth mask (python Art/sample_spray_pbr.py reads them).
At each capture the report holds the live particles per Niagara emitter (the components' own counts), the clumps drawn, the CPU kinds'
live counts, the car's speed, the wheels' rates and flags and the camera's sun angle.
Writes Art/Export/WheelSpray/check-report.json and the PNGs (and the dumps' EXRs) beside it.
"""
import unreal as u, json, time, math, traceback, os, sys
from pathlib import Path

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/WheelSpray'
VIEW = (1440, 900)
MUD_LEVEL = '/Game/GrandTour/ArtTests/MudVariants/L_MudVariants'
MUD_SPEC = '/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants'
GRAVEL_LEVEL = '/Game/GrandTour/ArtTests/DeformableGravel/L_GravelDeform'
GRAVEL_SPEC = '/Game/GrandTour/ArtTests/DeformableGravel/DA_GravelDeform'
u.EditorPythonScripting.set_keep_python_script_alive(True)
PACE = os.environ.get('GT_CHECK_PACE', '1').strip() != '0'
pace_rt = None
report = {'ok': False, 'pictures': []}
start = time.monotonic()
st = dict(phase='load', last=start, level=0, scenario=None, t0=0.0, shot=None, shot_t=0.0)
world = pc = car = move = spray = weather = camera = spec = None
REAR = dict(back=400., lat=250., up=115.)     # 4.7 m from the wheel
CLOSE = dict(back=240., lat=180., up=115.)    # 3.0 m

# P2c: the dust's lighting swept on Spray_Gravel_Close's paused frame (MPC_GT_Spray DustLit, DustFloor); the setup's own default first.
DUST_SWEEP = [(1.0, 0.3), (1.0, 1.0), (0.7, 1.0), (0.7, 1.4), (0.5, 1.4), (0.7, 2.0)]
DUST_DEFAULT = (0.7, 1.4)
# (level, name, kind, settings)
SCENARIOS = [
    (0, 'Spray_Mud_Spin', 'spin', dict(art=1, x=13200., cam=REAR)),
    (0, 'Spray_Mud_Spin_Greybox', 'spin', dict(art=0, x=13200., cam=REAR)),
    (0, 'Spray_Mud_Close', 'spin', dict(art=1, x=13200., cam=CLOSE, dump=True, arch=True, extra=[('_NoWater', 'water')])),
    (0, 'Spray_Mud_Drive', 'drive', dict(art=1, x=6000., speed=6.9, shoot_x=8700., cam=REAR, dump=True, heights=True)),
    (1, 'KillCheck', 'killcheck', dict(x=2000., y=-450.)),
    (1, 'Spray_Gravel_Drive', 'drive', dict(art=1, x=500., speed=11.1, shoot_x=9400., high=True, cam=REAR, extra=[('_NoGreyDust', 'dust')])),
    (1, 'Spray_Gravel_Launch', 'launch', dict(art=1, x=8600., high=True, cam=REAR)),
    (1, 'Spray_Gravel_Wet', 'drive', dict(art=1, x=500., speed=11.1, shoot_x=9400., high=True, wet=1., cam=REAR)),
    (1, 'Spray_Gravel_Close', 'drive', dict(art=1, x=2000., speed=8.3, shoot_x=9300., high=True, cam=CLOSE, dump=True,
                                            extra=[('_NoSprites', 'niagara')] + [('_Dust_L%g_F%g' % lf, ('dust_light',) + lf) for lf in DUST_SWEEP])),
]
LEVELS = [(MUD_LEVEL, MUD_SPEC), (GRAVEL_LEVEL, GRAVEL_SPEC)]
# Checks under a running game (docs/CHECKS_UNDER_GAME_PLAN.md, Art/Unreal/check_render.py): a fixed 1/60 s step (the wrapper's
# -UseFixedTimeStep -FPS=60, verified over 300 frames of the first scenario); the scene is rendered only where the GPU's particles
# matter - the kill check (30 frames before its burst, then throughout), and every spray scenario from its throttle-on to its capture
# (ground relief GR1c's checks follow-up: Niagara's GPU sims run only while rendering, and the drives rendered only their last 2 game
# seconds, so the fans built up a shorter history than the real step's - the spray check is short; the other checks keep windows),
# and the paused captures - and the GPU wait runs only then. The scenario timers (the 2 s settle, the 3 s spin, the 1.2 s launch, the 90 s stall) count game seconds.
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
from check_render import Gate  # noqa: E402
GATE = Gate()
DRIVE_WARM = 90


def gw():
    try:
        return u.GameplayStatics.get_time_seconds(world) if world is not None else 0.
    except Exception:  # noqa: BLE001
        return 0.


def gpu_pace():
    global pace_rt
    gw = u.EditorLevelLibrary.get_game_world()
    if gw is None:
        return
    try:
        gone = pace_rt is None or pace_rt.get_outer() is None
    except Exception:
        gone = True
    if gone:
        pace_rt = u.RenderingLibrary.create_render_target2d(gw, 1, 1, u.TextureRenderTargetFormat.RTF_RGBA8)
    u.RenderingLibrary.read_render_target_pixel(gw, pace_rt, 0, 0)


def finish(error=None):
    try:
        report['check_run'] = GATE.report()
    except Exception:  # noqa: BLE001
        report['check_run_error'] = traceback.format_exc().splitlines()[-1]
    st['phase'] = 'finished'
    if error:
        report['error'] = error
    (OUT / 'check-report.json').write_text(json.dumps(report, indent=2))
    u.unregister_slate_post_tick_callback(handle)
    try:
        u.EditorLevelLibrary.editor_end_play()
    except Exception:
        pass
    u.SystemLibrary.quit_editor()


def console(cmd):
    u.SystemLibrary.execute_console_command(world, cmd, pc)


def ground(x, y):
    return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec, x, y)


def place_car(x, y=0.):
    z = ground(x, y)
    car.reset_driving_inputs()
    move.set_handbrake_input(True)
    car.set_actor_location_and_rotation(u.Vector(x, y, z + 150), u.Rotator(), False, True)
    body = car.get_component_by_class(u.SkeletalMeshComponent)
    body.set_physics_linear_velocity(u.Vector())
    body.set_physics_angular_velocity_in_degrees(u.Vector())


def puddle_spot(x):
    """GR2 phase B item 7: the car's centre for a spin with a rear wheel (130 cm behind the centre, 80 cm out) on the puddle cell nearest
    the old spot's rear wheels (at least 2 cm of water, else 0.5 cm), in the patch under x; the old spot when there is none."""
    patches = u.GameplayStatics.get_all_actors_of_class(world, u.GTMudPatch)
    patch = next((p for p in patches if p.bounds_min.x <= x <= p.bounds_max.x), None)
    best = None
    for side in (-80., 80.):
        wheel = u.Vector2D(x - 130., side)
        hit = None
        for depth in (2.0, 0.5):
            hit = patch.nearest_puddle_cm(wheel, depth) if patch else None
            if hit is not None and hit.z >= 0.:
                break
        if hit is None or hit.z < 0.:
            continue
        d = math.hypot(hit.x - wheel.x, hit.y - wheel.y)
        if best is None or d < best[0]:
            best = (d, hit, side)
    if best is None:
        return x, 0., dict(found=False)
    d, hit, side = best
    return hit.x + 130., hit.y - side, dict(found=True, cell_cm=[round(hit.x, 1), round(hit.y, 1)], water_cm=round(hit.z, 2), moved_m=round(d / 100., 2),
                                           wheel='rear ' + ('left' if side < 0 else 'right'), car_cm=[round(hit.x + 130., 1), round(hit.y - side, 1)])


def unit(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.
    return (v[0] / n, v[1] / n, v[2] / n)


def sun():
    lights = u.GameplayStatics.get_all_actors_of_class(world, u.DirectionalLight)
    f = lights[0].get_actor_forward_vector() if lights else u.Vector(0, 0, -1)
    return unit((f.x, f.y, f.z))


def rear_view(cfg):
    """The P2b camera: for each rear wheel (the two whose contacts are furthest back) the eye cfg back and out from it, looking at
    the ground 1.2 m behind it; the one with the sun nearest behind the camera."""
    wheels = car.get_traction().wheels
    loc = car.get_actor_location()
    f = car.get_actor_forward_vector()
    r = car.get_actor_right_vector()
    pts = []
    for k, w in enumerate(wheels):
        p = w.contact_point
        if (p.x - loc.x) ** 2 + (p.y - loc.y) ** 2 > 400. ** 2:   # no contact (in the air): its place from the car's own frame
            fb = 130. if k < 2 else -130.
            lr = -80. if k % 2 == 0 else 80.
            p = u.Vector(loc.x + f.x * fb + r.x * lr, loc.y + f.y * fb + r.y * lr, loc.z - 40.)
        pts.append(p)
    order = sorted(range(len(pts)), key=lambda i: (pts[i].x - loc.x) * f.x + (pts[i].y - loc.y) * f.y)
    L = sun()
    best = None
    for i in order[:2]:
        p = pts[i]
        side = 1. if (p.x - loc.x) * r.x + (p.y - loc.y) * r.y > 0 else -1.
        eye = (p.x - f.x * cfg['back'] + r.x * side * cfg['lat'], p.y - f.y * cfg['back'] + r.y * side * cfg['lat'], p.z + cfg['up'])
        tgt = (p.x - f.x * 120., p.y - f.y * 120., p.z + 35.)
        v = unit((tgt[0] - eye[0], tgt[1] - eye[1], tgt[2] - eye[2]))
        ang = math.degrees(math.acos(max(-1., min(1., v[0] * L[0] + v[1] * L[1] + v[2] * L[2]))))
        dist = math.sqrt((eye[0] - p.x) ** 2 + (eye[1] - p.y) ** 2 + (eye[2] - p.z) ** 2)
        cand = dict(wheel=i, side='right' if side > 0 else 'left', eye=eye, target=tgt, sun_angle_deg=round(ang, 1), wheel_dist_m=round(dist / 100., 2))
        if best is None or ang < best['sun_angle_deg']:
            best = cand
    return best


def aim_view(view, fov=70.):
    pos = u.Vector(*view['eye'])
    camera.set_actor_location(pos, False, False)
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos, u.Vector(*view['target'])), False)
    camera.camera_component.set_field_of_view(fov)


def drive_to(speed_target, steer_y=0.):
    pos = car.get_actor_location()
    speed = car.get_velocity().length() / 100.
    yaw = math.degrees(math.atan2(steer_y - pos.y, 650.))
    err = (yaw - car.get_actor_rotation().yaw + 180) % 360 - 180
    car.set_raw_steer(max(-.6, min(.6, err / 24)))
    move.set_throttle_input(max(.15, min(1., .45 + (speed_target - speed) * .35)))
    move.set_brake_input(.3 if speed > speed_target + 1.5 else 0.)
    return pos, speed


def state(view=None):
    wheels = car.get_traction().wheels
    rates = [[round(spray.get_fine_rate(i, e), 2) for e in range(3)] for i in range(len(wheels))]
    return dict(
        niagara_live={'MudDroplets': spray.get_fine_live_count(0), 'GravelGrit': spray.get_fine_live_count(1), 'GravelDust': spray.get_fine_live_count(2)},
        clumps_drawn=spray.get_clumps_drawn(),
        cpu_live={k: spray.get_live_count(getattr(u.GTSprayKind, k.upper())) for k in ('Mud', 'Dust', 'Snow', 'Water')},
        speed_mps=round(car.get_velocity().length() / 100., 2),
        x_m=round(car.get_actor_location().x / 100., 2),
        camera=view,
        wheels=[dict(contact=bool(w.get_editor_property('bInContact')), gravel=bool(w.get_editor_property('bInGravelPatch')),
                     variant=int(w.get_editor_property('PatchVariant')), slipping=bool(w.get_editor_property('bSlipping')),
                     rates_mud_grit_dust=rates[i]) for i, w in enumerate(wheels)],
        art=u.SystemLibrary.get_console_variable_int_value('gt.Spray.Art'),
        fine=u.SystemLibrary.get_console_variable_int_value('gt.Spray.Fine'),
        fine_scale=u.SystemLibrary.get_console_variable_float_value('gt.Spray.FineScale'),
        muddy_splash=spray.get_muddy_splash_count(),
        wetness=round(weather.get_wetness(), 3))


def png(path):
    console('HighResShot %dx%d filename="%s"' % (VIEW[0], VIEW[1], path.as_posix()))


def niagara(on):
    """The car's Niagara components into custom depth, alone: whatever else of the car renders custom depth is taken out for the
    dump and put back after (the first P2b run's mask held the car's dashboard)."""
    for c in car.get_components_by_class(u.NiagaraComponent):
        c.set_render_custom_depth(on)
    if on:
        st['cd_off'] = [c for c in car.get_components_by_class(u.PrimitiveComponent)
                        if not isinstance(c, u.NiagaraComponent) and c.get_editor_property('render_custom_depth')]
        for c in st['cd_off']:
            c.set_render_custom_depth(False)
        report['pictures'][-1].setdefault('custom_depth_taken_out', [c.get_name() for c in st['cd_off']])
    else:
        for c in st.get('cd_off', []):
            c.set_render_custom_depth(True)
        st['cd_off'] = []


def dust_light(lit, floor):
    mpc = u.load_asset('/Game/GrandTour/FX/MPC_GT_Spray')
    u.MaterialLibrary.set_scalar_parameter_value(world, mpc, 'DustLit', lit)
    u.MaterialLibrary.set_scalar_parameter_value(world, mpc, 'DustFloor', floor)


def hide(what, hidden):
    """P2c capture-script hides, no code: the CPU Water spray's ISM ('water'), the CPU Dust kind's ISM ('dust'), or the car's Niagara
    components ('niagara'), for one capture of the same paused frame."""
    if isinstance(what, tuple):   # ('dust_light', lit, floor): not a hide, the dust's lighting for this capture
        dust_light(*(what[1:] if hidden else DUST_DEFAULT))
        return list(what[1:])
    if what == 'niagara':
        comps = car.get_components_by_class(u.NiagaraComponent)
    else:
        comps = [c for c in car.get_components_by_class(u.InstancedStaticMeshComponent) if c.get_name() == 'Spray_' + what]
    for c in comps:
        c.set_visibility(not hidden, False)
    return [c.get_name() for c in comps]


def arch_line():
    """The rear wheels' arch-top line on screen: each rear contact + twice the wheel radius + 10 cm, projected (viewport pixels)."""
    wheels = car.get_traction().wheels
    loc = car.get_actor_location()
    f = car.get_actor_forward_vector()
    rows = []
    for i, w in enumerate(wheels):
        p = w.contact_point
        if (p.x - loc.x) * f.x + (p.y - loc.y) * f.y > 0:
            continue
        try:
            radius = float(move.wheels[i].wheel_radius)
        except Exception:
            radius = 38.
        res = u.GameplayStatics.project_world_to_screen(pc, u.Vector(p.x, p.y, p.z + 2. * radius + 10.), False)
        ok, sp = (res[0], res[1]) if isinstance(res, tuple) else (True, res)
        rows.append(dict(wheel=i, radius_cm=round(radius, 1), screen=[round(sp.x, 1), round(sp.y, 1)] if ok else None))
    return dict(wheels=rows, viewport=list(pc.get_viewport_size()))


def droplet_heights():
    """P2d: the droplets' heights above the ground, a CPU estimate from the launch velocities (not the GPU's particles): each wheel's
    BaseVelocity and MudDroplets rate at the capture through NS_GT_WheelSpray's own distribution (the upward part x1.3; clumps
    within 15 deg, +-20 %; droplets in a 4.6 deg cone, +-8 %; the upward launch capped at 700 cm/s), launched 40 cm above the contact
    (+-6 cm), gravity 980 cm/s2 and the linear drag 0.3, each droplet seen at a uniform moment of its flight (until it meets the
    ground or its 0.6-1.4 s life ends). Sampled 20000 droplets in all, by the rates."""
    import random
    rng = random.Random(7)
    g, k = 980., .3
    wheels = car.get_traction().wheels
    rates = [spray.get_fine_rate(i, 0) for i in range(len(wheels))]
    total = sum(rates)
    if total <= 0:
        return dict(droplets=0)
    heights, apexes = [], []

    def unit(v):
        n = math.sqrt(sum(c * c for c in v)) or 1.
        return [c / n for c in v]
    for i, rate in enumerate(rates):
        if rate <= 0:
            continue
        b = spray.get_fine_base_velocity(i)
        v13 = [b.x, b.y, b.z * 1.3]
        a0 = unit([v13[0], v13[1], v13[2] + .001])
        length = math.sqrt(sum(c * c for c in v13))
        for _ in range(int(2000 * rate / total)):
            uu = [rng.uniform(-1, 1) for _ in range(3)]
            d = sum(x * y for x, y in zip(uu, a0))
            cdir = unit([a + .268 * .577 * (x - d * a) for a, x in zip(a0, uu)])
            cspeed = length * (.8 + .4 * rng.random())
            for _ in range(10):
                sp = min(cspeed * (.92 + .16 * rng.random()), 700. / max(cdir[2], .05))
                jitter = [rng.gauss(0, 1) for _ in range(3)]
                dd = sum(x * y for x, y in zip(jitter, cdir))
                perp = unit([x - dd * c for x, c in zip(jitter, cdir)])
                ang = math.radians(4.6) * math.sqrt(rng.random())
                dirv = unit([c * math.cos(ang) + q * math.sin(ang) for c, q in zip(cdir, perp)])
                vz = dirv[2] * sp
                z0 = 40. + rng.uniform(-6., 6.)
                life = rng.uniform(.6, 1.4)

                def z(t):
                    e = math.exp(-k * t)
                    return z0 + (vz + g / k) * (1 - e) / k - g / k * t
                t_end = life
                for step in range(1, 141):   # the ground meeting, at 10 ms
                    if z(step * .01) < 0:
                        t_end = min(life, step * .01)
                        break
                t_apex = max(0., math.log((vz + g / k) / (g / k)) / k) if vz > 0 else 0.
                apexes.append(z(min(t_apex, t_end)))
                heights.append(z(rng.uniform(0, t_end)))
    heights.sort()
    apexes.sort()

    def pct(a, q):
        return round(a[min(len(a) - 1, int(q * len(a)))] / 100., 3)
    return dict(method='CPU estimate from the launch velocities (BaseVelocity and rates at the capture)', droplets=len(heights),
                height_p50_m=pct(heights, .5), height_p95_m=pct(heights, .95), apex_p95_m=pct(apexes, .95), apex_max_m=pct(apexes, .999),
                base_velocities=[[round(c, 1) for c in (spray.get_fine_base_velocity(i).x, spray.get_fine_base_velocity(i).y,
                                                         spray.get_fine_base_velocity(i).z)] for i in range(len(wheels))],
                rates=[round(r, 1) for r in rates])


def start_captures(name, view, s):
    """Freeze the frame (the game paused), then the captures one after another: the picture, the gate dump, the hides."""
    u.GameplayStatics.set_game_paused(world, True)
    row = dict(name=name, image=str(OUT / (name + '.png')), at_capture=state(view))
    if s.get('arch'):
        row['arch_line'] = arch_line()
    if s.get('heights'):
        row['droplet_heights'] = droplet_heights()
    report['pictures'].append(row)
    q = [('png', name, None)]
    if s.get('dump'):
        # P2c: the dump twice, the second with the car's Niagara components hidden: the visible sprites are where the BaseColor
        # differs (custom depth alone also holds the sprites hidden behind the body, whose pixels show the body).
        q.append(('dump', name + '_Gate', None))
        q.append(('dump', name + '_Gate_NoSprites', 'niagara'))
    for suffix, what in s.get('extra', []):
        q.append(('png', name + suffix, what))
    st['queue'] = q
    st['step'] = None


def step_tick(now):
    """One capture at a time: issue it, wait for its file, undo its settings, the next. True when all are done (unpaused)."""
    if st['step'] is None:
        if not st['queue']:
            u.GameplayStatics.set_game_paused(world, False)
            return True
        kind, name, what = st['queue'].pop(0)
        st['shot_t'] = time.time()
        st['last'] = now
        if kind == 'dump':
            if what:
                hide(what, True)
            niagara(True)
            for cmd in ('r.BufferVisualizationOverviewTargets BaseColor,CustomDepth,Roughness', 'r.SaveEXR.CompressionQuality 0', 'r.PostProcessingColorFormat 1'):
                console(cmd)
            st['shot'] = OUT / (name + '_BaseColor.exr')
            report['pictures'][-1].setdefault('gate_dumps', []).append(dict(base=(OUT / name).as_posix(), hidden=what))
            console('HighResShot %dx%d 0 0 0 0 0 1 1 filename="%s"' % (VIEW[0], VIEW[1], (OUT / name).as_posix()))
        else:
            if what:
                report['pictures'][-1].setdefault('same_frame', {})[name] = dict(image=str(OUT / (name + '.png')), hidden=hide(what, True))
            st['shot'] = OUT / (name + '.png')
            png(st['shot'])
        st['step'] = (kind, name, what)
        return False
    f = st['shot']
    if f.exists() and f.stat().st_mtime >= st['shot_t'] and now - st['last'] > 1.5:
        kind, name, what = st['step']
        if kind == 'dump':
            niagara(False)
            console('r.PostProcessingColorFormat 0')
            if what:
                hide(what, False)
        elif what:
            hide(what, False)
        st['step'] = None
    elif now - st['last'] > 30.:
        raise RuntimeError('no capture written: %s' % f.name)
    return False


def begin_scenario(now):
    level, name, kind, s = st['scenario']
    if kind == 'killcheck':
        begin_killcheck(now, s)
        return
    console('gt.Spray.Art %d' % s.get('art', 1))
    weather.set_wetness_for_test(s.get('wet', 0.))
    car.get_drivetrain().set_low_range(not s.get('high', False))
    car.get_drivetrain().set_diff_lock(True)
    if kind == 'spin' and level == 0:
        # Ground relief GR2 phase B item 7: the Deep spin moved onto the nearest puddle cell (a rear wheel on it), so the muddy splash
        # has water under the wheel (GR1c's puddles lie off the old spot at 132 m).
        x, y, info = puddle_spot(s['x'])
        report.setdefault('puddle_spin', {})[name] = info
        place_car(x, y)
    else:
        place_car(s['x'])
    st['phase'] = 'settle'
    st['last'] = now


def begin_killcheck(now, s):
    """Kill On Collision, checked by a frame sequence: a still system 60 cm above the flat road (the car parked away), a 0.06 s burst
    of MudDroplets and GravelGrit from rest; their live counts every frame. From rest at 60 cm a particle meets the ground at
    0.35 s; with restitution 0.3 it rises again at 1.03 m/s and meets it a second time at 0.56 s (drag 0.3 shifts both a little).
    Mud (Kill On Collision 1) should go at the first, grit (2) at the second, both before their lives' ends (mud 0.6, grit 0.8 s)."""
    place_car(500.)
    z = ground(s['x'], s['y'])
    system = u.load_asset('/Game/GrandTour/FX/NS_GT_WheelSpray')
    c = u.NiagaraFunctionLibrary.spawn_system_at_location(world, system, u.Vector(s['x'], s['y'], z + 60.), u.Rotator(), u.Vector(1, 1, 1),
                                                          auto_destroy=False, auto_activate=True, pooling_method=u.NCPoolMethod.NONE, pre_cull_check=False)
    c.set_variable_vec3('User.BaseVelocity', u.Vector(0., 0., -1.))
    c.set_variable_float('User.MudRate', 450.)
    c.set_variable_float('User.GritRate', 450.)
    st['kc'] = dict(comp=c, t0=u.GameplayStatics.get_time_seconds(world), rows=[], z=z, off=False)
    eye = (s['x'] - 300., s['y'] - 60., z + 70.)
    aim_view(dict(eye=eye, target=(s['x'], s['y'], z + 25.)), 60.)
    st['phase'] = 'killcheck'
    st['last'] = now


def killcheck_tick(now):
    GATE.ready(world, pc)
    kc = st['kc']
    t = u.GameplayStatics.get_time_seconds(world) - kc['t0']
    c = kc['comp']
    if t > .06 and not kc['off']:
        c.set_variable_float('User.MudRate', 0.)
        c.set_variable_float('User.GritRate', 0.)
        kc['off'] = True
    kc['rows'].append([round(t, 3), u.GTSprayComponent.get_niagara_live_count(c, 0), u.GTSprayComponent.get_niagara_live_count(c, 1)])
    if t > 1.7:
        rows = kc['rows']
        out = dict(height_cm=60., burst_s=.06, expected_s=dict(first_hit=.35, second_hit=.56, mud_life_min=.6, grit_life_min=.8), frames=len(rows))
        for k, name in ((1, 'MudDroplets'), (2, 'GravelGrit')):
            peak = max(r[k] for r in rows)
            t_peak = next(r[0] for r in rows if r[k] == peak)
            half = next((r[0] for r in rows if r[0] > t_peak and r[k] <= peak * .5), None)
            gone = next((r[0] for r in rows if r[0] > t_peak and r[k] == 0), None)
            out[name] = dict(peak=peak, peak_s=t_peak, half_gone_s=half, all_gone_s=gone)
        out['rows_t_mud_grit'] = rows
        report['kill_check'] = out
        c.destroy_component(c)
        st['scenario'] = None
        st['phase'] = 'next'
        st['last'] = now


def scenario_tick(now):
    level, name, kind, s = st['scenario']
    if kind == 'killcheck':
        killcheck_tick(now)
        return
    weather.set_wetness_for_test(s.get('wet', 0.))
    if st['phase'] == 'capturing':
        GATE.ready(world, pc)
        if step_tick(now):
            report['pictures'][-1]['after_capture'] = state(st['view'])
            move.set_throttle_input(0.)
            move.set_brake_input(1.)
            st['scenario'] = None
            st['phase'] = 'next'
            st['last'] = now
        return
    view = rear_view(s['cam'])
    aim_view(view)
    if st['phase'] == 'settle':
        if 'g_settle' not in st or st.get('settle_of') != name:
            st['g_settle'] = gw()
            st['settle_of'] = name
        if gw() - st['g_settle'] > 2.:
            car.reset_driving_inputs()
            move.set_handbrake_input(False)
            move.set_brake_input(0.)
            move.set_target_gear(1, True)
            st['phase'] = 'act'
            st['t0'] = gw()
            GATE.start_dt()
    elif st['phase'] == 'act':
        fire = False
        if kind in ('spin', 'launch'):
            move.set_throttle_input(1.)
            car.set_raw_steer(0.)
            warm = GATE.ready(world, pc)          # the act is rendered: its particles live on the GPU
            fire = gw() - st['t0'] > (3. if kind == 'spin' else 1.2) and warm
        else:
            pos, speed = drive_to(s['speed'])
            warm = GATE.ready(world, pc, DRIVE_WARM)   # rendered from the throttle-on: the sprays' GPU particles live the whole drive
            fire = pos.x > s['shoot_x'] and warm
            if not fire and gw() - st['t0'] > 90.:
                raise RuntimeError('%s: the car stalled at %.1f m (%.1f m/s)' % (name, pos.x / 100., speed))
        if fire:
            st['view'] = view
            start_captures(name, view, s)
            st['phase'] = 'capturing'
            st['last'] = now


def tick(dt):
    global world, pc, car, move, spray, weather, camera, spec
    now = time.monotonic()
    try:
        if st['phase'] == 'finished':
            return
        GATE.tick(world)
        if world is not None:
            GATE.idle(world, pc)
        if PACE and GATE.on:
            gpu_pace()
        if now - start > 2400:
            raise RuntimeError('Wheel spray check timed out in phase %s' % st['phase'])
        ph = st['phase']
        if ph == 'load':
            st['phase'] = 'loading'
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVELS[st['level']][0])
            st['phase'] = 'loaded'
            st['last'] = now
        elif ph == 'loaded' and now - st['last'] > 6:
            lib = getattr(u, 'GTPlayWindowLibrary', None)
            ok = lib and lib.request_play_in_new_window(*VIEW)
            if not ok:
                u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
            st['phase'] = 'warm'
            st['last'] = now
        elif ph == 'warm' and now - st['last'] > 15:
            world = u.EditorLevelLibrary.get_game_world()
            if world is None:
                if now - st['last'] > 60:
                    raise RuntimeError('Play In Editor did not start')
                return
            pc = u.GameplayStatics.get_player_controller(world, 0)
            car = u.GameplayStatics.get_all_actors_of_class(world, u.GTCarPawn)[0]
            move = car.get_chaos_movement()
            spray = car.get_spray()
            if pc:
                pc.possess(car)
                car.disable_input(pc)
            weather = next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer() == world)
            clear = weather.find_state('Clear')
            if clear:
                weather.set_state(clear, True)
            spec = u.load_asset(LEVELS[st['level']][1]).spec
            camera = u.GTVehicleSetupLibrary.spawn_actor_of_class(world, u.CameraActor, u.Transform(), 'SprayCam')
            camera.camera_component.set_constraint_aspect_ratio(False)   # the whole 1440 x 900 frame, no bars
            pc.set_view_target_with_blend(camera, 0.)
            console('showhud')
            console('gt.Spray.FineScale 1')
            report.setdefault('sun', {})[LEVELS[st['level']][0]] = [round(v, 3) for v in sun()]
            st['phase'] = 'next'
            st['last'] = now
        elif ph == 'next' and now - st['last'] > 2:
            done = [p['name'] for p in report['pictures']] + (['KillCheck'] if 'kill_check' in report else [])
            rest = [sc for sc in SCENARIOS if sc[0] == st['level'] and sc[1] not in done]
            if rest and rest[0][2] == 'killcheck' and not GATE.ready(world, pc):
                return                                    # 30 rendered frames before the burst
            if rest:
                st['scenario'] = rest[0]
                begin_scenario(now)
            elif st['level'] + 1 < len(LEVELS):
                console('gt.Spray.Art 1')
                u.EditorLevelLibrary.editor_end_play()
                st['level'] += 1
                st['phase'] = 'ended'
                st['last'] = now
            else:
                console('gt.Spray.Art 1')
                pics = report['pictures']
                names = [sc[1] for sc in SCENARIOS if sc[2] != 'killcheck']
                report['ok'] = len(pics) == len(names) and all(Path(p['image']).exists() for p in pics) and 'kill_check' in report
                report['sun_angles_deg'] = {p['name']: p['at_capture']['camera']['sun_angle_deg'] for p in pics}
                finish(None if report['ok'] else 'missing pictures or the kill check')
        elif ph == 'ended' and now - st['last'] > 5:
            st['phase'] = 'load'
        elif st['scenario'] is not None:
            scenario_tick(now)
    except Exception:
        finish(traceback.format_exc())


handle = u.register_slate_post_tick_callback(tick)
