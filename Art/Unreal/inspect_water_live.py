import unreal as u,json
from pathlib import Path
out=Path(u.Paths.project_dir())/'Art/Export/BenmoreGaea/WaterDetail_20261011'
out.mkdir(exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
game=u.EditorLevelLibrary.get_game_world()
r={'editor_world':world.get_path_name(),'playing':bool(game)}
if game:
    pc=u.GameplayStatics.get_player_controller(game,0)
    pawn=pc.get_pawn()
    r['pawn']={'class':pawn.get_class().get_name(),'position':pawn.get_actor_location().to_tuple(),'rotation':pawn.get_actor_rotation().to_tuple()}
for name in ['get_dirty_map_packages','get_dirty_content_packages']:
    if hasattr(u.EditorLoadingAndSavingUtils,name):r[name]=[p.get_path_name() for p in getattr(u.EditorLoadingAndSavingUtils,name)()]
m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterRapids/M_GC_DomainRiver')
mel=u.MaterialEditingLibrary
r['refraction_node']=str(mel.get_material_property_input_node(m,u.MaterialProperty.MP_REFRACTION))
for key in ['blend_mode','shading_model','refraction_method','refraction_depth_bias','opacity_mask_clip_value']:
    try:r[key]=str(m.get_editor_property(key))
    except Exception:pass
for prop,name in [(u.MaterialProperty.MP_BASE_COLOR,'pixel'),(u.MaterialProperty.MP_OPACITY_MASK,'mask')]:
    n=mel.get_material_property_input_node(m,prop)
    if isinstance(n,u.MaterialExpressionCustom):(out/(name+'.hlsl')).write_text(str(n.get_editor_property('code')))
r['refraction_enums']={x:str(getattr(u.RefractionMode,x)) for x in dir(u.RefractionMode) if x.startswith('RM_')}
(out/'live-inspection.json').write_text(json.dumps(r,indent=2))
u.log('WATER_LIVE_INSPECTION '+str(out))
