"""Undo the single DustLab actor accidentally saved after SaveMap left its source open.
Does not rebuild terrain, change shared settings, or load Benmore.
"""
import json
import time
import traceback
from pathlib import Path
import unreal as u

u.EditorPythonScripting.set_keep_python_script_alive(True)
out = Path(u.Paths.project_dir()) / 'Art/Export/DustLab/source-map-repair.json'
report = {'ok': False, 'removed': []}
try:
    path = '/Game/GrandTour/ArtTests/DeformableGravel/L_GravelDeform'
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert levels.load_level(path)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    found = [a for a in actors.get_all_level_actors() if isinstance(a, u.GTDustLab) and a.get_actor_label() == 'DustLab_OptIn']
    assert len(found) == 1, 'Expected exactly our accidental prototype actor'
    for actor in found:
        report['removed'].append(actor.get_path_name())
        assert actors.destroy_actor(actor)
    assert levels.save_current_level()
    report['ok'] = True
except Exception:
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
finally:
    out.write_text(json.dumps(report, indent=2))
    quit_at = time.monotonic() + 3
    def tick(dt):
        if time.monotonic() > quit_at:
            u.unregister_slate_post_tick_callback(handle)
            u.SystemLibrary.quit_editor()
    handle = u.register_slate_post_tick_callback(tick)
