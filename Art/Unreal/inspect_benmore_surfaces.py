import unreal as u,json
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet/FerrariGroundContact')
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
r={'landscapes':[],'mud_patches':[],'profile_providers':[]}
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    if isinstance(a,u.LandscapeProxy):
        r['landscapes'].append({'label':a.get_actor_label(),'material':a.get_editor_property('landscape_material').get_path_name(),'default_surface':str(a.get_editor_property('default_phys_material')),'layers':str(a.get_editor_property('editor_layer_settings')) if hasattr(a,'editor_layer_settings') else None})
    if isinstance(a,u.GTMudPatch):
        r['mud_patches'].append({'label':a.get_actor_label(),'class':a.get_class().get_path_name(),'position':list(a.get_actor_location().to_tuple()),'profile':a.get_editor_property('has_profile'),'profile_max_sinkage_m':a.get_editor_property('profile_max_sinkage_m'),'profile_sinkage_rate':a.get_editor_property('profile_sinkage_rate')})
    if isinstance(a,u.GTTerrainBuilder):
        asset=a.get_editor_property('spec_asset')
        r['profile_providers'].append({'label':a.get_actor_label(),'asset':asset.get_path_name() if asset else None})
(OUT/'surfaces-before.json').write_text(json.dumps(r,indent=2));u.SystemLibrary.quit_editor()
