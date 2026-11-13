"""VRAM soak (docs/VRAM_SOAK.md): a MEMORY investigation of the "Out of video memory" crashes in check_mud_variants.py runs.

No frame-time, cost or timing measurement (the owner's rule): only the RHI's and D3D12's own memory and object counters, logged
to the editor log every GT_SOAK_LOG_S seconds (default 30) and around each capture, between "GTSOAK_MARK <tag>" lines the wrapper
(Art/soak_vram.ps1) parses:
- stat dumpnonframe D3D12Resources   (TOTAL, Render Targets, UAV Textures, Textures, UAV Buffers, Buffers, RayTracing, Transient)
- stat dumpnonframe D3D12RHI         (Num command lists / allocators / query heaps / PSOs: D3D12 objects alive)
- stat dumpnonframe D3D12MemoryDetails (standalone / pooled allocations, upload pool)
- rhi.DumpMemory                     (the RHI stat group: reserved buffers committed / uncommitted, texture / RT kinds)
- rhi.DumpResourceMemory 1           (the tracked RHI resources' total) and, at the start and the end, the top 30 by size
- r.DumpRenderTargetPoolMemory       (the render target pool, "Pool: referenced/allocated")
plus the GT counters that could grow (live splat decals, decal components, actors, the paint's splats and carried blots).

Modes (environment, set by the wrapper):
  GT_SOAK_MODE A: L_MudVariants, PIE 1440x900, the strip's drive repeated (full throttle, low range, diff lock, 5 m -> 215 m
                  out onto the exit gravel, a stalled section skipped by a teleport 2 m past it) for GT_SOAK_MINUTES (10).
               B: L_MudVariants, the car parked on the gravel at 212 m: 25 HighResShots and 6 buffer-visualisation dumps as
                  check_mud_variants.py takes them (its cameras' kinds, gt.Mud.POM / POMShadow per look, the dumps' console
                  sequence), logged after each, then a 60 s hold.
               C: L_SnowDrive, its drive (5 m -> 120 m) repeated for GT_SOAK_MINUTES (5).
               K: check_mud_variants.py verbatim (its pictures and report into Saved/SoakVRAM/K), this logger beside it every
                  GT_SOAK_LOG_S (15 s here). The check waits for the GPU itself (GT_CHECK_PACE, default on), so GT_SOAK_PACE does
                  nothing in mode K.
  GT_SOAK_PACE  1: every tick waits for the GPU (gpu_pace: a 1x1 render target readback), modes A, B and C only.
  GT_SOAK_OFF   comma-separated console switches set to 0 for the run (the bisect: gt.Mud.Settle, gt.Snow.MeshLod, ...).
  GT_SOAK_CMDS  semicolon-separated console commands run once play starts (e.g. a D3D12 setting under test).
Pictures (mode B) go to Saved/SoakVRAM. Writes Saved/SoakVRAM/soak-<mode>-report.json.
"""
import unreal as u,json,time,math,os,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Saved/SoakVRAM';OUT.mkdir(parents=True,exist_ok=True)
MODE=os.environ.get('GT_SOAK_MODE','A').upper()[:1]
MINUTES=float(os.environ.get('GT_SOAK_MINUTES','10' if MODE=='A' else '5'))
# Mode B's split (the bisect of the captures): 'move' = the 25 camera jumps without a HighResShot (the same waits), 'still' = 25
# HighResShots from one camera (the first look) and no dumps; '' = the check's captures, both.
B_KIND=os.environ.get('GT_SOAK_B','').strip().lower()
# GT_SOAK_PACE=1: the mitigation under test - every tick reads one pixel of a 1x1 render target, a GPU readback that waits for the
# GPU to finish everything submitted so far. -RenderOffScreen has no swap chain, and D3D12's RHIEndDrawingViewport only waits for
# the previous frame's GPU work after a native present, so nothing else paces the CPU to the GPU in these runs.
PACE=bool(os.environ.get('GT_SOAK_PACE'));pace_rt=None
LOG_S=float(os.environ.get('GT_SOAK_LOG_S','30'))
OFF=[s.strip() for s in os.environ.get('GT_SOAK_OFF','').split(',') if s.strip()]
CMDS=[s.strip() for s in os.environ.get('GT_SOAK_CMDS','').split(';') if s.strip()]
if MODE=='C':
    LEVEL='/Game/GrandTour/ArtTests/LiveSnowDrive/L_SnowDrive';SPEC='/Game/GrandTour/ArtTests/LiveSnowDrive/DA_SnowDrive'
    START_X=500.;LAP_X=12000.;SECTION_STARTS=[3000.,7000.]
