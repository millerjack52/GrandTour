"""Reversible first rendering budget pass; no FPS or simulation claims.

Preserves native heights, instances, collision and shared assets. Screenshots
are taken before/after from the same camera; no profiling runs here.
"""
import unreal as u
import json,sys,time,traceback,array,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_water_budget as water
import benmore_terrain_budget as terrain
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeRenderBudget'
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);eal=u.EditorAssetLibrary
phase='load';last=time.monotonic();started=last;index=0
report={'ok':False,'timings_collected':False,'simulation_installed':False,'changes':[],'images':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)

def signature():
    h=hashlib.sha256();count=0
    for a in sorted(act.get_all_level_actors(),key=lambda a:a.get_actor_label()):
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(c,u.GrassInstancedStaticMeshComponent):continue
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True);h.update(array.array('d',[*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()]).tobytes());count+=1
    return {'instances':count,'sha256':h.hexdigest()}

def apply():
    # Clone the water masters; the backup map continues to use the original ones.
    stream=water.make_stream();lake=water.make_lake();ground=terrain.make_terrain()
    for a in act.get_all_level_actors():
        label=a.get_actor_label()
        if isinstance(a,u.LandscapeProxy):
            old=a.get_editor_property('landscape_material')
            assert old.get_name() in ['M_RL_Terrain','M_RS_Terrain'];a.set_editor_property('landscape_material',ground)
            report['changes'].append({'actor':label,'material_before':old.get_path_name(),'material_after':ground.get_path_name()})
        for c in a.get_components_by_class(u.StaticMeshComponent):
            for i in range(c.get_num_materials()):
                m=c.get_material(i)
                if m and m.get_name() in ['M_RL_Stream','M_RL_Lake']:
                    new=stream if m.get_name()=='M_RL_Stream' else lake;c.set_material(i,new)
                    report['changes'].append({'actor':label,'material_before':m.get_path_name(),'material_after':new.get_path_name()})
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            # Only tiny RiverLife gravel is over-budget by confirmed setup values.
            # Existing road gravel already culls at 70-110 m and stays unchanged.
            if label.startswith('Benmore_RL_gravel_'):
                before=[c.get_editor_property('instance_start_cull_distance'),c.get_editor_property('instance_end_cull_distance')]
                c.set_cull_distances(5000,11000);c.set_editor_property('visible_in_ray_tracing',False)
                report['changes'].append({'actor':label,'instances':c.get_instance_count(),'cull_before_cm':before,'cull_after_cm':[5000,11000],'ray_tracing':False})
    after=signature();assert after==report['instance_signature_before'];report['instance_signature_after']=after
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL)

def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'budget-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

def tick(dt):
    global phase,last,index,cameras,task
    try:
        now=time.monotonic()
        if now-started>1200:raise RuntimeError('Bounded rendering review timeout')
        if phase=='load':
            phase='loading';assert les.load_level(LEVEL)
            if not eal.does_asset_exist(BACKUP):assert eal.duplicate_asset(LEVEL,BACKUP)
            report['backup']=BACKUP;report['instance_signature_before']=signature()
            cameras=[next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RL_Camera_'+name) for name in ['Ford','Long_Vista']]
            report['pass']='Before';phase='view'
        elif phase=='view':
            phase='moving';c=cameras[index];u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(c.get_actor_location(),c.get_actor_rotation());phase='warm';last=now
        elif phase=='warm' and now-last>35:
            phase='capturing'
            name=report['pass']+'_'+['Ford','Long_Vista'][index]+'.png';path=OUT/name
            task=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),cameras[index]);report['images'].append(str(path));phase='shot';last=now
        elif phase=='shot' and now-last>5:
            assert Path(report['images'][-1]).exists();index+=1
            if index<len(cameras):phase='view'
            elif report['pass']=='Before':
                phase='applying';apply();index=0;report['pass']='After';phase='view'
            else:
                phase='verifying';assert les.load_level(LEVEL);assert signature()==report['instance_signature_before'];report['saved_and_reloaded']=True;finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
