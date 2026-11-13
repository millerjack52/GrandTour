"""Bounded material/shoreline review without changing the native terrain."""
import unreal as u,json,sys,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/RiverLife';sys.path.insert(0,str(ROOT/'Art/Unreal'))
import benmore_river_life_materials as mats
import importlib
importlib.reload(mats)
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);phase='load';last=time.monotonic();report={'ok':False}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    global phase,last
    phase='await_review';last=time.monotonic();report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'polish-report.json').write_text(json.dumps(report,indent=2))
    if error:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,index,cameras,task
    try:
        now=time.monotonic()
        if phase=='load':
            phase='working';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            mats.water(u.load_asset(mats.DEST+'/T_RL_Flow'),u.load_asset(mats.DEST+'/T_RL_WaterMask'))
            rows=[]
            for a in act.get_all_level_actors():
                if not isinstance(a,u.StaticMeshActor):continue
                label=a.get_actor_label()
                if any(k in label for k in ['Mouth','Lake','Backdrop','Surface','Creek','Outlet','Stream']):
                    c=a.static_mesh_component;origin,extent=a.get_actor_bounds(False);rows.append({'label':label,'origin':list(origin.to_tuple()),'extent':list(extent.to_tuple()),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]})
            report['inventory']=rows
            assert u.EditorLoadingAndSavingUtils.save_map(world,'/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
            cameras=[next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RL_Camera_'+n) for n in ['Ford','River_Reach']]
            a=act.spawn_actor_from_class(u.CameraActor,u.Vector(-122000,-6500,1300));a.set_actor_rotation(u.MathLibrary.find_look_at_rotation(a.get_actor_location(),u.Vector(-127000,-1500,120)),False);a.camera_component.set_field_of_view(72);cameras.append(a);index=0;phase='view'
        elif phase=='view':
            c=cameras[index];u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(c.get_actor_location(),c.get_actor_rotation());phase='warm';last=now
        elif phase=='warm' and now-last>20:
            task=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(OUT/(['Ford_Polish','Reach_Polish','Mouth_Polish'][index]+'.png')),cameras[index]);phase='shot';last=now
        elif phase=='shot' and now-last>5:
            index+=1
            if index==len(cameras):finish()
            else:phase='view'
        elif phase=='await_review':
            command=OUT/'review-command.json'
            if command.exists():
                name=json.loads(command.read_text())['script'];assert name in ['polish_benmore_river_life.py','check_benmore_river_life.py','finish_benmore_river_outlet.py'];command.unlink();u.unregister_slate_post_tick_callback(handle);script=ROOT/'Art/Unreal'/name;exec(compile(script.read_text(),str(script),'exec'),{'__file__':str(script)})
            elif now-last>1200:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
