"""Rendered contact study and bounded real-time frame timing. No visual pass is inferred from tests."""
import csv,json,math,statistics,time,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudProvingGround';CSV=ROOT/'Saved/Profiling/CSV'
QUICK='-GTMudProvingQuick' in u.SystemLibrary.get_command_line()
report=dict(ok=False,images=[],samples=[],performance={},visual_acceptance='pending image inspection',handling_acceptance='unapproved')
world=pc=car=surface=camera=None;driving=False;drive_start=0;next_sample=0;follow=False;phase='crawl'

def save(): (OUT/'review-report.json').write_text(json.dumps(report,indent=2))
def console(s):u.SystemLibrary.execute_console_command(world,s,pc)
def aim(eye,target):
    camera.set_actor_location_and_rotation(u.Vector(*eye),u.MathLibrary.find_look_at_rotation(u.Vector(*eye),u.Vector(*target)),False,False)
    pc.set_view_target_with_blend(camera,0)

def capture(name,eye,target):
    aim(eye,target);console('ShowFlag.Rendering 1')
    # Let PlayerCameraManager publish the new view, then freeze moving subjects.
    # Pausing before that tick preserves the previous camera's cached POV.
    yield .035 if driving else 2
    u.GameplayStatics.set_game_paused(world,True)
    yield 3
    p=OUT/(name+'.png');stamp=time.time()
    console('HighResShot 1440x900 filename="'+p.as_posix()+'"')
    deadline=time.monotonic()+60
    while not p.exists() or p.stat().st_mtime<stamp:
        assert time.monotonic()<deadline,'Screenshot timeout: '+name
        yield .25
    report['images'].append(str(p));save()
    u.GameplayStatics.set_game_paused(world,False);console('ShowFlag.Rendering 0')
    yield .1

def position(x,y,yaw=0):
    car.reset_driving_inputs();car.set_actor_location_and_rotation(u.Vector(x,y,150),u.Rotator(pitch=0,yaw=yaw,roll=0),False,True)
    mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
    car.get_chaos_movement().set_handbrake_input(True)

def metrics(path):
    with path.open(newline='') as f:rows=list(csv.reader(f))
    result={}
    for i,key in enumerate(rows[0]):
        if key not in ['FrameTime','GameThreadTime','RenderThreadTime','RHIThreadTime','GPUTime']:continue
        values=[]
        for row in rows[1:]:
            if not row or row[0].startswith('[') or row[0]=='EVENTS':break
            try:values.append(float(row[i]))
            except (ValueError,IndexError):pass
        if values:
            values.sort();result[key]=dict(frames=len(values),mean_ms=statistics.fmean(values),p99_ms=values[min(len(values)-1,math.ceil(len(values)*.99)-1)])
    return result

