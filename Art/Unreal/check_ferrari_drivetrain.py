"""Ferrari-only drivetrain, steering and suspension probes in the existing rally map."""
import gc,hashlib,json,math,time,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Saved/FerrariDrivingQA';OUT.mkdir(parents=True,exist_ok=True)
BASELINE='-gtferraribaseline' in u.SystemLibrary.get_command_line().lower()
REPORT=OUT/('baseline.json' if BASELINE else 'check.json')
report=dict(ok=False,baseline=BASELINE,checks=[]);world=pc=car=None
protected=[ROOT/p for p in ['Content/GrandTour/ArtTests/RallyHandling/L_RallyHandling.umap','Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap','Content/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288.uasset']]
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
saved={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Saved/SaveGames').glob('*.sav')}
def save():REPORT.write_text(json.dumps(report,indent=2))
def check(value,label):
    assert value,label
    report['checks'].append(label);save()
def now():return u.GameplayStatics.get_time_seconds(world)
def wait(seconds):
    end=now()+seconds
    while now()<end:yield .02
def sample():
    move=car.get_chaos_movement();d=json.loads(car.get_drivetrain().setup_report());v=car.get_velocity();rot=car.get_actor_rotation()
    d.update(speed_kmh=v.length()*.036,forward_kmh=move.get_forward_speed()*.036,roll=rot.roll,pitch=rot.pitch,z=car.get_actor_location().z,vz=v.z,
        yaw=rot.yaw,slip=((math.degrees(math.atan2(v.y,v.x))-rot.yaw+180)%360-180) if v.length()>100 else 0,
        wheel_nm=[w.drive_torque_nm for w in car.get_drivetrain().wheels],omega=[w.omega_rad_s for w in car.get_drivetrain().wheels],
        wheel_z=[w.get_suspension_offset() for w in move.wheels],solver=json.loads(move.rally_handling_report()))
    return d
def drive(seconds,throttle,steer=0,brake=0,handbrake=False):
    move=car.get_chaos_movement();start=now();samples=[]
    while now()-start<seconds:
        move.set_handbrake_input(handbrake);move.set_throttle_input(throttle);move.set_brake_input(brake);car.set_raw_steer(steer)
        d=sample();d['t']=now()-start;samples.append(d);yield .02
    car.reset_driving_inputs();return samples
def fresh(transform=None):
    global car
    if car:car.reset_driving_inputs();car.destroy_actor();yield .1
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,transform or start_transform,'FerrariDrivingQA')
    pc.possess(car);car.disable_input(pc)
    if transform is None:pc.select_lane(1)
    car.get_chaos_movement().set_handbrake_input(True);yield from wait(3)
    car.get_drivetrain().set_low_range(False);car.get_drivetrain().set_diff_lock(False)
    check(car.get_velocity().length()<30,'Ferrari settles')
