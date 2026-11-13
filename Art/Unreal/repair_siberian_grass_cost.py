"""Patch saved grass render settings without rebuilding terrain or scattering."""
import unreal as u
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import siberian_surface_repairs as repairs
base='/Game/GrandTour/ArtTests/SiberianShowcase'
for path in u.EditorAssetLibrary.list_assets(base,True,False):
    asset=u.EditorAssetLibrary.load_asset(path)
    if isinstance(asset,u.Material) and asset.get_name()=='M_Soil':repairs.repair(asset,'M_Soil')
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/SiberianShowcase/L_SiberianShowcase')
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if isinstance(a,u.GTMixedGroundDetails):
        a.grass.set_cull_distances(2500,5500)
        a.grass.set_editor_property('visible_in_ray_tracing',False)
assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
(Path(u.Paths.project_dir())/'Art/Export/SiberianShowcase/repair-report.json').write_text(json.dumps({'ok':True,'grass_ray_tracing':False,'grass_cull_cm':[2500,5500]}))
import audit_siberian_materials
assert audit_siberian_materials.report['ok']
