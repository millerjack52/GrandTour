"""Ground relief GR1b item 1 (docs/GROUND_RELIEF_PLAN.md): what draws the dark lines along the old ruts. L_MudVariants in Play In
Editor, the Relief_Bog camera (Art/Export/GroundRelief/pictures-after.json), one picture per suspect switched off:
- in one session: as built; gt.Mud.POMShadow 0; gt.Mud.POM 0; the patch meshes cast no shadow; screen-space AO off;
- one session each (read at Init): gt.Mud.PreChurnDebug 1 (the tracks factor cleared), 2 (the field smoothed), 4 (lumps cleared);
and (item 2) a picture straight down on the road between Standard's and Deep's patch boxes (x 106.8-113.2 m), where the pale
rectangle is. Writes Art/Export/GroundRelief/CreaseDebug/*.png and crease-debug.json. No timing."""
import unreal as u,json,time,traceback,os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/GroundRelief'/(os.environ.get('GT_CREASE_OUT','').strip() or 'CreaseDebug');OUT.mkdir(parents=True,exist_ok=True)
LEVEL='/Game/GrandTour/ArtTests/MudVariants/L_MudVariants';SPEC='/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants'
VIEW=(1440,900)
cams=json.loads((ROOT/'Art/Export/GroundRelief/pictures-after.json').read_text())
BOG=next(s for s in cams['strips'] if s['strip']=='MudVariants')['cameras']['Relief_Bog']
SESSIONS=[(0,[('Crease_Base',[]),('Crease_POMShadow0',['gt.Mud.POMShadow 0']),('Crease_POM0',['gt.Mud.POMShadow 1','gt.Mud.POM 0']),
              ('Crease_NoMeshShadow',['gt.Mud.POM 2','MESHSHADOW 0']),('Crease_NoAO',['MESHSHADOW 1','r.AmbientOcclusionLevels 0']),
              ('Gap_TopDown',['r.AmbientOcclusionLevels -1','GAP'])]),
          (1,[('Crease_Debug1_NoTracks',[])]),(2,[('Crease_Debug2_Smoothed',[])]),(4,[('Crease_Debug4_NoLumps',[])])]
report={'ok':False,'images':[],'sessions':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
idx=0;phase='load';last=time.monotonic();start=last;world=pc=camera=None;queue=[];pending=None;FRAME=0;BUSY=False
def console(cmd,w=None,p=None):u.SystemLibrary.execute_console_command(w or world,cmd,p or pc)
def ground(x,y):return u.GTVehicleSetupLibrary.sample_terrain_height_cm(u.load_asset(SPEC).spec,x,y)
def finish(err=None):
    global phase
    phase='done'
    if err:report['error']=err
    (OUT/'crease-debug.json').write_text(json.dumps(report,indent=2))
    try:u.unregister_slate_post_tick_callback(handle)
    except Exception:pass
    try:u.EditorLevelLibrary.editor_end_play()
    except Exception:pass
    u.SystemLibrary.quit_editor()
def tick(dt):
    global BUSY
    if BUSY:return
    BUSY=True
    try:body()
    except Exception:finish(traceback.format_exc())
    finally:BUSY=False
def body():
    global idx,phase,last,world,pc,camera,pending,FRAME
    now=time.monotonic();FRAME+=1
    if now-start>3600:finish('timed out');return
    if pending and now>=pending[0] and FRAME>=pending[2]:
        console('HighResShot %dx%d filename="%s"'%(VIEW[0],VIEW[1],pending[1].as_posix()));pending=None;last=now;return
    if pending:return
    if phase=='load':
        assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL);phase='next';last=now
    elif phase=='next' and now-last>5:
        if idx>=len(SESSIONS):report['ok']=True;finish();return
        debug,_=SESSIONS[idx]
        ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        u.SystemLibrary.execute_console_command(ew,'gt.Mud.PreChurnDebug %d'%debug)
        lib=getattr(u,'GTPlayWindowLibrary',None)
        if not(lib and lib.request_play_in_new_window(VIEW[0],VIEW[1])):u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
        phase='warm';last=now
    elif phase=='warm' and now-last>20:
        world=u.EditorLevelLibrary.get_game_world()
        if world is None:
            if now-last>90:raise RuntimeError('PIE did not start')
            return
        pc=u.GameplayStatics.get_player_controller(world,0)
        camera=u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor)[0]
        weather=next((o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==world),None)
        if weather:
            clear=weather.find_state('Clear')
            if clear:weather.set_state(clear,True)
            weather.set_wetness_for_test(0.)
        for car in u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn):car.set_actor_location(u.Vector(-1500,0,ground(-1500,0)+150),False,True)
        patches=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch)
        report['sessions'].append(dict(debug=SESSIONS[idx][0],prechurn=[json.loads(p.describe_pre_churn()) for p in patches]))
        for name,cmds in SESSIONS[idx][1]:queue.append((name,cmds))
        phase='shots';last=now
    elif phase=='shots' and now-last>3:
        if not queue:
            u.EditorLevelLibrary.editor_end_play();idx+=1;phase='next';last=now+3;return
        name,cmds=queue.pop(0)
        for c in cmds:
            if c.startswith('MESHSHADOW'):
                on=c.endswith('1')
                for p in u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch):
                    for comp in p.get_components_by_class(u.ProceduralMeshComponent):comp.set_cast_shadow(on)
            elif c!='GAP':console(c)
        if 'GAP' in cmds:
            eye=u.Vector(11000.,0.,ground(11000.,0.)+1600.);look=u.Vector(11000.,1.,ground(11000.,0.));fov=70.
        else:
            e=BOG['eye_m'];l=BOG['look_m'];eye=u.Vector(e[0]*100,e[1]*100,e[2]*100);look=u.Vector(l[0]*100,l[1]*100,l[2]*100);fov=BOG['fov']
        camera.set_actor_location(eye,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(eye,look),False)
        camera.camera_component.set_field_of_view(fov);pc.set_view_target_with_blend(camera,0.)
        path=OUT/(name+'.png');report['images'].append(str(path));pending=(now+3.,path,FRAME+15)
handle=u.register_slate_post_tick_callback(tick)
