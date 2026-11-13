"""Living mud LM4e (docs/LIVING_MUD_PLAN.md LM4e): the clay reference for the snow's cost, on L_MudDrive in one Play In Editor
session (Art/profile_live_mud.ps1; the mud check's window, flags and CSV GPU stats).
- The shader compile workers idle first (their CPU time still for 6 s).
- The dry crossing as the mud check drives it (gt.Mud.Settle 1 on reset fields, the mud check's speed hold, 5 m to 119 m),
  profiled: the frame, the threads, the GPU by pass, the GT stats.
- The clay bog patch's own GPU cost from the view that matches the snow profile's cost camera (9 m up, 9 m behind and 5 m to the
  side of a point on the patch's line at its middle, 70 degrees): the patch mesh visible / hidden, ABBA twice, 5 s profiles after
  3.5 s. The snow profile measures its patch the same way (stand, Hidden).
Everything to Art/Export/LiveMudDrive/Profile_<tag>/profile-report.json.
"""
import unreal as u,json,time,math,traceback,csv,statistics,os,subprocess
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
TAG=os.environ.get('GT_MUD_PROFILE_TAG','ref')
OUT=ROOT/'Art/Export/LiveMudDrive'/('Profile_'+TAG);OUT.mkdir(parents=True,exist_ok=True)
CSV_DIR=ROOT/'Saved/Profiling/CSV'
LEVEL='/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive';SPEC='/Game/GrandTour/ArtTests/LiveMudDrive/DA_MudDrive'
u.EditorPythonScripting.set_keep_python_script_alive(True)
VIEW=(1440,900);PROFILE_S=5.;WARM_S=3.5
report={'ok':False,'tag':TAG,'profiles':[],'stand':[],'viewports':[]}
csv_marks=[];world=car=move=pc=camera=mud=weather=None
def console(cmd):
    u.SystemLibrary.execute_console_command(world,cmd,pc)
def csv_files():
    return set(p.name for p in CSV_DIR.glob('*.csv')) if CSV_DIR.exists() else set()
def begin_play():
    lib=getattr(u,'GTPlayWindowLibrary',None)
    if lib and lib.request_play_in_new_window(VIEW[0],VIEW[1]):return 'new window %dx%d'%VIEW
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();return 'level viewport'
def ground(x,y):
    return u.GTVehicleSetupLibrary.sample_terrain_height_cm(u.load_asset(SPEC).spec,x,y)
def start_csv(label):
    csv_marks.append((label,csv_files()));console('csvprofile start')
def aim_camera(cpos,ctarget,fov):
    camera.set_actor_location(cpos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos,ctarget),False);camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0.)
def gt_stats():
    return dict(settle_mean_ms=round(mud.get_settle_mean_ms(),4),settle_p99_ms=round(mud.get_settle_p99_ms(),4),upload_mean_ms=round(mud.get_upload_mean_ms(),4),upload_p99_ms=round(mud.get_upload_p99_ms(),4),
        stamp_mean_ms=round(mud.get_stamp_mean_ms(),4),stamp_p99_ms=round(mud.get_stamp_p99_ms(),4),clod_mean_ms=round(mud.get_clod_mean_ms(),4),clod_p99_ms=round(mud.get_clod_p99_ms(),4))
def read_csv(path):
    with open(path,newline='') as f:rows=list(csv.reader(f))
    header=rows[0];body=[]
    for r in rows[1:]:
        if not r or r[0].startswith('[') or r[0]=='EVENTS':break
        body.append(r)
    cols={}
    for i,name in enumerate(header):
        v=[]
        for r in body:
            try:v.append(float(r[i]))
            except (ValueError,IndexError):pass
        if v:cols[name]=v
    return cols,len(body)
GROUPS={'base':['Basepass','Prepass'],'shadows':['ShadowDepths','ShadowProjection','DistanceFieldShadows'],'lights':['RenderDeferredLighting','Lights','SubsurfaceScattering','TranslucentLighting'],
    'lumen':['LumenSceneUpdate','LumenScreenProbeGather','LumenReflections','RayTracingScene','RayTracingDynamicGeometry','DistanceFields'],'translucency':['Translucency'],
    'post':['TemporalSuperResolution','PostProcessing','MotionBlur','Fog','SkyAtmosphere'],'velocity':['RenderVelocities']}