def run():
    global world,pc,car,surface,camera,driving,drive_start,next_sample,follow,phase
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/MudProvingGround/L_MudProvingGround')
    yield 5
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
    yield 10
    world=u.EditorLevelLibrary.get_game_world();assert world
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
    old=u.GameplayStatics.get_player_pawn(world,0)
    if old and old!=car:old.set_actor_hidden_in_game(True)
    old=None
    pc.possess(car);car.disable_input(pc);position(-1250,-700);car.set_actor_hidden_in_game(True)
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    surface.observe_player_wheels=False;surface.follow_player=False
    camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'ProvingCamera')
    camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(65)
    settings=camera.camera_component.get_editor_property('post_process_settings')
    settings.set_editor_property('override_auto_exposure_bias',True);settings.set_editor_property('auto_exposure_bias',.6)
    camera.camera_component.set_editor_property('post_process_settings',settings)
    for cmd in ['showhud','DisableAllScreenMessages','r.MotionBlurQuality 0','r.VSync 0','t.MaxFPS 60']:console(cmd)
    yield 5
    log=(ROOT/'Saved/Logs/MudProvingGround-Review.log').read_text(errors='replace')
    assert not any('Failed to compile Material' in line and 'MudProvingGround' in line for line in log.splitlines()),'Proving material shader compilation failed'
    report['surface_before']=surface.get_surface_report();save()
    yield from capture('01_shape_wide',(-1100,-520,380),(200,0,0))
    yield from capture('02_pool_edge',(240,-210,85),(670,140,-8))
    yield from capture('03_old_ruts',(-900,-230,100),(-100,20,0))
    yield from capture('04_overview',(-250,-750,1650),(50,0,0))
    car.set_actor_hidden_in_game(False);position(-950,0)
    surface.observe_player_wheels=True
    car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
    yield 3
    drive_start=u.GameplayStatics.get_time_seconds(world);next_sample=0;driving=True
    while u.GameplayStatics.get_time_seconds(world)-drive_start<2:yield .1
    p=car.get_actor_location()
    yield from capture('05a_working_tyres',(p.x-280,p.y-380,p.z+140),(p.x,p.y,p.z-35))
    while u.GameplayStatics.get_time_seconds(world)-drive_start<8:yield .1
    driving=False;car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
    p=car.get_actor_location();report['drive_end']=list(p.to_tuple())
    yield from capture('05_loaded_tyres',(p.x+280,p.y-340,p.z+65),(p.x,p.y,p.z-55))
    car.set_actor_hidden_in_game(True);surface.observe_player_wheels=False
    yield from capture('06_driven_tracks',(-1180,-240,100),(-600,0,-6))
    car.set_actor_hidden_in_game(False);position(-150,-230,90);surface.observe_player_wheels=True
    yield 3
    phase='crossing';drive_start=u.GameplayStatics.get_time_seconds(world);next_sample=0;driving=True
    while u.GameplayStatics.get_time_seconds(world)-drive_start<8 and car.get_actor_location().y<230:yield .1
    driving=False;car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
    p=car.get_actor_location();report['crossing_end']=p.to_tuple()
    yield from capture('07_crossing',(p.x+360,p.y-450,p.z+190),(p.x,p.y,p.z-20))
    # Momentum entry checks for the old high-speed planing failure under actual wheel forces.
    position(-950,190);car.get_drivetrain().set_low_range(False)
    yield 3
    car.get_component_by_class(u.SkeletalMeshComponent).set_physics_linear_velocity(u.Vector(600,0,0))
    phase='momentum_entry';drive_start=u.GameplayStatics.get_time_seconds(world);next_sample=0;driving=True
    while u.GameplayStatics.get_time_seconds(world)-drive_start<3:yield .1
    p=car.get_actor_location()
    yield from capture('08_momentum_entry',(p.x-280,p.y-400,p.z+115),(p.x,p.y,p.z-30))
    while u.GameplayStatics.get_time_seconds(world)-drive_start<6:yield .1
    driving=False;car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
    report['momentum_end']=car.get_actor_location().to_tuple()
    # A second entry accelerates on firm ground, retaining real wheel angular momentum.
    position(-300,-1200,90);yield 3
    phase='rolling_entry';drive_start=u.GameplayStatics.get_time_seconds(world);next_sample=0;driving=True
    while u.GameplayStatics.get_time_seconds(world)-drive_start<10 and car.get_actor_location().y<230:yield .1
    driving=False;car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
    report['rolling_entry_end']=car.get_actor_location().to_tuple()
    car.get_drivetrain().set_low_range(True)
    # Timestamped rendered sequence for judging the interaction in motion, not just stills.
    position(-950,0);yield 3
    phase='motion_review';drive_start=u.GameplayStatics.get_time_seconds(world);next_sample=0;driving=True;follow=True
    report['motion_frames']=[];console('ShowFlag.Rendering 1')
    for frame in range(10 if QUICK else 28):
        next_time=u.GameplayStatics.get_time_seconds(world)+.18
        while u.GameplayStatics.get_time_seconds(world)<next_time:yield .02
        p=OUT/('motion_%03d.png'%frame);stamp=time.time()
        console('HighResShot 960x600 filename="'+p.as_posix()+'"')
        deadline=time.monotonic()+20
        while not p.exists() or p.stat().st_mtime<stamp:
            assert time.monotonic()<deadline,'Motion frame timeout'
            yield .02
        report['motion_frames'].append(dict(file=p.name,time=u.GameplayStatics.get_time_seconds(world)-drive_start))
    driving=False;follow=False;car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True);save()
    car.set_actor_hidden_in_game(True);surface.observe_player_wheels=False
    if QUICK:
        report['performance']={'scope':'Render/handling check only; timing capture deferred due GPU contention'}
        report['driving_performance']=[]
        yield from finish();return
    # Profile the active pool/soil scene separately from screenshots, unpaused and without fixed timestep.
    aim((150,-470,190),(640,100,-5));console('ShowFlag.Rendering 1');console('t.MaxFPS 0')
    yield 5
    before=set(CSV.glob('*.csv'));console('csvprofile start')
    yield 8
    console('csvprofile stop');yield 3
    paths=sorted(set(CSV.glob('*.csv'))-before);assert paths,'No frame timing CSV'
    report['performance']=dict(csv=str(paths[-1]),metrics=metrics(paths[-1]),scope='8-second stationary pool/soil diagnostic at 1440x900; not driving or streaming acceptance')
    report['driving_performance']=[]
    for quality in [1,0]:
        console('gt.LandscapeMud.Quality '+str(quality))
        car.set_actor_hidden_in_game(False);position(-1050,240);surface.observe_player_wheels=True;follow=True
        p=car.get_actor_location();aim((p.x-500,p.y-450,p.z+200),p.to_tuple())
        yield 4
        phase='profile_quality_'+str(quality);drive_start=u.GameplayStatics.get_time_seconds(world);next_sample=0;driving=True
        before=set(CSV.glob('*.csv'));console('csvprofile start');yield 8
        driving=False;follow=False;car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
        console('csvprofile stop');yield 3
        paths=sorted(set(CSV.glob('*.csv'))-before);assert paths
        report['driving_performance'].append(dict(quality=quality,csv=str(paths[-1]),metrics=metrics(paths[-1]),effects=surface.get_component_by_class(u.GTLandscapeWheelEffects).get_effect_report()))
        save()
    yield from finish()

