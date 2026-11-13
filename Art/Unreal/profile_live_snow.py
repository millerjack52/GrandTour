"""Living mud LM4e (docs/LIVING_MUD_PLAN.md LM4e, docs/LIVE_SNOW_DRIVE.md): the snow's cost, profiled in one Play In Editor session
on L_SnowDrive, and the before/after pictures on one deterministic field.

Run by Art/profile_live_snow.ps1 (the snow check's window, flags and CSV GPU stats). GT_SNOW_PROFILE_TAG names the run
(before, cut1, after ...); GT_SNOW_PROFILE lists its sections, in this order:
- warm: the shader compile workers idle (their CPU time still for 6 s), so no compile skews the first pass.
- drive: pass 1 from a reset field (the field's record on: UGTMudSubsystem::SetRecordingForTest) and pass 2 in its trench,
  at full throttle as the snow check drives them; each a CSV profile, the feel's segment speeds, the GT stats (Settle,
  upload, the stamps, the clods: mean / p99 / max; the tiles swept and the cells uploaded a frame). The record is saved after
  pass 1 (Saved/LM4e/rec_<tag>_pass1) and after pass 2 (Saved/LM4e/rec_<tag>).
- replay: the before run's pass-1 record replayed one recorded frame per tick (its stamps, clock and settle in place of the
  tick's own), from the cost camera, profiled: Settle's and the upload's cost on the very same work in every build.
- pics: the before run's pass 1 + 2 record replayed all at once (the CRC against the record's end), 10 s to settle, then
  Snow_OnFoot, Snow_GoW_View, Snow_Edge_Close, Snow_Channel_Close, Snow_Long and Snow_Cost_View from fixed cameras (the
  before run computes them on its replayed field, Saved/LM4e/cameras.json; every later run reads them) into
  Art/Export/LiveSnowDrive/BeforeLM4e (tag before) or AfterLM4e_<tag>.
- stand: from the on-foot camera and the cost camera on that field, each feature toggled alone in ABBA order (base, the
  feature, the feature, base), 5 s CSV profiles after 3.5 s: Parallax 1, SnowSSS 0, GlintDensity 0, the detail strength
  (SnowDetailCm 0), the patch's shadow casting off, the clods off, the patch hidden (its own cost), M_GT_Mud's instance on
  the patch, and the LM4e switches GT_SNOW_PROFILE_SWITCHES names (each at 0 against its default).
- toggles: pass 1 again on reset fields in the order A B C D D C B A (A the base; FineGrid 0, Settle 0, Clods 0), plus any
  LM4e switch GT_SNOW_PROFILE_PASS_SWITCHES names.
Everything goes to Art/Export/LiveSnowDrive/Profile_<tag>/profile-report.json.
"""
import unreal as u,json,time,math,traceback,csv,statistics,os,subprocess
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
TAG=os.environ.get('GT_SNOW_PROFILE_TAG','before')
SECTIONS=[s.strip() for s in os.environ.get('GT_SNOW_PROFILE','warm,drive,replay,pics,stand,toggles').split(',') if s.strip()]
STAND_SWITCHES=[s.strip() for s in os.environ.get('GT_SNOW_PROFILE_SWITCHES','').split(',') if s.strip()]
PASS_SWITCHES=[s.strip() for s in os.environ.get('GT_SNOW_PROFILE_PASS_SWITCHES','').split(',') if s.strip()]
STAND_ONLY=[s.strip() for s in os.environ.get('GT_SNOW_PROFILE_STAND_ONLY','').split(',') if s.strip()]
OUT=ROOT/'Art/Export/LiveSnowDrive'/('Profile_'+TAG);OUT.mkdir(parents=True,exist_ok=True)
PICS=ROOT/'Art/Export/LiveSnowDrive'/('BeforeLM4e' if TAG=='before' else 'AfterLM4e_'+TAG);PICS.mkdir(parents=True,exist_ok=True)
REC=ROOT/'Saved/LM4e';REC.mkdir(parents=True,exist_ok=True)
CSV_DIR=ROOT/'Saved/Profiling/CSV'
LEVEL='/Game/GrandTour/ArtTests/LiveSnowDrive/L_SnowDrive';SPEC='/Game/GrandTour/ArtTests/LiveSnowDrive/DA_SnowDrive'
CLAY='/Game/GrandTour/Materials/M_GT_Mud'
u.EditorPythonScripting.set_keep_python_script_alive(True)
VIEW=(1440,900)
START_X=500.;END_X=12500.;DONE_X=12000.;SNOW_X=(3000.,11000.);DRIFT_X=(7000.,8000.)
SEGS={'entry':(3000.,6600.),'A':(4000.,6600.),'drift':(7000.,8000.),'B':(8500.,11000.)}
MARKS=sorted(set(x for seg in SEGS.values() for x in seg)|set(SNOW_X)|set(DRIFT_X))
PASS_S=300.;STALL_S=15.;STOP_MPS=.1
PROFILE_S=5.;WARM_S=3.5
report={'ok':False,'tag':TAG,'sections':SECTIONS,'passes':[],'profiles':[],'images':[],'stand':[],'toggles':[],'viewports':[]}
csv_marks=[];samples=[];pending_shot=None
world=car=move=pc=camera=mud=weather=None

def console(cmd):
    u.SystemLibrary.execute_console_command(world,cmd,pc)
