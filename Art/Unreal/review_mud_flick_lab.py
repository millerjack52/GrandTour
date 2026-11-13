"""Real-car mud flick review, isolated PIE; no asset saves or performance claims."""
import json
import time
import traceback
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/DustLab'
u.EditorPythonScripting.set_keep_python_script_alive(True)
state = {'phase': 'load', 'start': time.monotonic(), 'last': time.monotonic(), 'index': 0}
report = {'ok': False, 'checks': {}, 'samples': [], 'pictures': [], 'profiled': False}
world = car = lab = move = pc = camera = spray = None
SHOTS = [(2., 'Mud_Forward_Close'), (5., 'Mud_Forward_Wide')]

def command(text):
    u.SystemLibrary.execute_console_command(world, text, pc)

def view(wide=False):
    p = car.get_actor_location()
    eye = u.Vector(p.x-1000, p.y+1300, p.z+500) if wide else u.Vector(p.x-650, p.y+900, p.z+330)
    target = u.Vector(p.x-150, p.y, p.z-30)
    camera.set_actor_location_and_rotation(eye, u.MathLibrary.find_look_at_rotation(eye,target), False, True)
    camera.camera_component.set_field_of_view(60.)

def sample():
    wheels = car.get_traction().wheels
    p = car.get_actor_location()
    return {'t': u.GameplayStatics.get_time_seconds(world), 'x_m': p.x/100, 'y_m': p.y/100,
            'speed_mps': car.get_velocity().length()/100, 'rate': lab.total_rate, 'live': lab.get_live_particles(),
            'mud_contacts': sum(w.get_editor_property('bInContact') and w.get_editor_property('bInMudPatch') for w in wheels),
            'tread': [w.get_editor_property('TreadCmPerS') for w in wheels],
            'thrown_cm3': sum(w.get_editor_property('ThrownCm3') for w in wheels),
            'physical_clumps_emitted': spray.get_throw_blobs_emitted(),
            'physical_clumps_landed': spray.get_throw_blobs_landed()}

def shot(name, next_phase):
    u.GameplayStatics.set_game_paused(world, True)
    state.update(phase='capture', name=name, path=OUT/(name+'.png'), next=next_phase,
                 last=time.monotonic(), shot_start=time.time(), issued=False)

def finish(error=None):
    global world, car, lab, move, pc, camera, spray
    if error:
        report['error'] = error
        u.log_error(error)
    report['ok'] = not error and bool(report['checks']) and all(report['checks'].values()) and len(report['pictures']) == 5
    (OUT/'mud-review-report.json').write_text(json.dumps(report, indent=2))
    world = car = lab = move = pc = camera = spray = None
    u.EditorLevelLibrary.editor_end_play()
    state.update(phase='stopping',last=time.monotonic())

