"""Private copy of the mud driving strip and fine spray; never saves a source map."""
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/DustLab'
BASE = '/Game/GrandTour/ArtTests/DustLab'
LEVEL = BASE + '/L_MudFlickLab'
SOURCE = '/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive'
RUN = BASE + '/Mud_' + datetime.now().strftime('%Y%m%d_%H%M%S')
eal = u.EditorAssetLibrary
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
report = {'ok': False, 'level': LEVEL, 'source': SOURCE}
u.EditorPythonScripting.set_keep_python_script_alive(True)

try:
    if not eal.does_asset_exist(LEVEL):
        assert levels.load_level(SOURCE)
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        assert u.EditorLoadingAndSavingUtils.save_map(world, LEVEL)
        del world
        report.update(ok=True, install_pending=True)
    else:
        # Reuse the approved masked wet-mud atlas material as a private copy.
        material = eal.duplicate_asset('/Game/GrandTour/FX/M_GT_SprayMud', RUN + '/M_MudFlick')
        assert material
        assert eal.save_loaded_asset(material)
        log = u.GTDustLabSetupLibrary.build_mud_flick(RUN, 'NS_MudFlick', material)
        report['niagara_log'] = log.splitlines()
        assert 'BUILD OK' in log and 'FAIL' not in log, log
        system = eal.load_asset(RUN + '/NS_MudFlick')
        assert system and eal.save_loaded_asset(system)
        assert levels.load_level(LEVEL)
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        assert world.get_path_name().startswith(LEVEL + '.')
        del world
        actors = u.get_editor_subsystem(u.EditorActorSubsystem)
        for actor in actors.get_all_level_actors():
            if isinstance(actor, u.GTMudFlickLab):
                actors.destroy_actor(actor)
        lab = actors.spawn_actor_from_class(u.GTMudFlickLab, u.Vector())
        lab.set_actor_label('MudFlickLab_OptIn')
        lab.mud_system = system
        lab.intensity = 1.4
        assert levels.save_current_level()
        report.update(ok=True, system=system.get_path_name(), material=material.get_path_name())
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    (OUT / 'mud-setup-report.json').write_text(json.dumps(report, indent=2))
    quit_at = time.monotonic() + 3.
    quit_stage = 0
    def quit_tick(dt):
        global quit_at, quit_stage
        if time.monotonic() < quit_at:
            return
        if quit_stage == 0 and not report.get('install_pending'):
            globals().pop('actor', None)
            globals().pop('lab', None)
            levels.load_level('/Engine/Maps/Entry')
            quit_stage = 1
            quit_at = time.monotonic() + 3.
            return
        u.unregister_slate_post_tick_callback(quit_handle)
        u.SystemLibrary.quit_editor()
    quit_handle = u.register_slate_post_tick_callback(quit_tick)