def csv_files():
    return set(p.name for p in CSV_DIR.glob('*.csv')) if CSV_DIR.exists() else set()
def begin_play():
    lib=getattr(u,'GTPlayWindowLibrary',None)
    if lib and lib.request_play_in_new_window(VIEW[0],VIEW[1]):return 'new window %dx%d'%VIEW
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();return 'level viewport'
def spec():
    return u.load_asset(SPEC).spec
def ground(x,y):
    return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec(),x,y)
def surface_z(x,y):
    xy=u.Vector2D(x,y);return ground(x,y)+mud.snow_top_cm_at(xy)+mud.mud_height_cm_at(xy)
def snow_patch():
    return next((p for p in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch) if p.medium==u.GTDeformMedium.SNOW),None)
def patch_cell(p=None):
    p=p or snow_patch();return (p.bounds_max.x-p.bounds_min.x)/max(1,p.cells_x)
def cell_centres(lo,hi,origin,cell):
    i0=math.ceil((lo-origin)/cell-.5);i1=math.floor((hi-origin)/cell-.5)
    return [origin+(i+.5)*cell for i in range(i0,i1+1)]
def place_car(x,y):
    z=ground(x,y);car.set_actor_location_and_rotation(u.Vector(x,y,z+150),u.Rotator(),False,True);body=car.get_component_by_class(u.SkeletalMeshComponent);body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True)
def aim_camera(cpos,ctarget,fov=55):
    camera.set_actor_location(cpos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos,ctarget),False);camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0.)
def aim(c):
    aim_camera(u.Vector(*c['location']),u.Vector(*c['target']),c['fov'])
def project(pt):
    r=u.GameplayStatics.project_world_to_screen(pc,pt,False)
    if r is None:return None
    if isinstance(r,tuple):
        if len(r)==2 and isinstance(r[0],bool):return r[1] if r[0] else None
        return r[0]
    return r
def drive_step(target_y):
    pos=car.get_actor_location();speed=car.get_velocity().length()/100.;yaw=car.get_actor_rotation().yaw
    target_yaw=math.degrees(math.atan2(target_y-pos.y,650.));error=(target_yaw-yaw+180)%360-180;car.set_raw_steer(max(-.65,min(.65,error/24)))
    move.set_throttle_input(1.);move.set_brake_input(.4 if speed>12. else 0.)
    return pos,speed
def seg_speeds(c):
    out={}
    for name,(lo,hi) in SEGS.items():
        if lo in c and hi in c and c[hi]>c[lo]:
            mps=(hi-lo)/100./(c[hi]-c[lo]);out[name]=dict(s=round(c[hi]-c[lo],3),mps=round(mps,3),kmh=round(mps*3.6,2))
        else:out[name]=None
    a=out.get('A');b=out.get('B')
    if a and b:
        mps=((SEGS['A'][1]-SEGS['A'][0])+(SEGS['B'][1]-SEGS['B'][0]))/100./(a['s']+b['s']);out['35cm']=dict(s=round(a['s']+b['s'],3),mps=round(mps,3),kmh=round(mps*3.6,2))
    else:out['35cm']=None
    return out
def gt_stats():
    # The GT stats since the last reset_settle_stats: Settle, the upload, the stamps, the clods (ms), the tiles and cells.
    return dict(settle_frames=mud.get_settle_frames(),settle_mean_ms=round(mud.get_settle_mean_ms(),4),settle_p99_ms=round(mud.get_settle_p99_ms(),4),settle_max_ms=round(mud.get_settle_max_ms(),4),
        awake_peak=mud.get_settle_awake_peak(),swept_tiles_mean=round(mud.get_swept_tiles_mean(),2),
        upload_mean_ms=round(mud.get_upload_mean_ms(),4),upload_p99_ms=round(mud.get_upload_p99_ms(),4),upload_max_ms=round(mud.get_upload_max_ms(),4),upload_cells_mean=round(mud.get_upload_cells_mean(),0),
        stamp_mean_ms=round(mud.get_stamp_mean_ms(),4),stamp_p99_ms=round(mud.get_stamp_p99_ms(),4),stamp_max_ms=round(mud.get_stamp_max_ms(),4),
        clod_frames=mud.get_clod_frames(),clod_mean_ms=round(mud.get_clod_mean_ms(),4),clod_p99_ms=round(mud.get_clod_p99_ms(),4),clod_max_ms=round(mud.get_clod_max_ms(),4))
def start_csv(label):
    csv_marks.append((label,csv_files()));console('csvprofile start')
def stop_csv():
    console('csvprofile stop')
def shot(name,delay=1.5):
    global pending_shot
    path=PICS/(name+'.png');report['images'].append(str(path));pending_shot=(time.monotonic()+delay,path)

# ---- the CSV ---------------------------------------------------------------------------------------------------------
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
def stats(v):
    s=sorted(v);n=len(s)
    return dict(mean=round(statistics.fmean(s),4),p99=round(s[min(n-1,max(0,math.ceil(.99*n)-1))],4),max=round(s[-1],4))
KEYS=['FrameTime','GameThreadTime','RenderThreadTime','RHIThreadTime','GPUTime','GTMud/GameThread/Settle','GTMud/GameThread/Upload','GTMud/GameThread/Clods','GTMud/Stamp','GTMud/SweptTiles','GTMud/UploadCells',
    'Exclusive/GameThread/UI','Exclusive/GameThread/TickActors']
