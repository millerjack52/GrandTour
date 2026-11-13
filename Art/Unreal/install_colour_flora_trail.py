"""Install reviewed native foliage colour response in two local tree materials."""
import unreal as u,json,sys,time,hashlib,traceback,shutil,gc
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/TreeColour';D='/Game/GrandTour/ArtTests/FloraTrail';LEVEL=D+'/L_FloraTrail'
sys.path.insert(0,str(R/'Art/Unreal'))

report={'ok':False};cfg=json.loads((R/'Art/flora_trail_canopy_settings.json').read_text());selection=json.loads((O/'selection.json').read_text())
def run():
 global world
 E=u.EditorAssetLibrary;L=u.get_editor_subsystem(u.LevelEditorSubsystem)
 previous=json.loads((R/'Art/Export/FloraTrail/build-report.json').read_text())
 hashes=previous['package_hashes'];mapfile=str(R/'Content/GrandTour/ArtTests/FloraTrail/L_FloraTrail.umap')
 backup=R/'Saved/FloraTrailBackups'/('colour-'+str(time.time_ns()));backup.mkdir(parents=True)
 shutil.copy2(R/'Art/flora_trail_canopy_settings.json',backup/'flora_trail_canopy_settings.json')
 assert L.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 mats={};count=0
 for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if c.get_instance_count() and c.static_mesh and c.static_mesh.get_path_name().startswith(D+'/Meshes/') and c.static_mesh.get_name() in ['SM_Exact_tree','SM_Exact_pine']:
    count+=c.get_instance_count()
    for m in c.get_materials():
     if m.blend_mode==u.BlendMode.BLEND_MASKED:mats[m.get_path_name()]=m
 assert len(mats)==2 and count==340
 allowed=[];before={}
 for key,m in mats.items():
  assert key.startswith(D+'/Materials/Canopy/')
  p=R/'Content'/ (key.split('.')[0][len('/Game/'):]+'.uasset');allowed.append(str(p));shutil.copy2(p,backup/p.name)
  scalars={str(n.get_editor_property('parameter_name')):n for n in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(n,u.MaterialExpressionScalarParameter)}
  before[key]={k:scalars[k].get_editor_property('default_value') for k in ['CanopyReflectance','CanopyTransmission']}
  scalars['CanopyReflectance'].set_editor_property('default_value',selection['reflectance'])
  scalars['CanopyTransmission'].set_editor_property('default_value',selection['transmission'])
  assert not u.MaterialEditingLibrary.recompile_material(m);assert E.save_loaded_asset(m,False)
 yield 3
 for p,h in hashes.items():
  if p not in allowed:assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
 cfg.update(reflectance=selection['reflectance'],transmission=selection['transmission'])
 (R/'Art/flora_trail_canopy_settings.json').write_text(json.dumps(cfg,indent=2)+'\n')
 report.update(ok=True,trees=count,materials=list(mats),changed_packages=allowed,before=before,settings=cfg,backup=str(backup),all_other_packages_unchanged=True,geometry_masks_normals_lights_exposure_unchanged=True)
 previous['tree_colour_refinement']=report.copy();previous['package_hashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail').rglob('*') if p.suffix in ['.uasset','.umap']}
 (R/'Art/Export/FloraTrail/build-report.json').write_text(json.dumps(previous,indent=2));(O/'install_colour-report.json').write_text(json.dumps(report,indent=2))
 yield 2
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
  report['error']=traceback.format_exc();(O/'install_colour-report.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
 finally:
  if state is not None:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
