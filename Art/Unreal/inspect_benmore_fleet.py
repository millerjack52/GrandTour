import unreal as u, json
from pathlib import Path
OUT=Path('C:/GrandTour/Art/Export/BenmoreFleet');OUT.mkdir(exist_ok=True)
MAP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP)
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
assert world.get_path_name().startswith(MAP+'.')
result={'actors':[],'starts':[]}
for a in actors:
    if isinstance(a,(u.PlayerStart,u.Pawn)) or 'Fleet' in a.get_actor_label():
        row={'label':a.get_actor_label(),'class':a.get_class().get_path_name(),'location':a.get_actor_location().to_tuple(),'rotation':a.get_actor_rotation().to_tuple()}
        result['actors'].append(row)
        if isinstance(a,u.PlayerStart):result['starts'].append(row)
gm=world.get_world_settings().get_editor_property('default_game_mode')
result['gamemode']=str(gm)
(OUT/'inventory.json').write_text(json.dumps(result,indent=2))
u.log('BENMORE_FLEET_INVENTORY_DONE')
