"""One-world editor preview workstation for the bounded RS6 authoring pass."""
import unreal as u
import sys,time,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
QA=ROOT/'Saved/LidarAuthoringQA/RS6';QA.mkdir(parents=True,exist_ok=True)
les=u.get_editor_subsystem(u.LevelEditorSubsystem)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
busy=False;loaded=False;began=time.monotonic()
def tick(dt):
 global busy,loaded
 if busy:return
 busy=True
 try:
  if not loaded:
   assert les.load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
   loaded=True;les.editor_set_viewport_realtime(False);les.editor_set_viewport_realtime(True)
   (QA/'ready.json').write_text(json.dumps({'ready':True}))
  job=QA/'job.py'
  if job.exists():
   code=job.read_text();job.unlink()
   exec(compile(code,str(job),'exec'),globals())
   (QA/'job-result.json').write_text(json.dumps({'ok':True,'time':time.time()}))
  if time.monotonic()-began>2700:
   u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  (QA/'job-result.json').write_text(json.dumps({'ok':False,'error':traceback.format_exc(),'time':time.time()}))
  u.log_error(traceback.format_exc())
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
