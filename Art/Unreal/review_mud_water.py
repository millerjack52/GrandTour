"""Actual vehicle/solver coupling, volume and bounded-cost evidence in PIE."""
import json,math,time,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudWaterShared'
LEVEL='/Game/GrandTour/ArtTests/MudWater/L_MudWater'
report=dict(ok=False,level=LEVEL,samples=[],images=[],scope='Actual car crossing the pond; screenshots pause simulation. Solver timings are CPU only, not whole-game FPS.')
world=pc=car=surface=sheet=camera=mesh=move=None
def save():(OUT/'review-report.json').write_text(json.dumps(report,indent=2))
def console(s):u.SystemLibrary.execute_console_command(world,s,pc)
def stats():return {k:float(v) for k,v in (word.split('=') for word in sheet.mud_water_diagnostics().split())}
PROBES=[(x,y) for x in range(250,851,75) for y in range(-125,326,75)]
def sample():
    return dict(time=u.GameplayStatics.get_time_seconds(world),position=car.get_actor_location().to_tuple(),water=stats(),
        probes=[dict(x=x,y=y,wet=sheet.covers(u.Vector2D(x,y)),z=sheet.surface_cm_at(u.Vector2D(x,y)),flow=sheet.flow_cm_per_s_at(u.Vector2D(x,y)).length()) for x,y in PROBES],
        wheels=[dict(contact=w.get_editor_property('bInContact'),water_cm=u.GTLandscapeSurface.query_wheel_surface(car,w.contact_point,w.tyre_heading,22).water_depth_cm) for w in car.get_traction().wheels])
def capture(name):
    u.GameplayStatics.set_game_paused(world,True)
    report['images'].append(dict(name=name+'.png',time=u.GameplayStatics.get_time_seconds(world),position=car.get_actor_location().to_tuple(),water=stats()));save()
    console('ShowFlag.Rendering 1');yield 4
    path=OUT/(name+'.png');stamp=time.time();console('HighResShot 1440x900 filename="'+path.as_posix()+'"')
    end=time.monotonic()+90
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<end,'Screenshot timeout';yield .25
    last=path.stat().st_mtime;stable=time.monotonic()
    while time.monotonic()-stable<5:
        yield .25
        if path.stat().st_mtime!=last:last=path.stat().st_mtime;stable=time.monotonic()
    assert path.stat().st_size>40000,'Empty render: '+name
    console('ShowFlag.Rendering 0');u.GameplayStatics.set_game_paused(world,False);yield .05
