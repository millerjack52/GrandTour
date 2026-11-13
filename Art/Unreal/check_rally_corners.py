"""Complete-circuit instrument. Real A/D key events; automated driver, not a feel verdict.

No saved assets, initial velocity injection, yaw torque or path correction. Logs
every callback during driving, plus engine CSV timings including hitches.
"""
import bisect, gc, hashlib, json, math, os, time, traceback
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
QA=ROOT/'Saved/RallyHandlingQA';QA.mkdir(exist_ok=True,parents=True)
LABEL=os.environ.get('GT_RALLY_HANDLING_LABEL','baseline')
DATA=json.loads((ROOT/'Art/Export/RallyHandling/course.json').read_text())
PTS=DATA['samples_m'];CUM=[0.]
for a,b in zip(PTS,PTS[1:]):CUM.append(CUM[-1]+math.dist(a[:2],b[:2]))
DRIVER=int(os.environ.get('GT_RALLY_DRIVER','2'))
assert DRIVER in (2,3)
report=dict(ok=False,label=LABEL,runs=[],controller_version=DRIVER,note='Offscreen PIE, real keyboard steering driven by a sideslip-aware path controller; not owner feel or standalone presentation FPS')
protected=ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'
digest=hashlib.sha256(protected.read_bytes()).hexdigest()
world=pc=car=author=None
key=0
frame_dt=0.

def save(): (QA/('corners-'+LABEL+'.json')).write_text(json.dumps(report,indent=2))
def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)
def keys(value):
    global key
    if value==key:return
    if key:cmd('Input.-key '+('A' if key<0 else 'D'))
    if value:cmd('Input.+key '+('A' if value<0 else 'D'))
    key=value
def wait(seconds):
    end=u.GameplayStatics.get_time_seconds(world)+seconds
    while u.GameplayStatics.get_time_seconds(world)<end:yield 0
def at(s):
    s=max(0,min(CUM[-1],s));i=max(1,min(len(CUM)-1,bisect.bisect_right(CUM,s)))
    f=(s-CUM[i-1])/max(.0001,CUM[i]-CUM[i-1])
    return tuple(a+(b-a)*f for a,b in zip(PTS[i-1],PTS[i]))
def project(x,y,station):
    best=(station,1e9)
    for i in range(max(1,bisect.bisect_left(CUM,station-15)),min(len(CUM),bisect.bisect_right(CUM,station+45)+1)):
        a,b=PTS[i-1],PTS[i];dx,dy=b[0]-a[0],b[1]-a[1]
        f=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(.0001,dx*dx+dy*dy)))
        off=math.hypot(x-a[0]-f*dx,y-a[1]-f*dy)
        if off<best[1]:best=(CUM[i-1]+f*(CUM[i]-CUM[i-1]),off)
    return best
def ground(x,y):
    for tile in author.relief_tiles.values():
        p=tile.get_actor_location()
        if p.x<=x<p.x+tile.span_cm and p.y<=y<p.y+tile.span_cm:return tile.height_at(u.Vector2D(x,y))
    return author.base_height_at(u.Vector2D(x,y))
def percentile(values,q):
    v=sorted(values);i=(len(v)-1)*q;lo=int(i)
    return v[lo]+(v[min(lo+1,len(v)-1)]-v[lo])*(i-lo)

