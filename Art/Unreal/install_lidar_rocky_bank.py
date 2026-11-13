"""Install RS6, with backup, serialized placement checks and an unchanged terrain digest."""
from pathlib import Path
import unreal as u
import sys,json,time,traceback,shutil,gc
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_rocky_bank as rocky
import lidar_bank_planting as bank
import lidar_slope_style as slopes
QA=rocky.QA;QA.mkdir(parents=True,exist_ok=True)
def save_current(placement):
 les=u.get_editor_subsystem(u.LevelEditorSubsystem)
 report=dict(ok=False,version=rocky.VERSION,placement=placement)
 report['validation']=rocky.validate(placement)
 report['snapshot']=rocky.snapshot();report['bank_snapshot']=bank.snapshot()
 report['owner_inventory']=rocky.owner_inventory()
 report['materials']=slopes.validate()
 bank.inventories()
 # Temporary preview cameras must never become part of the saved level.
 for a in rocky.actors.get_all_level_actors():
  if a.get_actor_label()=='RS6_PreviewCamera':rocky.actors.destroy_actor(a)
 assert les.save_current_level()
 (QA/'install.json').write_text(json.dumps(report,indent=2))
 return report
def verify_saved(report):
 assert rocky.snapshot()==report['snapshot'],'Serialized RS6 transforms differ'
 assert bank.snapshot()==report['bank_snapshot'],'Serialized surrounding planting differs'
 assert rocky.owner_inventory()==report['owner_inventory'],'Serialized vegetation counts differ'
 report['validation']=rocky.validate(report['placement'])
 assert slopes.validate()==report['materials'],'Terrain materials changed'
 report['map_sha256']=slopes.roads.digest(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap')
 report.update(ok=True,reloaded=True)
 (QA/'install.json').write_text(json.dumps(report,indent=2))
 (rocky.OUT/'rocky-bank.json').write_text(json.dumps(dict(version=rocky.VERSION,report=str(QA/'install.json'))))
 return report
if __name__=='__main__':
 busy=False;deadline=0;report={}
 def run():
  global report
  les=u.get_editor_subsystem(u.LevelEditorSubsystem)
  backup=ROOT/'Saved/LidarAuthoringBackups'/('RS6-'+str(time.time_ns()));backup.mkdir(parents=True)
  shutil.copy2(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',backup/'L_LidarStudy.umap')
  assert les.load_level(rocky.BASE+'/L_LidarStudy');yield 2
  placement=rocky.apply();placement['backup']=str(backup)
  report=save_current(placement);yield 2
  assert les.load_level('/Engine/Maps/Entry');gc.collect();yield 3
  assert les.load_level(rocky.BASE+'/L_LidarStudy');yield 2
  report=verify_saved(report)
  assert les.load_level('/Engine/Maps/Entry');yield 2
 steps=run();started=time.monotonic()
 def tick(dt):
  global busy,deadline
  if busy:return
  busy=True
  try:
   assert time.monotonic()-started<1000,'RS6 install timeout'
   if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
  except StopIteration:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  except Exception:
   report.update(ok=False,error=traceback.format_exc());(QA/'install.json').write_text(json.dumps(report,indent=2));u.log_error(report['error'])
   u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  finally:busy=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
