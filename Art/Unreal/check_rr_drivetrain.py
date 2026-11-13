"""Rendered PIE drivetrain checks; transient hill fixture and isolated save slots only."""
import gc, hashlib, json, math, time, traceback
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Saved/WorkshopQA';OUT.mkdir(parents=True,exist_ok=True)
report=dict(ok=False,checks=[],images=[],acceleration=[],hill=[])
world=pc=car=work=None
IDS=['Part.Engine','Part.RREngineRally','Part.RREngineExpedition']
protected=[ROOT/'Content/GrandTour/ArtTests/RallyHandling/L_RallyHandling.umap',ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
slots=['GT_Workshop_RangeRover_QA','GT_Drivetrain_Loadout_QA']
saved={ROOT/'Saved/SaveGames'/(s+'.sav'):None for s in slots}
for p in saved:
    if p.exists():saved[p]=p.read_bytes()
user_saves={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Saved/SaveGames').glob('*.sav') if p not in saved}

def save():(OUT/'drivetraincheck.json').write_text(json.dumps(report,indent=2))
def check(value,label):
    assert value,label
    report['checks'].append(label);save()
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def now():return u.GameplayStatics.get_time_seconds(world)
def wait(seconds):
    end=now()+seconds
    while now()<end:yield .03
def loadout(c=None):return [(str(e.slot.get_editor_property('tag_name')),str(e.part_id)) for e in (c or car).get_parts().get_loadout()]
def inventory():return [(str(e.item_id),e.count) for e in car.get_boot().items]
def setup(c=None):return json.loads((c or car).get_drivetrain().setup_report())
def config(c):
    d=setup(c)
    return {k:d[k] for k in ['setup','name','final_ratio','low_ratio','up_rpm','down_rpm','shift_seconds','pedal_exponent','centre_lsd','front_lsd','rear_lsd','gears']}
def replace_engine(entries,choice):
    result=[]
    for e in entries:
        n=u.GTSlotEntry();n.set_editor_property('slot',e.slot);n.set_editor_property('part_id',IDS[choice] if str(e.slot.get_editor_property('tag_name'))=='Slot.Engine' else e.part_id);result.append(n)
    return result
def capture(name):
    yield 2
    path=OUT/(name+'.png');stamp=time.time();console('Shot SHOWUI -nosuffix filename="'+path.as_posix()+'"')
    end=time.monotonic()+40
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<end,'Screenshot timeout';yield .2
    report['images'].append(str(path));save()

def fresh(choice,base,transform=None):
    global car
    if car:
        car.reset_driving_inputs();car.destroy_actor();yield .1
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.GTCarPawn,transform or start_transform,'DrivetrainQA')
    check(car is not None,'fresh drivetrain vehicle '+str(choice))
    car.get_parts().apply_loadout(replace_engine(base,choice),False);pc.possess(car);car.disable_input(pc)
    if transform is None:pc.select_lane(1)
    move=car.get_chaos_movement();move.set_handbrake_input(True)
    yield from wait(3)
    # Spawning/streaming can leave the fixture settling at the first sample.
    # Keep the same velocity requirement, with a bounded settling grace period.
    settle_deadline=now()+3
    while car.get_velocity().length()>=30 and now()<settle_deadline:yield .03
    report.setdefault('settling',[]).append(dict(choice=choice,speed_cm_s=car.get_velocity().length(),location=str(car.get_actor_location())))
    check(car.get_velocity().length()<30,'fixture settles '+str(choice))
    car.get_drivetrain().set_low_range(False);car.get_drivetrain().set_diff_lock(False)

def drive(seconds,throttle,steer=0,brake=0,handbrake=False):
    move=car.get_chaos_movement();move.set_handbrake_input(handbrake)
    start=now();samples=[]
    while now()-start<seconds:
        move.set_throttle_input(throttle);car.set_raw_steer(steer);move.set_brake_input(brake)
        d=setup();d.update(t=now()-start,speed_kmh=car.get_velocity().length()*.036,roll=car.get_actor_rotation().roll,steer=car.get_raw_steer(),grip_cap_nm=sum(w.cap_nm for w in car.get_drivetrain().wheels))
        samples.append(d);yield .03
    car.reset_driving_inputs()
    return samples

def run():
    global world,pc,car,work,start_transform
    u.GameplayStatics.delete_game_in_slot(slots[0],0)
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    console_world=u.EditorLevelLibrary.get_editor_world()
    u.SystemLibrary.execute_console_command(console_world,'Automation RunTests GrandTour.RangeRover.Drivetrain')
    deadline=time.monotonic()+120
    while True:
        log=(ROOT/'Saved/Logs/Workshop-DrivetrainCheck.log').read_text(errors='replace')
        if 'Result={Success} Name={Drivetrain}' in log:break
        assert 'Result={Fail}' not in log,'Native drivetrain regression failed'
        assert time.monotonic()<deadline,'Native drivetrain regression timeout'
        yield .5
    check(True,'native differential and pedal regression passes')
    check(level.load_level('/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling'),'rally level loads')
    yield 3;level.editor_set_viewport_realtime(False)
    check(u.GTPlayWindowLibrary.request_play_in_new_window(1600,900),'rendered play window starts')
    deadline=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<deadline;yield .2
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();work=pc.get_workshop()
    console('t.IdleWhenNotForeground 0');console('Slate.bAllowThrottling 0')
    pc.select_lane(1);car.get_chaos_movement().set_handbrake_input(True);yield from wait(4)
    start_transform=car.get_actor_transform();start_transform.translation+=u.Vector(0,0,60)
    base=car.get_parts().get_loadout();base_ids=loadout();boot=inventory();standard=config(car)
    other_transform=car.get_actor_transform();other_transform.translation+=u.Vector(0,800,100)
    independent=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.GTCarPawn,other_transform,'IndependentDrivetrain')
    independent.get_chaos_movement().set_handbrake_input(True);yield from wait(2)
    other_cfg=config(independent)
    check(setup()['setup']==0,'old/default loadout keeps authored Standard drivetrain')
    check(work.open(),'drivetrain workshop opens parked');work.select_part(5);work.preview(1)
    check(loadout()==base_ids and setup()['setup']==0 and inventory()==boot,'Rally preview changes no mechanical state')
    work.compare(True);work.compare(False);work.cancel()
    check(loadout()==base_ids and setup()['setup']==0,'compare and cancel preserve Standard')
    work.select_part(5);work.preview(2);work.close();yield from wait(.2)
    check(setup()['setup']==0,'close discards Expedition preview')
    condition=car.get_condition();condition.set_part_health(u.GTCarPart.ENGINE,.7)
    check(work.open(),'open Rally fitting');work.select_part(5);work.preview(1)
    yield from capture('11-rally-drivetrain')
    check(work.fit(),'Rally fits through workshop');work.close();yield from wait(.3)
    check(setup()['setup']==1,'actual drivetrain resolves Rally loadout')
    check(abs(condition.get_part_health(u.GTCarPart.ENGINE)-.7)<.001,'lab fitting does not repair engine')
    check(inventory()==boot,'lab fitting does not grant inventory')
    check([e for e in loadout() if 'Slot.Engine' not in e[0]]==[e for e in base_ids if 'Slot.Engine' not in e[0]],'drivetrain fit preserves tyres suspension and other parts')
    check(config(independent)==other_cfg,'independent Range Rover retains Standard configuration')
    # Native tests cover the protected save object's disk serialization. Here exercise
    # the same GetLoadout/ApplyLoadout path used by the production carry snapshot.
    independent.get_parts().apply_loadout(car.get_parts().get_loadout(),False);yield from wait(.3)
    check(setup(independent)['setup']==1,'fresh vehicle restores captured Rally loadout')
    independent.get_parts().apply_loadout(base,False);yield from wait(.2)
    check(config(independent)==other_cfg,'restoring old loadout removes every Rally override')
    independent.destroy_actor()
    # Reproduce the driver's exact complaint with each Range Rover package.
    # RPM must respond to the pedal while the braked wheels stay still; release
    # must transmit real drive progressively, without snapping engine RPM to idle.
    report['handbrake']=[]
    for choice in range(3):
        yield from fresh(choice,base)
        rev=yield from drive(3,1,handbrake=True)
        lift=yield from drive(2,0,handbrake=True)
        second_rev=yield from drive(2,1,handbrake=True)
        launch=yield from drive(3,1)
        report['handbrake'].append(dict(choice=choice,rev=rev,lift=lift,second_rev=second_rev,launch=launch));save()
        check(max(s['rpm'] for s in rev)>4500,'handbrake allows free revs '+str(choice))
        check(max(s['speed_kmh'] for s in rev)<1 and max(s['shaft_rpm'] for s in rev)<200,'revving on handbrake holds wheels stationary '+str(choice))
        check(all(s['clutch_engagement']==0 and abs(s['requested_wheel_nm'])<.01 for s in rev if s['t']>.2),'handbrake opens actual drivetrain clutch '+str(choice))
        check(all(s['gear']==1 and s['shift_cut_remaining']==0 for s in rev),'free revving does not shift gears '+str(choice))
        check(lift[-1]['rpm']<rev[-1]['rpm']-900,'throttle lift lowers free engine revs '+str(choice))
        check(any(s['t']<.4 and 0<s['clutch_engagement']<1 and s['requested_wheel_nm']>0 for s in launch),'release progressively engages drive '+str(choice))
        check(all(abs(b['rpm']-a['rpm'])<800 for a,b in zip(launch,launch[1:]) if b['t']-a['t']<.06),'release preserves engine inertia '+str(choice))
        check(max(s['speed_kmh'] for s in launch)>15,'handbrake release launches vehicle '+str(choice))
        check(max(s['rpm'] for s in rev+second_rev+launch)<=5101,'free and coupled RPM stay bounded '+str(choice))
    yield from fresh(1,base)
    yield from drive(4,.8)
    rolling=yield from drive(2,1,steer=.3,handbrake=True)
    recovery=yield from drive(3,.8)
    report['rolling_handbrake']=dict(held=rolling,released=recovery);save()
    check(any(s['t']>.5 and s['rpm']>4500 and s['clutch_engagement']==0 for s in rolling),'rolling handbrake still allows engine revs')
    check(any(s['t']>1 and s['clutch_engagement']>.9 and s['requested_wheel_nm']>0 and s['speed_kmh']>10 for s in recovery),'rolling handbrake reconnects powered drive')
    stopped=yield from drive(4,1,brake=1,handbrake=True)
    report['rolling_handbrake']['stopped']=stopped;save()
    check(stopped[-1]['speed_kmh']<1 and stopped[-1]['gear']==1 and stopped[-1]['rpm']>4500,'stopping on handbrake prepares first gear while engine keeps revving')
    # Same start, surface, tyres, health and simulation duration for all three packages.
    for choice in range(3):
        yield from fresh(choice,base)
        check(setup()['setup']==choice,'live setup '+str(choice)+' '+str(loadout()))
        samples=yield from drive(8,1)
        row=dict(choice=choice,samples=samples,max_kmh=max(s['speed_kmh'] for s in samples),max_gear=max(s['gear'] for s in samples),peak_rpm=max(s['rpm'] for s in samples))
        report['acceleration'].append(row);save()
        check(row['max_kmh']>25,'accelerates on gravel '+str(choice))
        check(row['max_gear']>=2,'automatic gearbox shifts '+str(choice))
        check(row['peak_rpm']<=5251,'RPM remains inside existing limiter/audio range '+str(choice))
        before=car.get_drivetrain().is_low_range();car.get_drivetrain().set_low_range(not before)
        check(car.get_drivetrain().is_low_range()==before,'moving transfer shift rejected '+str(choice))
        check(all(math.isfinite(w.drive_torque_nm) for w in car.get_drivetrain().wheels),'finite per-wheel torques '+str(choice))
    report['cornering']=[]
    for choice in [1,2]:
        yield from fresh(choice,base)
        yaw=car.get_actor_rotation().yaw
        samples=yield from drive(4,.55,steer=.35)
        rotation=car.get_actor_rotation();yaw_change=(rotation.yaw-yaw+180)%360-180
        peak_roll=max(abs(s['roll']) for s in samples)
        report['cornering'].append(dict(choice=choice,yaw_change=yaw_change,peak_roll=peak_roll,max_kmh=max(s['speed_kmh'] for s in samples)));save()
        check(abs(yaw_change)>8 and peak_roll<35,'package steers and stays upright from gravel start '+str(choice))
    # A transient 15-degree ramp above the map: an identical standing hill start,
    # no saved terrain changes and no prior wheel ruts to bias the second run.
    ramp_transform=u.Transform(location=u.Vector(0,0,10000),rotation=u.Rotator(pitch=15),scale=u.Vector(200,12,.5))
    ramp=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,ramp_transform,'DrivetrainHillFixture')
    component=ramp.static_mesh_component;component.set_mobility(u.ComponentMobility.MOVABLE);component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube.Cube'))
    component.set_collision_profile_name('BlockAll')
    component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
    angle=math.radians(15);direction=u.Vector(math.cos(angle),0,math.sin(angle));normal=u.Vector(-math.sin(angle),0,math.cos(angle))
    hill_start=u.Transform(location=u.Vector(0,0,10000)-direction*7000+normal*120,rotation=u.Rotator(pitch=15))
    for low in [False,True]:
        yield from fresh(2,base,hill_start)
        train=car.get_drivetrain();train.set_low_range(low);train.set_diff_lock(True)
        check(train.is_low_range()==low,'transfer shift accepted at rest '+str(low))
        origin=car.get_actor_location();samples=yield from drive(5,.4)
        delta=car.get_actor_location()-origin
        climb=(delta.x*direction.x+delta.y*direction.y+delta.z*direction.z)*.01
        report['hill'].append(dict(low=low,uphill_metres=climb,samples=samples));save()
        check(setup()['setup']==2 and train.is_diff_locked(),'Expedition locks remain selected on hill '+str(low))
    check(report['hill'][1]['uphill_metres']>report['hill'][0]['uphill_metres']+1,'low range improves identical Expedition hill start')
    check(report['hill'][1]['uphill_metres']>1,'Expedition low range climbs from rest at partial throttle')
    check(all(s['rpm']>=min(5000,s['shaft_rpm'])-100 for s in report['hill'][1]['samples'] if s['t']>.6 and s['clutch_engagement']>.99),'engaged low range cannot leave engine RPM lagging behind shaft speed')
    car.destroy_actor();car=None;ramp.destroy_actor()
    # Low-friction contact uses a transient material/fixture, never a saved surface asset.
    slippery=u.new_object(u.PhysicalMaterial);slippery.set_editor_property('friction',.08)
    flat=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(location=u.Vector(0,-10000,20000),scale=u.Vector(200,12,.5)),'SlipResponseFixture')
    floor=flat.static_mesh_component;floor.set_mobility(u.ComponentMobility.MOVABLE);floor.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube.Cube'))
    floor.set_collision_profile_name('BlockAll');floor.set_phys_material_override(slippery)
    slip_start=u.Transform(location=u.Vector(-6000,-10000,20120))
    report['traction_loss']=[]
    for choice in range(3):
        yield from fresh(choice,base,slip_start)
        samples=yield from drive(7,1)
        powered=[s for s in samples if s['t']>.5 and s['contacts']>=3 and s['requested_wheel_nm']>100]
        report['traction_loss'].append(dict(choice=choice,samples=samples));save()
        check(len(powered)>10,'low-grip contact produces powered samples '+str(choice))
        check(any(s['requested_wheel_nm']>s['grip_cap_nm']*1.2 for s in powered),'fixture exceeds available tyre grip '+str(choice))
        check(all(abs(s['delivered_wheel_nm']-s['requested_wheel_nm'])<.1 for s in powered),'low grip no longer discards wheel torque '+str(choice))
        check(any(s['wheelspin_shift_hold'] for s in powered),'wheelspin shift protection activates '+str(choice))
        check(all(s['shift_cut_remaining']==0 for s in samples if s['wheelspin_shift_hold'] and s['t']>.5),'wheelspin does not cause shift cuts '+str(choice))
    yield from fresh(1,base,slip_start)
    mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_enable_gravity(False)
    car.set_actor_location(slip_start.translation+u.Vector(0,0,1500),False,True)
    samples=yield from drive(3,1);report['airborne_slip']=samples;save()
    check(all(s['contacts']==0 and s['gear']==1 and s['shift_cut_remaining']==0 for s in samples if s['t']>.5),'airborne spinning wheels retain gear without shift torque cuts')
    check(any(s['shaft_rpm']>2000 and s['requested_wheel_nm']>s['grip_cap_nm']*5 for s in samples),'unloaded wheels spin above idle without the old grip-based torque cut')
    # Chaos has an existing unloaded-wheel spin ceiling; do not alter it merely
    # to reach the engine limiter in this fixture. Check actual recontact instead.
    mesh.set_enable_gravity(True);car.set_actor_location(slip_start.translation,False,True)
    samples=yield from drive(3,.75);report['traction_recovery']=samples;save()
    check(any(s['t']>.7 and s['contacts']>=3 and s['engine_nm']>50 and s['shift_cut_remaining']==0 for s in samples),'same vehicle resumes powered ground contact after airtime')
    check(all(abs(s['delivered_wheel_nm']-s['requested_wheel_nm'])<.1 for s in samples if s['t']>.7),'landing does not retain a hidden torque reduction')
    car.destroy_actor();car=None;flat.destroy_actor()
    # Reverse, fuel cutoff, restored Standard and saved Expedition.
    yield from fresh(2,base)
    check(work.open(),'open Expedition review');work.select_part(5);yield from capture('12-expedition-drivetrain');work.close()
    samples=yield from drive(2,0,brake=.5)
    check(any(s['gear']==-1 and s['engine_nm']>0 for s in samples) and car.get_chaos_movement().get_forward_speed()<-30,'Expedition reverse drives backward')
    yield from fresh(1,base)
    car.get_condition().fuel_litres=0;yield from wait(.3)
    samples=yield from drive(1,.7)
    check(all(abs(s['engine_nm'])<.01 for s in samples[2:]),'Rally does not bypass fuel cutoff')
    samples=yield from drive(2,1,handbrake=True)
    check(max(s['rpm'] for s in samples)<1000,'empty fuel tank cannot free rev on handbrake')
    yield from fresh(2,base)
    car.get_component_by_class(u.SkeletalMeshComponent).set_physics_linear_velocity(car.get_actor_forward_vector()*1000)
    samples=yield from drive(.9,.1)
    check(any(s['rpm']>1200 and s['engine_nm']>0 for s in samples if s['t']>.2),'light Expedition throttle supplies torque at rolling RPM')
    check(all(s['engine_nm']>=0 for s in samples if s['t']>.2),'progressive throttle does not accidentally engage engine braking')
    yield from fresh(2,base)
    expedition_loadout=car.get_parts().get_loadout();car.get_parts().apply_loadout(base,False);yield from wait(.2)
    check(config(car)==standard,'return to Standard restores authored ratios and diff behavior')
    car.get_parts().apply_loadout(expedition_loadout,False);yield from wait(.2)
    check(setup()['setup']==2,'captured Expedition loadout restores package')
    # A different fleet car rejects the package, including against a forced imported loadout.
    car.destroy_actor();cls=u.load_class(None,'/Game/GrandTour/Vehicles/Bodies/E39Touring/BP_E39Touring.BP_E39Touring_C')
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,start_transform,'UnchangedBMW');pc.possess(car);yield from wait(2)
    baseline=config(car)
    for part in IDS[1:]:check(not car.get_parts().can_install(part).fits,'BMW rejects '+part)
    car.get_parts().apply_loadout(replace_engine(car.get_parts().get_loadout(),1),False);yield from wait(.2)
    check(config(car)==baseline and setup()['setup']==-1,'non-Range Rover ignores imported Rally configuration')
    check(work.open(),'other fleet car can open drive-layout workshop')
    work.select_part(5)
    check('selected=-1 ' in work.describe(),'BMW cannot select Range Rover engine packages')
    work.select_part(6)
    check('selected=6 ' in work.describe(),'BMW can select drive layout')
    work.close()
    samples=yield from drive(1,1,handbrake=True)
    check(all(abs(s['rpm']-max(800,s['shaft_rpm']))<1 for s in samples if s['t']>.3),'BMW retains original wheel-coupled engine RPM')
    check(hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected},'saved rally and LiDAR maps unchanged')
    check(user_saves=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in user_saves},'player save files unchanged')
    report['ok']=True;save()
    world=pc=car=work=None;gc.collect();u.EditorLevelLibrary.editor_end_play();yield 3
    level.load_level('/Engine/Maps/Entry');yield 2

steps=run();deadline=0.;busy=False;began=time.monotonic()
def tick(dt):
    global deadline,busy,steps
    if busy or time.monotonic()<deadline:return
    busy=True;done=False
    try:
        assert time.monotonic()-began<900,'Drivetrain check timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle)
        for p,data in saved.items():
            if data is not None:p.write_bytes(data)
            elif p.exists():p.unlink()
        steps=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
save();u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
