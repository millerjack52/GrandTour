"""Transient H2 driving/device smoke test on the existing rally course. Saves no assets."""
import gc, hashlib, json, time, traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve(); OUT=ROOT/'Saved/AudioH2QA'
report=dict(ok=False,trace=[],fleet=[]); world=pc=car=None
protected=[ROOT/'Content/GrandTour/ArtTests/RallyHandling/L_RallyHandling.umap',ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}

def save():(OUT/'drive.json').write_text(json.dumps(report,indent=2))
def wait(seconds):
    end=u.GameplayStatics.get_time_seconds(world)+seconds
    while u.GameplayStatics.get_time_seconds(world)<end:yield 0
def hybrid_audio(vehicle):
    return [c for c in vehicle.get_components_by_class(u.AudioComponent) if c.get_name()=='RangeRoverH2Audio']
def ground_report():
    return json.loads(car.get_component_by_class(u.GTRangeRoverAudioComponent).ground_audio_report())
def segment(name,seconds,throttle=0,brake=0):
    move=car.get_chaos_movement();start=u.GameplayStatics.get_time_seconds(world)
    while u.GameplayStatics.get_time_seconds(world)-start<seconds:
        move.set_throttle_input(throttle);move.set_brake_input(brake);car.set_raw_steer(0.)
        report['trace'].append(dict(scene=name,rpm=car.get_drivetrain().get_engine_rpm(),
            throttle=car.get_drivetrain().get_drive_input(),kmh=car.get_velocity().length()*.036,ground=ground_report()))
        yield .05

