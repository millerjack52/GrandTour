"""Material-only detail revision, with fixed-time editor wake captures and binding audit."""
import unreal as u
import sys,json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_domain_material import make
report={'ok':False,'images':[],'driving_tested':False}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def run():
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
    make('River');make('Lake')
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    sheet=next(a for a in actors if a.get_actor_label()=='Benmore_RS_WaterDomain')
    camera=next(a for a in actors if a.get_actor_label()=='Benmore_RL_Camera_Ford')
    p=u.Vector(-65550,17800,1780);target=u.Vector(-66125,17750,1585);focus=u.Vector2D(-66125,17750)
    camera.set_actor_location(p,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(p,target),False)
    for name,delay in [('Rest',-1),('Wake',0),('Wake4s',4)]:
        sheet.preview_water_at(focus,0,True)
        if delay>=0:
            sheet.preview_water_wake(u.Vector2D(focus.x-300,focus.y),u.Vector2D(focus.x+300,focus.y),3)
            if delay:sheet.preview_water_at(focus,delay,False)
        if name=='Rest':
            c=sheet.get_component_by_class(u.ProceduralMeshComponent);m=c.get_material(0)
            report['binding']={'component':c.get_name(),'location':list(c.get_world_location().to_tuple()),'visible':c.is_visible(),
                'material':m.get_path_name(),'local':m.get_scalar_parameter_value('LocalSurface'),'active':m.get_scalar_parameter_value('FieldActive'),
                'foam_gain':m.get_scalar_parameter_value('FoamGain'),'sediment_gain':m.get_scalar_parameter_value('SedimentGain'),
                'detail_texture':m.get_texture_parameter_value('DetailTex').get_name()}
        yield 18
        path=OUT/('Detail_'+name+'.png');u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),camera);yield 3
        assert path.exists();report['images'].append(str(path))
    report['ok']=True
def finish(error=None):
    if error:report['error']=error;u.log_error(error)
    (OUT/'detail-polish-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
gen=run();next_at=time.monotonic();started=next_at;busy=False
def tick(dt):
    global next_at,busy
    if busy:return
    try:
        if time.monotonic()-started>350:raise RuntimeError('Detail polish timeout')
        if time.monotonic()<next_at:return
        busy=True
        next_at=time.monotonic()+next(gen)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
handle=u.register_slate_post_tick_callback(tick)