else:
    LEVEL='/Game/GrandTour/ArtTests/MudVariants/L_MudVariants';SPEC='/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants'
    START_X=500.;LAP_X=21500.;SECTION_STARTS=[3000.,7500.,12000.,16500.]
u.EditorPythonScripting.set_keep_python_script_alive(True)
VIEW=(1440,900);STALL_S=15.;LEG_CAP_S=240.;STOP_MPS=.1
phase='load';last=time.monotonic();start=last;play0=None;next_log=None;marks=0
FRAME=0;pending=None;hold_until=0
report={'ok':False,'mode':MODE,'b_kind':B_KIND,'pace':PACE,'minutes':MINUTES,'off':OFF,'cmds':CMDS,'level':LEVEL,'marks':[],'laps':[]}
world=car=move=pc=camera=mud=weather=paint=splats=None;run={}
def console(cmd):
    u.SystemLibrary.execute_console_command(world,cmd,pc)
def begin_play():
    lib=getattr(u,'GTPlayWindowLibrary',None)
    if lib and lib.request_play_in_new_window(VIEW[0],VIEW[1]):return 'new window %dx%d'%VIEW
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();return 'level viewport'
def spec():
    return u.load_asset(SPEC).spec
def ground(x,y):
    return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec(),x,y)
def surface_z(x,y):
    return ground(x,y)+(mud.mud_height_cm_at(u.Vector2D(x,y)) if mud else 0.)
def gt_counters():
    c={}
    try:
        c['actors']=len(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
        c['decal_components']=sum(1 for o in u.ObjectIterator(u.DecalComponent) if o.get_world()==world)
        if splats:c.update(live_decals=splats.get_live_decal_count(),decal_splats=splats.get_decal_splats(),landscape_splats=splats.get_landscape_splats(),pending_decals=splats.get_pending_decal_count())
        if paint:c.update(paint_splats=paint.get_splat_count(),carried_blots=paint.get_carried_blot_count())
        if mud:c['lowered_m3']=round(mud.total_lowered_cm3()/1e6,3)
    except Exception:c['error']=traceback.format_exc(limit=1)
    return c
def mem_log(tag,top=False):
    # Every command's output lands in the log after this mark (the stats commands may print a frame later); the wrapper reads a
    # mark's numbers from its line to the next mark.
    global marks
    marks+=1;t=round(time.monotonic()-(play0 or start),1)
    row=dict(n=marks,tag=tag,t_s=t,frame=FRAME,counters=gt_counters())
    if car is not None:p=car.get_actor_location();row['car_m']=[round(p.x/100.,1),round(p.y/100.,1)]
    report['marks'].append(row)
    u.log('GTSOAK_MARK %d %s t=%.1f frame=%d %s'%(marks,tag,t,FRAME,json.dumps(row['counters'])))
    for c in ('stat dumpnonframe D3D12Resources','stat dumpnonframe D3D12RHI','stat dumpnonframe D3D12MemoryDetails','rhi.DumpMemory','rhi.DumpResourceMemory 1','r.DumpRenderTargetPoolMemory'):
        console(c)
    if top:
        u.log('GTSOAK_TOP %d %s'%(marks,tag));console('rhi.DumpResourceMemory 30');console('rhi.DumpResourceMemory 30 Transient=yes')
def gpu_pace():
    # One 1x1 readback: FlushRenderingCommands, then the RHI's read waits for the GPU (D3D12: FlushCommands WaitForCompletion).
    global pace_rt
    gw=u.EditorLevelLibrary.get_game_world()
    if gw is None:return
    if pace_rt is None or pace_rt.get_outer() is None:
        pace_rt=u.RenderingLibrary.create_render_target2d(gw,1,1,u.TextureRenderTargetFormat.RTF_RGBA8)
    u.RenderingLibrary.read_render_target_pixel(gw,pace_rt,0,0)
def finish(error=None):
    global phase
    phase='finished'
    if error:report['error']=error
    else:report['ok']=True
    (OUT/('soak-%s-report.json'%MODE)).write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def place_car(x,y):
    z=ground(x,y);car.set_actor_location_and_rotation(u.Vector(x,y,z+150),u.Rotator(),False,True);body=car.get_component_by_class(u.SkeletalMeshComponent)
    body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());car.reset_driving_inputs();move.set_handbrake_input(True)
def settled(now,since,cap=90.):
    pos=car.get_actor_location()
    return (car.get_velocity().length()<25. and pos.z-ground(pos.x,pos.y)<60. and now-since>2.) or now-since>cap
