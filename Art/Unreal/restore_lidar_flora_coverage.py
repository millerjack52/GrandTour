"""Retain established low ferns and interactive grass beneath the new tree kit."""
import unreal as u,json,math,sys,hashlib,traceback,gc,time,shutil
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraIntegration';sys.path.insert(0,str(R/'Art/Unreal'))
import lidar_flora_materials as F,lidar_logging_trial as T
def run():
 r={'ok':False};les=u.get_editor_subsystem(u.LevelEditorSubsystem)
 try:
  cfg=json.loads((O/'profile.json').read_text());cfg.update(retain_native_grass=True,retain_ground_ferns=True)
  route=T.route(json.loads((R/'Art/Export/LidarStudy/Place/roads.json').read_text()))
  assert les.load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
  actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
  author=next(a for a in actors if isinstance(a,u.GTProceduralGround));digest=str(author.output_digest)
  owner=next(a for a in actors if a.get_actor_label()=='LidarStudy_Understory')
  records=json.loads((O/'source-removals.json').read_text());archive=O/'source-removals-before-coverage.json'
  if not archive.exists():shutil.copy2(O/'source-removals.json',archive)
  restored=[];groups={};r['restored_by_mesh']={};r['counts_before']={}
  for row in records:
   if row['actor']!='LidarStudy_Understory' or not any(k in row['mesh'] for k in ['CrownFern','Kiokio']):continue
   p=row['transform'];blocked=False
   for rock in cfg['outcrops']:
    x,y,_=T.at(route,rock['station'],rock['across'])
    if math.hypot(p[0]-x,p[1]-y)<rock['width_cm']*.5+100:blocked=True;break
   if blocked:continue
   groups.setdefault(row['component'],[]).append(row);restored.append(row)
  for name,rows in groups.items():
   c=next(c for c in owner.get_components_by_class(u.InstancedStaticMeshComponent) if c.get_name()==name)
   assert c.static_mesh.get_path_name()==rows[0]['mesh'];r['counts_before'][name]=c.get_instance_count()
   transforms=[]
   for row in rows:
    v=row['transform'];transforms.append(u.Transform(location=u.Vector(*v[:3]),rotation=u.Quat(*v[3:7]).rotator(),scale=u.Vector(*v[7:])))
   c.modify();c.add_instances(transforms,False,True)
   assert c.get_instance_count()==r['counts_before'][name]+len(rows)
   r['restored_by_mesh'][c.static_mesh.get_name()]=len(rows)
  cache={}
  for a in actors:
   if not isinstance(a,u.GTMixedGroundDetails):continue
   for field in ['grass_material','rank_material','card_grass_material','distant_grass_material','distant_pasture_material']:
    source=a.get_editor_property(field)
    if source:a.set_editor_property(field,F.grass_exclusion(source,route,cfg,cache))
  assert str(author.output_digest)==digest
  assert les.save_current_level()
  (O/'source-removals.json').write_text(json.dumps([v for v in records if v not in restored],indent=2))
  (O/'profile.json').write_text(json.dumps(cfg,indent=2))
  r.update(ok=True,restored_ferns=len(restored),native_grass_retained=True,rock_core_exclusion=True,ground_digest=digest,map_sha256=hashlib.sha256((R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap').read_bytes()).hexdigest())
 except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
 return r
r=run();(O/'coverage-report.json').write_text(json.dumps(r,indent=2));gc.collect()
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');gc.collect();deadline=time.monotonic()+3
def finish(dt):
 if time.monotonic()>deadline:u.unregister_slate_post_tick_callback(handle);gc.collect();u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
