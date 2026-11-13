"""Review-owned water optics/motion, repeatable stills and a same-view GPU ABBA check."""
import unreal as u
import sys,json,time,traceback,csv,statistics,math
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'
CSV=ROOT/'Saved/Profiling/CSV';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_domain_material import make,DEST
report={'ok':False,'images':[],'runs':[],'driving_tested':False}
skip_timings='-GTWaterAppearanceNoTimings' in u.SystemLibrary.get_command_line()
world=pc=None;mats=[];busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True)

def set_look(value,phase=-1):
    for m in mats:
        m.set_scalar_parameter_value('WaterTurbidity',value)
        m.set_scalar_parameter_value('SurfaceMotion',value)
        m.set_scalar_parameter_value('WaterTimeOverride',phase)

def bind(sheet):
    components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]
    components += [a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
    found=[c.get_material(0) for c in components]
    assert all(isinstance(m,u.MaterialInstanceDynamic) for m in found)
    return found

def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)

def analyse(path):
    with path.open(newline='') as f: rows=list(csv.reader(f))
    cols={k:[] for k in rows[0]}
    for row in rows[1:]:
        if not row or row[0].startswith('['):break
        for k,v in zip(cols,row):
            try:cols[k].append(float(v))
            except ValueError:pass
    keys=['FrameTime','GPUTime','GameThreadTime','GPU/SingleLayerWater','GPU/SingleLayerWaterDepthPrepass','GPU/LumenSceneUpdate','GTWater/GameThread/DomainTick']
    return {k:{'median':statistics.median(v),'p95':sorted(v)[min(len(v)-1,math.ceil(.95*len(v))-1)],'max':max(v),'samples':len(v)} for k,v in cols.items() if k in keys and v}

def run():
    global world,pc,mats
    les=u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert les.load_level(LEVEL)
    for kind in ['River','Lake']:
        path=DEST+'/M_RS_Domain'+kind
        if not u.EditorAssetLibrary.does_asset_exist(path+'_BeforeTurbidity'):
            assert u.EditorAssetLibrary.duplicate_asset(path,path+'_BeforeTurbidity')
        make(kind)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    sheet=next(a for a in actors if a.get_actor_label()=='Benmore_RS_WaterDomain')
    camera=next(a for a in actors if a.get_actor_label()=='Benmore_RL_Camera_Ford')
    for name,position,target,focus in [
        ('Ford',(-65550,17800,1780),(-66125,17750,1585),(-66125,17750)),
        ('Upstream',(-39425,42375,5296),(-40625,43875,4955),(-40625,43875)),
        ('Lake',(-166150,-3100,330),(-166800,-2700,60),(-166800,-2700))]:
        sheet.preview_water_at(u.Vector2D(*focus),0,True);mats=bind(sheet)
        camera.set_actor_location(u.Vector(*position),False,False)
        camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*position),u.Vector(*target)),False)
        # Prime the viewport at this camera before the comparison; grass streaming
        # otherwise visibly filled in between the first pair despite fixed water time.
        u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
        yield 35 if name=='Ford' else 15
        phases=[('Before',0,12),('After',1,12)]
        # Sample the material clock at 8 fps to review transported highlights; the
        # river mean/vehicle physics are deliberately held fixed in this editor preview.
        if name=='Ford':phases += [('Motion%02d'%i,1,12+i/8) for i in range(1,16)]
        for suffix,value,phase in phases:
            set_look(value,phase);yield 1 if suffix.startswith('Motion') else 3
            path=OUT/('Appearance_'+name+'_'+suffix+'.png')
            requested=time.time()
            task=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),camera)
            yield 2
            while not path.exists() or path.stat().st_mtime<requested:
                if time.time()-requested>45:raise RuntimeError('Screenshot did not finish: '+str(path))
                yield 1
            report['images'].append(str(path))
    set_look(1,-1)
    report['defaults']={'WaterTurbidity':1,'SurfaceMotion':1,'WaterTimeOverride':-1}
    # Saved masters carry the final defaults; transient camera/preview field are not saved.
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    report['reloaded']=True
    if skip_timings:
        report['timing_note']='Timing skipped by request because other GPU workloads are active.'
        report['ok']=True
        return
    ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    ew.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 20
    world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);assert world and pc
    report['viewport']=list(pc.get_viewport_size())
    for s in ['t.MaxFPS 0','r.VSync 0','r.ScreenPercentage 100','r.DynamicRes.OperationMode 0','gt.Look.Weather Clear']:cmd(s)
    sheet=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if a.get_editor_property('water_domain'))
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Benmore_RL_Camera_Ford')
    pawn.set_actor_location(u.Vector(-66125,17750,1700),False,True)
    p=u.Vector(-65550,17800,1780);target=u.Vector(-66125,17750,1585)
    camera.set_actor_location(p,False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(p,target),False)
    pc.set_view_target_with_blend(camera,0);yield 25
    mats=bind(sheet)
    report['live_defaults']={k:mats[0].get_scalar_parameter_value(k) for k in report['defaults']}
    assert report['live_defaults']==report['defaults']
    for value in [0,1,1,0]:
        set_look(value);yield 4
        before=set(CSV.glob('*.csv'));cmd('csvprofile start');yield 8;cmd('csvprofile stop');yield 3
        paths=set(CSV.glob('*.csv'))-before;assert len(paths)==1
        path=paths.pop();report['runs'].append({'new_look':value,'csv':str(path),'times':analyse(path)})
    set_look(1,-1);report['ok']=True

def finish(error=None):
    global gen
    gen=None
    if error:report['ok']=False;report['error']=error;u.log_error(error)
    report['timings_valid']=report['ok'] and not skip_timings and not (OUT/'appearance-external-load.json').exists()
    (OUT/'appearance-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle)
    if pc:u.EditorLevelLibrary.editor_end_play()
    u.SystemLibrary.quit_editor()

gen=run();next_at=time.monotonic();started=next_at
def tick(dt):
    global next_at,busy
    if busy:return
    try:
        if time.monotonic()-started>440:raise RuntimeError('Water appearance validation timeout')
        if time.monotonic()<next_at:return
        busy=True;next_at=time.monotonic()+next(gen)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
handle=u.register_slate_post_tick_callback(tick)