def drive_step(target_y):
    # The checks' drive: full throttle (the brake only past 12 m/s, a guard), steered to the line.
    pos=car.get_actor_location();speed=car.get_velocity().length()/100.;yaw=car.get_actor_rotation().yaw
    target_yaw=math.degrees(math.atan2(target_y-pos.y,650.));error=(target_yaw-yaw+180)%360-180;car.set_raw_steer(max(-.65,min(.65,error/24)))
    move.set_throttle_input(1.);move.set_brake_input(.4 if speed>12. else 0.)
    return pos,speed
def aim_camera(cpos,ctarget,fov):
    camera.set_actor_location(cpos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cpos,ctarget),False);camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0.)
# ---- mode B: the check's captures -------------------------------------------------------------------------------------------
def b_views():
    # 25 looks of the check's kinds (on-foot and close per section, the PBR close / steep ones with their POM levels, the car's side,
    # rear and rut views) and 6 dumps (the car, the calibration gravel, each section's ground), all at 1440x900.
    v=[]
    for name,x0 in (('Firm',3000.),('Standard',7500.),('Deep',12000.),('Stony',16500.)):
        mid=x0+1250.;ry=-90.;xa=x0+300.;xb=x0+1500.
        v.append(('OnFoot_'+name,2,(u.Vector(xa,ry,surface_z(xa,ry)+170.),u.Vector(xb,ry,surface_z(xb,ry)),65.)))
        v.append(('Close_'+name,2,(u.Vector(mid-140.,ry+90.,surface_z(mid-140.,ry+90.)+90.),u.Vector(mid+30.,ry,surface_z(mid,ry)-10.),50.)))
    tx,ty=8800.,320.;tz=surface_z(tx,ty)
    close=(u.Vector(tx-55.,ty,surface_z(tx-55.,ty)+25.),u.Vector(tx,ty,tz),50.);steep=(u.Vector(tx-80.,ty,tz+29.),u.Vector(tx,ty,tz),45.)
    foot=v[2][2]
    v+= [('PBR_OnFoot_POM0',0,foot),('PBR_OnFoot',2,foot),('PBR_Close_POM0',0,close),('PBR_Close',2,close),('PBR_Close_Steep',2,steep),('PBR_Close_Steep_NoShadow',-2,steep)]
    cx=21200.;gz=ground(cx,0.)
    v+= [('Car_Side',2,(u.Vector(cx-25.,640.,gz+110.),u.Vector(cx-25.,0.,gz+75.),50.)),('Car_Rear',2,(u.Vector(cx-700.,0.,gz+160.),u.Vector(cx,0.,gz+70.),50.)),
         ('Car_PBR',2,(u.Vector(cx-25.,640.,gz+110.),u.Vector(cx-25.,0.,gz+75.),50.))]
    for name,x0 in (('Deep_Rut',12000.),('Deep_Rut_Low',12000.),('Exit',19700.),('Grass',19000.)):
        bx,by=x0+250.,-100.;bz=surface_z(bx,by)
        v.append((name,2,(u.Vector(bx-220.,by+260.,bz+(190. if 'Low' not in name else 165.)),u.Vector(bx,by,bz-5.),45.)))
    v=v[:25]
    d=[('Dump_Car','car',(u.Vector(cx-25.,640.,gz+110.),u.Vector(cx-25.,0.,gz+75.),50.)),('Dump_Calib','calib',(u.Vector(6350.,260.,ground(6500.,260.)+200.),u.Vector(6530.,260.,ground(6500.,260.)),50.))]
    for name,x0 in (('Firm',3000.),('Standard',7500.),('Deep',12000.),('Stony',16500.)):
        mid=x0+1250.;ry=-90.;g=surface_z(mid,ry)
        d.append(('Dump_'+name,'ground',(u.Vector(mid-150.,ry+40.,g+220.),u.Vector(mid+20.,ry,g),50.)))
    return v,d
def written(path):
    return path.exists() and path.stat().st_mtime>=run.get('shot_t',0.)