KEYS=['FrameTime','GameThreadTime','RenderThreadTime','RHIThreadTime','GPUTime','GTMud/GameThread/Settle','GTMud/GameThread/Upload','GTMud/GameThread/Clods','GTMud/Stamp','Exclusive/GameThread/UI','Exclusive/GameThread/TickActors']
def parse():
    seen=[m[1] for m in csv_marks]+[csv_files()]
    for k,(label,before) in enumerate(csv_marks):
        new=sorted(seen[k+1]-before);e=dict(run=label)
        if new:
            cols,n=read_csv(CSV_DIR/new[0]);e['frames']=n;e['csv']=str(CSV_DIR/new[0])
            for name in KEYS:
                if name in cols:
                    s=sorted(cols[name]);e[name]=dict(mean=round(statistics.fmean(s),4),p99=round(s[min(len(s)-1,max(0,math.ceil(.99*len(s))-1))],4))
            g={c[4:]:statistics.fmean(v) for c,v in cols.items() if c.startswith('GPU/')}
            e['gpu']={a:round(sum(g.get(p,0.) for p in ps),4) for a,ps in GROUPS.items()}
            rt=[c for c in cols if c.startswith('Exclusive/RenderThread/') and 'EventWait' not in c]
            if rt:e['render_busy_ms']=round(sum(statistics.fmean(cols[c]) for c in rt),4)
        report['profiles'].append(e)
    def unit(e):
        if not e:return None
        o={k:e[k]['mean'] for k in KEYS if k in e};o['render_busy_ms']=e.get('render_busy_ms');o.update(e.get('gpu',{}));return o
    by={x['run']:x for x in report['profiles']}
    report['dry']['csv']=unit(by.get('dry'))
    for view in ('cost','match'):
        A=[unit(by[x['label']]) for x in report['stand'] if x.get('view')==view and x['side']=='A' and by.get(x['label'])];B=[unit(by[x['label']]) for x in report['stand'] if x.get('view')==view and x['side']=='B' and by.get(x['label'])]
        if A and B:
            keys=[k for k in A[0] if all(k in x and x[k] is not None for x in A+B)]
            ma={k:round(statistics.fmean(x[k] for x in A),4) for k in keys};mb={k:round(statistics.fmean(x[k] for x in B),4) for k in keys}
            report['patch_cost_'+view]=dict(visible=ma,hidden=mb,visible_minus_hidden={k:round(ma[k]-mb[k],4) for k in keys},runs=[len(A),len(B)])
