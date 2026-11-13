"""Stationary PIE water and rendering checks; no vehicle-driving claim."""
import unreal as u
import time,json,traceback,csv,statistics,math
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'
CSV=ROOT/'Saved/Profiling/CSV';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
report={'ok':False,'driving_tested':False,'runs':[]};world=pc=None
u.EditorPythonScripting.set_keep_python_script_alive(True)
def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)
def analyse(p):
    with p.open(newline='') as f:rows=list(csv.reader(f))
    cols={k:[] for k in rows[0]}
    for row in rows[1:]:
        if not row or row[0].startswith('['):break
        for k,v in zip(cols,row):
            try:cols[k].append(float(v))
            except ValueError:pass
    return {k:{'median':statistics.median(v),'p95':sorted(v)[min(len(v)-1,math.ceil(.95*len(v))-1)],'max':max(v),'samples':len(v)} for k,v in cols.items() if v and (k in ['FrameTime','GameThreadTime','RenderThreadTime','GPUTime','GPU/SingleLayerWater','GPU/SingleLayerWaterDepthPrepass','GPU/LumenSceneUpdate'] or k.startswith('GTWater/'))}

def run():
    global world,pc
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
    ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();ew.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 20
    world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);assert world and pc
    report['viewport']=list(pc.get_viewport_size());assert report['viewport'][0]>=640 and report['viewport'][1]>=480
    for c in ['t.MaxFPS 0','r.VSync 0','r.ScreenPercentage 100','r.DynamicRes.OperationMode 0','gt.Look.Weather Clear']:cmd(c)
    sheets=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)
    sheet=next(a for a in sheets if a.get_editor_property('water_domain'))
    cameras=u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor);cam=next(c for c in cameras if c.get_actor_label()=='Benmore_RL_Camera_Ford')
    pawn=u.GameplayStatics.get_player_pawn(world,0);assert pawn
    for name,focus,position,target in [
        ('Ford',(-66125,17750,1700),(-65550,17800,1780),(-66125,17750,1585)),
        ('Lake',(-166800,-2700,170),(-166150,-3100,330),(-166800,-2700,60)),
        ('OpenLake',(-378800,-162700,170),(-378150,-163100,330),(-378800,-162700,60))]:
        pawn.set_actor_location(u.Vector(*focus),False,True)
        cam.set_actor_location(u.Vector(*position),False,True);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*position),u.Vector(*target)),False);pc.set_view_target_with_blend(cam,0)
        yield 35
        xy=u.Vector2D(*focus[:2]);assert sheet.covers(xy)
        mean=sheet.surface_cm_at(xy);added=sheet.add_impulse(xy,180,6)
        yield .25
        displaced=sheet.surface_cm_at(xy)
        report['runs'].append({'name':name,'mean_cm':mean,'disturbed_cm':displaced,'added_m3':added})
        assert added>0 and abs(displaced-mean)>.005
        yield 10
        sheet.water_diagnostics(True);before=set(CSV.glob('*.csv'));cmd('csvprofile start');yield 8;cmd('csvprofile stop');yield 3
        new=set(CSV.glob('*.csv'))-before;assert len(new)==1
        p=new.pop();report['runs'][-1].update(csv=str(p),render_ms=analyse(p),water_stats=sheet.water_diagnostics(True))
    # Same fully wet lake view, ABBA for the incremental cosmetic field. Water physics and all
    # scene settings stay enabled; this comparison does not isolate total water cost.
    report['detail_abba']=[]
    for enabled in [1,0,0,1]:
        cmd('gt.Water.Domain.Detail '+str(enabled));yield 3
        before=set(CSV.glob('*.csv'));cmd('csvprofile start');yield 6;cmd('csvprofile stop');yield 2
        new=set(CSV.glob('*.csv'))-before;assert len(new)==1
        p=new.pop();report['detail_abba'].append({'enabled':enabled,'csv':str(p),'times':analyse(p)})
    cmd('gt.Water.Domain.Detail 1')
    # Rebuild/handoff cost is not present in the parked samples. Move an immersed
    # focus in aligned 10 m increments; this measures window shifts, not vehicle forces.
    before=set(CSV.glob('*.csv'));cmd('csvprofile start')
    for i in range(1,17):
        x=-378800+i*1000
        pawn.set_actor_location(u.Vector(x,-162700,170),False,True)
        cam.set_actor_location(u.Vector(x+650,-163100,330),False,True)
        yield .5
    cmd('csvprofile stop');yield 2
    new=set(CSV.glob('*.csv'))-before;assert len(new)==1
    p=new.pop();report['moving_window']={'shift_count':16,'spacing_m':10,'seconds_between_shifts':.5,'csv':str(p),'times':analyse(p),'driving_tested':False}
    report['ok']=True

def finish(error=None):
    global gen
    gen=None
    if error:report['ok']=False;report['error']=error;u.log_error(error)
    if (OUT/'domain-runtime-external-load.json').exists():report['timings_valid']=False
    else:report['timings_valid']=report['ok']
    (OUT/'domain-runtime-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
gen=run();next_at=time.monotonic();started=next_at;busy=False
def tick(dt):
    global next_at,busy
    if busy:return
    try:
        if time.monotonic()-started>400:raise RuntimeError('Runtime validation timeout')
        if time.monotonic()<next_at:return
        busy=True
        next_at=time.monotonic()+next(gen)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
handle=u.register_slate_post_tick_callback(tick)