def b_tick(now):
    global phase,last,pending
    if phase=='b_start':
        place_car(21200.,0.);phase='b_settle';last=now
    elif phase=='b_settle' and settled(now,last):
        move.set_brake_input(0.);run['views'],run['dumps']=b_views();phase='b_warm';last=now
    elif phase=='b_warm' and now-last>20.:
        mem_log('B_start',top=True);run['k']=0;phase='b_shot';last=now
    elif phase=='b_shot' and now-last>(8. if B_KIND=='move' else 3.5) and (not run.get('last') or written(run['last']) or now-last>30.):
        if run.get('last'):mem_log('B_shot%02d_%s'%(run['k'],run['last'].stem))
        elif run.get('move_wait'):mem_log('B_move%02d'%run['k'])
        if not run['views'] and B_KIND in ('move','still'):
            run['hold']=now;phase='b_hold';last=now;return
        if not run['views']:
            console('gt.Mud.POM 2');console('gt.Mud.POMShadow 1')
            console('r.BufferVisualizationOverviewTargets BaseColor,Roughness,MaterialAO');console('r.SaveEXR.CompressionQuality 0');console('r.PostProcessingColorFormat 1')
            run['last']=None;run['k']=0;phase='b_dump';last=now;return
        name,pom,(cpos,ctarget,fov)=run['views'].pop(0);run['k']+=1
        console('gt.Mud.POM %d'%abs(pom));console('gt.Mud.POMShadow %d'%(0 if pom<0 else 1))
        car.set_actor_hidden_in_game(not name.startswith('Car_'))
        if B_KIND=='still':cpos,ctarget,fov=run.setdefault('still_view',(cpos,ctarget,fov))
        aim_camera(cpos,ctarget,fov);run['shot_t']=time.time();path=OUT/('%s.png'%name);run['last']=path;last=now
        if B_KIND=='move':run['last']=None;run['move_wait']=now   # no capture: the same 1.5 s + 10 frames, then the next mark
        else:pending=(now+1.5,FRAME+10,path,False)
    elif phase=='b_dump' and now-last>3.5 and (not run.get('last') or written(run['last']) or now-last>30.):
        if run.get('last'):mem_log('B_dump%d_%s'%(run['k'],run['last'].stem.replace('_MaterialAO','')))
        if not run['dumps']:
            console('r.PostProcessingColorFormat 0');run['hold']=now;phase='b_hold';last=now;return
        name,kind,(cpos,ctarget,fov)=run['dumps'].pop(0);run['k']+=1
        car.set_actor_hidden_in_game(kind!='car');aim_camera(cpos,ctarget,fov);run['shot_t']=time.time()
        run['last']=OUT/(name+'_MaterialAO.exr');pending=(now+1.5,FRAME+10,OUT/(name+'.png'),True);last=now
    elif phase=='b_hold' and now-run['hold']>60.:
        mem_log('B_end',top=True);phase='b_done';last=now
    elif phase=='b_done' and now-last>5.:
        finish()
# ---- modes A and C: the drive repeated --------------------------------------------------------------------------------------
def drive_tick(now):
    global phase,last,next_log
    if phase=='d_start':
        mem_log('%s_start'%MODE,top=True);next_log=now+LOG_S;run['leg_from']=START_X;place_car(START_X,0.);phase='d_settle';last=now
    elif phase=='d_settle' and settled(now,last):
        pc.set_view_target_with_blend(car,0.);car.reset_driving_inputs();move.set_handbrake_input(False);move.set_target_gear(1,True)
        run['leg_t']=now;run['stop_since']=None;phase='d_drive';last=now
    elif phase=='d_drive':
        pos,speed=drive_step(0.)
        stopped=speed<STOP_MPS and now-run['leg_t']>5.
        run['stop_since']=(run['stop_since'] or now) if stopped else None
        end=None
        if pos.x>=LAP_X:end='lap'
        elif run['stop_since'] and now-run['stop_since']>=STALL_S:end='stall'
        elif now-run['leg_t']>=LEG_CAP_S:end='cap'
        if end:
            report['laps'].append(dict(t_s=round(now-play0,1),from_m=round(run['leg_from']/100.,1),end_m=round(pos.x/100.,1),ended=end))
            move.set_throttle_input(0.)
            # A stalled leg goes on 2 m before the next section (as the check's scripted pass), past the last one to the exit gravel.
            nxt=START_X if end=='lap' else next((s-200. for s in SECTION_STARTS if s-200.>pos.x),LAP_X-1500. if pos.x<LAP_X-1500. else START_X)
            run['leg_from']=nxt;place_car(nxt,0.);phase='d_settle';last=now
    if next_log and now>=next_log and phase!='finished':
        next_log=now+LOG_S
        if now-play0>=MINUTES*60.:
            mem_log('%s_end'%MODE,top=True);phase='d_done';last=now;next_log=None
        else:mem_log('%s_%04ds'%(MODE,int(now-play0)))
    if phase=='d_done' and now-last>5.:
        finish()
