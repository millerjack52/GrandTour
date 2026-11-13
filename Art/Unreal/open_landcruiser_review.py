"""Position the existing review level for visual inspection in the editor."""
import unreal as u,sys
from pathlib import Path
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.EditorLevelLibrary.eject_pilot_level_actor()
actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
floor=next((a for a in actors if a.get_actor_label()=='LC80_Floor'),None)
if floor:
    floor.set_actor_scale3d(u.Vector(200,200,.2))
    u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
pos=u.Vector(620,-600,300);rot=u.MathLibrary.find_look_at_rotation(pos,u.Vector(0,0,98))
u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(pos,rot)
u.SystemLibrary.execute_console_command(world,'r.ScreenPercentage 100')
if not u.AssetRegistryHelpers.get_asset_registry().is_loading_assets():
    u.EditorAssetLibrary.sync_browser_to_objects(['/Game/GrandTour/Vehicles/Bodies/LandCruiser80/SK_LandCruiser80'])
view=sys.argv[1] if len(sys.argv)>1 else 'Front'
camera=next((a for a in actors if a.get_actor_label()=='LC80_Camera_'+view),None)
if camera:u.EditorLevelLibrary.pilot_level_actor(camera)
u.get_editor_subsystem(u.LevelEditorSubsystem).editor_set_game_view(True)
Path(u.Paths.project_dir(),'Art/Export/LandCruiser/Package_v03/editor_review_ready.txt').write_text('Land Cruiser review viewport positioned; inspect renderer separately.')