def run():
    global world,pc,car,cls,start_transform
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(level.load_level('/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling'),'existing rally map loads');yield 3
    level.editor_set_viewport_realtime(False);check(u.GTPlayWindowLibrary.request_play_in_new_window(1600,900),'PIE starts')
    end=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<end;yield .2
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();pc.select_lane(1);yield from wait(3)
    for cmd in ['t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0']:u.SystemLibrary.execute_console_command(world,cmd,pc)
    start_transform=car.get_actor_transform();start_transform.translation+=u.Vector(0,0,60)
    cls=u.load_class(None,'/Game/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288.BP_Ferrari288_C')
    yield from fresh()
    move=car.get_chaos_movement();engine=move.get_editor_property('engine_setup');trans=move.get_editor_property('transmission_setup')
    com=move.get_editor_property('center_of_mass_override')
    report['settings']=dict(mass=move.get_editor_property('mass'),com_cm=[com.x,com.y,com.z],chassis_cm=[move.get_editor_property('chassis_width'),move.get_editor_property('chassis_height')],engine={k:engine.get_editor_property(k) for k in ['max_torque','max_rpm','engine_idle_rpm']},
        gears=list(trans.get_editor_property('forward_gear_ratios')),front_share=car.get_drivetrain().get_editor_property('centre_split_front'),
        wheels=[{k:w.get_editor_property(k) for k in ['spring_rate','suspension_damping_ratio','suspension_max_raise','suspension_max_drop','max_steer_angle','rollbar_scaling']} for w in move.wheels],solver_suspension=json.loads(move.suspension_report()))
    rev=yield from drive(3,1,handbrake=True);lift=yield from drive(2,0,handbrake=True);yield from drive(2,1,handbrake=True);launch=yield from drive(4,1)
    report['handbrake']=dict(rev=rev,lift=lift,launch=launch);save()
    if not BASELINE:
        check(report['settings']['front_share']==0 and len(report['settings']['gears'])==5 and report['settings']['engine']['max_rpm']==7500,'fresh Ferrari receives its own RWD five-speed engine configuration')
        check(all(w['suspension_max_raise']==8 and w['suspension_max_drop']==12 for w in report['settings']['wheels']),'expanded Ferrari suspension travel survives reload')
        check(report['settings']['wheels'][0]['spring_rate']==260 and report['settings']['wheels'][2]['spring_rate']==280,'Ferrari front and rear spring rates survive reload')
        check(abs(report['settings']['wheels'][0]['suspension_damping_ratio']-.72)<.001 and abs(report['settings']['wheels'][2]['suspension_damping_ratio']-.76)<.001,'Ferrari damping survives reload')
        check(report['settings']['wheels'][0]['max_steer_angle']==35,'Ferrari steering lock survives reload')
        check(max(s['rpm'] for s in rev)>7000,'handbrake reaches Ferrari rev range')
        check(max(s['speed_kmh'] for s in rev)<1,'handbrake holds car stationary')
        check(all(abs(s['requested_wheel_nm'])<.01 and s['clutch_engagement']==0 for s in rev if s['t']>.3),'handbrake disconnects actual wheel drive')
        check(lift[-1]['rpm']<rev[-1]['rpm']-1500,'engine runs down on lift')
        check(max(s['speed_kmh'] for s in launch)>30,'clutch release launches Ferrari')
        check(any(0<s['clutch_engagement']<1 for s in launch),'clutch release is progressive')
        check(max(s['rpm'] for s in rev+launch)<=7651,'Ferrari limiter remains bounded')
    yield from fresh();report['acceleration']=yield from drive(9,1);save()
    if not BASELINE:
        check(max(s['speed_kmh'] for s in report['acceleration'])>60,'normal Ferrari acceleration')
        check(max(s['gear'] for s in report['acceleration'])>=2,'automatic shifts work')
        check(all(s['solver']['ride_scale']==1 for s in report['acceleration']),'Ferrari suspension stays fixed as speed rises')
        check(all(abs(s['wheel_nm'][0])+abs(s['wheel_nm'][1])<.01 for s in report['acceleration']),'Ferrari remains rear-wheel drive')
        check(all(abs(s['shaft_rpm']-abs((s['omega'][2]+s['omega'][3])*.5)*s['total_ratio']*60/(2*math.pi))<2 for s in report['acceleration']),'shaft RPM follows driven rear wheels')
        low=car.get_drivetrain().is_low_range();car.get_drivetrain().set_low_range(not low);check(car.get_drivetrain().is_low_range()==low,'moving transfer shift rejected')
    yield from fresh();yield from drive(4,.7)
    left=yield from drive(1,.5,.5);right=yield from drive(1,.5,-.5);recover=yield from drive(3,.65)
    report['steering']=left+right+recover;save()
    check(max(abs(s['roll']) for s in report['steering'])<30,'steering reversal stays upright')
    if not BASELINE:
        check(all(abs(w['angle'])<.1 for w in recover[-1]['solver']['wheels'][:2]),'released steering returns to centre without autonomous steering')
    # Repeatable small crest above the existing world, no saved map modification.
    flat=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(location=u.Vector(0,-10000,20000),scale=u.Vector(200,16,.5)),'FerrariFixture')
    floor=flat.static_mesh_component;floor.set_mobility(u.ComponentMobility.MOVABLE);floor.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));floor.set_collision_profile_name('BlockAll')
    bumps=[]
    for x,pitch in [(-4000,4),(-3885,-4)]:
        a=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(location=u.Vector(x,-10000,20024),rotation=u.Rotator(pitch=pitch),scale=u.Vector(1.15,16,.1)),'FerrariBump')
        c=a.static_mesh_component;c.set_mobility(u.ComponentMobility.MOVABLE);c.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));c.set_collision_profile_name('BlockAll');bumps.append(a)
    fixture=u.Transform(location=u.Vector(-6000,-10000,20120))
    yield from fresh(fixture)
    mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector(1666.667,0,0),False)
    report['bump']=yield from drive(4,0);save()
    check(max(abs(s['roll']) for s in report['bump'])<15,'crest stays upright')
    check(abs(report['bump'][-1]['pitch'])<4 and abs(report['bump'][-1]['vz'])<40,'suspension settles after small crest')
    for a in bumps:a.destroy_actor()
    slippery=u.new_object(u.PhysicalMaterial);slippery.set_editor_property('friction',.08);floor.set_phys_material_override(slippery)
    yield from fresh(fixture)
    # Idle launch must now build sustained wheelspin without a clutch dump.
    report['slip']=yield from drive(6,1);save()
    if not BASELINE:
        powered=[s for s in report['slip'] if s['t']>.5 and s['engine_nm']>50]
        check(len(powered)>10,'low grip retains powered samples')
        check(all(abs(s['requested_wheel_nm']-s['delivered_wheel_nm'])<.1 for s in powered),'low grip no longer deletes drive torque')
        check(any(s['wheelspin_shift_hold'] for s in powered),'rear wheelspin is detected')
        check(max(s['rpm'] for s in report['slip'])>7000,'low-grip idle launch builds engine revs without handbrake assistance')
        check(all(s['shift_cut_remaining']==0 for s in report['slip'] if s['t']>.5 and s['wheelspin_shift_hold']),'wheelspin does not trigger repeated shift cuts')
        check(all(abs(s['wheel_nm'][0])+abs(s['wheel_nm'][1])<.01 for s in report['slip']),'limited slip only acts on driven axle')
    # Check the transfer gearing on firm contact. RWD cannot be expected to match
    # the inherited AWD baseline's acceleration on the near-frictionless fixture.
    firm=u.new_object(u.PhysicalMaterial);firm.set_editor_property('friction',.8);floor.set_phys_material_override(firm)
    yield from fresh(fixture);car.get_drivetrain().set_low_range(True);report['low']=yield from drive(4,.35);save()
    check(max(s['speed_kmh'] for s in report['low'])>5,'low range remains driveable')
    if not BASELINE:check(all(s['solver']['countersteer_weight']==0 for s in report['low']),'low range bypasses extra countersteer travel')
    car.destroy_actor();car=None;flat.destroy_actor()
    yield from fresh();report['reverse']=yield from drive(2,0,brake=.5)
    check(report['reverse'][-1]['forward_kmh']<-1,'reverse works')
    yield from fresh();car.get_condition().fuel_litres=0;report['fuel']=yield from drive(2,1,handbrake=True)
    check(max(s['rpm'] for s in report['fuel'])<1000,'fuel cutoff prevents free revs')
    check(hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected},'protected maps and vehicle blueprint unchanged by tests')
    check(saved=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in saved},'player saves unchanged')
    if not BASELINE:
        car.set_chase_camera(True);yield from wait(1)
        image_path=OUT/'ferrari-driving.png';stamp=time.time()
        u.SystemLibrary.execute_console_command(world,'Shot SHOWUI -nosuffix filename="'+image_path.as_posix()+'"',pc)
        end=time.monotonic()+30
        while not image_path.exists() or image_path.stat().st_mtime<stamp:
            assert time.monotonic()<end,'Ferrari screenshot timeout';yield .1
        report['image']=str(image_path)
    report['ok']=True;save();world=pc=car=None;gc.collect();u.EditorLevelLibrary.editor_end_play();yield 3
    level.load_level('/Engine/Maps/Entry');yield 3
steps=run();deadline=0.;busy=False;began=time.monotonic()
def tick(dt):
    global deadline,busy,steps
    if busy or time.monotonic()<deadline:return
    busy=True;done=False
    try:
        assert time.monotonic()-began<900,'Ferrari check timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
save();u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