def tick(dt):
    global world, car, lab, move, pc, camera, spray
    now = time.monotonic()
    try:
        phase = state['phase']
        if phase == 'done': return
        if now-state['start'] > 600: raise RuntimeError('Review timed out: '+phase)
        if phase == 'stopping':
            if now-state['last'] > 3 and u.EditorLevelLibrary.get_game_world() is None:
                assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
                state.update(phase='quitting',last=now)
            return
        if phase == 'quitting':
            if now-state['last'] > 3:
                state['phase']='done'
                u.unregister_slate_post_tick_callback(handle)
                u.SystemLibrary.quit_editor()
            return
        if phase == 'load':
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/DustLab/L_MudFlickLab')
            state.update(phase='loaded',last=now)
        elif phase == 'loaded' and now-state['last'] > 4:
            assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
            state.update(phase='warm',last=now)
        elif phase == 'warm' and now-state['last'] > 12:
            world = u.EditorLevelLibrary.get_game_world()
            if not world: return
            car = u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn)[0]
            lab = u.GameplayStatics.get_all_actors_of_class(world,u.GTMudFlickLab)[0]
            lab.target_car = car
            move = car.get_chaos_movement()
            spray = car.get_spray()
            pc = u.GameplayStatics.get_player_controller(world,0)
            pc.possess(car); car.disable_input(pc)
            camera = u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'MudFlickCamera')
            camera.camera_component.set_constraint_aspect_ratio(False)
            pc.set_view_target_with_blend(camera,0.)
            spec = u.load_asset('/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive').spec
            z = u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,4000.,-450.)
            car.reset_driving_inputs()
            car.set_actor_location_and_rotation(u.Vector(4000,-450,z+150),u.Rotator(),False,True)
            body = car.get_component_by_class(u.SkeletalMeshComponent)
            body.set_physics_linear_velocity(u.Vector()); body.set_physics_angular_velocity_in_degrees(u.Vector())
            move.set_handbrake_input(True)
            car.get_drivetrain().set_low_range(True)
            car.get_drivetrain().set_diff_lock(True)
            # Keep volume-carrying clumps and terrain deposits; suppress only the
            # old cosmetic rates and fine Niagara in this transient PIE process.
            spray.set_editor_property('mud_rate',0.)
            spray.set_editor_property('dust_rate',0.)
            command('gt.Spray.Fine 0'); command('showhud')
            lab.reset_spray()
            state.update(phase='settle',game_start=u.GameplayStatics.get_time_seconds(world))
            view()
        elif phase == 'settle':
            view()
            if u.GameplayStatics.get_time_seconds(world)-state['game_start'] > 3:
                report['checks']['idle_has_no_emission'] = lab.total_rate < .01
                move.set_handbrake_input(False)
                state.update(phase='drive',drive_start=u.GameplayStatics.get_time_seconds(world),last_sample=-1.)
        elif phase == 'drive':
            elapsed = u.GameplayStatics.get_time_seconds(world)-state['drive_start']
            move.set_target_gear(1,True); move.set_throttle_input(.9); move.set_brake_input(0.)
            car.set_raw_steer(0.)
            view(state['index'] > 0)
            if elapsed-state['last_sample'] > .2:
                report['samples'].append(sample()); state['last_sample']=elapsed
            if state['index'] < len(SHOTS) and elapsed >= SHOTS[state['index']][0]:
                name=SHOTS[state['index']][1]; state['index']+=1
                shot(name,'drive' if state['index']<len(SHOTS) else 'reverse_start')
        elif phase == 'capture':
            if not state['issued'] and now-state['last'] > .5:
                command('HighResShot 1440x900 filename="%s"' % state['path'].as_posix()); state['issued']=True
            if state['path'].exists() and state['path'].stat().st_mtime >= state['shot_start'] and now-state['last'] > 1.5:
                report['pictures'].append({'name':state['name'],'image':str(state['path']),'state':sample()})
                u.GameplayStatics.set_game_paused(world,False); state['phase']=state['next']
            elif now-state['last'] > 30: raise RuntimeError('Missing capture '+state['name'])
        elif phase == 'reverse_start':
            report['checks']['deformable_mud_emits'] = any(s['rate']>1 and s['live']>0 and s['mud_contacts']>0 for s in report['samples'])
            report['checks']['physical_clumps_preserved'] = spray.get_throw_blobs_emitted()>0
            state.update(phase='reverse',reverse_start=u.GameplayStatics.get_time_seconds(world))
        elif phase == 'reverse':
            # The custom drivetrain uses the held brake pedal to select/drive reverse.
            move.set_throttle_input(0.); move.set_brake_input(.8)
            view()
            if u.GameplayStatics.get_time_seconds(world)-state['reverse_start']>5.:
                s=sample(); report['samples'].append(s)
                report['checks']['reverse_tread_emits'] = any(t < -25 for t in s['tread']) and s['rate']>1 and s['live']>0
                shot('Mud_Reverse','stop_start')
        elif phase == 'stop_start':
            move.set_throttle_input(0.); move.set_brake_input(0.); move.set_handbrake_input(True)
            lab.set_editor_property('bEnabled',False)
            state.update(phase='stop',stop_start=u.GameplayStatics.get_time_seconds(world))
        elif phase == 'stop':
            move.set_target_gear(0,True); view(True)
            if u.GameplayStatics.get_time_seconds(world)-state['stop_start']>.12:
                report['checks']['disabled_stops_new_emission']=lab.total_rate<.01
                shot('Mud_AfterCutoff','fade')
        elif phase == 'fade':
            move.set_target_gear(0,True); view(True)
            if u.GameplayStatics.get_time_seconds(world)-state['stop_start']>2.:
                report['checks']['flecks_expire']=lab.get_live_particles()==0
                report['clumps_landed']=spray.get_throw_blobs_landed()
                shot('Mud_Cleared','finish')
        elif phase == 'finish':
            finish(None if all(report['checks'].values()) else 'Functional gates failed')
    except Exception:
        finish(traceback.format_exc())

handle = u.register_slate_post_tick_callback(tick)
