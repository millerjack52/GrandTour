"""One-world editor preview workstation for the bounded RS7 authoring pass."""
import unreal as u
import sys,time,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
QA=ROOT/'Saved/LidarAuthoringQA/RS7';QA.mkdir(parents=True,exist_ok=True)
les=u.get_editor_subsystem(u.LevelEditorSubsystem)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
busy=False;loaded=False;ready_announced=False;settle_until=0.;began=time.monotonic()
def tick(dt):
 global busy,loaded,settle_until,ready_announced
 if busy:return
 busy=True
 try:
  if not loaded:
   assert les.load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
   loaded=True;les.editor_set_viewport_realtime(False);les.editor_set_viewport_realtime(True)
   # A loaded package precedes editor-world collision registration. Allow normal
   # Slate/world ticks before running authoring or collision validation jobs.
   settle_until=time.monotonic()+2.
   return
  if time.monotonic()<settle_until:return
  if not ready_announced:
   (QA/'ready.json').write_text(json.dumps({'ready':True}));ready_announced=True
  job=QA/'job.py'
  if job.exists():
   code=job.read_text();job.unlink()
   exec(compile(code,str(job),'exec'),globals())
   (QA/'job-result.json').write_text(json.dumps({'ok':True,'time':time.time()}))
  if time.monotonic()-began>10800:
   u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  (QA/'job-result.json').write_text(json.dumps({'ok':False,'error':traceback.format_exc(),'time':time.time()}))
  u.log_error(traceback.format_exc())
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
