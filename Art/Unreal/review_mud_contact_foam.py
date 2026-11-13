"""Matched live vehicle passes, opt-in bank-work telemetry and rendered soil/water review."""
import csv,json,math,time,traceback,statistics
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudContactFoam'
BASE='/Game/GrandTour/ArtTests/RutInteraction/L_RutInteraction'
report=dict(ok=False,images=[],scope='Shared water contact foam, paired rendered review and passive simulation checks.')
world=pc=car=surface=sheet=camera=mesh=move=None
def save():(OUT/'review-report.json').write_text(json.dumps(report,indent=2))
def console(s):u.SystemLibrary.execute_console_command(world,s,pc)
def numbers(s):return {k:float(v) for k,v in (x.split('=') for x in s.split())}
def frame_metrics(path):
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
def sample():
    supports=[]
    for w,t in zip(car.get_traction().wheels,car.get_tuning().get_current().wheels):
        s=u.GTLandscapeSurface.query_wheel_surface(car,w.contact_point,w.tyre_heading,25)
        supports.append(dict(authored=s.get_editor_property('bWheelSupport'),sink=t.sinkage_cm,ground=t.ground_support_cm,settlement=max(0,s.rest_wheel_support_cm-t.ground_support_cm)+t.sinkage_cm))
    return dict(time=u.GameplayStatics.get_time_seconds(world),position=car.get_actor_location().to_tuple(),rotation=car.get_actor_rotation().to_tuple(),
        speed=car.get_velocity().length(),steer_degrees=[w.get_steer_angle() for w in move.wheels],bank=numbers(move.rut_interaction_report()),water=numbers(sheet.mud_water_diagnostics()),
        soil=numbers(surface.get_surface_report()),
        wheels=[dict(contact=w.get_editor_property('bInContact'),slip=w.slip_magnitude,tread=w.tread_cm_per_s) for w in car.get_traction().wheels],
        support=supports)
def aim(eye,target):
    camera.set_actor_location_and_rotation(u.Vector(*eye),u.MathLibrary.find_look_at_rotation(u.Vector(*eye),u.Vector(*target)),False,False)
    pc.set_view_target_with_blend(camera,0)
def capture(name,eye,target):
    aim(eye,target);yield .04
    u.GameplayStatics.set_game_paused(world,True);console('ShowFlag.Rendering 1');yield 4
    path=OUT/(name+'.png');stamp=time.time();console('HighResShot 1440x900 filename="'+path.as_posix()+'"')
    end=time.monotonic()+90
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<end,'Screenshot timeout';yield .25
    last=path.stat().st_mtime;stable=time.monotonic()
    while time.monotonic()-stable<5:
        yield .25
        if path.stat().st_mtime!=last:last=path.stat().st_mtime;stable=time.monotonic()
    assert path.stat().st_size>40000,'Empty render'
    report['images'].append(dict(file=name+'.png',time=u.GameplayStatics.get_time_seconds(world)));save()
    console('ShowFlag.Rendering 0');yield .05

