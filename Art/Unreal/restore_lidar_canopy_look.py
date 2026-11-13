"""Restore the user's preferred pre-surface-shadow appearance, preserving dressing."""
import unreal as u,json,sys,os,time,traceback,gc,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
import lidar_first_section as S
import lidar_forest_atmosphere as A
from forest_shaders import connected_nodes
QA=ROOT/'Saved/LidarAuthoringQA/PreferredCanopy';QA.mkdir(exist_ok=True)
STAGE=os.environ.get('GT_RESTORE_STAGE','install');les=u.get_editor_subsystem(u.LevelEditorSubsystem);mel=u.MaterialEditingLibrary
report=dict(ok=False,stage=STAGE);busy=False;deadline=0

def state():
 rows=C.actors.get_all_level_actors()
 return dict(bank=S.snapshot(),understory=S.outside_snapshot(),instances={a.get_actor_label()+'/'+c.get_name():dict(mesh=c.static_mesh.get_path_name(),**C.fingerprint(c)) for a in rows if a.get_actor_label()=='LidarStudy_Forest' or a.get_actor_label().startswith('LidarStudy_LevelDetail_') for c in a.get_components_by_class(u.InstancedStaticMeshComponent)},ground=[str(a.output_digest) for a in rows if isinstance(a,u.GTProceduralGround)])

def validate():
 assert state()==json.loads((QA/'protected.json').read_text())
 expected=u.load_asset(C.BASE+'/MI_NZ_Foliage_Canopy')
 forest=next(a for a in C.actors.get_all_level_actors() if a.get_actor_label()=='LidarStudy_Forest')
 for k in range(3):
  mesh=u.load_asset(C.DEST+'/SM_CD_Canopy_'+str(k));assert mesh.get_material(1)==expected
  c=next(c for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh==mesh);assert c.get_material(1)==expected
 for kind in ['Mature','Pole','Edge']:
  m=u.load_asset(C.DEST+'/'+kind+'/M_PD_TreeProxy')
  assert not any(str(n.get_editor_property('desc'))=='CanopySurfaceShadow' for n in connected_nodes(m))
  assert str(mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR).get_editor_property('desc'))=='CanopyEnvelopeLighting'
 fog=next(a for a in C.actors.get_all_level_actors() if isinstance(a,u.ExponentialHeightFog));f=fog.component;s=json.loads(A.CONFIG.read_text())
 for key,val in [('fog_density',s['density']),('fog_height_falloff',s['height_falloff']),('start_distance',s['start_cm']),('fog_max_opacity',s['max_opacity'])]:assert abs(f.get_editor_property(key)-val)<.0001
 assert abs(fog.get_actor_location().z-s['height_cm'])<.001
 assert [f.fog_inscattering_luminance.r,f.fog_inscattering_luminance.g,f.fog_inscattering_luminance.b]==s['luminance']
 return dict(protected_packages=C.validate_protected(),all_planting_and_ground_preserved=True,detail_instances=sum(v['count'] for k,v in state()['instances'].items() if k.startswith('LidarStudy_LevelDetail_')),fog=s)

def run():
 assert les.load_level(C.BASE+'/L_LidarStudy');yield 2
 if STAGE=='install':
  (QA/'protected.json').write_text(json.dumps(state(),indent=2))
  recipe=json.loads((C.OUT/'recipe.json').read_text());recipe['surface_shadows']=False;recipe['preferred_look']='distance-haze-after, restored from user-selected comparison';(C.OUT/'recipe.json').write_text(json.dumps(recipe,indent=2))
  shutil.copy2(ROOT/'Saved/LidarAuthoringQA/DistanceHaze/before-balance-config.json',A.CONFIG)
  for kind in ['Mature','Pole','Edge']:
   m=u.load_asset(C.DEST+'/'+kind+'/M_PD_TreeProxy')
   nodes=connected_nodes(m)
   envelope=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='CanopyEnvelopeLighting')
   assert mel.connect_material_property(envelope,'',u.MaterialProperty.MP_BASE_COLOR)
   assert mel.connect_material_property(envelope,'AO',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
   assert not mel.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m,False)
  C.apply();report.update(validate());assert les.save_current_level();report['saved']=True
 else:report.update(validate());report['saved_reload']=True
 report['ok']=True;yield 1
steps=run()
def tick(dt):
 global busy,deadline
 if busy or time.monotonic()<deadline:return
 busy=True
 try:deadline=time.monotonic()+float(next(steps))
 except StopIteration:
  (QA/(STAGE+'.json')).write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());(QA/(STAGE+'.json')).write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
