"""Move the too-steep recovery stop and clear its arrival/camera space."""
import unreal as u
import json,traceback,shutil,time
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BigMountain';LEVEL='/Game/GrandTour/ArtTests/BigMountain/L_BigMountain'
report={'ok':False}
try:
 backup=ROOT/'Saved/BigMountainBackups'/('stops-'+str(time.time_ns()));backup.mkdir(parents=True);shutil.copy2(ROOT/'Content/GrandTour/ArtTests/BigMountain/L_BigMountain.umap',backup/'L_BigMountain.umap')
 data=json.loads((OUT/'authoring.json').read_text());les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(LEVEL)
 actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors();route=next(a for a in actors if isinstance(a,u.GTMudRoute))
 route.set_editor_property('recovery_points',[u.Transform(location=u.Vector(*s['center'],s['center_height_cm']+80),rotation=u.Rotator(yaw=s['yaw'])) for s in data['sites']])
 site=next(s for s in data['sites'] if s['name']=='Hollows');x,y=site['center'];removed=0
 for a in actors:
  if a.get_actor_label()!='BigMountain_Forest':continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   erase=[]
   for i in range(c.get_instance_count()):
    p=c.get_instance_transform(i,True).translation
    if (p.x-x)**2+(p.y-y)**2<1200**2:erase.append(i)
   for i in reversed(erase):c.remove_instance(i);removed+=1
 assert les.save_current_level();assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
 report.update(ok=True,removed_tree_and_trunk_instances=removed,recovery=site)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'repair.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
