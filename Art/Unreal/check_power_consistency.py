"""Transient flat/low-grip and repeated-crest probes in the existing rally world.
Reports measurements, not a subjective handling pass. No saved assets changed.
"""
import gc,hashlib,json,math,os,time,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Saved/FerrariDrivingQA'
LABEL=os.environ.get('GT_POWER_LABEL','baseline');PATH=OUT/('consistency-'+LABEL+'.json')
report=dict(ok=False,label=LABEL,runs=[]);world=pc=car=None
protected=[ROOT/p for p in ['Content/GrandTour/ArtTests/RallyHandling/L_RallyHandling.umap','Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap','Content/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288.uasset','Content/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288_WheelFront.uasset','Content/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288_WheelRear.uasset']]+list((ROOT/'Saved/SaveGames').glob('*.sav'))
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
def save():PATH.write_text(json.dumps(report,indent=2))
def now():return u.GameplayStatics.get_time_seconds(world)
def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)
def wait(t):
    end=now()+t
    while now()<end:yield 0
def cube(name,pos,scale,pitch=0):
    a=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(location=pos,rotation=u.Rotator(pitch=pitch),scale=scale),name)
    c=a.static_mesh_component;c.set_mobility(u.ComponentMobility.MOVABLE);c.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));c.set_collision_profile_name('BlockAll');return a
def snap():
    m=car.get_chaos_movement();v=car.get_velocity();r=car.get_actor_rotation();d=json.loads(car.get_drivetrain().setup_report())
    d.update(t=now(),x=car.get_actor_location().x,y=car.get_actor_location().y,z=car.get_actor_location().z,vz=v.z,kmh=v.length()*.036,pitch=r.pitch,roll=r.roll,
        omega=[w.omega_rad_s for w in car.get_drivetrain().wheels],solver=json.loads(m.rally_handling_report()),suspension=json.loads(m.suspension_report()))
    return d
def record(seconds,throttle,handbrake=False,target_kmh=None):
    m=car.get_chaos_movement();end=now()+seconds;result=[]
    while now()<end:
        pedal=throttle if target_kmh is None else max(0,min(.5,.1+(target_kmh-m.get_forward_speed()*.036)*.07))
        m.set_throttle_input(pedal);m.set_handbrake_input(handbrake);result.append(snap());yield 0
    m.set_throttle_input(0);return result
def fresh(cls):
    global car
    if car:car.destroy_actor();yield 0
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,u.Transform(location=u.Vector(-6000,-10000,20120)),'ConsistencyCar')
    pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
    yield from wait(3)
    assert car.get_velocity().length()<30,'fixture settle'
def run():
    global world,pc,car
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if LABEL!='before':
        u.SystemLibrary.execute_console_command(u.EditorLevelLibrary.get_editor_world(),'Automation RunTests GrandTour.RangeRover.Drivetrain')
        deadline=time.monotonic()+120
        while True:
            log=(ROOT/'Saved/Logs/Ferrari-Consistency.log').read_text(errors='replace')
            if 'Result={Success} Name={Drivetrain}' in log:break
            assert 'Result={Fail}' not in log,'Native wheel/drivetrain regression failed'
            assert time.monotonic()<deadline,'Native regression timeout';yield .5
        report['native_pass']=True;save()
    assert level.load_level('/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling');yield 3
    level.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
    end=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<end;yield .2
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car()
    cmd('t.IdleWhenNotForeground 0');cmd('Slate.bAllowThrottling 0')
    flat=cube('PowerFixture',u.Vector(4000,-10000,20000),u.Vector(400,16,.5))
    material=u.new_object(u.PhysicalMaterial);material.set_editor_property('friction',.08);flat.static_mesh_component.set_phys_material_override(material)
    ferrari=u.load_class(None,'/Game/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288.BP_Ferrari288_C')
    for name,cls in [('Ferrari',ferrari),('RangeRover',u.GTCarPawn)]:
        for fps in [30,120]:
            cmd('t.MaxFPS '+str(fps));yield from fresh(cls)
            row=dict(car=name,probe='low-grip',fps=fps,tc=[w.get_editor_property('traction_control_enabled') for w in car.get_chaos_movement().wheels])
            row['power']=yield from record(6,1);row['lift']=yield from record(3,0)
            report['runs'].append(row);save()
    material.set_editor_property('friction',.8);flat.static_mesh_component.set_phys_material_override(material)
    bumps=[]
    for i in range(6):
        x=-4000+i*800
        for dx,pitch in [(0,2),(200,-2)]:
            bumps.append(cube('RepeatCrest',u.Vector(x+dx,-10000,20024),u.Vector(2,16,.1),pitch))
    cmd('t.MaxFPS 120')
    variants=[('authored',None),('compliant',(260,280,.72,.76)),('compliant-damped',(260,280,.85,.88))] if LABEL.startswith('candidate') else [('authored',None)]
    for variant,values in variants:
      if values:
        for axle,rate,damping in [('Front',values[0],values[2]),('Rear',values[1],values[3])]:
            w=u.get_default_object(u.load_class(None,'/Game/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288_Wheel'+axle+'.BP_Ferrari288_Wheel'+axle+'_C'))
            w.set_editor_property('spring_rate',rate);w.set_editor_property('suspension_damping_ratio',damping)
      for ride in ([1,0] if LABEL=='before' else [1]):
       for entry in ([40,80] if LABEL=='final' else [80]):
        cmd('gt.Vehicle.RallyRide '+str(ride));yield from fresh(ferrari)
        mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector(entry/0.036,0,0),False)
        row=dict(car='Ferrari',probe='repeated-crests',ride=ride,variant=variant,entry_kmh=entry)
        row['trace']=yield from record(640/entry,0,target_kmh=40 if entry==40 else None)
        assert row['trace'][-1]['x']>600,'all six crests must be crossed'
        assert max(abs(s['roll']) for s in row['trace'])<15,'repeated crests stay upright'
        report['runs'].append(row);save()
    if LABEL=='final':
        for name in ['Ferrari','RangeRover']:
            rows=[r for r in report['runs'] if r['car']==name and r['probe']=='low-grip']
            peaks=[max(s['shaft_rpm'] for s in r['power']) for r in rows]
            assert max(peaks)/min(peaks)<1.08,'shaft-speed response differs too much between frame caps'
            assert all(max(s['rpm'] for s in r['power'])>(7000 if name=='Ferrari' else 4500) for r in rows),'idle launch fails to build revs'
        report['consistency_assertions_pass']=True
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected},'protected assets/saves changed'
    report['protected_unchanged']=True;report['ok']=True;save();car.destroy_actor();flat.destroy_actor()
    for b in bumps:b.destroy_actor()
    world=pc=car=None;gc.collect();u.EditorLevelLibrary.editor_end_play();yield 3
    level.load_level('/Engine/Maps/Entry');yield 3
steps=run();deadline=0.;busy=False;began=time.monotonic()
def tick(dt):
    global deadline,busy,steps
    if busy or time.monotonic()<deadline:return
    busy=True;done=False
    try:
        assert time.monotonic()-began<900,'consistency timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
save();u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
