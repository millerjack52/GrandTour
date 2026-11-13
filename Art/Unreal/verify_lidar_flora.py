"""Fresh-load verification of the saved map, without mutating it."""
import unreal as u,json,hashlib,traceback,gc,time
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraIntegration';D='/Game/GrandTour/ArtTests/LidarStudy/FloraIntegration'
def verify():
 r={'ok':False};path=R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap';before=hashlib.sha256(path.read_bytes()).hexdigest()
 try:
  install=json.loads((O/'install-report.json').read_text());repair=json.loads((O/'repair-report.json').read_text())
  candidates=[O/name for name in ['install-report.json','repair-report.json','coverage-report.json'] if (O/name).exists()]
  newest=json.loads(max(candidates,key=lambda p:p.stat().st_mtime).read_text())
  assert before==newest.get('map_sha256',newest.get('saved_map_sha256'))
  assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
  rows=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();author=next(a for a in rows if isinstance(a,u.GTProceduralGround));surface=next(a for a in rows if isinstance(a,u.GTLandscapeSurface))
  assert str(author.output_digest)==install['protected_before']['ground']
  assert all(surface.get_editor_property(k)==v for k,v in install['protected_before']['soil'].items())
  water=sorted([(a.get_actor_label(),a.get_actor_location().to_tuple()) for a in rows if isinstance(a,u.GTWaterSheet)])
  assert json.loads(json.dumps(water))==install['protected_before']['water']
  owner=next(a for a in rows if a.get_actor_label()=='LidarStudy_FloraIntegration_Vegetation');counts={}
  for c in owner.get_components_by_class(u.InstancedStaticMeshComponent):
   n=c.static_mesh.get_name()
   if n.startswith('SM_Path_FP_'):counts[n.removeprefix('SM_Path_FP_')]=c.get_instance_count()
  assert counts==install['counts'],('Saved foliage population changed',counts)
  rocks=[a for a in rows if a.get_actor_label().startswith('LidarStudy_FloraIntegration_Rock_')];assert len(rocks)==12
  visual=next(a for a in rows if isinstance(a,u.GTMudRunnerVisual));assert visual.follow_player_grid and visual.material.get_path_name().startswith(D+'/M_FloraDetail')
  assert author.relief_material.get_path_name().startswith(D+'/M_FloraTerrain')
  for a in rows:
   if isinstance(a,u.GTMixedGroundDetails):assert a.grass_material.get_path_name().startswith(D+'/Grass/')
  forest=next(a for a in rows if a.get_actor_label()=='LidarStudy_Forest');colliders=next(c for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh.get_name()=='Cylinder')
  for p in repair['positions']:
   ids=colliders.get_instances_overlapping_sphere(u.Vector(*p),100,True)
   assert sum((colliders.get_instance_transform(i,True).translation-u.Vector(*p)).length()<.1 for i in ids)==1,'Retained dead spar must have exactly one original collider'
  assert hashlib.sha256(path.read_bytes()).hexdigest()==before
  r.update(ok=True,map_sha256=before,trees=install['tree_instances'],plants=install['plant_instances'],outcrops=len(rocks),native_soil_and_terrain_unchanged=True,water_domains_unchanged=True,following_visual_grid=True,retained_dead_tree_collision=True)
 except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
 return r
r=verify();(O/'verify-report.json').write_text(json.dumps(r,indent=2))
gc.collect();u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');gc.collect()
deadline=time.monotonic()+3
def finish(dt):
 if time.monotonic()>deadline:u.unregister_slate_post_tick_callback(handle);gc.collect();u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
