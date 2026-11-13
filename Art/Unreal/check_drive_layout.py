"""Drive layout conversions in rendered PIE; existing rally map, no authored asset writes."""
import gc,hashlib,json,math,time,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Saved/WorkshopQA';OUT.mkdir(parents=True,exist_ok=True)
report=dict(ok=False,checks=[],runs=[],images=[]);world=pc=car=work=None
protected=list((ROOT/'Saved/SaveGames').glob('*.sav'))+[ROOT/'Content/GrandTour/ArtTests/RallyHandling/L_RallyHandling.umap',ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap']
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
def save():(OUT/'layoutcheck.json').write_text(json.dumps(report,indent=2))
def check(ok,label):
    assert ok,label
    report['checks'].append(label);save()
def now():return u.GameplayStatics.get_time_seconds(world)
def wait(seconds):
    end=now()+seconds
    while now()<end:yield .03
def setup(c=None):return json.loads((c or car).get_drivetrain().setup_report())
def ids(c=None):return [(str(e.slot.get_editor_property('tag_name')),str(e.part_id)) for e in (c or car).get_parts().get_loadout()]
def config(c=None):return {k:v for k,v in setup(c).items() if k in ['gears','final_ratio','low_ratio','setup','up_rpm','down_rpm']}
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def capture(name):
    yield 2
    path=OUT/(name+'.png');stamp=time.time();console('Shot SHOWUI -nosuffix filename="'+path.as_posix()+'"')
    end=time.monotonic()+30
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<end;yield .2
    report['images'].append(str(path));save()
def fresh(cls,entries=None):
    global car
    if work and work.is_open():work.close()
    if car:car.reset_driving_inputs();car.destroy_actor();yield .1
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,start,'LayoutQA')
    pc.possess(car);car.disable_input(pc);pc.select_lane(1)
    if entries is not None:car.get_parts().apply_loadout(entries,False)
    car.get_chaos_movement().set_handbrake_input(True);yield from wait(3)
    car.get_drivetrain().set_low_range(False);car.get_drivetrain().set_diff_lock(False)
    check(car.get_velocity().length()<30,'car settles before conversion')
def fit(layout):
    check(work.open(),'parked workshop opens');work.select_part(6);work.preview(layout)
    check(work.fit(),'layout fits '+str(layout));work.close()
def drive(seconds,throttle,steer=0,brake=0,handbrake=False):
    move=car.get_chaos_movement();began=now();rows=[]
    while now()-began<seconds:
        move.set_throttle_input(throttle);move.set_brake_input(brake);move.set_handbrake_input(handbrake);car.set_raw_steer(steer)
        d=setup();d.update(t=now()-began,speed_kmh=car.get_velocity().length()*.036,forward_kmh=move.get_forward_speed()*.036,
            wheel_nm=[w.drive_torque_nm for w in car.get_drivetrain().wheels],omega=[w.omega_rad_s for w in car.get_drivetrain().wheels])
        rows.append(d);yield .03
    car.reset_driving_inputs();return rows
def check_torque(rows,layout,label):
    active=[s for s in rows if s['t']>.4 and abs(s['requested_wheel_nm'])>10]
    check(len(active)>5,label+' has sustained drive')
    check(all(abs(s['requested_wheel_nm']-sum(s['wheel_nm']))<.2 for s in active),label+' conserves delivered torque')
    if layout in (1,2):
        unpowered=slice(2,4) if layout==1 else slice(0,2)
        check(all(sum(abs(t) for t in s['wheel_nm'][unpowered])<.01 for s in active),label+' unpowered axle receives zero torque')
    else:check(any(abs(sum(s['wheel_nm'][:2]))>10 and abs(sum(s['wheel_nm'][2:]))>10 for s in active),label+' both axles receive torque')
    share={1:1,2:0,3:.5}[layout]
    check(all(abs(s['shaft_rpm']-abs((sum(s['omega'][:2])*share+sum(s['omega'][2:])*(1-share))*.5)*s['total_ratio']*60/(2*math.pi))<.2 for s in active),label+' shaft RPM uses driven wheels')