def run():
    global world,pc,car,surface,sheet,camera,mesh,move
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(LEVEL);yield 3
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 10
    world=u.EditorLevelLibrary.get_game_world();assert world
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
    old=u.GameplayStatics.get_player_pawn(world,0)
    if old and old!=car:old.set_actor_hidden_in_game(True)
    old=None;pc.possess(car);car.disable_input(pc)
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    sheet=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)[0]
    surface.follow_player=False;surface.observe_player_wheels=True
    car.reset_driving_inputs();car.set_actor_location_and_rotation(u.Vector(-150,100,150),u.Rotator(),False,True)
    mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
    move=car.get_chaos_movement();move.set_handbrake_input(True)
    car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
    camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'MudWaterReviewCamera')
    camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(60)
    settings=camera.camera_component.get_editor_property('post_process_settings')
    settings.set_editor_property('override_auto_exposure_bias',True);settings.set_editor_property('auto_exposure_bias',.6)
    camera.camera_component.set_editor_property('post_process_settings',settings)
    eye=u.Vector(190,-630,390);target=u.Vector(500,110,-3)
    camera.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,target),False,False);pc.set_view_target_with_blend(camera,0)
    for cmd in ['showhud','DisableAllScreenMessages','r.MotionBlurQuality 0','r.VSync 0','t.MaxFPS 60']:console(cmd)
    start=u.GameplayStatics.get_time_seconds(world)
    while u.GameplayStatics.get_time_seconds(world)-start<5:yield .1
    report['before']=sample();save();yield from capture('water_00_before')
    start=u.GameplayStatics.get_time_seconds(world);move.set_handbrake_input(False)
    for seconds,name in [(3,'water_01_enter'),(6,'water_02_cross'),(9,'water_03_leave')]:
        while u.GameplayStatics.get_time_seconds(world)-start<seconds:
            move.set_throttle_input(.6);move.set_brake_input(0)
            report['samples'].append(sample());yield .1
        yield from capture(name)
        if seconds==6:
            # Close, fixed view across the free water next to the moving tyres.
            # Unequal wall-clock render times never advance the paused solver.
            close_eye=u.Vector(780,-240,90);close_target=u.Vector(480,125,-5)
            camera.set_actor_location_and_rotation(close_eye,u.MathLibrary.find_look_at_rotation(close_eye,close_target),False,False)
            for frame in range(6):
                due=6.15+frame*.2
                while u.GameplayStatics.get_time_seconds(world)-start<due:
                    move.set_throttle_input(.6);report['samples'].append(sample());yield .025
                yield from capture('motion_'+str(frame).zfill(2))
            camera.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,target),False,False)
    car.reset_driving_inputs();move.set_handbrake_input(True)
    report['after']=sample();save()
    # Exercise sleeping and waking without discarding a pond's water or accumulating old solid stamps.
    console('gt.Water.Mud.MaxActive 0');yield 1
    report['sleep']=stats();console('gt.Water.Mud.MaxActive 1');yield 1
    report['wake']=stats()
    # A short rendered run measures the solver in a real frame loop. Screenshots are excluded.
    console('ShowFlag.Rendering 1');yield 2
    report['rendered_start']=sample();wall=time.monotonic();report['rendered_samples']=[]
    while time.monotonic()-wall<8:report['rendered_samples'].append(sample());yield .1
    report['rendered_end']=sample();console('ShowFlag.Rendering 0')
    start_positions=report['before']['position'];end_positions=report['after']['position']
    report['travel_cm']=math.dist(start_positions[:2],end_positions[:2])
    all_samples=[report['before']]+report['samples']+[report['after']]
    report['max_water_speed_cm_s']=max(p['flow'] for s in all_samples for p in s['probes'] if p['wet'])
    report['max_wheel_water_cm']=max(w['water_cm'] for s in all_samples for w in s['wheels'])
    report['checks']=dict(shared_grid_built=report['after']['water']['cells']>0,
        volume_conserved=max(abs(s['water']['delta_m3']) for s in all_samples)<.001,
        bed_follows_mud=report['after']['water']['bed_updates']>0,
        car_reached_water=report['max_wheel_water_cm']>1,
        water_disturbed=report['max_water_speed_cm_s']>2,
        vehicle_displaced_water=max(s['water']['lids'] for s in all_samples)>0,
        no_depth_clamps=report['rendered_end']['water']['clamps']==0,
        sleeps_and_wakes=report['sleep']['awake']==0 and report['wake']['awake']==1,
        sleep_preserves_volume=abs(report['sleep']['volume_m3']-report['wake']['volume_m3'])<.001)
    log=(ROOT/'Saved/Logs/MudWater-Review.log').read_text(errors='replace')
    report['checks']['material_compiled']=not any('Failed to compile Material' in line and 'MudWater' in line for line in log.splitlines())
    report['ok']=all(report['checks'].values());save()
    u.EditorLevelLibrary.editor_end_play();yield 5
    world=pc=car=surface=sheet=camera=mesh=move=None
    assert les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 5
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
steps=run();deadline=0;busy=False;started=time.monotonic()
def tick(dt):
    global deadline,busy
    if busy:return
    busy=True
    try:
        assert time.monotonic()-started<840,'Review deadline exceeded'
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:pass
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error'])
        u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
