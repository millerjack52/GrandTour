import unreal as u,sys,traceback
sys.path.insert(0,u.Paths.project_dir()+'/Art/Unreal')
try:
 import inspect_water_live
except Exception:
 u.log_error(traceback.format_exc())
u.SystemLibrary.quit_editor()
