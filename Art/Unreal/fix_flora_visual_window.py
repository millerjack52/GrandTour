"""Repair only demo mud/tread coverage gates; no soil, terrain or source edits."""
import unreal as u,json,traceback,sys,shutil
from pathlib import Path
sys.path.insert(0,'C:/GrandTour/Art/Unreal')
from flora_lidar_mud import local_visual_window
O=Path('C:/GrandTour/Art/Export/FloraDrive');r=dict(ok=False,materials=[])
try:
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/FloraDrive/L_FloraDrive')
    visual=next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual))
    r['follow_player_grid']=visual.follow_player_grid;r['half_size_cm']=visual.half_size_cm
    for m in [visual.material,visual.track_material]:
        assert m.get_path_name().startswith('/Game/GrandTour/ArtTests/FloraDrive/LidarMud/')
        row=dict(material=m.get_path_name())
        for e in u.MaterialEditingLibrary.get_material_expressions(m):
            if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='MR_VisualWindow':
                v=e.get_editor_property('default_value');row['before']=[v.r,v.g,v.b,v.a]
        row['after']=local_visual_window(m,visual)
        u.MaterialEditingLibrary.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m)
        r['materials'].append(row)
    r['ok']=True
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(O/'window-report.json').write_text(json.dumps(r,indent=2))
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.quit_editor()