def run():
    global world,pc,car,work,start
    editor=u.EditorLevelLibrary.get_editor_world()
    u.SystemLibrary.execute_console_command(editor,'Automation RunTests GrandTour.Vehicle.DriveLayout')
    end=time.monotonic()+120
    while True:
        log=(ROOT/'Saved/Logs/Workshop-LayoutCheck.log').read_text(errors='replace')
        if 'Result={Success} Name={DriveLayout}' in log:break
        assert 'Result={Fail}' not in log and time.monotonic()<end,'native save tests failed/timed out';yield .5
    check(True,'production disk serialization retains all four layout choices and engine package')
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    check(level.load_level('/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling'),'existing rally map loads');yield 3
    level.editor_set_viewport_realtime(False);check(u.GTPlayWindowLibrary.request_play_in_new_window(1600,900),'rendered PIE starts')
    end=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<end;yield .2
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();work=pc.get_workshop()
    console('t.IdleWhenNotForeground 0');console('Slate.bAllowThrottling 0')
    pc.select_lane(1);yield from wait(3);start=car.get_actor_transform();start.translation+=u.Vector(0,0,60)
    classes=[('Range Rover',u.GTCarPawn),('Ferrari',u.load_class(None,'/Game/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288.BP_Ferrari288_C')),('BMW',u.load_class(None,'/Game/GrandTour/Vehicles/Bodies/E39Touring/BP_E39Touring.BP_E39Touring_C'))]
    for name,cls in classes:
        yield from fresh(cls);base=car.get_parts().get_loadout();stock=setup();original=config();base_ids=ids()
        check(stock['drive_layout']==0,name+' missing conversion retains Factory')
        check(work.open(),name+' workshop opens without Range Rover cosmetic assets');work.select_part(6);work.preview(1)
        check(setup()['drive_layout']==0 and ids()==base_ids,name+' preview changes no mechanics')
        work.compare(True);work.compare(False);work.cancel();work.select_part(6);work.preview(3);work.close()
        check(setup()['drive_layout']==0,name+' compare/cancel/close preserve layout')
        for layout in (1,2,3):
            yield from fresh(cls,base)
            boot=[(str(e.item_id),e.count) for e in car.get_boot().items]
            car.get_condition().set_part_health(u.GTCarPart.ENGINE,.7)
            fit(layout);yield from wait(.2)
            check(setup()['drive_layout']==layout and setup()['front_share']=={1:1,2:0,3:.5}[layout],name+' applied layout '+str(layout))
            check(config()==original,name+' conversion preserves engine and ratios')
            check(abs(car.get_condition().get_part_health(u.GTCarPart.ENGINE)-.7)<.001,name+' conversion preserves health')
            check(boot==[(str(e.item_id),e.count) for e in car.get_boot().items],name+' lab fitting preserves inventory')
            converted=car.get_parts().get_loadout()
            if layout==3 and name!='BMW':
                check(work.open(),'open screenshot');work.select_part(6);yield from capture('drive-layout-'+name.lower().replace(' ','-'));work.close()
            # Restore the captured production loadout onto a new car and test actual torque after recreation.
            yield from fresh(cls,converted)
            check(setup()['drive_layout']==layout,name+' conversion survives pawn recreation')
            forward=yield from drive(4,.8,steer=.12)
            check_torque(forward,layout,name+' forward '+str(layout));check(max(s['speed_kmh'] for s in forward)>8,name+' accelerates '+str(layout))
            check(not work.open(),name+' moving workshop rejected')
            check(not car.get_parts().can_install('Part.DriveAWD' if layout!=3 else 'Part.DriveRWD').fits,name+' moving parts swap rejected')
            yield from fresh(cls,converted);car.get_drivetrain().set_diff_lock(True)
            locked=yield from drive(2,.65,steer=.5);check_torque(locked,layout,name+' locked turn '+str(layout))
            yield from fresh(cls,converted)
            reverse=yield from drive(2,0,brake=.65);check_torque(reverse,layout,name+' reverse '+str(layout))
            check(reverse[-1]['forward_kmh']<-1,name+' drives backwards '+str(layout))
            if name!='BMW':
                yield from fresh(cls,converted)
                rev=yield from drive(2,1,handbrake=True)
                check(max(s['rpm'] for s in rev)>4000 and max(s['speed_kmh'] for s in rev)<1,name+' handbrake revs without driving '+str(layout))
                car.get_drivetrain().set_low_range(True)
                low=yield from drive(2,.5);check_torque(low,layout,name+' low range '+str(layout))
            report['runs'].append(dict(car=name,layout=layout,forward=forward,locked=locked,reverse=reverse));save()
            yield from fresh(cls,converted);fit(0);yield from wait(.2)
            check(setup()['front_share']==stock['front_share'] and setup()['drive_layout']==0,name+' Factory restores original axle split')
            car.get_parts().apply_loadout(base,False)
            check(setup()['front_share']==stock['front_share'],name+' old save removes conversion')
        if name=='Range Rover':
            for package in (1,2):
                yield from fresh(cls,base);check(work.open(),'open engine package');work.select_part(5);work.preview(package);check(work.fit(),'fit engine package');work.close()
                expected=config()
                for layout in (1,2,3):
                    fit(layout);check(config()==expected,'engine package '+str(package)+' coexists with layout '+str(layout))
    check(hashes=={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in protected},'player saves and authored maps untouched')
    report['ok']=True;save();world=pc=car=work=None;gc.collect();u.EditorLevelLibrary.editor_end_play();yield 3
    level.load_level('/Engine/Maps/Entry');yield 3
steps=run();deadline=0.;busy=False;began=time.monotonic()
def tick(dt):
    global deadline,busy,steps
    if busy or time.monotonic()<deadline:return
    busy=True;done=False
    try:
        assert time.monotonic()-began<1200,'Layout check timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
save();u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
