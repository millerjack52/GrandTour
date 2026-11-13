"""Promote approved source lighting to FloraTrail only, with recoverable map/settings backup."""
import unreal as u,json,sys,time,hashlib,traceback,shutil,gc
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/FloraTrail/Source34';D='/Game/GrandTour/ArtTests/FloraTrail'
sys.path.insert(0,str(R/'Art/Unreal'))
from flora_trail_source34 import install_component,configure,settings
from flora_trail_asset_audit import verify
from flora_trail_evidence import audited_fingerprint
report={'ok':False}
def run():
 global world
 L=u.get_editor_subsystem(u.LevelEditorSubsystem);E=u.EditorAssetLibrary
 report['before_fingerprint']=audited_fingerprint()
 protected=json.loads((R/'Art/Export/FloraTreeLightBench/protected-before.json').read_text())
 protected={p:h for p,h in protected.items() if '/FloraTrail/' not in p.replace('\\','/') and Path(p).name not in ['flora_trail_settings.json','flora_trail_canopy_settings.json']}
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
 backup=R/'Saved/FloraTrailBackups'/('source34-'+str(time.time_ns()));backup.mkdir(parents=True)
 for relative in ['Content/GrandTour/ArtTests/FloraTrail/L_FloraTrail.umap','Content/GrandTour/ArtTests/FloraTrail/Controls/MPC_SourceLighting.uasset','Art/flora_trail_settings.json','Art/flora_trail_canopy_settings.json','Art/Export/FloraTrail/build-report.json']:
  p=R/relative;destination=backup/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,destination)
 report['backup']=str(backup)
 assert L.load_level(D+'/L_FloraTrail');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 rows=[]
 for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if c.get_instance_count() and c.static_mesh and c.static_mesh.get_path_name().startswith(D+'/Meshes/'):
    changed=install_component(c)
    if changed:rows.append({'component':c.get_path_name(),'instances':c.get_instance_count(),'materials':changed})
 assert len(rows)==4 and sum(r['instances'] for r in rows)==340
 report['trees']=rows;cfg=settings();report['lighting']=configure(world,cfg,save_collection=True)
 yield 8
 report['assets']=verify(world)
 canopy=json.loads((R/'Art/flora_trail_canopy_settings.json').read_text());canopy.pop('reference_palette',None);canopy['source_version']='3.4.1';(R/'Art/flora_trail_canopy_settings.json').write_text(json.dumps(canopy,indent=2)+'\n')
 scene=json.loads((R/'Art/flora_trail_settings.json').read_text())
 for key,value in {'sun':cfg['sun_energy'],'sky':cfg['sky_strength'],'sun_colour':cfg['sun_colour'],'sky_colour':cfg['sky_colour'],'sun_ray':cfg['sun_ray'],'sun_unit_gain':cfg['sun_unit_gain'],'sky_unit_gain':cfg['sky_unit_gain']}.items():scene[key]=value
 (R/'Art/flora_trail_settings.json').write_text(json.dumps(scene,indent=2)+'\n')
 assert L.save_current_level();yield 3
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
 report.update(ok=True,protected_other_assets=len(protected),other_maps_and_source_assets_unchanged=True,settings=cfg,physics_and_geometry_unchanged=True)
 previous=json.loads((R/'Art/Export/FloraTrail/build-report.json').read_text());previous['source34_promotion']=report.copy();previous['settings']=scene
 previous['package_hashes']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'Content/GrandTour/ArtTests/FloraTrail').rglob('*') if p.suffix in ['.uasset','.umap']}
 (R/'Art/Export/FloraTrail/build-report.json').write_text(json.dumps(previous,indent=2));report['after_fingerprint']=audited_fingerprint();(O/'install-report.json').write_text(json.dumps(report,indent=2))
 yield 2;L.load_level('/Engine/Maps/Entry');world=None;yield 3
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
  report['error']=traceback.format_exc();(O/'install-report.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
 finally:
  if state is not None:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
