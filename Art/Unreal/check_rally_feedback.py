"""Transient roll/surface diagnostic on the existing circuit. Injected 60 km/h,
fixed steering doublet: isolates body motion, not a complete-corner verdict."""
import gc, hashlib, json, math, os, time, traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();QA=ROOT/'Saved/RallyHandlingQA'
LABEL=os.environ.get('GT_RALLY_HANDLING_LABEL','feedback')
VISUAL_ONLY=os.environ.get('GT_RALLY_FEEDBACK_VISUAL','0')=='1'
report=dict(ok=False,label=LABEL,runs=[],note=__doc__,visual_only=VISUAL_ONLY)
world=pc=car=None
protected=ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap';digest=hashlib.sha256(protected.read_bytes()).hexdigest()
def save():(QA/('feedback-'+LABEL+'.json')).write_text(json.dumps(report,indent=2))
def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)
def wait(seconds):
    until=u.GameplayStatics.get_time_seconds(world)+seconds
    while u.GameplayStatics.get_time_seconds(world)<until:yield 0
def capture(name):
    path=QA/(LABEL+'-'+name+'.png');stamp=time.time()
    u.GameplayStatics.set_game_paused(world,True);yield .2
    cmd('HighResShot 1600x900 filename="'+path.as_posix()+'"')
    end=time.monotonic()+45
    while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<end;yield .2
    report.setdefault('images',[]).append(str(path))
    u.GameplayStatics.set_game_paused(world,False)
def probe(name,cls,variant):
    global car
    if car:car.destroy_actor()
    cmd('gt.Vehicle.RallyRide '+str(int(variant!='baseline')))
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,u.Transform(location=u.Vector(-10000,-18000,110)),'Feedback_'+name)
    pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();car.set_chase_camera(True)
    move=car.get_chaos_movement();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    car.get_drivetrain().set_low_range(variant=='low');move.set_handbrake_input(True)
    yield from wait(4)
    wheels=move.get_editor_property('wheels')
    setup=[{k:w.get_editor_property(k) for k in ['spring_rate','suspension_damping_ratio','spring_preload','suspension_max_raise','suspension_max_drop','rollbar_scaling']} for w in wheels]
    classes=[s.get_editor_property('wheel_class') for s in move.get_editor_property('wheel_setups')]
    original_defaults=[u.get_default_object(cls).get_editor_property('spring_rate') for cls in classes]
    row=dict(car=name,variant=variant,suspension=setup,com=list(mesh.get_center_of_mass().to_tuple()),trace=[])
    report['runs'].append(row)
    move.set_handbrake_input(False);mesh.set_physics_linear_velocity(u.Vector(1666.667,0,0),False)
    start=u.GameplayStatics.get_time_seconds(world);previous_velocity=car.get_velocity();previous_time=start
    photographed=False
    while True:
        t=u.GameplayStatics.get_time_seconds(world)-start
        if t>3.2:break
        steer=.65 if .55<=t<1.1 else -.65 if 1.1<=t<1.65 else 0.
        car.set_raw_steer(steer);move.set_throttle_input(0)
        v=car.get_velocity();rot=car.get_actor_rotation();p=car.get_actor_location()
        acc=(v-previous_velocity)/max(.001,t+start-previous_time)
        solver=json.loads(move.rally_handling_report())
        row['trace'].append(dict(t=t,raw=steer,roll=rot.roll,pitch=rot.pitch,yaw=rot.yaw,z=p.z,kmh=v.length()*.036,lateral_g=u.MathLibrary.dot_vector_vector(acc,car.get_actor_right_vector())/980.,wheel_z=[w.get_suspension_offset() for w in wheels],grit_rate=sum(car.get_spray().get_fine_rate(i,1) for i in range(4)),grit_live=car.get_spray().get_fine_live_count(1),ride_weight=move.get_rally_suspension_weight(),ride_scale=solver['ride_scale'],contacts=sum(w['contact'] for w in solver['wheels'])))
        previous_velocity=v;previous_time=start+t
        if variant=='candidate' and name=='RangeRover' and t>1.05 and not photographed:
            photographed=True;yield from capture(name+'-gravel-roll')
            if VISUAL_ONLY:
                # Let the camera manager update before pausing for a tyre-scale shot.
                origin=car.get_actor_location();forward=car.get_actor_forward_vector();right=car.get_actor_right_vector()
                position=origin-forward*340+right*300+u.Vector(0,0,75)
                target=origin-forward*175+u.Vector(0,0,10)
                rotation=u.MathLibrary.find_look_at_rotation(position,target)
                camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=position,rotation=rotation),'GravelVisualCamera')
                pc.set_view_target_with_blend(camera,0.);yield from wait(.05)
                yield from capture(name+'-gravel-close')
                pc.set_view_target_with_blend(car,0.);camera.destroy_actor()
            previous_velocity=car.get_velocity();previous_time=u.GameplayStatics.get_time_seconds(world)
        yield 0
    car.reset_driving_inputs();move.set_handbrake_input(True)
    row['peak_roll_deg']=max(abs(r['roll']) for r in row['trace']);row['peak_lateral_g']=max(abs(r['lateral_g']) for r in row['trace'])
    row['max_grit_live']=max(r['grit_live'] for r in row['trace'])
    assert original_defaults==[u.get_default_object(cls).get_editor_property('spring_rate') for cls in classes],'Shared wheel defaults mutated'
    row['shared_defaults_unchanged']=True
    if variant=='low':assert all(r['ride_scale']==1 and r['ride_weight']==0 for r in row['trace'])
    if variant=='candidate':
        assert min(r['ride_scale'] for r in row['trace'])<.9
        assert row['max_grit_live']>0,'No flying gravel particles'
        car.get_drivetrain().set_low_range(True);yield from wait(.15)
        row['low_range_restored_scale']=json.loads(move.rally_handling_report())['ride_scale']
        assert row['low_range_restored_scale']==1 and move.get_rally_suspension_weight()==0
    save();yield from wait(.5)
def run():
    global world,pc,car
    L=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert L.load_level('/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling');yield 5
    L.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
    end=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<end;yield .2
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car()
    cmd('t.IdleWhenNotForeground 0');cmd('Slate.bAllowThrottling 0');yield from wait(6)
    specs=[('RangeRover',u.GTCarPawn),('BMW',u.load_class(None,'/Game/GrandTour/Vehicles/Bodies/E39Touring/BP_E39Touring.BP_E39Touring_C')),('Suzuki',u.load_class(None,'/Game/GrandTour/Vehicles/Bodies/SJ413/BP_SJ413.BP_SJ413_C'))]
    if VISUAL_ONLY:specs=specs[:1]
    for name,cls in specs:
        for variant in (['candidate'] if VISUAL_ONLY else ['baseline','candidate','low']):yield from probe(name,cls,variant)
    cmd('gt.Vehicle.RallyRide 1')
    assert hashlib.sha256(protected.read_bytes()).hexdigest()==digest
    report['ok']=True;report['lidar_map_unchanged']=True;save()
    world=pc=car=None;gc.collect();u.EditorLevelLibrary.editor_end_play();yield 4
    assert L.load_level('/Engine/Maps/Entry');yield 3
steps=run();deadline=0.;busy=False;began=time.monotonic()
def tick(dt):
    global deadline,busy,steps
    if busy or time.monotonic()<deadline:return
    busy=True;done=False
    try:
        assert time.monotonic()-began<600,'Feedback timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
save();u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