def parse_profiles():
    seen=[m[1] for m in csv_marks]+[csv_files()]
    for k,(label,before) in enumerate(csv_marks):
        new=sorted(seen[k+1]-before);entry=dict(run=label,csv=None)
        if new:
            path=CSV_DIR/new[0];entry['csv']=str(path)
            cols,n=read_csv(path);entry['frames']=n
            for name in KEYS:
                if name in cols:entry[name]=stats(cols[name])
            # GPU by pass (every GPU/ column's mean) and the render thread's busy time (its exclusive scopes less its waits).
            entry['gpu']={c[4:]:round(statistics.fmean(v),4) for c,v in cols.items() if c.startswith('GPU/')}
            rt=[c for c in cols if c.startswith('Exclusive/RenderThread/') and 'EventWait' not in c]
            if rt:entry['render_busy_ms']=round(sum(statistics.fmean(cols[c]) for c in rt),4)
        report['profiles'].append(entry)
def prof(label):
    return next((e for e in report['profiles'] if e['run']==label),None)
GROUPS={'base':['Basepass','Prepass'],'shadows':['ShadowDepths','ShadowProjection','DistanceFieldShadows'],'lights':['RenderDeferredLighting','Lights','SubsurfaceScattering','TranslucentLighting'],
    'lumen':['LumenSceneUpdate','LumenScreenProbeGather','LumenReflections','RayTracingScene','RayTracingDynamicGeometry','DistanceFields'],'translucency':['Translucency'],
    'post':['TemporalSuperResolution','PostProcessing','MotionBlur','Fog','SkyAtmosphere'],'velocity':['RenderVelocities']}
def grouped(e):
    g=e.get('gpu',{})
    return {k:round(sum(g.get(p,0.) for p in ps),4) for k,ps in GROUPS.items()}
def summarise():
    # Per stand/toggle set: the means of its A runs and B runs, B - A, for the frame, the threads, the GPU and its passes.
    def unit(e):
        if not e:return None
        o={k:e[k]['mean'] for k in ('FrameTime','GameThreadTime','RenderThreadTime','RHIThreadTime','GPUTime') if k in e}
        o['render_busy_ms']=e.get('render_busy_ms');o.update(grouped(e))
        for k in ('GTMud/GameThread/Settle','GTMud/GameThread/Upload','GTMud/Stamp','GTMud/GameThread/Clods','Exclusive/GameThread/UI'):
            if k in e:o[k]=e[k]['mean']
        return o
    for group in ('stand','toggles','replay_ab'):
        if group not in report:continue
        out={}
        for item in report[group]:
            key=(item.get('view',''),item['feature'])
            out.setdefault(key,{'A':[],'B':[]})[item['side']].append(unit(prof(item['label'])))
        summ=[]
        for (view,feature),d in out.items():
            A=[x for x in d['A'] if x];B=[x for x in d['B'] if x]
            if not A or not B:continue
            keys=[k for k in A[0] if all(k in x and x[k] is not None for x in A+B)]
            ma={k:round(statistics.fmean(x[k] for x in A),4) for k in keys};mb={k:round(statistics.fmean(x[k] for x in B),4) for k in keys}
            entry=dict(view=view,feature=feature,A=ma,B=mb,B_minus_A={k:round(mb[k]-ma[k],4) for k in keys},runs=[len(A),len(B)])
            # The GT stats (Settle, upload, stamps: mean and p99) of the A and B runs, where the runs carry them.
            gts={'A':[],'B':[]}
            for item in report[group]:
                if (item.get('view',''),item['feature'])==(view,feature):
                    g=item.get('gt') or next((r for r in report.get('replays',[])+report.get('passes',[]) if r.get('label')==item['label']),None)
                    if g:gts[item['side']].append(g)
            for side in ('A','B'):
                if gts[side]:entry['gt_'+side]={k:round(statistics.fmean(x[k] for x in gts[side]),4) for k in ('settle_mean_ms','settle_p99_ms','upload_mean_ms','upload_p99_ms','stamp_mean_ms','stamp_p99_ms','upload_cells_mean','swept_tiles_mean') if all(k in x for x in gts[side])}
            summ.append(entry)
        report[group+'_summary']=summ
    for p in report['passes']:
        e=prof(p['label']);p['csv']=unit(e)
        if e:p['csv_p99']={k:e[k]['p99'] for k in ('FrameTime','GameThreadTime','GTMud/GameThread/Settle','GTMud/GameThread/Upload','GTMud/Stamp') if k in e}
    if report.get('replay'):
        e=prof(report['replay']['label']);report['replay']['csv']=unit(e)
        if e:report['replay']['csv_p99']={k:e[k]['p99'] for k in ('FrameTime','GameThreadTime','GTMud/GameThread/Settle','GTMud/GameThread/Upload','GTMud/Stamp') if k in e}