def tick(dt):
    global phase,last,world,car,move,pc,camera,mud,weather,paint,splats,play0,pending,FRAME,hold_until
    now=time.monotonic()
    try:
        FRAME+=1
        if PACE and world is not None:gpu_pace()
        if phase not in ('load','loaded','warm','restart','finished') and weather is not None:weather.set_wetness_for_test(0.)
        if pending and now>=pending[0] and FRAME>=pending[1]:
            _t,_f,path,dump=pending;pending=None;hold_until=FRAME+3
            console('HighResShot %dx%d%s filename="%s"'%(VIEW[0],VIEW[1],' 0 0 0 0 0 1 1' if dump else '',path.as_posix()))
        if now-start>5400:finish('soak timed out');return
        if pending or FRAME<hold_until:return
        if phase=='load':
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL);phase='loaded';last=now
        elif phase=='loaded' and now-last>6:
            report['play_mode']=begin_play();phase='warm';last=now
        elif phase=='restart' and now-last>5:
            report['play_mode_retry']=begin_play();phase='warm';last=now
        elif phase=='warm' and now-last>15:
            world=u.EditorLevelLibrary.get_game_world()
            if world is None:
                if now-last>40:raise RuntimeError('Play In Editor did not start')
                return
            cars=u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn);assert cars,'Automation car missing';car=cars[0]
            move=car.get_chaos_movement();pc=u.GameplayStatics.get_player_controller(world,0)
            if pc:pc.possess(car);car.disable_input(pc)
            size=list(pc.get_viewport_size())
            if str(report.get('play_mode','')).startswith('new window') and size[0]!=VIEW[0] and 'viewport_retry' not in report:
                report['viewport_retry']=size;u.EditorLevelLibrary.editor_end_play();phase='restart';last=now;return
            report['viewport_size']=size
            car.reset_driving_inputs();car.set_chase_camera(False);car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
            mud=next((o for o in u.ObjectIterator(u.GTMudSubsystem) if o.get_outer()==world),None)
            weather=next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==world)
            clear=weather.find_state('Clear')
            if clear:weather.set_state(clear,True)
            weather.set_wetness_for_test(0.)
            paint=next((o for o in u.ObjectIterator(u.GTTrackPaintSubsystem) if o.get_outer()==world),None)
            splats=next((o for o in u.ObjectIterator(u.GTMudSplatSubsystem) if o.get_outer()==world),None)
            camera=next((a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Live_Overview'),None)
            # GT_SOAK_NORAINCAPTURE=1: the weather's rain emitter ticks no more (its occlusion SceneCapture, re-centred on the camera,
            # is not drawn; the weather is Clear, so no drops are lost) - a bisect of what renders at a camera jump.
            if os.environ.get('GT_SOAK_NORAINCAPTURE'):
                ems=u.GameplayStatics.get_all_actors_of_class(world,u.GTRainEmitter)
                for a in ems:a.set_actor_tick_enabled(False)
                report['rain_capture_off']=len(ems)
            for s in OFF:console('%s 0'%s)
            for c in CMDS:console(c)
            play0=now;phase='b_start' if MODE=='B' else 'd_start';last=now
        elif phase.startswith('b_'):
            b_tick(now)
        elif phase.startswith('d_'):
            drive_tick(now)
    except Exception:finish(traceback.format_exc())
def k_tick(dt):
    # Mode K: only the logger; the check drives everything (its own callback) and quits the editor at its end.
    global world,pc,next_log,play0
    now=time.monotonic()
    try:
        # No gpu_pace here: the check paces every tick itself (GT_CHECK_PACE), so a second wait would add nothing.
        gw=u.EditorLevelLibrary.get_game_world()
        if gw is not None and world is None:
            world=gw;pc=u.GameplayStatics.get_player_controller(world,0);play0=now;next_log=now+5.;return
        if gw is None:world=pc=None
        if next_log and now>=next_log and world is not None:
            first=not report['marks'];next_log=now+LOG_S;mem_log('K_start' if first else 'K_%04ds'%int(now-play0),top=first)
    except Exception:u.log_warning('soak_vram K logger: '+traceback.format_exc(limit=2))
if MODE=='K':
    # The check verbatim (its pictures and report into Saved/SoakVRAM/K, not the committed Art/Export/MudVariants), with the logger
    # beside it every GT_SOAK_LOG_S seconds (15 by default here).
    if 'GT_SOAK_LOG_S' not in os.environ:LOG_S=15.
    handle=u.register_slate_post_tick_callback(k_tick)
    CHECK=ROOT/'Art/Unreal/check_mud_variants.py';src=CHECK.read_text()
    assert "OUT=ROOT/'Art/Export/MudVariants'" in src
    src=src.replace("OUT=ROOT/'Art/Export/MudVariants'","OUT=ROOT/'Saved/SoakVRAM/K'")
    exec(compile(src,str(CHECK),'exec'),{'__name__':'__main__','__file__':str(CHECK)})
else:
    handle=u.register_slate_post_tick_callback(tick)
