import unreal as u,sys,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreEnvironment';sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_environment_scene import ground_large_rocks
r={'ok':False}
try:
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    r['rocks']=ground_large_rocks(world)
    mat=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/M_Benmore_VergeStone');u.MaterialEditingLibrary.set_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);u.EditorAssetLibrary.save_loaded_asset(mat)
    for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label().startswith('Benmore_Backdrop_'):
            assert a.get_actor_location().length()<.1,str(a.get_actor_location())
    assert les.save_current_level();r['ok']=True
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(OUT/'support-report.json').write_text(json.dumps(r,indent=2));u.SystemLibrary.quit_editor()