def finish(error=None):
    global gen
    gen=None
    if error:report['error']=error
    for cmd in ('gt.Snow.Plough -1','gt.Snow.BellyDrag -1','gt.Snow.Parallax -1','gt.Mud.Clods 1','gt.Mud.Settle 1','gt.Snow.FineGrid 1'):
        try:console(cmd)
        except Exception:pass
    try:parse_profiles();summarise()
    except Exception:report['profile_error']=traceback.format_exc()
    (OUT/'profile-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()

# ---- the sections ----------------------------------------------------------------------------------------------------
def others(where):
    # The processes that would skew a timing (Blender, the games, another Unreal than this one: its PID, parent and command
    # line's start), noted where they were seen.
    try:
        cmd="Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(blender|GoWR|GoW|FarCry6|UnrealEditor|UnrealEditor-Cmd)\\.exe$' -and $_.ProcessId -ne %d } | ForEach-Object { $c=(($_.CommandLine + '') -replace '\\s+',' '); '{0}|{1}|{2}|{3}' -f $_.Name,$_.ProcessId,$_.ParentProcessId,$c.Substring(0,[Math]::Min(160,$c.Length)) }"%os.getpid()
        out=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,timeout=30).stdout.strip()
        names=[l for l in out.splitlines() if l.strip()]
    except Exception as e:names=['check failed: %s'%e]
    report.setdefault('others_seen',[]).append([where,round(time.monotonic()-START,1),names])
def scw_cpu():
    try:
        out=subprocess.run(['powershell','-NoProfile','-Command','(Get-Process ShaderCompileWorker -ErrorAction SilentlyContinue | Measure-Object CPU -Sum).Sum'],capture_output=True,text=True,timeout=20).stdout.strip()
        return float(out) if out else 0.
    except Exception:return -1.
def warm():
    # The on-foot and cost views once each (their shaders), then wait until the compile workers' CPU time stands still for 6 s.
    t0=time.monotonic();last=scw_cpu();still=0.;report['warm']={'scw_cpu_start':last}
    while time.monotonic()-t0<300.:
        yield 3.
        now=scw_cpu()
        if now<0:break
        still=still+3. if now-last<.3 else 0.
        last=now
        if still>=6.:break
    report['warm'].update(scw_cpu_end=last,waited_s=round(time.monotonic()-t0,1))
def drive_pass(label,npass,record=False):
    console('gt.Snow.Plough -1');console('gt.Snow.BellyDrag -1')
    if npass==1:
        if record:mud.set_recording_for_test(True)
        else:mud.reset_fields_for_test()
    place_car(START_X,0.)
    yield 4.
    pc.set_view_target_with_blend(car,0.)
    car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True)
    others(label+' start');mud.reset_settle_stats();car.get_spray().reset_throw_stats();start_csv(label)
    t0=time.monotonic();cross={};stop_since=None;stop_max=0.;stop_at=None;rows=[];sample_at=0.;why=None
    while True:
        now=time.monotonic();pos,speed=drive_step(0.);weather.set_wetness_for_test(0.)
        for mark in MARKS:
            if mark not in cross and pos.x>=mark:cross[mark]=now
        if now-sample_at>=.25:rows.append((round(pos.x/100.,3),round(pos.y/100.,3),round(speed,3)));sample_at=now
        stopped=pos.x>START_X+100. and speed<STOP_MPS
        if stopped:
            stop_since=stop_since or now
            if now-stop_since>stop_max:stop_max=now-stop_since;stop_at=round(pos.x/100.,2)
        else:stop_since=None
        if pos.x>=END_X:why='reached the end'
        elif stop_since is not None and pos.x>SNOW_X[0]+100. and now-stop_since>=STALL_S:why='stalled at %.2f m'%(pos.x/100.)
        elif now-t0>=PASS_S:why='timed out at %.2f m'%(pos.x/100.)
        if why:break
        yield 0.
    move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True);car.set_raw_steer(0.);stop_csv();others(label+' end')
    seg=seg_speeds(cross);drift_s=(cross[DRIFT_X[1]]-cross[DRIFT_X[0]]) if (DRIFT_X[0] in cross and DRIFT_X[1] in cross) else None
    drift_y=[r[1] for r in rows if DRIFT_X[0]/100.<=r[0]<=DRIFT_X[1]/100.]
    p=snow_patch()
    out=dict(label=label,npass=npass,ended=why,end_x_m=round(pos.x/100.,2),completed=bool(pos.x>=DONE_X),elapsed_s=round(time.monotonic()-t0,2),seg=seg,longest_stop_s=round(stop_max,3),longest_stop_at_m=stop_at,
        drift_mean_mps=round((DRIFT_X[1]-DRIFT_X[0])/100./drift_s,3) if drift_s else None,line_y_cm=round(statistics.fmean(drift_y)*100.,2) if drift_y else None,
        cell_cm=round(patch_cell(p),3),mesh_triangles=p.mesh_triangle_count,collapses_fired=p.collapses_fired,clods_live=p.clods_live)
    out.update(gt_stats())
    report['passes'].append(out)
    yield 3.
def section_drive():
    yield from drive_pass('pass1',1,record=True)
    n=mud.save_record_for_test(str(REC/('rec_%s_pass1'%TAG)));report['record_pass1_events']=n
    yield from drive_pass('pass2',2)
    mud.set_recording_for_test(False)
    n=mud.save_record_for_test(str(REC/('rec_%s'%TAG)));report['record_events']=n;report['record_end_crc']='%08x'%(mud.record_end_crc_for_test()&0xffffffff)
    p1=report['passes'][-2];p2=report['passes'][-1]
    report['feel']=dict(pass1_35cm_kmh=(p1['seg'].get('35cm') or {}).get('kmh'),pass1_drift_kmh=(p1['seg'].get('drift') or {}).get('kmh'),pass2_drift_kmh=(p2['seg'].get('drift') or {}).get('kmh'),
        drift_ratio=round(p2['drift_mean_mps']/p1['drift_mean_mps'],3) if (p1.get('drift_mean_mps') and p2.get('drift_mean_mps')) else None,
        pass1_A_kmh=(p1['seg'].get('A') or {}).get('kmh'),pass1_B_kmh=(p1['seg'].get('B') or {}).get('kmh'),both_completed=bool(p1['completed'] and p2['completed']))
