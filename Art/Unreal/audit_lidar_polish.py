"""Inspect the saved production map and material programs without changing assets."""
import unreal as u
import json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Saved/LidarAuthoringQA/LP6'
OUT.mkdir(parents=True,exist_ok=True)
try:
 les=u.get_editor_subsystem(u.LevelEditorSubsystem)
 assert les.load_level('/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy')
 refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 result={'materials':{},'components':[]}
 for path in ['/Game/GrandTour/ArtTests/LidarStudy/M_RiverWater','/Game/GrandTour/Environment/NativePlants/v01/M_NZ_Foliage','/Game/GrandTour/ArtTests/LidarStudy/CanopyKit/M_FirFar_0']:
  m=u.load_asset(path);result['materials'][path]=[{'desc':str(n.get_editor_property('desc')),'inputs':[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')],'code':str(n.get_editor_property('code'))} for n in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)]
 for a in refs:
  if a.get_actor_label() in ['LidarStudy_Forest','LidarStudy_Understory']:
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
    if c.static_mesh:result['components'].append(dict(actor=a.get_actor_label(),mesh=c.static_mesh.get_path_name(),count=c.get_instance_count(),lod=c.get_editor_property('instance_lod_distance_scale'),materials=[str(m) for m in c.get_editor_property('override_materials')]))
 (OUT/'audit.json').write_text(json.dumps(result,indent=2))
except Exception:(OUT/'audit-error.txt').write_text(traceback.format_exc())
u.SystemLibrary.quit_editor()
