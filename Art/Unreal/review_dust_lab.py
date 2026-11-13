"""Functional DustLab drive and capture. No profiling or asset saves.
Runs only L_DustLab, suppressing the original spray only in this transient PIE session.
"""
import json
import math
import time
import traceback
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/DustLab'
OUT.mkdir(parents=True, exist_ok=True)
LEVEL = '/Game/GrandTour/ArtTests/DustLab/L_DustLab'
SPEC = '/Game/GrandTour/ArtTests/DeformableGravel/DA_GravelDeform'
u.EditorPythonScripting.set_keep_python_script_alive(True)
report = {'ok': False, 'pictures': [], 'samples': [], 'checks': {}, 'profiled': False}
state = {'phase': 'load', 'last': time.monotonic(), 'start': time.monotonic(), 'shot': None, 'index': 0}
world = car = move = lab = pc = camera = spec = None
SHOTS = [(4., 'Dust_Dirt_Chase', 'chase'), (8., 'Dust_Gravel_Roadside', 'roadside'),
         (12., 'Dust_Trail_Elevated', 'elevated')]


def command(text):
    u.SystemLibrary.execute_console_command(world, text, pc)


def finish(error=None):
    global world, car, move, lab, pc, camera, spec
    if error:
        report['error'] = error
        u.log_error(error)
    report['ok'] = error is None and all(report['checks'].values()) and len(report['pictures']) == 5
    (OUT / 'review-report.json').write_text(json.dumps(report, indent=2))
    # Ending PIE is queued. Do not tear down the editor on the same frame or
    # keep Python wrappers pointing into the PIE world during its destruction.
    world = car = move = lab = pc = camera = spec = None
    state.update(phase='stopping', last=time.monotonic())
    u.EditorLevelLibrary.editor_end_play()


def view(kind):
    p = car.get_actor_location()
    f = car.get_actor_forward_vector()
    if kind == 'chase':
        eye = u.Vector(p.x-f.x*1100, p.y-f.y*1100-280, p.z+350)
        target = u.Vector(p.x+100, p.y, p.z)
    elif kind == 'roadside':
        eye = u.Vector(p.x-1600, p.y-2100, p.z+650)
        target = u.Vector(p.x-500, p.y, p.z+30)
    else:
        eye = u.Vector(p.x-4000, p.y-4800, p.z+3800)
        target = u.Vector(p.x-2600, p.y, p.z+100)
    camera.set_actor_location_and_rotation(eye, u.MathLibrary.find_look_at_rotation(eye, target), False, True)
    camera.camera_component.set_field_of_view(65.)


def sample():
    p = car.get_actor_location()
    return {'t': round(u.GameplayStatics.get_time_seconds(world), 3), 'x_m': round(p.x/100, 2),
            'speed_mps': round(car.get_velocity().length()/100, 2),
            'rate': round(lab.total_rate, 3), 'live': lab.get_live_particles(),
            'emitting_wheels': lab.emitting_wheels,
            'contacts': sum(bool(w.get_editor_property('bInContact')) for w in car.get_traction().wheels),
            'gravel_wheels': sum(bool(w.get_editor_property('bInGravelPatch')) for w in car.get_traction().wheels)}


def shot(name, kind, next_phase):
    view(kind)
    u.GameplayStatics.set_game_paused(world, True)
    path = OUT / (name + '.png')
    state.update(phase='capture', shot=path, shot_start=time.time(), last=time.monotonic(), next_phase=next_phase,
                 capture_issued=False, capture_name=name)


