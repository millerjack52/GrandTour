"""Bounded stationary or driving scalability diagnostic. Real frame/GPU CSV timings, no screenshots or GPU readbacks."""
import csv,json,math,statistics,time,traceback
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudResponse'
CSV=ROOT/'Saved/Profiling/CSV'
report=dict(ok=False,resolution=[1440,900],runs=[],scope='Short stationary diagnostic; not a long driving/streaming benchmark.')
DRIVE='-GTMudProfileDriving' in u.SystemLibrary.get_command_line()
REPORT='scalability-driving-report.json' if DRIVE else 'scalability-report.json'
report['driving']=DRIVE
if DRIVE:report['scope']='Short repeated driving passes with spray; not a long streaming benchmark.'
world=pc=surface=car=camera=None;driving=False

def save(): (OUT/REPORT).write_text(json.dumps(report,indent=2))
def console(s):u.SystemLibrary.execute_console_command(world,s,pc)
def files():return set(CSV.glob('*.csv'))
def metrics(path):
    with path.open(newline='') as f:rows=list(csv.reader(f))
    result={}
    for i,key in enumerate(rows[0]):
        if key not in ['FrameTime','GameThreadTime','RenderThreadTime','RHIThreadTime','GPUTime'] and not key.startswith('GPU/'):continue
        values=[]
        for row in rows[1:]:
            if not row or row[0].startswith('[') or row[0]=='EVENTS':break
            try:values.append(float(row[i]))
            except (ValueError,IndexError):pass
        if values:
            values.sort();result[key]=dict(frames=len(values),mean_ms=statistics.fmean(values),p99_ms=values[min(len(values)-1,math.ceil(len(values)*.99)-1)])
    return result

def run():
    global world,pc,surface,car,camera,driving
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/MudResponse/L_MudResponse')
    yield 5
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
    yield 10
    world=u.EditorLevelLibrary.get_game_world();assert world
    pc=u.GameplayStatics.get_player_controller(world,0)
    car=pc.get_car();assert car
    pc.possess(car);car.disable_input(pc);car.reset_driving_inputs()
    car.set_actor_location_and_rotation(u.Vector(0,0,140),u.Rotator(pitch=0,yaw=0,roll=0),False,True)
    car.get_chaos_movement().set_handbrake_input(True)
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'MudScalabilityCamera')
    eye=u.Vector(-620,650,280);target=u.Vector(0,0,15)
    camera.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,target),False,False)
    camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(65)
    pc.set_view_target_with_blend(camera,0)
    for cmd in ['DisableAllScreenMessages','r.VSync 0','t.MaxFPS 0','r.MotionBlurQuality 0']:console(cmd)
    yield 5
    console('ShowFlag.Rendering 1')
    for quality in [1,0,2,1]:
        console('gt.LandscapeMud.Quality '+str(quality))
        if DRIVE:
            car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
            car.set_actor_location_and_rotation(u.Vector(-850,0,140),u.Rotator(pitch=0,yaw=0,roll=0),False,True)
            mesh=car.get_component_by_class(u.SkeletalMeshComponent)
            mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
            car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
        yield 6
        entry=dict(quality=quality,surface_before=surface.get_surface_report())
        report['runs'].append(entry);save()
        before=files();console('csvprofile start')
        entry['start_position']=car.get_actor_location().to_tuple()
        if DRIVE:car.get_chaos_movement().set_handbrake_input(False);driving=True
        yield 6
        driving=False;car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
        entry['end_position']=car.get_actor_location().to_tuple()
        entry['effects']=surface.get_component_by_class(u.GTLandscapeWheelEffects).get_effect_report()
        console('csvprofile stop')
        yield 3
        new=sorted(files()-before)
        assert new,'No profiler CSV written'
        entry.update(csv=str(new[-1]),metrics=metrics(new[-1]),surface_after=surface.get_surface_report())
        assert entry['metrics'].get('FrameTime',{}).get('frames',0)>0
        save()
    console('ShowFlag.Rendering 0');report['ok']=True;save()
    u.EditorLevelLibrary.editor_end_play()
    yield 5
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

steps=run();deadline=0;busy=False
def tick(dt):
    global deadline,busy
    if busy:return
    if driving and car:
        move=car.get_chaos_movement()
        move.set_throttle_input(.6);move.set_brake_input(0)
        pos=car.get_actor_location();eye=pos+u.Vector(-620,650,230)
        camera.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,pos),False,False)
    if time.monotonic()<deadline:return
    busy=True
    try:deadline=time.monotonic()+next(steps)
    except StopIteration:pass
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error'])
        if world:console('ShowFlag.Rendering 0');console('csvprofile stop')
        u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