def match_camera(yc):
    # LM4e: the view that matches the mud profile's (Art/Unreal/profile_live_mud.py): 4 m over the patch's line at 50 m, looking
    # 3 m ahead along it (about 53 degrees down), 60 degrees: the frame all patch, so the two patches' costs cover the same pixels.
    z=surface_z(5000.,yc);tz=surface_z(5300.,yc)
    return dict(location=[5000.,round(yc,1),round(z+400.,1)],target=[5300.,round(yc,1),round(tz,1)],fov=60)
def cost_camera(yc):
    tz=surface_z(5000.,yc);return dict(location=[4300.,round(yc-450.,1),round(tz+900.,1)],target=[5200.,round(yc+50.,1),round(tz,1)],fov=70)
def section_replay():
    n=mud.load_record_for_test(str(REC/'rec_before_pass1'));report['replay']=dict(label='replay_pass1',events=n,record='rec_before_pass1')
    if n<=0:report['replay']['error']='no record';return
    cams=json.loads((REC/'cameras.json').read_text()) if (REC/'cameras.json').exists() else None
    aim(cams['cameras']['Snow_Cost_View'] if cams else cost_camera(0.))
    place_car(START_X,0.)
    yield 2.
    mud.start_replay_for_test(False);mud.reset_settle_stats();start_csv('replay_pass1');t0=time.monotonic()
    while mud.is_replaying_for_test() and time.monotonic()-t0<400.:
        yield .5
    stop_csv();report['replay'].update(gt_stats());report['replay']['seconds']=round(time.monotonic()-t0,1)
    report['replay']['crc']='%08x'%(mud.field_crc_for_test()&0xffffffff)
    yield 2.
REPLAY_SWITCHES=[s.strip() for s in (os.environ.get('GT_SNOW_PROFILE_REPLAY_SWITCHES') or 'gt.Snow.QuietSleep,gt.Snow.FastSweep,gt.Snow.UploadTiles').split(',') if s.strip()]
def replay_once(label):
    cams=json.loads((REC/'cameras.json').read_text())
    aim(cams['cameras']['Snow_Cost_View'])
    yield 2.
    mud.start_replay_for_test(False);mud.reset_settle_stats();others(label);start_csv(label);t0=time.monotonic()
    while mud.is_replaying_for_test() and time.monotonic()-t0<400.:
        yield .5
    stop_csv();out=dict(label=label,seconds=round(time.monotonic()-t0,1),crc='%08x'%(mud.field_crc_for_test()&0xffffffff));out.update(gt_stats())
    report.setdefault('replays',[]).append(out)
    yield 2.
def section_replay_ab():
    # A (every LM4e switch on), then each config off (all of them together, then each alone), mirrored, A again: ABCD..DCBA.
    if mud.load_record_for_test(str(REC/'rec_before_pass1'))<=0:report['replay_ab_error']='no record';return
    place_car(START_X,0.)
    configs=[('all',REPLAY_SWITCHES)]+[(s,[s]) for s in REPLAY_SWITCHES]
    order=[('base',[])]+configs+list(reversed(configs))+[('base',[])]
    for k,(name,offs) in enumerate(order):
        for s in offs:console('%s 0'%s)
        label='replayab_%s_%d'%(name.replace('.','-'),k)
        yield from replay_once(label)
        for s in offs:console('%s 1'%s)
        report.setdefault('replay_ab',[]).append(dict(label=label,view='replay',feature=name,side='A' if name=='base' else 'B'))
    base=[t for t in report['replay_ab'] if t['feature']=='base']
    for t in list(report['replay_ab']):
        if t['feature']!='base':
            for b in base:report['replay_ab'].append(dict(label=b['label'],view='replay',feature=t['feature'],side='A'))
    report['replay_ab']=[t for t in report['replay_ab'] if t['feature']!='base']
def track_floor_offsets(yc):
    # The tyres' trench floors at 50 m (the snow check's trench_profile rule): per side the lowest surface 30-130 cm off the line.
    p=snow_patch();c=patch_cell(p);b0=p.bounds_min;x=min(cell_centres(4990.,5010.,b0.x,c),key=lambda v:abs(v-5000.))
    out={}
    for side in (-1,1):
        best=None
        for y in cell_centres(yc+(30. if side>0 else -130.),yc+(130. if side>0 else -30.),b0.y,c):
            xy=u.Vector2D(x,y);s=mud.snow_top_cm_at(xy)+mud.mud_height_cm_at(xy)
            if best is None or s<best[0]:best=(s,y)
        out['+Y' if side>0 else '-Y']=abs(best[1]-yc) if best else 82.
    return out
