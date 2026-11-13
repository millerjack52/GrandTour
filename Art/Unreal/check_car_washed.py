"""MudRunner MR2 (docs/MUDRUNNER_LESSONS_PLAN.md MR2 item 7): the muddy car through L_MudDrive's ford, one picture before the ford
and one after it.

Play In Editor in a new 1440x900 window (as the other mud checks), Clear weather and wetness 0 held, low range and the diff lock,
the L_MudDrive check's own drive (about 3 m/s, steered to the line): from 5 m through the mud (32-60 m) to 74 m, stopped:
Car_PreFord.png from 4.7 m off its right side; then on through the ford (88-100 m, 35 cm deep) to 109 m (past the ford's riverbed
patch), stopped: Car_Washed.png from the same place relative to the car. The body state before and after (regions, the mud and
coat lines, the washed band, MudWet, the tyres), the deepest water at the wheels in the ford, the time in the water. Functional
only: no cost or timing measurement (the owner's rule). Writes Art/Export/LiveMudDrive/car-washed-report.json.
MudRunner MRP (docs/MUDRUNNER_LESSONS_PLAN.md MRP item 4): at 74 m, after Car_PreFord (the car's mud fresh and wet), the PBR
validation captures on L_MudDrive - HighResShot's buffer dump (BaseColor, Roughness, MaterialAO; uncompressed EXR): PBR_MudDrive_Car
(Car_PreFord's camera, the sill band between the arches as world corners, MudWet), PBR_MudDrive_Calib (the gravel at 20 m, 2.6 m
right of the line: roughness 0.9 by construction) and PBR_MudDrive_Ground (2.2 m over the -Y rut at 46 m, looking down about 50
degrees); the wrapper runs Art/sample_mud_pbr.py on them. Then on through the ford as before.
"""
import unreal as u, json, time, math, traceback
from pathlib import Path
ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/LiveMudDrive'
OUT.mkdir(parents=True, exist_ok=True)
LEVEL = '/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive'
SPEC = '/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive'
u.EditorPythonScripting.set_keep_python_script_alive(True)
VIEW = (1440, 900)
START_X = 500.; PRE_FORD_X = 7400.; AFTER_FORD_X = 10900.; FORD = (8800., 10000.)
LEG_S = 900.   # real seconds: with a game open the editor runs at 1-2 frames a second and the car's physics slower still
phase = 'load'; last = time.monotonic(); start = last; pending_shot = None
PARKED = False   # MR2b: the brake pedal held at a stop is reverse (UGTDrivetrainComponent); tick() lets it go once parked
report = {'ok': False, 'images': [], 'viewports': []}
world = car = move = pc = camera = weather = None
leg = {}


def console(cmd):
    u.SystemLibrary.execute_console_command(world, cmd, pc)


def begin_play():
    lib = getattr(u, 'GTPlayWindowLibrary', None)
    if lib and lib.request_play_in_new_window(VIEW[0], VIEW[1]):
        return 'new window %dx%d' % VIEW
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
    return 'level viewport'


def ground(x, y):
    return u.GTVehicleSetupLibrary.sample_terrain_height_cm(u.load_asset(SPEC).spec, x, y)


def place_car(x, y):
    car.set_actor_location_and_rotation(u.Vector(x, y, ground(x, y) + 150), u.Rotator(), False, True)
    body = car.get_component_by_class(u.SkeletalMeshComponent)
    body.set_physics_linear_velocity(u.Vector()); body.set_physics_angular_velocity_in_degrees(u.Vector())
    car.reset_driving_inputs(); move.set_handbrake_input(True)


def drive_step(target_y):
    # The L_MudDrive check's own drive: about 3.2 m/s, the brake past 4.5 m/s, steered to the line.
    global PARKED
    PARKED = False
    pos = car.get_actor_location(); speed = car.get_velocity().length() / 100.; yaw = car.get_actor_rotation().yaw
    target_yaw = math.degrees(math.atan2(target_y - pos.y, 650.)); error = (target_yaw - yaw + 180) % 360 - 180
    car.set_raw_steer(max(-.65, min(.65, error / 24)))
    move.set_throttle_input(max(.18, min(1., .42 + (3.2 - speed) * .22))); move.set_brake_input(.25 if speed > 4.5 else 0.)
    return pos, speed


