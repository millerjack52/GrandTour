"""Verify the restored pre-RS6 map and refresh its descriptive inventory only."""
import unreal as u
from pathlib import Path
import sys,json,traceback
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_bank_planting as bank
QA=ROOT/'Saved/LidarAuthoringQA/RS6'
busy=False
def tick(dt):
 global busy
 if busy:return
 busy=True
 try:
  les=u.get_editor_subsystem(u.LevelEditorSubsystem)
  assert les.load_level(bank.BASE+'/L_LidarStudy')
  expected=json.loads((bank.QA/'install.json').read_text())
  assert bank.snapshot()==expected['snapshot']
  assert not any(a.get_actor_label().startswith('LidarStudy_RS6_') for a in bank.actors.get_all_level_actors())
  bank.inventories()
  (QA/'rollback.json').write_text(json.dumps(dict(ok=True,restored_checkpoint='RS5',snapshot_verified=True,river_inventory_refreshed=True),indent=2))
  les.load_level('/Engine/Maps/Entry')
 except Exception:
  (QA/'rollback.json').write_text(json.dumps(dict(ok=False,error=traceback.format_exc()),indent=2))
  u.log_error(traceback.format_exc())
 finally:
  u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