def drive(ident,cls):
    global car
    keys(0)
    if car:car.destroy_actor()
    p=at(8);q=at(10);yaw=math.degrees(math.atan2(q[1]-p[1],q[0]-p[0]))
    car=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,cls,u.Transform(location=u.Vector(p[0]*100,p[1]*100,ground(p[0]*100,p[1]*100)+100),rotation=u.Rotator(yaw=yaw)),'CornerCheck_'+ident)
    assert car
    pc.possess(car);car.reset_driving_inputs();car.enable_input(pc);car.set_chase_camera(True)
    assert car.get_audio().muted,'Vehicle audio must remain muted'
    move=car.get_chaos_movement();drive=car.get_drivetrain();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    drive.set_low_range(False);drive.set_diff_lock(False);move.set_handbrake_input(True)
    yield from wait(5)
    wheels=move.get_editor_property('wheels')
    centres=[move.soil_wheel_centre(i) for i in range(4)]
    wheelbase=((centres[0]+centres[1])*.5-(centres[2]+centres[3])*.5).length()*.01
    lock=sum(w.get_editor_property('max_steer_angle') for w in wheels[:2])*.5
    row=dict(car=ident,wheelbase_m=wheelbase,lock_deg=lock,mass_kg=move.get_editor_property('mass'),front_drive_share=drive.get_editor_property('centre_split_front'),audio_muted=car.get_audio().muted,trace=[])
    if ident=='Ferrari':
        row['mesh']=car.get_component_by_class(u.SkeletalMeshComponent).get_editor_property('skeletal_mesh_asset').get_path_name()
        row['handbrake']=[]
        rev_start=u.GameplayStatics.get_time_seconds(world)
        while u.GameplayStatics.get_time_seconds(world)-rev_start<3:
            move.set_throttle_input(1)
            row['handbrake'].append(json.loads(drive.setup_report()))
            yield .03
        move.set_throttle_input(0);yield from wait(5)
    report['runs'].append(row);save()
    yield from wait(1) # Drain report serialization while parked, before starting either clock.
    cmd('csvprofile start')
    cmd('csvprofile event Rally_'+LABEL+'_'+ident)
    cmd('gt.Perf.Reset');cmd('gt.Perf.LogSpikes 2')
    move.set_handbrake_input(False)
    start=u.GameplayStatics.get_time_seconds(world);station=8.;last_switch=-1.;wall=time.perf_counter()
    while True:
        now=u.GameplayStatics.get_time_seconds(world)-start
        p=car.get_actor_location();v=car.get_velocity();r=car.get_actor_rotation()
        station,off=project(p.x*.01,p.y*.01,station);speed=v.length()*.01
        # Version 2 remains the original comparison. Version 3 separately probes
        # recovery with a driver that budgets speed for its actual recovery arc.
        look=max(7.,speed*.7);target=at(station+look)
        err=(math.degrees(math.atan2(target[1]-p.y*.01,target[0]-p.x*.01))-r.yaw+180)%360-180
        body_slip=(math.degrees(math.atan2(v.y,v.x))-r.yaw+180)%360-180 if speed>1 else 0
        angle=math.degrees(math.atan2(2*wheelbase*math.sin(math.radians(err)),look))+.7*body_slip
        mph=speed*2.23694;curve=[(0,1),(12,.72),(25,.5),(37,.34),(50,.26),(62,.2),(75,.17),(100,.14)]
        scale=curve[-1][1]
        for (a,va),(b,vb) in zip(curve,curve[1:]):
            if mph<=b:scale=va+(vb-va)*max(0,(mph-a)/(b-a));break
        desired=max(-1,min(1,angle/max(1,lock*scale)))
        solver=json.loads(move.rally_handling_report());assert len(solver.get('wheels',[]))==4
        # Duty-cycled keyboard control with a minimum 80ms hold and release band.
        # Feedback is wheel angle so the controller cannot mistake raw input for delivered steering.
        actual=sum(w['angle'] for w in solver['wheels'][:2])*.5
        error=angle-actual
        # Release an overshoot; do not tap the opposite key just to trim a turn.
        # Countersteer only when the demanded wheel direction actually reverses.
        newkey=(1 if angle>0 else -1) if error*angle>0 and abs(error)>.65 else 0
        if now-last_switch>=.08 and newkey!=key:keys(newkey);last_switch=now
        target_speed=27.78
        for ahead in (0,5,10,20,35,50,70):
            a,b,c=(at(station+ahead+d) for d in (0,5,10))
            ab,bc,ac=math.dist(a[:2],b[:2]),math.dist(b[:2],c[:2]),math.dist(a[:2],c[:2])
            cross=abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))
            curvature=2*cross/max(.001,ab*bc*ac)
            corner=math.sqrt(3.4/max(.0001,curvature))
            target_speed=min(target_speed,math.sqrt(corner*corner+2*3.0*ahead))
        if DRIVER==3:
            recovery_curvature=abs(2*math.sin(math.radians(err))/look)
            target_speed=min(target_speed,math.sqrt(3.4/max(.0001,recovery_curvature)))
        throttle=max(0,min(1,(target_speed-speed)*.35));brake=max(0,min(.65,(speed-target_speed)*.3))
        if DRIVER==3:
            # Driver lifts during a slide; vehicle torque/grip and failure limits
            # remain untouched. This result is not a version-2 regression pass.
            throttle*=max(0,min(1,(18-abs(body_slip))/10))
        move.set_throttle_input(throttle);move.set_brake_input(brake)
        stamp=time.perf_counter();slip=(math.degrees(math.atan2(v.y,v.x))-r.yaw+180)%360-180 if speed>1 else 0
        row['trace'].append(dict(t=now,s_m=station,off_m=off,kmh=speed*3.6,target_kmh=target_speed*3.6,command=key,raw=car.get_raw_steer(),desired_deg=angle,baseline_demand=desired,solver=solver,yaw_rate=mesh.get_physics_angular_velocity_in_degrees().z,slip_deg=slip,roll=r.roll,pitch=r.pitch,z_cm=p.z,ride_weight=move.get_rally_suspension_weight(),throttle=throttle,brake=brake,callback_ms=frame_dt*1000,wall_ms=(stamp-wall)*1000))
        if ident=='Ferrari':row['trace'][-1]['drivetrain']=json.loads(drive.setup_report())
        wall=stamp
        if station>=CUM[-1]-12:row['completed']=True;break
        if off>12 or abs(r.roll)>50 or now>180:
            row['aborted']='off course, rolled, or 180 second timeout';row['completed']=False;break
        yield 0
    keys(0);move.set_throttle_input(0);move.set_brake_input(1)
    cmd('csvprofile stop');yield 0
    cmd('gt.Perf.LogSpikes 0');cmd('gt.Perf.Dump rally-'+LABEL+'-'+ident)
    trace=row['trace'];ms=[r['wall_ms'] for r in trace[1:]]
    row.update(distance_m=station-8,peak_kmh=max(r['kmh'] for r in trace),max_off_m=max(r['off_m'] for r in trace),max_slip_deg=max(abs(r['slip_deg']) for r in trace),max_roll=max(abs(r['roll']) for r in trace),frames=len(trace),wall_frame_ms=dict(mean=sum(ms)/len(ms),p95=percentile(ms,.95),p99=percentile(ms,.99),max=max(ms)),saturated_seconds=sum(max(0,b['t']-a['t']) for a,b in zip(trace,trace[1:]) if abs(b['solver']['filtered'])>.98))
    save();yield from wait(4)

