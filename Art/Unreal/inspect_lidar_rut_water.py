"""Read-only saved-map water/particle bindings."""
import unreal as u,json
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve()
les=u.get_editor_subsystem(u.LevelEditorSubsystem)
assert les.load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
report={}
for cls,fields in [(u.GTMudRunnerWheelEffects,['materials']),(u.GTLandscapeSurface,['simulated_water','use_native_water_response','use_native_substance_response','separate_visual_mesh']),(u.GTWaterSheet,['water_domain','mud_surface','surface_material_path','road_pool_surfaces'])]:
 report[cls.__name__]=[]
 for a in actors:
  if not isinstance(a,cls):continue
  row={'name':a.get_actor_label()}
  for k in fields:
   try:row[k]=str(a.get_editor_property(k))
   except Exception:row[k]='unexposed'
  report[cls.__name__].append(row)
report['pool_materials']=[str(a.mesh.get_material(0)) for a in actors if isinstance(a,u.GTRoadWaterMesh)]
(root/'Saved/LidarAuthoringQA/rut-water-before.json').write_text(json.dumps(report,indent=2))
actors=None;u.SystemLibrary.quit_editor()
