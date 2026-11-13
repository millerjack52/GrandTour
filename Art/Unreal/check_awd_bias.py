"""Rendered AWD bias checks in the existing rally map; no player save or authored asset writes."""
import gc,hashlib,json,math,time,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Saved/WorkshopQA';OUT.mkdir(parents=True,exist_ok=True)
report=dict(ok=False,checks=[],runs=[],images=[]);world=pc=car=work=None
frame_dt=0.;recent_frames=[]
protected=list((ROOT/'Saved/SaveGames').glob('*.sav'))+[ROOT/'Content/GrandTour/ArtTests/RallyHandling/L_RallyHandling.umap',ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
def save():
    tmp=OUT/'biascheck.tmp';tmp.write_text(json.dumps(report,indent=2));tmp.replace(OUT/'biascheck.json')
def check(ok,label):
    assert ok,label
    report['checks'].append(label);save()
def now():return u.GameplayStatics.get_time_seconds(world)
def wait(seconds):
    end=now()+seconds
    while now()<end:yield .03
def setup():return json.loads(car.get_drivetrain().setup_report())
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def loadout():return [(str(e.slot.get_editor_property('tag_name')),str(e.part_id)) for e in car.get_parts().get_loadout()]
def boot():return [(str(e.item_id),e.count) for e in car.get_boot().items]
def fresh(cls):
    global car
    if work and work.is_open():work.close()
    if car:car.reset_driving_inputs();car.destroy_actor();yield .1
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,start,'AWDBiasQA')
    pc.possess(car);car.disable_input(pc);pc.select_lane(1)
    car.get_chaos_movement().set_handbrake_input(True);yield from wait(3)
    end=now()+3
    while car.get_velocity().length()>=30 and now()<end:yield .03
    check(car.get_velocity().length()<30,'fixture settles')
    car.get_drivetrain().set_low_range(False);car.get_drivetrain().set_diff_lock(False)
def select_awd(percent):
    check(work.open(),'workshop opens parked');work.select_part(6);work.preview(3)
    work.adjust_awd_split(round((percent-setup()['awd_front_share']*100)/5))
def fit(percent):
    select_awd(percent);check(work.fit(),'apply AWD '+str(percent));work.close()
def drive(seconds,throttle=.8,brake=0,steer=.15,handbrake=False):
    move=car.get_chaos_movement();began=now();rows=[]
    while now()-began<seconds:
        move.set_throttle_input(throttle);move.set_brake_input(brake);move.set_handbrake_input(handbrake);car.set_raw_steer(steer)
        d=setup();d.update(t=now()-began,frame_dt=frame_dt,speed_kmh=car.get_velocity().length()*.036,forward_kmh=move.get_forward_speed()*.036,
            wheel_nm=[w.drive_torque_nm for w in car.get_drivetrain().wheels],omega=[w.omega_rad_s for w in car.get_drivetrain().wheels])
        rows.append(d);yield .03
    car.reset_driving_inputs();return rows
def verify(rows,share,label,coupling=False):
    active=[s for s in rows if s['t']>.4 and abs(s['requested_wheel_nm'])>10]
    check(len(active)>5,label+' sustained drive')
    check(all(abs(sum(s['wheel_nm'])-s['requested_wheel_nm'])<.2 for s in active),label+' conserves total torque')
    allowance=400.2 if coupling else .2
    check(all(abs(sum(s['wheel_nm'][:2])-s['requested_wheel_nm']*share)<allowance for s in active),label+' front axle follows split'+(' with bounded diff coupling' if coupling else ''))
    check(all(abs(sum(s['wheel_nm'][2:])-s['requested_wheel_nm']*(1-share))<allowance for s in active),label+' rear axle follows split'+(' with bounded diff coupling' if coupling else ''))
    check(all(abs(s['shaft_rpm']-abs((sum(s['omega'][:2])*share+sum(s['omega'][2:])*(1-share))*.5)*s['total_ratio']*60/(2*math.pi))<.2 for s in active),label+' weighted driven shaft RPM')
def capture(name):
    yield 2
    path=OUT/(name+'.png');stamp=time.time();console('Shot SHOWUI -nosuffix filename="'+path.as_posix()+'"')
    end=time.monotonic()+30
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<end;yield .2
    report['images'].append(str(path));save()