def run():
    global world,pc,car,surface,sheet,camera,mesh,move
    les=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert les.load_level(BASE);yield 2
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 8
    world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
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
    camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'MudContactFoamCamera')
    camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(60)
    settings=camera.camera_component.get_editor_property('post_process_settings');settings.set_editor_property('override_auto_exposure_bias',True);settings.set_editor_property('auto_exposure_bias',.6)
    camera.camera_component.set_editor_property('post_process_settings',settings)
    for cmd in ['showhud','DisableAllScreenMessages','r.MotionBlurQuality 0','r.VSync 0','t.MaxFPS 60']:console(cmd)
    yield 5
    report['before']=sample();save()
    # Same camera and paused state for off/on comparisons. Change the MID only;
    # the cvar remains enabled so physics and foam history are identical.
    materials=[c.get_material(0) for c in sheet.get_components_by_class(u.PrimitiveComponent) if c.get_num_materials()>0 and isinstance(c.get_material(0),u.MaterialInstanceDynamic)]
    assert materials,'Missing runtime water material'
    def visibility(value):
        for mat in materials:mat.set_scalar_parameter_value('ContactFoamAmount',value)
    visibility(0);yield from capture('clods_off',(340,-210,180),(200,110,-8))
    visibility(1);yield from capture('clods_on',(340,-210,180),(200,110,-8))
    u.GameplayStatics.set_game_paused(world,False)
    start=u.GameplayStatics.get_time_seconds(world);move.set_handbrake_input(False);report['samples']=[]
    while u.GameplayStatics.get_time_seconds(world)-start<4:
        move.set_throttle_input(.5);move.set_brake_input(0);car.set_raw_steer(.1)
        report['samples'].append(sample());yield .1
    car.reset_driving_inputs();move.set_handbrake_input(True)
    report['after_drive']=sample();p=car.get_actor_location()
    eye=(p.x+220,p.y-340,p.z+160);target=(p.x+70,p.y,p.z-40)
    visibility(1);yield from capture('tyres_on',eye,target)
    visibility(0);yield from capture('tyres_off',eye,target)
    visibility(1)
    u.GameplayStatics.set_game_paused(world,False)
    # Rendered driving segment and actual cosmetic CPU cost.
    aim((190,-630,390),(200,110,-3));console('ShowFlag.Rendering 1');yield 2
    csv_start=time.time();console('csvprofile start');start=time.monotonic()
    move.set_handbrake_input(False);move.set_throttle_input(.3);car.set_raw_steer(.1)
    while time.monotonic()-start<6:report['samples'].append(sample());yield .1
    console('csvprofile stop');car.reset_driving_inputs();move.set_handbrake_input(True);yield 3
    files=[p for p in (ROOT/'Saved/Profiling/CSV').glob('*.csv') if p.stat().st_mtime>=csv_start]
    assert files
    latest=max(files,key=lambda p:p.stat().st_mtime);report['frame_profile']=frame_metrics(latest)
    report['after']=sample();save()
    # Temporary immersed stone validates a real mesh waterline as well as the
    # displaced terrain shoreline. It is never saved into the driving maps.
    car.set_actor_hidden_in_game(True)
    candidates=[(surface.sample_surface(u.Vector2D(x,y)).water_depth_cm,x,y) for x in range(-100,451,25) for y in range(-150,301,25)]
    depth,x,y=max(candidates);assert depth>3
    stone=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(),'FoamReviewStone')
    rock=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Benmore_Rock1');assert rock
    component=stone.static_mesh_component;component.set_mobility(u.ComponentMobility.MOVABLE);component.set_static_mesh(rock);component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    bounds=rock.get_bounds();scale=55/max(bounds.box_extent.x*2,bounds.box_extent.y*2)
    stone.set_actor_scale3d(u.Vector(scale,scale,scale));level=sheet.surface_cm_at(u.Vector2D(x,y))
    placement=u.Vector(x-bounds.origin.x*scale,y-bounds.origin.y*scale,level-bounds.origin.z*scale+3)
    stone.set_actor_location(placement,False,True)
    assert (stone.get_actor_location()-placement).length()<1,'Review stone did not move into the water'
    eye=(x+120,y-150,level+120);target=(x,y,level)
    visibility(0);yield from capture('stone_off',eye,target)
    visibility(1);yield from capture('stone_on',eye,target)
    report['stone_test']=dict(depth_cm=depth,position=[x,y,level],temporary=True)
    stone.destroy_actor();stone=component=rock=materials=None
    u.GameplayStatics.set_game_paused(world,False)
    console('ShowFlag.Rendering 0');yield 2
    materials=None;u.EditorLevelLibrary.editor_end_play();yield 5
    world=pc=car=surface=sheet=camera=mesh=move=None
    assert les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 5
    all_samples=[report['before'],report['after']]+report['samples']
    report['checks']=dict(foam_generated=max(s['water']['foam_peak'] for s in all_samples)>.025,
        water_conserved=all(abs(s['water']['delta_m3'])<.001 for s in all_samples),
        no_water_clamps=all(s['water']['clamps']==0 for s in all_samples),
        finite_car=all(math.isfinite(v) for s in all_samples for v in s['position']),
        rendered_pairs=len(report['images'])==6)
    report['ok']=all(report['checks'].values());save()
    les=None;u.SystemLibrary.collect_garbage();yield 5
    # Finish the generator before quitting so no Python frame retains editor objects.
    return

steps=run();deadline=0;busy=False;started=time.monotonic()
def tick(dt):
    global deadline,busy
    if busy:return
    busy=True
    try:
        assert time.monotonic()-started<840,'Review deadline exceeded'
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:
        u.unregister_slate_post_tick_callback(handle);steps.close();u.SystemLibrary.collect_garbage();u.SystemLibrary.quit_editor()
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error'])
        u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)

