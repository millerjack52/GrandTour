"""Unrestricted starts and coast-downs. Each trial gets fresh soil; never speed-govern the car."""
import json,time,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudResponse'
BASELINE='-GTMudDynamicsBaseline' in u.SystemLibrary.get_command_line()
DEST=OUT/('dynamics-before.json' if BASELINE else 'dynamics-after.json')
report=dict(ok=False,runs=[],baseline=BASELINE,automatic_speed_braking=False)
world=pc=car=surface=move=mesh=None;active=None;rows=[];deadline=0;clock='wall';busy=False
cases=[('firm_start',False,0,1,4),('bog_start',True,0,1,4),('bog_crawl',True,0,.45,4),
       ('firm_coast40',False,40,0,2),('bog_coast10',True,10,0,2),
       ('bog_coast25',True,25,0,2),('bog_coast40',True,40,0,2),
       ('bog_restart',True,0,1,4),('bog_reverse',True,0,-1,4),('bog_fresh40',True,40,0,2)]
def save():DEST.write_text(json.dumps(report,indent=2))
def now():return u.GameplayStatics.get_time_seconds(world) if clock=='sim' and world else time.monotonic()
def sample():
    t=car.get_component_by_class(u.GTVehicleTuningComponent).get_current();ws=car.get_traction().wheels
    s=dict(time=u.GameplayStatics.get_time_seconds(world),position=list(car.get_actor_location().to_tuple()),
        speed_kmh=car.get_velocity().length()*.036,tread=[w.tread_cm_per_s*.036 for w in ws],
        sink=[w.sinkage_cm for w in t.wheels],support=[w.ground_support_cm for w in t.wheels],
        grip=[w.friction_scale for w in t.wheels],drag=[w.rolling_resistance for w in t.wheels],
        contacts=[w.get_editor_property('bInContact') for w in ws],
        drivetrain=car.get_drivetrain().describe(),
        loads=[w.load for w in ws],contact_points=[list(w.contact_point.to_tuple()) for w in ws])
    for name in ['soil_drag_n','soil_grip','soil_slip','soil_contact_offset_cm']:
        try:s[name]=[float(w.get_editor_property(name)) for w in t.wheels]
        except Exception:pass
    return s
def run():
    global world,pc,car,surface,move,mesh,active,rows
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/MudResponse/L_MudResponse')
    yield ('wall',3)
    for name,mud,speed,throttle,duration in cases:
        assert u.GTPlayWindowLibrary.request_play_in_new_window(960,600)
        yield ('wall',6)
        world=u.EditorLevelLibrary.get_game_world();assert world
        pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
        pc.possess(car);car.disable_input(pc);car.reset_driving_inputs()
        move=car.get_chaos_movement();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
        surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
        fresh=name=='bog_fresh40'
        surface.enable_wheel_support=mud and not fresh;surface.observe_player_wheels=mud and not fresh;surface.follow_player=False
        car.set_actor_location_and_rotation(u.Vector(-1000 if throttle>=0 else 650,0,140),u.Rotator(pitch=0,yaw=0,roll=0),False,True)
        mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
        car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
        move.set_handbrake_input(True)
        yield ('sim',3 if name!='bog_restart' else 8)
        move.set_handbrake_input(False);move.set_brake_input(0)
        if fresh:surface.enable_wheel_support=True;surface.observe_player_wheels=True
        if throttle<0:move.set_target_gear(-1,True)
        if speed:mesh.set_physics_linear_velocity(u.Vector(speed/.036,0,0))
        active=dict(name=name,throttle=throttle,start=u.GameplayStatics.get_time_seconds(world));rows=[sample()]
        yield ('sim',duration)
        active=None;rows.append(sample());move.set_throttle_input(0)
        result=dict(name=name,samples=rows,travel_cm=rows[-1]['position'][0]-rows[0]['position'][0],
            peak_kmh=max(r['speed_kmh'] for r in rows),end_kmh=rows[-1]['speed_kmh'])
        report['runs'].append(result);save();u.log('MudDynamics '+name+' '+str(result['end_kmh']))
        car.reset_driving_inputs();world=pc=car=surface=move=mesh=None
        u.EditorLevelLibrary.editor_end_play();yield ('wall',3)
    report['ok']=len(report['runs'])==len(cases);save()
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
steps=run()
def tick(dt):
    global busy,clock,deadline
    if busy:return
    busy=True
    try:
        if active:
            move.set_throttle_input(max(0,active['throttle']))
            # The project's brake pedal selects/drives reverse at rest.
            move.set_brake_input(max(0,-active['throttle']))
            if not rows or u.GameplayStatics.get_time_seconds(world)-rows[-1]['time']>=.1:rows.append(sample())
        if now()<deadline:return
        clock,delay=next(steps);deadline=now()+delay
    except StopIteration:pass
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error'])
        u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