def run():
    global world,pc,car,work,start
    editor=u.EditorLevelLibrary.get_editor_world()
    # Process-only setting. Hidden-window tests must not inherit interactive background throttling.
    settings_class=u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings')
    u.get_default_object(settings_class).set_editor_property('bThrottleCPUWhenNotForeground',False)
    for suite,name in [('GrandTour.Vehicle.DriveLayout','DriveLayout'),('GrandTour.RangeRover.Drivetrain','Drivetrain')]:
        u.SystemLibrary.execute_console_command(editor,'Automation RunTests '+suite);end=time.monotonic()+180
        while True:
            log=(ROOT/'Saved/Logs/Workshop-BiasCheck.log').read_text(errors='replace')
            if 'Result={Success} Name={'+name+'}' in log:break
            assert 'Result={Fail}' not in log and time.monotonic()<end,'native tests failed/timed out';yield .5
        check(True,'native '+suite+' passed')
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(level.load_level('/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling'),'existing rally map loads');yield 3
    level.editor_set_viewport_realtime(False);check(u.GTPlayWindowLibrary.request_play_in_new_window(1600,900),'rendered PIE starts')
    end=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<end;yield .2
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();work=pc.get_workshop()
    console('t.IdleWhenNotForeground 0');console('Slate.bAllowThrottling 0')
    ready_deadline=time.monotonic()+60
    while len(recent_frames)<20 or sum(recent_frames[-20:])/20>.066:
        report['warmup_frame_dt']=recent_frames[-20:];save()
        assert time.monotonic()<ready_deadline,'rendered editor cannot sustain 15 Hz; acceleration measurement invalid'
        yield .2
    pc.select_lane(1);yield from wait(3);start=car.get_actor_transform();start.translation+=u.Vector(0,0,60)
    classes=[('Range Rover',u.GTCarPawn),('Ferrari',u.load_class(None,'/Game/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288.BP_Ferrari288_C'))]
    for name,cls in classes:
        yield from fresh(cls);factory=setup()['front_share']
        check(abs(setup()['awd_front_share']-.5)<.001,name+' defaults to balanced AWD preference')
        original=loadout();select_awd(30)
        check(setup()['drive_layout']==0 and abs(setup()['awd_front_share']-.5)<.001 and loadout()==original,name+' preview changes no layout or split')
        work.compare(True);work.compare(False);work.cancel();work.close()
        check(abs(setup()['awd_front_share']-.5)<.001,name+' cancel discards split preview')
        select_awd(30);work.close()
        check(abs(setup()['awd_front_share']-.5)<.001,name+' close discards split preview')
        for percent in [50,10,30,70,90]:
            yield from fresh(cls);fit(percent)
            check(abs(setup()['front_share']-percent*.01)<.001,name+' selected split applied '+str(percent))
            if percent==30:
                check(work.open(),'open split screenshot');work.select_part(6);yield from capture('awd-30-70-'+name.lower().replace(' ','-'));work.close()
            rows=yield from drive(3)
            report['runs'].append(dict(car=name,front_percent=percent,samples=rows));save()
            verify(rows,percent*.01,name+' '+str(percent));check(max(s['speed_kmh'] for s in rows)>6,name+' drives with '+str(percent))
            before=setup()['awd_front_share']
            check(not car.get_drivetrain().set_awd_front_share(.5) and abs(setup()['awd_front_share']-before)<.001,name+' rejects moving split adjustment')
        yield from fresh(cls);fit(30)
        old_parts=loadout();old_boot=boot();car.get_condition().set_part_health(u.GTCarPart.ENGINE,.63)
        select_awd(20);work.compare(True);work.compare(False)
        check(abs(setup()['front_share']-.3)<.001,name+' split-only preview leaves fitted value intact')
        check(work.fit(),'retune installed AWD');work.close()
        check(abs(setup()['front_share']-.2)<.001 and loadout()==old_parts and boot()==old_boot,name+' retune uses same kit and inventory')
        check(abs(car.get_condition().get_part_health(u.GTCarPart.ENGINE)-.63)<.001,name+' retune does not repair damage')
        select_awd(20);check(not work.fit(),'unchanged split cannot refit');work.close()
        select_awd(10);work.adjust_awd_split(-16);check(work.fit(),'lower UI clamp fits');work.close();check(abs(setup()['front_share']-.1)<.001,'UI lower clamp')
        select_awd(90);work.adjust_awd_split(16);check(work.fit(),'upper UI clamp fits');work.close();check(abs(setup()['front_share']-.9)<.001,'UI upper clamp')
        for layout,expected in [(1,1),(2,0),(0,factory),(3,.9)]:
            check(work.open(),'open layout switch');work.select_part(6);work.preview(layout);check(work.fit(),'switch layout');work.close()
            check(abs(setup()['front_share']-expected)<.001,name+' AWD preference does not override layout '+str(layout))
        yield from fresh(cls);fit(30);reverse=yield from drive(2,0,brake=.7);verify(reverse,.3,name+' reverse');check(reverse[-1]['forward_kmh']<-1,name+' reverse moves backwards')
        yield from fresh(cls);fit(30);car.get_drivetrain().set_low_range(True);low=yield from drive(2,.5);verify(low,.3,name+' low range')
        yield from fresh(cls);fit(30);car.get_drivetrain().set_diff_lock(True);locked=yield from drive(3,.7,steer=.6);verify(locked,.3,name+' locked turn',True)
        yield from fresh(cls);fit(30);rev=yield from drive(2,1,handbrake=True)
        check(max(s['rpm'] for s in rev)>4000 and max(s['speed_kmh'] for s in rev)<1,name+' handbrake still allows free revs')
        if name=='Range Rover':
            for package in [1,2]:
                check(work.open(),'open engine package');work.select_part(5);work.preview(package);check(work.fit(),'fit engine package');work.close()
                check(setup()['setup']==package and abs(setup()['front_share']-.3)<.001,'engine package preserves split '+str(package))
    check(hashes=={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in protected},'player saves and authored maps untouched')
    report['ok']=True;save();world=pc=car=work=None;gc.collect();u.EditorLevelLibrary.editor_end_play();yield 3
    level.load_level('/Engine/Maps/Entry');yield 3
steps=run();deadline=0.;busy=False;began=time.monotonic()
def tick(dt):
    global deadline,busy,steps,frame_dt
    frame_dt=float(dt);recent_frames.append(frame_dt)
    if len(recent_frames)>120:del recent_frames[:-120]
    if busy or time.monotonic()<deadline:return
    busy=True;done=False
    try:
        assert time.monotonic()-began<1200,'Bias check timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
save();u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