def make_cameras(yc):
    off=track_floor_offsets(yc);cams={}
    fz=surface_z(5000.,yc+20.);tz=surface_z(5250.,yc-10.)
    cams['Snow_Channel_Close']=dict(location=[5000.,round(yc+20.,1),round(fz+60.,1)],target=[5250.,round(yc-10.,1),round(tz,1)],fov=55)
    yt=yc+off['+Y'];cz=surface_z(5000.,yt+75.)+250.;tx=5000.+250./math.tan(math.radians(35.));tz=surface_z(tx,yt)
    cams['Snow_GoW_View']=dict(location=[5000.,round(yt+75.,1),round(cz,1)],target=[round(tx,1),round(yt,1),round(tz,1)],fov=60)
    yt=yc-off['-Y'];fz=surface_z(4600.,yt);tz=surface_z(6000.,yt)
    cams['Snow_OnFoot']=dict(location=[4600.,round(yt,1),round(fz+165.,1)],target=[6000.,round(yt,1),round(tz+40.,1)],fov=65)
    lip=yc-off['-Y']-30.;cy=lip-60.;cz=surface_z(4700.,cy)+30.;tz=surface_z(5300.,lip)+3.
    cams['Snow_Edge_Close']=dict(location=[4700.,round(cy,1),round(cz,1)],target=[5300.,round(lip,1),round(tz,1)],fov=55)
    zl=ground(5600.,yc);zt=ground(8400.,yc)
    cams['Snow_Long']=dict(location=[5600.,round(yc+130.,1),round(zl+170.,1)],target=[8400.,round(yc,1),round(zt,1)],fov=60)
    cams['Snow_Cost_View']=cost_camera(yc)
    return dict(line_y_cm=yc,track_offsets=off,cameras=cams)
PIC_ORDER=['Snow_OnFoot','Snow_GoW_View','Snow_Edge_Close','Snow_Channel_Close','Snow_Long','Snow_Cost_View']
def section_pics():
    n=mud.load_record_for_test(str(REC/'rec_before'));rep=dict(events=n,record='rec_before')
    report['pics']=rep
    if n<=0:rep['error']='no record';return
    place_car(START_X,0.)
    yield 1.
    t0=time.monotonic();mud.start_replay_for_test(True);rep['replay_s']=round(time.monotonic()-t0,2)
    rep['crc_after_replay']='%08x'%(mud.field_crc_for_test()&0xffffffff);rep['record_end_crc']='%08x'%(mud.record_end_crc_for_test()&0xffffffff);rep['crc_match']=rep['crc_after_replay']==rep['record_end_crc']
    yield 10.
    rep['crc_settled']='%08x'%(mud.field_crc_for_test()&0xffffffff);p=snow_patch();rep['collapses_fired']=p.collapses_fired;rep['clods_live']=p.clods_live
    if TAG=='before':
        line=next((x['line_y_cm'] for x in report['passes'] if x['npass']==1 and x.get('line_y_cm') is not None),0.)
        cams=make_cameras(line);(REC/'cameras.json').write_text(json.dumps(cams,indent=2))
    cams=json.loads((REC/'cameras.json').read_text());rep['cameras']=cams
    console('gt.Snow.Parallax 0')
    for name in PIC_ORDER:
        aim(cams['cameras'][name]);shot(name,1.5)
        yield 3.5
        # LM4e: the same frame with the patch's surface hidden: where the two differ is the patch (the summary's mask, so the
        # sky's drifting clouds and the HUD do not count in the before/after difference).
        surface_visible(False);shot(name+'_Hidden',1.5)
        yield 3.5
        surface_visible(True)
    # LM4e cut 4, the seams: with chunks, a view down the strip from 60 m where the chunks' LODs change at 87.8 m (LOD 0 to 1)
    # and 103.8 m (1 to 2), as the distance picks them (Snow_Seams) and with every chunk at LOD 0 (Snow_Seams_L0), and every
    # chunk border in view as screen polylines (the summary counts dark and sky-coloured pixels along them in both).
    p=snow_patch()
    if p and getattr(p,'chunk_count',0)>0:
        yc=cams['line_y_cm'];cz=surface_z(6000.,yc-150.)+170.
        cam=dict(location=[6000.,round(yc-150.,1),round(cz,1)],target=[10000.,round(yc,1),round(ground(10000.,yc),1)],fov=60)
        aim(cam);yield 2.
        lines=[];b0=p.bounds_min;b1=p.bounds_max;step=p.chunk_cells*patch_cell(p)
        x=b0.x+step
        while x<b1.x-1.:
            pts=[project(u.Vector(x,y,surface_z(x,y))) for y in [b0.y+20.*k for k in range(int((b1.y-b0.y)/20.)+1)]]
            lines.append(dict(border='x %.0f'%x,points=[[round(q.x,1),round(q.y,1)] for q in pts if q is not None]));x+=step
        y=b0.y+step
        while y<b1.y-1.:
            pts=[project(u.Vector(xx,y,surface_z(xx,y))) for xx in [6200.+50.*k for k in range(110)]]
            lines.append(dict(border='y %.0f'%y,points=[[round(q.x,1),round(q.y,1)] for q in pts if q is not None]));y+=step
        rep['seams']=dict(camera=cam,lines=lines,lods_natural=[p.chunks_at_lod.x,p.chunks_at_lod.y,p.chunks_at_lod.z],chunks=p.chunk_count)
        shot('Snow_Seams',1.5);yield 3.5
        p.force_chunk_lod_for_test(0);yield .5
        rep['seams']['lods_forced']=[p.chunks_at_lod.x,p.chunks_at_lod.y,p.chunks_at_lod.z]
        shot('Snow_Seams_L0',1.5);yield 3.5
        p.force_chunk_lod_for_test(-1)
    console('gt.Snow.Parallax -1')
