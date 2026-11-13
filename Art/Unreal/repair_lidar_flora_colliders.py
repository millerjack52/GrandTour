"""Restore the source collision of dead spars that were deliberately not replaced."""
import unreal as u,json,math,hashlib,traceback
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraIntegration';r={'ok':False}
try:
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
 records=json.loads((O/'source-removals.json').read_text());trees=[v['transform'][:2] for v in records if v['actor']=='LidarStudy_Forest' and 'SM_CD_Canopy' in v['mesh']]
 orphans=[v for v in records if v['mesh']=='/Engine/BasicShapes/Cylinder.Cylinder' and min(math.dist(v['transform'][:2],t) for t in trees)>1]
 a=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label()=='LidarStudy_Forest')
 for row in orphans:
  c=next(c for c in a.get_components_by_class(u.InstancedStaticMeshComponent) if c.get_name()==row['component']);v=row['transform'];c.modify()
  c.add_instance(u.Transform(location=u.Vector(*v[:3]),rotation=u.Quat(*v[3:7]).rotator(),scale=u.Vector(*v[7:])),True)
 assert len(orphans)<=1
 if orphans:
  assert les.save_current_level()
  (O/'source-removals.json').write_text(json.dumps([v for v in records if v not in orphans],indent=2))
 r.update(ok=True,restored_dead_spar_colliders=len(orphans),positions=[v['transform'][:3] for v in orphans],map_sha256=hashlib.sha256((R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap').read_bytes()).hexdigest())
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(O/'repair-report.json').write_text(json.dumps(r,indent=2));u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.quit_editor()
