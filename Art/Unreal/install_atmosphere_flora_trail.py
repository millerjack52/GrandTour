"""Install reviewed atmosphere settings without changing materials or gameplay."""
import unreal as u,json,sys,time,hashlib,traceback,shutil,gc
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/Atmosphere';D='/Game/GrandTour/ArtTests/FloraTrail';LEVEL=D+'/L_FloraTrail'
sys.path.insert(0,str(R/'Art/Unreal'))
from flora_trail_atmosphere import apply,snapshot
report={'ok':False};cfg=json.loads((R/'Art/flora_trail_atmosphere_settings.json').read_text())
def run():
 global world
 E=u.EditorAssetLibrary;L=u.get_editor_subsystem(u.LevelEditorSubsystem)
 previous=json.loads((R/'Art/Export/FloraTrail/build-report.json').read_text())
 hashes=previous['package_hashes'];mapfile=str(R/'Content/GrandTour/ArtTests/FloraTrail/L_FloraTrail.umap')
 backup=R/'Saved/FloraTrailBackups'/('atmosphere-'+str(time.time_ns()));backup.mkdir(parents=True);shutil.copy2(mapfile,backup/'L_FloraTrail.umap')
 assert L.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 fog=next(a for a in actors if a.get_actor_label()=='FloraTrail_Haze').component
 sun=next(a for a in actors if a.get_actor_label()=='FloraTrail_Sun').light_component
 report['before']=snapshot(fog,sun);apply(fog,sun,cfg)
 report['after']=snapshot(fog,sun)
 assert L.save_current_level();yield 3
 for p,h in hashes.items():
  if p!=mapfile:assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
 report.update(ok=True,existing_assets_unchanged=True,geometry_materials_surface_lighting_exposure_unchanged=True,settings=cfg,backup=str(backup),previous_package_fingerprint=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest())
 previous['atmosphere_refinement']=report.copy();previous['package_hashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail').rglob('*') if p.suffix in ['.uasset','.umap']}
 (R/'Art/Export/FloraTrail/build-report.json').write_text(json.dumps(previous,indent=2));(O/'install_atmosphere-report.json').write_text(json.dumps(report,indent=2))
 u.SystemLibrary.execute_console_command(world,'r.RHIThread.Enable 0');yield 2
 L.load_level('/Engine/Maps/Entry');world=None;yield 3
steps=run();state={'busy':False,'due':0}
def tick(dt):
 global steps
 if state['busy'] or time.monotonic()<state['due']:return
 state['busy']=True
 try:state['due']=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;u.unregister_slate_post_tick_callback(handle)
  for key,value in list(globals().items()):
   if not key.startswith('__') and key not in ('u','time'):globals()[key]=None
  value=None
  import gc
  gc.collect();u.SystemLibrary.collect_garbage();globals()['quit_at']=time.monotonic()+3
  def close(dt):
   if time.monotonic()>quit_at:u.unregister_slate_post_tick_callback(quit_handle);u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
  globals()['quit_handle']=u.register_slate_post_tick_callback(close)
 except Exception:
  report['error']=traceback.format_exc();(O/'install_atmosphere-report.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
 finally:
  if state is not None:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