def park():
    global PARKED
    move.set_throttle_input(0); move.set_brake_input(1); move.set_handbrake_input(True); car.set_raw_steer(0.); PARKED = True


def body_report():
    st = car.get_body_state(); bd = car.get_body()
    regions = {}
    for name in ('FRONT', 'REAR', 'ARCH_FL', 'ARCH_FR', 'ARCH_RL', 'ARCH_RR', 'SIDE_L', 'SIDE_R', 'ROOF', 'GLASS'):
        reg = getattr(u.GTDamageRegion, name, None)
        if reg is not None:
            regions[name.lower()] = round(st.get_dirt(reg), 3)
    g = bd.get_wheel_geom()
    return dict(describe=st.describe(), regions=regions, mud_line_cm=round(st.mud_line_cm, 1), coat_line_cm=round(st.coat_line_cm, 1),
                wash_cm=round(st.wash_cm, 1), wash_amount=round(st.wash_amount, 3), mud_wet=round(st.mud_wet, 3), tyres=[round(t, 3) for t in st.tyre_coat],
                hits=st.get_throw_hits(), mud_base_z=round(bd.get_mud_base_z(), 1), wheel_geom=[round(g.x, 1), round(g.y, 1), round(g.z, 1), round(g.w, 1)],
                tyre_slots=bd.get_tyre_slots(), wetness=round(st.wetness, 3),
                fan_coat=[round(c, 3) for c in st.fan_coat], fan_dir=[round(c, 1) for c in st.fan_dir])   # MR2b: the spray fans


def stopped(now):
    # At rest (a fixed wait is not enough at a game's frame rates), or 60 s.
    return (car.get_velocity().length() < 25. and now - last > 2.) or now - last > 60.


MRP_TARGETS = 'BaseColor,Roughness,MaterialAO'


def aim(cpos, target, fov):
    camera.set_actor_location(cpos, False, False); camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos, target), False)
    camera.camera_component.set_field_of_view(fov); pc.set_view_target_with_blend(camera, 0.)


def car_mud_box():
    # MRP: the sill band (15-45 cm above the wheel bottoms) between the arches on the car's +Y side, in world space.
    bd = car.get_body(); g = bd.get_wheel_geom(); base = bd.get_mud_base_z(); t = car.get_component_by_class(u.SkeletalMeshComponent).get_world_transform()
    x0, x1 = g.y + g.w + 12., g.x - g.w - 12.
    return [[round(v.x, 2), round(v.y, 2), round(v.z, 2)] for v in (u.MathLibrary.transform_location(t, u.Vector(x, 85., base + z)) for x, z in ((x0, 15.), (x1, 15.), (x1, 45.), (x0, 45.)))]


def shoot_dump(name, cpos, target, fov, now, kind, **extra):
    # MRP: a buffer dump (HighResShot ... 0 0 0 0 0 1 1: the buffers, HDR) at this camera.
    global pending_shot
    aim(cpos, target, fov)
    cam = dict(location=[round(cpos.x, 1), round(cpos.y, 1), round(cpos.z, 1)], target=[round(target.x, 1), round(target.y, 1), round(target.z, 1)], fov=fov)
    report.setdefault('cameras', {})[name] = cam
    report.setdefault('mrp', {}).setdefault('dumps', []).append(dict(name=name, kind=kind, base=str((OUT / name).as_posix()), camera=cam, **extra))
    leg['dump_t'] = time.time(); pending_shot = (now + 2.5, OUT / (name + '.png'), True)


def dump_written(name):
    f = OUT / (name + '_MaterialAO.exr')
    return f.exists() and f.stat().st_mtime >= leg.get('dump_t', 0.)