def run():
    global world,pc,car,author
    L=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert L.load_level('/Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling')
    yield 5 # Let loaded render resources settle before creating a second PIE scene.
    L.editor_set_viewport_realtime(False)
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
    until=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<until;yield .2
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car()
    author=u.GameplayStatics.get_all_actors_of_class(world,u.GTProceduralGround)[0]
    assert author.landscape_recess_depth_cm==5
    for c in ('t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','DisableAllScreenMessages'):cmd(c)
    cmd('gc.DumpAnalyticsToLog 1') # Diagnose collection hitches; collector settings are unchanged.
    response=int(os.environ.get('GT_RALLY_COUNTERSTEER','1'));cmd('gt.Vehicle.CountersteerResponse '+str(response));report['countersteer_response']=response
    report['profile']={c.split()[0]:u.SystemLibrary.get_console_variable_float_value(c.split()[0]) for c in json.loads((ROOT/'Art/lidar_performance.json').read_text())['commands']}
    report['viewport_resolution']=list(pc.get_viewport_size())
    yield from wait(8)
    specs=[('RangeRover',u.GTCarPawn)]
    if os.environ.get('GT_RALLY_FERRARI','0')=='1':
        specs=[('Ferrari',u.load_class(None,'/Game/GrandTour/Vehicles/Ferrari288Good/BP_Ferrari288.BP_Ferrari288_C'))]
    if os.environ.get('GT_RALLY_FLEET','0')=='1':
        specs += [('BMW',u.load_class(None,'/Game/GrandTour/Vehicles/Bodies/E39Touring/BP_E39Touring.BP_E39Touring_C')),('Suzuki',u.load_class(None,'/Game/GrandTour/Vehicles/Bodies/SJ413/BP_SJ413.BP_SJ413_C'))]
    for ident,cls in specs:yield from drive(ident,cls)
    report['execution_ok']=True
    report['ok']=all(r.get('completed',False) for r in report['runs'])
    assert hashlib.sha256(protected.read_bytes()).hexdigest()==digest
    report['lidar_map_unchanged']=True;save()
    keys(0);world=pc=car=author=None;gc.collect();u.EditorLevelLibrary.editor_end_play();yield 4
    assert L.load_level('/Engine/Maps/Entry');gc.collect();yield 3

steps=run();began=time.monotonic();deadline=0.;busy=False
def tick(dt):
    global deadline,busy,steps,frame_dt
    frame_dt=dt
    if busy or time.monotonic()<deadline:return
    busy=True;done=False
    try:
        assert time.monotonic()-began<1000,'Corner check timeout'
        deadline=time.monotonic()+next(steps)
    except StopIteration:done=True
    except Exception:
        report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error']);done=True
    finally:busy=False
    if done:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.EditorLevelLibrary.editor_end_play();u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
save();u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