def finish(error=None):
    global gen
    gen=None
    if error:report['error']=error
    try:parse()
    except Exception:report['profile_error']=traceback.format_exc()
    (OUT/'profile-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def scw_cpu():
    try:
        out=subprocess.run(['powershell','-NoProfile','-Command','(Get-Process ShaderCompileWorker -ErrorAction SilentlyContinue | Measure-Object CPU -Sum).Sum'],capture_output=True,text=True,timeout=20).stdout.strip()
        return float(out) if out else 0.
    except Exception:return -1.
def main():
    global world,car,move,pc,camera,mud,weather
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
    yield 6.
    report['play_mode']=begin_play()
    yield 15.
    for attempt in range(2):
        t0=time.monotonic()
        while u.EditorLevelLibrary.get_game_world() is None:
            if time.monotonic()-t0>40:raise RuntimeError('Play In Editor did not start')
            yield 1.
        world=u.EditorLevelLibrary.get_game_world()
        car=u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn)[0];move=car.get_chaos_movement();pc=u.GameplayStatics.get_player_controller(world,0)
        if pc:pc.possess(car);car.disable_input(pc)
        size=list(pc.get_viewport_size());report['viewports'].append(size)
        if attempt==0 and str(report.get('play_mode','')).startswith('new window') and size[0]!=VIEW[0]:
            u.EditorLevelLibrary.editor_end_play();yield 5.;report['play_mode_retry']=begin_play();yield 15.;continue
        break
    report['viewport_size']=size
    car.reset_driving_inputs();car.set_chase_camera(False);car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
    mud=next(o for o in u.ObjectIterator(u.GTMudSubsystem) if o.get_outer()==world);weather=next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==world)
    weather.set_wetness_for_test(0.)
    camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Live_Overview')
    patches=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch)
    bog=next(p for p in patches if not p.get_editor_property('bHasProfile'))
    report['patch']=dict(section=bog.section_index,bounds_min=[bog.bounds_min.x,bog.bounds_min.y],bounds_max=[bog.bounds_max.x,bog.bounds_max.y],cells=[bog.cells_x,bog.cells_y],mesh_vertices=bog.mesh_vertex_count,mesh_triangles=bog.mesh_triangle_count,
        cell_cm=round((bog.bounds_max.x-bog.bounds_min.x)/max(1,bog.cells_x),3),material=bog.mesh_material.get_base_material().get_path_name(),patches=len(patches))
    # Warm: the cost view once, then the compile workers idle.
    tx=.5*(bog.bounds_min.x+bog.bounds_max.x);ty=50.;tz=ground(tx,ty)
    cam=dict(location=[tx-900.,ty-500.,tz+900.],target=[tx,ty,tz],fov=70);report['cost_camera']=cam
    aim_camera(u.Vector(*cam['location']),u.Vector(*cam['target']),cam['fov'])
    yield 4.
    t0=time.monotonic();last=scw_cpu();still=0.
    while time.monotonic()-t0<300.:
        yield 3.
        now=scw_cpu()
        if now<0:break
        still=still+3. if now-last<.3 else 0.;last=now
        if still>=6.:break
    report['warm_s']=round(time.monotonic()-t0,1)
    # The dry crossing (the mud check's: gt.Mud.Settle 1 on reset fields, its speed hold).
    console('gt.Mud.Settle 1');mud.reset_fields_for_test()
    z=ground(500,0);car.set_actor_location_and_rotation(u.Vector(500,0,z+150),u.Rotator(),False,True);body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True)
    yield 4.
    pc.set_view_target_with_blend(car,0.)
    car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True);mud.reset_settle_stats();start_csv('dry');t0=time.monotonic()
    while True:
        pos=car.get_actor_location();speed=car.get_velocity().length()/100.;yaw=car.get_actor_rotation().yaw
        target_yaw=math.degrees(math.atan2(-pos.y,650.));error=(target_yaw-yaw+180)%360-180;car.set_raw_steer(max(-.65,min(.65,error/24)))
        move.set_throttle_input(max(.18,min(1.,.42+(3.2-speed)*.22)));move.set_brake_input(.25 if speed>4.5 else 0.);weather.set_wetness_for_test(0.)
        if pos.x>11900 or time.monotonic()-t0>110:break
        yield 0.
    move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True);console('csvprofile stop')
    report['dry']=dict(end_x_m=round(pos.x/100.,2),elapsed_s=round(time.monotonic()-t0,1));report['dry'].update(gt_stats())
    yield 3.
    # The bog patch's own GPU cost (its surface and its rut water) from the cost view and from the matching view (4 m over the
    # line, 3 m ahead, 60 degrees: the frame all patch, as the snow profile's): visible / hidden, ABBA twice each.
    zm=ground(4400.,0.);report['match_camera']=match=dict(location=[4400.,0.,zm+400.],target=[4700.,0.,ground(4700.,0.)],fov=60)
    for view,c in (('cost',cam),('match',match)):
        aim_camera(u.Vector(*c['location']),u.Vector(*c['target']),c['fov'])
        yield 3.
        n=0
        for side in ('A','B','B','A','A','B','B','A'):
            n+=1;bog.mesh.set_visibility(side=='A',False);bog.water_mesh.set_visibility(side=='A',False)
            yield WARM_S
            label='patch_%s_%s_%d'%(view,side,n);mud.reset_settle_stats();start_csv(label)
            yield PROFILE_S
            console('csvprofile stop');report['stand'].append(dict(label=label,side=side,view=view))
        bog.mesh.set_visibility(True,False);bog.water_mesh.set_visibility(True,False)
    yield 4.   # the last CSV is written after its stop
    report['ok']=True
    finish()
START=time.monotonic();gen=main();wake=0.
def tick(dt):
    global wake
    now=time.monotonic()
    try:
        if gen is None:return
        if now-START>1800:finish('LM4e mud profile timed out');return
        if now<wake:return
        w=next(gen);wake=now+(w or 0.)
    except StopIteration:
        pass
    except Exception:
        finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