def run():
    global world,pc,car
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert level.load_level('/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling');yield 4
    level.editor_set_viewport_realtime(False)
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
    deadline=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<deadline;yield .2
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();car.disable_input(pc)
    for cmd in ['t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0']:
        u.SystemLibrary.execute_console_command(world,cmd,pc)
    # Shader/asset warmup must not consume the launch or leave the pawn airborne.
    car.get_chaos_movement().set_handbrake_input(True)
    stable=0;settle_deadline=time.monotonic()+120
    while stable<30:
        assert time.monotonic()<settle_deadline,'Scene did not settle for the driving check'
        stable=stable+1 if ground_report()['contacts']>=3 else 0
        yield .1
    yield from wait(3)
    assert len(hybrid_audio(car))==1 and hybrid_audio(car)[0].is_playing(),'RR audio device source did not start'
    assert ground_report()['recorded_ready'],'S3 ground recording bank not loaded'
    assert not car.get_audio().get_editor_property('muted'),'RR master mute must permit H2 playback'
    assert not any(c.is_playing() for c in car.get_components_by_class(u.AudioComponent) if c.get_name()=='VehicleAudio'),'Legacy RR synth must stay silent'
    yield from segment('idle',1)
    car.get_chaos_movement().set_handbrake_input(False)
    yield from segment('accelerate',9,1)
    yield from segment('lift',2)
    pull=[x for x in report['trace'] if x['scene']=='accelerate']
    assert max(x['rpm'] for x in pull)>1800 and max(x['kmh'] for x in pull)>20,'Drive did not exercise RPM'
    assert max(x['throttle'] for x in pull)>.9
    assert report['trace'][-1]['throttle']<.01,'Lift did not reach zero throttle'
    assert max(x['ground']['layers']['Gravel'] for x in pull)>.2,'Live gravel contacts did not drive ground audio'
    assert report['trace'][-1]['ground']['activity']>.1,'Coasting must retain rolling sound'
    assert report['trace'][-1]['ground']['body_speed']>.01,'Coasting must retain body rumble'
    assert report['trace'][-1]['ground']['rendered_frames']>0,'Recorded ground callback did not run'
    # Move to the actual grass verge; no terrain/audio override or saved asset changes.
    car.reset_driving_inputs();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    mesh.set_physics_linear_velocity(u.Vector(0,0,0),False);mesh.set_physics_angular_velocity_in_degrees(u.Vector(0,0,0),False)
    car.set_actor_location_and_rotation(u.Vector(-10000,-19500,220),u.Rotator(yaw=0),False,True)
    yield from wait(2)
    yield from segment('grass',3,.65)
    grass=[x for x in report['trace'] if x['scene']=='grass']
    assert max(x['ground']['layers']['Grass'] for x in grass)>.1,'Actual grass verge did not drive grass layer'
    # Contact loss must gate ground sound even while the wheels are spinning.
    car.reset_driving_inputs();car.set_actor_location(u.Vector(-10000,-19500,1600),False,True)
    yield from wait(.25)
    report['airborne_ground']=ground_report()
    assert report['airborne_ground']['contacts']==0 and report['airborne_ground']['activity']==0
    report['ground_gravel_grass_coast_airborne']=True
    pc.select_lane(1);car.reset_driving_inputs();yield from wait(.5)
    yield from segment('reverse',2,0,1)
    assert report['trace'][-1]['throttle']>.9,'Reverse pedal was not mapped to engine load'
    pc.select_lane(7);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True);yield from wait(1)
    assert pc.exit_car();yield from wait(1)
    assert not hybrid_audio(car)[0].is_playing(),'Unpossessed RR source must stop after its fade'
    report['exit_silent']=True
    assert pc.enter_vehicle(car);yield from wait(1)
    assert hybrid_audio(car)[0].is_playing(),'RR source did not restart on re-entry'
    report['reentry_plays']=True
    car.get_audio().set_muted(True);yield from wait(1)
    assert not hybrid_audio(car)[0].is_playing(),'Public vehicle mute must also mute H2'
    car.get_audio().set_muted(False);yield from wait(1)
    assert hybrid_audio(car)[0].is_playing(),'Public vehicle unmute must restore H2'
    report['master_mute_works']=True
    garage=u.GameplayStatics.get_all_actors_of_class(world,u.GTGarage)[0]
    for entry in garage.vehicles:
        default=u.get_default_object(entry.vehicle_class)
        mesh=default.get_component_by_class(u.SkeletalMeshComponent).get_skeletal_mesh_asset()
        report['fleet'].append(dict(name=str(entry.name),mesh=mesh.get_path_name()))
    approved='/Game/GrandTour/Vehicles/Bodies/RangeRover/SK_RangeRover.SK_RangeRover'
    assert sum(x['mesh']==approved for x in report['fleet'])==1,'Range Rover selection is ambiguous'
    # Exercise separate pawn instances using the same fleet classes as the garage.
    for name,path in [('BMW','E39Touring'),('Suzuki','SJ413')]:
        car.destroy_actor()
        cls=u.load_class(None,f'/Game/GrandTour/Vehicles/Bodies/{path}/BP_{path}.BP_{path}_C')
        car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,u.Transform(location=u.Vector(-10000,-18000,110)),name)
        pc.possess(car);car.disable_input(pc);yield from wait(1)
        assert not hybrid_audio(car),'Non-RR allocated hybrid audio'
        assert car.get_audio().get_editor_property('muted'),'Other cars must remain silent during this audition'
        assert not car.get_component_by_class(u.GTRangeRoverAudioComponent).is_component_tick_enabled()
    report['other_cars_silent']=True
    car.destroy_actor();car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.GTCarPawn,u.Transform(location=u.Vector(-10000,-18000,110)),'ReturnToRR')
    pc.possess(car);yield from wait(2)
    assert len(hybrid_audio(car))==1 and hybrid_audio(car)[0].is_playing()
    report['return_to_rr_plays']=True
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    report['maps_unchanged']=True;report['ok']=True;save()
    world=pc=car=garage=default=mesh=None;gc.collect();u.EditorLevelLibrary.editor_end_play();yield 4
    assert level.load_level('/Engine/Maps/Entry');yield 3

steps=run();deadline=0.;busy=False;began=time.monotonic()
def tick(dt):
    global deadline,busy,steps
    if busy or time.monotonic()<deadline:return
    busy=True;done=False
    try:
        assert time.monotonic()-began<480,'H2 drive timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
OUT.mkdir(parents=True,exist_ok=True);save()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
