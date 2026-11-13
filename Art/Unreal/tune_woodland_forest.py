import unreal as u
from pathlib import Path
import sys,json,traceback,random
R=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(R/'Art/Unreal'))
from benmore_river_life_materials import props
B='/Game/GrandTour/ArtTests/BenmoreWoodland/Forest';report={'ok':False,'meshes':[]}
try:
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 for k in range(3):
  m=u.load_asset(B+'/SM_Fir_'+str(k));far=u.load_asset(B+'/SM_FirFar_'+str(k));assert m and far
  opts=props(u.StaticMeshReductionOptions(),auto_compute_lod_screen_size=False,reduction_settings=[props(u.StaticMeshReductionSettings(),percent_triangles=p,screen_size=s) for p,s in [(.18,1),(.07,.35),(.025,.18)]])
  assert sm.set_lods(m,opts)>=3
  assert sm.set_lod_from_static_mesh(m,3,far,0,True)==3
  assert sm.set_lod_screen_sizes(m,[1,.35,.18,.09])
  for lod in range(4):
   for sec in range(m.get_num_sections(lod)):sm.enable_section_cast_shadow(m,True,lod,sec)
  assert u.EditorAssetLibrary.save_loaded_asset(m)
  report['meshes'].append(dict(path=m.get_path_name(),vertices=[sm.get_number_verts(m,i) for i in range(4)]))
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/ArtTests/BenmoreWoodland/L_Benmore_Woodland')
 actors=u.get_editor_subsystem(u.EditorActorSubsystem)
 old=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='Woodland_DenseForest')
 forest=actors.spawn_actor_from_class(u.Actor,u.Vector());forest.set_actor_label('Woodland_DenseForest_New')
 trees=json.loads((R/'Art/Export/BenmoreWoodland/dense-trees.json').read_text());rng=random.Random(140925);trees=[t for t in trees if rng.random()<.62];trunks=[]
 for k in range(3):
  mesh=u.load_asset(B+'/SM_Fir_'+str(k));sb=u.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/SM_Fir_'+str(k)).get_bounds();ts=[]
  for x,y,z,kind,h,yaw in trees:
   if kind!=k:continue
   scale=h/(2*sb.box_extent.z);ts.append(u.Transform(location=u.Vector(x,y,z-(sb.origin.z-sb.box_extent.z)*scale-8),rotation=u.Rotator(yaw=yaw),scale=u.Vector(scale,scale,scale)))
   trunks.append(u.Transform(location=u.Vector(x,y,z+220),scale=u.Vector(.35,.35,4.4)))
  c=u.GTVegetationSubsystem.add_tagged_instances(forest,mesh,ts,'DenseForest','NoCollision',True);c.set_cull_distances(60000,75000)
  props(c,visible_in_ray_tracing=False,affect_distance_field_lighting=False,world_position_offset_disable_distance=3000)
 c=u.GTVegetationSubsystem.add_tagged_instances(forest,u.load_asset('/Engine/BasicShapes/Cylinder'),trunks,'WoodlandTrunks','BlockAll',False);c.set_visibility(False);c.set_hidden_in_game(True);c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
 actors.destroy_actor(old);forest.set_actor_label('Woodland_DenseForest');assert les.save_current_level();les.load_level('/Engine/Maps/Entry')
 report.update(ok=True,trees=len(trees),wind_disable_cm=3000,distance_field_lighting=False)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(R/'Art/Export/BenmoreWoodland/foresttune.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
