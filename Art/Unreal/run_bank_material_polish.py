"""Single owned editor job; always exits, recording failure separately."""
import unreal as u,sys,json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
QA=ROOT/'Saved/LidarAuthoringQA/VP2Materials'
request=json.loads((QA/'request.json').read_text());loaded=False;settle=0;busy=False
def tick(dt):
    global loaded,settle,busy
    if busy:return
    busy=True
    try:
        if not loaded:
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
            loaded=True;settle=time.monotonic()+3;return
        if time.monotonic()<settle:return
        import lidar_bank_material_polish as polish
        result=polish.run(request['mode'])
        (QA/'job-result.json').write_text(json.dumps(result,indent=2))
        u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    except Exception:
        (QA/'job-result.json').write_text(json.dumps(dict(ok=False,error=traceback.format_exc()),indent=2))
        u.log_error(traceback.format_exc());u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
