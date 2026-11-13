"""Native grass placements on the existing contact-capable component."""
import unreal as u
from pathlib import Path
import json,hashlib,traceback,math,time
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/NativeRoad';BASE='/Game/GrandTour/ArtTests/NativeRoad'
report=dict(ok=False);assets=u.EditorAssetLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
try:
 assert les.load_level(BASE+'/L_NativeRoad')
 grass=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTMixedGroundDetails))
 grass.generate_around_player=False;grass.grass.clear_instances();grass.distant_grass.clear_instances()
 mesh=grass.grass.static_mesh;b=mesh.get_bounds();rows=json.loads((OUT/'grass.json').read_text());transforms=[]
 for row in rows:
  x,y,z=row['p'];scale=row['height_cm']/max(1,2*b.box_extent.z)
  transforms.append(u.Transform(location=u.Vector(x,y,z-(b.origin.z-b.box_extent.z)*scale),rotation=u.Rotator(yaw=row['yaw']),scale=u.Vector(scale,scale,scale)))
 grass.grass.add_instances(transforms,False,True,False);grass.grass.set_cull_distances(10000,14000)
 assert grass.grass.get_instance_count()==len(rows)
 report['grass_mesh']=mesh.get_path_name();report['mesh_height_cm']=2*b.box_extent.z;report['grass_instances']=len(rows)
 report['grass_material']=grass.grass_material.get_path_name()
 # Thin branch meshes must be sized by their horizontal footprint. Scaling a
 # 2cm-thick twig to a 24cm height turned it into an enormous fallen tree.
 owner=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='NativeRoad_Understory')
 branch=next(c for c in owner.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name()=='SM_Branch')
 branch.clear_instances();b=branch.static_mesh.get_bounds();ts=[]
 for row in json.loads((OUT/'understory.json').read_text()):
  if row['kind']!=2:continue
  x,y,z=row['p'];native_scale=row['height_cm']/24
  # Native small_twig_a's occlusion footprint is 0.6 x 1.6m. This is a
  # documented footprint adapter until its original mesh is imported.
  scale=160*native_scale/max(1,2*max(b.box_extent.x,b.box_extent.y))
  ts.append(u.Transform(location=u.Vector(x,y,z-(b.origin.z-b.box_extent.z)*scale-2),rotation=u.Rotator(yaw=row['yaw']),scale=u.Vector(scale,scale,scale)))
 branch.add_instances(ts,False,True,False);report['twig_instances']=len(ts)
 # Original mud clod meshes were already imported by the earlier shader work.
 # Reuse them at native scale, replacing the pale generic rock stand-ins.
 debris=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='NativeRoad_NativeDebris')
 cs=[c for c in debris.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name().startswith(('SM_GD_Clod','SM_plants_mud_chunk'))]
 rows=json.loads((OUT/'debris.json').read_text());report['native_clods']=0
 for c,kind in zip(sorted(cs,key=lambda c:c.static_mesh.get_name()),['mud_chunk_a','mud_chunk_b']):
  mesh=u.load_asset('/Game/GrandTour/ArtTests/MudRoad/NativeInteractions/SM_plants_'+kind);assert mesh
  c.clear_instances();c.set_static_mesh(mesh);c.set_material(0,u.load_asset('/Game/GrandTour/ArtTests/MudRoad/NativeStage4/M_NativeClod'));ts=[]
  for d in rows:
   if d['brand']!=kind:continue
   qx,qy,qz,qw=d['native_quat'];rotation=u.Quat(-qx,-qz,-qy,qw).rotator();scale=d['scale']
   ts.append(u.Transform(location=u.Vector(*d.get('native_p',d['p'])),rotation=rotation,scale=u.Vector(scale,scale,scale)))
  c.add_instances(ts,False,True,False);c.set_collision_profile_name('BlockAll');c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS);report['native_clods']+=len(ts)
 assert report['native_clods']==983
 assert les.save_current_level();assert les.load_level('/Engine/Maps/Entry');assert les.load_level(BASE+'/L_NativeRoad')
 g=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTMixedGroundDetails));assert not g.generate_around_player and g.grass.get_instance_count()==report['grass_instances']
 for path,digest in json.loads((OUT/'install.json').read_text())['protected_before'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
 report.update(ok=True,saved_and_reloaded=True,protected_unchanged=True)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'finalize.json').write_text(json.dumps(report,indent=2))
# Drain the loaded map before shutdown, as in the stationary-check workflow.
les.load_level('/Engine/Maps/Entry')
deadline=time.monotonic()+4
def finish(dt):
 if time.monotonic()<deadline:return
 u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