def shoot(name, now):
    global pending_shot
    pos = car.get_actor_location(); gz = ground(pos.x, pos.y)
    cpos = u.Vector(pos.x - 20., pos.y + 470., gz + 105.); target = u.Vector(pos.x, pos.y, gz + 75.)   # the car's right side (lit on the strips)
    camera.set_actor_location(cpos, False, False); camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos, target), False)
    camera.camera_component.set_field_of_view(50.); pc.set_view_target_with_blend(camera, 0.)
    report.setdefault('cameras', {})[name] = dict(location=[round(cpos.x, 1), round(cpos.y, 1), round(cpos.z, 1)], target=[round(target.x, 1), round(target.y, 1), round(target.z, 1)], fov=50.)
    path = OUT / (name + '.png'); report['images'].append(str(path)); pending_shot = (now + 1.5, path)


def finish(error=None):
    global phase
    phase = 'finished'
    if error:
        report['error'] = error
    (OUT / 'car-washed-report.json').write_text(json.dumps(report, indent=2))
    u.unregister_slate_post_tick_callback(handle); u.EditorLevelLibrary.editor_end_play(); u.SystemLibrary.quit_editor()


def tick(dt):
    global phase, last, world, car, move, pc, camera, weather, pending_shot
    now = time.monotonic()
    try:
        if phase not in ('load', 'loaded', 'warm', 'finished', 'restart'):
            weather.set_wetness_for_test(0.)
        if PARKED and car is not None and car.get_velocity().length() < 50.:
            move.set_brake_input(0.)   # MR2b: never reverse when parked (the handbrake holds it)
        if pending_shot and now >= pending_shot[0]:
            path = pending_shot[1]; dump = len(pending_shot) > 2 and pending_shot[2]; pending_shot = None
            console('HighResShot %dx%d%s filename="%s"' % (VIEW[0], VIEW[1], ' 0 0 0 0 0 1 1' if dump else '', path.as_posix()))
        if now - start > 3000:
            finish('Car washed check timed out'); return
        if phase == 'load':
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL); phase = 'loaded'; last = now
        elif phase == 'loaded' and now - last > 6:
            report['play_mode'] = begin_play(); phase = 'warm'; last = now
        elif phase == 'restart' and now - last > 5:
            report['play_mode_retry'] = begin_play(); phase = 'warm'; last = now
        elif phase == 'warm' and now - last > 15:
            world = u.EditorLevelLibrary.get_game_world()
            if world is None:
                if now - last > 40:
                    raise RuntimeError('Play In Editor did not start')
                return
            cars = u.GameplayStatics.get_all_actors_of_class(world, u.GTCarPawn); assert cars, 'Automation car missing'; car = cars[0]
            move = car.get_chaos_movement(); pc = u.GameplayStatics.get_player_controller(world, 0)
            if pc:
                pc.possess(car); car.disable_input(pc)
            size = list(pc.get_viewport_size()); report['viewports'].append(size)
            if str(report.get('play_mode', '')).startswith('new window') and size[0] != VIEW[0] and 'viewport_retry' not in report:
                report['viewport_retry'] = size; u.EditorLevelLibrary.editor_end_play(); phase = 'restart'; last = now; return
            report['viewport_size'] = size
            car.reset_driving_inputs(); car.set_chase_camera(False)
            car.get_drivetrain().set_low_range(True); car.get_drivetrain().set_diff_lock(True)
            weather = next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer() == world)
            clear = weather.find_state('Clear')
            if clear:
                weather.set_state(clear, True)
            weather.set_wetness_for_test(0.); report['weather'] = weather.get_state_name()
            camera = next(a for a in u.GameplayStatics.get_all_actors_of_class(world, u.CameraActor) if a.get_actor_label() == 'Live_Overview')
            report['car_mud'] = u.SystemLibrary.get_console_variable_int_value('gt.Mud.CarMud')
            place_car(START_X, 0.); report['start'] = body_report(); phase = 'settle'; last = now
        elif phase == 'settle' and now - last > 4:
            pc.set_view_target_with_blend(car, 0.)
            car.reset_driving_inputs(); move.set_handbrake_input(False); move.set_target_gear(1, True)
            leg.update(target=PRE_FORD_X, name='mud', start=now, max_sink_m=0., max_water_m=0., water_s=0.); phase = 'drive'; last = now
        elif phase == 'drive':
            pos, speed = drive_step(0.)
            wheels = car.get_traction().wheels
            leg['max_sink_m'] = max(leg['max_sink_m'], max(w.sinkage for w in wheels))
            water = max(w.water_depth_m for w in wheels); leg['max_water_m'] = max(leg['max_water_m'], water)
            if water > .05:
                leg['water_s'] += dt
            if pos.x >= leg['target'] or now - leg['start'] > LEG_S:
                park()
                report[leg['name']] = dict(reached=bool(pos.x >= leg['target']), end_m=round(pos.x / 100., 2), s=round(now - leg['start'], 1),
                                           max_sink_m=round(leg['max_sink_m'], 3), max_water_m=round(leg['max_water_m'], 3), water_over_5cm_s=round(leg['water_s'], 1))
                phase = 'stop_' + leg['name']; last = now
        elif phase == 'stop_mud' and stopped(now):
            report['before_ford'] = body_report(); shoot('Car_PreFord', now); phase = 'shot_mud'; last = now
        elif phase == 'shot_mud' and now - last > 3.5:
            # MRP: the PBR captures while the car's mud is fresh, then the ford leg.
            console('r.BufferVisualizationOverviewTargets %s' % MRP_TARGETS); console('r.SaveEXR.CompressionQuality 0'); console('r.PostProcessingColorFormat 1')
            cam = report['cameras']['Car_PreFord']
            leg['dumps'] = [('PBR_MudDrive_Car', 'car', (u.Vector(*cam['location']), u.Vector(*cam['target']), 50.), dict(box_world=car_mud_box(), mud_wet=round(car.get_body_state().mud_wet, 3))),
                            ('PBR_MudDrive_Calib', 'calib', (u.Vector(1850., 260., ground(2000., 260.) + 200.), u.Vector(2030., 260., ground(2030., 260.)), 50.), {}),
                            ('PBR_MudDrive_Ground', 'ground', (u.Vector(4450., -35., ground(4450., -35.) + 220.), u.Vector(4620., -75., ground(4620., -75.)), 50.), dict(variant='Standard (L_MudDrive)'))]
            leg['last_dump'] = None; phase = 'mrp_dump'; last = now
        elif phase == 'mrp_dump' and now - last > 4. and (not leg['last_dump'] or dump_written(leg['last_dump']) or now - last > 30.):
            if leg['dumps']:
                name, kind, (cpos, target, fov), extra = leg['dumps'].pop(0)
                shoot_dump(name, cpos, target, fov, now, kind, **extra); leg['last_dump'] = name; last = now
                return
            car.reset_driving_inputs(); move.set_handbrake_input(False); move.set_target_gear(1, True)
            leg.update(target=AFTER_FORD_X, name='ford', start=now, max_sink_m=0., max_water_m=0., water_s=0.); phase = 'drive'; last = now
        elif phase == 'stop_ford' and stopped(now):
            report['after_ford'] = body_report(); shoot('Car_Washed', now); phase = 'shot_ford'; last = now
        elif phase == 'shot_ford' and now - last > 3.5:
            missing = [p for p in report['images'] if not Path(p).exists()]
            report['missing_images'] = missing
            report['ok'] = bool(report.get('mud', {}).get('reached') and report.get('ford', {}).get('reached') and not missing)
            if not report['ok']:
                report['error'] = 'mud leg %s, ford leg %s, images missing %d' % (report.get('mud'), report.get('ford'), len(missing))
            finish()
    except Exception:
        finish(traceback.format_exc())


handle = u.register_slate_post_tick_callback(tick)
