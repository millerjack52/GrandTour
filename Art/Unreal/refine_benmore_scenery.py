"""Increase mature willow scale and remove bright moss from the rock palette."""
import unreal as u,json,sys,traceback,time,math
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreScenery'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_rock_materials import configure,DEST
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
phase='load';last=time.monotonic();report={'ok':False,'tree_heights_m':{},'rock_materials':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'refinement-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='working';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
            placements=json.loads((OUT/'placements.json').read_text())
            actors={a.get_actor_label():a for a in act.get_all_level_actors()}
            for i,row in enumerate(placements['trees']):
                a=actors['Benmore_Scenery_trees_'+str(i).zfill(3)];mesh=a.static_mesh_component.get_editor_property('static_mesh');b=mesh.get_bounds();s=row['scale']
                # Include an off-centre crown when checking the road margin.
                radius=(max(b.box_extent.x,b.box_extent.y)+math.hypot(b.origin.x,b.origin.y))*s/100
                assert row['road_clearance_m']>radius+3,(i,radius,row['road_clearance_m'])
                a.set_actor_scale3d(u.Vector(s,s,s));report['tree_heights_m'].setdefault(row['variant'],[]).append(2*b.box_extent.z*s/100)
            for kind in [1,2,3]:report['rock_materials'].append(configure(u.load_asset(DEST+'/SM_Benmore_Rock'+str(kind)),kind))
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>12:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