def mid():
    return snow_patch().mesh_material
# LM4e cut 4: the surface may be chunks; the patch's helpers set every one (the grid component alone before them).
def surface_shadow(on):
    p=snow_patch()
    if hasattr(p,'set_surface_cast_shadow_for_test'):p.set_surface_cast_shadow_for_test(on)
    else:p.mesh.set_cast_shadow(on)
def surface_visible(on):
    p=snow_patch()
    if hasattr(p,'set_surface_visible_for_test'):p.set_surface_visible_for_test(on)
    else:p.mesh.set_visibility(on,False)
def surface_material(m):
    p=snow_patch()
    if hasattr(p,'set_surface_material_for_test'):p.set_surface_material_for_test(m)
    else:p.mesh.set_material(0,m)
def feature(name):
    # (set, restore) for one feature alone.
    p=snow_patch()
    if name=='Parallax':return (lambda:console('gt.Snow.Parallax 1'),lambda:console('gt.Snow.Parallax -1'))
    if name in ('SnowSSS','GlintDensity'):
        d=mid().get_scalar_parameter_value(name);return (lambda:mid().set_scalar_parameter_value(name,0.),lambda:mid().set_scalar_parameter_value(name,d))
    if name=='Detail':
        d=mid().get_vector_parameter_value('SnowDetailCm');return (lambda:mid().set_vector_parameter_value('SnowDetailCm',u.LinearColor(0.,0.,0.,0.)),lambda:mid().set_vector_parameter_value('SnowDetailCm',d))
    if name=='Shadow':return (lambda:surface_shadow(False),lambda:surface_shadow(True))
    if name=='Clods':return (lambda:console('gt.Mud.Clods 0'),lambda:console('gt.Mud.Clods 1'))
    if name=='Hidden':return (lambda:surface_visible(False),lambda:surface_visible(True))
    if name=='Clay':
        snow_mid=mid();clay=u.MaterialLibrary.create_dynamic_material_instance(world,u.load_asset(CLAY))
        for t in ('MudField','MudTread','MudLayer'):
            tex=snow_mid.get_texture_parameter_value(t)
            if tex:clay.set_texture_parameter_value(t,tex)
        for v in ('PatchMin','PatchSize','PatchTexels'):clay.set_vector_parameter_value(v,snow_mid.get_vector_parameter_value(v))
        for s in ('LugPeriodCm','DiagZ0','DiagZRange','MudDiagnostic'):clay.set_scalar_parameter_value(s,snow_mid.get_scalar_parameter_value(s))
        return (lambda:surface_material(clay),lambda:surface_material(snow_mid))
    if name=='Masked':
        # LM4e cut 5: M_GT_Snow is opaque; MI_GT_Snow_Masked is it with the copied root's masked blend mode, the patch's parameters copied.
        snow_mid=mid();mi=u.load_asset('/Game/GrandTour/Materials/MI_GT_Snow_Masked')
        if not mi:return (lambda:None,lambda:None)
        masked=u.MaterialLibrary.create_dynamic_material_instance(world,mi)
        for t in ('MudField','MudTread','MudLayer'):
            tex=snow_mid.get_texture_parameter_value(t)
            if tex:masked.set_texture_parameter_value(t,tex)
        for v in ('PatchMin','PatchSize','PatchTexels'):masked.set_vector_parameter_value(v,snow_mid.get_vector_parameter_value(v))
        for s in ('LugPeriodCm','DiagZ0','DiagZRange','MudDiagnostic','SnowParallax'):masked.set_scalar_parameter_value(s,snow_mid.get_scalar_parameter_value(s))
        return (lambda:surface_material(masked),lambda:surface_material(snow_mid))
    if name in REBUILD_SWITCHES:
        # Read when the patches are built: the switch, the patches built again and the before run's drive replayed onto them.
        return (lambda:rebuild_with(name,0),lambda:rebuild_with(name,1))
    # An LM4e switch: 0 against its default 1.
    return (lambda:console('%s 0'%name),lambda:console('%s 1'%name))
REBUILD_SWITCHES=('gt.Snow.MeshLod',)
def rebuild_with(name,value):
    console('%s %d'%(name,value));report.setdefault('rebuilds',[]).append([name,value,mud.rebuild_patches_for_test()])
    if mud.load_record_for_test(str(REC/'rec_before'))>0:mud.start_replay_for_test(True)
def profile_one(group,view,feat,side,n):
    label='%s_%s_%s_%s_%d'%(group,view,feat.replace('.','-'),side,n)
    yield WARM_S
    mud.reset_settle_stats();start_csv(label)
    yield PROFILE_S
    stop_csv();report[group].append(dict(label=label,view=view,feature=feat,side=side,gt=gt_stats()))