def tick(delta):
    global world, car, move, lab, pc, camera, spec
    now = time.monotonic()
    try:
        phase = state['phase']
        if phase == 'done':
            return
        if phase == 'stopping':
            if now-state['last'] > 3. and u.EditorLevelLibrary.get_game_world() is None:
                assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
                state.update(phase='quitting', last=now)
            elif now-state['last'] > 30.:
                raise RuntimeError('PIE did not finish stopping')
            return
        if phase == 'quitting':
            if now-state['last'] > 3.:
                state['phase'] = 'done'
                u.unregister_slate_post_tick_callback(handle)
                u.SystemLibrary.quit_editor()
            return
        if now - state['start'] > 600:
            raise RuntimeError('DustLab review timeout in ' + phase)
        if phase == 'load':
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
            state.update(phase='loaded', last=now)
        elif phase == 'loaded' and now-state['last'] > 4:
            if not u.GTPlayWindowLibrary.request_play_in_new_window(1440, 900):
                u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
            state.update(phase='warm', last=now)
        elif phase == 'warm' and now-state['last'] > 12:
            world = u.EditorLevelLibrary.get_game_world()
            if world is None:
                return
            cars = u.GameplayStatics.get_all_actors_of_class(world, u.GTCarPawn)
            labs = u.GameplayStatics.get_all_actors_of_class(world, u.GTDustLab)
            assert cars and labs, 'No car or opted-in DustLab actor'
            car, lab = cars[0], labs[0]
            pc = u.GameplayStatics.get_player_controller(world, 0)
            pc.possess(car)
            car.disable_input(pc)
            move = car.get_chaos_movement()
            lab.target_car = car
            lab.wetness_override = 0.
            lab.intensity = 2.4
            camera = u.GTVehicleSetupLibrary.spawn_actor_of_class(world, u.CameraActor, u.Transform(), 'DustLabCamera')
            camera.camera_component.set_constraint_aspect_ratio(False)
            pc.set_view_target_with_blend(camera, 0.)
            weather = next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer() == world)
            clear = weather.find_state('Clear')
            if clear:
                weather.set_state(clear, True)
            weather.set_wetness_for_test(0.)
            spec = u.load_asset(SPEC).spec
            z = u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec, 500., 0.)
            car.reset_driving_inputs()
            car.set_actor_location_and_rotation(u.Vector(500, 0, z+150), u.Rotator(), False, True)
            body = car.get_component_by_class(u.SkeletalMeshComponent)
            body.set_physics_linear_velocity(u.Vector())
            body.set_physics_angular_velocity_in_degrees(u.Vector())
            move.set_handbrake_input(True)
            car.get_drivetrain().set_low_range(False)
            car.get_drivetrain().set_diff_lock(True)
            # Disable original emitter rates only on this PIE car; shared defaults aren't edited.
            spray = car.get_spray()
            spray.set_editor_property('dust_rate', 0.)
            command('gt.Spray.Fine 0')
            command('showhud')
            lab.reset_dust()
            state.update(phase='settle', game_start=u.GameplayStatics.get_time_seconds(world))
            view(SHOTS[min(state['index'], len(SHOTS)-1)][2])
        elif phase == 'settle':
            if u.GameplayStatics.get_time_seconds(world)-state['game_start'] > 3:
                report['checks']['idle_has_no_emission'] = lab.total_rate < .01
                move.set_handbrake_input(False)
                state.update(phase='drive', drive_start=u.GameplayStatics.get_time_seconds(world), last_sample=-1.)
        elif phase == 'drive':
            elapsed = u.GameplayStatics.get_time_seconds(world)-state['drive_start']
            p = car.get_actor_location()
            speed = car.get_velocity().length()/100
            # Stay on the existing test road; no physics parameters are adjusted.
            heading = math.degrees(math.atan2(-p.y, 1000.))
            err = (heading-car.get_actor_rotation().yaw+180)%360-180
            car.set_raw_steer(max(-.4, min(.4, err/24)))
            move.set_throttle_input(max(.05, min(1., .42+(8.5-speed)*.35)))
            move.set_brake_input(.3 if speed > 10. else 0.)
            view(SHOTS[min(state['index'], len(SHOTS)-1)][2])
            if elapsed-state['last_sample'] > .25:
                report['samples'].append(sample())
                state['last_sample'] = elapsed
            index = state['index']
            if index < len(SHOTS) and elapsed >= SHOTS[index][0]:
                _, name, kind = SHOTS[index]
                state['index'] += 1
                shot(name, kind, 'drive' if state['index'] < len(SHOTS) else 'wet_start')
        elif phase == 'capture':
            if not state['capture_issued'] and now-state['last'] > .5:
                command('HighResShot 1440x900 filename="%s"' % state['shot'].as_posix())
                state['capture_issued'] = True
            path = state['shot']
            if path.exists() and path.stat().st_mtime >= state['shot_start'] and now-state['last'] > 1.5:
                report['pictures'].append(dict(name=state['capture_name'], image=str(path), state=sample()))
                u.GameplayStatics.set_game_paused(world, False)
                state['phase'] = state['next_phase']
            elif now-state['last'] > 30:
                raise RuntimeError('Missing capture '+str(path))
        elif phase == 'wet_start':
            report['checks']['dry_driving_emits'] = any(s['rate'] > 1 and s['live'] > 0 for s in report['samples'])
            report['checks']['ordinary_dirt_emits'] = any(s['rate'] > 1 and s['gravel_wheels'] == 0 for s in report['samples'])
            report['checks']['gravel_patch_emits'] = any(s['rate'] > 1 and s['gravel_wheels'] > 0 for s in report['samples'])
            lab.wetness_override = 1.
            move.set_throttle_input(0.)
            move.set_brake_input(1.)
            move.set_target_gear(0, True)
            move.set_handbrake_input(True)
            state.update(phase='wet_tail', tail_start=u.GameplayStatics.get_time_seconds(world))
        elif phase == 'wet_tail':
            move.set_target_gear(0, True)
            view('elevated')
            if u.GameplayStatics.get_time_seconds(world)-state['tail_start'] > 2.:
                report['checks']['wet_stops_emission'] = lab.total_rate < .01
                report['checks']['old_trail_survives_transition'] = lab.get_live_particles() > 0
                shot('Dust_AfterStop', 'elevated', 'fade')
        elif phase == 'fade':
            move.set_target_gear(0, True)
            view('elevated')
            if u.GameplayStatics.get_time_seconds(world)-state['tail_start'] > 13.:
                report['checks']['tail_eventually_expires'] = lab.get_live_particles() == 0
                shot('Dust_Faded', 'elevated', 'finish')
        elif phase == 'finish':
            finish(None if all(report['checks'].values()) else 'Functional gates failed; see checks')
    except Exception:
        finish(traceback.format_exc())


handle = u.register_slate_post_tick_callback(tick)