def finish():
    global world,pc,car,surface,camera
    report['surface_after']=surface.get_surface_report();report['ok']=True;save()
    console('ShowFlag.Rendering 0');u.EditorLevelLibrary.editor_end_play();yield 5
    world=pc=car=surface=camera=None
    # Release the test world's dynamic textures and Niagara systems while the RHI
    # is still alive, instead of leaving their teardown to process shutdown.
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
    u.SystemLibrary.collect_garbage();yield 5
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

steps=run();deadline=0;busy=False;started=time.monotonic()
def tick(dt):
    global deadline,busy,next_sample
    if busy:return
    busy=True
    try:
        if time.monotonic()-started>600:raise RuntimeError('Proving review deadline exceeded')
        if driving:
            move=car.get_chaos_movement();move.set_handbrake_input(False);move.set_throttle_input(.6);move.set_brake_input(0)
            if follow:
                p=car.get_actor_location();aim((p.x-500,p.y-450,p.z+200),p.to_tuple())
            t=u.GameplayStatics.get_time_seconds(world)-drive_start
            if t>=next_sample:
                wheels=car.get_traction().wheels
                tuning=car.get_component_by_class(u.GTVehicleTuningComponent).get_current()
                report['samples'].append(dict(phase=phase,t=t,position=car.get_actor_location().to_tuple(),speed_cm_s=car.get_velocity().length(),
                    tyre_coat=list(car.get_body_state().tyre_coat),
                    tread_cm_s=[w.tread_cm_per_s for w in wheels],effects=surface.get_component_by_class(u.GTLandscapeWheelEffects).get_effect_report(),
                    sinkage=[w.sinkage_cm for w in tuning.wheels],contacts=[w.get_editor_property('bInContact') for w in wheels],
                    ground=[surface.sample_surface(u.Vector2D(w.contact_point.x,w.contact_point.y)).surface_delta_cm for w in wheels]))
                next_sample=t+.2
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:pass
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error'])
        if world:console('ShowFlag.Rendering 0');console('csvprofile stop');u.GameplayStatics.set_game_paused(world,False)
        u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