def section_stand():
    cams=json.loads((REC/'cameras.json').read_text())['cameras']
    views=[('onfoot',cams['Snow_OnFoot']),('cost',cams['Snow_Cost_View']),('match',match_camera(json.loads((REC/'cameras.json').read_text())['line_y_cm']))]
    feats=STAND_ONLY or (['Parallax','SnowSSS','GlintDensity','Detail','Shadow','Clods','Hidden','Clay']+STAND_SWITCHES)
    for view,cam in views:
        aim(cam)
        yield 3.
        for f in feats:
            on,off=feature(f);n=0;slow=f in REBUILD_SWITCHES
            for side in ('A','B','B','A'):
                n+=1
                if side=='B' and n==2:
                    on()
                    if slow:aim(cam);yield 12.
                yield from profile_one('stand',view,f,side,n)
                if side=='B' and n==3:
                    off()
                    if slow:aim(cam);yield 12.
def section_toggles():
    # Pass 1 on reset fields, A B C D D C B A: A the base, then FineGrid 0, Settle 0, Clods 0 (and the LM4e pass switches).
    feats=['FineGrid','Settle','Clods']+PASS_SWITCHES
    order=['base']+feats+list(reversed(feats))+['base']
    for k,f in enumerate(order):
        side='A' if f=='base' else 'B'
        if f=='FineGrid':console('gt.Snow.FineGrid 0');report['rebuild_%d'%k]=mud.rebuild_patches_for_test();yield 5.
        elif f=='Settle':console('gt.Mud.Settle 0')
        elif f=='Clods':console('gt.Mud.Clods 0')
        elif f in REBUILD_SWITCHES:console('%s 0'%f);mud.rebuild_patches_for_test();yield 5.
        elif f!='base':console('%s 0'%f)
        label='toggle_%s_%d'%(f.replace('.','-'),k)
        yield from drive_pass(label,1)
        report['toggles'].append(dict(label=label,view='pass1',feature=f if f!='base' else 'base',side=side))
        if f=='FineGrid':console('gt.Snow.FineGrid 1');mud.rebuild_patches_for_test();yield 5.
        elif f=='Settle':console('gt.Mud.Settle 1')
        elif f=='Clods':console('gt.Mud.Clods 1')
        elif f in REBUILD_SWITCHES:console('%s 1'%f);mud.rebuild_patches_for_test();yield 5.
        elif f!='base':console('%s 1'%f)
    # The A/B pairs: every feature against the two base passes (the first and the last, ABBA over the whole set).
    base=[t for t in report['toggles'] if t['feature']=='base']
    for t in list(report['toggles']):
        if t['feature']!='base':
            for b in base:report['toggles'].append(dict(label=b['label'],view='pass1',feature=t['feature'],side='A'))
    report['toggles']=[t for t in report['toggles'] if t['feature']!='base']

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
        cars=u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn);assert cars,'Automation car missing';car=cars[0]
        move=car.get_chaos_movement();pc=u.GameplayStatics.get_player_controller(world,0)
        if pc:pc.possess(car);car.disable_input(pc)
        size=list(pc.get_viewport_size());report['viewports'].append(size)
        if attempt==0 and str(report.get('play_mode','')).startswith('new window') and size[0]!=VIEW[0]:
            u.EditorLevelLibrary.editor_end_play();yield 5.;report['play_mode_retry']=begin_play();yield 15.;continue
        break
    report['viewport_size']=size
    car.reset_driving_inputs();car.set_chase_camera(False)
    car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
    mud=next(o for o in u.ObjectIterator(u.GTMudSubsystem) if o.get_outer()==world);weather=next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==world)
    clear=weather.find_state('Clear')
    if clear:weather.set_state(clear,True)
    weather.set_wetness_for_test(0.)
    camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Live_Overview')
    p=snow_patch();report['patch']=dict(cell_cm=round(patch_cell(p),3),cells=[p.cells_x,p.cells_y],mesh_vertices=p.mesh_vertex_count,mesh_triangles=p.mesh_triangle_count,material=p.mesh_material.get_base_material().get_path_name())
    if 'warm' in SECTIONS:
        place_car(START_X,0.)
        aim_camera(u.Vector(4600.,-82.,ground(4600.,-82.)+200.),u.Vector(6000.,-82.,ground(6000.,-82.)),65)
        yield 4.
        aim(cost_camera(0.))
        yield 4.
        pc.set_view_target_with_blend(car,0.)
        yield from warm()
    for name,fn in (('drive',section_drive),('replay',section_replay),('replay_ab',section_replay_ab),('pics',section_pics),('stand',section_stand),('toggles',section_toggles)):
        if name in SECTIONS:
            report.setdefault('section_times',{})[name]=round(time.monotonic()-START,1);others(name)
            yield from fn()
    others('end')
    yield 4.   # the last CSV is written after its stop
    report['ok']=all(Path(q).exists() for q in report['images'])
    if not report['ok']:report['error']='a picture is missing'
    finish()

START=time.monotonic();gen=main();wake=0.
def tick(dt):
    global wake,pending_shot
    now=time.monotonic()
    try:
        if pending_shot and now>=pending_shot[0]:
            path=pending_shot[1];pending_shot=None
            console('HighResShot %dx%d filename="%s"'%(VIEW[0],VIEW[1],path.as_posix()))
        if gen is None:return
        if now-START>7200:finish('LM4e profile timed out');return
        if now<wake:return
        w=next(gen);wake=now+(w or 0.)
    except StopIteration:
        pass
    except Exception:
        finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
